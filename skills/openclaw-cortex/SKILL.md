---
name: openclaw-cortex
description: Native cognitive memory tools for OpenClaw agents: recall facts, link relational graphs, and flag epistemic contradictions.
version: 1.3.0
author: OpenClaw Cortex Contributors
tags: [memory, knowledge-graph, cortex, recall, reasoning]
---

# OpenClaw Cortex Skill

Autonomous agents require durable memory, structured relationship awareness, and contradiction detection. Cortex exposes three native tools that can be invoked at runtime during conversation.

## Available Agent Tools

### 1. `cortex_recall(query, type, depth, include_archived)`
Use whenever you need to recall past decisions, architectural patterns, user preferences, or system relationships:
- Recursively traverses connected entities up to `depth` hops (default: 2, range: 1–5).
- Matches keyword tokens via in-process SQLite FTS5 BM25 scoring.
- If investigating past historical shifts, set `include_archived: true`.

**Tool Invocation**:
```json
{
  "tool": "cortex_recall",
  "parameters": {
    "query": "Telemetry Service",
    "depth": 2
  }
}
```

### 2. `cortex_relate(subject, predicate, object)`
Use whenever a concrete relationship or dependency between two entities is established or changed:
- Valid predicates: `uses`, `depends_on`, `works_on`, `hosted_on`, `manages`, `prefers`, `dislikes`.
- Automatically appends a typed edge to `memory/relations.md`.

**Tool Invocation**:
```json
{
  "tool": "cortex_relate",
  "parameters": {
    "subject": "Telemetry Service",
    "predicate": "uses",
    "object": "TimescaleDB"
  }
}
```

### 3. `cortex_flag(fact_a, fact_b, reason)`
Use whenever you detect that a new user instruction contradicts an existing rule or recorded preference:
- Logs the dispute into `memory/flags.md` with timestamp.
- Allows you to alert the user or request clarification without silent hallucination.

**Tool Invocation**:
```json
{
  "tool": "cortex_flag",
  "parameters": {
    "fact_a": "Operator prefers PostgreSQL for all services",
    "fact_b": "Operator requests deploying ClickHouse for analytics",
    "reason": "Direct conflict on standard database preference"
  }
}
```

## Protocol Guidelines
- Call `cortex_recall` **before** making architectural assumptions or asking the operator questions they already answered.
- Call `cortex_relate` **after** confirming deployments, dependencies, or project assignments.
- Never silently discard contradicting information—always log with `cortex_flag`.
