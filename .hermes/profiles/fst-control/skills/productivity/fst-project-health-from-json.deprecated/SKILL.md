---
name: fst-project-health-from-json
version: 1.0.19
description: "**DEPRECATED 2026-09-24.** Этот скилл не используется. Используйте `fst-project-health-from-md-snapshot` для HTML-рендера из MD-слепков проекта в карточке MCP. См. `DEPRECATED.md` в этом каталоге и `CHANGELOG.md` семейства (раздел «Архитектурные инварианты»). [Оригинальное описание:] Class-level skill. Health-of-project report (sections 1-9) via PMForesight MCP. **v1.0.19:** `build_html_report.py --md PATH` для рендера HTML только из MD-снапшота (без /tmp/proj_*.json); `parse_project_metadata_from_md()` берёт Code/Name/ProjectId из самого MD. YAML `snapshot_timestamp` (из `rebuild_report.py`) — приоритетный источник момента времени в HTML-шапке «Слепок от: ...» (см. CHANGELOG семейства, раздел «Архитектурные инварианты»). **v1.0.18:** #50 (workflow применения reference-палитры: добавить `:root` целиком → менять только правила с прямым аналогом → всегда делать playbook-маппинг), #51 (Header = Hero-блок: gradient, eyebrow, meta-color, shadow по AGPM-токенам). **v1.0.17:** verify env-var claims before documenting success (10a). **v1.0.16:** #233 (все разделы равной глубины), #234 (порядок reference = порядок артефакта), #232 (HTTP-таймаут MCP для крупных проектов — sed TIMEOUT_TOOLS_CALL). **v1.0.15:** #229 (не перефразировать постановки), #219 (не хардкодить пользователя). **v1.0.14:** portable setup (.env.example + ENV_FILE_CANDIDATES) #224. **v1.0.13:** 6.12 НДС по периодам (только доходный контракт, fact>forecast>plan, vat в том же сценарии что amount, допуск 0.0001₽) #223. **v1.0.12:** 6.12 «Нет,» без (+N) #218; «все N фиксов сразу» #222; «делай по эталону» = полное соответствие #221; «сначала оформление» #226; «покажи эталон» #227; тесты #228. **v1.0.11:** 6.8 → Point/AllFinancePoint #214. **v1.0.10:** JWT displayname #213. **v1.0.9:** generator not HTML #205; порядок старые→новые #206. **v1.0.7:** __pycache__ #199; num тип #200. **v1.0.6:** 6.6 без синего; 6.7 прогноз. **v1.0.5:** ▼ 9px, whitelist, сетка. **v1.0.4:** 16 details. Pitfalls: 49 (#159-#230). Tests: 54/54 OK. **CRITICAL:** ждать «go» #192. Author: ROSTISLAV KUZNETSOV."
tags: [report, pmpractice, ru, foresight, project-health, health-check, html, markdown, word, docx, aggregator, portable, filters, indicators, trends, vat, ndfl, tax, budget, lifecycle, optimization, get_entity_data, details-summary, html-rendering, deprecated]
related_skills: [project-search, mcp-server-probing, fst-mcp-tester]
---

# fst-project-health

## When to load

- User asks for a project health / status / summary report ("отчёт о здоровье проекта", "health of project", "статус проекта 504-595").
- User asks about specific section like "покажи секцию 6" / "раздел 6.7" / "бюджет проекта".
- User asks to diagnose a slow project / overspend / overdue tasks — anything that maps to the 16 indicators in section 6.

## CRITICAL: user-preference — collect requirements first, act on explicit "go"

**RULE (Pitfall #192, 2026-09-03):** When user starts listing requirements
("Нужно сделать X", "Поправь Y", "В подпункте 6.7..."), DO **NOT** start
implementing or even drafting code. Just acknowledge each point briefly
("Принял, зафиксировал. Замечание #N — <summary>") and ask minimal
clarifying questions. **Wait** until the user explicitly says "Всё, можно
делать" / "Поехали" / "Давай" / "Делай".

**Trigger phrases that mean "wait, more coming":**
- "И жди" / "И жди ещё" / "Жди" / "Пауза"
- "Сейчас ещё замечания выдам" / "Я продолжу передавать требования"
- "Нужно будет - переделаем" (signals more pending)
- "Дополняю замечания" / "Продолжаю дополнять замечания"
- "Поправляй и снова генерируй" — но **сначала** убедись, что нет "И жди" / "Пауза" после.

**Stop phrases (means "go"):**
- "Всё, можно делать" / "Всё, поехали" / "Давай" / "Делай" / "Поехали" / "Стоп, всё"
- "Исправляй" / "Применяй" / "Реализуй" БЕЗ следующих "И жди" / "Пауза"

**Stop phrases (means "wait for verbatim"):
- "Дополнение получилось неправильное" / "Убери последнее обновление"
  (Pitfall #229, NEW v1.0.15) — пользователь откатывает то, что ты
  **перефразировал** его постановки. Lesson: никогда не перефразировать
  требования пользователя в документации (playbook, references, SKILL.md) —
  дословные цитаты в кавычках или явные ссылки на дату/контекст.

**What NOT to do while user is streaming requirements:**
- Do NOT run scripts (`python3 ...`, `run_all.py`)
- Do NOT edit files (`patch`, `write_file`)
- Do NOT ask the same clarifying question twice (если уже спросил — жди ответ, не дублируй)
- Do NOT say "принял, начинаю" or any synonym of "I'll start now"
- Do NOT even list a concrete plan of patches ("Сначала поменяю X, потом Y")
- Do NOT preemptively fix a small safe thing ("это CSS, безопасно, сделаю сейчас") —

**Что делать:** только collect requirements + задавать **минимальные**
уточняющие вопросы. Если вопрос уже задан в backlog (`references/section-6-backlog-2026-09-03.md`) —
не дублировать, просто отметить "вопрос #N в backlog".

**Correct response template:**
> "Принял. Зафиксировал: <короткое summary>. ❓ Уточнение (если есть):
> 1) ... 2) ... Слушаю дальше."

