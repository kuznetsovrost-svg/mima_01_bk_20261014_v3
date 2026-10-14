# Inline SVG for JSON Data Visualization (playbook)

**Дата:** 2026-08-22
**Назначение:** Когда `versioned-json-data-model` используется для аналитических отчётов (тренды, динамика, агрегации) — как рендерить графики в HTML без зависимостей.

---

## TL;DR

| Подход | Сложность | Качество | Печать PDF | Зависимости |
|--------|:---------:|:--------:|:----------:|:-----------:|
| **Inline SVG** ✅ | Средне | Высокое | ✅ отлично | Нет |
| Chart.js (CDN) | Низко | Высокое | ❌ | Да |
| D3.js (CDN) | Высоко | Очень высокое | ❌ | Да |
| Canvas | Высоко | Высокое | ❌ raster | Нет |
| Matplotlib (PNG) | Низко | Отличное | ✅ | Нет |

**Рекомендация:** Inline SVG — без зависимостей, печатается, доступен.

---

## Базовые элементы SVG (cheatsheet)

### Линия (line chart)

```html
<polyline points="0,50 50,30 100,40" fill="none" stroke="#dc2626" stroke-width="2"/>
```

### Окружность (donut)

```html
<circle cx="60" cy="60" r="40" fill="none" stroke="#dc2626" stroke-width="20"
        stroke-dasharray="60 251" transform="rotate(-90 60 60)"/>
```

### Прямоугольник (bar)

```html
<rect x="0" y="20" width="20" height="40" fill="#dc2626"/>
```

### Текст (метки)

```html
<text x="60" y="60" text-anchor="middle" font-size="14" fill="#000">6</text>
```

### Группа (структура)

```html
<g transform="translate(50,50)">
  <line x1="0" y1="0" x2="100" y2="0"/>
</g>
```

---

## 5 готовых паттернов (для трендов)

### 1. Line chart (multi-line для трендов по разделам)

```html
<svg viewBox="0 0 600 250" style="width:100%; max-width:600px;">
  <!-- сетка -->
  <line x1="50" y1="220" x2="580" y2="220" stroke="#e5e7eb"/>
  <line x1="50" y1="0" x2="50" y2="220" stroke="#e5e7eb"/>
  <!-- 3 линии по разделам -->
  <polyline points="..." stroke="#dc2626" fill="none" stroke-width="2.5"/>
  <polyline points="..." stroke="#f59e0b" fill="none" stroke-width="2.5"/>
  <polyline points="..." stroke="#3b82f6" fill="none" stroke-width="2.5"/>
  <!-- точки -->
  <circle cx="x" cy="y" r="4" fill="white" stroke="#dc2626" stroke-width="2.5"/>
  <!-- подписи осей -->
  <text x="x" y="240" text-anchor="middle" font-size="10">01.06</text>
</svg>
```

### 2. Step chart (для вердикта во времени)

```html
<polyline points="50,200 150,200 150,150 250,150 250,100"
          fill="none" stroke="#dc2626" stroke-width="3"/>
```

Линия идёт **горизонтально** потом **вертикально** — показывает моменты переходов.

### 3. Stacked area (общая динамика)

```html
<path d="M0,0 L100,0 L100,50 L0,50 Z" fill="#dc2626" opacity="0.85"/>
```

Строится по cumulative values. Каждый слой — `polyline` верхней границы + `polyline` нижней границы + заливка.

### 4. Sparkline (минималистичный тренд)

```html
<svg width="100" height="30" viewBox="0 0 100 30">
  <polyline points="0,20 25,15 50,18 75,10 100,8"
            fill="none" stroke="#10b981" stroke-width="1.5"/>
</svg>
```

### 5. Donut (для сводки)

```html
<svg viewBox="0 0 100 100" style="width:120px;height:120px;">
  <!-- Фон -->
  <circle cx="50" cy="50" r="40" fill="none" stroke="#fee2e2" stroke-width="20"/>
  <!-- Critical (14/17 = 82%) -->
  <circle cx="50" cy="50" r="40" fill="none" stroke="#dc2626" stroke-width="20"
          stroke-dasharray="82 251" transform="rotate(-90 50 50)"/>
  <!-- Warning (3/17 = 18%) -->
  <circle cx="50" cy="50" r="40" fill="none" stroke="#f59e0b" stroke-width="20"
          stroke-dasharray="18 251" stroke-dashoffset="-82" transform="rotate(-90 50 50)"/>
</svg>
```

**Расчёт `stroke-dasharray`:**
- Окружность = 2π × r = 251 (для r=40)
- Доля × 251 = длина дуги
- `stroke-dashoffset` сдвигает следующий сегмент

---

## Стандартная палитра (для health-отчётов)

| Цвет | Hex | Назначение |
|------|-----|-----------|
| Critical | `#dc2626` | Красный — серьёзные проблемы |
| Warning | `#f59e0b` | Оранжевый — требует внимания |
| Info | `#3b82f6` | Синий — информационные |
| Healthy | `#10b981` | Зелёный — всё ок |
| Neutral | `#9ca3af` | Серый — нет данных |
| Grid | `#f3f4f6` | Светло-серая сетка |
| Axis | `#9ca3af` | Оси |
| Text | `#374151` | Основной текст |
| Muted | `#6b7280` | Второстепенный |

---

## CSS-стили (reusable)

