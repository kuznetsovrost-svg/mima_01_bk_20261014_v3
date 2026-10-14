#!/usr/bin/env python3
"""
run_all_tests.py — главный раннер тестов семейства fst-project-health-*.

Использование:
    python3 run_all_tests.py                          # все группы
    python3 run_all_tests.py --group regression      # одна группа
    python3 run_all_tests.py --group mcp             # только MCP
    python3 run_all_tests.py --group snap_md         # только генератор
    python3 run_all_tests.py --no-mcp                # всё, кроме MCP
    python3 run_all_tests.py --list                  # показать список тестов без запуска
    python3 run_all_tests.py --quiet                 # минимум вывода

Группы (в порядке запуска):
    1. regression    — Уровень 1 (existing skill)
    2. mcp           — Уровень 4 (MCP write/read, требует TEST_PROJECT_CODE)
    3. snap_md       — Уровень 2 (генератор + логирование)
    4. from_md       — Уровень 3 (извлекатель + логирование)
    5. cross_skill   — Уровень 5 (интеграция)
    6. invariants    — Уровень 6 (4 инварианта устойчивости)

Коды возврата:
    0 — все тесты прошли (или были skipped)
    1 — хотя бы один тест упал
    2 — все MCP-тесты пропущены (это не ошибка, но сигнализирует)

Логи:
    Всё пишется в logs/tests.log с timestamp.
"""

import argparse
import importlib
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "tests"))
from _helpers import (
    green, yellow, red, bold, cyan,
    ok, fail, skip_msg, info, fmt_ms,
    log_to_file, log_section,
    TESTS_LOG,
)

SKILL_VERSION = "1.0.19"
TESTS_DIR = Path(__file__).resolve().parent / "tests"

# Группы тестов: имя -> (модуль, описание)
GROUPS = [
    ("regression",  "test_01_regression", "Уровень 1: regression существующих"),
    ("mcp",         "test_02_mcp",        "Уровень 4: MCP write/read (нужен TEST_PROJECT_CODE)"),
    ("snap_md",     "test_03_snap_md",    "Уровень 2: генератор + логирование"),
    ("from_md",     "test_04_from_md",    "Уровень 3: извлекатель + логирование"),
    ("cross_skill", "test_05_cross_skill","Уровень 5: cross-skill интеграция"),
    ("invariants",  "test_06_invariants", "Уровень 6: 4 инварианта устойчивости"),
]


def list_tests():
    print(bold(f"\n📋 Доступные тесты (v{SKILL_VERSION})\n"))
    for name, module, desc in GROUPS:
        print(f"  {cyan(name):<14}  {desc}")
    print(f"\nВсего групп: {len(GROUPS)}")
    print(f"Каталог тестов: {TESTS_DIR}")


def run_group(group_name: str, module_name: str, desc: str, *, quiet: bool) -> dict:
    """Запускает одну группу тестов. Возвращает {'passed': N, 'failed': N, 'skipped': N, 'duration_ms': N}."""
    print(f"\n{bold(f'▶ {desc}')}")
    log_section(f"GROUP {group_name.upper()} @ {datetime.now().isoformat()}")

    try:
        module = importlib.import_module(module_name)
    except ImportError as e:
        print(fail(f"  Не удалось импортировать {module_name}: {e}"))
        log_to_file(f"  IMPORT FAILED: {e}")
        return {"passed": 0, "failed": 1, "skipped": 0, "duration_ms": 0}

    tests = getattr(module, "TESTS", [])
    if not tests:
        print(yellow(f"  Нет тестов в {module_name}"))
        return {"passed": 0, "failed": 0, "skipped": 0, "duration_ms": 0}

    print(f"  Тестов в группе: {len(tests)}")

    passed = failed = skipped = 0
    group_t0 = time.perf_counter()

    for test in tests:
        # test — это dict с полями: name, fn, params (опц.)
        name = test.get("name", "<unnamed>")
        fn = test["fn"]
        params = test.get("params", {})

        t0 = time.perf_counter()
        try:
            result = fn(**params) if params else fn()
            duration = (time.perf_counter() - t0) * 1000

            if result is None:
                # По умолчанию = passed
                result = {"status": "passed"}

            status = result.get("status", "passed")
            if status == "passed":
                passed += 1
                if not quiet:
                    print(f"  {ok(name)} ({fmt_ms(duration)})")
                    if "details" in result:
                        print(f"      {cyan(result['details'])}")
                log_to_file(f"  PASS  {name} ({fmt_ms(duration)})")
            elif status == "skipped":
                skipped += 1
                reason = result.get("reason", "—")
                print(f"  {skip_msg(name)} — {reason}")
                log_to_file(f"  SKIP  {name} — {reason}")
            else:  # failed
                failed += 1
                reason = result.get("reason", result.get("error", "<no reason>"))
                print(f"  {fail(name)} ({fmt_ms(duration)}) — {reason}")
                log_to_file(f"  FAIL  {name} ({fmt_ms(duration)}) — {reason}")
        except Exception as e:
            duration = (time.perf_counter() - t0) * 1000
            failed += 1
            print(f"  {fail(name)} ({fmt_ms(duration)}) — {type(e).__name__}: {e}")
            log_to_file(f"  FAIL  {name} ({fmt_ms(duration)}) — {type(e).__name__}: {e}")

    group_duration = (time.perf_counter() - group_t0) * 1000

    # Итог по группе.
    summary_parts = []
    if passed: summary_parts.append(green(f"passed={passed}"))
    if failed: summary_parts.append(red(f"failed={failed}"))
    if skipped: summary_parts.append(yellow(f"skipped={skipped}"))
    print(f"  {' '.join(summary_parts)}, {fmt_ms(group_duration)}")

    return {
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "duration_ms": group_duration,
    }


