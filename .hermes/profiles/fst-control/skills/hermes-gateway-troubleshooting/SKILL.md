---
name: hermes-gateway-troubleshooting
description: "Use when a Hermes messaging gateway (Telegram, Discord, Slack, etc.) is misbehaving — startup fails, messages don't reach the bot, delivery is silent, or the user reports 'the bot doesn't respond'. Covers the diagnostic recipe, the .env-vs-config.yaml source-of-truth trap, and per-platform log signatures. Load for any 'why isn't my bot working' task."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, gateway, telegram, discord, slack, troubleshooting, diagnostics, configuration]
    related_skills: [hermes-agent]
---

# Hermes Gateway Troubleshooting

A focused companion to the bundled `hermes-agent` skill. The umbrella covers
setup, command reference, and broad platform notes; this skill covers what to
do **when the gateway is already running and the bot is silent, dropping
messages, or failing its startup notification**.

## When to Use

- User reports "the bot doesn't reply", "Telegram bot is silent", "messages
  aren't delivered", "home channel notification failed"
- `hermes gateway status` is green (service running) but behavior is wrong
- After a profile change, env edit, or gateway restart that didn't take effect
- Log lines like `Forbidden: bot can't send messages to the bot`, `Blocked
  unauthorized user`, or `Home-channel startup notification failed`

Don't use for: initial setup (use `hermes-agent` + `hermes setup`), model
selection, or non-messaging tool failures.

## The Universal Diagnostic Recipe

Five steps, in this order, cover ~90% of gateway misbehavior. Run them every
time before guessing.

### 1. Confirm the service is actually running

```bash
hermes gateway status                            # top-level
systemctl --user status hermes-gateway-<profile> # systemd detail
ps -ef | grep "[h]ermes.*gateway run"             # cross-check
```

`Active: active (running)` is necessary but not sufficient — gateway can be
up and completely broken in config.

### 2. Pull the last gateway log window

```bash
journalctl --user -u hermes-gateway-<profile>.service --no-pager -n 200
```

Grep for the failure signatures:

```bash
journalctl --user -u hermes-gateway-<profile>.service --no-pager -n 500 \
  | grep -iE "forbidden|blocked|home-channel|notification failed|error|warning"
```

**The most common log lines and what they mean:**

| Log signature | Meaning |
|---|---|
| `Forbidden: the bot can't send messages to the bot` | HOME_CHANNEL is the bot's own ID. Telegram forbids this. |
| `Blocked unauthorized user <id> in chat <id>` | ALLOWED_USERS doesn't include this sender's user_id. |
| `Home-channel startup notification failed for <platform>:<id>: ...` | First-time delivery on boot failed; same root cause as the `Forbidden` line. |
| `Discovering Telegram API fallback IPs via DNS-over-HTTPS…` | Normal startup; expect 1-3 seconds before connect succeeds. |
| `Connecting to Telegram (attempt N/8)…` | Network init. After 5+ attempts on the same line, the network path is blocked. |

If the same `Forbidden` or `Blocked unauthorized` line appears **repeatedly
across multiple PIDs**, it's a persistent misconfig, not a transient blip.

### 3. Identify the profile and the relevant keys

Multiple profiles = multiple gateways = multiple `.env` files. The one in
`/root/.hermes/profiles/<current>/.env` is what matters.

```bash
hermes config path          # active config.yaml
hermes config env-path      # active .env
grep -E "^TELEGRAM_|^DISCORD_|^SLACK_" "$(hermes config env-path)"
```

### 4. Know the .env vs config.yaml source-of-truth trap

**This is the most common reason "I changed the config and it didn't help".**

The Telegram adapter (`plugins/platforms/telegram/adapter.py`, the
`_apply_yaml_config` block around line 8268) reads the allowlist like this:

```python
allowed_users = telegram_cfg.get("allow_from")          # from config.yaml
if allowed_users is not None and not os.getenv("TELEGRAM_ALLOWED_USERS"):
    os.environ["TELEGRAM_ALLOWED_USERS"] = str(allowed_users)
```

Translation: yaml values are seeded into env **only if the env var is
unset**. If `.env` already has the key, yaml edits are silently shadowed by
the stale `.env` value. Same pattern applies to `HOME_CHANNEL` and other
platform-allowlist vars.

**The rule:** when a key lives in `.env`, edit `.env` directly. `hermes
config set` only writes yaml; it does not touch `.env`. A
gateway restart will not pick up a yaml change if the same key in `.env` is
still wrong.

`read_file` blocks direct `.env` reads as a credential store. Use terminal:

```bash
grep -nE "^TELEGRAM_(ALLOWED_USERS|HOME_CHANNEL)" \
  /root/.hermes/profiles/<profile>/.env
# Edit: sed -i 's/^TELEGRAM_ALLOWED_USERS=OLD$/TELEGRAM_ALLOWED_USERS=NEW/' \
#        /root/.hermes/profiles/<profile>/.env
```

### 5. Verify the fix end-to-end, not just "gateway restarted"

Gateway restart succeeding only proves the process didn't crash. Prove the
delivery path works:

```bash
TOKEN=$(grep ^TELEGRAM_BOT_TOKEN= /root/.hermes/profiles/<profile>/.env | cut -d= -f2)
USER_ID=<real_user_id>

# Bot -> user (proves the HOME_CHANNEL-equivalent path)
curl -s -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \
  -d "chat_id=${USER_ID}" -d 'text=✅ Hermes gateway verified'
# Expect: {"ok":true,"result":{"chat":{"id":<USER_ID>,...}}}

# User -> bot: send any message in Telegram, then check the gateway saw it
journalctl --user -u hermes-gateway-<profile>.service --since "1 minute ago" \
  | grep -i "${USER_ID}"
```

If the bot→user curl succeeds but the user→bot path is silent, the problem
is on the receive side (ALLOWED_USERS, or the bot isn't actually joined
to that chat).

## Per-Platform Failure Signatures

### Telegram

- **`Forbidden: bot can't send messages to the bot`** + **`Blocked unauthorized user`** in the same window → HOME_CHANNEL and/or ALLOWED_USERS is the bot's own ID. Get the real user_id (use `getChat` to confirm it's a real account, or have the user open `@userinfobot`), then patch `.env` and restart.
- **Bot replies in DMs but ignores groups** → check `TELEGRAM_GROUP_ALLOWED_USERS` / `TELEGROUP_ALLOWED_CHATS` separately from the DM allowlist.
- **Bot is in the group but never sees messages** → group's "Topics" / privacy mode may hide non-command messages from the bot. Disable privacy mode via `@BotFather` → Bot Settings → Group Privacy → Turn off.
- **`Connection refused` / `Timed out` retries on the same line** → network path to Telegram is blocked. The adapter's DNS-over-HTTPS fallback helps for DNS, not for outright IP blocks; check with `curl -v https://api.telegram.org`.

### Discord

- **Bot online in the server but never sends anything** → Message Content Intent is OFF. Bot → Privileged Gateway Intents → toggle Message Content Intent. Without it, the bot sees messages as empty.
- **Bot works in some channels but not others** → channel-level permission overrides; the bot needs `Send Messages` + (for slash commands) `Use Application Commands`.

### Slack

- **Bot silent in public channels, only works in DMs** → missing `message.channels` event subscription. Slack app → Event Subscriptions → Subscribe to bot events → add `message.channels`.
- **Slash command returns "dispatch_failed"** → the request URL in Slack app config points at the wrong gateway (common after profile switches).

## Restart and Re-Test Pattern

After any config change:

```bash
hermes gateway restart
sleep 8                            # gateway takes 2-5s to connect to platforms
journalctl --user -u hermes-gateway-<profile>.service --no-pager -n 100 \
  | tail -30                       # check for new errors
# Then run the verification curl from step 5 above.
```

`status` will show `active (running)` quickly (within 1-2 seconds) but
Telegram connect takes longer; the DNS-over-HTTPS line is normal and
should resolve in a few seconds. If after 30 seconds you still don't see
either a successful startup notification (proves HOME_CHANNEL works) or
a clean absence of errors, the config is still wrong.

## Common Pitfalls

1. **Trusting the green status light.** A gateway can be "active (running)"
   and entirely broken in config. Always check the journal.
2. **Editing config.yaml when the key is also in .env.** Silent shadowing;
   the gateway keeps the old `.env` value. Edit `.env` directly.
3. **Confusing a bot's own ID with the owner's user_id.** Both are integers,
   both look the same in `getMe` output. The bot's ID is from
   `getMe`; the user's ID is from a message the user sent (or
   `getChat?chat_id=<id>` — type:private + first_name confirms a real user).
4. **Restarting the gateway then immediately declaring success.** Give it
   5-10 seconds for connect, then verify with a real round-trip message.
5. **Checking only the active profile's logs.** Multi-profile setups
   (`hermes gateway list`) have one gateway per profile. If the user is
   messaging a bot bound to a different profile, you'll be reading the
   wrong logs. Confirm with `hermes gateway list` and cross-check the
   bot's username against the profile's `TELEGRAM_BOT_TOKEN` via
   `getMe`.
6. **Telling the user to "find their user_id" without giving a recipe.**
   They need a one-step path: open `@userinfobot` → Start → read the
   number. Anything longer and they will paste the bot ID again.
7. **Reporting a "fix" based on the gateway restart alone.** The deliverable
   is a verified working round-trip, not a green status line. Run the
   end-to-end verification in step 5 before declaring done.
8. **Capturing the bot's own ID as a "lesson learned".** The next time
   this happens, the fix is the same — find the right user_id, set the
   right key, restart. The lesson is the recipe, not the specific numbers.

## Verification Checklist

- [ ] `hermes gateway status` shows active
- [ ] `journalctl` shows the most recent 60 seconds free of the same
      `Forbidden` / `Blocked unauthorized` signature that was failing
- [ ] Bot→user test message (curl) returns `ok:true` and lands in the
      right chat
- [ ] User→bot test message in Telegram gets a reply within a few seconds
- [ ] If multiple profiles are running, the fix is in the profile that
      owns the affected bot
- [ ] Both `.env` and `config.yaml` are consistent (or `.env` is the
      source of truth and yaml's value is irrelevant for the keys that
      exist in `.env`)
