#!/usr/bin/env python3
"""Convert daily log entries into narrative form.

Exit codes: 0=success, 1=nothing to narrate, 2=error
"""

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DAILY_DIR = BASE_DIR / "memory" / "daily"
NARRATIVE_DIR = BASE_DIR / "memory" / "narrative"
CHAPTERS_DIR = NARRATIVE_DIR / "chapters"
SCENES_DIR = NARRATIVE_DIR / "scenes"
CURRENT_CHAPTER = NARRATIVE_DIR / "current_chapter.md"

EMOTION_KEYWORDS = {
    "accomplished": ["finally", "done", "completed", "deployed", "shipped", "working", "success"],
    "frustrated": ["ugh", "broken", "failed", "stupid", "wtf", "doesn't work"],
    "excited": ["awesome", "excited", "amazing", "love it", "cool"],
    "stressed": ["deadline", "urgent", "rush", "overwhelmed"],
    "amused": ["lol", "haha", "funny"],
}

WORD_CAP = 500


def count_words(text):
    return len(text.split())


def detect_emotion(line):
    lower = line.lower()
    best_emotion = None
    best_score = 0
    for emotion, keywords in EMOTION_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in lower)
        if score > best_score:
            best_score = score
            best_emotion = emotion
    if best_emotion and best_score > 0:
        confidence = min(1.0, best_score / 3.0)
        return best_emotion, round(confidence, 2)
    return None, 0.0


def extract_significant_lines(lines):
    significant = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("<!--"):
            continue
        if len(stripped) < 10:
            continue
        significant.append(stripped)
    return significant


def create_scene(date_str, lines):
    SCENES_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", lines[0][:30].lower()).strip("-")
    scene_file = SCENES_DIR / f"{date_str}-{slug}.md"
    emotion, confidence = detect_emotion(" ".join(lines))
    with open(scene_file, "w") as f:
        f.write(f"# Scene: {date_str}\n\n")
        f.write("\n".join(f"- {l}" for l in lines) + "\n\n")
        if emotion:
            f.write(f"[emotion: {emotion}, {confidence}]\n")
    return scene_file.name


def append_to_chapter(entries, date_str):
    NARRATIVE_DIR.mkdir(parents=True, exist_ok=True)
    new_text = "\n".join(entries)
    emotion, conf = detect_emotion(new_text)
    with open(CURRENT_CHAPTER, "a") as f:
        f.write(f"\n## {date_str}\n\n")
        for entry in entries:
            f.write(f"- {entry}\n")
        if emotion:
            f.write(f"\n[emotion: {emotion}, {conf}] [context: daily summary]\n")
    with open(CURRENT_CHAPTER, "r") as f:
        content = f.read()
    if count_words(content) > WORD_CAP:
        archive_chapter()


def archive_chapter():
    CHAPTERS_DIR.mkdir(parents=True, exist_ok=True)
    existing = list(CHAPTERS_DIR.glob("chapter_*.md"))
    next_num = len(existing) + 1
    archive_path = CHAPTERS_DIR / f"chapter_{next_num:03d}.md"
    if CURRENT_CHAPTER.exists():
        with open(CURRENT_CHAPTER, "r") as f:
            content = f.read()
        with open(archive_path, "w") as f:
            f.write(content)
    with open(CURRENT_CHAPTER, "w") as f:
        f.write("# Current Chapter\n\n")


def get_recent_daily_log():
    if not DAILY_DIR.exists():
        return None, None
    logs = sorted(DAILY_DIR.glob("*.md"), reverse=True)
    if logs:
        return logs[0], logs[0].stem
    return None, None


def main():
    log_file, date_str = get_recent_daily_log()
    if log_file is None:
        print("No daily logs to narrate.")
        sys.exit(1)
    try:
        with open(log_file, "r") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading daily log: {e}", file=sys.stderr)
        sys.exit(2)
    significant = extract_significant_lines(lines)
    if not significant:
        print("Nothing significant to narrate.")
        sys.exit(1)
    emotions_found = [detect_emotion(l) for l in significant]
    has_emotion = any(e[0] is not None for e in emotions_found)
    scene_name = None
    if has_emotion:
        emotional_lines = [l for l, (e, _) in zip(significant, emotions_found) if e is not None]
        if emotional_lines:
            scene_name = create_scene(date_str, emotional_lines[:3])
    append_to_chapter(significant, date_str)
    print(f"Narrated {len(significant)} entries from {date_str}.")
    if scene_name:
        print(f"Created scene: {scene_name}")
    sys.exit(0)


if __name__ == "__main__":
    main()
