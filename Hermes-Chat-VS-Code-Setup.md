# Hermes Agent Chat (poppywu124.hermes-chat) — документация и настройка

> Источники: VS Code Marketplace, GitHub `Narizis/hermes-chat-vscode`,
> package.json, README.md (HEAD = main).
> Дата: 2026-08-09

---

## 1. Краткая карточка расширения

| Параметр | Значение |
|---|---|
| **Publisher** | Poppywu124 |
| **Extension ID** | poppywu124.hermes-chat |
| **Display name** | Hermes Agent Chat |
| **Marketplace** | marketplace.visualstudio.com/items?itemName=poppywu124.hermes-chat |
| **Repo** | github.com/Narizis/hermes-chat-vscode |
| **License** | MIT |
| **Version** | 0.7.1 |
| **engines.vscode** | ^1.80.0 |
| **GitHub stars** | 12 |
| **GitHub forks** | 8 |
| **Created** | 2026-04-19 |
| **Last commit** | 2026-07-30 |
| **Language** | TypeScript |
| **Categories** | AI, Chat |
| **Activation** | onStartupFinished |

---

## 2. Что это такое

Это **VS Code extension для работы с Hermes Agent** через ACP. Это **НЕ** ещё
один агент — это **frontend** для уже установленного Hermes CLI. Расширение
запускает `hermes acp` под капотом и показывает диалог в боковой панели.

Цитата из README:

> "Persistent multi-agent Hermes chat with streaming ACP tools, workspace
> context, per-agent settings, memory, and history."

> "This extension does not bundle Hermes Agent. It is a VS Code frontend for
> a local Hermes CLI installation."

### Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│ VS Code                                                      │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ Hermes Agent Chat (extension.js)                     │    │
│  │   ↑ JSON-RPC over ACP (stdio)                       │    │
│  └──────┬───────────────────────────────────────────────┘    │
└─────────┼───────────────────────────────────────────────────┘
          │ запускает `hermes acp`
