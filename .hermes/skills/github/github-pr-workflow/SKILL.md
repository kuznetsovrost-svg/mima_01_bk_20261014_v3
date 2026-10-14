---
name: github-pr-workflow
title: GitHub Workflows (umbrella)
description: "Complete GitHub workflows: auth, repo management, code review, issue triage, and the PR lifecycle. Most operations are pure `git`; the `gh` CLI is preferred when present; `curl` is the universal fallback."
version: 2.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [GitHub, Pull-Requests, CI/CD, Git, Automation, Code-Review, Issues, Auth, Repo-Management]
    related_skills: [requesting-code-review, hermes-agent-vcs-portability]
---

# GitHub Workflows — Umbrella

Class-level skill for working with GitHub. Covers the full surface:
authentication, repository management, code review, issue triage, and
the PR lifecycle. Most operations are pure `git`; the `gh` CLI is preferred
when present; `curl` is the universal fallback.

If a `gh` CLI is **not** installed, every section below falls back to plain
`git` (for read/clone) or `curl` against the GitHub REST/GraphQL API (for
PRs, issues, releases). Run Detection Flow in §1 first.

## Section Index

1. **Auth setup & diagnostics** — choose your auth method, set up `gh` or
   `GITHUB_TOKEN`/SSH, run the connectivity diagnostic when something
   breaks. *(was: `github-auth`)*
2. **Repository management** — clone, create, fork, configure topics,
   releases, secrets, teams. *(was: `github-repo-management`)*
3. **Code review** — review local changes pre-push, review open PRs on
   GitHub, leave inline comments, request reviewers. *(was: `github-code-review`)*
4. **Issues** — list, search, create, triage, label, close, link to PRs.
   *(was: `github-issues`)*
5. **PR workflow** — branch, commit, push, open PR, monitor CI, auto-fix
   failures, merge. *(was the original `github-pr-workflow`)*
6. **References** — `references/`
7. **Templates** — `templates/`
8. **Helper scripts** — `scripts/`

> **Quick start — the canonical pre-flight for any GitHub work:**
>
> Source the helper once to set `GH_AUTH_METHOD`, `GITHUB_TOKEN`,
> `GH_USER`, `GH_OWNER`, `GH_REPO`:
>
> ```bash
> source scripts/gh-env.sh
> echo "Method: $GH_AUTH_METHOD | User: $GH_USER | Repo: $GH_OWNER/$GH_REPO"
> ```
>
> If you can't source, copy the inline detection in §1.1 below.

---

## 1. Auth Setup & Diagnostics *(was: `github-auth`)*

### 1.1 Detection Flow

When a user asks you to work with GitHub, run this first:

```bash
git --version
gh --version 2>/dev/null || echo "gh not installed"
gh auth status 2>/dev/null || echo "gh not authenticated"
git config --global credential.helper 2>/dev/null || echo "no git credential helper"
```

**Decision tree:**

1. `gh auth status` shows authenticated → use `gh` for everything.
2. `gh` installed but not authenticated → use `gh auth login` (or set
   `GH_TOKEN` / `GITHUB_TOKEN` env var).
3. `gh` not installed → use `git` + `GITHUB_TOKEN` / SSH key. **No sudo
   required.** Tell the user this requires either installing `gh`
   (needs sudo) or a user-binary download from
   https://github.com/cli/cli/releases.

> **`gh` missing silently breaks other skills.** The PR workflow,
> issues, and code-review sections below all assume `gh` is available
> for issue creation, PR opens, and API calls. When `gh` is not
> installed, they fall back to `curl` + `GITHUB_TOKEN` — set it up
> before doing non-trivial GitHub work.

### 1.2 Setting up `GITHUB_TOKEN` (no `gh`)

1. Create a token at https://github.com/settings/tokens. Scopes needed:
   `repo`, `read:org`, `workflow` (for Actions).
2. Save to `~/.hermes/.env` (preferred) or export.

   ```bash
   echo "GITHUB_TOKEN=ghp_REPLACE_ME" >> ~/.hermes/.env
   ```

