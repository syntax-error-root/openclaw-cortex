# OpenClaw Cortex

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-brightgreen.svg)](https://www.python.org/)
[![OpenClaw Ecosystem](https://img.shields.io/badge/ecosystem-OpenClaw-orange.svg)](https://openclaw.ai)


A structured three-tier memory architecture and adaptive behavioral framework for OpenClaw autonomous agents.

## System Overview

OpenClaw Cortex establishes a persistent cognitive substrate for local AI agents, moving beyond monolithic memory files into organized tiers of working state, continuous narrative, and indexed knowledge graphs.

### Three-Layer Memory Hierarchy

1. **Working State (`memory/state.json`)**
   - High-priority, compact operational state (<200 tokens).
   - Injected into every startup context with mood, active tasks, and recent events.

2. **Narrative Layer (`memory/narrative/`)**
   - Episodic memory stored as prose under a 500-word sliding window (`current_chapter.md`).
   - Automatically archives older chapters and captures key interaction scenes.
   - Maintains an evolving profile study in `characters/operator.md`.

3. **Structured Indexes (`memory/index/`)**
   - Categorized domain logs: `people.md`, `projects.md`, `preferences.md`, `topics.md`.
   - Typed entity graph linking items via `memory/relations.md`.
   - Contradiction tracking via `memory/flags.md`.
   - Mathematical decay scoring that moves stale data to `memory/archive/`.

## OpenClaw Hybrid Search Integration

OpenClaw natively supports hybrid search combining SQLite FTS5 (BM25 full-text search) and vector embeddings via `sqlite-vec`. 

To integrate Cortex with OpenClaw runtime search, configure `openclaw.json`:

```json5
{
  "agents": {
    "defaults": {
      "memorySearch": {
        "enabled": true,
        "provider": "ollama",
        "model": "mxbai-embed-large",
        "store": {
          "vector": {
            "enabled": true,
            "extensionPath": "bundled"
          }
        },
        "hybrid": {
          "enabled": true,
          "weightVector": 0.7,
          "weightKeyword": 0.3
        },
        "extraPaths": [
          "identity"
        ]
      }
    }
  }
}
```

Force index compilation from the terminal:
```bash
openclaw memory index --force
openclaw memory status --deep
```

## Directory Structure

```
├── AGENTS.md                  # Session guidelines and runtime red lines
├── SOUL.md                    # Core operational principles
├── USER.md                    # Operator profile template
├── TOOLS.md                   # Environment-specific endpoints and devices
├── HEARTBEAT.md               # Maintenance cadence instructions
├── identity/                  # Long-term agent identity evolution
├── memory/
│   ├── daily/                 # Daily interaction logs
│   ├── index/                 # Structured entities
│   ├── narrative/             # Narrative chapters and character studies
│   ├── archive/               # Decayed records
│   ├── relations.md           # Entity relationship graph
│   └── state.json             # Working memory state
└── scripts/
    ├── session_bootstrap.py   # Cold-start loader and context assembler
    ├── heartbeat_maint.py     # Periodic maintenance worker
    ├── memory_index.py        # Log extractor and relation parser
    ├── memory_recall.py       # Knowledge retrieval utility
    ├── persona_select.py      # Context-driven trait selector
    └── emotional_read.py      # Sentiment analyzer
```

## Quick Start

1. Initialize workspace state:
   ```bash
   python3 scripts/session_bootstrap.py
   ```

2. Run periodic maintenance:
   ```bash
   python3 scripts/heartbeat_maint.py
   ```

3. Query stored knowledge:
   ```bash
   python3 scripts/memory_recall.py --about "project" --type projects
   ```

## Related Open-Source Projects & Ecosystem

OpenClaw Cortex integrates with and builds upon several key open-source technologies:

- **[OpenClaw](https://openclaw.ai)**: The extensible, markdown-first agent execution runtime.
- **[sqlite-vec](https://github.com/asg017/sqlite-vec)**: Extremely fast vector search extension for SQLite, powering local hybrid retrieval without external vector databases.
- **[Ollama](https://github.com/ollama/ollama)**: Local model execution layer for generating private vector embeddings (e.g. `mxbai-embed-large`).
- **[SQLite FTS5](https://www.sqlite.org/fts5.html)**: Native inverted full-text search index providing BM25 keyword matching for hybrid fusion.

## License

This project is licensed under the [MIT License](LICENSE).
