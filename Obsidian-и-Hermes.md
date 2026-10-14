# Obsidian/SilverBullet + Hermes: подробная инструкция

**Статус:** ИССЛЕДОВАНИЕ. Ничего не устанавливаем. Готовим инструкции на будущее.

## Зачем этот файл

Изучаем возможность подключить **Obsidian-совместимое хранилище знаний** как постоянную базу для скиллов, памяти и контекста Hermes. Цели:

1. **Persistent shared knowledge base** — заметки выживают между сессиями и доступны всем агентам
2. **Граф связей** — визуализация через `[[wikilinks]]` какие скиллы к каким проектам привязаны
3. **HTTP API** — Hermes читает/пишет заметки через `curl`, без монолитной БД
4. **Self-hosted** — данные остаются на mima_g_01, без облака

## Часть 1. Изучение ситуации

### 1.1 Среда mima_g_01 (актуальный срез)

| Параметр | Значение |
|---|---|
| OS | Ubuntu 24.04.4 LTS |
| Kernel | 6.8.0-134-generic |
| Arch | x86_64 |
| RAM | 2.4 GB (из них 1.4 GB свободно) |
| Disk `/` | 77 GB всего, 69 GB свободно (10% занято) |
| `/root` | 2.4 GB занято |
| User | root |
| SSH | port 22, работает |
| Zabbix agent | port 10050 (мониторинг) |
| systemd-resolve | 127.0.0.53:53 (DNS) |

**Свободные ресурсы:** ~65 GB диска, ~1.4 GB RAM, полный root-доступ. Серебряная пуля + Dataview не выжрет и 200 MB.

### 1.2 Что уже установлено

| Компонент | Версия | Назначение |
|---|---|---|
| Python | 3.11.15 | стек Hermes |
| Node | 22.22.3 | для альтернатив (см. ниже) |
| npm | 10.9.8 | для альтернатив |
| git | 2.43.0 | версионирование vault |
| curl | 8.5.0 | HTTP-вызовы |
| OfficeCLI | 1.0.139 | для конвертации .md → .docx |
| graphviz | 2.42.2 | для BPMN |
| tiktoken | (Python) | подсчёт токенов |

### 1.3 Что НЕ установлено (но потребуется)

| Компонент | Для чего | Размер |
|---|---|---|
| **Deno** ≥ 2.0 | Runtime для SilverBullet | ~50 MB |
| **SilverBullet** | Серверный PKM | ~30 MB |
| **systemd-resolved** или **nginx** | Reverse proxy / TLS | уже частично есть |
| **certbot** (опционально) | Let's Encrypt | ~30 MB |

### 1.4 Занятые порты (чтобы не пересечься)

| Порт | Сервис | Что делать |
|---|---|---|
| 22 | sshd | не трогать |
| 10050 | zabbix | не трогать |
| 53 | systemd-resolve | не трогать |
| 3000 | свободен | **подходит для SilverBullet** |
| 8080 | свободен | альтернатива для WEB |
| 8443 | свободен | для HTTPS (если выставлять наружу) |

**Рекомендация:** SilverBullet слушает `127.0.0.1:3000` (только локально), наружу выставлять через SSH-туннель или `nginx + certbot`.

## Часть 2. Сравнение вариантов

### 2.1 Obsidian vs SilverBullet vs альтернативы

