# Файлы: VS Code + Hermes (mima-g-01) — playbook 01

> Настройка взаимодействия VS Code (Windows) и Hermes (mima-g-01)
> для совместной работы с файлами.
>
> Подробное описание всех вариантов настроек —
> от самых удобных до самых неудобных.
>
> Дата: 2026-08-09
> Связанные playbook:
> - VS-CODE-и-агент-HERMES-01.md (общие настройки VS Code + Hermes)
> - Совместная_работа_VSCode_и_агент_01.txt (workflow правки)


Введение
========

Этот playbook отвечает на конкретный вопрос:

"Как я могу работать с файлами в твоём каталоге?"

Под "твоим каталогом" понимается файловая система на mima_g_01,
где живёт Hermes, его профили, скиллы, и где агент выполняет
работу.

Есть несколько способов — от полностью прозрачного (файлы
на Windows, Remote-SSH пробрасывает) до ручного (копирование
через scp). Все они описаны ниже с оценкой удобства.

Шкала удобства — от 5 (отлично) до 1 (работает, но неудобно):

    5  — один клик, без переключений контекста
    4  — пара кликов, иногда переключение
    3  — несколько кликов, переключение окон
    2  — команды в терминале, синхронизация ручная
    1  — ручное копирование, много действий


Часть I. Удобные варианты (5-4 балла)
=====================================


Вариант 1. Remote-SSH workspace (⭐⭐⭐⭐⭐ 5/5)
--------------------------------------------

Это самый удобный способ. Открываешь папку на mima_g_01 как
локальный workspace в VS Code. Все файлы редактируешь
прямо — никакой синхронизации, всё нативно.

Что получает пользователь:
- файлы на mima_g_01 в Explorer VS Code
- редактирование = сохранение напрямую в remote fs
- терминал = shell на mima_g_01
- Git работает на remote
- поиск, grep, все extensions — работают с remote файлами
- агенту не нужно ничего делать — он видит те же файлы

Что получает агент (Hermes):
- работает с файлами через свою файловую систему (уже на mima_g_01)
- read_file, write_file, patch — нативно
- skills исполняются локально

Оба видят **одни и те же файлы** без какой-либо синхронизации.

Шаг 1. Установить расширение Remote-SSH

    VS Code → Ctrl+Shift+X → поиск "Remote-SSH"
    Publisher: Microsoft (ms-vscode)
    Install

Шаг 2. Настроить SSH config

    C:\Users\<user>\.ssh\config:
    Host mima-g-01
        HostName 72.56.29.69
        User root
        Port 22
        IdentityFile C:\Users\<user>\.ssh\id_ed25519_mima
        IdentitiesOnly yes
        ServerAliveInterval 30
        ServerAliveCountMax 6

Шаг 3. Подключиться к хосту

    Ctrl+Shift+P → "Remote-SSH: Connect to Host"
    Выбрать "mima-g-01"
    Выбрать платформу "Linux"
    Ждать пока Remote-SSH установит VS Code Server на mima_g_01

Шаг 4. Открыть папку

    После подключения:
    File → Open Folder → /root/hermes-workspace
    (или /root/.hermes/skills если работаешь со скиллами)

Шаг 5. Установить расширения в remote

    Расширения должны быть установлены **на remote**, не на Windows.
    VS Code спросит при первом открытии remote workspace.
    
    Установить в remote:
    - strato-space.acp-plugin
    - python
    - yaml

Где кликать:
- 1 клик: Ctrl+Shift+P → Connect to Host → mima-g-01
- 1 клик: File → Open Folder → выбрать
- установка расширений — 3 клика

Плюсы:
- ✅ Полностью прозрачно
- ✅ Файлы там, где живёт агент
- ✅ Никакой синхронизации
- ✅ Быстро

Минусы:
- ❌ Нужен стабильный SSH (см. предыдущий playbook)
- ❌ Установка VS Code Server на remote (300 MB)
- ❌ Некоторые расширения не работают в remote


