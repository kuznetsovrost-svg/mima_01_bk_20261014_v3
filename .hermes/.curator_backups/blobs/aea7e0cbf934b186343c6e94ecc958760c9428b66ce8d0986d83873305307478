---
name: hermes-agent-vcs-portability
description: "Backup, share, import, and roll back Hermes Agent 'agent packages' (skills + memories + config snippets + cron + mcp) via a Git remote (GitHub / Gitea / GitLab). Use when the user wants to: back up a Hermes install to a Git repo, publish an agent as a portable package, import a third-party agent package from a Git URL into a live Hermes, or roll back a botched import. The class is 'how to move a Hermes agent through Git round-trips' — not how to use `gh`, how to write a skill, or how to use a specific messaging platform."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [hermes, vcs, git, backup, import, rollback, skills, agent-package, portability, github, gitea, gitlab]
    related: [hermes-agent, hermes-agent-skill-authoring, messaging-gateway-setup]
---

# Hermes Agent VCS Portability

Move a working Hermes "agent package" (skills + memories + config
fragments + cron + MCP servers) through a Git remote, end-to-end:
snapshot → publish, import into a fresh or live Hermes, and roll
back when the import misbehaves. The skill covers the **class** of
work; reference documents attached below carry the per-recipe
detail.

## When to use this skill

- User says "back up the agent to GitHub" / "put my skills in a
  Git repo" / "publish this agent" / "version-control Hermes".
- User says "import this agent from GitHub" / "load the agent
  package from this repo" / "set up this skill bundle from a URL".
- User says "I imported a package and the agent is broken — undo
  it" / "roll back the last import" / "revert to the pre-import
  state".
- User wants the **canonical layout** for an agent package (so
  other people can import it cleanly).

## When NOT to use this skill

- The user just wants a single skill installed/updated — that's
  `hermes skills install <id>` from the `hermes-agent` skill, no
  Git round-trip needed.
- The user wants a normal `gh` PR / issue workflow — that's the
  existing `github-pr-workflow` skill (now an umbrella covering auth, issues, and code review too).
- The user wants to publish a SKILL.md to the skills hub — that's
  `hermes-agent-skill-authoring` plus `hermes skills publish`.

## Quick mental model

A "Hermes agent package" is a directory tree that an importer can
copy/merge into `~/.hermes/` to reproduce a working agent. The
minimum viable package is:

```
agents-backup/
├── README.md                 # who this agent is, how to start it
├── VERSION                   # semver
├── skills/<skill>/SKILL.md   # one or more skills
├── memories/                 # user.md, memory.md, *.json
├── config-snippets/          # mergeable config.yaml fragments
├── env-template.env          # variable NAMES only — no values
├── .gitignore                # exclude .env, *.bak, __pycache__
└── (optional) cron/, mcp/, release/
```

The full canonical layout with rationale, the snapshot-then-push
flow, the import flow, and the three rollback scenarios are in
`references/agent-package-layout.md` and
`references/import-rollback-recipes.md`. **Read those before
writing your own — they encode the lessons from a real session
where each omission cost a turn.**

## Workflow: backup (publish) side

1. Decide what's in the package. Default: skills, memories,
   config-snippets, env-template, .gitignore. Drop: `.env` (secrets
   go elsewhere), live session transcripts (`state.db` is
   profile-specific and big), `gateway.log` (noisy, has tokens).
2. Take a working snapshot. **Never edit `~/.hermes/` in place
   while publishing** — copy out to a scratch dir, then
   `git init` there.
3. `git init -b main` in the scratch dir, add, commit, push to
   the remote (SSH deploy key preferred over HTTPS PAT).
4. Tag a version: `git tag v1.2.3 && git push --tags`. Tagging
   matters because importers will pin to it.
5. (Optional) GPG-sign the tag and attach a tarball + sha256 to
   a GitHub Release — see the worked example in
   `references/agent-package-layout.md` §Release.

## Workflow: import (consumer) side

> ⚠️ **`~/.hermes/config.yaml` is guarded against the agent's
> own `write_file`/`patch` tools** (intentional, per the
> `hermes-agent` skill). Config edits happen from the shell, not
> from agent tool calls. Same for `~/.hermes/.env`.

