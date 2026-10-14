# Gateway cannot reach upstream

Symptom: gateway is `active (running)`, bot token is valid, but Telegram (or any other platform) doesn't respond. `gateway.log` shows a steady stream of warnings like:

```
WARNING gateway.platforms.telegram_network: [Telegram] Primary api.telegram.org connection failed (); trying fallback IPs 149.154.166.110
WARNING gateway.platforms.telegram_network: [Telegram] Fallback IP 149.154.166.110 failed:
WARNING gateway.platforms.telegram: [Telegram] Network error on send (attempt 1/3), retrying in 1s: Timed out
```

The 10-second cadence and the fallback-IP wording are diagnostic — the platform is trying, failing, retrying, exhausting backoff. **Configuration is not the problem; the network path to the upstream is.**

## Step 1 — confirm it's the network, not the token

```bash
# From the gateway host:
curl -sS -m 6 -o /dev/null -w "%{http_code} %{time_total}s\n" https://api.telegram.org/
curl -sS -m 6 -o /dev/null -w "%{http_code} %{time_total}s\n" https://149.154.166.110/
# As a control (should work even when Telegram is blocked):
curl -sS -m 6 -o /dev/null -w "%{http_code} %{time_total}s\n" https://www.google.com/
```

| Result to `api.telegram.org` | Control to google.com | Verdict |
|---|---|---|
| `200` (or 301/302) | `200` | Network OK — recheck token, firewall on the platform side, or recent config change |
| `000` timeout | `200` | **Host-level block** to Telegram subnet (most common cause) |
| `000` timeout | `000` timeout | **No internet at all** — fix upstream connectivity first |
| `301`/`302`/`403` | `200` | DNS / SNI / TLS issue, not a transport block |

If you get `200` to `api.telegram.org` from the gateway host but the bot still doesn't respond, check `~/.hermes/logs/gateway.log` for *token*-shaped errors (`Unauthorized`, `chat not found`, `Bot was blocked by the user`) rather than *network*-shaped ones.

## Step 2 — locate the block

Quick triage on the gateway host:

```bash
# DNS resolution — does it return IPv4, IPv6, or both?
getent hosts api.telegram.org
dig +short api.telegram.org A api.telegram.org AAAA

# TCP reachability to the IPs (Telegram typically lives in 149.154.160.0/20)
for ip in 149.154.166.110 91.108.56.0/22; do
  nc -vz -w 4 "$ip" 443 2>&1
done

# Routes
ip route get 149.154.166.110
ip -6 route get 2001:67c:4e8:f004::9

# Local firewall (root)
sudo iptables -L OUTPUT -n -v | head
sudo nft list ruleset 2>/dev/null | grep -iE "telegram|149.154"
```

Typical findings:
- `getent` returns an IPv6 address but the host only has IPv4 → IPv6 is dead, IPv4 also dead → host firewall or upstream provider is dropping both.
- Routes exist but `nc -vz` to the IP times out → stateful firewall / outbound filter on the host, VM, or hypervisor.
- `dig` returns CNAME → DNS is being intercepted (corporate / state-level).

## Step 3 — three escape plans

Pick by what you have available, not by what's cheapest.

### Plan A — own relay (you control the upstream)

Best when: you have a second Linux machine with a public IP, OR a Windows/Mac box reachable via reverse SSH.

1. On the relay host: install a SOCKS5/HTTP proxy that allows connections to `api.telegram.org:443`. 3proxy and dante both work; minimal 3proxy config:
   ```
   # /etc/3proxy/3proxy.cfg
   daemon
   plugin socks_soft -p8443
   external 0.0.0.0
   internal 127.0.0.1
   auth strong
   users youruser:CL:yourpassword
   allow youruser
   ```
2. On the **gateway host** (where Hermes runs), set up an autossh reverse tunnel to keep the relay reachable:
   ```bash
   sudo apt install -y autossh
   autossh -M 0 -N \
     -o "ServerAliveInterval=30" -o "ServerAliveCountMax=3" \
     -R 127.0.0.1:18443:127.0.0.1:8443 \
     youruser@relay-host
   ```
3. Add the proxy in `gateway.platforms.telegram`:
   ```yaml
   gateway:
     platforms:
       telegram:
         proxy: socks5://youruser:yourpassword@127.0.0.1:18443
   ```
