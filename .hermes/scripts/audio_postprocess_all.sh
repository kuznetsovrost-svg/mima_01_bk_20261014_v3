#!/bin/bash
# Loop through all chunks: postprocess + JEV quality gate

set -e

WORK_DIR="/tmp/hermes_audio_transcription"
CHUNKS_DIR="$WORK_DIR/chunks_out"
POST_DIR="$WORK_DIR/postprocessed"
EVAL_DIR="$WORK_DIR/quality_eval"

mkdir -p "$POST_DIR" "$EVAL_DIR"

TOTAL=$(ls "$CHUNKS_DIR" | wc -l)
COMPLETED=0
FAILED=0
SKIPPED=0
PIPELINE_START=$(date +%s)

echo "=== Postprocess + JEV pipeline for $TOTAL chunks ==="
echo ""

for chunk_dir in "$CHUNKS_DIR"/chunk_*; do
    base=$(basename "$chunk_dir")
    chunk_t=$(date +%s)

    # Check if already done (post + eval both exist)
    if [ -f "$POST_DIR/${base}_postprocess.md" ] && [ -f "$EVAL_DIR/${base}_quality.json" ]; then
        echo "[$base] SKIP: already processed"
        SKIPPED=$((SKIPPED + 1))
        continue
    fi

    # Run combined postprocess + JEV
    python3 /root/.hermes/scripts/audio_postprocess_chunk.py "$chunk_dir" "$POST_DIR" "$EVAL_DIR"
    exit_code=$?
    chunk_end=$(date +%s)
    chunk_dur=$((chunk_end - chunk_t))

    if [ $exit_code -ne 0 ]; then
        echo "[$base] FAIL after ${chunk_dur}s"
        FAILED=$((FAILED + 1))
    else
        echo "[$base] OK: ${chunk_dur}s"
        COMPLETED=$((COMPLETED + 1))
    fi

    sleep 3
done

PIPELINE_END=$(date +%s)
TOTAL_TIME=$((PIPELINE_END - PIPELINE_START))

# Final summary
cat > "$WORK_DIR/final/postprocess_report.md" << EOF
# Postprocess Report

## Summary
- Started: $(date -d @$PIPELINE_START "+%Y-%m-%d %H:%M:%S")
- Finished: $(date -d @$PIPELINE_END "+%Y-%m-%d %H:%M:%S")
- Total time: ${TOTAL_TIME}s ($((TOTAL_TIME / 60)) min)
- Chunks completed: $COMPLETED
- Chunks failed: $FAILED
- Chunks skipped: $SKIPPED

## Output Files
- Postprocessed: $POST_DIR/
- Quality evals: $EVAL_DIR/
EOF

echo ""
echo "=== Pipeline complete ==="
echo "Time: ${TOTAL_TIME}s ($((TOTAL_TIME / 60)) min)"
echo "Completed: $COMPLETED, Failed: $FAILED, Skipped: $SKIPPED"