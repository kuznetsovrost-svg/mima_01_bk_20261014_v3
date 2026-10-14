---
name: fst-project-health-snapshot
version: 1.0.19
description: "DEPRECATED 2026-09-24. Используйте fst-project-health-snap-md для MD-слепков или fst-project-health-from-md-snapshot для их чтения. См. DEPRECATED.md в этом каталоге."
tags: [snapshot, mcp, pmpractice, ru, foresight, project-health, trends, json, scheduled, deprecated]
---

# fst-project-health-snapshot

## When to load

- Пользователь просит «собрать слепки», «обновить снимки», «прогнать снепшоты»,
  «сделать снапшоты по списку проектов».
- Нужно **периодически** собирать состояние проектов для дальнейшего
  построения трендовых отчётов.
- Работает в связке с **построителем трендов** — этот скилл собирает
  данные, построитель — анализирует.

## CRITICAL: read-and-write на MCP

В отличие от `fst-mcp-tester` (read-only), этот скилл **записывает**
JSON-документы в карточку проекта через `mcp__fst_pmpractice__upload_entity_file`.

**Запрещено:**
- ❌ Модифицировать скилл `fst-project-health` (используется как зависимость).
- ❌ Загружать файл в другие категории документов (только "Документы ИИ").
- ❌ Удалять старые слепки (нет прав у токена на удаление DocumentFile — это by design).

## Quick reference

- **Главный скрипт:** `scripts/run_snapshot.py`
- **Запуск:** `python3 scripts/run_snapshot.py` (по всем 4 проектам)
- **Один проект:** `python3 scripts/run_snapshot.py --code 504-595`
- **Dry-run (без MCP):** `python3 scripts/run_snapshot.py --dry-run`
- **Документ-категория:** `DocumentId=70139` (Документы ИИ)
- **Список проектов:** `DEFAULT_PROJECTS` в `scripts/run_snapshot.py`

## Что делает

Для каждого проекта из списка:

1. **Запускает `fst-project-health/scripts/run_all.py --code <code>
   --generator fst-project-health-snapshot` через subprocess.** Это
   **не модифицирует** основной скилл — просто запускает его как
   внешнюю программу. Получает `/tmp/project_<code>_report.md`.
   Флаг `--generator` записывает атрибуцию в YAML front-matter MD.

2. **Парсит MD** встроенным `parse_md_to_data` (скопирован и
   синхронизирован с `fst-project-health/build_html_report.py`,
   v1.0.19). **Зависимость от `fst-project-health-word` снята** —
   парсер MD полностью внутри этого скилла.

3. **Оборачивает в JSON-snapshot** с `_meta`:
   ```json
   {
     "_meta": {
       "schema_version": "1.0.0",
       "generator": "fst-project-health-snapshot",
       "generator_version": "1.0.0",
       "produced_at": "2026-09-15T16:30:00+03:00",
       "snapshot_kind": "fst-project-health-snapshot",
       "project_code": "504-595",
       "project_id": 4595
     },
     "snapshot_kind": "fst-project-health-snapshot",
     ...
   }
   ```

4. **Сохраняет локальную копию** в `outputs/<code>_<timestamp>.json` для отладки.

5. **Загружает в MCP** через `mcp__fst_pmpractice__upload_entity_file`:
   - `entityName="Project"`, `dataId=<project_id>`
   - `documentId=70139` (категория "Документы ИИ")
   - `uploadedFileName="Слепок fst-project-health-snapshot-<project_code>-YYYY-MM-DD_HH-MM-SS.JSON"`

## Конвенция имён файлов

**Префикс (для машинного отбора «свой vs чужой»):**
```
Слепок fst-project-health-snapshot-<project_code>-YYYY-MM-DD_HH-MM-SS.JSON
```

- Префикс `Слепок fst-project-health-snapshot-` — однозначно отделяет от других
  документов на вкладке «Документы ИИ».
