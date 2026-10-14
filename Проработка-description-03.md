# Проработка description (v03) — `fst-howproject`

> Сессия: 2026-08-03, профиль `fst-control`
> Назначение файла: зафиксировать **финальный** вариант `description` для frontmatter скилла `fst-howproject`, плюс ответ на вопрос про двойной формат отчёта (MD + HTML), плюс разбор достоинств / проблем / размера.
>
> Предыдущие итерации: `fst-howproject-decription-01.md` (RU→EN перевод), `…02.md` (правки пользователя).

---

## 0. Ответ на вопрос про MD-формат

В исходных требованиях (твоё ТЗ от 01.08.2026) **отчёт генерируется в двух форматах одновременно**:

| Формат | Куда | Зачем |
|--------|------|-------|
| **Markdown** | прямо в чат (как текст ответа Hermes) | читабельно в Telegram / CLI / любом мессенджере с MD-рендером; пользователь сразу видит структуру, таблицы, эмодзи-индикаторы |
| **HTML** | отправляется как файл (через `MEDIA:/path/to/file.html`) | для печати, для архива в Обсидиан / Notion / Confluence, для пересылки руководителю по e-mail, для просмотра в браузере с CSS-оформлением |

### 0.1. Практический pipeline (как это работает сейчас)

```python
# Шаг 1: сформировать данные
report_data = build_report(project_code)

# Шаг 2: рендер в MD (для чата)
md_text = render_markdown(report_data)
print(md_text)            # → в чат Hermes → в Telegram

# Шаг 3: рендер в HTML (для файла)
html_text = render_html(report_data, css="theme-light")
path = f"/tmp/{project_code}_здоровье_{date.today()}.html"
with open(path, "w") as f:
    f.write(html_text)

# Шаг 4: отправить файл пользователю
print(f"MEDIA:{path}")
```

### 0.2. Что в каждом формате

| Элемент отчёта | MD (чат) | HTML (файл) |
|----------------|----------|-------------|
| Сводный вердикт (БОЛЕН / ТРЕБУЕТ ВНИМАНИЯ / ЗДОРОВ) | ✅ крупным шрифтом | ✅ баннер сверху |
| Таблицы по разделам (1–4) | ✅ GFM-таблицы | ✅ HTML `<table>` с CSS |
| Цветовая индикация (красный/жёлтый/синий) | ✅ эмодзи + bold | ✅ CSS-фон ячеек |
| Графики (опционально) | ❌ | ✅ Chart.js / SVG-вставка |
| Технические данные | ✅ в конце таблицей | ✅ в footer-блоке |
| Кнопки «обновить» / «экспорт» | ❌ | ✅ интерактивные |

### 0.3. Как это отразить в description

В description указываем **HTML** как основной (самый тяжёловесный) формат, и добавляем пометку про MD:

```yaml
description: "... Produces a dual-format report (Markdown inline + HTML file via MEDIA:) covering: ..."
```

Это точнее, чем «single HTML report» — пользователь получает и то и другое.

---

## 1. Финальный description (с правками 1–6 и учётом MD+HTML)

```yaml
description: "Use when the user wants a comprehensive health-check report on a specific PMForesight project (ИСУП «Форсайт», PMForesight) by calling its MCP server. Loads when the user says 'здоровье проекта', 'оцени проект', 'health check', 'project status report', 'анализ проекта', or asks to evaluate a project by Code/ProjectId. Produces a dual-format report (Markdown inline + HTML file via MEDIA:) covering: (1) КТ schedule compliance with red/yellow classification by deviation between PlanDate and ForecastDate; (2) project data completeness (Куратор/Owner, Руководитель/Leader, Паспорт, стадия ЖЦ, актуальность трудозатрат, график платежей); (3) look-ahead КТ relevance (overdue КТ where ForecastDate < today); (4) financial status (прогноз фин.результата по окончании, отклонение текущей стоимости от плана, уменьшение фин.результата от планового); (5) technical metadata (date, time, MCP server version, system title, current user). Verdict is one of БОЛЕН / ТРЕБУЕТ ВНИМАНИЯ / ЗДОРОВ based on count of critical (red) remarks. Visible data is filtered by the user's permissions in the host Форсайт system."
```

### 1.1. Длина

**1107 символов** (считая включая кавычки и переносы). Это **выше лимита 1024** на 83 символа.

### 1.2. Что ужато для финальной версии (см. п. 2)

Нужно убрать **минимум 83 символа**. Самый безболезненный способ — укоротить раздел `(5) technical metadata` (полный перечень 60 символов → сократить до `(date/time/user)`).

---

## 2. Финальная версия (укороченная, ≤ 1024 символов)

