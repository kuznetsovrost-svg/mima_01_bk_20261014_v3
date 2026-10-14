# PLAYBOOK — система слепков fst-project-health

**Дата PLAYBOOK:** 2026-09-24
**Назначение:** описание полного pipeline работы со слепками — от генерации до построения отчётов.

---

## 1. Архитектура системы

```
┌────────────────────────────────────────────────────────────────┐
│                    PMForesight MCP сервер                       │
│                                                                 │
│  ┌──────────────────┐    ┌──────────────────────────────────┐ │
│  │ Карточка проекта │    │ Раздел «Документы ИИ»            │ │
│  │ ────────────────  │    │ ──────────────────────────────── │ │
│  │ ProjectId=4595   │    │ 📄 Слепок ...504-595-2026-09-...│ │
│  │ Код: 504-595     │    │ 📄 Слепок ...504-595-2026-09-...│ │
│  │ Name: ...        │    │ 📄 Слепок ...504-595-2026-09-...│ │
│  └──────────────────┘    └──────────────────────────────────┘ │
│         ▲                              │                        │
└─────────┼──────────────────────────────┼────────────────────────┘
          │                              │
          │ (1) чтение                   │ (2) запись / чтение
          │ live                         │ snapshot
          │                              │
┌─────────┴────────────────┐    ┌────────┴───────────────────────┐
│ LIVE pipeline            │    │ SNAPSHOT pipeline              │
│ (контур реального времени)│    │ (накопительный контур)         │
│                         │    │                                │
│ run_all.py               │    │ run_snap_md.py                 │
│      │                  │    │      │                         │
│      ▼                  │    │      ▼                         │
│ /tmp/project_X_report.md │    │ upload_entity_file             │
│      │                  │    │      │                         │
│      ▼                  │    │      ▼                         │
│ build_html_report.py    │    │ MCP (карточка, раздел)         │
│      │                  │    │                                │
│      ▼                  │    │ ─────────────────────          │
│ HTML (без «Слепок от:») │    │ fetch_snapshot.py              │
└─────────────────────────┘    │      │                         │
                                │      ▼                         │
                                │ ~/.hermes/.../cache/...md      │
                                │      │                         │
                                │      ▼                         │
                                │ build_html.py                  │
                                │      │                         │
                                │      ▼                         │
                                │ HTML (с «Слепок от: ...»)      │
                                └────────────────────────────────┘
```

---

## 2. LIVE pipeline (контур реального времени)

### 2.1. Схема

```
┌──────────────┐     ┌─────────────────┐     ┌────────────────┐
│ Пользователь │ ──► │ run_all.py      │ ──► │ MCP (live)     │
│ --code X     │     │ --code X        │     │ (HTTP/SSE)     │
└──────────────┘     └────────┬────────┘     └────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ Секции 3-9 MD    │   ← разделы отчёта
                    │ (промежуточные)  │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ rebuild_report.py│   ← склейка + YAML
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────────────────┐
                    │ /tmp/project_X_report.md     │
                    │ YAML: generator="fst-..."   │
                    │ НЕТ snapshot_timestamp!      │
                    └────────┬─────────────────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ build_html_report│
                    │ .py              │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────────────────┐
                    │ HTML (без «Слепок от:»)      │
                    │ MCP: PMForesight MCP v3.2.4  │
                    └──────────────────────────────┘
```

### 2.2. Команда

```bash
python3 ~/.hermes/profiles/fst-control/skills/productivity/fst-project-health/scripts/run_all.py \
    --code 504-595
```

### 2.3. Артефакты

- `/tmp/project_<code>_report.md` (самодостаточный MD с YAML)
- `/tmp/project_<code>_report.html` (финальный HTML, ~41 KB)
- `/tmp/.cache_*.json` (кэш MCP-ответов)

### 2.4. Время

19–52 секунды (зависит от MCP).

### 2.5. Признак «live» в HTML

В шапке HTML:
```
MCP: PMForesight MCP v3.2.4
```
**НЕТ** строки «Слепок от:».

---

## 3. SNAPSHOT pipeline (генерация + извлечение)

