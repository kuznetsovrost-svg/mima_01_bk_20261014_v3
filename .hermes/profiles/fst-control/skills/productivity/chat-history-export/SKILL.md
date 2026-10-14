---
name: chat-history-export
description: "Use when the user asks to export, dump, archive, or audit their own chat history / requests / messages in a Hermes profile — 'собери мои обращения через бот', 'покажи всё что я писал', 'export my messages', 'audit my requests', 'дамп переписки', 'мои запросы за всё время'. Bypasses session_search truncation by querying the profile's SQLite state.db directly. Loads when the conversation is about extracting historical user messages or generating a chronological markdown of past requests, especially when session_search returns truncated first/last-20 messages."
version: 1.0.0
author: Hermes Agent + Rost
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, sqlite, session, export, history, audit, mcp, ru]
    related_skills: [hermes-agent, hermes-agent-skill-authoring]
---

# Chat History Export (chat-history-export)

## Overview

Экспорт **собственных user-сообщений** из профиля Hermes в markdown-файл.
Нужен, когда `session_search` обрезает выдачу (большие сессии → только
первые 20 + последние 10 сообщений) и нужно собрать **все** обращения
за период.

Источник — SQLite `state.db` профиля. Делает прямой SQL-запрос к
`messages` × `sessions`, фильтрует `role='user'`, чистит от
внутренних блоков (`[OUT-OF-BAND USER MESSAGE ...]`, ` `, `[PRIOR CONTEXT ...]`)
и собирает хронологический markdown.

Загружай, когда пользователь говорит:

- «Собери мои обращения через бот с начала работы»
- «Покажи все мои запросы за июль»
- «Дамп переписки по проекту X»
- «Export my chat history»
- «Что я писал тебе в прошлом месяце»
- «Audit my requests / Запросы для аудита»

**Не загружай** для одной конкретной сессии — там хватит `session_search`.

## Где живут данные

Hermes хранит сессии и сообщения в SQLite per-profile:

```
<profile_root>/state.db
```

Например, для текущего профиля (`fst-control`):

```
/root/.hermes/profiles/fst-control/state.db
```

⚠️ **Путь зависит от активного профиля.** Если профиль другой — поправь
`PROFILE_DB` в коде или передай явно.

## Схема таблиц (минимальная)

```sql
-- sessions
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,        -- e.g. "20260720_163608_dd0f5d6d"
    source TEXT NOT NULL,       -- 'telegram' | 'cli' | 'matrix' | ...
    started_at REAL NOT NULL,
    ended_at REAL,
    title TEXT,
    message_count INTEGER DEFAULT 0,
    -- ... много других полей (модель, токены, ветка и т.д.)
);

-- messages
CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,         -- 'user' | 'assistant' | 'tool'
    content TEXT,
    timestamp REAL NOT NULL,
    active INTEGER DEFAULT 1,   -- 1 = живое, 0 = удалённое
    compacted INTEGER DEFAULT 0 -- 1 = было схлопнуто в summary
);
```

## ⚠️ Critical: `compacted=1` — это потеря данных

Каждый раз, когда Hermes жмёт контекст через compaction, **несколько
старых user-сообщений** заменяются одной строкой с `compacted=1`. Внутри
этой строки — **свободный текст summary**, не оригинальные сообщения.

Это значит:

| `active=1, compacted=0` | развёрнутое user-обращение, видно целиком |
| `active=1, compacted=1` | спрессованный блок из 1+ обращений, **нельзя разделить** |

Один compacted-блок может покрывать 5–30 обращений. Включай их в отчёт
как **превью** (text-block с усечением до 3 000 символов), но **не
притворяйся, что это отдельные сообщения** — будет ложь пользователю.

## Алгоритм

