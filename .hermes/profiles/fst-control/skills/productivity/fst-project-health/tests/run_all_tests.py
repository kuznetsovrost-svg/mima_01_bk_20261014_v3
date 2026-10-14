"""
run_all_tests.py — оркестратор тестов скилла fst-project-health.

Запуск:
    python3 tests/run_all_tests.py
    python3 tests/run_all_tests.py --report   # отчёт в файл
    python3 tests/run_all_tests.py --fast      # без subprocess-based тестов

Тесты:
    1. test_no_hardcode — нет хардкода project_code/project_id
    2. test_imports — все модули импортируются
    3. test_helpers — mcp_config helpers
    4. test_run_all — CLI run_all.py
    5. test_pipeline_integration — subprocess-based
    6. test_skill_md_integrity — SKILL.md

После обновления скилла запускай:
    python3 tests/run_all_tests.py --report
"""
import sys
import subprocess
import time
import json
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = TESTS_DIR.parent
REPORT_PATH = SKILL_DIR / "tests" / "test_report.json"


def run_test_file(test_file: Path, fast: bool = False) -> dict:
    """Запускает один test файл и возвращает результат."""
    start = time.time()
    args = ["python3", str(test_file)]
    if fast and test_file.name == "test_pipeline_integration.py":
        # Пропускаем subprocess-based в fast-режиме
        return {
            "name": test_file.name,
            "status": "SKIPPED",
            "duration_sec": 0.0,
            "details": "subprocess-based (skip in fast mode)",
        }
    result = subprocess.run(
        args, capture_output=True, text=True,
        cwd=str(TESTS_DIR),
        timeout=60,
    )
    duration = time.time() - start
    return {
        "name": test_file.name,
        "status": "PASS" if result.returncode == 0 else "FAIL",
        "duration_sec": round(duration, 3),
        "returncode": result.returncode,
        "stdout_tail": result.stdout[-500:] if result.stdout else "",
        "stderr_tail": result.stderr[-500:] if result.stderr else "",
    }


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Запуск всех тестов скилла fst-project-health")
    ap.add_argument("--report", action="store_true", help="Сохранить отчёт в JSON")
    ap.add_argument("--fast", action="store_true", help="Пропустить subprocess-based тесты")
    args = ap.parse_args()

    test_files = sorted(TESTS_DIR.glob("test_*.py"))
    print(f"🧪 Запуск {len(test_files)} тестов:")
    print()

    total_start = time.time()
    results = []
    pass_count = 0
    fail_count = 0
    skipped_count = 0

    for test_file in test_files:
        print(f"  → {test_file.name}...", end=" ", flush=True)
        result = run_test_file(test_file, fast=args.fast)
        results.append(result)

        status = result["status"]
        if status == "PASS":
            pass_count += 1
            print(f"✅ PASS ({result['duration_sec']}s)")
        elif status == "SKIPPED":
            skipped_count += 1
            print(f"⏭️  SKIPPED")
        else:
            fail_count += 1
            print(f"❌ FAIL ({result['duration_sec']}s)")
            if result.get("stderr_tail"):
                print(f"     STDERR: {result['stderr_tail'][-200:]}")

    total_duration = round(time.time() - total_start, 3)

    print()
    print(f"{'='*60}")
    print(f"📊 ИТОГО:")
    print(f"   ✅ PASS:    {pass_count}/{len(test_files)}")
    print(f"   ❌ FAIL:    {fail_count}/{len(test_files)}")
    print(f"   ⏭️  SKIPPED: {skipped_count}/{len(test_files)}")
    print(f"   ⏱️  Время:   {total_duration}s")

    if args.report:
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "skill": "fst-project-health",
            "version": "0.9.0",
            "total_tests": len(test_files),
            "pass_count": pass_count,
            "fail_count": fail_count,
            "skipped_count": skipped_count,
            "total_duration_sec": total_duration,
            "tests": results,
        }
        REPORT_PATH.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"   📝 Отчёт: {REPORT_PATH}")

    print(f"{'='*60}")

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
