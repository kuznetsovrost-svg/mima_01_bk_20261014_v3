---
name: github-contents-api
title: GitHub Contents API — folder/file in one call
description: "Create or update a file in a GitHub repo (and the folder that contains it) with a single PUT against the Contents API. The minimal, headless-friendly way for an agent to drop a file into a repo without cloning it. Falls back to `gh api` or pure `curl`."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [GitHub, Contents API, File Creation, Headless, Automation, No-Clone]
    related_skills: [github-pr-workflow]
prerequisites:
  commands: [gh]
---

# GitHub Contents API — drop a file (and its folder) with one PUT

The **Contents API** is the cheapest way for an agent to create or update a
file in a GitHub repository. Crucially, **Git does not store empty folders
** — but the Contents API creates intermediate directories automatically
the moment you PUT a file whose `path` contains a folder. So
«create folder X and put file Y in it» collapses to a single HTTP request.

This skill is the minimal headless counterpart to the heavier
`github-pr-workflow` skill. Reach for it when:

- You don't want to clone the repo (no local git state, no race conditions).
- The change is one or a handful of small files, not a full feature.
- You're inside cron, CI, or another agent that just needs to land a file.
- You want one commit = one PUT, atomic, no rebase drama.

For branch + commit + push + PR workflows, see `github-pr-workflow` instead.

## When to use this skill

| Trigger | Skill |
|---|---|
| "Создай файл в репо" / "drop a file in this repo" | **this skill** |
| "Сделай PR с этими изменениями" / review flow | `github-pr-workflow` |
| Many files + history + code review | `github-pr-workflow` |
| "Create folder + file" — same as above, single PUT | **this skill** |

## Prerequisites

- One of: `gh` CLI logged in (`gh auth status` ✓), **or** a `GITHUB_TOKEN`
  in `$GITHUB_TOKEN` / `~/.hermes/.env` (see `github-pr-workflow`
  §1 for setup).
- The token needs `repo` scope (private) or `contents: write` (fine-grained PAT).
- `base64` and `curl` (present by default; `gh` brings its own transport).

## 1. Auth — one line, two modes

```bash
source ~/.hermes/skills/github/github-pr-workflow/scripts/gh-env.sh
# Sets: GH_AUTH_METHOD ("gh" | "curl" | "none"),
#       GH_USER, GH_OWNER, GH_REPO, GITHUB_TOKEN
```

If `GH_AUTH_METHOD=gh` (the common case on a Hermes box) — proceed with
`gh api`. If `curl` — substitute the curl block from §4.

## 2. The canonical one-liner

```bash
# Parameters
OWNER="${OWNER:-kuznetsovrost-svg}"
REPO="${REPO:-hermes-demo-folder}"
FOLDER="${FOLDER:-GitHub_папка_01}"        # intermediate folder (created automatically)
FILE="${FILE:-GitHub_папка_01.txt}"        # filename inside the folder
BRANCH="${BRANCH:-main}"
CONTENT="${CONTENT:-Hello from Hermes @ $(date -u +%FT%TZ)}"
COMMIT_MSG="${COMMIT_MSG:-feat: add $FOLDER/$FILE}"

# 1. base64-encode the content (NO trailing newline)
B64=$(printf '%s' "$CONTENT" | base64 -w0)

# 2. For UPDATES, fetch the file's current SHA first (omit on create)
SHA=""
if gh api "/repos/$OWNER/$REPO/contents/$FOLDER/$FILE" --silent >/dev/null 2>&1; then
  SHA=$(gh api "/repos/$OWNER/$REPO/contents/$FOLDER/$FILE" --jq '.sha')
fi

# 3. PUT the file (folder appears in the tree as a side effect)
gh api --method PUT \
  -H "Accept: application/vnd.github+json" \
  "/repos/$OWNER/$REPO/contents/$FOLDER/$FILE" \
  --field message="$COMMIT_MSG" \
  --field branch="$BRANCH" \
  --field content="$B64" \
  $([ -n "$SHA" ] && echo --field "sha=$SHA") \
  --jq '.content | {sha: .sha, url: .html_url, path: .path}'
```

**That's it.** Result is one commit, one new blob, one new tree, one
new folder. No `git init`, no rebase, no SSH prompt.

