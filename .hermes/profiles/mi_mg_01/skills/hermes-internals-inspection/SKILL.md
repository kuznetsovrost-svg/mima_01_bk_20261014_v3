---
name: hermes-internals-inspection
description: "Investigate the architecture and internals of a live Hermes Agent install. Use when the user asks 'how does Hermes do X', 'where is Y implemented', 'which module handles Z', 'what memory providers exist', 'how does RAG / vector search / FTS5 work in Hermes', or wants a code-grounded answer grounded in the actual installed package rather than docs. Covers the canonical recipe for locating the real source tree on editable-uv installs, walking the package, and mapping feature areas (gateway, tools, memory providers, session store)."
version: 1.1.0
author: agent
license: MIT
metadata:
  hermes:
    tags: [hermes, internals, architecture, source, memory, rag, vector, memory-provider, fts5, gateway, profile]
    related_skills: [hermes-agent, hermes-agent-skill-authoring, hermes-agent-vcs-portability]
---

# Hermes Internals Inspection

Read-only investigation of a live `hermes_agent` install. Produces code-grounded answers (path:line citations) about how a feature is implemented on THIS host, not what the docs claim.

## When to use

- User asks "how does Hermes do X" (RAG, memory, vector search, tool search, session persistence, gateway routing, profile resolution, …)
- User wants a map of a feature area (memory providers, platform adapters, tool registry, cron subsystem, profile subsystem)
- User asks "where is Y implemented" / "which file owns Z" / "what profile is active"
- Before making code-level changes you need to confirm the source layout on the actual install (paths differ between `pip`, `uv`, editable, git-cloned, and Hub installs)
- Cross-checking a doc claim against the running version

## When NOT to use

- Setting up or configuring Hermes → `hermes-agent` (bundled)
- Moving a Hermes agent through Git round-trips → `hermes-agent-vcs-portability`
- Writing or validating a new SKILL.md → `hermes-agent-skill-authoring`
- Running the agent itself → not a debugging task

## The canonical inspection recipe

Hermes installs vary (PyPI wheel, editable uv, git clone, Hub tap). Before walking any source, locate the **real** install root — `pip show`, `python -c "import hermes_agent"`, and `which hermes` will all mislead you on editable installs.

### Step 1 — locate the binary and follow it

```bash
which hermes
cat /usr/local/bin/hermes          # often a bash wrapper that unsets PYTHONPATH and execs the venv binary
```

Read the wrapper. On this host the wrapper is:

```bash
#!/usr/bin/env bash
unset PYTHONPATH
unset PYTHONHOME
exec "/usr/local/lib/hermes-agent/venv/bin/hermes" "$@"
```