- Timestamp с секундами (по требованию пользователя).
- В JSON дополнительно — `_meta.generator = "fst-project-health-snapshot"`
  как **второй уровень защиты** для фильтрации.

## Список проектов по умолчанию

4 проекта, по которым раньше строились отчёты:
- `504-595`
- `503-152`
- `503-434`
- `504-314`

Хранится в `DEFAULT_PROJECTS` (в скрипте). Можно переопределить через
env-vars или CLI `--code`.

## Накопительный режим

Каждый прогон создаёт **новый файл** с уникальным timestamp. Старые
**не удаляются** (нет прав у токена на удаление DocumentFile — by design
MCP). Это даёт историю для построителя трендов.

**Очистка старых слепков** — только вручную через UI PMForesight
(вкладка «Документы ИИ» проекта).

## Расписание

Запускается по **cron раз в неделю ночью**. Пример: воскресенье 03:00 MSK.

Внутри Hermes — через `cronjob_manage`. Внешний cron — через
`crontab -e` с командой:
```cron
0 3 * * 0 cd /opt/skills/fst-project-health-snapshot && python3 scripts/run_snapshot.py
```

## Portable setup

```bash
# 1. Скопировать каталог
scp -r fst-project-health-snapshot/ user@server:/opt/skills/

# 2. Зависимости
cd /opt/skills/fst-project-health-snapshot
pip install -r requirements.txt

# 3. .env
cp .env.example .env
nano .env  # вписать PMP_TOKEN

# 4. Зависимости от других скиллов
#    - fst-project-health (обязательно) — для сбора MD
#    - ~~fst-project-health-word НЕ нужен с v1.0.19 — parse_md_to_data встроен.~~
#    (если нужен DOCX-отчёт отдельно — см. fst-project-health-word как самостоятельный скилл)

# 5. Dry-run
python3 scripts/run_snapshot.py --dry-run

# 6. Боевой прогон
python3 scripts/run_snapshot.py
```

## Что НЕ делает

- ❌ Не строит HTML (отключено `--no-html`).
- ❌ Не строит WORD (не нужен — это сырые данные).
- ❌ Не удаляет старые слепки (нет прав).
- ❌ Не модифицирует `fst-project-health`.
- ❌ Не строит трендовые отчёты (это делает **построитель трендов**,
  отдельный скилл, ещё не создан).

## Связь с другими скиллами

```
fst-project-health-snapshot (этот)
   │
   ├─→ fst-project-health (для сбора MD через subprocess)
   │
   ├─→ (встроенный parse_md_to_data из fst-project-health/build_html_report.py, v1.0.19)
   │
   ├─→ PMForesight MCP (для find_project + upload_entity_file)
   │
   └─→ outputs/ (локальные копии для отладки)
```

**Построитель трендов** (в будущем) будет читать JSON-слепки из карточек
проектов (через `list_files` + фильтр по `_meta.generator`) и строить
трендовые отчёты.

**Подробнее** о механике загрузки (как найти `DocumentId` категории
«Документы ИИ», как работает `upload_entity_file`, почему нельзя
удалить через API) — в `playbook.md`, раздел **«MCP-write discovery»**.

## История

Версии семейства `fst-project-health-*` ведутся в общем [CHANGELOG.md](../fst-project-health/CHANGELOG.md).

- **v1.0.19** (2026-09-23) — синхронизация с семейством (MD = full source of truth).
- **v1.0.0** (2026-09-15) — первый релиз. Накопительный режим,
  4 проекта, документы в "Документы ИИ" (DocumentId=70139).

---

*См. также: `fst-project-health` (зависимость для сбора MD), `fst-project-health-snap-md` (MD-аналог),
`fst-project-health-word` (генератор DOCX, **опционально**), `fst-mcp-tester` (read-only тесты MCP).*
*Полный CHANGELOG семейства `fst-project-health-*` — [CHANGELOG.md](../fst-project-health/CHANGELOG.md).*