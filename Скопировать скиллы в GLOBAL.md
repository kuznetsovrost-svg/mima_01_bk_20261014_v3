# Скопировать скиллы в GLOBAL — рекомендация

> Анализ 68 bundled skills из /usr/local/lib/hermes-agent/skills/
> Дата: 2026-08-09

---

## Цель

Перенести скиллы, нужные ВСЕМ профилям, в `/root/.hermes/skills/`
(global user), чтобы:

1. Создавать новые профили с `--no-skills` (без копирования bundled)
2. Не дублировать bundled скиллы в каждом профиле
3. Экономить место (~7.3M на профиль)
4. Централизованно обновлять через global

---

## Архитектура

```
/usr/local/lib/hermes-agent/skills/    (system bundled, read-only)
                                       ↓ seed_profile_skills() при create
                                       ↓
/root/.hermes/profiles/<X>/skills/    (копия в профиль)

/root/.hermes/skills/                  (global user, доступно всем)
                                       ↓ SKILLS_DIR = HERMES_HOME/skills
                                       ↓
                                       доступно ВСЕМ профилям
```

---

## 1. Скиллы, которые НУЖНЫ ВСЕМ (перенести в global)

### 🎨 Creative — рисование и визуализация

| Скилл | Размер | Зачем всем |
|---|---|---|
| creative/excalidraw | 48K | диаграммы в .excalidraw |
| creative/architecture-diagram | 32K | C4, архитектурные диаграммы |
| creative/ascii-art | 16K | ASCII диаграммы в коде |
| creative/sketch | 16K | эскизы |

**Копировать**: `cp -r /usr/local/lib/hermes-agent/skills/creative/{excalidraw,architecture-diagram,ascii-art,sketch} /root/.hermes/skills/creative/`

### 👨‍💻 Software development — разработка

| Скилл | Размер | Зачем всем |
|---|---|---|
| software-development/plan | 16K | планирование задач |
| software-development/test-driven-development | 16K | TDD |
| software-development/systematic-debugging | 20K | debug методика |
| software-development/simplify-code | 16K | упрощение кода |
| software-development/spike | 16K | spike / research |
| software-development/requesting-code-review | 16K | как просить ревью |
| software-development/hermes-agent-skill-authoring | 16K | создание скиллов |
| software-development/python-debugpy | 20K | Python debugger |

**Копировать**: `cp -r /usr/local/lib/hermes-agent/skills/software-development/* /root/.hermes/skills/software-development/`

### � GitHub — работа с git

| Скилл | Размер | Зачем всем |
|---|---|---|
| github/github-pr-workflow | 44K | PR workflow |
| github/github-code-review | 28K | code review |
| github/github-issues | 28K | issues |
| github/github-repo-management | 32K | repo management |
| github/github-auth | 20K | auth |
| github/codebase-inspection | 8K | инспекция кодовой базы |

**Копировать**: `cp -r /usr/local/lib/hermes-agent/skills/github/* /root/.hermes/skills/github/`

### 📝 Productivity — продуктивность

| Скилл | Размер | Зачем всем |
|---|---|---|
| productivity/ocr-and-documents | 28K | OCR документов |
| productivity/nano-pdf | 8K | работа с PDF |
| productivity/google-workspace | 104K | Google Docs/Sheets |

**Копировать**: `cp -r /usr/local/lib/hermes-agent/skills/productivity/{ocr-and-documents,nano-pdf,google-workspace} /root/.hermes/skills/productivity/`

### 🔬 Research — исследования

| Скилл | Размер | Зачем всем |
|---|---|---|
| research/arxiv | 28K | поиск статей на arxiv |
| research/llm-wiki | 24K | LLM knowledge base |
| research/blogwatcher | 12K | мониторинг блогов |
| research/polymarket | 36K | prediction markets |

**Копировать**: `cp -r /usr/local/lib/hermes-agent/skills/research/{arxiv,llm-wiki,blogwatcher,polymarket} /root/.hermes/skills/research/`

### 🎬 Media — работа с медиа

| Скилл | Размер | Зачем всем |
|---|---|---|
| media/youtube-content | 24K | работа с YouTube |
| media/gif-search | 8K | поиск GIF |

**Копировать**: `cp -r /usr/local/lib/hermes-agent/skills/media/{youtube-content,gif-search} /root/.hermes/skills/media/`

### 🤖 MLOps — ML операции

| Скилл | Размер | Зачем всем |
|---|---|---|
| mlops/huggingface-hub | 8K | Hugging Face |

**Копировать**: `cp -r /usr/local/lib/hermes-agent/skills/mlops/huggingface-hub /root/.hermes/skills/mlops/`

### 📝 Note-taking — заметки

| Скилл | Размер | Зачем всем |
|---|---|---|
| note-taking/obsidian | 8K | Obsidian vault |

