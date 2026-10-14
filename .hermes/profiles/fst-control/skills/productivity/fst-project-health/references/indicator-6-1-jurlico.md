# Индикатор 6.1 — Юрлицо проекта/пресейла указано

**Дата:** 2026-09-02
**Автор:** ROSTISLAV KUZNETSOV (через Hermes-агент)
**Статус:** ✅ Реализован

---

## Назначение

Проверить что в карточке проекта указано **юридическое лицо**, от имени которого ведётся проект с Заказчиком.

**Зачем:** Без юрлица невозможно корректное ведение корпоративного учёта — нельзя спрогнозировать, на какой расчётный счёт поступят средства по коммерческому контракту. Пользователи иногда торопятся или проявляют невнимательность и ведут проект без указания юрлица (например, «ООО "Проектная ПРАКТИКА"» или «ООО "АТР"»).

## Получение данных

| Параметр | Значение |
|----------|----------|
| View | `Project/ProjectParameter` (`entityName="Project"`) |
| Фильтр | без фильтра (нет ProjectId-фильтра в этом view) |
| Поле | `ProjectCompanyNames` (str) |
| Live-probe 2026-09-02 (504-595) | `ProjectCompanyNames = "Проектная ПРАКТИКА"` |

### Live-probe результаты по проектам

| Проект | ProjectCompanyNames | Verdict |
|--------|---------------------|---------|
| 504-595 | "Проектная ПРАКТИКА" | ✅ Норма |
| 503-152 | "ЦВ" | ✅ Норма |
| 501-724 | "АТР" | ✅ Норма |
| 502-651 | "Проектная ПРАКТИКА" | ✅ Норма |
| 504-314 | None | ❌ Критическое |
| 503-210 | None | ❌ Критическое |

## Интерпретация

| Условие | Result | Verdict |
|---------|--------|---------|
| Поле заполнено (непустая строка) | значение поля | `Норма` |
| Поле None или пустое | `"Нет"` | `Критическое` |

## Вывод

| Колонка | Значение |
|---------|----------|
| **Результат** | название юрлица (например `"Проектная ПРАКТИКА"`) или `"Нет"` |
| **Детализация** | пустая (нет вложенной таблицы) |
| **Таблица 3-го уровня** | нет |

## Скрипт

`scripts/project_indicators.py::check_jurlico(project, sid) -> IndicatorResult`

Использует `fetch_with_cache()` для кеширования ProjectParameter (TTL=5 мин, ключ — viewName+filters+project_id).

## Важные открытия (live-probe)

### ❗ `ProjectCompanyNames` есть только в `ProjectParameter`, НЕ в `MyProject`/`AllProject`

При разработке проверял 4 view для Project:
- `MyProject` — НЕТ поля юрлица
- `AllProject` — НЕТ поля юрлица
- `ProjectBudgetCompleteBusiness` — не содержит юрлицо
- **`ProjectParameter`** — ✅ содержит `ProjectCompanyNames`, `ContractorName`, `PresaleStateName` и другие параметры

### ⚠️ ProjectParameter не поддерживает server-side `?ProjectId=` фильтр

Возвращает **22 строки** (все проекты в портфеле), нужно фильтровать клиентом через `find_project_by_code()`:

```python
rows = fetch_with_cache(sid, "Project", "ProjectParameter",
                        filters={},  # НЕ фильтруем!
                        project_id=project_id, limit=200)
target = next((r for r in rows if str(r.get("code", "")).strip() == project["code"]), None)
```

### Другие полезные поля ProjectParameter (для будущих индикаторов)

| Поле | Назначение |
|------|-----------|
| `ProjectCompanyNames` | Юрлицо (этот индикатор) |
| `ContractorName` | Название контрагента/подрядчика |
| `DirectProjectCostsGrade` | Грейд прямых затрат проекта |
| `ProjectBudgetGrade` | Грейд бюджета проекта |
| `PresaleStateName` | Состояние пресейла ("Активен"/"Заморожен"/...) |
| `PresaleClosedDate`, `PresaleRegisterDate` | Даты пресейла |
| `controlsubject`, `administrator`, `leader`, `owner` | Управление проектом |
| `PortfolioIds`, `PortfolioName` | Портфель(и) |
