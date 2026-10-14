# Playbook: `fst-project-health` + `fst-project-health-word` — как получить WORD-отчёт

**Версия:** v1.0.0 — 2026-09-15
**Для кого:** коллеги, которые хотят получить отчёт о здоровье проекта
в формате WORD (.docx).
**Связанные скиллы:**
- `fst-project-health` — основной (MD + HTML)
- `fst-project-health-word` — отдельный (WORD)

---

## 📖 Краткая суть

С 2026-09-15 **WORD-генерация вынесена в отдельный скилл**.
Раньше `fst-project-health` строил MD + HTML + WORD за один запуск,
тратя ресурсы зря (WORD нужен редко). Теперь:

```
fst-project-health          →  MD + HTML          (всегда при запуске)
fst-project-health-word     →  WORD               (только по запросу)
```

---

## 🚀 Сценарий 1: «Построй обычный отчёт по проекту 504-595»

Если нужен только **HTML** (например, для просмотра в браузере или
отправки в Telegram как файл), запускается только основной скилл:

```bash
python3 ~/.hermes/profiles/fst-control/skills/productivity/fst-project-health/scripts/run_all.py --code 504-595
```

**На выходе:**
- `/tmp/project_504-595_report.md` — Markdown
- `/tmp/project_504-595_report.html` — HTML (открыть в браузере)

Время: ~40 сек (зависит от объёма данных).

---

## 🚀 Сценарий 2: «Построй WORD по проекту 504-595»

### Шаг 1. Убедиться, что MD-файл уже есть

```bash
ls -la /tmp/project_504-595_report.md
```

Если файла нет — запустить основной скилл:

```bash
python3 ~/.hermes/profiles/fst-control/skills/productivity/fst-project-health/scripts/run_all.py --code 504-595
```

### Шаг 2. Запустить генерацию WORD

```bash
python3 ~/.hermes/profiles/fst-control/skills/productivity/fst-project-health-word/scripts/build_word_report.py --code 504-595
```

**На выходе:** `/tmp/project_504-595_report_WORD-форма1.docx`

Время: ~2–5 сек (только парсинг MD → .docx, без сетевых вызовов).

### Альтернатива: явный путь

```bash
python3 scripts/build_word_report.py \
    --md /tmp/project_504-595_report.md \
    --output /tmp/my_report.docx
```

---

## 🚀 Сценарий 3: «Отправь мне и HTML, и WORD по 504-595»

Через Hermes Agent:

1. Пользователь: «построй отчёт по 504-595 и пришли HTML и WORD»
2. Агент:
   - Запускает `fst-project-health` (MD + HTML).
   - Запускает `fst-project-health-word` (WORD).
   - Отправляет оба файла в Telegram.

---

## 🛠 Установка на другом сервере

```bash
# 1. Скопировать оба скилла
scp -r fst-project-health/      user@server:/opt/skills/
scp -r fst-project-health-word/ user@server:/opt/skills/

# 2. Установить зависимости
cd /opt/skills/fst-project-health
pip install -r requirements.txt     # requests, python-docx (но python-docx больше не нужен)

cd /opt/skills/fst-project-health-word
pip install -r requirements.txt     # только python-docx

# 3. Настроить .env для fst-project-health
cp .env.example .env
nano .env   # вписать PMP_TOKEN=<jwt-токен>

# 4. Готово
python3 /opt/skills/fst-project-health/scripts/run_all.py --code 504-595
python3 /opt/skills/fst-project-health-word/scripts/build_word_report.py --code 504-595
```

---

## ❓ FAQ

### Можно ли запустить только WORD без MD?

Нет. `fst-project-health-word` **читает MD-файл**. Без MD ему нечего
обрабатывать. Сначала запустите `fst-project-health`.

### Что если MD-файла нет, а WORD нужен?

Запустите оба скилла подряд:

```bash
python3 ~/.hermes/profiles/fst-control/skills/productivity/fst-project-health/scripts/run_all.py --code 504-595 && \
python3 ~/.hermes/profiles/fst-control/skills/productivity/fst-project-health-word/scripts/build_word_report.py --code 504-595
```

### WORD требует MCP-токен?

**Нет.** `fst-project-health-word` не обращается к MCP. Нужен только
`python-docx`. MCP-токен нужен только для `fst-project-health`
(при первом запуске для построения MD).

### Можно ли построить WORD по произвольному MD?

Да, через `--md`:

```bash
python3 scripts/build_word_report.py --md /path/to/any_report.md --output /tmp/out.docx
```

### Как понять, что MD устарел и надо пересобрать?

Сравнить даты:

```bash
ls -la /tmp/project_504-595_report.md /tmp/project_504-595_report.html
```

Если MD старше, чем данные в MCP — пересобрать:

```bash
cd ~/.hermes/profiles/fst-control/skills/productivity/fst-project-health/scripts
find . -name __pycache__ -type d -exec rm -rf {} +
rm -f /tmp/.cache_run_all_*.json
python3 run_all.py --code 504-595 --no-cache
```

### Что насчёт тестов?

Тесты `fst-project-health/tests/` остались без изменений. WORD
вынесен, но unit-тесты на `build_word_report.py` (если были) — нет.
Если нужны — добавить отдельный набор в `fst-project-health-word/tests/`.

---

## ⚠️ Что изменилось (для тех, кто работал с предыдущей версией)

| Что | Было (до 2026-09-15) | Стало |
|---|---|---|
| WORD-генерация | Внутри `run_all.py::build_word()` | Отдельный скилл `fst-project-health-word` |
| Флаг `--no-word` в `run_all.py` | был | удалён (нечего отключать) |
| Файл `build_word_report.py` | в `fst-project-health/scripts/` | в `fst-project-health-word/scripts/` |
| Файл `word-report-template.py` | в `fst-project-health/templates/` | в `fst-project-health-word/templates/` |
| Файл `word-report-procedure.md` | в `fst-project-health/references/` | в `fst-project-health-word/references/` |
| Зависимость `python-docx` | в `fst-project-health/requirements.txt` | в `fst-project-health-word/requirements.txt` |
| Время `run_all.py` (504-595) | ~53 сек (с WORD) | ~40 сек (без WORD) |

**Экономия:** ~14 сек на каждом запуске `run_all.py` без запроса WORD.

---

## 🔄 Если что-то пошло не так

### WORD не сгенерировался

1. Проверить, что MD-файл существует: `ls -la /tmp/project_<code>_report.md`.
2. Проверить, что `python-docx` установлен: `pip show python-docx`.
3. Запустить с `--md` явно: `python3 scripts/build_word_report.py --md /tmp/project_504-595_report.md`.

### HTML сломался (после обновления палитры AGPM)

Откатить через контрольную точку:

```bash
cd ~/.hermes/profiles/fst-control/skills/productivity
rm -rf fst-project-health
tar -xzf /tmp/fst-project-health-checkpoint-premod.tar.gz
```

Контрольная точка сделана **до** всех модификаций (палитра + выделение WORD).

---

*Сгенерировано для связки `fst-project-health` + `fst-project-health-word`.
Дата: 2026-09-15. Автор: Hermes Agent (постановка ROSTISLAV KUZNETSOV).*