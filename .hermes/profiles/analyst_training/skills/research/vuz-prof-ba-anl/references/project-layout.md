# Project Layout (Inputs/Outputs) for vuz-prof-ba-anl

Canonical directory structure for any project that runs this skill.

## Layout

```
<profile_dir>/projects/<project-slug>/
├── README.md                       # one-line description, project ID, skill pointers
├── Inputs/
│   ├── <program-file-1>.md         # source program description (UTF-8, .md/.pdf/.docx/.txt)
│   ├── <program-file-2>.md
│   └── ...
└── Outputs/
    ├── <program-file-1>-report.md  # report named to match the input
    ├── <program-file-2>-report.md
    └── ...
```

File names must preserve the **original Cyrillic / Unicode characters** of the source — do NOT transliterate to ASCII. The `Outputs/` filename mirrors the input filename with a `-report.md` suffix (per the SKILL's Verification §1).

## projects.db Schema (SQLite)

For each project, set BOTH:

1. `projects.primary_path` — absolute path to the project root
2. `project_folders` row — same path, `is_primary = 1`

```python
import sqlite3, time
db = "<profile_dir>/projects.db"
conn = sqlite3.connect(db); cur = conn.cursor()
root = "<profile_dir>/projects/<slug>"
cur.execute("UPDATE projects SET primary_path=? WHERE id=?", (root, project_id))
cur.execute("""INSERT INTO project_folders (project_id, path, label, is_primary, added_at)
               VALUES (?, ?, ?, ?, ?)""",
            (project_id, root, "project root", 1, int(time.time())))
conn.commit()
```

`project_meta.active_id` points to the active project ID (not slug) — no need to touch it for layout setup.

## Inputs/Outputs pairing rule

When the skill runs against an input file, it must produce ONE output file per input file, with the same base name + `-report.md` suffix. Never overwrite an existing output — if one already exists, append a numeric suffix (`-report-2.md`) or refuse and ask.

## Activating a project

If `projects.db` has multiple projects, set `project_meta.active_id` to the chosen project's ID before running the skill. The skill reads active_id to resolve `Inputs/` and `Outputs/` paths.

## Reference: example projects.db state for academic-course-anl-01

```sql
-- projects table
('p_ceebe9b3', 'academic-course-anl-01', 'academic-course-anl-01', NULL,
 '/root/.hermes/profiles/analyst_training/projects/academic-course-anl-01', 0)

-- project_folders
('p_ceebe9b3', '/root/.hermes/profiles/analyst_training/projects/academic-course-anl-01',
 'project root', 1, 1784196034)

-- project_meta
('active_id', 'p_ceebe9b3')
```