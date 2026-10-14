# Рубрикатор скиллов семейства fst-project-health

**Дата:** 2026-09-24

---

## Актуальные скиллы (5 шт)

### `fst-project-health` (v1.0.19)

| Поле | Значение |
|---|---|
| **Назначение** | Главный скилл — генерация «живого» HTML-отчёта по MCP в реальном времени |
| **Что делает** | MCP → MD → HTML (без «Слепок от:») |
| **Когда загружать** | Пользователь просит «отчёт по проекту», «здоровье проекта», «HTML по 504-595» |
| **Зависимости** | PMForesight MCP (live), requests, python-dotenv |
| **Главные скрипты** | `run_all.py`, `build_html_report.py`, `rebuild_report.py` |
| **Время работы** | 19–52 сек (зависит от MCP) |
| **PLAYBOOK** | `playbook.md` (в скилле) или `docs/fst-project-health-playbooks/fst-project-health.PLAYBOOK.md` |

---

### `fst-project-health-word` (v1.0.20)

| Поле | Значение |
|---|---|
| **Назначение** | Генерация DOCX-отчёта (Форма 1) из MD-файла |
| **Что делает** | MD (любой) → DOCX с подсветкой строк по severity |
| **Когда загружать** | Нужен DOCX-отчёт (вместо или в дополнение к HTML) |
| **Зависимости** | python-docx>=1.0.0, MD (не нужен MCP для сборки) |
| **Главные скрипты** | `build_word_report.py`, `build_word_from_snapshot.sh` |
| **Время работы** | ~2 сек (без MCP) |
| **PLAYBOOK** | `playbook.md` (в скилле) или `docs/fst-project-health-playbooks/fst-project-health-word.PLAYBOOK.md` |

---

### `fst-project-health-snap-md` (v1.0.19)

| Поле | Значение |
|---|---|
| **Назначение** | Генератор MD-слепков состояния проектов в карточки MCP |
| **Что делает** | MCP (live) → MD → загрузка в карточку проекта (раздел «Документы ИИ») |
| **Когда загружать** | Нужно собрать слепки (периодически, по cron, по списку проектов) |
| **Зависимости** | PMForesight MCP (live + write), всё от `fst-project-health` |
| **Главные скрипты** | `run_snap_md.py`, `logging_utils.py`, `rotate_logs.py` |
| **Время работы** | 19–52 сек/проект |
| **PLAYBOOK** | `playbook.md` (в скилле) или `docs/fst-project-health-playbooks/fst-project-health-snap-md.PLAYBOOK.md` |

---

### `fst-project-health-from-md-snapshot` (v1.0.19)

| Поле | Значение |
|---|---|
| **Назначение** | Извлечение MD-слепков из MCP + построение HTML-отчёта по ним |
| **Что делает** | MCP (read .MD) → локальный кэш → HTML (с «Слепок от:») |
| **Когда загружать** | Нужен отчёт по ранее сохранённому слепку (тренд, история, offline) |
| **Зависимости** | PMForesight MCP (read), requests |
| **Главные скрипты** | `fetch_snapshot.py` (5 режимов выбора), `build_html.py`, `run.py` |
| **Время работы** | 1–2 сек (fetch) + 1 сек (build) |
| **PLAYBOOK** | `playbook.md` (в скилле) или `docs/fst-project-health-playbooks/fst-project-health-from-md-snapshot.PLAYBOOK.md` |

---

### `fst-project-health-tests` (v1.0.19)

| Поле | Значение |
|---|---|
| **Назначение** | Тестовый скилл — 50 тестов в 6 группах |
| **Что делает** | Регрессия, MCP, snap-md, from-md-snapshot, cross-skill, инварианты |
| **Когда загружать** | После изменений в любом скилле семейства; в CI/cron |
| **Зависимости** | Все остальные скиллы семейства |
| **Главные скрипты** | `run_all_tests.py` (НЕ pytest), `tests/test_*.py` |
| **Время работы** | ~5 мин (все группы) |
| **PLAYBOOK** | `playbook.md` (в скилле) или `docs/fst-project-health-playbooks/fst-project-health-tests.PLAYBOOK.md` |

---

## Архитектурный скилл (1 шт)

