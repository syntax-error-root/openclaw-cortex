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
    "short_responses": r"^.{1,15}$",
    "exclamation_increase": r"!{2,}",
    "question_barrage": r"\?.*\?.*\?",
    "caps_emphasis": r"[A-Z]{3,}",
    "ellipsis": r"\.\.\.+$",
}


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


def extract_messages(log_path, count=10):
    """Extract last N non-empty, non-header lines from daily log."""
    try:
        with open(log_path, "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return []

    messages = []
    for line in reversed(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        messages.append(stripped)
        if len(messages) >= count:
            break
    return messages


def analyze_messages(messages):
    """Analyze messages for emotional signals."""
    if not messages:
        return "neutral", 0.0, ["no messages"]

    emotion_scores = {}
    for emotion, keywords in EMOTION_KEYWORDS.items():
        score = 0
        for msg in messages:
            msg_lower = msg.lower()
            for kw in keywords:
                if kw in msg_lower:
                    score += 1
        if score > 0:
            emotion_scores[emotion] = score

    signals = []
    short_count = 0
    for msg in messages:
        if re.match(SIGNAL_PATTERNS["short_responses"], msg):
            short_count += 1
        if re.search(SIGNAL_PATTERNS["exclamation_increase"], msg):
            signals.append("exclamation increase")
        if re.search(SIGNAL_PATTERNS["caps_emphasis"], msg):
            signals.append("caps emphasis")
        if re.search(SIGNAL_PATTERNS["ellipsis"], msg):
            signals.append("trailing ellipsis")

    if short_count > len(messages) * 0.6:
        signals.append("predominantly short responses")

    if emotion_scores:
        top_emotion = max(emotion_scores, key=emotion_scores.get)
        total_hits = sum(emotion_scores.values())
        confidence = min(1.0, total_hits / (len(messages) * 1.5))
        mood = top_emotion
    elif short_count > len(messages) * 0.6:
        mood = "focused"
        confidence = 0.6
        signals.append("brief, task-oriented messages")
    else:
        mood = "neutral"
        confidence = 0.5

    if not signals:
        signals = ["normal cadence"]

    return mood, round(confidence, 2), signals


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
