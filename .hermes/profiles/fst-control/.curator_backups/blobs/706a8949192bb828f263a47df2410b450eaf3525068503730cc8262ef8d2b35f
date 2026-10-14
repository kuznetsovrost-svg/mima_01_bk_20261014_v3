# Section 6 HTML rendering — итерация 2026-09-03

## Что зафиксировано

История правок `render_tbl6_indicators` + `templates/report.css` от первой
рабочей версии (16 индикаторов в таблице) до v1.1.0 (корректное
сворачивание вложенных таблиц по клику в колонку "Детали").

## Паттерн "клик в колонку "Детали" раскрывает вложенную таблицу"

**Финальная рабочая структура** (v1.1.0):

```html
<tr class="indicator-main-row" data-status="critical">
  <td colspan="4" style="padding: 0;">
    <details class="row-details-indicator">
      <summary class="hidden-summary"></summary>  <!-- скрыт через CSS -->
      <div class="indicator-main-row-content">
        <table class="tbl tbl-indicators-main-row">
          <colgroup>...4 колонки...</colgroup>
          <tbody><tr>
            <td class="col-num">6.1</td>
            <td class="col-name">Юрлицо...</td>
            <td class="col-result">Нет</td>
            <td class="col-details"><span class="col-details-marker">▼</span></td>
          </tr></tbody>
        </table>
        <div class="tbl-nested-wrapper">  <!-- появляется при [open] -->
          [вложенная таблица]
        </div>
      </div>
    </details>
  </td>
</tr>
```

**Обязательные CSS:**

```css
/* Скрываем <summary> чтобы не было серой полосы */
.row-details-indicator > summary.hidden-summary {
    display: none !important;
}

/* Маркер ▼ в колонке "Детали" — реальный <span> в HTML, не ::before */
.col-details-marker {
    display: inline-block;
    font-size: 16px;
    line-height: 1;
    color: #475569;
    cursor: pointer;
}

/* При открытии <details> меняется цвет маркера */
.row-details-indicator[open] .col-details-marker {
    color: #0284c7;
}

/* Вложенная таблица появляется при раскрытии */
.row-details-indicator .tbl-nested-wrapper {
    display: none;
    padding: 0 40px 12px;
    background: #fafafa;
    border-bottom: 1px solid #e2e8f0;
}
.row-details-indicator[open] .tbl-nested-wrapper {
    display: block;
}
```

## ❌ Что НЕ работает (проверено)

| Подход | Почему не работает |
|--------|-------------------|
| `<table>` внутри `<td>` | Не сдвигает строки, "уезжает в бок" |
| `<details><summary></summary></details>` внутри `<td>` | Полоса с треугольником ▲/▼ добавляется между строками — выглядит лишне |
| `<td class='col-details'>▼</td>` без `<details>` | Текст "▼" есть, но не кликабельный, вложенная таблица не появляется |
| `::before` для треугольника | Не отображается в `<td>` внутри `<details>` (особенности туннелирования `::before`) |
| `<details>` оборачивает только вложенную таблицу | Между основной и вложенной появляется серая полоса с `<summary>` |

## ✅ Что работает

| Решение | Зачем |
|---------|-------|
| `<details>` оборачивает ОБЕ строки (основная + вложенная) | Один клик — одно действие |
| `<summary>` с `display: none !important` | Убирает серую полосу |
| Реальный `<span class='col-details-marker'>▼</span>` в HTML | Курсор `pointer`, кликабельность |
| `.col-details` курсор + `cursor: pointer` | Визуально показывает кликабельность |
| `[open] .tbl-nested-wrapper { display: block; }` | CSS-only раскрытие (без JS) |

## ⚠️ Антипаттерны в build_html_report.py

### `<h class class="section-6-title">`

Дублирующийся атрибут `class class` — должно быть `<h2 class="section-6-title">`.
Этот блок потом был полностью удалён (заголовок секции в `<summary>` родительского `<details>`).

### `SectionVerdict(verdict='Критическое', counts={...})` — repr() в f-string

`SectionVerdict` это dataclass без `__str__`. При f-string выводится `repr()`.
Решение: добавить `__str__` возвращающий `self.verdict` ИЛИ использовать `.verdict` явно.

## Подкраска строк

```css
table.tbl-indicators tr[data-status="critical"] {
    background: #fee2e2;  /* красный */
}
table.tbl-indicators tr[data-status="substantial"] {
    background: #fef3c7;  /* жёлтый */
}
table.tbl-indicators tr[data-status="informational"] {
    background: #dbeafe;  /* голубой */
}
table.tbl-indicators tr[data-status="normal"] {
    background: #ffffff;
}
```

## Ширины колонок (v1.1.0)

```css
table.tbl-indicators col.col-num { width: 60px; }
table.tbl-indicators col.col-name { width: 40%; }
table.tbl-indicators col.col-result {
    width: calc(60% - 130px);
    word-wrap: break-word;  /* перенос длинных значений */
}
table.tbl-indicators col.col-details { width: 70px; }  /* для слова "Детали" */

table.tbl-indicators td {
    word-wrap: break-word;
    overflow-wrap: break-word;
    vertical-align: middle;
}
```

## Текст preview в `<summary>` родительского `<details>`

```python
# В build_html_report.py::_extract_preview_section_6_indicators
label_map = {
    "Критическое": "Критическое замечание",
    "Существенное": "Существенное замечание",
    "Информационное": "Информационное замечание",
    "Норма": "Норма",
}
# Пример: "Критическое замечание: 2 крит., 3 сущ., 1 инф."
```

НЕ выводить отдельный блок "Вердикт раздела: ..." над таблицей —
это дублирует `<summary>` родительского `<details>`.

## End-to-end test ОБЯЗАТЕЛЕН после правки HTML рендера

Каждый раз когда меняешь `render_tbl6_indicators` или `report.css`:

1. `python3 scripts/run_all.py --code 504-595` — собрать отчёт
2. Открыть `/tmp/project_504-595_report.html` в браузере
3. Раскрыть секцию «Показатели проекта»
4. Кликнуть ▼ в нескольких строках — убедиться что вложенная таблица
   показывается БЕЗ серой полосы
5. Проверить подкраску 6.1 (critical — розовый) vs 6.2 (normal — белый)
