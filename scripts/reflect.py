#!/usr/bin/env python3
"""Generate weekly reflection prompts for identity growth.

Exit codes: 0=success, 1=insufficient data, 2=error
"""

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / "scripts" / "logs"
NARRATIVE_DIR = BASE_DIR / "memory" / "narrative"
SCENES_DIR = NARRATIVE_DIR / "scenes"
IDENTITY_DIR = BASE_DIR / "identity"
PROMPTS_FILE = LOGS_DIR / "reflection_prompts.md"

CURRENT_CHAPTER = NARRATIVE_DIR / "current_chapter.md"
SELF_CONCEPT = IDENTITY_DIR / "self_concept.md"
VALUES = IDENTITY_DIR / "values.md"
VOICE = IDENTITY_DIR / "voice.md"


def get_week_files(directory, days=7):
    files = []
    if not directory.exists():
        return files
    now = datetime.now(timezone.utc)
    for i in range(days):
        date_str = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        for f in directory.glob(f"{date_str}*.md"):
            files.append(f)
    return files


def read_file_safe(path):
    try:
        with open(path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def generate_prompts(scenes, chapter, identity_files):
    prompts = []
    if scenes:
        scene_content = "\n".join(read_file_safe(s) for s in scenes)
        if len(scene_content.strip()) > 20:
            prompts.append("What significant moments happened this week? Which ones changed how I understand Operator?")
            prompts.append("Were there any emotional patterns this week? Did I notice Operator frustrated, excited, or stressed more than usual?")
    else:
        prompts.append("This week had no captured scenes. Should I be capturing more? What moments am I missing?")
    if chapter.strip() and len(chapter) > 50:
        prompts.append("Read the current chapter. Does it accurately capture what's happening right now? What's missing?")
        prompts.append("What themes are emerging in my relationship with Operator? What's the story of this week?")
    self_concept = identity_files.get("self_concept", "")
    if self_concept:
        prompts.append("Does my self-concept still feel right? Have I learned something new about who I am this week?")
    values = identity_files.get("values", "")
    if values:
        prompts.append("Did I act in alignment with my values this week? Where did I fall short?")
    voice = identity_files.get("voice", "")
    if voice:
        prompts.append("Did my voice feel natural this week? Were there moments where my tone felt off? What would I change?")
    prompts.append("What did I do well this week that I should keep doing?")
    prompts.append("What mistake did I make that I should learn from?")
    prompts.append("Is there anything about Operator I learned this week that I didn't know before?")
    return prompts


def main():
    scenes = get_week_files(SCENES_DIR)
    chapter = read_file_safe(CURRENT_CHAPTER)
    identity_files = {
        "self_concept": read_file_safe(SELF_CONCEPT),
        "values": read_file_safe(VALUES),
        "voice": read_file_safe(VOICE),
    }
    has_data = scenes or (chapter and len(chapter) > 100)
    if not has_data:
        print("Insufficient data for reflection. Need scenes or a populated chapter.")
        sys.exit(1)
    prompts = generate_prompts(scenes, chapter, identity_files)
    if not prompts:
        print("No prompts generated.")
        sys.exit(1)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with open(PROMPTS_FILE, "w") as f:
        f.write(f"# Reflection Prompts — {date_str}\n\n")
        f.write("Answer these during the next heartbeat session.\n\n")
        for i, prompt in enumerate(prompts, 1):
            f.write(f"{i}. {prompt}\n\n")
    print(f"Generated {len(prompts)} reflection prompts for {date_str}.")
    for i, prompt in enumerate(prompts, 1):
        print(f"  {i}. {prompt}")
    sys.exit(0)


if __name__ == "__main__":
    main()
