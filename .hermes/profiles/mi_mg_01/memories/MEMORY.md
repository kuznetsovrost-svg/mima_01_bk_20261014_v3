Telegram polling на twc1.net (8.31.79.37): ВОССТАНОВЛЕНА 2026-07-02. api.telegram.org IPv4 — HTTP 302 за 0.07s; IPv6 egress нет; fallback IP 149.154.166.110 — TLS SNI-чувствителен (api.telegram.org, не IP). Бот @MMRV_Hermes_bot id 8933960684, home 505586502, systemd linger OK. Прежний блок был транзиторным.
§
Hermes gateway Matrix adapter uses mautrix (gateway/platforms/matrix.py) with self-written _verify_device_keys_on_server() guard. On homeserver msg.lab.aidemo.adaptivepm.ru errors with M_BAD_JSON 'device_keys' values must be a list of strings (HS-side compat, not config). Workarounds + Python client template in skill `messaging-gateway-setup` (references/matrix.md, templates/matrix-direct-cs-client.py). When gateway is broken, send via direct C-S API — see that skill's "Когда gateway-шлюз не подходит" section.
§
Hermes sanitizes real tokens (3+ `*`-runs) into literal `***` в write_file/terminal/execute_code. Симптом: `Bearer <tok>` в bash-кавычках → eval-ошибка; curl получает `Authorization: Bearer ***`. Fix: split `Authorization`/`-H @file`/Python-req; detail в skill `messaging-gateway-setup` §"Тонкости shell-quoting".
§
`terminal()` writes to agent-state files under `~/.hermes/` (e.g. `cat >> ~/.hermes/memories/MEMORY.md <<EOF`) are BLOCKED by a user-consent gate. For `~/.hermes/memories/*` edits, prefer `patch`/`write_file`; fall back to `terminal()` only after explicit user OK.
§
Global git config: `user.name=kuznetsovrost-svg`, `user.email=kuznetsov.rost@gmail.com`, и `url.git@github.com:.insteadof https://github.com/` — HTTPS github URLs в clone/fetch/pull silently rewritten to SSH.
§
Matrix на этом HS: send_message list показывает 5 «разных» таргетов, но это ОДНА комната !OwBtrzzKTGFSNSmvQU:msg.lab.aidemo.adaptivepm.ru с разными thread_id. Для top-level delivery — target = matrix:!OwBtrzzKTGFSNSmvQU:msg.lab.aidemo.adaptivepm.ru БЕЗ :thread_id. clarify() с выбором из 5 = ловушка (висит до таймаута).
§
User style: "diagnose first, fix second" — не любит выдумывать баг. Подтверждено 2026-07-02 (fail2ban/systemd/getUpdates).