1. **Snapshot before importing.** This is non-negotiable — without
   it, the rollback recipes in `references/import-rollback-recipes.md`
   won't work. Run as root-equivalent user (or `sudo -u $USER`):
   ```bash
   TS=$(date -u +%Y%m%dT%H%M%SZ)
   sudo systemctl --user stop hermes-gateway
   tar -czf /var/tmp/hermes-pre-import-$TS.tar.gz -C $HOME .hermes
   hermes --version > /var/tmp/hermes-pre-import-$TS.ver
   hermes skills list > /var/tmp/hermes-pre-import-$TS.skills
   sudo systemctl --user start hermes-gateway
   ```
2. Clone to a scratch dir, NOT into `~/.hermes/`:
   `git clone <url> /var/tmp/hermes-import/repo`
3. **Dry run.** Look at what the package contains. Critically,
   grep for accidental secrets:
   `grep -rE '(API_KEY|SECRET|TOKEN|PASSWORD|BEGIN.*PRIVATE KEY)'
   repo/ | grep -v env-template.env | grep -v README` — if
   anything turns up, STOP. The author leaked something.
4. Import skills, memories, config-snippets, env-template, cron,
   mcp one at a time, with explicit conflict handling per
   category. The three strategies for skills (keep local /
   replace / import-alongside) are in
   `references/import-rollback-recipes.md` §Skills.
5. For config: `yq eval-all` to deep-merge snippets into
   `~/.hermes/config.yaml`, then `hermes config check` to
   validate. If validation fails, restore the `.pre-import-*.bak`
   you made in step 1.
6. Validate: `hermes doctor`, `hermes skills list`,
   `hermes config check`, `hermes cron list`, `hermes mcp list`,
   then a test chat: `hermes chat -q "/skills"`.
7. If anything looks wrong, jump to the rollback ladder.

## Workflow: rollback ladder

Three escalating scenarios, in this order — pick the lightest one
that fully resolves the issue. Full step-by-step and recovery
commands in `references/import-rollback-recipes.md` §Rollback.

1. **Per-skill rollback** (one skill misbehaves, rest is fine):
   restore from `.local.*.bak` (if you took option B on import),
   or from `.from-repo-*` (option C), or extract a single
   skill path from the pre-import snapshot. Note the path
   inside the snapshot tarball is `.hermes/skills/<name>/`,
   not `/root/...hermes/skills/<name>/` (the snapshot was made
   with `tar -C $HOME`, so the leading component is `.hermes`).
2. **Full rollback** (everything broke): restore the whole
   `~/.hermes/` from `/var/tmp/hermes-pre-import-$TS.tar.gz`,
   restart gateway, run `hermes doctor`. Always works if you
   took the snapshot.
3. **Escape-valve** (snapshot was missing or also broken):
   `sudo systemctl --user stop hermes-gateway && rm -rf ~/.hermes
   && curl -fsSL https://hermes-agent.nousresearch.com/install.sh
   | bash && hermes setup`. Last resort — loses everything
   not backed up, including auth tokens stored in `.env`. Recover
   those from your password manager / vault before doing this.

## Pitfalls

### 1. **Always snapshot before importing.** Single hardest rule.
If you don't, you cannot use any of the rollback recipes below
beyond the escape-valve, which costs you all local config. The
snapshot is two minutes of work and saves hours of debugging
when a foreign skill shadows your existing one with the same
name and breaks the agent's response format. **Suspect this
when** the user says "I just imported X and now Y is broken" —
first question to ask is "do you have `/var/tmp/hermes-pre-import-*.tar.gz`?"

### 2. **Conflict-handling for skills is not optional.**
Naive `cp -r repo/skills/* ~/.hermes/skills/` will silently
overwrite skills with the same name. Always iterate with a
conflict detector and pick A (keep local) / B (replace with
local backup) / C (import alongside as `.from-repo-*`) per
skill. Choice B is safest for first-time imports; choice C
is safest for iterative ones where you want to diff.

### 3. **`config.yaml` is shell-only.** The agent's
write_file/patch tools are explicitly blocked from editing it.
Use `hermes config edit` (opens in `$EDITOR`), `yq eval-all`
for programmatic merge, or `hermes config set key val` for
single keys. Same applies to the per-platform blocks scattered
across `gateway.platforms.<platform>`, top-level `<platform>:`
keys, and `platform_toolsets.<platform>` — see
`messaging-gateway-setup` §"The config.yaml Layout Is Spread Out"
for the full map.

### 4. **Memories are not safe to auto-merge.** SQLite-backed
memories and long markdown blocks contain LLM-generated
content that, if blindly merged with another version, can
produce contradictory or duplicated knowledge. Default policy:
**never overwrite** an existing memory file; import with a
`.from-repo-$TS` suffix and let the user merge manually.