```css
/* Линии тренда */
.trend-critical { stroke: #dc2626; stroke-width: 2.5; fill: none; }
.trend-warning  { stroke: #f59e0b; stroke-width: 2.5; fill: none; }
.trend-info     { stroke: #3b82f6; stroke-width: 2.5; fill: none; }
.trend-healthy  { stroke: #10b981; stroke-width: 2.5; fill: none; }

/* Точки */
.point-critical { fill: #dc2626; }
.point-warning  { fill: #f59e0b; }
.point-info     { fill: #3b82f6; }
.point-healthy  { fill: #10b981; }

/* Оси */
.axis-line { stroke: #d1d5db; stroke-width: 1; }
.axis-text { font-size: 11px; fill: #6b7280; }

/* Сетка */
.grid-line { stroke: #f3f4f6; stroke-width: 1; stroke-dasharray: 2,2; }

/* Заголовок */
.chart-title { font-size: 14px; font-weight: 600; fill: #111827; }
.legend-text { font-size: 11px; fill: #4b5563; }
```

---

## Python-генератор (шаблон)

```python
def line_chart(data, title="", x_label="", y_label="", color="#dc2626"):
    """data: [(date_short, value), ...]"""
    width, height = 600, 250
    margin = 50
    
    if not data:
        return f'<svg viewBox="0 0 {width} {height}"><text>No data</text></svg>'
    
    max_v = max(v for _, v in data) * 1.2 or 1
    n = len(data)
    
    def x(i): return margin + i * (width - 2 * margin) / max(n - 1, 1)
    def y(v): return height - margin - (v / max_v) * (height - 2 * margin)
    
    points = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, (_, v) in enumerate(data))
    
    svg = f'''<svg viewBox="0 0 {width} {height}" style="width:100%; max-width:600px; display:block;">
  <text x="{width//2}" y="20" text-anchor="middle" font-weight="bold">{title}</text>
  <line x1="{margin}" y1="{height - margin}" x2="{width - margin}" y2="{height - margin}" class="axis-line"/>
  <line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height - margin}" class="axis-line"/>
  <polyline points="{points}" stroke="{color}" fill="none" stroke-width="2.5"/>
'''
    for i, (date_short, value) in enumerate(data):
        svg += f'<circle cx="{x(i):.1f}" cy="{y(value):.1f}" r="4" fill="white" stroke="{color}" stroke-width="2.5"/>\n'
        svg += f'<text x="{x(i):.1f}" y="{height - margin + 16}" text-anchor="middle" class="axis-text">{date_short}</text>\n'
    svg += '</svg>'
    return svg
```

---

## Pitfalls

### S1. SVG внутри `<img>` теряет стили

`<img src="chart.svg">` работает, но `<img>` не позволяет переопределить CSS или добавить JavaScript. Если нужно кастомизировать стили или интерактивность — **inline SVG** (вставлять прямо в HTML).

### S2. `viewBox` без `width`/`height` атрибутов даёт неожиданные размеры

`viewBox="0 0 600 250"` без `width` и `height` = рендерится как 300×150 (default). **Всегда** указывайте `width`/`height` или используйте `style="width:100%; height:auto;"`.

### S3. `stroke-dasharray` неправильно рассчитан для donut

Если `stroke-dasharray` сумма меньше длины окружности — остаток не закрашивается. **Проверяйте:** сумма всех дуг = circumference = 2π × r.

### S4. Cyrillic в `<text>` без указания `font-family`

Без явного `font-family` SVG `<text>` может отображать кириллицу через serif fallback (Times New Roman). **Всегда** добавляйте:

```html
<svg style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;">
```

Или глобально через CSS:

```css
svg { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
```

### S5. `text-anchor` без указания text отображается не по центру

`<text x="100" y="50">Text</text>` — текст начинается в (100, 50). Чтобы центрировать:
- `text-anchor="middle"` (горизонтально)
- `dominant-baseline="central"` (вертикально, для circle)

### S6. HTML escaping в динамических подписях

Если вы рендерите SVG через f-string с пользовательским вводом — **экранируйте** HTML/JS-чувствительные символы:

```python
from html import escape
title_escaped = escape(user_title)
svg = f'<text>{title_escaped}</text>'
```

Без escape вредоносный ввод может сломать SVG или выполнить XSS.

---

## Ресурсы

- **MDN SVG**: https://developer.mozilla.org/en-US/docs/Web/SVG
- **W3C SVG spec**: https://www.w3.org/TR/SVG/
- **D3 Gallery** (для вдохновения): https://observablehq.com/@d3/gallery
- **Tufte principles**: https://www.edwardtufte.com/tufte/books_vdqi
- **FT Visual Vocabulary**: https://github.com/Financial-Times/chart-doctor/tree/main/visual-vocabulary
- **Stacked area chart**: https://observablehq.com/@d3/stacked-area-chart
- **Multi-line chart**: https://observablehq.com/@d3/multi-line-chart
- **Donut chart**: https://observablehq.com/@d3/donut-chart

---

## Когда НЕ использовать Inline SVG

| Сценарий | Альтернатива |
|----------|------------|
| **Интерактивные zoom/pan** | D3.js |
| **Real-time обновления** (WebSocket) | Chart.js |
| **Сложные многомерные графики** (sankey, treemap) | ECharts, D3 |
| **Огромный dataset (10K+ точек)** | Canvas (для производительности) |
| **Печать на бумаге** с особыми требованиями | Matplotlib → PDF |

Для всех остальных случаев — Inline SVG оптимален.

---

## Связь с `fst-project-trends` (будущий скилл)

Когда `fst-project-trends` будет создан, он будет использовать **5 графиков** на основе Inline SVG:

1. **Multi-line chart** — Critical по разделам (s3, s5, s6) по датам
2. **Step chart** — общий вердикт во времени
3. **Multi-line** — Effort (plan / forecast / fact)
4. **Stacked area** — суммарная динамика проблем
5. **Multi-line** — финансы (акты, оплаты, Δ)

Подробности — `/tmp/trend-report-design/docs/svg-playbook.md` (полный playbook с 5 паттернами + 7 источниками).

