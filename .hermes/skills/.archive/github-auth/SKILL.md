---
name: github-auth
description: "GitHub auth setup: HTTPS tokens, SSH keys, gh CLI login."
version: 1.3.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [GitHub, Authentication, Git, gh-cli, SSH, Setup]
    related_skills: [github-pr-workflow, github-code-review, github-issues, github-repo-management]
---

# GitHub Authentication Setup

This skill sets up authentication so the agent can work with GitHub repositories, PRs, issues, and CI. It covers two paths:

- **`git` (always available)** — uses HTTPS personal access tokens or SSH keys
- **`gh` CLI (if installed)** — richer GitHub API access with a simpler auth flow

## Detection Flow

When a user asks you to work with GitHub, run this check first:

```bash
# Check what's available
git --version
gh --version 2>/dev/null || echo "gh not installed"

# Check if already authenticated
gh auth status 2>/dev/null || echo "gh not authenticated"
git config --global credential.helper 2>/dev/null || echo "no git credential helper"
```

**Decision tree:**
1. If `gh auth status` shows authenticated → you're good, use `gh` for everything
2. If `gh` is installed but not authenticated → use "gh auth" method below
3. If `gh` is not installed → use "git-only" method below (no sudo needed)

> **`gh` missing silently breaks other skills.** The companion skills
> `github-pr-workflow`, `github-issues`, `github-code-review`, and
> `github-repo-management` all assume `gh` is available for issue
> creation, PR opens, and API calls. When `gh` is not installed, they
> fail with `gh: command not found` mid-operation. Detection Flow
> above tells YOU — also tell the user before any non-trivial
> github work begins, because installing `gh` requires either sudo
> or a user-binary download from
> https://github.com/cli/cli/releases.

## Diagnostic Procedure (Use When "Is GitHub Working?" Is The Question)