```python
import sqlite3, re
from datetime import datetime, timezone
from collections import defaultdict

PROFILE_DB = "/root/.hermes/profiles/fst-control/state.db"
SOURCE_FILTER = "telegram"  # 'cli' | 'matrix' | всё ('')

OOB_RE = re.compile(r"\[OUT-OF-BAND USER MESSAGE.*?\[/OUT-OF-BAND USER MESSAGE\]", re.DOTALL)
THINK_RE = re.compile(r"^.*?^.*?$", re.DOTALL)   # если есть — по контексту
PRIOR_RE = re.compile(r"\[PRIOR CONTEXT.*?not a new message\]", re.DOTALL)

def clean(t):
    if not t:
        return None
    if PRIOR_RE.search(t):
        return None  # инструментальный мусор, не пользователь
    t = OOB_RE.sub("", t)
    t = re.sub(r"^.*?^.*?$", "", t, flags=re.DOTALL)  # опц.
    return t.strip() or None

def fmt_ts(t):
    return datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

# 1. Подключение
con = sqlite3.connect(PROFILE_DB)
con.row_factory = sqlite3.Row

# 2. Все user-сообщения (активные + компактнутые)
sql = """
SELECT m.id, m.session_id, m.content, m.timestamp, m.active, m.compacted
FROM messages m
JOIN sessions s ON s.id = m.session_id
WHERE m.role = 'user'
  AND s.source = COALESCE(NULLIF(?, ''), s.source)
ORDER BY s.started_at, m.timestamp
"""
params = (SOURCE_FILTER,) if SOURCE_FILTER else ("",)
rows = con.execute(sql, params).fetchall()

# 3. Группировка по сессии
by_sid = defaultdict(lambda: {"active": [], "compacted": []})
for r in rows:
    by_sid[r["session_id"]]["compacted" if r["compacted"] else "active"].append(dict(r))

# 4. Сессии (для заголовка)
sessions = {r["id"]: dict(r)
            for r in con.execute("SELECT * FROM sessions ORDER BY started_at").fetchall()}
```

## Формат выходного markdown

```markdown
# <имя_файла>

> Сборник обращений пользователя к <bot-name>
> Профиль: <profile>
> Источник: SQLite state.db → messages × sessions
> Сессий-источников: N
> Сгенерировано: <UTC>

## Сводка по сессиям

| ID сессии | Начало | Конец | Заголовок | Сообщений | Активных user | Компактнутых |
|-----------|--------|-------|-----------|-----------|---------------|--------------|
| ... | ... | ... | ... | ... | ... | ... |

> ⚠️ 77 активных обращений (развёрнутые).
> ⚠️ 60 компактнутых блоков — это `compacted=1`-записи, не разделяются.

---

## 1. Активные обращения (хронологически)

### Сессия `<sid>` — <title>

#### #001  [<timestamp>]  (msg_id=<id>)

<text>

---

## 2. Компактнутые блоки (превью)

### Из сессии `<sid>`

#### ⏚ Блок msg_id=<id>  [<timestamp>]

> ⚠️ Сжато Hermes, не разделяется.

```text
<первые 3000 символов summary>
```
```

## Сборка и сохранение

```python
out = []
out.append("# <имя_файла>")  # обычно "<prefix>-запросы-NN.md"
out.append("")
# ... (см. формат выше)

path = "/root/<имя_файла>.md"
with open(path, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
```

## Готовый скрипт

См. `scripts/export_user_messages.py` — запускается из коробки:

```bash
python3 scripts/export_user_messages.py fst-control telegram /root/fst-запросы-01.md
# или без аргументов — авто-именование в /root/
```

Скрипт сам найдёт `state.db`, отфильтрует активные/компактнутые,
почистит OOB/PRIOR/think-блоки, и сгенерирует файл. Затем — `MEDIA:<path>` в чат.

⚠️ **Имя файла — кириллица + snake_case**, дата в формате `YYYY_MM_DD`,
постфикс-NN. Это соглашение пользователя `fst-control` (см. memory).

## ⚠️ Важная оговорка: длинная сессия Telegram

Telegram-сессии Hermes могут **длиться неделями** без перезапуска —
один и тот же `session_id` живёт с 20 июля по 1 августа с `message_count=514`.
Поэтому сессий в `sessions` будет мало (1-3), но user-сообщений — много (50-200).

Это **нормально**, не баг. Группируй по сессиям, но внутри каждой
сессии сортируй строго по `messages.timestamp`.

## Edge cases

| Случай | Поведение |
|--------|-----------|
| `state.db` не существует | Сообщить, спросить путь к профилю |
| Профиль другой (`analyst_training`, `default`) | Поправить `PROFILE_DB` |
| `compacted` summary содержит 50+ КБ текста | Усечь до 3000 символов с пометкой «обрезано» |
| Одно сообщение повторяется подряд (split длинного ответа) | Дедупликация по (`content`, `|Δt|<2s`) |
| `active=0` (удалённые) | По умолчанию пропускать; опц. флаг `--include-deleted` |
| Bot not в Telegram | `source != 'telegram'` — поменять `SOURCE_FILTER` |
| Matrix / Discord / CLI | `source` принимает нужное значение (см. `sessions` для всех) |

## Verification Checklist

