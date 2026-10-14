---
name: skill-driven-batch-task
description: "Use when the user wants the same skill applied independently to N input files, with per-file output, progress tracking, and no cross-contamination. Drives a per-file loop: mark in_progress → invoke skill → write output → mark done. Builds the supporting project scaffolding (Inputs/Outputs/tasks/progress.json/plan) before the loop starts."
version: 1.0.0
author: Hermes Agent + Rostislav Kuznetsov
license: MIT
metadata:
  hermes:
    tags: [batch, workflow, task-runner, skill-orchestration, progress-tracking, projects]
    category: productivity
    related_skills: [telegram-file-delivery]
---

# Skill-Driven Batch Task

## Overview

When a user wants the **same skill applied to N input files independently** (e.g. analyze 5 university programs with `vuz-prof-ba-anl`, score 20 CVs with `resume-screen`, translate 10 documents with `doc-translate`), they want:

1. A reproducible project scaffolding on disk (Inputs/Outputs/tasks/progress.json/plan).
2. Per-file isolation — no cross-contamination of context, results, or naming.
3. Status that survives a session crash (so the next session can resume).
4. A clear acceptance criteria checklist.
5. Delivery of all outputs at the end — bundled into a zip when N is large (see `telegram-file-delivery`).

This skill codifies the workflow. It is **meta** — it does not do the per-file work itself; it loads the user's chosen skill per file and writes outputs.

## When to Use

- The user posts a task file with `## Inputs` listing N file paths and `## Outputs` listing N output paths.
- The user names a specific skill to apply ("use `vuz-prof-ba-anl`", "apply `resume-screen` to each").
- The user wants sequential, independent processing — not parallel multi-agent work (use `delegate_task` for that).
- The outputs follow a per-file naming convention (`SANL_*.md`, `OUT_*.md`, etc.).