3. Verify by sourcing the helper:

   ```bash
   source scripts/gh-env.sh
   echo "Method: $GH_AUTH_METHOD | User: $GH_USER | Repo: $GH_OWNER/$GH_REPO"
   ```

### 1.3 Setting up SSH

The `templates/ssh-config-github` file is a ready-to-append block for
`~/.ssh/config`. It is set up to:

- Use `IdentitiesOnly yes` (prevents SSH offering every key in
  `~/.ssh/` and authenticating to the wrong account).
- Use `ControlMaster auto` + `ControlPersist 600` (drops `ls-remote`
  latency from ~700ms to ~50ms after the first op).
- Provide a `github-443` host fallback when outbound `22/tcp` is
  blocked (uses `ssh.github.com:443`).

```bash
cat templates/ssh-config-github >> ~/.ssh/config
chmod 600 ~/.ssh/config

# First-use: trust GitHub's host keys (public, safe to automate)
ssh-keyscan -H -t rsa,ecdsa,ed25519 ssh.github.com >> ~/.ssh/known_hosts
```

### 1.4 Connectivity Diagnostic

When the user asks "is GitHub working?" or "проверь подключение к
GitHub", run this ordered 12-step script. Every step is independent and
pure — no auth used unless the step explicitly requires it. Total
runtime ~5s on a healthy box. See `references/github-api-cheatsheet.md`
for the full endpoint reference.

```bash
echo "── 1. Tool versions ──"
git --version
gh --version 2>/dev/null || echo "gh not installed"
ssh -V 2>&1 | head -1

echo "── 2. gh CLI status ──"
gh auth status 2>&1 || echo "gh not authenticated or not installed"

echo "── 3. SSH test (BatchMode = no interactive prompt) ──"
ssh -T -o BatchMode=yes -o StrictHostKeyChecking=accept-new \
  git@github.com 2>&1
echo "exit=$?   (exit=1 + greeting = success — GitHub no-shell response)"

echo "── 4. Which key was offered (verbose, filtered) ──"
ssh -T -v -o BatchMode=yes -o StrictHostKeyChecking=accept-new \
  git@github.com 2>&1 | \
  grep -E 'Offering|Authenticated|Authentications that can continue'

echo "── 5. SSH agent and on-disk keys ──"
ssh-add -l 2>&1 || echo "no ssh-agent"
ls -la ~/.ssh/id_*.pub 2>/dev/null

echo "── 6. SSH config (relevant lines) ──"
[ -f ~/.ssh/config ] && grep -A4 -E '^Host github' ~/.ssh/config \
  || echo "no ~/.ssh/config"

echo "── 7. Global git config ──"
git config --global --get user.name
git config --global --get user.email
git config --global --get-regexp '^url\.'

echo "── 8. Credential helper + file ──"
git config --global --get-all credential.helper
ls -la ~/.git-credentials 2>/dev/null | head -1

echo "── 9. GitHub-related env / hermes env tokens (no secret leak) ──"
env | grep -iE 'github|gh_token' | sed 's/=.*\(........\)$/=REDACTED\1/' \
  || echo "no github env"
GITHUB_LEN=$(awk -F= '/^GITHUB_TOKEN=/{print length($2); exit}' ~/.hermes/.env 2>/dev/null)
GITHUB_PRE=$(awk -F= '/^GITHUB_TOKEN=/{print substr($2,1,4); exit}' ~/.hermes/.env 2>/dev/null)
echo "GITHUB_TOKEN set: length=$GITHUB_LEN prefix=$GITHUB_PRE"

echo "── 10. Anonymous API probe ──"
curl -sS -m 8 -o /dev/null -w 'HTTP=%{http_code} time=%{time_total}s\n' \
  https://api.github.com/

echo "── 11. Real git operation over SSH ──"
GIT_TERMINAL_PROMPT=0 \
  git ls-remote git@github.com:octocat/Hello-World.git 2>&1 | head -3

echo "── 12. Real git operation over HTTPS ──"
GIT_TERMINAL_PROMPT=0 \
  git ls-remote https://github.com/octocat/Hello-World.git 2>&1 | head -3
```

