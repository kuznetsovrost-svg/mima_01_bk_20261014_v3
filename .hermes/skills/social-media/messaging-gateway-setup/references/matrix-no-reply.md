# «User пишет в Matrix, никакой реакции» — пошаговый сценарий

Загружай этот файл, когда юзер жалуется на отсутствие ответа
от Matrix-бота, а в `gateway.log` всё чисто. В 95% случаев
причина — user not in bot's room + (опционально) E2EE.

## 0. Симптом

* `hermes status` — Matrix ✓ configured
* `systemctl --user status hermes-gateway` — active (running)
* `tail ~/.hermes/logs/gateway.log | grep matrix` — есть
  `✓ matrix connected`
* `MATRIX_ALLOWED_USERS` содержит user_id юзера
* Юзер пишет в Matrix-клиенте — ответа нет, в `gateway.log`
  тишина (никаких новых строк после его сообщения)

Это **не** баг гейтвея. Это «бот не подписан на рум, в
который юзер пишет», или «рум в E2EE и бот не может
прочитать блоб». И то, и другое — class-level сценарии,
достойные отдельной диагностики, а не random guess.

## 1. Три вопроса, которые надо задать первыми

Спроси юзера (короткие варианты дай — он любит A/B/C):

  1) В каком **имени комнаты** он пишет?
     (Element → название рума в шапке; Schildi → то же;
      веб → header рума)
  2) Под каким **аккаунтом** залогинен в клиенте?
     (Element → Settings → General → "Signed in as …")
  3) В каких комнатах **сам бот @oc_hermes** состоит?
     (это ты проверишь сам через API, см. §2)

Не пытайся «угадать» — переходи к §2 и докажи фактами.

## 2. Диагностика через C-S API

Токен бота берётся из `/root/.hermes/.env` (см. SKILL.md §7
про extraction). Дальше 3 запроса:

```python
from matrix_direct_cs_client import MatrixClient
mx = MatrixClient(hs, "/tmp/.mx_tok")

# (a) Кто я
print(mx.whoami())   # -> @oc_hermes:hs, device_id

# (b) В каких румах бот
for r in mx.joined_rooms():
    state = mx._curl("GET",
        f"/_matrix/client/v3/rooms/{r}/state")
    name = next((ev["content"].get("name")
                 for ev in state
                 if ev["type"] == "m.room.name"), None)
    enc  = any(ev["type"] == "m.room.encryption"
               for ev in state)
    members = mx._curl("GET",
        f"/_matrix/client/v3/rooms/{r}/members")["chunk"]
    joined = [ev["state_key"] for ev in members
              if ev["type"] == "m.room.member"
              and ev["content"].get("membership") == "join"]
    print(f"{r}  name={name!r}  encrypted={enc}")
    print(f"   joined: {joined}")
```

Ожидаемые находки:

  • Если user_id юзера нет ни в одном `[join]` →
    причина (a), переходи к §3.

  • Если рум `encrypted=True` И бот один без
    power_level на m.room.encryption → причина (b),
    см. SKILL.md §10(b).

  • Если user_id есть, encryption выключен, но ответа
    всё равно нет — это уже что-то более редкое
    (E2EE one-time keys, federation delay, rate limit).
    Собери логи и эскалируй.

## 3. Бот приглашает юзера (fix для случая (a))

Проверь, что у бота хватает power_level:

```python
state = mx._curl("GET",
    f"/_matrix/client/v3/rooms/{room}/state")
pl = next(ev["content"] for ev in state
          if ev["type"] == "m.room.power_levels")
invite_required = pl.get("invite", 0)
my_power = pl.get("users", {}).get(
    "@oc_hermes:hs", pl.get("users_default", 0))
assert my_power >= invite_required, \
    f"need {invite_required}, have {my_power}"
```

Типично: invite_required=0, my_power=100 (admin) — проходит.

Шли invite:

```python
mx._curl("POST",
    f"/_matrix/client/v3/rooms/{room}/invite",
    json_body={"user_id": "@user:hs"},
    content_type="application/json")
# -> {} (HTTP 200, пустое тело = success)
```

Скажи юзеру: «Открой Element/Schildi/web, в Home должно
быть приглашение — accept, потом пиши».

Verify через 1–2 секунды:

```python
import time; time.sleep(2)
members = mx._curl("GET",
    f"/_matrix/client/v3/rooms/{room}/members")["chunk"]
for ev in members:
    if ev["state_key"] == "@user:hs":
        print("membership now:",
              ev["content"].get("membership"))
        # -> "join" если юзер accept'нул,
        # -> "invite" если ещё не открыл клиент
```

## 4. Частые ловушки

  • **Юзер в Element смотрит на «Saved Messages» или
    пустой рум без шифрования** — это не тот рум, где бот.
    Element подсвечивает такие румы иконкой «домик».
    Попроси явно: «открой Home, найди рум, где @oc_hermes —
    это Hermes & Rostislav».

  • **Юзер залогинен под другим аккаунтом** (например, под
    @admin, а приглашение ушло на @rostislavkuznetsov).
    В Element: Settings → "Sign out" → Sign in как
    @rostislavkuznetsov:hs. Приглашения лежат в Home
    конкретного аккаунта.

  • **Federation delay** — если бот и юзер на разных
    homeserver-ах, invite идёт через федерацию, и доставка
    может занять 1–30 секунд. Подожди и retry-ни
    `joined_rooms`.

  • **m.room.power_levels.invite > 100** — крайне редко,
    но бывает в «приватных» румах. Тогда бот сам пригласить
    не может, нужен @admin homeserver-а.

  • **Юзер уже в руме, но как [leave] / [ban]** — в
    `members` это видно по `membership`. Re-invite из
    banned-статуса homeserver не пропустит (нужно
    unban от @admin).

## 5. Что НЕ делать

  • Не пытайся «угадать» — спрашивай у юзера, в каком руме
    он пишет. Два рума с разными именами могут выглядеть
    одинаково.

  • Не публикуй device_keys ботом «ради совместимости» с
    E2EE-румом. Это оживит MBadJSON из SKILL.md §5(b) и
    повалит весь гейтвей.

  • Не создавай новый рум без спроса — если у юзера уже
    есть подходящий plaintext-рум с ботом, новый ему не
    нужен.

  • Не «проверяй отправку» через send_text в случайный
    рум — это шум в его ленте. Сначала §2, потом §3.
