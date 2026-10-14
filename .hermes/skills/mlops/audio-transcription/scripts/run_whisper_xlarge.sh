#!/bin/bash
# Whisper Transcription Runner for large-v3 in cgroup-restricted environments.
#
# This script:
#  1. Creates a custom cgroup with 10 GB memory limit
#  2. Moves itself into that cgroup
#  3. Runs Whisper large-v3 with the inherited (larger) limit
#
# Usage:
#   bash run_whisper_xlarge.sh INPUT.{wav,mp3,mp4} OUTPUT_DIR
#
# Requires: CAP_SYS_ADMIN (root) and cgroup v2 at /sys/fs/cgroup/

set -e

if [ "$#" -lt 2 ]; then
    echo "Usage: $0 INPUT.{wav,mp3,mp4} OUTPUT_DIR [EXTRA_ARGS...]"
    echo ""
    echo "Example:"
    echo "  $0 lecture.mp4 ./out --model large-v3 --beam-size 5 \\"
    echo "     --prompt templates/initial_prompts/ba_modeling.txt \\"
    echo "     --hotwords 'Ом снежинка Коха AS-IS TO-BE'"
    exit 1
fi

INPUT="$1"
OUTDIR="$2"
shift 2
EXTRA_ARGS="$@"

# ----- Custom cgroup with 10 GB memory limit -----
CGROUP="/sys/fs/cgroup/hermes_whisper_xlarge"
LIMIT_BYTES=10737418240   # 10 GB

if [ ! -d "$CGROUP" ]; then
    mkdir -p "$CGROUP" || {
        echo "ERROR: cannot create $CGROUP. Need CAP_SYS_ADMIN and cgroup v2." >&2
        exit 1
    }
fi
echo "$LIMIT_BYTES" > "$CGROUP/memory.max"
echo $$ > "$CGROUP/cgroup.procs"

echo "=== cgroup $CGROUP ==="
echo "Memory limit: $((LIMIT_BYTES / 1024 / 1024 / 1024)) GB"
echo "PID in cgroup: $$"
echo

START=$(date +%s)

python3 /root/.hermes/skills/mlops/audio-transcription/scripts/transcribe_single.py \
    "$INPUT" \
    --output "$OUTDIR" \
    --max-memory-gb 9.5 \
    $EXTRA_ARGS 2>&1 | tail -15

ELAPSED=$(($(date +%s) - START))
echo "=== Total time: $ELAPSED sec ($((ELAPSED / 60)) min) ==="