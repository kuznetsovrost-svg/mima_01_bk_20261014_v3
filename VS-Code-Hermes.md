# VS Code + Hermes: полная инструкция для Windows

## Цель

Подключить **локальный VS Code на Windows** к **Hermes агенту на удалённом сервере mima-g-01** через протокол **ACP** (Agent Client Protocol).

После настройки:
- В VS Code открывается боковая панель чата с Hermes
- Можно выделять код, задавать вопросы
- Агент может читать файлы, делать изменения

## Предусловия

| Что | Проверить |
|---|---|
| **VS Code** | установлен на Windows (у тебя есть) |
| **OpenSSH Client** | встроен в Windows 10+ (Settings → Apps → Optional Features) |
| **SSH-ключ к mima_g_01** | уже есть: `~/.ssh/id_ed25519_mima` (fp `SHA256:rRAs/wkpLsIqkHyiLTr4Fu1BxnPbvjn1xSPo8WY6CmA`) |
| **ACP на mima_g_01** | уже установлен (`hermes acp --check` → OK) |
| **Hermes версия** | 0.18.0 |

## Схема подключения

```
┌──────────────────────────┐                   ┌──────────────────────────┐
│  Windows (VS Code)       │                   │  mima_g_01 (Linux)       │
│                          │                   │                          │
│  ┌────────────────────┐  │                   │  ┌────────────────────┐  │
│  │  VS Code Editor    │  │                   │  │  hermes-acp        │  │
│  │  + ACP extension   │  │  SSH stdio tunnel │  │  (stdio server)     │  │
│  └─────────┬──────────┘  │ ─────────────────►│  └─────────┬──────────┘  │
│            │             │  JSON-RPC over    │            │             │
│            │             │  stdin/stdout      │            │             │
└────────────┴─────────────┘                   └────────────┴─────────────┘
                                                                       │
                                                                       ▼
                                                            ┌──────────────────┐
                                                            │ MiniMax M3       │
                                                            │ (LLM backend)    │
                                                            └──────────────────┘
```

## Способ 1: VS Code SSH Remote + ACP (рекомендую)

Это **самый простой** способ — использует встроенный в VS Code SSH Remote для работы с файлами на mima_g_01, и ACP для чата.

### Шаг 1. Установить расширение Remote-SSH

VS Code → Extensions (Ctrl+Shift+X) → поиск `Remote - SSH` → установить от Microsoft.

### Шаг 2. Подключиться к mima_g_01

1. Нажми **Ctrl+Shift+P** → `Remote-SSH: Connect to Host...`
2. Введи: `root@mima_g_01`
3. Выбери конфиг SSH или создай новый
4. VS Code откроет «удалённое» окно — все файлы теперь на mima_g_01

### Шаг 3. Установить расширение ACP

VS Code → Extensions (Ctrl+Shift+X) → поиск `ACP` или `Agent Client Protocol` → установить.

Рекомендуемые расширения:
- **Zed ACP** (`zed-industries.ACP`) — официальный от Zed
- **Continue** (с ACP поддержкой)
- **Cline** (недавняя поддержка ACP)

### Шаг 4. Настроить ACP extension

Открой настройки VS Code (`Ctrl+,`) → найди `acp` → добавь:

```json
{
  "acp.agents": [
    {
      "name": "Hermes",
      "command": "ssh",
      "args": [
        "root@mima_g_01",
        "/usr/local/lib/hermes-agent/venv/bin/hermes-acp"
      ],
      "env": {}
    }
  ]
}
```

### Шаг 5. Открыть чат

В боковой панели VS Code появится иконка чата. Нажми → выбери агента `Hermes` → пиши запросы.

## Способ 2: Прямое SSH-подключение в Cursor / Windsurf

Если ты используешь **Cursor** или **Windsurf** вместо VS Code:

### Cursor

1. Settings → `Models` → `Custom API Keys` → добавить `HERMES_ACP`
2. В чате выбрать `Hermes (Local)`

### Windsurf

1. Plugins → найти `Hermes` → установить
2. Настроить endpoint: `ssh://root@mima_g_01/usr/local/lib/hermes-agent/venv/bin/hermes-acp`

## Способ 3: Самописное расширение (для опытных)

Если готовые расширения не подходят, можно сделать своё:

### PowerShell скрипт-мост

Создай файл `C:\Users\<USER>\.vscode\hermes-bridge.ps1`:

```powershell
# hermes-bridge.ps1
$ErrorActionPreference = "Stop"

# Проверяем что SSH настроен
if (-not (Test-Path "$env:USERPROFILE\.ssh\id_ed25519_mima")) {
    Write-Error "SSH ключ не найден: $env:USERPROFILE\.ssh\id_ed25519_mima"
    exit 1
}

# Запускаем hermes-acp через SSH
ssh -i "$env:USERPROFILE\.ssh\id_ed25519_mima" `
    -o StrictHostKeyChecking=no `
    -o UserKnownHostsFile=$env:USERPROFILE\.ssh\known_hosts `
    root@mima_g_01 `
    /usr/local/lib/hermes-agent/venv/bin/hermes-acp
```

### VS Code extension config

В `settings.json`:
```json
{
  "acp.agents": [
    {
      "name": "Hermes",
      "command": "powershell",
      "args": ["-File", "C:\\Users\\<USER>\\.vscode\\hermes-bridge.ps1"]
    }
  ]
}
```

