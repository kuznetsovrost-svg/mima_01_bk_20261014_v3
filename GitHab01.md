# Бэкап данных агентов в GitHab — GitHab01.md

> Версия 1.0 · Markdown-зеркало инструкции `GitHab01.txt`.
> Под "GitHab" подразумевается любой Git-хостинг (GitHub / Gitea / GitLab).
> Терминология и шаги идентичны текстовой версии; здесь — якоря и
> таблицы для удобной навигации в вебе и в IDE.

## Оглавление

- [§0. Подготовка](#0-подготовка-один-раз-на-машину)
- [§1. Что именно бэкапим](#1-что-именно-бэкапим)
- [§2. Сборка снапшота](#2-сборка-снапшота)
- [§3. Инициализация локального Git-репо](#3-инициализация-локального-git-репо-архива)
- [§4. Безопасная публикация в GitHab](#4-безопасная-публикация-в-githab)
- [§5. Автоматизация (cron / systemd)](#5-автоматизация-cronsystemd)
- [§6. Восстановление из бэкапа](#6-восстановление-из-бэкапа)
- [§7. Чеклист перед сдачей](#7-чеклист-перед-сдачей)
- [§8. Бэкап SQLite-сессий](#8-бэкап-sqlite-сессий-dbsqlitesqlite3)

---

## §0. Подготовка (один раз на машину)

**0.1.** Проверить, что Git установлен и настроен.

```bash
git --version
git config --global user.name  "agent-backup-bot"
git config --global user.email "agent-backup@<ваш-домен>"
# Если работаете от root и бэкапите чужие репо — добавьте safe.directory,
# иначе Git будет ругаться на права:
git config --global --add safe.directory '*'
```

**0.2.** Создать на GitHab пустой приватный репозиторий, например
`agents-backup`. Скопировать HTTPS-URL вида

```
https://<token>@github.com/<owner>/agents-backup.git
```

где `token` — PAT с правом `repo:write`. **Никогда** не коммитьте токен
в открытый файл (см. §4.2).

**0.3.** Определить каталог-источник бэкапа:

```bash
AGENT_ROOT="/root/.hermes"
BACKUP_TMP="/var/tmp/agents-backup"
mkdir -p "$BACKUP_TMP"
```

---

## §1. Что именно бэкапим

| Источник                                          | Что внутри                                  | Критичность |
|---------------------------------------------------|---------------------------------------------|-------------|
| `$AGENT_ROOT/skills/`                             | все skills, которыми пользуются агенты      | высокая     |
| `$AGENT_ROOT/memories/`                           | долговременная память агентов               | высокая     |
| `$AGENT_ROOT/config.yaml`                         | конфиг gateway и профилей                   | высокая     |
| `$AGENT_ROOT/.env`                                | секреты — **только** если храните в vault   | условная    |
| `$AGENT_ROOT/profiles/`                           | per-profile skills/plugins/cron/memories    | высокая     |
| `/opt/agent-workspaces/`                          | внешние workspace-папки агентов             | средняя     |
| `$HOME/.claude/`, `$HOME/.codex/`                 | state-каталоги других рантаймов             | средняя     |
| `*.db` / `*.sqlite` / `*.sqlite3` (см. §8)        | сессии, индексы воспоминаний, мета skill'ов  | высокая     |

> ⚠️ Перед копированием остановите активных агентов, чтобы не снять
> полузаписанный блоб. Если остановка невозможна — `rsync --partial --inplace`
> в режиме live snapshot, а SQLite — **только** через Backup API (§8).

---

## §2. Сборка снапшота

**2.1.** Создать каталог с датой-временем:

```bash
SNAP="$BACKUP_TMP/agents-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$SNAP"
```

**2.2.** Скопировать нужное (`rsync` сохраняет права/время):

```bash
rsync -aHAX --info=stats2 \
  $AGENT_ROOT/skills/     "$SNAP/skills/"
  $AGENT_ROOT/memories/   "$SNAP/memories/"
  $AGENT_ROOT/profiles/   "$SNAP/profiles/"
  $AGENT_ROOT/config.yaml "$SNAP/config.yaml"
  /opt/agent-workspaces/  "$SNAP/workspaces/"
```

**2.3.** Упаковать в `tar.gz` с контрольной суммой:

```bash
tar -C "$BACKUP_TMP" -czf "$SNAP.tar.gz" "$(basename "$SNAP")"
sha256sum "$SNAP.tar.gz" | tee "$SNAP.tar.gz.sha256"
```

**2.4.** (Опционально) подписать GPG-ключом, которому доверяет GitHab-side policy:

```bash
gpg --batch --yes --armor --detach-sign \
    --output "$SNAP.tar.gz.asc" "$SNAP.tar.gz"
```

**2.5.** Очистить временный каталог:

```bash
rm -rf "$SNAP"
```

---

## §3. Инициализация локального Git-репо архива

**3.1.** Распаковать архив в рабочую копию:

```bash
WORK="$BACKUP_TMP/agents-repo"
rm -rf "$WORK" && mkdir -p "$WORK"
tar -C "$WORK" -xzf "$SNAP.tar.gz"
# Внутри окажется каталог с тем же именем, что и tar.gz
WORK_DATA="$WORK/$(basename "$SNAP")"
```

**3.2.** Превратить в bare-friendly зеркало:

```bash
git init -b main "$WORK_DATA"
git -C "$WORK_DATA" add -A
git -C "$WORK_DATA" commit -m "snapshot $(date -u +%FT%TZ)"
```

**3.3.** Если раньше бэкапы уже пушились — подцепить историю:

```bash
git -C "$WORK_DATA" remote add origin \
  https://<token>@github.com/<owner>/agents-backup.git
git -C "$WORK_DATA" fetch origin
git -C "$WORK_DATA" rebase origin/main || \
  git -C "$WORK_DATA" rebase --abort
```

---

## §4. Безопасная публикация в GitHab

### 4.1. Способ 1 (рекомендуемый) — SSH-ключ

```bash
ssh-keygen -t ed25519 -C "agents-backup" -f ~/.ssh/agents_backup
# Публичный ключ добавить в GitHab → Settings → Deploy keys
# (с правом write) у репозитория agents-backup.
git -C "$WORK_DATA" remote set-url origin \
  git@github.com:<owner>/agents-backup.git
```

### 4.2. Способ 2 — HTTPS + PAT

**a)** Положить токен в файл с правами `0600`:

```bash
umask 077
printf '%s' 'ghp_XX...XXXX' > /root/.gh_backup_tok
chmod 600 /root/.gh_backup_tok
```

**b)** Собрать URL из кусков, чтобы токен не светился в истории:

```bash
TOK=$(cat /root/.gh_backup_tok)
URL="https://${TOK}@github.com/<owner>/agents-backup.git"
```

**c)** Привязать remote:

```bash
git -C "$WORK_DATA" remote add origin "$URL"
```

**d)** После успешного push URL с токеном желательно стереть:

```bash
git -C "$WORK_DATA" remote set-url origin \
  https://github.com/<owner>/agents-backup.git
unset URL TOK
```

### 4.3. Залить

```bash
git -C "$WORK_DATA" push -u origin main
# Если main уже существовал:
git -C "$WORK_DATA" push origin main:main --force-with-lease
# --force-with-lease безопаснее --force: GitHab отклонит push,
# если на сервере есть коммиты, которых у вас локально нет.
```

### 4.4. Проверить, что последний коммит виден удалённо

```bash
git -C "$WORK_DATA" ls-remote origin
# В выводе должна быть ваша SHA у refs/heads/main.
```

---

## §5. Автоматизация (cron / systemd)

**5.1.** Скрипт `/usr/local/bin/agents-backup.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
AGENT_ROOT="/root/.hermes"
BACKUP_TMP="/var/tmp/agents-backup"
WORK="$BACKUP_TMP/agents-repo"
SNAP_NAME="agents-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP_TMP"
tar -C "$BACKUP_TMP" -czf "$BACKUP_TMP/$SNAP_NAME.tar.gz" \
    -C "$AGENT_ROOT" skills memories profiles config.yaml
rm -rf "$WORK" && mkdir -p "$WORK"
tar -C "$WORK" -xzf "$BACKUP_TMP/$SNAP_NAME.tar.gz"
cd "$WORK/$SNAP_NAME"
git init -q -b main .
git add -A
git -c user.name=agents-backup-bot \
    -c user.email=agents-backup@localhost \
    commit -q -m "snapshot $SNAP_NAME"
git remote remove origin 2>/dev/null || true
git remote add origin \
  "https://$(cat /root/.gh_backup_tok)@github.com/<owner>/agents-backup.git"
git push -q origin main:main --force-with-lease
echo "OK $SNAP_NAME"
```

```bash
chmod 700 /usr/local/bin/agents-backup.sh
```

**5.2.** Запускать ежедневно в `03:17` через systemd timer:

`/etc/systemd/system/agents-backup.service`
```ini
[Unit]
Description=Agents data backup to GitHab
[Service]
Type=oneshot
ExecStart=/usr/local/bin/agents-backup.sh
```

`/etc/systemd/system/agents-backup.timer`
```ini
[Unit]
Description=Daily agents backup
[Timer]
OnCalendar=*-*-* 03:17:00
Persistent=true
[Install]
WantedBy=timers.target
```

```bash
systemctl daemon-reload
systemctl enable --now agents-backup.timer
```

**5.3.** Проверить, что таймер жив:

```bash
systemctl list-timers agents-backup.timer
journalctl -u agents-backup.service -n 50 --no-pager
```

---

## §6. Восстановление из бэкапа

**6.1.** Склонировать целиком:

```bash
git clone https://github.com/<owner>/agents-backup.git /tmp/restore
ls /tmp/restore/   # список снапшотов-каталогов
```

**6.2.** Достать нужный снапшот:

```bash
tar -C / -xzf /tmp/restore/agents-YYYYMMDDTHHMMSSZ.tar.gz
# либо распаковать вручную:
tar -xzf agents-YYYYMMDDTHHMMSSZ.tar.gz -C /tmp/restore/one
```

**6.3.** Верифицировать подпись/контрольную сумму:

```bash
sha256sum -c agents-YYYYMMDDTHHMMSSZ.tar.gz.sha256
gpg --verify agents-YYYYMMDDTHHMMSSZ.tar.gz.asc \
            agents-YYYYMMDDTHHMMSSZ.tar.gz
```

**6.4.** Скопировать восстановленные данные на штатные места
(`skills → $AGENT_ROOT/skills/` и т. д.), затем:

```bash
systemctl --user restart hermes-gateway    # если конфиг менялся
```

---

## §7. Чеклист перед сдачей

- [ ] `.gitignore` исключает `.env`, токены, `*.sqlite-*`
- [ ] Репозиторий приватный
- [ ] Deploy key / PAT имеет минимально нужные права
- [ ] Включён 2FA у аккаунта-владельца
- [ ] Тестовый прогон push + restore выполнен вручную
- [ ] Таймер активен, последний запуск успешен
- [ ] Логи бэкапа сохраняются 30+ дней
- [ ] Подпись/хеш архива проверяются автоматически на restore
- [ ] SQLite-БД бэкапятся online API, а не копированием (см. §8)

---

## §8. Бэкап SQLite-сессий (.db, .sqlite, .sqlite3)

SQLite-файлы в `~/.hermes/`, `~/.claude/`, `~/.codex/` и workspace-ах
хранят текущее состояние сессий, индексы воспоминаний и метаданные
навыков. Наивный `cp *.db $BACKUP/` берёт срез БД в произвольный
момент транзакции — результат может быть inconsistent, особенно в
режимах WAL / TRUNCATE.

### 8.1. Инвентаризация и режим журнала

```bash
find $AGENT_ROOT /opt/agent-workspaces -type f \
  \( -name '*.db' -o -name '*.sqlite' -o -name '*.sqlite3' \)

# Для каждой БД — определить journal_mode:
sqlite3 /path/to/sessions.db \
  "PRAGMA journal_mode; PRAGMA busy_timeout; PRAGMA wal_autocheckpoint;"
```

| `journal_mode` | Поведение при записи                          | Как бэкапить                          |
|----------------|-----------------------------------------------|---------------------------------------|
| `delete`       | основной `.db` + `.db-journal`                | можно `cp` после остановки / Backup API |
| `wal`          | `.db` + `.db-wal` + `.db-shm`                 | **только** Backup API                  |
| `truncate`     | похож на `delete`, но без journal-файла       | можно `cp` после остановки / Backup API |
| `persist`      | заголовок помечен, отдельного файла нет       | Backup API или `cp` под эксклюзивом   |
| `memory`       | журнал в RAM                                  | **нельзя** сохранить на лету          |
| `off`          | без журнала (опасно)                          | консистентно, но рискованно            |

### 8.2. Главное правило — Backup API

> **Никогда** не копируйте `.db`/`.wal`/`.shm` вручную. SQLite сама
> делает снимок на момент старта, держит нужные блокировки и
> отдаёт уже согласованный дамп.

```bash
sqlite3 /path/to/sessions.db \
  ".backup '$BACKUP_TMP/sessions-$(date -u +%Y%m%dT%H%M%SZ).db'"
# Код возврата 0 = OK, != 0 = проблема. Всегда проверяйте $? / используйте &&.
```

### 8.3. Альтернатива — `VACUUM INTO`

```bash
sqlite3 /path/to/sessions.db \
  "VACUUM INTO '$BACKUP_TMP/sessions-vacuumed.db'"
```

Полезно как вторичный артефакт: дефрагментированная копия для
хранения в репо. В hot-path не злоупотреблять — VACUUM эксклюзивно
блокирует БД.

### 8.4. `.gitignore` для SQLite

```gitignore
# SQLite transient files — НЕ бэкапим как часть репо
*.db-journal
*.db-shm
*.db-wal
*.sqlite-journal
*.sqlite-shm
*.sqlite-wal
*.sqlite3-journal
*.sqlite3-shm
*.sqlite3-wal
# Сами .db/.sqlite/.sqlite3 добавляем вручную (см. §3.1)
```

### 8.5. Очистка транзитных файлов перед коммитом

```bash
find "$WORK" \
  \( -name '*.db-journal'  -o -name '*.db-shm'  -o -name '*.db-wal' \
  -o -name '*.sqlite-journal' -o -name '*.sqlite-shm' -o -name '*.sqlite-wal' \
  -o -name '*.sqlite3-journal' -o -name '*.sqlite3-shm' -o -name '*.sqlite3-wal' \
  \) -delete

git -C "$WORK" add -A
git -C "$WORK" commit -m "snapshot $(date -u +%FT%TZ) [sqlite online backup]"
```

### 8.6. Опциональный `wal_checkpoint(TRUNCATE)` перед backup

```bash
sqlite3 /path/to/sessions.db "PRAGMA wal_checkpoint(TRUNCATE);"
sqlite3 /path/to/sessions.db ".backup '$BACKUP_TMP/sessions.db'"
```

`TRUNCATE` полностью освобождает `.db-wal`; безопасно на лету, если
нет долгих транзакций.

### 8.7. Блок для скрипта автоматизации (§5.1)

```bash
# SQLite backup step — выполнять ПОСЛЕ rsync, ДО tar
DB_BACKUP_DIR="$BACKUP_TMP/db-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$DB_BACKUP_DIR"
while IFS= read -r db; do
    [ -r "$db" ] || continue
    base=$(basename "$db")
    sqlite3 "$db" ".backup '$DB_BACKUP_DIR/$base'" \
      && echo "  backed up $db" \
      || { echo "  FAILED $db" >&2; exit 1; }
done < <(find "$AGENT_ROOT" /opt/agent-workspaces \
             -type f \( -name '*.db' -o -name '*.sqlite' \
             -o -name '*.sqlite3' \) 2>/dev/null)

tar -C "$DB_BACKUP_DIR/.." -czf \
    "$BACKUP_TMP/${SNAP_NAME}-dbs.tar.gz" \
    "$(basename "$DB_BACKUP_DIR")"
rm -rf "$DB_BACKUP_DIR"
```

### 8.8. Восстановление SQLite-БД

**a)** Распаковать тарбол:

```bash
tar -xzf agents-YYYYMMDDTHHMMSSZ-dbs.tar.gz -C /tmp/restore_db
```

**b)** Положить на штатное место:

```bash
cp /tmp/restore_db/<имя>.db /path/to/live/<имя>.db
chown <user>:<group> /path/to/live/<имя>.db
chmod 0640 /path/to/live/<имя>.db
```

**c)** Удалить транзитные файлы от старой БД (при остановленном live-процессе):

```bash
rm -f /path/to/live/<имя>.db-journal \
      /path/to/live/<имя>.db-wal \
      /path/to/live/<имя>.db-shm
```

**d)** Проверить целостность:

```bash
sqlite3 /path/to/live/<имя>.db "PRAGMA integrity_check;"
sqlite3 /path/to/live/<имя>.db "PRAGMA foreign_key_check;"
```

**e)** Запустить агентский сервис:

```bash
systemctl --user start hermes-gateway
journalctl -u hermes-gateway -n 20 --no-pager | tail
```

### 8.9. Подводные камни

- **`journal_mode=memory`** ⇒ Backup API тоже работает, но вы теряете
  данные с момента последней записи. Переключите на `wal`/`truncate` до backup-а.
- **`busy_timeout=0`** ⇒ backup может мгновенно падать с
  *database is locked*. Установите `PRAGMA busy_timeout=5000;` в
  настройках приложения или временно в скрипте:
  `sqlite3 "$db" "PRAGMA busy_timeout=5000;"`.
- **Огромные `.db-wal` (>1 ГБ)** ⇒ backup API будет долгим. Делайте
  `PRAGMA wal_checkpoint(TRUNCATE);` заранее или настройте
  `wal_autocheckpoint=1000;`.
- **SQLCipher** ⇒ Backup API работает, но выгруженный файл остаётся
  зашифрованным тем же ключом. Ключ хранить **отдельно** от бэкапа
  (никогда в одном коммите с `.db`).
- **Активная миграция схемы (`ALTER TABLE …`)** ⇒ Backup API ждёт
  окончания миграции, и таймаут systemd unit может сработать раньше.
  Бэкапьте в окно обслуживания либо увеличьте `TimeoutStartSec=`
  в unit-файле.

---

*Конец инструкции. Идентично содержимому `GitHab01.txt`, v1.0 от 2026-06-14.*
