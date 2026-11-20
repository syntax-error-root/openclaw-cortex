<div align="center">

```
   ____                      ____ _                  ____           _            
  / __ \____  ___  ____     / __ \ | __ _____      __/ __ \____  ____| |_ _____  __
 / / / / __ \/ _ \/ __ \   / / / / |/ // __ `/ | /| / / / / __ \/ ___/ __/ _ \ \/ /
/ /_/ / /_/ /  __/ / / /  / /_/ /|  < / /_/ /| |/ |/ / /_/ / /__/ /  / /_/  __/>  < 
\____/ .___/\___/_/ /_/   \____/ |__/\__,_/ |__/|__/\____/\___/_/   \__/\___/_/\_\ 
    /_/                                                                          
```

### *A Tripartite Cognitive Substrate & Adaptive Personality Engine for Autonomous Agents*

[![License: MIT](https://img.shields.io/badge/License-MIT-6E44FF.svg?style=for-the-badge&logo=opensourceinitiative&logoColor=white)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-Compatible-00C9A7.svg?style=for-the-badge&logo=target&logoColor=white)](https://openclaw.ai)
[![Architecture](https://img.shields.io/badge/Architecture-Neural--Symbolic-FF6B6B.svg?style=for-the-badge)](https://github.com/syntax-error-root/openclaw-cortex)

<br/>

> *"To remember is not merely to store tokens; it is to weave past occurrences into an ongoing identity."*

<br/>

[Philosophy](#-the-philosophy) •
[Cognitive Anatomy](#-cognitive-anatomy) •
[Hybrid Retrieval](#-hybrid-neural-symbolic-retrieval) •
[Personality Dynamics](#-the-affective-engine) •
[Quickstart](#-ignition-protocol) •
[Ecosystem](#-ecosystem-tapestry)

---

</div>

<br/>

## 🌌 The Philosophy

Monolithic agent memory designs fail in predictable ways:
- **Flat text dumps** cause catastrophic context window saturation.
- **Pure vector databases** hallucinate associations and lack causal, relational reasoning.
- **Static system prompts** produce sterile, sycophantic assistants devoid of genuine persona growth.

**OpenClaw Cortex** resolves this tension by treating memory as a **dynamic multi-layer ecosystem**: short-term working state, an evolving prose autobiography, and a formal relational knowledge graph — balanced by an automated affective feedback loop that reads operator sentiment and context.

<br/>

---

## 🧠 Cognitive Anatomy

```
                   ┌──────────────────────────────────────────┐
                   │           INCOMING PERCEPTION            │
                   └────────────────────┬─────────────────────┘
                                        │
             ┌──────────────────────────┼──────────────────────────┐
             ▼                          ▼                          ▼
   ┌───────────────────┐      ┌───────────────────┐      ┌───────────────────┐
   │  LAYER 1: STATE   │      │ LAYER 2: NARRATIVE│      │  LAYER 3: INDEX   │
   │  (Working RAM)    │      │ (Episodic Story)  │      │ (Relational Graph)│
   ├───────────────────┤      ├───────────────────┤      ├───────────────────┤
   │ • <200 tokens     │      │ • Prose chapters  │      │ • Typed Entities  │
   │ • Active threads  │      │ • 500-word cap    │      │ • Knowledge Links │
   │ • Affective mood  │      │ • Scene captures  │      │ • Contradictions  │
   │ • Critical flags  │      │ • Character study │      │ • Memory Decay    │
   │                   │      │                   │      │ • Graph Pruning   │
   └─────────┬─────────┘      └─────────┬─────────┘      └─────────┬─────────┘
             │                          │                          │
             └──────────────────────────┼──────────────────────────┘
                                        │
                                        ▼
                   ┌──────────────────────────────────────────┐
                   │       HYBRID RETRIEVAL & FUSION          │
                   │    (Dense Vectors ⨁ Sparse BM25)         │
                   └──────────────────────────────────────────┘
