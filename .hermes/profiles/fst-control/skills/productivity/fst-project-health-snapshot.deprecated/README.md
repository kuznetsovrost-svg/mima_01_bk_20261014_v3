# fst-project-health-snapshot

Скилл для **периодического сбора JSON-слепков** состояния проектов
из PMForesight и загрузки их в карточки проектов (категория
"Документы ИИ") для дальнейшего построения трендовых отчётов.

## Что делает

Для каждого проекта из списка:

1. Запускает `fst-project-health/scripts/run_all.py` через subprocess
   **с флагом `--generator fst-project-health-snapshot`** — этот
   скилл передаёт своё имя как генератор, и оно пишется в YAML
   front-matter (`generator: "fst-project-health-snapshot"`) в
   собранном MD. Это нужно для атрибуции: читатель JSON-снапшота
   видит, откуда данные (см. CHANGELOG семейства).
2. Парсит MD **собственным** `parse_md_to_data` (внутри
   `scripts/run_snapshot.py`). С v1.0.19 парсинг MD встроен в
   `fst-project-health-snapshot`, **зависимость от
   `fst-project-health-word` больше не нужна** (см. CHANGELOG семейства,
   секцию v1.0.19).
3. Оборачивает в JSON с `_meta.generator = "fst-project-health-snapshot"`
   и `_meta.generator_version = "1.0.19"`.
4. Загружает в карточку проекта через `mcp__fst_pmpractice__upload_entity_file`
   в категорию **"Документы ИИ"** (DocumentId=70139).

> **Примечание.** Поле `produced_at` в JSON-метаданных — это
> timestamp генерации JSON-снапшота (этого скрипта), а **не** момент
> самих данных. Для исторического среза данных используйте поле
> `snapshot_timestamp` в YAML front-matter **исходного MD**
> (которое `rebuild_report.py` пишет в `fst-project-health`).
> См. CHANGELOG семейства, раздел «Архитектурные инварианты».

## Установка

### Быстрая установка (локальный путь по умолчанию)

```bash
# 1. Зависимости
pip install -r requirements.txt

# 2. .env
cp .env.example .env
nano .env  # PMP_TOKEN=<jwt-токен PMForesight>

# 3. Должен быть установлен соседний скилл:
#    - fst-project-health (для сбора MD через subprocess).
#    ~~fst-project-health-word НЕ нужен с v1.0.19 — парсинг MD встроен.

# 4. Dry-run
python3 scripts/run_snapshot.py --dry-run

# 5. Боевой прогон
python3 scripts/run_snapshot.py
```

### Установка на другом сервере

```bash
# 1. Скопировать 2 скилла:
#    - fst-project-health (зависимость — для сбора MD)
#    - fst-project-health-snapshot (этот скилл)
#    ~~fst-project-health-word НЕ копировать — больше не нужен.~~
scp -r fst-project-health/      user@server:/opt/skills/
scp -r fst-project-health-snapshot/ user@server:/opt/skills/

# 2. Зависимости (один раз на сервере)
cd /opt/skills/fst-project-health-snapshot
pip install -r requirements.txt   # requests
# (если нужен DOCX-отчёт отдельно: см. fst-project-health-word)

# 3. Настроить .env с ПРАВИЛЬНЫМИ путями на этом сервере
cd /opt/skills/fst-project-health-snapshot
cp .env.example .env
nano .env
```

В `.env` для другого сервера обязательно укажите:

```bash
PMP_TOKEN=<jwt-токен>

# Путь к зависимому скиллу fst-project-health (если НЕ /root/.hermes/...):
FST_PROJECT_HEALTH_PATH=/opt/skills/fst-project-health
# FST_PROJECT_HEALTH_WORD_PATH больше НЕ нужен (см. CHANGELOG семейства v1.0.19).

# Если URL MCP другой (например, staging):
# MCP_URL=https://staging.example.com/mcp
```

**Переменные окружения** (все опциональные, есть разумные дефолты):

| Env | Назначение | По умолчанию |
|---|---|---|
| `PMP_TOKEN` | JWT-токен PMForesight | (обязательно) |
| `FST_PROJECT_HEALTH_PATH` | Путь к скиллу fst-project-health | `/root/.hermes/profiles/fst-control/skills/productivity/fst-project-health` |
| `MCP_URL` | URL MCP-сервера | `https://ppreplica.hera.pmpractice.ru/mcp` |

> **`FST_PROJECT_HEALTH_WORD_PATH`** — устаревшая переменная, **удалена**
> в v1.0.19. Парсинг MD встроен в этот скилл.

## Использование

