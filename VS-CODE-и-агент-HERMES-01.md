# VS Code + Hermes (mima-g-01) — playbook 01

> Настройка взаимодействия VS Code (Windows) и Hermes (mima-g-01)
> для совместной работы с файлами.
>
> Особый фокус: предотвращение прерывания сессии через несколько минут.
>
> Дата: 2026-08-09
> Источник: опыт реальных сессий через ACP.
> Связанные playbook: `Совместная_работа_VSCode_и_агент_01.txt`.


Введение
========

Этот playbook написан потому что в реальной работе сессии
VS Code ↔ Hermes через ACP обрывались через 3-15 минут
без видимой причины. Симптомы:

- в ACP чате перестают приходить ответы
- иконка агента в Activity Bar показывает "disconnected"
- при попытке отправить сообщение — "Agent process exited"
- в Output → ACP Traffic последние сообщения зависают
- в session_search на mima_g_01 сессия обрывается до flush

Это НЕ баг Hermes. Это результат нескольких слоёв таймаутов
(SSH, VS Code, ACP extension, Hermes), которые по умолчанию
не согласованы между собой.

Цель playbook — выровнять все таймауты так, чтобы сессия
жила столько, сколько нужно (часы, не минуты), и давала
явный сигнал при реальном обрыве.


Глава 1. Диагностика — почему сессия умирает
============================================

Есть 5 независимых причин обрыва. Нужно проверить каждую.

1.1 SSH-keepalive выключен (главная причина в 80% случаев)

    TCP-соединение через NAT/firewall умирает через 2-5 минут
    без keepalive-пакетов. Симптом: SSH работает минуту, потом
    зависает.

    Проверка:
        ssh -v root@mima-g-01 "echo ok"
        # в verbose-логе должно быть:
        # ServerAliveInterval (60-30)
        # TCPKeepAlive yes

1.2 ACP streamIdleTimeout = 120 секунд (по умолчанию)

    Если модель "думает" дольше 2 минут без chunk'а в потоке,
    ACP считает сессию мёртвой и закрывает её.

    Проверка:
        cat ~/.hermes/profiles/<name>/config.yaml | grep -i timeout
        # должно быть streamIdleTimeout >= 600

1.3 VS Code extension host рестарт

    VS Code может рестартить extension host при:
    - auto-update расширения
    - переключении workspace
    - потере фокуса окна (в фоне > 30 мин)

    Проверка:
        VS Code → Help → Toggle Developer Tools → Console
        # ищи "[ACPP] restarting" или подобные

1.4 Windows power management

    USB selective suspend, network adapter power saving,
    Modern Standby — всё это может усыплять сетевые соединения.

    Проверка:
        powercfg /energy
        # ищи "USB Selective Suspend: Enabled"

1.5 Antivirus / Firewall interference

    Kaspersky, ESET, Windows Defender real-time scan могут
    разрывать SSH-сессии, считая их подозрительными.

    Проверка:
        Event Viewer → Windows Logs → Security
        # ищи "Audit Failure" с source "Microsoft Windows security"


Глава 2. SSH-сторона — главные настройки
=========================================

Все настройки в `C:\Users\<user>\.ssh\config`.
У тебя уже есть запись `mima-g-01` — расширяем её.

2.1 Полная конфигурация для mima-g-01

    Host mima-g-01
        HostName 72.56.29.69
        User root
        Port 22
        IdentityFile C:\Users\<user>\.ssh\id_ed25519_mima
        IdentitiesOnly yes
        PreferredAuthentications publickey
        PasswordAuthentication no

        # === КРИТИЧНО: keepalive ===
        ServerAliveInterval 30
        ServerAliveCountMax 6
        TCPKeepAlive yes

        # === Опционально: multiplexing ===
        ControlMaster auto
        ControlPath C:\Users\<user>\.ssh\cm-%r@%h:%p
        ControlPersist 10m

        # === Опционально: ускорение повторных подключений ===
        Compression yes
        GSSAPIAuthentication no

