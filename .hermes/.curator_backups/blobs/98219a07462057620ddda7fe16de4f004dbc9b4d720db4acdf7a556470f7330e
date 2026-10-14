#!/bin/bash
# transcribe.sh — bash wrapper for audio-transcription skill
#
# Usage:
#   transcribe.sh <input.mp3> --output <dir> [options]
#
# Examples:
#   transcribe.sh lecture.mp3 --output ./out
#   transcribe.sh lecture.mp3 --output ./out --prompt "BPMN, jBPM, бизнес-процесс"
#   transcribe.sh lecture.mp3 --output ./out --hotwords "BPMN шлюз gateway"
#   transcribe.sh lecture.mp3 --output ./out --strict
#   transcribe.sh lecture.mp3 --output ./out --two-pass
#   transcribe.sh --batch /path/to/lectures/ --output ./out

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

# Defaults
INPUT=""
OUTPUT=""
LANGUAGE="ru"
BEAM_SIZE=5
MODEL="large-v3"
COMPUTE_TYPE="int8"
PROMPT=""
HOTWORDS=""
BATCH=false
SKIP_JEV=false
ONLY_STAGE=""
VAD_FILTER=true
TEMPERATURE_FALLBACK=true
STRICT=false
TWO_PASS=false
COMPRESSION_RATIO_THRESHOLD=2.4
LOGPROB_THRESHOLD=-1.0
NO_SPEECH_THRESHOLD=0.6

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --output) OUTPUT="$2"; shift 2 ;;
        --language) LANGUAGE="$2"; shift 2 ;;
        --beam-size) BEAM_SIZE="$2"; shift 2 ;;
        --model) MODEL="$2"; shift 2 ;;
        --compute-type) COMPUTE_TYPE="$2"; shift 2 ;;
        --prompt) PROMPT="$2"; shift 2 ;;
        --hotwords) HOTWORDS="$2"; shift 2 ;;
        --batch) BATCH=true; shift ;;
        --skip-jev) SKIP_JEV=true; shift ;;
        --only-stage) ONLY_STAGE="--only-stage $2"; shift 2 ;;
        --no-vad) VAD_FILTER=false; shift ;;
        --no-temperature-fallback) TEMPERATURE_FALLBACK=false; shift ;;
        --strict)
            STRICT=true
            COMPRESSION_RATIO_THRESHOLD=2.0
            LOGPROB_THRESHOLD=-0.5
            NO_SPEECH_THRESHOLD=0.8
            shift
            ;;
        --two-pass) TWO_PASS=true; shift ;;
        --compression-ratio-threshold) COMPRESSION_RATIO_THRESHOLD="$2"; shift 2 ;;
        --log-prob-threshold) LOGPROB_THRESHOLD="$2"; shift 2 ;;
        --no-speech-threshold) NO_SPEECH_THRESHOLD="$2"; shift 2 ;;
        --help|-h)
            echo "Usage: transcribe.sh <input.mp3> --output <dir> [options]"
            echo ""
            echo "Required:"
            echo "  --output DIR           Output directory (required)"
            echo ""
            echo "Common options:"
            echo "  --language LANG        Language code (default: ru)"
            echo "  --beam-size N          Beam size (default: 5, lower=faster)"
            echo "  --prompt TEXT|FILE     Initial prompt (text or path to file)"
            echo "  --hotwords WORDS       Hotwords to boost (space-separated)"
            echo "  --two-pass             Two-pass: extract hotwords with small model, then transcribe"
            echo "  --batch                Process all files in input directory"
            echo "  --strict               Strict anti-hallucination (tight thresholds)"
            echo "  --skip-jev             Skip all JEV validation stages"
            echo "  --only-stage N         Run only stage N (0-5)"
            echo ""
            echo "Advanced options:"
            echo "  --model NAME           Whisper model (default: large-v3)"
            echo "  --compute-type TYPE    Compute type (default: int8)"
            echo "  --no-vad               Disable Voice Activity Detection"
            echo "  --no-temperature-fallback  Use only temperature=0"
            echo "  --compression-ratio-threshold N  Skip segments above this (default: 2.4)"
            echo "  --logprob-threshold N  Skip segments below this (default: -1.0)"
            echo "  --no-speech-threshold N  Skip segments above this (default: 0.6)"
            echo "  --help                 Show this help"
            echo ""
            echo "Examples:"
            echo "  transcribe.sh lecture.mp3 --output ./out"
            echo "  transcribe.sh lecture.mp3 --output ./out --prompt 'BPMN, jBPM'"
            echo "  transcribe.sh lecture.mp3 --output ./out --hotwords 'BPMN шлюз gateway'"
            echo "  transcribe.sh lecture.mp3 --output ./out --two-pass --strict"
            echo "  transcribe.sh --batch /lectures/ --output ./out --resume"
            exit 0
            ;;
        -*) echo "Unknown option: $1. Try --help for usage."; exit 1 ;;
        *) INPUT="$1"; shift ;;
    esac
