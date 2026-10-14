# Рубрикатор PLAYBOOK семейства fst-project-health

**Дата:** 2026-09-24

Все PLAYBOOK лежат в `~/.hermes/profiles/fst-control/docs/fst-project-health-playbooks/`.

---

## Список документов

| № | Документ | Для чего | Что содержит (кратко) | Где лежит |
|---|---|---|---|---|
| 0 | **SKILLS-INDEX.md** | Полный рубрикатор по **всем скиллам** семейства (актуальные + DEPRECATED + архитектурные) | 5 актуальных + 1 архитектурный + 2 DEPRECATED, сводная таблица, маппинг «ситуация → скилл» | `docs/fst-project-health-playbooks/` |
| 1 | **fst-project-health.PLAYBOOK.md** | Подробный playbook основного скилла live-сборки | API, 40 скриптов с LOC/размером, методы для переиспользования, сценарии | `docs/fst-project-health-playbooks/` |
| 2 | **fst-project-health-word.PLAYBOOK.md** | Подробный playbook генератора DOCX | API, 2 скрипта, методы, **генерация WORD для live и для снапшота в отдельном разделе** | `docs/fst-project-health-playbooks/` |
| 3 | **fst-project-health-snap-md.PLAYBOOK.md** | Подробный playbook генератора MD-слепков | API, массовые вызовы, never-fail, логирование | `docs/fst-project-health-playbooks/` |
| 4 | **fst-project-health-from-md-snapshot.PLAYBOOK.md** | Подробный playbook извлечения снапшотов и HTML-сборки | 5 режимов выбора, методы, кросс-ссылка на word | `docs/fst-project-health-playbooks/` |
| 5 | **fst-project-health-tests.PLAYBOOK.md** | Подробный playbook тестового скилла | 6 групп тестов, конфиг проекта, устойчивость к flake | `docs/fst-project-health-playbooks/` |
| 6 | **ALL-SCRIPTS.PLAYBOOK.md** | Единый справочник по **всем 60 скриптам** всех скиллов | Скрипт, скилл, LOC, размер, назначение, время | `docs/fst-project-health-playbooks/` |
| 7 | **SNAPSHOTS-SYSTEM.PLAYBOOK.md** | Полное описание **системы слепков** (pipeline live + snapshot) | Схемы pipeline, массовые сценарии, признаки в HTML | `docs/fst-project-health-playbooks/` |
| 8 | **REUSABLE-METHODS.PLAYBOOK.md** | Каталог **переиспользуемых методов** всех скиллов | Метод, скилл, параметры, операции с MCP, паттерны импорта | `docs/fst-project-health-playbooks/` |
| — | **INDEX.md** | Этот рубрикатор | Указатель всех PLAYBOOK + маппинг «ситуация → документ» | `docs/fst-project-health-playbooks/` |

---

## Какие документы читать в каких ситуациях

| Ситуация | Что открыть |
|---|---|
| Хочу собрать live-отчёт | `[1]` |
| Хочу собрать DOCX | `[2]` |
| Хочу сгенерировать слепки | `[3]` |
| Хочу извлечь слепок и построить HTML | `[4]` |
| Хочу прогнать тесты | `[5]` |
| Хочу узнать, что делает конкретный скрипт | `[6]` |
| Хочу понять, как работает весь pipeline слепков | `[7]` |
| Хочу вызвать метод из своего кода | `[8]` |

---

## Размеры

| Документ | Размер |
|---|---|
| `fst-project-health.PLAYBOOK.md` | ~11 KB |
| `fst-project-health-word.PLAYBOOK.md` | ~11 KB |
| `fst-project-health-snap-md.PLAYBOOK.md` | ~9 KB |
| `fst-project-health-from-md-snapshot.PLAYBOOK.md` | ~9 KB |
| `fst-project-health-tests.PLAYBOOK.md` | ~11 KB |
| `ALL-SCRIPTS.PLAYBOOK.md` | ~10 KB |
| `SNAPSHOTS-SYSTEM.PLAYBOOK.md` | ~17 KB |
| `REUSABLE-METHODS.PLAYBOOK.md` | ~17 KB |
| **ИТОГО** | **~95 KB** |

---

## Штатные пути

Все PLAYBOOK лежат в:

```
~/.hermes/profiles/fst-control/docs/fst-project-health-playbooks/
```

Рубрикатор (этот файл) — `INDEX.md`.

---

## Соглашения об именовании

- `<skill-name>.PLAYBOOK.md` — playbook конкретного скилла (5 штук).
- `ALL-SCRIPTS.PLAYBOOK.md` — общий каталог скриптов.
- `SNAPSHOTS-SYSTEM.PLAYBOOK.md` — общий pipeline слепков.
- `REUSABLE-METHODS.PLAYBOOK.md` — каталог переиспользуемых методов.
- `INDEX.md` — этот рубрикатор.

Имена файлов содержат **понятный контекст**: при взгляде на имя сразу понятно, о чём документ.
