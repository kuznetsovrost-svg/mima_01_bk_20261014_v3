# GRACE-DOCX v3 — Playbook по использованию

> Подробный гайд по **GRACE-DOCX v3** (Element-Aware Bootstrap) — порту методологии GRACE на Office-документы от Mike Evdokimov (`@xronocode`). Лицензия MIT.
> Источник: репозиторий [xronocode/grace-docx](https://github.com/xronocode/grace-docx) (v3.0.0 для DOCX, preview v1 для PPTX). Гайд собран из README, `grace-docx-bootstrap.md` (полный v3 init-prompt), `docs/schema-v3.md`, `docs/release-v3.md`, `docs/v3-transition.md`, `docs/pptx-schema-v1.md` и CHANGELOG.
>
> Цель — дать вам **необходимый и достаточный** объём знаний, чтобы применять GRACE-DOCX к большим (1000+ страниц) текстовым документам, в т.ч. с таблицами, графиками, SmartArt и изображениями, и решать три задачи: **генерация без дрейфа**, **связные изменения при правках проекта**, **RAG-граф по всей документации**.

---

## 0. Ориентация за 60 секунд

**GRACE-DOCX** решает одну узкую, но острую проблему: **большие `.docx` враждебны к AI-редактированию**. На 50 страницах LLM вынужден сканировать тысячи XML-узлов, угадывать границы секций, не различать «живой» график и вставленную картинку, забывать про cross-link с приложением. К пятой итерации правки дрейфуют, появляются «исправления того, что не просили».

**Корень проблемы — context rot:** модели эффективно используют только 10–20% декларируемого контекстного окна; accuracy падает на 30%+ когда релевантный контент сидит в середине длинного контекста. Увеличение окна не лечит — откладывает.

**Решение GRACE-DOCX:** превратить `.docx` в **self-describing package**, инжектировав в него машинно-читаемый слой. Визуальное отображение **не меняется** — добавляются только 5 XML-частей под `word/` + invisible Word-bookmarks. После этого любой агент знает, **где** секция, **что внутри** (таблица / график / SmartArt / картинка), **что можно трогать**, и **как проверить**, что ничего не сломалось.

**Главный сдвиг v3:** v1 отвечал только «где целевая секция?». v3 добавляет второй вопрос — «что именно внутри, и как безопасно редактировать?». Это **element-aware** вместо section-aware.

**Главные принципы (портированы из GRACE):**
- **Contract-first** — read TypeContract → check ModuleContract overrides → satisfy both.
- **Bookmark integrity** — bookmarks paired, never delete/split/misalign.
- **Graph is current** — add/remove content → update `grace-graph.xml`.
- **Verify after edit** — run `grace-verification.xml`; rollback при hard-severity failure.
- **Surgical edits** — only what asked, match existing styles exactly, preserve metadata.
- **Element-type awareness** — перед правкой таблицы/графика проверить его тип в `<ELEMENTS>`.

---

## 1. Что лежит внутри GRACE-DOCX

### 1.1 Пять XML-частей под `word/`

| Файл | Обязателен | Назначение |
|---|:---:|---|
| `word/grace-manifest.xml` | да | Discovery beacon, протокол чтения, output policy, bookmark convention |
| `word/grace-instructions.xml` | да | Принципы, edit rules, anti-patterns |
| `word/grace-graph.xml` | да | Карта модулей (H1-секции), paragraph ranges, bookmarks, **element inventory** |
| `word/grace-contracts.xml` | да | GlobalRules + TypeContracts + ModuleContracts (per-module overrides) |
| `word/grace-verification.xml` | да | Structural invariants + post-edit checks |

Плюс **invisible Word-bookmarks** вокруг каждой H1-секции:

```xml
<w:bookmarkStart w:id="100" w:name="GRACE_M-XXX"/>
...
<w:bookmarkEnd w:id="100"/>
```

Паттерн: `GRACE_{MODULE-ID}`.

### 1.2 Что НЕ меняется при bootstrap

Визуальное отображение документа. Все `rsidR / paraId / textId` атрибуты. Существующие стили. Это **только инъекция** метаданных.

### 1.3 Hard constraints bootstrap

- **Never modify visible content during bootstrap** — только bookmarks и XML metadata parts.
- **Preserve all existing XML attributes** — `rsidR`, `paraId`, `textId` и пр.
- **Keep bookmarks balanced** — каждая пара `bookmarkStart/bookmarkEnd` идёт вместе.
- **Reference file existence** — все `source` атрибуты в `<ELEMENTS>` должны указывать на реально существующие файлы внутри пакета.

---

## 2. Module shape (как выглядит «модуль документа»)

```xml
<M-XXX>
  <n>[heading text]</n>
  <TYPE>[NARRATIVE|DATA|MIXED|NAVIGATION|META|REFERENCE]</TYPE>
  <BOOKMARK>GRACE_M-XXX</BOOKMARK>
  <PARA-START>[H1 paragraph index]</PARA-START>
  <PARA-END>[paragraph before next H1 or end]</PARA-END>
  <SubSections/>
  <ELEMENTS/>
</M-XXX>
```

**Module TYPE** — назначается по преобладающему контенту H1-секции:

| TYPE | Когда ставится |
|---|---|
| `NARRATIVE` | В основном prose-параграфы |
| `DATA` | В основном TABLE-DATA или CHART-NATIVE |
| `MIXED` | Проза + таблицы + графики |
| `NAVIGATION` | TOC, index, list of figures |
| `META` | Title page, cover, colophon |
| `REFERENCE` | Glossary, definitions, appendix entries |

### 2.1 Идентификация модуля: правила именования

- Inline override `module-ids` если задан пользователем.
- Иначе деривация из section/heading: 2-5 uppercase characters, intuitive.
- Спецкейсы: первая title-страница → `M-COVER`; agenda → `M-AGENDA`; последняя closing → `M-END`.
- IDs должны быть **уникальны** в документе.
- После bootstrap **никогда** не переименовывать модуль молча — это ломает все cross-link'и и bookmarks.

---

## 3. Element types: что внутри модуля

`<ELEMENTS>` — главное нововведение v3. Для каждого H1-модуля агент инвентаризует **всё не-текстовое содержимое** и типизирует:

| Element type | Editable | Source of truth (внутри .docx) |
|---|:---:|---|
| `TABLE-DATA` | Data rows, cell values | `word/document.xml` |
| `TABLE-STRUCT` | Cell text only | `word/document.xml` |
| `CHART-NATIVE` | Labels, values | `word/charts/chartN.xml` (+ optional embedded workbook) |
| `CHART-IMAGE` | **No** (read-only) | `word/media/imageN.*` |
| `CHART-SMARTART` | Text nodes only | `word/diagrams/dataN.xml` (не `layoutN.xml`!) |
| `VISUAL-IMAGE` | **No** (read-only) | `word/media/imageN.*` |
| `EMBEDDED` | No direct XML edit | Требуется host application |

### 3.1 Пример `<ELEMENTS>` в модуле

```xml
<M-PROC>
  <n>Approval Process</n>
  <TYPE>MIXED</TYPE>
  <BOOKMARK>GRACE_M-PROC</BOOKMARK>
  <PARA-START>120</PARA-START>
  <PARA-END>248</PARA-END>
  <ELEMENTS>
    <element type="TABLE-DATA" para-index="144" columns="4" rows="12"/>
    <element type="CHART-NATIVE" subtype="BAR" para-index="190" source="word/charts/chart1.xml"/>
    <element type="VISUAL-IMAGE" para-index="220" source="word/media/image2.png" readonly="true"/>
  </ELEMENTS>
</M-PROC>
```

### 3.2 Ключевые атрибуты element

| Element | Ключевые атрибуты |
|---|---|
| `TABLE-DATA` | `para-index`, `columns`, `rows` |
| `TABLE-STRUCT` | `para-index`, `columns`, `rows` |
| `CHART-NATIVE` | `subtype`, `source`, `embedded-data` (если есть workbook) |
| `CHART-IMAGE` | `source`, `readonly="true"` |
| `CHART-SMARTART` | `data-source`, `layout-source`, `text-editable="true"`, `topology-editable="false"` |
| `VISUAL-IMAGE` | `source`, `readonly="true"` |
| `EMBEDDED` | `readonly="true"` |

### 3.3 Почему это критично для AI-редактирования

Без типизации агент склонен:
- Менять `word/document.xml` рядом с `<w:drawing>` и сломать ссылку на chart.
- Принять `CHART-IMAGE` за живой график и пытаться «обновить данные» в PNG.
- Тронуть `word/diagrams/layoutN.xml` (топологию SmartArt) вместо `dataN.xml` (текст).

`<ELEMENTS>` + `TypeContracts` явно говорят агенту: «вот эта штука — readonly», «вот эту — редактируй через `chartN.xml`, не через `document.xml`», «вот эту — только текст, не топологию».

---

## 4. Contract resolution: как агент решает, что можно

**Строгий порядок разрешения прав (strictest wins):**

1. **GlobalRules** из `grace-contracts.xml` — applies to whole document.
2. **Element type** из `grace-graph.xml` — определяет `TypeContract`.
3. **TypeContract** — правила для данного element type независимо от модуля.
4. **ModuleContract** — overrides для конкретного модуля (`can-edit` / `cannot-edit` / `must-sync`).
5. **Apply the strictest relevant rule.**

Если у юзера явная инструкция выйти за эти рамки — explicit user instruction перебивает (но это уже за пределами safe-edit протокола).

### 4.1 Структура `grace-contracts.xml`

```xml
<GraceContracts VERSION="3.0.0">
  <GlobalRules>
    <rule severity="hard">Never remove or merge GRACE bookmark pairs</rule>
    <rule severity="hard">Never edit CHART-IMAGE source raster</rule>
    <rule severity="soft">Match surrounding paragraph style when adding content</rule>
    ...
  </GlobalRules>

  <TypeContracts>
    <C-NARRATIVE>
      <description>Prose sections: paragraphs, bullets, numbered lists</description>
      <can-edit>Add paragraphs after existing content, modify text runs, update numbered/bulleted items</can-edit>
      <cannot-edit>Change heading styles, modify list numbering format, alter paragraph indentation</cannot-edit>
    </C-NARRATIVE>

    <C-TABLE-DATA>
      <description>Data tables: header row + data rows</description>
      <can-edit>Add rows, edit data cells, preserve columns</can-edit>
      <cannot-edit>Change column count, rename headers, restructure</cannot-edit>
    </C-TABLE-DATA>

    <C-CHART-NATIVE>
      <description>Live Office chart (bar/line/pie etc.)</description>
      <can-edit>Edit chart XML in word/charts/chartN.xml, or linked embedded workbook</can-edit>
      <cannot-edit>Edit document.xml drawing wrapper, change chart subtype, restyle</cannot-edit>
    </C-CHART-NATIVE>

    <C-CHART-SMARTART>
      <description>SmartArt diagram: process flow, org chart, pyramid, cycle</description>
      <can-edit>Text content in word/diagrams/dataN.xml nodes</can-edit>
      <cannot-edit>word/diagrams/layoutN.xml — topology, node count, connection structure</cannot-edit>
    </C-CHART-SMARTART>

    <C-TABLE-STRUCT>
      <description>Structural matrix: RACI, comparison, layout-style table</description>
      <can-edit>Edit cell text only</can-edit>
      <cannot-edit>Add/remove rows or columns, change cell structure</cannot-edit>
    </C-TABLE-STRUCT>

    <C-CHART-IMAGE>
      <description>Raster image of a chart (not a live chart)</description>
      <can-edit>None by default</can-edit>
      <cannot-edit>All</cannot-edit>
    </C-CHART-IMAGE>

    <C-VISUAL-IMAGE>
      <description>Decorative or content image, not a chart</description>
      <can-edit>None by default</can-edit>
      <cannot-edit>All</cannot-edit>
    </C-VISUAL-IMAGE>
  </TypeContracts>

  <ModuleContracts>
    <M-PROC>
      <can-edit>Add rows to tables, add paragraphs after existing content</can-edit>
      <cannot-edit>Do not change table column headers</cannot-edit>
      <must-sync>
        <link>M-XXX -> M-YYY: must-sync: both sections must have matching totals</link>
      </must-sync>
    </M-PROC>
  </ModuleContracts>
</GraceContracts>
```

**`<must-sync>` — это и есть «связные изменения при правках проекта»** (ваше требование №2). Любая правка `M-PROC` обязана проверить, что `M-YYY` остался в синхроне.

---

## 5. Cross-link'и: навигация между модулями

`grace-graph.xml` содержит секцию `<CrossLinks>` для описания связей между модулями и элементами:

```xml
<CrossLinks>
  <link from="M-EXEC-SUMMARY" to="M-FINANCIALS" relation="references">
    <relation>feeds: executive summary numbers come from M-FINANCIALS</relation>
  </link>
  <link from="M-RISKS" to="M-MITIGATIONS" relation="constrains">
    <relation>constrains: every risk in M-RISKS must have a mitigation in M-MITIGATIONS</relation>
  </link>
  <link from="M-PROCESS-A" to="M-PROCESS-B" relation="must-sync">
    <relation>must-sync: total counts must match</relation>
  </link>
</CrossLinks>
```

**Relations:** `feeds` (один модуль — источник данных для другого), `must-sync` (двусторонняя инвариантность), `references` (ссылка), `constrains` (один модуль накладывает ограничения на другой).

**Использование в RAG-графе (ваше требование №3):** CrossLink'и + Module IDs + Element inventory = граф знаний по всей документации. Агент может отвечать на вопросы «где описано X?», «что зависит от Y?», «какие секции протухли после правки M-FINANCIALS?».

---

## 6. Протокол safe-edit (как агент редактирует документ)

```
[grace-docx-bootstrap.md]
[your-document.docx]
"Run bootstrap"
   ↓
[GRACE-enabled.docx]
   ↓
user: "обнови таблицу в секции 4.2"

agent:
1. Unpack .docx
2. Read word/grace-manifest.xml          → протокол, manifest, output policy
3. Read word/grace-instructions.xml      → поведенческие правила
4. Read word/grace-graph.xml            → найти M-XXX секции 4.2, посмотреть <ELEMENTS>
5. Read word/grace-contracts.xml        → TypeContract для TABLE-DATA + ModuleContract для M-XXX
6. Navigate via bookmark GRACE_M-XXX или paragraph range
7. Perform edit according to contract rules for the specific element type
8. Run word/grace-verification.xml      → structural invariants + post-edit checks
9. Repack the .docx (zip)
```

**Если любой hard-severity check из шага 8 падает — rollback.**

---

## 7. Bootstrap процесс (Phase 1-7)

Когда вы говорите агенту `Run bootstrap` для нового `.docx`, он проходит 7 фаз:

### Phase 1: Unpack and Analyze
- Распаковывает `.docx` (это ZIP).
- Читает `word/document.xml`, `word/styles.xml`, `word/numbering.xml`.
- Находит все H1-заголовки → candidate modules.
- Инвентаризует каждый H1: текст, paragraph range, tables, charts, images, SmartArt, embedded objects.
- Резолвит cross-link'и (внутренние ссылки, references, TOC).
- Записывает style fingerprint (шрифты, тема).

### Phase 2: Assign Module IDs
- Применяет inline overrides `module-ids`, если заданы.
- Иначе деривация из section/heading: 2-5 uppercase chars, intuitive.
- Спецкейсы: первая title → `M-COVER`; agenda → `M-AGENDA`; closing → `M-END`.
- Определяет TYPE по преобладающему контенту.

### Phase 3: Create GRACE XML Parts
- Создаёт 5 файлов в `word/`.
- Использует inline overrides где заданы; auto-detect заполняет остальное.

### Phase 4: Inject Bookmarks
- Вокруг каждой H1-секции — пары `<w:bookmarkStart>/<w:bookmarkEnd>` с именем `GRACE_{MODULE-ID}`.
- НЕ изменяет visible content.

### Phase 5: Update [Content_Types].xml and rels
- Регистрирует 5 новых XML-частей в `[Content_Types].xml`.
- Добавляет relationships в `word/_rels/document.xml.rels`.

### Phase 6: Repack
- Только изменённые файлы должны измениться.
- Repack в `.docx` (zip).

### Phase 7: Report

```
═══════════════════════════════════════════
GRACE-DOCX Bootstrap Complete  [v3]
═══════════════════════════════════════════
Document:        [name]
Modules:         [N] identified, [N] bookmarked
CrossLinks:      [N] detected + [N] from overrides
XML parts:       5 injected
Bookmarks:       [N] pairs injected
───────────────────────────────────────────
Element inventory:
  TABLE-DATA:        [N]
  TABLE-STRUCT:      [N]
  CHART-NATIVE:      [N]
  CHART-IMAGE:       [N]
  CHART-SMARTART:    [N]
  VISUAL-IMAGE:      [N]
  EMBEDDED:          [N]
═══════════════════════════════════════════
```

---

## 8. Inline overrides (при bootstrap)

Можно передать агенту вместе с `.docx` YAML-overrides, чтобы переопределить auto-detection:

```yaml
document-name: "Пресейл ФГК 2026"
document-version: "2.1"
output-mode: overwrite            # overwrite | new-version
module-ids:
  "Общее описание": M-OVERVIEW
  "Финансовая модель": M-FIN
  "Риски": M-RISKS
module-boundaries:
  - M-OVERVIEW: paragraphs 5-30
  - M-FIN: paragraphs 31-180
must-sync:
  M-FIN -> M-EXEC-SUMMARY: оба блока должны показывать одинаковые итоги
contracts:
  M-FIN:
    can-edit: обновлять числовые ячейки в TABLE-DATA
    cannot-edit: менять структуру таблиц
  M-EXEC-SUMMARY:
    must-sync: M-FIN — итоги должны совпадать
```

Все поля опциональны. Auto-detection заполняет остальное.

---

## 9. Verification: что проверяется после правки

`grace-verification.xml` содержит:

### 9.1 Structural invariants (всегда должны быть true)

- GRACE-bookmarks balanced and correctly scoped.
- Каждый H1 имеет graph module.
- Все GRACE XML-части well-formed.
- Кол-во колонок в TABLE-DATA / TABLE-STRUCT стабильно.
- Readonly media не изменились (если только явно не заменены).
- Native chart и SmartArt source-файлы существуют.
- SmartArt layout files не изменились.
- Element inventory обновлён при добавлении/удалении таблиц, графиков, изображений.

### 9.2 PostEdit checks (запускаются после каждой правки)

- После добавления/удаления параграфов — re-scan heading positions и обновить все `para-range` в `grace-graph.xml`.
- Сравнить file content до/после для readonly media. Должны быть **identical**.
- Проверить, что модуль, на который ссылается `must-sync`, остался в синхроне.

### 9.3 Severity

- **Hard** — нарушение → rollback обязателен.
- **Soft** — warning, можно игнорировать с explicit user instruction.

---

## 10. Решение ваших трёх задач

### 10.1 AI-генерация без дрейфа и галлюцинаций

**Проблема:** модель «забывает» структуру на длинных документах, выдумывает секции, которые не просил, теряет стиль.

**Как GRACE-DOCX решает:**

| Механизм | Что даёт |
|---|---|
| **Module contracts** (`<ModuleContracts>`) | Жёсткие границы: «вот это можно, вот это нельзя» — модель не «придумывает» структуру |
| **Type contracts** (`<TypeContracts>`) | Явная типизация таблиц/графиков/SmartArt — модель не пытается редактировать PNG как данные |
| **Bookmarks `GRACE_M-XXX`** | Детерминированная навигация — модель точно знает, где находится, не сканирует всё подряд |
| **Element inventory `<ELEMENTS>`** | Модель знает **полный** список editable/readonly объектов до начала правки |
| **Paragraph ranges** `PARA-START`/`PARA-END` | Жёсткая привязка к индексам параграфов — модель не «дрейфует» в соседние секции |
| **Verification** | Hard-check'и после правки; rollback при нарушении |
| **Style fingerprint** | Сохраняет шрифты/тему; модель не «причёсывает» стиль в свой собственный |

**Рекомендации для вашего проекта (документы 1000+ стр.):**

1. **Всегда начинать с bootstrap.** Даже если документ уже есть — `Run bootstrap` сначала. Без GRACE-разметки модель обречена на context rot.
2. **Делить большие документы на несколько .docx.** Если файл > 300 страниц, разнесите по томам с `M-VOL-1-COVER`, `M-VOL-1-TOC`, и т.д. Cross-document links через `<CrossLinks relation="references">` с явным указанием target file.
3. **Module IDs meaningful, не случайные.** `M-FINANCIALS-2026`, `M-RISKS-OPERATIONAL` — не `M-A1B2`. Агент работает лучше, когда имя несёт семантику.
4. **Strict module contracts для авто-генерации.** Если LLM должен сгенерировать секцию с нуля — `cannot-edit` список должен явно запрещать «придумывать» поля, которых нет в спеке.
5. **Per-task verification depth.** Не запускать `grace-verification.xml` на всю тысячу страниц после каждой правки — только на touched-секцию + её `must-sync` партнёров.

### 10.2 Средства взаимосвязанного изменения при правках проекта

**Проблема:** в проекте меняется модуль A (например, добавили endpoint), и это должно отразиться в 5 разделах документации. Без явных связей — каждое место придётся искать вручную.

**Как GRACE-DOCX решает: `<must-sync>` + CrossLink'и**

```xml
<ModuleContracts>
  <M-API-ENDPOINTS>
    <must-sync>
      <link>M-API-ENDPOINTS -> M-OPENAPI-SPEC: spec must list every endpoint</link>
      <link>M-API-ENDPOINTS -> M-CHANGELOG: every new endpoint = changelog entry</link>
      <link>M-API-ENDPOINTS -> M-DEPLOY-GUIDE: new endpoint = new env var section</link>
    </must-sync>
  </M-API-ENDPOINTS>
</ModuleContracts>
```

**Рабочий процесс при правке проекта:**

1. **Сделать правку в коде.** (Не в документе — в коде/системе.)
2. **Запустить diff-агент**, который находит в `.docx` все модули, ссылающиеся на изменённый артефакт (по `LINKS:` и `must-sync`).
3. **Получить список «touched modules»**: например, `M-API-ENDPOINTS` → `[M-OPENAPI-SPEC, M-CHANGELOG, M-DEPLOY-GUIDE, M-FAQ, M-TUTORIAL-AUTH]`.
4. **Для каждого touched module** — обновить контент, прогнать `grace-verification.xml` на нём + его `must-sync` партнёрах.
5. **Запустить `grace-status` (эквивалент)** — общий обзор, какие модули теперь stale.

**Конкретные relations для связности:**

| Relation | Семантика | Когда применять |
|---|---|---|
| `feeds` | Модуль A — источник данных для B | B пересказывает/цитирует A |
| `must-sync` | Двусторонняя инвариантность | Числа/имена должны совпадать (totals, names, version) |
| `references` | B ссылается на A | B упоминает A, но не дублирует |
| `constrains` | A накладывает ограничения на B | Schema, policy, contract |

**В вашем кейсе (проектная документация 1000+ стр.):** создайте отдельный «source of truth manifest» — файл, который перечисляет, какие артефакты проекта (код, схемы БД, API-контракты, конфиги) на какие модули документации влияют. При правке артефакта — grep по manifest, получить список модулей, пройтись по ним.

### 10.3 RAG-граф по всей документации проекта

**Проблема:** документов много (10+ .docx по 1000 стр. каждый = библиотека). Воркеру/ридеу нужно быстро отвечать на вопросы «где описано X?», «что зависит от Y?», «что протухло?».

**Как GRACE-DOCX решает: graceful.xml + CrossLink'и = готовая RAG-база.**

**Шаг 1: индексация.**

Извлечь из каждого GRACE-enabled `.docx`:
- Module ID + heading + TYPE.
- CrossLink'и (relations).
- Bookmarks.
- Element inventory (для фильтрации «у каких модулей есть графики?»).

Хранить в единой БД (SQLite, JSON-lines, или векторная БД + metadata).

**Шаг 2: query patterns.**

| Вопрос | Как ответить по RAG-графу |
|---|---|
| «Где описана авторизация?» | Filter `M-*` где heading содержит «auth» + их CrossLink'и |
| «Что зависит от API v2?» | BFS по `must-sync` / `feeds` от `M-API-V2` |
| «Какие секции протухли после релиза 2026-Q3?» | Diff code/release ↔ document modules; flag где `last-updated` < release date |
| «Найди все таблицы с финансовыми данными» | Filter elements где `type="TABLE-DATA"` AND `M-*` TYPE=DATA |
| «Какие графики упоминают риск-метрики?» | Filter `CHART-NATIVE` whose module's `M-*` heading contains «risk» |
| «Где описание процесса X?» | Exact `M-X` lookup, плюс все `references` на него и от него |

**Шаг 3: построение векторного индекса.**

Для семантического поиска — chunk каждый модуль (≈500 токенов на chunk = размер семантического блока в GRACE), attach metadata `{module_id, heading, type, last_updated, crosslinks}`. Embedding по chunk. Retrieval: vector search + metadata filter (по Module ID, TYPE, relation).

**Шаг 4: refresh-контур.**

`grace-status` (по аналогии с osovv/grace-marketplace) — периодический обход всех документов:
- `last-updated` каждого модуля.
- `must-sync` инварианты — пройтись grep'ом, сравнить значения.
- `freshness` — пометить модули, которые не обновлялись > N дней для своего домена.
- **Это и есть решение проблемы «документы протухают при правке проекта».**

**Практическая реализация (вне GRACE-DOCX, но в его духе):**

```python
# pseudo-RAG
def query(question, rag_index):
    # 1. identify intent
    if "где" in question or "найди":
        # structured lookup on module_ids / headings
        return rag_index.find_by_metadata(question)
    elif "зависит" in question or "связано":
        # graph traversal on CrossLinks
        return rag_index.traverse(question)
    else:
        # semantic + metadata filter
        return rag_index.vector_search(question, top_k=5)
```

---

## 11. Полный пример: bootstrap и правка реального документа

### 11.1 Исходный документ: «Пресейл ФГК 2026.docx»

Допустим, это 250-страничный Word с такими H1-секциями:
1. «Обзор проекта» — 5 стр. prose
2. «Финансовая модель» — 30 стр., 8 таблиц, 3 графика, 2 SmartArt-диаграммы
3. «Команда и ресурсы» — 4 стр. prose
4. «Сроки и этапы» — 6 стр. + 1 диаграмма Ганта
5. «Риски и митигация» — 8 стр., 2 таблицы
6. «Техническая архитектура» — 25 стр., 12 графиков, 4 SmartArt, 6 диаграмм
7. «Интеграции и API» — 15 стр., 4 таблицы
8. «Соответствие требованиям» — 10 стр. prose + 1 большая reference-таблица
9. «Приложения» — 140 стр.: глоссарий, схемы БД, чеклисты

### 11.2 Команда bootstrap (что вы пишете агенту)

```
[grace-docx-bootstrap.md]
[Пресейл ФГК 2026.docx]

Overrides:
document-name: "Пресейл ФГК 2026"
document-version: "1.0"
output-mode: overwrite
module-ids:
  "Обзор проекта": M-OVERVIEW
  "Финансовая модель": M-FIN
  "Команда и ресурсы": M-TEAM
  "Сроки и этапы": M-TIMELINE
  "Риски и митигация": M-RISKS
  "Техническая архитектура": M-ARCH
  "Интеграции и API": M-API
  "Соответствие требованиям": M-COMPLIANCE
  "Приложения": M-APPENDIX
must-sync:
  M-FIN -> M-OVERVIEW: executive summary numbers must match M-FIN totals
  M-ARCH -> M-API: every API endpoint in M-API must have a sequence diagram in M-ARCH
  M-RISKS -> M-APPENDIX: every risk in M-RISKS must have a mitigation owner in M-APPENDIX

Run bootstrap.
```

### 11.3 Что агент сделает (отчёт)

```
═══════════════════════════════════════════
GRACE-DOCX Bootstrap Complete  [v3]
═══════════════════════════════════════════
Document:        Пресейл ФГК 2026
Version:         1.0
Modules:         9 identified, 9 bookmarked
CrossLinks:      3 must-sync declared + 18 detected
XML parts:       5 injected
Bookmarks:       9 pairs injected
───────────────────────────────────────────
Element inventory:
  TABLE-DATA:        14
  TABLE-STRUCT:      3
  CHART-NATIVE:      15
  CHART-IMAGE:       0
  CHART-SMARTART:    6
  VISUAL-IMAGE:      0
  EMBEDDED:          0
───────────────────────────────────────────
Flags:
  - M-FIN: TABLE-DATA row count > 100 in table #5 — verify split
  - M-ARCH: 1 chart image detected (CHART-IMAGE) — readonly
═══════════════════════════════════════════
```

### 11.4 Команда правки (что вы пишете агенту потом)

```
[GRACE-enabled Пресейл ФГК 2026.docx]

user: "Обнови итоговую стоимость проекта в exec summary и финансовой модели.
       Новая цифра: 12 400 000 р. с НДС."

agent:
1. Unpack
2. Read manifest → protocol = safe-edit
3. Read instructions → principles = contract-first, surgical
4. Read graph → M-OVERVIEW (PARA-START 5, PARA-END 60), M-FIN (PARA-START 61, PARA-END 350)
5. Read contracts:
   - M-OVERVIEW contract: can-edit numbers in NARRATIVE paragraphs; must-sync M-FIN totals
   - M-FIN contract: can-edit TABLE-DATA values in "Итоги" table; cannot-edit TABLE-STRUCT
6. Navigate to M-OVERVIEW paragraph containing "итоговая стоимость"
7. Edit: 8 751 780 → 12 400 000
8. Navigate to M-FIN "Итоги" table (TABLE-DATA, columns=4, rows=12)
9. Edit: total cell value
10. Run verification:
    - bookmarks balanced ✓
    - M-OVERVIEW number == M-FIN total cell ✓ (must-sync satisfied)
    - TABLE-DATA column count stable ✓
    - CHART-NATIVE in M-FIN (3 charts) — not touched, source unchanged ✓
11. Repack
12. Return: [GRACE-enabled Пресейл ФГК 2026 v1.1.docx]
```

Если бы цифры в M-OVERVIEW и M-FIN после правки разошлись — verification упал бы на шаге 10, агент откатил бы правку и сообщил, что `must-sync` нарушен.

### 11.5 Что лежит в `word/` после bootstrap

```
word/
├── document.xml              ← оригинал, без изменений
├── styles.xml                ← оригинал
├── numbering.xml             ← оригинал
├── grace-manifest.xml        ← NEW: discovery beacon
├── grace-instructions.xml    ← NEW: agent behavior
├── grace-graph.xml           ← NEW: 9 modules + cross-links
├── grace-contracts.xml       ← NEW: global + type + module contracts
├── grace-verification.xml    ← NEW: structural invariants
└── _rels/
    └── document.xml.rels     ← UPDATED: +5 relationships for GRACE parts
```

Bookmarks `GRACE_M-OVERVIEW`, `GRACE_M-FIN`, и т.д. — внутри `document.xml`, invisible.

---

## 12. Graceful co-existence с osovv/grace-marketplace (код)

Если у вас одновременно и код (под GRACE 4 osovv/grace-marketplace), и документация (под GRACE-DOCX v3) — они **дополняют друг друга**, не конфликтуют.

| | GRACE osovv | GRACE-DOCX xronocode |
|---|---|---|
| Артефакты | `.grace/{context,graph,verification,changes}` + файловые контракты | 5 XML-частей под `word/` + bookmarks |
| Граф | `.grace/graph/*.xml` (M-*, V-M-*, C-*) | `<CrossLinks>` в `grace-graph.xml` (M-*) |
| Контракты | `MODULE_CONTRACT` в каждом .ts/.py | `<ModuleContracts>` в `grace-contracts.xml` |
| Верификация | `.grace/verification/*.xml` (V-M-*) | `<StructuralInvariants>` + `<PostEditChecks>` в `grace-verification.xml` |
| Lifecycle | spec → plan → execute → final | bootstrap → safe-edit → verification |
| Применяется к | исходный код | Office-документы (.docx, .pptx) |

**Связка «правка кода → правка документации»:**

1. Меняется `M-AUTH` в коде (GRACE 4 osovv).
2. CI triggers `doc-drift-detector`, который:
   - grep `M-AUTH` по всем `.docx` (через `word/grace-graph.xml` + `bookmarks`).
   - находит `M-API`, `M-ARCH`, `M-DEPLOY` в документации.
   - формирует список touched-doc-modules.
3. Воркер запускается на каждый touched-doc-module с контекстом «что изменилось в M-AUTH».
4. Каждый touched модуль проходит safe-edit protocol (Phase 1-7 GRACE-DOCX).
5. Финальный gate: `grace-status` (GRACE osovv) + cross-doc `must-sync` check (GRACE-DOCX).

**RAG-граф проекта** (включая и код, и документацию) — это **объединённый граф**:
- Узлы GRACE 4 osovv: M-* (код), V-M-* (тесты), C-* (changes).
- Узлы GRACE-DOCX: M-* (документы), CrossLinks, Bookmarks.
- Cross-link между ними: явно через `LINKS:` или `<CrossLink>` (например, `M-AUTH` (код) `feeds` `M-API-ENDPOINTS-AUTH` (документ)).

---

## 13. Best practices для 1000+ страничных проектов

### 13.1 Архитектура документации

1. **Разнесите по томам.** Один `.docx` = 1 логический том, ≤ 300 страниц. Cross-volume references через `<CrossLink relation="references" target="M-FIN-VOL-2">`.
2. **Стандартизируйте module IDs.** Префикс по тому: `M-V1-OVERVIEW`, `M-V1-FIN`, `M-V2-OVERVIEW`, `M-V2-FIN`. Иначе cross-volume ссылки сломаются.
3. **Централизуйте cross-link'и.** Отдельный `master-crosslinks.xml` хранит все межтомные связи; `grace-refresh` валидирует их против актуального состояния.
4. **Версионируйте модули, не документы.** `M-FIN v3.2` (внутри v3.2 документа) лучше, чем перевыпуск всего тома ради одной таблицы.

### 13.2 Контракты

5. **`<must-sync>` для чисел и имён.** Любые totals, версии, имена endpoint'ов, ФИО ответственных — `must-sync` между модулем-источником и всеми местами, где они цитируются.
6. **`<cannot-edit>` явно.** Для boilerplate-секций (META, NAVIGATION, обложка) — `cannot-edit: anything except version date and footer`.
7. **`<can-edit>` узко.** Не пишите «can-edit: anything not forbidden». Пишите «can-edit: numeric cells in TABLE-DATA marked TOTAL». Узкие права = меньше дрейфа.

### 13.3 Anti-patterns

8. **Не делать bootstrap на «сыром» документе без structure.** Если H1 не выделены явно, а используется visual styling — сначала приведите документ к semantic H1 (через outline view в Word).
9. **Не давать агенту писать в CHART-IMAGE.** Это raster — нельзя «обновить цифру», только заменить файл. Если график стал неактуальным — перегенерируйте и явно скажите «replace image».
10. **Не удалять bookmarks при правке.** Если paragraph range сдвинулся — обновите `PARA-START`/`PARA-END` в `grace-graph.xml`, но **сами bookmarks оставьте** (переместите, не удаляйте).
11. **Не запускать `grace-verification.xml` на весь документ после каждой правки** — только на touched-секцию + её `must-sync` партнёров. Иначе verification сама станет context rot.
12. **Не игнорировать flags в bootstrap report.** Если агент говорит «TABLE-DATA row count > 100, verify split» — это значит, структура плохо ляжет на safe-edit протокол. Разбейте таблицу или сделайте её TABLE-STRUCT.

### 13.4 Когда НЕ использовать GRACE-DOCX

- **Документ < 10 страниц и редактируется редко.** Overhead на bootstrap не окупится.
- **Документ без структуры** (visually styled без semantic H1, без chapter divisions). Сначала приведите к структуре.
- **PDF-only требование** — GRACE-DOCX работает с `.docx`. Для PDF-финальной версии сделайте export из GRACE-enabled `.docx`, но RAG/правки делайте в DOCX-источнике.
- **Коллаборативное редактирование человеком** — bookmarks и XML-метаданные **невидимы** в Word UI, но если человек сделает крупный restructure (вырежет секцию, переставит), bookmarks могут потерять pairing. После такого restructure — re-run bootstrap.

---

## 14. PPTX preview (бонус)

`xronocode/grace-docx` также содержит **preview v1** для PowerPoint. Концепция та же — 5 XML-частей под `ppt/`, но модули — это **слайды или группы слайдов**, не H1-секции.

| DOCX | PPTX |
|---|---|
| H1 module | Slide или slide group |
| Paragraph range | Shape tree path |
| Bookmark | Slide position + stable shape ID/name |
| TABLE-DATA | Slide table shape |
| Native chart | `ppt/charts/chartN.xml` |
| SmartArt | `ppt/diagrams/dataN.xml` + layout files |
| Visual image | `ppt/media/imageN.*` |

Дополнительные element types для PPTX: `TEXT-PLACEHOLDER`, `TEXT-BOX`, `NOTES`, `ANIMATION`, `MEDIA`. Authoritative slide order — только из `ppt/presentation.xml` (`<p:sldIdLst>`), не из filename.

Status: **preview**, не stable. Не рекомендуется для production-критичных деки до v1-stable.

---

## 15. Roadmap (из `docs/powerpoint-roadmap.md` + `CHANGELOG.md`)

Что планируется в `xronocode/grace-docx`:

- **Harden v3 на реальных `.docx` samples** со сложными таблицами, графиками, изображениями, SmartArt.
- **Runnable validators** для GRACE-enabled `.docx` архивов (сейчас validation в основном через LLM-агента, читающего XML).
- **Reference XML templates** под `grace/` для воспроизводимой bootstrap-генерации.
- **Harden GRACE-PPTX** на реальных деках с sections, notes, SmartArt, charts, animations, internal links.
- **Explore `.xlsx` workbooks** — тот же паттерн для Excel.

Следить: https://github.com/xronocode/grace-docx

---

## 16. Дизайн собственной системы (если строите аналог)

Если берёте принципы GRACE-DOCX, но не хотите зависеть от `xronocode/grace-docx` (например, потому что хотите поддержку `.md`/`.rst` или Confluence), ниже — минимальный набор артефактов, который надо реализовать.

### Минимальный артефактный набор (замены)

| GRACE-DOCX | Замена для своего формата |
|---|---|
| 5 XML-частей под `word/` | Frontmatter + sidecar JSON/YAML для каждого документа |
| `<w:bookmarkStart>` | Markdown-anchor `<!-- GRACE_M-XXX_START -->` ... `<!-- GRACE_M-XXX_END -->` |
| `grace-graph.xml` | `_graph.json` в корне проекта — все модули, cross-link'и |
| `grace-contracts.xml` | `_contracts.yaml` — type + module contracts |
| `grace-verification.xml` | `_verification.json` — structural invariants + post-edit checks |
| `grace-manifest.xml` | `_manifest.yaml` — протокол, output policy, schema version |
| Module ID `M-XXX` | Любой уникальный тег; не обязательно `M-` префикс |

### Минимальный набор ритуалов (замены скиллов)

1. **`doc-bootstrap`** — распаковывает (для .docx) или сканирует (для .md) документ, строит 5 артефактов.
2. **`doc-edit`** — safe-edit протокол: read manifest → read graph → read contracts → edit → verify → repack.
3. **`doc-reviewer`** — структурный review: balanced bookmarks, drift между модулями, must-sync инварианты.
4. **`doc-refresh`** — периодический обход: last-updated freshness, must-sync consistency, broken references.
5. **`doc-status`** — снимок здоровья: какие модули stale, какие ссылки протухли, где нет `must-sync`.
6. **`doc-rag-index`** — строит/обновляет векторный индекс + граф по всем документам.
7. **`doc-rag-query`** — отвечает на вопросы по RAG-графу: «где X?», «что зависит от Y?», «что протухло?».

### Что точно стоит перенести

1. **Element-type awareness** (TABLE-DATA vs TABLE-STRUCT, CHART-NATIVE vs CHART-IMAGE) — критично для безопасных AI-правок.
2. **Bookmarks / anchors как load-bearing structure** — не удалять при правках.
3. **CrossLink relations** (`feeds`, `must-sync`, `references`, `constrains`) — для связных изменений.
4. **Strict contract resolution** (GlobalRules → TypeContract → ModuleContract → user instruction) — strictest wins.
5. **Post-edit verification** с rollback на hard-severity failure.
6. **Style fingerprint** (шрифты, тема) — чтобы модель не «причёсывала» в свой стиль.
7. **Bootstrap report** с element inventory и flags — для transparency.
8. **RAG-граф на основе `<CrossLinks>`** + chunking по модулям + metadata filter.

### Что можно упростить

1. **Module taxonomy** — ваши 6 типов (NARRATIVE/DATA/MIXED/...) — замените на свои, подходящие к предметной области.
2. **Output policy** — `overwrite` vs `new-version` — по вашему workflow.
3. **Inline overrides** — если bootstrap автоматизирован, overrides не нужны; если ad-hoc — критичны.
4. **Anti-patterns список** — берите из GRACE-DOCX, добавляйте свои по опыту.

---

## Приложение A. Сводка тегов и ID

| Тег / ID | Где | Назначение |
|---|---|---|
| `M-XXX` | `grace-graph.xml`, contracts, verification | Module ID (H1-секция) |
| `GRACE_M-XXX` | bookmarks в `document.xml` | Invisible Word-bookmark |
| `C-NARRATIVE / C-TABLE-DATA / C-CHART-NATIVE / C-CHART-IMAGE / C-CHART-SMARTART / C-TABLE-STRUCT / C-VISUAL-IMAGE / C-EMBEDDED` | `<TypeContracts>` | Element type contracts |
| `<ELEMENTS>` | внутри `<M-XXX>` | Inventory таблиц/графиков/SmartArt/изображений в модуле |
| `<CrossLinks>` | `grace-graph.xml` | Связи между модулями с relations |
| `<GlobalRules>` | `grace-contracts.xml` | Правила для всего документа |
| `<ModuleContracts>` | `grace-contracts.xml` | Per-module overrides: `can-edit`, `cannot-edit`, `must-sync` |
| `<StructuralInvariants>` | `grace-verification.xml` | Hard-check invariants |
| `<PostEditChecks>` | `grace-verification.xml` | Проверки после каждой правки |
| relations: `feeds` / `must-sync` / `references` / `constrains` | `<CrossLinks>` | Семантика связи между модулями |

## Приложение B. Структура репо `xronocode/grace-docx`

```
grace-docx/
├── grace-docx-bootstrap.md        # latest stable bootstrap prompt (v3)
├── grace-docx-bootstrap-v3.md     # explicit v3 copy
├── grace-pptx-bootstrap.md        # PowerPoint preview (v1)
├── archive/
│   └── grace-docx-bootstrap-v1.md # previous section-aware version
├── assets/                        # GitHub README diagrams (SVG)
├── docs/
│   ├── pptx-schema-v1.md
│   ├── release-v3.md
│   ├── schema-v3.md
│   ├── v3-transition.md
│   ├── powerpoint-roadmap.md
│   └── github-publishing.md
├── CHANGELOG.md
└── README.md
```

## Приложение C. Совместимость и миграция

- **v1 → v3:** schema-level upgrade. Существующие v1-bootstrapped документы остаются читаемыми как section-aware, но без element inventory. Чтобы получить v3-поведение, run v3 bootstrap на исходном `.docx` (или migrate embedded GRACE parts).
- **DOCX ↔ PPTX:** разные схемы. DOCX = section-first, PPTX = slide-first. Концептуально совместимы (оба element-aware), но XML-части и inventory не взаимозаменяемы.
- **GRACE-DOCX ↔ GRACE osovv:** разные репозитории, разные авторы, разные схемы. Совместимы концептуально (оба портируют GRACE), но не имеют общих CLI/артефактов. Для проекта с кодом + документацией — используйте оба, склеивая через RAG-индекс.

---

*Конец playbook. Скиллы, артефакты и цитаты в этом гайде — выжимка из публичного репозитория `xronocode/grace-docx` (MIT). Ключевые формулировки сохранены. Концептуальные расширения для AI-генерации без дрейфа, связных изменений и RAG-графа (§10) — производные от базовой методологии, применимые к документам любого формата.*