┌─────────┴───────────────────────────────────────────────────┐
│ Local Hermes CLI                                             │
│  - agent pipeline                                            │
│  - tools, skills, memory, cron                               │
│  - configured MCP servers                                    │
└─────────────────────────────────────────────────────────────┘
```

**Важно**: расширение работает только локально. Hermes CLI должен быть
**уже установлен** на той же машине, где запущен VS Code.

---

## 3. Требования

| Компонент | Зачем |
|---|---|
| **Hermes CLI** | real runtime, без него расширение бесполезно |
| **Hermes в PATH** | либо указать `hermes-chat.hermesPath` |
| **VS Code 1.80+** | версия движка |
| **API key** | для LLM провайдера |

### Проверка перед установкой

```bash
hermes doctor       # диагностика Hermes
hermes version      # версия
hermes acp          # проверить что ACP mode работает
```

Если `hermes` не в PATH:
- macOS / Linux: добавить в `~/.bashrc` / `~/.zshrc`
- Windows: добавить в PATH или указать `hermes-chat.hermesPath` в settings

---

## 4. Установка

### Шаг 1. Установить Hermes CLI (если ещё нет)

> На mima_g_01 Hermes **уже установлен** и готов. У нас:
> - `hermes acp` работает
> - venv: `/usr/local/lib/hermes-agent/venv/`
> - binary: `/usr/local/lib/hermes-agent/venv/bin/hermes-acp`

### Шаг 2. Установить расширение

#### Вариант A: через UI

1. Открыть VS Code
2. Extensions (Ctrl+Shift+X)
3. Поиск: `Hermes Agent Chat` или `poppywu124.hermes-chat`
4. Install

#### Вариант B: через CLI

```powershell
# Windows PowerShell
code --install-extension poppywu124.hermes-chat
```

### Шаг 3. Настроить `hermesPath`

Если `hermes` НЕ в PATH (например, ты работаешь через Remote-SSH):

```json
// settings.json
{
  "hermes-chat.hermesPath": "/usr/local/lib/hermes-agent/venv/bin/hermes-acp"
}
```

> **Важный нюанс про Remote-SSH**: расширение запускает Hermes **на той же машине,
> где работает VS Code**. Если ты в Remote-SSH к mima_g_01, нужно либо
> установить Hermes локально на Windows, либо использовать
> `strato-space.acp-plugin` (универсальный ACP клиент).

---

## 5. Первый запуск

### Где найти

После установки в **Activity Bar** (иконка слева) появится вкладка **Hermes Agent**.

### Workflow

1. Клик на **Hermes Agent** в Activity Bar
2. Выбор агента (agent picker)
3. Прикрепить файлы workspace
4. Отправить сообщение

Альтернативно через Command Palette (Ctrl+Shift+P):

| Команда | Что |
|---|---|
| `Hermes: New Session` | начать новый чат |
| `Hermes: Open Chat in Panel` | открыть в панели |
| `Hermes: Clear Chat Display` | очистить визуально |
| `Hermes: Get API Key (Ace Data Cloud)` | получить ключ |

---

## 6. Настройки (`settings.json`)

| Setting | Default | Что |
|---|---|---|
| `hermes-chat.hermesPath` | `hermes` | путь к Hermes CLI |
| `hermes-chat.timeout` | `30` | таймаут для control requests |
| `hermes-chat.streamIdleTimeout` | `120` | idle timeout между чанками stream |
| `hermes-chat.autoApproveTools` | `false` | авто-approve tool requests |

### Минимальный конфиг

```json
{
  "hermes-chat.hermesPath": "hermes",
  "hermes-chat.timeout": 30,
  "hermes-chat.streamIdleTimeout": 120,
  "hermes-chat.autoApproveTools": false
}
```

### Если Hermes через SSH

```json
{
  "hermes-chat.hermesPath": "/usr/local/lib/hermes-agent/venv/bin/hermes-acp"
}
```

### ⚠️ Безопасность

| Setting | Риск |
|---|---|
| `autoApproveTools: true` | tools выполняются без подтверждения |
| `hermesPath: <untrusted>` | может выполнить чужой бинарник |

**Рекомендация**: `autoApproveTools: false` пока не доверяешь агенту.

---

## 7. Ключевые фичи

| Возможность | Поддержка |
|---|---|
| Persistent isolated agents | да |
| Blank or cloned agent creation | да |
| Per-agent provider and model settings | да |
| Per-agent chat history и session resume | да |
| Streaming ACP responses | да |
| Tool call и permission visibility | да |
| Active file и selection context | да |
| Workspace file attachments | да |
| Personality и memory file access | да |
| Token usage tracking | да |

### Multi-agent поддержка

Главная фишка — можно создать **несколько изолированных агентов** с разными:

- моделями (Claude, GPT, Gemini, etc.)
- personality
- memory
- history
- session

Каждый агент = отдельный профиль. Можно иметь:
- `coder` для программирования
- `analyst` для аналитики
- `writer` для текстов
- `reviewer` для код-ревью

### Workspace context

Автоматически подтягивает:
- **active file** (что открыто)
- **selection** (что выделено)
- **attached files** (через file picker)

То есть если ты выделил функцию и спросил "explain", агент получит
этот код в контексте.

---

## 8. Как это работает под капотом

### Подключение

1. Расширение активируется (`onStartupFinished`)
2. Открывает процесс `hermes acp`
3. Связь идёт через **JSON-RPC over ACP** (stdio)
4. Сообщения проходят через полный pipeline Hermes:
   - memory
   - tools
   - skills
   - cron jobs
   - MCP servers

### Что НЕ меняется

Это **только UI**. Вся работа делается через `hermes acp`, как и в CLI.
Skills, tools, prompts — всё что настроено в Hermes, доступно из VS Code.

---

## 9. Совместимость с нашим setup

### На mima_g_01 у нас

| Компонент | Статус |
|---|---|
| Hermes CLI | установлен |
| `hermes-acp` binary | `/usr/local/lib/hermes-agent/venv/bin/hermes-acp` |
| `hermes acp` | работает |
| Active profile | `analyst_training` |
| Multiple profiles | есть (`default`, `analyst_training`, `fst-control`) |

### Сценарий A: ты работаешь в Remote-SSH

**Вопрос**: Расширение запускает Hermes **локально** на Windows. Если ты в
Remote-SSH к mima_g_01, расширение **не найдёт** Hermes на Windows.

**Решение A.1**: поставить Hermes локально на Windows (нативный пакет или WSL).

**Решение A.2**: использовать `strato-space.acp-plugin` (универсальный ACP).

**Решение A.3**: SSH-туннель + ручной запуск Hermes.

### Сценарий B: ты работаешь локально на Windows

Если ты подключаешься **напрямую** через `ssh root@mima_g_01` и редактируешь
файлы через VS Code Remote, расширение всё равно запустит Hermes **локально**.

### Сценарий C: VS Code на mima_g_01 (через VNC/X11)

Тогда расширение запустит Hermes **на mima_g_01** — это работает.

---

## 10. Подробная настройка для твоего случая

### Способ 1: Полностью локальный Hermes на Windows

```
1. Установить Hermes CLI на Windows
   (native binary или WSL или Docker)

2. Настроить `~/.hermes/.env`  
   (TELEGRAM_BOT_TOKEN, FIGMA_PERSONAL_ACCESS_TOKEN, etc.)

3. Установить расширение
   code --install-extension poppywu124.hermes-chat

4. Запустить Hermes в режиме ACP
   hermes acp

5. Открыть VS Code, найти Hermes Agent в Activity Bar
```

### Способ 2: SSH-туннель (обходной путь)

```powershell
# Windows PowerShell
ssh -L 3284:127.0.0.1:3284 root@mima_g_01
```

Не поможет, потому что расширение запускает `hermes acp` локально.

### Способ 3: VS Code Remote + удаленный Hermes

```
1. Открыть VS Code Remote к mima_g_01
2. Установить расширение **в remote VS Code** (Remotes)
   - Extensions view → "Install in SSH: mima_g_01"
