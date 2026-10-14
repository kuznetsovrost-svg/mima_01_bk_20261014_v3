# Playbook по скиллу `fst-project-health-snapshot`

**Версия:** 1.0.19 — 2026-09-23
**Для кого:** коллеги и другие агенты, которые будут работать
с JSON-слепками проектов и/или поддерживать этот скилл.

---

## 📖 Назначение

Скилл `fst-project-health-snapshot` **периодически собирает JSON-слепки**
состояния проектов из PMForesight и загружает их в карточки проектов
(в категорию «Документы ИИ») для последующего построения
трендовых отчётов.

**Принципиальное отличие от `fst-project-health`:**
тот строит MD/HTML для **человека**, этот — JSON для **другого скилла**
(построителя трендов).

---

## 🎯 Главные конвенции (для понимания и поддержки)

### 1. Имя файла — главный идентификатор

```
Слепок fst-project-health-snapshot-<project_code>-YYYY-MM-DD_HH-MM-SS.JSON
```

- **Префикс** `Слепок fst-project-health-snapshot-` — однозначно
  отделяет наши слепки от других документов в категории
  «Документы ИИ» (там могут быть и другие документы).
- **Код проекта** (`<project_code>`, например `504-595`) — включён в
  имя для удобства группировки в UI PMForesight: при сортировке по
  имени файлы одного проекта идут подряд.
- **Timestamp с секундами** — по требованию пользователя.
- Расширение `.JSON` (заглавными) — как принято в PMForesight.

### 2. `_meta.generator` — второй уровень защиты

Внутри каждого JSON есть блок:

```json
{
  "_meta": {
    "schema_version": "1.0.0",
    "generator": "fst-project-health-snapshot",
    "generator_version": "1.0.19",     // v1.0.19: синхронизировано с семейством
    "produced_at": "2026-09-23T22:00:00+03:00",  // момент генерации JSON-слепка
    "snapshot_timestamp": "2026-09-23 21:55:00",  // v1.0.19: копия из YAML front-matter MD
    "snapshot_kind": "fst-project-health-snapshot",
    "source_skill": "fst-project-health",
    "source_skill_version": "1.0.19",
    "project_code": "504-595",
    "project_id": 4595
  },
  "snapshot_kind": "fst-project-health-snapshot",
  ...
}
```

**Различие между `produced_at` и `snapshot_timestamp` (v1.0.19):**

- `produced_at` — **момент генерации JSON-слепка** (этого скрипта).
- `snapshot_timestamp` — **копия `snapshot_timestamp` из YAML front-matter
  исходного MD** (момент сборки данных через `fst-project-health/run_all.py`).

Обычно `produced_at ≥ snapshot_timestamp` на единицы секунд, потому что
JSON — обёртка поверх MD. **Оба — надёжные источники правды**; для
построителя трендов важнее `snapshot_timestamp` (он не «дрейфует» при
перевыпуске JSON без пересборки MD).

**Для построителя трендов фильтр «свой vs чужой»:**

```python
def is_our_snapshot(json_obj: dict) -> bool:
    meta = json_obj.get("_meta", {})
    return (
        meta.get("generator") == "fst-project-health-snapshot"
        and meta.get("snapshot_kind") == "fst-project-health-snapshot"
        # опционально: проверка semver
        # and re.match(r"^\d+\.\d+\.\d+$", meta.get("schema_version", ""))
    )
```

**Два независимых признака:**
- Префикс имени файла (`Слепок fst-project-health-snapshot-`)
- Поле `_meta.generator` (`"fst-project-health-snapshot"`)

Если хотя бы одно совпадает — это наш слепок. Оба сразу — точно наш.

### 3. Накопительный режим

Каждый прогон создаёт **новый файл**, старые **не удаляются**.
Это by design — даёт историю для построителя трендов.

**Почему не удаляем:** у пользовательского токена нет прав на удаление
DocumentFile в MCP (проверено в probe 2026-09-15). Очистка — только
вручную через UI PMForesight.

---

## 🔧 Структура скилла