### 3.1. Фаза A: Генерация слепков

**Групповой режим** (несколько проектов одной командой):

```
Пользователь → run_snap_md.py --codes X Y Z
                  │
                  │  для каждого кода:
                  ▼
            ┌──────────────────┐
            │ run_all.py        │  (тот же что в LIVE)
            │ --code <X>        │
            └────────┬─────────┘
                     │
                     ▼
            ┌──────────────────────────────┐
            │ /tmp/project_<X>_report.md    │
            └────────┬─────────────────────┘
                     │
                     ▼
            ┌──────────────────────────────┐
            │ upload_entity_file            │
            │ Имя: «Слепок fst-project-     │
            │ health-snapshot-<X>-<TS>.MD» │
            └────────┬─────────────────────┘
                     │
                     ▼
            ┌──────────────────────────────┐
            │ MCP (карточка <X>, раздел     │
            │ «Документы ИИ»)               │
            └──────────────────────────────┘
```

**Команды:**

```bash
# 1 проект
python3 ~/.hermes/.../fst-project-health-snap-md/scripts/run_snap_md.py --code 504-595

# Группа проектов
python3 ~/.hermes/.../fst-project-health-snap-md/scripts/run_snap_md.py --codes 504-595 503-152 503-434 504-314

# Через скрипт-список (mass_list.py)
python3 ~/.hermes/.../fst-project-health-snap-md/scripts/mass_list.py
```

**Артефакты:**

- В MCP: новый файл `.MD` в карточке проекта.
- Локально (если включено): копия MD в `/tmp/project_<X>_report.md`.
- Лог: `<skill>/logs/<ISO-timestamp>.log`.

**Логика «never-fail»:** если один проект упал — пишем в лог, продолжаем остальные.

### 3.2. Фаза B: Извлечение слепков

**Групповой режим** (5 режимов выбора снапшота):

```
Пользователь → fetch_snapshot.py --code X [--last|--exact|--nearest|--first|--pick]
                  │
                  │ 1) list_files → найти все .MD в «Документы ИИ»
                  │ 2) выбрать по режиму
                  │ 3) resources/read file://download-file/<id>
                  ▼
            ┌──────────────────────────────┐
            │ ~/.hermes/.../cache/          │
            │ snapshots/<X>_<TS>.md        │
            └────────┬─────────────────────┘
                     │
                     ▼
            ┌──────────────────────────────┐
            │ build_html.py                │
            │ --md <PATH>                  │
            └────────┬─────────────────────┘
                     │
                     ▼
            ┌──────────────────────────────┐
            │ HTML (с «Слепок от: <TS>»)    │
            └──────────────────────────────┘
```

**5 режимов выбора:**

| Режим | Алгоритм | Когда использовать |
|---|---|---|
| `--last` (по умолчанию) | Сортировка по TS ↓, берём 1-й | «дай последний» |
| `--exact YYYY-MM-DDTHH:MM:SS` | Сравнение строк TS | Если знаем точный |
| `--nearest YYYY-MM-DDTHH:MM:SS` | Мин. расстояние до TS | Cron (по умолчанию для cron) |
| `--first` | Сортировка по TS ↑, берём 1-й | Трендовый анализ |
| `--pick` | Интерактивный список (TUI) | Разбор |

**Команды:**

```bash
# Скачать последний
python3 ~/.hermes/.../fst-project-health-from-md-snapshot/scripts/fetch_snapshot.py \
    --code 504-595 --last

# Скачать точный
python3 ~/.hermes/.../fst-project-health-from-md-snapshot/scripts/fetch_snapshot.py \
    --code 504-595 --exact 2026-09-20T14:30:00

# Скачать ближайший к дате (для cron)
python3 ~/.hermes/.../fst-project-health-from-md-snapshot/scripts/fetch_snapshot.py \
    --code 504-595 --nearest 2026-09-21T00:00:00

# Только список
python3 ~/.hermes/.../fst-project-health-from-md-snapshot/scripts/fetch_snapshot.py \
    --code 504-595 --list

# Цепочка fetch+build
python3 ~/.hermes/.../fst-project-health-from-md-snapshot/scripts/run.py \
    --code 504-595 --last --output /tmp/snapshot.html
```

