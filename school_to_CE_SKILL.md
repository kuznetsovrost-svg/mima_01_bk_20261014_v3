---
name: school-to-ce
description: Use when user is migrating a school / college / university / hobby project to a professional coding-environment (CE) workflow — uv, ruff, mypy, pytest, pre-commit, conventional commits, git hygiene, README + AGENTS.md, CI, packaging. Trigger on phrases like "school project to real", "перевести в нормальный workflow", "учебный проект в production", "professionalise my code", "from Jupyter to project", "code for portfolio", "для резюме", "хочу выложить на GitHub".
version: 0.2.0
author: Rost
license: MIT
platforms: linux, macos
metadata:
  hermes:
    tags:
      - migration
      - school-to-pro
      - workflow
      - python
      - git
      - ci
      - packaging
      - uv
      - ruff
      - mypy
    related_skills:
      - test-driven-development
      - systematic-debugging
      - simplify-code
      - requesting-code-review
      - plan
      - spike
---

# School → CE (Coding Environment) Migration

Translate a school / hobby / Jupyter-only project into a
professional coding-environment workflow: modern dependency manager,
typed code, automated tests, linter / formatter / type-checker,
pre-commit hooks, conventional git history, README + AGENTS.md, CI,
and a clean packaging story.

The skill is **deliberately prescriptive**. It produces a
deterministic deliverable set, not a recommendation. The default
stack is **Python: uv + ruff + mypy + pytest + pre-commit + GitHub
Actions**. For other languages, see "Stack by language".

────────────────────────────────────────────────────────────────────────────
WHEN TO USE
────────────────────────────────────────────────────────────────────────────

Trigger this skill when **any** of the following is true:

  - The user has a Jupyter notebook / Google Colab / one-script file
    and wants to make it a real project.
  - The user says "переведи мой школьный проект в нормальный",
    "make my college assignment production-ready",
    "professionalise this code", "I want to publish my homework as
    a library".
  - The user is starting to apply for jobs / internships and wants
    a portfolio piece that looks like real engineering.
  - The user wants to share the project with a senior developer
    and is embarrassed about the current state.
  - The project has **no tests**, **no README**, **no CI**,
    but the user wants all three.

Do NOT use this skill if:

  - The user wants a one-off prototype (use `spike` instead).
  - The user already has a mature workflow with CI/CD
    (just review what's missing).
  - The user wants a quick fix only (use `systematic-debugging`).
  - The project is in a non-versioned binary format
    (e.g., a compiled executable they cannot rebuild).
  - The user wants to migrate between languages
    (separate skill, e.g., 2to3 / ts-to-js / py-to-rs).

────────────────────────────────────────────────────────────────────────────
STEP-BY-STEP
────────────────────────────────────────────────────────────────────────────

1. **Discovery** — before touching anything.

   a) Ask the user the goal:
      - "What does this project do in one sentence?"
      - "Who is the audience (you only / classmates / recruiters /
        OSS users)?"
      - "What does 'done' look like?"
   b) Inventory the current state:
      - `find . -type f -not -path '*/\.*' | head -50`
      - Identify the language(s) and entrypoints
        (`if __name__ == '__main__':`, Jupyter notebooks,
        `package.json`, `Cargo.toml`, etc.).
      - Check for tests (`test_*.py`, `*_test.go`, `*.spec.ts`,
        etc.).
      - Check for README / docs.
   c) Write a one-page "before" snapshot into the workspace:
      `workspace/inbox/<task-id>/snapshot-before.md`.

2. **Decide on the target stack**.

   Default: Python + uv + ruff + mypy + pytest + pre-commit.
   If the user already uses something else (Node, Go, Rust),
   use that. Write the decision in `task.md` under "Decisions":
   "Use X because Y."

3. **Initialize the modern layout** (Python example).

   ```bash
   git init                                        # if not already
   uv init --package .                             # pyproject.toml, src/
   mkdir -p src/<package>/
   git mv *.py src/<package>/                      # adapt filenames
   echo "3.11" > .python-version
   ```

