# Извлечение ФИО пользователя из JWT-токена PMForesight

## Зачем

В разделе 7 «Технические данные отчёта» нужно показать ФИО **пользователя, от имени которого строится отчёт**, а не:
- ❌ Владелец проекта (`project["OwnerId"]`)
- ❌ Хардкод (`"Кузнецов Ростислав Владимирович"`)
- ❌ Auth.json fallback (там нет данных)
- ❌ `mcp_init() serverInfo` (это инфо о сервере, не о пользователе)

## Правильный путь — JWT

PMForesight MCP использует токен `PMP_TOKEN`, который является **JWT** в формате `header.payload.signature`. Из payload можно достать ФИО.

### Пример payload (PMForesight)

```json
{
  "UserId": 120872,
  "displayname": "Кузнецов Ростислав Владимирович",
  "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/sid": "120872",
  "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name": "tekora-c\\rkuznetsov",
  "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier": "tekora-c\\rkuznetsov",
  "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname": "Кузнецов Ростислав Владимирович",
  "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress": "rkuznetsov@pmpractice.ru",
  "http://schemas.microsoft.com/ws/2008/06/identity/claims/role": "auth",
  "nbf": 1784550446,
  "exp": 1803416400,
  "iss": "PMPractice.Foresight",
  "aud": "*"
}
```

### Реализация (в `scripts/mcp_config.py`)

```python
def get_current_user_from_token(token: Optional[str] = None) -> str:
    """Достаёт displayname пользователя из JWT-токена (PMP_TOKEN).

    Токен — JWT в формате header.payload.signature. Извлекаем payload,
    декодируем base64url → dict, ищем displayname или givenname.

    Returns:
        str — displayname (ФИО) пользователя.
        Если токен не JWT или не содержит нужных полей — "—".
    """
    import base64
    import json as _json

    if token is None:
        try:
            token = require_token()
        except RuntimeError:
            return "—"

    try:
        parts = token.split(".")
        if len(parts) < 2:
            return "—"
        payload_b64 = parts[1]
        # base64url без padding
        padding = "=" * (-len(payload_b64) % 4)
        payload_json = base64.urlsafe_b64decode(payload_b64 + padding)
        payload = _json.loads(payload_json)
        # Приоритет: displayname > givenname (claim name)
        name = payload.get("displayname") or payload.get(
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname"
        ) or "—"
        return name
    except Exception:
        return "—"
```

### Использование (в `scripts/run_all.py::build_section_7`)

```python
from mcp_config import get_current_user_from_token

# 1. Пользователь — из JWT-токена (пользователь, от имени которого
# строится отчёт, а НЕ владелец проекта).
user = get_current_user_from_token()
```

## Отладка

### Быстрая проверка в shell

```bash
PMP_TOKEN=$(grep "^PMP_TOKEN=" ~/.hermes/profiles/fst-control/.env | sed 's/PMP_TOKEN=//')
echo "${PMP_TOKEN}" | python3 -c "
import sys, base64, json
t = sys.stdin.read().strip().split('.')[1]
t += '=' * (-len(t) % 4)
payload = json.loads(base64.urlsafe_b64decode(t))
print('displayname:', payload.get('displayname'))
print('email:', payload.get('http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress'))
"
```

### Что делать, если токен не JWT

В будущем токен может перестать быть JWT (например, переход на opaque token). Тогда fallback-цепочка:
1. JWT-парсинг (текущий)
2. MCP-вызов `whoami` / `get_current_user` (если такой метод появится)
3. Auth.json / env var
4. `"—"` (пусто)

## Pitfall #213

См. также Pitfall #211 (откуда взялся этот фикс). Pitfall #205 («исправляй генератор, не HTML») тоже важен — JWT-парсинг живёт в `mcp_config.py`, а не где-то ещё.

## Связанные файлы

- `scripts/mcp_config.py::get_current_user_from_token()` — реализация
- `scripts/run_all.py::build_section_7()` — использование
- `references/section-7-tech-data-canonical.md` — формат секции 7 в целом
