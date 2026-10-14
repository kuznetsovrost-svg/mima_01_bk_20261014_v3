═══════════════════════════════════════════════════════════════════
  Таблица-в-FIGMA.md
  Конвенция дизайна таблиц в Figma под экспорт в HTML
  С учётом расширяемости (открывашка)
  + точный пример «Таблица замечаний» project_504-595
═══════════════════════════════════════════════════════════════════

Версия 2: 2026-07-29 (обновлена точными данными из project_504-595_здоровье.md)
Hermes Agent v0.18.0 на mima_g_01

═══════════════════════════════════════════════════════════════════
1. КОРОТКИЙ ОТВЕТ
═══════════════════════════════════════════════════════════════════

Главное правило:

  В Figma рисуй ОДНУ строку-шаблон в tbody,
  а в коде через {% for row in rows %} перебирай
  сколько угодно строк.

  Вместо  N конкретных строк  →  1 строка-образец с маркером

Принцип: декларативная ёмкость.

═══════════════════════════════════════════════════════════════════
2. ПРИНЦИП ДЕКЛАРАТИВНОЙ ЁМКОСТИ
═══════════════════════════════════════════════════════════════════

  Один образец       →   Готовая HTML-таблица (любое количество строк)
  ┌───┬───┬───┐
  │ A │ B │ C │       →   {% for row in rows %}
  └───┴───┴───┘           <tr>
                            <td>{{ row.col_a }}</td>
                            <td>{{ row.col_b }}</td>
                            <td>{{ row.col_c }}</td>
                          </tr>
                          {% endfor %}

═══════════════════════════════════════════════════════════════════
3. ИМЕНА ПЛЕЙСХОЛДЕРОВ ДЛЯ ТАБЛИЦ
═══════════════════════════════════════════════════════════════════

3.1. Шапка таблицы (thead)
──────────────────────────

  {cols[0]}              ← заголовок 1-й колонки
  {cols[1]}              ← заголовок 2-й колонки
  {cols[N]}              ← заголовок N-й колонки

  Или с префиксом:
  {thead.col_0}
  {thead.col_1}
  {thead.col_n}

3.2. Тело таблицы (tbody) — образец строки
──────────────────────────────────────────

  {rows[N].col_0}        ← ячейка 1
  {rows[N].col_1}        ← ячейка 2
  {rows[N].col_n}        ← ячейка N

  Или с осмысленными именами:
  {rows[N].metric}
  {rows[N].planned}
  {rows[N].actual}
  {rows[N].status}

3.3. Индексы
────────────

  Шаблон                Что значит
  ────────────────       ─────────────────────
  {rows[0].field}        1-я строка (явный индекс)
  {rows[N].field}        Любая N-я строка (маркер)
  {rows[*].field}        Все строки (wildcard)
  {rows[last].field}     Последняя строка
  {rows[0..2].field}     Диапазон

═══════════════════════════════════════════════════════════════════
4. ОБЯЗАТЕЛЬНАЯ СТРУКТУРА FIGMA
═══════════════════════════════════════════════════════════════════

