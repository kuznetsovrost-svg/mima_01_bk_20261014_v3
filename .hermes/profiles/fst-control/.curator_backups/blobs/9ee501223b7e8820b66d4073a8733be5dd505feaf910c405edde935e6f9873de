# Section 6 — v1.0.4 финальная архитектура (3 попытки до рабочего варианта)

**Статус:** ✅ работает с 2026-09-03. Применяется ко всем отчётам по 4 проектам.

**Контекст:** v1.0.0/v1.0.1 имел 4 одновременных бага:
1. Пустая колонка «Детали» (нет ▼).
2. Скрытые подпункты 6.3, 6.4, 6.6, 6.8, 6.15, 6.16 (нулевая высота строк).
3. Раскрытие вложенных таблиц не работает.
4. Подсветка строк применяется только к 6.1 (другие строки белые).

## Корневая причина (v1.0.0/v1.0.1)

Генератор секции 6 в `build_html_report.py` создавал **двойную обёртку**:

```html
<tr class='indicator-main-row' data-status="...">
  <td colspan='4' style='padding: 0;'>
    <details>
      <summary class='hidden-summary'></summary>   <!-- display:none! -->
      <div class='indicator-main-row-content'>
        <table class='tbl tbl-indicators-main-row'>
          <tr>
            <td data-status="...">6.X</td>          <!-- data-status на <td>! -->
            <td class='col-details'><span>▼</span></td>
          </tr>
        </table>
        <div class='tbl-nested-wrapper'>...</div>   <!-- display:none -->
      </div>
    </details>
  </td>
</tr>
```

**4 бага:**
1. **Пустая «Детали»**: `<td>` основной таблицы имеет `colspan='4'` и пустой `col-details`. Маркер ▼ есть только во вложенной таблице, которую не видно.
2. **Скрытые подпункты**: `colspan='4'` + `padding:0` + вложенная таблица ломают layout основной таблицы.
3. **Раскрытие не работает**: `<summary>` с `display:none` — нативный `<details>` без видимого summary не открывается.
4. **Подсветка не работает**: CSS `tr[data-status]` ищет атрибут на `<tr>`, а в коде он на `<td>` внутри вложенной таблицы.

## Попытка v1.0.2 (checkbox + label) — ❌ сломано

```html
<input type='checkbox' class='indicator-toggle' id='x' hidden aria-hidden='true'>
<label for='x' class='indicator-label'>
  <table class='tbl tbl-indicators'>
    <tr data-status="..."><td>6.X</td>...<td class='col-details'>▼</td></tr>
  </table>
</label>
<div class='indicator-details-panel'>...</div>
```

CSS:
```css
input.indicator-toggle:checked ~ .indicator-details-panel { display: block; }
input.indicator-toggle:not(:checked) ~ .indicator-details-panel { display: none; }
```

**Почему сломано:** CSS-селектор `~` — это «любой следующий сиблинг». Когда несколько
индикаторов идут подряд, **любой** checked input **выше** показывает **все** панели
**ниже**. Например: input#1 checked → показаны panel#1, panel#2, panel#3 (все).

Проверено в DevTools: `document.querySelectorAll('.indicator-details-panel')[N].display` —
`block` для всех панелей после первого checked input, независимо от их собственного состояния.

## Попытка v1.0.3 (нативный `<details>`) — ✅ работает

```html
<details class='indicator-details' data-status="...">
  <summary>
    <table class='tbl tbl-indicators'>
      <tr data-status="critical">
        <td>6.1</td>
        <td>Юрлицо проекта/пресейла указано</td>
        <td>Нет</td>
        <td class='col-details'>
          <span class='col-details-marker'>▼</span>
        </td>
      </tr>
    </table>
  </summary>
  <div class='indicator-details-panel'>
    <div class='tbl-nested-title'>...</div>
    <table class='tbl-nested'>...</table>
  </div>
</details>
```

**Почему работает:** нативный `<details>` управляет видимостью **только своего**
контента. Никакой CSS-селектор не «утекает» на соседние элементы.

### Критичные CSS-правила (должны быть в `templates/report.css`)

