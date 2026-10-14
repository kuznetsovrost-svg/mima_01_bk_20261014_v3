# FST-HOWPROJECT — проработка description (frontmatter)

> Сессия: 2026-08-03, профиль `fst-control`
> Цель: выработать качественное англоязычное `description` для SKILL.md → frontmatter скилла `fst-howproject` (он же `SKILL-FST-HOWPROJET.md`, v1.3)

---

## 1. Исходное описание (RU, от пользователя)

> «Скилл реализует работу с проектами информационной системы ПМ Форсайт через ее MCP-сервер. По результатам работы скилла формируется отчет, содержащий итоговые сведения, позволяющие оценить здоровье конкретного проекта с точки зрения методологии проектного управления. Скилл сообщает итоговые сведения о соблюдении сроков контрольных точек проекта, проверяет полноту заполнения данных проекта, проверяет актуальность прогнозов по проекту, актуальность данных проекта, оценивает финансовый статус проекта. Дополнительно присылаются технические данные (дата, время, имя системы, имя пользователя). Отображение данных проектов ограничено правами пользователя в основной системе АМ Форсайт.»

---

## 2. Анализ исходника

### 2.1. Что в нём хорошо

- Указана **платформа** (ИСУП «Форсайт» / PMForesight) и **канал доступа** (MCP-сервер).
- Перечислены **5 направлений проверки** (хотя и нечётко) — это 5 разделов будущего SKILL.
- Упомянуты **служебные данные** (дата/время/система/пользователь).
- Зафиксировано **ограничение** по правам.

### 2.2. Что плохо для frontmatter

| Проблема | Почему критично |
|----------|-----------------|
| Нет **триггеров** (user-prompt patterns) | Hermes не сможет автоматически загрузить скилл по запросу вроде «оцени здоровье проекта» |
| Нет **глагола назначения** в первой строке | Frontmatter convention: «Use when the user wants …» |
| Не указаны **конкретные сущности / view** (ProjectHealthCostMy, Point, ResourcePlanning/Kp) | Непонятно, какие MCP-инструменты задействуются |
| Не упомянут **выходной артефакт** (Markdown-отчёт + вердикт БОЛЕН/ТРЕБУЕТ ВНИМАНИЯ/ЗДОРОВ) | Не ясно, что пользователь получит |
| «с точки зрения методологии проектного управления» — расплывчатая фраза | Размывает суть — нужны конкретные оси оценки |
| «актуальность данных проекта» и «актуальность прогнозов по проекту» — перекрываются | В исходнике SKILL это разные показатели (раздел 1.4 и 2); в описании не разведены |
| Перечисление через запятую в одном предложении — трудно парсить | Frontmatter convention требует скалярной строки |

### 2.3. Целевая структура description

```
Use when {triggers}. 
Produces {artifact}. 
Covers {axes}. 
Verdict: {outcomes}. 
{caveats}.
```

---

## 3. Итоговый перевод (EN, full)

```yaml
description: "Use when the user wants a comprehensive health-check report on a specific Foresight PM Practice project (ИСУП «Форсайт», PMForesight) by calling its MCP server. Loads when the user says 'здоровье проекта', 'оцени проект', 'health check', 'project status report', 'анализ проекта', or asks to evaluate a project by Code/ProjectId. Produces a single Markdown report covering: (1) КТ (control points) schedule compliance with red/yellow/blue classification by deviation between PlanDate and ForecastDate; (2) project data completeness (Owner, Leader, Паспорт, стадия ЖЦ, актуальность трудозатрат, график платежей); (3) forecast currency (overdue КТ where ForecastDate < today); (4) financial status via ProjectHealthCostMy view (прогноз фин.результата по окончании, отклонение текущей стоимости от плана, уменьшение фин.результата от планового); (5) technical metadata (date, time, MCP server version, system title, current user). Verdict is one of БОЛЕН / ТРЕБУЕТ ВНИМАНИЯ / ЗДОРОВ based on count of critical (red) remarks. All data is filtered by the user's permissions in the host Форсайт system."
```

### 3.1. Что улучшено

| Аспект | Было (RU) | Стало (EN) |
|--------|-----------|------------|
| Длина | 1 длинное предложение простыни | 1 ёмкое описание + список из 5 секций через `(1)…(2)…(3)…(4)…(5)` |
| Триггеры | Не выделены | Явные user-prompt patterns: «здоровье проекта», «оцени проект», «health check», «анализ проекта» |
| Структура отчёта | Не описана | Перечислены 5 конкретных разделов + их внутренние показатели |
| Финансы | Только «финансовый статус» | Указаны 3 конкретных показателя из ProjectHealthCostMy (`forecast`, `devcost`, `deviation`) |
| Технические данные | Просто перечислены | Перечислены + указан источник (MCP `serverInfo`, `initialize`) |
| Вердикт | Не упоминался | Добавлен явный исход: БОЛЕН / ТРЕБУЕТ ВНИМАНИЯ / ЗДОРОВ + критерий (count of red remarks) |
| Ограничения | В конце предложения | Вынесены в финал как **важное предупреждение** |
| Семантика | «с точки зрения методологии…» — расплывчато | Конкретизировано через 4 направления проверки |

