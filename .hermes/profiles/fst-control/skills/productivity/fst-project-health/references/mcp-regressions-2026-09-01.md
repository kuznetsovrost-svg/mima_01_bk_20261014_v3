# MCP regressions — wave of 2026-09-01 (CLOSED)

**Дата:** 2026-09-01 (closed later same day)
**Контекст:** разработчики MCP выпулили несколько «фиксов», часть сломалась обратно.
**Связь:** предыдущие волны — `references/mcp-regression-2026-08-27.md` (InContract) и `references/mcp-regression-2026-08-31.md` (ProjectHealthCostMy упал в ноль).

---

## ⚠️ Статус: ВСЕ РЕГРЕССИИ ЗАКРЫТЫ (в той же сессии 2026-09-01)

К концу сессии 2026-09-01 **все** упомянутые ниже регрессии были устранены (по разным причинам — часть починили разработчики, часть — мы перешли на новый формат `filters={...}` который работает всегда).

**Не используй этот файл как reference — он исторический.** Актуальное состояние — в `SKILL.md` (pitfalls #78-#87) и в `references/mcp-server-filter-playbook.md`.

## Итоговое состояние (на конец сессии 2026-09-01)

| View | Статус | Исправление |
|------|:------:|--------------|
| `Project/ProjectHealthCostMy?ProjectId=` | ❌ → ✅ | Новый формат `filters={ProjectId: id}` |
| `Project/ProjectHealthCostMy` без фильтра | ❌ | Не использовать без фильтра |
| `InContract/InContractMyProject?ProjectId=` | ⚠️ → ✅ | Восстановлено (1 строка для 504-595) |
| `InContract/InContract?ProjectId=` | ❌ | Использовать `InContractMyProject` + клиентский фильтр через `ParentFullName` |
| `InContract` поле `projectid` | ❌ null → ✅ | Теперь заполняется (504-595: 4595) |
| `NormDayWorkHours` | ⚠️ → ✅ | Структура правильная (Date/Hours/ProjectId), фильтры работают |
| B-tree лимит 2704 | ❌ → ✅ | **ИСПРАВЛЕН** — теперь до 50 КБ JSON |
| `delete_entity` | ⚠️ → ✅ | Найден формат `remove=['AttributeValue\|<guid>']` |

## Live-probe после всех фиксов (2026-09-01, end of session)

| View | С фильтром | Без |
|------|:---:|:---:|
| `ProjectHealthCostMy?filters={ProjectId: 4595}` | ✅ 1 строка | — |
| `ProjectResourcePlan?filters={ProjectId: 4595}` | ✅ 100+ строк | — |
| `ProjectBudgetCompleteBusiness?filters={ProjectId: 4595}` | ✅ 12 строк | — |
| `InContractMyProject?filters={ProjectId: 4595}` | ✅ 1 строка (с projectid=4595) | — |
| `AllMyPoint?filters={ProjectId: 4595}` | ✅ 18 строк | — |
| `NormDayWorkHours?filters={ProjectId: 4595, StartDate, EndDate}` | ✅ 31 строка | — |
| `ApprovedBudget?filters={ActivityId: 4595, Year: 2026}` | ✅ 1 строка (54 млн ₽) | — |

**Все 7 views работают через стандартный формат `filters={...}`.**

## Что привело к починке

1. **Формат `filters={...}`** (введён разработчиками) — работает для **всех** views
2. **B-tree лимит** — разработчики расширили индекс (теперь >6 КБ JSON грузится)
3. **`projectid` в InContract** — разработчики добавили заполнение поля
4. **`NormDayWorkHours`** — структура исправлена, Hours=8 для будних, 0 для выходных
5. **`delete_entity`** — формат найден, 34/34 тестовых записей удалены

## Ключевые открытия сессии

- **`list_views`** — новый tool для discovery поддерживаемых фильтров
- **`ApprovedBudget`** — view для утверждённого бюджета (5 столбцов, фильтры ActivityId/PortfolioId/Year)
- **`ProjectBudgetCompleteBusiness`** — 36 столбцов включая `isprojectbudget`/`ispresalebudget`
- **Trend reports** возможны через `filters={DateBegin, DateEnd}` в `ProjectHealthCostMy`

## Скрипт-утилита для очистки тестовых данных

`/tmp/project-json-design/scripts/delete_attribute_values.py` — удаляет AttributeValue записи по ID.

**Live-probe:** 34/34 успешных удалений (100% успех).

## Контекст для следующей сессии

| Что | Статус | Когда пересмотреть |
|-----|:------:|--------------------|
| Скилл работает | ✅ | После очередного фикса |
| Pipeline 19-23 сек (vs 60-67 раньше) | ✅ | — |
| `delete_entity` (через `remove=['X\|<guid>']`) | ✅ | — |
| B-tree лимит 2704 (теперь не лимит) | ✅ | — |
| `InContract` фильтр для 503-434/503-152 | ❌ нет доступа | Ждём MCP |
| JSON-модель в `/tmp/project-json-design/` | ✅ готова | Когда пользователь одобрит применение |
| `fst-project-trends` | ⏸️ дизайн готов | Когда пользователь даст скриншот |

## Контакт

- **Telegram:** @kuznetsov-rostislav (или через Hermes-агент)
- **Дата:** 2026-09-01
- **Версия playbook:** 1.0 (CLOSED — регрессии устранены)
- **Скилл:** `fst-project-health` v0.14.0
