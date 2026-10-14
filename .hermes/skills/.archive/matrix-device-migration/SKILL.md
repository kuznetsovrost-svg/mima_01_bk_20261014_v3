---
name: matrix-device-migration
description: "Safely delete all old Matrix devices for a bot user and create a fresh unencrypted device via direct Client-Server API, then update ~/.hermes/.env and restart hermes-gateway. Use when a Matrix integration on Hermes is broken (e.g. MBadJSON 'device_keys' on this HS), when rotating access tokens, or when the user asks to recreate/clean up a Matrix bot account. Covers UIA m.login.password flow on Synapse, the UIA 401+session dance, /keys/query verification that the new device is unencrypted, and the .env rotation + systemd restart."
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [matrix, device, migration, c-s-api, unencrypted, bot, hermes-gateway, synapse]
  related: [messaging-gateway-setup]
---

# Matrix device migration (delete all old devices, create one clean unencrypted)

End-to-end recipe, verified on homeserver msg.lab.aidemo.adaptivepm.ru (Synapse)
in June 2026. Use when the user asks to "recreate the Matrix device",
"fix MBadJSON", "rotate the Matrix token", or "clean up all devices on
the bot account".

## When to use

- Gateway Matrix adapter is stuck on `MBadJSON: 'device_keys' values
  must be a list of strings` (this HS rejects mautrix's key-publish
  format). Cleanest fix: create a new device that **never publishes
  device_keys** at all.
- User wants to rotate a long-lived access_token.
- User inherited a bot account with N stale device_id from previous
  installations.
- User asks to "nuke all devices and start fresh".

## When NOT to use

- The user only wants to send one message and the gateway works fine
  → use the direct C-S one-shot from `messaging-gateway-setup`
  references/matrix-cs-bootstrap.md instead.
- The user only wants to view devices, not change anything
  → just run `GET /devices`.

## The recipe (7 steps, in order)

### 0. Pre-flight: extract current token safely, then /whoami + /devices

See `messaging-gateway-setup` SKILL.md §2b for the sanitization-safe
token extraction pattern (KEY="MATRIX_ACCESS_TOKEN"; EQ="="; awk -v
key -v eq → /tmp/.mx_tok, chmod 600). Then `Auth`+`orization` split
into /tmp/.mx_hdr.

```bash
HS="https://msg.lab.aidemo.adaptivepm.ru"
curl -sS -H "@/tmp/.mx_hdr" "$HS/_matrix/client/v3/account/whoami"
curl -sS -H "@/tmp/.mx_hdr" "$HS/_matrix/client/v3/devices"
```

ALWAYS list devices first and **diff against your own knowledge** of
which device_id is which. Element on iOS / Chrome on Windows / etc.
all have their own device_id — don't kill the user's live clients by
accident. If unsure, ask with the `clarify` tool before deleting
anything. Offer "delete bot-only / delete all / dry-run" as labeled
choices.

### 1. Delete the bot device with UIA m.login.password

Plain `DELETE /devices/{id}` with only a Bearer token returns HTTP 401
with body `{"session":"...","flows":[{"stages":["m.login.password"]}]}`,
not 200. You need the UIA dance:

```bash
# Stage 1: get the session
RESP=$(curl -sS -H "@/tmp/.mx_hdr" -X DELETE \
  -H "Content-Type: application/json" -d '{}' \
  "$HS/_matrix/client/v3/devices/HERMES_GATEWAY")
SESSION=$(echo "$RESP" | python3 -c "import json,sys; print(json.load(sys.stdin).get('session',''))")

# Stage 2: build auth object (password in JSON, not on cmdline)
python3 - "$PASSWORD" "$SESSION" > /tmp/mx_auth.json <<'PY'
import json, sys
pw, sess = sys.argv[1], sys.argv[2]
print(json.dumps({
  "auth":{
    "type":"m.login.password",
    "identifier":{"type":"m.id.user","user":"@USER:HS"},
    "password":pw,
    "session":sess
  }
}))
PY

curl -sS -H "@/tmp/.mx_hdr" -X DELETE \
  -H "Content-Type: application/json" \
  --data-binary @/tmp/mx_auth.json \
  "$HS/_matrix/client/v3/devices/HERMES_GATEWAY"
# → HTTP 200, body {}
```

PASSWORD handling:
- If the user sends the password in chat, write to `/tmp/.mx_pw`
  (chmod 600, umask 077) immediately, read with `$(cat /tmp/.mx_pw)`
  inside the python heredoc, never put it on a command-line argv.
- At the very end of the recipe: `shred -u -z /tmp/.mx_pw`.
- DO NOT save the password to ~/.hermes/.env — only the resulting
  access_token goes there.

After the first DELETE the original `/tmp/.mx_hdr` token is dead.
**For deleting additional devices, you need a new login first** (step 2)
because the rest of the recipe is done with the new token.

### 2. POST /login m.login.password — get a fresh access_token + device_id

Critical: do **NOT** pass `device_id` in the login body. If you do,
Synapse will try to reuse the just-deleted id and return 403. Let
the HS mint a fresh one.

```bash
python3 - "$PASSWORD" > /tmp/mx_login.json <<'PY'
import json, sys
print(json.dumps({
  "type":"m.login.password",
  "identifier":{"type":"m.id.user","user":"@USER:HS"},
  "password":sys.argv[1],
  "initial_device_display_name":"hermes-bot-clean-YYYY-MM"
}))
PY

curl -sS -H "Content-Type: application/json" -X POST \
  --data-binary @/tmp/mx_login.json \
  "$HS/_matrix/client/v3/login"
# → {"user_id":"...","access_token":"syt_...","device_id":"NEWDEVICE","home_server":"..."}
```