2.2 Что означает каждый параметр

    ServerAliveInterval 30
        Каждые 30 секунд SSH отправляет пустой пакет.
        Держит TCP-соединение живым через NAT.

    ServerAliveCountMax 6
        Если 6 пакетов подряд (180 сек) без ответа —
        закрыть соединение. То есть через 3 минуты
        неактивности сессия сама закроется (без зависания).

    TCPKeepAlive yes
        Использовать ОС-уровень TCP keepalive (страховка
        к SSH-уровню).

    ControlMaster auto
        Если уже есть соединение к этому хосту — переиспользовать.
        Открывает одно TCP-соединение на много логических.

    ControlPath C:\Users\<user>\.ssh\cm-%r@%h:%p
        Файл-сокет для multiplexing. %r = user, %h = host.

    ControlPersist 10m
        Мастер-соединение живёт 10 минут после последнего
        использования. Ускоряет reopen.

2.3 Как создать директорию для ControlPath

    PowerShell:
        New-Item -ItemType Directory -Force -Path $HOME\.ssh
        # Директория уже есть если config работает

2.4 Проверка после изменений

    PowerShell:
        ssh -F $HOME\.ssh\config -v root@mima-g-01 "echo ok"
        # в выводе ищи:
        # debug1: ServerAliveInterval 30
        # debug1: ServerAliveCountMax 6
        # debug1: TCPKeepAlive yes

    Тест на длинную сессию (5 минут idle):
        ssh root@mima-g-01 "sleep 300; echo ok"
        # через 5 минут должно вернуть "ok"
        # если зависло — keepalive не работает

2.5 Мультиплексирование — как пользоваться

    После первого подключения:
        ssh root@mima-g-01 "uptime"
        # создаётся ControlMaster

    Второе подключение в течение 10 минут:
        ssh root@mima-g-01 "ls"
        # переиспользует существующий master,
        # моментальное подключение

    Закрыть master вручную:
        ssh -O exit root@mima-g-01


Глава 3. Windows-сторона
========================

3.1 Power management — отключить засыпание сети

    PowerShell (от администратора):

        # Посмотреть текущие настройки
        powercfg /q SCHEME_CURRENT sub NONE

        # Отключить USB selective suspend
        powercfg /setacvalueindex SCHEME_CURRENT 2a737441-1930-4402-8d77-b2bebba308a3 48e6b7a6-50f5-4782-a5d4-53bb8f07e226 0

        # Отключить network adapter power saving
        # (через Device Manager → свойства сетевой карты → Power Management)
        # снять "Allow the computer to turn off this device to save power"

3.2 Отключить Modern Standby (если возможно)

    PowerShell (от администратора):

        powercfg /a
        # покажет доступные состояния сна

        # Если есть "Modern Standby" — это плохо для долгих сессий
        # Отключить через BIOS или:
        powercfg /setacvalueindex SCHEME_CURRENT 238c9fa8-0aad-41ed-83f4-97be242c8a20 29f6c1db-86da-48c5-9fdb-f2b67b1f44da 0

3.3 Windows Defender Firewall — исключение для SSH

    PowerShell (от администратора):

        New-NetFirewallRule -DisplayName "OpenSSH Server (mima-g-01)" -Direction Outbound -Program "C:\Windows\System32\OpenSSH\ssh.exe" -Action Allow -RemoteAddress 72.56.29.69

        # Проверить
        Get-NetFirewallRule -DisplayName "OpenSSH*"

3.4 Antivirus exclusions (если установлен сторонний)

    Для Kaspersky / ESET / Norton — добавить в исключения:
        - C:\Windows\System32\OpenSSH\ssh.exe
        - C:\Windows\System32\OpenSSH\sshd.exe (если есть)
        - VS Code: C:\Users\<user>\AppData\Local\Programs\Microsoft VS Code\
        - %TEMP%\ (для VS Code extension host)

3.5 Отключить Nagle algorithm (опционально)

    Для SSH это иногда помогает при медленных сетях:

        # Registry edit
        HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters
        TcpAckFrequency = 1
        TCPNoDelay = 1
        # После — перезагрузка


Глава 4. VS Code — настройки
============================

