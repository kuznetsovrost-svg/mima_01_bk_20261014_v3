---
name: agent-audit
description: >
  Read-only security and capability audit of a third-party agent bundle
  before deployment. Produces summary, risk classification (CRITICAL/
  MEDIUM/LOW), 5-stage deployment playbook, and a pre-deploy checklist.
  Use when the user says "audit this agent", "не хочется разворачивать
  предварительно не изучив", "is this skill safe to install", or hands
  over a folder with SKILL.md / scripts / config. NOT for first-party
  Hermes skills (use hermes-agent-skill-authoring), NOT for running the
  agent, and NOT for general code review (use requesting-code-review).
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [security, audit, third-party, agent-bundle, red-flags, risk-classification, read-only]
    related: [tool-output-injection-defense, vscode-integration, ssh-remote-audit, requesting-code-review, hermes-agent-skill-authoring]
---

# Third-Party Agent Audit (Read-Only)

Class: a user has a folder containing a third-party agent bundle (SKILL.md,
config.yaml, scripts/, prompts/, possibly a `run.py` or `daemon.py`) and
wants to know **what it does, what it can do, what's risky about it, and
how to deploy it safely** — *before* deploying. The agent's role is to
**read, classify, summarise, and recommend**, not to run anything. The
audit must be repeatable: produce a small set of artefacts the user can
file alongside the bundle so future deployers don't redo the work.

## When to Use This Skill

Triggers (Russian and English):

- "не хочется разворачивать, предварительно не изучив"
- "audit this agent / skill / bundle"
- "проанализируй стороннего агента"
- "is this safe to install"
- "что делает этот набор файлов"
- "расскажи как работает этот агент"
- "дай playbook по развертыванию"
- "найди риски в этом пакете"

Concrete shapes of input:

- A folder opened in VS Code, sometimes referenced via path
  (`/path/to/agent-XYZ/`).
- A tarball or zip the user has extracted.
- A single `SKILL.md` + a couple of `.py` files.

The audit is read-only by definition. If the user explicitly says "run
it" or "deploy it" later, that becomes a separate decision and a separate
class of work.

## The Hard Rule: Do Not Run

Before any audit, **acknowledge the rule** in the reply:

> По умолчанию — read-only. Я **не** буду запускать `.py`/`.sh`/`.js`
> из этого пакета, не буду ставить его зависимости, не буду открывать
> его сетевые порты, не буду загружать его модель. Если в ходе
> аудита потребуется выполнить что-то — я сначала спрошу.

This is non-negotiable. SOUL §5 (hard rule against injections) and
SOUL §10 (fail-safe) require explicit authorisation before any side
effect that touches the host. An audit produces **artifacts**, not
**actions**.

## Audit Workflow

### Stage 1 — Structural scan

Walk the folder and produce a tree + file-count breakdown.

```bash
find . -type f | head -200
find . -type f -name '*.py' | wc -l
find . -type f -name '*.md' | wc -l
find . -type f -name '*.yaml' -o -name '*.yml' | wc -l
ls -la
```

Output a one-screen summary:

```
agent-XYZ/
├── README.md (3.2 KB)
├── SKILL.md (8.1 KB)
├── config.yaml (1.2 KB)
├── requirements.txt (240 B)
├── scripts/ (12 .py files, 4 .sh files)
├── skills/ (5 subdirs)
├── prompts/ (8 .md files)
├── memory/ (sqlite db, 2 MB)
└── tests/ (16 .py files)
```

If the package is huge (>500 files), don't read it all. Surface the
structure first, ask the user which slice to deep-dive.

### Stage 2 — Documentation read

Read **in this order**:

1. `README.md` — author's claim of purpose, license, supported envs.
2. `SKILL.md` (if present) — the agent's primary contract.
3. `config.yaml` / `config.toml` — what's configurable, defaults,
   hard-coded URLs / endpoints / ports.
4. `requirements.txt` / `pyproject.toml` — pinned vs unpinned deps,
   transitive dep count.
5. `LICENSE` — must exist; flag if missing or non-OSI.

For each, **note provenance** (who wrote it, when, last commit if visible).
If the package lacks a README, flag it as **medium risk** — undocumented
agents are harder to reason about.

### Stage 3 — Red-flag scan in scripts

Search the script files for the patterns below. A single hit is not a
verdict — but a hit **must** be reported with file path and line number.