| Критерий | Obsidian | SilverBullet | TriliumNext | Logseq | AppFlowy |
|---|---|---|---|---|---|
| **Тип** | Десктоп | Сервер | Сервер | Десктоп | Сервер |
| **License** | Free (commercial sync) | MIT | MIT | AGPL | AGPL |
| **Формат** | `.md` + `.canvas` | `.md` + `.yaml` | `.sqlite` + `.md` | `.org` + `.md` | PostgreSQL |
| **Wikilinks** | ✅ `[[]]` | ✅ `[[]]` | ⚠️ вручную | ✅ `[[]]` | ❌ блоки |
| **Frontmatter** | ✅ YAML | ✅ YAML | ✅ | ⚠️ | ✅ |
| **Self-hosted** | ❌ нет | ✅ легко | ✅ легко | ⚠️ сложно | ✅ легко |
| **REST API** | плагин Local REST API | встроен | встроен | ❌ | встроен |
| **Multi-user** | ❌ single user | ✅ сессии | ✅ с auth | ❌ | ✅ |
| **Mobile** | ✅ iOS/Android | ⚠️ web only | ⚠️ web only | ✅ iOS/Android | ⚠️ web only |
| **Плагины** | 1500+ JS | 50+ JS/Lua | плагины | Clojure | SQL |
| **Требования** | macOS/Win/Linux | Deno 2+ | Node 18+ | JVM | Docker |
| **Ресурсы** | 300 MB RAM | 50 MB RAM | 200 MB RAM | 500 MB RAM | 300 MB RAM |
| **Obsidian-совместимость** | 100% | ~80% | ~30% | ~50% | 0% |

### 2.2 Почему **SilverBullet** для Hermes

| Плюс | Почему важно для Hermes |
|---|---|
| **Серверный** | Работает на mima_g_01 headless, без GUI |
| **Plain `.md` на диске** | Те же файлы, что уже есть в `/root/*.md` |
| **Built-in HTTP API** | Hermes обращается через `curl` без плагинов |
| **Deno runtime** | Безопасный, TypeScript-first, JSR-пакеты |
| **Active development** | 500+ коммитов, обновляется еженедельно |
| **Plug API** | Lua/JS-скрипты внутри заметок |
| **Multi-user из коробки** | Каждый пользователь — отдельная сессия |
| **Web-интерфейс** | localhost:3000 — редактор через браузер |

### 2.3 Когда выбрать Obsidian

- Работа в дороге (мобильное приложение)
- Привычка к desktop UX
- Нет доступа к SSH на mima_g_01

### 2.4 Когда SilverBullet НЕ подойдёт

- Если нужны `.canvas` (miro-подобные доски) — нет, это exclusive Obsidian
- Если нужны **community плагины Obsidian** (1.500 штук) — да, многое доступно, но не всё
- Если критична **оффлайн-работа** в поле — SilverBullet требует сервер

## Часть 3. Архитектура интеграции

### 3.1 Текущая структура Hermes (до интеграции)

```
mima_g_01
├── /root/.hermes/
│   ├── SOUL.md                  ← kernel prompt
│   ├── MEMORY.md                ← заметки агента
│   ├── USER.md                  ← профиль пользователя
│   └── skills/
│       ├── officecli/SKILL.md
│       ├── memory-hygiene/SKILL.md
│       └── failsafe-rules/SKILL.md
└── /root/                       ← рабочие файлы
    ├── Плейсхолдеры-FIMA-01.md
    ├── Шапка-в-FIGMA.md
    ├── Таблица-в-FIGMA.md
    ├── Динамические-цвета-в-FIGMA.md
    ├── Палитра-в-FIGMA.md
    ├── Компонент-с-вариантами.md
    ├── Подсветка-строк-в таблице.md
    ├── SETUP_01.txt
    └── ... (ещё 30+ файлов)
```

### 3.2 Целевая структура (после интеграции SilverBullet)