When a user asks the agent to verify or report on its GitHub
connectivity (e.g. "проверь подключение к GitHub", "does Hermes
have GitHub access?", "is the auth still good?"), run this ordered
sequence. Every step is independent and pure — no auth used unless
the step explicitly requires it. Run them as one script and report
results verbatim. Total runtime ~5s on a healthy box.

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
echo "exit=$?   (exit=1 + greeting = success — GitHub's 'no shell' response)"

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
env | grep -iE 'github|gh_token' | sed 's/=.*\(........\)$/=***\1/' \
  || echo "no github env"
awk -F= '/^GITHUB_TOKEN=/{print "GITHUB_TOKEN set, length="length($2)" prefix="substr($2,1,4)}' \
  ~/.hermes/.env 2>/dev/null || echo "no GITHUB_TOKEN in .env"

echo "── 10. Anonymous API probe ──"
curl -sS -m 8 -o /dev/null -w 'HTTP=%{http_code} time=%{time_total}s\n' \
  https://api.github.com/

echo "── 11. Real git operation over SSH ──"
GIT_TERMINAL_PROMPT=0 \
  git ls-remote git@github.com:octocat/Hello-World.git 2>&1 | head -3

echo "── 12. Real git operation over HTTPS (proves the rewrite works) ──"
GIT_TERMINAL_PROMPT=0 \
  git ls-remote https://github.com/octocat/Hello-World.git 2>&1 | head -3
```

**What to look for in the output (verdict matrix):**

| Step | Healthy | Broken |
|------|---------|--------|
| 1 | git + ssh present, `gh` may be missing | any of git/ssh missing → fatal |
| 3 | `Hi <user>! You've successfully authenticated, but GitHub does not provide shell access.` (exit=1) | `Permission denied (publickey)` or `Connection refused` |
| 4 | single `Offering public key: ~/.ssh/id_ed25519` + `Authenticated to github.com ... using "publickey"` | no `Offering` line → no key reachable; multiple `Offering` lines → `IdentitiesOnly yes` is missing in `~/.ssh/config` (see pitfall below) |
| 7 | `user.name` + `user.email` + the `url.*.insteadof` rewrite present | missing identity → commits will fail; missing rewrite → https URLs hit unauthenticated path |
| 10 | `HTTP=200 time<1s` | `HTTP=000` or timeout → outbound to api.github.com blocked (firewall/ISP) |
| 11 & 12 | identical ref lists, exit=0, no prompt | different/empty lists → rewrite broken or key not authorized for the repo |
| `hermes status` | `GitHub` provider line optional; it only reflects `GITHUB_TOKEN` presence, not git auth | `GitHub ✗` is **not** a connectivity verdict — it just means no API token in `.env`. The SSH channel can still be 100% working. |

**Always distinguish "git auth" from "API auth"** in the report.
They are independent: SSH key handles the first, GITHUB_TOKEN
handles the second. Telling the user "GitHub is broken" when only
the API token is missing is a false alarm.

### Pitfall: `gh` does NOT do anonymous API calls on this host (Ubuntu noble, gh ≥ 2.40)

Verified 2026-06-15 on `twc1.net` (Ubuntu 24.04.4 LTS, `gh 2.45.0`):
the same anonymous endpoint that returns 200 from `curl` returns
"To get started with GitHub CLI, please run: gh auth login" from
`gh api`. Concretely:

```bash
# WORKS — anonymous REST is fine
$ curl -sS -m 8 -o /dev/null -w '%{http_code}\n' https://api.github.com/users/kuznetsovrost-svg
200

# FAILS — gh refuses to call without a token
$ gh api /users/kuznetsovrost-svg --jq '.login'
To get started with GitHub CLI, please run:  gh auth login
```

This applies to **all** `gh` subcommands that hit the API
(`gh api`, `gh repo list`, `gh issue list`, `gh pr list` — even
on public repos). It is a build-time behavior of `gh` ≥ 2.40
(stricter auth requirements were added upstream), not a
connectivity problem. **Do not** let it look like "GitHub is
down" or "the host is firewalled" in your report — the channel
is healthy, only the wrapper is gated.

**Implications for the diagnostic procedure above:**

- Step 10 (anonymous API probe via `curl`) stays authoritative.
  Use it, not `gh api /`, to answer "is the REST channel up?".
- The "Helper: Detect Auth Method" block at the bottom is
  still the right logic, but the "use `gh`" branch only fires
  after `gh auth status` succeeds — never before.
- If the user asks "just use gh" while no token is configured,
  expect every `gh api` call to fail with the same message.
  Fix the auth first (PAT or `gh auth login`); don't try to
  coerce `gh` into anonymous mode.

**`gh` is still useful even without API auth** — `gh repo view`,
`gh issue view <num> --repo <owner>/<repo>`, etc. may work for
public repos on some `gh` versions if they fall back to git
remote + HTML scraping, but do not rely on this. Treat the
"no token → no `gh api`" rule as the safe default.

### Pitfall: `apt-get update` for external repos can hang

When installing `gh` on a freshly-provisioned Ubuntu host, the
GitHub-CLI apt repo (`https://cli.github.com/packages`) has been
observed to stall `apt-get update` past a 180s timeout in this
environment. Before going to that path, check whether `gh` is
already in the distro's universe repo:

```bash
apt-cache policy gh | head -10
```

On Ubuntu 24.04 (noble), `gh 2.45.0` is in
`noble-updates/universe` — install with plain
`apt-get install -y gh` and no external repo. Faster, no GPG
key management, no third-party mirror risk. Add the
`https://cli.github.com/packages` repo only if you need a newer
version than the distro ships.

After install, verify in one shot:

```bash
which gh && gh --version | head -1
# Expect: /usr/bin/gh
#         gh version 2.45.0 (2025-07-18 Ubuntu 2.45.0-ubuntuN)
```

If `which gh` succeeds but `gh --version` shows an older commit
hash (e.g. `2.40.x` from a previous external-repo install),
uninstall first (`apt-get remove -y gh`) and re-install from
universe to avoid two competing binaries on `$PATH`.

---

## Method 1: Git-Only Authentication (No gh, No sudo)

This works on any machine with `git` installed. No root access needed.

### Option A: HTTPS with Personal Access Token (Recommended)

This is the most portable method — works everywhere, no SSH config needed.

**Step 1: Create a personal access token**

Tell the user to go to: **https://github.com/settings/tokens**

- Click "Generate new token (classic)"
- Give it a name like "hermes-agent"
- Select scopes:
  - `repo` (full repository access — read, write, push, PRs)
  - `workflow` (trigger and manage GitHub Actions)
  - `read:org` (if working with organization repos)
- Set expiration (90 days is a good default)
- Copy the token — it won't be shown again

**Step 2: Configure git to store the token**

```bash
# Set up the credential helper to cache credentials
# "store" saves to ~/.git-credentials in plaintext (simple, persistent)
git config --global credential.helper store

# Now do a test operation that triggers auth — git will prompt for credentials
# Username: <their-github-username>
# Password: <paste the personal access token, NOT their GitHub password>
git ls-remote https://github.com/<their-username>/<any-repo>.git
```

After entering credentials once, they're saved and reused for all future operations.

**Alternative: cache helper (credentials expire from memory)**

```bash
# Cache in memory for 8 hours (28800 seconds) instead of saving to disk
git config --global credential.helper 'cache --timeout=28800'
```

**Alternative: set the token directly in the remote URL (per-repo)**

```bash
# Embed token in the remote URL (avoids credential prompts entirely)
git remote set-url origin https://<username>:<token>@github.com/<owner>/<repo>.git
the auto-generated address.

---

## Method 2: gh CLI Authentication
# Test push access (this should work without any prompts now)
git ls-remote https://github.com/<their-username>/<any-repo>.git

# Verify identity
git config --global user.name
git config --global user.email
```

### Option B: SSH Key Authentication

Good for users who prefer SSH or already have keys set up.

**Step 1: Check for existing SSH keys**

```bash
ls -la ~/.ssh/id_*.pub 2>/dev/null || echo "No SSH keys found"
```

**Step 2: Generate a key if needed**

```bash
# Generate an ed25519 key (modern, secure, fast)
ssh-keygen -t ed25519 -C "their-email@example.com" -f ~/.ssh/id_ed25519 -N ""

# Display the public key for them to add to GitHub
cat ~/.ssh/id_ed25519.pub
```

Tell the user to add the public key at: **https://github.com/settings/keys**
- Click "New SSH key"
- Paste the public key content
- Give it a title like "hermes-agent-<machine-name>"

### Step 3: Test the connection

```bash
ssh -T git@github.com
# Expected: "Hi <username>! You've successfully authenticated, but GitHub does not provide shell access."
# IMPORTANT: exit code is 1 on success (GitHub's "no shell" response).
# Do NOT treat exit=1 as a failure — judge by the greeting line, not the code.
```

### Step 4: Configure git to use SSH for GitHub

```bash
# Rewrite HTTPS GitHub URLs to SSH automatically
git config --global url."git@github.com:".insteadOf "https://github.com/"
```

> **Gotcha:** `insteadOf` rewrites *every* `https://github.com/...` URL — including HTTPS URLs that embed a fine-grained PAT (`x-access-token:...@github.com/...`). Usually fine, but if you intentionally use a token-embedded HTTPS URL for a specific repo (e.g. different account, fine-grained scope), set that remote URL *after* configuring the rewrite, or use `insteadOf` with a more specific pattern.

### Step 5: Pin the key with `IdentitiesOnly yes`

If you have multiple SSH keys in `~/.ssh/` (very common — e.g.
`id_ed25519_github_personal` + `id_ed25519_github_work` +
`id_ed25519_hermes_bot`), OpenSSH offers them to the server
*one-by-one* by default. The first one GitHub accepts is used.
That has two failure modes:

1. **Wrong account.** Key A is bound to GitHub user A, key B to
   user B. SSH picks A first, succeeds, and you accidentally
   pushed to A's account. Verification (`ssh -T`) succeeded
   with the wrong identity.
2. **Slow / noisy.** 5 keys × 2 attempts each = 10 round-trips
   before connection, plus `Too many authentication failures`
   errors when the server rate-limits.

Fix: pin the key in `~/.ssh/config` with `IdentitiesOnly yes`:

```bash
Host github.com
    HostName github.com
    User git
    Port 22
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    PreferredAuthentications publickey
```

Verification of correct pinning: `ssh -T -v git@github.com 2>&1 |
grep -E 'Offering|Authenticated'` shows **exactly one** `Offering`
line for the intended key, and `Authenticated to github.com ...
using "publickey"`.

A full ready-to-paste config (with multiplexing + a 443 fallback
alias `github-443` that uses `ssh.github.com:443` for when 22/tcp
is firewalled) lives at `templates/ssh-config-github`.

### Step 6: Configure git identity

```bash
git config --global user.name "Their Name"
git config --global user.email "their-email@example.com"
```
the auto-generated address.

---

## Method 2: gh CLI Authentication

If `gh` is installed, it handles both API access and git credentials in one step.

### Interactive Browser Login (Desktop)

```bash
gh auth login
# Select: GitHub.com
# Select: HTTPS
# Authenticate via browser
```

### Token-Based Login (Headless / SSH Servers)

```bash
echo "<THEIR_TOKEN>" | gh auth login --with-token

# Set up git credentials through gh
gh auth setup-git
```

### Headless / Remote Box: `gh auth login --web` (device flow)

Use this when you're on a remote host (SSH session, no display)
but the **user** is at a desktop with a browser. `--web` makes
`gh` print a one-time code and a URL; the user pastes the code
into github.com/login/device on their own browser and confirms
login. The token never has to cross the chat/terminal boundary
— `gh` polls GitHub internally.

```bash
# Run in the background so it can wait for the user to confirm;
# notify_on_complete so the agent loop wakes up when login finishes.
gh auth login --hostname github.com --git-protocol ssh --web
```

> **`--git-protocol ssh`** is the right choice when the host
> already has an authorized SSH key — it leaves git operations
> on the SSH path (no PAT needed for `git push`). Use
> `--git-protocol https` if you want the token itself to handle
> git auth (e.g. one-time token rotation, no SSH key in GitHub).

The agent must:

1. Start the process in the **background** (terminal default
   foreground times out at ~30–60s; device flow waits for the
   user, not the system).
2. Wait for `! First copy your one-time code:` to appear in
   stdout, then echo the code and the URL back to the user
   *verbatim* in the next turn.
3. Wait for the `[IMPORTANT: Background process ... completed]`
   notification (exit code 0 + `✓ Logged in as <user>` line).
4. Verify with `gh auth status` and a `gh api user --jq .login`.

**Pitfall — TTY prompts block the device-flow output.** When
`gh` runs without a TTY (e.g. inside `terminal()` without
`pty=true`, or piped from `cron`), it still prompts for
"Authentication method" and "Git protocol" *before* printing the
code. Two escapes:

- Pre-answer with `printf 'web\nssh\n\n' | gh auth login ...`
  (the two `\n` after `ssh` are empty responses for any
  leftover prompts — they go to stderr, harmless).
- Or set `GH_PROMPT_DISABLED=1` and pass `--git-protocol ssh`
  explicitly; `gh` will skip the protocol question but still
  ask for the auth method. Combine with `printf` above for
  full headless.

**Pitfall — codes are short-lived (~15 min) and per-process.**
Each `gh auth login --web` run gets a brand-new code. If the
user takes too long, kill the background process and restart;
do not assume the previous code is still valid.

**Pitfall — multiple concurrent `--web` runs collide.** If you
start a second `gh auth login --web` while a first is still
waiting, the new one prints its own code but the user's
browser session is already bound to the first. Kill the stale
one first (`process(action='kill', session_id=...)`) before
reissuing.

### Verify

```bash
gh auth status
# Expect:
#   ✓ Logged in to github.com account <user> (/root/.config/gh/hosts.yml)
#   - Git operations protocol: ssh
#   - Token: gho_************************************
#   - Token scopes: 'gist', 'read:org', 'repo'  (whatever scopes were granted)
```

```bash
# Sanity-check the token is actually usable
gh api user --jq '{login, id, public_repos}'
gh api rate_limit --jq '.resources.core | {limit, used, remaining}'
# Expect: limit=5000 for authed core (was 60 when anonymous)
```

---

## Using the GitHub API Without gh

When `gh` is not available, you can still access the full GitHub API using `curl` with a personal access token. This is how the other GitHub skills implement their fallbacks.

### Setting the Token for API Calls

```bash
# Option 1: Export as env var (preferred — keeps it out of commands)
export GITHUB_TOKEN="<token>"

# Then use in curl calls:
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/user
```

### Extracting the Token from Git Credentials

If git credentials are already configured (via credential.helper store), the token can be extracted:

```bash
# Read from git credential store
grep "github.com" ~/.git-credentials 2>/dev/null | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|'
```

### Helper: Detect Auth Method

Use this pattern at the start of any GitHub workflow:

```bash
# Try gh first, fall back to git + curl
if command -v gh &>/dev/null && gh auth status &>/dev/null; then
  echo "AUTH_METHOD=gh"
elif [ -n "$GITHUB_TOKEN" ]; then
  echo "AUTH_METHOD=curl"
elif [ -f ~/.hermes/.env ] && grep -q "^GITHUB_TOKEN=" ~/.hermes/.env; then
  export GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" ~/.hermes/.env | head -1 | cut -d= -f2 | tr -d '\n\r')
  echo "AUTH_METHOD=curl"
elif grep -q "github.com" ~/.git-credentials 2>/dev/null; then
  export GITHUB_TOKEN=$(grep "github.com" ~/.git-credentials | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|')
  echo "AUTH_METHOD=curl"
else
  echo "AUTH_METHOD=none"
  echo "Need to set up authentication first"
fi
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `git push` asks for password | GitHub disabled password auth. Use a personal access token as the password, or switch to SSH |
| `remote: Permission to X denied` | Token may lack `repo` scope — regenerate with correct scopes |
| `fatal: Authentication failed` | Cached credentials may be stale — run `git credential reject` then re-authenticate |
| `ssh: connect to host github.com port 22: Connection refused` | Try SSH over HTTPS port: add a `github-443` host alias with `Hostname ssh.github.com` and `Port 443` to `~/.ssh/config`, then use `git@github-443:owner/repo.git`. A ready-to-paste config is at `templates/ssh-config-github`. Remember to also `ssh-keyscan -H -t rsa,ecdsa,ed25519 ssh.github.com >> ~/.ssh/known_hosts` (public host keys, safe) — otherwise you'll get `Host key verification failed` on first connect. |
| Credentials not persisting | Check `git config --global credential.helper` — must be `store` or `cache` |
| Multiple GitHub accounts | Use SSH with different keys per host alias in `~/.ssh/config`, or per-repo credential URLs |
| `gh: command not found` + no sudo | Use git-only Method 1 above — no installation needed |
