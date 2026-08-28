#!/usr/bin/env bash
set -euo pipefail

readonly TOOLCHAIN_DIR="/Users/taeyoung/Developer/manim-toolchain"
readonly HOMEBREW_PREFIX="/opt/homebrew"
readonly HOMEBREW_PYTHON="$HOMEBREW_PREFIX/opt/python@3.13/bin/python3.13"
readonly -a HOMEBREW_FORMULAE=(uv python@3.13 typst ffmpeg sox)
readonly GLOBAL_MANIM_WRAPPER="/Users/taeyoung/.local/bin/manim-video"
readonly GLOBAL_VISUAL_WRAPPER="/Users/taeyoung/.local/bin/visual-python"
readonly USER_CONFIG="/Users/taeyoung/.config/manim/manim.cfg"

unset VIRTUAL_ENV
unset UV_PROJECT UV_PROJECT_ENVIRONMENT
unset UV_WORKING_DIR UV_WORKING_DIRECTORY
unset UV_ENV_FILE UV_NO_ENV_FILE UV_PYTHON

run_uv() {
    uv run --project "$TOOLCHAIN_DIR" --frozen --no-managed-python --no-env-file -- "$@"
}

check_homebrew_executable() {
    local executable="$1"
    local formula="$2"
    local executable_path
    local resolved_path

    executable_path="$(command -v "$executable" || true)"
    if [[ -z "$executable_path" ]]; then
        printf 'Required Homebrew executable is missing: %s\n' "$executable" >&2
        exit 1
    fi
    resolved_path="$(realpath "$executable_path")"
    case "$resolved_path" in
        "$HOMEBREW_PREFIX/Cellar/$formula/"*) ;;
        *)
            printf '%s is not owned by Homebrew formula %s: %s\n' \
                "$executable" "$formula" "$resolved_path" >&2
            exit 1
            ;;
    esac
    printf 'Homebrew executable: %s -> %s\n' "$executable" "$resolved_path"
}

printf 'Toolchain: %s\n' "$TOOLCHAIN_DIR"
if [[ "$(brew --prefix)" != "$HOMEBREW_PREFIX" ]]; then
    printf 'Unexpected Homebrew prefix: %s\n' "$(brew --prefix)" >&2
    exit 1
fi
printf 'Homebrew: '
brew --version | sed -n '1p'
for formula in "${HOMEBREW_FORMULAE[@]}"; do
    if ! formula_version="$(brew list --versions "$formula")"; then
        printf 'Required Homebrew formula is missing: %s\n' "$formula" >&2
        exit 1
    fi
    printf 'Homebrew formula: %s\n' "$formula_version"
done
check_homebrew_executable uv uv
check_homebrew_executable python3.13 python@3.13
check_homebrew_executable typst typst
check_homebrew_executable ffmpeg ffmpeg
check_homebrew_executable ffprobe ffmpeg
check_homebrew_executable sox sox
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
import manim_toolchain
from manim_toolchain.voiceover import ExpressiveGeminiService, ExpressiveVoiceoverScene
import pygfx
from rendercanvas.offscreen import RenderCanvas
import taichi
import wgpu

toolchain = Path("/Users/taeyoung/Developer/manim-toolchain")
interpreter = Path(sys.executable).absolute()
expected_environment = (toolchain / ".venv").absolute()
homebrew_python = Path("/opt/homebrew/opt/python@3.13/bin/python3.13").resolve()
base_interpreter = Path(sys._base_executable).resolve()

if not interpreter.is_relative_to(expected_environment):
    raise SystemExit(f"FAIL: interpreter is outside the central environment: {interpreter}")
if base_interpreter != homebrew_python:
    raise SystemExit(
        f"FAIL: central environment is not based on Homebrew Python 3.13: {base_interpreter}"
    )
if not Path(manim_toolchain.__file__).resolve().is_relative_to(toolchain / "src"):
    raise SystemExit("FAIL: expressive narration package is not imported from the central toolchain")