```bash
# Полный прогон по всем 4 проектам
python3 scripts/run_snapshot.py

# Один проект
python3 scripts/run_snapshot.py --code 504-595

# Dry-run (без загрузки в MCP — только локально)
python3 scripts/run_snapshot.py --dry-run

# Dry-run + один проект
python3 scripts/run_snapshot.py --code 504-595 --dry-run
```

## Имена файлов

Формат: `Слепок fst-project-health-snapshot-<project_code>-YYYY-MM-DD_HH-MM-SS.JSON`

Пример: `Слепок fst-project-health-snapshot-504-595-2026-09-15_16-30-45.JSON`

## Структура JSON

```json
{
  "_meta": {
    "schema_version": "1.0.0",
    "generator": "fst-project-health-snapshot",
    "generator_version": "1.0.19",
    "produced_at": "2026-09-23T22:00:00+03:00",
    "snapshot_kind": "fst-project-health-snapshot",
    "snapshot_timestamp": "2026-09-23 21:55:00",  // v1.0.19: копия из YAML front-matter MD
    "source_skill": "fst-project-health",
    "source_skill_version": "1.0.19",
    "project_code": "504-595",
    "project_id": 4595
  },
  "snapshot_kind": "fst-project-health-snapshot",
  "produced_at": "2026-09-23T22:00:00+03:00",
  "snapshot_timestamp": "2026-09-23 21:55:00",  // удобство: дублируем в корень
  "source_skill": "fst-project-health",
  "source_skill_version": "1.0.19",
  "source_generator": "fst-project-health",
  "source_generator_version": "1.0.19",  // синхронизировано с семейством
  "verdict": "Болен",  // "Здоров" / "Требует внимания" / "Болен"
  "section_3": {...},
  "section_4": {...}
  // ... остальные секции
}
```

**Ключевые поля v1.0.19:**
- `snapshot_timestamp` — **новое**, копируется из YAML front-matter
  исходного MD. Это **историческое** время данных (а не `produced_at`,
  которое — момент генерации JSON-обёртки).
- `verdict` теперь может быть «Болен» (не только «Здоров»/«Требует
  внимания») — потому что в v1.0.19 добавили раздел 6 «Показатели
  проекта», вердикт которых «Критическое» приравнивается к «Болен»
  для сводного вердикта.

**Что НЕ в JSON:**
- Сырой MD (для этого есть `fst-project-health-snap-md`).
- Подробная HTML-разметка (для рендера используйте
  `build_html_report.py --md <MD>`).

## Список проектов

4 проекта по умолчанию (`DEFAULT_PROJECTS` в скрипте):
- `504-595`
- `503-152`
- `503-434`
- `504-314`

Изменить — отредактировать `DEFAULT_PROJECTS` в `scripts/run_snapshot.py`.

## Расписание

Рекомендуется cron раз в неделю ночью. Например:
```cron
# Каждое воскресенье в 03:00 MSK
0 3 * * 0 cd /opt/skills/fst-project-health-snapshot && python3 scripts/run_snapshot.py >> logs/snapshot.log 2>&1
```

Внутри Hermes — через `cronjob_manage`:
```
job_id: snapshot-weekly-nightly
schedule: 0 3 * * 0
prompt: Запусти python3 ~/.hermes/profiles/fst-control/skills/productivity/fst-project-health-snapshot/scripts/run_snapshot.py
```

## Накопительный режим

Каждый прогон создаёт **новый файл** с уникальным timestamp. Старые
**не удаляются** — это история для построителя трендов.

## Локальные копии

В `outputs/` сохраняется копия каждого JSON для отладки:
`outputs/<project_code>_<timestamp>.json`

## Структура каталога

```
fst-project-health-snapshot/
├── SKILL.md                # описание скилла
├── README.md               # этот файл
├── .env.example            # шаблон токена
├── requirements.txt        # requests
├── scripts/
│   └── run_snapshot.py     # главный скрипт
└── outputs/                # локальные копии JSON-слепков
```

## История

Версии семейства `fst-project-health-*` ведутся в общем [CHANGELOG.md](../fst-project-health/CHANGELOG.md).

- **v1.0.19** (2026-09-23) — синхронизация с семейством (код не менялся
  функционально): снята зависимость от `fst-project-health-word`
  для парсинга, добавлено поле `snapshot_timestamp` в JSON-meta,
  версии подняты до `1.0.19`.
- **v1.0.0** (2026-09-15) — первый релиз.

---

*См. также: `fst-project-health` (зависимость), `fst-project-health-snap-md` (MD-аналог),
`fst-project-health-word` (генератор DOCX, опциональный), `fst-mcp-tester` (read-only тесты MCP).*