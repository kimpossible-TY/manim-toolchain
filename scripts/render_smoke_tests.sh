#!/usr/bin/env bash
set -euo pipefail

readonly TOOLCHAIN_DIR="/Users/taeyoung/Projects/manim-toolchain"
readonly MANIM_VIDEO="$TOOLCHAIN_DIR/bin/manim-video"

cd "$TOOLCHAIN_DIR"

MODE="${1:-all}"
case "$MODE" in
    all|--typst-only|--voiceover-only) ;;
    *)
        printf 'Usage: %s [--typst-only|--voiceover-only]\n' "$0" >&2
        exit 64
        ;;
esac

LOG_DIR="media/logs"
mkdir -p "$LOG_DIR"

probe_video() {
    local scene_name="$1"
    local metadata_path="$2"
    local video_path

    video_path="$(find media/videos -type f -name "${scene_name}.mp4" -print | sort | tail -n 1)"
    if [[ -z "$video_path" ]]; then
        printf 'Rendered video not found for %s\n' "$scene_name" >&2
        return 1
    fi

    printf 'Rendered video: %s\n' "$video_path"
    ffprobe \
        -v error \
        -show_entries format=filename,duration,size:stream=index,codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels \
        -of json \
        "$video_path" | tee "$metadata_path"
}

render_typst() {
    local log_path="$LOG_DIR/typst_smoke_test.log"

    "$MANIM_VIDEO" -v DEBUG -ql scenes/typst_smoke_test.py TypstSmokeTest 2>&1 | tee "$log_path"

    if grep -Eiq '(^|[^[:alpha:]])(latex|pdflatex|xelatex|lualatex|dvisvgm)([^[:alpha:]]|$)' "$log_path"; then
        printf 'FAIL: a LaTeX pipeline marker appeared in %s\n' "$log_path" >&2
        return 1
    fi

    printf 'PASS: render log contains no LaTeX executable or pipeline marker.\n' | tee -a "$log_path"
    probe_video TypstSmokeTest "$LOG_DIR/typst_smoke_test.ffprobe.json"
}

api_key_is_configured() {
    if [[ -n "${GEMINI_API_KEY+x}" || -n "${GOOGLE_API_KEY+x}" ]]; then
        return 0
    fi
    if [[ -f "$TOOLCHAIN_DIR/.env" ]] && grep -Eq \
        '^[[:space:]]*(GEMINI_API_KEY|GOOGLE_API_KEY)[[:space:]]*=' \
        "$TOOLCHAIN_DIR/.env"; then
        return 0
    fi
    return 1
}

adc_is_selected() {
    if [[ "${GEMINI_AUTH_MODE:-}" == "adc" ]]; then
        return 0
    fi
    if [[ -f "$TOOLCHAIN_DIR/.env" ]] && grep -Eq \
        '^[[:space:]]*GEMINI_AUTH_MODE[[:space:]]*=[[:space:]]*adc[[:space:]]*$' \
        "$TOOLCHAIN_DIR/.env"; then
        return 0
    fi
    return 1
}

render_voiceover() {
    local log_path="$LOG_DIR/voiceover_smoke_test.log"

    if ! api_key_is_configured && ! adc_is_selected; then
        printf '%s\n' 'Gemini credentials are not configured in the central toolchain.' >&2
        printf '%s\n' 'Copy the central .env.example to .env, edit it privately, then rerun with --voiceover-only.' >&2
        return 2
    fi

    "$MANIM_VIDEO" -v INFO -ql scenes/voiceover_smoke_test.py GeminiVoiceoverSmokeTest 2>&1 | tee "$log_path"
    probe_video GeminiVoiceoverSmokeTest "$LOG_DIR/voiceover_smoke_test.ffprobe.json"
}

if [[ "$MODE" != "--voiceover-only" ]]; then
    render_typst
fi

if [[ "$MODE" != "--typst-only" ]]; then
    render_voiceover
fi
