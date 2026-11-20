#!/usr/bin/env python3
"""OpenClaw Native Tool Runner for Cortex Memory Substrate.

Provides programmatic and CLI execution for OpenClaw tools:
- cortex_recall(query, type, depth, include_archived)
- cortex_relate(subject, predicate, object)
- cortex_flag(fact_a, fact_b, reason)

Exit codes: 0=success, 1=no results / soft failure, 2=invalid args / error
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import cortex_cache
import memory_recall

INDEX_DIR = BASE_DIR / "memory" / "index"
RELATIONS_FILE = BASE_DIR / "memory" / "relations.md"
FLAGS_FILE = BASE_DIR / "memory" / "flags.md"


def cortex_recall(query, fact_type=None, depth=2, include_archived=False):
    """Execute hybrid BM25 full-text recall and multi-hop graph traversal."""
    depth = max(1, min(5, depth))
    facts = memory_recall.search_index_files(
        query=query,
        fact_type=fact_type,
        include_archived=include_archived
    )
    relations = memory_recall.search_relations(
        query=query,
        depth=depth,
        include_archived=include_archived
    ) if query else []

    return {
        "status": "success",
        "query": query,
        "type": fact_type,
        "depth": depth,
        "include_archived": include_archived,
        "fact_count": len(facts),
        "relation_count": len(relations),
        "facts": facts,
        "relations": relations
    }


def cortex_relate(subject, predicate, obj):
    """Insert a typed directed relationship into relations.md."""
    if not subject or not predicate or not obj:
        raise ValueError("Subject, predicate, and object are required.")

    subject = subject.strip()
    predicate = re.sub(r"[^a-zA-Z0-9_\-]", "_", predicate.strip().lower())
    obj = obj.strip()
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    entry_line = f"- {subject} --[{predicate}]--> {obj} [added: {today_str}] [strength: 1.0]"

    RELATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not RELATIONS_FILE.exists():
        with open(RELATIONS_FILE, "w", encoding="utf-8") as f:
            f.write("# Relations\n\n<!-- Typed links. Format: - Subject --[type]--> Object [added: YYYY-MM-DD] [strength: 1.0] -->\n\n")

    with open(RELATIONS_FILE, "a", encoding="utf-8") as f:
        f.write(entry_line + "\n")

    return {
        "status": "success",
        "subject": subject,
        "predicate": predicate,
        "object": obj,
        "entry": entry_line
    }


def cortex_flag(fact_a, fact_b, reason):
    """Log an epistemic contradiction flag into memory/flags.md."""
    if not fact_a or not fact_b or not reason:
        raise ValueError("fact_a, fact_b, and reason are required.")

    fact_a = fact_a.strip()
    fact_b = fact_b.strip()
    reason = reason.strip()
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    flag_entry = f'- [{today_str}] Fact A: "{fact_a}" vs Fact B: "{fact_b}" → Reason: {reason}'

    FLAGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not FLAGS_FILE.exists():
        with open(FLAGS_FILE, "w", encoding="utf-8") as f:
            f.write("# Contradiction Flags\n\n")

    # Read existing lines, cap at 20 flags
    with open(FLAGS_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    header_lines = [l for l in lines if not l.strip().startswith("- [")]
    flag_lines = [l.strip() for l in lines if l.strip().startswith("- [")]
    flag_lines.append(flag_entry)
    if len(flag_lines) > 20:
        flag_lines = flag_lines[-20:]

    with open(FLAGS_FILE, "w", encoding="utf-8") as f:
        for h in header_lines:
            f.write(h)
        if header_lines and not header_lines[-1].endswith("\n"):
            f.write("\n")
        for fl in flag_lines:
            f.write(fl + "\n")

    return {
        "status": "success",
        "timestamp": today_str,
        "flag": flag_entry
    }


def main():
    parser = argparse.ArgumentParser(description="OpenClaw Cortex Tool Dispatcher")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: recall
    p_recall = subparsers.add_parser("recall", help="Query facts and multi-hop relations")
    p_recall.add_argument("--query", "-q", default="", help="Query string")
    p_recall.add_argument("--type", "-t", choices=["people", "projects", "preferences", "topics"], help="Filter category")
    p_recall.add_argument("--depth", "-d", type=int, default=2, help="Multi-hop depth (1-5)")
    p_recall.add_argument("--include-archived", action="store_true", help="Include cold archives")
    p_recall.add_argument("--json", action="store_true", help="Output raw JSON")

    # Subcommand: relate
    p_relate = subparsers.add_parser("relate", help="Add directed relationship edge")
    p_relate.add_argument("--subject", "-s", required=True, help="Subject entity")
    p_relate.add_argument("--predicate", "-p", required=True, help="Predicate relation type")
    p_relate.add_argument("--object", "-o", required=True, help="Object entity")
    p_relate.add_argument("--json", action="store_true", help="Output raw JSON")

    # Subcommand: flag
    p_flag = subparsers.add_parser("flag", help="Record contradiction flag")
    p_flag.add_argument("--fact-a", required=True, help="First assertion")
    p_flag.add_argument("--fact-b", required=True, help="Second conflicting assertion")
    p_flag.add_argument("--reason", required=True, help="Contradiction justification")
    p_flag.add_argument("--json", action="store_true", help="Output raw JSON")

    args = parser.parse_args()

    try:
        if args.command == "recall":
            res = cortex_recall(
                query=args.query,
                fact_type=args.type,
                depth=args.depth,
                include_archived=args.include_archived
            )
            if args.json:
                print(json.dumps(res, indent=2))
            else:
                formatted = memory_recall.format_results(res["facts"], res["relations"])
                print(formatted)
            sys.exit(0 if (res["fact_count"] > 0 or res["relation_count"] > 0) else 1)

        elif args.command == "relate":
            res = cortex_relate(args.subject, args.predicate, args.object)
            if args.json:
                print(json.dumps(res, indent=2))
            else:
                print(f"Recorded relation: {res['entry']}")
            sys.exit(0)

        elif args.command == "flag":
            res = cortex_flag(args.fact_a, args.fact_b, args.reason)
            if args.json:
                print(json.dumps(res, indent=2))
            else:
                print(f"Recorded contradiction flag: {res['flag']}")
            sys.exit(0)

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
