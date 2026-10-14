# Foresight MCP — всплывшие проблемы при составлении письма разработчикам (2026-08-07)

Это **дополнение** к `references/forsight-mcp-quirks.md` (pitfalls 1–18). Зафиксировано
при подготовке обстоятельного отчёта разработчикам MCP: были запущены прямые
SSE-probe (`scripts/mcp_probe.py`) для каждой проблемной точки. Часть того, что
обнаружено, **опровергает задокументированную** в `references/project-finance-budget-entities.md`
информацию — будьте внимательны.

> **Контекст:** в `Вопросы по MCP 2026_08_07.md` (корень профиля) собран полный
> отчёт разработчикам с 7 блокирующими проблемами + 7 неудобствами. Здесь —
> **техническая выжимка** для самого скилла: какие поля в каких сущностях
> **реально отсутствуют**, какие view какие коды возвращают, и как на это
> реагировать.

---

## F1. `MetaModel` — сущность есть, но `find_entity` возвращает 0 записей

Запросы:

```bash
python3 scripts/mcp_probe.py --tool find_entity \
  --args '{"name":"SystemTitle","limit":50}'
# {"items":[],"total":0,"limit":50,"offset":0}  ← пусто

python3 scripts/mcp_probe.py --tool find_entity \
  --args '{"name":"Title","limit":50}'
# {"items":[],"total":0,"limit":50,"offset":0}

python3 scripts/mcp_probe.py --tool find_entity \
  --args '{"name":"ProductName","limit":50}'
# {"items":[],"total":0,"limit":50,"offset":0}

python3 scripts/mcp_probe.py --tool find_entity \
  --args '{"name":"ИСФ","limit":50}'
# {"items":[],"total":0,"limit":50,"offset":0}
```

**Подтверждает pitfall #8** в `forsight-mcp-quirks.md` — `find_entity` для MetaModel
работает не так, как для обычных сущностей. Любой `name` даёт 0.

**НО:** была ещё гипотеза, что это просто неправильное имя ключа. Probe показал,
что **`find_entity` для MetaModel вообще не находит записи** — это не выбор query,
это ограничение самого `find_entity` для этой сущности. `find_entity` **не
является** general-purpose-запросом для MetaModel.

**Что это значит для скилла:** Раздел 7 показатель 2 «Титул системы» — ставим
«Нет данных (find_entity MetaModel — validation error)» **на любой стадии ЖЦ**.
Не пытаемся угадывать имя поля.

---

## F2. `MetaModel` — `get_entity_data` ломается SQL-ошибкой на id=1 и id=2

```bash
python3 scripts/mcp_probe.py --tool get_entity_data \
  --args '{"entityName":"MetaModel","data_id":"1"}'
# Error: 500 - оператор не существует: character varying = bigint

python3 scripts/mcp_probe.py --tool get_entity_data \
  --args '{"entityName":"MetaModel","data_id":"2"}'
# Error: 500 - оператор не существует: character varying = bigint
```

**Раньше pitfall #8** говорил что `find_entity` падает с Pydantic-ошибкой
«Missing required argument». Это было неправильно — реально `find_entity`
отдаёт пустой `items` (без ошибки), а ломается именно `get_entity_data` —
SQL-ошибка со стороны Форсайт.

**Что это нам говорит:**
- Вероятно, `MetaModel` в БД имеет несовместимость типов в JOIN для lookup
  по id (например, `parent_id` character varying vs `id` bigint).
- Т.к. `find_entity` и `get_view` для MetaModel тоже не работают, **сущность
  фактически недоступна на read**.
- На стороне скилла — единственное разумное: «Нет данных», просим разработчиков
  Форсайт починить или назвать правильный API.

---

## F3. `get_view` для MetaModel — вообще нет представлений

```bash
python3 scripts/mcp_probe.py --tool get_view \
  --args '{"entityName":"MetaModel","viewName":"AllMetaModel","limit":5}'
# Error: Конечная точка не найдена по адресу .../view/AllMetaModel.
#   Укажите корректный URL в заголовке X-Base-Url  ← странный текст, но 404

python3 scripts/mcp_probe.py --tool get_view \
  --args '{"entityName":"MetaModel","viewName":"MetaModel","limit":5}'
# Error: Для сущности 'MetaModel' нет доступных представлений.
```