4. **Add tools**.

   ```bash
   uv add --dev ruff
   uv add --dev mypy
   uv add --dev pytest pytest-xdist pytest-cov
   uv add --dev pre-commit
   ```

5. **Write minimal config files** (see "Config templates" below):
   `pyproject.toml`, `.pre-commit-config.yaml`, `.gitignore`,
   `.editorconfig`, `LICENSE`, `CHANGELOG.md`.

6. **Extract code from Jupyter notebooks** (if any).

   ```bash
   jupyter nbconvert --to script notebook.ipynb
   ```

   Manually split the result:
   - Configuration constants → `src/<package>/config.py`.
   - Functions → `src/<package>/<module>.py`.
   - "Main" workflow → `src/<package>/__main__.py` or `cli.py`.
   - Inline plots → `src/<package>/viz.py`.

   Strip out `In [12]:` prompts, `*` / `?` / `x =` magic prefixes,
   auto-printed DataFrames without assignments.

7. **Add tests**.

   - One happy-path test per public function.
   - One edge-case test (empty / large / bad input).
   - Use `tmp_path` fixture for any FS work.
   - Use `pytest.mark.parametrize` for variations.
   - Coverage target: ≥ 80% lines, ≥ 70% branches.

8. **Type-check the code**.

   ```bash
   uv run mypy src/
   ```

   Add type hints to all public functions. For complex types, use
   `from typing import ...` (or `from collections.abc import ...`
   on ≥ 3.9). Silence missing stubs with
   `[[tool.mypy.overrides]]` blocks.

9. **Format + lint**.

   ```bash
   uv run ruff format .
   uv run ruff check . --fix
   uv run ruff check .        # address what could not be auto-fixed
   ```

10. **Pre-commit hooks**.

    ```bash
    uv run pre-commit install
    uv run pre-commit run --all-files
    ```

11. **README + AGENTS.md**.

    `README.md` (for humans):
    - Title, one-line description, badges (CI, coverage, version).
    - "Install" section.
    - "Usage" with a small working example.
    - "Development" — how to run tests, lint, format.
    - License.

    `AGENTS.md` (for AI agents — Hermes, Claude Code, Codex):
    - Stack choices + why.
    - Commands (`uv sync`, `uv run pytest`, etc.).
    - Don'ts (no `print()`, no `pip install`, no push to main).
    - Project layout.

12. **CI** — `.github/workflows/ci.yml`.

    ```yaml
    name: CI
    on: [push, pull_request]
    jobs:
      test:
        runs-on: ubuntu-latest
        strategy:
          matrix: { python-version: ["3.11", "3.12"] }
        steps:
          - uses: actions/checkout@v4
          - uses: astral-sh/setup-uv@v3
            with:
              enable-cache: true
          - run: uv sync --all-extras --dev
          - run: uv run ruff check .
          - run: uv run ruff format --check .
          - run: uv run mypy src/
          - run: uv run pytest -n auto --cov=src/<package>
    ```