**Don't use for:**
- Single-file analysis (no batching needed; just invoke the skill).
- Cross-file reasoning where later files depend on earlier outputs (that's a pipeline, not a batch).
- Work the user wants done in parallel by subagents (use `delegate_task`).

## Procedure

### Phase 1: Validate Inputs and Skill

1. Read the task file.
2. For each path in `## Inputs`, confirm the file exists at the absolute path. If any are missing, stop and ask the user — do not proceed with a partial set.
3. Confirm the named skill exists in the active profile's `skills/<category>/<name>/SKILL.md`. Load it via `skill_view` so you understand its procedure.
4. Count N. If N=1, this skill is overkill — just run the inner skill directly.

### Phase 2: Build Project Scaffolding

Create the following layout under the project root (the project's `primary_path` if it has one, else `projects/<project_slug>/`):

```
<project_root>/
├── README.md                 (project description + structure map)
├── Inputs/                   (copies of source files, with consistent naming)
│   ├── file1.md
│   ├── file2.md
│   └── ...
├── Outputs/
│   └── results/<TASK-ID>/    (per-task output bucket)
│       ├── OUT_file1.md      (created later)
│       └── ...
├── tasks/
│   └── <TASK-ID>.md          (copy of the task spec)
└── progress.json             (state machine for the batch)
```

For each input file in the task spec:
- If the source filename uses spaces and the project's convention is underscores (or vice-versa), **normalize to one convention** and use the same convention in the `progress.json` `inputs`/`outputs` lists.
- Update the task file's `## Inputs` and `## Outputs` sections to match the normalized names so downstream agents and the user agree.

### Phase 3: Write progress.json

```json
{
  "task_id": "<TASK-ID>",
  "title": "<task title>",
  "profile": "<active profile>",
  "project_id": "<id>",
  "project_slug": "<slug>",
  "state": "draft",
  "created": "<YYYY-MM-DD>",
  "updated": "<YYYY-MM-DD>",
  "author": "<user>",
  "skill": "<the per-file skill>",
  "inputs": ["file1.md", "file2.md", ...],
  "outputs": ["results/<TASK-ID>/OUT_file1.md", ...],
  "per_file_status": {
    "file1.md": {"state": "pending", "started_at": null, "finished_at": null, "report_path": null},
    ...
  },
  "overall": {"state": "draft", "started_at": null, "finished_at": null},
  "token_budget_estimate": <int>,
  "wall_clock_budget_seconds": <int>
}
```

Tune `token_budget_estimate` realistically: for a 10-section analytical report with ~150 cited links, ~20k tokens per file is typical. A budget of 3000 tokens for N=5 reports is a 5x underestimate — surface this to the user before launching.

### Phase 4: Write Plan

Create `plans/<TASK-ID>.md` with:
- Goal (1-2 lines).
- Step-by-step procedure (one bullet per file + "after all files" + "stop conditions").
- Risks section (token overage, cross-contamination, low-quality links).
- Status log block (start empty; fill in timestamps as you go).

### Phase 5: The Loop

For each file (sequential, **not parallel** — the user explicitly wants independence):

1. **Mark in_progress** in `progress.json`:
   - `per_file_status[<file>].state = "in_progress"`
   - `per_file_status[<file>].started_at = "<ISO timestamp>"`
   - `overall.state = "in_progress"`
   - `overall.started_at = "<ISO timestamp>"` (first time only)
   - Write the file.

2. **Read the input file in full** (don't skim). Re-load the per-file skill via `skill_view` if it's been a while since the start of the session — the procedure may have evolved in your head.

3. **Invoke the per-file skill mentally** — follow its procedure exactly. Do NOT skip steps even if they seem repetitive across files; per-file isolation is the whole point.

4. **Write the output** to the exact path recorded in `progress.json.outputs[i]`. Use the format the per-file skill specifies.

5. **Mark done** in `progress.json`:
   - `per_file_status[<file>].state = "done"`
   - `per_file_status[<file>].finished_at = "<ISO timestamp>"`
   - `per_file_status[<file>].report_path = <output path>`
   - Write the file.

6. **Reset context before the next file.** Don't carry forward reasoning from file N to file N+1. If you find yourself saying "and as we saw in the previous file..." — stop, you're cross-contaminating.

### Phase 6: Finalize

After all N files are done:
1. Set `overall.state = "done"`, `overall.finished_at`.
2. Update `plans/<TASK-ID>.md` status log with completion time and a one-line summary.
3. Update `projects/<slug>/README.md` if it lists tasks.
4. Compose the final report to the user (see `telegram-file-delivery` for how to ship N outputs).

### Phase 7: Deliver

For the user-facing summary:
- Confirm each acceptance criterion from the task file as ✅/❌.
- Give a comparative synthesis only if the task explicitly asks for one (most don't — most want per-file independence).
- Bundle N outputs into a zip (or send a summary report as a single file) — do not paste N file contents inline.

## Common Pitfalls

- **Skipping the input-existence check.** "I'll assume the file is there" → mid-loop discovery that file 3 is missing → wasted work on files 1-2.
- **Carrying context across files.** "These programs all seem similar because..." — STOP. Each file is independent.
- **Aspirational budgets.** A 3000-token budget for a 5-file analytical task is fiction. Estimate per-file (20k for a full report) and surface the total before starting.
- **Unverified links silently added.** If the per-file skill calls for citations but you have no web access, mark every link `[не верифицировано]` and tell the user — do not pretend you verified them.
- **Pasting output contents into the chat.** Outputs go to `Outputs/`, not into the chat. The chat gets a summary; the user opens files for details.
- **Resuming after a crash without checking `progress.json`.** Always read `progress.json` first on resume — files in `state="in_progress"` may be half-written.
- **Mixing parallel subagent work with this skill.** This skill is sequential by design. If the user wants parallel speedup, they want `delegate_task`, not this.

## Verification

Before reporting completion:
- [ ] N outputs exist, each at the exact path recorded in `progress.json.outputs`.
- [ ] `progress.json` shows all `per_file_status[*].state == "done"`, all `finished_at` populated.
- [ ] `progress.json.overall.state == "done"`.
- [ ] Plan file's status log has the completion entry.
- [ ] Every acceptance criterion from the task file is closed (✅) or explicitly marked partial with a reason.
- [ ] No two output files share content (independent analysis verification).

## Reference

- Observed pattern: 5 MIREA bachelor programs analyzed via `vuz-prof-ba-anl` in 2026-07-16 by Rostislav K. — produced 5 ~25 KB reports + 1 comparative summary, all under `Outputs/results/TASK-2026-07-15-SPA/`. Total ~128 KB.
- Companion skill for shipping outputs: `telegram-file-delivery` (handles the zip-bundling rule when N≥2).
- Underlying project DB: `~/.hermes/profiles/<profile>/projects.db` — `projects`, `project_folders`, `project_meta` tables.