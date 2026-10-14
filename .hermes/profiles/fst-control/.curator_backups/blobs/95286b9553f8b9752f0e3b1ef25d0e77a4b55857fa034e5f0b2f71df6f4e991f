# HTML-отчёт v1.0.3: секция 6 — переход на `<details>` per indicator

**Дата:** 2026-09-03
**Автор:** ROSTISLAV KUZNETSOV
**Контекст:** Сломанная вёрстка секции 6 в HTML-отчёте. После v1.0.0/v1.0.1 индикаторы 6.3, 6.4, 6.6, 6.8, 6.15, 6.16 не были видны как отдельные строки, ▼-кнопка отсутствовала, клик не раскрывал вложенную таблицу, подсветка работала только у 6.1.

## User's bug list (verbatim)

> 1) Нет раскрытия секций вложенных таблиц
> 2) Нет некоторых подпунктов (похоже, их строки имеют нулевую высоту). Нет 6.3, 6.4, 6.6, 6.8, 6.15, 6.16
> 3) Нет кнопки в виде треугольника в колонке "Детали"
> 4) Нет подсветки строк кроме 6.1 (нужно проверить)

User's preferred fix: «Нужно чинить генератор. Проекты пересоберёшь позже. Нам нужно починить генерацию отчётов, чтобы каждый новый HTML был правильным».

---

## Architecture v1.0.0/v1.0.1 (broken)

```html
<table class="tbl tbl-indicators">
  <tbody>
    <tr data-status="critical">
      <td>6.1</td><td>Юрлицо...</td><td>Нет</td>
      <td class="col-details"></td>   <!-- пустая ячейка -->
    </tr>
    <tr class="indicator-main-row" data-status="substantial">
      <td colspan="4" style="padding: 0;">     <!-- внешняя обёртка -->
        <details class="row-details-indicator">
          <summary class="hidden-summary"></summary>   <!-- НЕВИДИМЫЙ -->
          <div class="indicator-main-row-content">
            <table class="tbl-indicators-main-row">     <!-- вложенная таблица -->
              <tr>
                <td data-status="substantial">6.3</td>  <!-- статус на td, не на tr -->
                <td data-status="substantial">Прогнозы по ресурсам заданы</td>
                <td data-status="substantial">Вопросы, 703 ч</td>
                <td class="col-details">
                  <span class="col-details-marker">▼</span>   <!-- тут есть -->
                </td>
              </tr>
            </table>
            <div class="tbl-nested-wrapper">...</div>   <!-- display:none -->
          </div>
        </details>
      </td>
    </tr>
  </tbody>
</table>
```

**Why all 4 bugs manifested:**

| Bug | Cause |
|-----|-------|
| 1. Не раскрывается | `<summary class="hidden-summary">` имеет `display:none !important` — нативный `<details>` без видимого summary не открывается по клику. CSS `:checked` не помогает, потому что summary скрыт. |
| 2. Подпункты скрыты | Внешний `<tr colspan='4' style='padding: 0;'>` конфликтует с `<colgroup>` (colspan на tr внутри таблицы с colgroup — невалидно и ломает layout, особенно когда padding=0). Браузер рендерит это как «одна строка с мини-таблицей», но высота сжимается и подсветка не применяется. |
| 3. Нет ▼ в основной ячейке | В ячейке `<td class="col-details">` основной таблицы пусто. Треугольник живёт глубоко во вложенной таблице, невидимой по умолчанию. |
| 4. Нет подсветки | CSS `tr[data-status="critical"]` ищет атрибут на `<tr>`. А в коде он на `<td>`. Поэтому фон применяется только у 6.1, где внешний `<tr>` имел правильный атрибут. |

## Architecture v1.0.3 (fixed — current)

**Каждый индикатор = ОТДЕЛЬНЫЙ `<details>`**, не одна большая таблица с `<details>` внутри:

```html
<table class="tbl tbl-indicators tbl-indicators-header">
  <thead><tr><th>#</th><th>Показатель</th><th>Результат</th><th>Детали</th></tr></thead>
</table>

<details class="indicator-details" data-status="...">      <!-- 6.1 -->
  <summary>
    <table class="tbl tbl-indicators">
      <tr data-status="critical">                            <!-- статус на <tr> -->
        <td>6.1</td><td>Юрлицо...</td><td>Нет</td>
        <td class="col-details"></td>                         <!-- пустая, нет данных -->
      </tr>
    </table>
  </summary>
</details>

<details class="indicator-details has-details" data-status="...">   <!-- 6.3 -->
  <summary>
    <table class="tbl tbl-indicators">
      <tr data-status="substantial">
        <td>6.3</td><td>Прогнозы по ресурсам заданы</td><td>Вопросы, 703 ч</td>
        <td class="col-details"><span class="col-details-marker">▼</span></td>
      </tr>
    </table>
  </summary>
  <div class="indicator-details-panel">      <!-- виден только когда [open] -->
    <div class="tbl-nested-title">Месяцы с проблемами в прогнозах</div>
    <table class="tbl-nested">
      <tr data-status="critical">
        <td>1</td><td>Октябрь-2026</td><td>Трудозатраты не заданы, ...</td>
      </tr>
    </table>
  </div>
</details>

<details class="indicator-details" data-status="normal"> ... <!-- 6.2 (без details) --> </details>
```

**Что даёт:**
- Каждый `<details>` — самодостаточный, его раскрытие не зависит от соседей.
- `data-status` всегда на `<tr>` главной мини-таблицы → подсветка работает у всех 16 строк.
- ▼ — внутри `<td class="col-details">` той же мини-таблицы, что и текст индикатора → виден на основной строке.
- Клик по `<summary>` (нативный) открывает `<details>[open]`, что делает `.indicator-details-panel { display: block }`.

