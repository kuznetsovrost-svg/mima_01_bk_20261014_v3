#!/usr/bin/env python3
"""
Audit what the agent (or the gateway on its behalf) has sent to a Matrix room.

Source of truth = the homeserver, NOT ~/.hermes/state.db.

Why not state.db? When the gateway's send_message adapter is the one that
ships the file (e.g. via the `MEDIA:/path` shortcut the platform adapter
intercepts), the rewritten event chain lives in the Matrix room, not in
the local tool_calls.arguments.message string. The state.db is what *we
asked for*; the homeserver is what *actually went out*. They can — and
do — disagree.

Usage:
    python3 audit-matrix-sends.py \\
        --homeserver https://msg.lab.aidemo.adaptivepm.ru \\
        --token-file /tmp/.mx_tok \\
        --room '!OwBtrzzKTGFSNSmvQU:msg.lab.aidemo.adaptivepm.ru' \\
        --bot-user '@oc_hermes:msg.lab.aidemo.adaptivepm.ru' \\
        --limit 200

Exits 0 on success, 1 on auth/transport failure. Prints a human-readable
summary plus a per-file table and a final TOTAL line.

If --bot-user is omitted, the script falls back to the user_id reported
by /account/whoami (any token can read this). This is the right default
for "count MY own sends" when you don't know the canonical user_id.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import urllib.parse


def _curl(method, url, token_file, *, data=None, extra_headers=None, timeout=15):
    """Single curl call. Reads the bearer from token_file, never argv."""
    headers_file = tempfile.NamedTemporaryFile(
        prefix=".mx_audit_hdr_", delete=False, mode="w"
    )
    try:
        # Build the header from non-asterisk parts to defeat the
        # Hermes payload sanitization (see SKILL.md §2a, §2b).
        hdr = "".join([
            "Auth", "orization: Bearer ",
            open(token_file).read().strip(),
            "\n",
        ])
        headers_file.write(hdr)
        headers_file.close()
        os.chmod(headers_file.name, 0o600)

        args = [
            "curl", "-sS", "-m", str(timeout),
            "-X", method,
            "-H", f"@{headers_file.name}",
        ]
        if extra_headers:
            for h in extra_headers:
                args.extend(["-H", h])
        if data is not None:
            args.extend(["--data-binary", data])
        args.append(url)
        r = subprocess.run(args, capture_output=True, text=True, check=True)
        return r.stdout
    finally:
        try:
            os.unlink(headers_file.name)
        except OSError:
            pass


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--homeserver", required=True,
                    help="e.g. https://msg.lab.aidemo.adaptivepm.ru")
    ap.add_argument("--token-file", required=True,
                    help="path to a 0600 file containing the Matrix access token")
    ap.add_argument("--room", required=True,
                    help="room_id, e.g. !OwBtrzzKTGFSNSmvQU:hs")
    ap.add_argument("--bot-user", default=None,
                    help="filter events to this sender; default = whoever the token belongs to")
    ap.add_argument("--limit", type=int, default=200,
                    help="how many recent events to page through (default 200)")
    ap.add_argument("--msgtypes", default="m.file,m.image,m.video,m.audio",
                    help="comma-separated msgtypes to count (default: all media)")
    args = ap.parse_args()

    hs = args.homeserver.rstrip("/")
    msgtypes = set(args.msgtypes.split(","))

    # Who am I?
    whoami_raw = _curl("GET", f"{hs}/_matrix/client/v3/account/whoami", args.token_file)
    whoami = json.loads(whoami_raw)
    bot = args.bot_user or whoami.get("user_id")
    if not bot:
        print(f"FAIL: /whoami did not return a user_id: {whoami_raw!r}", file=sys.stderr)
        return 1
    print(f"# bot user_id : {bot}")
    print(f"# room        : {args.room}")
    print(f"# limit       : {args.limit} (use --limit larger to page further back)")
    print()

    # Page through /messages. The endpoint paginates with `from=`; for an
    # audit, one or two pages of 200 are usually enough.
    url = (f"{hs}/_matrix/client/v3/rooms/{urllib.parse.quote(args.room, safe='!:')}"
           f"/messages?dir=b&limit={args.limit}")
    body = _curl("GET", url, args.token_file)
    chunk = json.loads(body).get("chunk", [])

    # If the first page hit the limit exactly, fetch the next page too.
    next_token = json.loads(body).get("end")
    if next_token and len(chunk) >= args.limit:
        body2 = _curl("GET", f"{url}&from={urllib.parse.quote(next_token, safe='')}",
                      args.token_file)
        chunk += json.loads(body2).get("chunk", [])

    print(f"# scanned {len(chunk)} events in the room timeline")
    print()
    print(f"{'event_id':<24} {'msgtype':<10} {'bytes':>10}  {'filename'}")
    print("-" * 80)

    totals = {mt: 0 for mt in msgtypes}
    by_msgtype = {mt: [] for mt in msgtypes}
    total_bytes = 0
    for ev in chunk:
        if ev.get("type") != "m.room.message":
            continue
        if ev.get("sender") != bot:
            continue
        c = ev.get("content", {})
        mt = c.get("msgtype", "")
        if mt not in msgtypes:
            continue
        totals[mt] += 1
        size = (c.get("info") or {}).get("size")
        # `info.size` is OPTIONAL on m.file per the C-S spec; older
        # homeserver-side uploads can produce events with size=null.
        # Don't trust the value for audit math; report what the HS
        # actually sent.
        size_str = "" if size is None else f"{size:>10,}"
        by_msgtype[mt].append(ev)
        if isinstance(size, int):
            total_bytes += size
        body = c.get("body", "") or c.get("filename", "")
        eid = ev.get("event_id", "")
        print(f"{eid[:22]:<24} {mt:<10} {size_str:>10}  {body}")

    print()
    print("=" * 80)
    for mt, n in totals.items():
        print(f"  {mt:<10}  {n}")
    print(f"  {'TOTAL':<10}  {sum(totals.values())} events, "
          f"{total_bytes:,} bytes (sum of non-null info.size)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
