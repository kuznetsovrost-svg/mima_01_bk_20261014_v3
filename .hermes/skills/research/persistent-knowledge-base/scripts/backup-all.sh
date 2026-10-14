#!/bin/bash
# backup-all.sh — Daily backup of all wiki vaults via git push
# Cron: 0 3 * * * /root/wiki-system/tools/backup-all.sh
#
# Each vault under VAULTS_DIR is its own git repo with its own remote.
# This script walks them all, commits any dirty state, and pushes.

set -e

VAULTS_DIR="${VAULTS_DIR:-/root/wiki-system/vaults}"
LOG="${BACKUP_LOG:-/var/log/wiki-backup.log}"
COMMIT_MESSAGE="${COMMIT_MESSAGE:-auto-backup}"

mkdir -p "$(dirname "$LOG")"

echo "[$(date -Iseconds)] backup: started, scanning $VAULTS_DIR" >> "$LOG"

pushed=0
skipped=0
failed=0

for vault_dir in "$VAULTS_DIR"/*/; do
    vault_name=$(basename "$vault_dir")

    # Skip non-git directories and the _archive folder
    if [ ! -d "$vault_dir/.git" ]; then
        echo "[$(date -Iseconds)] backup: $vault_name — no .git, skipping" >> "$LOG"
        skipped=$((skipped + 1))
        continue
    fi

    cd "$vault_dir"

    # Commit any pending changes
    if [[ -n $(git status --porcelain) ]]; then
        git add . >> "$LOG" 2>&1 || true
        if ! git commit -m "$COMMIT_MESSAGE: $(date -Iseconds)" >> "$LOG" 2>&1; then
            echo "[$(date -Iseconds)] backup: $vault_name — commit failed, skipping push" >> "$LOG"
            failed=$((failed + 1))
            continue
        fi
    fi

    # Push to remote
    if git push origin main >> "$LOG" 2>&1; then
        pushed=$((pushed + 1))
        echo "[$(date -Iseconds)] backup: $vault_name — pushed" >> "$LOG"
    else
        failed=$((failed + 1))
        echo "[$(date -Iseconds)] backup: $vault_name — push FAILED (no remote? check origin)" >> "$LOG"
    fi
done

echo "[$(date -Iseconds)] backup: done — pushed=$pushed skipped=$skipped failed=$failed" >> "$LOG"

# If everything failed, exit non-zero so cron / monitoring catches it
if [ "$failed" -gt 0 ] && [ "$pushed" -eq 0 ]; then
    exit 1
fi
exit 0