central_packages = (
    "manim",
    "manim-voiceover",
    "pygfx",
    "wgpu",
    "rendercanvas",
    "taichi",
    "google-genai",
    "typst",
)
for package_name in central_packages:
    package_root = Path(metadata.distribution(package_name).locate_file("")).resolve()
    if not package_root.is_relative_to(expected_environment.resolve()):
        raise SystemExit(
            f"FAIL: {package_name} is outside the central environment: {package_root}"
        )

print(f"Python interpreter: {interpreter}")
print(f"Python base interpreter: {base_interpreter}")
print(f"Manim package: {metadata.version('manim')}")
print(f"Manim Voiceover package: {metadata.version('manim-voiceover')}")
print(f"Typst Python package: {metadata.version('typst')}")
print(f"Google Gen AI SDK: {metadata.version('google-genai')}")
print(f"PyGfx package: {metadata.version('pygfx')}")
print(f"wgpu package: {metadata.version('wgpu')}")
print(f"rendercanvas package: {metadata.version('rendercanvas')}")
print(f"Taichi package: {metadata.version('taichi')}")
print("Import check: PASS")
print(f"Typst classes: {Typst.__module__}.{Typst.__name__}, {MathTypst.__module__}.{MathTypst.__name__}")
print(f"Voiceover class: {VoiceoverScene.__module__}.{VoiceoverScene.__name__}")
print(f"Gemini class: {GeminiService.__module__}.{GeminiService.__name__}")
print(f"Gemini constructor: {signature(GeminiService)}")
print(f"Expressive Gemini class: {ExpressiveGeminiService.__module__}.{ExpressiveGeminiService.__name__}")
print(f"Expressive scene class: {ExpressiveVoiceoverScene.__module__}.{ExpressiveVoiceoverScene.__name__}")
print(f"Google SDK import: {genai.__name__}")
print(f"PyGfx import: {pygfx.__name__}")
print(f"wgpu import: {wgpu.__name__}")
print(f"rendercanvas offscreen class: {RenderCanvas.__module__}.{RenderCanvas.__name__}")
print(f"Taichi import: {taichi.__name__}")
print("Central Python package ownership: PASS")
PY

"$HOMEBREW_PYTHON" - <<'PY'
from importlib import metadata

package_names = (
    "manim",
    "manim-voiceover",
    "pygfx",
    "wgpu",
    "rendercanvas",
    "taichi",
    "google-genai",
    "typst",
)
unexpected = []
for package_name in package_names:
    try:
        distribution = metadata.distribution(package_name)
    except metadata.PackageNotFoundError:
        continue
    unexpected.append(f"{package_name}=={distribution.version}")

if unexpected:
    raise SystemExit(
        "FAIL: visualization packages are installed in Homebrew system Python: "
        + ", ".join(unexpected)
    )
print("Homebrew system Python visualization packages: none (expected)")
PY

check_wrapper() {
    local wrapper="$1"
    local target="$2"

    if [[ ! -x "$wrapper" ]]; then
        printf 'Global wrapper is missing or not executable: %s\n' "$wrapper" >&2
        exit 1
    fi

    if [[ "$(readlink "$wrapper")" != "$target" ]]; then
        printf 'Global wrapper does not point to the central project: %s\n' "$wrapper" >&2
        exit 1
    fi

    printf 'Global wrapper: %s -> %s\n' "$wrapper" "$(readlink "$wrapper")"
}

check_wrapper "$GLOBAL_MANIM_WRAPPER" "$TOOLCHAIN_DIR/bin/manim-video"
check_wrapper "$GLOBAL_VISUAL_WRAPPER" "$TOOLCHAIN_DIR/bin/visual-python"

if [[ "$(readlink "$USER_CONFIG")" != "$TOOLCHAIN_DIR/manim.cfg" ]]; then
    printf 'User-wide Manim config does not point to the central project.\n' >&2
    exit 1
fi

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
