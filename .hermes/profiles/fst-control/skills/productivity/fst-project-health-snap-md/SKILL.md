---
name: fst-project-health-snap-md
version: 1.0.19
description: "Сохранение MD-слепков состояния проектов в карточки MCP (категория 'Документы ИИ'). Переиспользует логику fst-project-health без модификации. **v1.0.19:** never-fail (каждый проект в try/except/continue); `--codes X Y Z` для массовых прогонов; обязательное логирование в logs/<ISO-timestamp>.log (header: дата, аккаунт из JWT, роль из MCP / n/a, списки проектов; body: ✓/✗ + type+message на каждую ошибку; trailer в finally). Для исторического HTML-отчёта за прошлую дату."
tags: [snapshot, mcp, pmpractice, ru, foresight, project-health, md, historical, scheduled]
---

# fst-project-health-snap-md

## When to load

- Пользователь просит «сохранить слепки MD», «обновить снимки», «сделать
  исторические снимки», «снапшоты в формате MD».
- Нужно сохранять **MD-отчёты** в карточках проектов, чтобы потом
  построить HTML «как тогда выглядел проект».
- **Отличие от `fst-project-health-snapshot`:** этот скилл кладёт **MD**,
  а тот — **JSON** (для построителя трендов).

## CRITICAL: read-and-write на MCP

В отличие от `fst-mcp-tester` (read-only), этот скилл **записывает**
MD-документы в карточку проекта через `mcp__fst_pmpractice__upload_entity_file`.

**Запрещено:**
- ❌ Модифицировать скилл `fst-project-health` (используется как зависимость).
- ❌ Загружать файл в другие категории документов (только "Документы ИИ").
- ❌ Удалять старые слепки (нет прав у токена на удаление DocumentFile — by design).

## Quick reference

- **Главный скрипт:** `scripts/run_snap_md.py`
- **Запуск:** `python3 scripts/run_snap_md.py` (по всем 4 проектам)
- **Один проект:** `python3 scripts/run_snap_md.py --code 504-595`
- **Dry-run (без MCP):** `python3 scripts/run_snap_md.py --dry-run`
- **Документ-категория:** `DocumentId=70139` (Документы ИИ)

## Что делает

Для каждого проекта из списка:

1. **Запускает `fst-project-health/scripts/run_all.py --code <code>`
   через subprocess.** Это **не модифицирует** основной скилл — просто
   запускает его как внешнюю программу. Получает
   `/tmp/project_<code>_report.md`.

2. **Сохраняет локальную копию MD** в `outputs/<code>_<timestamp>.md`.

3. **Загружает в MCP** через `mcp__fst_pmpractice__upload_entity_file`:
   - `entityName="Project"`, `dataId=<project_id>`
   - `documentId=70139` (категория "Документы ИИ")
   - `uploadedFileName="Слепок fst-project-health-snapshot-<project_code>-<timestamp>.MD"`

## Конвенция имён файлов

```
Слепок fst-project-health-snapshot-<project_code>-YYYY-MM-DD_HH-MM-SS.MD
```

- Префикс `Слепок fst-project-health-snapshot-` однозначно отделяет наши
  слепки от других документов на вкладке «Документы ИИ».
- Код проекта (`<project_code>`) включён для удобства группировки в UI.
- Timestamp с секундами.
- Расширение `.MD` (заглавными) — как принято в PMForesight.

## Список проектов по умолчанию

4 проекта:
- `504-595`
- `503-152`
- `503-434`
- `504-314`

Хранится в `DEFAULT_PROJECTS` в скрипте.

## Накопительный режим

Каждый прогон создаёт **новый MD-файл** с уникальным timestamp.
Старые **не удаляются**. Это даёт историю для построения
**исторических HTML-отчётов** за прошлую дату.

**Очистка старых слепков** — только вручную через UI PMForesight.

## Расписание

Запускается по cron раз в неделю ночью. Например:
```cron
0 3 * * 0 cd /opt/skills/fst-project-health-snap-md && python3 scripts/run_snap_md.py
```

## Portable setup

```bash
# 1. Скопировать каталог + зависимый fst-project-health
scp -r fst-project-health/      user@server:/opt/skills/
scp -r fst-project-health-snap-md/ user@server:/opt/skills/

# 2. Зависимости
cd /opt/skills/fst-project-health-snap-md
pip install -r requirements.txt

# 3. .env
cp .env.example .env
nano .env  # PMP_TOKEN=<jwt-токен>

# 4. Готово
python3 scripts/run_snap_md.py --dry-run
python3 scripts/run_snap_md.py
```

## Что НЕ делает

- ❌ Не строит HTML (только MD).
- ❌ Не строит WORD.
- ❌ Не удаляет старые слепки.
- ❌ Не модифицирует `fst-project-health`.
- ❌ Не парсит MD (это делает будущий `fst-project-health-from-md`).

## Связь с другими скиллами

```
fst-project-health-snap-md (этот)
   │
   ├─→ fst-project-health (для сбора MD через subprocess)
   │
   ├─→ PMForesight MCP (для find_project + upload_entity_file)
   │
   └─→ outputs/ (локальные копии для отладки)
```

`fst-project-health-from-md` (в будущем) — будет читать эти MD-файлы
из карточек и строить HTML «за прошлую дату».

`fst-project-health-snapshot` — кладёт **JSON**, этот — **MD**. Они
дополняют друг друга: JSON для построителя трендов, MD для исторического
HTML.

## История

Версии семейства `fst-project-health-*` ведутся в общем [CHANGELOG.md](../fst-project-health/CHANGELOG.md).

- **v1.0.19** (2026-09-23) — см. CHANGELOG семейства (MD = full source of truth).
- **v1.0.0** (2026-09-21) — первый релиз.

---

*См. также: `fst-project-health` (зависимость), `fst-project-health-snapshot`
(JSON-аналог), `fst-mcp-tester` (read-only тесты MCP).*