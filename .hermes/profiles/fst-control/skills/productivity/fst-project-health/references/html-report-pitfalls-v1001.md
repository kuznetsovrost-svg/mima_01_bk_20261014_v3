# HTML-отчёт: pitfalls и integration bugs (v1.0.1)

**Дата:** 2026-09-03
**Автор:** ROSTISLAV KUZNETSOV
**Контекст:** Секция 6 «Показатели проекта» — после реализации выявлены integration bugs.

## 1. Pitfall: дублирование class в HTML

```html
<h class="section-6-title">6. Показатели проекта</h>
<h2 class="section-6-title">6. Показатели проекта</h2>
```

**Fix:** в `build_html_report.py::render_*` функциях заменяем `<h class="...">` на `<h2 class="...">` (или `<h1>`).

## 2. Pitfall: `repr()` для dataclass в f-string

```python
@dataclass
class SectionVerdict:
    verdict: str  # "Критическое"
    counts: dict

    def __str__(self) -> str:
        return self.verdict  # обязательно!

lines.append(f"**Вердикт раздела:** {section_verdict}")
# SectionVerdict(verdict='Критическое', counts={...})

lines.append(f"**Вердикт раздела:** {section_verdict.verdict}")
# Критическое
```

**Fix:** всегда добавлять `__str__` метод в dataclass. В f-string явно использовать `.{field}`.

## 3. Pitfall: `dataclass` в JSON без разворачивания

```python
data = {"section_verdict": section_verdict}
json.dumps(data)  # TypeError: Object of type SectionVerdict is not JSON serializable

data = {
    "section_verdict": section_verdict.verdict,
    "section_counts": section_verdict.counts,
}
json.dumps(data)  # OK
```

**Fix:** перед сохранением в JSON всегда `dataclass.field` → `str/int/dict`.

## 4. Pitfall: размещение секции в HTML

```html
<details id="section_8"><!-- Показатели --></details>
<details id="section_7"><!-- Технические --></details>
<details id="section_6"><!-- Финансы --></details>
...
```

User: «Почему секция размещена в самом низу?»

**Правильно — секция 6 «Показатели» между 5 и 6 (Финансы):**
```html
<details id="section_5"><!-- Актуальность --></details>
<details id="section_6_indicators"><!-- Показатели (16 индикаторов) --></details>
<details id="section_6"><!-- Финансы --></details>
<details id="section_7"><!-- Технические --></details>
```

**Fix:** в `templates/report.html` секции идут в **том же порядке** что и `main()` в `run_all.py`. Согласовывать с `build_section_*` номерами.

## 5. Pitfall: вложенная таблица "уезжает в бок" внутри `<td>`

```html
<tr>
  <td>1</td>
  <td>...</td>
  <td>Результат</td>
  <td>
    <table>...</table>
  </td>
</tr>
```

User: «Почему вложенная таблица не сдвигает строки внизу, а уехала куда-то в бок?»

**Правильно — вложенная таблица в отдельной строке:**
```html
<tr data-status="critical">
  <td>1</td>
  <td>...</td>
  <td>Результат</td>
  <td>▼</td>
</tr>
<tr class="nested-row" data-status="critical">
  <td colspan="4" class="nested-cell">
    <table class="tbl-nested">...</table>
  </td>
</tr>
```

**Fix:** в `build_html_report.py::render_tbl6_indicators` создаём **отдельный `<tr>`** с `colspan="4"` для вложенной таблицы.

## 6. Pitfall: `<details>` + `<summary>` внутри `<td>` vs отдельной строки

**Внутри `<td>` (плохо):**
```html
<td><details><summary>▼</summary><table>...</table></details></td>
```

**Лучший подход — отдельная строка + CSS сворачиваемость:**
```html
<tr><td>1</td>...<td>▼</td></tr>
<tr class="nested-row">
  <td colspan="4" class="nested-cell">
    <details class="nested-details">
      <summary></summary>
      <div class="tbl-nested-wrapper">
        <table class="tbl-nested">...</table>
      </div>
    </details>
  </td>
</tr>
```

**CSS для кастомного треугольника:**
```css
.nested-details > summary {
    list-style: none;
    cursor: pointer;
    padding: 8px 12px;
    user-select: none;
    background: #e2e8f0;
    font-weight: 600;
}
.nested-details > summary::-webkit-details-marker { display: none; }
.nested-details > summary::before {
    content: "▼";
    display: inline-block;
    margin-right: 8px;
    font-size: 12px;
}
.nested-details[open] > summary::before { content: "▲"; }
```

## 7. Pitfall: забытая подстановка в template

```html
<span class="tbl-preview">{{ section_8_preview }}</span>
```

В `build_html_report.py` забыли добавить:
```python
.replace("{{ section_8_preview }}", preview_8)  # строка отсутствует!
```

**Результат:** в HTML видно `{{ section_8_preview }}` как есть.

