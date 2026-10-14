# fst-project-health-from-md-snapshot

**Версия:** 1.0.19 — 2026-09-24

Скилл для **исторического** HTML-отчёта по проекту. Берёт MD-снимок из
карточки проекта в MCP (а не живой отчёт), строит HTML **строго** из этого
MD — никаких обращений к live MCP.

Заменяет deprecated `fst-project-health-from-json`.

---

## Зачем

Когда хочется узнать, **как проект выглядел 23 сентября** — этого не
даст `fst-project-health`, потому что он собирает данные «сейчас». Этот
скилл читает MD-архив, который ранее положил `fst-project-health-snap-md`
в карточку проекта, и собирает HTML по тем данным.

Типичные сценарии:

- **Аудит**: «покажи отчёт по состоянию на 23.09 для совещания у замдиректора».
- **Трендовый анализ**: «выгрузи снимки за последние 4 недели, я сделаю CSV».
- **Откат при сбое MCP**: «MCP лежит, но мне нужен отчёт за прошлую неделю».

---

## Использование

### Базовое

```bash
# Самый свежий снимок
python3 scripts/fetch_snapshot.py --code 504-595 --last

# Самый ранний (для трендов)
python3 scripts/fetch_snapshot.py --code 504-595 --first

# Ближайший к указанной дате (для cron'а "на конец дня")
python3 scripts/fetch_snapshot.py --code 504-595 --nearest --at "2026-09-23"

# Точный timestamp (если знаем из другого источника)
python3 scripts/fetch_snapshot.py --code 504-595 --exact "2026-09-23 21:53:09"

# Интерактивный выбор из списка
python3 scripts/fetch_snapshot.py --code 504-595 --pick

# Только список снимков (без скачивания)
python3 scripts/fetch_snapshot.py --code 504-595 --list
```

### Массовые прогоны (`--codes`)

```bash
# Последние снимки по 4 проектам
python3 scripts/fetch_snapshot.py --codes 504-595 503-152 503-434 504-314 --last

# Ближайшие к "2026-09-23 21:00"
python3 scripts/fetch_snapshot.py --codes 504-595 503-152 --nearest --at "2026-09-23 21:00"
```

### Полный цикл: fetch + HTML

```bash
python3 scripts/run.py --code 504-595 --last
# Step 1: fetch MD → ~/.hermes/profiles/fst-control/cache/snapshots/...
# Step 2: build HTML → /tmp/<basename>.html
```

Только извлечь (без HTML):
```bash
python3 scripts/run.py --code 504-595 --last --no-html
```

Только HTML из уже-скачанного MD:
```bash
python3 scripts/build_html.py --md ~/.hermes/profiles/fst-control/cache/snapshots/504-595_*.md
```

### Когда что использовать (резюме)

| Задача | Команда |
|---|---|
| Последний снимок (audit) | `--code X --last` |
| Снимок «на дату Х» (cron) | `--code X --nearest --at "..."` |
| Конкретный timestamp | `--code X --exact "..."` |
| Трендовый анализ (4+ проекта) | `--codes X Y Z --last` или `--nearest --at` |
| Просто посмотреть, что есть | `--code X --list` |

---

## Логирование

Каждый запуск пишет отдельный файл в `logs/<ISO-timestamp>.log`.

### Что внутри

1. **Header**:
   - дата/время старта;
   - аккаунт пользователя (из JWT);
   - роль из MCP (PMForesight не возвращает явную роль → `n/a (...)`);
   - **Action**: `fetch` (извлечение) / `html` (сборка HTML) / `fetch+html`;
   - **Args**: полная строка аргументов;
   - **Projects in run**: что пришло в `--code`/`--codes`.
2. **Body** (на каждый проект):
   - `✓ <code> — ok — file=... — snapshot_ts=... — duration=Ts`
   - `✗ <code> — <status> — duration=Ts` + блок с `type`/`http_code`/`message`/`raw`.
3. **Trailer** (в `finally:`).

