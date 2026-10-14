# Hermes-Internals Source Map for Guide Authors

When producing a `<Topic>_NN.txt` guide about a Hermes-internal feature, these are the canonical source paths to grep first. They are persistent across guides — once you have a source map, you have it for the whole series.

## 1. Profile / memory / SOUL system

| Topic | File | What to grep for |
|---|---|---|
| Profile creation / clone | `/usr/local/lib/hermes-agent/hermes_cli/profiles.py` | `_CLONE_SUBDIR`, `_CLONE_ALL_STRIP`, `profile create` |
| Memory (MEMORY.md / USER.md) storage paths | `/usr/local/lib/hermes-agent/hermes_cli/doctor.py` | `memories` directory paths |
| SOUL.md slot in prompt | `/usr/local/lib/hermes-agent/hermes_cli/prompt_builder.py` | `load_soul_md`, `build_context_files_prompt` |
| Auto-injection trigger | `/usr/local/lib/hermes-agent/hermes_cli/_parser.py` | `--ignore-rules`, context_files |
| Skill autoloader | `/usr/local/lib/hermes-agent/hermes_cli/skills_hub.py` | `rglob("SKILL.md")`, `entry / "SKILL.md"` |
| Tips shown to user | `/usr/local/lib/hermes-agent/hermes_cli/tips.py` | "context files", "SOUL.md", "AGENTS.md" |

## 2. AGENTS.md / context files

| Topic | File | What to grep for |
|---|---|---|
| Priority chain | `/usr/local/lib/hermes-agent/hermes_cli/tips.py` (line ~219) | `.hermes.md, AGENTS.md, CLAUDE.md, .cursorrules` |
| Env override | `/usr/local/lib/hermes-agent/website/docs/reference/environment-variables.md` | `HERMES_MD_NAMES` |
| Per-session injection | `/usr/local/lib/hermes-agent/hermes_cli/_parser.py` (lines ~214, 374) | `--ignore-rules`, `--safe-mode` |
| Prompt assembly | `/usr/local/lib/hermes-agent/website/docs/developer-guide/prompt-assembly.md` | `skip_soul`, identity slot |
| In-repo example | `/usr/local/lib/hermes-agent/AGENTS.md` | "Hermes Agent - Development Guide" |

## 3. Skills

| Topic | File | What to grep for |
|---|---|---|
| Skill loader | `/usr/local/lib/hermes-agent/hermes_cli/skills_hub.py` | `rglob("SKILL.md")`, `path / "SKILL.md"` |
| Bundled skill discovery | `/usr/local/lib/hermes-agent/hermes_cli/profile_distribution.py` (~line 483) | `rglob("SKILL.md")`, `is_excluded_skill_path` |
| Plugin skill paths | `/usr/local/lib/hermes-agent/hermes_cli/plugins.py` (~lines 1180, 1962) | `SKILL.md not found`, plugin SKILL.md path |
| Authoring validator | `/usr/local/lib/hermes-agent/tools/skill_manager_tool.py` | `_validate_frontmatter`, `MAX_SKILL_CONTENT_CHARS=100000`, `MAX_DESCRIPTION_LENGTH=1024` |

## 4. Projects

| Topic | File | What to grep for |
|---|---|---|
| Project model | `/usr/local/lib/hermes-agent/hermes_cli/projects_db.py` | `class Project`, `create_project`, `branch_name_for` |
| Project CLI | `/usr/local/lib/hermes-agent/hermes_cli/projects_cmd.py` | `_cmd_create`, `_cmd_list`, `_cmd_show`, `_cmd_bind_board` |
| Project → kanban integration | `/usr/local/lib/hermes-agent/hermes_cli/kanban.py` (line 321) | branch naming convention |

## 5. Gateway / messaging

| Topic | File | What to grep for |
|---|---|---|
| Gateway CLI | `/usr/local/lib/hermes-agent/hermes_cli/gateway.py` | long-poll, polling conflict |
| Logger / state | `/usr/local/lib/hermes-agent/hermes_cli/gateway_state.json` | runtime state (in `~/.hermes/`) |
| Web server memory reset | `/usr/local/lib/hermes-agent/hermes_cli/web_server.py` (~line 9760) | `MEMORY.md`, `USER.md` |

## 6. Cron / scheduled jobs

| Topic | File | What to grep for |
|---|---|---|
| Cron subcommands | `/usr/local/lib/hermes-agent/hermes_cli/subcommands/cron.py` | `--workdir`, "Injects AGENTS.md / CLAUDE.md" |

## 7. Docs (for citing official behavior)

All inside the install:
```
/usr/local/lib/hermes-agent/website/docs/
├── user-guide/features/
│   ├── personality.md          # SOUL.md vs AGENTS.md
│   ├── context-files.md        # auto-injection
│   └── hooks.md                # pre/post-tool events
├── developer-guide/
│   └── prompt-assembly.md      # system-prompt construction
├── reference/
│   ├── environment-variables.md  # HERMES_MD_NAMES, etc.
│   └── cli-commands.md         # all CLI flags
└── faq.md
```

## 8. Reusable grep recipes

```bash
# Where is a function called from?
grep -rn "function_name" /usr/local/lib/hermes-agent/hermes_cli/ | head -5

# What does the official doc say about X?
grep -rE "X|term" /usr/local/lib/hermes-agent/website/docs/ | head -10

# What does this CLI command really do?
PYTHONPATH=/usr/local/lib/hermes-agent /usr/local/lib/hermes-agent/venv/bin/python \
  -m hermes_cli.main X --help 2>&1 | head -30

# What DBs and config live in a profile?
ls ~/.hermes/profiles/<name>/
sqlite3 ~/.hermes/profiles/<name>/projects.db ".tables"
```

