#!/usr/bin/env python3
"""Detect emotional state from recent message patterns.

Reads the last ~10 lines from today's daily log, analyzes for emotional
signals using keyword matching and message pattern heuristics, and outputs
a structured mood assessment.

Exit codes: 0=success, 1=no messages (uses baseline), 2=error
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / "scripts" / "logs"
STATE_FILE = BASE_DIR / "memory" / "state.json"
MOOD_OUTPUT = LOGS_DIR / "last_mood.json"

# Emotion vocabulary (fixed set from spec)
EMOTION_KEYWORDS = {
    "frustrated": ["ugh", "annoying", "frustrated", "broken", "stupid", "wtf", "dammit", "doesn't work", "not working", "failed again"],
    "stressed": ["deadline", "urgent", "asap", "rush", "overwhelmed", "behind", "crunch", "pressure"],
    "excited": ["awesome", "excited", "amazing", "love it", "finally", "yes!", "great", "nice", "cool", "works"],
    "accomplished": ["done", "finished", "completed", "deployed", "shipped", "resolved", "fixed", "solved", "working"],
    "amused": ["lol", "haha", "lmao", "funny", "ha", "heh", "\U0001f602", "\U0001f480"],
    "confused": ["confused", "what?", "huh", "unclear", "don't understand", "makes no sense", "??"],
    "annoyed": ["annoying", "ridiculous", "seriously", "come on", "again?"],
    "proud": ["proud", "nailed it", "perfect", "exactly right", "beautiful"],
    "worried": ["worried", "concerned", "hope", "what if", "scared", "nervous"],
    "calm": ["fine", "okay", "good", "alright", "sure", "sounds good", "makes sense"],
}

SIGNAL_PATTERNS = {
    "short_responses": r"^.{1,20}$",
    "exclamation_increase": r"!{2,}",
    "question_barrage": r"\?.*\?.*\?",
    "caps_emphasis": r"\b[A-Z]{3,}\b",
    "ellipsis": r"\.\.\.+$",
}

TIMESTAMP_PATTERN = re.compile(
    r"^\[?(?:(\d{4}-\d{2}-\d{2})[T ])?(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?Z?\]?\s*(?:-|\bUser:|\bOperator:)?\s*(.*)$",
    re.IGNORECASE
)


def load_baseline_mood():
    """Load last known mood from state.json as fallback."""
    try:
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
        return state.get("operator_mood", "neutral")
    except (FileNotFoundError, json.JSONDecodeError):
        return "neutral"


def get_today_log():
    """Find today's daily log file."""
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    daily_dir = BASE_DIR / "memory" / "daily"
    log_file = daily_dir / f"{date_str}.md"
    if log_file.exists():
        return log_file
    return None