---

## CSS v1.0.3 (новые правила)

```css
/* v1.0.3: details + summary + panel */

/* <details> = блочный, без рамки */
details.indicator-details {
    display: block;
    margin: 0;
}

/* <summary> — кликабельная обёртка мини-таблицы. Убираем нативный marker */
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

/* Маркер ▼ → ▲ при [open] */
.col-details-marker {
    display: inline-block;
    font-size: 16px;
    line-height: 1;
    color: #475569;
}
details.indicator-details[open] > summary .col-details-marker {
    font-size: 0;                    /* прячем оригинальный ▼ */
    color: #0284c7;
}
details.indicator-details[open] > summary .col-details-marker::after {
    content: "▲";
    font-size: 16px;                  /* показываем ▲ */
}

/* Panel виден только когда details[open] */
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

---

## Pitfall #188 (v1.0.2 → v1.0.3): `<input type='checkbox'> + ~ ` не масштабируется

**Промежуточная попытка v1.0.2** (НЕ используется, зафиксирована как pitfall):

```html
<input type="checkbox" class="indicator-toggle" id="toggle-X-N" hidden>
<label for="toggle-X-N">
  <table><tr>...</tr></table>
</label>
<div class="indicator-details-panel">...</div>
```

```css
input.indicator-toggle:checked ~ .indicator-details-panel { display: block; }
input.indicator-toggle:not(:checked) ~ .indicator-details-panel { display: none; }
```

**Почему сломано:** CSS-селектор `~` — «любой следующий сиблинг». Это значит, что **любой** checked input выше показывает **все** panels ниже (включая чужие). При наличии 6+ индикаторов с details панели начинали показываться хаотично.

**Доказательство (live console):**
```js
document.querySelectorAll("input.indicator-toggle").length  // 6
document.querySelectorAll("input.indicator-toggle:checked").length  // 1
// но panels.length == 6, причём display:block стоит у 4 из них
```

**Fix:** использовать нативный `<details>` — он сам инкапсулирует состояние `open` и не имеет проблем с глобальной областью видимости селекторов.

**Урок:** для нативного expand/collapse **в HTML-отчётах без JS** используйте `<details>`, а не `<input type='checkbox' hidden>`. `<input>` работает только для одиночных тоглов или когда DOM-дерево жёстко контролируется (никаких соседей того же класса).

---

## Pitfall #189: нативный `<details>`-marker конфликтует с кастомным `▼`

Браузеры рисуют свой треугольник рядом с `<summary>` через `::-webkit-details-marker` (Chrome/Safari) и `::marker` (Firefox). Если в `<td class='col-details'>` есть свой `<span class='col-details-marker'>▼</span>`, в браузере будут **ДВА** треугольника: браузерный слева + наш справа.

**Fix (обязательно для v1.0.3):**
```css
details.indicator-details > summary::-webkit-details-marker { display: none; }
details.indicator-details > summary::marker { display: none; content: ""; }
```

Без этих двух строк пользователь видит **два ▼** в одной строке (см. первый прогон v1.0.3 в этой сессии).

---

## Pitfall #190: клик через browser.ax-tree не раскрывает `<details>`

При отладке через `browser_click(ref=...)` клик приходит в `<td>`, а `<summary>` остаётся без события. `<details>` не открывается, хотя DOM-логически всё правильно.

**Workaround для проверки:** открывайте программно через `document.querySelectorAll("details.indicator-details")[i].open = true` — это надёжнее.

**Live-проверка:** смотрите `.indicator-details-panel { display: block }` через `getComputedStyle`.

---

## Pre-ship checklist v1.0.3 (обновление для пункта 10 в pitfalls-v1001)

После правки секции 6 в HTML:

- [ ] Все 16 строк видны (`document.querySelectorAll('details.indicator-details').length === 16`)
- [ ] У индикаторов без `table` — пустая `<td class='col-details'></td>` (без `▼`)
- [ ] У индикаторов с `table` — `<span class="col-details-marker">▼</span>` в `<td class='col-details'>`
- [ ] Подсветка строк работает (`background-color` соответствует `data-status`)
- [ ] Клик по ▼ (или по всей строке) раскрывает panel
- [ ] При раскрытии ▼ → ▲, при закрытии ▲ → ▼
- [ ] Браузерный marker `<summary>` НЕ виден (два правила `display: none`)
- [ ] Нет дублей секций (раздел 6 один, открывается по `id="section_6_indicators"` в `<details open>`)

---

## Lessons из сессии v1.0.3

1. **`~` селектор имеет leaky scoping.** Любой checked input выше показывает всё ниже. Для нативного expand/collapse используйте `<details>`.
2. **Структура «одна большая таблица с `<details>` внутри `<td>`»** — тупик. HTML-table layout конфликтует с `display:none` на summary, colspan, и padding. Лучше: много маленьких `<details>`, каждый со своей мини-таблицей.
3. **`data-status` ВСЕГДА на `<tr>`, не на `<td>`.** CSS `tr[data-status]` — единственный надёжный селектор для подсветки строк.
4. **Нативный `<details>` + `<summary>` внутри `<table>`-ячеек** — рабочий паттерн, но требует:
   - `display: none` для обоих псевдо-маркеров (`::-webkit-details-marker`, `::marker`)
   - кастомный маркер через `<span>` с тогглом `▼`/`▲` при `[open]`
   - `<summary>` оборачивает мини-таблицу как блок (`display: block`)
