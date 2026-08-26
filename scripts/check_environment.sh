#!/usr/bin/env bash
set -euo pipefail

readonly TOOLCHAIN_DIR="/Users/taeyoung/Developer/manim-toolchain"
readonly GLOBAL_WRAPPER="/Users/taeyoung/.local/bin/manim-video"
readonly USER_CONFIG="/Users/taeyoung/.config/manim/manim.cfg"

unset VIRTUAL_ENV
unset UV_PROJECT UV_PROJECT_ENVIRONMENT
unset UV_WORKING_DIR UV_WORKING_DIRECTORY
unset UV_ENV_FILE UV_NO_ENV_FILE UV_PYTHON

run_uv() {
    uv run --project "$TOOLCHAIN_DIR" --frozen --no-env-file -- "$@"
}

printf 'Toolchain: %s\n' "$TOOLCHAIN_DIR"
printf 'macOS: '
sw_vers -productVersion
printf 'Architecture: '
uname -m
printf 'uv: '
uv --version
printf 'Python: '
run_uv python --version
printf 'Manim CLI: '
run_uv manim --version
printf 'Typst CLI: '
typst --version
printf 'FFmpeg: '
ffmpeg -version 2>&1 | sed -n '1p'
printf 'FFprobe: '
ffprobe -version 2>&1 | sed -n '1p'
printf 'SoX: '
brew list --versions sox

run_uv python - <<'PY'
from importlib import metadata
from inspect import signature
from pathlib import Path
import sys

from google import genai
from manim import MathTypst, Typst
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gemini import GeminiService

toolchain = Path("/Users/taeyoung/Developer/manim-toolchain")
interpreter = Path(sys.executable).absolute()
expected_environment = (toolchain / ".venv").absolute()

if not interpreter.is_relative_to(expected_environment):
    raise SystemExit(f"FAIL: interpreter is outside the central environment: {interpreter}")

print(f"Python interpreter: {interpreter}")
print(f"Manim package: {metadata.version('manim')}")
print(f"Manim Voiceover package: {metadata.version('manim-voiceover')}")
print(f"Typst Python package: {metadata.version('typst')}")
print(f"Google Gen AI SDK: {metadata.version('google-genai')}")
print("Import check: PASS")
print(f"Typst classes: {Typst.__module__}.{Typst.__name__}, {MathTypst.__module__}.{MathTypst.__name__}")
print(f"Voiceover class: {VoiceoverScene.__module__}.{VoiceoverScene.__name__}")
print(f"Gemini class: {GeminiService.__module__}.{GeminiService.__name__}")
print(f"Gemini constructor: {signature(GeminiService)}")
print(f"Google SDK import: {genai.__name__}")
PY

if [[ ! -x "$GLOBAL_WRAPPER" ]]; then
    printf 'Global wrapper is missing or not executable: %s\n' "$GLOBAL_WRAPPER" >&2
    exit 1
fi

if [[ "$(readlink "$GLOBAL_WRAPPER")" != "$TOOLCHAIN_DIR/bin/manim-video" ]]; then
    printf 'Global wrapper does not point to the central project.\n' >&2
    exit 1
fi

if [[ "$(readlink "$USER_CONFIG")" != "$TOOLCHAIN_DIR/manim.cfg" ]]; then
    printf 'User-wide Manim config does not point to the central project.\n' >&2
    exit 1
fi

printf 'Global wrapper: %s -> %s\n' "$GLOBAL_WRAPPER" "$(readlink "$GLOBAL_WRAPPER")"
printf 'Shared config: %s -> %s\n' "$USER_CONFIG" "$(readlink "$USER_CONFIG")"

latex_found=0
for executable in latex pdflatex xelatex lualatex dvisvgm; do
    if command -v "$executable" >/dev/null 2>&1; then
        printf 'Optional TeX executable present (not required): %s\n' "$executable"
        latex_found=1
    fi
done

if [[ "$latex_found" -eq 0 ]]; then
    printf 'LaTeX executables on PATH: none (expected)\n'
fi
