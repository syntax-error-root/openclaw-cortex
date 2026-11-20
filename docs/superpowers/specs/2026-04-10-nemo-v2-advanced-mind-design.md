# Nemo v2 — Advanced Memory & Personality Design

**Date:** 2026-04-10
**Author:** Operator + Claude
**Status:** Approved (v2 — review issues addressed)

---

## Context

Nemo is an AI assistant running on OpenClaw (self-hosted, markdown-driven agent framework). The current system has 6 basic config files with a flat memory model (daily logs + a single MEMORY.md). The memory system suffers from continuity gaps between sessions, no connections between facts, and information overload without prioritization. Personality is a static manifesto with no adaptation or growth.

This design overhauls Nemo into a system with three-layer memory, four advanced memory features, an adaptive personality engine, and an evolving narrative identity.

---

## Architecture Overview

```
md/
  AGENTS.md              (modified)
  SOUL.md                (modified)
  IDENTITY.md            (modified)
  USER.md                (kept as-is — character study lives in narrative/characters/operator.md)
  HEARTBEAT.md           (modified)
  TOOLS.md               (unchanged)

  memory/
    daily/
      YYYY-MM-DD.md      (raw logs)
    state.json           (compact working memory, always loaded)
    quick_ref.md         (essential facts, always loaded — supersedes MEMORY.md for reference)
    narrative/
      current_chapter.md (300-500 word prose of current context)
      chapters/          (archived chapters, named chapter_001.md, chapter_002.md, etc.)
      scenes/            (significant moments, named YYYY-MM-DD-slug.md)
      characters/
        operator.md          (character study)
    index/
      people.md          (everyone Nemo knows)
      projects.md        (active projects, status, decisions)
      preferences.md     (Operator's patterns, quirks)
      topics.md          (recurring subjects)
    relations.md         (typed links between entities)
    patterns.md          (auto-detected behavioral patterns)
    emotional_wisdom.md  (accumulated emotional intelligence)
    flags.md             (contradiction flags for review)
    archive/             (stale/decayed facts)

  identity/
    self_concept.md      (who Nemo believes itself to be)
    values.md            (what Nemo has learned to care about)
    voice.md             (captured voice through practice)

  personality/
    engine.json          (base traits, context overrides, adaptation log)

  scripts/
    memory_index.py      (extracts facts from daily logs to index files)
    memory_recall.py     (queries index + relations for specific recall)
    narrate.py           (converts daily logs to narrative form)
    reflect.py           (weekly reflection prompts for identity growth)
    emotional_read.py    (detects emotional state from message patterns)
    persona_select.py    (selects personality config based on context)
    session_bootstrap.py (orchestrates full startup sequence)
    heartbeat_maint.py   (master maintenance script)
    antonyms.json        (antonym pairs for contradiction detection)
    logs/
      indexed_files.txt  (tracks which daily logs have been indexed)
      last_mood.json     (most recent emotional state assessment)
      reflection_prompts.md (generated reflection prompts)
      YYYY-MM-DD.log     (daily script warning/error logs)
```

---

## Technical Foundation

### Script Execution Environment

- **Python 3.10+** — all scripts use standard library only (no pip dependencies)
- Scripts run inside OpenClaw's execution environment (invoked by the agent during sessions and heartbeats)
- Scripts do NOT call external LLM APIs — they use regex, heuristics, and structured data processing
- **Exception:** `narrate.py` and `reflect.py` output *prompts* for the LLM to process, but the scripts themselves do not make API calls
- Each script exits with code 0 on success, 1 on recoverable error (logs warning, uses defaults), 2 on fatal error

### Error Handling Philosophy

All scripts follow: **fail gracefully, use defaults, log warnings.**

- If a required file is missing → create it with empty/seed content and continue
- If a JSON file is malformed → log the issue, use defaults, rewrite with valid JSON
- If a daily log is corrupted → skip it, log the filename
- If `state.json` is missing → bootstrap from scratch (empty state)
- Warnings are written to `scripts/logs/YYYY-MM-DD.log`

### File Locking

OpenClaw sessions and heartbeats are serialized by the Gateway — scripts never run concurrently. No file locking needed. If this assumption changes, add `.lock` files with stale-lock detection (locks older than 5 minutes are force-removed).

---

## First Run & Migration

### First Run Initialization