```

<br/>

### Layer Breakdown

| Layer | Substrate | Persistence Lifecycle | Purpose |
| :--- | :--- | :--- | :--- |
| **`Layer 1: State`** | [`memory/state.json`](memory/state.json) | Continuous, instant read/write | Zero-latency context injection containing operational mood, open threads, and active projects. |
| **`Layer 2: Narrative`** | [`memory/narrative/`](memory/narrative/) | Sliding window (500-word limit) | Compresses daily chat logs into a coherent autobiography (`current_chapter.md`). Archives historical epochs into `chapters/` and milestone events into `scenes/`. |
| **`Layer 3: Index`** | [`memory/index/`](memory/index/) | Ebbinghaus decay ($R = e^{-t/S}$) | Categorized knowledge stores (`people.md`, `projects.md`, `preferences.md`, `topics.md`) with explicit link topologies ([`relations.md`](memory/relations.md)). |

<br/>

### ⏳ Spaced-Repetition Decay (Ebbinghaus Forgetting Curve)

Fact retention in Layer 3 is governed by an exponential spaced-repetition model:

$$R = e^{-\frac{t}{S}}$$

- **Dynamic Stability Factor ($S$)**: Starts at $S = 7.0$ days. Each time a fact is reinforced in daily logs, $S$ doubles ($7 \to 14 \to 28 \to \dots$), cementing frequently validated knowledge.
- **Automated Trivia Pruning**: Single-occurrence trivia drops below threshold ($R < 0.30$) and flushes to cold storage in [`memory/archive/`](memory/archive/) within 7–14 days.
- **Asymptotic Core Immunity**: System-critical facts (`[core: true]`) hold an asymptotic floor ($R \ge 0.50$), granting permanent retention.

<br/>

---

## ⚡ Hybrid Neural-Symbolic Retrieval

OpenClaw Cortex couples high-dimensional semantic search with exact symbolic indexing:

```
Query ────────► [ Dense Vector Embeddings ] ─────► Cosine Distance (0.70) ┐
        │                                                                   ├─► MMR Re-ranked Context
        └─────► [ In-Process SQLite FTS5 ]  ─────► BM25 Score     (0.30) ┘
```

### In-Process SQLite FTS5 Cache (`.cache/cortex_index.sqlite3`)

While Markdown remains the human-editable source of truth, Cortex maintains a non-authoritative in-process SQLite cache using Python's standard `sqlite3` engine:
- **Zero-Dependency**: No external database or C-compiler required.
- **Sub-Millisecond BM25**: Drops fact retrieval from $O(N)$ filesystem parsing to microsecond token searches.
- **Auto-Sync / Dirty Detection**: Compares filesystem `mtime` and file sizes on each query to automatically recompile dirty markdown changes.

```bash
# Inspect local FTS5 cache statistics
python3 scripts/cortex_cache.py --status

# Execute direct BM25 search benchmark
python3 scripts/cortex_cache.py --search "telemetry cluster"
```

### OpenClaw Gateway Integration

To activate Cortex native search inside your OpenClaw daemon, configure `openclaw.json`:

```json5
{
  "agents": {
    "defaults": {
      "memorySearch": {
        "enabled": true,
        "provider": "ollama",               // Or "local", "gemini", "openai"
        "model": "mxbai-embed-large",
        "store": {
          "vector": {
            "enabled": true,                // Hardware-accelerated sqlite-vec
            "extensionPath": "bundled"
          }
        },
        "hybrid": {
          "enabled": true,
          "weightVector": 0.7,              // 70% semantic similarity
          "weightKeyword": 0.3              // 30% exact token match
        },
        "extraPaths": [
          "identity"                        // Index identity & core beliefs
        ]
      }
    }
  }
}
```

Force compilation and inspect vector health:
```bash
openclaw memory index --force
openclaw memory status --deep
```

<br/>

---

## 🎭 The Affective Engine

Cortex rejects static agent personas. Behavior is governed by an adaptive multi-axis trait matrix that modulates tone based on situational awareness and operator emotional signals.

```
                  ┌────────────────────────────────────────┐
                  │        BASE TRAIT MATRIX               │
                  │  Formality   • Proactivity • Humor     │
                  │  Bluntness   • Warmth      • Curiosity │
                  └───────────────────┬────────────────────┘
                                      │
                     ┌────────────────┴────────────────┐
                     ▼                                 ▼
         [ Temporal Sensor ]              [ Sentiment Classifier ]
         • Late Night Shift               • Frustration / Crunch
         • Deep Work Window               • Accomplishment Pulse
                     │                                 │
                     └────────────────┬────────────────┘
                                      ▼
                        ┌───────────────────────────┐
                        │ Context-Modulated Persona │
                        └───────────────────────────┘
