# Cross-skill pipeline via shell wrapper

Pattern for chaining **multiple skills** in one user-facing command
when the pipeline needs data from each skill (e.g. snapshot from
skill A, render from skill B). The wrapper lives in the **calling**
skill and invokes Python from **peer** skills as subprocess.

## When to use

- User asks for a one-shot command that produces an artifact requiring
  multiple stages (e.g. `build_word_from_snapshot.sh 504-595` =
  fetch MD from MCP → render DOCX from MD).
- Each stage lives in a separate skill (no shared code, no shared
  imports — skills must be independent for portability).
- The wrapper exists **only** to give the user a single entry point;
  the individual scripts remain invokable on their own.

## Reference implementation

`fst-project-health-word/scripts/build_word_from_snapshot.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
if [[ $# -lt 1 ]]; then
    echo "Использование: $0 <project_code> [<project_code> ...]"
    exit 2
fi

SKILL_WORD_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SKILL_FETCH_DIR="${HOME}/.hermes/profiles/fst-control/skills/productivity/fst-project-health-from-md-snapshot"
CACHE_DIR="${HOME}/.hermes/profiles/fst-control/cache/snapshots"

for code in "$@"; do
    md_path=$(python3 "${SKILL_FETCH_DIR}/scripts/fetch_snapshot.py" \
        --code "${code}" --last --no-log >/dev/null 2>&1
        ls -1t "${CACHE_DIR}/${code}_"*.md 2>/dev/null | head -1)
    [[ -z "${md_path}" || ! -f "${md_path}" ]] && continue
    python3 "${SKILL_WORD_DIR}/scripts/build_word_report.py" \
        --md "${md_path}" --code "${code}" \
        --output "/tmp/${code}_report_$(date +%Y-%m-%d_%H%M%S)_WORD-форма1.docx"
done
```

## Pitfalls

### `python3` prefix is mandatory

Subprocess `subprocess.run` (or shell `subprocess.run([script])`)
**does not** auto-resolve the shebang unless you give the script
executable permission. Two failure modes observed:

| Invocation | Symptom | Fix |
|---|---|---|
| `"${SKILL}/scripts/fetch_snapshot.py"` | `Permission denied` (script not `chmod +x`) | Prepend `python3`, or `chmod +x` the script |
| `python3 ${SKILL}/scripts/...` | works | — |

Always invoke `python3 "${SKILL_DIR}/scripts/<name>.py"` from the
wrapper. The wrapper itself should be `chmod +x` (it has `#!/usr/bin/env bash`),
but the inner `.py` files need not be executable.

### `set -euo pipefail` for fail-fast inside `for`

`pipefail` is critical when redirecting stderr to null inside `$()` —
otherwise the wrapper continues even if `fetch_snapshot.py` returned
non-zero. Combine with explicit `[[ -z ${md_path} ]] && continue`
to skip per-iteration failures (mirrors `try/except/continue` in Python).

### Discover path via `cd "$(dirname "$0")/.."`

Hardcoding `~/.hermes/profiles/...` breaks portability (Pitfall #22
of `mcp-server-probing`, and the wider portability rule across the
family). The shell idiom:

```bash
SKILL_WORD_DIR="$(cd "$(dirname "$0")/.." && pwd)"
```

is the bash equivalent of `Path(__file__).resolve().parent.parent` in
Python — derives the skill directory from the wrapper's own location.

### Pass `set -o pipefail` for pipe `set -e` correctness

```bash
set -euo pipefail
```

Without `pipefail`, the script may silently swallow failures inside
pipes (e.g. `cmd1 | head -1` returning 0 even when `cmd1` failed).

## Reuse pattern

Apply this whenever the family grows a new "render X from Y" target:

| Wrapper lives in | Calls | Purpose |
|---|---|---|
| `fst-project-health-word/scripts/build_word_from_snapshot.sh` | `fst-project-health-from-md-snapshot/scripts/fetch_snapshot.py` + own `build_word_report.py` | DOCX from MCP-stored MD |
| `fst-project-health/scripts/build_trend_html.sh` (planned) | `fst-project-health/scripts/run_all.py` (multiple `--code`) + own `build_html_report.py` | Multi-project trend HTML |

Each wrapper is <50 lines, lives next to its primary skill, and
exposes the **user-facing** command name. Each inner script is
**independently invokable** for fine-grained work.
