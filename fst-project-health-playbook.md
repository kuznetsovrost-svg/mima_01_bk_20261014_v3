# Playbook — проверка скилла fst-project-health в VS Code

> Источник: `/root/.hermes/profiles/fst-control/skills/productivity/fst-project-health/`
> Дата: 2026-08-09
> Скилл: v0.10.0, автор ROSTISLAV KUZNETSOV

---

## 1. Краткая карточка скилла

| Параметр | Значение |
|---|---|
| **Имя** | `fst-project-health` |
| **Class** | class-level skill |
| **Расположение** | /root/.hermes/profiles/fst-control/skills/productivity/fst-project-health/ |
| **SKILL.md** | 81 KB, 470 строк |
| **Scripts** | 23 файла Python |
| **References** | 25 файлов .md |
| **Templates** | есть |
| **Category** | productivity |
| **Related** | project-search |
| **Версия** | 0.10.0 |
| **Автор** | ROSTISLAV KUZNETSOV |

### Что делает (из frontmatter)

> Generates health-of-project report (4 sections: timing, completeness,
> forecast-validity, financial) for one project in ИСУП «Форсайт» /
> PMForesight via its MCP. Five independent output formats.

### 5 форматов вывода

| Формат | Файл | Когда |
|---|---|---|
| **MD** | /tmp/project_<code>_report.md | chat / repo / reference |
| **HTML** | /tmp/project_<code>_report.html | browser, `<details>`, CSS |
| **MD Форма 2** | /tmp/project_<code>_report_MD-форма2.md | flat, "Цвет/Статус" |
| **WORD Форма 1** | /tmp/project_<code>_report_WORD-форма1.docx | print / email |
| **FIGMA bridge** | /tmp/figma_new_template/html/report_<code>_v2.html | HTML → Figma |

---

## 2. Прежде чем проверять — что НЕ нужно делать

| Не делать | Почему |
|---|---|
| Запускать `rebuild_report.py` без проекта | требует параметр `--code` |
| Подключаться к MCP Форсайта | only when actual project |
| Генерировать FIGMA bridge | требует отдельной подготовки |
| Менять SKILL.md | read-only анализ |

---

## 3. Подготовка в VS Code (что открыть)

### 3.1. Workspace структура

```
/root/.hermes/profiles/fst-control/skills/productivity/fst-project-health/
├── SKILL.md                                    # 81 KB — открыть первым
├── scripts/
│   ├── project-health-summary.py               # точка входа
│   ├── rebuild_report.py                       # manual rebuild
│   ├── build_html_report.py
│   ├── build_word_report.py
│   ├── build_report_header.py
│   ├── mcp_config.py                            # 17 KB — критичный
│   ├── mcp_probe.py
│   ├── find_project_by_code.py
│   ├── get_effort.py
│   ├── get_project_budget.py
│   ├── get_metamodel.py
│   ├── validate_figma_html.py                  # NEW
│   ├── Effort-check.py
│   ├── Payments-graph-check.py
│   ├── Passport-check.py
│   ├── Forecasted-financial-result.py
│   └── ... (23 total)
├── references/
│   ├── skill-design-spec.md                     # 65 KB — главный spec
│   ├── project-architecture.md                  # 23 KB
│   ├── html-report-pitfalls.md                  # 26 KB
│   ├── figma-to-html-workflow.md                # 27 KB
│   ├── figma-html-roundtrip.md                  # 13 KB
│   ├── md-report-conventions.md
│   ├── project-finance-budget-entities.md       # 17 KB
│   ├── mcp-api-quirks.md
│   ├── mcp-live-probe-cookbook.md
│   ├── mcp-view-discovery-cookbook.md
│   ├── mcp-sse-parsing-and-utf8.md
│   ├── forsight-mcp-quirks.md
│   ├── transport-and-portability.md
│   └── ... (25 total)
└── templates/
```

### 3.2. Что открыть в VS Code

#### Обязательный минимум (5 файлов)