```
fst-project-health-snapshot/
├── SKILL.md                   # описание для Hermes Agent
├── README.md                  # краткая инструкция
├── playbook.md                # ← ВЫ ЗДЕСЬ
├── .env.example               # PMP_TOKEN
├── requirements.txt           # requests
├── scripts/
│   └── run_snapshot.py        # главный скрипт
└── outputs/                   # локальные копии JSON-слепков
```

---

## 🚀 Использование

### Ручной запуск

```bash
# Все 4 проекта
python3 scripts/run_snapshot.py

# Один проект
python3 scripts/run_snapshot.py --code 504-595

# Dry-run (только локально, без MCP)
python3 scripts/run_snapshot.py --dry-run
```

### Расписание (cron)

Рекомендуется **раз в неделю ночью** (например, воскресенье 03:00 MSK).

**Внутри Hermes Agent** — через `cronjob_manage`:
```
action: create
job_id: snapshot-weekly
schedule: 0 3 * * 0
prompt: |
  Запусти:
  cd ~/.hermes/profiles/fst-control/skills/productivity/fst-project-health-snapshot
  python3 scripts/run_snapshot.py
  Если будут ошибки — пришли мне stderr.
deliver: origin
```

**Внешний cron** — `crontab -e`:
```cron
0 3 * * 0 cd /opt/skills/fst-project-health-snapshot && python3 scripts/run_snapshot.py >> logs/snapshot.log 2>&1
```

---

## 🔄 Pipeline (как это работает)

```
┌─ run_snapshot.py (этот скилл) ────────────────────────────────┐
│                                                              │
│ 1. find_project_id(code)         → MCP find_entity            │
│                                                              │
│ 2. subprocess.run(                                           │
│      [python3, run_all.py, --code, code, --no-cache,        │
│       --generator, fst-project-health-snapshot]              │
│    )                           → subprocess → MD             │
│                                                              │
│ 3. parse_md_to_data(md_path)     → СОБСТВЕННЫЙ парсер         │
│   (скопирован/синхронизирован с fst-project-health/         │
│    build_html_report.py, v1.0.19)                           │
│                                                              │
│ 4. wrap_into_snapshot(data)      → добавляет _meta            │
│                                                              │
│ 5. save_local(snapshot)          → outputs/<code>_<ts>.json   │
│                                                              │
│ 6. upload_to_mcp(snapshot, ...)  → MCP upload_entity_file    │
│       documentId=70139                                     │
│       file_name="Слепок fst-project-health-snapshot-..."    │
└──────────────────────────────────────────────────────────────┘
```

**Зачем `--generator fst-project-health-snapshot` (v1.0.19):**
атрибутирует происхождение MD в YAML (`generator:
"fst-project-health-snapshot"`). Без этого генератор MD был бы
`fst-project-health` (по умолчанию в `run_all.py`), и в JSON-метаданных
пришлось бы угадывать реального автора.

**Шаг 3 (парсер MD) — был внешним до v1.0.19.** Исторически этот
скилл импортировал `parse_md_to_data` из `fst-project-health-word`
(через `sys.path`). С v1.0.19 парсер MD встроен в этот скилл —
логика идентична `fst-project-health/build_html_report.py`
(`_parse_indicators_from_md` + секционный парсер). Зависимость от
`fst-project-health-word` снята.

### Почему subprocess, а не прямой import?

Прямой импорт `from fst_project_health.scripts import ...` потребовал бы
либо менять `PYTHONPATH`, либо запускать из каталога `fst-project-health`.
Subprocess — **чище**: запускаем готовый pipeline как чёрный ящик,
не трогаем основной скилл.

Минус: subprocess тратит ~40 сек на проект (на 4 проекта ~2.5 мин).
Прямой импорт мог бы быть ~10 сек на проект. Но **изоляция важнее
скорости** для накопительного режима (запускается раз в неделю).

---

## 📋 Список проектов по умолчанию

```python
DEFAULT_PROJECTS = ["504-595", "503-152", "503-434", "504-314"]
```

