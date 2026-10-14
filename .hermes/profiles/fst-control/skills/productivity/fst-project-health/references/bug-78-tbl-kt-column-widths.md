# Bug #78: `table.tbl-kt` — нет фиксированных ширин колонок (added 2026-08-22)

**Live-probe:** 2026-08-22, проект 503-434 (по жалобе пользователя: «значения в Колонках "код", "План" и "прогноз" не умещаются. И в поле "Наименование" нет переноса по словам»).

**Причина:** в `templates/report.css` для `table.tbl-kt th/td` был задан только `height: 30px`, **без ширин колонок** (в отличие от `tbl-overdue`, где `?ProjectId=...` фильтр добавил их).

**Симптомы:**
- Колонки `#`, `Код`, `План`, `Прогноз` растягивались по содержимому
- Длинные наименования вылезали за рамку колонки
- Даты `2026-08-13` обрезались, потому что `План` был ~70px вместо 110px
- `Наименование` без `word-wrap: break-word` — длинные названия КТ растягивали строку

**Фикс в `templates/report.css`:**
```css
table.tbl-kt th,
table.tbl-kt td { height: 30px; }

/* Ширины для tbl-kt (раздел 3): */
table.tbl-kt th:nth-child(1), td:nth-child(1) { width: 40px; }    /* # */
table.tbl-kt th:nth-child(2), td:nth-child(2) { width: 90px; }    /* Код */
table.tbl-kt th:nth-child(3), td:nth-child(3) { width: 552px; }   /* Наименование */
table.tbl-kt th:nth-child(4), td:nth-child(4) { width: 110px; }   /* План */
table.tbl-kt th:nth-child(5), td:nth-child(5) { width: 110px; }   /* Прогноз */
table.tbl-kt td { word-wrap: break-word; overflow-wrap: break-word; }
```

**Сумма: 40+90+552+110+110 = 902px** (узкие колонки для коротких данных + широкая для названий).

**Регрессионный тест:** `tests/test_skill_md_integrity.py::TestSkillMdIntegrity::test_tbl_kt_has_column_widths`:
- ✅ Ширины для всех 5 колонок
- ✅ `План` и `Прогноз` >= 110px (чтобы `2026-08-13` помещалось)
- ✅ `Наименование` >= 400px
- ✅ `word-wrap: break-word` присутствует

**Общий урок (применимо ко всем таблицам скилла):** таблицы отчёта (`tbl-kt`, `tbl-overdue`, `tbl-finance`, `tbl-completeness`, `tbl-tech`) **всегда** должны иметь:
1. Фиксированные ширины колонок через `nth-child(N)`.
2. `word-wrap: break-word` для переноса длинных наименований.
3. Достаточную ширину для дат в формате `YYYY-MM-DD` (>= 100px).
4. Достаточную ширину для названий КТ/проектов (>= 400px).

**Чек-лист при добавлении новой таблицы:**
```bash
# 1. Проверить что у всех колонок есть явная width
grep -A 30 "table.tbl-NEW-CLASS" templates/report.css | grep "nth-child"

# 2. Проверить word-wrap для ячеек
grep -A 30 "table.tbl-NEW-CLASS" templates/report.css | grep "word-wrap"

# 3. Запустить регрессионный тест
python3 tests/test_skill_md_integrity.py
```

**См. также:** Bug #77 (тот же баг для `tbl-overdue`).
