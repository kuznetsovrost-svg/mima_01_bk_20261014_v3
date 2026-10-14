# КАК Я ОТПРАВЛЯЮ ФАЙЛЫ В TELEGRAM

**Профиль:** `analyst_training` (active)
**Бот (текущая сессия):** `@MMRV_Hermes_bot` (id 8933960684)
**Дата:** 2026-08-01

---

## 1. Где лежит токен

```bash
/root/.hermes/.env
```

Содержит строку:
```
TELEGRAM_BOT_TOKEN=<46 символов, начинается с цифр>
```

Я **никогда не вывожу токен в чат** — только длину и маску.

---

## 2. Где лежит твой chat_id

Из `/root/.hermes/.env`:
```
TELEGRAM_HOME_CHANNEL=505586502
TELEGRAM_ALLOWED_USERS=505586502
```

Это твой личный DM-чат со мной (Rost).

---

## 3. Команда отправки (одной строкой)

```bash
TOK=$(grep '^TELEGRAM_BOT_TOKEN=' /root/.hermes/.env | cut -d= -f2- | tr -d '\n') && \
curl -sS -F document=@"/root/имя-файла.md" \
     -F chat_id=505586502 \
     -F caption="Подпись к файлу" \
     "https://api.telegram.org/bot${TOK}/sendDocument"
```

**Что здесь:**
- `TOK=...` — извлечь токен из `.env` (без кавычек внутри значения)
- `curl -sS` — тихий режим, но показывает ошибки
- `-F document=@/root/файл` — multipart form, файл с диска
- `-F chat_id=505586502` — куда слать
- `-F caption="..."` — подпись (опционально, до 1024 символов)
- `"https://api.telegram.org/bot${TOK}/sendDocument"` — endpoint

---

## 4. Полный пример (как я это делаю в workdir `/root`)

```bash
# 1. Положить файл в /root/ (если ещё не там)
# Используем /tmp + cp из-за инъекций в write_file

# 2. Извлечь токен
TOK=$(grep '^TELEGRAM_BOT_TOKEN=' /root/.hermes/.env | cut -d= -f2- | tr -d '\n')

# 3. Проверить размер файла
ls -la /root/имя-файла.md

# 4. Отправить
curl -sS -F document=@"/root/имя-файла.md" \
     -F chat_id=505586502 \
     -F caption="Что в файле" \
     "https://api.telegram.org/bot${TOK}/sendDocument" \
     -o /tmp/tg_resp.json

# 5. Проверить ответ
python3 -c "import json; d=json.load(open('/tmp/tg_resp.json')); print('OK' if d.get('ok') else 'FAIL'); print(json.dumps({'message_id': d['result']['message_id'], 'file_name': d['result']['document']['file_name'], 'file_size': d['result']['document']['file_size']}, ensure_ascii=False, indent=2))"
```

**Ожидаемый ответ:**
```json
{
  "message_id": 1742,
  "file_name": "имя-файла.md",
  "file_size": 35206
}
```

---

## 5. Кириллица в именах файлов

**Проблема:** `mv` и `cp` с кириллическими именами могут не работать без кавычек.

**Решение:** **всегда в кавычках**:
```bash
cp "/tmp/имя-файла.md" "/root/имя-файла.md"
curl -F document=@"/root/имя-файла.md" ...
```

**Проверка:** Telegram принимает Unicode-имена, отображает в UI как есть.

---

## 6. Что я делаю ДО отправки (безопасность)

1. **Записываю файл через `/tmp/` + `cp`** (не `write_file` напрямую — там инъекции)
2. **Проверяю 0 bad bytes**:
   ```bash
   python3 -c "d=open('/tmp/файл.md','rb').read(); bad=[(i,hex(b)) for i,b in enumerate(d) if b<0x20 and b not in (9,10,13)]; print('Bad bytes:', len(bad))"
   ```
3. **Копирую в `/root/`** для архива
4. **Сверяю SHA256** между `/tmp/` и `/root/`:
   ```bash
   sha256sum /tmp/файл.md /root/файл.md
   ```
5. **Отправляю** через `curl`
6. **Проверяю ответ** — `ok: true`, `message_id` приходит

---

## 7. Альтернативы (если `sendDocument` не сработал)

### A. Отправить как текст (если файл < 4096 символов)
```bash
curl -sS -X POST "https://api.telegram.org/bot${TOK}/sendMessage" \
     -d chat_id=505586502 \
     -d text="$(cat /root/файл.md)"
```

### B. Разбить файл на части
```bash
split -b 50000 /root/файл.md /tmp/chunk_
for f in /tmp/chunk_*; do
    curl -sS -F document=@"$f" -F chat_id=505586502 \
        "https://api.telegram.org/bot${TOK}/sendDocument"
done
```

