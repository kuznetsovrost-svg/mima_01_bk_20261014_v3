---
name: skill-candidate-review
description: "Use when a user pastes or attaches a candidate SKILL.md (or its draft) and asks for a review, sanity check, or 'is this valid?'. Runs the hermes-agent-skill-authoring validator, surfaces BLOCKER vs WARN vs substance issues, scans body for typos, and produces a structured report — without modifying or creating the skill until the user confirms."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [skills, review, validation, hermes-agent, conventions]
    related_skills: [hermes-agent-skill-authoring, requesting-code-review]
---

# Skill Candidate Review

## Overview

A user hands you a candidate `SKILL.md` — pasted in chat, attached as a file, or referenced by path — and asks "is this valid?" / "check before I commit" / "what would you change?". Your job is to **review, not create**. Read the file, run the same BLOCKER / WARN checks the bundled `hermes-agent-skill-authoring` skill encodes, scan the body for common authoring typos, and deliver a structured report. Do **not** call `skill_manage(action='create')` or write a new SKILL.md until the user explicitly approves the proposed changes.

## When to Use

- User pastes a SKILL.md draft in chat or attaches the file and asks for review.
- User says "check this is valid as a skill", "would this pass the validator?", "what's wrong with this skill?".
- User is iterating on a draft before committing it to `skills/<category>/<name>/`.

## Don't Use For

- **Authoring a skill from a blank page.** That's `hermes-agent-skill-authoring` — it covers the convention checklist and validator-source-truth.
- **Pre-commit code review of a git diff.** That's `requesting-code-review` — different surface, different rubric.
- **One-shot prose feedback on a non-skill document.** Stay in your lane.

## Procedure

1. **Locate the candidate.**
   - If the user pasted the content inline: work from the message body, do not write to disk yet.
   - If the user attached a file: read it with `read_file`. Note the on-disk path — the report file you produce later goes next to it (or wherever the user specifies).
   - If the user referenced a path: `read_file` it. Confirm it parses as text before validating.

2. **Run the bundled skill's checks.** Load `hermes-agent-skill-authoring` if not already loaded — it owns the BLOCKER list (`name` ≤64 chars, `description` ≤1024 chars, frontmatter opens with `---` at byte 0, closes with `\n---\n`, YAML parses, body non-empty, file ≤100k chars). Treat anything the bundled skill calls a hard requirement as **BLOCKER** in your report.

3. **Add the peer-convention WARN layer** that the bundled skill lists as "every peer has it but the validator doesn't enforce":
   - `name` lowercase + hyphens only (no underscores, no uppercase, no acronyms-in-caps).
   - `description` starts with `"Use when <trigger>. <one-line behavior>."`
   - `version`, `author`, `license`, `metadata.hermes.{tags, related_skills}` all present.
   - `tags` are lowercase + hyphens.
   - Body follows `# Title` → `## Overview` → `## When to Use` → body → `## Common Pitfalls` → `## Verification Checklist` (these names exist for a reason — "Pitfalls" without "Common" looks half-finished to a peer-reviewer).

