#!/usr/bin/env python3
"""Send postprocessed transcript to Telegram via direct curl."""
import re
import subprocess
import sys
from pathlib import Path

ENV_FILE = Path("/root/.hermes/.env")
TARGET_CHAT = "505586502"  # Rost
FILE_PATH = Path("/tmp/hermes_audio_transcription/final/full_postprocessed.md")
CAPTION = "Postprocessed transcript (72 min, 37 chunks). Model: medium. Postprocess: MiniMax-M3. JEV: quality gate."

# Extract token from .env
env_content = ENV_FILE.read_text(encoding="utf-8")
m = re.search(r"^TELEGRAM_BOT_TOKEN=(\d{8,12}:[A-Za-z0-9_-]{30,50})", env_content, re.MULTILINE)
if not m:
    print("ERROR: TELEGRAM_BOT_TOKEN not found in /root/.hermes/.env")
    sys.exit(1)
token = m.group(1)
print(f"Token extracted: {token[:15]}...{token[-10:]}")

# Send via curl
cmd = [
    "curl", "-sS", "-X", "POST",
    f"https://api.telegram.org/bot{token}/sendDocument",
    "-F", f"chat_id={TARGET_CHAT}",
    "-F", f"document=@{FILE_PATH}",
    "-F", f"caption={CAPTION}",
]

print(f"Sending {FILE_PATH} ({FILE_PATH.stat().st_size / 1024:.1f} KB)...")
result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

print(f"\nCurl exit: {result.returncode}")
print(f"Stderr: {result.stderr[:200]}")

if result.returncode == 0:
    # Extract message_id from response
    try:
        import json
        resp = json.loads(result.stdout)
        if resp.get("ok"):
            msg_id = resp["result"]["message_id"]
            file_size = FILE_PATH.stat().st_size
            print(f"\n✅ SENT")
            print(f"Message ID: {msg_id}")
            print(f"File: full_postprocessed.md ({file_size} bytes = {file_size/1024:.1f} KB)")
            # Save to log
            log_path = Path("/tmp/hermes_audio_transcription/telegram_send.log")
            log_path.write_text(
                f"{msg_id}\n{full_postprocessed.md}\n{file_size}\n",
                encoding="utf-8"
            )
        else:
            print(f"❌ Telegram API error: {resp}")
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse response: {e}")
        print(f"Response: {result.stdout[:500]}")
else:
    print(f"❌ Curl failed")