3. Расширение запустит Hermes на mima_g_01
```

**Это лучший вариант для тебя.**

---

## 11. API ключ (Ace Data Cloud)

Расширение предлагает **Ace Data Cloud** — один ключ для 50+ моделей.

| Модель | Через Ace Data Cloud |
|---|---|
| GPT-4o | да |
| Claude Sonnet/Opus | да |
| Gemini | да |
| DeepSeek | да |
| Grok | да |

Минусы:
- pay-as-you-go (не бесплатно после trial)
- OpenAI-compatible endpoint
- Данные идут через их прокси

**Альтернатива**: указать свой провайдер в Hermes config (`providers.yaml`).

---

## 12. Возможные проблемы

### Расширение не активируется

| Причина | Решение |
|---|---|
| `hermes` не в PATH | указать `hermes-chat.hermesPath` |
| Hermes не запускается | `hermes doctor` |
| Старая версия VS Code | обновить до 1.80+ |

### Stream рвётся

| Причина | Решение |
|---|---|
| Долгое thinking модели | увеличить `streamIdleTimeout` |
| Сложный tool call | меньше файлов в контексте |
| Сетевые проблемы | проверить endpoint |

### Tool approval запрашивает постоянно

| Причина | Решение |
|---|---|
| `autoApproveTools: false` | это by design, проверять каждый tool |
| Нет доверия | сначала approve, потом включить true |

---

## 13. Сравнение с альтернативами

| Расширение | Поддержка Hermes native | Multi-agent | Streaming | Контекст |
|---|---|---|---|---|
| **poppywu124.hermes-chat** | да | да | да | full |
| strato-space.acp-plugin | через ACP | нет | да | manual |
| joaompfp.hermes-ai-agent | да | да | да | full |
| Continue.continue | generic | да | да | full |
| Cline | generic | нет | да | full |

**poppywu124.hermes-chat** — лучший выбор для Hermes, потому что:
1. Нативная поддержка Hermes CLI
2. Multi-agent profiles
3. Per-agent settings
4. Streaming ACP
5. Workspace context

---

## 14. Структура репозитория (для аудита)

```
Narizis/hermes-chat-vscode/
├── README.md
├── LICENSE (MIT)
├── CHANGELOG.md
├── package.json          # манифест расширения
├── tsconfig.json
├── .github/
├── .vscode/
├── .vscodeignore
├── docs/
├── media/screenshots/    # PNG скриншоты
├── src/                  # TypeScript код
├── worker/
├── test/
├── icon.png
└── icon.svg
```

---

## 15. Что я рекомендую

### Для твоего случая (Remote-SSH к mima_g_01)

| Шаг | Действие |
|---|---|
| 1 | Remote-SSH подключение к mima_g_01 |
| 2 | Установить расширение **в remote VS Code** |
| 3 | Проверить `hermes acp` работает на mima_g_01 |
| 4 | Открыть Hermes Agent в Activity Bar |
| 5 | Создать первого агента (agent picker → "Create New") |
| 6 | Настроить provider/model в Settings |
| 7 | Прикрепить файл workspace |
| 8 | Отправить тестовое сообщение |

### Конфиг для твоего workflow

```json
{
  "hermes-chat.hermesPath": "/usr/local/lib/hermes-agent/venv/bin/hermes-acp",
  "hermes-chat.timeout": 60,
  "hermes-chat.streamIdleTimeout": 180,
  "hermes-chat.autoApproveTools": false
}
```

---

## 16. Главная мысль

> **poppywu124.hermes-chat** — это **только UI** для уже установленного Hermes.
> Лучше всего работает в Remote-SSH режиме, когда VS Code и Hermes на одной
> машине (mima_g_01). Если ты в Remote-SSH, устанавливай расширение в remote
> VS Code, а не локально на Windows иначе оно не найдёт Hermes.

---

## 17. Скажи дальше

| Команда | Что делаю |
|---|---|
| Установить расширение | дам точные команды |
| Создать первого агента | пошагово |
| Объясни multi-agent | детали по профилям |
| Настроить provider | конкретный endpoint |
| Аудит кода расширения | read-only анализ src/ |

---

## 18. Источники

- https://marketplace.visualstudio.com/items?itemName=poppywu124.hermes-chat
- https://github.com/Narizis/hermes-chat-vscode
- https://raw.githubusercontent.com/Narizis/hermes-chat-vscode/main/README.md
- https://raw.githubusercontent.com/Narizis/hermes-chat-vscode/main/package.json
- https://github.com/hermes-agent/hermes

---

*Документ создан 2026-08-09, отправлено через @MMRV_Hermes_bot в Telegram.*
