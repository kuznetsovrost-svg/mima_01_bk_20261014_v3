#!/usr/bin/env python3
"""
export_user_messages.py — Extract user_messages from a Hermes profile's state.db
into a chronological markdown file.

Usage:
    python3 export_user_messages.py [profile_name] [source_filter] [output_path]

Examples:
    python3 export_user_messages.py fst-control telegram /root/fst-запросы-01.md
    python3 export_user_messages.py fst-control cli /tmp/cli-audit.md
    python3 export_user_messages.py                     # defaults

Default behavior: active profile = 'fst-control', source = 'telegram',
output = '/root/<profile>-запросы-<NN>.md' (NN = next free index).

Companion skill: chat-history-export (see ~/.hermes/profiles/<profile>/skills/
productivity/chat-history-export/SKILL.md)
"""

import sqlite3
import re
import sys
import os
from datetime import datetime, timezone
from collections import defaultdict


# --- Configuration ----------------------------------------------------------

DEFAULT_PROFILE = "fst-control"
DEFAULT_SOURCE = "telegram"
DEFAULT_PROFILE_ROOT = "/root/.hermes/profiles"
DEFAULT_OUTPUT_DIR = "/root"

# Compiled once
OOB_RE = re.compile(r"\[OUT-OF-BAND USER MESSAGE.*?\[/OUT-OF-BAND USER MESSAGE\]", re.DOTALL)
THINK_RE = re.compile(r"^.*?^.*?$", re.DOTALL)
PRIOR_RE = re.compile(r"\[PRIOR CONTEXT.*?not a new message\]", re.DOTALL)
COMPACTED_PREVIEW_MAX = 3000


# --- Helpers ---------------------------------------------------------------

def clean(text: str) -> str | None:
    """Strip internal/non-user blocks. Returns None if the message is purely
    tool/instrumentation noise."""
    if not text:
        return None
    if PRIOR_RE.search(text):
        return None
    text = OOB_RE.sub("", text)
    text = re.sub(r"^.*?^.*?$", "", text, flags=re.DOTALL)
    text = text.strip()
    return text or None


def fmt_ts(t: float) -> str:
    return datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def next_index(out_dir: str, prefix: str) -> int:
    """Find next free NN in '<prefix>-NN.md' pattern."""
    n = 1
    while os.path.exists(os.path.join(out_dir, f"{prefix}-{n:02d}.md")):
        n += 1
    return n


# --- Core ------------------------------------------------------------------

def extract(profile_db: str, source_filter: str | None) -> tuple[list, dict]:
    """Return (message_dicts, sessions_dict) sorted by timestamp."""
    if not os.path.exists(profile_db):
        raise FileNotFoundError(
            f"Profile DB not found: {profile_db}\n"
            f"Check that profile name is correct and Hermes has been used at least once."
        )

    con = sqlite3.connect(profile_db)
    con.row_factory = sqlite3.Row

    # Filter clause
    if source_filter:
        where_source = "AND s.source = ?"
        params = (source_filter,)
    else:
        where_source = ""
        params = ()

    sql = f"""
        SELECT m.id, m.session_id, m.role, m.content, m.timestamp,
               m.active, m.compacted, s.started_at, s.ended_at, s.title, s.source
        FROM messages m
        JOIN sessions s ON s.id = m.session_id
        WHERE m.role = 'user'
        {where_source}
        ORDER BY s.started_at, m.timestamp
    """
    msgs = [dict(r) for r in con.execute(sql, params).fetchall()]

    sess = {r["id"]: dict(r)
            for r in con.execute("SELECT * FROM sessions ORDER BY started_at").fetchall()}
    con.close()
    return msgs, sess


