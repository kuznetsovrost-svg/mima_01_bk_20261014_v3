---
name: persistent-knowledge-base
description: "Multi-vault persistent knowledge base with per-vault AGENTS.md schemas, agent configuration via YAML allowed_vaults, and git-based backup strategy. Use when a user runs several substantially different research/work domains (5-10 vaults), each needs isolated wiki with its own agent permissions, and they want single-writer (server) + read-only viewer (laptop) workflow. Covers Karpathy LLM Wiki pattern scaled to multi-tenant personal use, NOT single-wiki setups (use llm-wiki)."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [wiki, knowledge-base, multi-vault, research, notes, markdown, hermes-agent-integration, enrichment-pipeline, human-curated]
    category: research
    related_skills: [llm-wiki, obsidian, hermes-profile-management]
    changelog: "v1.1.0 (2026-08-25): added the Enrichment Pipeline section — human builds the wiki skeleton in local Obsidian (graph, headings, brief summaries), embeds a JSON task block per stub note, and the server agent fills in bodies on demand. Covers the JSON-task protocol (type/depth/audience/length/must_cover/avoid/must_reference_pages/illustrate), the agent processing workflow, and 6 specific pitfalls (replace_body default, use_neighbour_content choice, vague must_cover, missing wikilinks, illustration kind, batch size). Schema reference extracted to references/enrichment-task-schema.md. v1.0.0: initial."
---

# Persistent Knowledge Base (Multi-Vault)

A persistent, compounding knowledge base built from interlinked markdown, **scaled to multiple domains**. Based on Karpathy's LLM Wiki pattern but extended for users with several substantially different work areas that need to stay isolated.

## When This Skill Activates

Use this skill when:
- User has **5-10 substantially different research/work domains** that need separate wikis
- User wants **per-vault schema discipline** (each vault has its own AGENTS.md)
- Multiple **agents need different vault access** (e.g., `default` reads everything, `analyst_training` only reads research)
- User wants **server-side single-writer** with **laptop read-only** workflow (no two-way sync conflicts)
- User is **already running the base llm-wiki skill** but needs multi-vault extensions

Do NOT use for:
- Single-wiki setups → use `llm-wiki`
- Generic markdown note-taking without Karpathy's compounding pattern → use `obsidian`
- Pure Obsidian UI work without server-side autonomy → use `obsidian`

## Architecture

```
/root/wiki-system/
├── README.md                              # overview
├── AGENTS.md                              # master schema (read by all agents)
├── templates/                             # starter files
│   ├── AGENTS.template.md                 # per-vault schema
│   ├── README.template.md
│   └── pages/                             # page format templates
├── vaults/                                # the wikis themselves
│   ├── engineering/                       # one vault per domain
│   │   ├── .git/                          # each vault is its own git repo
│   │   ├── AGENTS.md                      # per-vault discipline file
│   │   ├── 00_Inbox/                      # unsorted incoming material
│   │   ├── 10_Sources/                    # immutable raw sources
│   │   ├── 20_Notes/                      # human diary
│   │   ├── 80_Wiki/                       # LLM-maintained
│   │   │   ├── index.md
│   │   │   ├── log.md
│   │   │   ├── entities/
│   │   │   ├── concepts/
│   │   │   ├── sources/
│   │   │   ├── comparisons/
│   │   │   └── synthesis/
│   │   └── 90_Synthesis/
│   └── _archive/                          # retired vaults
├── agents/                                # agent configs
│   ├── _template.yaml
│   ├── default.yaml
│   ├── analyst_training.yaml
│   └── fst-control.yaml
├── cross-vault-index.md                   # auto-generated global catalog
└── tools/
    ├── new-vault.sh
    ├── new-agent.sh
    ├── copy-source.sh
    ├── cross-vault-search.sh
    ├── lint-all.sh
    ├── daily-digest.sh
    ├── backup-all.sh
    └── regenerate-cross-index.sh
```

The two-layer pattern is key: **global AGENTS.md** + **per-vault AGENTS.md**. The global file holds cross-cutting rules (cross-vault link format, backup policy, agent permission resolution). The per-vault file holds vault-specific rules (priority tags, ignored sources, vault-specific style).

## Resuming an Existing Multi-Vault Setup (CRITICAL)

Before doing anything in any session:

① **Read `/root/wiki-system/AGENTS.md`** — global rules
② **Read `/root/wiki-system/agents/${HERMES_PROFILE}.yaml`** — which vaults this agent can touch
③ **For the target vault**, read `<vault>/AGENTS.md` — vault-specific rules
④ **Read `<vault>/80_Wiki/index.md`** — what pages exist
⑤ **Scan `<vault>/80_Wiki/log.md`** — last 20-30 entries