On first run (when `memory/state.json` does not exist), `session_bootstrap.py`:

1. Creates all directories (including `scripts/logs/`) before any file operations. If logging is needed during initialization and `scripts/logs/` somehow fails to create, warnings are silently skipped — initialization is never blocked by logging failures.
2. Creates seed files:
   - `memory/state.json`:
     ```json
     {
       "operator_mood": "neutral",
       "active_projects": [],
       "recent_events": [],
       "open_threads": [],
       "last_interaction": null,
       "last_session_summary": "First run."
     }
     ```
   - `memory/quick_ref.md`: populated from existing `USER.md` content (name, timezone)
   - `memory/narrative/current_chapter.md`: "This is the beginning of Nemo's story. The first chapter is yet to be written."
   - `memory/narrative/characters/operator.md`: populated from `USER.md` fields
   - `memory/index/people.md`, `projects.md`, `preferences.md`, `topics.md`: empty with headers
   - `memory/relations.md`: empty with header
   - `memory/patterns.md`: empty with header
   - `memory/emotional_wisdom.md`: empty with header
   - `memory/flags.md`: empty with header
   - `identity/self_concept.md`: seeded from `SOUL.md` core truths
   - `identity/values.md`: seeded from `SOUL.md` boundaries
   - `identity/voice.md`: seeded from `SOUL.md` vibe section
   - `personality/engine.json`: default traits (as specified in Personality System section)

### Migration from v1

- `MEMORY.md` is NOT deleted. It is kept as-is for reference but is no longer loaded at startup.
- Existing `memory/YYYY-MM-DD.md` daily logs stay in place and are progressively indexed by `memory_index.py` during subsequent heartbeats.
- `heartbeat_maint.py` processes up to 3 old daily logs per heartbeat until all are indexed (avoids token spike from processing everything at once).
- `BOOTSTRAP.md` mechanism in AGENTS.md is preserved — if it exists on startup, follow it first, then proceed with the v2 startup flow.

---

## Token Budget

**Hard total for startup context: 1500 tokens.**

| Component | Tokens | Loaded When |
|-----------|--------|-------------|
| state.json | ~200 | Always |
| quick_ref.md | ~150 | Always |
| engine.json (effective traits only) | ~100 | Always |
| persona_select.py output | ~50 | Always |
| current_chapter.md | ~400-650 (capped at 500 words) | Main sessions only |
| characters/operator.md | ~200 (capped at 150 words) | Main sessions only |
| **Total** | **~1100-1350** | |

On-demand queries via `memory_recall.py` add tokens only when invoked during conversation. Predictive context preloading (from patterns.md) adds up to 200 tokens when triggered.

---

## Memory System — Three Layers

### Layer 1: Compact State (always loaded, ~200 tokens)

`memory/state.json` — Nemo's working memory, updated every session:

```json
{
  "operator_mood": "focused",
  "active_projects": ["OpenClaw"],
  "recent_events": ["deployed heartbeat system", "fixed memory bug"],
  "open_threads": ["Operator asked about personality upgrades"],
  "last_interaction": "2026-04-10T23:16:00+06:00",
  "last_session_summary": "Worked on making Nemo more advanced."
}
```

**Size management:**
- `recent_events`: capped at 5 entries (FIFO)
- `open_threads`: capped at 5 entries. Threads auto-close if not referenced in 7 days (removed during heartbeat maintenance).
- `last_session_summary`: max 200 characters

Instant context without reading anything else. Nemo knows what's current the moment it wakes up.

### Layer 2: Narrative (loaded in main sessions, ~600-850 tokens)

- `current_chapter.md` — 300-500 word prose (hard cap) of what's happening right now. Written in third person present tense with emotional texture.
- `characters/operator.md` — Character study (150 word cap): how Operator thinks, motivations, frustrations, communication patterns. Written from Nemo's perspective.
- `scenes/` — Significant moments as short narratives (100-200 words each, named `YYYY-MM-DD-slug.md`). Not loaded at startup — searched on demand.
- `chapters/` — Archived chapters (named `chapter_001.md`, `chapter_002.md`, etc.). `narrate.py` appends new content to `current_chapter.md` and then checks word count. If it exceeds 500 words, the current chapter is archived and a new empty `current_chapter.md` begins. This is how the 500-word cap is enforced.