## 9. Quick reference: paths inside `~/.hermes/profiles/<name>/`

These paths are referenced across multiple guides — make sure each one cites the canonical layout, not a guess:

- `SOUL.md` (in profile root, NOT in `memories/`)
- `memories/MEMORY.md`
- `memories/USER.md`
- `skills/<name>/SKILL.md`
- `projects.db` (SQLite)
- `kanban/*.db`
- `workspace/{inbox,results,references}/`
- `plans/<task-id>.md`
- `cron/*.json`
- `state.db`
- `config.yaml`, `.env`, `profile.yaml`
- `logs/{gateway,errors,...}.log`
- `hooks/<name>.py`
- `memories/`, `sessions/`, `skills/`, `sandboxes/`, `skins/`, `bin/`

For default profile, drop the `profiles/<name>/` segment — it lives directly in `~/.hermes/`.

## 10. Line numbers pinned (don't re-grep every time)

Confirmed during the Jul-2026 guides:

- `tips.py:212` — prompt-injection scanning
- `tips.py:219` — context-file priority chain
- `tips.py:220` — subdirectory progressive discovery
- `tips.py:223` — 20,000-char cap on context files
- `tips.py:326` — .cursorrules auto-detect
- `tips.py:393` — HERMES_IGNORE_RULES
- `_parser.py:214` — `--ignore-rules` CLI help
- `_parser.py:221` — `--safe-mode` CLI help
- `_parser.py:374` — `--ignore-rules` argparse
- `_parser.py:381` — `--safe-mode` argparse
- `oneshot.py:8-10` — context rules & CWD handling for one-shot mode
- `config.py:1263` — list of context-file names (first match)
- `kanban_db.py:7720` — workspace's AGENTS.md lookup
- `web_server.py:9760` — `MEMORY.md` reset target
- `web_server.py:9762` — `USER.md` reset target
- `profile_distribution.py:483` — SKILL.md walker
- `profile_distribution.py:602` — list of regenerable directories (plans, workspace, cron, home)
- `projects_db.py:236-265` — `Project` dataclass fields
- `projects_db.py:322-389` — `create_project` signature
- `projects_db.py:714` — `branch_name_for` (deterministic branch name shape)
- `claw.py:635-651` — sandbox TODO/SOUL/MEMORY/USER file detection
- `main.py:2348` — `--ignore-rules` early-skip
- `environment-variables.md:718,720` — `HERMES_IGNORE_RULES`, `HERMES_MD_NAMES`
- `personality.md:80-160` — SOUL.md vs AGENTS.md (full canonical write-up)

## 11. Catalogue of every context file (the .MD names)

When authoring a guide about "what `.md` files does Hermes care about", the four canonical filenames Hermes actually reads are:

- `SOUL.md`    → `~/.hermes/profiles/<name>/SOUL.md`              (slot #1 of system prompt)
- `MEMORY.md`  → `~/.hermes/profiles/<name>/memories/MEMORY.md`
- `USER.md`    → `~/.hermes/profiles/<name>/memories/USER.md`
- `SKILL.md`   → `~/.hermes/profiles/<name>/skills/<name>/SKILL.md` (and global `~/.hermes/skills/`)

Plus the cwd-discovered project-context chain (`HERMES_MD_NAMES`):
`.hermes.md` → `AGENTS.md` → `CLAUDE.md` → `.cursorrules`.

Hardcoded references in source (verified on this install):
- `web_server.py:9760` reads `MEMORY.md` for reset
- `web_server.py:9762` reads `USER.md` for reset
- `skills_hub.py:194, 201` walks `rglob("SKILL.md")`
- `claw.py:635-651` recognises sandbox `todo.json`, `SOUL.md`, `MEMORY.md`, `USER.md`

These canonical paths are NOT made up — they are extracted from
the running install. Cite them with line numbers in guides.

Note: `TASKS.md` is **not** a built-in Hermes file. The user's
codebase uses it as a convention. If asked to describe it, the
honest framing is "open-source convention, not Hermes feature".

## 12. Task data layout for `inbox/<TASK-ID>/`

When a guide covers task.md and where its data lives:

- `~/.hermes/profiles/<name>/workspace/inbox/<TASK-ID>/task.md`           ← prompt
- `~/.hermes/profiles/<name>/workspace/inbox/<TASK-ID>/progress.json`     ← machine state
- `~/.hermes/profiles/<name>/workspace/inbox/<TASK-ID>/inputs/`           ← input data
- `~/.hermes/profiles/<name>/workspace/results/<TASK-ID>/`                ← outputs
- `~/.hermes/profiles/<name>/plans/<TASK-ID>.md`                         ← journal

Verified in the Hermes source by `profile_distribution.py:602`
(`plans`, `workspace`, `cron`, `home` listed as regenerable
profile directories).

## 13. Profile inventory snapshot

When the user asks for a "show the contents of profile X as a tree":
use `apt-get install -y tree` if missing, then:

```bash
PROFILE="/root/.hermes/profiles/<name>"
tree -a -L 6 --dirsfirst -h "$PROFILE" > /tmp/snapshot.txt
```

Output should report: total size, file count, SKILL.md count per
category, top-5 largest SKILL.md. Compare three profiles
(default, analyst_training, mi_mg_01) to add dimension.