Skipping any of these causes: writing to vaults the agent doesn't have permission for, breaking cross-vault link conventions, or contradicting vault-specific rules.

## Initializing a New Multi-Vault Setup

1. Create the directory structure above
2. Write the global `AGENTS.md` (template in `templates/global-AGENTS.template.md`)
3. Create the agents config directory with `_template.yaml`
4. For each vault the user wants:
   - Run `tools/new-vault.sh <name> --description "..."`
   - This creates the vault structure, copies the AGENTS template, runs `git init`, makes the first commit
   - Customize the per-vault AGENTS.md with vault-specific notes
   - Add the vault to each agent's `allowed_vaults` in their YAML config
5. Run `tools/regenerate-cross-index.sh` to create the initial `cross-vault-index.md`

### Agent config format

Each agent gets a YAML file at `/root/wiki-system/agents/<profile>.yaml`:

```yaml
agent: default
description: "Main agent (Rost) — every domain"
allowed_vaults:
  - engineering
  - research
  - hermes-platform
  - product-strategy
  - personal-growth
default_vault: engineering
permissions:
  read: all          # all | allowed | none
  write: all         # all | allowed | none
restricted_paths:
  - vaults/_archive/
created: 2026-08-25
```

### Reading the agent config from the agent

The skill reads `$HERMES_PROFILE` to find the current agent's YAML. If the agent tries to operate on a vault not in `allowed_vaults`, refuse with a clear error pointing at the allowed list.

## Per-Vault AGENTS.md

Each vault has its own `AGENTS.md` (different from the global one). The full template is in `references/agents-md-schema.md` (loaded as a support file). Key sections:

- **Purpose** — what this vault covers
- **Folder structure** — the standard 6 subfolders
- **Ingest workflow** — including the "discuss before writing" rule
- **Page format** — Summary / Sources / Last updated / Related pages
- **Citation rules** — `(source: filename.pdf)` after every factual claim
- **Question answering** — explicitly say "I don't know" if the wiki doesn't have the answer
- **Lint** — page format compliance + contradictions + orphans
- **Rules** — kebab-case names, no source modification, ask on uncertainty
- **Cross-vault references** — `[[othervault:Page Name]]` format
- **Vault-specific notes** — empty by default, populate per vault

## Core Operations

### Ingest (per vault)

Same as `llm-wiki`, but scoped to one vault:

1. Capture source in `<vault>/10_Sources/<subdir>/`
2. Discuss takeaways with the user (skip in cron)
3. Check what exists in `<vault>/80_Wiki/index.md`
4. Create/update pages following the per-vault AGENTS.md format
5. Update `<vault>/80_Wiki/index.md` and `<vault>/80_Wiki/log.md`
6. For each new entity/concept, check if it exists in another vault — if yes, add `[[othervault:Page Name]]` cross-link
7. Report what changed

**Cross-vault sources:** if the source material applies to multiple vaults, use `tools/copy-source.sh <file> --from <vault_a> --to <vault_b>`. This copies the file and adds bidirectional cross-links to both wiki summaries.

### Query (single vault)

1. Read `<vault>/80_Wiki/index.md`
2. For 100+ page vaults, also `search_files` for the topic
3. Read the relevant pages, synthesize
4. Cite wiki pages: "Based on [[page-a]] and [[page-b]]..."
5. If answer is valuable and not already filed, offer to save as new page
6. **If the answer is not in the wiki, say so clearly** — no fabrication

### Cross-vault query

Use `tools/cross-vault-search.sh "<query>"` to grep across all `allowed_vaults`. Returns hits grouped by vault. Then read the relevant pages from each vault and answer.

### Lint (per vault)

Beyond standard `llm-wiki` lint, also check:
- **Page format compliance** — every wiki page has Summary / Sources / Last updated / Related pages sections
- **Citation density** — flag pages with <50% of factual claims having `(source: ...)` markers
- **Cross-vault link validity** — `[[othervault:Page]]` actually resolves to an existing page

Report findings as a numbered list with suggested fixes.

### Cross-vault lint

`tools/lint-all.sh` runs lint on every allowed vault, aggregates findings, reports per-vault stats. Use cron for weekly runs.

## Backup Strategy

**Git push to a remote (GitHub/GitLab) is the primary backup.** Each vault has its own git repo, so each can have its own remote (or share one with subdirectories).

```bash
# Set up remote for each vault
cd /root/wiki-system/vaults/engineering
git remote add origin git@github.com:<user>/wiki-engineering.git
git push -u origin main
```

