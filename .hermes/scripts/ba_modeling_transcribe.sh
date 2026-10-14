#!/bin/bash
# Transcribe BA modeling lecture with medium + ba_modeling prompt

set -e

SKILL_DIR="/root/.hermes/skills/mlops/audio-transcription"
PROMPT="$SKILL_DIR/templates/initial_prompts/ba_modeling.txt"
HOTWORDS="BPMN IDEF0 ARIS ArchiMate UML ER нотация моделирование AS-IS TO-BE Use Case User Story требования stakeholder заинтересованная"

WORK_DIR="/tmp/ba_modeling_audio"
INPUT_WAV="$WORK_DIR/Лекции 1_1.wav"
CHUNKS_DIR="$WORK_DIR/chunks_2min"
OUT_DIR="$WORK_DIR/chunks_out"
LOG_DIR="$WORK_DIR/logs"

# Create output directories
mkdir -p "$CHUNKS_DIR" "$OUT_DIR" "$LOG_DIR"

# Step 1: Split into 2-min chunks
echo "=== Splitting audio into 2-min chunks ==="
TOTAL_DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$INPUT_WAV")
TOTAL_CHUNKS=$(python3 -c "import math; print(math.ceil($TOTAL_DUR / 120))")
echo "Duration: ${TOTAL_DUR}s, Chunks: $TOTAL_CHUNKS"

# Clean previous chunks
rm -f "$CHUNKS_DIR"/chunk_*.wav

for i in $(seq 0 $((TOTAL_CHUNKS - 1))); do
    CHUNK_NUM=$(printf "%03d" $i)
    START=$((i * 120))
    ffmpeg -y -loglevel error -i "$INPUT_WAV" -ss $START -t 120 -ar 16000 -ac 1 "$CHUNKS_DIR/chunk_${CHUNK_NUM}.wav"
done

echo "Created $(ls $CHUNKS_DIR/chunk_*.wav | wc -l) chunks"

# Step 2: Transcribe each chunk
echo ""
echo "=== Transcribing $TOTAL_CHUNKS chunks ==="
PIPELINE_START=$(date +%s)
COMPLETED=0
FAILED=0

for chunk in "$CHUNKS_DIR"/chunk_*.wav; do
    base=$(basename "$chunk" .wav)
    out_subdir="$OUT_DIR/$base"
    log_file="$LOG_DIR/${base}.log"
    chunk_t=$(date +%s)

    if [ -f "$out_subdir/${base}_plain.md" ] && [ -s "$out_subdir/${base}_plain.md" ]; then
        echo "[$base] SKIP"
        COMPLETED=$((COMPLETED + 1))
        continue
    fi

    echo "[$base] Transcribing..."

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

    if [ $exit_code -ne 0 ]; then
        echo "[$base] FAIL: exit=$exit_code, dur=${chunk_dur}s"
        FAILED=$((FAILED + 1))
    else
        file_size=$(stat -c %s "$out_subdir/${base}_plain.md" 2>/dev/null || echo 0)
        echo "[$base] OK: ${chunk_dur}s, output=${file_size} bytes"
        COMPLETED=$((COMPLETED + 1))
    fi

    sleep 3
done

PIPELINE_END=$(date +%s)
TOTAL=$((PIPELINE_END - PIPELINE_START))

echo ""
echo "=== Transcription complete ==="
echo "Time: ${TOTAL}s ($((TOTAL / 60)) min)"
echo "Completed: $COMPLETED / $TOTAL_CHUNKS, Failed: $FAILED"