### 5. **`.env` is for variable NAMES, never values.** The
imported `env-template.env` lists which variables the package
expects. The actual values come from the user's vault and
must be appended to `~/.hermes/.env` with the existing keys
preserved (`grep -q "^$key="` check before append). A leaked
filled-in `.env` in a public repo is a credential emergency,
not a bug.

### 6. **Cron and MCP are added via CLI, not by file copy.**
Hermes stores them in SQLite (cron) and a registry (mcp).
`cp cron/foo.yaml ~/.hermes/cron/` does nothing. Translate
each YAML to the appropriate `hermes cron create` or
`hermes mcp add` command. A worked example for MCP is in
`references/import-rollback-recipes.md` §Cron/MCP.

### 7. **`/reload-skills` is a CLI slash, not a shell command.**
After a skill add/remove, the running session doesn't see
it. From CLI: `/reload-skills` or `/reset`. From gateway
session: `/restart`. From outside any session: `systemctl
--user restart hermes-gateway` covers everything.

### 8. **The agent-state shell-append gate.** `cat >> $HOME/.hermes/... <<EOF` is blocked by a protective gate ("BLOCKED:
User denied this command. The user has NOT consented to this
action."). If you need to add to `MEMORY.md` or similar agent
state, use the `memory` tool (not the shell) — that's the
sanctioned path. Full pitfall in
`messaging-gateway-setup` §7b (cross-linked because both
classes touch shell-on-`~/.hermes/`).

### 9. **Don't pin main in production imports.** Always
`git checkout v1.2.3` (or whatever tag) in the scratch clone.
`main` can move under you; the tag is the contract.

## Verification

After any backup:
- `git log --oneline` in the package repo shows the commit
- `git ls-remote <remote>` shows the same SHA on the matching
  ref
- Tarball sha256 (if you also published one) matches the
  `release/<version>.sha256` file

After any import:
- `hermes doctor` → all subsystems ✓
- `hermes skills list` includes the new skill names
- `hermes config check` exits 0
- `hermes chat -q "/skills"` shows the imported skills
- `~/.hermes/memories/` has either the new files (no conflict)
  or `.from-repo-*` siblings (conflict) — never silent
  overwrites
- The pre-import snapshot is still on disk (do NOT delete it
  until you've validated the imported package runs cleanly
  for at least one full work cycle)

After any rollback:
- `hermes doctor` → all subsystems ✓
- `hermes skills list | wc -l` matches the pre-import count
  (full rollback) or the expected post-rollback count
  (per-skill rollback)
- `ls $HOME/.hermes/skills/ | grep -E '(from-repo|local\.bak)'`
  is empty when the rollback is done

## References

- `references/agent-package-layout.md` — canonical export
  layout (the contract authors must follow), with a sample
  directory tree, sample `env-template.env`, sample
  `config-snippets/`, sample `cron/` and `mcp/` entries,
  and a complete `git push --tags` + Release flow.
- `references/import-rollback-recipes.md` — copy-pasteable
  shell recipes for: (a) the pre-import snapshot, (b) skill
  conflict resolution (options A/B/C), (c) `yq`-based config
  merge, (d) memory import with `.from-repo-*` suffix, (e) env
  variable additive append, (f) cron/MCP CLI translation, (g)
  the three rollback scenarios, (h) the post-rollback checklist,
  (i) the escape-valve.

Both reference files are **load-bearing**: this SKILL.md is
the index, they are the recipes. Loading only SKILL.md and
trying to improvise the commands from memory is how backups
get published with secrets and rollbacks get half-done.

## Related

- `hermes-agent` — the CLI reference (`hermes cron create`,
  `hermes mcp add`, `hermes skills list`, `hermes doctor`,
  `hermes config check`). Always read this first to ground
  the command names — they change between Hermes versions.
- `hermes-agent-skill-authoring` — the layout for SKILL.md
  frontmatter, used when the imported package contains new
  skills that need a known-good format.
- `messaging-gateway-setup` — the `~/.hermes/` agent-state
  shell gate (pitfall §7b) and the `~/.hermes/.env` token
  sanitization patterns. Both classes touch the same files.
- `github-pr-workflow` — covers the full GitHub CLI/API/curl surface (now an umbrella skill)
  operations; for the package repo creation, SSH key
  management, and release attachments.