**Копировать**: `cp -r /usr/local/lib/hermes-agent/skills/note-taking/obsidian /root/.hermes/skills/note-taking/`

### 📧 Email — почта

| Скилл | Размер | Зачем всем |
|---|---|---|
| email/himalaya | 28K | email клиент (CLI) |

**Копировать**: `cp -r /usr/local/lib/hermes-agent/skills/email/himalaya /root/.hermes/skills/email/`

### 📱 Social media — соцсети

| Скилл | Размер | Зачем всем |
|---|---|---|
| social-media/xurl | 20K | Twitter URL utilities |

**Копировать**: `cp -r /usr/local/lib/hermes-agent/skills/social-media/xurl /root/.hermes/skills/social-media/`

### 📊 Data science — данные

| Скилл | Размер | Зачем всем |
|---|---|---|
| data-science/jupyter-live-kernel | 12K | Jupyter kernel |

**Копировать**: `cp -r /usr/local/lib/hermes-agent/skills/data-science/jupyter-live-kernel /root/.hermes/skills/data-science/`

---

## 2. Скиллы, которые НЕ нужны всем (НЕ переносить)

### 🍎 Apple-специфичные — ты на Linux

| Скилл | Размер | Почему не нужен |
|---|---|---|
| apple/apple-notes | 8K | macOS only |
| apple/apple-reminders | 8K | macOS only |
| apple/findmy | 8K | macOS only |
| apple/imessage | 8K | macOS only |

**Не копировать** — не работает на Linux.

### 🏠 Smart home — не у всех есть умный дом

| Скилл | Размер | Почему |
|---|---|---|
| smart-home/openhue | 8K | Philips Hue, узкая ниша |

**Не копировать** — узкая ниша.

### 💴 yuanbao — китайская валюта

| Скилл | Размер | Почему |
|---|---|---|
| yuanbao/ | — | (категория пустая) |

**Не копировать**.

### 💻 computer-use — управление компьютером

| Скилл | Размер | Почему |
|---|---|---|
| computer-use/ | — | (категория пустая) |

**Не копировать**.

### 🤖 autonomous-ai-agents — специфичные агенты

| Скилл | Размер | Почему |
|---|---|---|
| autonomous-ai-agents/codex | 12K | OpenAI Codex, дубликат |
| autonomous-ai-agents/opencode | 12K | OpenCode |
| autonomous-ai-agents/claude-code | 40K | Claude Code |
| autonomous-ai-agents/hermes-agent | 80K | Hermes — мы и есть Hermes |

**Не копировать** — это сами агенты, не нужны как скиллы внутри.

### 🎨 Creative — тяжёлые и узкие

| Скилл | Размер | Почему |
|---|---|---|
| creative/comfyui | 364K | узкая ниша, тяжёлый |
| creative/popular-web-designs | 964K | справочник, тяжёлый |
| creative/ascii-video | 344K | узкая ниша |
| creative/manim-video | 156K | математические видео |
| creative/touchdesigner-mcp | 304K | TouchDesigner, узкая ниша |
| creative/p5js | 212K | p5.js, специфично |
| creative/baoyu-infographic | 220K | инфографика, специфично |
| creative/claude-design | 32K | специфично |
| creative/humanizer | 40K | специфично |
| creative/pretext | 96K | LaTeX pretext, специфично |
| creative/songwriting-and-ai-music | 16K | музыка, узкая ниша |
| creative/design-md | 20K | дизайн документов |

**Не копировать** — специфичные задачи.

### 💼 Productivity — тяжёлые и узкие

| Скилл | Размер | Почему |
|---|---|---|
| productivity/powerpoint | 1.2M | PowerPoint, тяжёлый |
| productivity/notion | 28K | Notion API, специфично |
| productivity/airtable | 16K | Airtable |
| productivity/maps | 64K | карты, специфично |
| productivity/teams-meeting-pipeline | 12K | Teams meetings |
| productivity/petdex | 8K | питомцы, очень специфично |

**Не копировать** — узкие ниши или тяжёлые.

### 🤖 MLOps — тяжёлые

| Скилл | Размер | Почему |
|---|---|---|
| mlops/evaluation | 156K | оценка моделей, тяжёлый |
| mlops/inference | 132K | inference, тяжёлый |
| mlops/models | 116K | модели, тяжёлый |

**Не копировать** — тяжёлые, не всем нужны.

### 🔬 Research — специфичные

| Скилл | Размер | Почему |
|---|---|---|
| research/research-paper-writing | 1.5M | академический стиль, тяжёлый |

**Не копировать** — большой и узкоспециализированный.

### 🎬 Media — специфичные

| Скилл | Размер | Почему |
|---|---|---|
| media/heartmula | 12K | генератор, специфично |
| media/songsee | 8K | Spotify, специфично |

**Не копировать**.

### 🐶 Dogfood — внутренние

