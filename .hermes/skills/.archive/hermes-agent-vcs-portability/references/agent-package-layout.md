# Canonical Layout for a Hermes Agent Package

The contract an **author** of an agent package must follow so that
an **importer** (any other Hermes user) can apply the package
deterministically. SKILL.md in the umbrella points here; do not
duplicate this layout elsewhere — this file is the source of truth.

## Directory tree

```
agents-backup/
├── README.md                  # who this agent is, what it does, how to start
├── CHANGELOG.md               # version history (matches git tags)
├── VERSION                    # semver, e.g. "1.2.3"
├── LICENSE                    # if redistributable
├── .gitignore                 # .env, *.bak, __pycache__, *.sqlite-*
├── skills/
│   └── <skill-name>/
│       ├── SKILL.md           # frontmatter (name/description/version/...)
│       ├── references/        # optional: longer docs the skill links to
│       ├── templates/         # optional: starter files
│       └── scripts/           # optional: runnable helpers
├── memories/
│   ├── user.md                # user profile (if applicable)
│   ├── memory.md              # long-term agent memory
│   └── <topic>.json           # structured blocks
├── config-snippets/
│   ├── agent.yaml             # model / agent settings
│   ├── terminal.yaml          # terminal backend
│   ├── memory.yaml            # memory provider
│   └── security.yaml          # redaction, approvals
├── env-template.env           # variable NAMES, never values
├── cron/
│   └── <job-name>.yaml        # schedule + prompt + delivery
├── mcp/
│   └── servers.yaml           # registry: name → url/command
└── release/                   # only on tagged releases
    ├── agents-backup-1.2.3.tar.gz
    ├── agents-backup-1.2.3.sha256
    └── agents-backup-1.2.3.tar.gz.asc   # GPG detached signature
```

## Per-file rules

### README.md (required)

Open with **one paragraph**: "This is the *<name>* agent for Hermes. It
does *<X>*. Start it with `<command>`. Backed up on *<date>*."

Then sections:
- Requirements (Hermes version, OS, external services, env vars)
- Install (clone, snapshot reminder, import steps)
- Configuration (which env vars, which config-snippets to merge)
- Usage (1–3 worked examples)
- Rollback (link to `references/import-rollback-recipes.md`)
- License

### VERSION (required)

Plain semver. Used by importers to:
- Pin (`git checkout v$(cat VERSION)`)
- Log (`import-log.txt` lines include the version)
- Validate (e.g. "requires Hermes >= X.Y.Z" in README)

### .gitignore (required)

```
.env
*.bak
*.local
*.local.*.bak
*.from-repo-*
__pycache__/
*.pyc
.DS_Store

# SQLite transient files — not part of the package
*.db-journal
*.db-shm
*.db-wal
*.sqlite-journal
*.sqlite-shm
*.sqlite-wal
```

Note: do NOT ignore `*.db` itself — the importer expects the package
to include `.db` snapshots as part of `memories/` if the agent has
SQLite-backed state. See the `*.sqlite-*` rules for the matching
transient files.

### skills/<name>/SKILL.md

Must use the `hermes-agent-skill-authoring` layout (frontmatter +
sections). The skill's name field must match the directory name.

### memories/*.md and *.json

If a memory file is present, it's authoritative for **importers
without their own memory of the same name**. If the importer
already has a `user.md`, the import logic should put the package's
copy alongside as `user.md.from-repo-$TS` — never silently
overwrite. LLM-generated memories are not safe to auto-merge.

### config-snippets/*.yaml

Each file is a **partial** `config.yaml` — the keys it contains
are the only ones the importer should merge. The standard merge
command is:

```bash
yq eval-all '. as $item ireduce ({}; . *+ $item)' \
    ~/.hermes/config.yaml \
    <snippet>.yaml \
    > /tmp/config.merged.yaml
yq eval '.' /tmp/config.merged.yaml > /dev/null    # validate
cp /tmp/config.merged.yaml ~/.hermes/config.yaml
hermes config check
```

The `*+` operator deep-merges; keys present in both files take
the snippet's value. Importer is responsible for backing up the
original `config.yaml` first (`config.yaml.pre-import-$TS.bak`).

### env-template.env

```
# Provide values in ~/.hermes/.env. Do NOT commit a filled-in .env.

# Required for skill <foo>
FOO_API_KEY=
FOO_ENDPOINT=https://api.example.com

# Optional
FOO_TIMEOUT_SEC=30
```

The **importer** does the additive append:

