# Matrix thread disambiguation — operational playbook

Companion to the main `messaging-gateway-setup` SKILL.md, §"Pre-flight"
and §"Don't `clarify()` over thread variants". This file is the
concrete recipe; the SKILL.md tells you when to run it.

## The problem in one paragraph

`send_message(action='list')` on this homeserver
(`msg.lab.aidemo.adaptivepm.ru`) returns 5 entries that all look
like separate Matrix destinations but are actually the same room
with different `thread_id` suffixes. If you send to the first
entry, your message lands in a thread the user is not watching
and they report "ничего не пришло" (nothing arrived), even though
the gateway cheerfully reported `success: true` and a `message_id`.

## Step 1 — read the directory, don't trust the list

`send_message list` is a summary. The canonical mapping lives at
`~/.hermes/channel_directory.json`. Read it directly:

```python
import json, os
p = os.path.expanduser("~/.hermes/channel_directory.json")
if not os.path.exists(p):
    print("NO_DIRECTORY")  # gateway may not be running
else:
    d = json.load(open(p))
    matrix = d.get("platforms", {}).get("matrix", [])
    print(f"rooms: {len({m['id'].split(':')[0] for m in matrix})}, "
          f"entries: {len(matrix)}")
    for m in matrix:
        rid, _, tid = m["id"].partition(":")
        print(f"  room={rid}  thread={tid}  name={m.get('name')!r}")
```

If `entries >> rooms` (5 entries / 1 room in this setup), the
list is misleading and you MUST pick the room root, not a thread.

## Step 2 — compute the right target string

```python
# Build it from the room_id you found in step 1 — no thread_id.
# For the known single-room setup:
room_id = "!OwBtrzzKTGFSNSmvQU:msg.lab.aidemo.adaptivepm.ru"
target_top = "matrix:" + room_id
# Equivalent wrong form (lands in thread):
target_thread = "matrix:rostislav_k / topic $G8SVCz9ReZ4VpeaJHr611oQFWSLV0oLI6oTPHgnH4Bg"
```

The string is built from concatenated halves so the source has no
run of three `*` (the sanitization layer would mangle the literal
thread_id-like strings, though `$...` is actually safe — the split
is for clarity, not sanitization avoidance).

## Step 3 — verify scope after the send

`send_message` returns JSON. The two fields that matter:

```python
result = send_message(target=target_top, message=..., action="send")
# Typical good return:
#   {"success": true,
#    "platform": "matrix",
#    "chat_id": "!OwBtrzzKTGFSNSmvQU:msg.lab.aidemo.adaptivepm.ru",
#    "message_id": "$abc...",
#    "mirrored": true}
#
# Typical bad (landed in thread) return:
#   {"success": true,
#    "chat_id": "!OwBtrzzKTGFSNSmvQU:msg.lab.aidemo.adaptivepm.ru",  # same room
#    "message_id": "$abc...",
#    "mirrored": true}  # mirror flag is NOT a scope indicator
```

The `chat_id` alone won't tell you thread vs room — both look
like the room_id. To verify scope you need to ask the gateway log
or query the room's `/messages` endpoint with the new message_id.
Cheaper alternative: just tell the user "check the main room,
not a thread" and ask "дошло?" — they confirm in <5 seconds.

## Decision matrix

| `send_message list` shape                | Correct action                                       |
|------------------------------------------|------------------------------------------------------|
| 1 entry                                  | Use it directly (no thread)                          |
| N entries, all same `room_id`            | Use `matrix:<room_id>` (no `:thread_id`). DON'T `clarify`. |
| N entries, different `room_id`s          | Open-ended `clarify` "Which room?" — user types name |
| N entries, user named a thread explicitly | Use `matrix:<room_id>:<thread_id>` form             |
| Empty                                    | Gateway not running; tail `~/.hermes/logs/gateway.log` |

## Anti-pattern log (real session burns)

1. **2026-06-16, this session.** Took the first list entry
   (`matrix:rostislav_k / topic $G8SVCz9ReZ4VpeaJHr611oQFWSLV0oLI6oTPHgnH4Bg`),
   sent a file with `MEDIA:` tag, user reported "ничего не
   пришло". Fix: re-sent to `matrix:!OwBtrzz…` (no thread).
   Root cause: the first list entry IS a thread of the same
   room, and the `send_message` "success" response did not flag
   the scope mismatch.

2. **2026-06-16, this session.** Used `clarify` with 4 choices
   of thread_id variants. The user didn't answer (they don't
   recognize the difference between threads visually). `clarify`
   timed out, agent had to retry without the prompt. Fix: skip
   the prompt, send to room root, verify with "дошло?".

3. **General.** Reading `mirrored: true` as "delivered to room"
   is wrong — it's a multi-platform echo flag and tells you
   nothing about scope. Read `chat_id` shape (presence of `$...`
   thread tail) only as a partial hint, not as proof.

## Cross-references

- Main skill: `messaging-gateway-setup/SKILL.md` — §"Disambiguating
  'the same room N times' vs 'N rooms'" + §"Pre-flight" + §"Don't
  `clarify()` over thread variants".
- User profile: "не отвечать в тредах, слать top-level" — the
  preference, not the technical disambiguation.
- Memory entry: "Matrix на этом HS: send_message list показывает
  5 «разных» таргетов" — quick factoid for the next session.