Вариант 2. ACP + Workspace attach (⭐⭐⭐⭐ 4/5)
---------------------------------------------

Используешь ACP-расширение для чата с агентом, прикрепляешь
файлы из workspace как контекст.

Что получает пользователь:
- обычный локальный VS Code на Windows
- файлы могут быть локально или remote (через Remote-SSH)
- чат с агентом в ACP panel
- прикрепляешь файлы в чат как контекст

Что получает агент:
- видит прикреплённые файлы
- может попросить прочитать другие через read_file
- может ответить на основе контекста

Где кликать:
- ACP panel → значок скрепки → Attach file
- или Ctrl+L → "прочитай <путь>"
- 2-3 клика на действие

Плюсы:
- ✅ Работает без Remote-SSH workspace
- ✅ ACP клиент может быть локальным
- ✅ Не требует VS Code Server на remote

Минусы:
- ❌ Каждое действие — явное прикрепление
- � Файлы должны быть в workspace или указаны путём
- ❌ Нет нативного editing


Вариант 3. Remote-SSH + ACP (⭐⭐⭐⭐⭐ 5/5)
------------------------------------------

Комбинация: Remote-SSH для файлов + ACP для чата.

Шаг 1. Подключиться через Remote-SSH (см. Вариант 1)
Шаг 2. Установить в remote VS Code:
    - strato-space.acp-plugin
Шаг 3. Настроить ACP с HERMES_PROFILE env

    settings.json в remote:
    {
        "agent_servers": {
            "hermes-default": {
                "command": "ssh",
                "args": ["root@127.0.0.1", "/usr/local/lib/hermes-agent/venv/bin/hermes-acp"],
                "env": {"HERMES_PROFILE": "default"}
            }
        }
    }

    Здесь ssh идёт на 127.0.0.1 — это loopback remote.
    Или просто вызвать hermes-acp без ssh:

    {
        "agent_servers": {
            "hermes-default": {
                "command": "/usr/local/lib/hermes-agent/venv/bin/hermes-acp",
                "env": {"HERMES_PROFILE": "default"}
            }
        }
    }

Где кликать:
- один раз настроить settings.json
- потом всё прозрачно

Плюсы:
- ✅ Максимальное удобство
- ✅ Файлы и чат в одной сессии
- ✅ Агент видит всё что ты редактируешь

Минусы:
- ❌ Самая сложная начальная настройка
- ❌ ACP extension должен работать в remote VS Code


Вариант 4. WSL + Remote-SSH (⭐⭐⭐⭐ 5/5)
-----------------------------------------

Если у тебя WSL (Windows Subsystem for Linux), можно
использовать WSL как промежуточный слой.

Шаг 1. Установить WSL
    PowerShell (admin):
        wsl --install

Шаг 2. Установить Ubuntu (или другой дистрибутив)
    Microsoft Store → Ubuntu → Install

Шаг 3. Из WSL подключаться к mima_g_01
    В WSL терминале:
        ssh root@mima-g-01
        # ключ можно скопировать через ssh-agent или pageant

Шаг 4. Открыть VS Code из WSL
    В WSL:
        code .
    # VS Code запускается на Windows, но контекст — WSL

Шаг 5. Подключиться к mima_g_01 через Remote-SSH
    Из VS Code → Ctrl+Shift+P → Connect to Host

Плюсы:
- ✅ Linux среда на Windows
- ✅ SSH ключи хранятся в WSL
- ✅ Можно использовать Linux-инструменты

Минусы:
- ❌ Дополнительный слой
- ❌ Может быть медленнее


Вариант 5. Multi-root workspace (⭐⭐⭐⭐ 5/5)
--------------------------------------------

Открыть workspace, который включает несколько папок:
- локальные файлы на Windows
- remote папку через Remote-SSH
- обе видны в одном Explorer

Шаг 1. Открыть workspace файл .code-workspace:
    {
        "folders": [
            {
                "name": "Local (Windows)",
                "path": "C:\\Users\\<user>\\my-project"
            },
            {
                "name": "Remote (mima_g_01)",
                "path": "/root/hermes-workspace"
            }
        ]
    }

