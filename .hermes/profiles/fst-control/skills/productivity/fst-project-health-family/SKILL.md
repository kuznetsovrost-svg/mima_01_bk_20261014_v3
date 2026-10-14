---
name: fst-project-health-family
version: 1.0.21
description: "fst-project-health-* family architecture and sync rules."
tags: [pmpractice, foresight, project-health, family, architecture, ru, v1.0.21]
---

# fst-project-health-family

## When to load

- Любой запрос про «отчёт по проекту», «здоровье проекта», «WORD/HTML по
  проекту 504-595», «слепок из MCP», «тренд по проекту».
- Когда меняешь нумерацию/структуру разделов MD и нужно проверить, что
  все рендереры (HTML, DOCX) и парсеры остались синхронизированы.
- Когда нужно выбрать правильный скилл для запроса пользователя и
  собрать кросс-скилловую цепочку.

## Состав семейства

| Скилл | Роль | Вход | Выход |
|---|---|---|---|
| `fst-project-health` (v1.0.19) | **live** отчёт | MCP (HTTP) | MD + HTML |
| `fst-project-health-snapshot.deprecated/` | — (DEPRECATED 2026-09-24) | — | — |
| `fst-project-health-snap-md` (v1.0.19) | исторический **MD-слепок** | MCP | MD в карточке MCP |
| `fst-project-health-from-md-snapshot` (v1.0.19) | рендер из MD-слепка | MD из MCP | HTML |
| `fst-project-health-word` (v1.0.20) | рендер из MD | MD | DOCX (Форма 1) |
| `fst-project-health-tests` (v1.0.19) | регрессия + MCP round-trip | — | отчёт тестов |
| `fst-project-health-from-json.deprecated/` | — (DEPRECATED 2026-09-24) | — | — |

**Источник истины — MD** (с YAML-front-matter, `generator`, `snapshot_timestamp`).
HTML и DOCX — это рендеры MD. JSON-snapshot — устаревший, остался для совместимости.

## Кросс-скилловые workflow

### 1. Live-отчёт (сейчас)

```
MCP → run_all.py → /tmp/project_<CODE>_report.md → build_html_report.py → /tmp/project_<CODE>_report.html
```

Триггер: «отчёт по 504-595», «HTML по проекту», «сейчас», «now».
Поле `generator="fst-project-health"` в YAML → **НЕТ** строки «Слепок от:» в HTML.

### 2. MD-слепок (для истории)

```
MCP → snap-md run_snap_md.py --code X → MD загружается в DocumentId=70139
                                       в карточке проекта
```

Триггер: «сохрани слепок», «сделай MD-слепок», «положи в карточку проекта».
Файл попадает в раздел «Документы ИИ» карточки проекта с префиксом
`<CODE>_<YYYY-MM-DD>_<HH-MM-SS>.md`.

### 3. Рендер HTML по MD-слепку

```
fetch_snapshot.py --code X --last        → ~/.hermes/profiles/fst-control/cache/snapshots/<CODE>_<timestamp>.md
build_html.py --md <MD>                   → HTML (с «Слепок от: <timestamp>»)
```

Триггер: «построй HTML по слепку», «исторический отчёт за дату».
Поле `generator="fst-project-health-snap-md"` или `-from-md-snapshot` →
**ЕСТЬ** строка «Слепок от:» в HTML.

### 4. Рендер DOCX по MD-слепку ⭐ v1.0.20+

```
fetch_snapshot.py --code X --last → MD
build_word_report.py --md <MD> --code X → DOCX
```

Или одной командой (несколько проектов):
`build_word_from_snapshot.sh 504-595 503-152 503-434`.

Триггер: «сделай WORD по снимку из MCP», «DOCX за прошлую дату».

**Маркер источника в DOCX:** метаданные `Источник: ...` строятся из
YAML front-matter MD:
- `generator=fst-project-health` (live) → `MCP (в реальном времени)`.
- Любой другой `generator` + `snapshot_timestamp` → `Слепок от <timestamp>`.
- Snapshot без `snapshot_timestamp` → `Слепок из MCP (timestamp не указан)`.

### 5. Тренд (несколько снимков)

```
fetch_snapshot.py --list --code X          → список всех снимков
fetch_snapshot.py --code X --exact TIMESTAMP → нужный снимок
… повторить для каждой даты
build_html_report.py --md <MD> ×N           → HTML за каждую дату
```

### 6. Регрессия

```
fst-project-health-tests/run_all_tests.py [--group GROUP] [--project CODE]
```

Группы: regression, mcp, snap_md, from_md, cross_skill, invariants.
MCP-тесты **включены по умолчанию** (по решению пользователя).
Тестовый проект — в `tests/test_project.py` (НЕ хардкодить).

## Структура MD (v1.0.19) — общая для всех рендереров

| № | Раздел | Колонок в pipe-table |
|---|---|---|
| 3 | Оценка здоровья (сроки) | 8/9 |
| 4 | Полнота заполнения | 5 |
| 5 | Актуальность прогнозов | 8/9 |
| **6** | **Показатели проекта (16)** | 4 + 16 вложенных `### 6.N` |
| 7 | Финансовый статус | 4 |
| 8 | Технические данные | 3 |
| 9 | Индикатор (общий вердикт) | 3 |
| — | Сводка по отчёту (без номера) | текст |

**Любой рендерер (HTML/DOCX) и любой парсер должны знать эту нумерацию.**
При изменении структуры MD — синхронизировать ВСЕ три места:

- `fst-project-health/scripts/build_html_report.py` (`_parse_indicators_from_md`)
- `fst-project-health/scripts/rebuild_report.py` (генерация секций)
- `fst-project-health-word/scripts/build_word_report.py` (`parse_md_to_data` + `build_word_report_from_data`)

## Pitfalls

### Синхронизация рендереров и парсеров

- **Если меняешь нумерацию разделов в MD — обнови ОБЯЗАТЕЛЬНО три файла**:
  `rebuild_report.py`, `build_html_report.py`, `build_word_report.py`.
  Иначе один рендерер будет показывать «6. Финансы», а другой — «6. Показатели».
  Сверяйся через `grep -n "^## " /tmp/project_504-595_report.md`.

- **Вложенные таблицы 6.N в WORD рендерятся раскрытыми** — DOCX не
  поддерживает интерактивность, поэтому `<details>` превращается в плоскую
  секцию `### 6.N` + таблица. Это требование пользователя: «WORD для
  человека — все данные видны».

### YAML-front-matter (snapshot_timestamp)

- Поле `snapshot_timestamp` пишется ТОЛЬКО для snapshot-генераторов:
  `fst-project-health-snap-md`, `fst-project-health-from-md-snapshot`.
  (`fst-project-health-snapshot` — DEPRECATED 2026-09-24, не использовать.)
- Для live (`fst-project-health`) поле НЕ пишется → в HTML НЕТ «Слепок от:».
- Это инвариант — не путать пользователя «живой» отчёт со «слепком».
- **Любой рендерер (HTML, DOCX) ОБЯЗАН парсить YAML front-matter** и выводить
  маркер источника: live → «MCP (в реальном времени)», snapshot →
  «Слепок от <snapshot_timestamp>». Если MD без front-matter (например,
  ручной дамп) — fallback: «Слепок из MCP (timestamp не указан)».
- **Парсить YAML regex'ом**, не через `yaml.safe_load`: проще, не тянет
  зависимость, устойчиво к кавычкам/лишним пробелам в значениях
  (`generator:\s*['"]?([^'"\n]+)['"]?`).

### Round-trip через MCP

- `upload_entity_file` (snap-md) → `list_files` → `resources/read file://download-file/{physicalFileId}`
  возвращает байт-в-байт (sha256 identical).
- **НО `download_md` иногда возвращает `result: {}`** — нужен retry с новой
  MCP-сессией (3 попытки). Это **transient**, не реальный сбой.
- После всех 3 попыток — `return 1`, не 0. Это влияет на логи `run_all.py`
  и `fetch_snapshot.py`.

### Логирование

- **Логи в `snap-md` и `from-md-snapshot`** — header (дата, JWT-аккаунт, роль
  MCP/n/a, списки проектов) → body (✓/✗ + type+http_code+message) →
  trailer в `finally:`.
- **`fetch_snapshot.py` сейчас печатает «0/1 ok» в ИТОГ** когда MD скачан,
  но счётчик не инкрементируется. Известный баг (фикс планируется).
  Файл при этом есть и валидный — **доверяй наличию файла**, а не счётчику.
- **Тесты (`fst-project-health-tests`)** — политика ротации **100 дней archive,
  400 дней delete** (НЕ 30/180 как у остальных).
- **`tests/` в каждом скилле** — НЕ имеют собственного логирования
  (по решению пользователя: «кому нужен лог — пусть запускает отдельный скилл
  тестирования»).

### Массовые вызовы

- `--codes X Y Z` в `run_snap_md.py` и `fetch_snapshot.py`.
- **Никогда не падать на середине**: проект не существует / нет доступа /
  опечатка в коде → запись в лог + переход к следующему.
- Принцип: «скрипт может — делает. Не может, пишет в лог, на середине
  никогда не останавливается и не падает».

### Bash-обёртки вокруг Python-скриптов

- В `.sh` скриптах вызывать Python-скрипты **только через явный
  интерпретатор**: `python3 path/to/script.py`, даже если файл
  помечен `chmod +x`. Без интерпретатора — `Permission denied`,
  потому что `#!/usr/bin/env python3` shebang читается только при
  exec-вызове ядром ОС, а bash-форк через `${VAR}` запускается без
  exec.
- Оборачивать вызовы Python-скриптов в `${VAR}/scripts/foo.py` —
  только после проверки, что `VAR` указывает на каталог скилла, а
  не на что-то левое (теряется при копировании скрипта без env).

### Dict-литералы с дублирующимися ключами

- Python dict-литерал `{4: ["A"], 4: ["B"]}` **молча** оставляет
  последнее значение. Если хочешь один и тот же ключ для разных
  разделов — заводи отдельный ключ под каждый раздел
  (`SECTIONS[6]`, `SECTIONS[7]`), либо комментарий-предупреждение
  в исходнике, иначе парсер/рендерер ниже возьмёт неожиданный
  список колонок.

## Что НЕ входит в семейство

- ❌ Любые изменения данных PMForesight (read-only на бэкенде).
- ❌ Загрузка документов в другие категории кроме «Документы ИИ»
  (DocumentId=70139).
- ❌ Рендер чего-либо кроме HTML/DOCX/MD.

## История и ссылки

- Общий CHANGELOG семейства — в `fst-project-health/CHANGELOG.md`.
- Контрольные точки для отката — `/tmp/fst-skills-*.tar.gz`.
- Зависимости между скиллами — в их собственных SKILL.md → секция
  «Связь с ...».
