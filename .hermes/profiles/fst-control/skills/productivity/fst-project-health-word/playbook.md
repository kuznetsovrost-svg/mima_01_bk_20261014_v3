# PLAYBOOK — fst-project-health-word

**Версия скилла:** v1.0.20
**Дата PLAYBOOK:** 2026-09-24
**Назначение:** построение WORD-отчёта (Форма 1) из MD-файла, полученного из `fst-project-health` или `fst-project-health-from-md-snapshot`.

---

## 1. Общий обзор

`fst-project-health-word` — генератор **DOCX-отчёта** из MD-файла. Все таблицы раскрыты (нет `<details>`, как в HTML), строки подсвечены по severity.

```
MD (из live или snapshot) → build_word_report.py → DOCX (Форма 1)
```

**Версия MD:** v1.0.19 (нумерация 3–9, 16 показателей, индикатор).
**Формат вывода:** `.docx` (Microsoft Word / LibreOffice Writer).
**Время выполнения:** ~2 секунды (MD уже есть, MCP не нужен).

> В метаданных DOCX добавлена строка **«Источник»**:
> - «MCP (в реальном времени)» — для live-MD (`generator="fst-project-health"`).
> - «Слепок от YYYY-MM-DD HH:MM:SS» — для MD-из-MCP.

---

## 2. Генерация WORD: два сценария

### 2.1. WORD для «текущего отчёта» (live)

```bash
# 1. Генерируем live-MD
cd ~/.hermes/profiles/fst-control/skills/productivity/fst-project-health
python3 scripts/run_all.py --code 504-595 --no-cache
# Получаем: /tmp/project_504-595_report.md (с YAML front-matter, generator="fst-project-health")

# 2. Собираем DOCX
cd ~/.hermes/profiles/fst-control/skills/productivity/fst-project-health-word
python3 scripts/build_word_report.py \
    --md /tmp/project_504-595_report.md \
    --code 504-595 \
    --output /tmp/project_504-595_LIVE_форма1.docx
# В метаданных DOCX: «Источник: MCP (в реальном времени)»
```

### 2.2. WORD по слепку (из MCP)

**Одна команда** (пакетная — можно передать несколько кодов):

```bash
~/.hermes/profiles/fst-control/skills/productivity/fst-project-health-word/scripts/build_word_from_snapshot.sh 504-595 [503-152 ...]
```

Этот скрипт сам:
1. Скачивает MD из MCP через `fetch_snapshot.py --last`.
2. Собирает DOCX через `build_word_report.py`.
3. Кладёт результат в `/tmp/<CODE>_report_<timestamp>_WORD-форма1.docx`.

**Пошагово** (если нужен контроль над выбором слепка):

```bash
# 1. Скачиваем нужный снапшот (по умолчанию --last)
cd ~/.hermes/profiles/fst-control/skills/productivity/fst-project-health-from-md-snapshot
python3 scripts/fetch_snapshot.py --code 504-595 --last --no-log
# Получаем: ~/.hermes/profiles/fst-control/cache/snapshots/504-595_<timestamp>.md
# В YAML front-matter: generator="fst-project-health-snap-md", snapshot_timestamp="..."

# 2. Собираем DOCX
cd ~/.hermes/profiles/fst-control/skills/productivity/fst-project-health-word
python3 scripts/build_word_report.py \
    --md /root/.hermes/profiles/fst-control/cache/snapshots/504-595_2026-09-24_16-34-12.md \
    --code 504-595 \
    --output /tmp/project_504-595_SNAPSHOT_форма1.docx
# В метаданных DOCX: «Источник: Слепок от 2026-09-24 16:34:12»
```

---

## 3. API скилла

### 3.1. CLI-параметры `build_word_report.py`

```bash
python3 scripts/build_word_report.py --md <PATH> --code <CODE> [опции]
```

| Параметр | Обязательный | Описание |
|---|---|---|
| `--md <PATH>` | ✅ | Путь к MD-файлу (любой: live или snapshot). |
| `--code <PROJECT_CODE>` | ✅ | Код проекта (используется в имени выходного файла по умолчанию). |
| `--output <PATH>` | ❌ | Куда сохранить DOCX (по умолчанию `/tmp/project_<code>_report_WORD-форма1.docx`). |
| `--generator <NAME>` | ❌ | Переопределить генератор (по умолчанию читается из MD front-matter). |
| `--no-cache` | ❌ | Не использовать кэш парсинга. |

### 3.2. Программный импорт

```python
import sys
sys.path.insert(0, "~/.hermes/profiles/fst-control/skills/productivity/fst-project-health-word/scripts")
from build_word_report import parse_md_to_data, build_word_report_from_data

# Парсим MD в data-словарь
data = parse_md_to_data(Path("/path/to/report.md"))

# Строим DOCX в памяти
doc = build_word_report_from_data(data)
doc.save("/path/to/output.docx")
```

