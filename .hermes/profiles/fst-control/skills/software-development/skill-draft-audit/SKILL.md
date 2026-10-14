---
name: skill-draft-audit
description: "Use when the user hands you a SKILL.md draft (typically `SKILL-<name>-V0N.md`) and asks you to 'проверить на недостатки', 'оптимизировать', 'убрать лишнее', or 'посмотри, есть что выкинуть' — and explicitly says 'сам скилл пока не создавай' or 'не устанавливай'. Trigger phrases: 'проверь проект скилла', 'оптимизируй заготовку', 'на что обратить внимание перед созданием', 'audit this skill draft'. Loads for any SKILL.md audit pass that produces an optimized next-version document without installing anything."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [skills, audit, review, optimization, hermes-agent, skill-md]
    related_skills: [hermes-agent-skill-authoring]
---

# Audit / Optimize a SKILL.md Draft Before Installation

## Overview

The user has a SKILL.md draft (often attached as a document or sitting in `~/.hermes/profiles/<profile>/cache/documents/`). They want a **review pass** that produces an optimized next-version file. They do **not** want the skill installed yet — that comes later, after manual validation.

This is distinct from `hermes-agent-skill-authoring` (which covers *creating* a skill) and from `requesting-code-review` (which covers source code, not skill docs). The output is a new draft document, never a live skill in `~/.hermes/skills/<name>/`.

## When to Use

- User sends a `SKILL-<name>-V0N.md` and says "проверь / оптимизируй / убери лишнее".
- User says "сам скилл пока не создавай" or "не устанавливай".
- User wants a `V0(N+1)` returned with version bumped and a change history.
- User mentions specific structural rules that must be preserved (e.g. "каждый раздел = Назначение / Получение / Интерпретация / Вывод").

**Do not use** when the user wants to:
- Install a new skill (use `hermes-agent-skill-authoring` and `skill_manage(action='create')`).
- Add `scripts/`, `templates/`, or `references/` files to an existing live skill.
- Make targeted edits to an already-installed skill (use `skill_manage(action='patch')`).

## Workflow

1. **Inventory the source.** Read the entire draft before touching it. Note the section structure the user specified, total lines and bytes (you'll quote them in the report).
2. **Inventory referenced assets lightly.** If the draft references files under `templates/`, `references/`, or `scripts/`, open them ONLY if they're in scope for the audit. If the user says "ссылки на скрипты пока не ищи" / "ими мы займёмся на следующем этапе" — skip. Keep those references intact in the optimized draft.
3. **Run a structured audit.** Build a table with these categories; mark each finding with the line/section it lives in:
   - **Typos** (headings, code identifiers, names, RU/EN transliteration mismatches).
   - **Version drift** (frontmatter `version:` vs. version mentioned in body).
   - **Frontmatter hygiene** (`category`, `tags`, `license`, `platforms` — flag anything that doesn't match peer norms in `hermes-agent-skill-authoring`).
   - **Placeholder/плейсхолдер correctness** — this is where draft bugs hide. Cross-check every `{r[N].xxx}` or template token against the column header and the data dictionary. Mismatched placeholders are a common defect.
   - **Numbering collisions** (rows numbered 1,1,2,2,3,3 instead of 1..N).
   - **Logic contradictions** (e.g. "set status X if Y" followed by "set status X if not Y" in the same paragraph).
   - **Terminology drift** (same concept named three ways across sections — pick one and propagate).
   - **Hardcoded thresholds** that should live in `*-thresholds.py` parameter files per the user's preferred style ("не хардкод").
   - **Repeated boilerplate** ("Шаблоны отчетов лежат в каталоге templates/" written in every section — extract once into Overview).
4. **Decide what to keep untouched.** List explicitly:
   - User-specified section structure (preserve literally).
   - Scripts referenced but not delivered yet — leave refs as-is, do NOT invent wrappers.
   - Anything the user flagged as "следующий этап" / "не ищи сейчас".
5. **Decide if new scripts are warranted.** Only create new scripts when a real new capability is added or the existing scripts can't express a needed transformation. The user said "Если нужно, создавай новые скрипты" — that's a permission, not a mandate. Empty wrappers or stub scripts are noise.
6. **Rewrite to V0(N+1).** Save next to the source with the same prefix and bumped version. Use `write_file` with the full optimized content. Keep a change history block at the bottom with a per-version diff table (what / where / why).
7. **Report.** Send the new file via `MEDIA:`. Include in chat: small audit table (categories → count), `+/-/lines` summary vs. prior version, and an explicit statement about whether new scripts were created (so the user doesn't expect an archive). If scripts *were* created, package them as `tar.gz` (preferred — `tar` is universally available; `rar` usually is not) with the future `skills/<name>/scripts/` directory layout, or as `zip` if that's what the user supplies.

## Output Contract

- One new draft file with version bumped in frontmatter and a populated change history.
- Chat report with audit summary, line/byte delta, and MEDIA: link to the new file.
- Optional archive attachment if new scripts were created.

## Common Pitfalls

1. **Installing the skill instead of producing a draft.** The user said "не создавай" — respect that. The optimized file goes next to the source (`cache/documents/...` or wherever the source lives), NOT into `~/.hermes/skills/<name>/`.
2. **Collapsing user-specified structure.** If the user said "каждый раздел = A / B / C / D", keep A/B/C/D literally in every section. Optimize prose inside each subsection; do not merge or rename.
3. **Inventing scripts to "fill" `scripts/`.** Empty wrappers are noise. Only create scripts when a real new capability is added.
4. **Treating audit as creation.** Audit produces a draft document. Creation is the next phase, gated by user approval.
5. **Skipping the placeholder cross-check.** A draft with `{r[N].nmb}` in the wrong column is broken — the audit table must include this category even if the placeholder list looks long.
6. **Putting "Шаблоны в templates/" in every section.** Reference once in Overview. Cross-section repetition is sediment.
7. **Hardcoding thresholds in body text.** If the user prefers `*-thresholds.py` parameter files, follow that. Note hardcoded values explicitly in the audit table so the user can decide.

## Verification Checklist

- [ ] Source draft read end-to-end before any edit
- [ ] Audit table covers typos, version drift, frontmatter hygiene, placeholders, numbering, logic, terminology, hardcoded thresholds, repeated boilerplate
- [ ] Untouched items listed explicitly (user structure, future-phase scripts, deferred content)
- [ ] New scripts created only if real new capability is added — counted and reported
- [ ] New file written next to source with version bumped and change history populated
- [ ] Chat report includes audit summary, line/byte delta, MEDIA: link
- [ ] Archive included only if new scripts were actually created