13. **Conventional Commits** (optional but recommended).

    Install `commitizen` or `commitlint` to enforce
    `<type>(<scope>): <description>`.

    Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`,
    `chore`, `ci`.

14. **Wrap-up**.

    - `git add . && git commit -m "chore: initialise project layout"`
    - Push to GitHub.
    - Verify CI is green.
    - Write `workspace/results/<task-id>/snapshot-after.md`
      comparing before and after.

────────────────────────────────────────────────────────────────────────────
STACK BY LANGUAGE
────────────────────────────────────────────────────────────────────────────

  ┌─────────────────┬──────────────────────┬──────────────────────────┐
  │ Concern         │ Python (default)      │ Other languages          │
  ├─────────────────┼──────────────────────┼──────────────────────────┤
  │ Pkg manager     │ uv                   │ npm/pnpm (JS)            │
  │                 │ (NOT pip/poetry/conda)│ cargo (Rust)             │
  │                 │                      │ go mod (Go)              │
  │                 │                      │ Maven (Java)             │
  │ Linter          │ ruff check           │ eslint+prettier (JS)     │
  │ Formatter       │ ruff format          │ prettier (JS)            │
  │ Type checker    │ mypy --strict        │ tsc --strict (JS/TS)     │
  │ Tests           │ pytest + pytest-xdist│ vitest (JS), go test,    │
  │                 │                      │ cargo test, JUnit (Java) │
  │ Pre-commit      │ pre-commit           │ husky + lint-staged (JS) │
  │ Versioning      │ git + git-cliff      │ release-please           │
  │ CI              │ GitHub Actions       │ GitHub Actions           │
  │ Docs            │ mkdocs / sphinx      │ typedoc (JS), godoc (Go) │
  │ Packaging       │ hatchling            │ npm publish              │
  └─────────────────┴──────────────────────┴──────────────────────────┘

────────────────────────────────────────────────────────────────────────────
CONFIG TEMPLATES
────────────────────────────────────────────────────────────────────────────

**pyproject.toml** (Python).

```toml
[project]
name = "my-project"
version = "0.1.0"
description = "..."
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
dev = ["ruff", "mypy", "pytest", "pytest-xdist", "pytest-cov",
       "pre-commit"]

[project.scripts]
my-project = "my_project.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/my_project"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "A", "C4", "PT",
          "RET", "SIM", "PTH", "ERA", "PL", "RUF"]
