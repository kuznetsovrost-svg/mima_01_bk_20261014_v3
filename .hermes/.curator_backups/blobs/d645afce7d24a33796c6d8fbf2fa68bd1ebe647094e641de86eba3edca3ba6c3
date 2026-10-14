# Hermes install layout on this host (twc1.net, 2026-06-15)

Concrete paths and binaries as they exist on this machine. Use this
to skip the "where is the source?" guessing step.

## TL;DR paths

| Thing | Path |
|-------|------|
| `hermes` binary (wrapper) | `/usr/local/bin/hermes` |
| `hermes` real entry point | `/usr/local/lib/hermes-agent/venv/bin/hermes` |
| **Hermes source root** | `/usr/local/lib/hermes-agent/` |
| Hermes package dirs | `/usr/local/lib/hermes-agent/{agent,cli,cron,gateway,hermes_cli,hermes_state,hermes_logging,...}/` |
| venv for hermes | `/usr/local/lib/hermes-agent/venv/` |
| venv python | `/usr/local/lib/hermes-agent/venv/bin/python` |
| editable-install finder (cache) | `~/.cache/uv/sdists-v9/editable/<hash>/<pkg>-<ver>-0.editable-py3-none-any/__editable___<pkg>_<ver>_finder.py` |
| editable-install archive-info (cache) | `~/.cache/uv/archive-v0/<id>/<pkg>-<ver>.dist-info/` |
| `HERMES_HOME` (this profile) | `/root/.hermes/` |
| Active profile marker | `~/.hermes/active_profile` (empty ⇒ default) |
| State DB (sessions + FTS5) | `~/.hermes/state.db` |
| Flat memory files | `~/.hermes/memories/MEMORY.md`, `~/.hermes/memories/USER.md` |
| Agent self-model | `~/.hermes/SOUL.md` |
| Config | `~/.hermes/config.yaml` |
| Secrets | `~/.hermes/.env` |
| Auth pool | `~/.hermes/auth.json` |
| Gateway logs | `~/.hermes/logs/gateway.log` |
| Skill tree | `~/.hermes/skills/` |
| Profiles root | `~/.hermes/profiles/` |

## Per-profile layout (verified 2026-07-02 on this host)

Each named profile `~/.hermes/profiles/<name>/` mirrors the top-level
shape but is **strictly isolated** by `set_hermes_home_override()`:

```
~/.hermes/profiles/<name>/
├── SOUL.md                    # persona (~ 513 bytes default template)
├── .env                       # secrets (mode 600)
├── config.yaml                # gateway/model/toolsets/messaging
├── profile.yaml               # metadata (created, distribution)
├── distribution.yaml          # if imported from a bundle
├── state.db                   # SQLite - sessions + FTS5
├── gateway.pid                # runtime: active gateway PID
├── gateway_state.json         # runtime: connection state JSON
├── gateway.lock               # runtime: lock during start/stop
├── channel_directory.json     # list of known chats/threads
├── memories/
│   ├── MEMORY.md              # facts about the world (memory)
│   └── USER.md                # facts about the user
├── skills/                    # per-profile skill tree; see (1)
├── cron/                      # cron jobs (per-profile)
├── hooks/                     # pre/post tool hooks
├── sessions/<id>/             # individual chat transcript
├── logs/                      # gateway + operation logs
├── sandboxes/singularity/     # sandbox dirs (Singularity here)
├── home/                      # HOME for sandbox envs
├── plans/                     # task plans / journals
├── workspace/                 # agent's per-profile working dir
│   ├── inbox/<task-id>/       # current task inputs
│   ├── results/<task-id>/     # current task outputs
│   ├── references/            # task-independent reference docs
│   └── templates/             # boilerplate (task-template, etc.)
├── image_cache/, audio_cache/
├── pairing/
├── skins/
└── bin/                       # local wrappers
```

**Three levels that matter for isolation:**

1. **Skill isolation**: bundled skills live in `~/.hermes/skills/`;
   per-profile skills live in `~/.hermes/profiles/<name>/skills/`.
   On a `set_hermes_home_override(profile_dir)` call, `SKILLS_DIR`
   is **rewritten to per-profile**, so most skill operations do not
   see bundled at all unless the per-profile path is empty/missing.
   Verify with: `hermes --profile=<name> skills list`.

