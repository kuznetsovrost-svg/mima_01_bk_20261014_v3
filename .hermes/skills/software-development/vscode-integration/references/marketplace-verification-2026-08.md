# VS Code Marketplace Verification — 2026-08 sessions

Session-specific details from ACP extension searches performed on
2026-08-08 and 2026-08-09 against the public VS Code Marketplace API
(`marketplace.visualstudio.com/_apis/public/gallery/extensionquery`).
Use this file as a starting point — the catalog changes, so re-verify
before any install.

## What Was Queried

Three searches:

1. 2026-08-08: `searchText="agent client protocol"` → 50 results.
2. 2026-08-08: `searchText="hermes agent"` → 20 results, several
   real Hermes-named agents that mention ACP.
3. 2026-08-09: same queries, refreshed list, + 12 newly surfaced
   extension IDs that came back in the second pass.

## Verified ACP Clients (2026-08-09)

`displayName` matches "ACP" with non-trivial `shortDescription`. Listed
in approximate order of relevance to a "talk to a remote Hermes from
VS Code" workflow:

| Extension ID | Display Name | Description (verbatim, truncated) |
|---|---|---|
| `strato-space.acp-plugin` | ACP — Agent Client Protocol | ACP client for VS Code. Chat with Agent Client Protocol (ACP) compatible coding agents directly in your editor. |
| `formulahendry.acp-client` | ACP Client | Agent Client Protocol client for VS Code — connect to GitHub Copilot, Claude Code, Gemini CLI, Qwen Code, Codex CLI, OpenCode, OpenClaw, Kiro CLI, Hermes Agent, and any ACP-compatible AI coding agent. |
| `multicoder.multicoder` | Multicoder ACP - One UI for every agent | Run coding agents directly from VS Code. One interface for Claude, Codex, OpenCode, Qwen, Hermes, and any other ACP-compatible agent. |
| `cosmosjeon.nexus-acp` | Nexus ACP | AI coding agents in VS Code via Agent Client Protocol (ACP). Chat with Claude, OpenCode, and other ACP-compatible agents directly in your editor. |
| `omercnet.vscode-acp` | VSCode ACP | AI coding agents in VS Code via Agent Client Protocol (ACP). Chat with Claude, OpenCode, and other ACP-compatible agents directly in your editor. |
| `nakedev.acp-nakedev` | ACP Nakedev | Connect AI agents to VS Code and Cursor via Agent Client Protocol (ACP). |
| `duclvz.acp-pro` | ACP Pro | One ACP Client for every AI agent (Claude, Copilot, Codex, …) with multi-tab sessions and remote sharing control. |
| `Brokk.brokk-vscode-acp` | Brokk ACP | Open Agent Client Protocol coding in VS Code with bundled Anvil and the official ACP registry. |
| `johnhom.acp-pilot` | ACP Pilot | A VS Code extension that connects to ACP agents through a custom chat panel. |
| `CheersCodeSL.paco-acp-chat` | Paco ACP Chat | VS Code extension to chat with the Paco ACP server. |
| `IrishBruse.ib-acp-ui` | ACP UI | Agent Client Protocol (ACP) UI integration. |
| `SolutionsUnity.acp-patchbay` | ACP Patchbay | Any ACP agent. Every integration it can accept. Shown exactly as it is. |

## Verified Hermes-Specific Extensions (ACP support claimed)

| Extension ID | Display Name | Description (verbatim, truncated) |
|---|---|---|
| `Poppywu124.hermes-chat` | Hermes Agent Chat | Persistent multi-agent Hermes chat with streaming ACP tools, workspace context, per-agent settings, memory, and history. |
| `joaompfp.hermes-ai-agent` | Hermes AI Agent | VS Code sidebar for the Hermes AI agent. Streams chat, runs tools, manages sessions. Multi-model (Claude, Codex). Communicates over ACP. |
| `Natadel.hermes-ollama-vscode` | Ollama Hermes Agent | Chat with Hermes Agent in VS Code via Ollama. Uses ACP protocol — full agent with tools, memory, and skills. |
| `JoveRina.rina-hermes-acp` | Rina Hermes ACP | Chat with Hermes Agent directly inside VS Code. |
| `automaitiq.hermes-agent` | Hermes Agent for Cursor & VS Code | Integrate Hermes Agent directly into your Cursor editor — manage kanban tasks, search sessions, run skills, and more. |

## Verified Generic Coding Agents (no Hermes claim)

| Extension ID | Display Name | Notes |
|---|---|---|
| `Continue.continue` | Continue - open-source AI code agent | Multi-provider. Has a custom-providers slot. |
| `kilocode.Kilo-Code` | Kilo Code: AI Coding Agent, Copilot, and Autocomplete | Open source. |
| `Joouis.agent-maestro` | Agent Maestro | Spawns Cline/Roo with Claude Code or Codex. |
| `anthropic.claude-code` | Claude Code for VS Code | Official Anthropic. |
| `openai.chatgpt` | Codex – OpenAI's coding agent | OpenAI. |

## Decoy / Unrelated "ACP" Matches

These show up in `searchText="acp"` searches but are NOT Agent Client
Protocol. Recommend against unless the user has a specific need:

| Extension ID | What it actually is |
|---|---|
| `UoA.acp` | Active Classroom Programmer — lecture tool. |
| `HannanAliShah.acp-pradyuman-bc` | Plays a sound on terminal errors. |
| `PratikshitSingh.cid-acp-vscode-extension` | Plays audio alert on exit-127. |
| `AhmadNYC.acp-git-commands` | git add/commit/push shortcut. |
| `AhmadNYC.git-acp-enhanced` | git add/commit/push wrapper. |
| `slimal.git-acp` | git add/commit/push. |
| `VITS101.BEST-PM-FASTrack-PMI-ACP-Exam-Simulation-Software-V-7ra` | PMP exam simulator (PMI's "Agile Certified Practitioner"). |
| `DataModelingGroup.OpenDataProtocolVisualizer` | OData visualization. |

## End-to-End Verified

Only **one** extension was tested end-to-end against the live
`mima_g_01` server in these sessions:

| Extension ID | Result |
|---|---|
| `strato-space.acp-plugin` | Verified working. Settings.json `command: ssh root@mima_g_01 /usr/local/lib/hermes-agent/venv/bin/hermes-acp` connected successfully. README fetched from `github.com/strato-space/acp-plugin` (Apache 2.0). |

All other entries above are vendor-supplied descriptions only.

## What Was NOT Verified

- **Install counts / ratings** — the public Marketplace API returned
  empty `statistics` arrays in both 2026-08-08 and 2026-08-09 calls. Do
  not cite install numbers without re-fetching and confirming non-null.
- **Version numbers** — the API did not return `versions[0].version`
  in the same call shape I used. Do not cite version numbers.
- **Compatibility with `hermes-acp` 0.18.x** — only `strato-space.acp-plugin`
  was tested end-to-end. The other extension descriptions claim ACP,
  but I did not connect to `hermes-acp` through any of them.
- **License** — only `strato-space.acp-plugin` (Apache 2.0) and
  `Poppywu124.hermes-chat` (MIT) were pulled from GitHub repos and
  verified. The rest are unknown until the user pulls the source.

## How to Re-Verify Before Any New Install

If more than a few weeks have passed, re-run:

```python
import subprocess, json
curl = subprocess.run(
    ["curl", "-s", "-X", "POST",
     "https://marketplace.visualstudio.com/_apis/public/gallery/extensionquery",
     "-H", "Content-Type: application/json",
     "-H", "Accept: application/json;api-version=7.1-preview.1",
     "-d", json.dumps({
         "filters": [{"criteria": [
             {"filterType": 10, "value": "agent client protocol"}
         ], "pageNumber": 1, "pageSize": 50}],
         "flags": 0,
     })],
    capture_output=True, text=True, timeout=15,
)
d = json.loads(curl.stdout)
for r in d.get("results", []):
    for ext in r.get("extensions", []):
        nm = ext.get("extensionName", "?")
        pub = ext.get("publisher", {}).get("publisherName", "?")
        disp = ext.get("displayName", "?")
        desc = ext.get("shortDescription", "?")[:80]
        print(f"{pub}.{nm} — {disp}: {desc}")
```

The `filterType: 10` is the search-text filter. The `filterType: 5` is
category, which only accepts Marketplace-internal category IDs (not
free-text) and returns `400` if you pass a category name as a string.

## Marketplace API Gotchas (Re-verified 2026-08-09)

- `displayName` is what the user sees in the UI; `extensionName` is the
  slug used in `code --install-extension`.
- `extensionId` = `publisherName.extensionName`. This is what you pass
  to `--install-extension`.
- The API does NOT return publisher reputation, install trend, or
  recency in a single call. You'd need to follow up with separate calls
  per extension.
- The `flags: 0` request returns basic info; `flags: 0x1` includes
  more (e.g., statistics), `flags: 0x20` includes version metadata. The
  flag set used here returned basic fields.

## What Was Installed Locally (these sessions)

Nothing was installed. The recommendations are guidance only. The user
must run `code --install-extension <id>` on their Windows machine
themselves.

## Files Generated Across These Sessions

User-facing artefacts delivered via `@MMRV_Hermes_bot` `sendDocument`:

- 2026-08-08: `VS-Code-Hermes.md` (11 865 B) — basic connection playbook.
- 2026-08-08: `VS-Code-Hermes-Playbook.md` (15 204 B) — full strategy.
- 2026-08-08: `Порядок-работы-с-документом-VS-Code.md` (16 656 B) —
  first-task workflow + parallel profile authoring.
- 2026-08-09: `Hermes-Chat-VS-Code-Setup.md` (17 231 B) — poppywu124
  deep-dive (for Windows user who asked the right question about
  local-vs-remote).
- 2026-08-09: `strato-space-acp-playbook.md` (16 336 B) — the
  SSH-friendly alternative, with a verified multi-agent settings.json
  example.

## Lessons for Future Sessions

1. **Always caveat extension recommendations.** The Marketplace catalog
   shifts; an extension that exists today may be deprecated or replaced
   next month. Give the user the install command and let them verify.
2. **Always verify `hermes-acp` on the server first.** Don't promise a
   working connection until `hermes acp --check` returns OK on the
   server the user is connecting from.
3. **Don't cite install counts you haven't fetched.** The API doesn't
   always return `statistics[]`. If you don't have a number, don't
   quote one.
4. **Document the routing rule.** Files delivered via Telegram must use
   the bot whose chat the user is in. Cross-bot delivery is forbidden.
5. **Distinguish local-vs-remote at the recommendation step.** For a
   Windows user on Remote-SSH to a Linux server, `poppywu124.hermes-chat`
   **fails** because there's no `hermes` on Windows. The right pick is
   `strato-space.acp-plugin` (configurable `command: ssh`) or installing
   the Hermes-specific extension **inside the remote VS Code** via
   "Install in SSH: <host>".
6. **The Marketplace is full of decoys.** "ACP" appears in PMP exam
   simulators, audio cues, git wrappers, classroom programming tools.
   Filter on `displayName`/`shortDescription` for the actual
   "Agent Client Protocol" string, not just the acronym.