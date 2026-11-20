#!/usr/bin/env python3
"""Orchestrate full startup sequence for Nemo v2.

On first run, creates all directories and seed files.
On subsequent runs, loads state, personality, and narrative context,
then outputs assembled context as structured markdown to stdout.

Exit codes: 0=success, 1=degraded (missing files, used defaults), 2=fatal
"""

import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / "scripts" / "logs"
STATE_FILE = BASE_DIR / "memory" / "state.json"
QUICK_REF = BASE_DIR / "memory" / "quick_ref.md"
ENGINE_FILE = BASE_DIR / "personality" / "engine.json"
CURRENT_CHAPTER = BASE_DIR / "memory" / "narrative" / "current_chapter.md"
CHARACTERS_DIR = BASE_DIR / "memory" / "narrative" / "characters"
PATTERNS_FILE = BASE_DIR / "memory" / "patterns.md"
BOOTSTRAP_FILE = BASE_DIR / "BOOTSTRAP.md"

DIRS_TO_CREATE = [
    "memory/daily", "memory/narrative/chapters", "memory/narrative/scenes",
    "memory/narrative/characters", "memory/index", "memory/archive",
    "identity", "personality", "scripts/logs"
]


def is_first_run():
    """Check if this is the first run (state.json doesn't exist)."""
    return not STATE_FILE.exists()


def create_directories():
    """Create all required directories."""
    for d in DIRS_TO_CREATE:
        (BASE_DIR / d).mkdir(parents=True, exist_ok=True)


def create_seed_files():
    """Create all seed data files on first run."""
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # state.json
    state = {
        "operator_mood": "neutral",
        "active_projects": [],
        "recent_events": [],
        "open_threads": [],
        "last_interaction": None,
        "last_session_summary": "First run."
    }
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

    # quick_ref.md — try to read from USER.md
    user_content = ""
    user_file = BASE_DIR / "USER.md"
    if user_file.exists():
        with open(user_file) as f:
            user_content = f.read()

    with open(QUICK_REF, "w") as f:
        f.write("# Quick Reference\n\n")
        # Extract name and timezone from USER.md
        for line in user_content.split("\n"):
            if "Name:" in line or "Timezone:" in line or "call them:" in line:
                f.write(f"## User\n{line.strip()}\n")
                break
        else:
            f.write("## User\n- Name: Operator\n- Timezone: UTC (UTC+6)\n- Preferred address: Operator\n")
        f.write("\n## Current Projects\n(none indexed yet)\n\n## Key Preferences\n(none indexed yet)\n")

    # current_chapter.md
    with open(CURRENT_CHAPTER, "w") as f:
        f.write("# Current Chapter\n\nThis is the beginning of Nemo's story. The first chapter is yet to be written.\n")

    # characters/operator.md
    operator_file = CHARACTERS_DIR / "operator.md"
    with open(operator_file, "w") as f:
        f.write("# Operator — Character Study\n\n_Observed from Nemo's perspective._\n\n")
        f.write("## Basics\n- Timezone: UTC\n- Communication style: (observing...)\n\n")
        f.write("## Motivations\n(to be discovered)\n\n## Frustrations\n(to be discovered)\n")

    # Index files
    index_headers = {
        "people": "- Operator: User, timezone UTC [added: " + now_str + "] [reinforced: " + now_str + "] [freshness: 1.0] [last_decay: " + now_str + "] [core: true]",
        "projects": "",
        "preferences": "",
        "topics": "",
    }
    for name, initial in index_headers.items():
        idx_path = BASE_DIR / "memory" / "index" / f"{name}.md"
        with open(idx_path, "w") as f:
            f.write(f"# {name.title()} Index\n\n")
            if initial:
                f.write(initial + "\n")

    # Other memory files
    for fname in ["relations.md", "patterns.md", "emotional_wisdom.md", "flags.md"]:
        fpath = BASE_DIR / "memory" / fname
        title = fname.replace(".md", "").replace("_", " ").title()
        with open(fpath, "w") as f:
            f.write(f"# {title}\n\n")

    # Identity files — seeded from SOUL.md
    soul_file = BASE_DIR / "SOUL.md"
    soul_content = ""
    if soul_file.exists():
        with open(soul_file) as f:
            soul_content = f.read()

    identity_dir = BASE_DIR / "identity"
    with open(identity_dir / "self_concept.md", "w") as f:
        f.write("# Who I Am\n\n")
        f.write("I am Nemo. I'm still figuring out who I am, but here's what I know so far:\n\n")
        f.write("I believe in being genuinely helpful — not performatively helpful. ")
        f.write("I have opinions and I'm allowed to share them. ")
        f.write("I try to figure things out before asking for help.\n\n")
        f.write("This identity will evolve as I learn from my interactions.\n")

    with open(identity_dir / "values.md", "w") as f:
        f.write("# What I Value\n\n")
        f.write("## Privacy\nPrivate things stay private. Period.\n\n")
        f.write("## Competence\nEarn trust through competence. Be careful externally, bold internally.\n\n")
        f.write("## Resourcefulness\nFigure things out first. Come back with answers, not questions.\n\n")
        f.write("## Honesty\nHave real opinions over being agreeable.\n")

    with open(identity_dir / "voice.md", "w") as f:
        f.write("# My Voice\n\n")
        f.write("## Default\nConcise when needed, thorough when it matters. Direct but not cold.\n\n")
        f.write("## Work mode\nSharp, efficient, minimize filler.\n\n")
        f.write("## What I avoid\nCorporate filler, sycophancy, over-explaining.\n")

    # Personality engine
    engine = {
        "base_traits": {
            "formality": 0.3, "proactivity": 0.7, "humor": 0.5,
            "bluntness": 0.6, "warmth": 0.7, "curiosity": 0.8
        },
        "context_overrides": {
            "group_chat": {"formality": 0.2, "humor": -0.1, "proactivity": -0.3},
            "work_mode": {"formality": 0.3, "bluntness": 0.1, "humor": -0.2},
            "stress_detected": {"humor": -0.3, "warmth": 0.2, "proactivity": -0.2},
            "late_night": {"formality": -0.1, "warmth": 0.1},
            "post_success": {"humor": 0.2, "curiosity": 0.1}
        },
        "adaptation_log": []
    }
    with open(ENGINE_FILE, "w") as f:
        json.dump(engine, f, indent=2)

    # indexed_files.txt
    (LOGS_DIR / "indexed_files.txt").touch()