```
mima_g_01
├── /root/.hermes/                       ← без изменений
│   ├── SOUL.md
│   ├── MEMORY.md
│   ├── USER.md
│   └── skills/
│       └── ...
├── /root/vault/                         ← НОВАЯ ПАПКА (SilverBullet)
│   ├── index.md                         ← корневая
│   ├── 📁 00 Мета                        ← теги #meta
│   │   ├── README.md                    ← описание vault
│   │   ├── Конвенции.md                 ← правила именования
│   │   └── Changelog.md
│   ├── 📁 01 Гермес                      ← теги #hermes
│   │   ├── SOUL.md                      ← symlink на /root/.hermes/SOUL.md
│   │   ├── MEMORY.md                    ← symlink
│   │   ├── USER.md                      ← symlink
│   │   ├── Настройка-шлюза.md
│   │   ├── PM-SKILL.md
│   │   └── Slug-генерация.md
│   ├── 📁 02 Skills                      ← теги #skill
│   │   ├── memory-hygiene.md
│   │   ├── failsafe-rules.md
│   │   ├── officecli.md
│   │   └── ...
│   ├── 📁 03 Проекты                     ← теги #project
│   │   ├── Космодром-Жуковский-504-595.md
│   │   ├── project_504-595_здоровье.md
│   │   └── ...
│   ├── 📁 04 Figma-Workflow              ← теги #figma
│   │   ├── Плейсхолдеры-FIMA.md
│   │   ├── Шапка.md
│   │   ├── Таблица.md
│   │   ├── Динамические-цвета.md
│   │   ├── Палитра.md
│   │   ├── Компонент-открывашка.md
│   │   └── Подсветка-строк.md
│   ├── 📁 05 Документация                ← теги #doc
│   │   ├── SETUP.md
│   │   ├── Шлюз-Профиля.md
│   │   ├── Slug-Генерация.md
│   │   ├── SKILL-данные.md
│   │   └── ...
│   ├── 📁 06 Заметки                     ← теги #note
│   │   ├── 2026-07-31 Obsidian-и-Hermes.md
│   │   └── ...
│   └── 📁 99 Шаблоны                     ← теги #template
│       ├── TPL-отчёт-проекта.md
│       ├── TPL-замечание.md
│       └── TPL-скилл.md
└── /root/.silverbullet/                  ← конфиг SB
    ├── CONFIG.md
    └── PLUGS/
        ├── git.lua                      ← авто-коммит в git
        ├── dataview.lua                 ← SQL по frontmatter
        └── ...
```

### 3.3 Связь Hermes ↔ vault

```
┌─────────────────────────────────────────────────────┐
│                   Hermes Agent                       │
│                                                      │
│   skill_view("figma")  ─┐                            │
│   read_file("MEMORY.md") │                           │
│   search("проект_504")   │                           │
│                         │                            │
│   ┌─────────────────────┴──────────────────────┐    │
│   │  Hermes Tools (read_file, search_files,    │    │
│   │  skill_view, write_file, terminal)         │    │
│   └─────────────────────┬──────────────────────┘    │
│                         │                            │
│                         ▼                            │
│   ┌─────────────────────────────────────────────┐   │
│   │  SB-Adapter (Python или просто curl)        │   │
│   │  base_url: http://127.0.0.1:3000            │   │
│   │  или прямой доступ к /root/vault/*.md       │   │
│   └─────────────────────┬───────────────────────┘   │
│                         │                            │
└─────────────────────────┼────────────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────┐
        │  SilverBullet (127.0.0.1:3000)       │
        │  или прямой доступ к /root/vault/   │
        │  • GET /index.md                    │
        │  • search ?q=figma+placeholder      │
        │  • query/?Query                     │
        └─────────────────────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────┐
        │  /root/vault/ (plain .md файлы)     │
        │  + .git (бэкап и версионирование)   │
        └─────────────────────────────────────┘
```

### 3.4 Сценарии доступа

| Сценарий | Способ |
|---|---|
| Чтение заметки в контексте Hermes | `read_file("/root/vault/02 Skills/officecli.md")` — **без SilverBullet** |
| Запись отчёта после выполнения задачи | `terminal: curl -X POST http://127.0.0.1:3000/vault/06-Notes/...` |
| Поиск по всем скиллам | `search_files("figma", path="/root/vault/")` — **без SB** |
| Полнотекстовый поиск с подсветкой | `curl http://127.0.0.1:3000/search?q=figma&context=10` |
| Граф связей | открыть `http://127.0.0.1:3000` в браузере |
| Dataview-индекс | `curl http://127.0.0.1:3000/query?Query=...` |
| Multi-user редактирование | Web-интерфейс SB, каждый со своей сессией |

## Часть 4. Пошаговая инструкция установки

> ⚠️ **СТАТУС:** Инструкция готова. **Не выполняется.** Будет применена когда решите перейти к внедрению.

