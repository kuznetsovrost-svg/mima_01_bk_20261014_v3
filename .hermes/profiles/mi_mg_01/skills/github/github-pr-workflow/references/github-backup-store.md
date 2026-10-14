# Using a Private GitHub Repo as a Backup / Artifact Store

A private GitHub repo is a reasonable cheap-and-durable target for periodic
server-state snapshots: binary assets don't bloat git history (they live in
the Releases store), and the index lives in the repo as ordinary files you can
browse and search.

The pattern: `gh release create` uploads the tarball + sha256 as release
assets under a tag named after the backup stamp, and the Contents API drops
the manifest/excludes alongside existing files in `main`.

## When to use

- Periodic snapshots of a server's `/root` (or any subtree) to a private repo
- Lifting build artifacts out of a sandbox and shipping them to a stable URL
- Versioned drop point for files that don't belong in git history (logs,
  binary state, large configs)

## The recipe (3 steps)

### 1. Build the archive with a bash script — NOT via execute_code's terminal

`terminal()` with chained `tar --exclude=...` commands repeatedly failed
silently (exit=-1) when exclude patterns with `**/.cache`-style globs were
involved, because shell-quoting inside execute_code mangles them. The
reliable pattern is to write a bash script to disk, then run it once:

```bash
cat > /tmp/build_backup.sh <<'SCRIPT'
#!/usr/bin/env bash
set -euo pipefail
cd /root
tar --exclude-from=/root/migration/backup_excludes.txt \
    -czf /root/migration/archives/backup-${STAMP}.tar.gz .
sha256sum /root/migration/archives/backup-${STAMP}.tar.gz \
    > /root/migration/archives/backup-${STAMP}.tar.gz.sha256
SCRIPT
bash /tmp/build_backup.sh
```

Why this matters: a single multi-flag tar invocation through the terminal
tool can hang on output buffering, get truncated, or fail to parse the
exclude file. A script with `set -euo pipefail` fails loudly on any error
and `tee`s progress to a log file you can re-read.

### 2. `gh release create` ships archive + sha256 in one shot

```bash
ARC=/path/to/backup-${STAMP}.tar.gz
SHA=${ARC}.sha256
NOTES=/path/to/release-notes.md
REPO=owner/repo
TAG=backup-${STAMP}

gh release create "$TAG" \
  "${ARC}#${ARC##*/}" \
  "${SHA}#sha256" \
  --repo "$REPO" \
  --title "Server backup ${STAMP}" \
  --notes-file "$NOTES" \
  --target main
```

The `file#label` syntax (only valid with `gh`, not raw curl) sets the
uploaded asset's `name`. Without it, the asset is named after the basename
of the local path — which usually matches anyway, so it's mostly a hint for
the download UI.

`--target main` ensures the tag points at `main` (otherwise it might point
at a stale head if the local clone is behind).

### 3. Contents API for the index (manifest, excludes)

The release page has the archive; the repo `main` should have a human-
browsable index. Two small files via the Contents API:

```bash
gh api -X PUT repos/${REPO}/contents/MANIFEST-${STAMP}.md \
  --input <(jq -Rn --rawfile c manifest.md \
            '{message:"backup '"${STAMP}"': add manifest", content: $c, branch:"main"}')
```

To update an existing file, GET its blob sha first and include it as `sha`
in the PUT body — otherwise GitHub returns 422 "does not match". See the
github-contents-api skill for the full headless template.

## Tag and file naming

```
Tag:    backup-YYYYMMDD-HHMMSS          (lexicographically sortable)
Asset:  mima_01_bk-root-YYYYMMDD-HHMMSS.tar.gz
Asset:  mima_01_bk-root-YYYYMMDD-HHMMSS.tar.gz.sha256
Files:  MANIFEST-YYYYMMDD-HHMMSS.md
        excludes-YYYYMMDD-HHMMSS.txt
```

Using the same stamp in all four names makes them trivially greppable.
Keep stamp generation in one place (the build script), don't regenerate
it across the steps — clock skew between calls produces orphan
manifests.

## Pitfalls

- **Recursive backup inclusion.** If the archive lives in a path that's
  inside the source tree (e.g. `/root/migration/archives/...` while
  archiving `/root`), tar happily slurps the previous backup too. Always
  add the output directory to the exclude list:
  ```
  migration/archives
  migration/mima_01_bk_stage_*
  ```

- **Secrets in tarballs.** `/root` almost always contains things that
  must NOT leave the box:
  - `.ssh/`, `.gnupg/`, `.netrc`, `.config/gh/`
  - `.hermes/.env*`, `.hermes/auth.json`, `.hermes/state.db*`,
    `.hermes/sessions/`, `.hermes/kanban.db*`
  - `.cache/`, `node_modules/`, `__pycache__/`
  Default the excludes file to drop all of these, then re-add what you
  need. The reusability is in the exclude list, not the tar invocation.

- **`--exclude-from=file` vs inline `--exclude=`.** When there are more
  than ~10 patterns, the file is far easier to read, version, and reuse.
  Use globs in the file (`**/.cache`); tar handles `**` as "zero or more
  path components" since GNU tar 1.32.

- **GitHub asset URLs behave differently across hosts.** A direct
  `curl` of `releases/download/<tag>/<file>` on some networks returns a
  9-byte stub or hits a TLS-handshake timeout on
  `release-assets.githubusercontent.com`, while `gh release download` and
  the GitHub web UI work fine. If verifying the round trip from the same
  host fails, the issue is usually outbound CDN access, not a bad upload —
  the API still reports `state: "uploaded"` and the right size. Verify
  from a second network.

- **Manifest and excludes must reach `main` BEFORE the release page
  links to them in the notes.** Order of operations matters: build →
  release → contents API. Reversing it produces a release whose notes
  link to files that 404 for a few seconds.

- **Tag vs branch race.** If you push to `main` via Contents API AFTER
  `--target main` was resolved at release-create time, the tag will point
  one commit behind. For backup purposes that's fine; for git-as-source-
  of-truth workflows it isn't. Add the index files first, then create
  the release, OR push the index via `git push` and let the tag follow.

- **The release asset download URL is stable** as long as the tag
  exists. If you delete the tag, all its assets vanish. Don't `git push
  origin :refs/tags/backup-*` to "clean up old backups" — they're the
  only thing GitHub hosts for you. Old releases on a private repo cost
  nothing and survive repo archival.

## Verifying a backup

From any host with normal GitHub access:

```bash
curl -sSL -o verify.tar.gz \
  https://github.com/${OWNER}/${REPO}/releases/download/${TAG}/${ASSET}
sha256sum -c ${ASSET}.sha256
tar -tzf verify.tar.gz | wc -l
tar -xzf verify.tar.gz path/to/specific/file
```

From the same host that produced the archive, the round-trip may fail
even though the upload succeeded (see "GitHub asset URLs behave
differently" above). The local sha256 sidecar is the authoritative
proof that the bytes you uploaded are the bytes you intended.

## Automation

For periodic backups, the natural cron job is:

1. The build script (`scripts/build-server-backup.sh`) generates the
   archive + sha256
2. The same script (or a follow-up) calls `gh release create` and the
   Contents PUT
3. The release is durable; the script is the only moving part

Cron examples and a one-shot invoke pattern live in
`scripts/build-server-backup.sh`.
