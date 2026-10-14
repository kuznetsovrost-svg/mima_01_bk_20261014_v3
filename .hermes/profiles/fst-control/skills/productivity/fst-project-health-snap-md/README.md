# fst-project-health-snap-md

Скилл для **периодического сохранения MD-слепков** состояния проектов
из PMForesight в карточки проектов (категория «Документы ИИ»).

## Назначение

Этот скилл — **исторический архив**. Каждый прогон сохраняет
MD-отчёт о состоянии проекта. Потом, когда пользователь спросит
«как проект 504-595 выглядел 2026-09-21» — другой скилл прочитает
сохранённый MD и построит HTML «как тогда».

**Почему MD, а не JSON:**
- HTML из MD — идентичен HTML от `fst-project-health` (используется
  тот же шаблон).
- Исторический отчёт за прошлую дату = точная копия того, что было бы
  в обычном отчёте на ту дату.

## Использование

```bash
# Полный прогон по всем проектам (DEFAULT_PROJECTS из скрипта)
python3 scripts/run_snap_md.py

# Один проект
python3 scripts/run_snap_md.py --code 504-595

# Массовый запуск: список кодов через --codes (см. PLAYBOOK §2.3)
python3 scripts/run_snap_md.py --codes 504-595 503-152 503-434 504-314

# Dry-run (только локально, без MCP)
python3 scripts/run_snap_md.py --dry-run

# Dry-run массовый (полезно для предварительной проверки списка)
python3 scripts/run_snap_md.py --codes 504-595 999-FAKE-XXX --dry-run
```

`--code` и `--codes` — взаимоисключающие. Без обоих — берётся
`DEFAULT_PROJECTS` из скрипта (правится ДО запуска).

## Логирование

**Каждый запуск пишет отдельный лог в `logs/<ISO-timestamp>.log`.**

Имя файла: `2026-09-24T14-31-51.log` (timestamp момента старта `main()`).

### Что внутри

1. **Header** (до первого проекта):
   - дата/время старта;
   - аккаунт пользователя (из JWT: `displayname <email> (sub=user_id)`);
   - роль из MCP (PMForesight НЕ возвращает явную роль → `n/a (PMForesight profile fields: ...)`);
   - **два списка проектов**: `Projects in script` (что было в `DEFAULT_PROJECTS`) и `Projects in run` (что пришло в этом запуске через `--codes` или `--code`).
2. **Body** (на каждый проект):
   - `✓ <code> — ok — FileId=N — duration=Ts`
   - `✗ <code> — <status> — duration=Ts` + блок с **полным текстом ошибки** (`type`, `http_code`, `message`, `raw[:300]`).
3. **Trailer** (в `finally:`): итог и время.

### Философия

> Скрипт может — делает.
> Не может — пишет в лог.
> На середине никогда не останавливается и не падает.

Если MCP лежит в момент `initialize` — лог всё равно пишется, цикл по проектам
пропускается с `n/a (MCP init skipped)`. Если один проект не существует
(опечатка в списке) — другие продолжают обрабатываться, в логе появится
`not_found`.

### Пример реального лога (DRY-RUN с частично неверным списком)

```
=== fst-project-health-snap-md v1.0.19 run log ===
Started at:           2026-09-24T14:31:51.508025
Caller account:       Кузнецов Ростислав Владимирович <rkuznetsov@pmpractice.ru> (sub=120872)
Caller role (MCP):    n/a (PMForesight profile fields: ['Account', 'DTheme_Identifier', ...]; no role/permissions exposed)
Mode:                 DRY-RUN (без MCP)
Projects in script:   ['504-595', '503-152', '503-434', '504-314']
Projects in run:      ['504-595', '999-FAKE-XXX']
─────────────────────────────────────────────────────────────────────────────
  ✓ 504-595 — ok — file=Слепок fst-project-health-snapshot-504-595-2026-09-24_14-32-12.MD — 20.22 s
  ✗ 999-FAKE-XXX — not_found — 0.50 s
      type:       find_entity
      message:    project_id не найден для кода 999-FAKE-XXX (проверьте право на чтение / существование проекта)
─────────────────────────────────────────────────────────────────────────────
Total: 2 projects, 1 ok, 1 fail
Total duration: 20.72 s
Finished at: 2026-09-24T14:32:13.241847
=== END LOG ===
```

### Зачем лог

- **Аудит**: кто, когда, что — без обращения к терминалу.
- **Диагностика**: при сбое видно `type`/`message`/`http_code` без воспроизведения.
- **Массовые прогоны**: один проект с ошибкой не роняет весь прогон.