**Verdict matrix** (what to look for in the output):

| Step | Healthy | Broken |
|------|---------|--------|
| 1 | git + ssh present, `gh` may be missing | any of git/ssh missing → fatal |
| 3 | `Hi <user>! You've successfully authenticated, but GitHub does not provide shell access.` (exit=1) | `Permission denied (publickey)` or `Connection refused` |
| 4 | single `Offering public key: ~/.ssh/id_ed25519` + `Authenticated to github.com ... using "publickey"` | no `Offering` line → no key reachable; multiple `Offering` lines → `IdentitiesOnly yes` missing in `~/.ssh/config` |
| 7 | `user.name` + `user.email` + the `url.*.insteadof` rewrite present | missing identity → commits will fail; missing rewrite → https URLs hit unauthenticated path |
| 10 | `HTTP=200 time<1s` | `HTTP=000` or timeout → outbound to api.github.com blocked (firewall/ISP) |
| 11 & 12 | identical ref lists, exit=0, no prompt | different/empty lists → rewrite broken or key not authorized for the repo |
| `hermes status` | `GitHub` provider line optional; it only reflects `GITHUB_TOKEN` presence, not git auth | `GitHub ✗` is **not** a connectivity verdict — it just means no API token in `.env`. The SSH channel can still be 100% working. |

**Always distinguish "git auth" from "API auth"** in the report. They
are independent: SSH key handles the first, GITHUB_TOKEN handles the
second. Telling the user "GitHub is broken" when only the API token is
missing is a false alarm.

### 1.5 Auth Pitfalls

- **Wrong key authenticates silently.** Multiple keys + missing
  `IdentitiesOnly yes` → SSH offers them all, first accepted wins,
  commits land on the wrong account. Always set `IdentitiesOnly yes`
  per host (see template above).
- **Outbound 22/tcp blocked at ISP/firewall.** Use the `github-443`
  host (ssh over TLS to ssh.github.com:443) or HTTPS + PAT.
- **PAT scopes insufficient.** `repo` scope is required for private
  repo write; `workflow` for Actions; `read:org` for org-level reads.
- **`.env` cached by gateway.** If you edit `~/.hermes/.env`, the
  gateway process keeps the old value at startup — restart it.

---

## 2. Repository Management *(was: `github-repo-management`)*

### 2.1 Cloning

Pure `git` — works identically either way:

```bash
# HTTPS
git clone https://github.com/owner/repo-name.git
# Into a specific directory
git clone https://github.com/owner/repo-name.git ./my-local-dir
# Shallow
git clone --depth 1 https://github.com/owner/repo-name.git
# Specific branch
git clone --branch develop https://github.com/owner/repo-name.git
# SSH
git clone git@github.com:owner/repo-name.git
```

**With `gh` shorthand:**

```bash
gh repo clone owner/repo-name
gh repo clone owner/repo-name -- --depth 1
```

### 2.2 Creating Repositories

**With `gh`:**

```bash
gh repo create my-new-project --public --clone
gh repo create my-new-project --private \
  --description "A useful tool" --license MIT --clone
gh repo create my-org/my-new-project --public --clone

# From existing local directory
cd /path/to/existing/project
gh repo create my-project --source . --public --push
```

**With `git` + `curl`:**

```bash
# Create the remote repo via API
curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/user/repos \
  -d '{
    "name": "my-new-project",
    "description": "A useful tool",
    "private": false,
    "auto_init": true,
    "license_template": "mit"
  }'

# Clone it
git clone https://github.com/$GH_USER/my-new-project.git

# -- OR -- push an existing local directory to the new repo
cd /path/to/existing/project
git init && git add . && git commit -m "Initial commit"
git remote add origin https://github.com/$GH_USER/my-new-project.git
git push -u origin main
```

**Alternative for a single-file repo with a folder (no clone, no git):** create the repo with `--add-readme`, then drop your file via the **Contents API** in one PUT — intermediate folders appear automatically. See skill `github-contents-api` for the headless template.

### 2.3 Forking