## Способ 4: HTTP прокси (если ACP не подходит)

Если ни одно расширение не поддерживает ACP, можно сделать HTTP-прокси.

### На mima_g_01: запустить Hermes в HTTP mode

```bash
# Hermes умеет работать через HTTP
hermes acp --http  # если поддерживается
# или
python3 -m hermes.serve --port 8080
```

### На Windows: подключиться через REST

```bash
# VS Code REST Client extension
GET http://mima_g_01:8080/v1/chat
```

⚠️ Этот способ **нестандартный** — лучше использовать ACP.

## Что доступно после подключения

| Действие | Где |
|---|---|
| **Чат с агентом** | боковая панель VS Code |
| **Edit выделенного кода** | Ctrl+K → `Refactor with Hermes` |
| **Объяснить функцию** | выделить → `Explain with Hermes` |
| **Создать файл** | `Hermes: New file` |
| **Запустить тесты** | `Hermes: Run tests` |
| **Git операции** | `Hermes: Commit` |
| **Поиск в проекте** | `Hermes: Search workspace` |

## Проверка подключения

### Тест 1: из терминала VS Code

Открой терминал (`Ctrl+``) и введи:

```bash
ssh root@mima_g_01 '/usr/local/lib/hermes-agent/venv/bin/hermes-acp --version'
```

Должен вернуть: `0.18.0`

### Тест 2: через Python

В VS Code → открой файл → создай тест:

```python
# test_acp.py
import subprocess
result = subprocess.run(
    ['ssh', 'root@mima_g_01', '/usr/local/lib/hermes-agent/venv/bin/hermes-acp', '--check'],
    capture_output=True, text=True
)
print(result.stdout)  # "Hermes ACP check OK"
```

### Тест 3: прямая отправка JSON-RPC

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":1}}' | ssh root@mima_g_01 /usr/local/lib/hermes-agent/venv/bin/hermes-acp
```

Должен вернуть capabilities агента.

## Типичные ошибки

| Ошибка | Решение |
|---|---|
| `Permission denied (publickey)` | Проверь что SSH-ключ есть в `~/.ssh/id_ed25519_mima` |
| `command not found: hermes-acp` | Используй полный путь `/usr/local/lib/hermes-agent/venv/bin/hermes-acp` |
| `Connection refused` | SSH-сервер не запущен или firewall блокирует |
| `Permission denied` на сервере | Запусти `chmod +x /usr/local/lib/hermes-agent/venv/bin/hermes-acp` |
| VS Code extension не находит агента | Проверь `acp.agents` в settings.json |
| Агент не отвечает | Проверь провайдер: `hermes acp --setup` |

## Безопасность

| Аспект | Как настроено |
|---|---|
| **SSH-ключ** | ed25519, fp `SHA256:rRAs/wkp...CmA` |
| **SSH только по ключу** | пароли отключены на mima_g_01 |
| **Токены агента** | в `/root/.hermes/.env` (chmod 600) |
| **Песочница** | ACP работает в контексте пользователя |
| **Audit log** | `/root/.hermes/profiles/default/logs/agent.log` |

## Расширенные настройки

### Кастомные tools

В `~/.hermes/.env` можно добавить:

```bash
HERMES_TOOLS_BROWSER=1
HERMES_TOOLS_DESKTOP=1
```

### Использовать конкретный профиль

```json
{
  "acp.agents": [
    {
      "name": "Hermes Analyst",
      "command": "ssh",
      "args": [
        "root@mima_g_01",
        "/usr/local/lib/hermes-agent/venv/bin/hermes-acp",
        "--profile=analyst_training"
      ]
    }
  ]
}
```

### Лимит контекста

В `~/.hermes/profiles/<profile>/config.yaml`:

```yaml
agent:
  max_turns: 150
session_reset:
  mode: auto
  threshold: 150000
```

## Чек-лист настройки

- [ ] VS Code установлен
- [ ] OpenSSH Client в Windows
- [ ] SSH-ключ к mima_g_01 работает
- [ ] Расширение Remote-SSH установлено
- [ ] Расширение ACP установлено
- [ ] settings.json сконфигурирован
- [ ] Подключение проверено (test 1-3)
- [ ] Чат с Hermes открывается
- [ ] Тестовый запрос работает

## Полезные ссылки

- **Agent Client Protocol**: https://github.com/agentclientprotocol/agent-client-protocol
- **Hermes документация**: https://hermes-agent.nousresearch.com/docs
- **VS Code Remote-SSH**: https://code.visualstudio.com/docs/remote/ssh
- **ACP docs (Hermes)**: `/usr/local/lib/hermes-agent/website/docs/user-guide/features/acp.md`

## Краткая шпаргалка

```bash
# Проверить ACP
ssh root@mima_g_01 'hermes acp --check'

# Версия
ssh root@mima_g_01 'hermes acp --version'

# Настроить provider/model
ssh root@mima_g_01 'hermes acp --setup'

# Установить browser tools (~400 MB)
ssh root@mima_g_01 'hermes acp --setup-browser'

# Прямой запуск stdio
ssh root@mima_g_01 /usr/local/lib/hermes-agent/venv/bin/hermes-acp
```

## Главная мысль

> **VS Code + Remote-SSH + ACP = полноценный AI-агент в IDE без локальной установки моделей.**
> Всё работает на mima_g_01, ты только подключаешься через SSH-туннель.
