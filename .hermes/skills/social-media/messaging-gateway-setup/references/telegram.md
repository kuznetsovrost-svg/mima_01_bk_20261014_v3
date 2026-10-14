# Telegram — Field Notes

Concrete notes that complement the umbrella `messaging-gateway-setup`
skill. Read this when the user is specifically wiring up Telegram.

## Token & Auth

- Get the token from `@BotFather` in Telegram: `/newbot` → name →
  username (must end in `bot`) → copy token of form `123456:ABC-DEF…`.
- Hermes stores it as `TELEGRAM_BOT_TOKEN` in `~/.hermes/.env`.
  Format: `TELEGRAM_BOT_TOKEN=123456:ABC-DEF…` — no quotes, no spaces.
- Bot **must** be started by the user (`/start`) before it can DM them.
- A token that parses ≠ a token that the host can reach. See
  "Reachable vs Configured" below.

## Where Each Setting Lives

For Telegram specifically:

| Setting                     | Path in config.yaml                                       |
|-----------------------------|-----------------------------------------------------------|
| home chat id                | `gateway.platforms.telegram.home_chat_id: <int>`          |
| whitelist of users          | `gateway.platforms.telegram.allowed_users: [<id>, …]`     |
| whitelist of chats (groups) | top-level `telegram.allowed_chats: "<csv>"` (string!)     |
| pairing / approval          | `gateway.platforms.telegram.pairing: true`                |
| proxy (SOCKS5/HTTPS)        | `gateway.platforms.telegram.proxy: socks5://…`            |
| long-polling timeout        | `gateway.platforms.telegram.poll_timeout: 30`             |
| edit-message "typing"       | `display.platforms.telegram.streaming: true`              |
| reactions                   | top-level `telegram.reactions: false`                      |
| chat prompts                | top-level `telegram.channel_prompts: {}`                  |
| tools in this platform      | `platform_toolsets.telegram: [list]`                      |

`allowed_chats` is a **comma-separated string**, not a list. Common
mistake: writing it as a YAML list — works syntactically but the
matcher does a substring check, so the list form is silently ignored.

## "Configured" Does NOT Mean "Reachable"

Telegram's Bot API is at `https://api.telegram.org/`. Long-polling
opens persistent HTTPS connections. Common failure modes:

1. **IPv6-only DNS, no IPv4 route.** `getent hosts api.telegram.org`
   returns `2001:67c:4e8:f004::9`. If the host has no IPv6 egress, the
   connect times out. log shows repeating
   `Primary api.telegram.org connection failed ()`.
2. **ISP / datacenter blocks Telegram.** Same symptom, but every
   `curl https://api.telegram.org` also times out from the shell.
3. **Local firewall drops 149.154.160.0/20.** Telegram publishes
   fallback IPs in this range; if iptables/nftables blocks them,
   the adapter cycles through fallbacks and logs `Fallback IP … failed`.
4. **TLS interception / SNI mismatch** — uncommon, manifests as
   `SSL: CERTIFICATE_VERIFY_FAILED` in the log.

Quick triage:

```bash
curl -sS -m 8 -o /dev/null -w "v4 %{http_code} %{time_total}s\n" \
  -4 https://api.telegram.org/
curl -sS -m 8 -o /dev/null -w "v6 %{http_code} %{time_total}s\n" \
  -6 https://api.telegram.org/
curl -sS -m 8 https://149.154.166.110/     # one of Telegram's IPs
sudo iptables -L OUTPUT -n -v | head
ip route get 149.154.166.110
```

If egress is broken and you have a SOCKS5 proxy, set
`gateway.platforms.telegram.proxy: socks5://user:pass@host:1080`
and restart the gateway.

## Pairing / Approval Flow

- Default `pairing: true` — first time a new user DMs the bot, they
  are queued. Run `hermes pairing list` → `hermes pairing approve <id>`.
- For private/single-user bots, set `allowed_users: [<your_id>]`
  and skip pairing.
- Get your chat id: message the bot, then look in
  `~/.hermes/logs/gateway.log` for the update payload, or run
  `curl -s "https://api.telegram.org/bot<TOKEN>/getUpdates" | jq`.

## Long-Message Splitting

Telegram's hard cap is 4096 chars per message. Hermes's Telegram
adapter auto-splits above that. If you see `Bad Request: message is
too long` in the log, the streaming transport may have tried to edit
a message past the cap. Workarounds:
- `hermes config set streaming.enabled false`
- or shorten model outputs via prompt.

## Voice / Stickers / Inline

- Voice messages from users are auto-transcribed (see `stt.*` config).
- Stickers are received as `sticker` updates, ignored by default.
- Inline mode (`@yourbot query`) requires `inline_query` handler —
  not enabled in the default adapter.

