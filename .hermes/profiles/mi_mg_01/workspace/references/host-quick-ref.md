# mima_g_01 — quick reference

Свободно редактируйте — это рабочий документ для профиля mi_mg_01.

## Хост
- hostname: `mima-g-01` (`72.56.29.69`)
- ОС: Ubuntu 24.04.4 LTS, kernel `6.8.0-134-generic`
- CPU/RAM/disk: 4 vCPU AMD EPYC, 7.8 GiB RAM, 80 GB disk (11% used)

## SSH
- Алиас: `mima-g-01` (в `~/.ssh/config`)
- Пользователь: `root`
- Ключ: `~/.ssh/id_ed25519_mima` (fingerprint SHA256:rRAs/...)
- Без пароля, `IdentitiesOnly=yes`

## Сетевая досягаемость
- IPv4 есть, IPv6 egress нет
- API Telegram fallback: `149.154.166.110` (если DNS шатает)
- DNS: `127.0.0.53` (systemd-resolved)
- Внешний шлюз: `72.56.29.1`

## Шлюз Hermes
- User-scope systemd unit: `hermes-gateway.service` (`Enabled`, `Linger=yes`)
- WorkingDirectory: `/root/.hermes`
- Логи: `~/.hermes/logs/gateway.log`, `~/.hermes/logs/errors.log`
- Лимит сессий: `max_concurrent_sessions: 5` (по умолчанию)

## Firewall
- UFW active, default deny incoming
- `22/tcp` LIMIT (rate-limit, после fail2ban)
- `10050/tcp` ALLOW (zabbix-agent)
- Остальное закрыто

## Защита от SSH-брутфорса
- fail2ban jail: `sshd` (aggressive, bantime 1h → 1w)
- Проверить баны: `fail2ban-client status sshd`

## Telegram-бот этого профиля
- Пока НЕ настроен. Чтобы добавить:
  1. Создать бота в @BotFather.
  2. Получить token.
  3. Положить в `~/.hermes/profiles/mi_mg_01/.env`:
     ```
     TELEGRAM_BOT_TOKEN=***
     TELEGRAM_ALLOWED_USERS=505586502
     ```
  4. `systemctl --user restart hermes-gateway.service` (из профиля).
- Глобальный бот `default` (@MMRV_Hermes_bot) уже работает.

## Часовой пояс
- `Europe/Moscow` (UTC+3, без DST)

## Частые операции (см. skill `mima_g_01_operations`)
- Health snapshot: `ssh mima-g-01 'uptime; df -h /; free -h'`
- Gateway status: `ssh mima-g-01 'XDG_RUNTIME_DIR=/run/user/0 systemctl --user status hermes-gateway.service'`
- Gateway restart: `ssh mima-g-01 'XDG_RUNTIME_DIR=/run/user/0 systemctl --user restart hermes-gateway.service'` — ТОЛЬКО с подтверждения.
- Журнал: `journalctl --user -u hermes-gateway.service -n 50`
- Tail логов: `tail -F ~/.hermes/logs/gateway.log`

## Питы (pitfalls)
- Всегда `XDG_RUNTIME_DIR=/run/user/0` для `systemctl --user` по SSH.
- Не убивать gateway процесс через `kill -9` — пусть systemd управляет.
- `apt upgrade` — только с явного подтверждения.
- Не выводить `/etc/shadow`, `id_*` без подтверждения.
