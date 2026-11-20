#!/usr/bin/env python3
"""Query index files and relations for specific fact retrieval.

Exit codes: 0=results found, 1=no results, 2=invalid args
"""

import argparse
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_DIR = BASE_DIR / "memory" / "index"
RELATIONS_FILE = BASE_DIR / "memory" / "relations.md"
ARCHIVE_DIR = BASE_DIR / "memory" / "archive"


def parse_freshness(line):
    m = re.search(r"\[freshness:\s*([\d.]+)\]", line)
    return float(m.group(1)) if m else 0.5


def parse_date(line, tag="added"):
    m = re.search(rf"\[{tag}:\s*(\d{{4}}-\d{{2}}-\d{{2}})\]", line)
    return m.group(1) if m else "unknown"


def search_index_files(query, fact_type=None, recent_days=None):
    results = []
    if fact_type:
        files = [INDEX_DIR / f"{fact_type}.md"]
    else:
        files = list(INDEX_DIR.glob("*.md"))
    cutoff = None
    if recent_days:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=recent_days)).strftime("%Y-%m-%d")
    for idx_file in files:
        if not idx_file.exists():
            continue
        category = idx_file.stem
        try:
            with open(idx_file, "r") as f:
                for line in f:
                    stripped = line.strip()
                    if not stripped.startswith("- "):
                        continue
                    if query and query.lower() not in stripped.lower():
                        continue
                    if cutoff:
                        added = parse_date(stripped, "added")
                        if added < cutoff:
                            continue
                    freshness = parse_freshness(stripped)
                    results.append({"category": category, "text": stripped, "freshness": freshness})
        except FileNotFoundError:
            pass
    return results


def search_relations(query):
    results = []
    if not RELATIONS_FILE.exists():
        return results
    try:
        with open(RELATIONS_FILE, "r") as f:
            for line in f:
                stripped = line.strip()
                if not stripped.startswith("- "):
                    continue
                if query and query.lower() not in stripped.lower():
                    continue
                results.append(stripped)
    except FileNotFoundError:
        pass
    return results


def search_archived(query, recent_days=None):
    results = []
    if not ARCHIVE_DIR.exists():
        return results
    cutoff = None
    if recent_days:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=recent_days)).strftime("%Y-%m-%d")
    for arch_file in sorted(ARCHIVE_DIR.glob("*.md"), reverse=True):
        try:
            with open(arch_file, "r") as f:
                for line in f:
                    stripped = line.strip()
                    if not stripped.startswith("- "):
                        continue
                    if query and query.lower() not in stripped.lower():
                        continue
                    if cutoff:
                        added = parse_date(stripped, "added")
                        if added < cutoff:
                            continue
                    results.append({"category": "archive", "text": stripped, "freshness": parse_freshness(stripped)})
        except FileNotFoundError:
            pass
    return results


def format_results(results, relations):
    if not results and not relations:
        return "No matching facts found."
    output = []
    if results:
        results.sort(key=lambda x: x["freshness"], reverse=True)
        current_cat = None
        for r in results:
            if r["category"] != current_cat:
                current_cat = r["category"]
                output.append(f"\n## {current_cat.title()}")
            output.append(r["text"])
    if relations:
        output.append("\n## Relations")
        for r in relations:
            output.append(r)
    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(description="Query Nemo's memory index")
    parser.add_argument("--about", help="Entity or topic to search for")
    parser.add_argument("--type", choices=["people", "projects", "preferences", "topics"], help="Restrict search to one index type")
    parser.add_argument("--recent", action="store_true", help="Only facts from recent days")
    parser.add_argument("--days", type=int, default=7, help="Number of recent days (default: 7)")
    parser.add_argument("--include-archived", action="store_true", help="Include archived facts")
    args = parser.parse_args()

    if not args.about and not args.type:
        print("ERROR: Provide --about or --type to search.", file=sys.stderr)
        sys.exit(2)

    query = args.about or ""
    recent_days = args.days if args.recent else None
    results = search_index_files(query, args.type, recent_days)
    relations = search_relations(query) if query else []
    if args.include_archived:
        results.extend(search_archived(query, recent_days))
    output = format_results(results, relations)
    print(output)
    if results or relations:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
