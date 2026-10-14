#!/usr/bin/env python3
"""
Send a local file to Telegram via Bot API.

Reusable helper used by every per-lecture sender in a batch-transcription
session. Extracts TELEGRAM_BOT_TOKEN from /root/.hermes/.env via a regex
(so the unsanitized token is never written into chat-visible code), posts
the file as a Telegram document to the given chat_id, prints the resulting
message_id on stdout. Use as a one-shot CLI:

    python3 send_telegram_doc.py /path/to/file.md "Optional caption < 200 chars"

The defaults match the production setup on the Hermes gateway (bot token
read from /root/.hermes/.env, chat_id 505586502). Override via flags
or env if you need a different target.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ENV_FILE = Path("/root/.hermes/.env")
DEFAULT_CHAT_ID = "505586502"
TOKEN_RE = re.compile(r"^TELEGRAM_BOT_TOKEN=(\d{8,12}:[A-Za-z0-9_-]{30,50})", re.MULTILINE)


def extract_token() -> str:
    text = ENV_FILE.read_text(encoding="utf-8")
    m = TOKEN_RE.search(text)
    if not m:
        sys.exit(f"ERROR: TELEGRAM_BOT_TOKEN not found in {ENV_FILE}")
    return m.group(1)


def send(filepath: Path, caption: str, chat_id: str) -> int:
    token = extract_token()
    cmd = [
        "curl", "-sS", "-X", "POST",
        f"https://api.telegram.org/bot{token}/sendDocument",
        "-F", f"chat_id={chat_id}",
        "-F", f"document=@{filepath}",
    ]
    if caption:
        cmd += ["-F", f"caption={caption}"]
    # --max-time caps curl at 180s; subprocess.run timeout caps the Python wait at 240s.
    # The parent terminal() call has its own timeout (default 180s) — large MD files
    # (30+ KB) need the parent's timeout raised to 300s when invoking this script.
    cmd[1:1] = ["--max-time", "180"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
    resp = json.loads(r.stdout)
    if not resp.get("ok"):
        sys.exit(f"Telegram API error: {resp}")
    return int(resp["result"]["message_id"])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("filepath", type=Path)
    ap.add_argument("caption", nargs="?", default="")
    ap.add_argument("--chat-id", default=DEFAULT_CHAT_ID)
    args = ap.parse_args()
    if not args.filepath.exists():
        sys.exit(f"ERROR: {args.filepath} does not exist")
    if len(args.caption) > 1024:
        sys.exit("ERROR: caption > 1024 chars (Telegram limit)")
    msg_id = send(args.filepath, args.caption, args.chat_id)
    size_kb = args.filepath.stat().st_size / 1024
    print(f"SENT: msg_id={msg_id}, size={size_kb:.1f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
