#!/usr/bin/env bash
# copy-bundled-to-global.sh
# Conflict-safe idempotent copy of bundled skills into the global user
# location (/root/.hermes/skills/). Designed for the workflow:
#
#   1. Pick skills from /usr/local/lib/hermes-agent/skills/<cat>/<name>/
#   2. Copy them into /root/.hermes/skills/<cat>/<name>/
#   3. Create new profiles with `hermes profile create X --no-skills`
#      — those profiles inherit all of /root/.hermes/skills/ via SKILLS_DIR
#
# Verified properties (verified 2026-08-09 on mima_g_01):
#   - Idempotent: SKIP entries that already exist in global.
#   - Conflict-safe: never overwrites; the skills_tool.py collision
#     detector would refuse a blind overwrite, so we probe first.
#   - Reports COPIED/SKIPPED/ERROR counts at the end.
#   - Categories are created lazily.
#   - No sudo / no root-required, just writable paths.
#
# Usage:
#   bash copy-bundled-to-global.sh                          # interactive: edit SKILLS_TO_COPY below
#   bash copy-bundled-to-global.sh creative/excalidraw github/github-pr-workflow
#                                                          # CLI args override the SKILLS_TO_COPY list
#
# To make a profile empty of bundled skills after this, run:
#   hermes profile create <name> --no-skills
# The new profile will see the global user skills (this script's destination)
# but NOT the bundled skills, because --no-skills writes the
# .no-bundled-skills marker that seed_profile_skills() honours.

set -e

SRC=/usr/local/lib/hermes-agent/skills
DST=/root/.hermes/skills

# --- Edit this list to control what gets copied ---
# Format: "<category>/<skill-name>". Add/remove entries freely.
SKILLS_TO_COPY=(
    # Creative — drawing and visualisation
    "creative/excalidraw"
    "creative/architecture-diagram"
    "creative/ascii-art"
    "creative/sketch"
    "creative/humanizer"
    "creative/design-md"

    # Software development
    "software-development/plan"
    "software-development/test-driven-development"
    "software-development/systematic-debugging"
    "software-development/simplify-code"
    "software-development/spike"
    "software-development/requesting-code-review"
    "software-development/hermes-agent-skill-authoring"
    "software-development/python-debugpy"
    "software-development/node-inspect-debugger"

    # GitHub
    "github/github-pr-workflow"
    "github/github-code-review"
    "github/github-issues"
    "github/github-repo-management"
    "github/github-auth"
    "github/codebase-inspection"

    # Productivity
    "productivity/ocr-and-documents"
    "productivity/nano-pdf"
    "productivity/google-workspace"
    "productivity/powerpoint"

    # Research
    "research/arxiv"
    "research/llm-wiki"
    "research/blogwatcher"
    "research/polymarket"
    "research/research-paper-writing"

    # Media
    "media/youtube-content"
    "media/gif-search"

    # MLOps
    "mlops/huggingface-hub"

    # Note-taking
    "note-taking/obsidian"

    # Email
    "email/himalaya"

    # Social media
    "social-media/xurl"

    # Data science
    "data-science/jupyter-live-kernel"

    # Autonomous-ai-agents (rarely needed but possible)
    "autonomous-ai-agents/hermes-agent"
)

# CLI args override the list above
if [ "$#" -gt 0 ]; then
    SKILLS_TO_COPY=("$@")
fi

# Counters
copied=0
skipped=0
errors=0

copy_one() {
    local rel="$1"
    local cat="${rel%%/*}"
    local name="${rel#*/}"
    local src="$SRC/$cat/$name"
    local dst="$DST/$cat/$name"

    if [ ! -d "$src" ]; then
        echo "  SKIP (not in bundled):  $rel"
        skipped=$((skipped + 1))
        return
    fi

    if [ -e "$dst" ]; then
        echo "  SKIP (already in global): $rel"
        skipped=$((skipped + 1))
        return
    fi

    mkdir -p "$DST/$cat"
    if cp -r "$src" "$DST/$cat/"; then
        echo "  COPIED:                  $rel"
        copied=$((copied + 1))
    else
        echo "  ERROR:                   $rel"
        errors=$((errors + 1))
    fi
}

echo "=== Copying bundled skills to global user location ==="
echo "Source:      $SRC"
echo "Destination: $DST"
echo "Count:       ${#SKILLS_TO_COPY[@]} skill(s) requested"
echo ""

for rel in "${SKILLS_TO_COPY[@]}"; do
    copy_one "$rel"
done

echo ""
echo "===================================="
echo "Copied:   $copied"
echo "Skipped:  $skipped"
echo "Errors:   $errors"
echo "===================================="
echo ""
echo "Next step: hermes profile create <name> --no-skills"
echo "  (the new profile inherits everything in $DST"
echo "   via SKILLS_DIR, but skips bundled skills.)"

if [ "$errors" -gt 0 ]; then
    exit 1
fi