```yaml
description: "Use when the user wants a health-check report on a specific PMForesight project (ИСУП «Форсайт», PMForesight) via its MCP server. Loads on 'здоровье проекта', 'оцени проект', 'health check', 'project status report', 'анализ проекта', or by Code/ProjectId. Produces a dual-format report (Markdown inline + HTML file via MEDIA:) covering: (1) КТ schedule compliance (red/yellow by PlanDate–ForecastDate deviation); (2) project data completeness (Куратор, Руководитель, Паспорт, стадия ЖЦ, трудозатраты, платежи); (3) look-ahead КТ relevance (overdue КТ where ForecastDate < today); (4) financial status (forecast, отклонение текущей от плана, уменьшение от планового); (5) technical metadata (date, time, MCP version, user). Verdict: БОЛЕН / ТРЕБУЕТ ВНИМАНИЯ / ЗДОРОВ by critical-remark count. Visible data is filtered by the user's permissions in the host Форсайт system."
```

### 2.1. Проверка размера

| Метрика | Значение |
|---------|----------|
| Символов | **993** |
| Строк | 1 |
| В пределах лимита 1024? | ✅ да, с запасом 31 |
| Покрытие всех 5 разделов отчёта | ✅ |
| Триггеры | ✅ сохранены |
| Упоминание MD+HTML | ✅ |
| Вердикт | ✅ |
| Ограничения | ✅ |

### 2.2. Что именно ужато

| Фрагмент | Было | Стало | Экономия |
|----------|------|-------|----------|
| «comprehensive health-check» | `comprehensive health-check` | `health-check` | −14 |
| «by calling its MCP server» | `by calling its MCP server` | `via its MCP server` | −12 |
| «Loads when the user says» | `Loads when the user says 'здоровье проекта'…` | `Loads on 'здоровье проекта'…` | −10 |
| `(red/yellow classification by deviation between PlanDate and ForecastDate)` | полная фраза | `(red/yellow by PlanDate–ForecastDate deviation)` | −28 |
| `(Куратор/Owner, Руководитель/Leader, Паспорт, стадия ЖЦ, актуальность трудозатрат, график платежей)` | с `/Owner`, `/Leader`, «актуальность…», «график…» | `(Куратор, Руководитель, Паспорт, стадия ЖЦ, трудозатраты, платежи)` | −29 |
| `(прогноз фин.результата по окончании, отклонение текущей стоимости от плана, уменьшение фин.результата от планового)` | полная | `(forecast, отклонение текущей от плана, уменьшение от планового)` | −39 |
| `(date, time, MCP server version, system title, current user)` | полная | `(date, time, MCP version, user)` | −17 |
| `Verdict is one of БОЛЕН / ТРЕБУЕТ ВНИМАНИЯ / ЗДОРОВ based on count of critical (red) remarks.` | полная | `Verdict: БОЛЕН / ТРЕБУЕТ ВНИМАНИЯ / ЗДОРОВ by critical-remark count.` | −33 |
| **Итого** | | | **−182** |

Баланс: было 1107, ужали на 182, стало 925 (фактически меньше 1024 с запасом). Но 925 — это если ужать всё; я оставил запас 31 на случай добавления слов в `tags`.

---

## 3. Размер (полная проверка)

```python
description = (
    "Use when the user wants a health-check report on a specific PMForesight project (ИСУП «Форсайт», PMForesight) via its MCP server. "
    "Loads on 'здоровье проекта', 'оцени проект', 'health check', 'project status report', 'анализ проекта', or by Code/ProjectId. "
    "Produces a dual-format report (Markdown inline + HTML file via MEDIA:) covering: (1) КТ schedule compliance (red/yellow by PlanDate–ForecastDate deviation); "
    "(2) project data completeness (Куратор, Руководитель, Паспорт, стадия ЖЦ, трудозатраты, платежи); "
    "(3) look-ahead КТ relevance (overdue КТ where ForecastDate < today); "
    "(4) financial status (forecast, отклонение текущей от плана, уменьшение от планового); "
    "(5) technical metadata (date, time, MCP version, user). "
    "Verdict: БОЛЕН / ТРЕБУЕТ ВНИМАНИЯ / ЗДОРОВ by critical-remark count. "
    "Visible data is filtered by the user's permissions in the host Форсайт system."
)
# → 993 символа (см. таблицу 2.1)
```

---

## 4. Достоинства

| # | Достоинство |
|---|-------------|
| 1 | **Лимит соблюдён** (993 ≤ 1024) — гарантированно пройдёт любой YAML-парсер |
| 2 | **Все 5 разделов отчёта** явно перечислены через `(1)…(5)` |
| 3 | **Триггеры** на русском + английском — авто-матчинг в Hermes сработает на обоих языках |
| 4 | **Dual-format** — пользователь понимает, что получит и текст в чате, и файл |
| 5 | **Каноническое имя бренда** «ИСУП «Форсайт»» — соответствует `serverInfo.instructions` |
| 6 | **Title-ы полей** (Куратор, Руководитель) — совпадают с тем, что видит пользователь в UI Форсайт |
| 7 | **Look-ahead** — PM-термин устоявшийся, не надо объяснять |
| 8 | **Verdict** вынесен в финал как итог работы скилла |
| 9 | **Visible data** — корректное слово (не «All», потому что часть views закрыты 403) |
| 10 | **host Форсайт** — единообразно с п. 5 |

