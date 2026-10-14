# SKILL-EXAMPLE.md
> **Сборник трёх github-скиллов профиля `default` Hermes Agent.**
> Источники: `~/.hermes/skills/github/*/SKILL.md`.
> Скомпоновано как единый демонстрационный файл, чтобы было видно, как устроен скилл в Hermes
> (frontmatter → WHEN TO USE → STEP-BY-STEP → STACK BY LANGUAGE → PITFALLS → VERIFICATION).

---

## Содержание

1. [codebase-inspection](#1-codebase-inspection) — анализ кодовой базы через pygount: LOC, языки, доли
2. [github-contents-api](#2-github-contents-api) — создание/обновление файла через Contents API одной PUT
3. [github-pr-workflow](#3-github-pr-workflow) — полный PR-цикл: auth, review, triage, lifecycle

---

# 1. codebase-inspection

> Источник: `/root/.hermes/skills/github/codebase-inspection/SKILL.md`

```skill
1|---
2|name: codebase-inspection
3|description: "Inspect codebases w/ pygount: LOC, languages, ratios."
4|version: 1.0.0
5|author: Hermes Agent
6|license: MIT
7|platforms: [linux, macos, windows]
8|metadata:
9|  hermes:
10|    tags: [LOC, Code Analysis, pygount, Codebase, Metrics, Repository]
11|    related_skills: [github-pr-workflow]
12|prerequisites:
13|  commands: [pygount]
14|---
15|
16|# Codebase Inspection with pygount
17|
18|Analyze repositories for lines of code, language breakdown, file counts, and code-vs-comment ratios using `pygount`.
19|
20|## When to Use
21|
22|- User asks for LOC (lines of code) count
23|- User wants a language breakdown of a repo
24|- User asks about codebase size or composition
25|- User wants code-vs-comment ratios
26|- General "how big is this repo" questions
27|
28|## Prerequisites
29|
30|```bash
31|pip install --break-system-packages pygount 2>/dev/null || pip install pygount
32|```
33|
34|## 1. Basic Summary (Most Common)
35|
36|Get a full language breakdown with file counts, code lines, and comment lines:
37|
38|```bash
39|cd /path/to/repo
40|pygount --format=summary \
41|  --folders-to-skip=".git,node_modules,venv,.venv,__pycache__,.cache,dist,build,.next,.tox,.eggs,*.egg-info" \
42|  .
43|```
44|
45|**IMPORTANT:** Always use `--folders-to-skip` to exclude dependency/build directories, otherwise pygount will crawl them and take a very long time or hang.
46|
47|## 2. Common Folder Exclusions
48|
49|Adjust based on the project type:
50|
51|```bash
52|# Python projects
53|--folders-to-skip=".git,venv,.venv,__pycache__,.cache,dist,build,.tox,.eggs,.mypy_cache"
54|
55|# JavaScript/TypeScript projects
56|--folders-to-skip=".git,node_modules,dist,build,.next,.cache,.turbo,coverage"
57|
58|# General catch-all
59|--folders-to-skip=".git,node_modules,venv,.venv,__pycache__,.cache,dist,build,.next,.tox,vendor,third_party"
60|```
61|
62|## 3. Filter by Specific Language
63|
64|```bash
65|# Only count Python files
66|pygount --suffix=py --format=summary .
67|
68|# Only count Python and YAML
69|pygount --suffix=py,yaml,yml --format=summary .
70|```
71|
72|## 4. Detailed File-by-File Output
73|
74|```bash
75|# Default format shows per-file breakdown
76|pygount --folders-to-skip=".git,node_modules,venv" .
77|
78|# Sort by code lines (pipe through sort)
79|pygount --folders-to-skip=".git,node_modules,venv" . | sort -t$'\t' -k1 -nr | head -20
80|```
81|
82|## 5. Output Formats
83|
84|```bash
85|# Summary table (default recommendation)
86|pygount --format=summary .
87|
88|# JSON output for programmatic use
89|pygount --format=json .
90|
91|# Pipe-friendly: Language, file count, code, docs, empty, string
92|pygount --format=summary . 2>/dev/null
93|```
94|
95|## 6. Interpreting Results
96|
97|The summary table columns:
98|- **Language** — detected programming language
99|- **Files** — number of files of that language
100|- **Code** — lines of actual code (executable/declarative)
101|- **Comment** — lines that are comments or documentation
102|- **%** — percentage of total
103|
104|Special pseudo-languages:
105|- `__empty__` — empty files
106|- `__binary__` — binary files (images, compiled, etc.)
107|- `__generated__` — auto-generated files (detected heuristically)
108|- `__duplicate__` — files with identical content
109|- `__unknown__` — unrecognized file types
110|
111|## Pitfalls
112|
113|1. **Always exclude .git, node_modules, venv** — without `--folders-to-skip`, pygount will crawl everything and may take minutes or hang on large dependency trees.
114|2. **Markdown shows 0 code lines** — pygount classifies all Markdown content as comments, not code. This is expected behavior.
115|3. **JSON files show low code counts** — pygount may count JSON lines conservatively. For accurate JSON line counts, use `wc -l` directly.
116|4. **Large monorepos** — for very large repos, consider using `--suffix` to target specific languages rather than scanning everything.
117|
```

---

# 2. github-contents-api

> Источник: `/root/.hermes/skills/github/github-contents-api/SKILL.md`

```skill
1|---
2|name: github-contents-api
3|title: GitHub Contents API — folder/file in one call
4|description: "Create or update a file in a GitHub repo (and the folder that contains it) with a single PUT against the Contents API. The minimal, headless-friendly way for an agent to drop a file into a repo without cloning it. Falls back to `gh api` or pure `curl`."
5|version: 1.0.0
6|author: Hermes Agent
7|license: MIT
8|platforms: [linux, macos, windows]
9|metadata:
10|  hermes:
11|    tags: [GitHub, Contents API, File Creation, Headless, Automation, No-Clone]
12|    related_skills: [github-pr-workflow]
13|prerequisites:
14|  commands: [gh]
15|---
16|
17|# GitHub Contents API — drop a file (and its folder) with one PUT
18|
19|The **Contents API** is the cheapest way for an agent to create or update a
20|file in a GitHub repository. Crucially, **Git does not store empty folders
21|** — but the Contents API creates intermediate directories automatically
22|the moment you PUT a file whose `path` contains a folder. So
23|«create folder X and put file Y in it» collapses to a single HTTP request.
24|
25|This skill is the minimal headless counterpart to the heavier
26|`github-pr-workflow` skill. Reach for it when:
27|
28|- You don't want to clone the repo (no local git state, no race conditions).
29|- The change is one or a handful of small files, not a full feature.
30|- You're inside cron, CI, or another agent that just needs to land a file.
31|- You want one commit = one PUT, atomic, no rebase drama.
32|
33|For branch + commit + push + PR workflows, see `github-pr-workflow` instead.
34|
35|## When to use this skill
36|
37|| Trigger | Skill |
38||---|---|
39|| "Создай файл в репо" / "drop a file in this repo" | **this skill** |
40|| "Сделай PR с этими изменениями" / review flow | `github-pr-workflow` |
41|| Many files + history + code review | `github-pr-workflow` |
42|| "Create folder + file" — same as above, single PUT | **this skill** |
43|
44|## Prerequisites
45|
46|- One of: `gh` CLI logged in (`gh auth status` ✓), **or** a `GITHUB_TOKEN`
47|  in `$GITHUB_TOKEN` / `~/.hermes/.env` (see `github-pr-workflow`
48|  §1 for setup).
49|- The token needs `repo` scope (private) or `contents: write` (fine-grained PAT).
50|- `base64` and `curl` (present by default; `gh` brings its own transport).
51|
52|## 1. Auth — one line, two modes
53|
54|```bash
55|source ~/.hermes/skills/github/github-pr-workflow/scripts/gh-env.sh
56|# Sets: GH_AUTH_METHOD ("gh" | "curl" | "none"),
57|#       GH_USER, GH_OWNER, GH_REPO, GITHUB_TOKEN
58|```
59|
60|If `GH_AUTH_METHOD=gh` (the common case on a Hermes box) — proceed with
61|`gh api`. If `curl` — substitute the curl block from §4.
62|
63|## 2. The canonical one-liner
64|
65|```bash
66|# Parameters
67|OWNER="${OWNER:-kuznetsovrost-svg}"
68|REPO="${REPO:-hermes-demo-folder}"
69|FOLDER="${FOLDER:-GitHub_папка_01}"        # intermediate folder (created automatically)
70|FILE="${FILE:-GitHub_папка_01.txt}"        # filename inside the folder
71|BRANCH="${BRANCH:-main}"
72|CONTENT="${CONTENT:-Hello from Hermes @ $(date -u +%FT%TZ)}"
73|COMMIT_MSG="${COMMIT_MSG:-feat: add $FOLDER/$FILE}"
74|
75|# 1. base64-encode the content (NO trailing newline)
76|B64=$(printf '%s' "$CONTENT" | base64 -w0)
77|
78|# 2. For UPDATES, fetch the file's current SHA first (omit on create)
79|SHA=""
80|if gh api "/repos/$OWNER/$REPO/contents/$FOLDER/$FILE" --silent >/dev/null 2>&1; then
81|  SHA=$(gh api "/repos/$OWNER/$REPO/contents/$FOLDER/$FILE" --jq '.sha')
82|fi
83|
84|# 3. PUT the file (folder appears in the tree as a side effect)
85|gh api --method PUT \
86|  -H "Accept: application/vnd.github+json" \
87|  "/repos/$OWNER/$REPO/contents/$FOLDER/$FILE" \
88|  --field message="$COMMIT_MSG" \
89|  --field branch="$BRANCH" \
90|  --field content="$B64" \
91|  $([ -n "$SHA" ] && echo --field "sha=$SHA") \
92|  --jq '.content | {sha: .sha, url: .html_url, path: .path}'
93|```
94|
95|**That's it.** Result is one commit, one new blob, one new tree, one
96|new folder. No `git init`, no rebase, no SSH prompt.
97|
98|## 3. What the API does for you (and what it doesn't)
99|
100|| Concern | Contents API behaviour |
101||---|---|
102|| Intermediate folders in `path` | **Created automatically.** No `mkdir` needed. |
103|| Empty folder only (no file) | **Not supported.** Folders only exist as a side effect of a file. |
104|| Filename with non-ASCII (Cyrillic, emoji) | Works. `gh api` percent-encodes; raw `curl` needs `--data-urlencode path`. |
105|| Updating an existing file | **Must include `"sha": "<existing_blob_sha>"`** — else 422. |
106|| Binary content | base64-encode the bytes (same code path). |
107|| File > 100 MB | **Not supported.** Use a `git push` for releases/large blobs. |
108|| Auth on private repos | Token scope `repo` (classic) or `contents: write` (fine-grained). |
109|| Rate limit | 5000 req/h authenticated. Each PUT = 1 req. |
110|
111|## 4. Pure `curl` fallback (no `gh`)
112|
113|```bash
114|# Set these first:
115|#   GITHUB_TOKEN, OWNER, REPO, FOLDER, FILE, BRANCH, CONTENT, COMMIT_MSG
116|
117|B64=$(printf '%s' "$CONTENT" | base64 -w0)
118|
119|# Optional: fetch existing SHA for updates
120|SHA=$(curl -s -H "Authorization: Bearer ***" \
121|  "https://api.github.com/repos/$OWNER/$REPO/contents/$FOLDER/$FILE" \
122|  | python3 -c "import sys,json; print(json.load(sys.stdin).get('sha',''))" 2>/dev/null)
123|
124|# Build JSON body in a temp file (avoids shell-quoting hell with
125|# newlines and special chars in the message)
126|JSON=$(mktemp)
127|python3 -c "
128|import json, sys
129|body = {
130|    'message': sys.argv[1],
131|    'content': sys.argv[2],
132|    'branch':  sys.argv[3],
133|}
134|if sys.argv[4]:
135|    body['sha'] = sys.argv[4]
136|print(json.dumps(body, ensure_ascii=False))
137|" "$COMMIT_MSG" "$B64" "$BRANCH" "$SHA" > "$JSON"
138|
139|curl -s -X PUT \
140|  -H "Authorization: Bearer ***" \
141|  -H "Accept: application/vnd.github+json" \
142|  --data-binary @"$JSON" \
143|  "https://api.github.com/repos/$OWNER/$REPO/contents/$FOLDER/$FILE"
144|rm -f "$JSON"
145|```
146|
147|## 5. Create-the-repo-then-file (full bootstrap)
148|
149|If the repo doesn't exist yet:
150|
151|```bash
152|gh repo create "$OWNER/$REPO" --public --description "..." --add-readme
153|
154|# Repo is created and you're in it — then proceed with §2.
155|# (Or cd into a clone from elsewhere and use §2.)
156|```
157|
158|Or with a single Contents call against a brand-new repo: create the
159|repo with `gh repo create` first (Contents API requires the repo to
160|exist — auto_init only gives you README, not your file).
161|
162|## 6. Real-world examples
163|
164|### 6.1 Drop a daily report
165|
166|```bash
167|OWNER=acme REPO=daily-digest
168|FOLDER="reports/$(date -u +%Y)/$(date -u +%m)"
169|FILE="$(date -u +%F).md"
170|CONTENT="# Digest for $(date -u +%F)\n\n…markdown body…"
171|# Run the §2 template. `reports/2026/06/` will be created automatically.
172|```
173|
174|### 6.2 Update a single config value
175|
176|```bash
177|# This skill's "fetch SHA → re-PUT with sha" pattern handles updates.
178|# Idempotent: if the content is unchanged, GitHub still creates a new
179|# commit — but it's safe to call on cron.
180|```
181|
182|### 6.3 Add many small files atomically (commits tree, not file)
183|
184|For 2+ files in one commit, use the **Git Tree + Commit + Ref** API
185|flow, not repeated Contents PUTs. See
186|`github-pr-workflow` §5 if you need this.
187|
188|## 7. Verification (always do this!)
189|
190|After the PUT, verify with one of:
191|
192|```bash
193|# Quick: just fetch the file's metadata
194|gh api "/repos/$OWNER/$REPO/contents/$FOLDER/$FILE" \
195|  --jq '{sha: .sha, size: .size, path: .path, html_url: .html_url}'
196|
197|# Strong: list the tree, confirm folder+blob are there
198|gh api "/repos/$OWNER/$REPO/git/trees/$BRANCH?recursive=1" \
199|  --jq ".tree[] | select(.path | startswith(\"$FOLDER/\")) | \"\(.type)  \(.path)  sha=\(.sha[:8])\""
200|
201|# Strongest: fetch the raw bytes
202|curl -fsSL "https://raw.githubusercontent.com/$OWNER/$REPO/$BRANCH/$FOLDER/$FILE"
203|```
204|
205|A successful PUT returns 201 (create) or 200 (update) with the file's
206|new `sha`. If you get 422 — usually missing `sha` for an update, or
207|the parent path was a **file** instead of a folder.
208|
209|## 8. Common errors and fixes
210|
211|| Status | Cause | Fix |
212||---|---|---|
213|| 401 | bad/expired token | `gh auth status`; refresh `GITHUB_TOKEN` |
214|| 403 "Resource not accessible" | PAT lacks `contents: write` | regenerate fine-grained PAT with the right repo + scope |
215|| 404 on PUT | repo/branch doesn't exist | check `OWNER/REPO/BRANCH`; pull first |
216|| 422 "sha" required | updating a file without `sha` | fetch `.sha` from GET, include in body |
217|| 422 "does not match" | you sent the `sha` of the **folder** tree, not the **blob** | the GET response's top-level `.sha` IS the blob sha; the tree sha is under `tree.sha` — use the blob one |
218|| 422 base64 newline | `base64` (GNU) wraps at 76 cols | use `base64 -w0` (Linux) or `base64 | tr -d '\n'` |
219|| 409 conflict | a branch protection / required status check blocks direct push to `main` | push to a feature branch + PR — `github-pr-workflow` §5 |
220|
221|## 9. Pitfalls
222|
223|1. **Git has no empty folders.** A folder only appears in the tree when
224|   a file's path traverses it. Contents API creates the folder as a
225|   side effect of the file PUT — you do **not** need to call anything
226|   else first.
227|2. **Auth ≠ connectivity.** A green `gh auth status` does not mean
228|   `api.github.com` is reachable. The first PUT will tell you. The
229|   `github-pr-workflow` §1.4 diagnostic covers this end-to-end.
230|3. **Branch protection.** If `main` is protected (required reviews,
231|   required status checks), Contents PUT to `main` will 409/422. You
232|   need to PUT to a feature branch and open a PR — see
233|   `github-pr-workflow` §5.6. To check, `gh api
234|   /repos/$OWNER/$REPO/branches/main/protection`.
235|4. **`url.*.insteadof` rewrite.** This host has
236|   `url.git@github.com:.insteadof https://github.com/` set globally.
237|   It affects `git clone` / `git push`, **not** `gh api` / `curl` — the
238|   Contents API calls are safe.
239|5. **Concurrent PUTs racing on the same file.** Two PUTs targeting the
240|   same path with the same old `sha` — the second will 409 ("does not
241|   match"). Re-fetch the new `sha` and retry. For multi-file atomic
242|   commits, use the Git Tree/Commit/Ref API.
243|6. **Token in shell history.** Avoid `Authorization: Bearer
***   $GITHUB_TOKEN` in commands you paste into chat. Prefer the §4
245|   `JSON=$(mktemp) + --data-binary @file` pattern, or just `gh api`
246|   (no token in command line at all).
247|
248|## 10. Minimal copy-paste for cron jobs
249|
250|```bash
251|#!/usr/bin/env bash
252|# cron/drop-file.sh — drop one file into one repo, daily.
253|set -euo pipefail
254|
255|OWNER="${OWNER:-kuznetsovrost-svg}"
256|REPO="${REPO:-my-repo}"
257|FOLDER="${FOLDER:-daily}"
258|FILE="${FILE:-$(date -u +%F).md}"
259|BRANCH="${BRANCH:-main}"
260|COMMIT_MSG="${COMMIT_MSG:-chore: daily drop $FILE}"
261|
262|CONTENT="# $(date -u +%F)\n\nauto-generated.\n"
263|
264|B64=$(printf '%s' "$CONTENT" | base64 -w0)
265|SHA=$(gh api "/repos/$OWNER/$REPO/contents/$FOLDER/$FILE" --jq '.sha' 2>/dev/null || true)
266|
267|ARGS=( --method PUT
268|       -H "Accept: application/vnd.github+json"
269|       "/repos/$OWNER/$REPO/contents/$FOLDER/$FILE"
270|       --field message="$COMMIT_MSG"
271|       --field branch="$BRANCH"
272|       --field content="$B64" )
273|[ -n "$SHA" ] && ARGS+=( --field "sha=$SHA" )
274|
275|gh api "${ARGS[@]}" --jq '"✓ " + .content.path + "  sha=" + .content.sha'
276|```
277|
278|## Related
279|
280|- `github-pr-workflow` — full GitHub surface: auth setup, repo create,
281|  PR lifecycle, code review, issues, releases.
282|  - Quick endpoint reference: `github-pr-workflow/references/github-api-cheatsheet.md`
283|    §"Contents API" (PUT/GET/DELETE on `/repos/{owner}/{repo}/contents/{path}`).
284|- `hermes-agent-vcs-portability` — backup/sync of your Hermes profile
285|  via GitHub (this skill is what that profile-sync actually uses
286|  under the hood).
287|
```

---

# 3. github-pr-workflow

> Источник: `/root/.hermes/skills/github/github-pr-workflow/SKILL.md`

```skill
1|---
2|name: github-pr-workflow
3|title: GitHub Workflows (umbrella)
4|description: "Complete GitHub workflows: auth, repo management, code review, issue triage, and the PR lifecycle. Most operations are pure `git`; the `gh` CLI is preferred when present; `curl` is the universal fallback."
5|version: 2.1.0
6|author: Hermes Agent
7|license: MIT
8|platforms: [linux, macos, windows]
9|metadata:
10|  hermes:
11|    tags: [GitHub, Pull-Requests, CI/CD, Git, Automation, Code-Review, Issues, Auth, Repo-Management]
12|    related_skills: [requesting-code-review, hermes-agent-vcs-portability]
13|---
14|
15|# GitHub Workflows — Umbrella
16|
17|Class-level skill for working with GitHub. Covers the full surface:
18|authentication, repository management, code review, issue triage, and
19|the PR lifecycle. Most operations are pure `git`; the `gh` CLI is preferred
20|when present; `curl` is the universal fallback.
21|
22|If a `gh` CLI is **not** installed, every section below falls back to plain
23|`git` (for read/clone) or `curl` against the GitHub REST/GraphQL API (for
24|PRs, issues, releases). Run Detection Flow in §1 first.
25|
26|## Section Index
27|
28|1. **Auth setup & diagnostics** — choose your auth method, set up `gh` or
29|   `GITHUB_TOKEN`/SSH, run the connectivity diagnostic when something
30|   breaks. *(was: `github-auth`)*
31|2. **Repository management** — clone, create, fork, configure topics,
32|   releases, secrets, teams. *(was: `github-repo-management`)*
33|3. **Code review** — review local changes pre-push, review open PRs on
34|   GitHub, leave inline comments, request reviewers. *(was: `github-code-review`)*
35|4. **Issues** — list, search, create, triage, label, close, link to PRs.
36|   *(was: `github-issues`)*
37|5. **PR workflow** — branch, commit, push, open PR, monitor CI, auto-fix
38|   failures, merge. *(was the original `github-pr-workflow`)*
39|6. **References** — `references/`
40|7. **Templates** — `templates/`
41|8. **Helper scripts** — `scripts/`
42|
43|> **Quick start — the canonical pre-flight for any GitHub work:**
44|>
45|> Source the helper once to set `GH_AUTH_METHOD`, `GITHUB_TOKEN`,
46|> `GH_USER`, `GH_OWNER`, `GH_REPO`:
47|>
48|> ```bash
49|> source scripts/gh-env.sh
50|> echo "Method: $GH_AUTH_METHOD | User: $GH_USER | Repo: $GH_OWNER/$GH_REPO"
51|> ```
52|>
53|> If you can't source, copy the inline detection in §1.1 below.
54|
55|---
56|
57|## 1. Auth Setup & Diagnostics *(was: `github-auth`)*
58|
59|### 1.1 Detection Flow
60|
61|When a user asks you to work with GitHub, run this first:
62|
63|```bash
64|git --version
65|gh --version 2>/dev/null || echo "gh not installed"
66|gh auth status 2>/dev/null || echo "gh not authenticated"
67|git config --global credential.helper 2>/dev/null || echo "no git credential helper"
68|```
69|
70|**Decision tree:**
71|
72|1. `gh auth status` shows authenticated → use `gh` for everything.
73|2. `gh` installed but not authenticated → use `gh auth login` (or set
74|   `GH_TOKEN` / `GITHUB_TOKEN` env var).
75|3. `gh` not installed → use `git` + `GITHUB_TOKEN` / SSH key. **No sudo
76|   required.** Tell the user this requires either installing `gh`
77|   (needs sudo) or a user-binary download from
78|   https://github.com/cli/cli/releases.
79|
80|> **`gh` missing silently breaks other skills.** The PR workflow,
81|> issues, and code-review sections below all assume `gh` is available
82|> for issue creation, PR opens, and API calls. When `gh` is not
83|> installed, they fall back to `curl` + `GITHUB_TOKEN` — set it up
84|> before doing non-trivial GitHub work.
85|
86|### 1.2 Setting up `GITHUB_TOKEN` (no `gh`)
87|
88|1. Create a token at https://github.com/settings/tokens. Scopes needed:
89|   `repo`, `read:org`, `workflow` (for Actions).
90|2. Save to `~/.hermes/.env` (preferred) or export.
91|
92|   ```bash
93|   echo "GITHUB_TOKEN=ghp_REPLACE_ME" >> ~/.hermes/.env
94|   ```
95|
96|3. Verify by sourcing the helper:
97|
98|   ```bash
99|   source scripts/gh-env.sh
100|   echo "Method: $GH_AUTH_METHOD | User: $GH_USER | Repo: $GH_OWNER/$GH_REPO"
101|   ```
102|
103|### 1.3 Setting up SSH
104|
105|The `templates/ssh-config-github` file is a ready-to-append block for
106|`~/.ssh/config`. It is set up to:
107|
108|- Use `IdentitiesOnly yes` (prevents SSH offering every key in
109|  `~/.ssh/` and authenticating to the wrong account).
110|- Use `ControlMaster auto` + `ControlPersist 600` (drops `ls-remote`
111|  latency from ~700ms to ~50ms after the first op).
112|- Provide a `github-443` host fallback when outbound `22/tcp` is
113|  blocked (uses `ssh.github.com:443`).
114|
115|```bash
116|cat templates/ssh-config-github >> ~/.ssh/config
117|chmod 600 ~/.ssh/config
118|
119|# First-use: trust GitHub's host keys (public, safe to automate)
120|ssh-keyscan -H -t rsa,ecdsa,ed25519 ssh.github.com >> ~/.ssh/known_hosts
121|```
122|
123|### 1.4 Connectivity Diagnostic
124|
125|When the user asks "is GitHub working?" or "проверь подключение к
126|GitHub", run this ordered 12-step script. Every step is independent and
127|pure — no auth used unless the step explicitly requires it. Total
128|runtime ~5s on a healthy box. See `references/github-api-cheatsheet.md`
129|for the full endpoint reference.
130|
131|```bash
132|echo "── 1. Tool versions ──"
133|git --version
134|gh --version 2>/dev/null || echo "gh not installed"
135|ssh -V 2>&1 | head -1
136|
137|echo "── 2. gh CLI status ──"
138|gh auth status 2>&1 || echo "gh not authenticated or not installed"
139|
140|echo "── 3. SSH test (BatchMode = no interactive prompt) ──"
141|ssh -T -o BatchMode=yes -o StrictHostKeyChecking=accept-new \
142|  git@github.com 2>&1
143|echo "exit=$?   (exit=1 + greeting = success — GitHub no-shell response)"
144|
145|echo "── 4. Which key was offered (verbose, filtered) ──"
146|ssh -T -v -o BatchMode=yes -o StrictHostKeyChecking=accept-new \
147|  git@github.com 2>&1 | \
148|  grep -E 'Offering|Authenticated|Authentications that can continue'
149|
150|echo "── 5. SSH agent and on-disk keys ──"
151|ssh-add -l 2>&1 || echo "no ssh-agent"
152|ls -la ~/.ssh/id_*.pub 2>/dev/null
153|
154|echo "── 6. SSH config (relevant lines) ──"
155|[ -f ~/.ssh/config ] && grep -A4 -E '^Host github' ~/.ssh/config \
156|  || echo "no ~/.ssh/config"
157|
158|echo "── 7. Global git config ──"
159|git config --global --get user.name
160|git config --global --get user.email
161|git config --global --get-regexp '^url\.'
162|
163|echo "── 8. Credential helper + file ──"
164|git config --global --get-all credential.helper
165|ls -la ~/.git-credentials 2>/dev/null | head -1
166|
167|echo "── 9. GitHub-related env / hermes env tokens (no secret leak) ──"
168|env | grep -iE 'github|gh_token' | sed 's/=.*\(........\)$/=REDACTED\1/' \
169|  || echo "no github env"
170|GITHUB_LEN=$(awk -F= '/^GITHUB_TOKEN=/{print length($2); exit}' ~/.hermes/.env 2>/dev/null)
171|GITHUB_PRE=$(awk -F= '/^GITHUB_TOKEN=/{print substr($2,1,4); exit}' ~/.hermes/.env 2>/dev/null)
172|echo "GITHUB_TOKEN set: length=$GITHUB_LEN prefix=$GITHUB_PRE"
173|
174|echo "── 10. Anonymous API probe ──"
175|curl -sS -m 8 -o /dev/null -w 'HTTP=%{http_code} time=%{time_total}s\n' \
176|  https://api.github.com/
177|
178|echo "── 11. Real git operation over SSH ──"
179|GIT_TERMINAL_PROMPT=0 \
180|  git ls-remote git@github.com:octocat/Hello-World.git 2>&1 | head -3
181|
182|echo "── 12. Real git operation over HTTPS ──"
183|GIT_TERMINAL_PROMPT=0 \
184|  git ls-remote https://github.com/octocat/Hello-World.git 2>&1 | head -3
185|```
186|
187|**Verdict matrix** (what to look for in the output):
188|
189|| Step | Healthy | Broken |
190||------|---------|--------|
191|| 1 | git + ssh present, `gh` may be missing | any of git/ssh missing → fatal |
192|| 3 | `Hi <user>! You've successfully authenticated, but GitHub does not provide shell access.` (exit=1) | `Permission denied (publickey)` or `Connection refused` |
193|| 4 | single `Offering public key: ~/.ssh/id_ed25519` + `Authenticated to github.com ... using "publickey"` | no `Offering` line → no key reachable; multiple `Offering` lines → `IdentitiesOnly yes` missing in `~/.ssh/config` |
194|| 7 | `user.name` + `user.email` + the `url.*.insteadof` rewrite present | missing identity → commits will fail; missing rewrite → https URLs hit unauthenticated path |
195|| 10 | `HTTP=200 time<1s` | `HTTP=000` or timeout → outbound to api.github.com blocked (firewall/ISP) |
196|| 11 & 12 | identical ref lists, exit=0, no prompt | different/empty lists → rewrite broken or key not authorized for the repo |
197|| `hermes status` | `GitHub` provider line optional; it only reflects `GITHUB_TOKEN` presence, not git auth | `GitHub ✗` is **not** a connectivity verdict — it just means no API token in `.env`. The SSH channel can still be 100% working. |
198|
199|**Always distinguish "git auth" from "API auth"** in the report. They
200|are independent: SSH key handles the first, GITHUB_TOKEN handles the
201|second. Telling the user "GitHub is broken" when only the API token is
202|missing is a false alarm.
203|
204|### 1.5 Auth Pitfalls
205|
206|- **Wrong key authenticates silently.** Multiple keys + missing
207|  `IdentitiesOnly yes` → SSH offers them all, first accepted wins,
208|  commits land on the wrong account. Always set `IdentitiesOnly yes`
209|  per host (see template above).
210|- **Outbound 22/tcp blocked at ISP/firewall.** Use the `github-443`
211|  host (ssh over TLS to ssh.github.com:443) or HTTPS + PAT.
212|- **PAT scopes insufficient.** `repo` scope is required for private
213|  repo write; `workflow` for Actions; `read:org` for org-level reads.
214|- **`.env` cached by gateway.** If you edit `~/.hermes/.env`, the
215|  gateway process keeps the old value at startup — restart it.
216|
217|---
218|
219|## 2. Repository Management *(was: `github-repo-management`)*
220|
221|### 2.1 Cloning
222|
223|Pure `git` — works identically either way:
224|
225|```bash
226|# HTTPS
227|git clone https://github.com/owner/repo-name.git
228|# Into a specific directory
229|git clone https://github.com/owner/repo-name.git ./my-local-dir
230|# Shallow
231|git clone --depth 1 https://github.com/owner/repo-name.git
232|# Specific branch
233|git clone --branch develop https://github.com/owner/repo-name.git
234|# SSH
235|git clone git@github.com:owner/repo-name.git
236|```
237|
238|**With `gh` shorthand:**
239|
240|```bash
241|gh repo clone owner/repo-name
242|gh repo clone owner/repo-name -- --depth 1
243|```
244|
245|### 2.2 Creating Repositories
246|
247|**With `gh`:**
248|
249|```bash
250|gh repo create my-new-project --public --clone
251|gh repo create my-new-project --private \
252|  --description "A useful tool" --license MIT --clone
253|gh repo create my-org/my-new-project --public --clone
254|
255|# From existing local directory
256|cd /path/to/existing/project
257|gh repo create my-project --source . --public --push
258|```
259|
260|**With `git` + `curl`:**
261|
262|```bash
263|# Create the remote repo via API
264|curl -s -X POST \
265|  -H "Authorization: token ***" \
266|  https://api.github.com/user/repos \
267|  -d '{
268|    "name": "my-new-project",
269|    "description": "A useful tool",
270|    "private": false,
271|    "auto_init": true,
272|    "license_template": "mit"
273|  }'
274|
275|# Clone it
276|git clone https://github.com/$GH_USER/my-new-project.git
277|
278|# -- OR -- push an existing local directory to the new repo
279|cd /path/to/existing/project
280|git init && git add . && git commit -m "Initial commit"
281|git remote add origin https://github.com/$GH_USER/my-new-project.git
282|git push -u origin main
283|```
284|
285|**Alternative for a single-file repo with a folder (no clone, no git):** create the repo with `--add-readme`, then drop your file via the **Contents API** in one PUT — intermediate folders appear automatically. See skill `github-contents-api` for the headless template.
286|
287|### 2.3 Forking
288|
289|```bash
290|# gh
291|gh repo fork owner/repo-name --clone --remote
292|
293|# API
294|curl -s -X POST -H "Authorization: token ***" \
295|  https://api.github.com/repos/owner/repo-name/forks
296|# Then: git clone https://github.com/$GH_USER/repo-name.git
297|```
298|
299|### 2.4 Configuring Repos (Topics, Settings, Visibility)
300|
301|```bash
302|# Set topics
303|curl -s -X PUT \
304|  -H "Authorization: token ***" \
305|  -H "Accept: application/vnd.github+json" \
306|  https://api.github.com/repos/$OWNER/$REPO/topics \
307|  -d '{"names": ["python", "cli", "agent"]}'
308|
309|# Change description / homepage
310|curl -s -X PATCH \
311|  -H "Authorization: token ***" \
312|  https://api.github.com/repos/$OWNER/$REPO \
313|  -d '{"description": "Updated", "homepage": "https://example.com"}'
314|
315|# Archive
316|curl -s -X PATCH \
317|  -H "Authorization: token ***" \
318|  https://api.github.com/repos/$OWNER/$REPO \
319|  -d '{"archived": true}'
320|```
321|
322|### 2.5 Releases
323|
324|```bash
325|# gh (cleanest)
326|gh release create v1.2.3 --title "v1.2.3" --notes "Bug fixes"
327|gh release upload v1.2.3 ./dist/*.tar.gz
328|gh release list
329|
330|# API — see references/github-api-cheatsheet.md
331|```
332|
333|### 2.6 Secrets & Variables
334|
335|```bash
336|# gh
337|gh secret set MY_SECRET --body "value"
338|gh secret list
339|
340|# API (requires libsodium public-key encryption — see gh docs)
341|curl -s -X PUT \
342|  -H "Authorization: token ***" \
343|  -H "Accept: application/vnd.github+json" \
344|  https://api.github.com/repos/$OWNER/$REPO/actions/secrets/$MY_SECRET \
345|  -d '{"encrypted_value": "<base64-libsodium-encrypted>", "key_id": "<public-key-id>"}'
346|```
347|
348|For a full endpoint reference, see `references/github-api-cheatsheet.md`.
349|
350|> **Using a private repo as a backup/artifact store** (tarballs,
351|> release notes, Contents-API index) is a different shape than
352|> release-per-tag for code. See `references/github-backup-store.md`
353|> and `scripts/build-server-backup.sh` for the full pattern.
354|
355|### 2.7 Cloning vs Forking — When to Use Each
356|
357|- **Clone** when you have write access and will not be sending PRs
358|  upstream.
359|- **Fork** when you do not have write access, or when you want to
360|  contribute back via PR from your own copy.
361|- **Branch in a clone you already own** when collaborating within a
362|  team that has access.
363|
364|---
365|
366|## 3. Code Review *(was: `github-code-review`)*
367|
368|### 3.1 Reviewing Local Changes (Pre-Push)
369|
370|This is pure `git` — works everywhere, no API needed.
371|
372|#### Get the Diff
373|
374|```bash
375|git diff --staged             # what would be committed
376|git diff main...HEAD          # what a PR would contain
377|git diff main...HEAD --name-only
378|git diff main...HEAD --stat
379|```
380|
381|#### Review Strategy
382|
383|1. **Get the big picture first:**
384|
385|   ```bash
386|   git diff main...HEAD --stat
387|   git log main..HEAD --oneline
388|   ```
389|
390|2. **Review file by file** — use `read_file` on changed files for full
391|   context, and the diff to see what changed:
392|
393|   ```bash
394|   git diff main...HEAD -- src/auth/login.py
395|   ```
396|
397|3. **Check for common issues:**
398|
399|   ```bash
400|   # Debug statements, TODOs, console.logs left behind
401|   git diff main...HEAD | grep -n "print\|console\.log\|TODO\|FIXME\|HACK\|XXX\|debugger"
402|
403|   # Large files accidentally staged
404|   git diff main...HEAD --stat | sort -t'|' -k2 -rn | head -10
405|
406|   # Secrets or credential patterns
407|   git diff main...HEAD | grep -in "password\|secret\|api_key\|token.*=\|private_key"
408|
409|   # Merge conflict markers
410|   git diff main...HEAD | grep -n "<<<<<<\|>>>>>>\|======="
411|   ```
412|
413|4. **Present structured feedback** to the user using the format in
414|   `references/review-output-template.md` (Critical / Warnings /
415|   Suggestions / Looks Good).
416|
417|### 3.2 Reviewing a Pull Request on GitHub
418|
419|#### View PR Details
420|
421|```bash
422|# gh
423|gh pr view 42
424|gh pr view 42 --json files,title,body,additions,deletions
425|gh pr diff 42
426|
427|# curl
428|curl -s -H "Authorization: token ***" \
429|  https://api.github.com/repos/$OWNER/$REPO/pulls/42
430|```
431|
432|#### File-by-File Review
433|
434|```bash
435|gh pr view 42 --json files --jq '.files[].path'
436|gh pr diff 42 -- path/to/file.py
437|```
438|
439|#### Leave Inline Review Comments
440|
441|```bash
442|# gh (cleanest for review submissions)
443|gh pr review 42 --comment --body "Overall: looks good. Two nits."
444|gh pr review 42 --request-changes --body "Needs work — see comments."
445|gh pr review 42 --approve
446|
447|# API
448|curl -s -X POST \
449|  -H "Authorization: token ***" \
450|  -H "Accept: application/vnd.github+json" \
451|  https://api.github.com/repos/$OWNER/$REPO/pulls/42/reviews \
452|  -d '{
453|    "commit_id": "<SHA>",
454|    "event": "REQUEST_CHANGES",
455|    "body": "Please address the SQL injection in auth.py:45",
456|    "comments": [
457|      {
458|        "path": "src/auth.py",
459|        "line": 45,
460|        "body": "Use parameterized queries — this is a SQL injection vector."
461|      }
462|    ]
463|  }'
464|```
465|
466|#### Request Reviewers
467|
468|```bash
469|# gh
470|gh pr edit 42 --add-reviewer user1,user2
471|
472|# API
473|curl -s -X POST \
474|  -H "Authorization: token ***" \
475|  https://api.github.com/repos/$OWNER/$REPO/pulls/42/requested_reviewers \
476|  -d '{"reviewers": ["user1", "user2"]}'
477|```
478|
479|For the canonical review comment format, see
480|`references/review-output-template.md`.
481|
482|### 3.3 Code Review Pitfalls
483|
484|- **Reviewing your own work is unreliable.** The
485|  `requesting-code-review` skill in `software-development/` covers the
486|  pre-commit auto-review pattern (3 parallel reviewers, one fix loop).
487|  Use it BEFORE pushing. Use THIS skill for reviewing OTHER people's
488|  PRs.
489|- **Large diffs hide real issues.** If `git diff main...HEAD --stat`
490|  shows > 500 lines changed, ask the author to split it into stacked
491|  PRs — reviewing 1500 lines of mixed concerns is a recipe for rubber
492|  stamps.
493|- **Missing CI?** Don't approve until CI is green. `gh pr checks` is
494|  the fastest check.
495|
496|---
497|
498|## 4. Issues *(was: `github-issues`)*
499|
500|### 4.1 Viewing Issues
501|
```

---