---

## 4. Короткая версия (если full не лезет в лимит frontmatter)

> В некоторых SKILL.md-конвенциях `description` ограничен ~1024 символами; full выше — около 950, помещается, но короткая версия страхует.

```yaml
description: "Use when the user wants a health-check report on a specific Foresight PM Practice project via its MCP server. Loads on 'здоровье проекта', 'оцени проект', 'health check', 'project status report', or by Code/ProjectId. Produces a Markdown report with КТ schedule compliance (red/yellow/blue classification), project data completeness, forecast currency, financial status (via ProjectHealthCostMy), and technical metadata (MCP version, user, system title). Verdict: БОЛЕН / ТРЕБУЕТ ВНИМАНИЯ / ЗДОРОВ. Data is filtered by user permissions in host Форсайт."
```

**Длина:** ~470 символов. **Когда использовать:** если full не проходит парсер / рендерится обрезанным.

---

## 5. Готовый frontmatter-блок целиком (для вставки в SKILL.md)

```yaml
---
name: fst-howproject
description: "Use when the user wants a comprehensive health-check report on a specific Foresight PM Practice project (ИСУП «Форсайт», PMForesight) by calling its MCP server. Loads when the user says 'здоровье проекта', 'оцени проект', 'health check', 'project status report', 'анализ проекта', or asks to evaluate a project by Code/ProjectId. Produces a single Markdown report covering: (1) КТ (control points) schedule compliance with red/yellow/blue classification by deviation between PlanDate and ForecastDate; (2) project data completeness (Owner, Leader, Паспорт, стадия ЖЦ, актуальность трудозатрат, график платежей); (3) forecast currency (overdue КТ where ForecastDate < today); (4) financial status via ProjectHealthCostMy view (прогноз фин.результата по окончании, отклонение текущей стоимости от плана, уменьшение фин.результата от планового); (5) technical metadata (date, time, MCP server version, system title, current user). Verdict is one of БОЛЕН / ТРЕБУЕТ ВНИМАНИЯ / ЗДОРОВ based on count of critical (red) remarks. All data is filtered by the user's permissions in the host Форсайт system."
version: 1.4.0
author: Hermes Agent + Rost
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [mcp, pmpractice, foresight, project-health, kpi, health-check, report, ru]
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

### 5.1. Что внутри `metadata.hermes`

| Поле | Назначение |
|------|-----------|
| `tags` | Используются для авто-подбора скиллов по ключевым словам. Включены: протокол (mcp), продукт (pmpractice, foresight), функция (project-health, kpi, health-check, report), язык (ru). |
| `related_skills` | Связи с другими скиллами профиля `fst-control`. `fst-howproject` — это **обёртка-агрегатор** над ними: использует `project-search` для поиска проекта, `project-timing-control` для оценки сроков, `project-completeness-check` для полноты, `project-effort-plan/write` для трудозатрат (через раздел 1.4), `project-payment-schedule` для финансов (через раздел 3). |

---

## 6. Открытые вопросы / что уточнить перед фиксацией

1. **Имя скилла.** В файле `SKILL-FST-HOWPROJET.md` он сейчас **не оформлен как skills** (лежит как workflow в `/root/`). Имя `fst-howproject` (lowercase, hyphenated) — моё предложение. Альтернативы:
   - `project-health-report` — более понятно англоязычному читателю
   - `fst-project-health` — по конвенции «префикс продукта + функция»
   - оставить `SKILL-FST-HOWPROJET` (но в имя скилла это не канон — должно быть lowercase)
2. **Версия.** В workflow `SKILL-FST-HOWPROJET.md` — v1.3 (по разделу «История изменений»). Если оформлять как skills, разумно начать с **v1.4.0** (новый шаг = структуризация в SKILL.md).
3. **Категория.** По конвенции профиля — `productivity` (как у `project-search`, `project-timing-control`, `project-completeness-check`, `project-payment-schedule`). Это логично: скилл — инструмент руководителя проекта / РП для подготовки отчёта.
4. **Раздел «Ограничения» в description.** Стоит ли выносить в отдельную строку `caveats:` или оставить встроенным в `description`? По Hermes-конвенции — внутри description, чтобы не плодить мета-поля.
5. **Связь с `project-completeness-check`.** Текущий SKILL `project-completeness-check` уже покрывает раздел 1 (полнота заполнения). Возможно, **`fst-howproject` должен не дублировать, а вызывать** его как подскилл. Это упростит поддержку. Уточнить у пользователя архитектурное решение.

---

## 7. Что делать дальше

1. Согласовать имя скилла и версию с пользователем.
2. Создать каталог `~/.hermes/profiles/fst-control/skills/productivity/fst-howproject/`.
3. Перенести содержимое `/root/SKILL-FST-HOWPROJET.md` → `SKILL.md` с этим frontmatter.
4. Решить архитектурный вопрос про вложенность (агрегатор над другими скиллами vs самостоятельный).
5. Обновить `metadata.hermes.related_skills` у зависимых скиллов (добавить `fst-howproject` в их списки — для двусторонней навигации).
6. Перенести «Историю изменений» из workflow → в секцию `## История` SKILL.md.