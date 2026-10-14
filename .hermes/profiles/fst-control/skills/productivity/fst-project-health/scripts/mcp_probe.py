__version__ = "1.0.19"
"""mcp_probe.py — утилита для прямых вызовов tools MCP сервера fst_pmpractice.

Избавляет от копи-пасты curl-команд с SSE-стримом. Работает через JSON-RPC 2.0
напрямую на MCP-эндпоинт, минуя Hermes-обёртку.

Тонкости реализации (выжжены граблями):
- Сервер требует именно `Accept: application/json, text/event-stream`
  (без этого вернёт 406 "Not Acceptable")
- session_id берётся из заголовка `mcp-session-id` ответа initialize
- После initialize ОБЯЗАТЕЛЬНО отправить `notifications/initialized`,
  иначе tools/call упадёт
- JSON-RPC ответ упакован в SSE: строки вида `data: {...}`
- Внутри `result.content[0].text` — JSON в виде строки (двойное кодирование),
  парсить надо ОДНИМ уровнем json.loads(), не двумя

⚠️ Разные сущности используют разные naming conventions для полей:
- Большинство: CamelCase (`PlanDate`, `planningHours`...)
- ResourcePlanning, ResourcePlanningKp: snake_case (`planning_date`,
  `planning_hours`, `participation`, `manual`)

Использование:

    # Список всех tools
    ./mcp_probe.py --tools

    # Конкретный вызов tool
    ./mcp_probe.py --tool get_user_profile

    # С аргументами
    ./mcp_probe.py --tool describe_entity --args '{"entityName":"Point","data_id":"1686"}'

    # Для ResourcePlanningKp — ИСПОЛЬЗУЙ snake_case!
    ./mcp_probe.py --tool save_entity --args '{
        "entityName": "ResourcePlanningKp",
        "id": "new",
        "data": {
            "PointId": 4721, "AccountId": 120872,
            "planning_date": "15.07.2026", "planning_hours": 20.0,
            "participation": 100, "manual": true
        }
    }'

    # JSON-RPC метод напрямую (например, initialize, tools/list)
    ./mcp_probe.py --method tools/list

Опции:
    --url URL      MCP endpoint (по умолчанию https://ppreplica.hera.pmpractice.ru/mcp)
    --token TOKEN  Bearer token (по умолчанию из $PMP_TOKEN в ~/.hermes/.../fst-control/.env)
    --method M     JSON-RPC method (по умолчанию tools/call)
    --tool NAME    Имя tool (сокращение для method=tools/call, name=NAME)
    --args JSON    JSON-строка с аргументами
    --id N         JSON-RPC id (по умолчанию 1)
    --raw          Вывести сырой ответ (без парсинга SSE/data:)
    --pretty       Pretty-print JSON-результата
"""

import argparse
import json
import sys
import urllib.request

# Централизованная конфигурация из mcp_config.
from mcp_config import MCP_URL as DEFAULT_URL, ENV_FILE, load_token_from_env_file


def load_token() -> str | None:
    """Читает PMP_TOKEN из .env профиля fst-control.

    Делегирует в mcp_config.load_token_from_env_file().
    Оставлено для обратной совместимости с CLI --token.
    """
    return load_token_from_env_file(ENV_FILE)


def post_jsonrpc(url: str, token: str, payload: dict, session_id: str | None = None) -> dict:
    """Отправляет JSON-RPC запрос, возвращает dict с status/headers/body/session_id."""
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {token}",
        },
    )
    if session_id:
        req.add_header("mcp-session-id", session_id)

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return {
                "status": resp.status,
                "headers": dict(resp.headers),
                "body": raw,
                "session_id": resp.headers.get("mcp-session-id"),
            }
    except urllib.error.HTTPError as e:
        return {
            "status": e.code,
            "headers": dict(e.headers),
            "body": e.read().decode("utf-8", errors="replace"),
            "session_id": e.headers.get("mcp-session-id"),
        }


def parse_sse(raw: str) -> str:
    """Извлекает JSON из SSE-стрима (отбрасывает префиксы event:/data:/etc.)."""
    for line in raw.splitlines():
        if line.startswith("data: "):
            return line[6:].strip()
    # Если это не SSE — вернуть как есть
    return raw.strip()


def main() -> int:
    ap = argparse.ArgumentParser(description="MCP probe для fst_pmpractice")
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--token")
    ap.add_argument("--method", default=None, help="JSON-RPC method: tools/list, tools/call, и т.п.")
    ap.add_argument("--tool", help="Короткое имя для method=tools/call")
    ap.add_argument("--args", default="{}", help="JSON-строка с аргументами")
    ap.add_argument("--id", type=int, default=1, help="JSON-RPC id")
    ap.add_argument("--tools", action="store_true", help="Эквивалент --method tools/list")
    ap.add_argument("--raw", action="store_true")
    ap.add_argument("--pretty", action="store_true")
    args = ap.parse_args()

    token = args.token or load_token()
    if not token:
        print("PMP_TOKEN не найден. Установи через env или укажи --token", file=sys.stderr)
        return 2

    # Определить JSON-RPC method и params
    if args.tools:
        method = "tools/list"
        params = {}
    elif args.tool:
        method = "tools/call"
        try:
            arguments = json.loads(args.args)
        except json.JSONDecodeError as e:
            print(f"--args не валидный JSON: {e}", file=sys.stderr)
            return 2
        params = {"name": args.tool, "arguments": arguments}
    elif args.method:
        method = args.method
        try:
            params = json.loads(args.args)
        except json.JSONDecodeError:
            params = {}
    else:
        ap.print_help()
        return 1

    payload = {
        "jsonrpc": "2.0",
        "id": args.id,
        "method": method,
        "params": params,
    }

    # Step 1: initialize, get session id
    init_payload = {
        "jsonrpc": "2.0", "id": 0, "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "mcp_probe", "version": "1.0"},
        },
    }
    init_resp = post_jsonrpc(args.url, token, init_payload)
    session_id = init_resp.get("session_id")
    if not session_id:
        print(f"Не удалось получить session id (status={init_resp['status']}):\n{init_resp['body'][:500]}", file=sys.stderr)
        return 3

    # Step 2: notifications/initialized (ОБЯЗАТЕЛЬНО после initialize)
    notif = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    post_jsonrpc(args.url, token, notif, session_id=session_id)

    # Step 3: основной вызов
    result = post_jsonrpc(args.url, token, payload, session_id=session_id)

    if args.raw:
        print(f"HTTP {result['status']}")
        print(result["body"])
        return 0 if result["status"] == 200 else 1

    body = result["body"]
    if result["status"] != 200:
        print(f"HTTP {result['status']}", file=sys.stderr)
        print(body, file=sys.stderr)
        return 1

    # Извлечь JSON из SSE
    data = parse_sse(body)
    try:
        parsed = json.loads(data)
        print(json.dumps(parsed, ensure_ascii=False, indent=2, default=str))
        return 0
    except json.JSONDecodeError:
        # Не JSON — вернуть как есть
        print(data)
        return 0


if __name__ == "__main__":
    sys.exit(main())
