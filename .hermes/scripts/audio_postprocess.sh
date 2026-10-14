#!/bin/bash
# Postprocess all chunks via transcription-postprocess + JEV quality gate

set -e

SKILL_DIR="/root/.hermes/skills/note-taking/transcription-postprocess"
JEV_DIR="/root/.hermes/skills/jev-decisions"
WORK_DIR="/tmp/hermes_audio_transcription"
CHUNKS_DIR="$WORK_DIR/chunks_out"
POST_DIR="$WORK_DIR/postprocessed"
EVAL_DIR="$WORK_DIR/quality_eval"

mkdir -p "$POST_DIR" "$EVAL_DIR"

TOTAL=$(ls "$CHUNKS_DIR" | wc -l)
COMPLETED=0
SKIPPED=0
FAILED=0
PIPELINE_START=$(date +%s)

echo "=== Postprocessing $TOTAL chunks ==="

for chunk_dir in "$CHUNKS_DIR"/chunk_*; do
    base=$(basename "$chunk_dir")
    words_file="$chunk_dir/${base}_words.json"
    plain_file="$chunk_dir/${base}_plain.md"
    
    post_file="$POST_DIR/${base}_postprocess.md"
    eval_file="$EVAL_DIR/${base}_quality.json"
    
    # Skip if already done
    if [ -f "$post_file" ] && [ -s "$post_file" ]; then
        echo "[$base] SKIP: already postprocessed"
        SKIPPED=$((SKIPPED + 1))
        continue
    fi
    
    if [ ! -f "$words_file" ]; then
        echo "[$base] SKIP: no words.json"
        continue
    fi
    
    chunk_t=$(date +%s)
    echo "[$base] Postprocessing..."
    
    # Step 1: Run transcription-postprocess on this chunk
    python3 "$SKILL_DIR/scripts/postprocess.py" "$words_file" \
        --output "$POST_DIR" \
        > "$POST_DIR/${base}.log" 2>&1
    
    post_exit=$?
    
    if [ $post_exit -ne 0 ]; then
        echo "[$base] POSTPROCESS FAIL: exit=$post_exit"
        FAILED=$((FAILED + 1))
        continue
    fi
    
    # Step 2: JEV quality gate
    if [ -f "$post_file" ] && [ -s "$POST_FILE" ]; then
        # Build JEV request
        post_text=$(cat "$post_file")
        # Truncate to ~500 chars for JEV
        preview=$(echo "$post_text" | head -c 500)
        
        # Call JEV score
        python3 << EOF > "$eval_file" 2>&1
from jev_client import jev_score
import json

text_preview = """$preview"""

result = jev_score(
    text=text_preview,
    criteria="Readability of postprocessed Russian lecture transcript (punctuation, paragraphs, names capitalization). 1=unreadable, 5=excellent.",
    min_val=1,
    max_val=5,
)
print(json.dumps({
    "chunk": "$base",
    "score": result.get("value"),
    "confidence": result.get("confidence"),
    "raw": result,
}, ensure_ascii=False, indent=2))
EOF
        
        if [ -f "$eval_file" ] && [ -s "$eval_file" ]; then
            score=$(python3 -c "import json; print(json.load(open('$eval_file')).get('score', 'N/A'))")
            echo "[$base] OK: postprocess + JEV score=$score"
        else
            echo "[$base] OK: postprocess (JEV eval failed)"
        fi
    else
        echo "[$base] WARN: no postprocess output"
    fi
    
    COMPLETED=$((COMPLETED + 1))
    sleep 2
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
echo "=== Postprocess pipeline complete ==="
echo "Total: ${TOTAL_TIME}s ($((TOTAL_TIME / 60)) min)"
echo "Completed: $COMPLETED, Failed: $FAILED, Skipped: $SKIPPED"