def main():
    ap = argparse.ArgumentParser(
        description="Раннер тестов семейства fst-project-health-*.",
        epilog=(
            "СОВЕТ: запускайте по группам отдельно (--group mcp, --group regression, ...).\n"
            "Полный прогон ВСЕХ групп занимает 5–10 минут (зависит от MCP) и\n"
            "может приводить к таймаутам на больших карточках.\n"
            "Типичный cron:\n"
            "  0 3 * * 0 cd /root/.hermes/profiles/fst-control/skills/productivity/fst-project-health-tests && python3 run_all_tests.py --group regression\n"
            "  0 4 * * 0 cd /root/.hermes/profiles/fst-control/skills/productivity/fst-project-health-tests && python3 run_all_tests.py --group snap_md\n"
            "  0 5 * * 0 cd /root/.hermes/profiles/fst-control/skills/productivity/fst-project-health-tests && python3 run_all_tests.py --group from_md\n"
            "  0 6 * * 0 cd /root/.hermes/profiles/fst-control/skills/productivity/fst-project-health-tests && python3 run_all_tests.py --group mcp"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--group", choices=[g[0] for g in GROUPS], default=None,
                    help="Запустить только одну группу (по умолчанию — все).")
    ap.add_argument("--no-mcp", action="store_true",
                    help="Не запускать группу 'mcp' (по умолчанию — запускать).")
    ap.add_argument("--list", action="store_true",
                    help="Показать список групп и выйти.")
    ap.add_argument("--quiet", action="store_true",
                    help="Минимум вывода (только fail и итоги).")
    args = ap.parse_args()

    if args.list:
        list_tests()
        return 0

    # Header.
    overall_t0 = time.perf_counter()
    start_ts = datetime.now().isoformat()
    print(bold(f"\n🧪 fst-project-health-tests v{SKILL_VERSION}"))
    print(f"   Started: {start_ts}")

    TESTS_LOG.parent.mkdir(parents=True, exist_ok=True)
    log_to_file("")
    log_to_file(f"=== TESTS RUN @ {start_ts} (v{SKILL_VERSION}) ===")

    # Выбор групп.
    if args.group:
        groups_to_run = [g for g in GROUPS if g[0] == args.group]
    elif args.no_mcp:
        groups_to_run = [g for g in GROUPS if g[0] != "mcp"]
    else:
        groups_to_run = GROUPS

    # Запуск.
    total = {"passed": 0, "failed": 0, "skipped": 0, "duration_ms": 0}
    all_groups_skipped_mcp = True

    for name, module, desc in groups_to_run:
        result = run_group(name, module, desc, quiet=args.quiet)
        for k in ("passed", "failed", "skipped", "duration_ms"):
            total[k] += result[k]
        if name != "mcp" and result["passed"] + result["failed"] > 0:
            all_groups_skipped_mcp = False

    # Итог.
    overall_duration = (time.perf_counter() - overall_t0) * 1000
    end_ts = datetime.now().isoformat()

    print(bold(f"\n{'='*60}"))
    parts = []
    if total['passed']: parts.append(green(f"PASSED: {total['passed']}"))
    if total['failed']: parts.append(red(f"FAILED: {total['failed']}"))
    if total['skipped']: parts.append(yellow(f"SKIPPED: {total['skipped']}"))
    print(bold(f"ИТОГ: {' '.join(parts)}, {fmt_ms(overall_duration)}"))
    print(bold(f"{'='*60}"))
    print(f"   Started:  {start_ts}")
    print(f"   Finished: {end_ts}")
    print(f"   Лог:      {TESTS_LOG}")

    log_to_file("")
    log_to_file(f"=== TOTAL: passed={total['passed']} failed={total['failed']} skipped={total['skipped']} duration={fmt_ms(overall_duration)} ===")

    # Коды возврата.
    if total["failed"] > 0:
        return 1
    if all_groups_skipped_mcp and "mcp" in [g[0] for g in groups_to_run]:
        return 2  # все MCP-тесты пропущены
    return 0


if __name__ == "__main__":
    sys.exit(main())
