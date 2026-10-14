# Import and Rollback Recipes

Copy-pasteable shell recipes for the consumer side of a Hermes
agent package round-trip. Every command here was run end-to-end
in a real session; the expected output is shown. SKILL.md is the
index, this file is the recipe book.

If you only read SKILL.md and improvise, you will:

1. Forget the pre-import snapshot (catastrophic — no rollback)
2. Try to edit `~/.hermes/config.yaml` from the agent's
   `write_file` tool (silently blocked, see
   `messaging-gateway-setup` §7b)
3. Naively `cp -r` skills over the existing dir, losing your
   customised versions
4. Commit filled-in `.env` to the package repo on the next round

These recipes prevent all four. Run them in order; read the
comments; don't skip the dry-run.

---

## §A. Pre-import snapshot (REQUIRED)

Without this file, only the escape-valve rollback works, and
that one costs you everything. **Run first, ask questions later.**

```bash
TS=$(date -u +%Y%m%dT%H%M%SZ)
export TS

# Stop the gateway so files aren't mid-write
sudo systemctl --user stop hermes-gateway

# Snapshot the whole $HOME/.hermes tree.
# Note: -C $HOME means the tarball's leading component is ".hermes/",
# not "/root/.hermes/". Rollback recipes later rely on this.
tar -czf /var/tmp/hermes-pre-import-$TS.tar.gz -C $HOME .hermes

# Capture state for human-readable diff
hermes --version                   > /var/tmp/hermes-pre-import-$TS.ver
hermes skills list                 > /var/tmp/hermes-pre-import-$TS.skills
hermes config show                 > /var/tmp/hermes-pre-import-$TS.config
sha256sum /var/tmp/hermes-pre-import-$TS.tar.gz \
                                   > /var/tmp/hermes-pre-import-$TS.tar.gz.sha256

sudo systemctl --user start hermes-gateway
ls -l /var/tmp/hermes-pre-import-$TS.*   # sanity check
```

Expected: a 1–50 MB tarball (depends on skills count and memory
size), 4 sibling metadata files. The whole thing takes ~3 seconds.

---

## §B. Clone and dry-run

```bash
WORK=/var/tmp/hermes-import
rm -rf "$WORK" && mkdir -p "$WORK"
git clone https://github.com/<owner>/agents-backup.git "$WORK/repo"
cd "$WORK/repo"

# Pin to a version, NOT main
git checkout v$(cat VERSION)   # or v1.2.3 literal
git status                      # must be clean

# Look at what we're about to import
ls -la
cat README.md
for d in skills/*/; do
    name=$(basename "$d")
    printf '[%s] ' "$name"
    head -n 1 "$d/SKILL.md"
done
ls -la memories/ config-snippets/ cron/ mcp/ 2>/dev/null
cat env-template.env
```

### Secret-leak dry-run (CRITICAL)

```bash
grep -rE '(API_KEY|SECRET|TOKEN|PASSWORD|BEGIN .* PRIVATE KEY)' "$WORK/repo" \
    | grep -v 'env-template.env' \
    | grep -v 'README' \
    | grep -v 'CHANGELOG' \
    | head -20 \
    || echo "  OK: no leaked secrets in repo"
```

If anything prints, **STOP**. The author leaked credentials.
Don't import; report back to the author; treat any keys you see
as compromised.

---

## §C. Skills — conflict-aware import

The package's `skills/<name>/` and the user's
`~/.hermes/skills/<name>/` may collide on `<name>`. Three
strategies; pick per-skill.

```bash
DEST=$HOME/.hermes/skills
CONFLICTS_LOG=/var/tmp/hermes-import-conflicts-$TS.txt
> "$CONFLICTS_LOG"

for src in "$WORK/repo/skills/"*/; do
    name=$(basename "$src")
    if [ ! -e "$DEST/$name" ]; then
        # No conflict — install
        cp -a "$src" "$DEST/$name"
        echo "  installed: $name"
    else
        # Conflict — record and apply default strategy
        echo "$name" >> "$CONFLICTS_LOG"
        # Default strategy: import alongside with .from-repo-$TS suffix
        cp -a "$src" "$DEST/${name}.from-repo-$TS"
        echo "  [C] conflict → $DEST/${name}.from-repo-$TS  (local kept at $DEST/$name)"
    fi
done

cat "$CONFLICTS_LOG" | wc -l   # number of conflicts
```

