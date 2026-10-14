# Consolidation Note (2026-06-16)

This skill was created as an **umbrella** by merging five sibling
skills that all shared the same auth-detection pattern and the same
`gh` / `curl` API surface. The originals are kept under
`~/.hermes/skills/.archive/` for recoverability.

| Archived skill | What moved into this umbrella |
|----------------|------------------------------|
| `github-auth` | §1 (Auth Setup & Diagnostics) + `scripts/gh-env.sh` + `templates/ssh-config-github` |
| `github-repo-management` | §2 (Repository Management) + `references/github-api-cheatsheet.md` |
| `github-code-review` | §3 (Code Review) + `references/review-output-template.md` |
| `github-issues` | §4 (Issues) + `templates/issue-bug-report.md` + `templates/issue-feature-request.md` |
| `github-pr-workflow` | §5 (PR Workflow) — this skill was the umbrella seed |

## Why an umbrella

All five skills shared:
- The same `gh auth status` / `GITHUB_TOKEN` / SSH detection flow.
- The same `OWNER`/`REPO` extraction from `git remote get-url origin`.
- The same `Authorization: token $GITHUB_TOKEN` header pattern.
- A heavy `gh` vs `curl` decision tree inside every section.

Splitting them across five skills meant every section repeated the
auth-detection preamble. A maintainer would write this as one skill
with labeled subsections (which is what's now here). The `codebase-
inspection` pygount skill remains a separate sibling because it
analyzes local code rather than interacting with the GitHub API.

## Updating cross-references

The following other skills referenced the archived skill names and
were updated to point at this umbrella:

- `autonomous-ai-agents/hermes-agent/references/webhooks.md` —
  `--skills "github-code-review"` → `--skills "github-pr-workflow"`
- `hermes-agent-vcs-portability/SKILL.md` — "github-pr-workflow and
  github-issues" → "github-pr-workflow skill (now an umbrella)";
  related-skill bullet updated
- `software-development/requesting-code-review/SKILL.md` —
  `related_skills: [..., github-code-review]` → `github-pr-workflow`;
  prose comparison updated
- `github/codebase-inspection/SKILL.md` —
  `related_skills: [github-repo-management]` → `github-pr-workflow`
- `github/DESCRIPTION.md` — category description updated to mention
  the umbrella
