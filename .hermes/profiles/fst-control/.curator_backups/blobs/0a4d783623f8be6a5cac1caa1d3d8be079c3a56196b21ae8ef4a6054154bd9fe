# 6.16 — Метки КП (проект/пресейл)

## Эскиз

`"Да/Нет"` + вложенная таблица с КТ без меток.

- ✅ Все КТ с меткой → `"Да"` (Норма, ▼ неактивна)
- ⚠️ Хотя бы одна без метки → `"Нет"` + таблица (Существенное)

Колонки таблицы: #, Код (Point.Code), Тип (Point.pcdName — "К"/"Р"), Наименование, План (PlanDate), Прогноз (ForecastDate).

## Реализация

`scripts/project_indicators.py::check_kp_labels()` + `scripts/kp_labels_thresholds.py::has_label()`.

## Логика метки (Pitfall #142 + #152)

Метка считается **определённой** если выполняется ОДНО из условий:

1. `PointTagName ∈ {"Проект", "Пресейл"}`
2. `isprojectbudget == True` ИЛИ `ispresalebudget == True`

Невалидные значения `PointTagName`: `None`, `""`, `"Процесс"`, и т.д. (Pitfall #142).

Поля `isprojectbudget`/`ispresalebudget` — ссылки на справочник `ActivityPhase`. «Нет метки» = **`None`** в обоих полях, а НЕ `False` в обоих (Pitfall #152):

```python
def has_label(row):
    ipb = row.get("isprojectbudget")
    ipsb = row.get("ispresalebudget")
    if ipb is None and ipsb is None:
        return False  # метка не назначена
    if ipb is True or ipsb is True:
        return True   # есть метка
    return False      # остальные случаи тоже невалидны
```

**Применимо ко всем индикаторам, проверяющим семантически взаимоисключающие поля.**

## Исключения (Pitfall #143)

Обязательные КТ из `MANDATORY_KT_BY_STAGE[current_stage]` (из справочника 6.2) **исключаются** из проверки меток.

```python
from lc_stage_kt_registry import MANDATORY_KT_BY_STAGE
mandatory_kts = MANDATORY_KT_BY_STAGE.get(current_stage, [])
is_mandatory = any(mk.lower() in name.lower() for mk in mandatory_kts)
if is_mandatory:
    continue
```

## Pitfall #144: метка проверяется для ВСЕХ КТ проекта, не только привязанных к бюджету

User correction (2026-09-03): «Отсутствие метки "проект/пресейл" является замечанием даже в том случае, если элемент КП не привязан к бюджету».

Используем `AllMyPoint` (все КТ) как источник истины, а не только строки `ProjectBudgetCompleteBusiness`.

## Источники данных

| View | Для чего |
|------|----------|
| `Project/ProjectBudgetCompleteBusiness` | `isprojectbudget`/`ispresalebudget` метки |
| `Point/AllMyPoint` | Code, pcdName (тип К/Р), PlanDate, ForecastDate, PointTagName |

## Live-probe на 504-595 (2026-09-03)

Сначала — все КТ с меткой `"Проект"`: `"Да"` (Норма).

После добавления 2 КТ (`104-734` с `Tag='?'`, `104-735` с `Tag='Процесс'`): `"Нет"` + 2 замечания:

- 104-734 Р Оринтологическое обеспечение (ловля ворон)
- 104-735 Р Изгнание чаек с помойки

## Итерации развития индикатора

| Итерация | Что добавлено |
|----------|---------------|
| 1 | Только привязанные к бюджету КТ. XOR. **Неправильно**. |
| 2 (Pitfall #144) | Все КТ через `AllMyPoint` |
| 3 (Pitfall #143) | Исключение обязательных КТ |
| 4 (Pitfall #142) | `"Процесс"` = недопустимая метка |
| 5 (Pitfall #152) | `None` в обоих полях = не определено |

## Файлы

- `scripts/project_indicators.py::check_kp_labels()` — основная функция
- `scripts/kp_labels_thresholds.py` — пороги (`has_label()` helper)
- Использует: `lc_stage_kt_registry.py::MANDATORY_KT_BY_STAGE` (Pitfall #143)