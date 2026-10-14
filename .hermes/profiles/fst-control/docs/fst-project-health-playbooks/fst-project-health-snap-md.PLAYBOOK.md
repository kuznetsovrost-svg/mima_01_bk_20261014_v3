# PLAYBOOK — fst-project-health-snap-md

**Версия скилла:** v1.0.19
**Дата PLAYBOOK:** 2026-09-24
**Назначение:** генерация MD-слепков состояния проектов в карточки MCP (категория «Документы ИИ»).

---

## 1. Общий обзор

`fst-project-health-snap-md` — **генератор слепков**. Запускает live-сборку через `run_all.py` и загружает MD в карточку проекта.

```
MCP (сейчас) → run_all.py → MD → upload_entity_file → MCP (карточка, раздел «Документы ИИ»)
```

**Формат хранения:** MD (не JSON). Самодостаточный (YAML front-matter + секции + таблицы).
**Категория в MCP:** «Документы ИИ» (там же, где «Документы проекта»).
**Префикс файла:** `Слепок fst-project-health-snapshot-<code>-<timestamp>.MD`.

> **Важно:** префикс содержит «snapshot» (имя старого скилла) — это **наследие**, не баг. Так удобнее для совместимости с историческими записями в карточке.

---

## 2. API скилла

### 2.1. CLI-параметры `run_snap_md.py`

```bash
python3 scripts/run_snap_md.py --code <PROJECT_CODE> [опции]
```

| Параметр | Обязательный | Описание |
|---|---|---|
| `--code <PROJECT_CODE>` | ✅* | Код проекта (один или несколько через пробел). |
| `--codes <CODE1> <CODE2> ...` | ✅* | Альтернативный синтаксис для нескольких кодов. |
| `--no-log` | ❌ | Не писать лог (по умолчанию лог пишется всегда). |
| `--log-dir <DIR>` | ❌ | Куда писать лог (по умолчанию `~/.hermes/profiles/fst-control/skills/productivity/fst-project-health-snap-md/logs/`). |

`*` Нужен хотя бы один из `--code` или `--codes`.

### 2.2. Массовый вызов: 2 варианта

**Вариант A — список в скрипте** (редактируется заранее):
```python
# scripts/mass_list.py
CODES = ["504-595", "503-152", "503-434", "504-314"]
```

**Вариант B — массив через флаг:**
```bash
python3 scripts/run_snap_md.py --codes 504-595 503-152 503-434 504-314
```

### 2.3. Возвращаемые артефакты

- **В MCP:** новый файл в карточке проекта (раздел «Документы ИИ»), имя `Слепок fst-project-health-snapshot-<code>-<timestamp>.MD`.
- **В локальном кэше** (опционально): копия MD в `/tmp/project_<code>_report.md`.
- **Лог:** `<skill>/logs/<ISO-timestamp>.log` (если не указан `--no-log`).

---

## 3. Скрипты скилла

| Скрипт | LOC | Размер | Назначение |
|---|---|---|---|
| `run_snap_md.py` | 572 | 25 KB | **Главный.** Запускает live-сборку и загружает MD в MCP. Поддерживает массовые вызовы. |
| `logging_utils.py` | 270 | 12 KB | `RunLogger` с header/body/trailer. Не падает на середине (never-fail). |
| `rotate_logs.py` | 188 | 8 KB | Ротация логов: 30 дней → archive (gzip), 180 дней → delete. |

**Всего: 3 скрипта.**

---

## 4. Методы скилла (для переиспользования)

### 4.1. `run_snap_md.py::main()`

- **Назначение:** CLI-точка входа.
- **Параметры:** см. раздел 2.1.

### 4.2. `run_snap_md.py::run_one()`

- **Назначение:** собрать и загрузить слепок для одного проекта.
- **Параметры:** `code: str`, `log: RunLogger`.
- **Что делает:**
  1. Запускает `subprocess.run([sys.executable, "run_all.py", "--code", code])`.
  2. Читает `/tmp/project_<code>_report.md`.
  3. Вызывает `mcp__fst_pmpractice__upload_entity_file` (или `save_entity`).
  4. Пишет результат в лог.
- **Когда переиспользовать:** для интеграции в другие автоматизированные скрипты.

### 4.3. `logging_utils.py::RunLogger`

