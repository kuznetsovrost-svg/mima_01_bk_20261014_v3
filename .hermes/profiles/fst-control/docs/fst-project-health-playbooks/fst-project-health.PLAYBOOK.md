# PLAYBOOK — fst-project-health

**Версия скилла:** v1.0.19
**Дата PLAYBOOK:** 2026-09-24
**Назначение:** построение «живого» HTML-отчёта о здоровье проекта по текущим данным PMForesight MCP.

---

## 1. Общий обзор

`fst-project-health` — **головной** скилл семейства. Делает **live-отчёт** (по данным MCP прямо сейчас) в формате HTML:

```
MCP (сейчас) → run_all.py → MD (промежуточный) → build_html_report.py → HTML
```

**Источник данных:** только MCP в реальном времени (без кэширования результатов между вызовами).
**Формат вывода:** HTML (открывается в браузере, отправляется в Telegram как файл).
**Время выполнения:** ~25–60 секунд на проект (зависит от нагрузки MCP и объёма проекта).

> В отчёте **НЕТ** строки «Слепок от:» — это признак того, что отчёт построен **по живым данным**, а не по сохранённому ранее слепку.

---

## 2. API скилла

### 2.1. CLI-параметры

```bash
python3 scripts/run_all.py --code <project_code> [опции]
```

| Параметр | Обязательный | Описание |
|---|---|---|
| `--code <PROJECT_CODE>` | ✅ | Код проекта в PMForesight (например `504-595`). Можно передать **несколько** через `--code X --code Y`. |
| `--no-cache` | ❌ | Не использовать кэш `.cache_*.json` в `/tmp` (по умолчанию кэш используется). |
| `--generator <name>` | ❌ | Имя генератора для YAML front-matter (по умолчанию `fst-project-health`). |

### 2.2. Возвращаемые артефакты

- `/tmp/project_<code>_report.md` — самодостаточный MD с YAML front-matter.
- `/tmp/project_<code>_report.html` — финальный HTML-отчёт (открывается в браузере, отправляется в Telegram).
- `/tmp/.cache_<resource>_<project_id>.json` — кэш MCP-ответов (для ускорения повторных прогонов; удалить `/tmp/.cache_*.json` для полной перегенерации).

---

## 3. Скрипты скилла

| Скрипт | LOC | Размер | Назначение |
|---|---|---|---|
| `run_all.py` | 1072 | 48 KB | **Главный скрипт.** Оркестрирует весь pipeline: вызывает MCP, собирает MD, запускает HTML-сборку. |
| `build_html_report.py` | 1015 | 49 KB | **Главный HTML-сборщик.** Парсит MD и рендерит HTML. Поддерживает `--md PATH` для построения по произвольному MD. |
| `rebuild_report.py` | 238 | 10 KB | Склеивает все секции MD в один файл + YAML front-matter (`generator`, `snapshot_timestamp`, `project_code`, `project_id`). |
| `build_report_header.py` | 592 | 25 KB | Шапка отчёта (метаданные, вердикт, сводка разделов). |
| `mcp_config.py` | 549 | 24 KB | Конфигурация MCP-соединения (URL, JWT, кэш). |
| `mcp_probe.py` | 212 | 8 KB | Диагностика MCP (initialize, list, ping). |
| `find_project_by_code.py` | 267 | 12 KB | Поиск ProjectId по коду проекта (`504-595` → `4595`). |
| `lc_stage_kt_registry.py` | 621 | 33 KB | Реестр КТ (контрольных точек) проекта: статусы, планы, прогнозы, исполнители. |
| `point_states.py` | 256 | 10 KB | Состояния точек КТ (план/факт/прогноз/просрочка). |
| `get_effort.py` | 373 | 16 KB | Трудозатраты по проекту (план/факт/прогноз). |
| `get_project_budget.py` | 309 | 12 KB | Бюджет проекта (план/факт/прогноз). |
| `project_indicators.py` | 2743 | 115 KB | **Большой модуль** — 16 показателей проекта (раздел 6). Главный источник данных для таблицы показателей. |
| `get_metamodel.py` | 143 | 5 KB | Метамодель проекта (типы сущностей, связи). |
| `indicator_thresholds.py` | 94 | 3 KB | Пороги для показателей (когда «здоров» / «болен»). |
| `*_thresholds.py` (10 файлов) | 50–140 | 1–4 KB | Пороги для каждого раздела (3, 4, 5, 6, 7). |
| `act_pay_amounts_thresholds.py` | 141 | 4 KB | Пороги по суммам оплат. |
| `cross_activity_overload_thresholds.py` | 90 | 3 KB | Пороги по перегрузке активностями. |
| `vat_calc.py` / `vat_constants.py` | 128 + 24 | 5 KB | Расчёт НДС. |
| `*check.py` (8 файлов) | 19–315 | 0.5–15 KB | Частные проверки (Effort, FinResult, Payments, Passport, LeaderID, OwnerID). |