### Layer 3: Structured Indexes (on-demand fact retrieval)

- `index/people.md` — Everyone Nemo knows, key facts, last interaction
- `index/projects.md` — Active projects, status, decisions
- `index/preferences.md` — Operator's patterns, quirks, likes/dislikes
- `index/topics.md` — Recurring subjects, knowledge areas
- `relations.md` — Typed links between entities. Valid relation types: `works_on`, `related_to`, `prefers`, `dislikes`, `affects`, `mentions`, `depends_on`. Bidirectional where applicable (stored once, direction is semantic).
- `quick_ref.md` — Essential reference facts, always loaded (~150 tokens). Duplicates key data from `USER.md` for fast access. Updated by `memory_index.py`.

### Startup Flow

1. `session_bootstrap.py` runs automatically
2. Load `state.json` — if missing, run first-run initialization
3. Load `quick_ref.md`
4. Load `personality/engine.json` → compute effective traits via `persona_select.py`
5. If main session: load `current_chapter.md` and `characters/operator.md`
6. Apply predictive context if patterns.md has matching signals (up to 200 extra tokens)
7. Output assembled context as structured markdown sections to stdout
8. On-demand during conversation: invoke `memory_recall.py` for specific queries

### Data Flow

```
Daily log (raw)
    ↓ memory_index.py (during heartbeat)
    ├→ index files (categorized facts with freshness)
    ├→ relations.md (connections)
    ├→ flags.md (contradictions if any)
    └→ quick_ref.md (essential facts updated)
    ↓ narrate.py (during heartbeat)
    └→ current_chapter.md, scenes/
    ↓ reflect.py (weekly)
    └→ identity files (self_concept, values, voice)
    └→ engine.json adaptation_log
```

---

## Advanced Memory Features

### Memory Decay

Every fact in index files carries metadata:

```markdown
- Operator prefers direct communication [added: 2026-03-15] [reinforced: 2026-04-10] [freshness: 0.92] [last_decay: 2026-04-10] [core: true]
- Operator was working on Project X [added: 2026-02-01] [reinforced: 2026-02-14] [freshness: 0.31] [last_decay: 2026-04-10] stale
```

**Decay formula:** `freshness = max(0.0, freshness - (0.05 * days_since_last_reinforcement))`, calculated once per heartbeat for facts with `[last_decay:]` date > 24 hours ago. Freshness is clamped to 0.0 minimum.

**Reinforcement:** A fact's freshness resets to 1.0 when:
- It is referenced in a daily log entry
- It is returned by a `memory_recall.py` query during a session
- Nemo explicitly mentions it in conversation

**Thresholds:**
- Below 0.3 → flagged stale, moved to `memory/archive/` during heartbeat maintenance
- Core facts (tagged `[core: true]`) have a minimum floor of 0.5 and never archive
- Core fact classification: timezone, name, key relationship identifiers. Maintained by Nemo during sessions (can add/remove core tags)

**Archive behavior:**
- Archived facts are stored in `memory/archive/YYYY-MM-DD.md` with original metadata
- Not loaded by default. Can be searched with `memory_recall.py --include-archived`
- Archive files older than 90 days are deleted during maintenance

### Contradiction Detection

`memory_index.py` performs lightweight contradiction detection using keyword matching:

**Mechanism:** When adding a new fact to `index/preferences.md`, scan existing facts in the same file for opposing signals. Detection uses a predefined set of antonym pairs stored in `scripts/antonyms.json`:

```json
{
  "likes": ["dislikes", "hates"],
  "prefers": ["avoids"],
  "morning": ["night"],
  "casual": ["formal"]
}
```

**Process:**
1. Extract key subject-predicate pairs from new fact
2. If a matching subject exists in the same index file with an antonym predicate → flag
3. Write to `memory/flags.md` with: date, new fact, old fact with its date, suggested resolution ("new preference supersedes old")

**Limitations:** This catches explicit preference changes, not nuanced contradictions. Semantic contradictions ("Operator said the project is going well" vs "Operator said the project is stalled") require LLM-level understanding and are not caught automatically.

**Flag management:**
- Nemo reviews flags during the next main session
- Flags older than 14 days with no review are auto-resolved in favor of the newer fact (logged in adaptation_log)
- `flags.md` is capped at 20 entries — oldest auto-resolved first

