#!/usr/bin/env python3
"""Zero-Dependency In-Process SQLite FTS5 Cache for OpenClaw Cortex.

Maintains a non-authoritative SQLite cache (.cache/cortex_index.sqlite3)
synchronized with Markdown index files in memory/index/ and memory/archive/.
Provides sub-millisecond BM25 full-text ranking via SQLite's native FTS5 engine.

Exit codes: 0=success, 1=dirty/re-synced, 2=error
"""

import argparse
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / ".cache"
DB_PATH = CACHE_DIR / "cortex_index.sqlite3"
INDEX_DIR = BASE_DIR / "memory" / "index"
ARCHIVE_DIR = BASE_DIR / "memory" / "archive"


def get_db_connection():
    """Establish connection to SQLite cache database with WAL mode."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH))
    con.execute("PRAGMA journal_mode = WAL")
    con.execute("PRAGMA synchronous = NORMAL")
    con.row_factory = sqlite3.Row
    return con


def init_schema(con):
    """Initialize relational and FTS5 tables with automatic content triggers."""
    con.executescript("""
    CREATE TABLE IF NOT EXISTS file_sync (
        file_path TEXT PRIMARY KEY,
        mtime REAL NOT NULL,
        file_size INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS cortex_facts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        text TEXT NOT NULL,
        freshness REAL NOT NULL,
        stability REAL NOT NULL,
        added TEXT,
        reinforced TEXT,
        last_decay TEXT,
        is_core INTEGER NOT NULL,
        raw_line TEXT NOT NULL,
        source_file TEXT NOT NULL,
        is_archived INTEGER NOT NULL DEFAULT 0
    );

    CREATE VIRTUAL TABLE IF NOT EXISTS cortex_facts_fts USING fts5(
        category,
        text,
        content='cortex_facts',
        content_rowid='id',
        tokenize='porter unicode61'
    );

    -- Keep FTS5 index synchronized with cortex_facts table
    CREATE TRIGGER IF NOT EXISTS cortex_facts_ai AFTER INSERT ON cortex_facts BEGIN
        INSERT INTO cortex_facts_fts(rowid, category, text)
        VALUES (new.id, new.category, new.text);
    END;

    CREATE TRIGGER IF NOT EXISTS cortex_facts_ad AFTER DELETE ON cortex_facts BEGIN
        INSERT INTO cortex_facts_fts(cortex_facts_fts, rowid, category, text)
        VALUES ('delete', old.id, old.category, old.text);
    END;

    CREATE TRIGGER IF NOT EXISTS cortex_facts_au AFTER UPDATE ON cortex_facts BEGIN
        INSERT INTO cortex_facts_fts(cortex_facts_fts, rowid, category, text)
        VALUES ('delete', old.id, old.category, old.text);
        INSERT INTO cortex_facts_fts(rowid, category, text)
        VALUES (new.id, new.category, new.text);
    END;
    """)
    con.commit()


def get_tracked_files():
    """Return dictionary of {relative_path: (mtime, size)} for all markdown stores."""
    files = {}
    if INDEX_DIR.exists():
        for p in INDEX_DIR.glob("*.md"):
            try:
                stat = p.stat()
                rel = str(p.relative_to(BASE_DIR))
                files[rel] = (stat.st_mtime, stat.st_size)
            except OSError:
                pass
    if ARCHIVE_DIR.exists():
        for p in ARCHIVE_DIR.glob("*.md"):
            try:
                stat = p.stat()
                rel = str(p.relative_to(BASE_DIR))
                files[rel] = (stat.st_mtime, stat.st_size)
            except OSError:
                pass
    return files


def is_cache_dirty(con):
    """Check if any tracked markdown file was modified or removed."""
    tracked = get_tracked_files()
    cursor = con.execute("SELECT file_path, mtime, file_size FROM file_sync")
    synced = {row["file_path"]: (row["mtime"], row["file_size"]) for row in cursor.fetchall()}

    if set(tracked.keys()) != set(synced.keys()):
        return True

    for path, (mtime, size) in tracked.items():
        synced_mtime, synced_size = synced[path]
        if abs(mtime - synced_mtime) > 1e-4 or size != synced_size:
            return True

    return False


def parse_fact_line(raw_line):
    """Extract structured attributes from a raw markdown fact line."""
    stripped = raw_line.strip()
    if not stripped.startswith("- "):
        return None

    freshness_m = re.search(r"\[freshness:\s*([\d.]+)\]", stripped)
    stability_m = re.search(r"\[stability:\s*([\d.]+)\]", stripped)
    last_decay_m = re.search(r"\[last_decay:\s*(\d{4}-\d{2}-\d{2})\]", stripped)
    reinforced_m = re.search(r"\[reinforced:\s*(\d{4}-\d{2}-\d{2})\]", stripped)
    added_m = re.search(r"\[added:\s*(\d{4}-\d{2}-\d{2})\]", stripped)
    core_m = re.search(r"\[core:\s*(true|false)\]", stripped)

    # Cut off text before the first metadata bracket '[added:'
    idx = stripped.find("[added:")
    if idx != -1:
        clean_text = stripped[2:idx].strip()
    else:
        # Fallback: strip any bracketed tag at end
        clean_text = re.sub(r"\[.*?\]", "", stripped[2:]).strip()

    freshness = float(freshness_m.group(1)) if freshness_m else 1.0
    stability = float(stability_m.group(1)) if stability_m else 7.0
    added = added_m.group(1) if added_m else None
    reinforced = reinforced_m.group(1) if reinforced_m else added
    last_decay = last_decay_m.group(1) if last_decay_m else None
    is_core = 1 if (core_m and core_m.group(1) == "true") else 0

    return {
        "text": clean_text,
        "freshness": freshness,
        "stability": stability,
        "added": added,
        "reinforced": reinforced,
        "last_decay": last_decay,
        "is_core": is_core,
        "raw_line": stripped
    }


def sync_cache(force=False):
    """Synchronize SQLite FTS5 cache from human-editable Markdown source of truth."""
    con = get_db_connection()
    init_schema(con)

    if not force and not is_cache_dirty(con):
        con.close()
        return False

    tracked = get_tracked_files()

    with con:
        # Clear out facts for all tracked files and resync cleanly
        con.execute("DELETE FROM cortex_facts")
        con.execute("DELETE FROM file_sync")

        for rel_path, (mtime, size) in tracked.items():
            abs_path = BASE_DIR / rel_path
            is_archived = 1 if "archive" in rel_path else 0
            category = abs_path.stem  # e.g., 'people', 'projects'

            try:
                with open(abs_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            except OSError:
                continue

            for line in lines:
                parsed = parse_fact_line(line)
                if not parsed:
                    continue

                con.execute("""
                INSERT INTO cortex_facts (
                    category, text, freshness, stability, added, reinforced,
                    last_decay, is_core, raw_line, source_file, is_archived
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    category, parsed["text"], parsed["freshness"], parsed["stability"],
                    parsed["added"], parsed["reinforced"], parsed["last_decay"],
                    parsed["is_core"], parsed["raw_line"], rel_path, is_archived
                ))

            con.execute("""
            INSERT INTO file_sync (file_path, mtime, file_size) VALUES (?, ?, ?)
            """, (rel_path, mtime, size))

    con.close()
    return True