| Файл | Зачем |
|---|---|
| `SKILL.md` | описание, раздел "Five report shapes" |
| `scripts/project-health-summary.py` | точка входа |
| `scripts/mcp_config.py` | конфигурация MCP |
| `references/skill-design-spec.md` | архитектура и контракт |
| `references/project-architecture.md` | архитектура |

#### Дополнительно (по задачам)

| Задача | Открыть |
|---|---|
| Проверить HTML формат | `scripts/build_html_report.py` + `references/html-report-pitfalls.md` |
| Проверить WORD формат | `scripts/build_word_report.py` + `references/word-report-procedure.md` |
| Проверить MD формат | `references/md-report-conventions.md` |
| Проверить FIGMA bridge | `scripts/validate_figma_html.py` + `references/figma-html-roundtrip.md` |
| Проверить MCP quirks | `references/mcp-api-quirks.md` + `references/forsight-mcp-quirks.md` |
| Проверить skidd | `references/skill-design-spec.md` (65 KB) |

### 3.3. Конфигурация VS Code

```json
// settings.json
{
  "files.associations": {
    "*.py": "python"
  },
  "python.analysis.autoImportCompletions": true,
  "python.analysis.typeCheckingMode": "basic",
  "editor.formatOnSave": false,
  "files.trimTrailingWhitespace": false
}
```

---

## 4. Подключение через ACP

### 4.1. Установить strato-space.acp-plugin

(или poppywu124.hermes-chat в remote — оба варианта)

### 4.2. Настроить подключение

```json
// settings.json
{
  "agent_servers": {
    "hermes-fst-analyzer": {
      "name": "Hermes FST Analyzer",
      "command": "ssh",
      "args": [
        "root@mima_g_01",
        "/usr/local/lib/hermes-agent/venv/bin/hermes-acp",
        "--profile", "default"
      ],
      "cwd": "/root/.hermes/profiles/fst-control/skills/productivity/fst-project-health"
    }
  }
}
```

### 4.3. Контекст сессии

```
@Hermes, сегодня я проверяю скилл fst-project-health.

Контекст:
1. SKILL.md (81 KB) — описание
2. 23 скрипта в scripts/
3. 25 references в references/
4. Скилл v0.10.0, автор ROSTISLAV KUZNETSOV
5. Не запускай скрипты — только читать и анализировать

Цель: проверка качества, риски, оптимизация.
```

---

## 5. Стратегия проверки (10 этапов)

### Этап 1. Обзор архитектуры

**Что я делаю:**

```
ты: "Прочитай SKILL.md и skill-design-spec.md.
     Скажи как устроен скилл, какая у него архитектура."
```

**Что я ищу:**

| Аспект | Где смотреть |
|---|---|
| Контракт входов | SKILL.md → "Inputs" / "Procedures" |
| Контракт выходов | SKILL.md → "Five report shapes" |
| Точки входа | scripts/project-health-summary.py |
| MCP зависимости | scripts/mcp_config.py |
| Side effects | любые `write_*` / `replace_*` |
| Шаблоны | scripts + templates/ |

**Команды:**

```
"Прочитай SKILL.md. Какие 5 выходных форматов?"
"Что такое Five report shapes rule?"
"Главные entry points?"
"Какие side effects?"
"Что в templates/?"
```

### Этап 2. Проверка точки входа

**Файл**: `scripts/project-health-summary.py`

```
ты: "Прочитай project-health-summary.py.
     Покажи main() flow, какие функции вызываются,
     какие параметры обязательные."
```

**Что я должен найти:**

| Аспект | Хорошо | Плохо |
|---|---|---|
| Точка входа | `if __name__ == "__main__":` | нет main |
| Параметры | argparse / dataclass | magic globals |
| Ошибки | `raise` + sys.exit | print + continue |
| Dry-run | `--dry-run` флаг | нет |
| Help | `--help` | нет |

### Этап 3. Проверка MCP config

**Файл**: `scripts/mcp_config.py` (17 KB — **критичный**)

```
ты: "Прочитай mcp_config.py.
     Какие endpoints, какие credentials, есть ли
     rate limiting, как обрабатываются ошибки?"
```

**Что я должен найти:**