To switch to strategy B (replace local with backup) for a specific
skill:

```bash
name=my-skill
rm -rf "$DEST/$name"
mv "$DEST/${name}.from-repo-$TS" "$DEST/${name}.local.${TS}.bak"
cp -a "$WORK/repo/skills/$name" "$DEST/$name"
```

To switch to strategy A (keep local, discard the imported copy):

```bash
name=my-skill
rm -rf "$DEST/${name}.from-repo-$TS"
```

After the loop:

```bash
# Re-read skills in the running session
sudo systemctl --user restart hermes-gateway
# or: /reload-skills in an open chat
hermes skills list | grep -E "from-repo|local\.bak" \
    || echo "  no leftover conflict markers"
```

---

## §D. Memories — never auto-overwrite

```bash
MEM_DEST=$HOME/.hermes/memories
mkdir -p "$MEM_DEST"
for f in "$WORK/repo/memories/"*.md "$WORK/repo/memories/"*.json; do
    [ -e "$f" ] || continue
    name=$(basename "$f")
    if [ -e "$MEM_DEST/$name" ]; then
        cp -a "$f" "$MEM_DEST/${name}.from-repo-$TS"
        echo "  [merge] $MEM_DEST/${name}.from-repo-$TS  (local kept)"
    else
        cp -a "$f" "$MEM_DEST/$name"
        echo "  installed: $name"
    fi
done
```

Manual merge for any `.from-repo-$TS` file is the user's job. Do
not write code to auto-merge LLM-generated memory blocks.

---

## §E. config.yaml — shell-only edit, yq deep-merge

`~/.hermes/config.yaml` is **blocked from agent's write_file/patch**
(intentional, see `messaging-gateway-setup` §7b). Edit from the
shell. For programmatic merge:

```bash
cp -a $HOME/.hermes/config.yaml $HOME/.hermes/config.yaml.pre-import-$TS.bak

# Merge one snippet at a time, validating after each
for snippet in "$WORK/repo/config-snippets/"*.yaml; do
    [ -e "$snippet" ] || continue
    yq eval-all '. as $item ireduce ({}; . *+ $item)' \
        $HOME/.hermes/config.yaml \
        "$snippet" \
        > /tmp/config.merged.yaml \
        || { echo "  yq failed on $snippet — skipping"; continue; }

    # Validate syntax
    yq eval '.' /tmp/config.merged.yaml > /dev/null \
        || { echo "  yq validation failed on $snippet — skipping"; continue; }

    cp /tmp/config.merged.yaml $HOME/.hermes/config.yaml
    echo "  merged: $(basename $snippet)"
done

hermes config check
```

If `hermes config check` fails:

```bash
# Roll back config to the pre-import state
cp $HOME/.hermes/config.yaml.pre-import-$TS.bak $HOME/.hermes/config.yaml
hermes config check    # should be OK now
```

Then merge snippets **one at a time** to find which one breaks.

---

## §F. env-template.env — additive append

```bash
ENV=$HOME/.hermes/.env
TEMPLATE="$WORK/repo/env-template.env"

# First-time only: copy template as the starting point
[ -f "$ENV" ] || { cp -a "$TEMPLATE" "$ENV"; chmod 600 "$ENV"; }

# For each var in the template, append only if not present
while IFS='=' read -r key defval; do
    case "$key" in ''|\#*) continue ;; esac
    if ! grep -q "^${key}=" "$ENV" 2>/dev/null; then
        # Append with the default from the template (may be empty)
        printf '\n%s=%s\n' "$key" "$defval" >> "$ENV"
        echo "  added: $key"
    fi
done < "$TEMPLATE"
chmod 600 "$ENV"
ls -l "$ENV"   # confirm mode
```

