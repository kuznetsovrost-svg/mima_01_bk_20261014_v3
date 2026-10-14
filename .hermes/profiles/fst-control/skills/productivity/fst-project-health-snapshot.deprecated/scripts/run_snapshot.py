__version__ = "1.0.19"
#!/usr/bin/env python3
"""
fst-project-health-snapshot: еженедельный сбор JSON-слепков состояния
проектов в карточки MCP.

Переиспользует логику скилла `fst-project-health` через subprocess
(БЕЗ модификации самого скилла).

Назначение:
- Для каждого проекта из `PROJECTS` запускает `run_all.py --code <code>`.
- Парсит получившийся MD (через `parse_md_to_data` из `build_word_report.py`).
- Оборачивает в JSON с _meta (generator: "fst-project-health-snapshot").
- Загружает в карточку проекта в категорию "Документы ИИ" (DocumentId=70139).

Использование:
    python3 run_snapshot.py                       # полный прогон по всем проектам
    python3 run_snapshot.py --code 504-595       # один проект (override)
    python3 run_snapshot.py --dry-run            # без загрузки в MCP (только локально)
    python3 run_snapshot.py --no-html            # пропустить HTML в run_all (быстрее)
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Конфигурация
# ---------------------------------------------------------------------------

# Тестируемый проект по умолчанию — список из 4 проектов, по которым
# раньше строились отчёты.
DEFAULT_PROJECTS = ["504-595", "503-152", "503-434", "504-314"]

# Путь к скиллу fst-project-health (БЕЗ модификации, только subprocess).
# На другом сервере переопределяется через env-var FST_PROJECT_HEALTH_PATH.
SKILL_DIR = Path(
    os.environ.get(
        "FST_PROJECT_HEALTH_PATH",
        "/root/.hermes/profiles/fst-control/skills/productivity/fst-project-health",
    )
)
SKILL_SCRIPTS = SKILL_DIR / "scripts"

# Путь к скиллу fst-project-health-word (для парсера MD).
# На другом сервере переопределяется через env-var FST_PROJECT_HEALTH_WORD_PATH.
FST_PROJECT_HEALTH_WORD_PATH = Path(
    os.environ.get(
        "FST_PROJECT_HEALTH_WORD_PATH",
        "/root/.hermes/profiles/fst-control/skills/productivity/fst-project-health-word",
    )
)

# MCP-параметры.
# URL берётся из env MCP_URL или дефолтный production.
MCP_URL = os.environ.get("MCP_URL", "https://ppreplica.hera.pmpractice.ru/mcp")
DOCUMENT_ID_AI = 70139  # категория "Документы ИИ" в PMForesight
ENTITY_NAME = "Project"
TIMEOUT_INITIALIZE = 30
TIMEOUT_TOOLS_CALL = 60

# ENV-файлы для поиска PMP_TOKEN (порядок приоритета).
ENV_FILE_CANDIDATES = [
    Path(__file__).resolve().parent.parent / ".env",
    Path.home() / ".hermes/profiles/fst-control/.env",
]

# Генератор метаданных для машинного отбора «свой vs чужой».
SNAPSHOT_GENERATOR = "fst-project-health-snapshot"
SNAPSHOT_VERSION = "1.0.0"
SNAPSHOT_KIND = "fst-project-health-snapshot"

# Префикс имени файла.
FILE_PREFIX = "Слепок fst-project-health-snapshot-"
FILE_EXT = ".JSON"

# Папка для локальных копий.
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "outputs"

# Таймаут одного прогона run_all.py (сек).
PIPELINE_TIMEOUT = 300

# ANSI-цвета.
def _c(code, text):
    return f"\033[{code}m{text}\033[0m"
def green(t): return _c("32", t)
def yellow(t): return _c("33", t)
def red(t): return _c("31", t)
def bold(t): return _c("1", t)


# ---------------------------------------------------------------------------
# MCP-клиент (read-only-ish, write для upload_entity_file)
# ---------------------------------------------------------------------------

def _load_token() -> str:
    """PMP_TOKEN: сначала env, потом .env файлы."""
    tok = os.environ.get("PMP_TOKEN")
    if tok:
        return tok
    for env_path in ENV_FILE_CANDIDATES:
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("PMP_TOKEN"):
                _, _, v = line.partition("=")
                v = v.strip().strip("'\"")
                if v:
                    return v
    raise RuntimeError(
        "PMP_TOKEN не найден. Экспортируйте или положите в .env"
    )


def _parse_sse(resp, context: str) -> dict:
    """Парсит первую data:-строку из SSE-ответа (см. Pitfall из fst-mcp-tester)."""
    resp.encoding = "utf-8"
    for line in resp.text.splitlines():
        if line.startswith("data: "):
            try:
                return json.loads(line[6:])
            except json.JSONDecodeError as e:
                raise RuntimeError(f"[{context}] невалидный JSON: {e}; line[:200]={line[:200]}")
    raise RuntimeError(f"[{context}] нет data-строки в SSE; status={resp.status_code}")


def mcp_init() -> tuple[str, dict]:
    """MCP handshake. Возвращает (sid, serverInfo)."""
    import requests
    token = _load_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "fst-project-health-snapshot", "version": SNAPSHOT_VERSION},
        },
    }
    resp = requests.post(MCP_URL, json=payload, headers=headers, timeout=TIMEOUT_INITIALIZE)
    resp.raise_for_status()
    sid = resp.headers.get("mcp-session-id")
    if not sid:
        raise RuntimeError(f"сервер не вернул mcp-session-id. headers={dict(resp.headers)}")
    envelope = _parse_sse(resp, "initialize")
    server_info = envelope.get("result", {}).get("serverInfo", {})
    # best-effort notifications/initialized
    try:
        requests.post(
            MCP_URL,
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
            headers={**headers, "mcp-session-id": sid},
            timeout=10,
        )
    except Exception:
        pass
    return sid, server_info


def mcp_call(sid: str, tool_name: str, arguments: dict, *, timeout: int = TIMEOUT_TOOLS_CALL) -> dict:
    """tools/call."""
    import requests
    token = _load_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "mcp-session-id": sid,
    }
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }
    resp = requests.post(MCP_URL, json=payload, headers=headers, timeout=timeout)
    resp.raise_for_status()
    envelope = _parse_sse(resp, tool_name)
    result = envelope.get("result", {})
    if result.get("isError"):
        return {"_error": result.get("content", [{}])[0].get("text", "<no msg>")}
    text = result.get("content", [{}])[0].get("text", "{}")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"_raw_text": text[:500]}


# ---------------------------------------------------------------------------
# Утилиты
# ---------------------------------------------------------------------------

def timestamp_for_filename() -> str:
    """YYYY-MM-DD_HH-MM-SS — формат с секундами."""
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def iso_timestamp() -> str:
    """ISO-8601 с timezone для _meta.produced_at."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def build_filename(project_code: str) -> str:
    """Финальное имя файла для загрузки в MCP.

    Формат: `Слепок fst-project-health-snapshot-{project_code}-{YYYY-MM-DD_HH-MM-SS}.JSON`
    Код проекта включён в имя для удобства группировки файлов в UI
    PMForesight (при сортировке по имени файлы одного проекта идут подряд).

    Префикс `Слепок fst-project-health-snapshot-` однозначно отделяет наши
    слепки от других документов на вкладке «Документы ИИ».
    """
    return f"{FILE_PREFIX}{project_code}-{timestamp_for_filename()}{FILE_EXT}"


