# Теги для `metadata.hermes.tags` будущего скилла

> Сессия: 2026-08-03, профиль `fst-control`
> Назначение файла: зафиксировать **обоснованный** набор тегов для `metadata.hermes.tags` секции frontmatter скилла `fst-howproject` (рабочее название; альтернативы: `project-health-report`, `fst-project-health`).
>
> Это **четвёртый** файл в серии проработки скилла. Предыдущие:
> - `fst-howproject-decription-01.md` — RU→EN перевод description
> - `Проработка-description-03.md` — расширенная проработка с правками
> - `Проработка-description-04.md` — финализация description

---

## 1. Принцип отбора тегов

В Hermes `metadata.hermes.tags` используется для:

1. **Авто-подбора скилла** по ключевым словам в запросе пользователя (matching по подстроке).
2. **Категоризации** — группировка скиллов по домену, функции, формату.
3. **Фильтрации** в `skills_list` и curator-командах.

Значит, каждый тег должен:

| Критерий | Пояснение |
|----------|-----------|
| **Полезен для matching** | По нему пользователь мог бы задать вопрос |
| **Не дублирует `name:`** | Имя скилла уже в `name:`, не надо |
| **Не утекает в implementation detail** | `view`, `get_view`, `PlanDate` — это **как** скилл работает, а не **что** |
| **Совместим с конвенцией** | Префикс `[mcp, pmpractice, foresight, ru]` уже принят у `project-*` скиллов |

---

## 2. Полный рекомендованный набор (17 тегов)

```yaml
metadata:
  hermes:
    tags:
      # ─── Тип скилла ───
      - mcp                        # работает через MCP-сервер
      - report                     # генерирует отчёт

      # ─── Продукт / домен ───
      - pmpractice                 # продукт «ПМ Практика»
      - foresight                  # ИСУП «Форсайт»
      - pm                         # project management

      # ─── Функция / назначение ───
      - project-health             # оценка здоровья проекта
      - health-check               # англоязычный эквивалент
      - kpi                        # метрики проекта
      - diagnostic                 # диагностика состояния
      - project-analysis           # анализ проекта

      # ─── Формат вывода ───
      - html                       # HTML-отчёт файлом
      - markdown                   # MD в чате
      - dual-format                # два формата одновременно

      # ─── Язык / локаль ───
      - ru                         # русскоязычные триггеры и вывод
      - bilingual                  # работает на RU + EN триггерах

      # ─── Связи / категория ───
      - aggregator                 # агрегатор над другими скиллами
      - executive                  # для руководителя проекта / РП
```

---

## 3. Обоснование каждого тега