done

if [ -z "$OUTPUT" ]; then
    echo "ERROR: --output is required"
    exit 1
fi

mkdir -p "$OUTPUT"

# Two-pass: use dedicated script
if [ "$TWO_PASS" = true ]; then
    TWO_PASS_ARGS=(
        "$SCRIPT_DIR/two_pass_transcribe.py"
        --output "$OUTPUT"
        --beam-size "$BEAM_SIZE"
    )
    if [ -n "$PROMPT" ]; then
        TWO_PASS_ARGS+=(--initial-prompt "$PROMPT")
    fi
    
    if [ "$BATCH" = true ]; then
        for f in "$INPUT"/*.mp3 "$INPUT"/*.wav "$INPUT"/*.m4a; do
            [ -f "$f" ] || continue
            echo ""
            echo "--- Two-pass: $f ---"
            python3 "${TWO_PASS_ARGS[@]}" "$f" || echo "Failed: $f"
        done
    else
        python3 "${TWO_PASS_ARGS[@]}" "$INPUT"
    fi
    exit 0
fi

# Single-pass
PYTHON_ARGS=(
    "$SCRIPT_DIR/full_pipeline.py"
    --output "$OUTPUT"
    --language "$LANGUAGE"
    --beam-size "$BEAM_SIZE"
)

if [ -n "$PROMPT" ]; then
    PYTHON_ARGS+=(--initial-prompt "$PROMPT")
fi

if [ -n "$HOTWORDS" ]; then
    PYTHON_ARGS+=(--hotwords "$HOTWORDS")
fi

if [ "$VAD_FILTER" = false ]; then
    PYTHON_ARGS+=(--no-vad)
fi

if [ "$TEMPERATURE_FALLBACK" = false ]; then
    PYTHON_ARGS+=(--no-temperature-fallback)
fi

if [ "$SKIP_JEV" = true ]; then
    PYTHON_ARGS+=(--skip-jev)
fi

if [ -n "$ONLY_STAGE" ]; then
    PYTHON_ARGS+=($ONLY_STAGE)
fi

# Run
if [ "$BATCH" = true ]; then
    if [ -z "$INPUT" ]; then
        echo "ERROR: --batch requires input directory"
        exit 1
    fi
    echo "Batch mode: processing $INPUT"
    for f in "$INPUT"/*.mp3 "$INPUT"/*.wav "$INPUT"/*.m4a; do
        [ -f "$f" ] || continue
        echo ""
        echo "--- Processing: $f ---"
        python3 "${PYTHON_ARGS[@]}" "$f" || echo "Failed: $f"
    done
else
    if [ -z "$INPUT" ]; then
        echo "ERROR: input file is required"
        exit 1
    fi
    if [ ! -f "$INPUT" ]; then
        echo "ERROR: file not found: $INPUT"
        exit 1
    fi
    python3 "${PYTHON_ARGS[@]}" "$INPUT"
fi

echo ""
echo "Done. Output: $OUTPUT"