## 3. What the API does for you (and what it doesn't)

| Concern | Contents API behaviour |
|---|---|
| Intermediate folders in `path` | **Created automatically.** No `mkdir` needed. |
| Empty folder only (no file) | **Not supported.** Folders only exist as a side effect of a file. |
| Filename with non-ASCII (Cyrillic, emoji) | Works. `gh api` percent-encodes; raw `curl` needs `--data-urlencode path`. |
| Updating an existing file | **Must include `"sha": "<existing_blob_sha>"`** — else 422. |
| Binary content | base64-encode the bytes (same code path). |
| File > 100 MB | **Not supported.** Use a `git push` for releases/large blobs. |
| Auth on private repos | Token scope `repo` (classic) or `contents: write` (fine-grained). |
| Rate limit | 5000 req/h authenticated. Each PUT = 1 req. |

## 4. Pure `curl` fallback (no `gh`)

```bash
# Set these first:
#   GITHUB_TOKEN, OWNER, REPO, FOLDER, FILE, BRANCH, CONTENT, COMMIT_MSG

B64=$(printf '%s' "$CONTENT" | base64 -w0)

# Optional: fetch existing SHA for updates
SHA=$(curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO/contents/$FOLDER/$FILE" \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('sha',''))" 2>/dev/null)

# Build JSON body in a temp file (avoids shell-quoting hell with
# newlines and special chars in the message)
JSON=$(mktemp)
python3 -c "
import json, sys
body = {
    'message': sys.argv[1],
    'content': sys.argv[2],
    'branch':  sys.argv[3],
}
if sys.argv[4]:
    body['sha'] = sys.argv[4]
print(json.dumps(body, ensure_ascii=False))
" "$COMMIT_MSG" "$B64" "$BRANCH" "$SHA" > "$JSON"

curl -s -X PUT \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  --data-binary @"$JSON" \
  "https://api.github.com/repos/$OWNER/$REPO/contents/$FOLDER/$FILE"
rm -f "$JSON"
```

## 5. Create-the-repo-then-file (full bootstrap)

If the repo doesn't exist yet:

```bash
gh repo create "$OWNER/$REPO" --public --description "..." --add-readme

# Repo is created and you're in it — then proceed with §2.
# (Or cd into a clone from elsewhere and use §2.)
```

Or with a single Contents call against a brand-new repo: create the
repo with `gh repo create` first (Contents API requires the repo to
exist — auto_init only gives you README, not your file).

## 6. Real-world examples

### 6.1 Drop a daily report

```bash
OWNER=acme REPO=daily-digest
FOLDER="reports/$(date -u +%Y)/$(date -u +%m)"
FILE="$(date -u +%F).md"
CONTENT="# Digest for $(date -u +%F)\n\n…markdown body…"
# Run the §2 template. `reports/2026/06/` will be created automatically.
```

### 6.2 Update a single config value

```bash
# This skill's "fetch SHA → re-PUT with sha" pattern handles updates.
# Idempotent: if the content is unchanged, GitHub still creates a new
# commit — but it's safe to call on cron.
```

### 6.3 Add many small files atomically (commits tree, not file)

For 2+ files in one commit, use the **Git Tree + Commit + Ref** API
flow, not repeated Contents PUTs. See
`github-pr-workflow` §5 if you need this.

## 7. Verification (always do this!)

After the PUT, verify with one of:

```bash
# Quick: just fetch the file's metadata
gh api "/repos/$OWNER/$REPO/contents/$FOLDER/$FILE" \
  --jq '{sha: .sha, size: .size, path: .path, html_url: .html_url}'

# Strong: list the tree, confirm folder+blob are there
gh api "/repos/$OWNER/$REPO/git/trees/$BRANCH?recursive=1" \
  --jq ".tree[] | select(.path | startswith(\"$FOLDER/\")) | \"\(.type)  \(.path)  sha=\(.sha[:8])\""

# Strongest: fetch the raw bytes
curl -fsSL "https://raw.githubusercontent.com/$OWNER/$REPO/$BRANCH/$FOLDER/$FILE"
```

A successful PUT returns 201 (create) or 200 (update) with the file's
new `sha`. If you get 422 — usually missing `sha` for an update, or
the parent path was a **file** instead of a folder.

