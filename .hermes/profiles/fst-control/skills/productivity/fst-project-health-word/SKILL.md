---
name: fst-project-health-word
version: 1.0.20
description: "Генератор WORD-отчёта (Форма 1) из MD-файла, созданного fst-project-health. Опциональная часть pipeline — WORD нужен редко, поэтому выделен в отдельный скилл."
tags: [report, pmpractice, ru, foresight, project-health, word, docx, docx-generation, optional]
---

# fst-project-health-word

## When to load

- Пользователь просит «сделай WORD», «.docx отчёт», «WORD-версия»,
  «отчёт в формате Word» — для проекта, по которому уже построены
  MD/HTML через `fst-project-health`.
- Нужно сгенерировать WORD-версию **по запросу**, не при каждом
  запуске основного скилла (экономия ресурсов).

## CRITICAL: это ОПЦИОНАЛЬНАЯ часть pipeline

**Не запускается автоматически** вместе с `fst-project-health`.
Только по явному запросу пользователя.

**Предпосылка:** уже есть `/tmp/project_<code>_report.md` (создан
`fst-project-health/scripts/run_all.py`). Без MD — скилл не работает.

## Quick reference

- **Главный скрипт:** `scripts/build_word_report.py`
- **Запуск:** `python3 scripts/build_word_report.py --code 504-595`
- **MD на входе:** `/tmp/project_<code>_report.md`
- **WORD на выходе:** `/tmp/project_<code>_report_WORD-форма1.docx`
- **Портабельность:** portable (только Python + python-docx)

## Использование из Hermes

### Паттерн 1: «построй WORD по проекту 504-595»

```
1. Проверить, есть ли /tmp/project_504-595_report.md
2. Если нет — запустить fst-project-health для построения MD/HTML
3. Запустить этот скилл: python3 scripts/build_word_report.py --code 504-595
4. Отправить .docx пользователю в Telegram
```

### Паттерн 2: «сделай всё по проекту 504-595 (включая WORD)»

```
1. fst-project-health → MD + HTML
2. Этот скилл → WORD
3. Отправить оба файла пользователю
```

### Паттерн 3: пользователь прислал свой MD-файл

```
python3 scripts/build_word_report.py --md /path/to/report.md --output /tmp/out.docx
```

## Что внутри

| Файл | Назначение |
|---|---|
| `scripts/build_word_report.py` | Читает MD → строит data-словарь → вызывает `build_word_report_from_data()` → сохраняет .docx |
| `templates/word-report-template.py` | Шаблон DATA-словаря для ручной генерации (когда MD не используется) |
| `references/word-report-procedure.md` | Подробная процедура (Pitfall #58 и др.) |
| `requirements.txt` | `python-docx>=1.0.0` |
| `.env.example` | Пустой (MCP не нужен) |

## Что НЕ входит

- ❌ Нет MCP-вызовов (всё read-only по MD).
- ❌ Нет сборки MD/HTML — это делает `fst-project-health`.
- ❌ Нет модификации данных PMForesight.

## Связь с `fst-project-health`

```
fst-project-health (основной)
   ├── scripts/run_all.py    → MD + HTML
   │
   └── /tmp/project_<code>_report.md  (передаётся)
                                        │
                                        ▼
              fst-project-health-word (этот скилл)
                  └── scripts/build_word_report.py → .docx
```

**Триггер запуска:** только когда пользователь явно попросил WORD.
Не запускать при обычной просьбе «отчёт по 504-595».

## Portable setup

```bash
# 1. Скопировать каталог
scp -r fst-project-health-word/ user@server:/opt/skills/

# 2. Зависимости
cd /opt/skills/fst-project-health-word
pip install -r requirements.txt

# 3. Готово. .env не нужен.
python3 scripts/build_word_report.py --code 504-595
```

Нужен только `python-docx` (Python-зависимость) и **MD-файл от
`fst-project-health`**. Никаких токенов, никакой сети.

## Pitfalls (из истории)

- **#58** — старый формат данных WORD-отчёта; при миграции
  `fst-project-health` нужно проверить совместимость
  `data-словаря`.
- **#224** — портабельность: при переносе на другой сервер нужны
  только Python + python-docx, НЕ нужен MCP-токен.

## История

Версии семейства `fst-project-health-*` ведутся в общем [CHANGELOG.md](../fst-project-health/CHANGELOG.md).

- **v1.0.19** (2026-09-23) — синхронизация с семейством. Код
  `scripts/build_word_report.py` актуализирован для перенумерованного
  MD (раздел 6 = «Показатели проекта», 7 = «Финансы», 8 = «Тех.
  данные»): `self_extract_table(flexible=True)` для совместимости
  с разным числом колонок; распознаётся новый формат вердикта
  (`**Статус: БОЛЕН**`); старые MD от 21.09 продолжают работать.
  Шаблон был сломан при переходе на v1.0.18 — теперь работает.
- **v1.0.0** (2026-09-15) — выделен из `fst-project-health`. До этого
  WORD генерился в `run_all.py::build_word()` при каждом запуске —
  зря тратил ресурсы. Теперь — опциональная команда.

---

*См. также: `fst-project-health` (основной), `fst-mcp-tester`
(тестирование MCP-методов).*