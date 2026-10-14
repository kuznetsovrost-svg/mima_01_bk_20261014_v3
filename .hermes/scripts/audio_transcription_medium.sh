#!/bin/bash
# Sequential transcription of 37 × 2-min chunks with medium model
# Each chunk waits 5 sec after previous to allow memory cleanup

set -e

SKILL_DIR="/root/.hermes/skills/mlops/audio-transcription"
PROMPT="$SKILL_DIR/templates/initial_prompts/hermes_agents.txt"
HOTWORDS="Hermes агент скилл skill профиль profile SOUL cron канбан kanban JEV"
WORK_DIR="/tmp/hermes_audio_transcription"
CHUNKS_DIR="$WORK_DIR/chunks_2min"
OUT_DIR="$WORK_DIR/chunks_out"
LOG_DIR="$WORK_DIR/logs"

mkdir -p "$OUT_DIR" "$LOG_DIR"

TOTAL_CHUNKS=$(ls "$CHUNKS_DIR"/chunk_*.wav | wc -l)
echo "=== Total chunks: $TOTAL_CHUNKS ==="

PIPELINE_START=$(date +%s)
COMPLETED=0
FAILED=0
TIMES=()

for chunk in "$CHUNKS_DIR"/chunk_*.wav; do
    base=$(basename "$chunk" .wav)
    out_subdir="$OUT_DIR/$base"
    log_file="$LOG_DIR/${base}.log"
    chunk_t=$(date +%s)

    # Skip if already transcribed
    if [ -f "$out_subdir/${base}_plain.md" ] && [ -s "$out_subdir/${base}_plain.md" ]; then
        echo "[$base] SKIP: already done"
        COMPLETED=$((COMPLETED + 1))
        continue
    fi

    echo "[$base] Transcribing (medium)..."

    python3 "$SKILL_DIR/scripts/transcribe.py" "$chunk" \
        --output "$out_subdir" \
        --prompt "$PROMPT" \
        --hotwords "$HOTWORDS" \
        --model medium \
        --beam-size 3 \
        --no-speech-threshold 0.7 \
        --compression-ratio-threshold 2.2 \
        --log-prob-threshold -0.7 \
        --no-temperature-fallback \
        > "$log_file" 2>&1

    exit_code=$?
    chunk_end=$(date +%s)
    chunk_dur=$((chunk_end - chunk_t))
    TIMES+=("$chunk_dur")

    if [ $exit_code -ne 0 ]; then
        echo "[$base] FAIL: exit=$exit_code, dur=${chunk_dur}s"
        FAILED=$((FAILED + 1))
    else
        file_size=$(stat -c %s "$out_subdir/${base}_plain.md" 2>/dev/null || echo 0)
        echo "[$base] OK: ${chunk_dur}s, output=$file_size bytes"
        COMPLETED=$((COMPLETED + 1))
    fi

    sleep 5
done

PIPELINE_END=$(date +%s)
TOTAL=$((PIPELINE_END - PIPELINE_START))

# Calculate average time
SUM=0
for t in "${TIMES[@]}"; do SUM=$((SUM + t)); done
COUNT=${#TIMES[@]}
if [ $COUNT -gt 0 ]; then
    AVG=$((SUM / COUNT))
else
    AVG=0
fi

# Write final report
cat > "$WORK_DIR/final/pipeline_report.md" << EOF
# Pipeline Report

## Summary
- Start: $(date -d @$PIPELINE_START "+%Y-%m-%d %H:%M:%S")
- End: $(date -d @$PIPELINE_END "+%Y-%m-%d %H:%M:%S")
- Total time: ${TOTAL}s ($((TOTAL / 60)) min)
- Chunks completed: $COMPLETED / $TOTAL_CHUNKS
- Chunks failed: $FAILED
- Average time per chunk: ${AVG}s

## Per-chunk times
$(printf '%s\n' "${TIMES[@]}" | nl)

## Parameters
- Model: medium (int8)
- Beam size: 3
- Initial prompt: hermes_agents.txt (1339 words)
- Hotwords: "$HOTWORDS" (11 words)
- Audio format: 16kHz mono WAV, 2 min each
EOF

echo ""
echo "=== Pipeline complete ==="
echo "Total: $TOTAL sec ($((TOTAL / 60)) min)"
echo "Completed: $COMPLETED / $TOTAL_CHUNKS"
echo "Failed: $FAILED"
echo "Avg per chunk: ${AVG}s"