---

## 4. Скрипты скилла

| Скрипт | LOC | Размер | Назначение |
|---|---|---|---|
| `build_word_report.py` | 1155 | 55 KB | **Главный.** Парсит MD → DOCX через python-docx. |
| `build_word_from_snapshot.sh` | 46 | 1.7 KB | **Пакетная обёртка.** Цепочка `fetch_snapshot → build_word` для нескольких проектов одной командой. |

**Всего: 2 скрипта.** Главный — `build_word_report.py`.

---

## 5. Методы скилла (для переиспользования)

### 5.1. `build_word_report.py::main()`

- **Назначение:** CLI-точка входа.
- **Параметры:** см. раздел 3.1.

### 5.2. `build_word_report.py::parse_md_to_data()`

- **Назначение:** парсит MD в data-словарь.
- **Параметры:** `md_path: Path`.
- **Возвращает:** `dict` с полями `project_code`, `project_id`, `verdict`, `section_3` … `section_9`, `generator`, `snapshot_timestamp`, `summary_text`.
- **Когда переиспользовать:** когда нужно **программно** работать со структурой отчёта, не собирая DOCX.

### 5.3. `build_word_report.py::build_word_report_from_data()`

- **Назначение:** собирает DOCX из data-словаря.
- **Параметры:** `data: dict`.
- **Возвращает:** `Document` (python-docx).
- **Когда переиспользовать:** когда хотим **модифицировать** отчёт перед сохранением (например, добавить свой параграф).

### 5.4. `build_word_report.py::_parse_section()`

- **Назначение:** парсит одну секцию MD (с заданным числом колонок).
- **Параметры:** `sec_text: str`, `expected_cols: int`.
- **Когда переиспользовать:** в кастомных скриптах для парсинга отдельной таблицы.

### 5.5. `build_word_report.py::_parse_indicators_from_md()`

- **Назначение:** парсит 16 показателей из раздела 6 MD (включая вложенные таблицы `### 6.N`).
- **Параметры:** `sec_text: str`.
- **Когда переиспользовать:** когда нужны **только** показатели (без остальных разделов).

### 5.6. `build_word_from_snapshot.sh`

- **Назначение:** bash-обёртка для цепочки `fetch_snapshot.py + build_word_report.py`.
- **Параметры:** коды проектов через пробел.
- **Когда переиспользовать:** для **массовой** генерации DOCX из снапшотов.

---

## 6. Структура DOCX (что внутри)

```
┌─────────────────────────────────────────────────────┐
│ Отчёт о здоровье проекта «...»                       │
│ Дата формирования: 2026-09-24 17:31                   │
│ Источник: MCP (в реальном времени) / Слепок от …      │
│ MCP: PMForesight MCP v3.2.4                           │
│ Scope: полный отчёт по проекту (разделы 3-9)          │
├─────────────────────────────────────────────────────┤
│ Общий вердикт: БОЛЕН                                  │
├─────────────────────────────────────────────────────┤
│ 3. Оценка здоровья с точки зрения сроков             │
│ 4. Проверка полноты заполнения                        │
│ 5. Актуальность прогнозов                            │
│ 6. Показатели проекта (16 индикаторов)               │
│    6.3 Прогнозы по ресурсам заданы                   │
│    6.4 Плановые трудозатраты заданы                   │
│    6.6, 6.7, 6.8, 6.15, 6.16 …                        │
│ 7. Финансовый статус проекта                         │
│ 8. Технические данные отчёта                         │
│ 9. Индикатор (общий вердикт)                         │
│ Сводка по отчёту в целом                              │
└─────────────────────────────────────────────────────┘
```

Все таблицы **раскрыты** (нет `<details>`, как в HTML — DOCX не интерактивен).

---

## 7. Прецеденты

| Сценарий | Время | Размер DOCX |
|---|---|---|
| live (`/tmp/project_504-595_report.md`) | ~2 сек | ~45 KB |
| snapshot (`cache/snapshots/504-595_*.md`) | ~2 сек | ~45 KB |
| пакетная сборка по 4 проектам | ~10 сек | ~180 KB (4 файла) |

---

## 8. Где скилл лежит

```
~/.hermes/profiles/fst-control/skills/productivity/fst-project-health-word/
├── SKILL.md
├── README.md
├── CHANGELOG.md            ← v1.0.0 → v1.0.20
├── scripts/
│   ├── build_word_report.py
│   └── build_word_from_snapshot.sh
├── templates/              ← заготовки (пока не используются)
├── references/             ← word-playbook (старая версия)
└── requirements.txt        ← python-docx>=1.0.0
```