2. **Memory isolation**: built-in memory files live in
   `~/.hermes/profiles/<name>/memories/{MEMORY.md,USER.md}` (under
   the profile, not at `~/.hermes/memories/`). `set_hermes_home_override`
   also redirects these. Use `memory write --target=user|memory`
   for clean targeted writes; direct `read_file/patch/write_file`
   on these paths is **blocked** by a separate file-write gate
   (worth pairing with the `messaging-gateway-setup` skill, "Pitfalls §12",
   which describes the same gate from the gateway-setup perspective).

3. **Gateway/run-agent isolation**: a user-level systemd
   `hermes-gateway.service` can only manage one gateway at a time
   per profile. Different profiles get different `WorkingDirectory`
   and run as separate processes (`ps -ef` will show two
   `hermes_cli.main gateway run` entries for two active profiles).
   Cannot share a Telegram/Matrix bot token between profiles —
   long-poll conflict (one bot = one gateway only).

**What gets cloned with `--clone` (verified in
`hermes_cli/profiles.py:_CLONE_SUBDIR_FILES`):**

- `SOUL.md`
- `memories/MEMORY.md`
- `memories/USER.md`

**NOT cloned (treated as regenerable or runtime):**

- `state.db`, `gateway.*`, `processes.json` (runtime)
- `logs/`, `workspace/`, `home/`, `plans/` (regenerated by usage)
- `skills/`, `cron/`, `hooks/` (configured per profile)
- `sessions/` (session-history specific to source)

**What `hermes profile create <name>` does (vs `--clone`):**

- Creates the directory layout above (empty).
- Optionally creates wrapper script at `/root/.local/bin/<name>`
  (PATH advice: `export PATH="$HOME/.local/bin:$PATH"` to use it).
- Reads `profile.yaml`, applies `disabled_skills` if requested.
- Does NOT populate anything by default — fill in yourself.

## What `which hermes` actually points to

```bash
$ which hermes
/usr/local/bin/hermes
$ cat /usr/local/bin/hermes
#!/usr/bin/env bash
unset PYTHONPATH
unset PYTHONHOME
exec "/usr/local/lib/hermes-agent/venv/bin/hermes" "$@"
```

So `/usr/local/bin/hermes` is a 6-line bash shim. It unsets PYTHONPATH
and PYTHONHOME (so the inner venv sees a clean env) and execs the real
binary at `/usr/local/lib/hermes-agent/venv/bin/hermes`. That binary is
a console-script entry point generated by the editable install.

## The editable-install mapping (authoritative directory list)

```bash
F=$(find ~/.cache/uv -name '__editable___hermes_agent*finder.py' 2>/dev/null | head -1)
sed -n 's/^MAPPING:.*//;/^MAPPING = {/,/^}/p' "$F" | head -50
```

Produces something like (paraphrased; full list is in the file):

```
MAPPING = {
    'agent':                '/usr/local/lib/hermes-agent/agent',
    'cli':                  '/usr/local/lib/hermes-agent/cli',
    'cron':                 '/usr/local/lib/hermes-agent/cron',
    'gateway':              '/usr/local/lib/hermes-agent/gateway',
    'hermes_cli':           '/usr/local/lib/hermes-agent/hermes_cli',
    'hermes_state':         '/usr/local/lib/hermes-agent/hermes_state',
    'hermes_logging':       '/usr/local/lib/hermes-agent/hermes_logging',
    'mcp_serve':            '/usr/local/lib/hermes-agent/mcp_serve',
    'model_tools':          '/usr/local/lib/hermes-agent/model_tools',
    'plugins':              '/usr/local/lib/hermes-agent/plugins',
    'providers':            '/usr/local/lib/hermes-agent/providers',
    'run_agent':            '/usr/local/lib/hermes-agent/run_agent',
    'tools':                '/usr/local/lib/hermes-agent/tools',
    'toolsets':             '/usr/local/lib/hermes-agent/toolsets',
    'trajectory_compressor':'/usr/local/lib/hermes-agent/trajectory_compressor',
    'tui_gateway':          '/usr/local/lib/hermes-agent/tui_gateway',
    'utils':                '/usr/local/lib/hermes-agent/utils',
    'acp_adapter':          '/usr/local/lib/hermes-agent/acp_adapter',
    'batch_runner':         '/usr/local/lib/hermes-agent/batch_runner',
    'hermes_bootstrap':     '/usr/local/lib/hermes-agent/hermes_bootstrap',
    'hermes_constants':     '/usr/local/lib/hermes-agent/hermes_constants',
    'hermes_time':          '/usr/local/lib/hermes-agent/hermes_time',
    'plugin_utils':         '/usr/local/lib/hermes-agent/plugins/plugin_utils',
    'toolset_distributions':'/usr/local/lib/hermes-agent/toolset_distributions',
}
```