4. **Substance review (one short pass).** Look at the body for things the validator cannot catch:
   - **Completion criteria** on each ordered step ("how does the agent know it's done?" — if a step has no completion check, that's a substance WARN).
   - **No-op prose** ("be careful", "be thorough", "use best practices" with no concrete behavior change).
   - **Triggers vs tasks** — the `When to Use` section should describe a *class* of triggers, not a single task. "Use when debugging X" > "Debug X".
   - **Counter-triggers** ("Don't use for: ...") — peer skills usually have these.

5. **Typo scan.** Use the heuristic list in `references/typo-hints.md`. False positives are fine to flag — the user can dismiss. Russian-speaking authors commonly produce Latin/Cyrillic homoglyphs (`аcademic`, `архитектор → аритектор`), doubled letters (`утвержденние`), and the `"Otp"/"Outputs"` slip. Run a quick line-by-line grep; do not over-engineer.

6. **Cross-reference scan.** If the candidate names other skills in `metadata.hermes.related_skills`, verify they resolve. In-repo skills should reference in-repo skills; user-local references break for other clones.

7. **Produce the report.** Use the format in `references/report-template.md`. Sections:
   1. Verdict (one line: PASS / WARN / BLOCKER)
   2. BLOCKER checklist (each item: [OK] / [FAIL] with reason)
   3. WARN / peer-convention list (numbered W1, W2, ...)
   4. Substance observations (S1, S2, ...)
   5. Typo table (with line numbers)
   6. Final pre-commit checklist (checkboxes the user can tick)

8. **Deliver.** Send the report inline (Telegram/Discord) AND write it to disk if the user named a path. The user said "пришли файл" → write to `<candidate-stem>-rep01.txt` next to the source. If the user only asked for chat feedback, do not create files.

9. **Wait for explicit go-ahead** before any modification. The user may want to revise the draft first, ask for a rewrite, or scrap the candidate. Do not pre-emptively call `skill_manage(action='create')` or `write_file` on `SKILL.md` paths.

## Completion Criteria

You are done when **all** are true:
- [ ] The validator checks ran and each result is reported with severity (BLOCKER / WARN).
- [ ] The substance review covered completion criteria, no-op prose, and triggers.
- [ ] The typo scan ran over the body (line-by-line), not just the frontmatter.
- [ ] The report matches the template structure in `references/report-template.md`.
- [ ] The report was delivered where the user asked (chat, file, or both).
- [ ] No `skill_manage(action='create')` was called.
- [ ] No write to the candidate's source path was made.

## Common Pitfalls

1. **Treating the skill as "create this for me" instead of "review this".** The user's verb matters. "Review / check / validate" → report only. "Create / make / add" → you may proceed to creation after the report.

2. **Skipping the typo scan because the validator passed.** The validator doesn't see body prose. Typos and Cyrillic/Latin homoglyphs in body text break trust but don't fail validation — your report is the only place they get caught.

3. **Calling peer-convention rules "BLOCKER".** Lowercase-only names and "Use when ..." descriptions are peer-convention, not validator-enforced. Mark them WARN — over-blocking will make the user think the file is unloadable when it isn't.

4. **Modifying the source file before the user reads the report.** The user wanted a review. If you silently "fix" the typos, you've taken away their decision.

5. **Writing the report to disk when the user only asked for chat feedback.** Don't create stray files. Match the user's delivery request.

6. **Conflating review with the bundled `hermes-agent-skill-authoring` skill.** That skill owns the *convention checklist* and the *validator source code*. This skill owns the *review workflow* — locating the file, running the checks in the right order, formatting the report, and not over-stepping. They are complementary, not duplicates.

7. **Reporting the absence of a peer-convention field as BLOCKER.** Missing `version` / `author` / `license` / `metadata` is WARN — the file still loads without them.

## Verification Checklist

- [ ] Ran the BLOCKER checks first; reported them in order (file-starts-with, yaml-parses, required-fields, length-limits, body-non-empty, size-limit).
- [ ] Ran the WARN checks next; numbered them (W1, W2, ...) for easy back-and-forth.
- [ ] Did the substance pass; numbered observations (S1, S2, ...).
- [ ] Did the typo scan; presented as a table with line numbers.
- [ ] Final pre-commit checklist included and is actionable (each item maps to a concrete edit).
- [ ] No `skill_manage(create)` or `write_file` to a `SKILL.md` path was issued.
- [ ] Report delivered where the user asked (chat inline, file attachment, or both).

## Related Skills

- `hermes-agent-skill-authoring` — owns the convention checklist, validator source code, and authoring workflow. Load it first to get the BLOCKER list right.
- `requesting-code-review` — pre-commit review of git diffs (different surface, different rubric).