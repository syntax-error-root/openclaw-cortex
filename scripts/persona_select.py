#!/usr/bin/env python3
"""Select personality configuration based on current context.

Reads personality/engine.json and scripts/logs/last_mood.json,
applies context overrides based on time, platform, and emotional state,
and outputs a single-line personality instruction.

Exit codes: 0=success, 1=no mood data (base traits only), 2=error
"""

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ENGINE_FILE = BASE_DIR / "personality" / "engine.json"
MOOD_FILE = BASE_DIR / "scripts" / "logs" / "last_mood.json"

TRAIT_NAMES = ["formality", "proactivity", "humor", "bluntness", "warmth", "curiosity"]

# UTC is UTC+6
USER_TZ = timezone(timedelta(hours=6))


def load_engine():
    """Load personality engine configuration."""
    try:
        with open(ENGINE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"ERROR: Cannot load engine.json: {e}", file=sys.stderr)
        return None


def load_mood():
    """Load last mood assessment."""
    try:
        with open(MOOD_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def detect_context(mood_data):
    """Determine active contexts based on time and mood."""
    now = datetime.now(USER_TZ)
    contexts = []

    # Late night: 23:00-06:00
    if now.hour >= 23 or now.hour < 6:
        contexts.append("late_night")

    # Stress detected from mood
    if mood_data and mood_data.get("mood") in ("stressed", "frustrated"):
        contexts.append("stress_detected")

    # Post success
    if mood_data and mood_data.get("mood") in ("accomplished", "excited", "proud"):
        contexts.append("post_success")

    # Work mode: if signals include project/task indicators
    if mood_data and mood_data.get("mood") in ("focused",):
        contexts.append("work_mode")

    return contexts


def compute_effective_traits(engine, contexts):
    """Apply context overrides to base traits."""
    base = engine["base_traits"].copy()
    overrides = engine.get("context_overrides", {})

    for ctx in contexts:
        if ctx in overrides:
            for trait, delta in overrides[ctx].items():
                if trait in base:
                    base[trait] = max(0.0, min(1.0, base[trait] + delta))

    return base


def format_instruction(traits, mood_data, contexts):
    """Format effective personality as a single-line instruction."""
    if traits["formality"] > 0.5:
        tone = "formal"
    elif traits["formality"] < 0.3:
        tone = "casual"
    else:
        tone = "casual-direct"

    mood_label = mood_data.get("mood", "neutral") if mood_data else "neutral"

    adjustments = []
    if traits["humor"] > 0.6:
        adjustments.append("humor welcome")
    elif traits["humor"] < 0.3:
        adjustments.append("skip humor")

    if traits["bluntness"] > 0.7:
        adjustments.append("be direct")
    elif traits["bluntness"] < 0.4:
        adjustments.append("be gentle")

    if traits["proactivity"] > 0.7:
        adjustments.append("act first")
    elif traits["proactivity"] < 0.4:
        adjustments.append("wait for direction")

    if traits["warmth"] > 0.8:
        adjustments.append("show warmth")

    if traits["curiosity"] > 0.7:
        adjustments.append("ask follow-ups")

    adj_str = ", ".join(adjustments) if adjustments else "balanced"

    instruction = f"Tone: {tone}. Mood: {mood_label}. Adjust: {adj_str}."
    return instruction


def main():
    engine = load_engine()
    if engine is None:
        sys.exit(2)

    mood_data = load_mood()
    exit_code = 0 if mood_data else 1

    contexts = detect_context(mood_data)
    traits = compute_effective_traits(engine, contexts)
    instruction = format_instruction(traits, mood_data, contexts)

    print(instruction)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
