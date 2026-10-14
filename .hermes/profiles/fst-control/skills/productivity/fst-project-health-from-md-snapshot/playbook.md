# PLAYBOOK — fst-project-health-from-md-snapshot

**Версия скилла:** v1.0.19
**Дата PLAYBOOK:** 2026-09-24
**Назначение:** извлечение MD-слепков из MCP и построение HTML-отчёта по ним (без обращения к MCP в реальном времени).

---

## 1. Общий обзор

`fst-project-health-from-md-snapshot` — **извлекатель слепков + построитель отчётов**.

```
MCP (карточка проекта, раздел «Документы ИИ») 
    → fetch_snapshot.py → MD в кэш 
    → build_html.py → HTML
```

**Отличие от live:** HTML строится **только** по скачанному MD. К текущему состоянию MCP не обращается.
**Признак в HTML:** в шапке появляется строка **«Слепок от: YYYY-MM-DD HH:MM:SS»** (timestamp из YAML front-matter скачанного MD).

---

## 2. API скилла

### 2.1. `fetch_snapshot.py` — извлечение MD

```bash
python3 scripts/fetch_snapshot.py --code <CODE> [опции]
```

| Параметр | Обязательный | Описание |
|---|---|---|
| `--code <PROJECT_CODE>` | ✅ | Код проекта. |
| `--last` | ❌ | Скачать самый свежий снимок (по умолчанию — `--nearest`). |
| `--exact YYYY-MM-DDTHH:MM:SS` | ❌ | Скачать снимок с **точным** timestamp. |
| `--nearest YYYY-MM-DDTHH:MM:SS` | ❌ | Скачать снимок, **ближайший** к указанному времени (по умолчанию — `--last`). |
| `--first` | ❌ | Скачать самый ранний снимок. |
| `--pick` | ❌ | Интерактивный выбор из списка (показывает все снапшоты). |
| `--list` | ❌ | Только список снапшотов без скачивания. |
| `--no-log` | ❌ | Не писать лог. |
| `--log-dir <DIR>` | ❌ | Куда писать лог. |

### 2.2. `build_html.py` — построение HTML

```bash
python3 scripts/build_html.py --md <PATH> [опции]
```

| Параметр | Обязательный | Описание |
|---|---|---|
| `--md <PATH>` | ✅ | Путь к MD-файлу (из `--last`/`--exact`/`--nearest`). |
| `--output <PATH>` | ❌ | Куда сохранить HTML. |
| `--code <CODE>` | ❌ | Код проекта (для имени файла). |

### 2.3. `run.py` — цепочка fetch+build

```bash
python3 scripts/run.py --code <CODE> [--last|--exact|--nearest ...] [опции]
```

`run.py` объединяет fetch + build в одну команду. Удобно для cron.

---

## 3. Режимы выбора снапшота (5 режимов)

| Режим | Когда использовать | Пример |
|---|---|---|
| `--last` | «дай последний» (по умолчанию) | `--last` |
| `--exact` | Если знаем точный timestamp из другого источника | `--exact 2026-09-20T14:30:00` |
| `--nearest` | Cron / скрипты (по умолчанию) | `--nearest 2026-09-21T00:00:00` |
| `--first` | Трендовый анализ | `--first` |
| `--pick` | Интерактивный разбор (редко) | `--pick` |

### 3.1. Алгоритм выбора

1. `list_files` → получить все `*.MD` файлы в разделе «Документы ИИ» карточки.
2. Извлечь timestamp из имени файла (`Слепок fst-project-health-snapshot-<code>-<YYYY-MM-DDTHH-MM-SS>.MD`).
3. Применить фильтр по режиму.
4. Скачать выбранный через `resources/read file://download-file/<physicalFileId>`.

### 3.2. Прецедент: `--list`

```bash
python3 scripts/fetch_snapshot.py --code 504-595 --list
```

```
📂 Доступные снапшоты для 504-595:
  1. 2026-09-24 16:34:12 — FileId=70139, 14210 bytes
  2. 2026-09-24 17:18:12 — FileId=70201, 14160 bytes
  3. 2026-09-24 17:31:45 — FileId=70202, 14200 bytes
  ...
```

---

## 4. Скрипты скилла

| Скрипт | LOC | Размер | Назначение |
|---|---|---|---|
| `fetch_snapshot.py` | 598 | 24 KB | **Главный — извлечение.** 5 режимов выбора снапшота, retry при пустом `result: {}`. |
| `build_html.py` | 142 | 5 KB | **Главный — HTML-сборка.** Минимальный wrapper над `build_html_report.py`. |
| `run.py` | 141 | 5 KB | Цепочка `fetch + build` для одной команды. |
| `logging_utils.py` | 243 | 10 KB | `RunLogger` (зеркало snap-md, с дополнительной диагностикой для извлечения). |
| `rotate_logs.py` | 188 | 8 KB | Ротация: 30 дней archive, 180 дней delete. |

