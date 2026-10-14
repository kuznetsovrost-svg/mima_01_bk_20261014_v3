#!/bin/bash
# v3 pipeline: conservative transcription with heavy overlap + LLM stitch + minimal postprocess
set -e

SKILL_DIR="/root/.hermes/skills/mlops/audio-transcription"
POST_DIR="/root/.hermes/skills/mlops/audio-postprocess"
WORK_DIR="/tmp/ba_modeling_audio"
INPUT_WAV="$WORK_DIR/Лекции 1_1.wav"

if [ ! -f "$INPUT_WAV" ]; then
    echo "ERROR: $INPUT_WAV not found"
    exit 1
fi

echo "=== STEP 1: Transcribe with 1-min chunks, 30-sec overlap ==="
bash /root/.hermes/scripts/transcribe_v3.sh "$INPUT_WAV" "$WORK_DIR"

echo ""
echo "=== STEP 2: LLM stitch (conservative) ==="
python3 "$POST_DIR/scripts/stitch_v3.py" \
    "$WORK_DIR/chunks_v3_out" \
    "$WORK_DIR/final/ba_modeling_stitched.md" \
    --overlap-sec 30 \
    --context-sec 20

echo ""
echo "=== STEP 3: Punctuation + ASR fix (2 minimal passes) ==="
python3 "$POST_DIR/scripts/punctuate_v3.py" \
    "$WORK_DIR/final/ba_modeling_stitched.md" \
    "$WORK_DIR/final/ba_modeling_v3" \
    --passes 1,2

echo ""
echo "=== STEP 4: Cleanup ==="
python3 "$SKILL_DIR/scripts/cleanup.py" \
    "$WORK_DIR/final/ba_modeling_v3_final.md" \
    "$WORK_DIR/final/ba_modeling_v3.md"

echo ""
echo "=== Pipeline complete ==="
ls -la "$WORK_DIR/final/"
echo ""
echo "Final file size:"
wc -w "$WORK_DIR/final/ba_modeling_v3.md"