# Skill-family documentation hygiene

**Date:** 2026-09-23
**Origin:** `fst-project-health` v1.0.19 family (5 skills: `fst-project-health`, `fst-project-health-snap-md`, `fst-project-health-snapshot`, `fst-project-health-from-json`, `fst-project-health-word`)

When a project has a **family of class-level skills** (one canonical skill + N satellites that depend on it), keeping their documentation in sync is half the work. The other half is making the relationship obvious to a **new reader receiving the skills** with no context — they must understand the architecture from `README` alone, without sitting through a tour.

This file captures the conventions a future agent should follow when adding a satellite to an existing family, or when receiving a family that doesn't yet follow them.

## The shape

```
<root-skill>/                      # e.g. fst-project-health/
├── SKILL.md                       # always-on rules + "When to load" trigger
├── README.md                      # written for a new human reader
├── CHANGELOG.md                   # single source of truth for versions of the WHOLE family
├── templates/                     # optional, shared
├── scripts/                       # main + helpers
├── references/                    # deep topical docs, indexed from SKILL.md
└── tests/

<satellite-1>/                    # e.g. fst-project-health-snap-md/
├── SKILL.md                       # describes THIS skill only (triggers, dependencies, gotchas)
├── README.md                      # written for a new human reader
├── playbook.md                    # if this skill is heavyweight enough to warrant it
└── references/                    # only if its own depth justifies it
```

Satellites **do not** have their own `CHANGELOG.md`. They link to the root.

## One CHANGELOG.md, in the root skill

`CHANGELOG.md` lives in the **root skill** of the family (the one that all satellites depend on, transitively). Every satellite's `SKILL.md` and `README.md` have a **single-line link** to it:

```markdown
## История

Версии семейства `<root-name>-*` ведутся в общем [CHANGELOG.md](../<root-name>/CHANGELOG.md).

- **v1.0.X** (YYYY-MM-DD) — [summary of what changed for THIS satellite]
- **v1.0.0** (YYYY-MM-DD) — первый релиз.
```

The root's `CHANGELOG.md` covers **the whole family** — every entry mentions which satellites were touched (e.g. "v1.0.19: snap-md использует `--generator`"). Drift in this rule causes the symptoms below; treat it as load-bearing.

## Three signal symptoms that mean "documentation is wrong"

When a new human (or agent) reads a skill and finds one of these, the family is broken — the README is lying about the code:

1. **"What does this need from the others?"** — the README's dependencies table says `X` is required, but the README of `X` doesn't list this skill as a consumer. The relationship is one-sided; whoever told you to install `X` first was lying.
2. **"What version?"** — `version: 1.0.19` in `SKILL.md::description` but the file `CHANGELOG.md` doesn't have v1.0.19. Either the version is fabricated or the changelog is lagging.
3. **"Where does the timestamp come from?"** — the HTML output shows timestamp A; the underlying MD carries timestamp B. There are now two sources of truth for the same fact. Pick one (MD), drop the other.

Each of these means **the next agent will lose 30–60 minutes** sorting out what's true. Fix at the root, not by adding caveats to the README.

## The "one file per fact" rule

A fact lives in **exactly one file**. If a fact recurs in another file, that's a **link** to the original, not a copy. Examples:

| Fact | Lives in | Satellites reference it as |
|------|----------|------------------------------|
| Version history of the family | `<root>/CHANGELOG.md` | "see История in [CHANGELOG.md](../<root>/CHANGELOG.md)" |
| Color palette / shared design tokens | `<root>/references/<topic>.md` | "design tokens live in `<root>/references/...`" |
| MCP method signatures (per-tool contracts) | a top-level Playbook/Reference | "see Playbook section X.Y" |
| Scheduler (`source_template = "cron"`) | one schema — `cron` does NOT exist as a separate skill | n/a |

**Anti-pattern** to recognise: a fact appears in both `README.md` and `CHANGELOG.md`, slightly phrased differently. After three such drifts, readers stop trusting either file. The "fix" is **never** "copy more carefully" — it's "delete the second copy, link to the original".

## The `--generator` convention

When a root skill writes an MD (or any artifact) that downstream skills may consume, the writer exposes a `generator` parameter (CLI flag or function arg) and **the caller passes its own name**. The default `generator` value is the most-likely caller, but it MUST be overridable.

