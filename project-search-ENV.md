# Структура скилла project-search

> **Скилл:** `project-search` v1.0.0
> **Назначение:** поиск ProjectId по имени, коду или фрагменту в Форсайт ПМ Практике
> **Путь:** `~/.hermes/profiles/fst-control/skills/productivity/project-search/`
> **Дата обзора:** 2026-08-03

---

## 1. Дерево каталогов

```
project-search/
├── references/      # ← отсутствует
├── templates/      # ← отсутствует
├── scripts/      # ← отсутствует
├── assets/      # ← отсутствует
├── examples/      # ← отсутствует
└── SKILL.md       # ← единственный файл
```

> **Файлов:** 1
> **Подкаталогов:** 0
> **Общий размер:** 7774 байт

---

## 2. Детальный листинг файлов

| # | Путь относительно корня скилла | Размер | Изменён |
|---|-------------------------------|-------:|---------|
| 1 | `./SKILL.md` | 7774 байт | 2026-07-29 13:13 |

---

## 3. Назначение каждого файла

### `SKILL.md` — основной файл скилла

**Размер:** 7774 байт, ~172 строк

**Назначение:** единственный файл скилла. Содержит полную спецификацию: триггеры, алгоритм, edge-cases, формат отчёта, verification checklist.

**Frontmatter (метаданные):**

| Поле | Значение |
|------|----------|
| `name` | `project-search` |
| `description` | `Use when the user wants to find a Foresight PM Practice project by name (or part of it), asks 'найди проект', 'какой ProjectId у проекта', 'поиск проекта по имени', 'project search', 'look up project'…` |
| `version` | `1.0.0` |
| `author` | `Hermes Agent + Rost` |
| `license` | `MIT` |
| `platforms` | `[linux, macos, windows]` |
| `metadata` | `` |
| `hermes` | `` |
| `tags` | `[mcp, pmpractice, foresight, project, search, lookup, ru]` |
| `related_skills` | `[fst-pmpractice, project-timing-control, project-payment-schedule]` |

**Структура файла (по разделам markdown):**

- **# Project Search (project-search)**
  - ## Overview
  - ## When to Use
  - ## ⚠️ Архитектурная особенность
  - ## Алгоритм
  - ## Уточняющий вопрос пользователю (шаг 3c)
  - ## Возврат результата
  - ## Edge cases
  - ## Пример вызова
  - ## Связь с другими скиллами
  - ## Verification Checklist

---

## 4. Подкаталоги

**Подкаталоги отсутствуют.** Скилл компактный — вся логика в одном `SKILL.md`.

Это нормально для скиллов, которые описывают простой алгоритм (поиск + уточнение) без дополнительных шаблонов, скриптов или справочных материалов.

---

## 5. Что внутри SKILL.md (краткий пересказ)

**Архитектурный контекст:**

```
Project
  └─ Activity  ← реальный контейнер всех дочерних сущностей
       ├─ Point
       ├─ Payments
       ├─ Risk
       └─ DocumentFile
```

У большинства сущностей **нет прямого FK на Project** — только на Activity. Поэтому после нахождения ProjectId может понадобиться шаг «получить список ActivityId» для дальнейшей работы.

**Алгоритм (5 шагов):**

1. `get_view(Project, MyProject)` → fallback `AllProject`
2. Поиск по подстроке в `Name` (case-insensitive)
3. Ветвление: 0 совпадений / 1 совпадение / >1 совпадений (уточнение)
4. Обработка ответа пользователя: Code / число / подстрока
5. Возврат `ProjectId` + `Code` + `Name`

**Что возвращает:** ProjectId, Code, Name. **Ничего больше** — после нахождения ProjectId работа передаётся другим скиллам (`project-timing-control`, `project-payment-schedule` и т.д.).

**Связанные скиллы (из `metadata.hermes.related_skills`):**

- `fst-pmpractice` — базовый (формат `get_view`, формат дат)
- `project-timing-control` — анализ сроков проекта (получает ProjectId отсюда)
- `project-payment-schedule` — график платежей проекта

---

## 6. Итог

| Параметр | Значение |
|----------|----------|
| Категория | `productivity` |
| Версия | `1.0.0` |
| Автор | Hermes Agent + Rost |
| Лицензия | MIT |
| Платформы | linux, macos, windows |
| Файлов | 1 |
| Подкаталогов | 0 |
| Общий размер | 7774 байт |
