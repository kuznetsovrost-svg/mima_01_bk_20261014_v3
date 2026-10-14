#!/usr/bin/env bash
# build_word_from_snapshot.sh
# v1.0.19: Сборка DOCX-отчёта по снимку MD из MCP.
#
# Цепочка:
#   1) fetch_snapshot.py --code <CODE> --last       → MD-файл в кэш
#   2) build_word_report.py --md <MD_PATH> --code <CODE> → DOCX
#
# Использование:
#   ./build_word_from_snapshot.sh 504-595
#   ./build_word_from_snapshot.sh 504-595 503-152 503-434
#
# Артефакты:
#   MD:   ~/.hermes/profiles/fst-control/cache/snapshots/<CODE>_*.md
#   DOCX: /tmp/<CODE>_report_<timestamp>_WORD-форма1.docx

set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Использование: $0 <project_code> [<project_code> ...]"
    exit 2
fi

SKILL_WORD_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SKILL_FETCH_DIR="${HOME}/.hermes/profiles/fst-control/skills/productivity/fst-project-health-from-md-snapshot"
CACHE_DIR="${HOME}/.hermes/profiles/fst-control/cache/snapshots"

for code in "$@"; do
    echo ""
    echo "=== ${code} ==="
    md_path=$(python3 "${SKILL_FETCH_DIR}/scripts/fetch_snapshot.py" --code "${code}" --last --no-log 2>&1 >/dev/null; ls -1t "${CACHE_DIR}/${code}_"*.md 2>/dev/null | head -1)

    if [[ -z "${md_path}" || ! -f "${md_path}" ]]; then
        echo "✗ ${code}: не удалось скачать MD из MCP"
        continue
    fi

    echo "📥 MD: ${md_path}"

    docx_path="/tmp/${code}_report_$(date +%Y-%m-%d_%H%M%S)_WORD-форма1.docx"
    if python3 "${SKILL_WORD_DIR}/scripts/build_word_report.py" --md "${md_path}" --code "${code}" --output "${docx_path}" 2>&1 | tail -5; then
        echo "✅ DOCX: ${docx_path}"
    else
        echo "✗ ${code}: ошибка сборки DOCX"
    fi
done
