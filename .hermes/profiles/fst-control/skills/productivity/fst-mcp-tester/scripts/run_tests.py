#!/usr/bin/env python3
"""
fst-mcp-tester: тестирует все методы MCP, используемые в fst-project-health.

Использование:
    python3 run_tests.py              # полный прогон
    python3 run_tests.py --quick      # только latency+success (без payload-size)
    python3 run_tests.py --output X.md  # свой путь к отчёту

Читает PMP_TOKEN из .env (порядок поиска — см. SKILL.md секция "Переносимость").

Важно: тесты read-only. Не модифицируют данные на стороне MCP.
"""

import argparse
import json
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Конфигурация тестируемого проекта
# ---------------------------------------------------------------------------
# По умолчанию — 504-595 (тот же проект, что использует fst-project-health).
# Чтобы поменять проект для теста — замените TEST_PROJECT_CODE и
# TEST_PROJECT_ID. project_id берётся из fst-project-health через поиск
# по коду (find_project). Если хотите указать его руками — заполните
# TEST_PROJECT_ID и поставьте DISABLE_PROJECT_LOOKUP=True.

TEST_PROJECT_CODE = os.environ.get("MCP_TEST_PROJECT_CODE", "504-595")
TEST_PROJECT_ID = int(os.environ.get("MCP_TEST_PROJECT_ID", "4595"))
DISABLE_PROJECT_LOOKUP = os.environ.get("MCP_TEST_DISABLE_LOOKUP", "0") == "1"

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "outputs"

# Цвета (ANSI) для консоли. Если не нужны — `--no-color`.
USE_COLOR = True


def _c(code: str, text: str) -> str:
    if not USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


def green(t): return _c("32", t)
def yellow(t): return _c("33", t)
def red(t): return _c("31", t)
def bold(t): return _c("1", t)


# ---------------------------------------------------------------------------
# MCP-клиент (read-only): копия логики mcp_config из fst-project-health
# ---------------------------------------------------------------------------

MCP_URL = os.environ.get("MCP_URL", "https://ppreplica.hera.pmpractice.ru/mcp")
TIMEOUT_INITIALIZE = 30
TIMEOUT_TOOLS_CALL = 60

ENV_FILE_CANDIDATES = [
    Path(__file__).resolve().parent.parent / ".env",
    Path.home() / ".hermes/profiles/fst-control/.env",
]


def _load_token() -> str:
    tok = os.environ.get("PMP_TOKEN")
    if tok:
        return tok
    for env_path in ENV_FILE_CANDIDATES:
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line.startswith("PMP_TOKEN"):
                    _, _, v = line.partition("=")
                    v = v.strip().strip("'\"")
                    if v:
                        return v
    raise RuntimeError("PMP_TOKEN не найден ни в env, ни в .env файлах.")


def _parse_sse(resp, context: str) -> dict:
    """
    Вытаскивает JSON-RPC envelope из SSE-ответа.

    SSE-формат: поток строк, JSON-RPC идёт в первой `data:`-строке
    (Pitfall #2 из fst-project-health — принудительно UTF-8, парсим
    первую data-строку, не конкатенируем все — многострочные JSON ломаются).
    """
    resp.encoding = "utf-8"
    for line in resp.text.splitlines():
        if line.startswith("data: "):
            try:
                return json.loads(line[6:])
            except json.JSONDecodeError as e:
                raise RuntimeError(f"[{context}] невалидный JSON: {e}; line[:200]={line[:200]}")
    raise RuntimeError(f"[{context}] нет data-строки в SSE; status={resp.status_code}; body[:200]={resp.text[:200]}")


def mcp_init() -> tuple[str, dict]:
    """Initialize MCP. Возвращает (sid, serverInfo)."""
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
            "clientInfo": {"name": "fst-mcp-tester", "version": "1.0"},
        },
    }
    import requests
    resp = requests.post(MCP_URL, json=payload, headers=headers, timeout=TIMEOUT_INITIALIZE)
    resp.raise_for_status()
    sid = resp.headers.get("mcp-session-id")
    if not sid:
        raise RuntimeError(f"сервер не вернул mcp-session-id. headers={dict(resp.headers)}")
    env = _parse_sse(resp, "initialize")
    server_info = env.get("result", {}).get("serverInfo", {})
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
    """Вызов tools/call. Возвращает dict (распарсенный result.content[0].text)."""
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
    env = _parse_sse(resp, tool_name)
    result = env.get("result", {})
    if result.get("isError"):
        return {"_error": result.get("content", [{}])[0].get("text", "<no msg>")}
    text = result.get("content", [{}])[0].get("text", "{}")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"_raw_text": text[:500]}


