---
name: vscode-integration
description: >
  Connect a remote Hermes Agent to VS Code on the user's local machine via the
  Agent Client Protocol (ACP), set up the SSH transport, and run day-to-day
  IDE-assisted work — code review, inline edits, file generation, multi-file
  refactoring, and "open N tabs as context" workflows. Use when the user says
  "подключи меня к VS Code", "работать через VS Code", "open these files in
  VS Code", "send this to my editor", or asks for a side-by-side
  chat-in-IDE workflow where the remote agent becomes a panel inside the
  editor. NOT for editing files purely on the server (use read_file + patch
  in place), NOT for running a local-only agent without an IDE in the loop,
  and NOT for IDEs that don't speak ACP (IntelliJ without the ACP plugin,
  Sublime, vim, etc.).
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [vscode, acp, ide-integration, remote-development, ssh-tunnel, agent-protocol]
    related: [tool-output-injection-defense, agent-audit, ssh-remote-audit, hermes-agent-skill-authoring]
---

# VS Code Integration via ACP

Class: a remote Hermes Agent install (a daemon on `mima_g_01`-style headless
Linux server) speaks to a local VS Code on the user's machine over SSH via
the **Agent Client Protocol (ACP)** — an open protocol where the editor is
client and the agent is server. The user opens N files as context, asks the
agent for review/edits, and applies the diff inline. The class covers the
end-to-end recipe: ACP setup on the server, VS Code extension choice on the
client, settings.json transport, the "N tabs as context" pattern, multi-agent
profiles, Excalidraw/Figma/docx reading, and safe defaults when the user has
not yet authorised anything.

## When to Use This Skill

