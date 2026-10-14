# Hermes RAG / Vector / Memory Architecture Map

Code-grounded reference for "how does memory / RAG / vector search work in
Hermes Agent". Updated for hermes_agent 0.16.0.

## Two-layer model

Hermes RAG is NOT a single vector pipeline. It's two cooperating layers:

- **Layer A: session lexical retrieval** — SQLite + FTS5 BM25 over all session
  messages. Always on. Implementation: `hermes_state.py` + `tools/session_search_tool.py`.
- **Layer B: memory providers** — pluggable, off by default. The "RAG" most
  people think of. Implementation: 7 plugins under `plugins/memory/`, all
  inheriting from `agent/memory_provider.MemoryProvider`.

In this host's `~/.hermes/config.yaml`:
```yaml
memory:
  provider: ''           # empty → Layer B disabled
  memory_enabled: true
  memory_char_limit: 2200
  user_char_limit: 1375
```
So Layer A is working, Layer B is **not**. Nothing in `pip list` for the
hermes venv contains a vector library (no numpy, no faiss, no chroma, no
sqlite-vec, no rank_bm25, no honcho/mem0/supermemory/retaindb/hindsight/
openviking).

## Layer A — session lexical retrieval (FTS5 BM25)

- **Storage**: `~/.hermes/state.db` (SQLite, WAL mode with DELETE-journal
  fallback for NFS/SMB).
- **Schema**: `messages_fts` + `messages_fts_trigram` virtual tables,
  maintained by triggers `_FTS_TRIGGERS = ('messages_fts_insert',
  'messages_fts_delete', 'messages_fts_update', ..._trigram_*)`.
- **Tool**: `session_search()` with 3 calling shapes (no mode param,
  shape inferred from args):
  - `query=...` → DISCOVERY (FTS5, top-N sessions, snippet + ±5 window +
    bookend_start/bookend_end)
  - `session_id + around_message_id` → SCROLL (window around anchor)
  - no args → BROWSE (recent sessions chronologically)
- **Sibling**: `tools/tool_result_storage.py` — when a tool result
  exceeds the per-tool threshold, full output is written to
  `/tmp/hermes-results/{tool_use_id}.txt` and replaced in context with
  `<persisted-output>...</persisted-output>` containing a preview + path.
  Aggregate per-turn budget is `MAX_TURN_BUDGET_CHARS = 200 000`.
- **Vectors in this layer**: NONE. Pure lexical.

## Layer B — memory providers (7 plugins)

All implement `MemoryProvider` ABC. One is active at a time (single
`memory.provider` string in config, not a list). All expose a small set
of tool schemas (search, profile, conclude/remember) so the agent can
call them like any other tool.

| Plugin | Path | Storage | Embeddings | Cost | Standout |
|--------|------|---------|------------|------|----------|
| **mem0** | `plugins/memory/mem0/` | Mem0 Platform API | Cloud (Mem0) | Paid | Server-side LLM extraction + reranking + dedup |
| **supermemory** | `plugins/memory/supermemory/` | supermemory.ai API | Cloud | Paid | Auto-recall/auto-capture; injects `<supermemory-context>` into system prompt; profile every N turns |
| **retaindb** | `plugins/memory/retaindb/` | retaindb.com API | Cloud | Paid | Dialectic synthesis (LLM-synthesized user understanding, prefetched each turn); agent self-model from `SOUL.md`; rdb:// file store |
| **honcho** | `plugins/memory/honcho/` | Honcho AI server | Cloud | Paid | Two-peer model (user + assistant); local message cache + async writer |
| **hindsight** | `plugins/memory/hindsight/` | Hindsight (cloud OR local) | Either | Mixed | Knowledge graph + entity resolution; `HINDSIGHT_BUDGET=low/mid/high` |
| **openviking** | `plugins/memory/openviking/` | Volcengine (default `http://127.0.0.1:1933`) | Either | Mixed (local free) | viking:// URI filesystem; tiered context L0 (~100t) / L1 (~2kt) / L2 (full); resource ingestion |
| **byterover** | `plugins/memory/byterover/` | (TBD) | (TBD) | (TBD) | Pluggable provider slot |
| **holographic** | `plugins/memory/holographic/` | SQLite (`memory_store.db` default) | HRR phase vectors (LOCAL, no LLM) | **Free** | See below |

### holographic — the local, free, no-SaaS option

Worth its own paragraph because it's the only one that works offline
and without subscriptions.

