#!/usr/bin/env bash
# probe_mcp_sse.sh
# Прямой probe любого MCP сервера через SSE/HTTP, минуя Hermes-обёртку.
#
# Зачем: когда mcp__<server>__* tools падают с непонятной ошибкой, или
# документация в tools/list противоречит тому, что сервер реально принимает.
#
# Использование:
#   probe_mcp_sse.sh <URL> <TOKEN_ENV_VAR> [TOOL_NAME] [TOOL_ARGS_JSON]
#
# Примеры:
#   probe_mcp_sse.sh https://ppreplica.hera.pmpractice.ru/mcp PMP_TOKEN
#   probe_mcp_sse.sh https://ppreplica.hera.pmpractice.ru/mcp PMP_TOKEN list_entities
#   probe_mcp_sse.sh https://example.com/mcp API_TOKEN get_user_profile '{}'
#
# Требует: curl, jq (опционально, для красивого вывода).

set -euo pipefail

URL="${1:?Usage: $0 <URL> <TOKEN_ENV_VAR> [TOOL_NAME] [TOOL_ARGS_JSON]}"
TOKEN_VAR="${2:?Missing token env var name}"
TOOL_NAME="${3:-}"
TOOL_ARGS="${4:-{}}"

# Получаем токен из env или файла
TOKEN="${!TOKEN_VAR:-}"
if [[ -z "$TOKEN" ]]; then
  # Попробуем прочитать из .env профиля fst-control
  if [[ -f "$HOME/.hermes/profiles/fst-control/.env" ]]; then
    TOKEN=$(grep "^${TOKEN_VAR}=" "$HOME/.hermes/profiles/fst-control/.env" | cut -d= -f2-)
  fi
fi
if [[ -z "$TOKEN" || "$TOKEN" == "PASTE_YOUR_TOKEN_HERE" ]]; then
  echo "✗ Токен $TOKEN_VAR не задан или равен плейсхолдеру." >&2
  echo "  Задай: export $TOKEN_VAR=... или положи в ~/.hermes/profiles/fst-control/.env" >&2
  exit 1
fi

OUT_DIR="${OUT_DIR:-/tmp/mcp_probe_$(date +%Y%m%d_%H%M%S)}"
mkdir -p "$OUT_DIR"
echo "→ Output dir: $OUT_DIR"

# 1) Initialize + extract session id from response headers
echo "→ initialize..."
INIT=$(curl -sS -i -m 30 -N \
  -H "Accept: application/json, text/event-stream" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -X POST "$URL" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize",
       "params":{"protocolVersion":"2024-11-05",
                 "capabilities":{},
                 "clientInfo":{"name":"probe","version":"1.0"}}}')

echo "$INIT" > "$OUT_DIR/01_init.txt"

SID=$(echo "$INIT" | tr -d '\r' | awk '/^[Mm]cp-[Ss]ession-[Ii][Dd]:/ {print $2}')
if [[ -z "$SID" ]]; then
  echo "✗ Не удалось получить session id. Сервер ответил:" >&2
  head -20 "$OUT_DIR/01_init.txt" >&2
  exit 1
fi
echo "✓ session: $SID"

# 2) notifications/initialized (обязательно перед tools/list)
echo "→ notifications/initialized..."
curl -sS -m 30 -N \
  -H "Accept: application/json, text/event-stream" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "mcp-session-id: $SID" \
  -X POST "$URL" \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  > "$OUT_DIR/02_initialized.txt"

# 3) tools/list — реальные схемы всех tools
echo "→ tools/list..."
curl -sS -m 60 -N \
  -H "Accept: application/json, text/event-stream" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "mcp-session-id: $SID" \
  -X POST "$URL" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  > "$OUT_DIR/03_tools_list.txt"

TOOLS_DATA=$(grep '^data: ' "$OUT_DIR/03_tools_list.txt" | sed 's/^data: //')
echo "$TOOLS_DATA" > "$OUT_DIR/03_tools_list.json"

# Краткое summary tools
if command -v jq >/dev/null 2>&1; then
  echo ""
  echo "=== Tools обнаружено ==="
  echo "$TOOLS_DATA" | jq -r '.result.tools[]? | "  - \(.name): \(.description | split("\n")[0] | .[0:80])"' 2>/dev/null || \
    echo "  (jq не смог распарсить, см. $OUT_DIR/03_tools_list.json)"
else
  echo ""
  echo "=== Tools (raw, установи jq для красивого вывода) ==="
  echo "$TOOLS_DATA" | grep -oE '"name":"[^"]+"' | head -30
fi

# 4) tools/call (если передан TOOL_NAME)
if [[ -n "$TOOL_NAME" ]]; then
  echo ""
  echo "→ tools/call: $TOOL_NAME"
  curl -sS -m 60 -N \
    -H "Accept: application/json, text/event-stream" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -H "mcp-session-id: $SID" \
    -X POST "$URL" \
    -d "{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/call\",
         \"params\":{\"name\":\"$TOOL_NAME\",\"arguments\":$TOOL_ARGS}}" \
    > "$OUT_DIR/04_tool_call.txt"

  # Извлечь содержимое и pretty-print если есть jq
  CONTENT=$(grep '^data: ' "$OUT_DIR/04_tool_call.txt" | sed 's/^data: //')
  if command -v jq >/dev/null 2>&1 && [[ -n "$CONTENT" ]]; then
    echo "$CONTENT" | jq . > "$OUT_DIR/04_tool_call.json" 2>/dev/null || echo "$CONTENT" > "$OUT_DIR/04_tool_call.json"
    # Если это ошибка — выведем красиво
    if echo "$CONTENT" | jq -e '.result.isError == true' >/dev/null 2>&1; then
      echo ""
      echo "=== Tool вернул ОШИБКУ ==="
      echo "$CONTENT" | jq -r '.result.content[0].text // .error.message // .'
    else
      echo ""
      echo "=== Tool ответ (success) ==="
      echo "$CONTENT" | jq -r '.result.content[0].text // .' | head -c 500
      echo "..."
    fi
  else
    echo "  Сырой ответ в $OUT_DIR/04_tool_call.txt"
  fi
fi

echo ""
echo "============================================================="
echo "Готово. Все ответы в: $OUT_DIR"
echo "  01_init.txt            — initialize + headers"
echo "  02_initialized.txt     — notifications/initialized"
echo "  03_tools_list.json     — реальные схемы всех tools"
echo "  04_tool_call.json      — ответ tools/call (если был вызван)"
echo ""
echo "Подсказки:"
echo "  - Если ошибка Pydantic: ищи 'Missing required' и 'Unexpected keyword'"
echo "    в $OUT_DIR/04_tool_call.txt — там реальные имена параметров"
echo "  - Если 406 Not Acceptable: добавь 'Accept: application/json, text/event-stream'"
echo "  - Если 'Missing session ID': сначала выполни initialize в этой же сессии"
echo "============================================================="