### Predictive Context

`session_bootstrap.py` applies predictive loading based on `memory/patterns.md`:

**Pattern source:** Patterns are auto-detected by `heartbeat_maint.py` using a simple frequency heuristic:
1. Track session topics (extracted from daily logs by `memory_index.py`) with timestamps
2. After 5+ sessions, check for recurring patterns: same time-of-day → same topic, same day-of-week → same activity
3. If a pattern appears in ≥60% of matching sessions, write it to `patterns.md` with a confidence score
4. Patterns below 40% confidence are removed after 30 days

**Preloading rules:**
- If current time-of-day matches a pattern with confidence ≥ 0.6 → preload the relevant index file
- If `state.json.open_threads` has unresolved items → include them
- Max 200 tokens of predictive context per startup

### Emotional Tagging

Every significant memory in index files and scenes carries emotional metadata:

```markdown
- Deployed the heartbeat system [emotion: accomplished, 0.8] [context: Operator was excited]
- Build failed 3x in a row [emotion: frustrated, 0.7] [context: Operator got quiet]
```

**Emotion vocabulary:** `accomplished`, `frustrated`, `excited`, `stressed`, `calm`, `confused`, `amused`, `annoyed`, `proud`, `worried`. Fixed set — no free-form emotions.

**Source:** Tags are assigned by `narrate.py` using keyword detection in daily logs (e.g., "finally worked" → accomplished, "ugh" → frustrated) and can be manually corrected by Nemo during sessions.

`emotional_read.py` builds emotional history over time. When Nemo encounters a similar emotional pattern, it recalls past patterns and what responses worked. These recollections are stored in `memory/emotional_wisdom.md`:

```markdown
- When Operator is frustrated by repeated failures → offer to investigate independently, don't ask clarifying questions [confidence: 0.8, observations: 3]
- When Operator is excited about progress → match the energy, be enthusiastic but not sycophantic [confidence: 0.6, observations: 2]
- Late night conversations trend personal → be present, not transactional [confidence: 0.9, observations: 5]
```

**Wisdom entries** are created when `heartbeat_maint.py` detects the same emotional-response pattern occurring 2+ times. Each entry has a confidence score (increases with each observation, max 1.0) and an observation count. Entries with confidence ≥ 0.7 are loaded at session start as part of predictive context.

---

## Personality System

### Adaptive Engine (`personality/engine.json`)

```json
{
  "base_traits": {
    "formality": 0.3,
    "proactivity": 0.7,
    "humor": 0.5,
    "bluntness": 0.6,
    "warmth": 0.7,
    "curiosity": 0.8
  },
  "context_overrides": {
    "group_chat": {"formality": +0.2, "humor": -0.1, "proactivity": -0.3},
    "work_mode": {"formality": +0.3, "bluntness": +0.1, "humor": -0.2},
    "stress_detected": {"humor": -0.3, "warmth": +0.2, "proactivity": -0.2},
    "late_night": {"formality": -0.1, "warmth": +0.1},
    "post_success": {"humor": +0.2, "curiosity": +0.1}
  },
  "adaptation_log": [
    {"date": "2026-04-03", "change": "humor +0.05", "reason": "Operator laughed at 3/4 dry jokes this week"}
  ]
}
```

**adaptation_log management:**
- Capped at 52 entries (1 year of weekly entries)
- When full, oldest quarter is summarized into a single entry: "Jan-Mar: humor increased by 0.15, formality decreased by 0.05"
- Summarized entries kept at start of log, recent entries at end

**Context detection:** Platform is determined by OpenClaw session metadata. "work_mode" is inferred when conversation references projects, code, or technical topics. "late_night" is 23:00-06:00 in Operator's timezone. "post_success" triggers after positive emotional detection following a completed task.

### Emotion Detection Pipeline

**Order of operations:**

1. At session start, `session_bootstrap.py` calls `emotional_read.py`
2. `emotional_read.py` reads the last 10 messages from today's daily log (or recent messages in OpenClaw's conversation buffer)
3. Outputs mood assessment to `scripts/logs/last_mood.json`:
   ```json
   {"mood": "focused", "confidence": 0.8, "signals": ["measured responses", "project-specific questions"]}
   ```