4.1 Критичные настройки в settings.json

    Открыть Ctrl+, → иконка {} (Open Settings JSON):

    {
        // === Telemetry — минимум ===
        "telemetry.telemetryLevel": "off",
        "telemetry.enableTelemetry": false,

        // === Auto-update — отключить ===
        "update.mode": "none",
        "extensions.autoUpdate": "none",

        // === Window — не усыплять ===
        "window.titleBarStyle": "custom",
        "window.zoomLevel": 0,

        // === Extensions — защита от рестарта ===
        "extensions.supportUntrustedWorkspaces": {
            "strato-space.acp-plugin": true,
            "ms-vscode-remote.remote-ssh": true
        },

        // === Files — watcher для Remote-SSH ===
        "files.watcherExclude": {
            "**/.git/objects/**": true,
            "**/node_modules/**": true,
            "**/.venv/**": true,
            "**/__pycache__/**": true
        },

        // === Remote-SSH ===
        "remote.SSH.connectTimeout": 60,
        "remote.SSH.serverAliveInterval": 30,
        "remote.SSH.serverAliveCountMax": 6,

        // === Terminal ===
        "terminal.integrated.enablePersistentSessions": false,
        "terminal.integrated.scrollback": 10000
    }

4.2 Что значат эти настройки

    telemetry.telemetryLevel: off
        VS Code не отправляет telemetry. Не тратит bandwidth,
        не прерывает фоновые процессы.

    update.mode: none
        VS Code не обновляется автоматически. Обновление
        = рестарт extension host = обрыв ACP.

    extensions.autoUpdate: none
        Расширения не обновляются автоматически. То же самое.

    extensions.supportUntrustedWorkspaces
        Некоторые расширения требуют явно trusted workspace.
        Без этого они могут выгружаться.

    files.watcherExclude
        VS Code тратит CPU на watching ненужных файлов.
        При большом проекте это может нагружать remote host.

    remote.SSH.*
        Зеркало настроек SSH keepalive внутри VS Code.

4.3 Отключить автоперезагрузку окна

    Ctrl+Shift+P → "Preferences: Configure Runtime Arguments"

    В argv.json добавить:
        "disable-window-auto-reload": true

    Это предотвращает авто-reload VS Code при потере фокуса.

4.4 Отключить авто-сохранение (опционально)

    {
        "files.autoSave": "afterDelay",
        "files.autoSaveDelay": 5000
    }

    Не "onFocusChange" — это вызывает reload файлов
    при потере фокуса, что может нагружать remote.


Глава 5. ACP extension — настройки
==================================

У тебя установлен `strato-space.acp-plugin`. Настройки:

5.1 Критичные настройки

    В settings.json (VS Code):

    {
        "agent_servers": {
            "hermes-default": {
                "name": "Hermes Agent",
                "command": "ssh",
                "args": [
                    "root@mima-g-01",
                    "/usr/local/lib/hermes-agent/venv/bin/hermes-acp"
                ],
                "env": {
                    "HERMES_PROFILE": "default"
                },
                "cwd": "${workspaceFolder}"
            }
        },

        // === КРИТИЧНО: таймауты ===
        "acp.connectTimeoutMs": 1800000,        // 30 минут вместо 10
        "acp.streamIdleTimeout": 1800,         // 30 минут вместо 2 минут
        "acp.autoApprovePermissions": "ask",   // не "allowAll"
        "acp.logTraffic": true,                // для отладки

        // === Новые настройки (если есть в версии) ===
        "acp.reconnectOnFailure": true,
        "acp.maxReconnectAttempts": 5,
        "acp.reconnectDelayMs": 5000
    }

5.2 Что означают новые таймауты

    acp.connectTimeoutMs: 1800000
        Подключение может идти до 30 минут. По умолчанию 10 минут
        (600000) — этого мало при медленном SSH handshake или
        большом количестве startup-скиллов.

    acp.streamIdleTimeout: 1800
        Между двумя chunk'ами потока может быть до 30 минут паузы.
        Это КРИТИЧНО для длинных reasoning-моделей, которые могут
        думать несколько минут перед первым chunk'ом.

        Если модель думает 20 минут — это нормально. Не должно
        обрывать сессию.

    acp.reconnectOnFailure: true
        При обрыве SSH пытаться переподключиться. Без этого
        любая кратковременная потеря сети = конец сессии.

    acp.maxReconnectAttempts: 5
        До 5 попыток reconnect с интервалом 5 секунд.

