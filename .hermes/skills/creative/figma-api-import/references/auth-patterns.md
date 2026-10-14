---
name: figma-api-import
description: Как получить Personal Access Token для Figma API
version: 0.1.0
---

# Как получить FIGMA_PERSONAL_ACCESS_TOKEN

## Шаг 1: Открой настройки токенов

Перейди на https://www.figma.com/developers/api#access-tokens

Или через UI:
1. Открой https://www.figma.com
2. Кликни на аватар → **Settings**
3. Вкладка **Security**
4. Раздел **Personal access tokens**

## Шаг 2: Создай токен

1. Нажми **Generate new token**
2. Введи имя (например, `hermes-figma-import`)
3. Выбери **Scopes**:
   - ✅ `File read` — для чтения файлов
   - ✅ `File write` — если нужно менять файлы
   - ✅ `Variables` — для доступа к variables
4. Нажми **Generate token**

## Шаг 3: Скопируй токен

⚠️ **Токен показывается один раз.** Сохрани его сразу.

Формат: `figd_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

## Шаг 4: Положи в `.env`

```bash
nano /root/.hermes/.env
```

Добавь в конец:
```
FIGMA_PERSONAL_ACCESS_TOKEN=figd_xxxxx
```

Сохрани: Ctrl+O, Enter, Ctrl+X

## Шаг 5: Проверь

```bash
python3 /root/.hermes/skills/creative/figma-api-import/scripts/figma_client.py
```

Должен вернуть JSON с твоим профилем.

## Альтернатива: через UI профиля Figma

1. Открой https://www.figma.com
2. Аватар → Account settings
3. Security
4. Personal access tokens → Generate

## Альтернатива: OAuth 2.0 (для приложений)

Если создаёшь приложение для других пользователей:
https://www.figma.com/developers/api#oauth2

Скилл `figma-api-import` использует Personal Access Token, не OAuth.

## Типичные ошибки

| Ошибка | Решение |
|---|---|
| 401 Unauthorized | Токен неверный или отозван |
| 403 Forbidden | Token scope не хватает |
| 404 Not Found | file_key или node_id неправильный |
| 429 Too Many Requests | Превышен rate limit (60/мин) |
| Empty response | Файл не расшарен с токеном |

## Безопасность

- ❌ НЕ коммить `FIGMA_PERSONAL_ACCESS_TOKEN` в git
- ✅ Храни в `.env` с `chmod 600`
- ✅ Используй `.env.example` для примера без токена
- ✅ Ротация: раз в 90 дней