Шаг 2. File → Open Workspace → выбрать файл

Плюсы:
- ✅ Все файлы в одном workspace
- ✅ Видно обе стороны
- ✅ Поиск работает по обоим

Минусы:
- ❌ Нужно явно создать .code-workspace
- ❌ Может запутывать (откуда файл?)


Часть II. Средние варианты (3 балла)
=====================================


Вариант 6. SFTP-расширение (⭐⭐⭐ 3/5)
-------------------------------------

Использовать SFTP расширение для синхронизации файлов
между Windows и mima_g_01.

Шаг 1. Установить расширение
    VS Code → Extensions → "SFTP" (liximomo)
    Install

Шаг 2. Создать конфиг
    Ctrl+Shift+P → "SFTP: Config"
    Откроется sftp.json:
    {
        "name": "mima_g_01",
        "host": "72.56.29.69",
        "username": "root",
        "password": null,
        "privateKeyPath": "C:\\Users\\<user>\\.ssh\\id_ed25519_mima",
        "remotePath": "/root/hermes-workspace",
        "uploadOnSave": true,
        "downloadOnOpen": true,
        "ignore": [".git", "node_modules", ".venv"]
    }

Шаг 3. Sync
    Ctrl+Shift+P → "SFTP: Sync Local → Remote"
    или Ctrl+Shift+P → "SFTP: Sync Remote → Local"

Где кликать:
- 1 клик Sync (после каждой правки)
- uploadOnSave: автоматически при сохранении

Плюсы:
- ✅ Не нужен Remote-SSH workspace
- ✅ Upload on save = автосинхронизация
- ✅ Работает с локальным VS Code

Минусы:
- ❌ Нужно явно Sync (если uploadOnSave выключен)
- ❌ Конфликты версий не разрешаются
- ❌ Нет терминала на remote (только sync)
- ❌ Нужно следить за ignore


Вариант 7. Терминал + scp (⭐⭐⭐ 3/5)
------------------------------------

Использовать встроенный терминал VS Code + scp команды.