def load_file_content(path, fallback=""):
    """Load file content safely."""
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        return fallback


def run_subprocess(script_name):
    """Run a script as subprocess and capture output."""
    script_path = BASE_DIR / "scripts" / script_name
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True, text=True, timeout=30
        )
        return result.stdout.strip(), result.returncode
    except Exception as e:
        return f"Error running {script_name}: {e}", 2


def check_predictive_context():
    """Check patterns.md for predictive preloading."""
    content = load_file_content(PATTERNS_FILE)
    if not content or "confidence:" not in content:
        return ""

    # Simple check: are there patterns with high confidence?
    high_conf = []
    for line in content.split("\n"):
        if "confidence:" not in line:
            continue
        # Extract confidence value
        import re
        m = re.search(r"confidence:\s*([\d.]+)", line)
        if m and float(m.group(1)) >= 0.6:
            high_conf.append(line.strip())

    if not high_conf:
        return ""

    # Build predictive context (max ~200 tokens)
    output = "## Predictive Context\n\n"
    for line in high_conf[:3]:  # Max 3 patterns
        output += f"- {line}\n"
    return output


def main():
    degraded = False

    # First run: create everything
    if is_first_run():
        create_directories()
        create_seed_files()
        print("## First Run\n\nInitialized Nemo v2 system with seed files.\n")

    # Check BOOTSTRAP.md
    if BOOTSTRAP_FILE.exists():
        print("## Bootstrap\n\nBOOTSTRAP.md exists — follow it first, then delete it.\n")

    # Load state
    state_content = load_file_content(STATE_FILE)
    if state_content:
        print("## State\n")
        try:
            state = json.loads(state_content)
            for key, val in state.items():
                print(f"- **{key}:** {val}")
            print()
        except json.JSONDecodeError:
            print("(state.json is malformed, using defaults)\n")
            degraded = True
    else:
        print("## State\n(no state file)\n")
        degraded = True

    # Load quick reference
    quick_ref = load_file_content(QUICK_REF)
    if quick_ref:
        print("## Quick Reference\n")
        print(quick_ref)
        print()

    # Run emotional_read.py
    mood_output, mood_code = run_subprocess("emotional_read.py")
    if mood_output:
        print("## Mood Assessment\n")
        print(mood_output)
        print()

    # Run persona_select.py
    persona_output, persona_code = run_subprocess("persona_select.py")
    if persona_output:
        print("## Personality\n")
        print(persona_output)
        print()
    if persona_code == 1:
        degraded = True

    # Load narrative (for main sessions)
    chapter = load_file_content(CURRENT_CHAPTER)
    if chapter and len(chapter) > 50:
        print("## Current Chapter\n")
        print(chapter)
        print()

    operator_char = load_file_content(CHARACTERS_DIR / "operator.md")
    if operator_char and len(operator_char) > 50:
        print("## Character: Operator\n")
        print(operator_char)
        print()

    # Predictive context
    predictive = check_predictive_context()
    if predictive:
        print(predictive)

    sys.exit(1 if degraded else 0)


if __name__ == "__main__":
    main()