### Шаг 1. Подготовка

```bash
# 1.1 Создать директорию vault
mkdir -p /root/vault /root/.silverbullet
cd /root/vault

# 1.2 Инициализировать git (опционально, для бэкапа)
git init -b main
git config user.email "hermes@mima_g_01.local"
git config user.name "Hermes Agent"

# 1.3 Создать index.md
cat > index.md << 'EOF'
---
title: Mima_g_01 Vault
tags: #meta
---

# Корневая страница знаний Hermes

Этот vault — shared knowledge base для Hermes.

## Структура
- [[00 Мета]] — конвенции, changelog
- [[01 Гермес]] — SOUL, MEMORY, USER, настройки
- [[02 Skills]] — описание скиллов
- [[03 Проекты]] — заметки по проектам
- [[04 Figma-Workflow]] — playbook'и Figma→HTML
- [[05 Документация]] — SETUP, шлюзы, инструкции
- [[06 Заметки]] — журнал сессий
- [[99 Шаблоны]] — TPL-*

Создано: 2026-07-31
EOF
```

### Шаг 2. Установка Deno

```bash
# 2.1 Скачать установщик (проверить .sha256sum после)
curl -fsSL https://deno.land/install.sh -o /tmp/deno_install.sh
cat /tmp/deno_install.sh | head -3   # краткий просмотр

# 2.2 Запустить установку
DENO_INSTALL=/root/.deno sh /tmp/deno_install.sh

# 2.3 Добавить в PATH (одноразово для текущей сессии)
export PATH="/root/.deno/bin:$PATH"

# 2.4 Проверить
deno --version                         # ожидаем: deno 2.x.x

# 2.5 Сделать PATH постоянным
echo 'export PATH="/root/.deno/bin:$PATH"' >> /root/.bashrc
```

**Альтернативный способ (apt):**
```bash
# Может быть доступно в apt, но часто отстаёт по версии
apt list --installed 2>/dev/null | grep deno
sudo apt install -y deno || echo "Через install.sh предпочтительнее"
```

### Шаг 3. Установка SilverBullet

```bash
# 3.1 Скачать бинарь (latest release)
curl -fsSL https://github.com/silverbulletmd/silverbullet/releases/latest/download/silverbullet-x86_64-unknown-linux-gnu.zip -o /tmp/sb.zip

# 3.2 Проверить SHA-256 (сверять с release notes)
# ожидаем файл /tmp/sb.zip.sha256 рядом со скачанным
curl -fsSL https://github.com/silverbulletmd/silverbullet/releases/latest/download/silverbullet-x86_64-unknown-linux-gnu.zip.sha256 -o /tmp/sb.zip.sha256
sha256sum -c /tmp/sb.zip.sha256

# 3.3 Распаковать
mkdir -p /opt/silverbullet
unzip -d /opt/silverbullet /tmp/sb.zip
chmod +x /opt/silverbullet/silverbullet

# 3.4 Создать симлинк в PATH
ln -sf /opt/silverbullet/silverbullet /usr/local/bin/silverbullet

# 3.5 Проверить
silverbullet --version
```

### Шаг 4. Конфигурация SilverBullet

```bash
# 4.1 Создать конфиг
mkdir -p /root/.config/silverbullet
cat > /root/.config/silverbullet/CONFIG.md << 'EOF'
---
title: Config
tags: #config
---

```yaml
# Public URL для веб-интерфейса
publicUrl: http://127.0.0.1:3000

# Bind address (только localhost по умолчанию)
bindAddress: 127.0.0.1

# Порт
port: 3000

# Authenticated sessions
# - "ro": только чтение
# - "rw": чтение + запись
# - "admin": чтение + запись + плагины
auth:
  user1:password1:rw
  user2:password2:ro

# Read-only режим (false = можно редактировать)
readOnly: false

# Background sync (опционально)
syncOnly: false

# Plug directory для плагинов
plugFolders:
  - /root/.silverbullet/PLUGS
