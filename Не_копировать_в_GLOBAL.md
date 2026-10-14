# Скиллы НЕ для копирования в GLOBAL

> Полный список 35 bundled skills, которые я НЕ рекомендую
> переносить в /root/.hermes/skills/. Будут недоступны в новых профилях
> с флагом --no-skills.
> Дата: 2026-08-09

---

## Как читать этот список

| Столбец | Что значит |
|---|---|
| **Скилл** | bundled скилл |
| **Размер** | место на диске |
| **Почему не рекомендую** | моя причина |
| **Может быть полезен** | если да — для чего |

Если ты решил, что какой-то скилл нужен, скажи — добавлю в скрипт копирования.

---

## 1. 🍎 APPLE (4 скилла) — macOS only

| Скилл | Размер | Почему не рекомендую |
|---|---|---|
| apple/apple-notes | 8K | macOS only, ты на Linux |
| apple/apple-reminders | 8K | macOS only |
| apple/findmy | 8K | macOS only |
| apple/imessage | 8K | macOS only |

**Может быть полезен**: ❌ нет (если ты не перейдёшь на Mac).

---

## 2. 🤖 AUTONOMOUS-AI-AGENTS (4 скилла) — сами агенты

| Скилл | Размер | Почему не рекомендую |
|---|---|---|
| autonomous-ai-agents/codex | 12K | OpenAI Codex — это скилл для работы с Codex CLI |
| autonomous-ai-agents/opencode | 12K | OpenCode — для opencode CLI |
| autonomous-ai-agents/claude-code | 40K | Claude Code — для Claude CLI |
| autonomous-ai-agents/hermes-agent | 80K | **мы и есть Hermes** — self-reference |

**Может быть полезен**:
- `claude-code` — если используешь Claude Code как доп. агента
- `codex` — если используешь OpenAI Codex
- `opencode` — редко
- `hermes-agent` — ❌ нет, self-reference

---

## 3. 🎨 CREATIVE — тяжёлые/специфичные (12 скиллов)

| Скилл | Размер | Почему не рекомендую |
|---|---|---|
| creative/comfyui | 364K | ComfyUI — узкая ниша (Stable Diffusion workflow) |
| creative/popular-web-designs | 964K | Справочник, тяжёлый |
| creative/ascii-video | 344K | ASCII видео в терминале, узкая ниша |
| creative/manim-video | 156K | Математические видео через Manim |
| creative/touchdesigner-mcp | 304K | TouchDesigner — motion graphics |
| creative/p5js | 212K | p5.js sketches в браузере |
| creative/baoyu-infographic | 220K | Инфографика, специфичный стиль |
| creative/claude-design | 32K | Claude Artifacts design |
| creative/humanizer | 40K | Де-аизация текста |
| creative/pretext | 96K | LaTeX Pretext (учебники) |
| creative/songwriting-and-ai-music | 16K | AI музыка |
| creative/design-md | 20K | Дизайн документов |

**Может быть полезен**:
- `humanizer` — если пишешь тексты и хочешь сделать их менее "ИИшными"
- `design-md` — если делаешь design.md документы
- `manim-video` — если делаешь математические видео
- `popular-web-designs` — если часто верстаешь

---

## 4. 💼 PRODUCTIVITY — узкие/тяжёлые (6 скиллов)

| Скилл | Размер | Почему не рекомендую |
|---|---|---|
| productivity/powerpoint | 1.2M | PowerPoint через python-pptx, тяжёлый |
| productivity/notion | 28K | Notion API — если не используешь Notion |
| productivity/airtable | 16K | Airtable — если не используешь Airtable |
| productivity/maps | 64K | Карты (Google Maps API) |
| productivity/teams-meeting-pipeline | 12K | Microsoft Teams meetings |
| productivity/petdex | 8K | Pet tracker, очень специфично |

**Может быть полезен**:
- `powerpoint` — если делаешь .pptx
- `notion` — если используешь Notion как базу знаний
- `airtable` — если используешь Airtable
- `maps` — если работаешь с картами

---

## 5. 🤖 MLOps — тяжёлые (3 скилла)

| Скилл | Размер | Почему не рекомендую |
|---|---|---|
| mlops/evaluation | 156K | Оценка ML моделей |
| mlops/inference | 132K | ML inference пайплайны |
| mlops/models | 116K | Управление ML моделями |