4.1. Что ОБЯЗАТЕЛЬНО
────────────────────

  • Таблица — это Auto Layout vertical (или horizontal внутри ячеек)
  • thead отделён от tbody (отдельные Frame'и)
  • В tbody — ОДНА строка-образец с именем tr.template
  • Все ячейки строки-образца используют {rows[N].<field>}
  • Все ячейки имеют фиксированную ширину

4.2. Что ОПЦИОНАЛЬНО
─────────────────────

  • Чётные/нечётные строки — через CSS :nth-child(even)
  • Статус-индикатор — отдельный vector/circle
  • tfoot — для итогов (см. §6.4)
  • tr.template.merged — для rowspan/colspan

4.3. Что ЗАПРЕЩЕНО
──────────────────

  • Несколько одинаковых строк в tbody (только одна-образец)
  • Реальные числа/имена в плейсхолдерах ({rows[0].value: 42}, нет)
  • Hard-coded количество строк

═══════════════════════════════════════════════════════════════════
5. ОТКРЫВАШКА · ACCORDION-TABLE (ЭТАПЫ СВОРАЧИВАНИЯ)
═══════════════════════════════════════════════════════════════════

В Figma нужно явно показать, что таблица будет раскрываться
по клику. Это специальный паттерн, и его нужно явно обозначить,
иначе плагин сделает обычную таблицу.

5.1. Состояния (states) в Figma
───────────────────────────────

Для каждой таблицы-открывашки нужно сделать ДВА состояния:
  - State: collapsed   (одна строка)
  - State: expanded    (все строки видны)

В Figma это реализуется как Component с variants:

  Component: tbl.collapsible
    ├─ Variant: collapsed      ← одна строка видна
    └─ Variant: expanded       ← все строки видны

5.2. Именование компонентов и элементов
───────────────────────────────────────

  ┌─ cmp.tbl-collapsible (Auto Layout vertical)
    │
    ├─ Frame: tbl-controls (header bar, всегда виден)
    │  ├─ Text: {collapsible.summary_label}      "Замечания (всего: {{ count }})"
    │  ├─ Vector: {collapsible.toggle_icon}     ▼/▶ (chevron)
    │  └─ btn.toggle-collapsible
    │
    ├─ thead (Auto Layout horizontal)
    │  ├─ Cell: {cols[0]}
    │  ├─ Cell: {cols[1]}
    │  ├─ ...
    │  └─ Cell: {cols[n]}
    │
    ├─ Frame: tbl-expand-area (только в варианте «expanded»)
    │  │
    │  └─ tbody (Auto Layout vertical)
    │     └─ tr.template
    │        ├─ Cell: {rows[N].col_0}
    │        ├─ Cell: {rows[N].col_1}
    │        └─ ...
    │
    └─ Frame: tbl-actions (только в варианте «expanded»)
       ├─ btn.add-row                "+ Добавить замечание"
       └─ btn.export-csv            "Скачать CSV"

5.3. Именование слоёв для accordion
─────────────────────────────────────

В Frame есть специальные соглашения:

  cmp.collapsible.tbl-remarks        ← variant «table-remarks»
      ├─ collapsed                    ← variant state
      └─ expanded                     ← variant state

Имена внутри cmp.collapsible.tbl-remarks:

  Слой                          Имя в Figma                Тип
  ──────────────────────────   ─────────────────────────   ───────────
  Сам компонент                cmp.collapsible             Component
  Variant                      collapsed / expanded        Variant
  Header bar                   tbl-controls                Frame
  Toggle button                btn.toggle                  Component
  Chevron icon                 ico.chevron-down            Vector
  Summary text                 {collapsible.summary_label}  Text
  Expandable area              tbl-expand-area             Frame
  thead                        thead                       Frame
  Cell N                       {cols[N]}                   Text
  tbody                        tbody                       Frame
  Row template                 tr.template                 Frame
  Cell N                       {rows[N].<field>}           Text
  Add row button               btn.add-row                 Frame
  Export CSV button            btn.export-csv              Frame

5.4. Маркер, что таблица открывашка
─────────────────────────────────────

В SKILL/HTML это пометится специальным data-атрибутом:

  <table class="collapsible-table"
         data-collapsible="true"
         data-collapsed="true">

Имена в Figma, которые ОБЯЗАТЕЛЬНО должны быть:

  • cmp.collapsible  — тип компонента (открывашка)
  • collapsed / expanded — variant state
  • btn.toggle — кнопка раскрытия
  • tbl-expand-area — область, которая скрывается/раскрывается

Если в Figma нет таких имён, экспорт даст обычную таблицу
без аккордеона.

5.5. Альтернативный способ: data-атрибут
────────────────────────────────────────

Если в Figma нет технической возможности делать Component variants,
можно пометить таблицу-открывашку через специальный плейсхолдер:

  Frame: tbl.remarks
    └─ <внутри любого слоя> Text: {tbl.collapsible=true}
       (просто текстовая метка, по которой агент распознает)

Это менее надёжно, но работает.

5.6. Конкретный пример (псевдографика)
──────────────────────────────────────

Свернутая (collapsed) — одна строка-саммари с toggle-кнопкой:

  ┌──────────────────────────────────────────────────────────┐
  │  Замечания (всего: 3)                          ▶        │  ← tbl-controls
  └──────────────────────────────────────────────────────────┘

Развёрнутая (expanded) — все строки видны:

  ┌──────────────────────────────────────────────────────────┐
  │  Замечания (всего: 3)                          ▼        │  ← tbl-controls
  ├──────────────────────────────────────────────────────────┤
  │  № │ Цвет │ Статус │ Code │ Name │ Plan │ Forecast │ Fact │ Исполнитель │  ← thead
  │────┼──────┼────────┼──────┼──────┼──────┼──────────┼──────┼─────────────│
  │  1 │  🔴  │ Крит.  │ 104-721│ ЧТЗ...│ ... │   ...   │  —   │ Кузнецов...│  ← tr.template
  │  2 │  🔴  │ Крит.  │ 104-719│ ...  │ ... │   ...   │  —   │ Кузнецов...│
  │  3 │  🟡  │ Сущ.   │ 104-722│ ...  │ ... │   ...   │  —   │ Кузнецов...│
  ├──────────────────────────────────────────────────────────┤
  │  [+ Добавить замечание]              [Скачать CSV]      │  ← tbl-actions
  └──────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════
6. ТАБЛИЦА ЗАМЕЧАНИЙ PROJECT_504-595 (ТОЧНЫЙ ПРИМЕР)
═══════════════════════════════════════════════════════════════════

Данные из файла: /root/.hermes/cache/documents/doc_6a5b90652522_project_504-595_здоровье.md

6.1. Контекст проекта (ТОЧНЫЙ)
─────────────────────────────

  Проект:    Космодром Жуковский, внедрение ИСУП
  Code:      504-595
  ProjectId: 4595
  Состояние: ТРЕБУЕТ ВНИМАНИЯ (цвет: ЖЕЛТЫЙ)
  Алгоритм:
    БОЛЕН (красный)         → critical_count ≥ 3
    ТРЕБУЕТ ВНИМАНИЯ (жёлт) → 1 ≤ critical_count ≤ 2
    ЗДОРОВ                  → critical_count = 0

  Замечаний всего: 3
  Из них критических (красных): 2
  Существенных (жёлтых): 1
  Информационных (синих): 0

6.2. Условия отбора замечаний (ТОЧНЫЕ)
──────────────────────────────────────

  В таблицу попадают только Point, у которых:
    1. PlanDate ≠ ForecastDate
    2. FactDate не заполнена (КТ ещё не завершена)

6.3. Цветовая логика (ТОЧНАЯ)
──────────────────────────────

  Цвет        │ Статус        │ Условие
  ────────────┼────────────────┼─────────────────────────────
  Красный     │ Критическое   │ |ForecastDate − PlanDate| > 10 дней
  Жёлтый      │ Существенное  │ 2 < diff ≤ 10 дней
  Синий       │ Информационное│ 0 ≤ diff ≤ 2 дня

6.4. Реальные данные (3 строки из отчёта)
─────────────────────────────────────────

  #   Цвет         Статус        Code      Name
  ─── ──────────── ───────────── ───────── ──────────────────────────────
  1   Красный      Критическое   104-721   ЧТЗ согласовано
  2   Красный      Критическое   104-719   Первый блок работ принят Заказчиком
  3   Жёлтый       Существенное  104-722   Подписан протокол согласования по 1-му блоку работ

  PlanDate   ForecastDate  Diff (дней)  Исполнитель
  ────────── ───────────── ──────────── ──────────────────────────────────
  2026-07-15 2026-07-27    12           Кузнецов Ростислав Владимирович (id=120872)
  2026-07-24 2026-08-06    13           Кузнецов Ростислав Владимирович (id=120872)
  2026-07-24 2026-07-27    3            Кузнецов Ростислав Владимирович (id=120872)

  FactDate у всех 3 — не заполнена (КТ ещё не завершены)

6.5. Колонки таблицы (фиксированная структура)
──────────────────────────────────────────────

  # п/п  Имя колонки      Ширина  Плейсхолдер
  ─────  ────────────────  ───────  ─────────────────────────────
  1      №                  50px   {rows[N].number}
  2      Цвет               80px   {rows[N].color}
  3      Статус            130px   {rows[N].status}
  4      Code               90px   {rows[N].code}
  5      Name              260px   {rows[N].name}
  6      PlanDate           110px  {rows[N].plan_date}
  7      ForecastDate       120px  {rows[N].forecast_date}
  8      FactDate           100px  {rows[N].fact_date}
  9      Исполнитель        220px  {rows[N].executor}
                                ────
                          Итого: 1160px

  Имена в thead:
  {cols[0]}  "№"
  {cols[1]}  "Цвет"
  {cols[2]}  "Статус"
  {cols[3]}  "Code"
  {cols[4]}  "Name"
  {cols[5]}  "PlanDate"
  {cols[6]}  "ForecastDate"
  {cols[7]}  "FactDate"
  {cols[8]}  "Исполнитель"

  Опциональные поля (если агент может вычислить):
  {rows[N].diff_days}     — вычисляемое: |Forecast - Plan|
  {rows[N].color_class}   — вычисляемое: red / yellow / blue
  {rows[N].status_class}  — вычисляемое: critical / substantial / info

6.6. Полная структура Figma-композиции (ТОЧНАЯ)
───────────────────────────────────────────────

  Artboard: Report — Desktop (1280×auto)

  sec.report-content (Auto Layout vertical, padding: 32px, gap: 24px)

  ├─ sec.header (Auto Layout vertical, gap: 8px)
  │  ├─ Text: {report.title}
  │  │   "Общая оценка здоровья проекта 504-595: Космодром Жуковский, ИСУП"
  │  ├─ Text: {report.subtitle}
  │  │   "С точки зрения сроков КТ"
  │  ├─ Text: {report.timestamp}
  │  │   "Составлено: 2026-07-28 13:36:53"
  │  └─ grp.meta (Auto Layout vertical, gap: 4px)
  │     ├─ Text: {report.code}            "Code: 504-595"
  │     └─ Text: {report.project_id}      "ProjectId: 4595"
  │
  ├─ sec.health-summary (Auto Layout vertical, padding: 24px)
  │  │
  │  ├─ Frame: status-badge (Auto Layout horizontal, padding: 12px 24px)
  │  │  ├─ Vector: status-dot
  │  │  └─ Text: {health.status_label}
  │  │     "Состояние: ТРЕБУЕТ ВНИМАНИЯ"
  │  │
  │  ├─ Frame: counters (Auto Layout horizontal, gap: 24px)
  │  │  ├─ cmp.counter (critical)
  │  │  │  ├─ Text: {summary.critical.label}    "Критических"
  │  │  │  └─ Text: {summary.critical.value}    "2"
  │  │  ├─ cmp.counter (substantial)
  │  │  │  ├─ Text: {summary.substantial.label} "Существенных"
  │  │  │  └─ Text: {summary.substantial.value} "1"
  │  │  ├─ cmp.counter (info)
  │  │  │  ├─ Text: {summary.info.label}        "Информационных"
  │  │  │  └─ Text: {summary.info.value}        "0"
  │  │  └─ cmp.counter (total)
  │  │     ├─ Text: {summary.total.label}       "Всего"
  │  │     └─ Text: {summary.total.value}       "3"
  │  │
  │  └─ Frame: algorithm (Auto Layout vertical, padding: 12px)
  │     ├─ Text: {health.algorithm_title}
  │     │   "Алгоритм оценки:"
  │     ├─ Text: {health.algorithm_rule_1}
  │     │   "  critical_count ≥ 3 → БОЛЕН (красный)"
  │     ├─ Text: {health.algorithm_rule_2}
  │     │   "  1 ≤ critical_count ≤ 2 → ТРЕБУЕТ ВНИМАНИЯ (жёлтый)"
  │     ├─ Text: {health.algorithm_rule_3}
  │     │   "  critical_count = 0 → ЗДОРОВ"
  │     └─ Text: {health.algorithm_current}
  │         "  Текущее: critical_count = 2 → ТРЕБУЕТ ВНИМАНИЯ"
  │
  └─ sec.remarks (Auto Layout vertical, gap: 16px)
     │
     ├─ Text: {remarks.section_title}
     │   "СПИСОК ЗАМЕЧАНИЙ ПО СРОКАМ"
     │
     ├─ Frame: filter-info (Auto Layout vertical, padding: 12px)
     │  ├─ Text: {remarks.filter_title}    "Условия отбора:"
     │  └─ grp.conditions (Auto Layout vertical, gap: 4px)
     │     ├─ Text: {remarks.condition_1}
     │     │   "1. PlanDate ≠ ForecastDate"
     │     └─ Text: {remarks.condition_2}
     │         "2. FactDate не заполнена (КТ ещё не завершена)"
     │
     └─ cmp.collapsible.tbl-remarks    ← ТАБЛИЦА-ОТКРЫВАШКА
        │
        ├─ Variant: collapsed
        │  └─ Frame: tbl-controls
        │     │  (Auto Layout horizontal,
        │     │   padding: 12px 16px,
        │     │   background: #F9FAFB)
        │     ├─ Vector: ico.color-marker (mixed)
        │     ├─ Text: {collapsible.summary_label}
        │     │   "Список замечаний (всего: {remarks.count})"
        │     ├─ (gap auto)
        │     ├─ Text: {collapsible.preview}
        │     │   "2 критических, 1 существенное"
        │     ├─ (gap 12px)
        │     └─ Vector: ico.chevron-right
        │
        └─ Variant: expanded
           │
           ├─ Frame: tbl-controls
           │  │  (Auto Layout horizontal,
           │  │   padding: 12px 16px,
           │  │   background: #F9FAFB)
           │  ├─ Vector: ico.color-marker
           │  ├─ Text: {collapsible.summary_label}
           │  │   "Список замечаний (всего: {remarks.count})"
           │  ├─ (gap auto)
           │  ├─ Text: {collapsible.toggle_label}    "Свернуть"
           │  ├─ (gap 8px)
           │  └─ Vector: ico.chevron-down
           │
           ├─ Frame: tbl-table-wrapper
           │  │  (Auto Layout vertical, gap: 0)
           │  │
           │  ├─ thead (Auto Layout horizontal, padding: 8px, gap: 0)
           │  │  │  (background: #F3F4F6)
           │  │  ├─ Cell (width: 50px)
           │  │  │  └─ Text: {cols[0]}               "№"
           │  │  ├─ Cell (width: 80px)
           │  │  │  └─ Text: {cols[1]}               "Цвет"
           │  │  ├─ Cell (width: 130px)
           │  │  │  └─ Text: {cols[2]}               "Статус"
           │  │  ├─ Cell (width: 90px)
           │  │  │  └─ Text: {cols[3]}               "Code"
           │  │  ├─ Cell (width: 260px)
           │  │  │  └─ Text: {cols[4]}               "Name"
           │  │  ├─ Cell (width: 110px)
           │  │  │  └─ Text: {cols[5]}               "PlanDate"
           │  │  ├─ Cell (width: 120px)
           │  │  │  └─ Text: {cols[6]}               "ForecastDate"
           │  │  ├─ Cell (width: 100px)
           │  │  │  └─ Text: {cols[7]}               "FactDate"
           │  │  └─ Cell (width: 220px)
           │  │     └─ Text: {cols[8]}               "Исполнитель"
           │  │
           │  └─ tbody (Auto Layout vertical, gap: 0)
           │     │
           │     └─ tr.template (Auto Layout horizontal)
           │        │  ← ОБРАЗЕЦ СТРОКИ (одна!)
           │        │
           │        ├─ Cell (width: 50px)
           │        │  └─ Text: {rows[N].number}        "1"
           │        │
           │        ├─ Cell (width: 80px)
           │        │  ├─ Vector: {rows[N].color_marker}
           │        │  │   (🔴 / 🟡 / 🔵 — цветной кружок)
           │        │  └─ Text: {rows[N].color}         "Красный"
           │        │
           │        ├─ Cell (width: 130px)
           │        │  └─ Text: {rows[N].status}       "Критическое"
           │        │
           │        ├─ Cell (width: 90px)
           │        │  └─ Text: {rows[N].code}         "104-721"
           │        │
           │        ├─ Cell (width: 260px)
           │        │  └─ Text: {rows[N].name}         "ЧТЗ согласовано"
           │        │
           │        ├─ Cell (width: 110px)
           │        │  └─ Text: {rows[N].plan_date}    "2026-07-15"
           │        │
           │        ├─ Cell (width: 120px)
           │        │  └─ Text: {rows[N].forecast_date} "2026-07-27"
           │        │
           │        ├─ Cell (width: 100px)
           │        │  └─ Text: {rows[N].fact_date}    "—"
           │        │
           │        └─ Cell (width: 220px)
           │           ├─ Text: {rows[N].executor_name}
           │           │   "Кузнецов Ростислав Владимирович"
           │           └─ Text: {rows[N].executor_id}
           │               "(id=120872)"
           │
           └─ Frame: tbl-actions
              │  (Auto Layout horizontal, padding: 12px 16px,
              │   background: #F9FAFB)
              ├─ btn.add-row
              │  └─ Text: {buttons.add_row}      "+ Добавить замечание"
              ├─ (gap auto)
              ├─ btn.export-csv
              │  └─ Text: {buttons.export_csv}    "Скачать CSV"
              └─ btn.print
                 └─ Text: {buttons.print}         "Печать"

6.7. Иконки цветов (КРАСНЫЙ / ЖЁЛТЫЙ / СИНИЙ)
─────────────────────────────────────────────

  Vector: {rows[N].color_marker}
    ┌────────────────────────────────────────────┐
    │ Цвет кружка зависит от {rows[N].color}:   │
    │                                            │
    │   Красный     → #DC2626 (red-600)          │
    │   Жёлтый      → #D97706 (amber-600)        │
    │   Синий       → #2563EB (blue-600)         │
    └────────────────────────────────────────────┘

  Этот vector — ЕДИНСТВЕННЫЙ способ показать цвет в Figma.
  В HTML ему будет соответствовать CSS-класс:
    .color-marker--red    { background: #DC2626; }
    .color-marker--yellow { background: #D97706; }
    .color-marker--blue   { background: #2563EB; }

6.8. Status badge «ТРЕБУЕТ ВНИМАНИЯ»
────────────────────────────────────

  Для project_504-595 текущее состояние — ЖЁЛТЫЙ:

  ┌─ Frame: status-badge (Auto Layout horizontal, padding: 12px 24px,
  │                       border-radius: 999px,
  │                       background: #FEF3C7)
  │  ├─ Vector: status-dot (жёлтый #D97706, диаметр 12px)
  │  └─ Text: {health.status_label}
  │     "Состояние: ТРЕБУЕТ ВНИМАНИЯ" (Inter SemiBold 16px, #92400E)

  CSS-аналог:
    .status-badge--yellow { background: #FEF3C7; color: #92400E; }
    .status-badge--red    { background: #FEE2E2; color: #991B1B; }
    .status-badge--green  { background: #D1FAE5; color: #065F46; }

6.9. Чек-лист (специфичный для project_504-595)
───────────────────────────────────────────────

Перед экспортом проверь:

  [ ] 9 ячеек в thead: №, Цвет, Статус, Code, Name,
      PlanDate, ForecastDate, FactDate, Исполнитель
  [ ] 8 ячеек в tr.template (number — auto)
  [ ] Cell widths: 50, 80, 130, 90, 260, 110, 120, 100, 220 px
  [ ] Все ячейки используют {cols[N]} в thead
  [ ] Все ячейки используют {rows[N].<field>} в tbody
  [ ] Color marker — vector, а не просто текст «Красный»
  [ ] Status badge имеет правильный цвет (жёлтый сейчас)
  [ ] 4 счётчика: critical / substantial / info / total
  [ ] Algorithm показывает текущее состояние
  [ ] Collapsible variant: collapsed + expanded

═══════════════════════════════════════════════════════════════════
7. ПРИМЕРЫ ПЛЕЙСХОЛДЕРОВ ДЛЯ ДРУГИХ ТАБЛИЦ В ОТЧЁТЕ
═══════════════════════════════════════════════════════════════════

Таблица метрик:

  cmp.tbl-metrics
    ├─ thead
    │  ├─ {cols[0]}    "Показатель"
    │  ├─ {cols[1]}    "План"
    │  ├─ {cols[2]}    "Факт"
    │  ├─ {cols[3]}    "Δ"
    │  └─ {cols[4]}    "Статус"
    └─ tbody
       └─ tr.template
          ├─ {rows[N].metric}
          ├─ {rows[N].planned}
          ├─ {rows[N].actual}
          ├─ {rows[N].delta}
          └─ {rows[N].status}

Таблица рисков:

  cmp.tbl-risks
    ├─ thead
    │  ├─ {cols[0]}    "Риск"
    │  ├─ {cols[1]}    "Вероятность"
    │  ├─ {cols[2]}    "Влияние"
    │  ├─ {cols[3]}    "Митigation"
    │  └─ {cols[4]}    "Ответственный"
    └─ tbody
       └─ tr.template
          ├─ {rows[N].risk}
          ├─ {rows[N].probability}
          ├─ {rows[N].impact}
          ├─ {rows[N].mitigation}
          └─ {rows[N].owner}

Таблица вех (milestones):

  cmp.tbl-milestones
    ├─ thead
    │  ├─ {cols[0]}    "Веха"
    │  ├─ {cols[1]}    "План"
    │  ├─ {cols[2]}    "Факт/Прогноз"
    │  └─ {cols[3]}    "Статус"
    └─ tbody
       └─ tr.template
          ├─ {rows[N].milestone}
          ├─ {rows[N].planned_date}
          ├─ {rows[N].actual_date}
          └─ {rows[N].status}

═══════════════════════════════════════════════════════════════════
8. ШПАРГАЛКА
═══════════════════════════════════════════════════════════════════

Текст → плейсхолдер:
  ✓ {category.field}
  ✗ "реальный текст"

Ячейка таблицы:
  ✓ {rows[N].<field>}     ← образец
  ✗ {rows[0].value: 42}   ← реальное значение

Слой таблицы:
  ✓ cmp.tbl-<name>
  ✓ tr.template           ← ОБРАЗЕЦ строки (одна)
  ✗ tr.row-1, tr.row-2    ← несколько строк

Открывашка:
  ✓ cmp.collapsible        ← тип компонента
  ✓ variants: collapsed + expanded
  ✓ tbl-controls (sticky header)
  ✓ btn.toggle (кнопка раскрытия)

Ширины ячеек:
  ✓ Cell (width: 100px)
  ✗ auto / hug content     ← плохо для адаптивности

═══════════════════════════════════════════════════════════════════
Конец документа.
Версия 2: 2026-07-29
Hermes Agent v0.18.0 на mima_g_01
═══════════════════════════════════════════════════════════════════