- **Vector model**: Holographic Reduced Representations (Plate 1995,
  Gayler 2004) using **phase encoding** — each atom is a vector of
  angles in [0, 2π), dim=1024 by default. Atoms generated
  deterministically from `SHA-256(f"{word}:{i}")` — identical across
  machines, no RNG.
- **Algebra**:
  - `bind(a, b) = (a + b) mod 2π` (circular convolution, quasi-orthogonal)
  - `unbind(m, k) = (m - k) mod 2π` (circular correlation)
  - `bundle(*vs) = angle(sum(exp(i*vs))) mod 2π` (superposition)
  - `similarity(a, b) = mean(cos(a - b))` in [-1, 1]
- **Storage schema** (SQLite, `plugins/memory/holographic/store.py`):
  - `facts(fact_id, content, category, tags, trust_score, retrieval_count,
    helpful_count, created_at, updated_at, hrr_vector BLOB)`
  - `entities(entity_id, name, entity_type, aliases, created_at)`
  - `fact_entities(fact_id, entity_id)` many-to-many
  - `facts_fts` FTS5 virtual table for lexical fallback
- **Retrieval pipeline** (`retrieval.py`):
  1. FTS5 candidates ×3 (headroom for rerank)
  2. Jaccard token overlap rerank
  3. HRR similarity (if `hrr_weight > 0` AND `numpy` available)
  4. Trust weighting: `score = relevance * trust_score`
  5. Optional temporal decay: `0.5^(age_days / half_life)`
  6. Sort desc, top N
  - Default weights: `fts_weight=0.4, jaccard_weight=0.3, hrr_weight=0.3`
- **Compositional queries** (algebraic, not keyword):
  - `probe(entity)` — unbind entity from memory bank
  - `reason(entities)` — facts bound to MULTIPLE entities
  - `related(entity)` — structural adjacency
  - `contradict` — find conflicting claims
- **Trust loop**: `fact_feedback(helpful|unhelpful, fact_id)` raises/lowers
  trust_score, which gates retrieval. `min_trust_threshold=0.3` filters noise.
- **HARD DEPENDENCY: numpy**. Without it, `hrr_weight` is auto-zeroed
  (see `retrieval.py:53-58`) and you get FTS5+Jaccard only — no vector
  behavior at all. This is the most common silent regression.
- **Config example** (`~/.hermes/config.yaml`):
  ```yaml
  memory:
    provider: hermes-memory-store
  plugins:
    hermes-memory-store:
      db_path: /root/.hermes/memory_store.db
      auto_extract: true         # uses LLM to extract facts from conversation
      default_trust: 0.5
      min_trust_threshold: 0.3
      temporal_decay_half_life: 30
  ```

## Tool search (progressive tool disclosure) — not exactly RAG, but related

`tools/tool_search.py` replaces the dozens of MCP/plugin tools with
three bridge tools (`tool_search`, `tool_describe`, `tool_call`) when
deferrable tools would consume more than `tools.tool_search.threshold_pct`
(10% by default) of the model's context window. CHARS_PER_TOKEN=***
heuristic. Core tools from `toolsets._HERMES_CORE_TOOLS` are NEVER
deferred. The catalog is rebuilt every assembly (stateless by design
— see OpenClaw cron regression #84141 that motivated this).

Lexical search over tool names/descriptions, not vector.

## What to check on a given host to know "is RAG on?"

1. `~/.hermes/config.yaml` — `memory.provider` and `memory.memory_enabled`.
2. `/usr/local/lib/hermes-agent/venv/bin/pip list` — vector libs?
3. `~/.hermes/memories/MEMORY.md` / `USER.md` — flat-file fact storage
   (Layer A's persistent memory surface, separate from FTS5).
4. `~/.hermes/state.db` — FTS5 schema presence (always there if SQLite works).
5. `~/.hermes/SOUL.md` — agent self-model; consumed by retaindb if active.
6. Any `~/.hermes/<plugin>.json` (mem0.json, supermemory.json, etc.) — per-plugin
   configs.

## When to recommend what to the user

- "Free, offline, no API key" → `holographic` (after `pip install numpy`)
- "Best quality, $$ OK" → `mem0` or `supermemory` (similar DX, different vendor)
- "Self-hosted with knowledge graph" → `hindsight` (local mode) or `openviking`
- "Cross-session user modeling" → `honcho` or `retaindb`
- "Just want lexical search working" → it's already working; teach the user
  to use `session_search()`
