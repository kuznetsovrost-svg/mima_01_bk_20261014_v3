__version__ = "1.0.19"
#!/usr/bin/env python3
"""
fetch_snapshot.py — достаёт JSON-слепок из карточки проекта в PMForesight.

Назначение:
- По `project_code` или `project_id` находит в категории "Документы ИИ"
  (DocumentId=70139) JSON-файлы, загруженные скиллом `fst-project-health-snapshot`.
- Фильтрует по `_meta.generator == "fst-project-health-snapshot"`
  (отбрасывает посторонние JSON, которые могут оказаться на вкладке).
- Возвращает список доступных снапшотов (timestamp + file_id + размер),
  и скачивает выбранный в локальный файл.

Использование:
    python3 fetch_snapshot.py --code 504-595           # показать список снапшотов
    python3 fetch_snapshot.py --code 504-595 --timestamp "2026-09-21_18-14-36"  # скачать конкретный
    python3 fetch_snapshot.py --project-id 4595 --timestamp "2026-09-21_18-14-36"
    python3 fetch_snapshot.py --code 504-595 --output my_snapshot.json
"""

import argparse
import base64
import json
import os
import re
import sys
from pathlib import Path

# MCP-параметры.
MCP_URL = os.environ.get("MCP_URL", "https://ppreplica.hera.pmpractice.ru/mcp")
DOCUMENT_ID_AI = 70139
ENTITY_NAME = "Project"
SNAPSHOT_GENERATOR = "fst-project-health-snapshot"  # для машинного отбора

# ENV-файлы.
ENV_FILE_CANDIDATES = [
    Path(__file__).resolve().parent.parent / ".env",
    Path.home() / ".hermes/profiles/fst-control/.env",
]

TIMEOUT_INITIALIZE = 30
TIMEOUT_TOOLS_CALL = 60


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
                return json.loads(line[6:])
            except json.JSONDecodeError as e:
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
            "clientInfo": {"name": "fst-project-health-from-json", "version": "1.0.0"},
        },
    }
    resp = requests.post(MCP_URL, json=payload, headers=headers, timeout=TIMEOUT_INITIALIZE)
    resp.raise_for_status()
    sid = resp.headers.get("mcp-session-id")
    if not sid:
        raise RuntimeError(f"сервер не вернул mcp-session-id. headers={dict(resp.headers)}")
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
    except json.JSONDecodeError:
        return {"_raw_text": text[:500]}


def find_project_id(sid: str, code: str) -> int | None:
    """Поиск project_id по коду."""
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


def list_snapshot_files(sid: str, project_id: int) -> list[dict]:
    """Возвращает список файлов в категории 'Документы ИИ' проекта."""
    result = mcp_call(sid, "list_files", {
        "className": ENTITY_NAME,
        "dataId": project_id,
        "documentId": DOCUMENT_ID_AI,
    })
    if not isinstance(result, list):
        return []
    return result


def download_file(sid: str, physical_file_id: str) -> bytes | None:
    """Скачивает файл через read_resource (file://download-file/{id})."""
    import requests
    token = _load_token()
    # Сначала получаем инфо о файле (URL).
    info = mcp_call(sid, "get_file_info", {"physicalFileId": physical_file_id})
    url_path = info.get("url", "") if isinstance(info, dict) else ""
    if not url_path:
        return None
    # Полный URL — относительный к MCP_URL.
    if url_path.startswith("/"):
        full_url = MCP_URL.rsplit("/", 1)[0] + url_path
    elif url_path.startswith("http"):
        full_url = url_path
    else:
        full_url = MCP_URL.rsplit("/", 1)[0] + "/" + url_path
    headers = {
        "Authorization": f"Bearer {token}",
    }
    resp = requests.get(full_url, headers=headers, timeout=60)
    resp.raise_for_status()
    return resp.content


# ---------------------------------------------------------------------------
# Фильтрация: только наши снапшоты
# ---------------------------------------------------------------------------

_TIMESTAMP_RE = re.compile(r"(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})")


def extract_timestamp_from_name(name: str) -> str | None:
    """Извлекает timestamp из имени файла.

    Формат имени: `Слепок fst-project-health-snapshot-<code>-YYYY-MM-DD_HH-MM-SS.JSON`
    """
    m = _TIMESTAMP_RE.search(name)
    return m.group(1) if m else None


def is_our_snapshot(name: str) -> bool:
    """Файл относится к нашим снапштам?
    Проверяем имя (префикс) — самый надёжный признак.
    """
    return name.startswith("Слепок fst-project-health-snapshot-")


def is_our_snapshot_by_meta(content_bytes: bytes) -> bool:
    """Дополнительная проверка по содержимому (_meta.generator)."""
    try:
        obj = json.loads(content_bytes)
        return obj.get("_meta", {}).get("generator") == SNAPSHOT_GENERATOR
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Главное
# ---------------------------------------------------------------------------

def fmt_ms(ms) -> str:
    if ms is None:
        return "—"
    if ms >= 1000:
        return f"{ms/1000:.2f} s"
    return f"{ms:.0f} ms"


def green(t): return f"\033[32m{t}\033[0m"
def yellow(t): return f"\033[33m{t}\033[0m"
def red(t): return f"\033[31m{t}\033[0m"
def bold(t): return f"\033[1m{t}\033[0m"