5.3 Если настройки reconnect не поддерживаются

    Старые версии strato-space.acp-plugin не имеют reconnect.
    Решение: обновить расширение или принять что reconnect
    невозможен — фокус на prevention (Главы 2-4).

5.4 Логирование для отладки

    "acp.logTraffic": true → вывод в Output → ACP Traffic.

    Что искать при обрыве:
        - последний chunk (как давно)
        - SSH disconnect events
        - "stream idle timeout reached" (если есть)


Глава 6. Hermes CLI — настройки
===============================

6.1 config.yaml для профиля

    /root/.hermes/profiles/<name>/config.yaml:

    model:
      default: MiniMax-M3
      provider: minimax

    agent:
      max_turns: 150

    display:
      tool_progress: all

    session_reset:
      mode: auto              # авто-reset при приближении к лимиту
      threshold: 150000       # 150K токенов
      keep_last_n: 30         # хранить последние 30 сообщений

    platform_toolsets:
      cli:
        - browser
        - code_execution
        - file
        - memory
        - skills
        - terminal
        - web

6.2 Что значат session_reset настройки

    mode: auto
        Автоматический reset когда приближаемся к лимиту контекста.
        Без этого контекст раздувается → медленнее ответы →
        дольше думает → streamIdleTimeout.

    threshold: 150000
        Начинать reset при 150K токенов (для модели с 200K лимитом).

    keep_last_n: 30
        Хранить 30 последних сообщений после reset. Контекст
        не теряется, но сессия остаётся быстрой.

6.3 Проверка текущего размера сессии

    На mima_g_01:
        ls -la /root/.hermes/state.db*
        sqlite3 /root/.hermes/state.db           "SELECT count(*) FROM messages;"

    Если больше 200 сообщений — нужен reset (или auto-reset).


Глава 7. Сетевые настройки
===========================

7.1 Если подключение через роутер/NAT

    NAT таблицы на роутерах обычно сбрасывают idle TCP через
    60-300 секунд. Это главная причина обрывов.

    Решения:
        - SSH ServerAliveInterval 30 (уже в Главе 2)
        - если есть доступ к роутеру — увеличить NAT timeout
        - VPN с persistent connection

7.2 Если подключение через VPN

    Некоторые VPN (Cisco AnyConnect, GlobalProtect) разрывают
    долгие соединения принудительно.

    Решения:
        - переключиться на WireGuard (persistent)
        - включить VPN keepalive в настройках клиента
        - в настройках SSH добавить ExitOnForwardFailure no

7.3 Если mima_g_01 за файрволом (провайдер/облако)

    AWS Security Groups, Azure NSG — могут иметь stateful
    timeout. По умолчанию 350 секунд для idle.

    Решение (если есть доступ):
        - увеличить timeout до 1 часа
        - или настроить iptables keepalive на сервере

7.4 iptables keepalive на mima_g_01 (root)

    # Посмотреть текущие настройки
    sysctl net.ipv4.tcp_keepalive_time
    sysctl net.ipv4.tcp_keepalive_intvl
    sysctl net.ipv4.tcp_keepalive_probes

    # Установить агрессивный keepalive
    sysctl -w net.ipv4.tcp_keepalive_time=60
    sysctl -w net.ipv4.tcp_keepalive_intvl=10
    sysctl -w net.ipv4.tcp_keepalive_probes=6

    # Сделать постоянным через /etc/sysctl.d/99-keepalive.conf
    echo "net.ipv4.tcp_keepalive_time = 60" >> /etc/sysctl.d/99-keepalive.conf
    echo "net.ipv4.tcp_keepalive_intvl = 10" >> /etc/sysctl.d/99-keepalive.conf
    echo "net.ipv4.tcp_keepalive_probes = 6" >> /etc/sysctl.d/99-keepalive.conf


Глава 8. Pre-flight чеклист
============================

Перед каждой долгой сессией (особенно если в прошлый раз был обрыв):