**Всего: ~40 скриптов.** Главные — `run_all.py`, `build_html_report.py`, `rebuild_report.py`. Остальные — частные модули.

---

## 4. Методы скилла (для переиспользования)

### 4.1. `run_all.py::main()`

- **Назначение:** точка входа. Прогон всего pipeline для одного/нескольких проектов.
- **Параметры:** см. раздел 2.1.
- **Что берёт из MCP:** проект целиком (карточка, КТ, бюджет, ресурсы, показатели).
- **Что делает:**
  1. Ищет ProjectId по коду через `find_project_by_code`.
  2. Параллельно опрашивает разделы 3–9.
  3. Склеивает MD через `rebuild_report.py`.
  4. Запускает `build_html_report.py` для генерации HTML.
- **Когда переиспользовать:** когда нужна **полная сборка** отчёта.

### 4.2. `build_html_report.py::build_html_report()`

- **Назначение:** парсит MD → HTML.
- **Параметры CLI:** `--md <PATH>`, `--code <CODE>`, `--no-cache`, `--generator <NAME>`.
- **Программный импорт:**
  ```python
  from build_html_report import build_html_report
  html = build_html_report(md_path=Path("..."), generator="...", snapshot_timestamp="...")
  ```
- **Когда переиспользовать:** когда **MD уже есть** и нужно собрать HTML (используется также из `fst-project-health-from-md-snapshot`).

### 4.3. `rebuild_report.py::rebuild_report()`

- **Назначение:** склеивает секции (3–9 + Сводка) в финальный MD + YAML front-matter.
- **Параметры:** `--sections-dir <DIR>`, `--output <PATH>`, `--generator <NAME>`.
- **Когда переиспользовать:** для восстановления MD из `/tmp/section_*_result.md` (например, после частичного сбоя).

### 4.4. `rebuild_report.py::_build_front_matter()`

- **Назначение:** собирает YAML front-matter.
- **Параметры:** `generator`, `project_code`, `project_id`, `timestamp` (None для live).
- **Логика (v1.0.19):** `snapshot_timestamp` пишется **ТОЛЬКО** для snapshot-генераторов (`snap-md`, `snapshot`, `from-md-snapshot`). Для live (`generator="fst-project-health"`) поле **отсутствует** → в HTML **нет** строки «Слепок от:».

### 4.5. `mcp_config.py::get_mcp_client()`

- **Назначение:** создаёт MCP-клиент (SSE).
- **Когда переиспользовать:** в любом скрипте, которому нужен доступ к PMForesight MCP.

### 4.6. `find_project_by_code.py::find_project()`

- **Назначение:** код проекта → ProjectId.
- **Когда переиспользовать:** всегда в начале любого скрипта, работающего с MCP.

---

## 5. Особенности поведения

### 5.1. Кэш

Кэш MCP-ответов хранится в `/tmp/.cache_*.json` (по одному на каждый ресурс × проект).
Чтобы пересобрать **с нуля** — `rm -f /tmp/.cache_*.json` или используйте `--no-cache`.

### 5.2. YAML front-matter и «Слепок от:»

Live-отчёт (`generator="fst-project-health"`) **не содержит** поле `snapshot_timestamp` →
в HTML **нет** строки «Слепок от:» (только «MCP: PMForesight MCP v3.2.4»).

### 5.3. Прецеденты по времени

| Сценарий | Время |
|---|---|
| `run_all.py --code 504-595` (с кэшем) | 19–25 секунд |
| `run_all.py --code 504-595 --no-cache` | 25–52 секунды |
| `build_html_report.py --md PATH` (без MCP) | 1 секунда |

---

## 6. Ошибки и их обработка

| Ошибка | Что делать |
|---|---|
| `ReadTimeout` от MCP | Повторить (транзиентная). Скилл автоматически ретраит через `@_transient_safe`. |
| Проект не найден по коду | Проверить код в PMForesight. |
| `JWT expired` | Обновить токен (см. `.env.example`). |

---

## 7. Сценарии использования

### 7.1. Идеальный сценарий (live)

```bash
python3 scripts/run_all.py --code 504-595
```

Результат: `/tmp/project_504-595_report.html` (~41 KB).

### 7.2. Частая ситуация: «забыл про кэш»

```bash
rm -f /tmp/.cache_*.json
python3 scripts/run_all.py --code 504-595 --no-cache
```

### 7.3. Опечатка в коде

```bash
python3 scripts/run_all.py --code 504-59   # лишний символ
# → ERROR: проект не найден
# Решение: проверить код в PMForesight
```

---

## 8. Где скилл лежит

```
~/.hermes/profiles/fst-control/skills/productivity/fst-project-health/
├── SKILL.md              ← описание для агента
├── README.md             ← краткая документация
├── CHANGELOG.md          ← история версий
├── scripts/              ← все скрипты
├── templates/            ← Jinja-шаблоны (HTML)
├── outputs/              ← кэш артефактов
├── references/           ← вспомогательные документы
├── requirements.txt
└── .env.example
```