## 8. Common errors and fixes

| Status | Cause | Fix |
|---|---|---|
| 401 | bad/expired token | `gh auth status`; refresh `GITHUB_TOKEN` |
| 403 "Resource not accessible" | PAT lacks `contents: write` | regenerate fine-grained PAT with the right repo + scope |
| 404 on PUT | repo/branch doesn't exist | check `OWNER/REPO/BRANCH`; pull first |
| 422 "sha" required | updating a file without `sha` | fetch `.sha` from GET, include in body |
| 422 "does not match" | you sent the `sha` of the **folder** tree, not the **blob** | the GET response's top-level `.sha` IS the blob sha; the tree sha is under `tree.sha` — use the blob one |
| 422 base64 newline | `base64` (GNU) wraps at 76 cols | use `base64 -w0` (Linux) or `base64 | tr -d '\n'` |
| 409 conflict | a branch protection / required status check blocks direct push to `main` | push to a feature branch + PR — `github-pr-workflow` §5 |

## 9. Pitfalls

1. **Git has no empty folders.** A folder only appears in the tree when
   a file's path traverses it. Contents API creates the folder as a
   side effect of the file PUT — you do **not** need to call anything
   else first.
2. **Auth ≠ connectivity.** A green `gh auth status` does not mean
   `api.github.com` is reachable. The first PUT will tell you. The
   `github-pr-workflow` §1.4 diagnostic covers this end-to-end.
3. **Branch protection.** If `main` is protected (required reviews,
   required status checks), Contents PUT to `main` will 409/422. You
   need to PUT to a feature branch and open a PR — see
   `github-pr-workflow` §5.6. To check, `gh api
   /repos/$OWNER/$REPO/branches/main/protection`.
4. **`url.*.insteadof` rewrite.** This host has
   `url.git@github.com:.insteadof https://github.com/` set globally.
   It affects `git clone` / `git push`, **not** `gh api` / `curl` — the
   Contents API calls are safe.
5. **Concurrent PUTs racing on the same file.** Two PUTs targeting the
   same path with the same old `sha` — the second will 409 ("does not
   match"). Re-fetch the new `sha` and retry. For multi-file atomic
   commits, use the Git Tree/Commit/Ref API.
6. **Token in shell history.** Avoid `Authorization: Bearer
   $GITHUB_TOKEN` in commands you paste into chat. Prefer the §4
   `JSON=$(mktemp) + --data-binary @file` pattern, or just `gh api`
   (no token in command line at all).

## 10. Minimal copy-paste for cron jobs

```bash
#!/usr/bin/env bash
# cron/drop-file.sh — drop one file into one repo, daily.
set -euo pipefail

OWNER="${OWNER:-kuznetsovrost-svg}"
REPO="${REPO:-my-repo}"
FOLDER="${FOLDER:-daily}"
FILE="${FILE:-$(date -u +%F).md}"
BRANCH="${BRANCH:-main}"
COMMIT_MSG="${COMMIT_MSG:-chore: daily drop $FILE}"

CONTENT="# $(date -u +%F)\n\nauto-generated.\n"

B64=$(printf '%s' "$CONTENT" | base64 -w0)
SHA=$(gh api "/repos/$OWNER/$REPO/contents/$FOLDER/$FILE" --jq '.sha' 2>/dev/null || true)

ARGS=( --method PUT
       -H "Accept: application/vnd.github+json"
       "/repos/$OWNER/$REPO/contents/$FOLDER/$FILE"
       --field message="$COMMIT_MSG"
       --field branch="$BRANCH"
       --field content="$B64" )
[ -n "$SHA" ] && ARGS+=( --field "sha=$SHA" )

gh api "${ARGS[@]}" --jq '"✓ " + .content.path + "  sha=" + .content.sha'
```

## Related

- `github-pr-workflow` — full GitHub surface: auth setup, repo create,
  PR lifecycle, code review, issues, releases.
  - Quick endpoint reference: `github-pr-workflow/references/github-api-cheatsheet.md`
    §"Contents API" (PUT/GET/DELETE on `/repos/{owner}/{repo}/contents/{path}`).
- `hermes-agent-vcs-portability` — backup/sync of your Hermes profile
  via GitHub (this skill is what that profile-sync actually uses
  under the hood).