```bash
# gh
gh repo fork owner/repo-name --clone --remote

# API
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/owner/repo-name/forks
# Then: git clone https://github.com/$GH_USER/repo-name.git
```

### 2.4 Configuring Repos (Topics, Settings, Visibility)

```bash
# Set topics
curl -s -X PUT \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/$OWNER/$REPO/topics \
  -d '{"names": ["python", "cli", "agent"]}'

# Change description / homepage
curl -s -X PATCH \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO \
  -d '{"description": "Updated", "homepage": "https://example.com"}'

# Archive
curl -s -X PATCH \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO \
  -d '{"archived": true}'
```

### 2.5 Releases

```bash
# gh (cleanest)
gh release create v1.2.3 --title "v1.2.3" --notes "Bug fixes"
gh release upload v1.2.3 ./dist/*.tar.gz
gh release list

# API — see references/github-api-cheatsheet.md
```

### 2.6 Secrets & Variables

```bash
# gh
gh secret set MY_SECRET --body "value"
gh secret list

# API (requires libsodium public-key encryption — see gh docs)
curl -s -X PUT \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/$OWNER/$REPO/actions/secrets/$MY_SECRET \
  -d '{"encrypted_value": "<base64-libsodium-encrypted>", "key_id": "<public-key-id>"}'
```

For a full endpoint reference, see `references/github-api-cheatsheet.md`.

> **Using a private repo as a backup/artifact store** (tarballs,
> release notes, Contents-API index) is a different shape than
> release-per-tag for code. See `references/github-backup-store.md`
> and `scripts/build-server-backup.sh` for the full pattern.

### 2.7 Cloning vs Forking — When to Use Each

- **Clone** when you have write access and will not be sending PRs
  upstream.
- **Fork** when you do not have write access, or when you want to
  contribute back via PR from your own copy.
- **Branch in a clone you already own** when collaborating within a
  team that has access.

---

## 3. Code Review *(was: `github-code-review`)*

### 3.1 Reviewing Local Changes (Pre-Push)

This is pure `git` — works everywhere, no API needed.

#### Get the Diff

```bash
git diff --staged             # what would be committed
git diff main...HEAD          # what a PR would contain
git diff main...HEAD --name-only
git diff main...HEAD --stat
```

#### Review Strategy

1. **Get the big picture first:**

   ```bash
   git diff main...HEAD --stat
   git log main..HEAD --oneline
   ```

2. **Review file by file** — use `read_file` on changed files for full
   context, and the diff to see what changed:

   ```bash
   git diff main...HEAD -- src/auth/login.py
   ```

3. **Check for common issues:**

   ```bash
   # Debug statements, TODOs, console.logs left behind
   git diff main...HEAD | grep -n "print\|console\.log\|TODO\|FIXME\|HACK\|XXX\|debugger"

   # Large files accidentally staged
   git diff main...HEAD --stat | sort -t'|' -k2 -rn | head -10

   # Secrets or credential patterns
   git diff main...HEAD | grep -in "password\|secret\|api_key\|token.*=\|private_key"

   # Merge conflict markers
   git diff main...HEAD | grep -n "<<<<<<\|>>>>>>\|======="
   ```

4. **Present structured feedback** to the user using the format in
   `references/review-output-template.md` (Critical / Warnings /
   Suggestions / Looks Good).

### 3.2 Reviewing a Pull Request on GitHub

#### View PR Details

```bash
# gh
gh pr view 42
gh pr view 42 --json files,title,body,additions,deletions
gh pr diff 42

# curl
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/42
```

#### File-by-File Review

```bash
gh pr view 42 --json files --jq '.files[].path'
gh pr diff 42 -- path/to/file.py
```

#### Leave Inline Review Comments

```bash
# gh (cleanest for review submissions)
gh pr review 42 --comment --body "Overall: looks good. Two nits."
gh pr review 42 --request-changes --body "Needs work — see comments."
gh pr review 42 --approve

# API
curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/42/reviews \
  -d '{
    "commit_id": "<SHA>",
    "event": "REQUEST_CHANGES",
    "body": "Please address the SQL injection in auth.py:45",
    "comments": [
      {
        "path": "src/auth.py",
        "line": 45,
        "body": "Use parameterized queries — this is a SQL injection vector."
      }
    ]
  }'
```