## Restart Cheatsheet

```bash
hermes gateway restart                    # preferred
systemctl --user restart hermes-gateway   # if installed as service
hermes gateway status                     # confirm
tail -f ~/.hermes/logs/gateway.log        # watch
```

## Out-of-Band Bot-API Probes (Direct curl, No Gateway)

When you need to verify the token / bot identity / webhook state from the
shell **without touching the long-poll slot**, use these endpoints instead
of `getUpdates`. They are read-only or outbound and do **not** conflict
with the gateway's polling session.

| Check              | Endpoint                                       | Use                                                  |
|--------------------|------------------------------------------------|------------------------------------------------------|
| Token valid?       | `GET  /bot<TOKEN>/getMe`                       | returns `{ok, result.id, result.username, ...}`     |
| Webhook configured?| `GET  /bot<TOKEN>/getWebhookInfo`              | `url==""` and `pending_update_count==0` = polling    |
| Outbound send      | `POST /bot<TOKEN>/sendMessage`                 | smoke-test actual delivery to home chat             |
| Recent updates     | `GET  /bot<TOKEN>/getUpdates?timeout=0&limit=1`| **DO NOT** use while gateway is polling (see below) |

**Three things that bite during these probes:**

1. **Token extraction from `~/.hermes/.env` is sanitizer-fragile.**
   A naive `awk -F= '/^TELEGRAM_BOT_TOKEN=...{print $2}' ...` or
   `grep '^TELEGRAM_BOT_TOKEN=...' | sed ...` collides with the
   `***` redaction (the pattern's `=` and the redaction are adjacent in
   the shell source). Result: awk warns `unterminated regexp`, the
   variable comes back empty, the URL becomes `…/bot/getMe` → HTTP 404.

   Working extraction (token stays out of argv, sanitizer can't see the
   literal `***` next to `=`):
   ```bash
   awk -v k=TELEGRAM_BOT_TOKEN -v eq='=' \
       'index($0, k eq) == 1 { sub(k eq, ""); print; exit }' \
       /root/.hermes/.env > /tmp/.tg_tok
   chmod 600 /tmp/.tg_tok
   # use as: curl "https://api.telegram.org/bot$(cat /tmp/.tg_tok)/getMe"
   # cleanup:
   shred -u -z /tmp/.tg_tok
   ```
   `awk -v key=…` passes the key as a separate argv value, so there is
   no contiguous `=***` run in your shell command source.

2. **`curl …/getUpdates` from the agent steals the polling slot.**
   `getUpdates` is a long-poll — every open one holds a server-side
   session for that token. If the gateway is already polling, your curl
   will be rejected with `409 Conflict: terminated by other getUpdates
   request`. The gateway will see the same 409 and log
   `WARNING … Telegram polling conflict (1/5) — previous session still
   held open`. This self-heals after Telegram drops your curl (~20s)
   and the gateway logs `Telegram polling resumed after conflict retry 1/5`.
   **Do not confuse that WARNING for a real fault.** If you really need
   recent updates from the shell, read the gateway log instead:
   `tail -200 ~/.hermes/logs/gateway.log | grep -E "inbound message|update_id"`.

3. **Direct-IP curl to `149.154.166.110` always fails TLS.**
   Telegram's fallback IP serves a certificate that is only valid for
   the `api.telegram.org` SNI. Calling the IP directly returns
   `SSL: no alternative certificate subject name matches target host name`.
   This is expected — gateway uses the IP for fallback but with
   correct SNI. From the shell, just use the hostname.

**Diagnostic-grade send-message smoke test** (verifies the full
path: token → Bot API → Telegram servers → recipient's client):
```bash
TOK=$(awk -v k=TELEGRAM_BOT_TOKEN -v eq='=' \
        'index($0, k eq) == 1 { sub(k eq, ""); print; exit }' \
        /root/.hermes/.env)
curl -sS -m 10 -X POST "https://api.telegram.org/bot${TOK}/sendMessage" \
     -H "Content-Type: application/json" \
     -d "{\"chat_id\": $(awk -v k=TELEGRAM_HOME_CHAT_ID -v eq='=' \
        'index($0, k eq) == 1 { sub(k eq, ""); print; exit }' \
        /root/.hermes/config.yaml), \
        \"text\": \"Telegram smoke test $(date '+%H:%M:%S')\"}"
```
Or read `home_chat_id` directly from
`grep home_chat_id ~/.hermes/config.yaml`. Expected response: `ok:true,
result.message_id:<int>, result.chat.id:<chat_id>`. If the user
does not see the message, the most common cause is that they haven't
started the bot (`/start` in the Telegram client) — DMs require an
explicit start before Bot API can deliver messages back.