**Fix:** при добавлении новой секции **всегда проверять**:
- В `templates/report.html` есть `{{ section_N_preview }}` и `{{ section_N_content }}`
- В `build_html_report.py` есть `.replace("{{ section_N_preview }}", preview_N)` и `.replace("{{ section_N_content }}", content_N)`
- В `build_html()` оба параметра вычисляются

## 8. Pitfall: ширина колонок "Детали" (40px мало)

```css
table.tbl-indicators col.col-details { width: 40px; }  /* обрезается */
table.tbl-indicators col.col-details { width: 50px; }  /* помещается */
```

**Стандартные ширины (для 4-колоночной таблицы 6.x):**
- `col-num`: 50px
- `col-name`: 40%
- `col-result`: calc(60% - 100px)  (оставшееся после двух col + col-details)
- `col-details`: 50px

## 9. Prefetch pattern (v1.0.1)

В `run_all_indicators()` **до** запуска 16 индикаторов вызывается `_prefetch_project_data()`, который загружает 7 общих view в кеш:

```python
def _prefetch_project_data(project, sid):
    fetch_with_cache(sid, "Project", "_get_entity_data_", ...)
    fetch_with_cache(sid, "Point", "AllMyPoint", ...)
    fetch_with_cache(sid, "Project", "ProjectResourcePlan", ...)
    fetch_with_cache(sid, "Project", "ProjectBudgetCompleteBusiness", ...)
    # + MyProject, InContractBudgetBusiness, ApprovedBudget
```

**Эффект (504-595, live 2026-09-03):**
- 1-й запуск: 32.93 сек
- 2-й запуск: 8.43 сек
- **Экономия: -74%** на втором запуске

## 10. Pre-ship checklist для новой секции

После добавления новой секции (например, 6.16 «Метки КП»):

- [ ] Unit-тесты проходят (7/7)
- [ ] `run_all.py --code 504-595` отрабатывает
- [ ] HTML валиден (нет `<h class=...>`, корректные теги)
- [ ] MD не содержит `repr()` (нет `SectionVerdict(...)`, `IndicatorResult(...)`)
- [ ] JSON файлы парсятся без ошибок
- [ ] Prefetch работает (2-й запуск -70-80%)
- [ ] Шаблон HTML содержит `{{ section_N_preview }}` И `{{ section_N_content }}`
- [ ] `build_html_report.py` подставляет оба
- [ ] CSS-стили применяются к новой таблице (`.tbl-*`)
- [ ] Секция в правильном месте HTML (по порядку)

## 11. Pitfall: повторное использование `<summary>` для колонки «Детали» в основной таблице

Когда основная таблица в `<details><summary>...`, **не выводите второй `<h2>` или `<summary>`** внутри `render_*()`. Иначе будет двойной заголовок + большие пробелы.

```python
out.append("<h2 class='section-6-title'>6. Показатели проекта</h2>")
out.append("<div class='section-6-verdict'>Вердикт: ...</div>")

out.append("<div class='section-6-verdict'>Вердикт: ...</div>')

.section-6-title { display: none; }
```

**Правило:** если секция обёрнута в `<details><summary>...</summary>...</details>`, внутри ничего лишнего не нужно.

## 12. Audit-tool: порядок секций

```bash
grep -A 1 "build_section_" scripts/run_all.py | grep -oP "build_section_\w+"
grep -oP 'id="section_\w+"' templates/report.html
```

Порядки должны **совпадать**.

## 13. Pitfall: large header spacing в CSS

```css
.section-6-title {
    margin-top: 24px;
    margin-bottom: 12px;
    padding: 8px 12px;
    background: #e0f2fe;
    border-left: 4px solid #0284c7;
    font-size: 16px;
    font-weight: 700;
}
```

**Compact (no big spaces around heading):**
```css
.section-6-title {
    display: none;  /* Скрыт — заголовок уже в <summary> */
}
.section-6-verdict {
    margin: 4px 0 8px 0;
    padding: 6px 12px;
    font-size: 14px;
    font-weight: 600;
}
```

## Live lessons из сессии v1.0.0 → v1.0.1

1. **Первая попытка добавить секцию 6 в HTML** — поставил в конец template. **Неправильно** — должна быть между 5 и 6 (Финансы). User: «Почему секция размещена в самом низу?».
2. **Первая попытка сделать заголовок** — использовал `<h class="section-6-title">`. **Дубль class**. User: «Почему оформление заголовка отличается?».
3. **Первая попытка вложенной таблицы** — внутри `<td>`. **"Уехала в бок"**. User: «Почему вложенная таблица не сдвигает строки внизу, а уехала куда-то в бок?».
4. **Первая попытка вердикта в MD** — `repr()` dataclass. **«SectionVerdict(verdict='...')»** в отчёте. User этого не заметил, но я нашёл через `render_tbl6_indicators`.
5. **Первая попытка JSON** — сохранял dataclass напрямую. **Ошибка сериализации**. Исправлено добавлением `__str__` и явным `.{field}`.

Все 5 багов — **integration bugs**, не видны в unit-тестах. Только через end-to-end pipeline + визуальный review.
