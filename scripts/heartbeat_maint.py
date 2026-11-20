#!/usr/bin/env python3
"""Master maintenance script run during heartbeats.

Orchestrates: memory indexing, narrative conversion, emotional reading,
state updates, decay calculations, archival, flag resolution, and
weekly reflection.

Exit codes: 0=success, 1=partial (some tasks failed), 2=fatal
"""

import json
import math
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"
LOGS_DIR = SCRIPTS_DIR / "logs"
STATE_FILE = BASE_DIR / "memory" / "state.json"
INDEX_DIR = BASE_DIR / "memory" / "index"
ARCHIVE_DIR = BASE_DIR / "memory" / "archive"
FLAGS_FILE = BASE_DIR / "memory" / "flags.md"
PATTERNS_FILE = BASE_DIR / "memory" / "patterns.md"
RELATIONS_FILE = BASE_DIR / "memory" / "relations.md"
ARCHIVED_RELATIONS_FILE = ARCHIVE_DIR / "relations.md"

STALE_THRESHOLD = 0.3
CORE_FLOOR = 0.5
ARCHIVE_DAYS = 90


def log_msg(msg):
    """Log a maintenance message."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with open(LOGS_DIR / f"{date_str}.log", "a") as f:
        f.write(f"[MAINT] {msg}\n")


def run_script(name):
    """Run a script as subprocess. Returns (output, exit_code)."""
    script_path = SCRIPTS_DIR / name
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True, text=True, timeout=60
        )
        return result.stdout.strip(), result.returncode
    except Exception as e:
        log_msg(f"Error running {name}: {e}")
        return str(e), 2


def get_active_entities():
    """Extract all active entity identifiers from index files and user configuration."""
    active = set()

    # 1. Primary user / operator
    user_file = BASE_DIR / "USER.md"
    if user_file.exists():
        try:
            with open(user_file, "r") as f:
                for line in f:
                    if line.strip().lower().startswith("- **name:**"):
                        val = line.split(":", 1)[1].strip().strip("*").strip()
                        if val:
                            active.add(val.lower())
        except Exception:
            pass
    active.add("operator")
    active.add("user")

    # 2. Scan all active index files
    if INDEX_DIR.exists():
        for idx_file in INDEX_DIR.glob("*.md"):
            try:
                with open(idx_file, "r") as f:
                    for line in f:
                        stripped = line.strip()
                        if not stripped.startswith("- "):
                            continue
                        content = stripped[2:].strip()
                        # Extract before colon if present (e.g., "- Name: description")
                        if ":" in content:
                            ent = content.split(":", 1)[0].strip()
                            if ent:
                                active.add(ent.lower())
                        # Also extract leading token/subject
                        tokens = content.split()
                        if tokens:
                            active.add(tokens[0].lower())
            except Exception:
                pass

    return active


def prune_dangling_relations(archived_facts=None):
    """Prune dangling relation edges from relations.md and archive them to preserve provenance.

    A relation 'Subject --[rel]--> Object' is considered dangling if:
    1. Subject or Object decayed into the archive during this or prior cycles.
    2. Subject or Object no longer exists among active entities in index files.
    """
    if not RELATIONS_FILE.exists():
        return 0

    try:
        with open(RELATIONS_FILE, "r") as f:
            lines = f.readlines()
    except Exception as e:
        log_msg(f"Error reading relations file: {e}")
        return 0

    decayed_entities = set()
    if archived_facts:
        for fact_line in archived_facts:
            stripped = fact_line.strip()
            if stripped.startswith("- "):
                content = stripped[2:].strip()
                if ":" in content:
                    decayed_entities.add(content.split(":", 1)[0].strip().lower())
                tokens = content.split()
                if tokens:
                    decayed_entities.add(tokens[0].lower())

    active_entities = get_active_entities()
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    kept_lines = []
    pruned_relations = []
    rel_pattern = re.compile(r"^-\s+(.+?)\s+--\[(.+?)\]-->\s+(.+?)(?:\s+(\[.*\]))?$")

    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("- "):
            kept_lines.append(line)
            continue

        match = rel_pattern.match(stripped)
        if not match:
            kept_lines.append(line)
            continue

        subj = match.group(1).strip()
        rel_type = match.group(2).strip()
        obj_full = match.group(3).strip()
        meta = match.group(4) or ""

        subj_lower = subj.lower()
        obj_lower = obj_full.lower()

        is_decayed = (subj_lower in decayed_entities) or (obj_lower in decayed_entities)
        is_orphan = (subj_lower not in active_entities) or (obj_lower not in active_entities)

        if is_decayed or is_orphan:
            reason = "entity_decay" if is_decayed else "orphan_node"
            meta_str = meta.strip()
            archived_entry = f"- {subj} --[{rel_type}]--> {obj_full}"
            if meta_str:
                archived_entry += f" {meta_str}"
            archived_entry += f" [archived: {today_str}] [reason: {reason}]"
            pruned_relations.append(archived_entry)
        else:
            kept_lines.append(line)

    if pruned_relations:
        with open(RELATIONS_FILE, "w") as f:
            f.writelines(kept_lines)

        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        archived_rel_file = ARCHIVE_DIR / "relations.md"
        first_write = not archived_rel_file.exists() or archived_rel_file.stat().st_size == 0
        with open(archived_rel_file, "a") as f:
            if first_write:
                f.write("# Archived Relations\n\n<!-- Relations pruned due to entity decay or orphan node references. -->\n\n")
            for entry in pruned_relations:
                f.write(entry + "\n")

    return len(pruned_relations)


def run_decay_calculations():
    """Apply freshness decay to all facts in index files."""
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    decayed_count = 0
    archived_count = 0
    all_archived_facts = []

    for idx_file in INDEX_DIR.glob("*.md"):
        try:
            with open(idx_file, "r") as f:
                lines = f.readlines()
        except FileNotFoundError:
            continue

        new_lines = []
        facts_to_archive = []

        for line in lines:
            stripped = line.strip()

            # Only process fact lines
            if not stripped.startswith("- "):
                new_lines.append(line)
                continue

            # Parse metadata
            freshness_m = re.search(r"\[freshness:\s*([\d.]+)\]", stripped)
            last_decay_m = re.search(r"\[last_decay:\s*(\d{4}-\d{2}-\d{2})\]", stripped)
            reinforced_m = re.search(r"\[reinforced:\s*(\d{4}-\d{2}-\d{2})\]", stripped)
            core_m = re.search(r"\[core:\s*(true|false)\]", stripped)
            stability_m = re.search(r"\[stability:\s*([\d.]+)\]", stripped)

            if not freshness_m or not last_decay_m:
                new_lines.append(line)
                continue

            freshness = float(freshness_m.group(1))
            last_decay = last_decay_m.group(1)
            is_core = core_m and core_m.group(1) == "true"
            stability = float(stability_m.group(1)) if stability_m else (90.0 if is_core else 7.0)

            # Check if decay needs calculation (>24 hours since last)
            last_decay_date = datetime.strptime(last_decay, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if (now - last_decay_date).days < 1:
                new_lines.append(line)
                continue

            # Calculate Ebbinghaus spaced-repetition exponential decay: R = e^(-t / S)
            reinforced = reinforced_m.group(1) if reinforced_m else last_decay
            reinforced_date = datetime.strptime(reinforced, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            t_days = max(0.0, float((now - reinforced_date).days))
            new_freshness = math.exp(-t_days / stability)

            # Core floor (asymptotic immunity for critical core facts)
            if is_core:
                new_freshness = max(CORE_FLOOR, new_freshness)

            # Update line
            new_line = re.sub(r"\[freshness:\s*[\d.]+\]", f"[freshness: {new_freshness:.2f}]", stripped)
            if stability_m:
                new_line = re.sub(r"\[stability:\s*[\d.]+\]", f"[stability: {stability:.1f}]", new_line)
            else:
                new_line = re.sub(r"(\[freshness:\s*[\d.]+\])", rf"\1 [stability: {stability:.1f}]", new_line)
            new_line = re.sub(r"\[last_decay:\s*\d{4}-\d{2}-\d{2}\]", f"[last_decay: {today_str}]", new_line)

            # Mark stale
            if new_freshness < STALE_THRESHOLD and not is_core:
                if "stale" not in new_line:
                    new_line += " stale"
                facts_to_archive.append(new_line)
                all_archived_facts.append(new_line)
                archived_count += 1
                decayed_count += 1
                continue  # Don't include in new_lines

            new_lines.append(new_line + "\n")
            decayed_count += 1

        # Write back
        with open(idx_file, "w") as f:
            f.writelines(new_lines)

        # Archive stale facts
        if facts_to_archive:
            ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
            archive_file = ARCHIVE_DIR / f"{today_str}.md"
            with open(archive_file, "a") as f:
                for fact in facts_to_archive:
                    f.write(fact + "\n")

    # Prune dangling relation edges from relations.md
    pruned_relations_count = prune_dangling_relations(all_archived_facts)

    return decayed_count, archived_count, pruned_relations_count


def clean_old_archives():
    """Delete archive files older than 90 days."""
    if not ARCHIVE_DIR.exists():
        return 0
    cutoff = (datetime.now(timezone.utc) - timedelta(days=ARCHIVE_DAYS))
    deleted = 0
    for f in ARCHIVE_DIR.glob("*.md"):
        try:
            date_str = f.stem  # YYYY-MM-DD
            fdate = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if fdate < cutoff:
                f.unlink()
                deleted += 1
        except ValueError:
            pass
    return deleted


def auto_resolve_flags():
    """Auto-resolve flags older than 14 days."""
    if not FLAGS_FILE.exists():
        return 0

    with open(FLAGS_FILE, "r") as f:
        lines = f.readlines()

    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=14)).strftime("%Y-%m-%d")

    header = []
    flag_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- ["):
            flag_lines.append(line)
        else:
            header.append(line)

    resolved = 0
    kept = []
    for line in flag_lines:
        m = re.match(r"- \[(\d{4}-\d{2}-\d{2})\]", line.strip())
        if m and m.group(1) < cutoff:
            resolved += 1
        else:
            kept.append(line)

    # Cap at 20
    if len(kept) > 20:
        kept = kept[-20:]

    with open(FLAGS_FILE, "w") as f:
        for h in header:
            f.write(h)
        f.write("\n")
        for k in kept:
            f.write(k)

    return resolved


def update_state():
    """Update state.json with current information."""
    if not STATE_FILE.exists():
        return

    try:
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
    except json.JSONDecodeError:
        return

    # Update timestamp
    state["last_interaction"] = datetime.now(timezone.utc).isoformat()

    # Cap open_threads — remove threads older than 7 days
    state["open_threads"] = state.get("open_threads", [])[:5]
    state["recent_events"] = state.get("recent_events", [])[:5]

    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def is_weekly():
    """Check if it's been at least 7 days since last reflection."""
    prompts_file = LOGS_DIR / "reflection_prompts.md"
    if not prompts_file.exists():
        return True
    # Check file modification time
    mtime = datetime.fromtimestamp(prompts_file.stat().st_mtime, tz=timezone.utc)
    return (datetime.now(timezone.utc) - mtime).days >= 7