- **Назначение:** структурированное логирование массовых операций.
- **Параметры:** `enabled: bool = True`, `log_dir: Path = ...`.
- **Методы:**
  - `log_header(account: str, role: str, action: str, args: list)`.
  - `log_body(code: str, ok: bool, type: str = "", http_code: int = 0, message: str = "", raw: str = "")`.
  - `log_trailer()` — вызывать в `finally:`.
- **Структура лога:**
  ```
  === HEADER ===
  Дата: 2026-09-24T16:34:00
  User: user@example.com
  Role: role-name (или n/a)
  Action: run_snap_md
  Args: --codes 504-595 503-152
  Projects: ['504-595', '503-152']
  === BODY ===
  ✓ 504-595 ... (ok=True, http_code=200)
  ✗ 503-152 ... (ok=False, http_code=403, message=Forbidden)
  === TRAILER ===
  Total: 2 (1 ok, 1 failed)
  Elapsed: 1m 23s
  ```
- **Когда переиспользовать:** в любых **массовых** операциях с MCP (не только для слепков).

### 4.4. `rotate_logs.py::rotate()`

- **Назначение:** архивация старых логов.
- **Политика:** >30 дней → `gzip` → `archive/`, >180 дней → `delete`.
- **Когда запускать:** через cron раз в сутки (см. раздел 6).

---

## 5. Сценарии массового вызова

### 5.1. Идеальный сценарий

> Все проекты в списке доступны пользователю, генерация и запись проходят без ошибок.

```
=== BODY ===
✓ 504-595 → MCP FileId=206003
✓ 503-152 → MCP FileId=206004
✓ 503-434 → MCP FileId=206005
✓ 504-314 → MCP FileId=206006
=== TRAILER ===
Total: 4 (4 ok, 0 failed)
```

### 5.2. Частая проблема: недостаточно прав

> Пользователь имеет права не на все проекты из списка.

```
=== BODY ===
✓ 504-595 → MCP FileId=206003
✗ 503-152 → FORBIDDEN: нет прав на проект (http=403)
✓ 503-434 → MCP FileId=206005
✗ 504-314 → FORBIDDEN: нет прав на проект (http=403)
=== TRAILER ===
Total: 4 (2 ok, 2 failed)
```

**Принцип: «скрипт может — делает. Не может — пишет в лог, на середине никогда не останавливается и не падает.»**

### 5.3. Ошибка в списке проектов

> Указан код несуществующего проекта.

```
=== BODY ===
✓ 504-595 → MCP FileId=206003
✗ 999-FAKE → NOT_FOUND: проект не найден (http=404)
✓ 503-152 → MCP FileId=206004
=== TRAILER ===
Total: 3 (2 ok, 1 failed)
```

### 5.4. Сценарий «ничего не работает»

> MCP лежит целиком (например, идёт ремонт).

```
=== BODY ===
✗ 504-595 → ReadTimeout: HTTPSConnectionPool...
✗ 503-152 → ReadTimeout: HTTPSConnectionPool...
✗ 503-434 → ReadTimeout: HTTPSConnectionPool...
✗ 504-314 → ReadTimeout: HTTPSConnectionPool...
=== TRAILER ===
Total: 4 (0 ok, 4 failed)
Elapsed: 2m 8s
```

Скилл не падает — возвращает exit-code 0, всё записано в лог.

---

## 6. Ротация логов

```bash
# cron (ежедневно в 03:00)
0 3 * * * ~/.hermes/.../fst-project-health-snap-md/scripts/rotate_logs.py
```

Политика:
- Лог старше **30 дней** → сжимается gzip → переносится в `archive/`.
- Лог старше **180 дней** → удаляется.

---

## 7. Прецеденты

| Сценарий | Время |
|---|---|
| 1 проект, MCP жив | 19–52 сек |
| 4 проекта, все ОК | 2–4 мин |
| 4 проекта, 2 недоступны | 2–4 мин (неудачи идут параллельно) |

---

## 8. Где скилл лежит

```
~/.hermes/profiles/fst-control/skills/productivity/fst-project-health-snap-md/
├── SKILL.md
├── README.md
├── CHANGELOG.md
├── playbook.md
├── scripts/
│   ├── run_snap_md.py
│   ├── logging_utils.py
│   └── rotate_logs.py
├── references/
├── logs/                       ← сюда пишутся логи
└── .env.example
```
