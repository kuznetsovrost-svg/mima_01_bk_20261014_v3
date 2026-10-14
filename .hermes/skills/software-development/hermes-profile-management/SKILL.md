---
name: hermes-profile-management
description: >
  Create, inspect, and reason about Hermes Agent profiles (default,
  analyst_training, fst-control, custom), the four-tier skill visibility
  model (bundled / global user / profile-specific / override), the
  `hermes profile create` flag matrix (--clone / --clone-from / --no-skills
  / --description / --clone-all / --no-alias), and the "active profile"
  confusion between what the system prompt says and what
  `~/.hermes/profiles/<name>/` actually contains. Use when the user asks
  "create N profiles", "make a skill visible to every profile", "why
  doesn't my profile see skill X", "what does --no-skills actually do",
  or notices the active profile in the system prompt does not match
  any existing directory. NOT for editing SOUL.md / MEMORY.md / USER.md
  content (use `agent-config-iteration`), NOT for writing a new SKILL.md
  (use `hermes-agent-skill-authoring`).
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [hermes, profile, skills, multi-profile, bundled, global-user, --no-skills, agent-routing]
    related: [vscode-integration, agent-config-iteration, hermes-agent-skill-authoring, hermes-internals-inspection]
---

# Hermes Profile & Skill Visibility Management

Class: managing multiple Hermes Agent profiles on one host, understanding
which skills each profile can see, and avoiding the three recurring
"profile confusion" patterns that have hit past sessions:

1. **The "default profile doesn't exist" pattern** — the system prompt
   reports `Active Hermes profile: default`, but `~/.hermes/profiles/default/`
   is missing because the original `default` lived as `/root/.hermes/.env`
   + the bare gateway command (`hermes_cli.main gateway run` with no
   `--profile` flag).
2. **The "bundled skills are global" misconception** — `/usr/local/lib/hermes-agent/skills/`
   is NOT auto-visible to a profile. Bundled skills reach a profile only
   via `seed_profile_skills()` at create time, which copies them into
   `~/.hermes/profiles/<name>/skills/`. A `--no-skills` profile therefore
   sees **zero** bundled skills unless they were also copied into
   `/root/.hermes/skills/` (global user).
3. **The "same name = silent override" pattern** — a profile with
   `<name>/skills/foo/SKILL.md` overrides any global user or bundled
   `foo` skill. The `skills_tool.py` collision detector refuses ambiguous
   lookups, so duplicate names across tiers will surface as errors, not
   silent shadowing.

This skill encodes the verified recipe for the `hermes profile` command,
the four-tier skill visibility model (with code-grounded pointers), the
flag matrix, and the troubleshooting ladder when the active profile does
not match the directory layout.

## When to Use This Skill

- User asks "создай 5 профилей" / "create N profiles" — give them the
  `hermes profile create` flag matrix, not a `mkdir -p` script.
- User asks "где создавать скиллы, чтобы видели все" — point them to
  `/root/.hermes/skills/`, with the four-tier model explained.
- User asks "почему в моём профиле нет скилла X" — diagnose by walking
  the four tiers (bundled → global user → profile-specific → override).
- User asks "что такое --no-skills" — explain the seed_profile_skills
  opt-out marker and what *does* stay visible.
- User notices that the system prompt says one profile but the gateway
  PID belongs to another — the routing-confusion troubleshooting ladder.
- User asks "скопируй bundled скиллы в global" — provide the conflict-
  checked copy recipe (pitfall: same-name collisions are refused, not
  shadowed).

Triggers (Russian or English): "создай профиль", "create profile",
"active profile", "активный профиль", "видимость скиллов", "skill
visibility", "глобальные скиллы", "global skills", "hermes profile",
"--no-skills", "--clone", "bundled skills", "установить профиль".

## The Four-Tier Skill Visibility Model

Verified against `/usr/local/lib/hermes-agent/tools/skills_tool.py` and
`/usr/local/lib/hermes-agent/hermes_cli/profiles.py` (Hermes 2026-08,
build that ships `hermes-acp` 0.18.x).