User explicitly reprimanded twice in one session ("Я же сказал ждать!!!",
"Зачем ты бросаешься исправлять, когда я ещё не закончил передавать тебе
требования!"). This is non-negotiable.

## Quick reference

- **Skill location:** `~/.hermes/profiles/fst-control/skills/productivity/fst-project-health/`
- **Main script:** `scripts/run_all.py --code <CODE> [--no-cache] [--timing]`
- **Templates:** `templates/report.html`, `templates/report.css`
- **Indicators:** `scripts/project_indicators.py` (16 indicators as separate methods)
- **Thresholds:** `scripts/*-thresholds.py` (10 per-indicator threshold files)
- **MD/HTML outputs:** `/tmp/project_<CODE>_report.{md,html}`
- **WORD output:** формируется **отдельным скиллом** `fst-project-health-word`
  (см. Pitfall #52). Не запускается автоматически.

## HTML section 6 architecture (v1.0.7 — current)

Each of the 16 indicators is its own `<details>`:

```html
<details class="indicator-details" data-status="...">
  <summary>
    <table class="tbl tbl-indicators">
      <tr data-status="critical">
        <td>6.1</td><td>Юрлицо...</td><td>Нет</td>
        <td class="col-details"><span class="col-details-marker">▼</span></td>
      </tr>
    </table>
  </summary>
  <div class="indicator-details-panel">
    <div class="tbl-nested-title">...</div>
    <table class="tbl-nested">...</table>
  </div>
</details>
```

**Critical CSS rules** (must be present in `templates/report.css`):
- `details.indicator-details > summary::-webkit-details-marker { display: none; }`
- `details.indicator-details > summary::marker { display: none; content: ""; }`
- `details.indicator-details[open] > summary .col-details-marker::after { content: "▲"; }`

**Visual specs for `▼` marker (v1.0.5):**
- Размер **9px** (меньше чем в `<summary>` разделов 3-7, там 10px).
- Цвет **тёмно-синий `#1e40af`** (blue-800), **отличается** от серого `#475569`
  треугольника в заголовках разделов.
- Сетка вложенных таблиц: **`#cbd5e1`** (темнее), **1px** (без изменений толщины).

**Whitelist подпунктов с возможными вложенными таблицами:**

```python
allowed_numbers = {2, 3, 4, 5, 6, 7, 8, 15, 16}  # Pitfall #193
```

**Поведение `▼` по типу подпункта:**

| Подпункт | В whitelist? | Данные есть | Данных нет |
|---|---|---|---|
| 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.15, 6.16 | ДА | ▼ тёмно-синий кликабельный (`<details>`) | ▼ серый `#94a3b8` неактивный (без `<details>`) |
| Остальные (6.1, 6.9, 6.10, 6.11, 6.12, 6.13, 6.14) | НЕТ | Пустая ячейка «Детали» (без ▼ вообще) | Пустая ячейка «Детали» (без ▼ вообще) |

Серый неактивный ▼ имеет класс `.col-details-marker-disabled`,
`cursor: default`. Не кликабельный — НЕ создаём `<details>` для него.

**Don't:** use `<input type='checkbox' hidden> + label + ~ panel` — selector `~` has leaky scoping (Pitfall #188, see `references/html-report-v1003-section6-architecture.md`).

**Don't:** put `<details>` inside `<td>` with colspan — table layout breaks (Pitfall #5 in `references/html-report-pitfalls-v1001.md`).

**Don't:** показывать ▼ для **всех** индикаторов без данных — это была
ошибка v1.0.5 (Pitfall #194). Сначала проверь whitelist `allowed_numbers`.

**`table=[]` vs `table=None` — критично для рендера ▼ (Pitfall #198):**
- `table=None` → подпункт НЕ из whitelist (нет возможности вложенной
  таблицы) → пустая ячейка «Детали», без ▼ вообще.
- `table=[]` → подпункт ИЗ whitelist, но данных нет в текущем запуске →
  серый неактивный ▼ `#94a3b8` через `.col-details-marker-disabled`.
- `table=[{...}, ...]` → подпункт ИЗ whitelist, есть данные → синий
  кликабельный ▼ через `<details>`.

Реализация в `build_html_report.py`:
```python
has_data = has_details and len(table) > 0
if not can_have_details:       # нет в whitelist → без ▼
    ... <td class='col-details'></td>
elif not has_data:             # whitelist, но пусто → серый ▼
    ... <span class='col-details-marker-disabled'>▼</span>
else:                          # whitelist + данные → синий ▼ в <details>
    ... <details><summary>...▼...</summary><div class='indicator-details-panel'>...</div></details>
```

## Section 6 v1.0.6 — семантика конкретных подпунктов

### 6.6 — без цветовой подсветки

Подпункт «Есть нереализованные прогнозы по ролевым ресурсам» всегда
получает `verdict = "Норма"` (без синей подсветки). Таблица с ролями
остаётся (если есть данные). Палитра в секции 6 — **только** красный
(критическое), жёлтый (существенное), белый (норма + информационное).

Реализация: `scripts/project_indicators.py::check_unfilled_roles` —
`verdict = "Норма"` всегда.

### 6.7 — по прогнозу (Pitfall #196)

Подпункт «Есть исполнители у которых **прогноз** в сумме с др.активностями
> 100%». Используем `forecast_hours` (НЕ `plan_hours`).

**Колонки таблицы:**

| Колонка | Что показывает | Источник |
|---|---|---|
| ФИО | username исполнителя | `username` |
| **Прогноз по активн.** | прогноз ТОЛЬКО по проекту отчёта (например, 504-595) | `forecast_hours WHERE projectid == project_id` |
| Превышение сумм. | суммарный прогноз (по всем проектам) минус норма | считать |
| %Превышения | `(sum_forecast / norm) × 100` | считать |

**Сортировка: по алфавиту ФИО (Pitfall #210, 2026-09-03)** — пользователь
отверг сортировку по severity + percent. Используем:
```python
sorted(overload_rows, key=lambda r: (r["user"] or "").lower())
```

**Pitfall #196:** В `ProjectResourcePlan` поле для фильтрации проекта —
**`projectid`** (lowercase, без подчёркивания). НЕ `project_id`, НЕ `ProjectId`.
Сравнение через `str(row_projectid) == str(project_id)`.

**Pitfall #197:** Чтобы переопределить заголовок колонки для конкретного
подпункта (например, 6.7 «План» → «Прогноз по активн.»), подменяем в
`build_html_report.py` в цикле формирования заголовков после словарной
подстановки:

```python
for h in headers:
    if num == "7" and h == "План":
        h = "Прогноз по активн."
    out.append(f"<th>{h}</th>")
```

`col_names_ru` общий для всех подпунктов — per-indicator override
делается в `render_section_6_indicators`.

### 6.12 — НДС по всему проекту (Pitfall #223, NEW v1.0.13)

Подпункт «Сумма НДС расчётная». Проверяет, что указанный пользователем
НДС (статья 611-13) совпадает с расчётным `сумма / 105 × 5`.

**Ключевое правило (NEW v1.0.13):** суммируем amount и vat **по всем
периодам проекта**, не по отдельным месяцам. Подробности —
`references/indicator-6-12-vat-amount-format.md`.

**Иерархия приоритетов в каждом периоде:**
- `fact > forecast > plan` (внутри `max(pay, act)`)
- vat берётся **в том же сценарии**, что и amount

**Текст результата (Pitfall #218):**
- «Да» если совпадает с допуском 0.0001 ₽
- «Нет, Должно быть:X/Указано:Y/%:Z» если нет (запятая после «Нет»,
  без `(+N)`)
- `verdict = "Норма"` всегда (без цветовой подсветки)

### 6.8 — финансовые КТ проекта (Pitfall #214-#217, NEW v1.0.11)

Подпункт «Соблюдение сроков финансовых КТ». Раньше брал **акты/оплаты
из `InContractBudgetBusiness`** — НЕПРАВИЛЬНО (там были «Акт-4724» /
«Оплата-4724», это ID финансовых сущностей, а не КТ).

**Правильный источник — view `Point/AllFinancePoint`** (с фильтром
`ProjectId`). Этот view возвращает **КТ типа `point`** с
`ParentEntityName="InContract"` (parent = контракт, не проект напрямую).

**Структура КТ для 6.8 (иерархия, Pitfall #216):**

```
Проект (parent)
  └─ Контракт (InContract, parent)
     └─ КТ (type=point, ParentEntityName=InContract)  ← ЭТО в таблице
```

**Признак «привязана к контракту»:** `ParentEntityName == "InContract"`.
НЕ путать с `ParentEntityName == "Project"` (КТ уровня проекта, не
подходит для 6.8).

**Признак «просрочена»:** `ForecastDate < today AND FactDate is None`.

**Pitfall #217 — `AllMyPoint` ≠ `AllFinancePoint`:**
- `AllMyPoint?ProjectId=...` — КТ уровня проекта (`ParentEntityName=Project`).
  Используется в 6.3, 6.4 (просрочки по трудозатратам).
- `AllFinancePoint?ProjectId=...` — финансовые КТ (`ParentEntityName=InContract`).
  Используется в 6.8 (просрочки по актам/оплатам).
- **Не использовать `AllMyPoint` для 6.8** — там не будет финансовых КТ.

**Колонки таблицы 6.8 — как в секции 3 «Замечания по срокам» (Pitfall #215):**

| # | Код | Наименование | План | Прогноз |

5 колонок, **БЕЗ** колонки «Δ дн» (это в секции 5 «Актуальность прогнозов»).
Состав колонок единый с разделом 3 — это правило пользователя от 2026-09-03:
> «состав колонок и отображение данных для просроченных финансовых вложенной
> таблицы КТ должен соответствовать таблице в секции "Замечания по срокам"».

## Common workflows

### Portable setup (для переноса на другой сервер)

Скилл **portable** — работает и в Hermes-профиле `fst-control`, и автономно в любом каталоге.

**Минимальный набор для переноса:**

```bash
# 1. Скопировать каталог скилла
scp -r fst-project-health/ user@other-server:/opt/skills/

# 2. Установить зависимости
cd /opt/skills/fst-project-health
pip install -r requirements.txt

# 3. Создать .env из шаблона (ОБЯЗАТЕЛЬНО заполнить PMP_TOKEN)
cp .env.example .env
nano .env  # вставить реальный токен

# 4. Запустить
cd scripts
python3 run_all.py --code 504-595
```

**Структура каталога скилла (всё самодостаточно):**

```
fst-project-health/
├── SKILL.md           # описание скилла
├── .env.example       # шаблон для токена (без секретов)
├── requirements.txt   # Python-зависимости
├── scripts/           # все .py (включая .env.example рядом со скиллом)
├── templates/         # report.html, report.css
├── references/        # документация
├── tests/             # тесты
└── project-search/    # вспомогательный skill
```

**Runtime-артефакты (в `/tmp`, НЕ нужны при переносе):**
- `/tmp/project_<CODE>_report.{html,md,docx}` — выходной отчёт (пользователю)
- `/tmp/section_*_result.md` — промежуточные секции
- `/tmp/.cache_*` — межзапусковый кеш (5 мин TTL)
- `/tmp/__pycache__` — Python-кеш (создаётся автоматически)

**Приоритет поиска `PMP_TOKEN`:**
1. `os.environ["PMP_TOKEN"]` (для shell-сессий)
2. `<каталог скилла>/.env` (для portable-режима)
3. `~/.hermes/profiles/fst-control/.env` (для Hermes-режима)

### Generate report for one project

```bash
cd ~/.hermes/profiles/fst-control/skills/productivity/fst-project-health/scripts
python3 run_all.py --code 504-595 --no-cache --timing
```

Outputs land in `/tmp/project_504-595_report.{md,html,docx}`. Cache is in `/tmp/.cache_run_all_<CODE>.json` (5min TTL).

### Large projects — увеличить HTTP-таймаут MCP

Дефолтный `TIMEOUT_TOOLS_CALL=60` (см. `scripts/mcp_config.py:155`)
**недостаточен** для крупных проектов: на 504-595 `get_entity_data`
падает с `ReadTimeoutError` (Pitfall #232). Если проект содержит
тысячи строк в `ProjectResourcePlan` / `ProjectBudgetCompleteBusiness` /
КТ — увеличить таймаут **до запуска**:

```bash
# Вариант 1: поднять константу в mcp_config.py (permanent fix)
sed -i 's/TIMEOUT_TOOLS_CALL: int = 60/TIMEOUT_TOOLS_CALL: int = 180/' \
  scripts/mcp_config.py

**Вариант 2:** на данный момент **не существует** env-override для
таймаута. `PMP_TIMEOUT` не считывается `mcp_config.py` (проверено:
grep по `os.environ` показывает только `PMP_TOKEN`). Если хочется
env-override — добавить в `mcp_config.py::mcp_call`:
```python
timeout = int(os.environ.get("PMP_TIMEOUT", timeout))
```
или передавать `timeout` явно в место вызова.

**Признак**, что нужно увеличить: в traceback — `Read timed out` /
`ReadTimeoutError` от `ppreplica.hera.pmpractice.ru:443`, при том что
проект существует и непустой. После правки — удалить `__pycache__`
(Pitfall #199).

### Re-render HTML from MD only (fast)

**v1.0.19** ввёл режим `--md` для `build_html_report.py` —
рендер HTML **только** из MD-файла, без `/tmp/proj_*.json` и без MCP.
Метаданные проекта (Code, Name, ProjectId) берутся из самого MD
(`parse_project_metadata_from_md`).

```bash
# Рендер из MD-снапшота (НЕ из живого прогона)
python3 ~/.hermes/profiles/fst-control/skills/productivity/fst-project-health/scripts/build_html_report.py \
    --md /root/.hermes/profiles/fst-control/skills/productivity/fst-project-health-snap-md/outputs/504-595_2026-09-23_21-53-09.md
```

Результат: HTML-отчёт с шапкой вида «MCP: PMForesight MCP v3.2.4
**Слепок от: <timestamp из YAML front-matter>**» — то есть исторический
отчёт «как тогда выглядел проект», а не текущий.

### Clear cache

```bash
rm -f /tmp/.cache_run_all_*.json /tmp/.cache_project_card_*.json /tmp/.cache_indicators_*.json
find ~/.hermes/profiles/fst-control/skills/productivity/fst-project-health -name __pycache__ -type d -exec rm -rf {} +
```

Все **четыре** уровня: `run_all` (общий), `project_card` (по коду проекта),
`indicators` (по project_id), `__pycache__` (Python bytecode — Pitfall #199).
Без удаления `__pycache__` изменения в `build_html_report.py` или
`project_indicators.py` могут не подхватываться.

## Documentation discipline rules (always-on)

When producing reference docs, playbooks, READMEs, or any per-section
guide, the following rules apply — they override convenience choices
about depth and order.

8. **All sections get equal depth, not just the headline one (NEW)** —
   if a document covers N sections, every section gets N comparable
   subsections. The rule that broke this: I described section 6 in
   detail and skimmed the rest. Result: user had to ask "почему
   подробно описана только работа с пунктами раздела 6?". Fix: when
   building a per-section reference, draft the table-of-contents first
   with one row per section at the same depth, then fill each row with
   the same template (Назначение / Метод / Параметры / Скрипты /
   Edge cases). If a section has less content, mark it «сводка, детали
   в X» rather than skipping subsections.
9. **Reference doc order = artifact order (NEW)** — when documenting
   a report (or any linear artifact with numbered sections), subsections
   in the doc must follow the artifact's section numbers in order.
   The rule that broke this: I organized sections by what I knew best
   (section 6 first, then everything else scrambled) instead of by
   report order (1 → 3 → 4 → 5 → 6 → 7 → 8). Fix: at the top of every
   per-section reference, state «подразделы идут в том же порядке, что
   и разделы отчёта», and lay out `7.1 → 7.3 → 7.4 → 7.5 → 7.6 →
   7.7 → 7.8` (matching the report, gaps allowed).

## Critical pitfalls (current priority)

1. **`project_id=accountid` typo** (Pitfall #159, CRITICAL) — different entities, always check the right field.
2. **HTML section 6 v1.0.0/v1.0.1 broken** — fixed in v1.0.4. See `references/html-report-v1003-section6-architecture.md` for full diff.
3. **`~` selector leaky scoping** (Pitfall #188) — use native `<details>`, not checkbox+label.
4. **Native `<summary>` marker conflict** (Pitfall #189) — must hide both `::-webkit-details-marker` and `::marker`.
5. **`data-status` always on `<tr>`, never on `<td>`** (Pitfall #190) — CSS `tr[data-status]` is the only reliable selector.
6. **Whitelist подпунктов с вложенными таблицами** (Pitfall #193) —
   `allowed_numbers = {2, 3, 4, 5, 6, 7, 8, 15, 16}`. У остальных 7
   подпунктов НИКОГДА не должно быть ▼.
7. **Серый ▼ ≠ для всех без данных** (Pitfall #194) — серый неактивный ▼
   только для whitelist. Не путай с «у всех подпунктов без данных».
8. **Collect requirements, жди explicit «go»** (Pitfall #192) — пользователь
   2 раза ругал за опережение. Не исправляй превентивно, не предлагай
   план реализации, пока не скажет «Давай» / «Исправляй» / «Поехали».
9. **User-driven data refresh** (Pitfall #195) — пользователь может САМ
   менять данные в MCP (например, чтобы появились данные для 6.7). При
   сигнале «перестрой отчёт» после правок данных — потри ВСЕ три уровня
   кэша и пересобирай с `--no-cache`.
10. **`ProjectResourcePlan.projectid` lowercase** (Pitfall #196) — НЕ
    `project_id`, НЕ `ProjectId`. Поле для фильтрации по проекту.
10a. **Verify env-var claims before documenting success (NEW v1.0.16,
    2026-09-06)** — never write `FOO=val cmd works` from a single
    successful run without grepping the codebase for `os.environ.get("FOO")`
    in the actual handler. The previous SKILL.md "Large projects" section
    claimed `PMP_TIMEOUT=180 python3 run_all.py` raised the timeout, but
    `mcp_config.py` only reads `PMP_TOKEN` from env. The command
    "worked" by coincidence (retry / partial data), not because the
    env var was honored. Symptom of an unfaked claim: doc says «use
    env var X», codebase has no read of X. Fix: add the env-read in
    production code (`mcp_call(timeout=int(os.environ.get("PMP_TIMEOUT", timeout)))`),
    THEN document.
11. **Per-indicator header override в `build_html_report.py`** (Pitfall #197)
    — `col_names_ru` общий для всех 16 подпунктов. Чтобы переопределить
    заголовок для конкретного (6.7 «План» → «Прогноз по активн.»),
    подменяем в цикле формирования заголовков после словарной подстановки.
12. **6.6 без цветовой подсветки** — `verdict = "Норма"` всегда в
    `check_unfilled_roles`. Палитра секции 6: только красный/жёлтый/белый.
13. **Палитра секции 6** — **4 (НЕ 3) возможных фона строки**:
    `critical` (красный `#fee2e2`), `substantial` (жёлтый `#fef3c7`),
    `informational` (синий `#dbeafe` — **НЕ запрещён**, это 4-й статус,
    отступление от AGPM 4-статусной модели), `normal` (белый `#ffffff`).
    Иерархия severity: `critical > substantial > informational > Норма`.
    Синяя подсветка (`#dbeafe` для informational, `#1e40af` текст) —
    **допустима** для строк с `verdict="Информационное"`. Это **не**
    противоречит правилу 3-цветной палитры эталона 26 — там просто
    не было informational статуса в то время.
    Цвета AGPM-палитры (`--green-bg`, `--yellow-bg`, `--red-bg`, `--gray-bg`)
    **могут пересекаться** с нашими `--ink`, `--muted` — для каждого
    токена смотри `references/color-palette-mapping.md`.
    Если по требованию пользователя нужна подкраска `verdict="Норма"`
    без выделения — `verdict = "Норма"` (но вложенная таблица может быть).
14. **`table=[]` vs `table=None` (Pitfall #198)** — чтобы отрендерить
    серый неактивный ▼ для подпункта без данных, нужно вернуть
    **`table=[]`** (пустой список), НЕ `table=None`. `None` означает
    «у подпункта не может быть вложенной таблицы вообще» (проверка
    по `allowed_numbers`), `[]` означает «может, но данных нет сейчас».
    Применяется во всех подпунктах whitelist `{2,3,4,5,6,7,8,15,16}`.
    Пример: 6.7 — если `overload_rows` пустой → `table = []`,
    и тогда HTML рендерит серый ▼ через `.col-details-marker-disabled`.
15. **`__pycache__` блокирует правки `build_html_report.py` / `project_indicators.py`
    (Pitfall #199)** — после `patch` или `write_file` в эти скрипты Python
    может НЕ перечитать изменения из `.pyc` кэша. **Симптом:** правка в файле
    есть (`grep` подтверждает), а HTML генерируется по старой логике.
    **Фикс:** удалить `__pycache__`:
    `find ~/.hermes/profiles/fst-control/skills/productivity/fst-project-health -name __pycache__ -type d -exec rm -rf {} +`
    и пересобрать. Делать **после** каждой правки `build_html_report.py` или
    `project_indicators.py`, не доверять одному `python3 run_all.py`.
16. **`num` тип в `build_html_report.py` (Pitfall #166 + #200)** — `IndicatorResult.number`
    приходит как **число** (`7`) в Python, но после JSON-сериализации в
    `section_6_indicators_data.json` становится **строкой** (`"7"`). Когда
    `build_html_report.py` читает `ind.get("number", "")`, он получает строку.
    Поэтому сравнение `num == "7"` работает. **НО** если где-то в коде
    используется `int(num)` или `num` без `str()` — сломается. Лучше всегда:
    `str(num) == "7"`.
17. **Respect «сначала X, потом Y» (Pitfall #201)** — пользователь явно
    разделяет работу на этапы: «сначала оформление», «потом N». **Не
    агрегировать** все правки в один заход. Делать **только** то, что
    сказано в текущей «go» команде, не превентивно делать следующий этап.
    Пример: пользователь сказал «Исправь сначала оформление» → я сделал
    оформление + **заодно** начал переименовывать 6.7 → пользователь
    отругал. **Ждать отдельный «go» на каждый этап.**
18. **Дубли секций в `templates/report.html` при добавлении новой (Pitfall #202)**
    — в шаблоне **уже были дубли** секций 4, 5, 6 (tbl2/tbl3/tbl4 по
    ДВЕ открывашки `<details class="variant-tbl">` каждый с разными
    заголовками: «Полнота заполнения КТ» + «Полнота заполнения проекта»,
    «Актуальность прогнозов» + «Актуальность прогнозов по проекту»,
    «Финансы» + «Финансовый статус проекта»). Причина — наслоение
    итераций. **При любой правке `report.html`:**
    - Сначала **проверить**, что каждая секция (3/4/5/6-finance/7) имеет
      **ровно одну** `<details>`-открывашку.
    - Заголовки должны быть канонические (см. ниже).
    - Если секция не нужна (например, раздел 8 «Индикатор») — **удалить
      полностью**, а не оставлять «на всякий случай».

19. **Правильный порядок секций и канонические заголовки** (Pitfall #203,
    эталон «26» от 2026-09-03) — финальный порядок для `report.html`:

    | # | Заголовок `<span class="tbl-name">` | placeholder |
    |---|---|---|
    | 1 | «Замечания по срокам:» | `{{ section_3_preview/content }}`, **открыт** по умолчанию |
    | 2 | «Полнота заполнения **проекта**:» | `{{ section_4_* }}` |
    | 3 | «Актуальность прогнозов:» | `{{ section_5_* }}` |
    | 4 | «Показатели проекта:» | `{{ section_8_* }}`, **открыт** (NEW v1.0.0) |
    | 5 | «**Финансовый статус проекта**:» | `{{ section_6_* }}` |
    | 6 | «Технические данные отчёта:» | `{{ section_7_* }}` (preview = «ℹ️ Нейтральный — справочная информация») |

    **НЕ использовать:** «Финансы» (вместо «Финансовый статус проекта»),
    «Полнота заполнения КТ» (вместо «Полнота заполнения проекта»). Это
    были старые заголовки, которые остались как дубли после наслоения.

20. **Метод отладки: сравнение с эталонным отчётом** (Pitfall #204) —
    когда пользователь говорит «привести в порядок» или «сломались секции»,
    но не даёт конкретики, **не угадывать**. Попросить эталонный HTML
    («дай эталонный отчёт, например 26-й») и сравнить построчно:
    - Количество `<details>` блоков (должно быть 6 для v1.0.4+).
    - Заголовки `<span class="tbl-name">` (см. Pitfall #203).
    - Подсветка строк по severity (только три цвета — Pitfall #13).
    - Ширины колонок (`<col>` widths в `report.css`).
    Принести список отличий пользователю, а не «исправлять всё подряд».
21. **«Исправляй не сам HTML, а генератор» (Pitfall #205)** — пользователь
    может прислать эталонный HTML (например, «26-й отчёт») с правильным
    визуалом и сказать «почини». **Не правь HTML-файл руками** (patch в
    `/tmp/...html` или `~/.hermes/profiles/.../cache/documents/*.html`).
    Правь **генератор**: `scripts/build_html_report.py` (функция
    `render_tbl*` или `build_html()`) или `scripts/run_all.py`
    (формирование MD). Правка разового HTML — это костыль: при следующем
    пересборе файл пересоздастся и ошибка вернётся. **Сначала** найти
    место в генераторе, **потом** патчить.
22. **«Сначала приведи в порядок старые секции, потом — новые» (Pitfall #206)**
    — пользователь явно разделяет порядок доводки: сначала секции
    3/4/5/6-finance/7 (существовавшие до v1.0.0), потом секция 6
    «Показатели проекта». Не агрегировать в один раунд. После
    внедрения новой секции 6.0 (v1.0.0) **всегда** проверять, что
    окружающие секции не сломались (порядок, заголовки, дубли — см.
    Pitfalls #202, #203). Если пользователь говорит «привести в порядок
    секции, сделанные ранее» — это **именно** разделы 3/4/5/6-finance/7,
    не трогать 6-indicators до явного запроса.
23. **`render_tbl4_finance` — объединять «Результат» + «Детализация» в одну
    ячейку (Pitfall #207)** — в эталоне 26 (2026-08-07) колонка
    «Результат» содержит **и статус, и детализацию** через «—», например:
    «Да — Прогноз фин.результата: -221,860.00 ₽ → критическое».
    В MD эта информация в **двух** колонках: «Результат» (= «Да») и
    «Детализация» (= «Forecast: ... критическое замечание»).
    `render_tbl4_finance` должен объединять их: `cell = f"{result} — {detail}"`.
    Подсветка через `status_class(cell)` — ищет «критическ» в объединённом
    тексте и применяет `class="status-critical"` к `<tr>`.
24. **`_extract_preview` regex — «Вердикт раздела», не «Статус раздела»
    (Pitfall #208)** — в MD раздела 6 (и других) используется заголовок
    `**Вердикт раздела:** Болен`, а regex `_extract_preview` исторически
    искал `**Статус раздела:**` (старая нотация). Без исправления
    preview теряет префикс «Болен —» и показывает только итог:
    «3 критических, 0 существенных, 0 информационных» вместо
    «Болен — 3 критических, ...». Fix: regex с альтернативой —
    `\*\*Вердикт раздела|Статус раздела:\*\*`.
25. **`status_class()` ищет «критическ» в detail — синхронизировать MD
    (Pitfall #209)** — `status_class()` в `build_html_report.py` определяет
    класс подсветки по тексту результата через ключевые слова («критическ»,
    «существен», «информацион»). Если `run_all.py` для какого-то
    показателя **не добавляет** в `detail` суффикс «— критическое замечание»
    (как было в `build_section_6()` для p3 «Δ прогноза от плана > 2 млн»),
    то даже при `result="Да"` строка **не подсветится красным**. **Синхронизировать:**
    - При добавлении показателя в `run_all.py` — всегда писать суффикс
      «— критическое замечание» / «— существенное замечание» / «норма»
      в `detail`, **аналогично** другим показателям того же раздела.
    - При правке `status_class()` — убедиться, что новые ключевые слова
      матчатся с тем, что реально пишется в MD.
    - Признак проблемы: `<tr class=''>` в HTML при `result="Да"` →
      недостающий суффикс в `run_all.py`.
26. **6.7 сортировка по алфавиту ФИО (Pitfall #210, 2026-09-03)** —
    пользователь явно отверг сортировку по severity + percent. Правило:
    `sorted(overload_rows, key=lambda r: (r["user"] or "").lower())`.
    Не путать с 6.3/6.4 (там сортировка по severity).
27. **Полнота секции 7 «Технические данные» — разные ключи в MD vs
    fallback (Pitfall #211)** — `render_tbl5_tech` в `build_html_report.py`
    парсит строки из MD. Если MD содержит **5 строк** (как в `build_section_7()`
    в `run_all.py`: Пользователь/Титул/Core/URL/Версия MCP), а fallback в
    `render_tbl5_tech` определён на **6 строк** (Пользователь/Титул/URL/
    Версия скилла/Версия MCP/Версия ПМ «Форсайт») — строки из MD **не
    матчатся** с fallback'ом по позициям, итог выглядит странно. Решение:
    привести MD и fallback к одному набору строк, в одном порядке, с
    одинаковыми именами. Сейчас актуальный канон (по эталону 26):
    1. Пользователь, 2. Титул системы, 3. URL MCP-сервера,
    4. Версия скилла, 5. Версия MCP, 6. Версия Core (или «ПМ «Форсайт»»).
28. **Bug «N/A» в строке 1 секции 7 (Pitfall #211)** — в `build_section_7()`
    исторически строка формировалась как
    `{(project.get('name') and 'N/A') or '—'}`. Это **баг**:
    `project['name']` (название проекта) всегда непустое, поэтому
    выражение `project.get('name') and 'N/A'` всегда истинно → в строке
    «Пользователь» показывалось «N/A» вместо ФИО текущего пользователя.
29. **JWT-парсинг для извлечения пользователя (Pitfall #213, NEW)** —
    правильный способ получить ФИО пользователя, от имени которого
    строится отчёт — **распарсить JWT-токен `PMP_TOKEN`**. Токен
    PMForesight — JWT в формате `header.payload.signature`. В payload
    есть claims:
    - `displayname` — ФИО для UI (например, «Кузнецов Ростислав
      Владимирович»)
    - `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname` —
      то же самое через WS-Identity claim
    - `UserId`, `emailaddress`, `nameidentifier` — для аудита
    **Реализация:** функция `get_current_user_from_token()` в
    `scripts/mcp_config.py`:
    ```python
    def get_current_user_from_token(token=None):
        # 1. Взять токен из env (PMP_TOKEN)
        # 2. Распарсить JWT: split('.')[1] → base64url decode → JSON
        # 3. payload.get("displayname") или
        #    payload.get(".../claims/givenname")
        # 4. Fallback → "—"
    ```
    **Использование в `run_all.py::build_section_7()`:**
    ```python
    from mcp_config import get_current_user_from_token
    user = get_current_user_from_token()
    ```
    **НЕ работает:**
    - `mcp_init()` — возвращает `(sid, serverInfo)`, serverInfo — это
      инфо о СЕРВЕРЕ (имя, версия), не о пользователе.
    - `project["OwnerId"]` — владелец проекта, не то же самое что
      пользователь токена (проект может быть открыт другим человеком).
    - `mcp_call(sid, "whoami"/"get_current_user"/...)` — нет такого
      метода в PMForesight MCP (на 2026-09-04).
30. **CSS-класс серого неактивного ▼ (Pitfall #212)** — для подпунктов
    из whitelist `{2,3,4,5,6,7,8,15,16}` без данных используется
    **отдельный** CSS-класс `.col-details-marker-disabled` (НЕ тот же
    `.col-details-marker`). Параметры:
    - `font-size: 9px` (как у активного, но отличается от 16px по умолчанию)
    - `color: #94a3b8` (slate-400 — **светлее** чем `#475569` в
      заголовках разделов, но темнее чем фон)
    - `cursor: default` (НЕ `pointer` — не кликабельный)
    - Не в `<details>` (нельзя кликнуть)
    Активный ▼ — `.col-details-marker` (без суффикса `disabled`):
    `font-size: 9px`, `color: #1e40af` (blue-800), внутри `<details>`.
31. **6.8: правильный view — `Point/AllFinancePoint` (Pitfall #214,
    NEW v1.0.11)** — НЕ использовать `InContractBudgetBusiness` (там
    были «Акт-4724» / «Оплата-4724» — ID финансовых сущностей, не КТ).
    Правильный view: `Point/AllFinancePoint?ProjectId=<id>`. Возвращает
    **КТ с `ParentEntityName=InContract`** (parent = контракт).
    Найдено через `list_views(entityName="Point")` — в списке 9 views,
    два финансовых: `MyFinancePoint` и `AllFinancePoint`.
32. **Иерархия для 6.8: `Project → InContract → Point` (Pitfall #216,
    NEW v1.0.11)** — для просроченных финансовых КТ нужны КТ, **привязанные
    к контрактам** (не к проекту напрямую). Признак: поле
    `ParentEntityName == "InContract"`. Поле `ParentActivity` содержит
    человекочитаемое имя контракта (например, «704-724. Контракт на
    разработку ИСУП для ТЛК "Космодром Жуковский"»).
33. **`AllMyPoint` ≠ `AllFinancePoint` (Pitfall #217, NEW v1.0.11)** —
    - `AllMyPoint?ProjectId=...` — **КТ уровня проекта** (parent=Project).
      Используется в 6.3, 6.4 (просрочки по трудозатратам).
    - `AllFinancePoint?ProjectId=...` — **финансовые КТ** (parent=InContract).
      Используется в 6.8 (просрочки по актам/оплатам).
    - **Не путать!** Probe обязателен при добавлении нового индикатора
      по КТ — `list_views(entityName=...)` показывает все доступные view'ы.
34. **Колонки 6.8 = как в секции 3 «Замечания по срокам» (Pitfall #215,
    NEW v1.0.11)** — пользователь явно сказал: «состав колонок и
    отображение данных для просроченных финансовых вложенной таблицы КТ
    должен соответствовать таблице в секции "Замечания по срокам"».
    Это значит: **5 колонок** (#, Код, Наименование, План, Прогноз),
    **БЕЗ** колонки «Δ дн» (Δ — в секции 5 «Актуальность прогнозов»).
    Применяется и к другим индикаторам, где пользователь укажет
    «соответствует таблице X».
35. **6.12 формат текста результата: «Нет,» (запятая) и БЕЗ `(+N)` (Pitfall #218,
    NEW 2026-09-04)** — пользователь требует:
    - После «Нет» — **запятая**, НЕ вертикальная черта «|».
    - НЕ добавлять `(+N)` если есть несколько mismatches (берем первое,
      показываем без счётчика «остальных»).
    Правильный формат:
    ```
    Нет, Должно быть:125000.00 руб./Указано:75000.00 руб./%:5.2632
    ```
    Было:
    ```
    Нет | Должно быть:... руб./Указано:... руб./%:5.2632 (+2)
    ```
    Реализация в `project_indicators.py::check_vat_amount` — обе ветки
    (1 mismatch / несколько) формируют текст одинаково, без `(+N)`.
36. **«Делай по эталону» (Pitfall #221, NEW 2026-09-04)** — когда пользователь
    присылает эталонный HTML (например, «отчёт 26») и говорит «приведи
    в порядок», это значит **полное соответствие** эталону по всем
    параметрам:
    - Заголовки секций (см. Pitfall #203).
    - Количество строк в таблицах (секция 7 = 6 строк по эталону 26).
    - Формат данных внутри ячеек (кавычки, префиксы, постфиксы).
    - Подсветка и иерархия severity.
    НЕ делать «частичный» фикс («сделал заголовок, но не данные»).
    Применимо к шаблонам `templates/report.html`, `templates/report.css`
    и секционным генераторам в `scripts/run_all.py::build_section_*`.
    Если пользователь говорит «делай по эталону» без уточнений —
    **сравнить построчно** эталон и текущий вывод, принести список
    отличий пользователю **до** реализации, либо сразу реализовать все
    отличия (зависит от контекста).

37. **Эталонный отчёт = образец структуры (Pitfall #220, NEW 2026-09-04)** —
    эталонные HTML-отчёты пользователь присылает как файлы в `cache/documents/`:
    - `doc_d38ea33168f2_project_504-595_report (26).html` — эталон 26,
      2026-08-07, до внедрения секции «Показатели проекта».
    - `doc_abc6a67e2967.png` — скриншот текущего (с дефектами).
    **Структура эталона 26** (см. `references/html-report-structure-etalon-26.md`):
    - 6 секций, без секции 8 и «Показатели проекта».
    - Секция 7 «Технические данные» содержит 6 строк.
    - В секции 6 «Финансовый статус» текст ячейки «Результат» содержит
      И статус («Да»), И детализацию («Forecast: -221,860.00 ₽ → критическое»)
      через «—».
    При доводке генератора под эталон — открыть **этот файл**, не
    предполагать содержимое по памяти.
38. **«Все N фиксов — пользователь требует все сразу» (Pitfall #222,
    NEW 2026-09-04)** — когда пользователь даёт список правок (например,
    «1) X, 2) Y, 3) Z»), даже если они кажутся связанными, **делать все
    в одном раунде**, не «частично». Применимо если пользователь явно
    сказал «все три», «все чини», «всё сразу». Если не сказал —
    уточнить через `clarify` (a/b/c/d варианты).
    **Примеры из сессии:**
    - 6.7: пользователь сказал «все три уточнения — да» (формат таблицы,
      сортировка, ▼ серый) — все три сделаны в `run_all.py` +
      `build_html_report.py`.
    - 6.7 v2: пользователь сказал «всё, по эталону» (заголовки колонок
      «Прогноз по активн.», «Превышение сумм.», «%Превышения») — все три
      переименованы через `str(num) == "7"` блок.
    **Контр-пример:** если пользователь говорит «только X, остальное
    потом» — **только X**, без превентивных фиксов (Pitfall #201).
39. **6.12 переписан — суммирование по всему проекту (Pitfall #223,
    NEW v1.0.13, 2026-09-04)** — пользователь сказал: «Мы чиним генератор,
    а не отчет по одному проекту. Сумма НДС за все периоды, указанная в
    статье 611-13 сравнивается с суммой по всем актам за весь период».
    Логика v1.0.13 в `scripts/project_indicators.py::check_vat_amount`:
    - Берём **только** `budgettype="Доходный контракт"` для amount
      (никакие расходы в расчёте не участвуют).
    - Берём `budgettype="Расход ручной ввод"` + `fs=128` для указанного
      НДС (это статья 611-13, это **то, с чем сравниваем**).
    - **По каждому периоду** приоритет сценария: факт > прогноз > план,
      внутри `max(pay, act)`.
    - **vat берётся в том же сценарии, что и amount**: если amount
      из факта → vat из факта; если из прогноза → vat из прогноза;
      иначе → vat из плана.
    - **Суммируем** по ВСЕМ периодам в один `total_amount` и `total_vat`.
    - Расчёт: `total_amount / 105 × 5 = calculated_vat`.
    - Фактический %: `(total_vat / (total_amount − total_vat)) × 100`.
    - Допуск: `VAT_TOLERANCE_RUB = 0.0001 ₽`.
    - Текст результата: «Нет, Должно быть:X/Указано:Y/%:Z» (Pitfall #218).
    - `verdict = "Норма"` всегда (без подсветки, по аналогии с 6.6).
    **Реализация НЕ через `pick_amount_by_priority`** — старая логика
    выбирала ОДИН сценарий из строки (независимо от периода). Новая
    логика группирует по `(period, scenario)`. Сначала `pick_amount_by_priority`
    использовался, но он брал максимум по факт>прогноз>план, а нужно
    было различать сценарий для amount и vat **в одном периоде**.
    Подробности — `references/indicator-6-12-vat-amount-format.md`.
    **Известное расхождение (FAQ):** для 504-595 план по июлю = 2 500 000,
    но в июле есть **факт 2 497 500** → берётся факт → расчёт меньше плана.
    Это **нормально** — показываем пользователю его ошибку: «должно быть
    190 357.14, ты указал 200 000 (5.2666%, а не 5%)».

40. **MCP probe ПЕРЕД большой правкой индикатора (Pitfall #224,
    NEW v1.0.14, 2026-09-04)** — при переписывании логики индикатора (особенно если
    меняется источник данных, как для 6.8 `InContractBudgetBusiness →
    AllFinancePoint`, или для 6.12 логика суммирования) — **сначала**
    сделать MCP probe для понимания реальной структуры данных:
    - `list_views(entityName="...")` — какие view вообще есть, какие фильтры
      поддерживают (это позволило найти `AllFinancePoint` для 6.8).
    - `get_view(entityName="...", viewName="...", filters={ProjectId: id},
      limit: 5)` — распечатать первые 5 строк, посмотреть поля
      (`ParentEntityName`, `ParentId`, `Code`, `PlanDate`, `ForecastDate`,
      `FactDate`, `budgettype`, `financesourceid`).
    - Сравнить «что я предполагал» vs «что реально есть».
    **Пример для 6.8:** probe `list_views` показал 9 view'ов, среди них
    `MyFinancePoint` и `AllFinancePoint` — последний то что нужно.
    **Пример для 6.12:** probe `get_view(ProjectBudgetCompleteBusiness)`
    показал, что `fs=128` находится в строках `budgettype="Расход
    ручной ввод"`, а не в «Доходный контракт» (это **не баг системы**,
    это особенность модели данных — НДС-строка логически связана с
    доходным контрактом, но учтена как расход).
    **Когда НЕ делать probe:** для косметических правок (CSS, переименование
    заголовка, формат «Нет,» vs «Нет |») — там нет изменения источника.
    Реализация probe — `references/mcp-live-probe-cookbook.md`.

41. **Скилл portable: `.env` в каталоге скилла (Pitfall #225,
    NEW v1.0.14, 2026-09-04)** — для переноса на другой сервер без Hermes-профиля.
    Приоритет поиска `PMP_TOKEN`:
    1. `os.environ["PMP_TOKEN"]` (shell)
    2. `<каталог скилла>/.env` (portable)
    3. `~/.hermes/profiles/fst-control/.env` (Hermes)
    Скилл поставляется с `.env.example` (без секретов) — другой агент
    копирует в `.env` и заполняет реальный токен. `requirements.txt`
    фиксирует `requests>=2.28` и `python-docx>=1.0` — все внешние
    зависимости.

42. **«Сначала оформление, потом логика» (Pitfall #226, NEW 2026-09-04)**
    — пользователь явно разделяет работу: «Сначала мы должны привести в
    порядок секции отчета, сделанные ранее» / «сначала оформление» /
    «сначала X, потом Y». Если пользователь **не указывает** порядок
    — спросить. **НЕ перескакивать** на следующий этап без явного «go».
    Пример из сессии: пользователь сказал «давай исправим сначала
    оформление» → я сделал оформление, дождался «давай 6.7» → только
    тогда перешёл к логике 6.7. Превентивный фикс 6.7 → ругань.
    **Конфликт с Pitfall #222** («все N фиксов сразу»): если пользователь
    сказал «все три уточнения — да», делать все в одном раунде (Pitfall #222
    имеет приоритет над Pitfall #226, потому что явное «все» сильнее
    неявного «сначала X»).

43. **«Покажи эталон» — процесс сравнения (Pitfall #227, NEW 2026-09-04)**
    — когда пользователь говорит «это не правильно, посмотри эталон» /
    «сделай по эталону» / «приведи в порядок» — **алгоритм**:
    1. **Спросить у пользователя путь к эталону** (или поискать в
       `cache/documents/` — пользователь обычно прикладывает файл).
    2. Прочитать эталон **до** реализации, выписать конкретные отличия
       (количество строк, заголовки, формат данных, подсветка).
    3. Принести пользователю **список отличий**, а не сразу фиксить.
    4. После подтверждения — фиксить **генератор** (Pitfall #205), не HTML.
    Если пользователь даёт эталон без явного «сначала посмотри»,
    подразумевается «сделай как там» → фиксить сразу (Pitfall #221).
    Пример: эталон 26 в `cache/documents/doc_d38ea33168f2_project_504-595_report (26).html`
    — финальная структура секций и заголовков.

44. **Добавление тестов для новых Pitfalls (workflow, NEW 2026-09-04)** —
    при добавлении новой фичи в скилл (новый индикатор, новый формат,
    новый helper) **сразу** добавить тесты в `tests/test_*.py`. Не
    откладывать «потом». Минимум тестов:
    1. **Константа/правило тест** — проверка что новый паттерн/число
       правильное (например, `DEFAULT_VAT_RATE == 5.0`).
    2. **Логика тест** — проверка что новая функция делает что должна
       (например, что 6.12 суммирует amount по периодам, не по строкам).
    3. **Edge cases** — пустые данные, невалидный ввод, отсутствие поля.
    Тесты должны быть **автономны** (не требовать MCP) — парсить
    исходники через `ast`/`re` или мокать вызовы. Полный рецепт —
    `references/testing-recipe.md`.

45. **Тесты false positives — исправить за 1-2 итерации (Pitfall #228,
    NEW 2026-09-04)** — тесты для скилла пишутся быстро и иногда
    содержат баги в самих себе. Типичные false positives:
    - Поиск строки через `re.search` с `re.DOTALL` и `re.MULTILINE`
      ломается на многострочных строках (`.*?` слишком жадный).
    - `func_text.lower().replace(" ", "")` теряет `\n` и слипает код.
    - Сравнение **строки** с **числом** (`num == "7"` vs `int(num) == 7`).
    - Игнорирование **docstring** (упоминание старого view в комментарии).
    - Разные варианты написания заголовка («Версия Core» vs «Версия Core (ПМ «Форсайт»)»).
    **Если тест сразу не проходит:**
    1. Прочитать assertion message внимательно — обычно там видно
       **что не совпало** (фактический текст vs ожидаемый).
    2. Поправить **тест**, а не production-код (если production-code
       правильный по логике).
    3. Запустить ещё раз, проверить что все остальные тесты тоже
       проходят (не сломали что-то новое).
    4. После прохождения — закоммитить. **Если тесты находят **настоящие**
       баги** в production — фиксить сначала код, потом тесты.
    Пример из сессии: 6 тестов в первой итерации — 4 проходят, 2 fail
    с false positives. После 2 раундов правок тестов — все 54 теста
    зелёные.

## References (support files)

- **`references/playbook.md`** — **главный playbook для коллег**.
  Подробное описание каждого пункта отчёта в 4 секциях (Назначение /
  Получение данных / Интерпретация / Вывод). Покрывает разделы 1, 3-8 и
  все 16 индикаторов секции 6. **Читать первым** при знакомстве со скиллом.
- **`references/color-palette-mapping.md`** — маппинг AGPM-палитры
  (handoff-документа с токенами `--bg / --paper / --ink / --hero-*`) на
  правила `templates/report.css`. Что совпало, что близко (но не
  идентично), что не перенесено и почему. Обязательно создаётся при
  каждой правке палитры по эталону — Pitfall #50 (см. Critical Pitfalls).
  Там же: anti-patterns (не пытаться «дотянуть» все токены до активного
  использования за один проход).
- **`references/mcp-methods-playbook.md`** — справочник по всем методам
  MCP (`initialize`, `notifications/initialized`, `tools/call` →
  `get_view` / `get_entity_data` / `find_entity`), используемым скиллом:
  сигнатура, где применяется (по секциям/индикаторам), параметры,
  скрипты, edge cases. Раздел 7 идёт в каноническом порядке отчёта
  (1 → 3 → 4 → 5 → 6 → 7 → 8).
- **`references/scripts-catalog.md`** — каталог всех 42 скриптов
  `scripts/`: основные / пороги / CLI-утилиты. Отдельная таблица для
  скриптов со справочными константами и критериями статуса (ставка НДС,
  REMARK_THRESHOLDS, OVERDUE_THRESHOLDS, lc_stage_kt_registry, и т.п.).
  Сводка «какой check_* + какой порог» по всем16 индикаторам.
- **`references/testing-recipe.md`** — рецепт добавления тестов в скилл.
  7 типичных паттернов (константа, формула, mock-данные, парсинг re/ast,
  JWT fixture, ENV fixture), 5 типичных false positives с фиксами,
  workflow от создания до коммита. Использовать при добавлении нового
  Pitfall/фичи — минимум 3 теста (basic, edge, false positive).
- **`references/mcp-live-probe-cookbook.md`** — рецепт MCP probe перед
  большой правкой индикатора. Список команд для `list_views` и
  `get_view`, как парсить ответ.
- **`references/mcp-methods-playbook.md`** — справочник по всем методам
  MCP (`initialize`, `notifications/initialized`, `tools/call` →
  `get_view` / `get_entity_data` / `find_entity`), используемым скиллом:
  сигнатура, где применяется (по секциям/индикаторам), параметры,
  скрипты, edge cases.
- **`references/indicator-6-12-vat-amount-format.md`** — формат текста
  6.12 (Pitfall #218 «Нет,» без (+N)), приоритеты полей
  `pick_amount_by_priority`, конкретный пример 504-595 (июль 125 тыс. ₽,
  август 75 тыс. ₽), формула `НДС = сумма/21`, открытые вопросы v1.1.0
  (почему НДС 125 000 ≠ расчётный 119 047.62).
- **`references/html-report-structure-etalon-26.md`** — структура
  эталонного отчёта 26: 6 секций, заголовки по канону, формат ячеек
  секции 6 «Результат» («Да — Forecast: ... → критическое»).
- **`references/section-6-backlog-2026-09-03.md`** — отложенные требования
  по секции 6. **Читать первым** при загрузке skill, если секция 6 снова
  в работе. Содержит список выполненных и невыполненных требований с
  привязкой к Pitfall'ам.
- **`references/mcp-token-jwt-extract.md`** — рецепт извлечения
  displayname из JWT-токена PMForesight. Подробности формата payload,
  fallback на givenname claim.
- **`references/point-allfinancepoint-view.md`** — view `Point/AllFinancePoint`
  (Pitfall #214). Финансовые КТ с `ParentEntityName=InContract` + поля
  `PlanSum`/`ForecastSum`/`FactSum` одним запросом (без `get_entity_data`).
  Содержит таблицу всех 9 view для сущности `Point`, сравнение с
  `AllMyPoint`, и рекомендацию для скилла `project-payment-schedule` (оптимизация).
- **`references/transport-and-portability.md`** — что нужно для переноса
  скилла на другой сервер, как настроить `.env`, какие зависимости.
- **`references/dependencies.md`** — все зависимости скилла (связанные скиллы,
  Python-зависимости, thresholds, MCP-сервер, документация, тесты).
  Использовать при переносе, аудите, отладке.

---

## Новые Pitfalls (v1.0.15, записаны по следам сессии)

46. **Pitfall #229 уже существует (subagent v1.0.15)** — «не перефразировать
    постановки пользователя». Подробности см. в Critical Pitfalls #5.
    Здесь только **уточнение** (NEW): когда пересказываешь требования в
    документации (playbook, references), пользователь часто **откатывает**
    («Убери последнее обновление playbook»). Lesson: **дословные цитаты**
    (в кавычках) с датой и контекстом. Никаких собственных формулировок.

47. **Не хардкодить пользователя в коде (Pitfall #219, NEW v1.0.15,
    2026-09-04)** — «Пользователь» в отчёте (раздел 8 «Технические данные»)
    **ВСЕГДА** берётся из JWT-токена `PMP_TOKEN` через
    `get_current_user_from_token()`. Симптом: «Это не правильно! Должен
    быть тот пользователь, с токеном которого вызывается отчет!».
    **НЕ работает:** `OwnerId` проекта, хардкод в коде (`"Кузнецов\n    Ростислав Владимирович"` = баг), `auth.json` (там пусто в профиле
    fst-control).
    **Edge case:** если `get_current_user_from_token()` падает с ошибкой
    → возвращает `"—"` (прочерк), а **НЕ** хардкод.
    Реализация — Pitfall #213.

48. **Pitfall #225 уже существует (subagent v1.0.14)** — про
    перефразирование постановок. Дубликат убран (см. #46).
    конкретные формулировки — копировать, не выдумывать. Это частный
    случай Pitfall #229.

49. **Pitfall #225 уже существует (от subagent) — не дублировать** —
    subagent уже добавил Pitfall #225 «Не перефразировать постановки
    пользователя (NEW v1.0.15)» в Top-10. Pitfall #229 в этой
    секции — **расширенная** версия с правилами дословного цитирования.

50. **Применение reference-палитры (handoff-документа с цветами) — workflow
    (NEW, 2026-09-15)** — когда пользователь присылает документ-палитру
    (например, «Цветовая гамма отчёта AGPM Portfolio» как markdown с
    таблицей токенов `--bg/--paper/--ink/--hero-*`) и говорит «примени»,
    **не угадывать** соответствия и **не править** каждый hex в
    `templates/report.css` руками по памяти:
    1. **Сначала** добавить `:root { --<token>: <hex>; ... }` блок **целиком**
       в начало `templates/report.css`. Все токены из эталона — одной пачкой.
    2. **Потом** сопоставить токены эталона с текущими правилами CSS и
       поменять **только те правила, которые имеют прямой аналог**. Остальные
       правила (старые hex без аналога) — оставить как есть, **не выбрасывать**
       (есть риск сломать другие места, использующие их).
    3. Если пользователь сказал «отчёт по умолчанию должен работать в
       новых цветах» и «фон как в AGPM» — менять body `background` и
       `color`, **не оставляя старые значения как fallback**.
    4. Если пользователь сказал «оставь X как был» (например,
       `informational` синий `#dbeafe` остаётся 5-м статусом в секции 6) —
       **не трогать** соответствующее правило, только добавить переменную
       если её нет.
    5. **Всегда** собирать playbook-маппинг: «что совпало, что близко
       (но не идентично), что неперенесённое и почему» — и приложить как
       `references/color-palette-mapping.md`. Это делает правки
       воспроизводимыми при следующей итерации.
    **Симптом ошибки:** правишь CSS руками без `:root` → позже приходит
    запрос «верни как было для раздела Y, X не трогай» и непонятно, что
    было оригиналом, потому что уже всё свалено в одну палитру.

51. **Header (раздел 1) = Hero-блок (NEW, 2026-09-15)** — по запросу
    пользователя от 2026-09-15 «настройки HERO примени к разделу 1
    Header». CSS-структура `.report-header` соответствует Hero из
    reference-палитры AGPM:
    - `.report-header-text` и `.report-indicator`: фон = градиент
      `linear-gradient(135deg, var(--navy) 0%, var(--hero-middle) 56%, var(--teal) 100%)`.
    - `.report-header-prefix` (eyebrow): `var(--hero-eyebrow)`, `text-transform: uppercase`,
      `letter-spacing: 0.5px`.
    - `.report-header-meta`: `color: rgba(255, 255, 255, 0.82)`,
      `<b>` внутри = `#ffffff`.
    - `.report-header`: `box-shadow: 0 20px 44px rgba(16, 24, 40, 0.16)`.
    - `.report-header-title`: `color: #ffffff` (НЕ `#fffcfc` — старое
      значение из v1.0.x; это отступление от «инстинкта делать off-white»).
    Эти правила обязательны, если в `templates/report.css` объявлены
    AGPM-токены `--navy / --hero-middle / --teal / --hero-eyebrow`. Если
    токенов нет (legacy отчёт) — Header остаётся на старой синей заливке
    `#2563eb`.