#### Request Reviewers

```bash
# gh
gh pr edit 42 --add-reviewer user1,user2

# API
curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/42/requested_reviewers \
  -d '{"reviewers": ["user1", "user2"]}'
```

For the canonical review comment format, see
`references/review-output-template.md`.

### 3.3 Code Review Pitfalls

- **Reviewing your own work is unreliable.** The
  `requesting-code-review` skill in `software-development/` covers the
  pre-commit auto-review pattern (3 parallel reviewers, one fix loop).
  Use it BEFORE pushing. Use THIS skill for reviewing OTHER people's
  PRs.
- **Large diffs hide real issues.** If `git diff main...HEAD --stat`
  shows > 500 lines changed, ask the author to split it into stacked
  PRs — reviewing 1500 lines of mixed concerns is a recipe for rubber
  stamps.
- **Missing CI?** Don't approve until CI is green. `gh pr checks` is
  the fastest check.

---

## 4. Issues *(was: `github-issues`)*

### 4.1 Viewing Issues

```bash
# gh
gh issue list
gh issue list --state open --label "bug"
gh issue list --assignee @me
gh issue list --search "authentication error" --state all
gh issue view 42

# curl — note: PRs appear in /issues too, filter them out
curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO/issues?state=open&per_page=20" \
  | python3 -c "
import sys, json
for i in json.load(sys.stdin):
    if 'pull_request' not in i:
        labels = ', '.join(l['name'] for l in i['labels'])
        print(f'#{i[\"number\"]:5}  {i[\"state\"]:6}  {labels:30}  {i[\"title\"]}')"

# Filter by label
curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO/issues?state=open&labels=bug&per_page=20" \
  | python3 -c "
import sys, json
for i in json.load(sys.stdin):
    if 'pull_request' not in i:
        print(f'#{i[\"number\"]}  {i[\"title\"]}')"

# Search
curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/search/issues?q=authentication+error+repo:$OWNER/$REPO" \
  | python3 -c "
import sys, json
for i in json.load(sys.stdin)['items']:
    print(f'#{i[\"number\"]}  {i[\"state\"]:6}  {i[\"title\"]}')"
```

### 4.2 Creating Issues

Use `templates/issue-bug-report.md` for bug reports and
`templates/issue-feature-request.md` for feature requests.

```bash
# gh
gh issue create \
  --title "Login redirect ignores ?next= parameter" \
  --body-file templates/issue-bug-report.md \
  --label "bug,backend" \
  --assignee "username"

# curl
BODY=$(cat templates/issue-bug-report.md | jq -Rs .)
curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/issues \
  -d "{
    \"title\": \"Login redirect ignores ?next= parameter\",
    \"body\": $BODY,
    \"labels\": [\"bug\", \"backend\"],
    \"assignees\": [\"username\"]
  }"
```

### 4.3 Triaging

```bash
gh issue edit 42 --add-label "priority:high" --remove-label "needs-triage"
gh issue edit 42 --add-assignee @me
gh issue edit 42 --milestone "v1.2.0"

# Bulk triage
for n in 40 41 42 43; do
  gh issue edit $n --add-label "needs-triage" --remove-label "untriaged"
done
```

### 4.4 Closing & Linking

```bash
gh issue close 42 --comment "Fixed in #47"
gh issue close 42 --reason "not planned"

# Link to PR (use "Closes #N" in PR body for auto-close)
gh pr create --title "fix: redirect bug" --body "Closes #42"
```

### 4.5 Issue Pitfalls

- **PRs appear in `/issues`.** Filter with
  `if 'pull_request' not in i:` when using curl.
- **Label/assignee names are case-sensitive** in the API. Match the
  repo's existing labels exactly.
- **`hermes webhook subscribe github-issues`** can push issue events
  into a webhook consumer — see
  `autonomous-ai-agents/hermes-agent/references/webhooks.md` for the
  setup pattern.

---

## 5. PR Workflow *(was: `github-pr-workflow`)*