| Аспект | Хорошо | Плохо |
|---|---|---|
| Credentials | env vars | hardcoded |
| Endpoints | config dict | magic strings |
| Rate limit | exponential backoff | retry = 3 |
| Errors | structured exceptions | print+continue |
| Timeout | configurable | hardcoded 30s |

**Из SKILL.md фронтматтера:**

> "Key MCP pitfalls: ParentFullName for contract link;
> ?ProjectId=<id> server-side filter on ProjectResourcePlan /
> ProjectBudgetCompleteBusiness (149 rows vs 600k scan);
> ProjectBudgetCompleteBusiness > ProjectHealthCostMy (31 columns, clear semantics)."

Проверить, что эти pitfalls **документированы** в коде или references.

### Этап 4. Проверка каждого формата вывода

#### 4.1. MD формат

```
ты: "scripts/rebuild_report.py — это manual rebuild.
     Что он делает? Какие файлы создаёт?
     Покажи структуру MD."
```

#### 4.2. HTML формат

```
ты: "scripts/build_html_report.py — это HTML build.
     Какие CSS переменные, как обрабатываются <details>,
     безопасен ли для browser preview?"
```

#### 4.3. WORD формат

```
ты: "scripts/build_word_report.py — это .docx generator.
     Использует python-docx? Какие стили, w:shd правильно?"
```

#### 4.4. FIGMA bridge

```
ты: "scripts/validate_figma_html.py — это NEW.
     Что валидирует? placeholders, position absolute,
     display grid, CSS variables — какие проверки?"
```

#### 4.5. MD Форма 2

```
ты: "MD Форма 2 — manual copy template.
     Покажи шаблон и пример."
```

### Этап 5. Проверка references

```
ты: "Открой references/skill-design-spec.md (65 KB).
     Сделай оглавление. Какие основные секции?"
```

**Что я должен найти в references:**

| Reference | Проверить |
|---|---|
| skill-design-spec.md | актуальная версия? |
| project-architecture.md | совпадает с кодом? |
| html-report-pitfalls.md | все pitfalls решены? |
| figma-to-html-workflow.md | workflow актуален? |
| mcp-api-quirks.md | все quirks описаны? |
| md-report-conventions.md | conventions применяются? |
| transport-and-portability.md | переносимость учтена? |

### Этап 6. Проверка thresholds

**Файлы**:
- `scripts/point-timing-health-thresholds.py`
- `scripts/point-overdue-thresholds.py`
- `scripts/finresult-thresholds.py`
- `scripts/effort-gap-threshold.py`
- `scripts/financial-deviation-threshold.py`
- `scripts/forecasted-financial-result-deviation.py`
- `scripts/forecasted-financial-value-deviation.py`
- `scripts/point-timing-remark-thresholds.py`

```
ты: "8 файлов thresholds/*.py.
     Каждый должен определять константы вида:
     CRITICAL_DEVIATION_DAYS = N
     Составь таблицу: какой файл, какие константы,
     какие значения. Укажи какие используются в коде."
```

### Этап 7. Проверка чекеров

**Файлы**:
- `Effort-check.py`
- `Fin-result-check.py`
- `LeaderID-check.py`
- `OwnerID-check.py`
- `Passport-check.py`
- `Payments-graph-check.py`
- `Points-forecast-relevance.py`

```
ты: "7 файлов *-check.py.
     У каждого должна быть функция check_*().
     Какие сигнатуры, какие входы, какие выходы?"
```

### Этап 8. Red flags в коде

```
ты: "Просканируй ВСЕ 23 .py файла на red flags:
     - os.system, subprocess shell=True
     - eval, exec
     - requests.post с user data
     - open файлов в /etc/, /var/, /root/
     - hardcoded credentials
     - pickle, yaml.load (не safe)
     - base64 decode"
```

**Ожидаемо**:

| Должно быть | Не должно быть |
|---|---|
| subprocess.run([...], shell=False) | subprocess shell=True |
| pathlib.Path | os.system |
| yaml.safe_load | yaml.load |
| json.loads | eval |
| env vars | hardcoded secrets |

### Этап 9. Проверка документации

