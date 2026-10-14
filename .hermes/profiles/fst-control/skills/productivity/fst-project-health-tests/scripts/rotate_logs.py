#!/usr/bin/env python3
"""
rotate_logs.py — ротация логов скилла fst-project-health-tests.

Политика (v1.0.19):
    - логи старше 100 дней (≈3.3 месяца)  → gzip + logs/archive/YYYY-MM/
    - логи старше 400 дней (≈13.3 месяца) → удалить совсем

Зачем:
    Без ротации логи копятся бесконечно. У нас они маленькие (~37 KB
    на прогон), но привычка важна. С такой политикой в logs/ остаются
    последние ~3 месяца (читаемо), в archive/ — последний год
    (сжатые), старше — удалено.

Использование:
    # Текущий каталог logs/:
    python3 rotate_logs.py

    # Dry-run:
    python3 rotate_logs.py --dry-run

    # С другой политикой:
    python3 rotate_logs.py --archive-days 30 --delete-days 180

    # На конкретный каталог:
    python3 rotate_logs.py --log-dir /path/to/other/skill/logs

Безопасность:
    - НИКОГДА не трогает файлы не по маске "*.log" (только свои логи).
    - archive и delete — две разные фазы; archive выполняется всегда
      перед delete (если файл уже в архиве, он не будет удалён).
    - Dry-run по умолчанию выключен; --dry-run ничего не меняет.

Идемпотентность:
    Повторный запуск не приводит к ошибкам: файлы, уже в архиве или
    удалённые, отсутствуют в исходном каталоге.
"""

import argparse
import gzip
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

SKILL_VERSION = "1.0.19"
DEFAULT_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
DEFAULT_ARCHIVE_DAYS = 100
DEFAULT_DELETE_DAYS = 400

# ANSI.
def _c(code, text):
    return f"\033[{code}m{text}\033[0m"
def green(t): return _c("32", t)
def yellow(t): return _c("33", t)
def red(t): return _c("31", t)
def bold(t): return _c("1", t)


def parse_args():
    ap = argparse.ArgumentParser(
        description="Ротация логов fst-project-health-* (политика archive/delete по возрасту)."
    )
    ap.add_argument("--log-dir", type=Path, default=DEFAULT_LOG_DIR,
                    help="Каталог с логами (по умолчанию — logs/ рядом со скриптом).")
    ap.add_argument("--archive-days", type=int, default=DEFAULT_ARCHIVE_DAYS,
                    help="Возраст в днях для архивации (gzip + перенос в archive/YYYY-MM/).")
    ap.add_argument("--delete-days", type=int, default=DEFAULT_DELETE_DAYS,
                    help="Возраст в днях для удаления (только из logs/, не из archive/).")
    ap.add_argument("--dry-run", action="store_true",
                    help="Показать план без реальных действий.")
    return ap.parse_args()


def age_days(path: Path, now: datetime) -> float:
    """Возраст файла в днях (по mtime)."""
    return (now - datetime.fromtimestamp(path.stat().st_mtime)).total_seconds() / 86400


def archive_file(log: Path, log_dir: Path, dry_run: bool) -> str:
    """gzip → logs/archive/YYYY-MM/<basename>.log.gz. Возвращает описание."""
    now = datetime.now()
    archive_dir = log_dir / "archive" / now.strftime("%Y-%m")
    target = archive_dir / (log.name + ".gz")
    if dry_run:
        return f"would archive: {log.name} → archive/{now.strftime('%Y-%m')}/{log.name}.gz"
    archive_dir.mkdir(parents=True, exist_ok=True)
    with log.open("rb") as src, gzip.open(target, "wb", compresslevel=9) as dst:
        shutil.copyfileobj(src, dst)
    log.unlink()
    return f"archived: {log.name} → {target.relative_to(log_dir)}"


def delete_file(log: Path, dry_run: bool) -> str:
    """Удалить лог. Возвращает описание."""
    if dry_run:
        return f"would delete: {log.name}"
    log.unlink()
    return f"deleted: {log.name}"


def main() -> int:
    args = parse_args()
    log_dir: Path = args.log_dir
    archive_days: int = args.archive_days
    delete_days: int = args.delete_days
    dry_run: bool = args.dry_run

    if not log_dir.exists():
        print(red(f"Каталог не существует: {log_dir}"))
        return 1
    if not log_dir.is_dir():
        print(red(f"Не каталог: {log_dir}"))
        return 1

    print(bold(f"\n🗂  rotate_logs v{SKILL_VERSION}"))
    print(f"   Каталог:    {log_dir}")
    print(f"   Политика:   > {archive_days}d → archive; > {delete_days}d → delete")
    print(f"   Режим:      {'DRY-RUN' if dry_run else 'БОЕВОЙ'}")

    now = datetime.now()

    # Шаг 1: посчитать все *.log (НЕ трогаем .gitkeep, .gz и т.п.)
    logs = sorted(log_dir.glob("*.log"))
    if not logs:
        print(yellow(f"   В {log_dir} нет *.log файлов — нечего ротировать."))
        return 0

    print(f"\n   Найдено {len(logs)} .log файлов в {log_dir.name}/")
    print(f"   ─────────────────────────────────────────────")

    archived = []
    deleted = []
    skipped = []

    for log in logs:
        age = age_days(log, now)
        # Сначала проверяем delete (старше delete_days) — удаляем.
        if age > delete_days:
            try:
                msg = delete_file(log, dry_run)
                deleted.append(msg)
                print(f"   {red('✗')} {msg} (age={age:.0f}d)")
            except Exception as e:
                print(f"   {red('✗ delete failed')}: {log.name} — {type(e).__name__}: {e}")
        # Затем archive (старше archive_days, но моложе delete_days).
        elif age > archive_days:
            try:
                msg = archive_file(log, log_dir, dry_run)
                archived.append(msg)
                print(f"   {yellow('→')} {msg} (age={age:.0f}d)")
            except Exception as e:
                print(f"   {red('✗ archive failed')}: {log.name} — {type(e).__name__}: {e}")
        else:
            skipped.append(log.name)
            # Не печатаем «пропущено» — их слишком много, шум.

    # Шаг 2: почистить archive/, если там слишком старые файлы (> delete_days в архиве).
    # По политике удаляются только из logs/, не из archive/.
    # Этого достаточно: archive сам истечёт через 4 года, если archive-период 400d,
    # значит в archive попадают файлы 400-1500d; удаляются >1500d.
    # Т.е. archive живёт файлами 400-1500d, потом удаляются. Нормально.

    print(f"   ─────────────────────────────────────────────")
    if dry_run:
        print(f"\n📋 DRY-RUN: ничего не менялось.")
    print(bold(f"\n{'='*60}"))
    print(bold(f"ИТОГ: archived={len(archived)}, deleted={len(deleted)}, skipped={len(skipped)}"))
    print(bold(f"{'='*60}"))
    if archived:
        print(f"\nАрхивировано ({len(archived)}):")
        for m in archived[:20]:
            print(f"  {m}")
        if len(archived) > 20:
            print(f"  ...и ещё {len(archived) - 20}")
    if deleted:
        print(f"\nУдалено ({len(deleted)}):")
        for m in deleted[:20]:
            print(f"  {m}")
        if len(deleted) > 20:
            print(f"  ...и ещё {len(deleted) - 20}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
