#!/usr/bin/env python3
"""Create a portable Blender image-sequence bundle without starting Colab."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


TOOLCHAIN_DIR = Path(__file__).resolve().parents[1]
RUNNER_FILES = (
    "blender_render.py",
    "blender_cycles.py",
    "parallel_blender_render.py",
    "verify_frame_sequence.py",
    "colab_session.py",
)
SENSITIVE_FILENAMES = {
    ".env",
    ".netrc",
    "id_rsa",
    "id_ecdsa",
    "id_dsa",
    "id_ed25519",
    "credentials",
    "credentials.json",
    "application_default_credentials.json",
    "adc.json",
    "cookies",
    "cookies.sqlite",
    "login data",
    "web data",
    "local state",
}
SENSITIVE_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}
SENSITIVE_DIRECTORY_NAMES = {
    ".aws",
    ".ssh",
    "gcloud",
    "chrome",
    "chromium",
    "firefox",
    "user data",
    "browser profile",
    "browser profiles",
}
SENSITIVE_NAME_MARKERS = (
    "credential",
    "private_key",
    "private-key",
    "privatekey",
    "service_account",
    "service-account",
    "application_default_credentials",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", type=Path, required=True)
    parser.add_argument("--scene-script", type=Path)
    parser.add_argument("--asset-dir", type=Path, action="append", default=[])
    parser.add_argument("--asset-file", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--width", type=int, required=True)
    parser.add_argument("--height", type=int, required=True)
    parser.add_argument("--fps", type=int, required=True)
    parser.add_argument("--frame-start", type=int, required=True)
    parser.add_argument("--frame-end", type=int, required=True)
    parser.add_argument("--engine", choices=("cycles", "eevee"), default="cycles")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--samples", type=int, default=128)
    parser.add_argument("--denoise", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument(
        "--device",
        choices=("auto", "cpu", "gpu", "cuda", "optix", "metal", "hip", "oneapi"),
        default="auto",
    )
    parser.add_argument("--require-gpu", action="store_true")
    parser.add_argument(
        "--colab-gpu", choices=("T4", "L4", "G4", "H100", "A100", "cpu"), default="T4"
    )
    parser.add_argument("--skip-scene-validation", action="store_true")
    args = parser.parse_args()
    for name in ("width", "height", "fps", "samples", "workers"):
        if getattr(args, name) <= 0:
            parser.error(f"--{name.replace('_', '-')} must be positive")
    if args.frame_start > args.frame_end:
        parser.error("--frame-start cannot exceed --frame-end")
    return args


def resolved_file(path: Path, description: str, suffix: str | None = None) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise ValueError(f"{description} is not a file: {resolved}")
    if suffix is not None and resolved.suffix.lower() != suffix:
        raise ValueError(f"{description} must have the {suffix} suffix: {resolved}")
    return resolved


def blender_binary() -> str:
    for candidate in ("blender", "/Applications/Blender.app/Contents/MacOS/Blender"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
        if Path(candidate).is_file():
            return candidate
    raise RuntimeError(
        "Blender is required to validate asset portability. Install Blender or perform the "
        "same validation separately before using --skip-scene-validation."
    )


def validate_source_scene(scene: Path) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="manim-toolchain-assets-") as directory:
        report_path = Path(directory) / "asset-validation.json"
        command = [
            blender_binary(),
            "--background",
            str(scene),
            "--python",
            str(TOOLCHAIN_DIR / "scripts" / "blender_render.py"),
            "--",
            "--mode",
            "validate",
            "--validate-assets",
            "--require-portable-assets",
            "--report",
            str(report_path),
        ]
        try:
            subprocess.run(command, check=True, text=True, capture_output=True)
            return json.loads(report_path.read_text(encoding="utf-8"))
        except subprocess.CalledProcessError as error:
            message = error.stderr.strip() or error.stdout.strip() or "Blender validation failed"
            raise RuntimeError(message) from error


def is_sensitive(path: Path) -> bool:
    name = path.name.lower()
    if name == ".env" or name.startswith(".env."):
        return True
    if name in SENSITIVE_FILENAMES or path.suffix.lower() in SENSITIVE_SUFFIXES:
        return True
    if any(part.lower() in SENSITIVE_DIRECTORY_NAMES for part in path.parts):
        return True
    return any(marker in name for marker in SENSITIVE_NAME_MARKERS)


def copy_asset(source: Path, destination: Path, copied: list[str]) -> None:
    if is_sensitive(source):
        raise ValueError(f"Refusing to include credential-like asset: {source.name}")
    if source.is_file():
        files = [(source, Path(source.name))]
    elif source.is_dir():
        files = [
            (child, child.relative_to(source))
            for child in sorted(source.rglob("*"))
            if child.is_file()
        ]
    else:
        raise ValueError(f"Asset path does not exist: {source}")
    for file_path, relative_path in files:
        if file_path.is_symlink():
            raise ValueError(f"Refusing to include symlink asset: {file_path.name}")
        if is_sensitive(file_path) or is_sensitive(file_path.resolve()):
            raise ValueError(f"Refusing to include credential-like asset: {file_path.name}")
        target = destination / relative_path
        if target.exists():
            raise ValueError(f"Asset destination collision: {target.relative_to(destination.parent)}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, target)
        copied.append(target.relative_to(destination.parent).as_posix())


def copy_file(source: Path, destination: Path) -> None:
    if is_sensitive(source):
        raise ValueError(f"Refusing to include credential-like file: {source.name}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def write_bootstrap(bundle: Path, manifest: dict[str, object]) -> None:
    render = manifest["render"]
    assert isinstance(render, dict)
    workers = int(render.get("workers", 4))
    frame_start = int(render["frame_start"])
    frame_end = int(render["frame_end"])
    total_frames = max(1, frame_end - frame_start + 1)
    engine = str(manifest.get("render_engine", "CYCLES")).lower()

    if total_frames > 1 or workers > 1:
        command = [
            "python3", "parallel_blender_render.py",
            "--blender-bin", '"$BLENDER_BIN"',
            "--output", "output/frame_",
            "--report", "output/render_report.json",
            "--engine", engine,
            "--width", str(render["width"]),
            "--height", str(render["height"]),
            "--fps", str(render["fps"]),
            "--frame-start", str(frame_start),
            "--frame-end", str(frame_end),
            "--workers", str(workers),
            "--samples", str(render["samples"]),
            "--device", str(manifest["requested_compute_device"]),
            "--denoise" if render["denoise"] else "--no-denoise",
        ]
        if manifest["scene_script"]:
            command.extend(("--scene-script", "scene.py"))
        else:
            command.extend(("--scene", "scene.blend"))
    else:
        command = [
            '"$BLENDER_BIN"', "--background", "scene.blend", "--python", "blender_render.py", "--",
            "--mode", "render", "--engine", engine, "--output", "output/frame_",
            "--report", "output/render_report.json", "--width", str(render["width"]),
            "--height", str(render["height"]), "--fps", str(render["fps"]),
            "--frame-start", str(frame_start), "--frame-end", str(frame_end),
            "--samples", str(render["samples"]), "--device", str(manifest["requested_compute_device"]),
            "--denoise" if render["denoise"] else "--no-denoise",
        ]
        if manifest["require_gpu"]:
            command.append("--require-gpu")
        if manifest["scene_script"]:
            command.extend(("--scene-script", "scene.py"))

    verify_command = [
        "python3", "verify_frame_sequence.py", "--directory", "output", "--prefix", "frame_",
        "--frame-start", str(render["frame_start"]), "--frame-end", str(render["frame_end"]),
        "--width", str(render["width"]), "--height", str(render["height"]),
    ]
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "# Run this only inside an explicitly authorized remote runtime.",
        'BLENDER_BIN="${BLENDER_BIN:-blender}"',
        'BLENDER_VERSION="${BLENDER_VERSION:-4.2.3}"',
        'BLENDER_MAJOR_MINOR="$(printf \'%s\\n\' "$BLENDER_VERSION" | cut -d. -f1,2)"',
        'BLENDER_TARBALL="blender-${BLENDER_VERSION}-linux-x64.tar.xz"',
        'BLENDER_URL="${BLENDER_TARBALL_URL:-https://download.blender.org/release/Blender${BLENDER_MAJOR_MINOR}/${BLENDER_TARBALL}}"',
        'BLENDER_INSTALL_DIR="/opt/blender-${BLENDER_VERSION}"',
        'if command -v "$BLENDER_BIN" >/dev/null 2>&1 && "$BLENDER_BIN" --version >/dev/null 2>&1; then',
        "  echo 'REMOTE_BLENDER_ACTION=reused'",
        'elif [[ -x "$BLENDER_INSTALL_DIR/blender" ]] && "$BLENDER_INSTALL_DIR/blender" --version >/dev/null 2>&1; then',
        '  BLENDER_BIN="$BLENDER_INSTALL_DIR/blender"',
        "  echo 'REMOTE_BLENDER_ACTION=reused'",
        "else",
        "  echo 'REMOTE_BLENDER_ACTION=installing'",
        '  mkdir -p "$BLENDER_INSTALL_DIR"',
        '  TMP_TARBALL="$(mktemp "${TMPDIR:-/tmp}/blender-XXXXXX")"',
        '  if command -v curl >/dev/null 2>&1; then',
        '    curl -fsSL "$BLENDER_URL" -o "$TMP_TARBALL"',
        '  elif command -v wget >/dev/null 2>&1; then',
        '    wget -q -O "$TMP_TARBALL" "$BLENDER_URL"',
        "  else",
        "    printf 'Neither curl nor wget is available to download Blender\\n' >&2",
        "    exit 1",
        "  fi",
        '  tar -xf "$TMP_TARBALL" -C "$BLENDER_INSTALL_DIR" --strip-components=1',
        '  find "$TMP_TARBALL" -delete',
        '  ln -sf "$BLENDER_INSTALL_DIR/blender" /usr/local/bin/blender || true',
        '  BLENDER_BIN="$BLENDER_INSTALL_DIR/blender"',
        "  echo 'REMOTE_BLENDER_ACTION=installed'",
        "fi",
        'REMOTE_BLENDER_VERSION="$("$BLENDER_BIN" --version | sed -n \'1p\')"',
        'printf \'REMOTE_BLENDER_VERSION=%s\\n\' "$REMOTE_BLENDER_VERSION"',
        " ".join(command),
        " ".join(verify_command),
        "python3 - <<'PY'",
        "import json",
        "from pathlib import Path",
        "report_path = Path('output/render_report.json')",
        "if not report_path.is_file() or report_path.stat().st_size == 0:",
        "    raise SystemExit('Blender render report is missing or empty')",
        "report = json.loads(report_path.read_text(encoding='utf-8'))",
        "if not report.get('render_executed'):",
        "    raise SystemExit(f'Incomplete Blender render report: {report}')",
        "print('REMOTE_CONFIGURED_DEVICE=' + str(report.get('render_device', 'GPU')))",
        "print('REMOTE_RENDER_REPORT=PASS')",
        "PY",
        "",
    ]
    target = bundle / "bootstrap.sh"
    target.write_text("\n".join(lines), encoding="utf-8")
    target.chmod(0o755)


def write_colab_files(bundle: Path, manifest: dict[str, object]) -> None:
    remote_runner = """import shutil
