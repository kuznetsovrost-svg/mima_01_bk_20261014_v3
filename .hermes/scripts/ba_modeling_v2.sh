#!/bin/bash
# Full pipeline: overlap transcribe + dedup + multi-pass postprocess + cleanup
set -e

SKILL_DIR="/root/.hermes/skills/mlops/audio-transcription"
WORK_DIR="/tmp/ba_modeling_audio"
INPUT_WAV="$WORK_DIR/Лекции 1_1.wav"

if [ ! -f "$INPUT_WAV" ]; then
    echo "ERROR: $INPUT_WAV not found"
    exit 1
fi

echo "=== STEP 1: Transcribe with overlap ==="
bash /root/.hermes/scripts/transcribe_overlap.sh "$INPUT_WAV" "$WORK_DIR"

echo ""
echo "=== STEP 2: Dedup overlap zones ==="
python3 "$SKILL_DIR/scripts/dedup_overlap.py" \
    "$WORK_DIR/chunks_overlap_out" \
    "$WORK_DIR/final/ba_modeling_dedup.md" \
    --overlap-sec 15

echo ""
echo "=== STEP 3: Multi-pass LLM postprocess ==="
python3 "$SKILL_DIR/scripts/postprocess_multi.py" \
    "$WORK_DIR/final/ba_modeling_dedup.md" \
    "$WORK_DIR/final/ba_modeling" \
    --passes 1,2,3,4

echo ""
echo "=== STEP 4: Final cleanup ==="
python3 "$SKILL_DIR/scripts/cleanup.py" \
    "$WORK_DIR/final/ba_modeling_final.md" \
    "$WORK_DIR/final/ba_modeling_v2.md"

echo ""
echo "=== Pipeline complete ==="
ls -la "$WORK_DIR/final/"
echo ""
echo "Final file size:"
wc -w "$WORK_DIR/final/ba_modeling_v2.md"