```
ты: "Прочитай ВСЕ 25 references/*.md.
     Сделай оглавление. Какие секции актуальны,
     какие устарели (упоминают старый API)?"
```

### Этап 10. Итоговый отчёт

```
ты: "Сделай финальный отчёт:
     1. Резюме — что хорошо
     2. Риски — что опасно
     3. Оптимизации — что улучшить
     4. Checklist — 30 пунктов проверки"
```

---

## 6. Конкретные вопросы для AI (готовые)

### Архитектурные

```
1. Объясни архитектуру скилла в 5 предложениях
2. Какие 5 форматов вывода и когда какой использовать?
3. Главная точка входа?
4. Какие MCP endpoints используются?
5. Какие side effects есть у скилла?
```

### Качество

```
6. Найди 3 риска в коде
7. Какие conflict-prone места?
8. Какие hardcoded значения можно вынести в config?
9. Где нарушен DRY?
10. Какие scripts можно объединить?
```

### Безопасность

```
11. Где credentials хранятся?
12. Какие red flags?
13. Что если MCP endpoint даст 500?
14. Что если проект не существует?
15. Что если HTML содержит XSS?
```

### Оптимизация

```
16. Какие можно распараллелить?
17. Какие неэффективные циклы?
18. Какие тяжёлые JSON.parse можно заменить?
19. Какие thresholds устарели?
20. Какие references устарели?
```

### Совместимость

```
21. Поддерживает ли Python 3.9+?
22. Какие используются externals?
23. Что если python-docx не установлен?
24. Что если MCP API изменится?
25. Какие version-pinned dependencies?
```

### Документация

```
26. SKILL.md отражает реальность?
27. Какие references устарели?
28. Где нужны примеры?
29. Где нужны диаграммы?
30. Что добавить в README?
```

---

## 7. Стратегия "что положить и как открыть"

### 7.1. Layout в VS Code

```
┌─────────────────────────────────────────────────────────────┐
│ VS Code (Remote-SSH → mima_g_01)                             │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ Explorer:                                              │  │
│  │  fst-project-health/                                   │  │
│  │   ├── SKILL.md (1) — открыть                          │  │
│  │   ├── scripts/                                         │  │
│  │   │   ├── project-health-summary.py (2) — открыть     │  │
│  │   │   ├── mcp_config.py (3) — открыть                 │  │
│  │   │   └── ...                                          │  │
│  │   └── references/                                      │  │
│  │       └── skill-design-spec.md (4) — открыть          │  │
│  └──────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ Editor tabs:                                           │  │
│  │  [SKILL.md] [project-health-summary.py] [mcp_config.py]│  │
│  │  [skill-design-spec.md] [project-architecture.md]      │  │
│  └──────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ ACP Sidebar:                                          │  │
│  │  Chat with Hermes (analyst_training)                  │  │
│  │  [Send: "Привет, контекст: скилл fst-project-health"] │  │
│  └──────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 7.2. Что положить в `cwd:` для контекста

| Поле | Значение |
|---|---|
| `cwd` | `/root/.hermes/profiles/fst-control/skills/productivity/fst-project-health` |
| `args` (extra) | включить путь workspace в prompt |

### 7.3. Файлы для attached-context

```
@Hermes, рабочий контекст:
1. SKILL.md — описание скилла
2. scripts/project-health-summary.py — главный script
3. scripts/mcp_config.py — конфиг MCP
4. scripts/rebuild_report.py — manual rebuild
5. scripts/build_html_report.py — HTML build
6. scripts/build_word_report.py — DOCX build
7. scripts/validate_figma_html.py — FIGMA validator
8. references/skill-design-spec.md — главный spec
9. references/project-architecture.md — архитектура
10. references/html-report-pitfalls.md — известные грабли