| Тег | Зачем | Конвенция |
|-----|-------|-----------|
| `mcp` | Используется для фильтрации «MCP-driven» скиллов | ✅ стандартный |
| `report` | Главная функция — отчёт | ✅ стандартный |
| `pmpractice` | Привязка к продукту | уже есть у `project-*` скиллов |
| `foresight` | Синоним продукта (ИСУП «Форсайт») | уже есть у `fst-pmpractice` |
| `pm` | Домен (project management) | общепринятый |
| `project-health` | Главная функция | новый (под этот скилл) |
| `health-check` | EN-эквивалент для англоязычных триггеров | синоним `project-health` |
| `kpi` | Скилл выдаёт метрики (forecast, devcost, …) | общепринятый |
| `diagnostic` | Скилл диагностирует проект | синоним `health-check` |
| `project-analysis` | Альтернативное название | синоним |
| `html` | HTML как формат отчёта | общепринятый |
| `markdown` | MD как формат отчёта | общепринятый |
| `dual-format` | Уникальная особенность этого скилла (оба формата) | новый |
| `ru` | Русскоязычный интерфейс/триггеры | ✅ стандартный |
| `bilingual` | RU + EN триггеры одновременно | общепринятый |
| `aggregator` | Архитектурный признак — собирает данные из других скиллов | новый (полезен для curator'а) |
| `executive` | Целевая аудитория — руководитель | общепринятый |

---

## 4. Что **не нужно** включать (и почему)

| Кандидат | Почему нет |
|----------|-----------|
| `fst-howproject` | Имя скилла и так в `name:`, дублировать в tags избыточно |
| `ProjectId`, `Code`, `Point`, `КТ` | Конкретные сущности — implementation detail, не user-facing |
| `view`, `get_view` | MCP-вызовы — не для авто-матчинга |
| `corp` | Избыточно, перекрывается `pmpractice` |
| `ProjectHealthCostMy` | Конкретный view — implementation detail |
| `PlanDate`, `ForecastDate` | Конкретные поля — implementation detail |
| `fst-pmpractice` | Имя зависимого скилла — для этого есть `related_skills` |
| `Kuznetsov`, `Rost` | Конкретный пользователь — нарушение общности |

---

## 5. Сравнение с тегами других `project-*` скиллов

| Скилл | Его теги (из `metadata.hermes.tags`) |
|-------|--------------------------------------|
| `project-search` | `[mcp, pmpractice, foresight, project, search, lookup, ru]` |
| `project-effort-plan` | `[mcp, pmpractice, foresight, effort, planning, forecast, resource-planning, ru]` |
| `project-effort-write` | `[mcp, pmpractice, foresight, effort, fact, time-entry, ru]` |
| `project-completeness-check` | `[mcp, pmpractice, foresight, project, completeness, health-check, verification, ru]` |
| `project-timing-control` | `[mcp, pmpractice, foresight, project, schedule, health, КТ, timing, ru]` |
| `project-payment-schedule` | `[mcp, pmpractice, foresight, project, payments, schedule, contract, ru]` |

**Закономерность:** общий префикс `[mcp, pmpractice, foresight, ru]` + 2-5 уникальных тегов под функцию.

---

## 6. Рекомендуемый **минимальный** набор (8 тегов)

Если хочется компактности, можно ужать до 8 — оставить только те, что **реально полезны** для matching:

```yaml
tags:
  - mcp                # тип
  - pmpractice         # продукт
  - foresight          # продукт (синоним)
  - ru                 # язык
  - project-health     # функция (главный тег)
  - report             # функция (что выдаёт)
  - aggregator         # архитектурный признак
  - executive          # целевая аудитория
```

**Плюсы:** короче, чище, нет синонимов.
**Минусы:** ниже recall при англоязычных формулировках («health check» без `health-check` тега уже не сматчится напрямую).

---

## 7. Рекомендуемый **полный** набор (17 тегов)

(см. секцию 2)

**Плюсы:** максимальный recall по разным формулировкам запросов; curator видит всё многообразие функций.
**Минусы:** длиннее; некоторые теги — синонимы.

---

## 8. Макет будущей секции `metadata.hermes.tags` (как будет во frontmatter)

### 8.1. Полный вариант (17 тегов)

```yaml
---
name: fst-howproject
description: "Use when the user wants a health-check report on a specific PMForesight project (ИСУП «Форсайт», PMForesight) via its MCP server. Loads on 'здоровье проекта', 'оцени проект', 'health check', 'project status report', 'анализ проекта', or by Code/ProjectId. Produces a dual-format report (Markdown inline + HTML file via MEDIA:) covering: (1) КТ schedule compliance (red/yellow by PlanDate–ForecastDate deviation); (2) project data completeness (Куратор, Руководитель, Паспорт, стадия ЖЦ, трудозатраты, платежи); (3) look-ahead КТ relevance (overdue КТ where ForecastDate < today); (4) financial status (forecast, прогноз фин.результата по окончании и его отклонение от планового, отклонение текущей стоимости от плана); (5) technical metadata (date, time, MCP version, user). Verdict: БОЛЕН / ТРЕБУЕТ ВНИМАНИЯ / ЗДОРОВ by critical-remark count. Visible data is filtered by the user's permissions in the host Форсайт system."
version: 1.4.0
author: Hermes Agent + Rost
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags:
      - mcp
      - report
      - pmpractice
      - foresight
      - pm
      - project-health
      - health-check
      - kpi
      - diagnostic
      - project-analysis
      - html
      - markdown
      - dual-format
      - ru
      - bilingual
      - aggregator
      - executive
    related_skills:
      - fst-pmpractice
      - project-search
      - project-timing-control
      - project-completeness-check
      - project-effort-plan
      - project-effort-write
      - project-payment-schedule
---
```

### 8.2. Минимальный вариант (8 тегов)

```yaml
metadata:
  hermes:
    tags:
      - mcp
      - pmpractice
      - foresight
      - ru
      - project-health
      - report
      - aggregator
      - executive
    related_skills:
      - fst-pmpractice
      - project-search
      - project-timing-control
      - project-completeness-check
      - project-effort-plan
      - project-effort-write
      - project-payment-schedule
```

### 8.3. Промежуточный вариант (10 тегов) — **баланс** ⭐

```yaml
metadata:
  hermes:
    tags:
      # общий префикс для всех project-* в fst-control
      - mcp
      - pmpractice
      - foresight
      - ru

      # уникальные для fst-howproject
      - project-health
      - health-check
      - report
      - html
      - markdown
      - aggregator
    related_skills:
      - fst-pmpractice
      - project-search
      - project-timing-control
      - project-completeness-check
      - project-effort-plan
      - project-effort-write
      - project-payment-schedule
```

---

## 9. Что выбрать — итоговая рекомендация

**Промежуточный вариант (10 тегов, секция 8.3).** Обоснование:

| Аргумент | За | Против |
|----------|----|----|
| Совместимость с другими `project-*` (общий префикс) | ✅ да | — |
| Уникальные теги для matching (`project-health`, `health-check`) | ✅ recall ↑ | — |
| Форматы (`html`, `markdown`) — важны для авто-подбора по «как отдать» | ✅ да | длиннее на 2 |
| Синонимы (`diagnostic`, `project-analysis`, `kpi`, `bilingual`, `pm`, `dual-format`, `executive`) | recall ↑ ещё | **избыточно** для matching |
| `report` — уже покрывается префиксом | — | оставить, т.к. главная функция |

Если пользователь хочет **максимум recall** — полный (17). Если **минимум** — 8. **Золотая середина — 10.**

Решение нужно принять до коммита `SKILL.md`. Запишу выбранный вариант в итоговый `SKILL.md`.

---

## 10. Открытые вопросы (нужно решить перед коммитом)

1. **Сколько тегов выбираем:** 8 / 10 / 17?
2. **Имя скилла:** `fst-howproject` / `project-health-report` / `fst-project-health`?
3. **`related_skills`:** добавить двустороннюю ссылку в каждый из 7 зависимых скиллов?
4. **Дополнительные мета-поля:** нужен ли `metadata.hermes.triggers` (отдельный список триггеров для более точного matching, нежели из `description`)?

---

## 11. Контрольный чек-лист (готовность к коммиту)

- [ ] Выбран размер набора тегов (8 / 10 / 17)
- [ ] Согласовано имя скилла
- [ ] Подготовлен каталог `~/.hermes/profiles/fst-control/skills/productivity/<name>/`
- [ ] `SKILL.md` создан с финальным frontmatter
- [ ] `related_skills` обновлён у зависимых скиллов
- [ ] Проверено, что `skills_list` подхватывает новый скилл
- [ ] Проверено, что триггеры из `description` действительно активируют скилл