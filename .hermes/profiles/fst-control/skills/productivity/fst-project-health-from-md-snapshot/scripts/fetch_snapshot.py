#!/usr/bin/env python3
"""
fetch_snapshot.py — извлечение MD-слепков из карточек проектов в MCP.

Что делает:
    Подключается к MCP, читает список файлов из «Документы ИИ»
    (DocumentId=70139) нужного проекта, выбирает ОДИН снимок
    по заданному критерию, скачивает MD, сохраняет в локальный кэш.

Куда кладёт скачанное:
    ~/.hermes/profiles/fst-control/cache/snapshots/<code>_<timestamp>.md

Когда использовать:
    - Хотим HTML-отчёт за прошлую дату (передать MD в build_html.py).
    - Хотим прочитать снапшот для анализа без обращения к live MCP.
    - Хотим массово выгрузить снимки (--codes) для трендового анализа.

v1.0.19: never-fail. Каждый проект в try/except/continue.
Обязательное логирование в logs/<ISO-timestamp>.log.

Использование:
    # Один проект, последний снимок:
    python3 fetch_snapshot.py --code 504-595 --last

    # Один проект, ближайший к точке во времени (для cron):
    python3 fetch_snapshot.py --code 504-595 --at "2026-09-23 21:00"

    # Один проект, конкретный timestamp:
    python3 fetch_snapshot.py --code 504-595 --exact 2026-09-23T21:53:09

    # Самый ранний (для трендов):
    python3 fetch_snapshot.py --code 504-595 --first

    # Интерактивный выбор из списка:
    python3 fetch_snapshot.py --code 504-595 --pick

    # Просто список снимков (без скачивания):
    python3 fetch_snapshot.py --code 504-595 --list

    # Массовый прогон (последние снимки по 4 проектам):
    python3 fetch_snapshot.py --codes 504-595 503-152 503-434 504-314 --last

Режимы выбора:
    --nearest (default)  точка во времени в --at, ближайший снимок
    --exact              ровно этот timestamp (ошибка если нет)
    --last               самый свежий
    --first              самый ранний
    --pick               интерактивный выбор
    --list               только список (--at / --exact игнорируются)

См. PLAYBOOK §3 для детального описания режимов.
"""

import argparse
import base64
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from logging_utils import RunLogger, decode_jwt_user, get_user_role_via_mcp

# --- Конфигурация ----------------------------------------------------------

MCP_URL = os.environ.get("MCP_URL", "https://ppreplica.hera.pmpractice.ru/mcp")
DOCUMENT_ID_AI = 70139  # категория «Документы ИИ»
ENTITY_NAME = "Project"
TIMEOUT_TOOLS_CALL = 30

# Кэш скачанных MD.
CACHE_DIR = Path.home() / ".hermes/profiles/fst-control/cache/snapshots"

# ENV.
ENV_FILE_CANDIDATES = [
    Path(__file__).resolve().parent.parent / ".env",
    Path.home() / ".hermes/profiles/fst-control/.env",
]

SKILL_VERSION = "1.0.19"


# --- Утилиты ---------------------------------------------------------------

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
    raise RuntimeError("PMP_TOKEN не найден")


def _parse_sse(resp, ctx: str) -> dict:
    body = resp.content.decode("utf-8", errors="replace")
    for line in body.splitlines():
        if line.startswith("data: "):
            try:
                return json.loads(line[6:])
            except Exception as e:
                raise RuntimeError(f"[{ctx}] невалидный JSON: {e}; line[:200]={line[:200]}")
    raise RuntimeError(f"[{ctx}] нет data-строки в SSE; status={resp.status_code}")


def _c(code, text):
    return f"\033[{code}m{text}\033[0m"
def green(t): return _c("32", t)
def yellow(t): return _c("33", t)
def red(t): return _c("31", t)
def bold(t): return _c("1", t)


def fmt_ms(ms):
    if ms is None:
        return "—"
    if ms >= 1000:
        return f"{ms/1000:.2f} s"
    return f"{ms:.0f} ms"


# --- MCP клиент ------------------------------------------------------------