Чтобы изменить:
1. Открыть `scripts/run_snapshot.py`.
2. Изменить массив `DEFAULT_PROJECTS`.
3. Сохранить.

Или передать `--code <проект>` для разового запуска.

---

## 🔌 Зависимости от других скиллов

| Скилл | Что берём | Как |
|---|---|---|
| `fst-project-health` | Сбор MD через `run_all.py` | subprocess (БЕЗ модификации) |
| PMForesight MCP | `find_entity`, `upload_entity_file` | прямые SSE-вызовы через `requests` |

> **v1.0.19:** снята зависимость от `fst-project-health-word` (откуда
> раньше импортировался `parse_md_to_data`). Парсер MD теперь встроен
> в этот скилл (см. секцию «Pipeline»).

**Если любой из них недоступен — скилл не работает.**

---

## 🌐 Переменные окружения (портабельность)

Все пути и URL — через env-vars с fallback на `/root/.hermes/...` (для
локального Hermes-профиля). Для другого сервера — установить:

| Env | Назначение | По умолчанию |
|---|---|---|
| `PMP_TOKEN` | JWT-токен PMForesight | (обязательно) |
| `FST_PROJECT_HEALTH_PATH` | Путь к скиллу fst-project-health | `/root/.hermes/profiles/fst-control/skills/productivity/fst-project-health` |
| `MCP_URL` | URL MCP-сервера | `https://ppreplica.hera.pmpractice.ru/mcp` |

> **`FST_PROJECT_HEALTH_WORD_PATH`** — устаревшая переменная, **удалена**
> в v1.0.19. Парсинг MD встроен в этот скилл.

**Порядок приоритета для PMP_TOKEN:**
1. `os.environ["PMP_TOKEN"]`
2. `<каталог скилла>/.env`
3. `~/.hermes/profiles/fst-control/.env`

**Установка на другом сервере (полностью):**

```bash
# 1. Скопировать 2 скилла (НЕ три — word больше не нужен)
scp -r fst-project-health/          user@server:/opt/skills/
scp -r fst-project-health-snapshot/ user@server:/opt/skills/
# ~~fst-project-health-word/ НЕ копировать — больше не нужен.~~

# 2. Зависимости
cd /opt/skills/fst-project-health-snapshot
pip install -r requirements.txt     # requests
# (если нужен DOCX-отчёт отдельно: см. fst-project-health-word)

# 3. .env (с путями этого сервера)
cd /opt/skills/fst-project-health-snapshot
cp .env.example .env
# раскомментировать и заполнить:
#   FST_PROJECT_HEALTH_PATH=/opt/skills/fst-project-health
#   PMP_TOKEN=<jwt>
# (FST_PROJECT_HEALTH_WORD_PATH больше не нужен.)

# 4. Dry-run
python3 scripts/run_snapshot.py --dry-run

# 5. Боевой прогон
python3 scripts/run_snapshot.py
```

---

## ⚠️ Что делать, если что-то сломалось

### `find_project_id` возвращает None

- Проверить, что код проекта корректен.
- Проверить, что в MCP есть проект (через UI).

### `subprocess.run` падает с таймаутом

- Увеличить `PIPELINE_TIMEOUT` в скрипте (по умолчанию 300 сек).
- Проверить, что `fst-project-health` работает автономно:
  ```bash
  cd ~/.hermes/profiles/fst-control/skills/productivity/fst-project-health/scripts
  python3 run_all.py --code 504-595
  ```

### `parse_md_to_data` падает

> **v1.0.19:** этот раздел устарел. `parse_md_to_data` теперь встроен
> в этот скилл (см. секцию «Pipeline»), а не импортируется из
> `fst-project-health-word`. Если парсер падает — это **баг в коде
> парсера**, а не проблема зависимостей.
>
> Что делать:
> 1. Сохранить MD (`outputs/<code>_<ts>.md`) для отладки.
> 2. Перейти в `fst-project-health/scripts/build_html_report.py` —
>    там та же логика парсера, и можно сравнить поведение.
> 3. Если MD был сгенерирован **новой версией** `fst-project-health`
>    со старым парсером — обновить парсер, обновить версию в
>    `__init__`.

