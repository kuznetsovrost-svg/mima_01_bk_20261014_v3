#!/bin/bash
# Wrapper for cronjob - запускает run_full.sh и пишет результат
set -e

WORK_DIR="/tmp/hermes_audio_transcription"
LOG_FILE="$WORK_DIR/cronjob_output.log"

echo "=== Cronjob fired at $(date -Iseconds) ===" >> "$LOG_FILE"

# Запускаем основной скрипт
bash "$WORK_DIR/run_full.sh" >> "$LOG_FILE" 2>&1
EXIT=$?

echo "=== Cronjob finished at $(date -Iseconds), exit=$EXIT ===" >> "$LOG_FILE"

# Если есть результаты - склеиваем
if [ -d "$WORK_DIR/chunks_out" ]; then
    completed=$(ls "$WORK_DIR/chunks_out" | wc -l)
    echo "Completed chunks: $completed / 37" >> "$LOG_FILE"
fi

exit $EXIT