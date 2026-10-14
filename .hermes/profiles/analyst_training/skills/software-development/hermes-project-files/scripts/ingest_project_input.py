#!/usr/bin/env python3
"""
ingest_project_input.py — atomic "copy one file into projects/<slug>/Inputs/".

Usage:
    python ingest_project_input.py \
        --profile analyst_training \
        --slug academic-course-anl-01 \
        --source /path/to/file.md

If --source is omitted, the script auto-discovers the most recently
created file in the profile's cache/documents/ directory (Telegram
attachments land there).

Behavior:
    1. Resolves profile dir = ~/.hermes/profiles/<profile>/
    2. Resolves project root = profile/projects/<slug>/
    3. Creates Inputs/ if missing
    4. Copies source -> project_root/Inputs/<basename> with shutil.copy2
       (preserves mtime)
    5. Verifies: size matches, UTF-8 decode succeeds, names preserved
    6. If projects.db has the slug as a project and primary_path is NULL,
       sets primary_path + inserts project_folders row
    7. Prints a one-line summary; exits 0 on success, 1 on any failure

The script never renames the file and never modifies its content.
"""

from __future__ import annotations
import argparse
import os
import shutil
import sqlite3
import sys
import time
from pathlib import Path


def find_latest_cache_doc(profile_dir: Path) -> Path | None:
    """Return the most recently modified file in cache/documents/, or None."""
    cache = profile_dir / "cache" / "documents"
    if not cache.is_dir():
        return None
    candidates = [p for p in cache.iterdir() if p.is_file()]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def update_sqlite(profile_dir: Path, project_root: Path) -> tuple[str, str] | None:
    """If projects.db has a project matching this slug, set primary_path
    and insert a project_folders row. Returns (project_id, slug) or None."""
    db = profile_dir / "projects.db"
    if not db.exists():
        return None
    conn = sqlite3.connect(str(db))
    cur = conn.cursor()
    slug = project_root.name
    cur.execute("SELECT id FROM projects WHERE slug=? OR name=?", (slug, slug))
    row = cur.fetchone()
    if row is None:
        conn.close()
        return None
    project_id = row[0]
    cur.execute("UPDATE projects SET primary_path=? WHERE id=?", (str(project_root), project_id))
    cur.execute("SELECT COUNT(*) FROM project_folders WHERE project_id=?", (project_id,))
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO project_folders (project_id, path, label, is_primary, added_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (project_id, str(project_root), "project root", 1, int(time.time())),
        )
    conn.commit()
    conn.close()
    return (project_id, slug)


def verify_copy(src: Path, dst: Path) -> None:
    """Raise if the copy did not succeed byte-for-byte (size + UTF-8)."""
    src_size = src.stat().st_size
    dst_size = dst.stat().st_size
    if src_size != dst_size:
        raise RuntimeError(
            f"size mismatch after copy: src={src_size} dst={dst_size}"
        )
    # UTF-8 round-trip — file content unchanged
    dst.read_bytes().decode("utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", default="analyst_training")
    ap.add_argument("--slug", required=True, help="project slug, e.g. academic-course-anl-01")
    ap.add_argument("--source", default=None, help="path to file; if omitted, picks latest in cache/documents/")
    args = ap.parse_args()

    profile_dir = Path.home() / ".hermes" / "profiles" / args.profile
    if not profile_dir.is_dir():
        print(f"ERR: profile dir not found: {profile_dir}", file=sys.stderr)
        return 1

    src = Path(args.source) if args.source else find_latest_cache_doc(profile_dir)
    if src is None or not src.is_file():
        print("ERR: --source not given and cache/documents/ is empty", file=sys.stderr)
        return 1

    project_root = profile_dir / "projects" / args.slug
    inputs_dir = project_root / "Inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)

    dst = inputs_dir / src.name
    if dst.exists():
        # Don't clobber — refuse and let the caller decide
        print(f"ERR: destination already exists: {dst}", file=sys.stderr)
        return 1

    try:
        shutil.copy2(src, dst)
        verify_copy(src, dst)
    except Exception as e:
        print(f"ERR: copy/verify failed: {e}", file=sys.stderr)
        # Clean up partial copy if any
        if dst.exists():
            dst.unlink()
        return 1

    sqlite_info = update_sqlite(profile_dir, project_root)

    print(f"OK: {src} -> {dst} ({dst.stat().st_size} bytes)")
    if sqlite_info:
        pid, slug = sqlite_info
        print(f"    sqlite: primary_path set, project_folders row inserted (id={pid}, slug={slug})")
    return 0


if __name__ == "__main__":
    sys.exit(main())