#!/bin/bash
# Transcribe with 1-min chunks and 30-sec overlap for high-fidelity reconstruction
# Usage: transcribe_v3.sh INPUT_WAV OUTPUT_DIR

set -e

INPUT_WAV="$1"
WORK_DIR="$2"

if [ -z "$INPUT_WAV" ] || [ -z "$WORK_DIR" ]; then
    echo "Usage: $0 INPUT_WAV WORK_DIR"
    exit 1
fi

SKILL_DIR="/root/.hermes/skills/mlops/audio-transcription"
PROMPT="$SKILL_DIR/templates/initial_prompts/ba_modeling.txt"
HOTWORDS="BPMN IDEF0 ARIS ArchiMate UML ER нотация моделирование AS-IS TO-BE Use Case User Story требования stakeholder заинтересованная"

CHUNKS_DIR="$WORK_DIR/chunks_v3"
OUT_DIR="$WORK_DIR/chunks_v3_out"
LOG_DIR="$WORK_DIR/logs_v3"

mkdir -p "$CHUNKS_DIR" "$OUT_DIR" "$LOG_DIR"

# Parameters
CHUNK_LEN=60       # 1 minute
OVERLAP=30         # 30 sec overlap (50%)
STEP=$((CHUNK_LEN - OVERLAP))  # 30 sec step

TOTAL_DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$INPUT_WAV")
echo "Duration: ${TOTAL_DUR}s, Chunk: ${CHUNK_LEN}s, Overlap: ${OVERLAP}s, Step: ${STEP}s"

# Calculate chunk count
TOTAL_CHUNKS=$(python3 -c "
import math
dur=$TOTAL_DUR
step=$STEP
n = 0
pos = 0
while pos < dur:
    n += 1
    pos += step
print(n)
")
echo "Total chunks: $TOTAL_CHUNKS"

rm -f "$CHUNKS_DIR"/chunk_*.wav

i=0
pos=0
while [ $(python3 -c "print(int($pos < $TOTAL_DUR))") -eq 1 ]; do
    CHUNK_NUM=$(printf "%03d" $i)
    ffmpeg -y -loglevel error -i "$INPUT_WAV" -ss $pos -t $CHUNK_LEN -ar 16000 -ac 1 "$CHUNKS_DIR/chunk_${CHUNK_NUM}.wav"
    i=$((i + 1))
    pos=$((pos + STEP))
done

ACTUAL_CHUNKS=$(ls $CHUNKS_DIR/chunk_*.wav | wc -l)
echo "Created $ACTUAL_CHUNKS chunks"

# Transcribe each
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
echo "=== v3 transcription complete ==="
echo "Time: ${TOTAL}s ($((TOTAL / 60)) min)"
echo "Completed: $COMPLETED / $ACTUAL_CHUNKS, Failed: $FAILED"