def build_markdown(profile: str, msgs: list, sess: dict) -> str:
    """Render the markdown body."""
    by_sid = defaultdict(lambda: {"active": [], "compacted": []})
    for r in msgs:
        key = "compacted" if r["compacted"] else "active"
        by_sid[r["session_id"]][key].append(r)

    out: list[str] = []
    out.append(f"# {profile}-запросы-??")
    out.append("")
    out.append(f"> Сборник обращений пользователя к Hermes-боту")
    out.append(f"> Профиль: **{profile}**")
    out.append(f"> Источник: SQLite `state.db` → `messages` × `sessions`")
    out.append("")

    # Summary table
    total_active = sum(len(v["active"]) for v in by_sid.values())
    total_compacted = sum(len(v["compacted"]) for v in by_sid.values())
    out.append("## Сводка по сессиям")
    out.append("")
    out.append("| ID сессии | Начало | Конец | Заголовок | Сообщений | Активных user | Компактнутых |")
    out.append("|-----------|--------|-------|-----------|-----------|---------------|--------------|")
    for sid in sorted(sess):
        m = sess[sid]
        start = fmt_ts(m["started_at"])
        end = fmt_ts(m["ended_at"]) if m.get("ended_at") else "(активна)"
        out.append(
            f"| `{sid}` | {start} | {end} | {m['title']} | "
            f"{m.get('message_count', 0)} | {len(by_sid[sid]['active'])} | "
            f"{len(by_sid[sid]['compacted'])} |"
        )
    out.append(f"| **ИТОГО** | | | | | **{total_active}** | **{total_compacted}** |")
    out.append("")
    out.append(f"> ⚠️ **{total_active} активных обращений** (развёрнутые).")
    out.append(">")
    out.append(f"> ⚠️ **{total_compacted} компактнутых блоков** — Hermes-сжатие суммировало их в один блок. Не разделяются.")
    out.append("")

    # Active messages
    out.append("---")
    out.append("")
    out.append("## 1. Активные обращения (хронологически)")
    out.append("")
    n = 0
    for sid in sorted(sess):
        items = by_sid[sid]["active"]
        if not items:
            continue
        m = sess[sid]
        out.append(f"### Сессия `{sid}` — {m['title']}")
        out.append("")
        out.append(f"_Период: {fmt_ts(m['started_at'])} → {fmt_ts(m['ended_at']) if m.get('ended_at') else '(активна)'}_")
        out.append("")
        for r in items:
            n += 1
            content = clean(r["content"])
            if content is None:
                continue
            out.append(f"#### #{n:03d}  [{fmt_ts(r['timestamp'])}]  (msg_id={r['id']})")
            out.append("")
            out.append(content)
            out.append("")

    # Compacted blocks
    out.append("---")
    out.append("")
    out.append("## 2. Компактнутые блоки (превью)")
    out.append("")
    out.append("> Эти записи — результат сессионного сжатия Hermes. Не разделяются на отдельные сообщения.")
    out.append("")
    for sid in sorted(sess):
        blocks = by_sid[sid]["compacted"]
        if not blocks:
            continue
        out.append(f"### Из сессии `{sid}`")
        out.append("")
        for r in blocks:
            content = clean(r["content"]) if r["content"] else ""
            if not content:
                continue
            out.append(f"#### ⏚ Блок msg_id={r['id']}  [{fmt_ts(r['timestamp'])}]")
            out.append("")
            preview = (content[:COMPACTED_PREVIEW_MAX]
                       + (f"\n\n… [обрезано; полный размер {len(content)} символов] …"
                          if len(content) > COMPACTED_PREVIEW_MAX else ""))
            out.append("```text")
            out.append(preview)
            out.append("```")
            out.append("")

    return "\n".join(out)


# --- CLI -------------------------------------------------------------------

def main():
    profile = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PROFILE
    source = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_SOURCE
    output_path = sys.argv[3] if len(sys.argv) > 3 else None

    profile_db = os.path.join(DEFAULT_PROFILE_ROOT, profile, "state.db")
    source_filter = source if source.lower() != "all" else None

    # Auto-name output
    if not output_path:
        idx = next_index(DEFAULT_OUTPUT_DIR, f"{profile}-запросы")
        output_path = os.path.join(DEFAULT_OUTPUT_DIR, f"{profile}-запросы-{idx:02d}.md")

    msgs, sess = extract(profile_db, source_filter)
    md = build_markdown(profile, msgs, sess)

    # Replace title placeholder with actual filename
    import os.path as osp
    fname = osp.basename(output_path).rsplit(".", 1)[0]
    md = md.replace(f"{profile}-запросы-??", fname, 1)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)

    size = os.path.getsize(output_path)
    active_count = sum(1 for m in msgs if not m["compacted"])
    compacted_count = sum(1 for m in msgs if m["compacted"])
    print(f"✅ Written: {output_path}")
    print(f"   size: {size:,} bytes")
    print(f"   active: {active_count}, compacted: {compacted_count}")
    print(f"\n→ Send via: MEDIA:{output_path}")


if __name__ == "__main__":
    main()