Why this is non-obvious: if the writer hardcodes `generator: "fst-project-health"` (the writer's own name), then when a satellite calls the same writer to produce an MD **that the satellite owns**, the MD claims to be from `fst-project-health` — wrong attribution, debugging nightmare.

```python
# WRONG: writer hardcodes its own name
def write_md(project: dict):
    metadata["generator"] = "fst-project-health"   # always!
    # ...

# RIGHT: writer accepts and uses caller's name
def write_md(project: dict, generator: str = "fst-project-health"):
    metadata["generator"] = generator
    # ...
```

The convention is captured in CHANGELOG.md of fst-project-health under "Архитектурные инварианты" → "Каждый caller `run_all.py` передаёт `--generator <свой>`".

## Conventions for a new satellite

When adding a satellite to a family, the order matters — do this in one pass to avoid drift:

1. **Make the satellite's `SKILL.md`** describe only what THIS skill does. Triggers, dependencies, output shape. Not the parent's history.
2. **Link, don't copy.** Satellite's SKILL.md has a single sentence "История ведётся в `<root>/CHANGELOG.md`". Done.
3. **Satellite's `README.md`** answers "how do I run this one thing?" Same one-sentence link to root CHANGELOG.
4. **Root's `SKILL.md::description` (and root's `CHANGELOG.md`)** get the entry about the new satellite. Each version entry lists what changed in each sibling.

Lather-rinse-repeat per version. If you find yourself updating a satellite's docs but not the root's CHANGELOG, you're about to cause symptom #2.

## When someone adds a NEW fact mid-sprint

Common case: a satellite's README needs one new sentence that isn't anywhere else.

**Wrong move:** add the sentence, leave the parent CHANGELOG alone.

**Right move:** add the sentence to the satellite, AND add a one-bullet entry to the root's CHANGELOG in the "Not yet released" section (if you have one), or in the next version entry. The two are inseparable — without the CHANGELOG entry, the satellite's fact will become symptom #2 within a session or two.

If the new fact is **architecture-level** (a "always-true rule", e.g. snapshot format is always one file), promote it to the root CHANGELOG's "Архитектурные инварианты" section, **not** the version history. That section is the rule book; don't bury rules in release notes.

## Cross-cutting reference table

| Question | Pointer |
|----------|---------|
| "What's the current canonical setup?" | `<root>/SKILL.md::Quick reference` (do not duplicate in satellites) |
| "Why was X done?" | `<root>/CHANGELOG.md` (one entry, do not restate) |
| "What fact never changes?" | `<root>/CHANGELOG.md::Архитектурные инварианты` (treated as immutable contract) |
| "How does satellite N work in detail?" | `<satellite-N>/playbook.md` (own reference, allowed to be detailed) |
| "What's outdated?" | `<root>/CHANGELOG.md` — find the latest version entry and act on that |

## Failure mode to remember

The original symptom that produced this file: a new reader of `fst-project-health-snap-md` opened the README, saw "Зависимость от word", installed word, found it wasn't needed, and spent an hour realising the dependency had been removed without anyone updating the README. Each fix made the symptoms grow because the source of truth (CHANGELOG) wasn't being read.

That cost was recoverable. The next cost — symptom #1 (dependency mismatch across README files) where one side says "required" and the other side says "doesn't exist" — is recoverable only if the agent catches it early. The hygiene above makes both classes of bug visible at the moment they appear, not weeks later.

## Anti-patterns to fail loudly on

Reject any of these on sight — they always come back:

- **"I'll add a CHANGELOG entry next week"** — it never happens. Either the entry is in the root CHANGELOG now, or the work isn't done.
- **"I'll mention the satellite in passing in the satellite's README"** — root CHANGELOG gets the version-aware mention, satellite gets a one-line link.
- **"I'll factor the dependency table later"** — DRY violations between satellite README and root SKILL.md accumulate; do the cleanup while context is fresh.
- **"I'll add the YAML schema for the satellite generator field"** — that's a separate workstream; if you're here to fix the docs, stay on docs.

The pattern: each time you say "later", you're setting up the next 30-minute re-discovery.