EOF
```

> ⚠️ **NB:** формат `username:password:role` — слабый. В продакшне нужно:
> - Сгенерировать bcrypt-хэши: `htpasswd -nbB user pass`
> - Указать `authFile: /root/.silverbullet/users.htpasswd`
> - Выставить через nginx + TLS

### Шаг 5. Запуск (первый раз)

```bash
# 5.1 Запустить в фоне с логом
nohup silverbullet /root/vault > /var/log/silverbullet.log 2>&1 &
echo $! > /var/run/silverbullet.pid

# 5.2 Дождаться старта
sleep 3
tail -20 /var/log/silverbullet.log

# 5.3 Проверить HTTP
curl -sI http://127.0.0.1:3000/
# ожидаем HTTP/1.1 200 OK
```

### Шаг 6. systemd unit (для авто-старта)

```bash
# 6.1 Создать unit
cat > /etc/systemd/system/silverbullet.service << 'EOF'
[Unit]
Description=SilverBullet PKM server
Documentation=https://github.com/silverbulletmd/silverbullet
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/vault
ExecStart=/usr/local/bin/silverbullet /root/vault --config /root/.config/silverbullet/CONFIG.md
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal

# Hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/root/vault /root/.silverbullet

[Install]
WantedBy=multi-user.target
EOF

# 6.2 Активировать
systemctl daemon-reload
systemctl enable silverbullet
systemctl start silverbullet

# 6.3 Статус
systemctl status silverbullet
```

### Шаг 7. Доступ через web-интерфейс

```bash
# Извне через SSH-туннель (РЕКОМЕНДУЕТСЯ)
ssh -L 3000:127.0.0.1:3000 user@mima_g_01
# На локальной машине открыть http://127.0.0.1:3000 — увидим SB

