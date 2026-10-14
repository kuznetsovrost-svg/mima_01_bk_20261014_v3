#!/usr/bin/env python3
"""
fst-project-health-snap-md: еженедельное сохранение MD-слепков проектов
в карточки MCP (категория "Документы ИИ").

v1.0.19: Полная переработка под новую нумерацию разделов и самодостаточный MD.

Архитектурные гарантии (2026-09-23):
- MD = полный source of truth. HTML рендерится из MD без обращения к MCP.
- Снапшот = MD от `run_all.py` без модификаций. YAML-front-matter
  (snapshot_timestamp, generator, skill_version, schema_version) уже
  стоит в начале — `build_html_report.py` его читает приоритетно.
- Никакого `<!-- snapshot_timestamp ... -->` от snap-md больше не пишем —
  это работа YAML-front-matter от `rebuild_report.py`.
- HTML собранный из снапшота = HTML собранный из живого прогона, потому
  что `build_html_report.py::build_html` принимает один и тот же MD +
  `proj_<code>.json` в обоих случаях. Версия рендера = `1.0.19`.

Назначение:
- Для каждого проекта из PROJECTS запускает `run_all.py --code <code>`
  (собирает MD в `/tmp/project_<code>_report.md`).
- Копирует этот MD-файл в карточку проекта через `upload_entity_file`,
  с именем `Слепок fst-project-health-snapshot-<code>-<timestamp>.MD`.

Альтернативный запуск с явным списком:
    python3 run_snap_md.py --codes 504-595 503-152 503-434 504-314
"""

import argparse
import base64
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Локальный модуль логирования (см. logging_utils.py).
from logging_utils import RunLogger, decode_jwt_user

# ---------------------------------------------------------------------------
# Конфигурация
# ---------------------------------------------------------------------------

# Тестируемый проект по умолчанию — список из 4 проектов.
DEFAULT_PROJECTS = ["504-595", "503-152", "503-434", "504-314"]

# Версии (v1.0.19 — синхронизировано со всем семейством fst-project-health-*).
# SOURCE_SKILL_VERSION читается из SKILL.md основного скилла автоматически
# (см. _read_source_skill_version()), чтобы не править руками при каждом bump.
SKILL_NAME = "fst-project-health-snap-md"
SKILL_VERSION = "1.0.19"
SCHEMA_VERSION = "1.0.0"  # версия схемы YAML-front-matter (== версия fst-project-health)
SOURCE_SKILL_NAME = "fst-project-health"
SOURCE_SKILL_VERSION_FALLBACK = "1.0.19"  # на случай если SKILL.md не читается

# Путь к скиллу fst-project-health (БЕЗ модификации, только subprocess).
# На другом сервере переопределяется через env-var FST_PROJECT_HEALTH_PATH.
SKILL_DIR = Path(
    os.environ.get(
        "FST_PROJECT_HEALTH_PATH",
        "/root/.hermes/profiles/fst-control/skills/productivity/fst-project-health",
    )
)
SKILL_SCRIPTS = SKILL_DIR / "scripts"

# MCP-параметры.
MCP_URL = os.environ.get("MCP_URL", "https://ppreplica.hera.pmpractice.ru/mcp")
DOCUMENT_ID_AI = 70139  # категория "Документы ИИ" в PMForesight
ENTITY_NAME = "Project"
TIMEOUT_INITIALIZE = 30
TIMEOUT_TOOLS_CALL = 60

# ENV-файлы.
ENV_FILE_CANDIDATES = [
    Path(__file__).resolve().parent.parent / ".env",
    Path.home() / ".hermes/profiles/fst-control/.env",
]

# Префикс имени файла.
FILE_PREFIX = "Слепок fst-project-health-snapshot-"
FILE_EXT = ".MD"  # именно заглавными, как принято в PMForesight

# Папка для локальных копий.
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "outputs"