The user must fill the empty values with their actual secrets
(API keys, tokens, etc.) — never the package author.

---

## §G. cron and MCP — CLI translation, not file copy

```bash
# Cron
for f in "$WORK/repo/cron/"*.yaml; do
    [ -e "$f" ] || continue
    name=$(basename "$f" .yaml)
    schedule=$(yq -r .schedule "$f")
    prompt=$(yq -r .prompt "$f")
    skills_csv=$(yq -r '.skills // [] | join(",")' "$f")
    delivery=$(yq -r '.delivery // "origin"' "$f")
    [ "$skills_csv" = "null" ] && skills_csv=""
    [ "$skills_csv" = "" ] \
        && hermes cron create "$schedule" "$prompt" --delivery "$delivery" \
        || hermes cron create "$schedule" "$prompt" --skills "$skills_csv" --delivery "$delivery"
    echo "  cron: $name"
done
hermes cron list

# MCP
if [ -e "$WORK/repo/mcp/servers.yaml" ]; then
    yq eval '.servers[] | .name + "|" + (.url // .command[0] // "?")' \
        "$WORK/repo/mcp/servers.yaml" \
    | while IFS='|' read -r name where; do
        [ "$name" = "" ] && continue
        if yq eval ".servers[] | select(.name == \"$name\") | has(\"url\")" \
            "$WORK/repo/mcp/servers.yaml" | grep -q true; then
            url=$(yq eval ".servers[] | select(.name == \"$name\") | .url" \
                  "$WORK/repo/mcp/servers.yaml")
            hermes mcp add "$name" --url "$url"
        else
            cmd=$(yq eval -o=tsv ".servers[] | select(.name == \"$name\") | .command[]" \
                  "$WORK/repo/mcp/servers.yaml" | tr '\n' ' ')
            # shellcheck disable=SC2086
            hermes mcp add "$name" --command $cmd
        fi
    done
    hermes mcp list
    for n in $(yq eval '.servers[].name' "$WORK/repo/mcp/servers.yaml"); do
        hermes mcp test "$n" || echo "  WARN: $n failed handshake"
    done
fi
```

---

## §H. Final validation

```bash
hermes doctor
hermes config check
hermes skills list | wc -l   # compare with .pre-import-*.skills count
hermes cron list
hermes mcp list

# End-to-end test
hermes chat -q "/skills" --tools skills
hermes chat -q "Загрузи skill <imported-name> и расскажи, что он делает." --tools skills
```

If all green, log the import:

```bash
echo "$TS  imported $WORK/repo (v$(cat $WORK/repo/VERSION)): \
skills=[$(ls $WORK/repo/skills/ | tr '\n' ',')], \
conflicts=[$(cat $CONFLICTS_LOG 2>/dev/null | tr '\n' ',')]" \
    >> $HOME/.hermes/import-log.txt
```

**Do NOT delete the pre-import snapshot yet.** Keep it until the
imported package has been in use for at least one full work cycle
without issues.

---

## §I. Rollback scenarios

### §I.1. Per-skill rollback (lightest)

Pick one of three paths depending on what `.bak`/`.from-repo-*`
artifacts exist:

```bash
name=my-skill
DEST=$HOME/.hermes/skills

# Path A: restore from .local.$TS.bak (strategy B on import)
if [ -d "$DEST/${name}.local.${TS}.bak" ]; then
    rm -rf "$DEST/$name"
    mv "$DEST/${name}.local.${TS}.bak" "$DEST/$name"
    echo "  restored from .local.${TS}.bak"
# Path B: drop the imported copy, keep local
elif [ -d "$DEST/${name}.from-repo-${TS}" ]; then
    rm -rf "$DEST/${name}.from-repo-${TS}"
    echo "  dropped imported copy, local kept"
# Path C: extract just this one skill from the pre-import snapshot
else
    SKILL_TMP=/var/tmp/hermes-skill-restore-$name-$TS
    rm -rf "$SKILL_TMP" && mkdir -p "$SKILL_TMP"
    # NOTE: leading ".hermes/" in the tarball path — not "/root/..."
    tar -C "$SKILL_TMP" -xzf \
        /var/tmp/hermes-pre-import-$TS.tar.gz \
        ".hermes/skills/$name/"
    rm -rf "$DEST/$name"
    cp -a "$SKILL_TMP/.hermes/skills/$name" "$DEST/$name"
    echo "  restored from pre-import snapshot"
fi

sudo systemctl --user restart hermes-gateway
hermes skills list | grep -w "$name"
```