```css
/* === v1.0.4: <details> оборачивает индикатор === */

/* <details> = блочный, без рамки */
details.indicator-details {
    display: block;
    margin: 0;
}

/* <summary> — кликабельная обёртка мини-таблицы.
   Убираем нативный marker браузера, рисуем свой через .col-details-marker. */
details.indicator-details > summary {
    list-style: none;
    cursor: pointer;
    display: block;
    margin: 0;
    padding: 0;
}
details.indicator-details > summary::-webkit-details-marker { display: none; }
details.indicator-details > summary::marker { display: none; content: ""; }
details.indicator-details > summary > table.tbl-indicators { margin: 0; }

/* Ховер по строке — лёгкая подсветка треугольника */
details.indicator-details > summary:hover .col-details-marker { color: #0284c7; }

/* Когда details открыт — маркер ▲ (через ::after на td.col-details) */
details.indicator-details[open] > summary .col-details-marker {
    color: #0284c7;
}
details.indicator-details[open] > summary .col-details-marker::after {
    content: "▲";
}
details.indicator-details[open] > summary .col-details-marker {
    font-size: 0;     /* убираем оригинальный ▼ */
}
details.indicator-details[open] > summary .col-details-marker::after {
    font-size: 16px;  /* показываем псевдоэлемент */
}

/* Panel с вложенной таблицей — виден только когда details[open] */
details.indicator-details .indicator-details-panel {
    display: none;
    padding: 0 40px 12px;
    background: #fafafa;
    border-bottom: 1px solid #e2e8f0;
}
details.indicator-details[open] .indicator-details-panel {
    display: block;
}
```

### Техника замены ▼ → ▲ через `font-size: 0` + `::after`

Проблема: оригинальный символ `▼` внутри `<span class='col-details-marker'>` занимает
место, и при добавлении `::after { content: "▲" }` получается `▼▼` (два треугольника).

Решение:
```css
/* Скрываем сам span (font-size: 0) */
details[open] .col-details-marker { font-size: 0; }
/* Показываем только ::after с реальным размером */
details[open] .col-details-marker::after {
    content: "▲";
    font-size: 16px;
}
```

Без `font-size: 0` родителя `::after` рендерится **после** оригинального `▼`,
получая два символа.

## Подсветка строк — `data-status` всегда на `<tr>`

В v1.0.0/v1.0.1 атрибут `data-status` ставился на `<td>`:
```html
<td data-status="critical">6.X</td>
```

CSS правило `tr[data-status="critical"]` не срабатывает (атрибут не на `<tr>`).
В v1.0.4 атрибут **всегда** на `<tr>`:
```html
<tr data-status="critical">
  <td>6.1</td>
  <td>Юрлицо...</td>
  <td>Нет</td>
  <td class='col-details'>▼</td>
</tr>
```

CSS:
```css
table.tbl-indicators tr[data-status="critical"]      { background: #fee2e2; }
table.tbl-indicators tr[data-status="substantial"]    { background: #fef3c7; }
table.tbl-indicators tr[data-status="informational"]  { background: #dbeafe; }
table.tbl-indicators tr[data-status="normal"]         { background: #ffffff; }
```

## Pitfall-сводка (добавить в `references/html-report-pitfalls.md`)

### Pitfall #188 — `~` selector leaky scoping
**Проблема:** `input:checked ~ .panel` показывает **все** панели после input,
не только свою.
**Решение:** Использовать нативный `<details>`, не `checkbox+label`.

### Pitfall #189 — `<summary>` нативный marker
**Проблема:** Браузер рисует свой треугольник ▼ рядом с `<summary>`. Получается
`▼ ▼` (наш + нативный).
**Решение:** Скрыть `::-webkit-details-marker` И `::marker`.

### Pitfall #190 — `data-status` на `<td>` vs `<tr>`
**Проблема:** CSS `tr[data-status]` не работает, если атрибут на `<td>`.
**Решение:** Всегда ставить `data-status` на `<tr>`, не на `<td>`.

### Pitfall #191 — `font-size: 0` для замены символа через `::after`
**Проблема:** `::after { content: "▲" }` рендерится рядом с оригинальным `▼`.
**Решение:** `font-size: 0` на родителе + `font-size: 16px` на `::after`.

## Тест после правки

```bash
cd ~/.hermes/profiles/fst-control/skills/productivity/fst-project-health/scripts
rm -f /tmp/.cache_run_all_*.json /tmp/.cache_project_card_*.json
python3 run_all.py --code 504-595 --no-cache
```

Открыть `/tmp/project_504-595_report.html` в браузере:
- Все 16 строк (6.1 — 6.16) видны как отдельные.
- У 6.1, 6.8 — красный фон.
- У 6.3, 6.4, 6.16 — жёлтый.
- У 6.6 — голубой.
- У 6.3, 6.4, 6.6, 6.8, 6.15, 6.16 — клик по строке раскрывает вложенную таблицу.
- ▼ меняется на ▲ при раскрытии.

## Что ещё можно улучшить (бэклог)

- **▼ серый неактивный** для 9 подпунктов без данных (требует изменения логики
  `build_html_report.py` — передавать `has_data` и не создавать `<details>` если
  `False`).
- **Размер ▼ ≤ 10px, цвет `#1e40af`** (сейчас 16px серый).
- **Сетка вложенных таблиц темнее** (`#cbd5e1` вместо `#e2e8f0`, толщина 1px).
- **Убрать голубой** для 6.6 (только красный/жёлтый/белый).

См. `references/section-6-backlog-2026-09-03.md`.