def extract_messages(log_path, count=15):
    """Extract last N non-empty, non-header lines from daily log in chronological order."""
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return []

    collected = []
    for line in reversed(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("<!--"):
            continue
        collected.append(stripped)
        if len(collected) >= count:
            break
    # Return in forward chronological order
    return list(reversed(collected))


def parse_message_telemetry(raw_messages):
    """Parse messages into chronological structured entries with timestamp telemetry."""
    entries = []
    for line in raw_messages:
        match = TIMESTAMP_PATTERN.match(line)
        if match:
            date_part, hour, minute, second, content = match.groups()
            sec_of_day = int(hour) * 3600 + int(minute) * 60 + int(second)
            clean_text = content.strip() if content else line
            entries.append({
                "raw": line,
                "text": clean_text,
                "sec_of_day": sec_of_day,
                "has_ts": True
            })
        else:
            clean_text = line[2:].strip() if line.startswith("- ") else line
            entries.append({
                "raw": line,
                "text": clean_text,
                "sec_of_day": None,
                "has_ts": False
            })
    return entries


def compute_telemetry_dynamics(entries):
    """Compute interaction velocity, sentence length contraction, and punctuation acceleration."""
    signals = []
    modifiers = {}

    if not entries:
        return signals, modifiers

    # 1. Interaction Velocity: Rapid short queries (< 10 seconds apart)
    timed_entries = [e for e in entries if e["has_ts"]]
    rapid_burst_count = 0
    if len(timed_entries) >= 2:
        for i in range(len(timed_entries) - 1):
            delta = timed_entries[i+1]["sec_of_day"] - timed_entries[i]["sec_of_day"]
            if delta < 0:
                delta += 86400  # Midnight rollover
            if 0 < delta < 10:
                rapid_burst_count += 1

    if rapid_burst_count >= 1:
        signals.append("rapid interaction velocity (<10s burst)")
        modifiers["frustrated"] = modifiers.get("frustrated", 0) + (rapid_burst_count * 2)
        modifiers["stressed"] = modifiers.get("stressed", 0) + rapid_burst_count

    # 2. Sentence Length Contraction (> 60% drop over recent turns)
    lengths = [len(e["text"]) for e in entries]
    if len(lengths) >= 3:
        mid = max(1, len(lengths) // 2)
        baseline_avg = sum(lengths[:mid]) / mid
        recent_avg = sum(lengths[-2:]) / 2

        if baseline_avg >= 20 and recent_avg <= (baseline_avg * 0.40):
            signals.append("sentence length contraction (>60% drop)")
            modifiers["stressed"] = modifiers.get("stressed", 0) + 3
            modifiers["frustrated"] = modifiers.get("frustrated", 0) + 2

    # 3. Capitalization & Punctuation Acceleration (multiple ? or ! bursts)
    punc_burst_pattern = re.compile(r"(\?{2,}|!{2,}|[\?!]{2,})")
    caps_pattern = re.compile(r"\b[A-Z]{3,}\b")

    punctuation_burst_count = 0
    caps_word_count = 0

    for e in entries:
        txt = e["text"]
        if punc_burst_pattern.search(txt):
            punctuation_burst_count += 1
        caps_words = caps_pattern.findall(txt)
        if caps_words:
            caps_word_count += len(caps_words)

    if punctuation_burst_count >= 1:
        signals.append("punctuation acceleration (multiple ?/! bursts)")
        modifiers["frustrated"] = modifiers.get("frustrated", 0) + (punctuation_burst_count * 2)
        modifiers["worried"] = modifiers.get("worried", 0) + 1

    if caps_word_count >= 2:
        signals.append("capitalization acceleration (all-caps emphasis)")
        modifiers["frustrated"] = modifiers.get("frustrated", 0) + 2
        modifiers["stressed"] = modifiers.get("stressed", 0) + 1

    return signals, modifiers


def analyze_messages(raw_messages):
    """Analyze messages using dual-layer keyword matching and telemetry dynamics."""
    if not raw_messages:
        return "neutral", 0.0, ["no messages"]

    entries = parse_message_telemetry(raw_messages)
    telemetry_signals, modifiers = compute_telemetry_dynamics(entries)

    # 1. Keyword semantic scoring
    emotion_scores = {}
    for emotion, keywords in EMOTION_KEYWORDS.items():
        score = 0
        for e in entries:
            text_lower = e["text"].lower()
            for kw in keywords:
                if kw in text_lower:
                    score += 1
        if score > 0:
            emotion_scores[emotion] = score

    # 2. Integrate telemetry modifiers
    for emotion, mod in modifiers.items():
        emotion_scores[emotion] = emotion_scores.get(emotion, 0) + mod

    signals = list(telemetry_signals)
    short_count = sum(1 for e in entries if len(e["text"]) <= 20)

    if short_count > len(entries) * 0.6:
        signals.append("predominantly short responses")

    # 3. Mood synthesis & confidence calculation
    if emotion_scores:
        top_emotion = max(emotion_scores, key=emotion_scores.get)
        total_score = sum(emotion_scores.values())
        # Keyword agreement + telemetry boost
        confidence = min(0.95, round(0.5 + (total_score / (len(entries) * 2.0)), 2))
        mood = top_emotion
    elif short_count > len(entries) * 0.6:
        mood = "focused"
        confidence = 0.65
        signals.append("brief, task-oriented messages")
    else:
        mood = "neutral"
        confidence = 0.50

    if not signals:
        signals = ["normal cadence"]

    return mood, confidence, signals


def main():
    log_path = get_today_log()
    exit_code = 0

    if log_path is None:
        baseline = load_baseline_mood()
        mood, confidence, signals = baseline, 0.3, ["no daily log, using baseline"]
        exit_code = 1
    else:
        messages = extract_messages(log_path)
        if not messages:
            baseline = load_baseline_mood()
            mood, confidence, signals = baseline, 0.3, ["empty daily log, using baseline"]
            exit_code = 1
        else:
            mood, confidence, signals = analyze_messages(messages)

    result = {
        "mood": mood,
        "confidence": confidence,
        "signals": signals,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(MOOD_OUTPUT, "w") as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