**Вторая строка — это нормальная ошибка от самого MCP**: «У сущности MetaModel
нет view в реестре». Т.е. `MetaModel` — это **singleton/key-value** сущность,
которая не предназначена для view-вызовов. И `get_entity_data` ломается
(F2). И `find_entity` молчит (F1).

**Вывод для скилла:** MetaModel — **мёртвая** сущность для текущего read-API.
Не надо пробовать `get_view` или `get_entity_data` — оба пути не работают.

---

## F4. `Point.PlanSum` / `ForecastSum` / `FactSum` — НЕ None в recipe, **None в реальности**

Recipe `references/project-finance-budget-entities.md` (и pitfall #10)
утверждают:

> В `Point` (68 полей) — Поля с финансовыми данными (на КТ):
> `PlanSum`, `ForecastSum`, `FactSum`, `StageSum`, `StageSumNumber`, `PctComplete`.
> Доступ через `get_entity_data(Point, data_id="4725")` — открыт.

Реально:

```bash
python3 scripts/mcp_probe.py --tool get_entity_data \
  --args '{"entityName":"Point","data_id":"1686"}'
# {"properties":{
#   "ActivityId":1686,
#   "PctComplete":0,
#   "PlanSum":None,        ← NULL!
#   "ForecastSum":None,    ← NULL!
#   "FactSum":None,        ← NULL!
#   "FactSumAct":None,
#   "FactSumPaid":None,
#   "ActivityResultPoint":[],
#   ...
# }}
```

**Это для КТ 1686 (`101-686`), которая входит в проект 501-682.** Поля существуют
в схеме (`describe_entity` показывает их), но **не заполнены**.

**Когда поля заполняются:** возможно, только когда к КТ привязаны
`ContractPlanSummariesValue` (которые 403 для обычного пользователя). Получается,
что **закрытость view `ContractPlanSummaries*` блокирует заполнение
`Point.PlanSum/ForecastSum/FactSum`**.

**Что это значит для скилла:**
- Раздел 5 (Прогнозы по КТ) — **нельзя** показать «план/факт/прогноз» по КТ
  через `get_entity_data(Point, ...)`. Поля будут None.
- Раздел 6 — финансовый план/факт проекта надо брать **только** из
  `ProjectHealthCostMy` (открытый view).
- Recipe `project-finance-budget-entities.md` сейчас вводит в заблуждение —
  она говорит «получай через get_entity_data(Point)», но реально там None.

**FIX:** recipe нужно переписать с упоминанием того, что `PlanSum/ForecastSum/FactSum`
в `Point` **часто None** для КТ без привязки к `ContractPlanSummariesValue`. Если
None — fallback на `ProjectHealthCostMy` (агрегат по проекту, не по КТ).

---

## F5. `Project.PlanSum` / `ForecastSum` / `FactSum` — **НЕ существуют** в схеме

Recipe `project-finance-budget-entities.md` утверждает:

> В `Project` (68 полей)
> Поля с финансовыми данными:
> - `PlanSum` — плановая сумма
> - `ForecastSum` — прогнозная сумма
> - `FactSum` — фактическая сумма
> - `ProjectBudgetGrade` (numeric) — бюджет проекта (оценка), руб.
> - `DirectProjectCostsGrade` (numeric) — прямые затраты проекта (оценка), руб.
> - `PresaleLimit` (numeric) — лимит на пресейл
> - `PresaleBudgetPercentage` (numeric) — % пресейла от бюджета

**Реально через `describe_entity(Project, "4595")` получены только:**

```
PlanUrl: character varying
Explanation: character varying
ProjectBudgetGrade: numeric
DirectProjectCostsGrade: numeric
IsUseInResourcePlan: boolean
PresaleBudgetPercentage: numeric
OutcomeContractActivity: bigint
```

**`PlanSum`, `ForecastSum`, `FactSum` отсутствуют в схеме Project.** Эти поля
есть только в `Point` (КT), см. F4.

**Что это значит для скилла:**
- Нельзя делать `project["PlanSum"]` или `project["FactSum"]` — будет
  KeyError (если через `properties["PlanSum"]` — будет `{}` без value).
- Все финансы на уровне проекта — через `ProjectHealthCostMy` (view) —
  поля `plan`, `forecast`, `fact`, `deviation`, `inplan`, `infact`, `outplan`,
  `outfact`, `outallplan`, `outallforecast`, `devcost`, `devallcost`.
- `ProjectBudgetGrade` и `DirectProjectCostsGrade` — другие величины (см. F6).

---

## F6. `ProjectBudgetGrade` vs `ProjectHealthCostMy.plan` — нет документации по семантике

**Данные 504-595 (ProjectId=4595):**

```bash
python3 scripts/mcp_probe.py --tool get_entity_data \
  --args '{"entityName":"Project","data_id":"4595"}'
# {"properties":{
#   "ProjectBudgetGrade":{"value":54000000.0},
#   "DirectProjectCostsGrade":{"value":32000000.0},
#   "PresaleLimit":{"value":2700000.0},
#   "PresaleBudgetPercentage":{"value":5.0},
#   "ProjectProfileId":{"value":1,"display":"Базовый"}
# }}

python3 scripts/mcp_probe.py --tool get_view \
  --args '{"entityName":"Project","viewName":"ProjectHealthCostMy","limit":2000}'
# {"id":108,"projectid":4595,
#  "inplan":6497500.0,"infact":2500000.0,
#  "outplan":75000.0,"outfact":3244415.0,
#  "fact":-744415.0,
#  "outallplan":75000.0,"outallforecast":4221860.0,
#  "plan":6422500.0,"forecast":-221860.0,
#  "deviation":-6644360.0,"devcost":3340856.0,"devallcost":4146860.0}
```

**Вопросы без ответа:**
- `ProjectBudgetGrade = 54 000 000` vs `plan = 6 422 500` из `ProjectHealthCostMy` —
  разница в **8.4 раза**. Что это? План при инициировании vs текущая
  согласованная сумма?
- `DirectProjectCostsGrade = 32 000 000` vs `fact = 744 415` — разница
  в **43 раза**. Что это?
- `PresaleLimit` (2 700 000) и `PresaleBudgetPercentage` (5%) — что это за
  проценты? От чего? Зачем нужен преcейл-лимит?
- `ProjectProfileId = 1` («Базовый») — это **профиль шаблона проекта**, а не
  сам проект. То есть скилл должен понимать, что `Grade` — это **сумма по
  шаблону**, а не по конкретному проекту.

**Что это значит для скилла:** **не использовать** `ProjectBudgetGrade` /
`DirectProjectCostsGrade` для отчёта, пока нет документации. Использовать
только `ProjectHealthCostMy` (агрегат).

**Вопросы к разработчикам Форсайт:**
- Что такое `ProjectBudgetGrade`? Это оценка на момент открытия или текущее
  значение?
- Если это оценка, то почему она в 8 раз больше `plan` из cost-view?
- Документировать `ProjectBudgetGrade`, `DirectProjectCostsGrade`, `ProjectLimit`,
  `PresaleLimit`, `PresaleBudgetPercentage`.

---

## F7. `ProjectHealthCostMy` — одни null-поля для проекта 503-152 (Пресейл)

```bash
python3 scripts/mcp_probe.py --tool get_view \
  --args '{"entityName":"Project","viewName":"ProjectHealthCostMy","limit":100}'
# {"id":99,"projectid":3152,
#  "fact":-4995218.6385,
#  "forecast":-37489319.853,
#  "plan":null,                    ← NULL!
#  "deviation":null,               ← NULL (зависит от plan)
#  "devcost":null,                 ← NULL
#  "devallcost":null,              ← NULL
#  "projectprofileid":1,
#  "projectprofilename":"Базовый"}
```

**Project 503-152 (Пресейл, 3152) — все «deviation»/«devcost» поля null.**
Это блокирует раздел 6 показатель 2 («отклонение текущей стоимости от плана на
более 1 млн») и показатель 3 («уменьшение forecast по сравнению с plan»).

**На стороне скилла:** для Пресейл-проектов раздел 6 показывает только
показатель 1 (forecast < 0). Остальные два — «Неопределено (нет plan)». Это
**нормальное** поведение, не баг.

**Но для активных проектов (504-595)** — те же поля **заполнены**
(`plan=6422500`, `deviation=-6644360`). Значит, проблема только в Пресейл.

**Просьба к разработчикам:** для Проекта в стадии Пресейл где `plan` не
планируется — отдельный статус `null` (не путать с «план = 0»).

---

## F8. `ProjectHealthCostMy` — НЕТ «as_of_date» / периода — семантика неясна

```bash
python3 scripts/mcp_probe.py --tool get_view \
  --args '{"entityName":"Project","viewName":"ProjectHealthCostMy","limit":100}'
# {"id":108,"projectid":4595,
#  "fact":-744415.0,
#  "forecast":-221860.0,
#  "plan":6422500.0,
#  "deviation":-6644360.0,...}
```

**Что непонятно:**
- `fact = -744 415` — это **кумулятивный** факт на сейчас? Или только за
  последний **закрытый** месяц? Или за последний **период**?
- `forecast = -221 860` — это **прогноз на окончание проекта**? Или **текущий
  месяц**?
- `deviation = -6 644 360` — `forecast - plan` = `-221 860 - 6 422 500 = -6 644 360`.
  **Верно!** Это значит `deviation` = `forecast - plan`. Но непонятно, какой
  `forecast` — на окончание или на текущий момент.
- `devcost = 3 340 856` — что это? `outallforecast - outplan` = `4 221 860 - 75 000` = `4 146 860`. **Не сходится.** Либо `devcost` — это процент, либо другая формула.

**Просьба:** формальный glossary полей `ProjectHealthCostMy`:
- `fact` — кумулятивный/закрытый месяц/текущий месяц/период?
- `forecast` — на окончание проекта или на текущий месяц?
- `plan` — на окончание или на текущий?
- `devcost` vs `devallcost` — формулы?
- `outplan` vs `outallplan` — разница?

---

## F9. `AllPayments` — нет `ProjectId` / `ContractId` / `ActivityId`

```bash
python3 scripts/mcp_probe.py --tool get_view \
  --args '{"entityName":"Payments","viewName":"AllPayments","limit":5}'
# {"data":[
#   {"id":1,"PaymentsId":1118,"Name":"Оплата вознаграждения...",
#    "InvoiceNumberAndDate":"Счет на оплату...",
#    "ActivityName":"500-656. РОСАТОМ. АСУ-ИНВЕСТ. ИС Сириус 2024...",
#    "FinanceSourceName":"414.  Прочее бухгалтерия.",
#    "SumRub":316.75,"Date":"2025-12-25T00:00:00+03:00",
#    "ContractorName":"ПАО \"Банк ПСБ\"","ContractorId":10304,
#    "CompanyName":"АТР","CompanyId":4},
#   ...
# ]}
```

**Есть `ActivityName` (текстовое имя активности) — но НЕ `ActivityId`**
как колонка view. Также нет `ProjectId` (проекта) и нет `ContractId`
(контракта).

**Проблема**: чтобы отфильтровать платежи по проекту, приходится парсить
текстовое поле `ActivityName` (= «500-656. РОСАТОМ. АСУ-ИНВЕСТ. ИС Сириус 2024
и 2025 (5О) .»). Это ненадёжно (пробелы, переименования, точки), и
для Пресейл-проекта `ActivityName` может быть пустым.

**Просьба:** добавить `ProjectId`, `ContractId`, `ActivityId` как колонки view.

---

## F10. `Point` view `AllMyPoint` — `ParentFullName = null` в строке

```bash
python3 scripts/mcp_probe.py --tool get_view \
  --args '{"entityName":"Point","viewName":"AllMyPoint","limit":5}'
# {"data":[
#   {"id":1686,"PointId":1686,"Code":"101-686","ParentCode":"501-682",
#    "ParentFullName":null,...},  ← null!
#   ...
# ]}
```

**Подтверждает pitfall #1 и #17 в `forsight-mcp-quirks.md`**: `ParentFullName`
для привязки к проекту **нужен в view rows**, но в реальности **получить
его через view нельзя** — null. Нужен fallback `get_entity_data` для активности.

**Дополнительная проблема:** `ParentCode` в view — это **код активности**
(`501-682`), а **не проекта**. Фильтр `row["ParentCode"].startswith("504-595")`
**НЕ сработает** — это другой уровень иерархии.

**Просьба:** добавить `ParentFullName` как колонку view `AllMyPoint` и
`AllPoint` (см. также pitfall #17 про contract binding).

---

## F11. `find_entity` без `entityName` — то же, что `find_entity` с любым `entityName`

```bash
python3 scripts/mcp_probe.py --tool find_entity \
  --args '{"entityName":"MetaModel","limit":50}'
# {"items":[],"total":0,"limit":50,"offset":0}  ← пусто
```

**Предположение:** вызов `find_entity` с `entityName="MetaModel"` отфильтрует
по сущности. **Реально:** нет — он ищет по `name` (text), и для MetaModel
возвращает 0 (потому что find_entity сломан для MetaModel, см. F1).

**Неудобство:** нет отдельного `find_entity_by_entity(entityName, ...)` —
приходится смотреть **все** сущности. `find_entity` возвращает `items` с
полем `entityName` в каждом, но нужно знать как фильтровать.

**Просьба:** разделить `find_entity` (по name) и `find_entity_by_entity`
(по entityName). Или добавить `entityName` как опциональный фильтр.

---

## Чек-лист при работе с фин. данными (обновлённый)

- [ ] **НЕ использовать** `Project.PlanSum/ForecastSum/FactSum` — этих полей нет в схеме
- [ ] **НЕ рассчитывать** на `Point.PlanSum/ForecastSum/FactSum` — они **часто None** без `ContractPlanSummariesValue`
- [ ] **Использовать** `ProjectHealthCostMy` для агрегата на уровне проекта (поля `plan`, `forecast`, `fact`, `deviation`, `inplan/outplan` и т.д.)
- [ ] **Обрабатывать null** в `plan`/`deviation` — это стадия Пресейл, нормально
- [ ] **Не угадывать** семантику `ProjectHealthCostMy` — запрашивать glossary у разработчиков
- [ ] **Не угадывать** `ProjectBudgetGrade` vs `plan` — без документации не использовать
- [ ] **Платежи** фильтровать по `ActivityName` (текстовое имя) как last resort, просить разработчиков добавить `ProjectId`/`ContractId`/`ActivityId`
- [ ] **КТ связи** использовать fallback `get_entity_data(Activity, ...)` для получения `ParentFullName` (в view null)
- [ ] **MetaModel** признать сломанной сущностью (find_entity 0, get_view 404, get_entity_data 500 SQL)

---

## Связь с другими references

- `references/forsight-mcp-quirks.md` — базовые pitfalls 1–18. Расширяет их
  конкретными пробами где recipe был неправильным.
- `references/project-finance-budget-entities.md` — **УСТАРЕЛ**, требует
  правки (см. F4, F5, F6, F8).
- `references/effort-data-403-recipe.md` — подтверждает, что
  `ProjectHealthWorkload` возвращает `projectprofileid` (НЕ `projectid`),
  что критично для любых фин. расчётов.
- `references/contract-binding-via-parentfullname.md` — связан с F10,
  контракт↔проект логика.
- `references/jc-stage-indicator-allowlist.md` — связан с F7 (Пресейл
  имеет `plan=null` в cost-view).

---

*Зафиксировано 2026-08-07 при подготовке `Вопросы по MCP 2026_08_07.md`. Не
заменяет `forsight-mcp-quirks.md` — дополняет его.*
