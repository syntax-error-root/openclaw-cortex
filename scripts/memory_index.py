#!/usr/bin/env python3
"""Extract structured facts from daily logs into index files.

Exit codes: 0=success, 1=no new files, 2=parse error
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / "scripts" / "logs"
INDEXED_FILE = LOGS_DIR / "indexed_files.txt"
DAILY_DIR = BASE_DIR / "memory" / "daily"
INDEX_DIR = BASE_DIR / "memory" / "index"
RELATIONS_FILE = BASE_DIR / "memory" / "relations.md"
FLAGS_FILE = BASE_DIR / "memory" / "flags.md"
ANTONYMS_FILE = BASE_DIR / "scripts" / "antonyms.json"

PREFERENCE_KEYWORDS = ["likes", "dislikes", "prefers", "hates", "loves", "always", "never", "usually", "avoids"]
ACTION_VERBS = ["deployed", "fixed", "decided", "moved", "changed", "created", "removed", "updated", "added", "deleted", "resolved", "implemented", "built", "released", "shipped", "configured", "installed"]
RELATIONAL_PHRASES = ["works on", "is part of", "belongs to", "is related to", "uses", "depends on", "is working on", "is building"]

MAX_LOGS_PER_RUN = 3


def log_warning(msg):
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with open(LOGS_DIR / f"{date_str}.log", "a") as f:
        f.write(f"[WARNING] {msg}\n")


def load_indexed_files():
    try:
        with open(INDEXED_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        return set()


def save_indexed_files(indexed):
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(INDEXED_FILE, "w") as f:
        for path in sorted(indexed):
            f.write(f"{path}\n")


def find_new_logs(indexed):
    if not DAILY_DIR.exists():
        return []
    new_logs = []
    for log_file in sorted(DAILY_DIR.glob("*.md")):
        rel = str(log_file.relative_to(BASE_DIR))
        if rel not in indexed:
            new_logs.append(log_file)
        if len(new_logs) >= MAX_LOGS_PER_RUN:
            break
    return new_logs


def load_known_names():
    names = set()
    for idx_file in INDEX_DIR.glob("*.md"):
        try:
            with open(idx_file, "r") as f:
                for line in f:
                    m = re.match(r"^-\s+([A-Z][a-zA-Z]+)", line)
                    if m:
                        names.add(m.group(1))
        except FileNotFoundError:
            pass
    return names


def load_antonyms():
    try:
        with open(ANTONYMS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def extract_facts(lines, known_names):
    facts = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("<!--"):
            continue
        lower = stripped.lower()

        for kw in PREFERENCE_KEYWORDS:
            if kw in lower:
                subject = None
                for name in known_names:
                    if name.lower() in lower:
                        subject = name
                        break
                if not subject:
                    subject = "Operator"
                facts.append({"type": "preference", "subject": subject, "predicate": kw, "text": stripped, "target_file": "preferences"})
                break
        else:
            for verb in ACTION_VERBS:
                if f" {verb} " in lower or lower.startswith(verb + " "):
                    subject = None
                    for name in known_names:
                        if name.lower() in lower:
                            subject = name
                            break
                    if not subject:
                        subject = "Operator"
                    facts.append({"type": "event", "subject": subject, "predicate": verb, "text": stripped, "target_file": "projects" if subject != "Operator" else "topics"})
                    break
            else:
                for phrase in RELATIONAL_PHRASES:
                    if phrase in lower:
                        subject = None
                        obj = None
                        for name in known_names:
                            if name.lower() in lower:
                                if not subject:
                                    subject = name
                                elif not obj:
                                    obj = name
                        if not subject:
                            subject = "Operator"
                        facts.append({"type": "relation", "subject": subject, "predicate": phrase, "text": stripped, "target_file": None, "object": obj})
                        break
                else:
                    for name in known_names:
                        if name in stripped and name != "Operator":
                            already = any(f["subject"] == name for f in facts if f["type"] != "relation")
                            if not already:
                                facts.append({"type": "mention", "subject": name, "predicate": "mentioned", "text": stripped, "target_file": "people"})
                            break
    return facts


def format_fact_entry(fact, date_str, stability=7.0):
    return f"- {fact['text']} [added: {date_str}] [reinforced: {date_str}] [freshness: 1.00] [stability: {stability:.1f}] [last_decay: {date_str}] [core: false]"


def append_or_reinforce_in_index(target_file, facts, date_str):
    """Append new facts or reinforce existing facts (doubling stability factor S)."""
    idx_path = INDEX_DIR / f"{target_file}.md"
    if not idx_path.exists():
        idx_path.parent.mkdir(parents=True, exist_ok=True)
        with open(idx_path, "w") as f:
            f.write(f"# {target_file.title()} Index\n\n")
        existing_lines = []
    else:
        with open(idx_path, "r") as f:
            existing_lines = f.readlines()

    def extract_fact_core(line):
        stripped = line.strip()
        if not stripped.startswith("- "):
            return ""
        idx = stripped.find("[added:")
        if idx != -1:
            return stripped[2:idx].strip().lower()
        return stripped[2:].strip().lower()

    updated_lines = list(existing_lines)

    for fact in facts:
        fact_text = fact["text"].strip()
        fact_core = fact_text.lower()
        matched = False

        for i, line in enumerate(updated_lines):
            existing_core = extract_fact_core(line)
            if existing_core and (fact_core == existing_core or fact_core in existing_core or existing_core in fact_core):
                # Reinforce existing fact: double stability S, reset freshness to 1.00
                stripped = line.strip()
                s_match = re.search(r"\[stability:\s*([\d.]+)\]", stripped)
                current_s = float(s_match.group(1)) if s_match else 7.0
                new_s = current_s * 2.0  # S doubles on reinforcement

                new_line = re.sub(r"\[reinforced:\s*\d{4}-\d{2}-\d{2}\]", f"[reinforced: {date_str}]", stripped)
                new_line = re.sub(r"\[freshness:\s*[\d.]+\]", "[freshness: 1.00]", new_line)
                new_line = re.sub(r"\[last_decay:\s*\d{4}-\d{2}-\d{2}\]", f"[last_decay: {date_str}]", new_line)
                if s_match:
                    new_line = re.sub(r"\[stability:\s*[\d.]+\]", f"[stability: {new_s:.1f}]", new_line)
                else:
                    new_line = re.sub(r"(\[freshness:\s*[\d.]+\])", rf"\1 [stability: {new_s:.1f}]", new_line)
                new_line = new_line.replace(" stale", "")
                updated_lines[i] = new_line + "\n"
                matched = True
                break

        if not matched:
            new_entry = f"- {fact_text} [added: {date_str}] [reinforced: {date_str}] [freshness: 1.00] [stability: 7.0] [last_decay: {date_str}] [core: false]\n"
            updated_lines.append(new_entry)

    with open(idx_path, "w") as f:
        f.writelines(updated_lines)


def append_to_relations(subject, rel_type, obj, date_str):
    with open(RELATIONS_FILE, "a") as f:
        f.write(f"- {subject} --[{rel_type}]--> {obj} [added: {date_str}] [strength: 1.0]\n")


def check_contradictions(new_facts, antonyms):
    flags = []
    prefs_path = INDEX_DIR / "preferences.md"
    if not prefs_path.exists():
        return flags
    existing_prefs = []
    try:
        with open(prefs_path, "r") as f:
            for line in f:
                if line.strip().startswith("-"):
                    existing_prefs.append(line.strip())
    except FileNotFoundError:
        return flags
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for fact in new_facts:
        if fact["type"] != "preference":
            continue
        predicate = fact["predicate"].lower()
        antonyms_for_pred = antonyms.get(predicate, [])
        for existing in existing_prefs:
            existing_lower = existing.lower()
            for ant in antonyms_for_pred:
                if ant in existing_lower:
                    flags.append(f'- [{today}] New: "{fact["text"]}" vs Old: "{existing}" → Resolution: new preference supersedes')
                    break
    return flags


def append_flags(flags):
    if not flags:
        return
    if not FLAGS_FILE.exists():
        with open(FLAGS_FILE, "w") as f:
            f.write("# Contradiction Flags\n\n")
    with open(FLAGS_FILE, "a") as f:
        for flag in flags:
            f.write(flag + "\n")
    try:
        with open(FLAGS_FILE, "r") as f:
            lines = f.readlines()
        header_lines = [l for l in lines if not l.strip().startswith("- [")]
        flag_lines = [l for l in lines if l.strip().startswith("- [")]
        if len(flag_lines) > 20:
            flag_lines = flag_lines[-20:]
        with open(FLAGS_FILE, "w") as f:
            for l in header_lines:
                f.write(l)
            f.write("\n")
            for l in flag_lines:
                f.write(l)
    except Exception:
        pass


def main():
    indexed = load_indexed_files()
    new_logs = find_new_logs(indexed)
    if not new_logs:
        print("No new daily logs to index.")
        sys.exit(1)
    known_names = load_known_names()
    antonyms = load_antonyms()
    all_facts = []
    for log_file in new_logs:
        try:
            with open(log_file, "r") as f:
                lines = f.readlines()
        except Exception as e:
            log_warning(f"Cannot read {log_file}: {e}")
            continue
        facts = extract_facts(lines, known_names)
        date_str = log_file.stem
        by_target = {}
        for fact in facts:
            target = fact.get("target_file")
            if target:
                by_target.setdefault(target, []).append(fact)
            elif fact["type"] == "relation" and fact.get("object"):
                append_to_relations(fact["subject"], fact["predicate"], fact["object"], date_str)
        for target, target_facts in by_target.items():
            append_or_reinforce_in_index(target, target_facts, date_str)
        all_facts.extend(facts)
        flags = check_contradictions(facts, antonyms)
        append_flags(flags)
        rel = str(log_file.relative_to(BASE_DIR))
        indexed.add(rel)
    save_indexed_files(indexed)
    print(f"Indexed {len(new_logs)} daily logs, extracted {len(all_facts)} facts.")
    for target in ["people", "projects", "preferences", "topics"]:
        idx_path = INDEX_DIR / f"{target}.md"
        if idx_path.exists():
            with open(idx_path) as f:
                count = sum(1 for l in f if l.strip().startswith("- "))
            if count > 0:
                print(f"  {target}: {count} facts")
    sys.exit(0)


if __name__ == "__main__":
    main()