def sanitize_fts_query(query_str):
    """Sanitize user query for safe SQLite FTS5 prefix/phrase matching."""
    if not query_str:
        return ""
    # Remove characters that cause FTS5 parse errors
    clean = re.sub(r'["\'*^:()\[\]{}]', ' ', query_str).strip()
    tokens = clean.split()
    if not tokens:
        return ""
    # Build prefix query: term1* term2*
    return " ".join(f'"{t}"*' for t in tokens)


def query_facts(query_str=None, category=None, recent_days=None, include_archived=False, limit=50):
    """Query facts using in-process SQLite FTS5 BM25 ranking.
    
    Returns list of dicts:
    [{'category': str, 'text': str, 'freshness': float, 'rank': float}]
    """
    con = get_db_connection()
    init_schema(con)

    # Auto-sync if dirty
    if is_cache_dirty(con):
        sync_cache(force=True)
        con = get_db_connection()

    cutoff_date = None
    if recent_days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=recent_days)
        cutoff_date = cutoff.strftime("%Y-%m-%d")

    params = []
    where_clauses = []

    if not include_archived:
        where_clauses.append("f.is_archived = 0")

    if category:
        where_clauses.append("f.category = ?")
        params.append(category)

    if cutoff_date:
        where_clauses.append("(f.added IS NOT NULL AND f.added >= ?)")
        params.append(cutoff_date)

    fts_query = sanitize_fts_query(query_str) if query_str else None

    if fts_query:
        where_clauses.append("cortex_facts_fts MATCH ?")
        params.append(fts_query)
        where_sql = " AND ".join(where_clauses)
        sql = f"""
        SELECT f.category, f.raw_line, f.freshness, bm25(cortex_facts_fts) as rank
        FROM cortex_facts_fts
        JOIN cortex_facts f ON f.id = cortex_facts_fts.rowid
        WHERE {where_sql}
        ORDER BY rank ASC, f.freshness DESC
        LIMIT {limit}
        """
    else:
        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        sql = f"""
        SELECT f.category, f.raw_line, f.freshness, 0.0 as rank
        FROM cortex_facts f
        {where_sql}
        ORDER BY f.freshness DESC
        LIMIT {limit}
        """

    cursor = con.execute(sql, params)
    rows = cursor.fetchall()
    results = [
        {"category": r["category"], "text": r["raw_line"], "freshness": r["freshness"], "rank": r["rank"]}
        for r in rows
    ]
    con.close()
    return results


def main():
    parser = argparse.ArgumentParser(description="Manage Cortex SQLite FTS5 Cache")
    parser.add_argument("--sync", action="store_true", help="Force sync cache from markdown files")
    parser.add_argument("--status", action="store_true", help="Check cache status and row counts")
    parser.add_argument("--search", help="Execute test FTS5 search query")
    args = parser.parse_args()

    con = get_db_connection()
    init_schema(con)

    if args.sync:
        synced = sync_cache(force=True)
        print("Cache synchronized." if synced else "Cache already up to date.")
        sys.exit(0)

    if args.status:
        dirty = is_cache_dirty(con)
        count = con.execute("SELECT count(*) as c FROM cortex_facts").fetchone()["c"]
        files = con.execute("SELECT count(*) as c FROM file_sync").fetchone()["c"]
        print(f"Cortex Cache Status:")
        print(f"  Database Path: {DB_PATH}")
        print(f"  Dirty: {dirty}")
        print(f"  Tracked Files: {files}")
        print(f"  Indexed Facts: {count}")
        sys.exit(0)

    if args.search:
        results = query_facts(query_str=args.search, include_archived=True)
        print(f"Found {len(results)} results for '{args.search}':")
        for r in results:
            print(f"  [{r['category']}] (BM25 rank: {r['rank']:.3f}, freshness: {r['freshness']:.2f}) {r['text']}")
        sys.exit(0)

    con.close()


if __name__ == "__main__":
    main()