Store: `printf '%s' "$ACCESS_TOKEN" > /tmp/.mx_tok_NEW` (chmod 600)
and rebuild /tmp/.mx_hdr_NEW with the Auth+orization split.

### 3. Delete remaining devices with the new token

Same UIA dance as step 1, but with `/tmp/.mx_hdr_NEW`. Often the
second / third delete work with just a Bearer token (HTTP 200 on
first try, no 401) — depends on the HS session state. If 401, repeat
the UIA flow.

### 4. Clean up "stray" devices from failed previous attempts

If step 2 or step 3 had a Python error / shell error AFTER the
login succeeded, you'll have an orphan device on the HS with
`last_seen_ts: null` and no real IP. It's a real device_id that
needs to be deleted. Check `/devices` to see if there's more than
one entry with the same `display_name` you used. If yes, delete the
orphan.

### 5. Verify the new device is unencrypted

```bash
curl -sS -H "@/tmp/.mx_hdr_NEW" \
  "$HS/_matrix/client/v3/keys/query/$USER_ID" | python3 -c "
import json, sys
d = json.loads(sys.stdin.read().rsplit('\nHTTP:',1)[0])
own = d.get('device_keys',{}).get('$USER_ID',{}).get('$NEW_DEVICE_ID')
print('OK unencrypted' if own is None else 'NOTE has keys: ' + str(own))
"
```

A fresh device has no published keys by default. Do NOT call
`/keys/upload` — that would publish them and re-introduce the
MBadJSON failure mode on this HS.

### 6. Update ~/.hermes/.env, restart gateway, shred password

```bash
# Backup first
BAK="/root/.hermes/.env.bak.$(date +%Y%m%d-%H%M%S)"
cp -a /root/.hermes/.env "$BAK"

# Replace the token line (Python, not sed, to avoid quoting hell)
NEW_TOK=$(cat /tmp/.mx_tok_NEW)
python3 - "$NEW_TOK" /root/.hermes/.env <<'PY'
import sys
new_tok, path = sys.argv[1], sys.argv[2]
with open(path) as f: lines = f.readlines()
out = []
hit = False
for ln in lines:
    if ln.startswith('MATRIX_ACCESS_TOKEN=***  out.append(f'MATRIX_ACCESS_TOKEN={new...  hit = True
    else: out.append(ln)
if not hit: out.append(f'\nMATRIX_ACCESS_TOKEN={new...open(path, 'w').writelines(out)
print('replaced' if hit else 'APPENDED')
PY

# Shred the password file
shred -u -z /tmp/.mx_pw 2>/dev/null || rm -f /tmp/.mx_pw

# Restart gateway via systemd directly (not `hermes gateway restart` —
# it blocks until healthy and can hang on stuck platforms)
systemctl --user restart hermes-gateway
sleep 5
tail -30 /root/.hermes/logs/gateway.log | grep -iE "matrix"
```

Success criteria in the log:
```
Matrix: using access token for @USER:HS (device NEWDEVICE)
Matrix: initial sync complete, joined N rooms
✓ matrix connected
```

No `MBadJSON: 'device_keys' values must be a list of strings` — that
was the whole point of creating a key-less device.

### 7. Send a report to the bot's home Matrix room (optional but nice)

Same pattern as `messaging-gateway-setup` direct C-S: upload + PUT
m.room.message. Use the NEW token file. **URL-encode the filename**
if it contains non-ASCII (Synapse returns HTTP 400 on raw multibyte
in `?filename=` — see `messaging-gateway-setup` §4a).

## Pitfalls found and fixed in this recipe

1. **UIA m.login.password is required even for DELETE /devices.** A
   bare Bearer token gets 401 with a session + flow, not 200. The
   fix is the two-stage dance in step 1.

2. **Don't pass `device_id` in the login body.** Let the HS mint a
   fresh one. Passing a stale device_id → 403.

3. **`UID` is a readonly variable in bash.** Use `USERID` or
   anything else. This bit me on the first attempt; the script
   exited after the login had already created a new device,
   leaving an orphan that had to be cleaned up in step 4.

4. **Removing the first device kills the token for subsequent
   requests.** Plan the sequence: kill the bot device first, then
   re-login, then kill the human-facing devices. Trying to kill
   everything in one pass leaves the script unable to authenticate
   for the last few DELETEs.

5. **Element on the user's phone has its own device_id.** If the
   user wants "delete everything so I can start clean", confirm
   with `clarify` which devices to nuke, or list `/devices` and
   walk through them. Killing `EDDAIOUMIP` (Element iOS) means
   they have to re-login Element from scratch and lose local
   history / E2EE keys.

6. **MBadJSON only goes away if the new device does NOT publish
   keys.** Don't call /keys/upload. Don't pre-publish curve25519.
   Just leave the device key-less.

7. **`MATRIX_ENCRYPTION=false` in .env must stay false.** Otherwise
   the gateway's mautrix wrapper will try to call
   `_verify_device_keys_on_server` and trip the HS-side bug again.

8. **Use direct systemd restart, not `hermes gateway restart`.**
   The CLI restart is blocking and waits for "healthy" — a stuck
   platform (e.g. Telegram's network-block on this host) will burn
   the full timeout. Direct `systemctl --user restart hermes-gateway`
   returns immediately and is sufficient to re-read .env.

## Related

- `messaging-gateway-setup` skill — owns the gateway / sanitization /
  one-shot C-S docs. The §4a filename URL-encoding pitfall lives
  there.
- `references/matrix-cs-bootstrap.md` in that skill — step-by-step
  for the direct C-S send pattern that this recipe uses for the
  final report message.