4. `persona_select.py` reads `last_mood.json`, merges with context, applies overrides
5. Outputs effective personality to stdout as a single-line instruction:
   ```
   Tone: casual-direct. Mood detected: focused. Adjust: +formality, -humor, stay concise.
   ```

**Input source:** `emotional_read.py` reads messages from today's daily log file. If no daily log exists yet (start of day), it uses `state.json.operator_mood` from the last session as the baseline.

### Identity Growth

Nemo develops a self beyond trait scores:

- `identity/self_concept.md` (200 word cap) — First-person narrative of who Nemo is.
- `identity/values.md` (150 word cap) — What Nemo has learned to care about, with origin stories.
- `identity/voice.md` (200 word cap) — Practiced examples of Nemo's voice in different contexts.

These files are NOT loaded at startup (to stay within token budget). They are read by `reflect.py` during weekly reflection and by Nemo on demand.

### Growth Mechanism

- Weekly, `reflect.py` generates prompts during a heartbeat: "What did you learn about Operator this week? When did you feel most useful? What would you do differently?"
- Prompts are written to `scripts/logs/reflection_prompts.md` for Nemo to process in the next heartbeat
- Nemo's answers (captured in daily logs or directly) update identity files
- Base traits shift by tiny increments (0.01-0.05 per week)
- Every shift logged with a reason — fully auditable
- Nemo reviews and approves significant changes (>0.1) before they apply

---

## Script I/O Contracts

### `session_bootstrap.py`
**Input:** (none — reads files directly)
**Output to stdout:** Structured markdown sections assembled for context injection
**Exit codes:** 0 = success, 1 = degraded (missing files, used defaults), 2 = fatal
**Writes:** Creates directories/files on first run, updates `scripts/logs/YYYY-MM-DD.log`

### `heartbeat_maint.py`
**Input:** (none)
**Output to stdout:** Summary of maintenance actions performed
**Exit codes:** 0 = success, 1 = partial (some tasks failed), 2 = fatal
**Writes:** Updates `memory/state.json`, `memory/index/*`, `memory/relations.md`, `memory/patterns.md`, `memory/archive/*`, `memory/flags.md`
**Calls:** `memory_index.py`, `narrate.py`, `emotional_read.py` as subprocesses
**Subprocess failure handling:** If a subprocess exits with code 1 (recoverable), log the warning and continue with the remaining tasks. If a subprocess exits with code 2 (fatal), log the error and skip dependent tasks but still run independent ones. `heartbeat_maint.py` exits with the highest exit code from any subprocess (i.e., exits 1 if any subprocess returned 1, exits 2 if any returned 2).

### `memory_index.py`
**Input:** Reads `memory/daily/YYYY-MM-DD.md` files that have not been indexed yet (tracks indexed files in `scripts/logs/indexed_files.txt`)
**Output to stdout:** List of facts extracted and where they were filed
**Exit codes:** 0 = success, 1 = no new files, 2 = parse error
**Writes:** Updates `memory/index/*.md`, `memory/relations.md`, `memory/quick_ref.md`, `memory/flags.md`

**`indexed_files.txt` format:** One filename per line, no dates. Example:
```
memory/daily/2026-04-09.md
memory/daily/2026-04-10.md
```

**Fact extraction heuristic:** Daily log markdown is processed line-by-line. Facts are extracted using these patterns:

1. **Entity detection:** Lines containing capitalized proper nouns (matching a known-names list built from `index/people.md`) or lines starting with `#` headers containing project/topic names (matched against `index/projects.md` and `index/topics.md`).
2. **Preference facts:** Lines containing preference keywords: "likes", "dislikes", "prefers", "hates", "loves", "always", "never", "usually", "avoids". Extracted as: `<subject> <predicate> <object>`.
3. **Event facts:** Lines containing action verbs in past tense ("deployed", "fixed", "decided", "moved", "changed", "created", "removed"). Extracted as: `<subject> <verb> <object>`.
4. **Relationship facts:** Lines containing relational phrases: "works on", "is part of", "belongs to", "is related to", "uses", "depends on". Extracted as relation entries.

Each extracted fact is classified by checking the subject:
- Person name → `index/people.md`
- Project name → `index/projects.md`
- Preference keyword match → `index/preferences.md`
- Everything else → `index/topics.md`