### `fst-project-health-family` (v1.0.21)

| Поле | Значение |
|---|---|
| **Назначение** | Описание архитектуры семейства и правил синхронизации |
| **Что делает** | Содержит карту скиллов, правила совместимости версий, контракт MD |
| **Когда загружать** | Меняешь структуру MD и нужно проверить синхронизацию всех рендереров |
| **Зависимости** | Нет (это мета-скилл) |
| **PLAYBOOK** | Нет (сам является метадокументом) |

---

## DEPRECATED скиллы (2 шт)

### `fst-project-health-from-json.deprecated/`

| Поле | Значение |
|---|---|
| **Статус** | DEPRECATED 2026-09-24 |
| **Причина** | Использовал JSON вместо MD; JSON нечитаем для человека |
| **Замена** | `fst-project-health-from-md-snapshot` |
| **Архив** | `/tmp/fst-project-health-from-json.deprecated.2026-09-24.tar.gz` (46 KB) |
| **Действие** | Не удалять — оставлен для истории и совместимости со старыми данными |

### `fst-project-health-snapshot.deprecated/`

| Поле | Значение |
|---|---|
| **Статус** | DEPRECATED 2026-09-24 |
| **Причина** | Использовал JSON вместо MD; никем не вызывается с 21.09 |
| **Замена** | `fst-project-health-snap-md` |
| **Архив** | `/tmp/fst-project-health-snapshot.deprecated.2026-09-24.tar.gz` (32 KB) |
| **Действие** | Не удалять — оставлен для истории |

---

## Сводная таблица

| Скилл | Версия | LOC | Скриптов | Статус |
|---|---|---|---|---|
| `fst-project-health` | 1.0.19 | ~9 200 | 40 | ✅ актуальный |
| `fst-project-health-word` | 1.0.20 | ~1 200 | 2 | ✅ актуальный |
| `fst-project-health-snap-md` | 1.0.19 | ~1 030 | 3 | ✅ актуальный |
| `fst-project-health-from-md-snapshot` | 1.0.19 | ~1 312 | 5 | ✅ актуальный |
| `fst-project-health-tests` | 1.0.19 | ~1 700 | 10 | ✅ актуальный |
| `fst-project-health-family` | 1.0.21 | — | — | 📐 архитектурный |
| `fst-project-health-from-json.deprecated/` | 1.0.0 | — | — | 🗑 DEPRECATED |
| `fst-project-health-snapshot.deprecated/` | 1.0.19 | — | — | 🗑 DEPRECATED |
| **ИТОГО актуальных** | | **~14 500** | **60** | |

---

## Где лежит

```
~/.hermes/profiles/fst-control/skills/productivity/
├── fst-project-health/                     ← live HTML
├── fst-project-health-word/                ← DOCX
├── fst-project-health-snap-md/             ← генерация слепков
├── fst-project-health-from-md-snapshot/    ← извлечение слепков + HTML
├── fst-project-health-tests/               ← тесты
├── fst-project-health-family/              ← архитектура
├── fst-project-health-from-json.deprecated/
└── fst-project-health-snapshot.deprecated/
```

PLAYBOOK лежат в:
```
~/.hermes/profiles/fst-control/docs/fst-project-health-playbooks/
```

---

## Какие скиллы загружать в каких ситуациях

| Ситуация | Скилл |
|---|---|
| «Отчёт по 504-595 в реальном времени» | `fst-project-health` |
| «Тот же отчёт в WORD» | `fst-project-health-word` |
| «Собрать слепки по списку проектов» | `fst-project-health-snap-md` |
| «Построй отчёт по слепку от вчера» | `fst-project-health-from-md-snapshot` |
| «Прогони тесты» | `fst-project-health-tests` |
| «Как связаны все эти скиллы?» | `fst-project-health-family` |

---

## Соглашения об именовании

- **Префикс** `fst-project-health-*` для всех скиллов семейства.
- Суффиксы:
  - без суффикса → головной (live)
  - `-word` → DOCX
  - `-snap-md` → генератор MD-слепков
  - `-from-md-snapshot` → извлечение MD-слепков
  - `-tests` → тесты
  - `-family` → архитектура
  - `.deprecated/` → отключён