# ---------------------------------------------------------------------------
# Тест-план: все методы MCP, которые использует fst-project-health
# ---------------------------------------------------------------------------

def build_test_plan(project_id: int) -> list[dict]:
    """
    Возвращает список тест-кейсов:
    [
        {
            "id": "T01",
            "category": "lifecycle" | "view" | "entity" | "search",
            "method": "initialize" | "tools/call: get_view" | ...,
            "description": "что проверяем",
            "args_factory": lambda: {...}  # генератор аргументов (запоминает на момент запуска)
        },
        ...
    ]
    """
    return [
        # --- lifecycle ---
        {
            "id": "T01",
            "category": "lifecycle",
            "method": "initialize",
            "description": "MCP initialize (получить mcp-session-id + serverInfo).",
            "args_factory": lambda: {},
            "skip": False,
        },

        # --- get_view ---
        {
            "id": "T10",
            "category": "view",
            "method": "tools/call: get_view",
            "description": "Project/MyProject — расширенная карточка проекта (раздел 6.8, 6.9, 6.15).",
            "args_factory": lambda: {
                "entityName": "Project",
                "viewName": "MyProject",
                "filters": {"ProjectId": project_id},
                "limit": 200,
            },
        },
        {
            "id": "T11",
            "category": "view",
            "method": "tools/call: get_view",
            "description": "Point/AllMyPoint — все КТ уровня проекта (parent=Project).",
            "args_factory": lambda: {
                "entityName": "Point",
                "viewName": "AllMyPoint",
                "filters": {"ProjectId": project_id},
                "limit": 500,
            },
        },
        {
            "id": "T12",
            "category": "view",
            "method": "tools/call: get_view",
            "description": "Point/AllFinancePoint — финансовые КТ (parent=InContract).",
            "args_factory": lambda: {
                "entityName": "Point",
                "viewName": "AllFinancePoint",
                "filters": {"ProjectId": project_id},
                "limit": 200,
            },
        },
        {
            "id": "T13",
            "category": "view",
            "method": "tools/call: get_view",
            "description": "Project/ProjectResourcePlan — ресурсный план (план/прогноз часов).",
            "args_factory": lambda: {
                "entityName": "Project",
                "viewName": "ProjectResourcePlan",
                "filters": {"ProjectId": project_id},
                "limit": 1000,
            },
        },
        {
            "id": "T14",
            "category": "view",
            "method": "tools/call: get_view",
            "description": "Project/ProjectBudgetCompleteBusiness — бюджет проекта (план/факт/прогноз).",
            "args_factory": lambda: {
                "entityName": "Project",
                "viewName": "ProjectBudgetCompleteBusiness",
                "filters": {"ProjectId": project_id},
                "limit": 500,
            },
        },
        {
            "id": "T15",
            "category": "view",
            "method": "tools/call: get_view",
            "description": "InContract/InContractBudgetBusiness — финансовый поток по контрактам.",
            "args_factory": lambda: {
                "entityName": "InContract",
                "viewName": "InContractBudgetBusiness",
                "filters": {"ProjectId": project_id},
                "limit": 500,
            },
        },
        {
            "id": "T16",
            "category": "view",
            "method": "tools/call: get_view",
            "description": "Project/ApprovedBudget — утверждённый бюджет по годам.",
            "args_factory": lambda: {
                "entityName": "Project",
                "viewName": "ApprovedBudget",
                "filters": {"ActivityId": project_id},
                "limit": 200,
            },
        },
        {
            "id": "T17",
            "category": "view",
            "method": "tools/call: get_view",
            "description": "Project/ProjectHealthCostMy — финансовое здоровье (forecast/devcost).",
            "args_factory": lambda: {
                "entityName": "Project",
                "viewName": "ProjectHealthCostMy",
                "filters": {"ProjectId": project_id},
                "limit": 100,
            },
        },

        # --- get_entity_data ---
        {
            "id": "T20",
            "category": "entity",
            "method": "tools/call: get_entity_data",
            "description": "Project/<id> — карточка проекта (полные атрибуты).",
            "args_factory": lambda: {
                "entityName": "Project",
                "data_id": str(project_id),
            },
        },

        # --- find_entity ---
        {
            "id": "T30",
            "category": "search",
            "method": "tools/call: find_entity",
            "description": "find_entity по 'MetaModel' (поиск по названию, без entityName).",
            "args_factory": lambda: {
                "name": "MetaModel",
                "limit": 5,
            },
        },
        {
            "id": "T31",
            "category": "search",
            "method": "tools/call: find_entity",
            "description": "find_entity по 'Title' (поиск значения MetaModel.Title).",
            "args_factory": lambda: {
                "name": "Title",
                "limit": 5,
            },
        },
    ]