def build_meta(project_code: str, project_id: int | None) -> dict:
    return {
        "schema_version": SNAPSHOT_VERSION,
        "generator": SNAPSHOT_GENERATOR,
        "generator_version": SNAPSHOT_VERSION,
        "produced_at": iso_timestamp(),
        "snapshot_kind": SNAPSHOT_KIND,
        "project_code": project_code,
        "project_id": project_id,
    }


def fmt_ms(ms) -> str:
    if ms is None:
        return "—"
    if ms >= 1000:
        return f"{ms/1000:.2f} s"
    return f"{ms:.0f} ms"


# ---------------------------------------------------------------------------
# Шаг 1: запуск fst-project-health через subprocess
# ---------------------------------------------------------------------------

def run_fst_project_health(code: str, *, no_html: bool = True) -> Path:
    cmd = [
        sys.executable,
        str(SKILL_SCRIPTS / "run_all.py"),
        "--code", code,
        "--no-cache",
    ]
    if no_html:
        cmd.append("--no-html")
    print(f"\n→ {code}: запуск fst-project-health... ", end="", flush=True)
    t0 = time.perf_counter()
    try:
        result = subprocess.run(
            cmd,
            cwd=str(SKILL_SCRIPTS),
            timeout=PIPELINE_TIMEOUT,
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired:
        print(red(f"TIMEOUT ({PIPELINE_TIMEOUT}с)"))
        raise
    duration = time.perf_counter() - t0
    md_path = Path(f"/tmp/project_{code}_report.md")
    if result.returncode != 0:
        print(yellow(f"exit={result.returncode}, время={fmt_ms(duration*1000)}"))
        if result.stderr:
            print(f"  stderr (последние 500 символов):\n  {result.stderr[-500:]}")
        raise RuntimeError(f"fst-project-health завершился с кодом {result.returncode}")
    if not md_path.exists():
        print(red(f"MD не создан ({fmt_ms(duration*1000)})"))
        raise RuntimeError(f"Ожидался {md_path}, но файл не появился")
    print(green(f"OK ({fmt_ms(duration*1000)}) → {md_path.name} ({md_path.stat().st_size} байт)"))
    return md_path


# ---------------------------------------------------------------------------
# Шаг 2: парсинг MD → data-словарь
# ---------------------------------------------------------------------------

def parse_md_to_data(md_path: Path) -> dict:
    word_skill = FST_PROJECT_HEALTH_WORD_PATH / "scripts"
    sys.path.insert(0, str(word_skill))
    from build_word_report import parse_md_to_data as _parse
    return _parse(md_path)


# ---------------------------------------------------------------------------
# Шаг 3: обёртка + локальное сохранение
# ---------------------------------------------------------------------------

def wrap_into_snapshot(data: dict, project_code: str, project_id: int | None) -> dict:
    snapshot = {
        "_meta": build_meta(project_code, project_id),
        "snapshot_kind": SNAPSHOT_KIND,
        "produced_at": iso_timestamp(),
        "source_generator": data.get("_meta", {}).get("generator", "fst-project-health"),
        "source_generator_version": data.get("_meta", {}).get("generator_version", "?"),
    }
    for key, value in data.items():
        if key not in snapshot:
            snapshot[key] = value
    return snapshot


def save_local(snapshot: dict, project_code: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    local_name = f"{project_code}_{timestamp_for_filename()}.json"
    local_path = OUTPUT_DIR / local_name
    local_path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return local_path


# ---------------------------------------------------------------------------
# Шаг 4: загрузка в MCP
# ---------------------------------------------------------------------------

def upload_to_mcp(sid: str, snapshot: dict, project_id: int, file_name: str) -> dict:
    content = json.dumps(snapshot, ensure_ascii=False, indent=2).encode("utf-8")
    content_b64 = base64.b64encode(content).decode("ascii")
    return mcp_call(sid, "upload_entity_file", {
        "entityName": ENTITY_NAME,
        "dataId": str(project_id),
        "documentId": DOCUMENT_ID_AI,
        "uploadedFileName": file_name,
        "uploadedFileContentBase64": content_b64,
    })


# ---------------------------------------------------------------------------
# Шаг 5: получение project_id
# ---------------------------------------------------------------------------

def find_project_id(sid: str, code: str) -> int | None:
    result = mcp_call(sid, "find_entity", {"name": code, "limit": 5})
    items = result.get("items", []) if isinstance(result, dict) else []
    for it in items:
        if it.get("entityName") == "Project" and it.get("name", "").startswith(code):
            url = it.get("url", "")
            if "/auto/" in url:
                try:
                    return int(url.rsplit("/", 1)[-1])
                except ValueError:
                    pass
    return None


# ---------------------------------------------------------------------------
# Главная функция
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Сбор JSON-слепков состояния проектов в карточки MCP (категория «Документы ИИ»)"
    )
    ap.add_argument("--code", type=str, default=None, help="Один проект (override)")
    ap.add_argument("--dry-run", action="store_true", help="Без загрузки в MCP")
    ap.add_argument("--no-html", action="store_true", default=True, help="Пропустить HTML")
    args = ap.parse_args()

    projects = [args.code] if args.code else DEFAULT_PROJECTS

    print(bold(f"\n📸 fst-project-health-snapshot v{SNAPSHOT_VERSION}"))
    print(f"   Проекты: {projects}")
    print(f"   Режим: {'DRY-RUN (без MCP)' if args.dry_run else 'боевой (загрузка в MCP)'}")
    print(f"   Документ-категория: DocumentId={DOCUMENT_ID_AI} (Документы ИИ)")
    print()

    print("→ initialize MCP... ", end="", flush=True)
    t0 = time.perf_counter()
    sid, server_info = mcp_init()
    print(green(f"OK ({fmt_ms((time.perf_counter()-t0)*1000)}) — {server_info.get('name')} {server_info.get('version')}"))

    results = []
    overall_t0 = time.perf_counter()
    for code in projects:
        t0 = time.perf_counter()
        result = {"code": code, "status": "ok", "file_name": None, "file_id": None,
                  "duration_ms": 0, "error": None}
        try:
            project_id = find_project_id(sid, code)
            if project_id is None:
                raise RuntimeError(f"project_id не найден для кода {code}")
            print(f"   project_id={project_id}")

            md_path = run_fst_project_health(code, no_html=args.no_html)

            print(f"→ {code}: парсинг MD... ", end="", flush=True)
            data = parse_md_to_data(md_path)
            print(green(f"OK (verdict={data.get('verdict', '?')})"))

            print(f"→ {code}: обёртка в snapshot... ", end="", flush=True)
            snapshot = wrap_into_snapshot(data, code, project_id)
            local_path = save_local(snapshot, code)
            print(green(f"OK → {local_path.name} ({local_path.stat().st_size} байт)"))

            file_name = build_filename(code)
            result["file_name"] = file_name
            if args.dry_run:
                print(yellow(f"→ {code}: DRY-RUN, загрузка в MCP пропущена"))
            else:
                print(f"→ {code}: загрузка в MCP (DocumentId={DOCUMENT_ID_AI})... ", end="", flush=True)
                t_upload = time.perf_counter()
                upload_result = upload_to_mcp(sid, snapshot, project_id, file_name)
                upload_duration = (time.perf_counter() - t_upload) * 1000
                if isinstance(upload_result, dict) and upload_result.get("success"):
                    file_id = upload_result.get("id")
                    result["file_id"] = file_id
                    print(green(f"OK ({fmt_ms(upload_duration)}) — FileId={file_id}"))
                else:
                    err = upload_result.get("error") if isinstance(upload_result, dict) else str(upload_result)
                    print(red(f"FAIL: {err}"))
                    result["status"] = "upload_error"
                    result["error"] = err

        except Exception as e:
            result["status"] = "exception"
            result["error"] = str(e)
            print(red(f"\n✗ {code}: {type(e).__name__}: {e}"))
        result["duration_ms"] = (time.perf_counter() - t0) * 1000
        results.append(result)

    overall_duration_ms = (time.perf_counter() - overall_t0) * 1000
    ok = sum(1 for r in results if r["status"] == "ok")
    fail = len(results) - ok

    print(bold(f"\n{'='*60}"))
    print(bold(f"ИТОГ: {ok} ok, {fail} fail за {fmt_ms(overall_duration_ms)}"))
    print(bold(f"{'='*60}"))
    for r in results:
        sym = "✓" if r["status"] == "ok" else "✗"
        extra = f" FileId={r['file_id']}" if r["file_id"] else f" файл={r['file_name']}"
        print(f"  {sym} {r['code']} ({fmt_ms(r['duration_ms'])}) — {r['status']}{extra}")

    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())