4. `systemctl --user restart hermes-gateway` and re-check `gateway.log`.

### Plan B — paid SOCKS5 / HTTP proxy

Best when: no spare machine, willing to pay a few $/month.

1. Subscribe to a SOCKS5 provider (ProtonVPN, Mullvad, IPRoyal, etc.). Get a `socks5://user:pass@host:port` string.
2. Add it to `gateway.platforms.telegram.proxy` exactly as in Plan A step 3.
3. Restart and verify.

Caveat: if you're behind a state-level block (Roskomnadzor, GFW, etc.), most commercial proxies are already known and blocked. Choose a provider whose IP ranges aren't on the block list, or rotate.

### Plan C — move gateway to the relay

Best when: the gateway host can't reach Telegram *and* you can't/shouldn't add a proxy on it (e.g. it's a rented VPS in a different region from your network). Move the **gateway process**, not all of Hermes — the CLI/cron profile can stay on the original host.

1. On the relay (Linux or WSL 2 Ubuntu):
   ```bash
   curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
   ```
2. From the **current gateway host**, copy the two files that matter:
   ```bash
   scp ~/.hermes/.env        youruser@relay:~/.hermes/
   scp ~/.hermes/config.yaml youruser@relay:~/.hermes/
   ```
3. On the relay, fix perms and start the gateway:
   ```bash
   chmod 600 ~/.hermes/.env
   hermes setup gateway      # Telegram will show "configured" (token in .env)
   hermes gateway install
   systemctl --user status hermes-gateway
   ```
4. On the **old** host, stop and disable the gateway so only one process polls Telegram (otherwise two gateways fight over `getUpdates`):
   ```bash
   hermes gateway stop
   systemctl --user disable hermes-gateway
   sudo systemctl --user mask hermes-gateway
   ```
5. Verify: `tail -f ~/.hermes/logs/gateway.log | grep -i telegram` on the relay. Press `/start` in Telegram.

### Windows-specific variant of Plan C (WSL 2)

Most home users don't have a Linux box — they have a Windows laptop. WSL 2 Ubuntu is the cheapest path:

1. `wsl --install` in an admin PowerShell, reboot.
2. In WSL: enable systemd so `hermes gateway install` works:
   ```bash
   sudo tee /etc/wsl.conf >/dev/null <<'EOF'
   [boot]
   systemd=true
   EOF
   ```
   Then `wsl --shutdown` from PowerShell, reopen Ubuntu.
3. Install Hermes inside WSL, `scp` the config, `hermes gateway install`. Done.

Gotchas worth knowing up front:
- WSL 2 freezes when Windows sleeps. If the bot must be 24/7, disable sleep in Windows Power Options — or accept that Plan C-via-WSL is a "laptop-must-be-awake" arrangement and put gateway on a VPS / Pi if that doesn't fit.
- `~/.hermes/.env` copied from a Windows-side editor will arrive with CRLF line endings; strip them in WSL: `sed -i 's/\r$//' ~/.hermes/.env`.
- Forward WSL's port 22 if you want to reach the gateway host externally; otherwise Plan C-via-WSL is local-only.

## Plan D — wait it out

If the upstream block is transient (host migration, datacenter move, your provider is rolling a new route table), the gateway will reconnect on its own once the path opens. `hermes gateway status` will flip from "warning loop" to clean reconnects. No code change needed; just keep the gateway running.

## Quick decision matrix

| You have... | Pick |
|---|---|
| A second Linux server with a public IP | A (own relay) |
| A Windows/Mac machine, willing to leave it on 24/7 with WSL | C-WSL |
| A laptop that sleeps / no spare machine | C-VPS, B, or D |
| $0 budget and patience | D |
| $3-5/month and no patience | C-VPS (Hetzner/DO/Vultr) |
| Sensitive about exit IPs (corporate audit) | A with self-hosted relay |

## Related

- `hermes-agent` SKILL.md, "Gateway (Messaging Platforms)" — `gateway.platforms.<platform>` block schema.
- `hermes-agent` SKILL.md, "Troubleshooting → Gateway issues" — log-grep recipes, systemd linger, WSL2 systemd=true requirement.