| Tier | Path | Visible to | How it gets there |
|---|---|---|---|
| **1. Bundled (system)** | `/usr/local/lib/hermes-agent/skills/<cat>/<name>/SKILL.md` | All profiles | `seed_profile_skills()` at `hermes profile create` time. 18 categories, 68 skills total, ~7.3 MB. |
| **2. Global user** | `/root/.hermes/skills/<cat>/<name>/SKILL.md` | All profiles (always) | `SKILLS_DIR = HERMES_HOME / "skills"` (i.e. `/root/.hermes/skills/`) is appended to `all_dirs` unconditionally in `skills_tool.py`. The only path that is visible without per-profile opt-in. |
| **3. Profile-specific** | `/root/.hermes/profiles/<name>/skills/<cat>/<name>/SKILL.md` | Only `<name>` | Created by the user. Useful for narrow-purpose skills (e.g. `fst-pmpractice` in `fst-control`). |
| **4. Override** | Same path as (3), same `<name>` as a bundled or global skill | Only the profile, but overrides tier 1/2 of the same name | The collision detector refuses ambiguous lookups across tiers, so an explicit override means "I'm replacing this for my profile." |

The visible-to-all-paths are tier 1 (after seeding) and tier 2 (always).
Tiers 3 and 4 are per-profile.

**Pitfall (recurring, hit 2026-08):** assuming that because a bundled
skill exists in `/usr/local/lib/hermes-agent/skills/`, it is "global." It
is not — it must be copied into `/root/.hermes/skills/` to be global in
the cross-profile sense. Tier 1 becomes global only via the seeding
mechanism during `hermes profile create`.

**Pitfall (recurring, hit 2026-08):** recommending "copy bundled skills
to global to avoid the per-profile copy." Before doing that, check that
the destination `<cat>/<name>/` does not already exist in
`/root/.hermes/skills/` — the collision detector will refuse same-name
duplicates. A robust copy recipe must probe each destination first.

## The `hermes profile create` Flag Matrix

Verified via `hermes profile create --help` (2026-08):

| Flag | Bundled seeded? | SOUL.md / config.yaml / .env | Skills source | Alias wrapper |
|---|---|---|---|---|
| `(no flag)` | ✅ all 68 | default template | bundled | created |
| `--clone` | ✅ all 68 | copied from **active** profile | active profile | created |
| `--clone-from <src>` | ✅ all 68 (unless `--no-skills`) | copied from `<src>` | `<src>` profile | created |
| `--clone-all` | ✅ all 68 | copied + state.db / state.db-* / session history (excluded per `_CLONE_ALL_HISTORY_EXCLUDE_ROOT`) | `<src>` profile (full) | created |
| `--no-skills` | ❌ (writes `.no-bundled-skills` marker) | default template | none — but global user (tier 2) still visible via `SKILLS_DIR` | created |
| `--no-alias` | per other flags | per other flags | per other flags | ❌ skipped |
| `--description <text>` | per other flags | per other flags | per other flags | per other flags |

**What `--no-skills` actually does:**

1. Writes an empty `.no-bundled-skills` marker into the new profile root.
2. `seed_profile_skills()` checks this marker and returns
   `{"skipped_opt_out": True, ...}` — no bundled copy.
3. `hermes update`'s all-profile sync and the web dashboard also honour
   the marker.
4. The profile is still allowed to install skills manually via
   `hermes skills install` or by dropping `SKILL.md` files into its own
   `skills/`.
5. **Critically:** global user skills (tier 2) at
   `/root/.hermes/skills/` remain visible — the `--no-skills` opt-out
   only affects tier 1.

**Pitfall:** "no-skills" sounds like "no skills at all." In reality it
means "no *bundled* skills in this profile's `skills/` directory." A
well-stocked global user location makes a `--no-skills` profile more
capable than its name implies.

**Profile name rule:** lowercase alphanumeric only (verified via the
`--help` text: "Profile name (lowercase, alphanumeric)"). Use hyphens for
separators: `coder-v2` OK, `Coder V2` not OK, `coder.v2` not OK.

## The Active-Profile Troubleshooting Ladder

When the system prompt reports `Active Hermes profile: X` but the
directory `~/.hermes/profiles/X/` does not exist (or the gateway PID
belongs to a different profile), walk this ladder before doing anything
destructive:

1. **Verify the actual gateways.** `ps auxf | grep hermes` shows every
   running gateway and its `--profile` flag (or absence, for the
   implicit-default case).
2. **Map PID → profile:**
   - `hermes_cli.main gateway run` (no `--profile`) → implicit `default`,
     uses `/root/.hermes/.env` for tokens.
   - `hermes_cli.main --profile <name> gateway run` → `<name>`.
3. **Map bot → profile via the token file:**
   - `/root/.hermes/.env` → the implicit-`default` bot.
   - `/root/.hermes/profiles/<name>/.env` → the bot registered to that
     profile's gateway.
4. **If the system prompt says `default` but `default/` is missing:**
   create it as a bare-bones profile (copy `SOUL.md` + `config.yaml` from
   a sibling profile such as `analyst_training`). Do **not** invent a
   new gateway — keep the existing PID running.
5. **If the gateway PID does not match the profile the user is talking
   to:** the user is reaching the wrong bot. Send them the bot ID vs
   profile mapping (do not auto-redirect).
6. **For Telegram delivery:** route files via the **sending** bot's
   token, never the receiving bot's. See the
   `messaging-gateway-setup` skill for the `sendDocument` recipe; do
   not switch profiles to "fix" the routing.

**Anti-pattern:** assuming the active profile from a memory note in a
prior compaction summary. The system prompt is the only ground truth;
re-read it on every fresh session.

**Pitfall (recurring, hit 2026-08-09): profile name in VS Code `agent_servers` JSON does not match the SSH alias.** When a profile becomes reachable from VS Code via `strato-space.acp-plugin`, the SSH target in the JSON (`args[0]`) must match a `Host` alias declared in the user's local `~/.ssh/config`. Common mismatch: profile is `coder-vsc` (hyphen) but the user types `coder_vsc` (underscore) in the JSON, or the profile is on `mima_g_01` (underscore, as written in conversation) but `~/.ssh/config` declares `Host mima-g-01` (hyphen). The error from VS Code is verbatim `ssh: Could not resolve hostname ...: No such host is known.` (exit 255), and the ACP client surfaces it as `Agent process exited before ACP initialized`. The fix is **not** a profile rename — profiles are server-side, the SSH config is client-side, and renaming the profile would invalidate all running gateways. Fix the JSON spelling to match the existing `Host` block, or add an alias block to `~/.ssh/config`.

## Copying Bundled Skills to Global — Conflict-Safe Recipe

Verified pattern (when the user wants skills shared across `--no-skills`
profiles):

```bash
SRC=/usr/local/lib/hermes-agent/skills
DST=/root/.hermes/skills

for src_path in "$SRC"/*/*/; do
    rel="${src_path#$SRC/}"          # e.g. "creative/excalidraw"
    dest="$DST/$rel"
    if [ -e "$dest" ]; then
        echo "SKIP (exists): $rel"
        continue
    fi
    mkdir -p "$(dirname "$dest")"
    cp -r "$src_path" "$dest"
    echo "COPIED: $rel"
done
```

The collision detector in `skills_tool.py` is what would refuse the copy
if you tried to `cp -r` blindly; the probe above avoids that by checking
first.

## Pitfalls

### "Bundled skills are global"

They are not, in the cross-profile sense. `/usr/local/lib/hermes-agent/skills/`
is only visible to a profile after `seed_profile_skills()` copies them
into `~/.hermes/profiles/<name>/skills/`. The "global user" location is
`/root/.hermes/skills/`, which is unconditional via `SKILLS_DIR`.

### "`--no-skills` means no skills"

It means "no *bundled* skills seeded into this profile." Global user
skills (tier 2) remain visible. If the user wants an empty profile, they
need an empty global user directory *and* `--no-skills`.

### "Same name across tiers shadows silently"

`skills_tool.py` has explicit collision detection: it collects candidates
across every directory using every lookup strategy (direct path,
recursive by parent dir name, legacy flat `<name>.md`) and **refuses**
ambiguous lookups. The error message names the conflicting paths. Use
the conflict-safe copy recipe above to avoid this.

### "Copy bundled to global — done"