def main():
    ap = argparse.ArgumentParser(description="Скачать JSON-слепок из карточки проекта в PMForesight")
    ap.add_argument("--code", type=str, default=None, help="Код проекта (504-595)")
    ap.add_argument("--project-id", type=int, default=None, help="Числовой ID проекта")
    ap.add_argument("--timestamp", type=str, default=None,
                    help="Таймстамп снапшота (например, 2026-09-21_18-14-36). "
                         "Если не указан — выводится список доступных.")
    ap.add_argument("--output", type=str, default=None,
                    help="Путь к локальному файлу. По умолчанию: <code>_<timestamp>.json")
    ap.add_argument("--include-meta-check", action="store_true",
                    help="Дополнительно проверить _meta.generator внутри каждого файла "
                         "(медленнее, но надёжнее).")
    args = ap.parse_args()

    # 1. Получаем project_id
    if not args.code and not args.project_id:
        print(red("✗ Укажите --code или --project-id"))
        sys.exit(1)

    import time
    overall_t0 = time.perf_counter()
    print(bold(f"\n🔍 fst-project-health-from-json v1.0.0 — fetch_snapshot"))

    print("→ initialize MCP... ", end="", flush=True)
    t0 = time.perf_counter()
    sid, server_info = mcp_init()
    print(green(f"OK ({fmt_ms((time.perf_counter()-t0)*1000)}) — {server_info.get('name')} {server_info.get('version')}"))

    project_id = args.project_id
    if project_id is None:
        print(f"→ поиск project_id по коду '{args.code}'... ", end="", flush=True)
        t0 = time.perf_counter()
        project_id = find_project_id(sid, args.code)
        if project_id is None:
            print(red(f"не найден"))
            sys.exit(1)
        print(green(f"OK ({fmt_ms((time.perf_counter()-t0)*1000)}) — project_id={project_id}"))

    # 2. Список файлов
    print(f"→ список файлов в 'Документы ИИ' проекта {project_id}... ", end="", flush=True)
    t0 = time.perf_counter()
    files = list_snapshot_files(sid, project_id)
    print(green(f"OK ({fmt_ms((time.perf_counter()-t0)*1000)}) — {len(files)} файлов"))

    # 3. Фильтрация: только наши снапшоты
    snapshots = []
    for f in files:
        name = f.get("name", "")
        if not is_our_snapshot(name):
            continue
        ts = extract_timestamp_from_name(name)
        if ts is None:
            continue
        snapshots.append({
            "physical_file_id": f.get("physicalFileId", ""),
            "name": name,
            "timestamp": ts,
            "file_size": f.get("fileSize", 0),
            "url": f.get("url", ""),
        })

    # Опциональная проверка по _meta
    if args.include_meta_check:
        print(f"→ дополнительная проверка _meta.generator ({len(snapshots)} файлов)...", flush=True)
        verified = []
        for s in snapshots:
            content = download_file(sid, s["physical_file_id"])
            if content and is_our_snapshot_by_meta(content):
                s["_meta_verified"] = True
                verified.append(s)
            else:
                s["_meta_verified"] = False
        snapshots = verified
        print(f"   подтверждено по _meta: {len(snapshots)}")

    # Сортировка по timestamp (новые сверху)
    snapshots.sort(key=lambda s: s["timestamp"], reverse=True)

    if not snapshots:
        print(red(f"\n✗ Снапшотов fst-project-health-snapshot не найдено для проекта {project_id}."))
        print(yellow(f"  Возможно, fst-project-health-snapshot ещё не запускался для этого проекта."))
        sys.exit(1)

    if not args.timestamp:
        # Только список — без скачивания
        print(f"\n{bold(f'Найдено снапшотов: {len(snapshots)}')} (отсортированы: новые сверху)\n")
        print(f"  {'#':<4}{'TIMESTAMP':<25}{'SIZE':<10}{'NAME'}")
        print(f"  {'-'*4} {'-'*24} {'-'*9} {'-'*60}")
        for i, s in enumerate(snapshots, 1):
            print(f"  {i:<4}{s['timestamp']:<25}{s['file_size']:<10}{s['name']}")
        print(f"\n💡 Чтобы скачать конкретный снапшот, используйте:")
        print(f"   python3 fetch_snapshot.py --code {args.code or project_id} --timestamp <TIMESTAMP>")
        return

    # 4. Скачивание выбранного
    target = next((s for s in snapshots if s["timestamp"] == args.timestamp), None)
    if target is None:
        print(red(f"\n✗ Снапшот с timestamp='{args.timestamp}' не найден."))
        print(f"Доступные:")
        for s in snapshots:
            print(f"  - {s['timestamp']}")
        sys.exit(1)

    print(f"\n→ скачивание '{target['name']}'... ", end="", flush=True)
    t0 = time.perf_counter()
    content = download_file(sid, target["physical_file_id"])
    if content is None:
        print(red(f"FAIL — пустой ответ"))
        sys.exit(1)
    print(green(f"OK ({fmt_ms((time.perf_counter()-t0)*1000)}) — {len(content)} байт"))

    # 5. Сохранение
    if args.output:
        out_path = Path(args.output)
    else:
        out_path = Path(f"{(args.code or str(project_id))}_{target['timestamp']}.json")
    out_path.write_bytes(content)
    print(green(f"\n✅ Сохранено: {out_path} ({out_path.stat().st_size} байт)"))

    # 6. Доп. проверка _meta
    if not args.include_meta_check:
        try:
            obj = json.loads(content)
            gen = obj.get("_meta", {}).get("generator", "?")
            kind = obj.get("_meta", {}).get("snapshot_kind", "?")
            print(f"   _meta.generator: {gen}")
            print(f"   _meta.snapshot_kind: {kind}")
            if gen != SNAPSHOT_GENERATOR:
                print(yellow(f"   ⚠️ _meta.generator не совпадает с ожидаемым '{SNAPSHOT_GENERATOR}'."))
        except Exception:
            print(yellow(f"   ⚠️ Не удалось разпарсить JSON для проверки _meta."))

    overall_ms = (time.perf_counter() - overall_t0) * 1000
    print(f"\nИтого: {fmt_ms(overall_ms)}")


if __name__ == "__main__":
    main()