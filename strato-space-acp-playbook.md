# strato-space.acp-plugin — playbook использования

> Универсальный ACP клиент для VS Code с SSH-подключением к удалённому Hermes.
> Источник: github.com/strato-space/acp-plugin, marketplace.visualstudio.com.
> Дата: 2026-08-09

---

## 1. Краткая карточка

| Параметр | Значение |
|---|---|
| **Publisher** | strato-space |
| **Extension ID** | strato-space.acp-plugin |
| **Display name** | ACP — Agent Client Protocol |
| **Marketplace** | marketplace.visualstudio.com/items?itemName=strato-space.acp-plugin |
| **Repo** | github.com/strato-space/acp-plugin |
| **License** | Apache 2.0 |
| **Stars / Forks** | 8 / 0 |
| **Created** | 2026-02-09 |
| **Last commit** | 2026-06-30 |
| **Стек** | TypeScript + React (monorepo) |

### Главная фишка

> "ACP is the protocol. This repository ships a **client** (VS Code extension + optional web UI)."

Это **универсальный клиент** для **любого** ACP-совместимого агента.
В отличие от `poppywu124.hermes-chat`, **не привязан** к Hermes CLI.

---

## 2. Зачем тебе это расширение

### Сравнение с poppywu124.hermes-chat

| Критерий | poppywu124.hermes-chat | strato-space.acp-plugin |
|---|---|---|
| Привязка к Hermes CLI | да (только Hermes) | нет (любой ACP агент) |
| Работает через SSH | нет (только local) | да (command = ssh) |
| Multi-agent | только профили Hermes | любые агенты |
| Built-in presets | нет | 9 штук |
| Формат конфига | native | Zed-compatible `agent_servers` |
| Установка | в remote VS Code | работает откуда угодно |

### Главное преимущество для тебя

> **Ты можешь подключаться к Hermes на mima_g_01 через SSH прямо из VS Code
> на Windows.** Не нужно ставить расширение в remote VS Code.

```
VS Code (Windows) → ssh root@mima_g_01 → hermes-acp → ...
```

---

## 3. Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│ VS Code (Windows)                                            │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ strato-space.acp-plugin (extension)                  │    │
│  │   ↑ JSON-RPC over ACP (stdio)                       │    │
│  │   ↓ spawn process via `command`                     │    │
│  └──────┬───────────────────────────────────────────────┘    │
│         │                                                     │
│         │ ssh root@mima_g_01 /usr/local/lib/.../hermes-acp    │
└─────────┼─────────────────────────────────────────────────────┘
          │ SSH
┌─────────┴───────────────────────────────────────────────────┐
│ mima_g_01                                                    │
│  hermes-acp (ACP mode)                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Установка

### Вариант A: через Marketplace

```powershell
# Windows PowerShell
code --install-extension strato-space.acp-plugin
```

Или:
1. Открыть VS Code
2. Extensions (Ctrl+Shift+X)
3. Поиск: `ACP — Agent Client Protocol`
4. Install

### Вариант B: через VSIX (локально)

```bash
# Если нужна specific версия
git clone https://github.com/strato-space/acp-plugin
cd acp-plugin
npm ci
npm run package
npx vsce package --no-dependencies
code --install-extension ./acp-plugin-<version>.vsix --force
```

> **Активация**: `onStartupFinished` — расширение стартует при запуске VS Code.

---

## 5. Настройка для твоего случая (Windows → mima_g_01)

### Шаг 1. Открыть Settings

- `Ctrl+,` → Search: `acp`
- Или: `Ctrl+Shift+P` → `Preferences: Open User Settings (JSON)`

### Шаг 2. Добавить конфигурацию агента

Открой `settings.json` (Ctrl+Shift+P → Open User Settings JSON) и добавь:

```json
{
  "acp.agents": {
    "hermes-mima": {
      "type": "custom",
      "name": "Hermes on mima_g_01",
      "command": "ssh",
      "args": [
        "root@mima_g_01",
        "/usr/local/lib/hermes-agent/venv/bin/hermes-acp"
      ],
      "cwd": "${workspaceFolder}",
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  },
  "acp.includeBuiltInAgents": true,
  "acp.connectTimeoutMs": 600000,
  "acp.autoApprovePermissions": "ask",
  "acp.defaultWorkingDirectory": "",
  "acp.logTraffic": true
}
```

### Шаг 3. Альтернативный формат (Zed-compatible)

Можно использовать `agent_servers` (предпочитаемый формат):

