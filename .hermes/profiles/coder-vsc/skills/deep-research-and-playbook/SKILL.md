---
name: deep-research-and-playbook
description: "Triggers on 'playbook', 'собери гайд', 'how to use X'."
version: 1.0.0
author: Hermes Agent + Nous Research
license: MIT
metadata:
  hermes:
    tags: [research, writing, documentation, playbook, methodology, synthesis, markdown, long-form]
---

# Deep Research → Playbook

Synthesize a public or internal methodology into a long-form, navigable, example-rich playbook. The output is a single `.md` file (typically 40–100 KB) that a human can read once and act on, or that a future agent session can re-load to reproduce the same workflow. This skill is the *production* side of "load a framework's source, understand it, and ship a guide that survives contact with reality".

## When to use

- "собери playbook / гайд / how-to по X"
- "research methodology X and produce a doc"
- "объясни X подробно, с примерами, пошагово"
- "compare A vs B (frameworks, libraries, methods) and ship a decision doc"
- "make a reference doc for our team's workflow based on tool Y"
- After web research that has surfaced 5+ primary sources, and the user wants a permanent artifact, not just an answer in chat.

## When NOT to use

- One-paragraph "what is X" question — answer in chat.
- "Fix this bug" / "implement this feature" — that's coding, not research.
- Internal docs that are 1–2 pages of procedures — `write_file` directly, no playbook ceremony.

## Procedure

### Step 1. Clarify scope (one question, 2–4 named options, recommended first)

The user said "playbook" but the depth and shape vary enormously. Ask **one** `clarify` call covering:
- **Depth**: exhaustive (every skill, every template, every schema field) vs. practical (apply-it-tomorrow) vs. conceptual (why, not how)
- **Source recency**: latest stable release only, or also include previews / WIP / historical context
- **Output format**: one consolidated .md, or split per topic; with or without embedded code samples; with or without comparative table vs. alternatives
- **Delivery**: in chat, or as a file (default: file when payload > ~15 KB)

Skip the question only if the user already specified "exhaustive / practical / conceptual" AND format AND delivery in the original request.

### Step 2. Map the source space in parallel

Before reading deeply, fan out 2–4 parallel `web_search` / `web_extract` calls to map the territory:
- Official repo README + CHANGELOG + tag list
- Each top-level skill / module's `SKILL.md` (or equivalent)
- The 1–3 "explainer" / "design doc" reference files
- If a fork exists with different version, fetch its README too (often has sharper wording)

Why parallel: a single `web_search` rarely surfaces both the canonical doc and the *index* of supporting files. You need the map before the territory.

### Step 3. Read the canonical sources in priority order