### `upload_to_mcp` возвращает ошибку

- Проверить `PMP_TOKEN` в `.env`.
- Проверить, что `DocumentId=70139` всё ещё существует (категория
  «Документы ИИ»).
- Проверить, что `dataId` = числовой project_id.

### Накопились старые слепки

Вручную через UI PMForesight (вкладка «Документы ИИ» проекта,
выделить → удалить). API для удаления нет (ограничение безопасности MCP).

---

## 📥 MCP-write discovery: как найти категорию документа и загрузить файл

Этот раздел — для тех, кто поддерживает скилл или пишет аналогичный
write-скилл. Описан один раз, чтобы не пришлось повторять probe-этапы.

### Шаг 1. Найти `documentId` нужной категории

Категории документов в карточке проекта — это записи сущности `Document`.
Не `DocumentFile` (это сами файлы), а `Document` (категории вкладок).

```python
# Получить все категории для сущности Project
resp = mcp_call(sid, "get_view", {
    "entityName": "Document",
    "viewName": "DocumentView",
    "limit": 100,
})
# Каждая запись содержит:
#   DocumentId, Entity="Проект", Name="Документы ИИ",
#   ActivityPhase="Архив, Завершение, Инициирование, Отменено,
#                  Подготовка, Постпроектный мониторинг [отключен],
#                  Пресейл, Реализация"
#   entityName="Project", ProjectProfile="Базовый полный"
```

Найти нужную запись по `Name`. Для «Документы ИИ» → `DocumentId=70139`.