# Таймаут одного прогона run_all.py.
PIPELINE_TIMEOUT = 300


# ANSI-цвета.
def _c(code, text):
    return f"\033[{code}m{text}\033[0m"
def green(t): return _c("32", t)
def yellow(t): return _c("33", t)
def red(t): return _c("31", t)
def bold(t): return _c("1", t)


# ---------------------------------------------------------------------------
# MCP-клиент
# ---------------------------------------------------------------------------

def _load_token() -> str:
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
    resp.encoding = "utf-8"
    for line in resp.text.splitlines():
        if line.startswith("data: "):
            try:
                import json
                return json.loads(line[6:])
            except Exception as e:
                raise RuntimeError(f"[{context}] невалидный JSON: {e}; line[:200]={line[:200]}")
    raise RuntimeError(f"[{context}] нет data-строки в SSE; status={resp.status_code}")


def mcp_init() -> tuple[str, dict]:
    import requests
    token = _load_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    payload = {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "fst-project-health-snap-md", "version": "1.0.0"},
        },
    }
    resp = requests.post(MCP_URL, json=payload, headers=headers, timeout=TIMEOUT_INITIALIZE)
    resp.raise_for_status()
    sid = resp.headers.get("mcp-session-id")
    if not sid:
        raise RuntimeError(f"сервер не вернул mcp-session-id")
    envelope = _parse_sse(resp, "initialize")
    server_info = envelope.get("result", {}).get("serverInfo", {})
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


def mcp_call(sid: str, tool_name: str, arguments: dict) -> dict:
    import json
    import requests
    token = _load_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "mcp-session-id": sid,
    }
    payload = {
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }
    resp = requests.post(MCP_URL, json=payload, headers=headers, timeout=TIMEOUT_TOOLS_CALL)
    resp.raise_for_status()
    envelope = _parse_sse(resp, tool_name)
    result = envelope.get("result", {})
    if result.get("isError"):
        return {"_error": result.get("content", [{}])[0].get("text", "<no msg>")}
    text = result.get("content", [{}])[0].get("text", "{}")
    try:
        return json.loads(text)
    except Exception:
        return {"_raw_text": text[:500]}


# ---------------------------------------------------------------------------
# Утилиты
# ---------------------------------------------------------------------------

def _read_source_skill_version() -> str:
    """Читает `version:` из front-matter SKILL.md основного скилла.

    Если файл недоступен или поле отсутствует — возвращает fallback.
    Это позволяет source_skill_version в MD-снапшоте всегда совпадать
    с реальной версией fst-project-health (без ручных правок в двух местах).
    """
    skill_md = SKILL_DIR / "SKILL.md"
    if not skill_md.exists():
        return SOURCE_SKILL_VERSION_FALLBACK
    try:
        text = skill_md.read_text(encoding="utf-8")
    except Exception:
        return SOURCE_SKILL_VERSION_FALLBACK
    # Парсим front-matter (между первыми ---...---)
    import re as _re
    m = _re.match(r"^---\s*\n(.+?)\n---\s*\n", text, _re.DOTALL)
    if not m:
        return SOURCE_SKILL_VERSION_FALLBACK
    for line in m.group(1).splitlines():
        kv = _re.match(r"^version\s*:\s*(\S+)\s*$", line)
        if kv:
            return kv.group(1).strip().strip('"').strip("'")
    return SOURCE_SKILL_VERSION_FALLBACK


def timestamp_for_filename() -> str:
    """YYYY-MM-DD_HH-MM-SS — формат с секундами."""
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def build_filename(project_code: str) -> str:
    return f"{FILE_PREFIX}{project_code}-{timestamp_for_filename()}{FILE_EXT}"


def fmt_ms(ms) -> str:
    if ms is None:
        return "—"
    if ms >= 1000:
        return f"{ms/1000:.2f} s"
    return f"{ms:.0f} ms"