Подробности — в `playbook.md`, секция «Принципы логирования и устойчивости».

### Ротация логов

Логи **не ротируются сами**. За это отвечает отдельный скрипт
`scripts/rotate_logs.py` (можно ставить в cron).

Политика (v1.0.19):
- **> 400 дней** → gzip + `logs/archive/YYYY-MM/`
- **> 1500 дней** → удалить

```bash
# Боевой прогон:
python3 scripts/rotate_logs.py

# Только показать план (dry-run):
python3 scripts/rotate_logs.py --dry-run

# С другой политикой (например, для тестов):
python3 scripts/rotate_logs.py --archive-days 180 --delete-days 730

# На конкретный каталог (если нужно прогнать на чужом logs/):
python3 scripts/rotate_logs.py --log-dir /path/to/other/skill/logs
```

## Имена файлов

```
Слепок fst-project-health-snapshot-<project_code>-YYYY-MM-DD_HH-MM-SS.MD
```

Пример: `Слепок fst-project-health-snapshot-504-595-2026-09-21_18-30-45.MD`

## Установка

```bash
# Зависимости
pip install -r requirements.txt

# .env
cp .env.example .env
nano .env  # PMP_TOKEN=<jwt-токен PMForesight>

# Должен быть установлен соседний скилл:
# - fst-project-health (для сбора MD через subprocess)
```

### На другом сервере

```bash
# 1. Скопировать 2 скилла:
scp -r fst-project-health/      user@server:/opt/skills/
scp -r fst-project-health-snap-md/ user@server:/opt/skills/

# 2. Зависимости
cd /opt/skills/fst-project-health-snap-md
pip install -r requirements.txt

# 3. .env
cp .env.example .env
# Указать пути:
#   FST_PROJECT_HEALTH_PATH=/opt/skills/fst-project-health
#   PMP_TOKEN=<jwt>
```

## Список проектов

4 проекта (`DEFAULT_PROJECTS` в скрипте):
- `504-595`, `503-152`, `503-434`, `504-314`

## Расписание

Рекомендуется cron раз в неделю ночью:
```cron
0 3 * * 0 cd /opt/skills/fst-project-health-snap-md && python3 scripts/run_snap_md.py
```

## Структура каталога

```
fst-project-health-snap-md/
├── SKILL.md                  # описание скилла
├── README.md                 # этот файл
├── .env.example              # шаблон PMP_TOKEN
├── requirements.txt          # requests
├── scripts/
│   └── run_snap_md.py        # главный скрипт
└── outputs/                  # локальные копии MD
```

## Отличие от `fst-project-health-snapshot`

| | `fst-project-health-snapshot` | `fst-project-health-snap-md` (этот) |
|---|---|---|
| Что кладёт | JSON (data-словарь) | MD (готовый отчёт) |
| Парсит ли MD сам | Нет (парсинг MD теперь в `fst-project-health/build_html_report.py`) | Нет (этот скилл вообще не парсит) |
| Имя файла | `.JSON` | `.MD` |
| Назначение | Для построителя трендов (аналитика) | Для исторического HTML |

**v1.0.19 уточнение.** Раньше снимок-в-JSON зависел от
`fst-project-health-word` ради парсера MD. С v1.0.19 парсинг встроен
в `fst-project-health/build_html_report.py` (`_parse_indicators_from_md`),
поэтому зависимость от `fst-project-health-word` для парсинга больше
**не нужна**. `fst-project-health-word` остаётся отдельным скиллом для
генерации DOCX.

**v1.0.19 уточнение по генератору.** `--generator fst-project-health-snap-md`
передаётся в `run_all.py` — это имя пишется в YAML-метаданных MD
в поле `generator:`. Так читатель снапшота сразу видит, что данные
пришли из этого скилла, а не из живого прогона `fst-project-health`.

## История

- **v1.0.19** (2026-09-23) — убрана зависимость от `fst-project-health-word`
  для парсинга (парсинг встроен в `fst-project-health/build_html_report.py`);
  добавлен `--generator fst-project-health-snap-md` для атрибуции в YAML
  front-matter; снят HTML-комментарий `<!-- snapshot_timestamp -->` —
  теперь timestamp живёт в YAML front-matter от `rebuild_report.py`.
- **v1.0.0** (2026-09-21) — первый релиз.

---

*См. также: `fst-project-health` (зависимость), `fst-project-health-snapshot`
(JSON-аналог), `fst-mcp-tester` (read-only тесты MCP).*