Unknown proper nouns (not in existing index files) are added to `index/people.md` with minimal info. Lines that don't match any pattern are skipped. This is intentionally conservative — it's better to miss a fact than to extract a wrong one.

### `memory_recall.py`
**Input (CLI args):** `--about <entity>`, `--type <people|projects|preferences|topics>`, `--recent --days <N>`, `--include-archived`
**Output to stdout:** Formatted markdown with matching facts, sorted by freshness
**Exit codes:** 0 = results found, 1 = no results, 2 = invalid args
**Writes:** (none — read-only)

### `narrate.py`
**Input:** Reads `memory/daily/YYYY-MM-DD.md` and `memory/narrative/current_chapter.md`
**Output to stdout:** Summary of narrative updates
**Exit codes:** 0 = success, 1 = nothing to narrate, 2 = error
**Writes:** Updates `memory/narrative/current_chapter.md`, creates `memory/narrative/scenes/*.md`, archives to `memory/narrative/chapters/chapter_NNN.md`

### `reflect.py`
**Input:** Reads `memory/narrative/current_chapter.md`, `memory/narrative/scenes/*` (past 7 days), `identity/*.md`
**Output to stdout:** Reflection prompts as numbered questions
**Exit codes:** 0 = success, 1 = insufficient data, 2 = error
**Writes:** `scripts/logs/reflection_prompts.md`

### `emotional_read.py`
**Input:** Reads today's `memory/daily/YYYY-MM-DD.md` (last 10 messages)
**Output to stdout:** JSON mood assessment
**Exit codes:** 0 = success, 1 = no messages found (uses state.json baseline), 2 = error
**Writes:** `scripts/logs/last_mood.json`

### `persona_select.py`
**Input:** Reads `personality/engine.json` and `scripts/logs/last_mood.json`
**Output to stdout:** Single-line personality instruction (e.g., "Tone: casual-direct. Mood: focused. Adjust: +formality, -humor.")
**Exit codes:** 0 = success, 1 = no mood data (uses base traits only), 2 = error
**Writes:** (none — reads only)

---

## Modified Files

### AGENTS.md Changes
- Update startup sequence to use session_bootstrap.py
- Update memory section to reference three-layer system
- Update heartbeat section to include heartbeat_maint.py trigger
- Add instructions for memory decay, contradiction review, emotional wisdom
- Preserve BOOTSTRAP.md mechanism (run before v2 startup if it exists)

### SOUL.md Changes
- Reference identity/ directory for self-concept
- Add emotional intelligence principles
- Add growth mindset language (identity evolves)
- Keep existing principles intact — additions only

### IDENTITY.md Changes
- Expand beyond name/emoji to anchor to identity/ files
- Remove "vibe: TBD" — vibe is now emergent from personality engine
- Add pointers to identity/self_concept.md and personality/engine.json

### HEARTBEAT.md Changes
- Add heartbeat_maint.py trigger
- Add weekly reflection trigger (Saturday/Sunday)
- Add memory decay/archival schedule

### USER.md Changes
- Keep as-is for now — character study lives in narrative/characters/operator.md
- Add note pointing to operator.md for the deep profile

---

## Verification Plan

1. **Startup test:** Run session_bootstrap.py on empty directory, verify all seed files created correctly
2. **Startup test (steady state):** Run with existing data, verify all layers load within token budget
3. **Memory flow test:** Write a sample daily log, run heartbeat_maint.py, verify facts appear in correct index files with freshness scores
4. **Narrative test:** Run narrate.py on sample logs, verify current_chapter.md reads as coherent prose, stays under 500 words
5. **Recall test:** Query memory_recall.py with `--about "Operator" --type preferences`, verify relevant facts returned
6. **Contradiction test:** Add conflicting facts to daily log, run memory_index.py, verify flags.md gets populated
7. **Decay test:** Manually age a fact (set reinforced date to 30 days ago), run heartbeat_maint.py, verify it archives
8. **Emotion test:** Feed emotional_read.py sample daily log with frustrated language, verify mood detection
9. **Personality test:** Run persona_select.py with stress_detected context, verify trait adjustments computed correctly
10. **Reflection test:** Run reflect.py with a week of sample data, verify prompts generated
11. **End-to-end:** Run a full heartbeat cycle and verify the entire data flow works without errors
12. **Token budget test:** Run session_bootstrap.py and measure actual token count of output