So the real `hermes_agent` source is at `/usr/local/lib/hermes-agent/`, **not** in `~/.hermes/hermes-agent/` (the bundled SKILL.md's "Source code" hint is wrong for editable installs).

### Step 2 — find the editable-install mapping

Editable uv installs ship a `__editable___<pkg>_<ver>_finder.py` whose `MAPPING` dict lists every top-level package → real path:

```bash
F=$(python3 -c "import hermes_agent" 2>&1; find ~/.cache/uv -name '__editable___hermes_agent*finder.py' 2>/dev/null | head -1)
cat "$F" | head -30
```

You'll see something like:

```
MAPPING = {
    'agent': '/usr/local/lib/hermes-agent/agent',
    'cli': '/usr/local/lib/hermes-agent/cli',
    'gateway': '/usr/local/lib/hermes-agent/gateway',
    'tools': '/usr/local/lib/hermes-agent/tools',
    'plugins': '/usr/local/lib/hermes-agent/plugins',
    'hermes_state': '/usr/local/lib/hermes-agent/hermes_state',
    ...
}
```

That is the authoritative directory map. Use these paths as the roots in step 3.

### Step 3 — walk the package and grep

Use the search tool of your host (ripgrep, fd, or `os.walk` from `execute_code`). Useful patterns to scope by feature area:

| Area | Pattern (regex) | Typical location |
|------|-----------------|------------------|
| Memory / RAG | `\b(rag\|embedding\|vector\|faiss\|chroma\|qdrant\|retrieval\|semantic_search\|cosine\|ann_index\|vector_store\|hybrid\|bm25)\b` | `plugins/memory/*/`, `agent/memory_provider.py`, `hermes_state.py`, `tools/session_search_tool.py` |
| Session persistence | `FTS5\|CREATE VIRTUAL TABLE\|messages_fts` | `hermes_state.py` (FTS5 schema, WAL handling) |
| Tool search | `tool_search\|tool_describe\|tool_call\|threshold_pct\|deferred` | `tools/tool_search.py` |
| Context budget | `MAX_TURN_BUDGET_CHARS\|persisted-output\|maybe_persist_tool_result` | `tools/tool_result_storage.py` |
| Gateway / platforms | `class.*Adapter\|platforms/.*\.py` | `gateway/platforms/<name>.py` |
| Slash commands | `CommandDef\|COMMAND_REGISTRY` | `hermes_cli/commands.py` |
| Profiles | `HERMES_HOME\|profile_exists\|normalize_profile_name\|get_active_profile_name\|active_profile` | `hermes_cli/profiles.py`, `hermes_cli/main.py:378` |
| Cron | `add_cronjob\|scheduler\.py\|jobs\.py` | `cron/` |
| Profile introspection | `get_active_profile_name\|set_active_profile\|resolve_profile_env` | `hermes_cli/profiles.py:1280`, `hermes_cli/main.py:378–390` |

Tip: to filter out false positives, exclude `node_modules`, `__pycache__`, `dashboard/dist`, `assets/`, `tests/`, `neutts_samples`, and vendored `node/include/node/openssl/...` before grepping — node.js on this host is a tarball extract, not a real source tree, and the bulk is `node/include/node/openssl/archs/*/crypto/buildinf.h` noise that drowns real signals.

### Step 4 — read the relevant files

For each hit file, read the **first 30-50 lines** (module docstring + class + immediate methods) to understand intent, then jump to the cited line for the specific symbol. Most modules in Hermes have good top-of-file docstrings explaining the design — read those first, they save a lot of grepping.

### Step 5 — verify what's actually active on this host

Code presence ≠ activation. Cross-check by:

1. Reading `~/.hermes/config.yaml` for the relevant section (e.g. `memory.provider`, `tools.tool_search`, `gateway.platforms.*`).
2. Listing installed pip packages in the venv: `/usr/local/lib/hermes-agent/venv/bin/pip list`.
3. Checking flat-file state: `~/.hermes/memories/MEMORY.md`, `~/.hermes/memories/USER.md`, `~/.hermes/SOUL.md`, `~/.hermes/state.db`.
4. Inspecting `~/.hermes/profiles/<name>/` for profile-scoped overrides.
5. Determining the active profile: `hermes profile list` (the `◆` row) or `cat ~/.hermes/active_profile` for the sticky override. See `references/profile-introspection.md` for the full algorithm.

A plugin may be **present in the source tree** (`plugins/memory/mem0/`) but **inactive** (no API key, no `provider: mem0` in config). Always report both presence and activation status.

## Pitfalls and traps

- **Don't trust `pip show hermes_agent` for the source path on editable installs.** It returns the egg-info directory, not the real source root. Use the `__editable___*_finder.py` MAPPING instead.
- **`python3 -c "import hermes_agent"` raises `ModuleNotFoundError`** on this host. Hermes's wrapper unsets `PYTHONPATH` and execs its own venv, so a bare `python3` from any other env can't import it. Use the venv's python: `/usr/local/lib/hermes-agent/venv/bin/python` if you need to import.
- **`sqlite3` CLI is not installed on this host** (Ubuntu 24.04 minimal). For SQLite schema inspection use the Python stdlib: `python3 -c "import sqlite3; c=sqlite3.connect('...'); print('\n'.join(r[0] for r in c.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")))"`. However, **direct `python3` reads of `~/.hermes/state.db` are blocked by a user-consent gate** (Hermes security policy treats agent-state DBs as sensitive). Use this trick: read schema via metadata first, then ask the user before opening the DB read-write.
- **Bundled `hermes-agent` skill's "Key Paths" section says `Source code: ~/.hermes/hermes-agent/`** — that's only true for git-clone installs. On uv editable installs, source is at `/usr/local/lib/hermes-agent/`. Don't trust that line blindly.
- **The `node/` directory under `~/.hermes/node/` is a Node.js binary distribution** (with `include/node/openssl/archs/*/crypto/buildinf.h` etc.) — not Hermes code. Grep through it produces tens of thousands of irrelevant `crypto/buildinf.h` lines. Always exclude it.
- **Many plugin "memory providers" require API keys that aren't on this host** (mem0, supermemory, retaindb, honcho, hindsight, openviking, byterover). Listing the plugin directory doesn't mean it works — check `is_available()` semantics in each `__init__.py` (usually `return bool(os.environ.get("XXX_API_KEY"))`).
- **Editable-uv installs duplicate package metadata** in `~/.cache/uv/sdists-v9/editable/.../hermes_agent-0.16.0-0.editable-py3-none-any/` and `~/.cache/uv/archive-v0/.../hermes_agent-0.16.0.dist-info/`. These are caches, not the real source.
- **Hermes sanitizes runs of 3+ `*` in tool payloads** (token redaction). When pasting token-shaped strings into bash via `execute_code`, the asterisks get replaced with `***`. Workaround: pass tokens via `os.environ` or read from a file with `chmod 600` — never via inline f-strings.
- **The session-search tool returns 3-shape outputs (DISCOVERY / SCROLL / BROWSE)** with no explicit mode parameter. The shape is inferred from the args. Read `tools/session_search_tool.py` module docstring before assuming semantics.
- **`HERMES_HOME` and `~/.hermes/active_profile` can disagree** about which profile is "active." `HERMES_HOME` wins if already exported in the shell; the sticky file only takes effect for processes started with no `HERMES_HOME`. `unset HERMES_HOME` to force sticky behaviour. See `references/profile-introspection.md` for the resolution algorithm.
- **`/proc/<pid>/environ` is NUL-separated.** Read with `tr '\0' '\n' < /proc/<pid>/environ`. Permissions are UID-scoped — gateway runs as root, so non-root users need `sudo` to inspect it.

## Quick reference — feature-area file map

Updated for hermes_agent 0.16.0 on this host. Paths under `/usr/local/lib/hermes-agent/`.

### Memory & RAG
- `agent/memory_provider.py` — `MemoryProvider` ABC
- `plugins/memory/mem0/__init__.py` — Mem0 SaaS (server-side extraction + semantic search + reranking)
- `plugins/memory/supermemory/__init__.py` — Supermemory SaaS (auto-recall/auto-capture, system-prompt injection)
- `plugins/memory/retaindb/__init__.py` — RetainDB SaaS (dialectic synthesis, agent self-model from SOUL.md, shared file store rdb://)
- `plugins/memory/honcho/` — Honcho AI SaaS (user-modeling peers)
- `plugins/memory/hindsight/__init__.py` — Hindsight (knowledge graph + entities, cloud OR local)
- `plugins/memory/openviking/__init__.py` — Volcengine OpenViking (viking:// URI, tiered context L0/L1/L2)
- `plugins/memory/byterover/__init__.py` — Byterover
- `plugins/memory/holographic/` — LOCAL, no SaaS. HRR (Plate 1995) + SHA-256 atom vectors + FTS5 + Jaccard rerank + trust weighting. Needs `numpy`; without it, hrr_weight auto-degrades to 0 (FTS5+Jaccard only).

### Session persistence & search
- `hermes_state.py` — SQLite WAL, FTS5 schema (`messages_fts`, `messages_fts_trigram`), `parent_session_id` lineage, NFS/SMB WAL fallback to DELETE journal
- `tools/session_search_tool.py` — `session_search()` tool with 3 calling shapes

### Tool search & context budget
- `tools/tool_search.py` — progressive tool disclosure (CHARS_PER_TOKEN=4 heuristic, stateless catalog, threshold gate)
- `tools/tool_result_storage.py` — per-tool + per-turn budget enforcement, large outputs to `/tmp/hermes-results/{tool_use_id}.txt`
- `tools/budget_config.py` — `BudgetConfig` defaults

### Agent loop & runtime
- `run_agent.py` — `AIAgent` core conversation loop
- `model_tools.py` — tool dispatch, `handle_function_call`
- `toolsets.py` — `TOOLSETS` dict, `_HERMES_CORE_TOOLS`
- `agent/` — prompt builder, context compression, memory manager, model routing, skill dispatch

### CLI
- `cli.py` — interactive CLI (HermesCLI)
- `hermes_cli/main.py` — argparse entry; profile-sticky override read at `:378–390`
- `hermes_cli/commands.py` — `COMMAND_REGISTRY` (slash command definitions)
- `hermes_cli/profiles.py` — profile isolation, normalized profile names, `get_active_profile_name()` at `:1285`
- `hermes_cli/config.py` — `DEFAULT_CONFIG`, env-var definitions

### Profiles
- `hermes_cli/profiles.py:get_active_profile_name()` — the canonical "what profile is this?" function (HERMES_HOME → default/name/custom)
- `hermes_cli/main.py:378–390` — reads `~/.hermes/active_profile` sticky marker at startup
- `hermes_cli/profiles.py:set_active_profile()` — atomic write of the sticky marker (via `.tmp` + replace)
- See `references/profile-introspection.md` for the full algorithm + worked example.

### Gateway
- `gateway/run.py`, `gateway/session.py`
- `gateway/platforms/<name>.py` — one adapter per platform
- `gateway/platforms/base.py` — `MessagingPlatform` ABC

### Cron
- `cron/jobs.py`, `cron/scheduler.py`

### Tests
- `tests/` — ~3000 pytest tests, auto-redirect `HERMES_HOME` to tempdirs

## Verification checklist (run before publishing an answer)

1. **Code-cite the file:line for every claim** — never paraphrase without a path. Future agents reading the answer should be able to `read_file` straight to the line.
2. **Distinguish "code is present" from "feature is active on this host"** — both states are interesting, the user needs to know which one they're getting.
3. **List the venv's pip packages for the relevant area** — `pip list | grep -iE 'numpy|faiss|chroma|...'` catches missing dependencies that silently disable features.
4. **If a feature has a fallback** (e.g. holographic without numpy → FTS5+Jaccard), document the trigger condition and the fallback path.
5. **If proposing code changes, check the `hermes-agent` skill first** — the project layout, security guards, commit conventions, and tool-registration pattern are documented there.
6. **For "which profile?" questions, always include `HERMES_HOME` AND `~/.hermes/active_profile` AND the `◆` row** — they can disagree (HERMES_HOME wins if exported). Single-signal answers mislead.

## Output template for a "how does Hermes do X" report

When the user asks a "how does Hermes do X" question, structure the answer as:

```
1. TL;DR (3-5 bullets, file:line citations)
2. The two layers / components / modules involved
3. Code walkthrough with path:line refs
4. What is currently active on THIS host (config.yaml + pip list)
5. How to enable / disable / extend
6. Pitfalls (with symptoms)
7. Where to look in the docs
```

Files cited should be absolute paths under `/usr/local/lib/hermes-agent/...` (not module-style names) so the reader can `read_file` them directly.

## See also

- `hermes-agent` (bundled) — high-level config, CLI reference, troubleshooting
- `hermes-agent-vcs-portability` — backup/import/export of a Hermes agent via Git
- `hermes-agent-skill-authoring` — how to write a SKILL.md
- `references/hermes-rag-vector-map.md` — the 7 MemoryProvider plugins compared (depth)
- `references/host-install-layout.md` — concrete paths and binaries on this specific host
- `references/profile-introspection.md` — how to determine the active Hermes profile (HERMES_HOME + sticky marker + `◆` row + cross-process `/proc` introspection)