### Зачем нужен лог для **извлекателя** (отдельная мотивация)

Если кто-то переиспользует `fetch_snapshot.py` для **массового** чтения
MD (например, трендовый анализ по 50 проектам), лог ему скажет:

- какие проекты прочитались;
- какие — нет и почему (`not_found`, `permission_denied`,
  `read_error` с полным текстом);
- можно ли безопасно продолжать pipeline, или нужна ручная обработка.

Без лога — это «50 файлов на диске, но какие-то пустые, разбирайтесь сами».

### Пример реального лога

```
=== fst-project-health-from-md-snapshot v1.0.19 run log ===
Started at:           2026-09-24T14:37:52.561777
Caller account:       Кузнецов Ростислав Владимирович <rkuznetsov@pmpractice.ru> (sub=120872)
Caller role (MCP):    n/a (PMForesight profile fields: ['Account', 'DTheme_Identifier', ...]; no role/permissions exposed)
Action:               fetch
Args:                 --codes 504-595 999-FAKE --last
Projects in run:      ['504-595', '999-FAKE']
────────────────────────────────────────────────────────────────────────────────
  ✓ 504-595 — ok — physicalFileId=72afc483-7205-40d1-bc49-d05fc04ee3a6 — file=504-595_2026-09-24_14-37-41.md — snapshot_ts=2026-09-24 14:37:41 — 5.47 s
  ✗ 999-FAKE — not_found — 0.45 s
      type:       find_entity
      message:    project_id не найден для кода 999-FAKE
────────────────────────────────────────────────────────────────────────────────
Total: 2 projects, 1 ok, 1 fail
Total duration: 5.92 s
Finished at: 2026-09-24T14:37:59.512455
=== END LOG ===
```

---

## Сценарии устойчивости (важно!)

Этот скилл **никогда не падает на середине цикла**. Три типичных сценария:

### 1. Идеальный

Пользователь имеет права на все проекты, MCP доступен, снимки есть.
Все 4 проекта → 4 OK в логе.

### 2. Частый: нет прав на часть проектов

```
--codes 504-595 503-152 503-434 504-314
```

Если у пользователя есть права только на 504-595 и 503-152:

- 504-595 и 503-152 → OK, MD скачаны.
- 503-434 и 504-314 → `not_found` или `permission_denied` в логе.
- **Скрипт продолжает**, итог: 2 ok / 2 fail.

### 3. Опечатка / удалённый проект

```
--codes 504-595 999-FAKE
```

- 504-595 → OK.
- 999-FAKE → `not_found` в логе с message «проверьте право на чтение / существование».
- **Скрипт продолжает**, итог: 1 ok / 1 fail.

### Принцип

> Скрипт может — делает.
> Не может — пишет в лог.
> На середине никогда не останавливается и не падает.

---

## Ротация логов

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

# С другой политикой:
python3 scripts/rotate_logs.py --archive-days 180 --delete-days 730

# На конкретный каталог:
python3 scripts/rotate_logs.py --log-dir /path/to/other/skill/logs
```

Зачем нужен ротатор для **извлекателя** (отдельная мотивация):
если этот скилл гоняется **массово** (трендовый анализ по 50 проектам),
логи копятся быстрее. Без ротации через 2–3 месяца в `logs/` будет
тысяча файлов; ротатор держит в `logs/` только последние ~13 месяцев.

---

## Где хранится кэш

`~/.hermes/profiles/fst-control/cache/snapshots/`

Имя файла: `<code>_<timestamp>.md` (timestamp из имени снимка в MCP).

Пример:
```
504-595_2026-09-24_14-37-41.md
503-152_2026-09-21_20-30-00.md
```

Кэш не ротируется автоматически. За очистку отвечает администратор или
ваш pipeline.

---

## История

- **v1.0.19** (2026-09-24) — первая версия. Заменяет `fst-project-health-from-json`.

Подробный changelog и все архитектурные решения — в общем [CHANGELOG.md](../fst-project-health/CHANGELOG.md).