**Артефакты:**

- `~/.hermes/profiles/fst-control/cache/snapshots/<X>_<TS>.md` — локальная копия MD.
- `<skill>/logs/<ISO-timestamp>.log` — лог.

### 3.3. Признак «snapshot» в HTML

В шапке HTML:
```
MCP: PMForesight MCP v3.2.4 · Слепок от: 2026-09-24 16:34:12
```

**ЕСТЬ** строка «Слепок от:».

---

## 4. Сравнение LIVE и SNAPSHOT

| Параметр | LIVE | SNAPSHOT |
|---|---|---|
| Источник данных | MCP сейчас | MD-файл в карточке |
| Генератор | `fst-project-health` | `fst-project-health-snap-md` |
| YAML `snapshot_timestamp` | **НЕТ** | **ДА** |
| В HTML «Слепок от:» | НЕТ | ДА |
| Время сборки | 19–52 сек (зависит от MCP) | 1–2 сек (только HTML) |
| Зависит от MCP при чтении? | ДА (нельзя прочитать offline) | НЕТ (MD локально) |

---

## 5. Массовые операции: сценарии

### 5.1. Идеальный

> Все проекты в списке доступны, генерация/чтение проходят без ошибок.

```
=== BODY ===
✓ 504-595 → upload ok (FileId=206003)
✓ 503-152 → upload ok (FileId=206004)
✓ 503-434 → upload ok (FileId=206005)
✓ 504-314 → upload ok (FileId=206006)
=== TRAILER ===
Total: 4 (4 ok, 0 failed)
```

### 5.2. Частая проблема: недостаточно прав

> Пользователь имеет права не на все проекты.

```
=== BODY ===
✓ 504-595 → upload ok (FileId=206003)
✗ 503-152 → FORBIDDEN (http=403)
✓ 503-434 → upload ok (FileId=206005)
✗ 504-314 → FORBIDDEN (http=403)
=== TRAILER ===
Total: 4 (2 ok, 2 failed)
```

Скилл не падает — успешные проекты обрабатываются, ошибки пишутся в лог.

### 5.3. Ошибка в списке

> Указан код несуществующего проекта.

```
=== BODY ===
✓ 504-595 → upload ok (FileId=206003)
✗ 999-FAKE → NOT_FOUND (http=404)
✓ 503-152 → upload ok (FileId=206004)
=== TRAILER ===
Total: 3 (2 ok, 1 failed)
```

---

## 6. Прецеденты по времени

| Операция | Время |
|---|---|
| LIVE: `run_all.py` (1 проект) | 19–52 сек |
| SNAPSHOT: генерация 1 проекта | 19–52 сек |
| SNAPSHOT: извлечение 1 слепка | 1–2 сек |
| SNAPSHOT: HTML из MD | 1 сек |
| Массовая генерация 4 проектов | 2–4 мин |
| Массовое чтение 4 снапшотов | 5–8 сек |

---

## 7. Где что лежит

```
~/.hermes/profiles/fst-control/skills/productivity/
├── fst-project-health/                    ← LIVE pipeline
├── fst-project-health-word/               ← DOCX из MD
├── fst-project-health-snap-md/            ← генерация слепков
├── fst-project-health-from-md-snapshot/   ← извлечение слепков + HTML
└── fst-project-health-tests/              ← тесты всего семейства

~/.hermes/profiles/fst-control/cache/snapshots/
└── <code>_<timestamp>.md                  ← кэш скачанных слепков

/tmp/
├── project_<code>_report.md               ← live-MD (промежуточный)
├── project_<code>_report.html             ← финальный HTML (live)
├── snapshot_<code>.html                   ← HTML из снапшота
└── .cache_*.json                          ← кэш MCP-ответов

PMForesight MCP / Карточка проекта / Раздел «Документы ИИ»:
└── Слепок fst-project-health-snapshot-<code>-<timestamp>.MD
```