```json
{
  "agent_servers": {
    "hermes-mima": {
      "type": "custom",
      "name": "Hermes on mima_g_01",
      "command": "ssh",
      "args": [
        "root@mima_g_01",
        "/usr/local/lib/hermes-agent/venv/bin/hermes-acp"
      ],
      "cwd": "${workspaceFolder}",
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

> `acp.agents` — alias для upstream совместимости.
> `agent_servers` — Zed-style, корневой формат.

### Шаг 4. Убедиться что SSH работает

```powershell
ssh root@mima_g_01 /usr/local/lib/hermes-agent/venv/bin/hermes-acp --check
```

Ожидаемый вывод: `Hermes ACP check OK`.

### Шаг 5. Перезапустить VS Code

Расширение активируется при старте.

---

## 6. Настройки (полная таблица)

| Setting | Default | Что |
|---|---|---|
| `agent_servers` | `{}` | Главная конфигурация агентов (Zed-style) |
| `acp.agents` | `{}` | Alias для upstream |
| `acp.includeBuiltInAgents` | `true` | Включить встроенные пресеты |
| `acp.connectTimeoutMs` | `600000` | Таймаут подключения (ms) |
| `acp.autoApprovePermissions` | `ask` | `ask` или `allowAll` |
| `acp.defaultWorkingDirectory` | `""` | Рабочая директория по умолчанию |
| `acp.logTraffic` | `true` | Логировать JSON-RPC traffic |

### Merging правила

| Scope | Приоритет |
|---|---|
| Global settings | низший |
| Workspace settings | средний |
| Workspace-folder settings | высший |

---

## 7. Переменные в конфигурации

| Placeholder | Что подставляется |
|---|---|
| `${workspaceFolder}` | текущая рабочая папка |
| `${userHome}` | домашняя директория |
| `${env:NAME}` | значение env переменной NAME |

### Пример с переменными

```json
{
  "agent_servers": {
    "hermes-mima": {
      "command": "ssh",
      "args": [
        "root@mima_g_01",
        "/usr/local/lib/hermes-agent/venv/bin/hermes-acp",
        "--workspace",
        "${workspaceFolder}"
      ],
      "env": {
        "HERMES_PROFILE": "${env:HERMES_PROFILE:-analyst_training}"
      }
    }
  }
}
```

---

## 8. Первый запуск

### Где найти

1. **Activity Bar** (боковая панель) → иконка **ACP**
2. Клик → открывается вьюха
3. Кнопка **"Open Chat"**
4. Settings (gear icon) → выбрать агента
5. **Connect** → начать чат

### Через Command Palette

`Ctrl+Shift+P` → `ACP: Connect` → выбрать `hermes-mima` → чат открывается.

### В Output Channel

`Ctrl+Shift+U` → `ACP Traffic` — там видны все JSON-RPC сообщения
(если `acp.logTraffic: true`).

---

## 9. Built-in агенты (если `acp.includeBuiltInAgents: true`)

| ID | Name | Default command |
|---|---|---|
| `codex` | Codex CLI | `npx --yes @zed-industries/codex-acp@latest` |
| `fast-agent-acp` | Fast Agent ACP | `uvx fast-agent-acp --shell --model codex` |
| `github-copilot` | GitHub Copilot | `npx --yes @github/copilot-language-server@latest --acp` |
| `claude-code` | Claude Code | `npx --yes @zed-industries/claude-code-acp@latest` |
| `gemini` | Gemini CLI | `npx --yes @google/gemini-cli@latest --experimental-acp` |
| `qwen-code` | Qwen Code | `npx --yes @qwen-code/qwen-code@latest --acp --experimental-skills` |
| `auggie` | Auggie CLI | `npx --yes @augmentcode/auggie@latest --acp` |
| `qoder` | Qoder CLI | `npx --yes @qoder-ai/qodercli@latest --acp` |
| `opencode` | OpenCode | `npx --yes opencode-ai@latest acp` |

> **Важно**: эти `npx` команды работают только если на машине есть Node.js.

---

## 10. Multi-agent setup

Ты можешь подключить несколько агентов одновременно:

```json
{
  "agent_servers": {
    "hermes-mima-main": {
      "command": "ssh",
      "args": ["root@mima_g_01", "/usr/local/lib/hermes-agent/venv/bin/hermes-acp"]
    },
    "hermes-mima-coder": {
      "command": "ssh",
      "args": ["root@mima_g_01", "/usr/local/lib/hermes-agent/venv/bin/hermes-acp",
               "--profile", "coder"]
    },
    "claude-code": {
      "command": "npx",
      "args": ["--yes", "@zed-industries/claude-code-acp@latest"]
    },
    "gemini": {
      "command": "npx",
      "args": ["--yes", "@google/gemini-cli@latest", "--experimental-acp"]
    }
  }
}
```

Каждый агент = **отдельная вкладка** в ACP UI.

---

## 11. Что умеет UI

### Sticky UI preferences

- Состояние collapse/expand run-frame запоминается
- "Show more" / "Show less" для tool lists — также sticky

### Tool-call window

- По умолчанию показывает **5 последних regular tools**
- task/agent rows всегда видны

### Mobile-friendly

- Narrow widths (iPhone XR class) — адаптивный layout

### Attachments

- Workspace files прикрепляются к сообщению
- Active editor selection автоматически в контексте

---

## 12. Permissions

| Setting | Поведение |
|---|---|
| `acp.autoApprovePermissions: "ask"` | каждый tool запросит подтверждение |
| `acp.autoApprovePermissions: "allowAll"` | все tools auto-approved |

**Рекомендация**: `"ask"` для первого знакомства, потом по ситуации.

---

## 13. Troubleshooting

### Расширение не подключается

| Причина | Решение |
|---|---|
| SSH не работает | `ssh root@mima_g_01` руками |
| hermes-acp не в PATH | указать полный путь |
| Таймаут | увеличить `acp.connectTimeoutMs` |

### SSH Permission denied

| Причина | Решение |
|---|---|
| Нет ключа | `ssh-keygen` + `ssh-copy-id` |
| Неправильный пользователь | проверить `root@mima_g_01` |
| Host key | `ssh-keyscan mima_g_01 >> ~/.ssh/known_hosts` |

### Stream рвётся

| Причина | Решение |
|---|---|
| Idle timeout | увеличить `acp.connectTimeoutMs` |
| Большие файлы | меньше context |

### Логи

`Ctrl+Shift+U` → `ACP Traffic` — там JSON-RPC.

Также:
- `~/.acp/logs/` (если есть)
- VS Code Developer Tools → Console

---

## 14. Конфиг для твоего workflow

### Минимальный (только Hermes)

```json
{
  "agent_servers": {
    "hermes-mima": {
      "name": "Hermes on mima_g_01",
      "command": "ssh",
      "args": [
        "root@mima_g_01",
        "/usr/local/lib/hermes-agent/venv/bin/hermes-acp"
      ],
      "cwd": "${workspaceFolder}"
    }
  },
  "acp.autoApprovePermissions": "ask",
  "acp.logTraffic": true
}
```

### Расширенный (multi-agent)

```json
{
  "agent_servers": {
    "hermes-main": {
      "name": "Hermes Main (analyst_training)",
      "command": "ssh",
      "args": [
        "root@mima_g_01",
        "/usr/local/lib/hermes-agent/venv/bin/hermes-acp"
      ],
      "cwd": "${workspaceFolder}"
    },
    "hermes-coder": {
      "name": "Hermes Coder (default profile)",
      "command": "ssh",
      "args": [
        "root@mima_g_01",
        "/usr/local/lib/hermes-agent/venv/bin/hermes-acp",
        "--profile", "default"
      ],
      "cwd": "${workspaceFolder}"
    },
    "hermes-local": {
      "name": "Hermes Local (если есть на Windows)",
      "command": "hermes",
      "args": ["acp"],
      "cwd": "${workspaceFolder}"
    }
  },
  "acp.connectTimeoutMs": 600000,
  "acp.autoApprovePermissions": "ask",
  "acp.logTraffic": true
}
```

---

## 15. Сравнение альтернатив

| Расширение | SSH support | Multi-agent | Hermes native | Built-in |
|---|---|---|---|---|
| **strato-space.acp-plugin** | ✅ | ✅ любые | через config | 9 presets |
| poppywu124.hermes-chat | ❌ | ✅ только Hermes | ✅ | нет |
| joaompfp.hermes-ai-agent | ? | ? | ✅ | нет |
| formulahendry.acp-client | ? | ✅ | через config | ? |
| multicoder.multicoder | ? | ✅ | через config | ? |

**strato-space.acp-plugin** — лучший баланс гибкости и функциональности.

---

## 16. Build from source (если хочется)

```bash
git clone https://github.com/strato-space/acp-plugin
cd acp-plugin
npm ci
npm run package
npx vsce package --no-dependencies
# Локально установить
code --install-extension ./acp-plugin-*.vsix --force
```

Зачем:
- Specific версия
- Кастомизация UI
- PR с улучшением

---

## 17. Roadmap (из README)

| Цель | Статус |
|---|---|
| User-defined agents | ✅ |
| ACP-first | ✅ |
| Active release cadence | ✅ |
| Fast-agent.ai integration | ✅ |
| Massive parallel agent call testing | 🚧 |
| Automated test coverage | 🚧 |
| Modern assistant UI | 🚧 |

---

## 18. Дополнительные ресурсы

| Ссылка | Что |
|---|---|
| github.com/strato-space/acp-plugin | Исходный код |
| github.com/agentclientprotocol/python-sdk | Python SDK |
| zed.dev/docs/ai/external-agents | Zed docs |
| agentclientprotocol.com | Спецификация ACP |

---

## 19. Главная мысль

> **strato-space.acp-plugin** — лучший выбор для тебя, потому что:
> 1. **Умеет SSH** — подключается к Hermes на mima_g_01 без remote extension
> 2. **Zed-compatible** — стандартный формат `agent_servers`
> 3. **Multi-agent** — можно держать несколько подключений
> 4. **9 built-in** — есть Codex, Claude, Gemini, etc. из коробки
> 5. **Open source** — Apache 2.0

---

## 20. Скажи дальше

| Команда | Что делаю |
|---|---|
| Установить расширение | дам команды |
| Настроить multi-agent | распишу конфиг |
| Аудит кода расширения | read-only анализ |
| Сравнить с multicoder | детали |

---

*Документ создан 2026-08-09, отправлено через @MMRV_Hermes_bot в Telegram.*
