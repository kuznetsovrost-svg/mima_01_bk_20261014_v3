# API: программное использование `fst-project-health-from-md-snapshot`

Для случаев, когда скилл нужно вызвать из Python-кода (не CLI).

## `fetch_snapshot.py` — импортируемые функции

```python
import sys
sys.path.insert(0, "/root/.hermes/profiles/fst-control/skills/productivity/fst-project-health-from-md-snapshot/scripts")

from fetch_snapshot import (
    mcp_init,                # → sid (mcp-session-id)
    find_project_id,         # (sid, code) → int|None
    list_snapshots,          # (sid, project_id, code) → list[dict{name,physicalFileId,fileSize,url,timestamp}]
    download_md,             # (sid, physical_id) → bytes
    select_snapshot,         # (snapshots, mode, at, exact) → (snapshot|None, status)
    save_to_cache,           # (code, ts, content) → Path
    # Константы:
    MCP_URL,
    DOCUMENT_ID_AI,
    CACHE_DIR,
)
```

### Пример: получить последний MD для одного проекта

```python
from fetch_snapshot import (
    mcp_init, find_project_id, list_snapshots, download_md, save_to_cache
)

sid = mcp_init()
project_id = find_project_id(sid, "504-595")
if project_id is None:
    raise SystemExit("проект не найден")
snapshots = list_snapshots(sid, project_id, "504-595")
if not snapshots:
    raise SystemExit("снимков нет")
latest = snapshots[-1]
content = download_md(sid, latest["physicalFileId"])
path = save_to_cache("504-595", latest["timestamp"], content)
print(f"OK: {path} ({len(content)} bytes)")
```

### Пример: трендовый прогон (без HTML)

```python
from fetch_snapshot import (
    mcp_init, find_project_id, list_snapshots, download_md, save_to_cache
)
from datetime import datetime

PROJECTS = ["504-595", "503-152", "503-434", "504-314"]
results = {"ok": [], "fail": []}

sid = mcp_init()
for code in PROJECTS:
    try:
        pid = find_project_id(sid, code)
        if pid is None:
            results["fail"].append((code, "not_found"))
            continue
        snaps = list_snapshots(sid, pid, code)
        if not snaps:
            results["fail"].append((code, "no_snapshots"))
            continue
        latest = snaps[-1]
        content = download_md(sid, latest["physicalFileId"])
        path = save_to_cache(code, latest["timestamp"], content)
        results["ok"].append((code, path, len(content)))
    except Exception as e:
        results["fail"].append((code, f"exception: {type(e).__name__}: {e}"))

print(f"OK: {len(results['ok'])}/{len(PROJECTS)}")
for code, reason in results["fail"]:
    print(f"  ✗ {code}: {reason}")
```

### Пример: построить HTML из MD через `build_html.py`

```python
import subprocess
md_path = "/root/.hermes/profiles/fst-control/cache/snapshots/504-595_2026-09-24_14-37-41.md"
subprocess.run([
    sys.executable,
    "/root/.hermes/profiles/fst-control/skills/productivity/fst-project-health-from-md-snapshot/scripts/build_html.py",
    "--md", md_path,
    "--output", "/tmp/my_report.html",
], check=True)
```

Или напрямую через основной скилл:
```python
subprocess.run([
    sys.executable,
    "/root/.hermes/profiles/fst-control/skills/productivity/fst-project-health/scripts/build_html_report.py",
    "--md", md_path,
], check=True)
```

---

## `logging_utils.py` — для своих логов

```python
from logging_utils import RunLogger, decode_jwt_user, get_user_role_via_mcp

logger = RunLogger()
logger.log_header(
    version="1.0.19",
    token_user={"name": "...", "email": "...", "sub": "..."},
    role="n/a (...)",
    action="my-action",
    projects_in_run=["504-595"],
    args_summary="--code 504-595",
)
logger.log_project(
    "504-595", "ok",
    local_path=Path("..."),
    snapshot_ts="2026-09-24 14:37:41",
    duration_ms=17000,
)
logger.log_trailer(total_ms=17000)
logger.close()
```

---

## Расположение кэша

`~/.hermes/profiles/fst-control/cache/snapshots/`

Файлы: `<code>_<timestamp>.md`.

Программный доступ:
```python
from pathlib import Path
CACHE_DIR = Path.home() / ".hermes/profiles/fst-control/cache/snapshots"
for p in sorted(CACHE_DIR.glob("504-595_*.md")):
    print(p.stat().st_size, p.name)
```

---

## См. также

- [playbook.md](../playbook.md) — режимы выбора, сценарии, edge cases.
- [README.md](../README.md) — для людей, с примерами CLI.
- [общий CHANGELOG семейства](../../fst-project-health/CHANGELOG.md).
