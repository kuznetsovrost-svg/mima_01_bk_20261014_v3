"""
send-file-with-preview.py — отправка файла в Matrix с текстовым
превью и автоматической верификацией доставки.

Копируй и модифицируй, а не пиши с нуля. Используй, когда нужно
доставить длинный файл (документацию, миграционный план,
дамп, отчёт) и сопроводить его кратким описанием.

Использование:

    # 1) Положи токен бота в 0600-файл (см. SKILL.md §7):
    #       (umask 077; grep -E '^MATRIX_ACCESS_TOKEN=' .../env | sed ... ) > /tmp/.mx_tok
    #       chmod 600 /tmp/.mx_tok
    #
    # 2) Поправь константы ниже и запусти:
    python3 send-file-with-preview.py

Внутри — три шага:
  1) send_text() — короткое превью (структура, версия, что внутри)
  2) send_file() — сам файл как m.file с filename/mimetype/size
  3) recent_messages() — проверка, что оба event'а дошли
"""

import importlib.util
import os
import sys

# Загрузка клиента из шаблона того же skill'а.
# Не пытайся делать "from matrix_direct_cs_client import ..."
# — файл с дефисами в имени не import'ится по имени.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_PATH = os.path.join(
    SCRIPT_DIR, "..", "templates", "matrix-direct-cs-client.py"
)
spec = importlib.util.spec_from_file_location("mx_client", CLIENT_PATH)
_m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_m)
MatrixClient = _m.MatrixClient


# ──── Поправь под свою задачу ──────────────────────────────────────
HOMESERVER = "https://msg.lab.aidemo.adaptivepm.ru"
TOKEN_FILE = "/tmp/.mx_tok"
ROOM_ID    = "!qtymGlxhfChwRcTygM:msg.lab.aidemo.adaptivepm.ru"
FILE_PATH  = "/tmp/Migration01.txt"
FILENAME   = "Migration01.txt"   # ASCII — иначе URL-encode (?filename=)
MIMETYPE   = "text/plain"

PREVIEW = (
    "🚚 Migration01.txt — пошаговый план миграции\n\n"
    "Метод: rsync по SSH + короткий cutover.\n"
    "Файл прикреплён ниже (≈23 КБ)."
)
# ──────────────────────────────────────────────────────────────────


def main() -> int:
    if not os.path.exists(FILE_PATH):
        print(f"file not found: {FILE_PATH}", file=sys.stderr)
        return 1
    if not os.path.exists(TOKEN_FILE):
        print(f"token file not found: {TOKEN_FILE}", file=sys.stderr)
        return 1

    mx = MatrixClient(HOMESERVER, TOKEN_FILE)

    print(f"file size: {os.path.getsize(FILE_PATH)}")
    who = mx.whoami()
    print(f"whoami: {who.get('user_id')}  device: {who.get('device_id')}")

    # 1) Превью текстом
    eid_text = mx.send_text(ROOM_ID, PREVIEW)
    print(f"text event_id: {eid_text}")

    # 2) Сам файл
    eid_file = mx.send_file(
        ROOM_ID, FILE_PATH,
        filename=FILENAME,
        mimetype=MIMETYPE,
    )
    print(f"file event_id: {eid_file}")

    # 3) Верификация: последние 3 сообщения
    last3 = mx.recent_messages(ROOM_ID, limit=3)
    print("\nlast 3 events in room:")
    for ev in last3:
        c = ev.get("content", {})
        sender = ev.get("sender")
        if c.get("msgtype") == "m.text":
            body = c.get("body", "")[:80].replace("\n", " ")
            print(f"  [text] from {sender}: {body}")
        elif c.get("msgtype") == "m.file":
            print(
                f"  [file] from {sender}: "
                f"{c.get('body')}  size={c.get('size')}  "
                f"mxc={c.get('url')}"
            )
        elif c.get("msgtype") == "m.room.encrypted":
            print(f"  [encrypted] from {sender} (cannot read body)")
        else:
            print(f"  [{c.get('msgtype')}] from {sender}")

    return 0


if __name__ == "__main__":
    sys.exit(main())


# ──── Известные подводные камни (см. SKILL.md §4a) ─────────────────
#
# 1) Кириллица в FILENAME ломает upload с HTTP 400 M_BAD_QUERY.
#    Если имя файла не-ASCII, оборачивай в urllib.parse.quote():
#        from urllib.parse import quote
#        # но upload идёт через send_file() — там ?filename=...
#        # собирается без quote. Workaround: передавай
#        # ASCII-имя (например Migration01.txt), а в body
#        # m.room.message оставляй кириллицу — клиент покажет
#        # нормально. Проверено на Synapse 1.x.
#
# 2) Токен НИКОГДА не пиши в исходнике как литерал. Если
#    матрица шаблона подменяется «***» (sanitization-слой
#    Hermes — см. SKILL.md §2a), скрипт сломается тихо.
#    Решение: TOKEN_FILE снаружи, chmod 600.
#
# 3) ROOM_ID должен быть румом, где бот уже [join] — иначе
#    send_text / send_file вернёт M_FORBIDDEN. Если юзер
#    «не видит бота», проблема не в этом скрипте, а в
#    membership — см. references/matrix-no-reply.md.
#
# 4) Если файл > 100 МБ — Synapse по умолчанию режет на
#    max_upload_size. Для больших файлов нужен chunked
#    upload (/v1/media/v3/upload_async), его в шаблоне
#    пока нет.
# ──────────────────────────────────────────────────────────────────
