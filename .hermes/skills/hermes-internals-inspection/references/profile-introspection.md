# Hermes Profile Introspection

Code-grounded reference for "what profile is Hermes running under?" / "which
profile is active?" / "how do I find out what a different Hermes process is
configured as?" Updated for hermes_agent 0.16.0.

## TL;DR

1. **`hermes profile list`** — the row marked `◆` is the current (sticky) profile.
2. **`hermes profile show <name>`** — full info on one profile (path, model,
   gateway status, skill count).
3. **`HERMES_HOME`** — the source of truth inside Hermes itself. Path layout
   encodes the profile:
   - `~/.hermes` → profile `"default"`
   - `~/.hermes/profiles/<name>` → profile `<name>`
   - anywhere else → profile `"custom"`
4. **`~/.hermes/active_profile`** — sticky override written by
   `hermes profile use <name>`. Empty/missing ⇒ no override ⇒ default.

## Source-of-truth: `get_active_profile_name()`

`hermes_cli/profiles.py:1285` — the function Hermes actually calls when it
needs to know the current profile name.

```python
def get_active_profile_name() -> str:
    """Infer the current profile name from HERMES_HOME.

    Returns ``"default"`` if HERMES_HOME is not set or points to ``~/.hermes``.
    Returns the profile name if HERMES_HOME points into ``~/.hermes/profiles/<name>``.
    Returns ``"custom"`` if HERMES_HOME is set to an unrecognized path.
    """
    from hermes_constants import get_hermes_home
    hermes_home = get_hermes_home()
    resolved = hermes_home.resolve()

    default_resolved = _get_default_hermes_home().resolve()
    if resolved == default_resolved:
        return "default"

    profiles_root = _get_profiles_root().resolve()
    try:
        rel = resolved.relative_to(profiles_root)
        parts = rel.parts
        if len(parts) == 1 and _PROFILE_ID_RE.match(parts[0]):
            return parts[0]
    except ValueError:
        pass

    return "custom"
```

Key takeaway: **only `HERMES_HOME` matters at runtime.** No config.yaml
setting, no DB column, nothing else. Three branches → three answers.

## The sticky override: `~/.hermes/active_profile`

`hermes_cli/main.py:378–390` — checked BEFORE the env-var lookup at startup:

```python
# 2. If no flag, check active_profile in the hermes root
if profile_name is None:
    try:
        from hermes_constants import get_default_hermes_root
        active_path = get_default_hermes_root() / "active_profile"
        if active_path.exists():
            name = active_path.read_text().strip()
            if name and name != "default":
                profile_name = name
                consume = 0  # don't strip anything from argv
    except (UnicodeDecodeError, OSError):
        pass  # corrupted file, skip
```

So even if `HERMES_HOME=/root/.hermes` (default), a file
`/root/.hermes/active_profile` containing `"work"` will switch the
effective profile to `work` on next startup.

`hermes profile use <name>` writes this file (atomic via `.tmp` + replace —
see `set_active_profile()` in `profiles.py:1280`). It survives across
sessions until you `hermes profile use default` (or delete the file).

The flag `--profile <name>` and the env var `HERMES_PROFILE` (when set) take
precedence over the sticky file.

## `◆` marker in `hermes profile list`

`hermes profile list` reads the same `get_active_profile_name()` and marks
the active row with `◆`. Output on a default-only install:

```
 Profile          Model                        Gateway      Alias
───────────────  ───────────────────────────  ───────────  ────────
 ◆default         MiniMax-M3                   running      —
───────────────  ───────────────────────────  ───────────  ────────
```

If multiple profiles exist, only one is `◆`. The `Gateway` column shows
running/stopped per profile (each profile has its own gateway).

## All the ways to discover the active profile

In rough order of usefulness:

| # | Method | Command / API | What it tells you |
|---|--------|---------------|-------------------|
| 1 | CLI list | `hermes profile list` | Sticky/current profile (◆ row), all profiles + gateway state |
| 2 | CLI show | `hermes profile show <name>` | Path, model, gateway status, skill count, .env/SOUL.md presence |
| 3 | Current process env | `env \| grep HERMES_HOME` | HERMES_HOME of THIS shell/agent (may differ from gateway) |
| 4 | Other process env | `tr '\0' '\n' < /proc/<pid>/environ \| grep HERMES_HOME` | HERMES_HOME of the gateway / a sibling REPL / a cron job |
| 5 | Sticky marker | `cat ~/.hermes/active_profile` | Override name (empty ⇒ no override) |
| 6 | Python API | `from hermes_cli.profiles import get_active_profile_name; print(...)` | Returns "default" / profile name / "custom" |
| 7 | Profiles root | `ls ~/.hermes/profiles/` | Lists additional profile directories (no profiles/ dir ⇒ only default) |

### Method 4 in detail (cross-process introspection)

The gateway runs as a separate process (PID usually small, started at
boot). Cron jobs each run in fresh processes. They can each have their
own `HERMES_HOME`. To inspect any of them:

```bash
# Find PIDs
pgrep -f 'hermes_cli.main'         # gateway
pgrep -f 'hermes.*cron'            # cron runner
pgrep -f 'hermes.*session'         # REPL sessions

# Read env of a specific PID (replace <pid>)
sudo tr '\0' '\n' < /proc/<pid>/environ 2>/dev/null | grep -E 'HERMES_HOME|HERMES_PROFILE'

# Or, when current user matches the target:
tr '\0' '\n' < /proc/<pid>/environ | grep -E 'HERMES_HOME|HERMES_PROFILE'
```

`/proc/<pid>/environ` is NUL-separated bytes; the `tr '\0' '\n'` translates
to one env var per line. Permissions: world-readable for same-UID processes,
owner-only otherwise. Hermes runs as root in the systemd-managed gateway on
this host, so you'll need `sudo` from a non-root shell.

## Switching profiles (for completeness)

```bash
hermes profile create work       # copy current profile → ~/.hermes/profiles/work/
hermes profile use work          # write ~/.hermes/active_profile = "work"
hermes profile list              # verify ◆ moved to "work"
```

After `hermes profile use`, restart any running gateways so they pick up
the new sticky setting:

```bash
hermes gateway restart
```

## How `profile list` decides which row is "active"

The `◆` is rendered by `hermes_cli/main.py` (look for `list_profiles` /
`print_profile_table`). It compares each profile name against
`get_active_profile_name()` for the row's `HERMES_HOME`. Each profile is
shown with its own HERMES_HOME resolved from
`resolve_profile_env(profile_name)`.

If a profile exists on disk but is not the active one, it's still listed,
just without `◆`. Removing it is `hermes profile delete <name>` (cannot
delete the currently active profile — switch first).

## Pitfalls

- **`active_profile` and `HERMES_HOME` can disagree.** If you `hermes
  profile use work` but your shell still has `HERMES_HOME=~/.hermes`, a
  Hermes launched from THAT shell will see HERMES_HOME first (because
  main.py checks env-var before the sticky file). The sticky file only
  takes effect for processes started without HERMES_HOME already set. To
  force the sticky choice, `unset HERMES_HOME` before launching.
- **`hermes profile show <name>` requires a name.** Unlike `list`, there's
  no "show the current one" mode — you have to know the name (or
  identify it via the `◆` in `list`).
- **`HERMES_HOME=/root/.hermes/profiles/` (trailing slash, no name)** →
  resolves to the profiles ROOT, not a profile. `get_active_profile_name()`
  falls through to `"custom"`. Always include the name segment.
- **The gateway runs as a daemon and may predate a `profile use` change.**
  Restart it. Cron jobs spawned before the change will use the OLD
  profile for that tick.
- **`sudo`/`su` changes UID → fresh env.** When investigating via
  `/proc/<pid>/environ`, make sure you're reading the PID that actually
  owns the Hermes process you care about (`pgrep -af hermes`).

## Worked example — diagnosis on this host (2026-06-29)

```bash
$ hermes profile list
 Profile          Model                        Gateway      Alias
───────────────  ───────────────────────────  ───────────  ────────
 ◆default         MiniMax-M3                   running      —

$ hermes profile show default
Profile: default
Path:    /root/.hermes
Model:   MiniMax-M3 (minimax)
Gateway: running
Skills:  72
.env:    exists
SOUL.md: exists

$ env | grep HERMES_HOME
HERMES_HOME=/root/.hermes        # NORMAL: not inside profiles/, so default

$ ls ~/.hermes/profiles/ 2>/dev/null
ls: cannot access ...: No such file or directory   # only default exists

$ cat ~/.hermes/active_profile 2>/dev/null
cat: ...: No such file or directory                # sticky override not set

# Conclusion: active profile is "default", gateway (running) is also default.
```

## Quick reference — code locations

| Concern | File:line |
|---------|-----------|
| `get_active_profile_name()` (the algorithm) | `hermes_cli/profiles.py:1285` |
| Sticky override read at startup | `hermes_cli/main.py:378–390` |
| `set_active_profile()` (writes the sticky file) | `hermes_cli/profiles.py:1280` |
| `_get_default_hermes_home()` | `hermes_cli/profiles.py` (look up) |
| `_get_profiles_root()` | `hermes_cli/profiles.py` (look up) |
| `_PROFILE_ID_RE` (name validity) | `hermes_cli/profiles.py` (look up) |
| `hermes profile list` rendering (the `◆` marker) | `hermes_cli/main.py` (grep for `list_profiles` / `profile_table`) |

## See also

- `references/host-install-layout.md` — concrete paths on this host; the
  profiles-root and active_profile marker table entries.
- `hermes-agent-vcs-portability` — when you actually want to MOVE a
  profile between hosts.
- `hermes-agent-skill-authoring` — profile-scoped skills (`skills/`
  under each profile's HERMES_HOME).