[ ] SSH keepalive работает
    PowerShell: ssh -v root@mima-g-01 "echo ok"
    → ServerAliveInterval 30, TCPKeepAlive yes

[ ] ACP streamIdleTimeout = 1800 (30 минут)
    settings.json VS Code → acp.streamIdleTimeout

[ ] VS Code auto-update отключён
    settings.json → update.mode: none

[ ] Расширения не обновляются автоматически
    settings.json → extensions.autoUpdate: none

[ ] Power management: USB/network не усыпляются
    powercfg /energy

[ ] Долгая SSH-сессия работает
    ssh root@mima-g-01 "sleep 600; echo ok"
    Должно вернуть "ok" через 10 минут

[ ] Профиль Hermes в порядке
    ls /root/.hermes/profiles/<name>/
    sqlite3 state.db "SELECT count(*) FROM messages"

[ ] session_reset.mode = auto
    config.yaml → session_reset.mode

[ ] Output → ACP Traffic пустой
    (нет ошибок перед стартом)

[ ] VS Code открыт в foreground
    Если свернуть — некоторые расширения приостанавливаются


Глава 9. Мониторинг во время сессии
====================================

9.1 Смотреть Output → ACP Traffic

    В реальном времени показывает:
        - JSON-RPC сообщения
        - SSH keepalive (нет, не показывает)
        - ошибки handshake

9.2 Смотреть состояние на mima_g_01

    В отдельном SSH (не в чате):
        watch -n 60 "ss -tn | grep ':3284\|:22' | head"
        # показать активные SSH-соединения

        tail -f /root/.hermes/state.db-wal
        # лог записи в SQLite (но это бинарный)

9.3 Логи в VS Code

    Help → Toggle Developer Tools → Console
    Фильтр: "acp", "ssh", "connection"

    Что искать:
        - "Connection lost"
        - "Stream idle timeout"
        - "ECONNRESET"
        - "ssh: connect to host"

9.4 Логи в PowerShell

    ssh -v root@mima-g-01 "echo ok" 2>&1 | tee ssh.log
    # потом смотреть ssh.log

9.5 Команды на mima_g_01 (отдельный SSH)

    # Активные сессии
    ps aux | grep -E "hermes|acp" | grep -v grep

    # SSH connections
    ss -tn | grep ':22'

    # Размер state.db
    du -sh /root/.hermes/state.db*

    # Последние сообщения в state.db
    sqlite3 /root/.hermes/state.db       "SELECT datetime(created_at, 'unixepoch'), role, substr(content, 1, 100)
       FROM messages ORDER BY id DESC LIMIT 20;"


Глава 10. Если всё равно обрывается
====================================

Шаг 1. Определи на каком слое обрыв

    PowerShell:
        ssh -v root@mima-g-01 "sleep 300; echo ok" 2>&1 | tee log.txt
        # если зависло на 60-180 сек — проблема в SSH keepalive

    VS Code Output → ACP Traffic:
        # если последнее сообщение = JSON-RPC без response —
        # проблема в ACP streamIdleTimeout

    Windows Event Viewer → Security:
        # если много Audit Failure — firewall/antivirus

Шаг 2. Включи максимальное логирование

    "acp.logTraffic": true,
    "remote.SSH.logLevel": "verbose"   // в settings.json

    ssh -vvv root@mima-g-01 "echo ok"  // от PowerShell

Шаг 3. Проверь что iptables keepalive применился

    На mima_g_01:
        sysctl net.ipv4.tcp_keepalive_time
        # должно быть 60

Шаг 4. Попробуй ControlMaster multiplexing

    ssh -M -S $HOME\.ssh\cm-%r@%h:%p root@mima-g-01 "echo ok"
    # создаёт мастер-соединение
    # следующие ssh используют его

Шаг 5. Если ничего не помогло — используй cron вместо ACP

    Для длительных задач без активного чата:
        # Создать cron-задачу
        hermes cron add --profile default --interval "1h" --task "..."

        # Это не требует открытого ACP-соединения