import subprocess
import tarfile
from pathlib import Path

archive = Path('__REMOTE_INPUT_ARCHIVE__')
job_dir = Path('__REMOTE_JOB_DIRECTORY__')
output_archive = Path('__REMOTE_OUTPUT_ARCHIVE__')

if not archive.is_file():
    raise FileNotFoundError(f'Uploaded job archive is missing: {archive}')
if job_dir.exists():
    raise FileExistsError(f'Remote job directory already exists: {job_dir}')
if output_archive.exists():
    raise FileExistsError(f'Remote output archive already exists: {output_archive}')

job_dir.parent.mkdir(parents=True, exist_ok=True)
job_dir.mkdir()
import sys
process = subprocess.Popen(
    ['bash', str(job_dir / 'bootstrap.sh')],
    cwd=job_dir,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
)
for line in process.stdout:
    print(line, end='', flush=True)
returncode = process.wait()
if returncode != 0:
    raise subprocess.CalledProcessError(returncode, ['bash', str(job_dir / 'bootstrap.sh')])
if not (job_dir / 'output').is_dir():
    raise FileNotFoundError(f'Render output directory is missing: {job_dir / "output"}')
output_archive.parent.mkdir(parents=True, exist_ok=True)
with tarfile.open(output_archive, 'w:gz') as tar:
    tar.add(job_dir / 'output', arcname='output')
