# Task-driven workflow: executing a user-supplied TASK spec

## When this applies

The user pastes a Markdown file (commonly named `TASK-YYYY-MM-DD-<slug>.md`) whose structure includes:

- `## Inputs` — a list of source files (in `Inputs/`).
- `## Outputs` — a list of destination paths (in `Outputs/results/<task-id>/`).
- `## Acceptance Criteria` — checkbox list.
- `## Constraints` — budget, wall-clock, sensitive data notes.
- `## Status Log` — running history of agent actions.

…and then says something like "запусти задачу" / "execute the task" / "go". The agent must read the spec, run a domain skill (e.g. `vuz-prof-ba-anl`) per input, write each output, and close `progress.json` + `plans/<task>.md` on completion.

This file describes the workflow that sits ON TOP of the per-file ingest rules in `SKILL.md` and a domain skill.

## Pre-flight: validate before running

Before dispatching any per-file work, run the acceptance preflight:

1. **Names match the FS.** Each `Inputs` filename in the spec must exist in `Inputs/`. Filenames can drift (the user or a prior session may have used `_` instead of spaces, or spaces). Either resolve and reconcile silently, or — if the mismatch is substantive — ask the user before proceeding.
2. **Output paths are creatable.** For each output, the parent directory must be writable. If the spec says `Outputs/results/TASK-XXX/SANL_*.md`, create the nested directory before the first write. Don't flatten "for simplicity" — that breaks acceptance.
3. **`progress.json` is in draft.** If `overall.state != "draft"` and `per_file_status[<file>].state in {"done", "in_progress"}`, the task has been partially executed. Decide whether to resume from `pending` files or restart. Do not silently overwrite a `done` entry's `finished_at` / `report_path`.
4. **Acceptance Criteria are checkable.** Each `- [ ]` should map to an observable artifact. If a criterion says "Style: Russian, professional" — that's a judgment call, not a checkbox; flag it.
5. **Budget is realistic.** The user often quotes an aspirational budget (e.g. "<3000 tokens"). Compare to: domain skill rules (does it demand web verification?), output count, links-per-claim. If the budget is clearly fiction, raise it BEFORE running — not after.

## Per-file loop

For each file in `Inputs`, in the order the spec dictates:

```
for f in spec.inputs:
    update progress.json: per_file_status[f].state = "in_progress"
    update progress.json: per_file_status[f].started_at = <ISO timestamp>

    read f
    apply domain skill to f  # e.g. skill_view("vuz-prof-ba-anl"); follow its Procedure
    write spec.outputs[i]   # exactly the path the spec names, not a flattened variant

    update progress.json: per_file_status[f].state = "done"
    update progress.json: per_file_status[f].finished_at = <ISO timestamp>
    update progress.json: per_file_status[f].report_path = spec.outputs[i]
```

**Critical: do not blend files.** A common failure mode is to read all inputs first, then write outputs that reference facts from other files. The skill spec says "не смешивай результаты анализа одного файла с другим" — take it literally. Reset the context per file if the skill demands it.

**Critical: independent runs.** Treat each file as if the previous one never happened. If you remember a fact from input 1 when writing output 2, that's contamination. Re-read input 2 and start fresh.

## When the domain skill demands verification you can't do

A domain skill may require, for example, "2-3 working links per claim, verified". If web tools (`browser_navigate`, `web_search`) are unavailable in the current session, you have three honest options:

1. **Stop and ask the user.** State plainly: "skill demands verified links; web is unavailable; how do you want to proceed?" Options: skip links, use placeholder links marked `[not verified]`, or run in a session with web access.
2. **Skip the verification gate and mark every link `[not verified]`.** Then call it out loudly in the LQA report so the user knows to re-verify.
3. **Refuse.** Only if the skill is hard-gated on verification — refuse with a clear reason.

What you must NOT do: fabricate URLs that look plausible. A model-trained guess about an arxiv ID or a docs URL is a fabrication, not a verified link. Mark and move on.

## Closing the task

After the per-file loop:

1. `progress.json` overall state → `done`, set `finished_at`.
2. Append to the spec's `## Status Log` a line per file: `agent started HH:MM` / `agent outputs ready HH:MM`. Use actual timestamps; do not invent.
3. Append to `plans/<task-id>.md` a "Статус выполнения" section with checkboxes mirroring the spec's Acceptance Criteria.
4. Report to the user: files written, sizes, total tokens if tracked, plus any deviations from the spec.

## Pitfalls

1. **Running without a preflight.** Always validate before dispatch — name mismatches, partial prior runs, unrealistic budgets surface here, not after 30 minutes of work.
2. **Mixing files' content.** "не смешивай" means literally: re-read each input file before writing its output; do not rely on what you remember from earlier files.
3. **Flattening nested output paths.** `Outputs/results/TASK-XXX/SANL_*.md` is not the same as `Outputs/SANL_*.md`. The spec names those nested dirs for a reason (separation across multiple tasks in one project).
4. **Inventing `[verified]` marks.** If web verification is impossible, every link is `[not verified]`. Tell the user explicitly in the LQA that they must re-verify before publishing.
5. **Skipping the spec's Status Log.** Agents leave the `Status Log` empty "because it's not strictly an artifact." The user reads it. Fill it.
6. **Treating acceptance criteria as a hint.** Each `- [ ]` in the spec is something the user expects to be true. If you can't satisfy one, leave it `- [ ]` and report why — don't check it off.
7. **Writing outputs before reading inputs.** Tempting on a long task to start writing the first output while still reading the last input. Read all inputs first, then run the loop. Avoids blending.