- The user mentions "VS Code" + a remote server ("Hermes на mima_g_01", "мой
  сервер", "удалённый агент") and wants to connect them.
- The user asks "what extensions do I need", "how do I make my editor talk
  to you", "setup VS Code integration", "open these files in VS Code".
- The user has multiple text/JSON/MD files open and wants the agent to
  reason across them ("open 5 tabs as context for a new document").
- The user wants to extend the remote agent's capabilities inside the IDE
  (custom profile, model switch, skill invocation).
- The user asks about ACP specifically ("is ACP installed", "what's the
  version", "how do I check").

Triggers (Russian or English): "подключи к VS Code", "соедини VS Code с
сервером", "ACP", "Agent Client Protocol", "remote agent", "чат в VS Code",
"IDE assistant", "side panel agent".

## What ACP Is (Short)

ACP = **Agent Client Protocol**, an open standard where:

- The **editor** (VS Code, Zed, JetBrains) is the *client*.
- The **agent** (Hermes, or any compliant agent) is the *server*.
- They communicate over **stdio** (or another transport), exchanging JSON-RPC
  messages that describe prompts, tool calls, file selections, diffs, and
  permissions.

Hermes ships with a built-in ACP server (`hermes-acp`, package version
visible via `hermes acp --check`). The remote agent is fully functional
without VS Code — ACP is just one of several transports (CLI, Telegram,
HTTP, ACP).

## Extension Selection: Local-Only vs SSH-Native ACP

`Poppywu124.hermes-chat` and `strato-space.acp-plugin` look similar in the Marketplace but have **different transport models**. Pick based on whether VS Code is local or Remote-SSH.

| Extension | Where Hermes runs | User experience |
|---|---|---|
| `strato-space.acp-plugin` | At the SSH target. The `command` field accepts `ssh`, so the extension host on the user's laptop just runs `ssh user@server /path/hermes-acp`. | Works on local VS Code talking to remote Hermes. Default for Windows → Linux server. |
| `Poppywu124.hermes-chat` | On the same machine as VS Code — it spawns `hermes acp` as a child of the extension host. | Requires `hermes` on `$PATH` on the VS Code host. In Remote-SSH sessions, install via "Install in SSH: <host>" so the extension host lives on the server. |

**Pitfall (recurring, hit 2026-08):** recommending `Poppywu124.hermes-chat` to a Windows user in a Remote-SSH session to a Linux server. It fails because there's no `hermes` binary on the Windows host. The fix is either (a) `strato-space.acp-plugin` with `command: ssh`, or (b) install `Poppywu124.hermes-chat` **into the remote VS Code** via "Install in SSH: <host>". Verify with `which hermes` inside the shell VS Code uses before recommending.

**Marketplace is crowded with similarly-named extensions:** `Natadel.hermes-ollama-vscode`, `joaompfp.hermes-ai-agent`, `JoveRina.rina-hermes-acp`, `automaitiq.hermes-agent`, `GrupoLada.hermes-vscode`, `hermes-dev.hermes-dev-extension-pack`, `formulahendry.acp-client`. None of these are first-party. Before recommending, fetch the live Marketplace API and verify the extension's `description` mentions ACP.

**Pitfall (recurring, hit 2026-08-09): SSH hostname in JSON does not match `~/.ssh/config`.** When writing a multi-agent `agent_servers` JSON for `strato-space.acp-plugin`, the `args[0]` (e.g. `root@mima_g_01`) must exactly match a `Host` alias already declared in the user's local `~/.ssh/config`. On `mima_g_01` the existing config declares `Host mima-g-01` (with hyphens) — but users often type `mima_g_01` (with underscores) in the JSON because that's the convention used in conversation and compaction summaries. VS Code then runs `ssh root@mima_g_01` locally, gets `ssh: Could not resolve hostname mima_g_01: No such host is known.` (exit 255), and the ACP client reports `Agent process exited before ACP initialized` (verified error string verbatim, 2026-08-09). Fix: (a) change the JSON to match the existing alias (`root@mima-g-01`), or (b) add a new alias block to `~/.ssh/config` mapping `mima_g_01` → the same `HostName`. **Before writing or pasting any `agent_servers` JSON**, do `cat ~/.ssh/config` on the user's machine and read out the existing `Host` lines — write the JSON against those names, not against whatever spelling is comfortable in prose.

## When NOT to Use This Skill

- The user only wants to read/edit files on the server directly — no IDE.
  Use `read_file` + `patch` in place.
- The IDE is not ACP-capable (Sublime, vim/Neovim without the plugin,
  older JetBrains without the integration). Recommend alternative or
  fall back to Remote-SSH + manual file edits.
- The user wants the agent to control the cursor or do live collaboration
  in the canvas — ACP does not expose drawing primitives. For
  `.excalidraw`/`.figma`/diagram workflows, see the
  `creative/excalidraw` and `creative/figma-api-import` skills, which
  describe file-level JSON read/write through ACP — but not real-time
  drawing.

## Workflow

### 1. Verify ACP on the server (read-only)

```bash
ssh user@mima_g_01 "hermes acp --check"
# Expected: Hermes ACP check OK
```

If not OK, do NOT auto-install. Tell the user what's missing and offer a
plan. The agent has no authority to install missing packages without an
explicit "install it" approval.

### 2. Decide which VS Code extension to install

The VS Code Marketplace has at least three classes of relevant extensions
(verified 2026-08 against the public Marketplace API):

| Extension | What it does | When to recommend |
|---|---|---|
| `strato-space.acp-plugin` | Native ACP client. Single-purpose: chat with any ACP-compatible agent. The `command` field can be `ssh`, so the agent runs at the SSH target, not at the VS Code host. | **First choice for Windows-user-→-Linux-server** — no need to install Hermes on Windows. |
| `Poppywu124.hermes-chat` (`Hermes Agent Chat`) | Sidebar chat for the Hermes Agent specifically. **Spawns `hermes acp` locally** as a child process of the VS Code extension host. | Works only when `hermes` is on the same machine as VS Code. In Remote-SSH sessions, install via "Install in SSH: <host>" so the extension host runs on the server. |

**Pitfall:** Never recommend an extension by name unless its `extensionName`
was verified against the live Marketplace API in this session. The catalog
changes; do not cite install counts or star counts that you have not just
fetched. When in doubt, give the user the `code --install-extension <id>`
command and let them confirm.

### 3. settings.json transport (ACP over SSH)

The minimal client-side config for `strato-space.acp-plugin`:

```json
{
  "acp.agents": [
    {
      "name": "Hermes",
      "command": "ssh",
      "args": [
        "user@mima_g_01",
        "/path/to/venv/bin/hermes-acp"
      ]
    }
  ]
}
```

Verify the path on the server first. Common locations:

- `/usr/local/lib/hermes-agent/venv/bin/hermes-acp`
- `~/.local/share/uv/.../venv/bin/hermes-acp` (uv-managed installs)
- `~/venv/bin/hermes-acp`

If SSH-key auth isn't set up, walk the user through `ssh-keygen` +
`ssh-copy-id` before changing `settings.json`.

### 4. The "N tabs as context" pattern

When the user opens K context files and 1 working file, ACP sees **paths
and active tab titles** but **not their content by default**. The agent
must explicitly `read_file` each one. This is the most common UX surprise.

**Template reply to the user (translate as needed):**

```
Я вижу K открытых табов и M выделенных фрагментов. Чтобы я мог с ними
работать, мне нужно явно подтвердить — какие из них контекст, какой —
рабочий, и в каком порядке читать. Дай мне:
1. Список файлов-контекста (требования, данные, пример).
2. Рабочий файл.
3. Порядок: сначала правила, потом данные, потом пример.
```

The user will reply with a list. Then run a single batch:

```python
for path in context_paths:
    content = read_file(path)
    # append to session memory, not to the visible reply
```

**Pitfall:** do NOT load all 5 files into the user-visible reply. The user
asked for help, not a transcription of their own files. Summarise after
reading; reference specific lines only when the user asks.

### 5. Three working modes

Document these three modes explicitly so the user can choose:

| Mode | What the agent does | When to use |
|---|---|---|
| **A. Review** | Reads the working file, comments against requirements, returns a structured diff or report. The user keeps typing. | The user is a confident writer and wants feedback. |
| **B. Generate** | Reads the example/requirements, drafts a section, returns an apply-ready diff. The user clicks "Apply" in VS Code. | The user wants to move fast and trusts the agent's first draft. |
| **C. Iterate** | The user highlights a paragraph in the working file, asks for a rewrite, the agent returns the replacement. | The user has a draft and wants incremental improvement. |

The agent should default to **A** unless the user explicitly asks for B or C.

### 6. Large source documents (>200K tokens)

If the example or requirements file exceeds ~200K tokens (≈ 600-page DOCX,
≈ 1.5M words, ≈ 8000-line JSON), the agent cannot hold it whole. Recipe:

1. **Slice first.** Use `python-docx` (already available in the default
   install) to extract a TOC: list of all `Heading 1-3` paragraphs with
   their indices.
2. **Read by section.** When the user asks for "section N", read only that
   section (`read_file` with offset/limit or extract paragraphs in range).
3. **Do NOT load the entire example into context.** Even with a 1M-token
   model, the marginal quality gain is small and the prompt-cache hit rate
   drops to zero.

```python
from docx import Document
doc = Document("example-600.docx")
toc = [(i, p.style.name, p.text) for i, p in enumerate(doc.paragraphs)
       if p.style.name.startswith("Heading")]
# Save TOC for repeated use
```

### 7. Multi-agent profiles in VS Code

Each `acp.agents[]` entry is one panel. The user can keep several open:

- `Hermes · main` → analyst_training profile, full SOUL.md
- `Hermes · coder` → short-answer coding profile
- `Hermes · reviewer` → focused on bugs/security
- `Hermes · fast` → cheaper/faster model

Each profile runs in its own ACP session, with its own context budget. The
agent on the server picks the profile by the entry the user clicked.

**Pitfall:** the kernel (SOUL.md) is shared across profiles. Switching
profiles changes the *system prompt additions* (skill visibility,
personality), not the *kernel rules* (privacy, fail-safe, injection
defense). Don't promise the user that switching profiles bypasses any
hard rule from SOUL §3-§11.

**Telegram token routing pitfall:** the profile's bot token lives in
`/root/.hermes/profiles/<name>/.env`. The `default` profile's token lives
in `/root/.hermes/.env`. When the user reaches the agent via bot A, files
must be delivered via bot A's token. Sending via the wrong token routes
the file through the wrong bot. Verify the active profile by reading the
system prompt's "Active Hermes profile:" line, not from session memory.

### 8. What to do when the user opens binary / office files

| Format | How the agent reads it via ACP |
|---|---|
| `.md`, `.txt`, `.json`, `.yaml`, `.csv` | Direct `read_file`. |
| `.docx` | `python-docx` via the existing `creative/docx-authoring` pattern; do NOT attempt raw XML parsing unless explicitly asked. |
| `.pdf` | `pdf-toolkit` skill (pymupdf / marker-pdf). |
| `.excalidraw` | JSON via `read_file`; see `creative/excalidraw`. |
| `.figma` | Not a file — use `figma-api-import` skill and the Personal Access Token. |
| `.png`/`.jpg` | Image analysis (`vision_analyze`) on demand. |

The agent must **say** which tool it's using, so the user understands why
the agent pauses for a moment before responding.

### 9. Safe defaults

When the user has not authorised destructive actions in this session:

- ✅ Read files (`read_file`).
- ✅ Read-only listing / search (`search_files`, `terminal ls/cat`).
- ✅ Patch files **in the working file only** when the user explicitly
  asks "apply this diff".
- ❌ Don't run setup scripts, install dependencies, restart services, or
  modify config files.
- ❌ Don't write into `/root/.hermes/profiles/<other_profile>/` without
  explicit cross-profile authorisation (the cross-profile soft guard
  triggers by default).

## Pitfalls

### "I'll just read all the tabs"

Do NOT loop through every open tab on every turn. Context is a budget, not
a grab-bag. Read once, summarise, cache the summary in the session. Re-read
only when the user explicitly says "re-read X" or after a `git pull`.

### "I can see what you're typing"

ACP exposes selection, not keystrokes. The agent sees what the user
**selects** (highlighted text, current cursor position), not what the user
**types** between selections. Don't pretend to give "live autocomplete";
that's a different class of tool (Copilot/Continue autocomplete channel).

### "VS Code extension X definitely supports ACP"

You have not verified unless you just fetched the Marketplace listing in
this session. Always caveat recommendations. Provide the
`code --install-extension <publisher>.<name>` command and the link to the
Marketplace page so the user can confirm before installing.

### "Switching profile changes the kernel"

Profiles add overlays (USER.md extension, skill set, model choice), but
the kernel (SOUL.md v11) stays the same. The agent cannot "escape" tier-1
rules (privacy, fail-safe, injection defense) by switching profiles. If
the user asks "can I get a profile that doesn't redact tokens?" — no,
because redaction is a kernel rule, not a profile setting.

### "ACP died after 10 minutes"

When the user reports sessions that disconnect within 3-15 minutes of
opening, the cause is almost always **timeout mismatch**:

| Layer | Default | Symptom if wrong |
|--------|---------|-----------------|
| `acp.streamIdleTimeout` | 120 seconds | Session drops while model "thinks" > 2 min |
| `acp.connectTimeoutMs` | 600000 (10 min) | Connection times out on slow startup |
| SSH `ServerAliveInterval` | unset | TCP dies through NAT/firewall |
| `acp.reconnectOnFailure` | unset | Brief network glitch kills session |

Fix: in the user's `settings.json`, raise the ACP timeouts to match the
expected thinking time and reconnect on transient failures:

```json
{
  "acp.connectTimeoutMs": 1800000,
  "acp.streamIdleTimeout": 1800,
  "acp.reconnectOnFailure": true,
  "acp.maxReconnectAttempts": 5,
  "acp.reconnectDelayMs": 5000
}
```

Then add SSH keepalive to `~/.ssh/config`:

```
Host mima-g-01
    HostName 72.56.29.69
    ServerAliveInterval 30
    ServerAliveCountMax 6
    TCPKeepAlive yes
```

Diagnose the failure layer with `ssh -v` and look at the timestamp
between TCP connect and the first protocol banner. If the gap is < 2
minutes, the issue is SSH-side. If the gap matches a thinking pause, the
issue is `acp.streamIdleTimeout`.

### "Profile via --profile flag vs HERMES_PROFILE env"

`hermes-acp` does **not** accept `--profile <name>` (verified error: `error:
unrecognized arguments: --profile default`). To target a non-default
profile, pass `HERMES_PROFILE=<name>` through the ACP client's
`env` field rather than `args`:

```json
{
  "agent_servers": {
    "hermes-default": {
      "command": "ssh",
      "args": [
        "root@mima-g-01",
        "/usr/local/lib/hermes-agent/venv/bin/hermes-acp"
      ],
      "env": {
        "HERMES_PROFILE": "default"
      }
    }
  }
}
```

This pattern lets one extension entry per profile; switching in VS Code
selects the profile by entry. Confirmed working on 2026-08-09.

### "I see your 600-page DOCX in context"

You don't, not whole. The skill explicitly forbids loading it whole.
Slice first, then read by section. If the user pushes back ("just read
the whole thing"), explain the token budget and offer the TOC + on-demand
section reads as the working pattern.

### "I'll save the conversation locally"

When the user asks for a written playbook about the VS Code integration,
**write through `/tmp` + `subprocess.run(["cp", tmp, dst])`**, then verify
via `read_file` from a separate channel, then deliver via Telegram using
the `messaging-gateway-setup` recipe (sendDocument, not `MEDIA:` shortcut).
The `tool-output-injection-defense` skill governs the injection-defense
part; the `messaging-gateway-setup` skill governs the delivery part.

### "Apply this diff inline"

ACP supports showing the user a diff and asking for approval, but **the
agent must never auto-apply** to a file outside the working tab. If the
user opens `requirements.md` and `output.md`, edits proposed by the agent
go to `output.md` only. Editing the requirement source is a privacy
violation (the user might be holding a third-party template they do not
own).

## Examples of Real Use

- User: "Открыто 5 файлов контекста + 1 пустой. Сгенерируй введение в
  новый документ." → Agent: confirms list, reads 1-2 at a time, generates
  diff for the empty tab, returns.
- User: "Я выделил функцию handle_auth. Проверь на race condition." →
  Agent: reads the selection, returns targeted review.
- User: "Сделай TOC для example-600.docx." → Agent: runs the
  `python-docx` snippet, returns TOC, keeps it cached for the session.
- User: "Какое расширение VS Code ставить?" → Agent: runs Marketplace
  query via the public API, gives the user a concrete
  `code --install-extension` command, does NOT install anything itself.

## Checklist Before Recommending an Install

Before recommending a specific `code --install-extension` command, verify:

1. [ ] The extension name and publisher were fetched from the live
       Marketplace API in this session.
2. [ ] The path to `hermes-acp` on the server was confirmed via
       `hermes acp --check` or `which hermes-acp`.
3. [ ] SSH-key auth from Windows → server is set up.
4. [ ] The user has explicitly accepted the install (don't pre-install
       without asking).
5. [ ] If recommending an `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` /
       provider choice: confirm with the user which provider they want;
       don't guess from the system prompt.

## Related Skills

- `tool-output-injection-defense` — the same `/tmp + subprocess.cp` recipe
  applies when delivering a VS Code–related playbook as a file artifact.
- `agent-audit` — when the user wants to inspect a third-party agent
  before installing/running it; the read-only discipline overlaps.
- `ssh-remote-audit` — for "check the server" workflows that predate VS
  Code setup (key auth, gateway health, service probes).
- `messaging-gateway-setup` — for delivering the playbook back to the
  user via Telegram or another channel.
- `hermes-agent-skill-authoring` — if the user wants to create a
  dedicated `vscode-coder` profile.

## Reference Files

- `references/marketplace-verification-2026-08.md` — verified extension
  IDs from the 2026-08-08 session against the live Marketplace API,
  with caveats on what was and was not verified, and the recipe for
  re-running the search when the catalog shifts.