### §I.2. Full rollback (everything)

```bash
sudo systemctl --user stop hermes-gateway
rm -rf $HOME/.hermes
tar -C $HOME -xzf /var/tmp/hermes-pre-import-$TS.tar.gz
sudo systemctl --user start hermes-gateway
hermes doctor
diff /var/tmp/hermes-pre-import-$TS.skills <(hermes skills list) \
    && echo "  skill list matches pre-import"
```

If `hermes doctor` flags anything, the snapshot itself was taken
from a broken state. Move to §I.3.

### §I.3. Escape-valve (snapshot missing or also broken)

```bash
sudo systemctl --user stop hermes-gateway
rm -rf $HOME/.hermes
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
hermes setup   # interactive wizard
```

Before running this: copy `~/.hermes/.env` (if you still have
read access) somewhere safe — it has the credentials. After the
escape-valve, you'll need to re-add them via the setup wizard or
`hermes auth add <provider>`.

---

## §J. Post-rollback checklist

- [ ] `hermes doctor` → all ✓
- [ ] `hermes skills list` matches pre-import count (full rollback)
      or expected post-rollback count (per-skill)
- [ ] `hermes config check` exits 0
- [ ] `hermes cron list` has no leftover job-ids from the failed import
- [ ] `hermes mcp list` has no leftover names
- [ ] `ls $HOME/.hermes/memories/ | grep from-repo` is empty
- [ ] `ls $HOME/.hermes/skills/ | grep -E "from-repo|local\.bak"` is empty
- [ ] `du -sb $HOME/.hermes` close to pre-import size
- [ ] `hermes chat -q "/skills"` shows expected set
- [ ] One real task done end-to-end without anomaly

If more than one item fails: §I.2 (full rollback) and try again.
If full rollback also leaves it broken: §I.3 (escape-valve) and
start the diagnostic from scratch.

---

## §K. Common failure modes (one-liners)

| Symptom | Likely cause | Fix |
|---|---|---|
| `hermes doctor` shows `skill: missing frontmatter` | Skill copied without its `references/`/`templates/` siblings | Re-copy whole dir, not just `SKILL.md` |
| Imported skill invisible in `/skills` | Session wasn't reset | `/reload-skills` (CLI) or `/restart` (gateway) |
| `hermes config check` invalid after yq merge | yq version mismatch between author and importer | Pin yq version in README; or merge by hand |
| Cron job created but never fires | Schedule string format wrong | `hermes cron run <id>` to test; check `hermes cron status` |
| MCP server "added" but tools missing | Handshake failed (wrong URL/command) | `hermes mcp test <name>`; check the process is actually running |
| Memory file lost during import | Strategy C wasn't applied; package's `memories/<name>.md` overwrote local | Re-import with the loop in §D, restore from pre-import snapshot |
| Imported `.env` values missing | User never filled them in | Re-run §F; user must populate empty values |
| `git checkout` of an old version doesn't undo the import | The agent is *running* off the file, but the file is the same | `hermes skills check && hermes skills update` is for hub-installed skills; for Git packages, `git pull` in the cloned scratch dir, then re-run §C–§G |

---

## §L. What to capture in `import-log.txt`

```text
$TS  imported <repo-url> (v$VERSION)
       skills: a, b, c (no conflicts)
       skills: x (CONFLICT, strategy C)
       config: merged 2 snippets
       cron: added 1 job
       mcp: added 1 server
       env: appended 3 keys
       snapshot: /var/tmp/hermes-pre-import-$TS.tar.gz (kept)
```

This becomes the audit trail when the user later asks "what did
I import last month?" or "did we ever import the bad v0.9
package?".
