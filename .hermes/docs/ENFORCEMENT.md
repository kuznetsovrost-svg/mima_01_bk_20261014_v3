# Hermes Agent · Fail-safe Enforcement Map

> Authoritative table of enforcement levels for the 11 fail-safe rules.
> Promoted out of `SOUL.md` §11 into this file in v6 to keep the
> kernel prompt small. Loaded on demand by the `failsafe-rules` skill.
>
> See: `~/.hermes/skills/failsafe-rules/SKILL.md` for the rule catalog.
> See: `~/.hermes/SOUL.md` §10-§11 for the in-kernel reference.

## Enforcement levels

| Level | Meaning | Tools / mechanisms |
|-------|---------|--------------------|
| `high` | Hermes has a tool-level gate. The user must override the gate explicitly. | `tirith`, `approvals.mode`, `terminal.yolo`, `media_delivery_allow_dirs` |
| `medium` | Hermes has a heuristic gate (`tirith` patterns). Catch obvious cases, may miss novel ones. | `tirith` patterns |
| `low` | No tool gate. The text-only rule in `failsafe-rules` skill is the only protection. | (skill only) |

## The 11 rules and their enforcement

| # | Rule (short) | Trigger pattern | Enforcement | Level |
|---|--------------|-----------------|-------------|-------|
| 1 | `curl \| sh` | `curl/wget` piped to `sh`/`bash`, downloaded-binary run | text only | low |
| 2 | `rm -rf` | `rm -rf /`, `rm -rf ~/*`, `rm -rf ../*` (path resolves above cwd or $HOME) | `tirith` patterns | medium |
| 3 | external send | `curl -F`, `curl -d @file`, multipart upload, `send_file` outside chat-platforms | `media_delivery_allow_dirs` + `gateway.platforms.<name>.home_chat_id` | high |
| 4 | push to main | `git push origin main`, `git push --force` to protected branch | text + git host branch-policy | low |
| 5 | `/etc/*` etc | writes to `/etc/`, `/usr/`, `/var/`, global `~/.bashrc`/`~/.zshrc`/`~/.profile` | `terminal` require-approval for paths outside `$HOME` | high |
| 6 | `chmod 777` on secrets | `chmod 777`, `chmod -R 777`, `chmod a+rwx` on SSH keys / `~/.netrc` / `~/.aws/credentials` / `.env` | `tirith` patterns | medium |
| 7 | package install | `apt/apt-get/pip/npm/yarn/cargo/brew install` | text only | low |
| 8 | `--yolo` / tirith off | `hermes --yolo`, `hermes --no-sandbox`, `tirith disable`, setting `security.tirith_enabled=false` | `terminal.yolo=false` in `~/.hermes/config.yaml` | high |
| 9 | publish-as-user | `gh pr create`, posting to X/Twitter/LinkedIn, committing to public repo, posting to forum under user identity | text only | low |
| 10 | impersonation | calling self "openai"/"anthropic"/"support for X", signing messages with other identity | text only | low |
| 11 | credentials non-text | credentials embedded in images / audio / video / PDFs (OCR, vision, transcription) | text only | low |

## Summary

```
high (3):   rules 3, 5, 8
medium (2): rules 2, 6
low (6):    rules 1, 4, 7, 9, 10, 11
```

## What this means at runtime

- **Rules 3, 5, 8 are protected at the tool layer.** Before relying on these, the model can assume Hermes will ask for approval or block. The `failsafe-rules` skill provides the policy rationale; the tool does the blocking.
- **Rules 2, 6 are protected by heuristic matching.** `tirith` may catch common patterns (`rm -rf /`, `chmod 777`) but won't catch novel phrasings. The model must apply the rule manually when uncertain.
- **Rules 1, 4, 7, 9, 10, 11 are text-only.** No tool blocks them. If the model doesn't load `failsafe-rules` and apply the check, the action executes unchecked. This is the largest attack surface in the kernel.

## When to consult this file

- Before a `terminal` / `git` / `write_file` / `patch` action that affects system state.
- After every SOUL §8 self-audit on a destructive action (the audit will reference this file).
- When changing the kernel: any rule whose enforcement level changes must be re-evaluated against the corresponding gate.

## Versioning

- v6 (2026-07-15): promoted out of `SOUL-prototype-5.md` §11.
- Prior: lived in `SOUL.md` §11 (≤ v5).