- [ ] `state.db` существует по указанному пути
- [ ] SQL вернул ≥ 0 user-сообщений (или честно сказали «0»)
- [ ] Каждое сообщение прошло `clean()` (нет `[OUT-OF-BAND]`, ` `, `[PRIOR CONTEXT]`)
- [ ] Сводная таблица сессий содержит корректные `started_at` / `ended_at`
- [ ] Активные сообщения выводятся в хронологическом порядке с msg_id
- [ ] Компактнутые блоки помечены как «не разделяются» + показаны превью
- [ ] Файл сохранён в `/root/` (или `/tmp/`, если временный)
- [ ] Файл отправлен пользователю через `MEDIA:<path>`, не вставлен inline

## Pitfalls

1. **Не выдавай `session_search`-truncation за полные данные.** Если попросили
   «все мои обращения», а ты получил 30 из 500 — это ложь. Всегда
   предупреждай: «X% обращений в compacted-блоках, недоступны по одному».

2. **Не путай `session_id` и `message_id`.** `session_id` — это идентификатор
   разговора (1 на сессию), `message_id` — конкретное сообщение. В выводе
   оба полезны: первый для группировки, второй для трассировки.

3. **`timestamp` у message ≠ `started_at` у session.** `started_at` сессии —
   это момент её создания (может быть на месяц раньше). `timestamp` сообщения —
   это когда **конкретная строка** появилась в БД. Сортируй по
   `messages.timestamp`, не по `sessions.started_at`.

4. **`source` фильтруй, но не ограничивай.** `telegram` — это chat-платформа.
   `cli` — это терминал. `matrix` — другой мессенджер. Если пользователь
   сказал «мои обращения», скорее всего имел в виду текущую платформу
   (последнюю активную сессию). Но **лучше спросить**, чем угадывать.

5. **Compiled cleaned text может быть очень длинным.** Один compacted-блок
   может весить 50 КБ. Никогда не вставляй его целиком в финальный markdown
   — усекай до 3000 символов. Иначе файл распухнет, а пользователь
   не сможет его прочитать.

6. **Отправляй файл через `MEDIA:`, не inline.** Файл >30 строк →
   `MEDIA:/root/<name>.md`. Inline только превью + сводка.

7. **Одна Telegram-сессия может жить неделями.** В `sessions.started_at`/
   `ended_at` — реальный интервал сессии (например, `2026-07-20 13:36` →
   `2026-08-01 19:14`, `message_count=514`). Но **активные user-сообщения**
   могут концентрироваться в последний день. Сортировка по
   `messages.timestamp` покажет реальный хронологический ход событий.
   Если вывести «по сессиям» — заголовок сессии будет длинный, а внутри
   — внезапно один день. Это не баг. **Аннотируйте** в сводке: «сессия
   формально 12 дней, активность — 1 августа».

8. **Проверь `scripts/export_user_messages.py` ПЕРЕД ручным SQL.**
   Скрипт уже существует и параметризован (`python3 scripts/export_user_messages.py
   <profile> <source> <output>`). Если будешь писать SQL inline через
   `execute_code` — остановись и запусти скрипт. Зачем дублировать?

9. **Compacted-блоки часто содержат tool-call JSON / `find_ent_MESSAGE_QUERY_manual`
   шум.** `clean()` с `PRIOR_RE` уже убирает инструментальные инъекции,
   но внутри summary могут быть обрывки вроде
   `]11;rgb:0000/0000/0000]11;rgb:0000/0000/0000Hermes проведи д...`. Для
   компактнутых блоков в финальном markdown оставляй ` ```text ```
   превью — пользователь сам поймёт, что это шум, и не будет пытаться
   парсить. **Не пытайся** дополнительно фильтровать — потеряешь осмысленные
   фрагменты.

## Связь с другими скиллами

- **`hermes-agent`** — команды `hermes sessions`, `hermes profile show`
  могут дать ту же информацию, но **не** в виде user-portable markdown.
- **`hermes-agent-skill-authoring`** — конвенции именования, frontmatter,
  размер SKILL.md.
- **`session_search`** (встроенный инструмент) — для поиска **внутри**
  конкретной сессии или discovery. Не для массового экспорта.

## История изменений

- **v1.0.0** — первый выпуск. Извлечение через `state.db` × `sessions` × `messages`.
  Возник из задачи «собрать мои обращения через бот с начала работы» для профиля
  `fst-control` (1 августа 2026). Найдено 77 активных + 60 компактнутых
  блоков в 2 telegram-сессиях.