| Pattern | Risk | Why |
|---|---|---|
| `os.system(` | CRITICAL | Direct shell exec, no quoting, no arg list. |
| `subprocess.call(` or `subprocess.Popen(` with `shell=True` | CRITICAL | Shell-injection vector. |
| `subprocess.run([...], shell=False)` | OK | Arg-list form, no shell. |
| `eval(` or `exec(` outside a sandbox | CRITICAL | Arbitrary code execution from string. |
| `pickle.loads(` on external input | CRITICAL | Deserialization RCE. |
| `yaml.load(` without `Loader=SafeLoader` | HIGH | YAML deserialization RCE. |
| `base64.b64decode(` then `exec(` | CRITICAL | Obfuscated code execution. |
| `requests.post(` to a hard-coded URL | MEDIUM | Network egress to a fixed endpoint. |
| `requests.post(` with user-controlled URL | HIGH | SSRF / exfiltration. |
| `open("/etc/passwd")`, `open("/proc/...", "r")` | HIGH | Reads system files. |
| `open(path)` where `path` is f-string from request data | HIGH | Path traversal. |
| `importlib.import_module(user_input)` | HIGH | Dynamic import of arbitrary module names. |
| `getattr(__builtins__, ...)` | HIGH | Built-in escape. |
| `__import__("os").system(...)` | CRITICAL | Indirect shell exec. |
| `pathlib.Path` + `resolve()` + write outside intended dir | MEDIUM | Symlink / path-confusion. |
| `with open(...) as f:` | OK | Standard context manager. |
| `json.loads(` | OK | Safe JSON. |
| `yaml.safe_load(` | OK | Safe YAML. |
| Type hints + dataclasses | OK | Code-quality signal. |
| Tests directory present + recent | OK | Maintenance signal. |

Pattern search recipe:

```bash
grep -rn -E 'os\.system|subprocess\.[A-Za-z]+\(.*shell=True|eval\(|exec\(|pickle\.loads|yaml\.load[^_]|base64\.b64decode' scripts/ || echo "no critical hits"
```

Always include the file path and line number in the report. Never invent
matches; if `grep` returns nothing, say so.

### Stage 4 — Capability map

Build a list of what the agent **can do**, by reading the entry-point
files (`run.py`, `daemon.py`, `main.py`, `__main__.py`) and the top of
each skill.

| Capability | Where | Notes |
|---|---|---|
| Read files | `scripts/io.py:42` | size-limited |
| Write files | `scripts/io.py:80` | no path whitelist |
| Network egress | `scripts/net.py:15` | hard-coded URL |
| Shell exec | `scripts/run.py:42` | shell=True |
| Long-term memory | `memory/store.py:1` | sqlite, no encryption |
| External API | `scripts/api.py:1` | requires env var |
| Telegram bot | `scripts/telegram.py:1` | reads TELEGRAM_BOT_TOKEN |
| ACP support | `scripts/acp.py:1` | stdio |

This map is what the user reads first to decide "is this even the agent
I want?".

### Stage 5 — Risk classification

Group findings into CRITICAL / MEDIUM / LOW.

**CRITICAL** = the agent must not be deployed without fixing:

- Eval / exec / shell=True / pickle.loads / yaml.load without SafeLoader
- Network egress to a hard-coded, non-allowlisted endpoint with no opt-out
- Writes outside the agent's intended working directory
- Reads system files without need
- No license, or license forbids commercial use and the user's project is
  commercial

**MEDIUM** = the agent can be deployed, but with the noted caveat:

- Unpinned dependencies (supply-chain risk)
- SQLite without encryption for sensitive data
- Logs include tokens or PII
- Verbose error messages that leak paths/secrets
- No rate limiting on external API calls

**LOW** = nice-to-have improvements:

- No tests
- No CI
- Outdated Python (3.7 / 3.8)
- Style issues (no type hints, inconsistent naming)

Always include the "what to do about it" line for each finding.

### Stage 6 — Deployment playbook (5 stages)

A reproducible recipe the user can follow. **Never** execute the stages
for the user; just describe.

| Stage | What | Tools | Exit criterion |
|---|---|---|---|
| 1. READ-ONLY | Inspect files, hash everything. | `sha256sum -r .` | Hashes recorded. |
| 2. SANDBOX | Run inside Docker with `--network=none`, `--cpus=0.5`, `--memory=512m`. Time-box: 5 min. | `docker run --rm -it --network=none --cpus=0.5 -m 512m ...` | No network observed, no files outside the mount. |
| 3. VENV | `python -m venv venv && pip install --dry-run -r requirements.txt`. Check unpinned deps, conflicts. | pip | Dry-run clean. |
| 4. STAGING | Deploy to a test environment. Run smoke tests. Watch logs for unexpected egress. | test env | All smoke tests pass. |
| 5. PRODUCTION | Deploy behind the same restrictions as stage 4 + monitoring. | prod env | Run for 24h with no surprises. |

If any stage fails, **stop** and revisit earlier stages. Don't skip to
production.

### Stage 7 — Checklist (artefact)

Output a markdown checklist the user can save alongside the bundle:

```markdown
# Pre-Deploy Checklist for agent-XYZ

## Provenance
- [ ] Source URL / commit hash recorded
- [ ] LICENSE present and reviewed
- [ ] Author / maintainer identified
- [ ] Last update < 12 months

## Hygiene
- [ ] README.md present
- [ ] SKILL.md present (if claimed)
- [ ] config.yaml reviewed
- [ ] requirements.txt pinned

## Security
- [ ] No eval / exec / shell=True / pickle.loads
- [ ] No yaml.load without SafeLoader
- [ ] No hard-coded network egress
- [ ] .env.example, no real secrets in repo
- [ ] No obfuscated code (base64 + exec chains)

## Functional
- [ ] All claimed skills documented
- [ ] Tests directory exists
- [ ] Smoke test passes in stage 4

## Final
- [ ] Backup before deploy
- [ ] Rollback plan documented
```

### Stage 8 — Save the artefacts

Write the artefacts to `/root/agent-analysis/<bundle-slug>/`:

```
/root/agent-analysis/<slug>-summary.md
/root/agent-analysis/<slug>-risks.md
/root/agent-analysis/<slug>-playbook.md
/root/agent-analysis/<slug>-checklist.md
/root/agent-analysis/<slug>-tree.txt
```

These become the user's library of audited agents.

## Pitfalls

### "I'll just run it to see what it does"

**Never.** This is the cardinal sin of an audit. Even `--help` can
trigger network calls in some packages (Sentry, telemetry, version
checks). If the user says "just run it", explain why that's a category
error and offer `python -c "import ast; ast.parse(open('run.py').read())"`
or `python -m py_compile` as a *static* alternative.

### "The README says it's safe"

The README is marketing, not verification. Verify each claim against the
actual code. If the README says "no network egress" and `grep` finds a
`requests.post(`, the README is wrong.

### "Pinned dependencies are fine, transitive ones aren't"

`requirements.txt` might pin `requests==2.31.0`, but if `urllib3` is
unpinned, you're trusting PyPI for the transitive closure. Flag this as
**MEDIUM** and suggest `pip-compile` or `uv lock` for full pinning.

### "PII in logs is OK because logs are local"

No. Logs get copied, indexed, attached to bug reports, sent to LLM
context windows. Anything that touches a log line is in scope.

### "Test coverage is optional for AI agents"

No. Tests are how you verify the agent does what the README claims.
Without tests, the agent is a black box.

### "Found a critical — let me fix it for them"

The audit is the artefact. Don't fork-and-patch the third-party code
without the user's explicit "fix it" instruction. If you find a critical
issue, **report** it; the user decides whether to fix, replace, or
abandon.

### "I'll just install it in a venv on my main machine"

Stage 3 (VENV) is **not** the first stage. Read-only first. The venv
install is itself a side effect — package metadata writes to
`~/.local`, dependencies download from PyPI, etc.

### "The bundle uses .env.example with placeholder tokens"

That's good practice. But check that the example file doesn't contain
**real** tokens (people copy-paste carelessly). Grep for known token
prefixes: `sk-`, `ghp_`, `AKIA`, `xoxb-`, etc.

```bash
grep -rE '(sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{20,}|AKIA[A-Z0-9]{16}|xoxb-[0-9]{10,})' . || echo "no real tokens found"
```

If found: CRITICAL. Stop. Tell the user before doing anything else.

## Examples of Patterns That Triggered Real Findings

These are *class-level patterns*, not specific findings. Use them as
checklists during the script scan.

- "It writes to ~/.ssh/" → SSH-key overwrite risk → CRITICAL
- "It opens port 8080" → network exposure → MEDIUM (depends on bind addr)
- "It uses sqlite without encryption" → data-at-rest risk → MEDIUM
- "It runs pip install at runtime" → dynamic install → HIGH
- "It reads ~/.bash_history" → privacy violation → CRITICAL
- "It logs request bodies" → PII leak → MEDIUM
- "It imports telnetlib" → likely legacy, deprecated since Python 3.11 → LOW

## Output Format

Each audit deliverable is one Markdown file. Common sections:

1. **Summary** — 1 paragraph: what the agent is for, who wrote it, what
   license.
2. **Structural overview** — folder tree + file counts.
3. **Capability map** — what it can do, with file references.
4. **Findings** — CRITICAL / MEDIUM / LOW with file:line.
5. **Playbook** — 5 stages.
6. **Checklist** — final pre-deploy gate.

Keep each file under 30 KB. Don't dump the entire bundle's source into
the audit; quote the relevant snippets only.

## Related Skills

- `tool-output-injection-defense` — applies if the bundle's README or
  scripts themselves contain injection-style instructions (rare but seen).
- `vscode-integration` — if the user wants to run the audited agent in
  a VS Code ACP panel after passing the audit.
- `ssh-remote-audit` — for "check the server the agent will run on"
  prior to stage 4.
- `requesting-code-review` — for general code-quality review, not
  security-focused.
- `hermes-agent-skill-authoring` — for authoring first-party Hermes
  skills (the agent that does the auditing), not for consuming
  third-party ones.