# ---------------------------------------------------------------------------
# Запуск одного теста + замер метрик
# ---------------------------------------------------------------------------

def _count_records(result) -> tuple[int, str]:
    """Возвращает (число записей, имя поля-контейнера)."""
    if isinstance(result, dict):
        for key in ("data", "result", "rows", "items"):
            if key in result and isinstance(result[key], list):
                return len(result[key]), key
        # если dict с одним list-значением
        for k, v in result.items():
            if isinstance(v, list):
                return len(v), k
        return 1, "object"
    if isinstance(result, list):
        return len(result), "list"
    return 0, "empty"


def _payload_size(obj) -> int:
    """Размер JSON-сериализованного объекта в байтах."""
    try:
        return len(json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8"))
    except Exception:
        return 0


def run_test(case: dict, sid: str, *, measure_size: bool = True) -> dict:
    """Запускает один тест, возвращает словарь с метриками."""
    import requests

    method = case["method"]
    args = case["args_factory"]()
    started_at = time.perf_counter()
    started_wall = datetime.now()

    record = {
        "id": case["id"],
        "category": case["category"],
        "method": method,
        "description": case["description"],
        "args": args,
        "started_at": started_wall.isoformat(timespec="seconds"),
    }

    try:
        if method == "initialize":
            # Re-init: внутри одного прогона можем пере-запустить сессию
            new_sid, server_info = mcp_init()
            duration_ms = (time.perf_counter() - started_at) * 1000
            record.update({
                "status": "ok",
                "duration_ms": round(duration_ms, 1),
                "session_id": new_sid,
                "server_info": server_info,
                "record_count": 0,
                "record_field": "—",
                "payload_bytes": len(json.dumps(server_info, ensure_ascii=False).encode("utf-8")),
                "error": None,
                "http_status": 200,
                "retries": 0,
            })
            return record

        # tools/call
        # simulate retries: пробуем один раз (для ретраев см. --retries флаг)
        retry_count = 0
        result = None
        last_error = None
        for attempt in range(3):  # max 3 attempts
            retry_count = attempt
            try:
                t0 = time.perf_counter()
                raw = mcp_call(sid, method.split(": ", 1)[1], args)
                t1 = time.perf_counter()
                result = raw
                last_error = None
                break
            except requests.exceptions.ReadTimeout as e:
                last_error = f"ReadTimeout: {e}"
                continue
            except requests.exceptions.RequestException as e:
                last_error = f"RequestException: {e}"
                break
            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"
                break
        duration_ms = (time.perf_counter() - started_at) * 1000

        is_error = isinstance(result, dict) and "_error" in result
        rec_count, rec_field = _count_records(result) if not is_error else (0, "—")
        size = _payload_size(result) if measure_size and not is_error else 0

        record.update({
            "status": "error" if is_error or last_error else "ok",
            "duration_ms": round(duration_ms, 1),
            "session_id": sid,
            "server_info": None,
            "record_count": rec_count,
            "record_field": rec_field,
            "payload_bytes": size if measure_size else None,
            "error": result.get("_error") if is_error else last_error,
            "http_status": 200 if not last_error else None,
            "retries": retry_count,
        })
    except Exception as e:
        duration_ms = (time.perf_counter() - started_at) * 1000
        record.update({
            "status": "exception",
            "duration_ms": round(duration_ms, 1),
            "session_id": sid,
            "server_info": None,
            "record_count": 0,
            "record_field": "—",
            "payload_bytes": 0,
            "error": f"{type(e).__name__}: {e}\n{traceback.format_exc()[:500]}",
            "http_status": None,
            "retries": 0,
        })

    return record


# ---------------------------------------------------------------------------
# Генерация MD-отчёта
# ---------------------------------------------------------------------------

def fmt_ms(ms) -> str:
    if ms is None:
        return "—"
    if ms >= 1000:
        return f"{ms/1000:.2f} s"
    return f"{ms:.0f} ms"


def fmt_bytes(n) -> str:
    if n is None:
        return "—"
    if n >= 1024 * 1024:
        return f"{n / 1024 / 1024:.2f} MB"
    if n >= 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n} B"


