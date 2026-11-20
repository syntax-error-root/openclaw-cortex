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


def load_all_relations(include_archived=False):
    """Load and parse relation edges from active and optional archived partitions."""
    files_to_check = [RELATIONS_FILE]
    if include_archived:
        archived_rel = ARCHIVE_DIR / "relations.md"
        if archived_rel.exists():
            files_to_check.append(archived_rel)

    edges = []
    pattern = re.compile(r"^-\s+(.+?)\s+--\[(.+?)\]-->\s+(.+?)(?:\s+(\[.*\]))?$")
    for rel_path in files_to_check:
        if not rel_path.exists():
            continue
        try:
            with open(rel_path, "r") as f:
                for line in f:
                    stripped = line.strip()
                    if not stripped.startswith("- "):
                        continue
                    m = pattern.match(stripped)
                    if m:
                        edges.append({
                            "subj": m.group(1).strip(),
                            "rel": m.group(2).strip(),
                            "obj": m.group(3).strip(),
                            "line": stripped
                        })
        except FileNotFoundError:
            pass
    return edges


def search_relations(query, depth=2, include_archived=False):
    """Perform recursive multi-hop graph traversal up to depth N."""
    if not query:
        return []

    edges = load_all_relations(include_archived=include_archived)
    if not edges:
        return []

    query_lower = query.strip().lower()
    traversal_results = []
    visited_edges = set()
    visited_nodes = set()

    # Step 1: Identify seed entities matching query
    seed_nodes = set()
    for edge in edges:
        s_lower = edge["subj"].lower()
        o_lower = edge["obj"].lower()
        if query_lower in s_lower:
            seed_nodes.add(edge["subj"])
        if query_lower in o_lower:
            seed_nodes.add(edge["obj"])

    if not seed_nodes:
        # Fallback: substring match on entire line
        for edge in edges:
            if query_lower in edge["line"].lower():
                seed_nodes.add(edge["subj"])
                seed_nodes.add(edge["obj"])

    if not seed_nodes:
        return []

    current_frontier = set(seed_nodes)
    visited_nodes.update(n.lower() for n in seed_nodes)

    for hop in range(1, depth + 1):
        next_frontier = set()
        for edge in edges:
            edge_key = (edge["subj"].lower(), edge["rel"].lower(), edge["obj"].lower())
            if edge_key in visited_edges:
                continue

            s_lower = edge["subj"].lower()
            o_lower = edge["obj"].lower()

            matched_node = None
            neighbor_node = None

            for frontier_node in current_frontier:
                fn_lower = frontier_node.lower()
                if fn_lower == s_lower or fn_lower in s_lower:
                    matched_node = edge["subj"]
                    neighbor_node = edge["obj"]
                    break
                elif fn_lower == o_lower or fn_lower in o_lower:
                    matched_node = edge["obj"]
                    neighbor_node = edge["subj"]
                    break

            if matched_node:
                visited_edges.add(edge_key)
                hop_prefix = f"[Hop {hop}] " if depth > 1 else ""
                traversal_results.append(f"{hop_prefix}{edge['line']}")
                if neighbor_node.lower() not in visited_nodes:
                    visited_nodes.add(neighbor_node.lower())
                    next_frontier.add(neighbor_node)

        current_frontier = next_frontier
        if not current_frontier:
            break

    return traversal_results


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
    parser.add_argument("--depth", type=int, default=2, help="Graph traversal recursion depth (1-5, default: 2)")
    args = parser.parse_args()

    if not args.about and not args.type:
        print("ERROR: Provide --about or --type to search.", file=sys.stderr)
        sys.exit(2)

    query = args.about or ""
    depth = max(1, min(5, args.depth))
    recent_days = args.days if args.recent else None
    results = search_index_files(query, args.type, recent_days)
    relations = search_relations(query, depth=depth, include_archived=args.include_archived) if query else []
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