def mcp_init():
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
            "clientInfo": {"name": "fst-project-health-from-md-snapshot", "version": "1.0.19"},
        },
    }
    resp = requests.post(MCP_URL, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    sid = resp.headers.get("mcp-session-id")
    if not sid:
        raise RuntimeError("сервер не вернул mcp-session-id")
    envelope = _parse_sse(resp, "initialize")
    try:
        requests.post(
            MCP_URL,
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
            headers={**headers, "mcp-session-id": sid},
            timeout=10,
        )
    except Exception:
        pass
    return sid


def mcp_call(sid: str, tool_name: str, arguments: dict) -> dict:
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


# --- Извлечение списка снимков --------------------------------------------

def list_snapshots(sid: str, project_id: int, code: str) -> list[dict]:
    """Возвращает список всех снимков из карточки проекта.

    Каждый элемент: {"name": ..., "physicalFileId": "...", "fileSize": N,
                     "timestamp": "YYYY-MM-DD HH:MM:SS" (извлечён из имени или изнутри)}
    """
    raw = mcp_call(sid, "list_files", {
        "documentId": DOCUMENT_ID_AI,
        "dataId": project_id,
        "className": ENTITY_NAME,
    })
    items = raw if isinstance(raw, list) else raw.get("items", [])

    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        name = it.get("name", "")
        # Извлекаем timestamp из имени файла: "...-YYYY-MM-DD_HH-MM-SS"
        m = re.search(r"(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})", name)
        ts_iso = None
        if m:
            date = m.group(1)
            time_part = m.group(2).replace("-", ":")
            ts_iso = f"{date} {time_part}"
        out.append({
            "name": name,
            "physicalFileId": it.get("physicalFileId"),
            "fileSize": it.get("fileSize", 0),
            "url": it.get("url", ""),
            "timestamp": ts_iso,
        })
    # Сортируем по timestamp'у (строковое сравнение для ISO-формата работает)
    out.sort(key=lambda x: x["timestamp"] or "")
    return out


def find_project_id(sid: str, code: str) -> int | None:
    raw = mcp_call(sid, "find_entity", {"name": code, "limit": 5})
    items = raw.get("items", []) if isinstance(raw, dict) else raw
    for it in items:
        if isinstance(it, dict) and it.get("entityName") == ENTITY_NAME and it.get("name", "").startswith(code):
            url = it.get("url", "")
            if "/auto/" in url:
                try:
                    return int(url.rsplit("/", 1)[-1])
                except ValueError:
                    pass
    return None


def download_md(sid: str, physical_id: str) -> bytes:
    """Скачивает MD из MCP через resources/read (blob — base64).

    Стратегия retry (v1.0.19): если ответ пустой (MCP иногда возвращает
    `result: {}` без contents), пробуем ещё раз. До 3 попыток, каждая
    с **новой сессией MCP** (mcp_init заново) — старая сессия иногда
    «застревает» с пустым ответом.
    """
    import time as _time
    import requests
    token = _load_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    payload = {
        "jsonrpc": "2.0", "id": 1, "method": "resources/read",
        "params": {"uri": f"file://download-file/{physical_id}"},
    }

    last_error = None
    for attempt in range(3):
        # Каждая попытка с новой сессией (старая могла «застрять»).
        try:
            sid_local = mcp_init()
        except Exception as e:
            last_error = RuntimeError(f"mcp_init failed: {e}")
            if attempt < 2:
                _time.sleep(1)
                continue
            raise last_error

        headers["mcp-session-id"] = sid_local
        try:
            resp = requests.post(MCP_URL, json=payload, headers=headers, timeout=60)
            resp.raise_for_status()
            envelope = _parse_sse(resp, "resources/read")
            result = envelope.get("result", {})

            if result.get("isError"):
                err_msg = result.get("content", [{}])[0].get("text", "<no msg>")
                raise RuntimeError(f"isError: {err_msg}")

            contents = result.get("contents", [])
            if not contents:
                last_error = RuntimeError(f"empty contents (attempt {attempt + 1}/3)")
                if attempt < 2:
                    _time.sleep(1)
                    continue
                raise last_error

            blob_b64 = contents[0].get("blob", "")
            if not blob_b64:
                url = contents[0].get("text") or contents[0].get("url", "")
                if url.startswith("http"):
                    r2 = requests.get(url, timeout=60)
                    r2.raise_for_status()
                    return r2.content
                raise RuntimeError("нет blob и нет url в contents[0]")
            return base64.b64decode(blob_b64)
        except (RuntimeError, requests.RequestException) as e:
            last_error = e
            if attempt < 2:
                _time.sleep(1)
                continue
            raise

    raise last_error


# --- Выбор снимка ----------------------------------------------------------

def select_snapshot(snapshots: list[dict], *, mode: str,
                      at: str | None = None,
                      exact: str | None = None) -> tuple[dict | None, str]:
    """Возвращает (snapshot_or_None, status_or_note).

    mode: 'last' | 'first' | 'nearest' | 'exact' | 'pick'
    """
    if not snapshots:
        return None, "no_snapshots"

    if mode == "last":
        return snapshots[-1], "ok"
    if mode == "first":
        return snapshots[0], "ok"
    if mode == "exact":
        if exact is None:
            return None, "no_target"
        # Ищем точное совпадение timestamp'а
        for s in snapshots:
            if s["timestamp"] == exact:
                return s, "ok"
        return None, "no_exact_match"
    if mode == "nearest":
        if at is None:
            return snapshots[-1], "ok"  # default — last
        target = at.replace("T", " ")
        # Если в target только дата, добавим 00:00:00
        if len(target) == 10:
            target = target + " 00:00:00"
        # Найти ближайший по timestamp
        def delta(s_ts):
            # Строковое сравнение для ISO формата — приблизительно
            # Если target меньше минимального, вернуть большую дельту
            try:
                t1 = datetime.strptime(target, "%Y-%m-%d %H:%M:%S")
                t2 = datetime.strptime(s_ts, "%Y-%m-%d %H:%M:%S")
                return abs((t1 - t2).total_seconds())
            except (ValueError, TypeError):
                return float("inf")
        candidates = [(s, delta(s["timestamp"])) for s in snapshots if s["timestamp"]]
        if not candidates:
            return snapshots[-1], "ok"
        candidates.sort(key=lambda x: x[1])
        # Если есть ничья — берём более новый (последний из равных)
        return candidates[0][0], "ok"
    if mode == "pick":
        # Интерактивный выбор
        print(bold("Снимки в карточке:"))
        for i, s in enumerate(snapshots):
            print(f"  [{i+1}] {s['timestamp'] or '?'}  {s['fileSize']:>6} байт  {s['name']}")
        print(f"  [q] отмена")
        while True:
            ans = input("Выберите номер: ").strip()
            if ans.lower() in ("q", "quit", "exit"):
                return None, "user_cancelled"
            try:
                idx = int(ans)
                if 1 <= idx <= len(snapshots):
                    return snapshots[idx-1], "ok"
            except ValueError:
                pass
            print("Неверный ввод.")
    return None, "unknown_mode"


# --- Сохранение ------------------------------------------------------------

def save_to_cache(code: str, ts: str | None, content: bytes) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe_ts = (ts or datetime.now().strftime("%Y-%m-%d %H:%M:%S")).replace(" ", "_").replace(":", "-")
    path = CACHE_DIR / f"{code}_{safe_ts}.md"
    path.write_bytes(content)
    return path


# --- main ------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Извлечение MD-слепков из карточек проектов в MCP. "
                    "Never-fail: каждый проект в try/except/continue.",
    )
    ap.add_argument("--code", type=str, default=None, help="ОДИН проект.")
    ap.add_argument("--codes", nargs="+", default=None,
                    help="МАССОВЫЙ: коды проектов через пробел.")
    ap.add_argument("--nearest", action="store_true", help="(default) Ближайший к --at.")
    ap.add_argument("--at", type=str, default=None,
                    help="Точка во времени для --nearest. Формат: 'YYYY-MM-DD HH:MM:SS' или 'YYYY-MM-DD'.")
    ap.add_argument("--exact", type=str, default=None,
                    help="Точный timestamp (--mode exact). 'YYYY-MM-DD HH:MM:SS'.")
    ap.add_argument("--last", action="store_true", help="Самый свежий снимок.")
    ap.add_argument("--first", action="store_true", help="Самый ранний снимок.")
    ap.add_argument("--pick", action="store_true", help="Интерактивный выбор.")
    ap.add_argument("--list", action="store_true", help="Только список (без скачивания).")
    ap.add_argument("--no-log", action="store_true",
                    help="Не писать лог (по умолчанию лог пишется всегда).")
    args = ap.parse_args()

    # Взаимоисключающие.
    if args.code and args.codes:
        ap.error("--code и --codes — взаимоисключающие")
    for flag in (args.nearest, args.exact, args.last, args.first, args.pick, args.list):
        cnt = sum([bool(args.nearest), bool(args.exact), bool(args.last),
                   bool(args.first), bool(args.pick), bool(args.list)])
        if cnt > 1:
            ap.error("--nearest, --exact, --last, --first, --pick, --list — взаимоисключающие")

    # Список проектов.
    if args.codes:
        projects = list(args.codes)
    elif args.code:
        projects = [args.code]
    else:
        ap.error("Укажите --code X или --codes X Y Z")

    # Выбор режима.
    if args.list:
        mode = "list"
    elif args.last:
        mode = "last"
    elif args.first:
        mode = "first"
    elif args.pick:
        mode = "pick"
    elif args.exact:
        mode = "exact"
    else:
        mode = "nearest"  # default

    args_summary = " ".join(sys.argv[1:])

    # --- Логгер (открываем сразу, до MCP) ---
    run_started_at = datetime.now()
    logger = RunLogger(now=run_started_at) if not args.no_log else None

    print(bold(f"\n📥 fst-project-health-from-md-snapshot v{SKILL_VERSION} (fetch)"))
    print(f"   Режим: {mode}{f' (at={args.at})' if mode == 'nearest' and args.at else ''}{f' (exact={args.exact})' if mode == 'exact' else ''}")
    print(f"   Проекты: {projects}")
    if logger:
        print(f"   Лог: {logger.log_file}")

    # --- Header лога ---
    try:
        token = _load_token()
        token_user = decode_jwt_user(token)
    except Exception:
        token_user = {"name": "n/a", "email": "n/a", "sub": "n/a"}

    sid = None
    role = "n/a (MCP init skipped)"
    try:
        sid = mcp_init()
        role = get_user_role_via_mcp(lambda: sid)
    except Exception as e:
        print(red(f"MCP init FAIL: {type(e).__name__}: {e}"))

    if logger:
        logger.log_header(
            version=SKILL_VERSION,
            token_user=token_user,
            role=role,
            action="fetch",
            projects_in_run=projects,
            args_summary=args_summary,
        )

    # --- Список снимков (общий, если нужно) ---
    # При --list печатаем списки для всех проектов.
    if mode == "list":
        for code in projects:
            try:
                project_id = find_project_id(sid, code) if sid else None
                if project_id is None:
                    print(red(f"  ✗ {code}: not_found"))
                    continue
                snaps = list_snapshots(sid, project_id, code)
                print(bold(f"\n  {code} ({len(snaps)} снимков):"))
                for i, s in enumerate(snaps):
                    print(f"    [{i+1}] {s['timestamp'] or '?'}  {s['fileSize']:>6} байт  {s['name']}")
            except Exception as e:
                print(red(f"  ✗ {code}: {type(e).__name__}: {e}"))
        if logger:
            logger.close()
        return 0

    # --- Основной цикл ---
    overall_t0 = time.perf_counter()
    try:
        for code in projects:
            t0 = time.perf_counter()
            try:
                if sid is None:
                    raise RuntimeError("MCP не инициализирован — пропуск проекта")
                project_id = find_project_id(sid, code)
                if project_id is None:
                    if logger:
                        logger.log_project(
                            code, "not_found",
                            error={"type": "find_entity",
                                   "message": f"project_id не найден для кода {code}"},
                            duration_ms=(time.perf_counter()-t0)*1000,
                        )
                    print(red(f"  ✗ {code}: not_found"))
                    continue

                snaps = list_snapshots(sid, project_id, code)
                if not snaps:
                    if logger:
                        logger.log_project(
                            code, "no_snapshots",
                            error={"type": "list_files",
                                   "message": "В карточке проекта нет снимков"},
                            duration_ms=(time.perf_counter()-t0)*1000,
                        )
                    print(yellow(f"  ✗ {code}: no_snapshots"))
                    continue

                selected, sel_status = select_snapshot(
                    snaps, mode=mode,
                    at=args.at if mode == "nearest" else None,
                    exact=args.exact if mode == "exact" else None,
                )
                if selected is None:
                    err_msg = f"select_snapshot вернул None (status={sel_status})"
                    if logger:
                        logger.log_project(
                            code, sel_status,
                            error={"type": "select", "message": err_msg},
                            duration_ms=(time.perf_counter()-t0)*1000,
                        )
                    print(red(f"  ✗ {code}: {sel_status} — {err_msg}"))
                    continue

                # Скачиваем
                content = download_md(sid, selected["physicalFileId"])
                local_path = save_to_cache(code, selected["timestamp"], content)
                if logger:
                    logger.log_project(
                        code, "ok",
                        local_path=local_path,
                        snapshot_ts=selected["timestamp"],
                        physical_id=selected["physicalFileId"],
                        duration_ms=(time.perf_counter()-t0)*1000,
                    )
                print(green(f"  ✓ {code} → {local_path} ({len(content)} bytes)"))
                print(f"     snapshot_ts={selected['timestamp']}")

            except Exception as e:
                err_msg = f"{type(e).__name__}: {e}"
                if logger:
                    logger.log_project(
                        code, "exception",
                        error={"type": type(e).__name__, "message": str(e)[:300]},
                        duration_ms=(time.perf_counter()-t0)*1000,
                    )
                print(red(f"  ✗ {code}: {err_msg}"))
                # continue — следующий проект.

        ok = sum(1 for r in (logger._results if logger else []) if r["ok"])
        total = len(logger._results) if logger else len(projects)
        print(bold(f"\n{'='*60}"))
        print(bold(f"ИТОГ: {ok}/{total} ok"))
        print(bold(f"{'='*60}"))

    finally:
        if logger:
            try:
                logger.log_trailer(total_ms=(time.perf_counter()-overall_t0)*1000)
            except Exception:
                pass
            logger.close()
            print(f"\n📝 Лог сохранён: {logger.log_file}")

    # Возвращаем 1 если были failures (для скриптовых пайплайнов).
    fail = total - ok
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