That's the directory map to use when grepping the source.

## What is NOT at `/root/.hermes/`

The bundled `hermes-agent` skill's "Key Paths" table says
`Source code: ~/.hermes/hermes-agent/`. That is **only** true for
git-clone installs. On this host:

```bash
$ ls -la /root/.hermes/hermes-agent/
ls: cannot access '/root/.hermes/hermes-agent/': No such file or directory
```

So don't follow that hint without verifying. The real source is
`/usr/local/lib/hermes-agent/` (and `~/.hermes/` holds config, state,
logs, skills, profiles, secrets — not source).

## Pitfalls on this host

- **No `sqlite3` CLI.** Use `python3 -c "import sqlite3; ..."` for schema
  inspection. Even so, reading `~/.hermes/state.db` directly is blocked
  by a user-consent gate ("agent cannot touch security-sensitive
  configuration / state") — explain what you want to look up and ask
  first.
- **No `gh` CLI by default.** This session installed it via
  `apt-get install -y gh` (Ubuntu 24.04, package `gh` 2.45.0-1ubuntu0.3,
  available in `noble-updates/universe`).
- **No vector libraries in the hermes venv.** `pip list | grep -iE
  'numpy|faiss|chroma|qdrant|sqlite-vec|rank_bm25|honcho|mem0|...'` →
  empty. If a memory-provider feature needs one, install it explicitly.
- **`python3 -c "import hermes_agent"` fails** (the wrapper unsets
  PYTHONPATH and execs the venv binary, so the system python can't
  find the package). Use the venv python directly when import is
  needed.
- **`gh` ≥ 2.40 requires auth for ALL calls** (including anonymous
  public-API ones). On this host, `gh api /users/<name>` returns
  "To get started with GitHub CLI, please run gh auth login" until
  you `gh auth login` or set `GH_TOKEN`. `gh auth login --web` uses
  the device-flow code shown in the terminal — confirm in browser,
  gh saves the token to `~/.config/gh/hosts.yml` automatically.
- **Git config rewrite on this host**: `git config url.git@github.com:
  .insteadof https://github.com/` silently redirects HTTPS clones to
  SSH. So `git clone https://github.com/<owner>/<repo>.git` works
  because the SSH key is already authorized, but error messages
  mentioning "Permission denied (publickey)" without an HTTPS URL
  in the command are a clue that someone is rewriting the URL.
- **Global git identity on this host**: `user.name=kuznetsovrost-svg`,
  `user.email=kuznetsov.rost@gmail.com` (the real address, not the
  GitHub noreply form — so commits are not email-private by default).
- **Matrix room layout**: 5 listed "rostislav_k / topic $..." targets
  in `send_message list` are all the SAME room
  `!OwBtrzzKTGFSNSmvQU:msg.lab.aidemo.adaptivepm.ru` with different
  `thread_id`s. User preference (from USER.md): send to the ROOM
  (`matrix:!OwBtrzzKTGFSNSmvQU:msg.lab.aidemo.adaptivepm.ru`), NOT
  to a thread. `~/.hermes/matrix_threads.json` is the full thread
  list if you need it.
- **Token redaction in payloads**: Hermes sanitizes runs of 3+ `*`
  in `write_file` / `terminal` / `execute_code` payloads (and bash
  argv). Symptom: `Authorization: Bearer ***` instead of the real
  token. Workaround for authed API calls: pass tokens via env vars
  or read from a chmod-600 file. Never paste tokens into chat or
  inline f-strings.
- **Bundled `~/.hermes/node/` is a Node.js binary distribution** (not
  Hermes code). `~/.hermes/node/include/node/openssl/archs/*/crypto/
  buildinf.h` is tens of thousands of irrelevant `crypto/buildinf.h`
  lines. Exclude when grepping.
- **Per-profile file-gate**: trying to write to `~/.hermes/profiles/<name>/{SOUL.md,memories/MEMORY.md,memories/USER.md}` via `write_file`/`patch` produces `Write denied: '/root/.hermes/profiles/<name>/<file>' is a protected system/credential file.` Verify the right exit path by reading this file before editing. The agent's sanctioned paths are the `memory` tool, the dashboard editor, or `terminal('sed -i.bak …')` after explicit consent.