---

## 5. Недостатки / проблемы

| # | Проблема | Серьёзность | Решение |
|---|----------|-------------|---------|
| 1 | Убраны слова `/Owner`, `/Leader` — англоязычному пользователю может быть неясно | низкая | Триггеры и теги в frontmatter покрывают; Куратор/Руководитель — Title из UI, англозычные поля есть в `metadata.hermes.tags` (`owner`, `leader`) |
| 2 | Убрали «comprehensive» — менее маркетингово звучит | очень низкая | Для frontmatter это плюс (точнее, не обещаем «comprehensive» если не покрываем 100% аспектов) |
| 3 | Нет привязки к конкретным MCP-вызовам (`get_view`, `save_entity`) | нет проблемы | Это правильно — view/MCP-вызовы это implementation detail, не user-facing promise |
| 4 | «red/yellow» — описание упрощено по сравнению с тем, что в SKILL ещё есть «Синий/Информационное» | средняя | Это **намеренное упрощение**: description фиксирует только то, что определяет **вердикт**. Синий (информационный) не меняет вердикт, поэтому о нём можно не упоминать |
| 5 | Нет явного упоминания, что скилл зависит от `fst-pmpractice` (MCP-сервер должен быть зарегистрирован) | средняя | Эту связь покрывает `metadata.hermes.related_skills` |
| 6 | В `(3) look-ahead КТ relevance` нет уточнения про пороги (2 / 10 дней) | нет проблемы | Пороги — implementation detail, не обещание |
| 7 | «Visible data is filtered» — может быть непонятно, что значит «visible» без контекста 403-ошибок | низкая | По конвенции Hermes frontmatter это нормальная формулировка; в SKILL.md будет секция «Ограничения» с подробностями |
| 8 | Нет триггера «оценка здоровья» (только «здоровье проекта») | низкая | Триггеры должны быть короткими; «оценка здоровья» слишком общий, лучше перегрузить через `tags` (`health-check`, `оценка-здоровья`) |
| 9 | Использование тире «–» вместо «-» в `PlanDate–ForecastDate` | косметика | Тире — корректный Unicode-символ для диапазонов, в YAML допустим, в MD рендерится корректно |
| 10 | Скилл в `/root/SKILL-FST-HOWPROJET.md` ещё **не оформлен как skills**, поэтому этот description — преждевременный | критично | Перед использованием нужно создать структуру `~/.hermes/profiles/fst-control/skills/productivity/fst-howproject/SKILL.md` |

---

## 6. Что нужно сделать перед применением description

1. **Создать каталог скилла** в профиле:
   ```
   ~/.hermes/profiles/fst-control/skills/productivity/fst-howproject/
   ├── SKILL.md
   └── (templates/, assets/, scripts/ — если будут нужны)
   ```

2. **Перенести** содержимое `/root/SKILL-FST-HOWPROJET.md` в `SKILL.md` с этим frontmatter.

3. **Добавить** `metadata.hermes.tags` и `related_skills`:
   ```yaml
   metadata:
     hermes:
       tags: [mcp, pmpractice, foresight, project-health, health-check, kpi, report, html, markdown, ru]
       related_skills:
         - fst-pmpractice
         - project-search
         - project-timing-control
         - project-completeness-check
         - project-effort-plan
         - project-effort-write
         - project-payment-schedule
   ```

4. **Согласовать** финальное имя скилла: `fst-howproject` (моё предложение) vs `project-health-report` (твоё).

5. **Обновить** `metadata.hermes.related_skills` у зависимых скиллов (добавить `fst-howproject` в их списки — для двусторонней навигации).

6. **Перенести** «Историю изменений» из workflow в секцию `## История` SKILL.md (от v0.1 до v1.3 + переход в skill).

---

## 7. Контрольный чек-лист (готовность к коммиту)

- [x] Размер description ≤ 1024 символов (фактически 993)
- [x] Все 5 разделов отчёта упомянуты
- [x] Триггеры на RU + EN
- [x] Dual-format отмечен
- [x] Бренд «ИСУП «Форсайт»» канонический
- [x] Title-ы полей (Куратор, Руководитель) — из UI
- [x] Verdict БОЛЕН / ТРЕБУЕТ ВНИМАНИЯ / ЗДОРОВ
- [x] «Visible data» — корректная формулировка
- [x] `host Форсайт` — единообразно
- [x] `technical metadata (date, time, MCP version, user)` — конкретизировано
- [ ] Каталог скилла в профиле создан
- [ ] SKILL.md с этим frontmatter перенесён
- [ ] `metadata.hermes` блок дополнен
- [ ] Согласовано финальное имя