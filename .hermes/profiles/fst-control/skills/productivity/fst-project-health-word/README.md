# fst-project-health-word

Отдельный скилл для генерации **WORD-отчёта** (Форма 1) на основе
MD-файла, созданного скиллом `fst-project-health`.

**Зачем выделен в отдельный скилл:**
WORD нужен редко, а его генерация занимает время. Поэтому `fst-project-health`
строит **только MD + HTML**, а WORD генерируется **по запросу** этим
скиллом — как опция.

## Использование

### Способ 1: из CLI (вручную)

```bash
# Сначала сгенерировать MD (использует основной скилл):
python3 ~/.hermes/profiles/fst-control/skills/productivity/fst-project-health/scripts/run_all.py --code 504-595

# Потом сгенерировать WORD (этот скилл):
python3 ~/.hermes/profiles/fst-control/skills/productivity/fst-project-health-word/scripts/build_word_report.py --code 504-595
```

### Способ 2: через Hermes Agent

Попросить: «сделай WORD по проекту 504-595». Агент сам:
1. Запустит `fst-project-health` для построения MD/HTML (если ещё не построены).
2. Запустит этот скилл для генерации `.docx`.
3. Пришлёт файл в Telegram.

### Способ 3: с явным указанием путей

```bash
python3 scripts/build_word_report.py \
    --md /tmp/project_504-595_report.md \
    --output /tmp/my_report.docx
```

## Структура

```
fst-project-health-word/
├── SKILL.md                  # описание скилла для Hermes Agent
├── README.md                 # этот файл
├── .env.example              # пустой (MCP не нужен)
├── requirements.txt          # python-docx>=1.0
├── scripts/
│   └── build_word_report.py  # генератор .docx из MD
├── templates/
│   └── word-report-template.py  # шаблон DATA-словаря
├── references/
│   └── word-report-procedure.md # детали процедуры
└── outputs/                  # сюда класть .docx (по умолчанию /tmp/)
```

## Входные данные

- **MD-файл** — `/tmp/project_<code>_report.md` (создаётся `fst-project-health`).
  Скрипт парсит разделы 3–7, section_6_indicators, и собирает data-словарь.

## Выход

- **.docx файл** — `/tmp/project_<code>_report_WORD-форма1.docx` (по умолчанию).

## Что НЕ делает

- ❌ **Не строит MD/HTML** — это делает `fst-project-health`.
- ❌ **Не обращается к MCP** — никаких токенов, никаких сетевых вызовов.
- ❌ **Не модифицирует данные** на стороне PMForesight.

## Переносимость

Скилл portable. Не требует MCP-токена, не требует доступа к сети.
Работает и в Hermes-профиле `fst-control`, и автономно в любом
каталоге (если есть `build_word_report.py` + `python-docx`).

```bash
# На другом сервере
scp -r fst-project-health-word/ user@server:/opt/skills/
cd /opt/skills/fst-project-health-word
pip install -r requirements.txt

# Нужен только MD-файл от fst-project-health — сгенерируйте его
# на любой машине с доступом к MCP и скопируйте сюда.
python3 scripts/build_word_report.py --code 504-595 --md /path/to/report.md
```

## История

Версии семейства `fst-project-health-*` ведутся в общем [CHANGELOG.md](../fst-project-health/CHANGELOG.md).

- **v1.0.19** (2026-09-23) — синхронизация с семейством. Код
  `scripts/build_word_report.py` актуализирован для перенумерованного
  MD (раздел 6 = «Показатели проекта», 7 = «Финансы», 8 = «Тех.
  данные»): `self_extract_table(flexible=True)` для совместимости
  с разным числом колонок; распознаётся новый формат вердикта
  (`**Статус: БОЛЕН**`); старые MD от 21.09 продолжают работать.
- **v1.0.0** (2026-09-15) — выделен из `fst-project-health` как
  отдельный скилл. До этого WORD генерился при каждом запуске
  `run_all.py` (зря тратил ресурсы).