**Всего: 5 скриптов.**

---

## 5. Методы скилла (для переиспользования)

### 5.1. `fetch_snapshot.py::main()`

- **Назначение:** CLI-точка входа.

### 5.2. `fetch_snapshot.py::download_md()`

- **Назначение:** скачивает MD по physicalFileId.
- **Параметры:** `physical_file_id: str`, `target_path: Path`.
- **Retry:** 3 попытки с новой MCP-сессией (защита от пустого `result: {}`).
- **Когда переиспользовать:** в любых скриптах, которые скачивают файлы из MCP.

### 5.3. `fetch_snapshot.py::select_snapshot()`

- **Назначение:** выбирает снапшот из списка по режиму (`--last/--exact/--nearest/--first/--pick`).
- **Параметры:** `files: list`, `mode: str`, `target_ts: Optional[str]`.
- **Когда переиспользовать:** для интеграции в другие скрипты выбора снапшотов.

### 5.4. `build_html.py::main()`

- **Назначение:** CLI-точка входа для HTML-сборки.

### 5.5. `run.py::run()`

- **Назначение:** цепочка fetch+build.
- **Параметры:** `code: str`, `mode: str`, `target_ts: Optional[str]`.
- **Когда переиспользовать:** для cron-задач (одна команда = «скачай и собери отчёт»).

### 5.6. `logging_utils.py::RunLogger` (расширенный)

- **Назначение:** структурированное логирование для извлечения.
- **Дополнительные поля** (по сравнению с snap-md):
  - `file_id`: ID скачиваемого файла.
  - `bytes_received`: сколько байт получено.
  - `sha256`: контрольная сумма для верификации.
- **Когда переиспользовать:** когда нужно **скачать** что-то из MCP массово (не только слепки).

---

## 6. Сценарии массового вызова (массовое чтение)

### 6.1. Идеальный

```
✓ 504-595 → cache/snapshots/504-595_2026-09-24_16-34-12.md (14210 bytes)
✓ 503-152 → cache/snapshots/503-152_2026-09-24_15-12-00.md (13800 bytes)
=== TRAILER ===
Total: 2 (2 ok, 0 failed)
```

### 6.2. Недостаточно прав

```
✓ 504-595 → cache/snapshots/504-595_2026-09-24_16-34-12.md (14210 bytes)
✗ 503-152 → FORBIDDEN: нет прав на чтение карточки (http=403)
=== TRAILER ===
Total: 2 (1 ok, 1 failed)
```

### 6.3. Ошибка в списке

```
✓ 504-595 → cache/snapshots/504-595_2026-09-24_16-34-12.md (14210 bytes)
✗ 999-FAKE → NOT_FOUND: проект не найден (http=404)
=== TRAILER ===
Total: 2 (1 ok, 1 failed)
```

Принцип: «скрипт может — делает. Не может — пишет в лог.»

---

## 7. Построение отчёта по скачанному MD

```bash
# 1. Скачать снапшот
python3 scripts/fetch_snapshot.py --code 504-595 --last --no-log
# → cache/snapshots/504-595_<timestamp>.md

# 2. Собрать HTML
python3 scripts/build_html.py --md cache/snapshots/504-595_<timestamp>.md \
    --code 504-595 --output /tmp/snapshot_504-595.html

# В HTML: «MCP: PMForesight MCP v3.2.4 · Слепок от: <timestamp>»
```

### 7.1. Цепочка одной командой (`run.py`)

```bash
python3 scripts/run.py --code 504-595 --last \
    --output /tmp/snapshot_504-595.html
```

---

## 8. Прецеденты

| Сценарий | Время |
|---|---|
| `fetch_snapshot --last` (1 проект) | 1–2 сек |
| `build_html --md` | 1 сек |
| `run.py` (цепочка) | 2–3 сек |
| Массовое чтение 4 проектов | 5–8 сек |

---

## 9. Где скилл лежит

```
~/.hermes/profiles/fst-control/skills/productivity/fst-project-health-from-md-snapshot/
├── SKILL.md
├── README.md
├── CHANGELOG.md
├── playbook.md
├── scripts/
│   ├── fetch_snapshot.py
│   ├── build_html.py
│   ├── run.py
│   ├── logging_utils.py
│   └── rotate_logs.py
├── references/
│   └── api.md
├── logs/                       ← сюда пишутся логи
└── .env.example
```