### C. Закодировать в base64 (для бинарных файлов)
```bash
B64=$(base64 -w0 /root/image.png)
curl -sS -X POST "https://api.telegram.org/bot${TOK}/sendPhoto" \
     -F chat_id=505586502 \
     -F "photo=data:image/png;base64,${B64}"
```

### D. Передать через прокси (если Telegram заблокирован)
```bash
curl --proxy socks5h://127.0.0.1:9050 ...
```

---

## 8. Что НЕ работает

| Ошибка | Причина | Решение |
|---|---|---|
| `{"ok":false,"error_code":400,"description":"Bad Request: chat not found"` | Бот не access к чату | Написать боту `/start` |
| `{"ok":false,"error_code":401,"description":"Unauthorized"` | Токен неверный/протух | Переполучить у @BotFather |
| `{"ok":false,"error_code":403,"description":"Forbidden: bot was blocked by the user"` | Пользователь заблокировал бота | Разблокировать в Telegram |
| `{"ok":false,"error_code":429,"description":"Too Many Requests"}` | Rate limit | Подождать N секунд |
| Файл не приходит (пустой чат) | Файл > 50 MB | Сжать или разбить |
| `curl: (3) URL using bad/illegal format` | Пробелы в имени без кавычек | Кавычки везде |

---

## 9. Лимиты Telegram Bot API

| Параметр | Лимит |
|---|---|
| Размер файла (upload) | 50 MB |
| Caption длина | 1024 символа |
| Число сообщений в секунду | 1 (на чат) |
| Burst (getUpdates) | 30/sec |
| Inline query | 30/sec |
| Webhook updates | Не более 100/sec |

---

## 10. Какой бот используется

Сейчас (2026-08-01) общение идёт через:
- **Bot:** `@MMRV_Hermes_bot` (id 8933960684)
- **Token source:** `/root/.hermes/.env` (default профиля)
- **Telegram chat_id:** 505586502 (ты, Rost)

**`@fst_control_bot`** (id 8934212474) — это **другой бот**, его токен в `/root/.hermes/profiles/fst-control/.env`. Я **НЕ** отправляю через него, потому что:
- Правило: токен берётся с бота, через которого пришёл запрос
- Сейчас пришёл запрос через `@MMRV_Hermes_bot` → значит отвечаю через него

Если нужно отправить что-то через `@fst_control_bot` — это делается **отдельным запросом** через этот бот (написать ему напрямую).

---

## 11. Просмотр отправленных файлов в Telegram

Все отправленные мной файлы попадают:
- **В этот DM-чат** (505586502)
- **С подписью** (caption)
- **С возможностью Save to Files** (на iOS/Android)
- **С возможностью Open in** (Preview)

Файлы лежат на серверах Telegram, **доступны всегда** (пока не удалишь).

---

## 12. Хронология (последние файлы в этой сессии)

| msg_id | Файл | Размер |
|---|---|---|
| 1726 | Obsidian-и-Hermes.md | 35 206 B |
| 1713 | Подсветка-строк-в таблице.md | 16 112 B |
| 1700 | Компонент-с-вариантами.md | 13 026 B |
| 1684 | figma-tokens-full.json | 31 964 B |
| 1674 | figma-tokens.json | 19 257 B |
| 1667 | figma-tokens.json (повтор) | — |
| 1658 | color-map.html | 25 608 B |
| 1648 | Палитра-в-FIGMA.md | 52 357 B |

---

## 13. Шпаргалка

```
TOKEN:     /root/.hermes/.env  →  TELEGRAM_BOT_TOKEN
CHAT_ID:   505586502
CMD:       curl -F document=@/root/файл -F chat_id=505586502 \
                "https://api.telegram.org/bot${TOK}/sendDocument"
БОТ:       @MMRV_Hermes_bot (id 8933960684)
ЛИМИТ:     50 MB
БЕЗОПАС.:  /tmp write + cp /root + 0 bad bytes + SHA256
```

---

## 14. Что делать если я не могу отправить

1. **Проверить токен** — вывести длину, не сам токен
2. **Проверить chat_id** — посмотреть `TELEGRAM_HOME_CHANNEL`
3. **Проверить файл** — `ls -la /root/файл`, `file /root/файл`
4. **Проверить путь** — абсолютный, начинается с `/root/`
5. **Проверить кавычки** — кириллица в кавычках
6. **Проверить ответ curl** — `cat /tmp/tg_resp.json`
7. Если `error_code: 429` — подождать
8. Если `error_code: 4xx` — чинить ошибку в запросе
9. Если `error_code: 5xx` — Telegram лежит, подождать

---

## 15. Итог одной фразой

> Я извлекаю токен из `/root/.hermes/.env`, отправляю файл из `/root/` через `curl -F document=@... `на `api.telegram.org/bot${TOK}/sendDocument` с `chat_id=505586502`. Кириллица в кавычках. Перед отправкой — `/tmp` + проверка + SHA256.