# ---------------------------------------------------------------------------
# Шаг 1: запуск fst-project-health через subprocess
# ---------------------------------------------------------------------------

def run_fst_project_health(code: str, generator: str = SKILL_NAME) -> Path:
    """Запускает run_all.py, возвращает путь к MD.

    v1.0.19: передаёт `--generator {SKILL_NAME}` чтобы в YAML атрибутировать
    этот MD как сгенерированный snap-md (а не run_all.py напрямую).
    """
    cmd = [
        sys.executable,
        str(SKILL_SCRIPTS / "run_all.py"),
        "--code", code,
        "--no-cache",
        "--no-html",     # нам не нужен HTML — экономим время
        "--generator", generator,  # v1.0.19: атрибуция генератора
    ]
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
# Шаг 2: сохранение локальной копии MD
# ---------------------------------------------------------------------------

def save_local(md_path: Path, project_code: str) -> Path:
    """Сохраняет локальную копию MD от run_all.py БЕЗ модификаций.

    v1.0.19: MD уже полностью самодостаточен благодаря YAML-front-matter
    от `rebuild_report.py` (snapshot_timestamp, generator, skill_version).
    Раньше мы добавляли отдельный `<!-- snapshot_timestamp: ... -->` —
    сейчас это не нужно, так как YAML берётся приоритетно в
    `build_html_report.py::build_html`.

    Гарантия идентичности с живым прогоном:
        cp /tmp/project_<code>_report.md <dest>   # это всё, что мы делаем
    """
    import shutil
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    local_name = f"{project_code}_{timestamp_for_filename()}.md"
    local_path = OUTPUT_DIR / local_name
    shutil.copyfile(md_path, local_path)
    return local_path


# ---------------------------------------------------------------------------
# Шаг 3: загрузка в MCP
# ---------------------------------------------------------------------------

def upload_to_mcp(sid: str, md_path: Path, project_id: int, file_name: str) -> dict:
    """Загружает MD как документ в карточку проекта."""
    content = md_path.read_bytes()
    content_b64 = base64.b64encode(content).decode("ascii")
    return mcp_call(sid, "upload_entity_file", {
        "entityName": ENTITY_NAME,
        "dataId": str(project_id),
        "documentId": DOCUMENT_ID_AI,
        "uploadedFileName": file_name,
        "uploadedFileContentBase64": content_b64,
    })


# ---------------------------------------------------------------------------
# Шаг 4: получение project_id
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