Complete guide for managing the PR lifecycle. Each section shows the
`gh` way first, then the `git` + `curl` fallback.

### 5.1 Branch Creation

Pure `git` — identical either way:

```bash
git fetch origin
git checkout main && git pull origin main
git checkout -b feat/add-user-authentication
```

Branch naming conventions:

- `feat/description` — new features
- `fix/description` — bug fixes
- `refactor/description` — code restructuring
- `docs/description` — documentation
- `ci/description` — CI/CD changes

### 5.2 Making Commits

```bash
git add src/auth.py src/models/user.py tests/test_auth.py
git commit -m "feat: add JWT-based user authentication

- Add login/register endpoints
- Add User model with password hashing
- Add auth middleware for protected routes
- Add unit tests for auth flow"
```

Commit message format (Conventional Commits) — full reference in
`references/conventional-commits.md`:

```
type(scope): short description

Longer explanation if needed. Wrap at 72 characters.
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `ci`, `chore`, `perf`.

### 5.3 Pushing and Creating a PR

#### Push the Branch

```bash
git push -u origin HEAD
```

#### Create the PR

**With `gh`:**

```bash
gh pr create \
  --title "feat: add JWT-based user authentication" \
  --body-file templates/pr-body-feature.md \
  --reviewer user1,user2 \
  --label "enhancement" \
  --base develop
```

Options: `--draft`, `--reviewer user1,user2`, `--label "enhancement"`,
`--base develop`.

**With `git` + `curl`:**

```bash
BRANCH=$(git branch --show-current)
BODY=$(cat templates/pr-body-feature.md | jq -Rs .)

curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/$OWNER/$REPO/pulls \
  -d "{
    \"title\": \"feat: add JWT-based user authentication\",
    \"body\": $BODY,
    \"head\": \"\$BRANCH\",
    \"base\": \"main\"
  }"
```

Use `templates/pr-body-bugfix.md` for bug-fix PRs and
`templates/pr-body-feature.md` for feature PRs.

The response JSON includes the PR `number` — save it for later
commands. To create as a draft, add `"draft": true` to the JSON body.

### 5.4 Monitoring CI Status

#### Check CI Status

```bash
# One-shot
gh pr checks

# Watch until all checks finish (polls every 10s)
gh pr checks --watch
```

**With `curl`:**

```bash
# Get the latest commit SHA
SHA=$(git rev-parse HEAD)

# Combined status
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/commits/$SHA/status

# Actions check runs (separate endpoint)
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/commits/$SHA/check-runs
```

#### Poll Until Complete

```bash
SHA=$(git rev-parse HEAD)
for i in $(seq 1 20); do
  STATUS=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
    https://api.github.com/repos/$OWNER/$REPO/commits/$SHA/status \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['state'])")
  echo "Check $i: $STATUS"
  if [ "$STATUS" = "success" ] || [ "$STATUS" = "failure" ] || [ "$STATUS" = "error" ]; then
    break
  fi
  sleep 30
done
```

### 5.5 Auto-Fixing CI Failures

When CI fails, diagnose and fix. Full troubleshooting reference in
`references/ci-troubleshooting.md`.

**Step 1 — Get failure details:**

```bash
# gh
gh run list --branch $(git branch --show-current) --limit 5
gh run view <RUN_ID> --log-failed

# curl
RUN_ID=<run_id>
curl -s -L -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/actions/runs/$RUN_ID/logs \
  -o /tmp/ci-logs.zip