Шаг 1. Открыть встроенный терминал
    Ctrl+` (или Terminal → New Terminal)

Шаг 2. Копировать файл вручную
    scp /local/path/file.txt root@mima-g-01:/root/hermes-workspace/

Шаг 3. Копировать с remote на local
    scp root@mima-g-01:/root/hermes-workspace/file.txt /local/path/

Шаг 4. Или редактировать напрямую через ssh
    ssh root@mima-g-01 nano /root/hermes-workspace/file.txt

Где кликать:
- Открыть терминал (1 клик)
- Написать scp команду (несколько секунд)
- Подождать пока скопируется

Плюсы:
- ✅ Не нужны расширения
- ✅ Полный контроль
- ✅ Работает где угодно

Минусы:
- ❌ Много ручных действий
- ❌ Нужно помнить пути
- ❌ Нет визуального sync


Вариант 8. SSHFS / WinFsp (⭐⭐⭐ 3/5)
-------------------------------------

Монтировать remote файловую систему как локальный диск.

Шаг 1. Установить WinFsp
    https://winfsp.dev/
    Install

Шаг 2. Установить SSHFS-Win
    https://github.com/billziss-gh/sshfs-win
    Install

Шаг 3. Подключить remote
    В проводнике:
    \\sshfs\\root@72.56.29.69!22\root\hermes-workspace

    Или через net use:
    net use Z: \\sshfs\\root@72.56.29.69!22\root\hermes-workspace

Шаг 4. Открыть VS Code
    File → Open Folder → Z:\workspace

Плюсы:
- ✅ Remote файлы как локальный диск
- ✅ Работают все программы

Минусы:
- ❌ SSHFS-Win бывает медленным
- ❌ Конфликты при потере сети
- ❌ Нет специфичной интеграции с VS Code


Вариант 9. Git remote + push (⭐⭐⭐ 3/5)
----------------------------------------

Использовать Git для синхронизации через удалённый репозиторий.

Шаг 1. На Windows — клонировать repo
    git clone git@github.com:user/hermes-workspace.git
    cd hermes-workspace

Шаг 2. На mima_g_01 — клонировать тот же repo
    git clone git@github.com:user/hermes-workspace.git
    cd hermes-workspace

Шаг 3. На Windows — редактировать + push
    [правки]
    git add .
    git commit -m "..."
    git push

Шаг 4. На mima_g_01 — pull
    ssh root@mima-g-01 "cd /root/workspace && git pull"

Где кликать:
- Правки + commit + push (3 действия)
- Отдельная SSH команда для pull

Плюсы:
- ✅ История изменений
- ✅ Можно работать offline
- ✅ Стандартный workflow

Минусы:
- ❌ Каждый push = ручной pull на remote
- � Merge конфликты если редактируешь оба места
- ❌ Нужен GitHub/GitLab


Часть III. Неудобные варианты (2 балла)
========================================


Вариант 10. VS Code + tmux на remote (⭐⭐ 2/5)
---------------------------------------------

Использовать tmux на mima_g_01 для долгих сессий.

Шаг 1. На mima_g_01 — запустить tmux
    ssh root@mima-g-01
    tmux new -s workspace

Шаг 2. Редактировать в nano/vim
    nano /root/workspace/file.txt
    # или
    vim /root/workspace/file.txt

Шаг 3. На Windows — подключиться к тому же tmux
    ssh -t root@mima-g-01 "tmux attach -t workspace"

Где кликать:
- SSH (1 клик)
- tmux команды (вручную)

Плюсы:
- ✅ Сессия переживает обрыв SSH
- ✅ Можно работать где угодно
- ✅ Не зависит от VS Code

Минусы:
- ❌ Нет GUI редактора
- ❌ Только text-mode (nano/vim)
- ❌ Нет IntelliSense


Вариант 11. File watcher + auto-pull (⭐⭐ 2/5)
---------------------------------------------

Сделать авто-pull на mima_g_01 через cron или systemd.

Шаг 1. На Windows — редактировать локальную копию
    cd C:\\Users\\<user>\\workspace
    [правки]
    git push

Шаг 2. На mima_g_01 — настроить cron
    crontab -e
    */5 * * * * cd /root/workspace && git pull

Где кликать:
- Правки + push (как в Вариант 9)
- Ждать 5 минут до pull

Плюсы:
- ✅ Автоматическая синхронизация
- ✅ Сессия переживает обрывы

Минусы:
- ❌ Задержка до 5 минут
- ❌ Если забыл push — изменения не доедут
- ❌ Может затереть твои правки на remote


Вариант 12. Двойной буфер обмена (⭐⭐ 2/5)
-------------------------------------------

Копировать содержимое через буфер обмена.

Шаг 1. На Windows — выделить текст
    Ctrl+C

Шаг 2. В ACP чате — попросить агента
    "вот текст, примени его к файлу /root/X"

Шаг 3. Вставить
    Ctrl+V в чат

Шаг 4. Агент применяет
    Через patch или write_file

Где кликать:
- Копировать (2 клика)
- Вставить в чат (1 клик)

Плюсы:
- ✅ Не нужны SSH/расширения
- ✅ Работает где угодно

Минусы:
- ❌ Длинные файлы не помещаются в буфер
- � Бинарные файлы не работают
- ❌ Нет структуры (теряется подсветка синтаксиса)


Вариант 13. Email + cron (⭐⭐ 2/5)
-----------------------------------

Отправлять файлы по email, агент забирает.

Шаг 1. Отправить email
    mail -A file.txt user@mima-g-01.local

Шаг 2. На mima_g_01 — fetch через cron
    */5 * * * * fetchmail -u user mima-g-01.local

Где кликать:
- Email команды (несколько)
- Настройка почтового сервера

Плюсы:
- ✅ Работает через любой firewall
- ✅ История в почтовом клиенте

Минусы:
- ❌ Задержка до 5 минут
- ❌ Сложная настройка
- ❌ Attachments могут ломаться


Часть IV. Совсем неудобные (1 балл)
====================================


Вариант 14. Ручное копирование через web UI (⭐ 1/5)
----------------------------------------------------

Шаг 1. На mima_g_01 — поднять http сервер
    python3 -m http.server 8080 --directory /root/workspace

Шаг 2. На Windows — скачать через браузер
    http://72.56.29.69:8080/file.txt

Шаг 3. Поправить, загрузить обратно

Где кликать:
- Запустить сервер (вручную)
- Браузер (несколько кликов)
- Загрузить обратно

Плюсы:
- ✅ Работает без SSH

Минусы:
- ❌ Очень много ручных действий
- ❌ Безопасность (http без auth)
- ❌ Конфликты при параллельной работе


Вариант 15. Копирование через Telegram (⭐ 1/5)
-----------------------------------------------

Шаг 1. Агент отправляет файл в Telegram
    [через send_file tool]

Шаг 2. Ты скачиваешь
    В Telegram клиенте

Шаг 3. Редактируешь локально
    [правки]

Шаг 4. Отправляешь обратно агенту как attachment
    [через Telegram]

Где кликать:
- Много кликов в Telegram

Плюсы:
- ✅ Работает на любом устройстве
- ✅ Файлы в истории чата

Минусы:
- ❌ Telegram имеет лимит на размер файлов (50 MB)
- ❌ Много переключений
- ❌ Нет структуры проекта


Вариант 16. Файлы по одному через чат (⭐ 1/5)
----------------------------------------------

Шаг 1. В ACP чате: "прочитай /root/X.txt"

Шаг 2. Я читаю, показываю содержимое

Шаг 3. Ты копируешь вывод чата

Шаг 4. Редактируешь

Шаг 5. Вставляешь обратно: "вот содержимое, сохрани в /root/Y.txt"

Где кликать:
- Только чат

Плюсы:
- ✅ Минимум настроек

Минусы:
- ❌ Очень медленно
- ❌ Теряется форматирование
- ❌ Большие файлы не помещаются


Сводная таблица
===============

Вариант                  Удобство  Скорость  Сложность  Что нужно
------------------------  --------  --------  ---------  ----------
1. Remote-SSH workspace   5/5       быстро    средне     Remote-SSH ext
2. ACP + Workspace attach 4/5       средне    низкая     ACP ext
3. Remote-SSH + ACP       5/5       быстро    высокая    Remote-SSH + ACP
4. WSL + Remote-SSH       5/5       быстро    средняя    WSL
5. Multi-root workspace   5/5       быстро    низкая     .code-workspace
6. SFTP-расширение        3/5       средне    низкая     SFTP ext
7. Терминал + scp         3/5       медленно  низкая     нет
8. SSHFS / WinFsp         3/5       медленно  средняя    SSHFS-Win
9. Git remote + push      3/5       средне    средняя    GitHub
10. tmux + nano/vim       2/5       медленно  средняя    tmux
11. Watcher + auto-pull   2/5       средне    средняя    cron
12. Clipboard             2/5       медленно  низкая     нет
13. Email + cron          2/5       медленно  высокая    почта
14. Web UI + http.server  1/5       медленно  средняя    http.server
15. Telegram              1/5       медленно  низкая     Telegram
16. Файлы через чат       1/5       очень     нет        только чат
                           медленно


Рекомендация
============

Для твоего случая (VS Code Windows + Hermes mima_g_01 +
разработка скиллов):

⭐ **Вариант 3: Remote-SSH + ACP** — лучший баланс.

Если сложно с настройкой Remote-SSH workspace с ACP —
начни с **Варианта 1: Remote-SSH workspace** (без ACP чата).
Потом добавь ACP extension в remote.

Если совсем не хочется Remote-SSH — **Вариант 2: ACP + Workspace
attach** — работает локально, но с явным прикреплением файлов.

Если нужен fallback (вдруг что-то сломается) — **Вариант 7:
Терминал + scp** — самый надёжный, работает всегда.


Что выбрать если
================

Если ты делаешь "правишь руками → проверяешь со мной → запускаешь":

→ **Вариант 1 или 3** (Remote-SSH + опционально ACP)

Если ты работаешь с одним проектом долго:

→ **Вариант 5** (Multi-root workspace) — видишь обе стороны

Если у тебя нестабильный интернет:

→ **Вариант 6** (SFTP) с uploadOnSave — работает даже
   при кратковременных обрывах (sync после reconnect)

Если у тебя нет SSH-ключа и лень настраивать:

→ **Вариант 14** (web UI) — для разовых задач


Пошаговая установка лучшего варианта (3)
=========================================

Шаг 1. Подготовка SSH (один раз)

    PowerShell:
        Test-Path C:\Users\<user>\.ssh
        # если False:
        New-Item -ItemType Directory -Force -Path $HOME\.ssh

    Скопировать ключ (если нет):
        ssh-keygen -t ed25519 -f $HOME\.ssh\id_ed25519_mima
        # публичный ключ показать и добавить в authorized_keys

Шаг 2. Настроить SSH config

    C:\Users\<user>\.ssh\config:
    Host mima-g-01
        HostName 72.56.29.69
        User root
        Port 22
        IdentityFile C:\Users\<user>\.ssh\id_ed25519_mima
        IdentitiesOnly yes
        ServerAliveInterval 30
        ServerAliveCountMax 6

Шаг 3. Проверить SSH

    ssh root@mima-g-01 "echo ok"
    # → ok

Шаг 4. Установить Remote-SSH

    VS Code → Extensions → "Remote-SSH" (Microsoft) → Install

Шаг 5. Подключиться

    Ctrl+Shift+P → "Remote-SSH: Connect to Host" → mima-g-01
    # VS Code установит server на mima_g_01 (300 MB)

Шаг 6. Открыть папку

    File → Open Folder → /root/.hermes/skills

Шаг 7. Установить extensions в remote

    Когда VS Code спросит — Yes, install
    Extensions → установить python, yaml, strato-space.acp-plugin

Шаг 8. Настроить ACP

    Remote VS Code → Ctrl+, → settings.json:
    {
        "agent_servers": {
            "hermes-default": {
                "command": "/usr/local/lib/hermes-agent/venv/bin/hermes-acp",
                "env": {"HERMES_PROFILE": "default"}
            }
        },
        "acp.streamIdleTimeout": 1800,
        "acp.connectTimeoutMs": 1800000
    }

Шаг 9. Тест

    Ctrl+Shift+P → "ACP: Connect"
    Должен открыться чат
    Написать: "прочитай ~/.hermes/skills/ и расскажи что есть"

Готово. Это занимает ~10 минут настройки, после чего всё
работает прозрачно.


Что делать если что-то не работает
==================================

Symptom: VS Code не видит remote папку
→ Ctrl+Shift+P → Remote-SSH: Kill VS Code Server on Host
→ переподключиться

Symptom: ACP чат зависает
→ Output → ACP Traffic → посмотреть последний chunk
→ если зависло > 5 минут — Ctrl+Shift+P → ACP: Restart Session

Symptom: "Permission denied" при открытии файла
→ проверить права на remote: ls -la /root/file
→ chmod если нужно

Symptom: "No space left on device"
→ на remote: df -h
→ очистить ~/.cache если нужно

Symptom: Remote-SSH отключается через 5 минут
→ проверить настройки из playbook VS-CODE-и-агент-HERMES-01.md


Связанные playbook
==================

- VS-CODE-и-агент-HERMES-01.md — общие настройки, предотвращение
  обрывов сессии. ОБЯЗАТЕЛЬНО прочитай первым.

- Совместная_работа_VSCode_и_агент_01.txt — workflow правки скиллов.

- strato-space-acp-playbook.md — настройка ACP extension.

- Hermes-Chat-VS-Code-Setup.md — альтернативный ACP клиент
  (poppywu124.hermes-chat).


Конец playbook.