```bash
ENV=$HOME/.hermes/.env
[ -f "$ENV" ] || cp -a env-template.env "$ENV"
chmod 600 "$ENV"
while IFS='=' read -r key _; do
    case "$key" in ''|\#*) continue ;; esac
    grep -q "^$key=" "$ENV" 2>/dev/null \
        || printf '\n%s\n' "$key=$(grep -E "^$key=" env-template.env | tail -1 | cut -d= -f2-)" >> "$ENV"
done < env-template.env
```

### cron/<job-name>.yaml

```yaml
name: weekly-summary
schedule: "0 9 * * 1"
prompt: |
  Summarize the past week's sessions and post to my home chat.
skills: [summarizer, session-search]
delivery: origin
model:
  provider: openrouter
  model: anthropic/claude-sonnet-4
```

Importer translates to CLI:

```bash
hermes cron create "$(yq .schedule cron/weekly-summary.yaml)" \
    "$(yq -r .prompt cron/weekly-summary.yaml)" \
    --skills "$(yq -r '.skills | join(",")' cron/weekly-summary.yaml)" \
    --delivery "$(yq -r .delivery cron/weekly-summary.yaml)"
```

`--model` and `--provider` flags exist; pass them only if the
package's `model:` block is non-empty.

### mcp/servers.yaml

```yaml
servers:
  - name: my-mcp
    url: http://127.0.0.1:8765/sse
  - name: cli-mcp
    command: ["npx", "-y", "@example/cli-mcp"]
```

Importer:

```bash
yq eval '.servers[] | .name + "\t" + (.url // .command[0])' mcp/servers.yaml \
| while IFS=$'\t' read -r name where; do
    if yq eval ".servers[] | select(.name == \"$name\") | has(\"url\")" mcp/servers.yaml | grep -q true; then
        url=$(yq eval ".servers[] | select(.name == \"$name\") | .url" mcp/servers.yaml)
        hermes mcp add "$name" --url "$url"
    else
        cmd=$(yq eval ".servers[] | select(.name == \"$name\") | .command | join(\" \")" mcp/servers.yaml)
        # shellcheck disable=SC2086
        hermes mcp add "$name" --command $cmd
    fi
done
hermes mcp list
hermes mcp test <name>     # validate each connection
```

## Releasing a version

```bash
cd <package-repo>
# 1. Bump VERSION and CHANGELOG.md
echo "1.2.4" > VERSION
$EDITOR CHANGELOG.md

# 2. Commit, tag, sign
git add VERSION CHANGELOG.md
git commit -m "release 1.2.4: <summary>"
git tag -s v1.2.4 -m "release 1.2.4"

# 3. Push commit + tag
git push origin main
git push --tags

# 4. Build the release tarball
mkdir -p release
git archive --format=tar.gz \
    --prefix=agents-backup-1.2.4/ \
    -o release/agents-backup-1.2.4.tar.gz \
    v1.2.4
sha256sum release/agents-backup-1.2.4.tar.gz \
    > release/agents-backup-1.2.4.sha256

# 5. GPG-sign the tarball
gpg --batch --yes --armor --detach-sign \
    --output release/agents-backup-1.2.4.tar.gz.asc \
    release/agents-backup-1.2.4.tar.gz

# 6. Attach the three files to the GitHub Release
gh release create v1.2.4 \
    release/agents-backup-1.2.4.tar.gz \
    release/agents-backup-1.2.4.sha256 \
    release/agents-backup-1.2.4.tar.gz.asc
```

## What NOT to include

- `~/.hermes/.env` (filled-in) — credential leak
- `~/.hermes/sessions/` — contains tokens, user PII, and
  per-user state; export only if explicitly requested, and
  redact first
- `~/.hermes/logs/` — has secrets in plain text
- `~/.hermes/state.db` — large, profile-specific; the canonical
  store is here, but a portable agent package should NOT carry
  someone else's session state
- `gateway/auth.json` — OAuth tokens, never export

## Why a flat layout

Putting `skills/`, `memories/`, etc. at the top level (not nested
under `hermes/`) means:
- The package is readable as a normal directory tree (`ls`, `find`,
  IDE project) without unpacking
- `git diff` shows category changes at a glance
- Future tools can compose multiple packages without nested
  container conventions
- Importer scripts can copy whole subtrees (`cp -a repo/skills/
  ~/.hermes/skills/`) with a single command — though for
  conflict-safe copy, iterate with the recipes in
  `import-rollback-recipes.md` instead