Шаг 6. Nuclear option — переключиться на Telegram

    Если ACP нестабилен, основная работа — в Telegram через
    @MMRV_Hermes_bot. Файлы передаются файлом. Есть ограничения
    (нет inline edit, нет workspace context), но сессия стабильна
    часами.


Глава 11. Что НЕ поможет
=========================

Не трать время на эти "лекарства":

- Увеличение `acp.connectTimeoutMs` без `streamIdleTimeout` —
  обрыв всё равно будет по stream timeout.

- Отключение antivirus полностью — опасно и часто не помогает
  (Defender всё равно активен).

- Перезапуск VS Code каждую минуту — помогает на короткий срок,
  но не устраняет причину.

- Использование WSL вместо Windows SSH — добавляет слой, который
  тоже может обрываться.

- Увеличение VS Code memory limit — не связано с обрывами.

- Отключение Windows Update полностью — обрывы будут по другим
  причинам.


Глава 12. Шпаргалка команд
============================

Быстрая диагностика (PowerShell):

    ssh -v root@mima-g-01 "echo ok"
    # → должно вернуть "ok" без warning про keepalive

    ssh root@mima-g-01 "sleep 60; echo ok"
    # → через минуту "ok", не timeout

    ssh root@mima-g-01 "sleep 600; echo ok"
    # → через 10 минут "ok" (тест на длинные сессии)

Быстрая проверка настроек VS Code:

    Ctrl+Shift+P → Preferences: Open User Settings (JSON)
    # проверить:
    # acp.streamIdleTimeout: 1800
    # acp.connectTimeoutMs: 1800000
    # update.mode: "none"
    # extensions.autoUpdate: "none"

Быстрая проверка на mima_g_01:

    sysctl net.ipv4.tcp_keepalive_time     # 60
    cat ~/.hermes/profiles/default/config.yaml | grep -i timeout
    sqlite3 ~/.hermes/state.db "SELECT count(*) FROM messages;"  # <500

Перезапуск всего стека (если совсем плохо):

    # На mima_g_01
    systemctl --user restart hermes-gateway-default.service

    # На Windows
    # Ctrl+Shift+P → Developer: Reload Window
    # (это перезапустит extension host, включая ACP)


Приложение А. Сводка таймаутов
===============================

Слой                  Параметр                   Значение
--------------------  ------------------------  -----------
SSH                   ServerAliveInterval        30 сек
SSH                   ServerAliveCountMax        6 (3 мин)
SSH                   TCPKeepAlive               yes
SSH                   ControlPersist             10 мин
iptables              tcp_keepalive_time         60 сек
iptables              tcp_keepalive_intvl        10 сек
iptables              tcp_keepalive_probes       6
VS Code remote.SSH    serverAliveInterval        30 сек
VS Code remote.SSH    serverAliveCountMax        6
VS Code remote.SSH    connectTimeout             60 сек
ACP                   connectTimeoutMs           1800000 (30 мин)
ACP                   streamIdleTimeout          1800 (30 мин)
ACP                   reconnectOnFailure         true
ACP                   maxReconnectAttempts       5
ACP                   reconnectDelayMs           5000
Hermes                session_reset.mode         auto
Hermes                session_reset.threshold    150000 токенов
Hermes                session_reset.keep_last_n  30

Главное правило: ВСЕ таймауты должны быть согласованы.
Если один слой режет через 2 минуты, а другой через 30 —
сессия умрёт через 2 минуты.


Приложение Б. Контекст этой сессии
===================================

Дата: 2026-08-09
Активный профиль: default
Подключение: ACP через SSH root@mima-g-01
Проблема: сессии обрывались через 3-15 минут

Связанные playbook:
- /root/Совместная_работа_VSCode_и_агент_01.txt
  (общий workflow)
- /root/VS-Code-Hermes.md (базовое подключение)
- /root/VS-Code-Hermes-Playbook.md (развёрнутый playbook)
- /root/strato-space-acp-playbook.md (настройка ACP)
- /root/Hermes-Chat-VS-Code-Setup.md (альтернатива)

Связанные скиллы:
- vscode-integration v1.0.0
- hermes-agent-skill-authoring v1.1.0
- memory-hygiene
- failsafe-rules
- messaging-gateway-setup


Конец playbook.