НЕ запускай скрипты. Только читай и анализируй.
```

---

## 8. Стоит ли создать специального агента?

### Короткий ответ

**Да, но осторожно.** Предлагаю **новый профиль** `skill-auditor`.

### Концепция: профиль `skill-auditor`

```
/root/.hermes/profiles/skill-auditor/
├── SOUL.md                # специализированный kernel
├── OVERLAY.md             # дополнения
├── skills/
│   ├── 01-skill-anatomy/      # что должно быть в скилле
│   ├── 02-red-flag-scanner/   # поиск уязвимостей
│   ├── 03-code-quality/       # dry, dup, complexity
│   ├── 04-doc-sync/           # SKILL.md vs code
│   ├── 05-references-audit/   # устаревшие refs
│   ├── 06-thresholds-check/   # осмысленность порогов
│   └── 07-playbook-generator/ # генерация playbook
├── memory/
│   └── seed-memory.md
├── config.yaml
└── README.md
```

### Что он умеет

| Возможность | Описание |
|---|---|
| **Anatomy** | Проверить наличие main, error handling, dry-run |
| **Red flags** | os.system, eval, hardcoded creds |
| **Quality** | DRY, complexity, naming |
| **Doc sync** | SKILL.md vs реальный код |
| **References** | Какие устарели |
| **Thresholds** | Осмысленность порогов |
| **Playbook** | Сгенерировать playbook по скиллу |

### Kernel (SOUL.md) — ключевые правила

```markdown
# SOUL.md: skill-auditor

1. READ-ONLY по умолчанию. Ничего не запускать.
2. Любое предложение = evidence (file:line).
3. Каждое "хорошо" с указанием места.
4. Каждое "плохо" с severity + как исправить.
5. Перед любым патчем — спросить "apply?".
6. Помнить: проверяю ЧУЖОЙ код, не свой.
7. Если SKILL.md длиннее 50 KB — предложить разбить.
8. Если references > 20 — предложить индекс.
```

### Плюсы

| Плюс | Описание |
|---|---|
| Изоляция | не загрязняет основной профиль |
| Специализация | качественный анализ |
| Переиспользование | для всех будущих скиллов |
| Аудит-трейл | каждый отчёт — файл |

### Минусы

| Минус | Описание |
|---|---|
| Усилие | нужно создать профиль |
| Контекст | нужен отдельный gateway |
| Drift | SOUL.md может устареть |

### Рекомендация

| Если | То |
|---|---|
| Проверять 1-2 скилла | используй текущий профиль (analyst_training) |
| Проверять 5+ скиллов | создай `skill-auditor` |
| Регулярный аудит | создай `skill-auditor` |
| Один раз | текущий профиль OK |

### Минимальный сценарий (без нового профиля)

```
1. Открыть fst-project-health в VS Code
2. Подключиться к Hermes (analyst_training)
3. Использовать мой playbook выше
4. Получить отчёт
5. Сохранить в /root/skill-audits/fst-project-health.md
```

### Расширенный сценарий (с новым профилем)

```
1. Создать /root/.hermes/profiles/skill-auditor/
2. Настроить SOUL.md + skills
3. Открыть fst-project-health в VS Code
4. Подключиться к Hermes (skill-auditor)
5. Запустить playbook из профиля
6. Получить отчёт с audit-trail
```

### Что НЕ нужно делать

| Не делать | Почему |
|---|---|
| Делать новый gateway сразу | start small |
| Переносить всё в skill-auditor | текущий профиль пока справляется |
| Создавать 10+ новых skills | keep it focused |

### Что нужно сделать

| Шаг | Действие |
|---|---|
| 1 | Сначала проверить fst-project-health текущим профилем |
| 2 | Сохранить отчёт |
| 3 | Через 3 скилла — решить, нужен ли skill-auditor |
| 4 | Если да — создать поэтапно |

---

## 9. Что я НЕ делал

| Действие | Статус |
|---|---|
| ❌ Создавал профиль skill-auditor | не делал |
| ❌ Создавал файлы | не делал |
| ❌ Менял конфиги | не делал |
| ✅ Изучил структуру скилла | сделано |
| ✅ Составил playbook | сделано |

---

## 10. Скажи дальше

| Команда | Что делаю |
|---|---|
| Готов начать аудит | буду задавать вопросы |
| Сохранить playbook | отправлю в Telegram |
| Создать skill-auditor | начну поэтапно |
| Другой скилл | переключусь |

---

*Документ создан 2026-08-09, отправлено через @MMRV_Hermes_bot в Telegram.*