```

- **Stress & Velocity Detection**: Dynamically detects interaction velocity (<10s query bursts), sentence length contraction (>60% drop), and punctuation/caps acceleration. Reduces humor, boosts succinctness, and prioritizes autonomous problem mitigation.
- **Late-Night Modality**: Drops formality, dampens proactivity to avoid interrupting the operator during off-hours.
- **Contradiction Guard**: Scans incoming statements against [`scripts/antonyms.json`](scripts/antonyms.json) to flag conflicting truths inside [`memory/flags.md`](memory/flags.md).

<br/>

---

## 🧭 File System Geography

```
openclaw-cortex/
├── AGENTS.md                  # Behavioral handbook, security boundaries & red lines
├── SOUL.md                    # Core consciousness axioms & growth tenets
├── USER.md                    # Operator profile template
├── TOOLS.md                   # Environment hardware, TTS & endpoint register
├── HEARTBEAT.md               # Periodic cron protocol specifications
│
├── identity/                  # Metacognitive self-constructs
│   ├── self_concept.md        # Internal perspective & role understanding
│   ├── values.md              # Moral imperatives with experiential origin stories
│   └── voice.md               # Calibrated linguistic style guides
│
├── memory/                    # Tripartite memory vault
│   ├── state.json             # Ephemeral working state (<200 tokens)
│   ├── relations.md           # Typed entity-relationship knowledge graph
│   ├── flags.md               # Contradiction ledger
│   ├── patterns.md            # Heuristically discovered user workflows
│   ├── emotional_wisdom.md    # Longitudinal interaction insights
│   ├── narrative/             # Prose autobiography & character models
│   ├── index/                 # Structured entities (people, projects, preferences)
│   └── archive/               # Decayed, historical memories
│
└── scripts/                   # Zero-dependency Python 3 automation
    ├── session_bootstrap.py   # Cold-start environment & context loader
    ├── heartbeat_maint.py     # Background indexer, decay auditor & narrate cycler
    ├── cortex_cache.py        # In-process SQLite FTS5 BM25 cache & synchronizer
    ├── memory_index.py        # Entity & relationship heuristic extractor
    ├── memory_recall.py       # Deterministic knowledge graph traverser
    ├── emotional_read.py      # Operator sentiment & cadence classifier
    └── persona_select.py      # Context-aware behavioral weight synthesizer
```

<br/>

---

## 🚀 Ignition Protocol

### 1. Initialize Cognitive State
Execute the bootstrap sequence to generate foundational state structures and load session memory:

```bash
python3 scripts/session_bootstrap.py
```

### 2. Trigger Autonomous Heartbeat
Run the heartbeat worker to parse daily logs, recalculate decay factors, and resolve contradictions:

```bash
python3 scripts/heartbeat_maint.py
```

### 3. Multi-Hop Relational Graph Query
Query the knowledge graph with recursive multi-hop depth traversal ($N=1$ to $5$):

```bash
# Standard 2-hop traversal
python3 scripts/memory_recall.py --about "Telemetry Service" --depth 2

# Extended 3-hop traversal including archived provenance edges
python3 scripts/memory_recall.py --about "Telemetry Service" --depth 3 --include-archived
```

<br/>

---

## 🌐 Ecosystem Tapestry

OpenClaw Cortex is built with deep reverence for the modern open-source agent stack:

- **[OpenClaw](https://openclaw.ai)** — The markdown-native agent orchestration runtime.
- **[sqlite-vec](https://github.com/asg017/sqlite-vec)** — High-performance vector search engine embedded in SQLite.
- **[Ollama](https://github.com/ollama/ollama)** — Private, zero-telemetry local LLM & embedding generation.
- **[SQLite FTS5](https://www.sqlite.org/fts5.html)** — Tokenized BM25 full-text search engine.

<br/>

---

## 📜 License

Crafted for the open-source agent ecosystem under the **[MIT License](LICENSE)**.

<div align="center">

*“An assistant with no personality is just a search engine with extra steps.”*

</div>
