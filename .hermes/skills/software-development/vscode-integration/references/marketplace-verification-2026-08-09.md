# Marketplace verification + multi-agent configs (2026-08-09)

## What's verified

Verified against the live VS Code Marketplace API on 2026-08-09
(`marketplace.visualstudio.com/_apis/public/gallery/extensionquery`,
`searchText="strato-space.acp-plugin"`, `searchText="poppywu124.hermes-chat"`,
`searchText="hermes agent"`, `searchText="agent client protocol"`).

| Extension | Publisher | version | Stars/Forks | License | Notes |
|---|---|---|---|---|---|
| `strato-space.acp-plugin` | strato-space | (version not in API response) | 8 / 0 | Apache 2.0 | Native ACP client, supports `command: ssh`. First choice for Windows→Linux server. |
| `poppywu124.hermes-chat` | Poppywu124 | 0.7.1 | (not in API response) | MIT | "Hermes Agent Chat" — sidebar chat. Spawns `hermes acp` locally; requires Hermes on the VS Code host. Repo: `github.com/Narizis/hermes-chat-vscode` (12 stars, 8 forks, TypeScript). |
| `joaompfp.hermes-ai-agent` | joaompfp | n/a | n/a | n/a | "VS Code sidebar for the Hermes AI agent" — claims ACP. |
| `Poppywu124.hermes-chat` README (verified): "This extension does not bundle Hermes Agent. It is a VS Code frontend for a **local Hermes CLI installation**." |
| `strato-space.acp-plugin` README (verified): "ACP is the protocol. This repository ships a **client**." |

## Why this matters

- `poppywu124.hermes-chat` does NOT work if `hermes` is missing from
  the VS Code host's PATH. On Remote-SSH sessions to a Linux server,
  that means installing the extension via **"Install in SSH: <host>"**
  so the extension host lives on the server.
- `strato-space.acp-plugin` does NOT have this constraint — its
  `command` field accepts `ssh`, so the extension host on the user's
  laptop just spawns `ssh user@server /path/hermes-acp`. **Default
  choice for Windows → Linux server.**
- Multiple similarly-named extensions live in the Marketplace
  (`Natadel.hermes-ollama-vscode`, `JoveRina.rina-hermes-acp`,
  `automaitiq.hermes-agent`, `GrupoLada.hermes-vscode`,
  `hermes-dev.hermes-dev-extension-pack`, `formulahendry.acp-client`).
  None of these are first-party Hermes.

## Working `agent_servers` config (verified 2026-08-09)

Saved as `templates/agent-servers-mima-g-01.json` — the full
multi-agent setup that the user pasted, validated, and got working
on mima_g_01. Uses `root@mima-g-01` (hyphens) to match the existing
`Host mima-g-01` block in the user's `~/.ssh/config`.

JSON-level validation:
- All three entries use `command: "ssh"` (NOT `"hermes"` — that
  variant fails because it tries to run `hermes` locally on the
  VS Code host, not on the remote server).
- Each profile has an explicit `--profile <name>` flag. Without
  this, the gateway falls through to the implicit-`default` profile
  regardless of what the agent name implies.
- `cwd: "${workspaceFolder}"` resolves to the user's currently-open
  project in VS Code.
- `acp.connectTimeoutMs: 600000` (10 minutes) — generous enough for
  cold-start model loading on the remote server.
- `acp.autoApprovePermissions: "ask"` — every tool call prompts the
  user. Safer than `allowAll` until the user trusts the agent.
- `acp.logTraffic: true` — keeps JSON-RPC traffic in the `ACP
  Traffic` output channel for debugging.

## The `mima_g_01` vs `mima-g-01` pitfall (verbatim)

Error returned by VS Code (`strato-space.acp-plugin`) when the JSON
used `root@mima_g_01` (underscores) but `~/.ssh/config` declared only
`Host mima-g-01` (hyphens):

```
Agent process exited before ACP initialized (code: 255).
stderr: ssh: Could not resolve hostname mima_g_01: No such host is known.
```

VS Code runs `ssh` locally; the local SSH client does hostname
resolution against `~/.ssh/config` only. An underscore-only spelling
with no matching `Host` block returns "No such host is known" and
exits 255 — which the ACP client surfaces verbatim.

**Resolution ladder:**
1. Read `cat ~/.ssh/config` to find existing `Host` lines.
2. Use the existing alias spelling in the JSON.
3. If you want the underscore spelling to work, add a new `Host`
   block to `~/.ssh/config` mapping it to the same `HostName`:

```
Host mima_g_01
    HostName 72.56.29.69
    User root
    IdentityFile ~/.ssh/id_ed25519_mima
    IdentitiesOnly yes
    PreferredAuthentications publickey
    Port 22
```

(Use the actual `HostName` from the original `Host mima-g-01` block.)

## ACP `settings.json` field reference (verified 2026-08-09)

| Field | Type | Default | Notes |
|---|---|---|---|
| `agent_servers` | object | `{}` | Main agent configuration, Zed-compatible. `acp.agents` is supported as alias. |
| `acp.includeBuiltInAgents` | bool | `true` | Include built-in presets in the agent selector. |
| `acp.connectTimeoutMs` | int | `600000` | Max time for ACP `initialize()`. |
| `acp.autoApprovePermissions` | string | `"ask"` | `"ask"` or `"allowAll"`. |
| `acp.defaultWorkingDirectory` | string | `""` | Empty uses current workspace folder. |
| `acp.logTraffic` | bool | `true` | Log raw ACP JSON-RPC traffic. |

Variable expansion supported in `command`, `args`, `cwd`:
`${workspaceFolder}`, `${userHome}`, `${env:NAME}`.

Built-in agent presets (when `acp.includeBuiltInAgents: true`):
`codex`, `fast-agent-acp`, `github-copilot`, `claude-code`, `gemini`,
`qwen-code`, `auggie`, `qoder`, `opencode`. All default to `npx`-based
invocations; require Node.js on the machine running VS Code.

## Related

- `agent-audit` — read-only audit of third-party agent bundles
  before installing them on the same Hermes host.
- `ssh-remote-audit` — for the SSH-key / known_hosts / first-login
  side of getting the SSH transport working before the ACP layer
  is even relevant.
- `hermes-profile-management` — explains the four-tier skill
  visibility model that becomes relevant once the user has
  `--no-skills` profiles reachable via VS Code.