Если категория НЕ существует — её надо **создать** через `save_entity` с
`id="new"` (см. `references/mcp-attribute-value-write-pitfalls.md` P-MCP-1
про `create_entity` doesn't exist).

### Шаг 2. Загрузить файл через `upload_entity_file`

```python
import base64
content_b64 = base64.b64encode(json_content_bytes).decode("ascii")

resp = mcp_call(sid, "upload_entity_file", {
    "entityName": "Project",          # сущность карточки
    "dataId":      "4595",           # числовой project_id как строка
    "documentId":  70139,            # ID категории из шага 1
    "uploadedFileName": "Слепок fst-project-health-snapshot-2026-09-15_16-30-45.JSON",
    "uploadedFileContentBase64": content_b64,
    # activityPhaseId — НЕ передавать для multi-phase категорий
    # (например «Документы ИИ» привязаны ко всем 8 фазам ЖЦ).
    # Если передать — сервер может отклонить или записать в одну фазу.
})
# resp: {"success": true, "id": <FileId>, "url": "/api/file/get/..."}
```

### Шаг 3. Проверить, что файл появился

```python
files = mcp_call(sid, "list_files", {
    "className": "Project",         # обязательно — имя класса сущности
    "dataId":    "4595",
    "documentId": 70139,
})
# [{physicalFileId, url, name, fileSize, isLink}, ...]
```

⚠️ `list_files` требует **`className`** (не `entityName`, не `entity`) —
это легкое несоответствие с другими методами MCP.

### Шаг 4. ⚠️ Удалить НЕЛЬЗЯ

```python
mcp_call(sid, "delete_entity", {"entityName": "DocumentFile", "id": "205987"})
# → {"error": "Удаление не выполнено: Нет доступа к удалению"}
```

**У пользовательского токена НЕТ прав на удаление `DocumentFile` через
MCP.** Это ограничение безопасности системы, не баг. Решения:

- Ничего не делать — накопительный режим (текущая стратегия).
- Очищать вручную через UI PMForesight.
- Запросить у администраторов MCP права на удаление `DocumentFile`.

### Частые ошибки probe (из live-сессии 2026-09-15)

| Симптом | Причина | Как обойти |
|---|---|---|
| `find_entity` по запросу «Документ» возвращает только `Point` | `find_entity` не фильтрует по типу сущности, ищет по `name` глобально | Использовать `get_view("Document", "DocumentView")` для категорий |
| `list_files` падает «Параметр 'documentId' обязателен» | Забыли `documentId` или передали 0 вместо реального ID | Передать реальный `DocumentId` из шага 1 |
| `get_view("DocumentFileViewAll")` возвращает документы контрактов, не проекта | View не поддерживает фильтр `ProjectId` | Использовать `list_files` с `className="Project"` |
| `upload_entity_file` → "уже существует" | Имя файла коллидирует с чужим | Добавить timestamp в секундах в имя (мы так делаем) |
| MCP не возвращает `data` при ошибке | Сервер отдаёт `_error` в `result.content[0].text` | Распарсить `result["_error"]`, не падать с KeyError |

### Минимальный sanity-check перед первым боевым запуском

1. **Probe** (один раз) — загрузить тестовый файл 200 байт в `DocumentId=70139`,
   проверить через `list_files` что он появился. **Не пытаться удалить**
   (прав нет).
2. **Dry-run** нашего скрипта — `python3 scripts/run_snapshot.py --dry-run` —
   файл НЕ загружается, только локальная копия в `outputs/`.
3. **Один проект** в боевом режиме — `python3 scripts/run_snapshot.py --code 504-595`.
4. **Все четыре** — `python3 scripts/run_snapshot.py`.

---

## 📊 Хронометраж боевого прогона (2026-09-23, ориентир)

Прогон по **4 проектам** в режиме `--no-cache` (HTML обычно отключается
через `--no-html` в этом скилле — эмпирически подтверждено, что без
HTML скилл **в 2–4 раза быстрее**, чем с ним):

| Этап | 504-595 | 503-152 | 503-434 | 504-314 |
|---|---:|---:|---:|---:|
| `find_project_id` (MCP) | ~0.5 с | ~0.5 с | ~0.5 с | ~0.5 с |
| `subprocess fst-project-health` | **~22 с** | **~52 с** ⚠ | **~22 с** | **~22 с** |
| Парсинг MD (встроенный) | <0.1 с | <0.1 с | <0.1 с | <0.1 с |
| Обёртка в snapshot + сохранение локально | <0.1 с | <0.1 с | <0.1 с | <0.1 с |
| Загрузка в MCP (`upload_entity_file`) | **~1 с** | **~1–2 с** | **~1 с** | **~1 с** |
| **ИТОГО на проект** | **~24 с** | **~55 с** | **~24 с** | **~24 с** |

**Сводка:**
- 4 проекта, 4 ok, 0 fail.
- Суммарное время: **~2,5 минуты** (на типичных проектах).
- Инициализация MCP: ~0.5 с (одна на все 4 проекта).
- Проекты с >1000 КТ (как 503-152) — самые тяжёлые (~52 с).

### Наблюдения

- **Большая часть времени** (~95–97 %) — `subprocess.run_all.py` (потому
  что `run_all.py` сам делает много MCP-вызовов). Это неэффективно,
  но правильно: мы **не трогаем** `fst-project-health`.
- **Загрузка в MCP** стабильно ~1 сек на файл — приемлемо.
- **Парсинг MD** теперь встроен — вызов `parse_md_to_data`
  из `fst-project-health-word` больше не нужен, что устранило ещё одну
  сетевую/файловую зависимость.

## 📚 История

Версии семейства `fst-project-health-*` ведутся в общем [CHANGELOG.md](../fst-project-health/CHANGELOG.md).

- **v1.0.19** (2026-09-23) — синхронизация с семейством:
  - снята зависимость от `fst-project-health-word` для парсинга MD —
    парсер встроен в этот скилл;
  - добавлено поле `snapshot_timestamp` в JSON-meta (копия из YAML
    front-matter MD);
  - версии подняты до `1.0.19`;
  - `--generator fst-project-health-snapshot` передаётся в subprocess.
- **v1.0.0** (2026-09-15) — первый релиз. 4 проекта, накопительный режим,
  категория «Документы ИИ» (DocumentId=70139).

---

*См. также: `fst-project-health` (зависимость), `fst-project-health-snap-md` (MD-аналог),
`fst-project-health-word` (генератор DOCX, опционально), `fst-mcp-tester` (read-only тесты MCP).*