ignore = ["PLR0913", "PLR0915"]  # too-many-args, too-many-statements

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["PLR2004", "S101"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_unreachable = true
warn_unused_ignores = true

[[tool.mypy.overrides]]
module = "third_party_no_stub.*"
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = ["-ra", "--strict-markers", "--strict-config"]
markers = ["slow: marks tests as slow"]

[tool.coverage.run]
source = ["src/my_project"]
branch = true

[tool.coverage.report]
show_missing = true
fail_under = 80
```

**`.pre-commit-config.yaml`**.

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-added-large-files
        args: ["--maxkb=1024"]

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.7.4
    hooks:
      - id: ruff
        args: ["--fix"]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.13.0
    hooks:
      - id: mypy
        additional_dependencies: ["pydantic>=2"]
        args: ["--strict"]

  - repo: https://github.com/compilerla/conventional-pre-commit
    rev: v3.6.0
    hooks:
      - id: conventional-pre-commit
        stages: [commit-msg]
```

**`.gitignore`** (Python).

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
dist/
build/
*.egg-info/
.venv/
venv/

# IDE
.vscode/
.idea/
*.swp
.DS_Store

# Project-specific
data/
*.log
```

**`.editorconfig`**.

```ini
root = true

[*]
charset = utf-8
end_of_line = lf
indent_style = space
indent_size = 4
trim_trailing_whitespace = true
insert_final_newline = true

[*.{yml,yaml,toml,json}]
indent_size = 2

[*.md]
trim_trailing_whitespace = false
```

────────────────────────────────────────────────────────────────────────────
PITFALLS
────────────────────────────────────────────────────────────────────────────

1. **Don't migrate everything in one commit**.
   - First: `chore: initialise project layout`.
   - Second: `refactor: extract functions from notebook`.
   - Third: `test: add initial tests for analysis module`.
   - Fourth: `ci: add GitHub Actions workflow`.
   Reviewable diff, easy bisect if something breaks.

2. **Don't over-engineer coverage**.
   - Target 80% lines, 70% branches.
   - Don't test private functions.
   - Don't add tests that just call `assert True`.

3. **uv lockfile matters**.
   - Always commit `uv.lock`.
   - In CI, use `uv sync --frozen` (not bare `uv sync`).
   - For libraries, consider not shipping `uv.lock` to PyPI.

4. **mypy --strict is a feature, not a punishment**.
   - It catches real bugs.
   - Add types incrementally — don't rewrite the whole codebase
     in one go.

5. **Pre-commit hooks fail on Windows line endings**.
   - Set `.gitattributes` to `* text=auto eol=lf` for all text
     files, or use `.editorconfig`.

6. **Don't keep Jupyter notebooks in the source tree**.
   - Move them to `notebooks/` or `examples/`.
   - Or strip them to `.py` files via `nbconvert`.
   - Mixed formats confuse linters and CI.

7. **CI must fail loudly on lint / format issues**.
   - Add `uv run ruff format --check .` (note: `--check`, not
     auto).
   - Add `uv run ruff check .` (no `--fix`).
   - Otherwise pre-commit is just theatre.

8. **Don't use setup.py anymore**.
   - Use `pyproject.toml` with hatchling, setuptools ≥ 61, or pdm.
   - `setup.py` is a legacy format and breaks with PEP 517.

9. **Don't commit `.env`**.
   - Use `.env.example` with placeholders.
   - Real `.env` in `.gitignore`.

10. **No "magic" comments**.
    - `# TODO: refactor this` — open an issue instead.
    - `# XXX` — fix it.
    - `# type: ignore` without an explanatory comment.

11. **Don't `from foo import *`**.
    - Ruff F401 / F403 catch this.
    - Be explicit.

12. **README must show a working example**.
    - Install + run + see output. No marketing fluff.

13. **Avoid pinning to old Python versions**.
    - 3.11 minimum on 2026.
    - 3.12 is fine. 3.13 if you can.
    - 3.10 and below are EOL.

14. **Don't import from `src.`** in user-facing API.
    - Users should `import my_project`, not `import src.my_project`.
    - Fixed via `[tool.hatch.build.targets.wheel] packages`.

15. **Be careful with `__init__.py` exports**.
    - Use `__all__` to control `from my_project import *`.
    - Don't export internal helpers.

────────────────────────────────────────────────────────────────────────────
VERIFICATION
────────────────────────────────────────────────────────────────────────────

After applying this skill, **all** of the following must be true:

  □ `uv run ruff check .` exits 0.
  □ `uv run ruff format --check .` exits 0.
  □ `uv run mypy src/` exits 0.
  □ `uv run pytest` exits 0 with ≥ 80% coverage.
  □ `uv run pre-commit run --all-files` exits 0.
  □ `README.md` exists with install + usage example.
  □ `AGENTS.md` exists with stack + commands + don'ts.
  □ `pyproject.toml` committed with all sections.
  □ `uv.lock` committed.
  □ `.github/workflows/ci.yml` exists.
  □ CI is green on the default branch.
  □ All commits follow Conventional Commits.
  □ LICENSE file exists.
  □ `.gitignore` excludes `.env`, `__pycache__`, `.venv`, etc.

If any of these is missing, the migration is incomplete. Don't claim
"done" until all checkboxes are ticked.

────────────────────────────────────────────────────────────────────────────
SAMPLE OUTPUTS
────────────────────────────────────────────────────────────────────────────

**Before / After file layout**.

BEFORE:
```
project/
├── analysis.ipynb          # 200 cells, mixed code & text
├── data.csv
├── requirements.txt
└── README.txt
```

AFTER:
```
project/
├── .github/
│   └── workflows/
│       └── ci.yml
├── .gitignore
├── .editorconfig
├── .pre-commit-config.yaml
├── AGENTS.md
├── CHANGELOG.md
├── LICENSE
├── README.md
├── pyproject.toml
├── uv.lock
├── src/
│   └── my_project/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       └── analysis.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_analysis.py
│   └── test_cli.py
└── data/
    └── raw.csv
```

**Conventional commit log**.

```
chore: initialise project layout
refactor: extract functions from notebook
test: add initial tests for analysis module
docs: add README and AGENTS.md
ci: add GitHub Actions workflow
chore: add pre-commit hooks
feat: add CLI entry point
```

**Sample CI run output**.

```
✓ lint (ruff check)            1.2s
✓ format (ruff format --check) 0.8s
✓ types (mypy --strict)        4.3s
✓ tests (pytest)              12.7s
  Python 3.11: 42 passed, 0 failed
  Python 3.12: 42 passed, 0 failed
✓ coverage                     0.5s
  TOTAL: 87% lines, 79% branches
All checks passed.
```

────────────────────────────────────────────────────────────────────────────
SCOPE / NON-GOALS
────────────────────────────────────────────────────────────────────────────

This skill does NOT cover:

  - **Code review feedback** (use `requesting-code-review`).
  - **Performance optimisation** (use a separate skill or measure
    first).
  - **Deployment** to PyPI / Docker / k8s (separate skill).
  - **Python 2 → 3 migration** (that's `2to3` territory).
  - **Cross-framework migration** (Flask → FastAPI, etc.).
  - **Building web apps or services** (separate skill set).

If the user asks for any of the above, defer to the relevant skill
or escalate.

────────────────────────────────────────────────────────────────────────────
PREREQUISITES
────────────────────────────────────────────────────────────────────────────

The user must have:

  - Python 3.11+ installed.
  - `uv` installed (`pip install uv` or `brew install uv` or
    `curl -LsSf https://astral.sh/uv/install.sh | sh`).
  - `git` installed and configured (`user.name`, `user.email`).
  - A GitHub account (for CI).
  - Basic terminal comfort.

If any of these is missing, the skill can install / configure them
but only with explicit user consent. Don't run `apt install` without
asking.

────────────────────────────────────────────────────────────────────────────
ESTIMATED EFFORT
────────────────────────────────────────────────────────────────────────────

  ┌─────────────────────────────┬───────────────────────────────┐
  │ Project size                │ Estimated effort              │
  ├─────────────────────────────┼───────────────────────────────┤
  │ Single script (1 file)      │ 1-2 hours                     │
  │ Small project (5-10 files)  │ Half a day                    │
  │ Medium project              │ 1-2 days                      │
  │ (3-5 notebooks)             │                               │
  │ Large project (multi-       │ 3-5 days, possibly more       │
  │ module, multiple authors)   │                               │
  └─────────────────────────────┴───────────────────────────────┘

────────────────────────────────────────────────────────────────────────────
FOLLOW-UP TOPICS
────────────────────────────────────────────────────────────────────────────

After migration, consider:

  - `mkdocs` or `sphinx` for proper docs site.
  - `release-please` or `commitizen` for release automation.
  - Renovate or Dependabot for dependency updates.
  - `bandit` / `pip-audit` for security scanning.
  - `pyright` alongside `mypy` for stricter type checking.
  - `pytest-benchmark` for performance regression tests.

These are out of scope for the initial migration — pick what
matters.

────────────────────────────────────────────────────────────────────────────
NOTES FOR THE AGENT
────────────────────────────────────────────────────────────────────────────

When running this skill:

  1. Don't assume — ask the user clarifying questions if the goal
     is ambiguous.
  2. Don't over-engineer — this is a school project, not a
     satellite.
  3. Don't go too fast — let the user see what's changing.
  4. Always show a "before" and "after" snapshot.
  5. If the migration surfaces bugs in the original code, flag
     them but don't fix them in this skill — open an issue.
  6. If the user wants to skip a step (e.g., "no CI, this is just
     for me"), respect that and update the verification checklist
     accordingly.
  7. Document decisions in `task.md` under "Decisions".
  8. After publishing, recommend `git-cliff` for auto-generated
     `CHANGELOG.md` from conventional commits.

────────────────────────────────────────────────────────────────────────────
END OF SKILL
────────────────────────────────────────────────────────────────────────────