def render_report(results: list[dict], project_code: str, project_id: int,
                  server_info: dict, total_duration_ms: float) -> str:
    """Генерирует подробный MD-отчёт (форма для коллег)."""
    now = datetime.now()

    # Сводка
    ok_count = sum(1 for r in results if r["status"] == "ok")
    err_count = sum(1 for r in results if r["status"] == "error")
    exc_count = sum(1 for r in results if r["status"] == "exception")

    total_payload = sum(r.get("payload_bytes") or 0 for r in results)
    total_records = sum(r.get("record_count") or 0 for r in results)

    durations = [r["duration_ms"] for r in results if r.get("duration_ms") is not None]
    avg_ms = sum(durations) / len(durations) if durations else 0
    max_ms = max(durations) if durations else 0
    min_ms = min(durations) if durations else 0
    p95_idx = int(len(durations) * 0.95) if durations else 0
    durations_sorted = sorted(durations)
    p95_ms = durations_sorted[p95_idx] if durations_sorted else 0

    lines = []
    W = lines.append

    W(f"# Отчёт тестирования MCP (`fst-mcp-tester`)")
    W("")
    W(f"**Дата прогона:** {now.strftime('%Y-%m-%d %H:%M:%S')}")
    W(f"**Тестируемый проект:** `{project_code}` (id={project_id})")
    W(f"**MCP URL:** `{MCP_URL}`")
    W(f"**ServerInfo:** `{server_info.get('name', '?')} {server_info.get('version', '?')}`")
    W(f"**Общее время прогона:** {fmt_ms(total_duration_ms)}")
    W(f"**Всего тестов:** {len(results)} (ok={ok_count}, error={err_count}, exception={exc_count})")
    W("")
    W("> Тесты read-only. Данные в MCP **не модифицируются**.")
    W("")

    # Сводная таблица
    W("## 1. Executive summary")
    W("")
    W("| Метрика | Значение |")
    W("|---|---|")
    W(f"| Успешных тестов | **{ok_count} / {len(results)}** ({ok_count*100//max(1,len(results))}%) |")
    W(f"| Тестов с ошибкой | {err_count} |")
    W(f"| Тестов с исключением | {exc_count} |")
    W(f"| Среднее время ответа | {fmt_ms(avg_ms)} |")
    W(f"| Медиана | {fmt_ms(durations_sorted[len(durations)//2] if durations_sorted else 0)} |")
    W(f"| Min / Max | {fmt_ms(min_ms)} / {fmt_ms(max_ms)} |")
    W(f"| P95 | {fmt_ms(p95_ms)} |")
    W(f"| Суммарный объём payloads | {fmt_bytes(total_payload)} |")
    W(f"| Суммарно записей в ответах | {total_records:,} |")
    W("")

    # По категориям
    W("## 2. Результаты по категориям")
    W("")
    cats = {}
    for r in results:
        cats.setdefault(r["category"], []).append(r)
    for cat, items in sorted(cats.items()):
        ok = sum(1 for r in items if r["status"] == "ok")
        avg = sum(r["duration_ms"] for r in items if r.get("duration_ms")) / max(1, len(items))
        W(f"### {cat} — {ok}/{len(items)} ok, среднее {fmt_ms(avg)}")
        W("")
    W("")

    # Детальная таблица
    W("## 3. Детальная таблица тестов")
    W("")
    W("| # | Категория | Метод | Описание | Статус | Время | Записей | Payload | Ретраев | Ошибка |")
    W("|---|---|---|---|---|---|---|---|---|---|")
    for r in results:
        method_short = r["method"].replace("tools/call: ", "")
        desc = r["description"][:60].replace("|", "\\|")
        status = {
            "ok": "✅ ok",
            "error": "⚠️ error",
            "exception": "❌ exception",
        }.get(r["status"], r["status"])
        err = (r.get("error") or "—")
        if err != "—":
            err = err.replace("\n", " ")[:50]
        W(f"| {r['id']} | {r['category']} | `{method_short}` | {desc} | "
          f"{status} | {fmt_ms(r['duration_ms'])} | "
          f"{r.get('record_count', 0):,} | {fmt_bytes(r.get('payload_bytes'))} | "
          f"{r.get('retries', 0)} | {err} |")
    W("")

    # Гистограмма латентности (ASCII)
    W("## 4. Латентность (ASCII-гистограмма)")
    W("")
    if durations:
        max_d = max(durations)
        bucket = max(1, max_d / 20)
        buckets = [0] * 20
        for d in durations:
            idx = min(int(d / bucket), 19)
            buckets[idx] += 1
        max_count = max(buckets) or 1
        W("```")
        W("Диапазон           | Кол-во | Гистограмма")
        for i, c in enumerate(buckets):
            lo = i * bucket
            hi = (i + 1) * bucket
            bar = "█" * int(c * 30 / max_count)
            W(f"{fmt_ms(lo):>10} - {fmt_ms(hi):<10}| {c:>5}  | {bar}")
        W("```")
    W("")

    # Сводка payloads по вызовам
    W("## 5. Payload-размеры (по убыванию)")
    W("")
    by_size = sorted([r for r in results if r.get("payload_bytes")],
                     key=lambda x: x["payload_bytes"], reverse=True)
    W("| # | View | Размер | Записей | Байт/запись |")
    W("|---|---|---|---|---|")
    for r in by_size:
        rc = r.get("record_count", 0) or 1
        bpr = (r.get("payload_bytes", 0) or 0) // rc
        W(f"| {r['id']} | `{r['method'].replace('tools/call: ', '')}` | "
          f"{fmt_bytes(r['payload_bytes'])} | {r.get('record_count', 0):,} | "
          f"{fmt_bytes(bpr)} |")
    W("")

    # Errors & warnings
    errs = [r for r in results if r["status"] != "ok"]
    if errs:
        W("## 6. Ошибки и предупреждения")
        W("")
        for r in errs:
            W(f"### {r['id']} — {r['method']}")
            W(f"**Описание:** {r['description']}")
            W(f"**Статус:** {r['status']}")
            W(f"**Время:** {fmt_ms(r['duration_ms'])}")
            W(f"**Ошибка:**")
            W("```")
            W((r.get("error") or "—").replace("```", "'''"))
            W("```")
            W("")
    else:
        W("## 6. Ошибки и предупреждения")
        W("")
        W("✅ Ошибок нет.")
        W("")

    # Рекомендации
    W("## 7. Рекомендации по оптимизации")
    W("")
    recs = []

    slow_tests = sorted(results, key=lambda x: x.get("duration_ms") or 0, reverse=True)[:3]
    if slow_tests:
        names = ", ".join(f"`{r['id']}`" for r in slow_tests)
        recs.append(f"🐢 Самые медленные вызовы — {names}. Рассмотрите кеширование или "
                    f"`fetch_with_cache` (5 мин TTL) в `fst-project-health::project_indicators.py`.")

    big_payloads = [r for r in results if (r.get("payload_bytes") or 0) > 500_000]
    if big_payloads:
        names = ", ".join(f"`{r['id']}`" for r in big_payloads)
        recs.append(f"📦 Большие payloads (>500 KB) — {names}. "
                    f"Проверьте, не запрашиваются ли лишние поля.")

    many_records = [r for r in results if (r.get("record_count") or 0) > 1000]
    if many_records:
        names = ", ".join(f"`{r['id']}`" for r in many_records)
        recs.append(f"📊 Много записей (>1000) — {names}. "
                    f"Уточните фильтры в `fst-project-health`.")

    retried = [r for r in results if (r.get("retries") or 0) > 0]
    if retried:
        names = ", ".join(f"`{r['id']}`" for r in retried)
        recs.append(f"🔄 Были ретраи — {names}. "
                    f"Увеличьте `TIMEOUT_TOOLS_CALL` (сейчас {TIMEOUT_TOOLS_CALL} с) или "
                    f"используйте меньший `limit`.")

    if not recs:
        recs.append("✨ Всё хорошо — замечаний нет.")

    for rec in recs:
        W(f"- {rec}")
    W("")

    # Сырые данные
    W("## 8. Сырые данные (JSON)")
    W("")
    W("```json")
    raw = {
        "metadata": {
            "timestamp": now.isoformat(),
            "project_code": project_code,
            "project_id": project_id,
            "mcp_url": MCP_URL,
            "server_info": server_info,
            "total_duration_ms": round(total_duration_ms, 1),
        },
        "summary": {
            "total": len(results),
            "ok": ok_count,
            "error": err_count,
            "exception": exc_count,
            "avg_ms": round(avg_ms, 1),
            "min_ms": round(min_ms, 1),
            "max_ms": round(max_ms, 1),
            "p95_ms": round(p95_ms, 1),
            "total_payload_bytes": total_payload,
            "total_records": total_records,
        },
        "results": [
            {k: v for k, v in r.items() if k != "session_id"}
            for r in results
        ],
    }
    W(json.dumps(raw, ensure_ascii=False, indent=2, default=str))
    W("```")
    W("")

    # Артефакты
    W("## 9. Артефакты")
    W("")
    W(f"- Этот отчёт: `outputs/mcp_test_report_<timestamp>.md`")
    W(f"- JSON-сырые данные (если нужны для дальнейшей обработки):")
    W("")
    W("---")
    W(f"*Сгенерировано `fst-mcp-tester` v1.0.0 — {now.strftime('%Y-%m-%d %H:%M:%S')}*")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Тесты MCP-методов fst-project-health (read-only)")
    ap.add_argument("--quick", action="store_true", help="Без замера payload-размера")
    ap.add_argument("--no-color", action="store_true", help="Без ANSI-цветов")
    ap.add_argument("--output", type=str, default=None, help="Путь к MD-отчёту")
    args = ap.parse_args()

    global USE_COLOR
    if args.no_color:
        USE_COLOR = False

    output_path = Path(args.output) if args.output else (
        OUTPUT_DIR / f"mcp_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(bold(f"\n🔍 fst-mcp-tester v1.0.0"))
    print(f"Проект: {TEST_PROJECT_CODE} (id={TEST_PROJECT_ID})")
    print(f"MCP URL: {MCP_URL}")
    print(f"Отчёт: {output_path}\n")

    # Init сессии
    print("→ initialize MCP ...", end=" ", flush=True)
    t0 = time.perf_counter()
    sid, server_info = mcp_init()
    t1 = time.perf_counter()
    print(green(f"OK ({fmt_ms((t1-t0)*1000)}) — serverInfo: {server_info.get('name')} {server_info.get('version')}\n"))

    # Тесты
    plan = build_test_plan(TEST_PROJECT_ID)
    results = []
    overall_t0 = time.perf_counter()

    for case in plan:
        print(f"→ {case['id']} {case['method']} ...", end=" ", flush=True)
        # initialize — отдельно (он сам создаёт сессию)
        if case["method"] == "initialize":
            r = run_test(case, sid, measure_size=not args.quick)
        else:
            r = run_test(case, sid, measure_size=not args.quick)
        results.append(r)

        if r["status"] == "ok":
            rec = r.get("record_count", 0)
            extra = f", {rec} rows" if rec else ""
            print(green(f"OK {fmt_ms(r['duration_ms'])}{extra}"))
        elif r["status"] == "error":
            print(yellow(f"ERROR {fmt_ms(r['duration_ms'])}: {(r.get('error') or '')[:80]}"))
        else:
            print(red(f"EXCEPTION {fmt_ms(r['duration_ms'])}: {(r.get('error') or '')[:80]}"))

    overall_duration_ms = (time.perf_counter() - overall_t0) * 1000

    # Генерация отчёта
    print(f"\n→ Генерация отчёта ...", end=" ", flush=True)
    report = render_report(results, TEST_PROJECT_CODE, TEST_PROJECT_ID,
                           server_info, overall_duration_ms)
    output_path.write_text(report, encoding="utf-8")
    print(green(f"OK → {output_path}"))

    # Сводка
    ok = sum(1 for r in results if r["status"] == "ok")
    err = sum(1 for r in results if r["status"] != "ok")
    print(f"\n{bold('Итог:')} {green(f'{ok} ok')}, {yellow(f'{err} не ok')} из {len(results)} за {fmt_ms(overall_duration_ms)}")
    print(f"Отчёт: {bold(str(output_path))}\n")

    return 0 if err == 0 else 1


if __name__ == "__main__":
    sys.exit(main())