# Или через nginx reverse proxy (если SilverBullet нужно выставить на 443)
# /etc/nginx/sites-available/silverbullet.conf:
server {
  listen 8443 ssl;
  server_name vault.mima_g_01.local;
  ssl_certificate /etc/letsencrypt/live/vault.mima_g_01.local/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/vault.mima_g_01.local/privkey.pem;
  location / {
    proxy_pass http://127.0.0.1:3000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  }
}
```

### Шаг 8. Local REST API (ВАРИАНТ A — через web-протокол SB)

> ⚠️ **ВАЖНО:** SilverBullet **имеет встроенный HTTP API**, но он **НЕ** полный REST как у Obsidian. Проверьте текущую версию (на момент 2026-07-31):

| Эндпоинт | Метод | Описание |
|---|---|---|
| `/` | GET | Web UI |
| `/login` | GET/POST | Auth |
| `/fs/...` | GET | Читать файл |
| `/fs/...` | PUT | Записать файл |
| `/command/...` | POST | Выполнить команду SB |
| `/query` | GET | Dataview-запрос |

**Пример:**
```bash
# Прочитать файл
curl -u user:pass http://127.0.0.1:3000/fs/index.md

# Записать файл
curl -u user:pass -X PUT \
  --data-binary @new-note.md \
  http://127.0.0.1:3000/fs/06-Заметки/2026-08-01.md

# Dataview
curl -u user:pass 'http://127.0.0.1:3000/query?query=TABLE%20file.link%20FROM%20%23skill'
```

> ⚠️ **NB:** Актуальный API может отличаться. Перед использованием смотреть [docs.silverbullet.md](https://silverbullet.md) и/или `silverbullet --help`.

### Шаг 9. Альтернатива: прямой доступ к vault (Вариант B)

Если SilverBullet не запущен или нужен прямой доступ — Hermes работает с vault как обычной папкой:

```bash
# Чтение через read_file
# Это работает ВСЕГДА, даже если SB не запущен
read_file("/root/vault/02 Skills/officecli.md")

# Запись
write_file("/root/vault/06 Заметки/2026-08-01.md", content)

# Поиск
search_files("figma", path="/root/vault/")
```

**Это самый простой подход.** SilverBullet добавляет:
- Web-интерфейс для визуального редактирования
- Граф связей
- Dataview (SQL по frontmatter)
- Live preview

Если нужен только persistent shared storage — **можно без SB**.

## Часть 5. Миграция существующих файлов

### 5.1 Перенос 30+ файлов из `/root/` в vault

```bash
# 5.1.1 Создать подкаталоги
mkdir -p /root/vault/04\ Figma-Workflow
mkdir -p /root/vault/05\ Документация

# 5.1.2 Скопировать Figma-playbook'и
cp /root/Плейсхолдеры-FIMA-01.md "/root/vault/04 Figma-Workflow/Плейсхолдеры.md"
cp /root/Шапка-в-FIGMA.md         "/root/vault/04 Figma-Workflow/Шапка.md"
cp /root/Таблица-в-FIGMA.md        "/root/vault/04 Figma-Workflow/Таблица.md"
cp /root/Динамические-цвета-в-FIGMA.md "/root/vault/04 Figma-Workflow/Динамические-цвета.md"
cp /root/Палитра-в-FIGMA.md        "/root/vault/04 Figma-Workflow/Палитра.md"
cp "/root/Компонент-с-вариантами.md" "/root/vault/04 Figma-Workflow/Компонент-открывашка.md"
cp "/root/Подсветка-строк-в таблице.md" "/root/vault/04 Figma-Workflow/Подсветка-строк.md"

# 5.1.3 Скопировать документацию
cp /root/SETUP_01.txt          "/root/vault/05 Документация/SETUP.md"
cp /root/Шлюз-Профиля-01.txt   "/root/vault/05 Документация/Шлюз-Профиля.md"
cp /root/Slug-Генерация-01.txt "/root/vault/05 Документация/Slug-Генерация.md"
cp /root/SKILL\ и\ его\ данные.txt "/root/vault/05 Документация/SKILL-данные.md"
cp /root/PM_SKILL_01.txt       "/root/vault/05 Документация/PM-SKILL.md"
cp /root/bpmn-to-skill.txt     "/root/vault/05 Документация/bpmn-to-skill.md"
cp /root/Вычисления_по_датам.md "/root/vault/05 Документация/Вычисления-по-дататам.md"
cp /root/Переключение_контекста_Агента_01.txt "/root/vault/05 Документация/Контекст-рот.md"
cp /root/Набор-MD-11.txt "/root/vault/05 Документация/Анализ-MD-11.md"

# 5.1.4 Скопировать 03 Проекты
cp /root/.hermes/cache/documents/doc_*.md "/root/vault/03 Проекты/project_504-595_здоровье.md"
```

### 5.2 Преобразование `.txt` → `.md`

```bash
# Простое переименование
for f in /root/vault/05\ Документация/*.txt; do
    mv "$f" "${f%.txt}.md"
done

# Если есть структура заголовков — можно оставить как есть
# SilverBullet рендерит любой .md
```

### 5.3 Добавить frontmatter (если отсутствует)

```bash
# Шаблон frontmatter для playbook
cat > /tmp/fm_skill.md << 'EOF'
---
tags: #figma #workflow
type: playbook
created: 2026-07-31
status: active
related: "[[Палитра]]" "[[Шапка]]" "[[Таблица]]"
---
EOF

# Добавить в начало каждого файла
for f in /root/vault/04\ Figma-Workflow/*.md; do
    # Если frontmatter отсутствует (нет --- в начале)
    if ! head -1 "$f" | grep -q "^---$"; then
        cat /tmp/fm_skill.md "$f" > "${f}.tmp" && mv "${f}.tmp" "$f"
    fi
done
```

### 5.4 Создание индексной страницы Dataview

```bash
cat > "/root/vault/04 Figma-Workflow/_index.md" << 'EOF'
---
title: Figma Workflow — индекс
tags: #figma #index
---

# Figma → HTML Workflow

## Playbook
```dataview
TABLE type, status, created
FROM #figma
WHERE type = "playbook"
SORT created DESC
```

## По статусу
```dataview
LIST
FROM #figma
WHERE status = "active"
SORT file.name ASC
```

## Связи
- [[Плейсхолдеры]] → используется в: [[Шапка]], [[Таблица]]
- [[Палитра]] → используется в: [[Динамические-цвета]]
- [[Компонент-открывашка]] → содержит: [[Таблица]]
- [[Подсветка-строк]] → содержит: [[Палитра]]
```

EOF
```

## Часть 6. Интеграция с Hermes

### 6.1 Добавить SB-скилл в Hermes

```bash
# 6.1.1 Создать skill
mkdir -p /root/.hermes/skills/silverbullet

cat > /root/.hermes/skills/silverbullet/SKILL.md << 'EOF'
---
name: silverbullet
description: Work with /root/vault (SilverBullet compatible). Read/write/search markdown notes, query Dataview, manage folder structure, create templates, link notes via [[wikilinks]].
when_to_use: |
  - When you need persistent shared knowledge across sessions
  - When user asks to save a document, create a note, or search vault
  - When you need to maintain context for a long-running project
  - When you need to link related concepts (skill, project, playbook)
scripts:
  - script: sb_query.sh
    description: Run Dataview query against vault
  - script: sb_search.sh
    description: Full-text search in vault
EOF
```

### 6.2 Скрипты-обёртки

```bash
# /root/.hermes/skills/silverbullet/scripts/sb_query.sh
cat > /root/.hermes/skills/silverbullet/scripts/sb_query.sh << 'EOF'
#!/bin/bash
# Dataview query через SilverBullet
# Usage: sb_query.sh "TABLE file.link FROM #skill"
QUERY="$1"
curl -u user:pass \
  --data-urlencode "query=$QUERY" \
  -G http://127.0.0.1:3000/query
EOF
chmod +x /root/.hermes/skills/silverbullet/scripts/sb_query.sh

# /root/.hermes/skills/silverbullet/scripts/sb_search.sh
cat > /root/.hermes/skills/silverbullet/scripts/sb_search.sh << 'EOF'
#!/bin/bash
# Full-text search через ripgrep (без SB)
# Usage: sb_search.sh "figma"
QUERY="$1"
rg -i --no-heading -A 2 "$QUERY" /root/vault/
EOF
chmod +x /root/.hermes/skills/silverbullet/scripts/sb_search.sh
```

### 6.3 Обновить SOUL.md (опционально)

Добавить в раздел "Channel-aware completion" ссылку на vault:

```markdown
## Использование vault

Перед началом работы с проектом проверить `/root/vault/03 Проекты/` —
есть ли заметки по нему. Если есть — прочитать, дать ответ в контексте истории.
После завершения задачи — добавить заметку в `/root/vault/06 Заметки/`.
```

## Часть 7. Безопасность

### 7.1 Что может пойти не так

| Риск | Защита |
|---|---|
| SB слушает на 0.0.0.0 → доступ из интернета | Bind = 127.0.0.1, наружу только через nginx+TLS |
| Слабый пароль в config | Использовать bcrypt-хэши (htpasswd) |
| API key утечёт | Ротация credentials, ограничение IP через nginx |
| Vault = plain `.md` без шифрования | Полное шифрование диска (LUKS) на mima_g_01 |
| Плагин из community с backdoor | Устанавливать только проверенные, читать код |
| Заметки в vault доступны другим пользователям SSH | chmod 700 /root/vault |

### 7.2 Аудит-чеклист

```bash
# Проверить что SB работает только на localhost
ss -tlnp | grep :3000

# Проверить права на vault
ls -ld /root/vault

# Проверить git remote (если выставили vault в git)
git -C /root/vault remote -v

# Посмотреть последние изменения
git -C /root/vault log --oneline -20
```

## Часть 8. Удаление/откат

### 8.1 Если что-то пошло не так

```bash
# 8.1.1 Остановить SB
systemctl stop silverbullet
systemctl disable silverbullet

# 8.1.2 Удалить unit
rm /etc/systemd/system/silverbullet.service
systemctl daemon-reload

# 8.1.3 Удалить бинарь
rm /usr/local/bin/silverbullet
rm -rf /opt/silverbullet

# 8.1.4 Удалить Deno (если не нужен)
rm -rf /root/.deno

# 8.1.5 Vault оставить (это ваши данные!)
# Если нужно удалить:
rm -rf /root/vault

# 8.1.6 Проверить что ничего не сломалось
curl -sI http://127.0.0.1:3000/ 2>&1 || echo "SilverBullet остановлен - OK"
```

## Часть 9. Решение "делать или нет"

### 9.1 Аргументы ЗА

- Persistent shared memory: заметки переживают compaction
- Граф связей: визуально показывает отношения между скиллами/проектами
- Dataview: SQL-подобные запросы по frontmatter
- Web UI: удобное редактирование в браузере
- Multi-user: можно расшарить с другими

### 9.2 Аргументы ПРОТИВ

- +50 MB диска, +50 MB RAM, +1 сервис для мониторинга
- Дополнительная сложность (Deno, SB, nginx, сертификаты)
- Local REST API Obsidian НЕ переносится 1:1 в SilverBullet
- Frontend UX Obsidian лучше (desktop app, native performance)
- Если mima_g_01 переедет — vault надо переносить отдельно

### 9.3 Моя рекомендация

**Не запускать SB сразу.** Начать с **минимального варианта**:

1. **Создать `/root/vault/`** (просто папку)
2. **Скопировать туда существующие 30+ файлов** из `/root/`
3. **Добавить frontmatter** с тегами
4. **Создать `[[wikilinks]]`** между связанными playbook'ами
5. **Использовать через `read_file`/`write_file`/`search_files`** — без SB

**Затем, если понравится:**

6. Запустить SilverBullet локально (через SSH-туннель)
7. Проверить Dataview
8. Если используется активно — выставить через nginx + TLS

**Зачем такой порядок:**

- Zero risk на первом этапе
- Можно откатить просто удалив папку
- Hermes уже умеет работать с vault-как-папкой
- SB добавляется как enhancement, не как dependency

## Часть 10. Открытые вопросы

| Вопрос | Что нужно выяснить |
|---|---|
| Какой API у текущей версии SilverBullet? | Проверить `silverbullet --help` и docs.silverbullet.md |
| Поддерживает ли SB Plug API совместимый с Obsidian? | Изучить Plug Store |
| Dataview в SB — это плагин или встроен? | Проверить `/plug/` folder |
| Какой формат `[[wikilinks]]` с пробелами? | `[[Путь/К-Заметке]]` или `[[Имя-заметки]]` |
| Как интегрировать с Telegram? | Webhook или polling |
| Как связать с Hermes memory-hygiene? | Через skill silverbullet |

## Шпаргалка

```
ЦЕЛЬ:    Persistent shared knowledge для Hermes
ВАРИАНТ: SilverBullet (серверный Obsidian-совместимый)
СЕЙЧАС:  НЕ установлен. Изучаем.
ШАГ 1:   mkdir /root/vault + перенести файлы
ШАГ 2:   (опционально) установить Deno + SilverBullet
ШАГ 3:   (опционально) настроить nginx + TLS
ШАГ 4:   (опционально) добавить skill silverbullet
```

## Связь с другими файлами

| Файл | Что оттуда взять |
|---|---|
| `SETUP_01.txt` | Текущая структура /root/.hermes и /root/ |
| `SKILL и его данные.txt` | Как организовать данные скилла |
| `Slug-Генерация-01.txt` | Имена папок/файлов в vault |
| `PM_SKILL_01.txt` | Vault = база для project management |

## Что делать прямо сейчас

1. Прочитать этот файл
2. Решить: ZA / PROTIV / ПОЗЖЕ
3. Если ZA — выполнить минимальный шаг 1 (создать /root/vault, перенести файлы)
4. Если ПОЗЖЕ — добавить в todo: «вернуться к этому файлу через N дней»
5. Если PROTIV — забыть (этот файл останется как reference)
