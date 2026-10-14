## PATCH для /root/.hermes/profiles/fst-control/config.yaml

**Дата:** 2026-08-01
**Причина:** опечатки в ответах из-за context overflow (327K токенов > 200K лимита MiniMax M3)
**Решение:** включить `session_reset.mode: auto` + threshold

---

## ДО (текущее состояние — режим отсутствует)

```yaml
session_reset:
  mode: none
```

## ПОСЛЕ (исправленное — автокомпакция при переполнении)

```yaml
session_reset:
  mode: auto
  threshold: 150000
  keep_last_n: 30
```

---

## ПАРАМЕТРЫ

| Параметр | Значение | Зачем |
|---|---|---|
| `mode: auto` | автоматически | Hermes сам делает reset по триггеру |
| `threshold: 150000` | 150K токенов | Порог для reset (ниже 200K лимита MiniMax M3) |
| `keep_last_n: 30` | 30 сообщений | Сколько последних сообщений оставить при truncate |

---

## КАК ПРИМЕНИТЬ

### Вариант 1: через sed (быстрый)

```bash
# 1. Бэкап оригинала
cp /root/.hermes/profiles/fst-control/config.yaml \
   /root/.hermes/profiles/fst-control/config.yaml.bak.20260801

# 2. Заменить блок одной командой
sed -i 's/  mode: none/  mode: auto\n  threshold: 150000\n  keep_last_n: 30/' \
    /root/.hermes/profiles/fst-control/config.yaml

# 3. Проверить результат
grep -A 3 'session_reset:' /root/.hermes/profiles/fst-control/config.yaml
```

Ожидаемый вывод:
```yaml
session_reset:
  mode: auto
  threshold: 150000
  keep_last_n: 30
```

### Вариант 2: через Python (надёжный)

```bash
# 1. Бэкап
cp /root/.hermes/profiles/fst-control/config.yaml \
   /root/.hermes/profiles/fst-control/config.yaml.bak.20260801

# 2. Заменить
python3 << 'EOF'
import re
path = '/root/.hermes/profiles/fst-control/config.yaml'
with open(path) as f:
    content = f.read()

old = '''session_reset:
  mode: none'''

new = '''session_reset:
  mode: auto
  threshold: 150000
  keep_last_n: 30'''

if old not in content:
    print("ERROR: old block not found")
else:
    content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)
    print("OK")
EOF

# 3. Проверить
grep -A 3 'session_reset:' /root/.hermes/profiles/fst-control/config.yaml
```

### Вариант 3: вручную через nano/vim

```bash
nano /root/.hermes/profiles/fst-control/config.yaml
```

Найти:
```yaml
session_reset:
  mode: none
```

Заменить на:
```yaml
session_reset:
  mode: auto
  threshold: 150000
  keep_last_n: 30
```

Сохранить (`Ctrl+O`, `Enter`, `Ctrl+X`).

---

## ПОСЛЕ ПРИМЕНЕНИЯ

### 1. Перезапустить gateway

```bash
# Если запущен через systemd
systemctl --user restart hermes-gateway-fst-control

# Или (альтернатива)
hermes gateway restart -p fst-control

# Проверить статус
systemctl --user status hermes-gateway-fst-control
```

### 2. Сделать `/reset` текущей сессии

Так как state.db уже раздут до 1 256 сообщений:

```
Написать @fst_control_bot: /reset
```

Или:
```
Написать @fst_control_bot: /new
```

### 3. Проверить через 30-50 turn'ов

```bash
# Сумма токенов в активной сессии
sqlite3 -readonly /root/.hermes/profiles/fst-control/state.db \
  "SELECT session_id, SUM(token_count) FROM messages WHERE token_count IS NOT NULL GROUP BY session_id ORDER BY SUM(token_count) DESC LIMIT 1"
```

Если `SUM > 150000` — значит auto-reset не сработал, нужна ручная настройка.

### 4. Если проблема не уйдёт

Снизить threshold:
```yaml
session_reset:
  mode: auto
  threshold: 100000   # ← более агрессивно
  keep_last_n: 20
```

---

## ОТКАТ (если что-то не так)

```bash
# Восстановить из бэкапа
cp /root/.hermes/profiles/fst-control/config.yaml.bak.20260801 \
   /root/.hermes/profiles/fst-control/config.yaml

# Перезапустить gateway
systemctl --user restart hermes-gateway-fst-control
```

---

## БЕЗОПАСНОСТЬ

| Аспект | Защита |
|---|---|
| Потеря данных | Бэкап перед изменением |
| Что-то сломается | Откат через `cp ... bak` |
| Случайное удаление | `config.yaml.bak.20260801` хранится в той же папке |
| Reset без потери | State.db не модифицируется, меняются только конфиг |

---

## СВЯЗАННЫЕ ИЗМЕНЕНИЯ (опционально)

### Уменьшить `max_turns`

В файле конфига также есть:
```yaml
agent:
  max_turns: 150
```

Если нужна более жёсткая защита:
```yaml
agent:
  max_turns: 50   # уменьшить до 50
```

### Удалить старую сессию (для чистоты)

Опционально, после стабилизации:
```bash
# ⚠️ Удалит ВСЕ сообщения. Сначала бэкап:
cp /root/.hermes/profiles/fst-control/state.db \
   /root/.hermes/profiles/fst-control/state.db.bak.20260801

# Сбросить БД (только если уверены)
sqlite3 /root/.hermes/profiles/fst-control/state.db \
  "DELETE FROM messages WHERE session_id = '20260720_163608_dd0f5d6d'"
```

---

## ЧЕГО ОЖИДАТЬ

| Состояние | Поведение |
|---|---|
| До патча | Каждые ~100 turn'ов контекст переполняется → опечатки |
| После патча | Auto-reset при 150K токенов → нет опечаток |
| После reset | Контекст = 0 → идеально на 30-50 turn'ов |
| Далее | При 150K автоматически truncate до 30 последних сообщений |

---

## КОНТРОЛЬНЫЙ ЧЕК-ЛИСТ

- [ ] Создан бэкап `config.yaml.bak.20260801`
- [ ] Изменён `mode: none` → `mode: auto`
- [ ] Добавлен `threshold: 150000`
- [ ] Добавлен `keep_last_n: 30`
- [ ] Проверен результат через `grep -A 3 session_reset`
- [ ] Gateway перезапущен
- [ ] Сделано `/reset` для текущей сессии
- [ ] Через 30-50 turn'ов context < 150K
- [ ] Опечатки исчезли

---

## КОНЕЦ ПАТЧА