1. The single "explainer" / "read-me-first" doc first (it usually names every concept you'll later cross-reference)
2. The top-level catalog of skills / modules / artifacts (gives you the enumeration)
3. The 2–3 most central skill files (in a framework with 15 skills, read the 3 that everyone else calls into)
4. The XML / config / schema templates (these are the *real* artifact, more important than the prose)
5. Reference docs only after you have a working mental model — they fill gaps, they don't build the structure

Do **not** read all 15 skills at equal depth. Read the 3–5 central ones deeply; skim the rest for unique terms / cross-references / examples.

### Step 4. Distinguish observed from inferred — explicitly

Every claim in the playbook must be tagged one of:
- **From source** — direct quote, code block, or schema field, with citation (URL or file path).
- **Inferred from principles** — your synthesis, marked as such ("If we apply the same pattern to a new use-case...").
- **Analogy / extension** — when applying the source's pattern to a domain the source doesn't cover (e.g. applying a code-engineering methodology to a documentation project). Mark these with "Analogy" or "Extension" and explain the mapping.

Without this discipline, the playbook becomes a paste-bin that confidently asserts things the source never said. The user's "не выдумывай источники" rule applies.

### Step 5. Compose the playbook structure (always include these sections)

1. **Orientation in 60 seconds** — what is X, the 3–5 problem/solution pairs, the 1–2 governing metaphors (e.g. "process-first, not prompt-first"). This is the section that gets re-read first.
2. **Principles** (5–8 numbered, ~1 paragraph each) — the irreducible rules. Distilled from source, not verbatim quotes.
3. **Catalog** — every component, named, with one-line purpose. Tables work well here.
4. **Lifecycle / workflow** — the main loop (init → spec → plan → execute → verify → archive, or equivalent). The most-referenced section.
5. **Per-component detail** — one subsection per major component (skill, artifact, schema, CLI command). Include real example snippets taken from the source, not invented.
6. **End-to-end worked example** — one realistic scenario, walked through all phases, with real XML / code / artifacts. This is where readers build intuition. Use the actual templates from the source, with your placeholder values.
7. **Pitfalls / anti-patterns** — what the source warns against + what the user is likely to attempt wrong.
8. **For your own system** (if the user is designing their own process) — what to lift, what to drop, what to rename, what format to use. This is the highest-leverage section for a builder-user.
9. **Appendix** — file paths, tag glossary, source URLs.

### Step 6. Source the examples, don't invent them

For every XML / code / config example in the playbook:
- Prefer the actual template file from the source repo (fetch via `web_extract` of the raw URL). Real templates have the right field names, the right defaults, the right namespace.
- If the source has no template, write the minimum needed to make the principle concrete — but flag it as "inferred" and explain the fields.
- Never invent IDs, namespaces, or attribute names that contradict the source's own examples. If you do, the user will discover it on first try.

### Step 7. Length budget

- 40–80 KB is the sweet spot for a framework playbook (covers 5–10 components with real examples). Below 20 KB = undercooked; above 120 KB = needs splitting.
- If the source has 15+ components, consider a "Part 1" / "Part 2" split rather than one 150 KB file. The user asked for "one playbook"; respect that, but use a clear top-of-doc TOC and named section anchors.

### Step 8. Deliver as `MEDIA:` when over 15 KB

For long playbooks, write the file to disk first (`/root/<topic>-playbook.md`), then send via `MEDIA:/root/<topic>-playbook.md`. This:
- gives the user a permanent handle to re-share,
- shows up as a native file in Telegram (vs. an inline code block the user has to scroll),
- lets you reference the file path in any follow-up session.

Don't paste 60 KB of markdown into chat — the user can't scroll back to find section 9.

## Pitfalls

- **Don't paraphrase the official README into your own words without adding analysis.** A playbook that just re-says the README adds zero value and burns the user's trust on the second read. Synthesis is the deliverable; the source quote is a *citation*.
- **Don't use `vision_analyze` or rendering tools on `.md` / `.json` source files.** Use `web_extract` (clean text, no LLM summary) for raw GitHub URLs and other text endpoints; reserve browser tools for interactive pages. The `file-format-conversion` skill covers the rest.
- **Don't paste full source files into the playbook.** Quote the relevant 5–30 lines with citation; let the user follow the link for the rest. Playbooks that embed 200-line source dumps become unreadable.
- **Don't fabricate "typical workflow" diagrams from imagination.** If the source's README has a workflow diagram, either link to it or transcribe the steps as a text list. Never invent a step.
- **Don't skip the "for your own system" section even if the user didn't ask for it.** If the user requested a research playbook, they are usually building something — give them the extension. Mark it as "extension beyond source" so they can skip it if they just want the literal guide.
- **Don't deliver as inline chat when the payload is large.** Telegram and similar channels truncate, scroll past, and the user can't search later. Always write to disk + `MEDIA:` for payloads > ~15 KB.
- **Don't load the canonical doc twice (once in `web_extract`, once via `browser_navigate`)** — pick one tool per source. `web_extract` for `.md` / raw text endpoints; `browser_navigate` only for interactive pages that need rendering or clicks.

## Hard rules

- **Cite every load-bearing claim with a source path or URL** — not a memory of reading the source. If you can't cite it, the claim either comes from inference (mark it) or doesn't belong in the playbook.
- **Never claim a feature exists in version X without confirming the version** — GitHub repos have `main`, stable tags, and previews. Use `web_extract` on the canonical CHANGELOG / release notes when version matters.
- **Never deliver a playbook whose worked example uses invented namespaces or placeholder IDs that contradict the source.** If the source uses `<M-AUTH NAME="..." TYPE="...">`, use that exact form; don't write `<module id="M-AUTH">`.
- **If the user said "файл сюда в телеграм" / "send as a file" / "пришли .md"**, the file IS the deliverable, not a summary that points at the file. Send the file via `MEDIA:` and add a 3–5 line chat summary, not the other way around.

## Quick environment check (before starting a 60 KB research task)

```bash
# Confirm you have disk space and a writable location
df -h /root 2>&1 | tail -2
ls -ld /root 2>&1
```

If `/root` is not writable, redirect output to `~/.hermes/profiles/<active>/cache/` and reference that path in `MEDIA:`.

## Output checklist (before sending the file)

- [ ] Top-of-doc TOC with named section anchors (`## §3`, `### 3.1`, etc.)
- [ ] Every load-bearing claim has a citation (URL or file path)
- [ ] Worked example uses real source templates, not invented ones
- [ ] "For your own system" or equivalent extension section is present
- [ ] Anti-patterns / pitfalls section is present
- [ ] Total file size between 30–120 KB; if larger, split with a Part 1/Part 2
- [ ] File written to `/root/<topic>-playbook.md` (or active profile cache) and sent via `MEDIA:`
- [ ] Chat message after the file is ≤ 5 lines: TOC + 1-line "what's inside" + offer to drill into a section