archive.unlink(missing_ok=True)
print(f'REMOTE_JOB_DIRECTORY={job_dir}')
print(f'COLAB_RENDER_ARCHIVE={output_archive}')
"""
    cleanup_runner = """import shutil
from pathlib import Path

job_dir = Path('__REMOTE_JOB_DIRECTORY__')
input_archive = Path('__REMOTE_INPUT_ARCHIVE__')
output_archive = Path('__REMOTE_OUTPUT_ARCHIVE__')
for path in (job_dir, input_archive, output_archive):
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()
print('REMOTE_JOB_CLEANUP=PASS')
"""
    (bundle / "run_colab_job.py").write_text(remote_runner, encoding="utf-8")
    (bundle / "cleanup_colab_job.py").write_text(cleanup_runner, encoding="utf-8")
    default_session = "visual-render"
    default_gpu = str(manifest["colab_gpu"])
    render = manifest["render"]
    assert isinstance(render, dict)
    lines = [
        "#!/usr/bin/env bash",
        "# Colab is an optional remote backend; local-first routing remains the default.",
        "# Authorization-required: upload and remote execution begin below.",
        "# `colab new` allocates a billable/limited runtime and is allowed only with",
        "# --allow-new-session or COLAB_ALLOW_NEW_SESSION=1.",
        "# The normal session policy is reuse-before-create: visual-render on T4.",
        "# The bundled resolver uses official `colab sessions`, `colab status`, and `colab ls`.",
        "# A session's accelerator is fixed for its lifetime; mismatches fail safely.",
        "set -euo pipefail",
        "umask 077",
        "",
        "usage() {",
        "  cat <<'USAGE'",
        "Usage: colab_commands.sh [--allow-new-session] [--stop-after-job]",
        "",
        "  --allow-new-session  explicitly authorize allocation when the named session is absent",
        "  --stop-after-job     explicitly use disposable mode and stop after local verification",
        "",
        "Environment overrides: COLAB_SESSION, COLAB_GPU, COLAB_JOB_ID,",
        "COLAB_ALLOW_NEW_SESSION=1, and COLAB_STOP_AFTER_JOB=1.",
        "USAGE",
        "}",
        'ALLOW_NEW_SESSION="${COLAB_ALLOW_NEW_SESSION:-0}"',
        'STOP_AFTER_JOB="${COLAB_STOP_AFTER_JOB:-0}"',
        "while (($# > 0)); do",
        '  case "$1" in',
        "    --allow-new-session) ALLOW_NEW_SESSION=1 ;;",
        "    --stop-after-job) STOP_AFTER_JOB=1 ;;",
        "    --help|-h) usage; exit 0 ;;",
        '    *) printf \'Unknown option: %s\\n\' "$1" >&2; usage >&2; exit 64 ;;',
        "  esac",
        "  shift",
        "done",
        'case "$ALLOW_NEW_SESSION" in 0|1) ;; *) printf \'COLAB_SESSION_ACTION=unavailable\\nInvalid COLAB_ALLOW_NEW_SESSION: %s\\n\' "$ALLOW_NEW_SESSION" >&2; exit 64 ;; esac',
        'case "$STOP_AFTER_JOB" in 0|1) ;; *) printf \'Invalid COLAB_STOP_AFTER_JOB: %s\\n\' "$STOP_AFTER_JOB" >&2; exit 64 ;; esac',
        'JOB_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)"',
        f'SESSION_NAME="${{COLAB_SESSION:-{default_session}}}"',
        f'REQUESTED_GPU="${{COLAB_GPU:-{default_gpu}}}"',
        'BUNDLE_NAME="$(basename -- "$JOB_DIR")"',
        'BUNDLE_SLUG="$(printf \'%s\' "$BUNDLE_NAME" | tr -c \'A-Za-z0-9._-\' \'-\')"',
        'BUNDLE_SLUG="${BUNDLE_SLUG:-render-job}"',
        'JOB_ID="${COLAB_JOB_ID:-${BUNDLE_SLUG}-$(date -u +%Y%m%dT%H%M%SZ)-$$}"',
        'if ! [[ "$JOB_ID" =~ ^[A-Za-z0-9._-]+$ ]]; then printf \'Invalid COLAB_JOB_ID: %s\\n\' "$JOB_ID" >&2; exit 64; fi',
        'REMOTE_JOB_DIRECTORY="/content/manim-toolchain/jobs/$JOB_ID"',
        'REMOTE_INPUT_ARCHIVE="/content/manim-toolchain-upload-$JOB_ID.tar.gz"',
        'REMOTE_OUTPUT_ARCHIVE="/content/manim-toolchain-output-$JOB_ID.tar.gz"',
        'JOB_ARCHIVE="$JOB_DIR.tar.gz"',
        'LOCAL_ARCHIVE="$JOB_DIR/render-output-$JOB_ID.tar.gz"',
        'LOCAL_OUTPUT_DIRECTORY="$JOB_DIR/output"',
        'printf \'REMOTE_JOB_ID=%s\\nREMOTE_JOB_DIRECTORY=%s\\n\' "$JOB_ID" "$REMOTE_JOB_DIRECTORY"',
        'if ! command -v colab >/dev/null 2>&1; then printf \'COLAB_SESSION_ACTION=unavailable\\nColab CLI is not installed or not on PATH.\\n\' >&2; exit 127; fi',
        'if [[ -n "$(find "$LOCAL_OUTPUT_DIRECTORY" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then printf \'Refusing to reuse a non-empty local output directory: %s\\n\' "$LOCAL_OUTPUT_DIRECTORY" >&2; exit 1; fi',
        'if [[ -e "$JOB_ARCHIVE" || -e "$LOCAL_ARCHIVE" ]]; then printf \'Refusing to overwrite an existing local archive; use a fresh render-job bundle.\\n\' >&2; exit 1; fi',
        'SESSION_HELPER="$JOB_DIR/colab_session.py"',
        'if [[ ! -f "$SESSION_HELPER" ]]; then printf \'Colab session helper is missing from the bundle: %s\\n\' "$SESSION_HELPER" >&2; exit 1; fi',
        'SESSION_ARGS=(--session "$SESSION_NAME" --requested-gpu "$REQUESTED_GPU")',
        'if [[ "$ALLOW_NEW_SESSION" == "1" ]]; then SESSION_ARGS+=(--allow-new-session); fi',
        "# Authorization-required session resolution begins here; it may allocate only with the explicit flag.",
        'if SESSION_INFO="$(python3 "$SESSION_HELPER" "${SESSION_ARGS[@]}")"; then',
        '  printf \'%s\\n\' "$SESSION_INFO"',
        "else",
        '  printf \'%s\\n\' "$SESSION_INFO"',
        "  printf '%s\\n' 'REMOTE_EXECUTION=not_started'",
        "  exit 1",
        "fi",
        'SESSION_ACTION=""',
        'ACTUAL_GPU=""',
        'while IFS=\'=\' read -r INFO_KEY INFO_VALUE; do',
        '  case "$INFO_KEY" in',
        '    COLAB_SESSION_ACTION) SESSION_ACTION="$INFO_VALUE" ;;',
        '    COLAB_ACTUAL_GPU) ACTUAL_GPU="$INFO_VALUE" ;;',
        "  esac",
        'done <<< "$SESSION_INFO"',
        'if [[ "$SESSION_ACTION" != "reused" && "$SESSION_ACTION" != "created" ]]; then printf \'Unexpected Colab session action: %s\\n\' "$SESSION_ACTION" >&2; exit 1; fi',
        'SESSION_LIFETIME_STATE="yes"',
        'RUNNER_SCRIPT=""',
        'CLEANUP_SCRIPT=""',
        "on_exit() {",
        '  local exit_code=$?',
        '  [[ -z "$RUNNER_SCRIPT" ]] || find "$RUNNER_SCRIPT" -delete',
        '  [[ -z "$CLEANUP_SCRIPT" ]] || find "$CLEANUP_SCRIPT" -delete',
        '  if ((exit_code != 0)); then',
        "    printf '%s\\n' 'REMOTE_EXECUTION=failed'",
        '    printf \'COLAB_SESSION_LEFT_RUNNING=%s\\n\' "$SESSION_LIFETIME_STATE"',
        "  fi",
        "}",
        "trap on_exit EXIT",
        "",
        "render_template() {",
        '  local template_path="$1" output_path="$2" remote_input="$3" remote_job="$4" remote_output="$5"',
        "  python3 - \"$template_path\" \"$output_path\" \"$remote_input\" \"$remote_job\" \"$remote_output\" <<'PY'",
        "from pathlib import Path",
        "import sys",
        "template = Path(sys.argv[1]).read_text(encoding='utf-8')",
        "for placeholder, value in zip((\"__REMOTE_INPUT_ARCHIVE__\", \"__REMOTE_JOB_DIRECTORY__\", \"__REMOTE_OUTPUT_ARCHIVE__\"), sys.argv[3:]):",
        "    if placeholder not in template:",
        "        raise SystemExit(f'Missing template placeholder: {placeholder}')",
        "    template = template.replace(placeholder, value)",
        "if '__REMOTE_' in template:",
        "    raise SystemExit('Unresolved remote path placeholder in Colab runner')",
        "Path(sys.argv[2]).write_text(template, encoding='utf-8')",
        "PY",
        "}",
        'RUNNER_SCRIPT="$(mktemp "${TMPDIR:-/tmp}/visual-colab-runner.XXXXXX")"',
        'CLEANUP_SCRIPT="$(mktemp "${TMPDIR:-/tmp}/visual-colab-cleanup.XXXXXX")"',
        'render_template "$JOB_DIR/run_colab_job.py" "$RUNNER_SCRIPT" "$REMOTE_INPUT_ARCHIVE" "$REMOTE_JOB_DIRECTORY" "$REMOTE_OUTPUT_ARCHIVE"',
        'render_template "$JOB_DIR/cleanup_colab_job.py" "$CLEANUP_SCRIPT" "$REMOTE_INPUT_ARCHIVE" "$REMOTE_JOB_DIRECTORY" "$REMOTE_OUTPUT_ARCHIVE"',
        'COPYFILE_DISABLE=1 tar -czf "$JOB_ARCHIVE" --exclude=output --exclude=\'render-output-*.tar.gz\' -C "$JOB_DIR" .',
        "",
        "# Authorization-required upload and remote execution begin below.",
        'colab upload -s "$SESSION_NAME" "$JOB_ARCHIVE" "$REMOTE_INPUT_ARCHIVE"',
        'colab exec -s "$SESSION_NAME" --timeout 3600 -f "$RUNNER_SCRIPT"',
        'colab download -s "$SESSION_NAME" "$REMOTE_OUTPUT_ARCHIVE" "$LOCAL_ARCHIVE"',
        'if [[ ! -s "$LOCAL_ARCHIVE" ]]; then printf \'Downloaded render archive is missing or empty: %s\\n\' "$LOCAL_ARCHIVE" >&2; exit 1; fi',
        'python3 - "$LOCAL_ARCHIVE" "$JOB_DIR" <<\'PY\'',
        "import sys",
        "import tarfile",
        "from pathlib import Path",
        "archive_path = Path(sys.argv[1])",
        "destination = Path(sys.argv[2]).resolve()",
        "with tarfile.open(archive_path, 'r:gz') as tar:",
        "    for member in tar.getmembers():",
        "        target = (destination / member.name).resolve()",
        "        if not target.is_relative_to(destination):",
        "            raise SystemExit(f'Unsafe downloaded archive member: {member.name}')",
        "        if member.issym() or member.islnk():",
        "            raise SystemExit(f'Links are not allowed in downloaded render output: {member.name}')",
        "    tar.extractall(destination, filter='data')",
        "PY",
        f'python3 "$JOB_DIR/verify_frame_sequence.py" --directory "$LOCAL_OUTPUT_DIRECTORY" --prefix frame_ --frame-start {render["frame_start"]} --frame-end {render["frame_end"]} --width {render["width"]} --height {render["height"]}',
        'python3 - "$LOCAL_OUTPUT_DIRECTORY/render_report.json" <<\'PY\'',
        "import json",
        "import sys",
        "from pathlib import Path",
        "report_path = Path(sys.argv[1])",
        "if not report_path.is_file():",
        "    raise SystemExit(f'Missing downloaded render report: {report_path}')",
        "report = json.loads(report_path.read_text(encoding='utf-8'))",
        "if not report.get('render_executed'):",
        "    raise SystemExit(f'Unexpected downloaded render report: {report}')",
        "if report.get('render_device') not in {'CPU', 'GPU'}:",
        "    raise SystemExit(f'Render device was not recorded: {report.get(\"render_device\")}')",
        "print('LOCAL_RENDER_REPORT=PASS')",
        "print('LOCAL_CONFIGURED_DEVICE=' + str(report.get('render_device')))",
        "PY",
        'if colab exec -s "$SESSION_NAME" -f "$CLEANUP_SCRIPT"; then',
        "  REMOTE_CLEANUP=completed",
        "else",
        "  REMOTE_CLEANUP=failed",
        "  printf '%s\\n' 'Remote cleanup failed; the job-specific remote artifacts were retained for diagnosis.' >&2",
        "fi",
        'printf \'REMOTE_CLEANUP=%s\\n\' "$REMOTE_CLEANUP"',
        'if [[ "$STOP_AFTER_JOB" == "1" ]]; then',
        "  # Explicit disposable mode; failures above never stop a shared session.",
        '  if colab stop -s "$SESSION_NAME"; then',
        '    SESSION_LIFETIME_STATE="no"',
        "  else",
        '    SESSION_LIFETIME_STATE="unknown"',
        "    printf '%s\\n' 'Explicit session stop failed; inspect the Colab session manually.' >&2",
        "    exit 1",
        "  fi",
        "fi",
        "",
        "printf '%s\\n' 'REMOTE_EXECUTION=completed'",
        'printf \'LOCAL_ARCHIVE=%s\\nLOCAL_OUTPUT_DIRECTORY=%s\\n\' "$LOCAL_ARCHIVE" "$LOCAL_OUTPUT_DIRECTORY"',
        'printf \'COLAB_SESSION_LEFT_RUNNING=%s\\n\' "$SESSION_LIFETIME_STATE"',
        'if [[ "$SESSION_LIFETIME_STATE" == "yes" ]]; then printf \'COLAB_SESSION_STOP_COMMAND=visual-colab-stop --session %s\\n\' "$SESSION_NAME"; fi',
        "",
    ]
    target = bundle / "colab_commands.sh"
    target.write_text("\n".join(lines), encoding="utf-8")
    target.chmod(0o755)


def main() -> None:
    args = parse_args()
    scene = resolved_file(args.scene, "--scene", ".blend")
    scene_script = resolved_file(args.scene_script, "--scene-script") if args.scene_script else None
    output = args.output.expanduser().resolve()
    if output.exists():
        raise ValueError(f"Refusing to overwrite existing job bundle: {output}")
    validation = (
        {"checked": False, "portable": None, "asset_count": 0, "reason": "user skipped"}
        if args.skip_scene_validation
        else validate_source_scene(scene)
    )
    asset_validation = validation.get("asset_validation", validation)
    assert isinstance(asset_validation, dict)
    output.mkdir(parents=True)
    try:
        copy_file(scene, output / "scene.blend")
        if scene_script:
            copy_file(scene_script, output / "scene.py")
        for filename in RUNNER_FILES:
            copy_file(TOOLCHAIN_DIR / "scripts" / filename, output / filename)
        assets_directory = output / "assets"
        assets_directory.mkdir()
        copied_assets: list[str] = []
        for asset_dir in args.asset_dir:
            copy_asset(asset_dir.expanduser().resolve(), assets_directory, copied_assets)
        for asset_file in args.asset_file:
            copy_asset(resolved_file(asset_file, "--asset-file"), assets_directory, copied_assets)
        (output / "output").mkdir()
        manifest: dict[str, object] = {
            "format_version": 1,
            "scene": "scene.blend",
            "scene_script": "scene.py" if scene_script else None,
            "assets": sorted(copied_assets),
            "source_validation": {
                "checked": asset_validation.get("checked", False),
                "portable": asset_validation.get("portable"),
                "asset_count": asset_validation.get("asset_count", 0),
            },
            "blender_version": str(validation.get("blender_version", "validated locally")),
            "render_engine": args.engine.upper(),
            "requested_compute_device": args.device,
            "require_gpu": args.require_gpu,
            "colab_session": "visual-render",
            "colab_gpu": args.colab_gpu,
            "colab_session_policy": "reuse-before-create",
            "render": {
                "engine": args.engine.upper(),
                "width": args.width, "height": args.height, "fps": args.fps,
                "frame_start": args.frame_start, "frame_end": args.frame_end,
                "output_format": "PNG", "output_prefix": "output/frame_",
                "samples": args.samples, "denoise": args.denoise,
                "workers": args.workers,
                "color_management": validation.get("color_management", {}),
            },
            "remote_authorization_required": True,
        }
        (output / "render_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        write_bootstrap(output, manifest)
        write_colab_files(output, manifest)
    except Exception:
        shutil.rmtree(output)
        raise
    print(f"RENDER_JOB={output}")
    print(f"RENDER_JOB_ASSETS={len(copied_assets)}")
    print("RENDER_JOB_REMOTE_EXECUTION=NOT_STARTED")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(2) from error