**Может быть полезен**:
- Все три — если работаешь с ML моделями регулярно

---

## 6. 🔬 RESEARCH — узкие (1 скилл)

| Скилл | Размер | Почему не рекомендую |
|---|---|---|
| research/research-paper-writing | 1.5M | Академический стиль, ОЧЕНЬ тяжёлый |

**Может быть полезен**:
- Если пишешь академические статьи

---

## 7. 🎬 MEDIA — специфичные (2 скилла)

| Скилл | Размер | Почему не рекомендую |
|---|---|---|
| media/heartmula | 12K | Музыкальный генератор |
| media/songsee | 8K | Spotify — посмотреть что играет |

**Может быть полезен**:
- `songsee` — если часто работаешь со Spotify

---

## 8. � SMART-HOME — узкая ниша (1 скилл)

| Скилл | Размер | Почему не рекомендую |
|---|---|---|
| smart-home/openhue | 8K | Philips Hue лампы |

**Может быть полезен**:
- Если у тебя Hue лампы

---

## 9. 🐶 DOGFOOD — внутренние Hermes (2 скилла)

| Скилл | Размер | Почему не рекомендую |
|---|---|---|
| dogfood/references | 8K | Внутренний справочник Hermes |
| dogfood/templates | 8K | Внутренние шаблоны Hermes |

**Может быть полезен**:
- ❌ нет, это внутренние для разработки Hermes

---

## 10. 💻 ПУСТЫЕ КАТЕГОРИИ (3)

| Категория | Размер | Почему не рекомендую |
|---|---|---|
| computer-use/ | — | пустая категория |
| yuanbao/ | — | пустая |
| index-cache/ | — | пустая |

---

## Итоговая сводка

| Категория | Не рекомендую | Размер |
|---|---|---|
| apple | 4 | 32K |
| autonomous-ai-agents | 4 | 144K |
| creative (тяжёлые) | 12 | ~2.7M |
| productivity (узкие) | 6 | ~1.4M |
| mlops (тяжёлые) | 3 | ~400K |
| research (research-paper-writing) | 1 | 1.5M |
| media (специфичные) | 2 | 20K |
| smart-home | 1 | 8K |
| dogfood | 2 | 16K |
| пустые категории | 0 | — |
| **ИТОГО** | **35** | **~6.2M** |

---

## Что рекомендую добавить в скрипт копирования

| Если хочешь | Добавляем |
|---|---|
| AI музыку | media/heartmula |
| Spotify | media/songsee |
| PowerPoint | productivity/powerpoint |
| Notion | productivity/notion |
| Airtable | productivity/airtable |
| Карты | productivity/maps |
| ML | mlops/{evaluation,inference,models} |
| Pet tracker | productivity/petdex |
| Teams | productivity/teams-meeting-pipeline |
| De-AI-изация текстов | creative/humanizer |
| design.md | creative/design-md |
| Математические видео | creative/manim-video |
| Учебники LaTeX | creative/pretext |
| Веб-дизайн справочник | creative/popular-web-designs |
| Claude Artifacts | creative/claude-design |
| ASCII видео | creative/ascii-video |
| TouchDesigner | creative/touchdesigner-mcp |
| ComfyUI | creative/comfyui |
| p5.js | creative/p5js |
| Инфографика | creative/baoyu-infographic |
| Академический стиль | research/research-paper-writing |
| Hue лампы | smart-home/openhue |
| Claude Code | autonomous-ai-agents/claude-code |
| Codex | autonomous-ai-agents/codex |
| OpenCode | autonomous-ai-agents/opencode |
| Apple (если перейдёшь на Mac) | apple/* (4 шт) |

---

## Что точно НЕ нужно

| Не копировать | Причина |
|---|---|
| autonomous-ai-agents/hermes-agent | self-reference |
| dogfood/* | внутренние Hermes |
| computer-use/ | пустая |
| yuanbao/ | пустая |
| index-cache/ | пустая |

---

## Скажи

| Команда | Что делаю |
|---|---|
| «Добавь X в список» | пересмотрю рекомендацию |
| «Все ок, копируй 33» | запускай скрипт |
| «Сделай --no-skills профиль» | покажу команду |

---

*Документ создан 2026-08-09, отправлено через @MMRV_Hermes_bot в Telegram.*