cd /tmp && unzip -o ci-logs.zip -d ci-logs && cat ci-logs/*.txt
```

**Step 2 — Fix and push:**

```bash
git add <fixed_files>
git commit -m "fix: resolve CI failure in <check_name>"
git push
```

**Step 3 — Verify:** re-check CI status from §5.4.

**Auto-fix loop pattern:** when asked to auto-fix CI:

1. Check CI status → identify failures.
2. Read failure logs → understand the error.
3. Use `read_file` + `patch`/`write_file` → fix the code.
4. `git add . && git commit -m "fix: ..." && git push`.
5. Wait for CI → re-check status.
6. Repeat if still failing (up to 3 attempts, then ask the user).

### 5.6 Merging

```bash
# Squash + delete branch (cleanest for feature branches)
gh pr merge --squash --delete-branch

# Enable auto-merge
gh pr merge --auto --squash --delete-branch
```

**With `curl`:**

```bash
PR_NUMBER=<number>

curl -s -X PUT \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER/merge \
  -d "{
    \"merge_method\": \"squash\",
    \"commit_title\": \"feat: add user authentication (#$PR_NUMBER)\"
  }"

BRANCH=$(git branch --show-current)
git push origin --delete $BRANCH
git checkout main && git pull origin main
git branch -d $BRANCH
```

Merge methods: `"merge"` (merge commit), `"squash"`, `"rebase"`.

#### Enable Auto-Merge (curl — uses GraphQL)

```bash
PR_NODE_ID=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['node_id'])")

QUERY=$(printf '{"query": "mutation { enablePullRequestAutoMerge(input: {pullRequestId: \\"%s\\", mergeMethod: SQUASH}) { clientMutationId } }"}' "$PR_NODE_ID")
curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  https://api.github.com/graphql \
  -d "$QUERY"
```

### 5.7 Complete Workflow Example

```bash
# 1. Start from clean main
git checkout main && git pull origin main

# 2. Branch
git checkout -b fix/login-redirect-bug

# 3. (Agent makes code changes with file tools)

# 4. Commit
git add src/auth/login.py tests/test_login.py
git commit -m "fix: correct redirect URL after login

Preserves the ?next= parameter instead of always redirecting to /dashboard."

# 5. Push
git push -u origin HEAD

# 6. Create PR
gh pr create --title "fix: login redirect" --body-file templates/pr-body-bugfix.md

# 7. Monitor CI (§5.4)

# 8. Merge when green (§5.6)
```

### 5.8 Useful PR Commands Reference

| Action | gh | git + curl |
|--------|-----|-----------|
| List my PRs | `gh pr list --author @me` | `curl -s -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/repos/$OWNER/$REPO/pulls?state=open"` |
| View PR diff | `gh pr diff` | `git diff main...HEAD` (local) or `curl -H "Accept: application/vnd.github.diff" ...` |
| Add comment | `gh pr comment N --body "..."` | `curl -X POST .../issues/N/comments -d '{"body":"..."}'` |
| Request review | `gh pr edit N --add-reviewer user` | `curl -X POST .../pulls/N/requested_reviewers -d '{"reviewers":["user"]}'` |
| Close PR | `gh pr close N` | `curl -X PATCH .../pulls/N -d '{"state":"closed"}'` |
| Check out someone's PR | `gh pr checkout N` | `git fetch origin pull/N/head:pr-N && git checkout pr-N` |

---

## 6. References

| File | Purpose |
|------|---------|
| `references/ci-troubleshooting.md` | Common CI failure patterns, log reading |
| `references/conventional-commits.md` | Commit message format reference |
| `references/github-api-cheatsheet.md` | Full REST/GraphQL endpoint reference |
| `references/github-backup-store.md` | **Using a private GitHub repo as a backup/artifact store** (releases for the tarball + Contents API for the index) — useful for periodic server-state snapshots, not code release flow |
| `references/review-output-template.md` | Canonical PR review comment format |

## 7. Templates

| File | Purpose |
|------|---------|
| `templates/pr-body-bugfix.md` | PR body for bug fixes |
| `templates/pr-body-feature.md` | PR body for new features |
| `templates/issue-bug-report.md` | Issue body for bug reports |
| `templates/issue-feature-request.md` | Issue body for feature requests |

## 8. Helper Scripts

| File | Purpose |
|------|---------|
| `scripts/gh-env.sh` | Source to set `GH_AUTH_METHOD`, `GITHUB_TOKEN`, `GH_USER`, `GH_OWNER`, `GH_REPO` |
| `scripts/build-server-backup.sh` | Re-runnable server-state backup: `tar.gz` + `sha256` → `gh release create` + Contents API for manifest/excludes. See `references/github-backup-store.md` for the design. |
