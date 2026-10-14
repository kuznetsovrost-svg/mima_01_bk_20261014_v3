# Hermes Desktop — какой десктоп выбрать

> Версия 1.0 · Источник: [hermes-agent.nousresearch.com/docs](https://hermes-agent.nousresearch.com/docs/)
> Короткая шпаргалка по выбору GUI / IDE / CLI-варианта для Hermes Agent —
> только официальные пути, без сторонних обёрток.

## Оглавление

- [§0. TL;DR](#0-tldr)
- [§1. Hermes Desktop](#1-hermes-desktop-рекомендованный-путь-для-winmacos)
- [§2. ACP Editor Integration](#2-acp-editor-integration-zed-и-совместимые)
- [§3. CLI-only](#3-cli-only-tui--one-shot--серверный-и-олдскульный-путь)
- [§4. Сравнительная таблица](#4-сравнительная-таблица)
- [§5. Рекомендация "что выбрать мне"](#5-рекомендация-что-выбрать-мне)
- [§6. Что Hermes НЕ рекомендует](#6-что-hermes-не-рекомендует-по-состоянию-docs-v2x)
- [§7. Контакты](#7-контакты)

---

## §0. TL;DR

- **Hermes Desktop** — официальный GUI-инсталлятор, ставится на Windows и macOS, в комплекте идёт CLI.
- Если нужна интеграция с редактором, а не отдельное окно — **ACP Editor Integration**: запускаешь `hermes acp`, и редакторы с поддержкой ACP (Zed и совместимые) подключаются к Hermes как к ACP-серверу.
- Если сервер / Linux / WSL2 / Termux / вообще без GUI — чистый CLI: `hermes chat` (TUI) или `hermes chat -q "..."` (one-shot).
- Сторонних GUI-обёрток (типа Continue / Cursor / Windsurf-стиля) Hermes не рекомендует. Вся интеграция — через ACP.

---

## §1. Hermes Desktop (рекомендованный путь для Win/macOS)

**1.1. Что это:**

- GUI-приложение + встроенный CLI в одной установке.
- Скачивается с сайта [hermes-agent.nousresearch.com](https://hermes-agent.nousresearch.com/) (кнопка **Download Desktop** в шапке).
- На главной странице docs: *"To easily install the command-line and desktop applications, download the Hermes Desktop installer from our website and run it."*

**1.2. Когда выбирать:**

- Windows или macOS.
- Хочется "поставил → сразу работает" без `curl`/`iex`.
- Нужен ярлык в меню, иконка, нормальная интеграция с системными нотификациями.
- Не хочется возиться с PowerShell-установщиком.

**1.3. Что внутри (по уверению команды Hermes):**

- Само GUI-приложение.
- `hermes` CLI в `PATH` (тот же бинарь, что и при установке через `install.sh` / `install.ps1`).
- `hermes setup --portal` после установки — единый OAuth на модель + 4 Tool Gateway (web search, image gen, TTS, browser).

**1.4. Чего НЕ делает:**

- Не заменяет ACP — это GUI для чата/управления, а не IDE-интеграция.
- Не идёт на Linux / WSL2 / Android (Termux) — там только CLI-путь.

---

## §2. ACP Editor Integration (Zed, и совместимые)

**2.1. Что это:**

- `hermes acp` запускает Hermes в режиме **ACP-сервера** (Agent Client Protocol, JSON-RPC по stdio).
- Редактор с поддержкой ACP подключается к этому серверу и видит Hermes как агента с полным tool-набором.
- Задокументировано в sidebar: *Integrations → ACP Editor Integration*.

**2.2. Когда выбирать:**

- Уже сидишь в **Zed** (или другом ACP-совместимом редакторе) и хочешь, чтобы Hermes "жил" прямо в его боковой панели.
- Нужна IDE-семантика: выделение кода, send-to-agent, inline diff и т. п. — без копипаста в отдельный TUI.

**2.3. Подключение GitHub Copilot через ACP:**

Это **отдельный** путь. В скилле `hermes-agent` и в таблице провайдеров он указан явно:

| Provider            | Auth     | Key env var                          |
|---------------------|----------|--------------------------------------|
| GitHub Copilot ACP  | External | `COPILOT_CLI_PATH` или Copilot CLI   |

- `hermes model` → выбрать GitHub Copilot. Тогда Hermes стартует поверх Copilot-совместимого CLI.
- ⚠️ **ВАЖНО:** токены `gh auth login` **НЕ** работают для Copilot API. Нужен именно device-code OAuth через Copilot CLI.

**2.4. Если редактора с ACP нет:**

- Используй чистый `hermes chat` в tmux / обычном терминале.
- Не пытайся "прикрутить" Hermes к VSCode через Continue / Cline / Roo Code — это разные стеки, официальной интеграции с ними нет.

---

## §3. CLI-only (TUI / one-shot) — серверный и олдскульный путь

**3.1. Что это:**

- `hermes chat` — интерактивный TUI REPL на `prompt_toolkit`.
- `hermes chat -q "<prompt>"` — одиночный запрос, без TUI. Удобно из скриптов, cron-джобов, других агентов.
- `hermes --resume <id>` / `hermes --continue` — возобновить прошлую сессию.

**3.2. Когда выбирать:**

- Linux / macOS / WSL2 / Android (Termux).
- Удалённый сервер (VPS $5/mo, Daytona, Modal) — там GUI в принципе некуда ставить, а Hermes "говорит" с тобой через Telegram / Matrix / etc.
- CI/CD-пайплайн, автотесты, batch-задачи.
- Когда нужна скриптуемость: `hermes chat -q "..."` в cron / pipeline работает из коробки.

**3.3. Подводный камень PTY:**

- `hermes chat` использует `prompt_toolkit`, а он требует **реальный TTY**. Из `terminal()` напрямую `hermes chat` не запустится корректно (будут проблемы с `\r` vs `\n`).
- Решение — tmux-обёртка:

```bash
tmux new-session -d -s hermes -x 120 -y 40 'hermes chat'
sleep 5
tmux send-keys -t hermes 'сделай X' Enter
sleep 20
tmux capture-pane -t hermes -p | tail -50
```

- Для неинтерактивных задач используй `hermes chat -q "..."` (PTY не нужен, отрабатывает в фоне и возвращает stdout).

---

## §4. Сравнительная таблица

| Вариант                | Платформы           | Когда брать                          | Минусы                            |
|------------------------|---------------------|--------------------------------------|------------------------------------|
| **Hermes Desktop**     | Win, macOS          | GUI, "поставил и работает"           | Нет на Linux / WSL / Termux        |
| `hermes acp` + ACP-IDE | Любая с ACP-IDE     | Уже в Zed / ACP-редакторе            | Зависишь от поддержки ACP в IDE    |
| CLI TUI `hermes chat`  | Все                 | Полный контроль, tmux-автоматизация  | Нужен TTY (tmux или скрипт)        |
| CLI one-shot `-q`      | Все                 | CI/CD, cron, агенты, batch           | Нет интерактивности                |
| Copilot через ACP      | Любая (нужен CLI)   | Уже есть подписка Copilot            | Модели и лимиты Copilot            |

---

## §5. Рекомендация "что выбрать мне"

- Сидишь на Windows/macOS, не хочешь возиться с curl → **Hermes Desktop**.
- Уже работаешь в Zed → `hermes acp` + Zed.
- Linux / сервер / WSL2 / Termux → `hermes chat` (TUI через tmux) или `hermes chat -q "..."` (one-shot в cron/скриптах).
- Есть подписка GitHub Copilot и хочется именно её модели → ACP-Copilot.
- Все остальные сценарии (прод-сервер, агенты-в-агенте, нотификации в Telegram) → CLI one-shot + messaging-gateway.

---

## §6. Что Hermes НЕ рекомендует (по состоянию docs v2.x)

- **Сторонние GUI-обёртки** типа Continue / Cline / Roo Code / Cursor / Windsurf. Hermes — самостоятельный агент, он не плагин в IDE, он **host-процесса**, к которому IDE подключается через ACP.
- **Tight coupling с конкретным редактором.** В отличие от Claude Code (заточен под VSCode) или Codex (CLI + IDE), Hermes по дизайну живёт "везде, где вы его поставили": VPS, GPU-кластер, serverless.
- **Самописные лаунчеры.** Если очень хочется GUI на Linux — оборачивай `hermes chat` в свой скрипт, но это не "рекомендованный путь", а кастом.

---

## §7. Контакты

- Сайт / документация: [hermes-agent.nousresearch.com/docs/](https://hermes-agent.nousresearch.com/docs/)
- Скилл `hermes-agent` (CLI-референс, ACP, providers):
  `~/.hermes/skills/autonomous-ai-agents/hermes-agent/SKILL.md`
- Раздел интеграций в docs: *Integrations → ACP Editor Integration*
- Источник этой карточки: главная страница docs (кнопка **Download Desktop** + секция **Install**).

---

*Конец карточки. Идентично содержимому `DESCOTOPDESKTOP01.txt`, v1.0 от 2026-06-14.*