def _classify_error(e: Exception, mcp_result=None) -> dict:
    """Возвращает dict с полями для записи в лог при ошибке."""
    info = {"type": type(e).__name__, "message": str(e)[:300]}
    if isinstance(e, requests.HTTPError if False else Exception):
        pass
    # Прячем в глобальный скоуп для type-checking
    import requests as _r
    if isinstance(e, _r.HTTPError) and getattr(e, 'response', None) is not None:
        info["http_code"] = e.response.status_code
        try:
            info["raw"] = e.response.text[:300]
        except Exception:
            pass
    if mcp_result is not None and isinstance(mcp_result, dict):
        # MCP вернул isError: true — текст ошибки в content[0].text
        if mcp_result.get("_error") or mcp_result.get("isError"):
            info["raw"] = mcp_result.get("_error") or str(mcp_result)[:300]
    return info


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Сохранение MD-слепков состояния проектов в карточки MCP. "
                    "Философия: «скрипт может — делает, не может — пишет в лог». "
                    "Никогда не падает на середине цикла по проектам."
    )
    ap.add_argument("--code", type=str, default=None,
                    help="ОДИН проект (legacy-режим). Используйте --codes для массовых прогонов.")
    ap.add_argument("--codes", nargs="+", default=None,
                    help="МАССОВЫЙ запуск: коды проектов через пробел. "
                         "Пример: --codes 504-595 503-152 503-434 504-314")
    ap.add_argument("--dry-run", action="store_true", help="Без загрузки в MCP")
    ap.add_argument("--no-log", action="store_true",
                    help="Не писать лог (по умолчанию лог пишется всегда — для согласованности с fetch_snapshot.py).")
    args = ap.parse_args()

    # Защита от взаимоисключающих аргументов.
    if args.code and args.codes:
        ap.error("Укажите либо --code X, либо --codes X Y Z, не оба одновременно.")

    # Snapshot списка — копия! Чтобы случайная правка DEFAULT_PROJECTS
    # между моментом старта и моментом записи в лог не сломала аудит.
    projects_in_script = list(DEFAULT_PROJECTS)
    if args.codes:
        projects_in_run = list(args.codes)
    elif args.code:
        projects_in_run = [args.code]
    else:
        projects_in_run = list(DEFAULT_PROJECTS)

    mode = "DRY-RUN (без MCP)" if args.dry_run else "боевой (загрузка в MCP)"

    print(bold(f"\n📸 fst-project-health-snap-md v{SKILL_VERSION}"))
    print(f"   Проекты в скрипте: {projects_in_script}")
    print(f"   Проекты в этом запуске: {projects_in_run}")
    print(f"   Режим: {mode}")
    print(f"   Документ-категория: DocumentId={DOCUMENT_ID_AI} (Документы ИИ)")
    print()

    # ------------------------------------------------------------------
    # Logger: открывается ДО MCP, чтобы даже при краше initialize
    # у нас остался лог с header'ом.
    # ------------------------------------------------------------------
    run_started_at = datetime.now()
    if args.no_log:
        logger = RunLogger(now=run_started_at, enabled=False)
        print(f"   Лог: (отключён)")
    else:
        logger = RunLogger(now=run_started_at)
        print(f"   Лог: {logger.log_file}")

    # Параметры, которые потребуются для header.
    try:
        token = _load_token()
    except Exception as e:
        token = ""
        print(red(f"⚠ PMP_TOKEN не найден: {e}. Лог будет с неполным header'ом."))

    token_user = decode_jwt_user(token) if token else {"name": "n/a", "email": "n/a", "sub": "n/a"}

    # Инициализация MCP — если не получится, проставим n/a и попробуем дальше.
    sid_for_role = lambda: ""  # placeholder до успешного initialize
    role = "n/a (MCP init skipped)"
    sid = None
    try:
        print("→ initialize MCP... ", end="", flush=True)
        t0 = time.perf_counter()
        sid, server_info = mcp_init()
        print(green(f"OK ({fmt_ms((time.perf_counter()-t0)*1000)}) — {server_info.get('name')} {server_info.get('version')}"))
        sid_for_role = lambda: sid
        # Попробуем получить роль (если MCP доступен)
        from logging_utils import get_user_role_via_mcp
        role = get_user_role_via_mcp(sid_for_role)
    except Exception as e:
        print(red(f"MCP init FAIL: {type(e).__name__}: {e}"))
        # Продолжаем без MCP — каждый проект в try/except и сам разберётся.

    # Header лога: пишем сейчас, после MCP init (или его краха).
    if logger:
        logger.log_header(
            version=SKILL_VERSION,
            token_user=token_user,
            role=role,
            projects_in_script=projects_in_script,
            projects_in_run=projects_in_run,
            mode=mode,
        )

    # ------------------------------------------------------------------
    # ОСНОВНОЙ ЦИКЛ — never-fail: каждый проект в try/except/continue.
    # ------------------------------------------------------------------
    overall_t0 = time.perf_counter()
    try:
        for code in projects_in_run:
            t0 = time.perf_counter()
            try:
                if sid is None:
                    raise RuntimeError("MCP не инициализирован — пропуск проекта")

                project_id = find_project_id(sid, code)
                if project_id is None:
                    # not_found — не исключение, просто статус в логе
                    logger.log_project(
                        code, "not_found",
                        error={"type": "find_entity",
                               "message": f"project_id не найден для кода {code} (проверьте право на чтение / существование проекта)"},
                        duration_ms=(time.perf_counter()-t0)*1000,
                    )
                    print(red(f"\n✗ {code}: not_found, проект отсутствует или нет прав на чтение"))
                    continue
                print(f"   project_id={project_id}")

                md_path = run_fst_project_health(code)
                local_path = save_local(md_path, code)
                print(f"   локальная копия: {local_path.name} ({local_path.stat().st_size} байт)")

                md_for_upload = local_path
                file_name = build_filename(code)

                if args.dry_run:
                    print(yellow(f"→ {code}: DRY-RUN, загрузка в MCP пропущена"))
                    logger.log_project(
                        code, "ok", file_name=file_name,
                        duration_ms=(time.perf_counter()-t0)*1000,
                    )
                    continue

                # Загрузка
                print(f"→ {code}: загрузка в MCP (DocumentId={DOCUMENT_ID_AI})... ", end="", flush=True)
                t_upload = time.perf_counter()
                upload_result = upload_to_mcp(sid, md_for_upload, project_id, file_name)
                upload_duration = (time.perf_counter() - t_upload) * 1000
                if isinstance(upload_result, dict) and upload_result.get("success"):
                    file_id = upload_result.get("id")
                    print(green(f"OK ({fmt_ms(upload_duration)}) — FileId={file_id}"))
                    logger.log_project(
                        code, "ok", file_id=file_id, file_name=file_name,
                        duration_ms=(time.perf_counter()-t0)*1000,
                    )
                elif isinstance(upload_result, dict) and (upload_result.get("_error") or upload_result.get("isError")):
                    err_msg = upload_result.get("_error") or upload_result.get("content", [{}])[0].get("text", "no msg")
                    print(red(f"FAIL: {err_msg[:100]}"))
                    logger.log_project(
                        code, "upload_error",
                        file_name=file_name,
                        error={"type": "upload_entity_file",
                               "message": err_msg if isinstance(err_msg, str) else str(err_msg)[:300],
                               "http_code": "MCP-isError"},
                        duration_ms=(time.perf_counter()-t0)*1000,
                    )
                else:
                    err = str(upload_result)[:300]
                    print(red(f"FAIL (неизвестный ответ): {err[:100]}"))
                    logger.log_project(
                        code, "upload_error",
                        file_name=file_name,
                        error={"type": "unknown",
                               "message": f"Неожиданный формат ответа: {err}",
                               "raw": str(upload_result)[:300]},
                        duration_ms=(time.perf_counter()-t0)*1000,
                    )

            except Exception as e:
                # Любое неперехваченное исключение → лог, continue.
                info = _classify_error(e)
                logger.log_project(
                    code, "exception",
                    error=info,
                    duration_ms=(time.perf_counter()-t0)*1000,
                )
                print(red(f"\n✗ {code}: {type(e).__name__}: {e}"))
                # continue — НЕ raise, идём к следующему проекту.

        ok = sum(1 for r in logger._results if r["ok"])
        fail = len(logger._results) - ok
        overall_duration_ms = (time.perf_counter() - overall_t0) * 1000

        print(bold(f"\n{'='*60}"))
        print(bold(f"ИТОГ: {ok} ok, {fail} fail за {fmt_ms(overall_duration_ms)}"))
        print(bold(f"{'='*60}"))
        for r in logger._results:
            sym = "✓" if r["ok"] else "✗"
            print(f"  {sym} {r['code']} — {r['status']}")

    finally:
        # Trailer пишется ВСЕГДА, даже при KeyboardInterrupt.
        try:
            logger.log_trailer(total_ms=(time.perf_counter()-overall_t0)*1000)
        except Exception:
            pass
        logger.close()
        if logger.enabled:
            print(f"\n📝 Лог сохранён: {logger.log_file}")
        else:
            print(f"\n📝 Логирование отключено (--no-log)")

    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())