**Daily automatic backup via cron:**

```bash
# /root/wiki-system/tools/backup-all.sh
#!/bin/bash
set -e
VAULTS_DIR="/root/wiki-system/vaults"
for vault_dir in $VAULTS_DIR/*/; do
    vault_name=$(basename "$vault_dir")
    cd "$vault_dir"
    [[ -n $(git status --porcelain) ]] && git add . && git commit -m "auto-backup: $(date -Iseconds)" || true
    git push origin main 2>> /var/log/wiki-backup.log
done
```

Cron entry:
```cron
0 3 * * * /root/wiki-system/tools/backup-all.sh
```

**Local backup on demand:**

```bash
# /root/wiki-system/tools/local-backup.sh
tar -czf /root/wiki-backups/wiki-system-$(date +%Y%m%d_%H%M%S).tar.gz \
    --exclude='.git/objects' \
    --exclude='__pycache__' \
    /root/wiki-system/
```

Keep last 30 days via separate cron cleanup.

## Sync to Laptop (read-only)

User runs manual `rsync` when they want to view:

```bash
# Whole wiki-system
rsync -av --delete user@mima_g_01:/root/wiki-system/ ~/Desktop/wiki-readonly/

# Just one vault
rsync -av --delete user@mima_g_01:/root/wiki-system/vaults/engineering/ ~/Desktop/wiki-readonly/engineering/
```

Then open the local copy in Obsidian / VSCode / any markdown viewer. **Do not modify locally and rsync back** — vault is single-writer (server only).

## Cross-Vault Link Format

```
[[vaultname:Page Name]]
```

- **Same-vault link:** `[[machine-learning]]` (no prefix, resolved in current vault)
- **Cross-vault link:** `[[research:Distributed Systems]]`
- **Resolution order:** exact match → slug match → fuzzy match → broken link (flag in lint)

The skill maintains `/root/wiki-system/cross-vault-index.md` as the global catalog. Auto-regenerated by `tools/regenerate-cross-index.sh`. Sections per vault: page count, hub pages, orphan pages, recent activity, and a cross-vault link matrix.

## Pitfalls

- **Single-writer only** — vault files are written by ONE writer (the server agent). If user edits locally, rsync back will overwrite their changes silently. Always surface this warning.
- **Git remote is the primary backup** — not Obsidian Sync, not Syncthing, not Dropbox. Sync to those tools complicates the git history.
- **AGENTS.md per vault must be small** — agents read it every session; large files slow orientation. Put deep conventions in vault-specific READMEs instead.
- **Cross-vault links are references, not duplicates** — when a concept exists in two vaults, that's intentional. Don't merge them. Each vault has its own context.
- **Cascade limit** — single ingest max 3 levels deep (source → entity → synthesis). Deeper cascades silently explode the wiki.
- **`reviewed: true` is sacred** — never overwrite a reviewed page without explicit user confirmation, even with strong new evidence. Surface the conflict, let user decide.
- **Lint format matters** — page format compliance (Summary / Sources / Last updated / Related pages) is enforced by lint. Pages without it should be auto-fixed or flagged, not ignored.
- **Citation rule is strict** — every factual claim needs `(source: filename.pdf)`. Synthesis without citation is is editorializing, not a wiki.

"## Related Skills

- `llm-wiki` — the single-wiki pattern this scales
- `obsidian` — for filesystem-first vault work on a single vault
- `hermes-profile-management` — for creating/configuring the Hermes profiles that drive `agents/<profile>.yaml`
- `arxiv` — natural pairing for `research/` vaults
- `plan` — useful when designing new vault structure

## Sharing Out: Knowledge Garden Export

For distributing a single vault (or 2-3 vaults together) to non-Obsidian users — collaborators, reviewers, anyone who should browse the graph and read notes — produce a self-contained HTML artifact called a "Knowledge Garden". The full architectural decisions, output structure, cytoscape configuration, and motion behaviors live in `references/knowledge-garden-export.md`. Read it before designing the build script or re-litigating format choices — that file is the source of truth for **what** gets generated; the JSON-task protocol section above is **how** the agent processes individual stub notes.

## Setup Needed

- Each vault needs `git init` and a remote configured for backup
- Each agent's `$HERMES_PROFILE` env var must map to an existing `/root/wiki-system/agents/<profile>.yaml`
- Optional: `obsidian-headless` or manual `rsync` for laptop viewing

## The Enrichment Pipeline (human-skeleton → agent-enriches)

A different flow from the standard "agent ingests sources on demand" pattern. Here the **human** builds the wiki skeleton in their local Obsidian — graph, headings, [[wikilinks]], brief summaries — and the **agent** on the server fills in the bodies on demand.

