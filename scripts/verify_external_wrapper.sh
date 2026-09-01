#!/usr/bin/env bash
set -euo pipefail

readonly TOOLCHAIN_DIR="/Users/taeyoung/Developer/visual-explainer-toolchain"
readonly FIXTURE_DIR="$TOOLCHAIN_DIR/tests/external-project"
readonly LOG_DIR="$TOOLCHAIN_DIR/media/logs"
readonly BLENDER_PREVIEW="$TOOLCHAIN_DIR/bin/visual-blender-preview"
readonly VISUAL_PYTHON="$TOOLCHAIN_DIR/bin/visual-python"

mkdir -p "$LOG_DIR"

temp_base="$(CDPATH= cd -- "${TMPDIR:-/tmp}" && pwd -P)"
TEMP_PROJECT="$(mktemp -d "$temp_base/visual-explainer-external.XXXXXX")"
TEMP_PROJECT="$(CDPATH= cd -- "$TEMP_PROJECT" && pwd -P)"

cleanup() {
    case "$TEMP_PROJECT" in
        "$temp_base"/manim-video-external.*) rm -rf "$TEMP_PROJECT" ;;
        *) printf 'Refusing to clean unexpected path: %s\n' "$TEMP_PROJECT" >&2 ;;
    esac
}
trap cleanup EXIT

cp -R "$FIXTURE_DIR/." "$TEMP_PROJECT/"

cd "$TEMP_PROJECT"
uv venv --python 3.14 .venv

hash_external_venv() {
    COPYFILE_DISABLE=1 tar -cf - .venv | shasum -a 256
}

external_venv_before="$(hash_external_venv)"
external_project_before="$(shasum -a 256 pyproject.toml)"

# This is intentionally the public command, with a relative scene path, from a
# project that has its own incompatible Python requirement and local .venv.
manim-video scene.py TestScene 2>&1 | tee "$LOG_DIR/external-wrapper-smoke.log"
visual-python visual_scene.py 2>&1 | tee "$LOG_DIR/external-visual-wrapper-smoke.log"
"$BLENDER_PREVIEW" \
    --scene-script blender_scene.py \
    --output external-renders/blender-preview.png \
    --report external-renders/blender-preview.json \
    --width 96 --height 72 --samples 2 --frame 1 \
    2>&1 | tee "$LOG_DIR/external-blender-wrapper-smoke.log"

external_venv_after="$(hash_external_venv)"
external_project_after="$(shasum -a 256 pyproject.toml)"
if [[ "$external_venv_before" != "$external_venv_after" ]]; then
    printf 'FAIL: the external project .venv was modified.\n' >&2
    exit 1
fi
if [[ "$external_project_before" != "$external_project_after" ]]; then
    printf 'FAIL: the external project pyproject.toml was modified.\n' >&2
    exit 1
fi

grep -F "EXTERNAL_SCENE_CWD=$TEMP_PROJECT" "$LOG_DIR/external-wrapper-smoke.log" >/dev/null
grep -F "EXTERNAL_SCENE_PYTHON=$TOOLCHAIN_DIR/.venv/bin/python" "$LOG_DIR/external-wrapper-smoke.log" >/dev/null
grep -F 'EXTERNAL_SCENE_MANIM=0.21.0' "$LOG_DIR/external-wrapper-smoke.log" >/dev/null
grep -F 'EXTERNAL_SCENE_TYPST=0.15.0' "$LOG_DIR/external-wrapper-smoke.log" >/dev/null
grep -F 'EXTERNAL_SCENE_CLOUD_CREDENTIALS_ABSENT=True' "$LOG_DIR/external-wrapper-smoke.log" >/dev/null

grep -F "EXTERNAL_VISUAL_CWD=$TEMP_PROJECT" "$LOG_DIR/external-visual-wrapper-smoke.log" >/dev/null
grep -F "EXTERNAL_VISUAL_PYTHON=$TOOLCHAIN_DIR/.venv/bin/python" "$LOG_DIR/external-visual-wrapper-smoke.log" >/dev/null
grep -F 'EXTERNAL_VISUAL_PYGFX=0.17.0' "$LOG_DIR/external-visual-wrapper-smoke.log" >/dev/null
grep -F 'EXTERNAL_VISUAL_WGPU=0.32.0' "$LOG_DIR/external-visual-wrapper-smoke.log" >/dev/null
grep -F 'EXTERNAL_VISUAL_TAICHI=1.7.4' "$LOG_DIR/external-visual-wrapper-smoke.log" >/dev/null
grep -F 'EXTERNAL_VISUAL_NARRATION=question/curious' "$LOG_DIR/external-visual-wrapper-smoke.log" >/dev/null
grep -F 'EXTERNAL_VISUAL_CREDENTIALS_ABSENT=True' "$LOG_DIR/external-visual-wrapper-smoke.log" >/dev/null
grep -F "EXTERNAL_BLENDER_CWD=$TEMP_PROJECT" "$LOG_DIR/external-blender-wrapper-smoke.log" >/dev/null

rendered_video="$(find external-media -type f -name 'TestScene.mp4' -print | head -n 1)"
if [[ -z "$rendered_video" ]]; then
    printf 'FAIL: external scene video was not produced.\n' >&2
    exit 1
fi

if [[ ! -s external-renders/frame.rgba ]]; then
    printf 'FAIL: external offscreen frame was not produced.\n' >&2
    exit 1
fi
if [[ "$(stat -f '%z' external-renders/frame.rgba)" -ne $((96 * 72 * 4)) ]]; then
    printf 'FAIL: external offscreen frame has an unexpected size.\n' >&2
    exit 1
fi

"$VISUAL_PYTHON" "$TOOLCHAIN_DIR/scripts/verify_blender_render.py" \
    --image external-renders/blender-preview.png \
    --report external-renders/blender-preview.json \
    --engine BLENDER_EEVEE --width 96 --height 72

ffprobe \
    -v error \
    -show_entries format=filename,duration,size:stream=index,codec_type,codec_name,width,height,r_frame_rate \
    -of json \
    "$rendered_video" | tee "$LOG_DIR/external-wrapper-smoke.ffprobe.json"

printf 'PASS: both wrappers preserved the caller cwd and relative output paths.\n'
printf 'PASS: central Manim, PyGfx, wgpu, Taichi, and narration packages were used.\n'
printf 'PASS: visual-python did not load narration credentials.\n'
printf 'PASS: external Manim did not load Runpod/R2 credentials.\n'
printf 'PASS: external pyproject.toml and .venv were ignored and left unchanged.\n'
printf 'PASS: Blender preview preserved the caller cwd and did not mutate its environment.\n'