Without checking first, you can either (a) overwrite a newer user version
of the same skill in `/root/.hermes/skills/`, or (b) trigger the
collision detector. Always probe with `[ -e "$dest" ]` before `cp -r`.

### "Active profile is what the last session said"

The system prompt's `Active Hermes profile:` line is the ground truth.
Compaction summaries can be stale across gateways restarts, profile
renames, and bot reassignments. Re-verify at the start of every session.

### "I'll just edit `~/.hermes/profiles/other-profile/`"

Cross-profile edits trigger a soft guard in `write_file`. Either copy
into the user's own profile, or ask for explicit cross-profile
authorisation before patching. Do not silently bypass.

### "Token routing fix: switch profiles"

Token routing is fixed by sending via the **sending** bot's token, not
by switching profiles. Profiles do not own tokens — gateways do. The
`messaging-gateway-setup` skill has the `sendDocument` recipe.

## Examples of Real Use

- User: "Создай 5 профилей." → Agent: gives a `for name in ...; do
  hermes profile create "$name" --description "..."; done` snippet,
  asks whether to `--no-skills`, `--clone-from default`, or full
  `--clone-all`. Does not invent gateways or tokens.
- User: "Где создавать скиллы, чтобы видели все?" → Agent: explains the
  four tiers, points to `/root/.hermes/skills/`, shows the conflict-safe
  copy recipe.
- User: "У меня профиль `default`, но `/root/.hermes/profiles/default/`
  не существует." → Agent: walks the troubleshooting ladder, confirms
  via `ps auxf | grep hermes`, suggests creating the directory with a
  minimal structure (SOUL.md + config.yaml from a sibling), does NOT
  start a new gateway.
- User: "Я пишу через `@botA` — это какой профиль?" → Agent: maps
  gateway PID → profile → `.env` → bot token, tells the user "you're
  talking to profile X via bot A." If files need sending back, the
  `messaging-gateway-setup` skill gives the `sendDocument` recipe via
  bot A's token.

## Checklist Before Touching Profiles / Skills

- [ ] Active profile confirmed via system prompt, not memory.
- [ ] Gateway PIDs mapped to profile names (`ps auxf | grep hermes`).
- [ ] Bot → profile mapping confirmed via the `.env` files.
- [ ] If creating profiles, the user has named them (lowercase
      alphanumeric).
- [ ] If copying bundled → global, conflict check performed.
- [ ] If `--no-skills`, the user understands that global user (tier 2)
      is still visible.
- [ ] Telegram delivery uses the **sending** bot's token (per
      `messaging-gateway-setup`), regardless of active profile.

## Related Skills

- `vscode-integration` — multi-profile setup through ACP, including the
  per-profile `--clone-from` workflow.
- `agent-config-iteration` — for evolving SOUL.md / MEMORY.md / USER.md
  *content*, not the directory layout.
- `hermes-agent-skill-authoring` — for writing a new SKILL.md, not for
  choosing where to place it.
- `hermes-internals-inspection` — for reading Hermes source code to
  answer "where is this implemented," not for deciding profiles.
- `messaging-gateway-setup` — for Telegram / Discord / Slack delivery
  once the profile-vs-bot routing is sorted out.

## Reference Files

- `references/profile-architecture-2026-08.md` — verified file paths,
  PID → profile mapping, the four-tier skill model with code-grounded
  excerpts from `skills_tool.py`, `profiles.py`, and `main.py`,
  including the bundled skill catalogue (68 skills across 18 categories).
- `templates/copy-bundled-to-global.sh` — conflict-safe idempotent
  bash script that copies a curated list of bundled skills into
  `/root/.hermes/skills/`. Each entry is probed for existence first
  (no blind overwrite), the script counts COPIED / SKIPPED / ERROR
  outcomes, and it prints the next-step reminder
  (`hermes profile create X --no-skills`). The default list mirrors
  the v0.1.0 verified recommendation set; CLI args override it.
  Verified 2026-08-09: ran clean (5 copied, 33 skipped, 0 errors) when
  28 of the 33 recommendation entries were already in global; the
  5 newly-copied skills were `humanizer`, `design-md`, `powerpoint`,
  `research-paper-writing`, `hermes-agent`.