def main():
    actions = []
    max_exit_code = 0

    # 1. Run memory indexing
    output, code = run_script("memory_index.py")
    actions.append(f"memory_index: {output}")
    max_exit_code = max(max_exit_code, code)

    # 2. Run narrative conversion
    output, code = run_script("narrate.py")
    actions.append(f"narrate: {output}")
    max_exit_code = max(max_exit_code, code)

    # 3. Run emotional reading
    output, code = run_script("emotional_read.py")
    actions.append(f"emotional_read: {output}")
    max_exit_code = max(max_exit_code, code)

    # 4. Run decay calculations & graph pruning
    decayed, archived, pruned = run_decay_calculations()
    actions.append(f"decay: {decayed} facts decayed, {archived} archived, {pruned} dangling relations pruned")

    # 5. Clean old archives
    deleted = clean_old_archives()
    if deleted > 0:
        actions.append(f"archive_cleanup: {deleted} old archives deleted")

    # 6. Auto-resolve old flags
    resolved = auto_resolve_flags()
    if resolved > 0:
        actions.append(f"flags: {resolved} auto-resolved")

    # 7. Synchronize SQLite FTS5 cache
    try:
        from cortex_cache import sync_cache
        synced = sync_cache(force=True)
        actions.append(f"fts_cache: {'synchronized' if synced else 'up_to_date'}")
    except Exception as e:
        actions.append(f"fts_cache: failed ({e})")

    # 8. Update state
    update_state()
    actions.append("state: updated")

    # 9. Weekly: run reflection
    if is_weekly():
        output, code = run_script("reflect.py")
        actions.append(f"reflect: {output}")
        max_exit_code = max(max_exit_code, code)

    # Output summary
    print(f"Heartbeat maintenance complete. {len(actions)} actions performed:")
    for action in actions:
        print(f"  - {action}")

    log_msg(f"Heartbeat complete: {'; '.join(actions)}")

    sys.exit(max_exit_code)


if __name__ == "__main__":
    main()