### When to use this pattern

- The user has 30-200 wiki nodes planned and wants fine control over which ones get written when
- The user wants to think in terms of "what should this note say" rather than "ingest this source"
- The user's domain is mostly human-curated knowledge (training material, concepts, internal docs) — not a stream of new external sources
- The user wants to keep Obsidian as the source of truth (they own the vault), with the server agent acting as a contractor

### The JSON-task protocol

The human writes a JSON block inside each stub note describing what the agent should do with it. After processing, the agent deletes the JSON.

```json
{
  "enrich": {
    "type": "entity | concept | synthesis | comparison | note",
    "purpose": "Why this note exists (1 sentence)",
    "depth": "expand | decompose | compare | illustrate | synthesize",
    "audience": "beginner | intermediate | expert",
    "length": "brief | 1page | 2page | long",
    "must_cover": ["point 1", "point 2", "point 3"],
    "avoid": ["what NOT to write"],
    "must_reference_pages": ["Note A", "Note B"],
    "illustrate": [{"kind": "mermaid", "title": "...", "what": "..."}],
    "structure_hint": "Optional: suggested H2 order"
  },
  "context_from_graph": {
    "neighbours": ["Note A"],
    "use_neighbour_content": "summary_only | summary_and_links | full"
  },
  "remove_after": true,
  "replace_body": true,
  "review": {
    "audience_check": "What reader should understand after reading",
    "length_target_words": 600
  }
}
```

The full schema, every enum value, and worked examples live in `references/enrichment-task-schema.md`.

### How the agent processes a task

1. **Parse the JSON** — fail loud if `enrich` block is missing or `must_cover` is empty.
2. **Read neighbour notes** per `must_reference_pages` / `neighbours` — `summary_only` by default, escalate to `summary_and_links` or `full` only when the task says so. **Do not read the whole graph** unless `synthesize` depth.
3. **Honor `replace_body: true`** — wipe everything between the H1 and the JSON block (preserving `[[wikilinks]]` if they appear outside the body, e.g., in a metadata section above the body).
4. **Honor `remove_after: true`** — strip the JSON fence after the body is written.
5. **Bump `updated` date** in frontmatter; set `confidence` per claim quality.
6. **Add `[[wikilinks]]`** for every `must_reference_pages` entry — the agent MUST, not best-effort.
7. **Verify against `audience_check`** — re-read the produced body and ask "does this deliver the stated check?". If no, rewrite before claiming done.

### Pitfalls

- **`replace_body: false` is dangerous.** If the stub has any placeholder text (`[TODO: enrich]`, draft sentences), the agent's new text glues onto it. Always default to `replace_body: true`.
- **`use_neighbour_content: full` on 50-node graphs.** This reads every linked note in full. For a synthesis note that's appropriate; for an `expand` task on one entity, it's overkill and burns context. Default `summary_only` covers 80% of cases.
- **`must_cover` as a single vague sentence.** `"Расскажи про X подробно"` is not a `must_cover` — it's a wish. The schema wants a list of points, each of which becomes a paragraph or section. Vague `must_cover` produces vague bodies.
- **No `must_reference_pages`.** Without this list, the agent may write a note that has zero `[[wikilinks]]`, breaking the point of the wiki. **Always require** the user to list at least 2-3 wikilinks per note.
- **Illustrating without `kind`.** `illustrate: ["add a diagram"]` is unparseable. The agent may default to ASCII art which Obsidian won't render. Require `kind: mermaid | table | external`.
- **Processing all 50 notes in one session.** This is not Karpathy's pattern. Process 5-10 at a time, let the user review, fix the schema based on what's missing, then continue. **Do not run the same prompt over 50 files in a loop.**
- **Forgetting `remove_after`.** If left unset or `false`, the JSON block survives in the final note and clutters it. Default is `true`.

### Relation to other skills

- `llm-wiki` — the agent-driven ingest pattern; this is its complement for human-curated content
- `obsidian` — Obsidian is the user's editing surface here, the agent never opens the desktop app
- `simple-parallel-batch` (if it exists in the user's stack) — useful for "process N notes", but loop-by-loop is preferred to a single batch so the user can adjust between rounds

## Setup Needed (extended)

The Enrichment Pipeline adds two setup items on top of the base setup:

- A `templates/AGENTS.md` snippet that documents the JSON-task protocol (point the user to it via `references/enrichment-task-schema.md` if they're writing tasks by hand)
- A `tools/enrich-batch.sh` script (optional) — runs the agent loop over a list of stub notes, pauses every N notes for user review