| Скилл | Размер | Почему |
|---|---|---|
| dogfood/references | 8K | внутренний справочник Hermes |
| dogfood/templates | 8K | внутренние шаблоны |

**Не копировать** — внутренние для Hermes.

---

## 3. Сводная таблица

| Категория | Всего bundled | Перенести в global | Не переносить |
|---|---|---|---|
| apple | 4 | 0 | 4 |
| autonomous-ai-agents | 4 | 0 | 4 |
| computer-use | 0 | 0 | 0 |
| creative | 16 | 4 | 12 |
| data-science | 1 | 1 | 0 |
| dogfood | 2 | 0 | 2 |
| email | 1 | 1 | 0 |
| github | 6 | 6 | 0 |
| index-cache | 0 | 0 | 0 |
| media | 4 | 2 | 2 |
| mlops | 4 | 1 | 3 |
| note-taking | 1 | 1 | 0 |
| productivity | 9 | 3 | 6 |
| research | 5 | 4 | 1 |
| smart-home | 1 | 0 | 1 |
| social-media | 1 | 1 | 0 |
| software-development | 9 | 9 | 0 |
| yuanbao | 0 | 0 | 0 |
| **ИТОГО** | **68** | **33** | **35** |

---

## 4. Готовый скрипт

```bash
#!/bin/bash
# copy-to-global.sh
# Копирует 33 универсальных скилла из bundled в global user

set -e

SRC=/usr/local/lib/hermes-agent/skills
DST=/root/.hermes/skills

# Создать структуру
mkdir -p $DST/{creative,software-development,github,productivity,research,media,mlops,note-taking,email,social-media,data-science}

# Creative (4)
cp -r $SRC/creative/excalidraw $DST/creative/
cp -r $SRC/creative/architecture-diagram $DST/creative/
cp -r $SRC/creative/ascii-art $DST/creative/
cp -r $SRC/creative/sketch $DST/creative/

# Software development (9 — все)
for skill in plan test-driven-development systematic-debugging simplify-code               spike requesting-code-review hermes-agent-skill-authoring               python-debugpy node-inspect-debugger; do
    cp -r $SRC/software-development/$skill $DST/software-development/
done

# GitHub (6 — все)
for skill in github-pr-workflow github-code-review github-issues               github-repo-management github-auth codebase-inspection; do
    cp -r $SRC/github/$skill $DST/github/
done

# Productivity (3)
cp -r $SRC/productivity/ocr-and-documents $DST/productivity/
cp -r $SRC/productivity/nano-pdf $DST/productivity/
cp -r $SRC/productivity/google-workspace $DST/productivity/

# Research (4)
cp -r $SRC/research/arxiv $DST/research/
cp -r $SRC/research/llm-wiki $DST/research/
cp -r $SRC/research/blogwatcher $DST/research/
cp -r $SRC/research/polymarket $DST/research/

# Media (2)
cp -r $SRC/media/youtube-content $DST/media/
cp -r $SRC/media/gif-search $DST/media/

# MLOps (1)
cp -r $SRC/mlops/huggingface-hub $DST/mlops/

# Note-taking (1)
cp -r $SRC/note-taking/obsidian $DST/note-taking/

# Email (1)
cp -r $SRC/email/himalaya $DST/email/

# Social media (1)
cp -r $SRC/social-media/xurl $DST/social-media/

# Data science (1)
cp -r $SRC/data-science/jupyter-live-kernel $DST/data-science/

echo "Copied 33 skills to global user location"
ls -la $DST/
```

---

## 5. Создание новых профилей после переноса

```bash
# Теперь можно создавать профили без bundled skills
hermes profile create coder --no-skills
hermes profile create writer --no-skills
hermes profile create analyst --no-skills

# Все они получат доступ к 33 global user skills через SKILLS_DIR
```

---

## 6. Что будет доступно в новом профиле

| Источник | Количество | Размер |
|---|---|---|
| Global user (после переноса) | 33 + 32 = **65** | ~1.5M |
| Profile-specific | 0 | 0 |
| Bundled в профиле | 0 | 0 |

**Итого 65 скиллов** в новом профиле `--no-skills`.

---

## 7. Экономия

| Что | До | После |
|---|---|---|
| Размер скиллов в профиле | ~7.3M (68 bundled) | ~1.5M (65 global) |
| Дубликаты | да | нет |
| Время создания профиля | долго (копирование) | быстро (--no-skills) |

---

## 8. ⚠️ Что важно

1. **Сначала копируем** bundled в global
2. **Потом создаём** новые профили с `--no-skills`
3. **Старые профили** (analyst_training, fst-control) можно почистить позже

## 9. Скажи

| Команда | Что делаю |
|---|---|
| Запустить скрипт | скопирую 33 скилла |
| Создать 5 профилей с --no-skills | пустые + global |
| Только список | без действий |

---

*Документ создан 2026-08-09, отправлено через @MMRV_Hermes_bot в Telegram.*
