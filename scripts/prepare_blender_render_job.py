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
RUNNER_FILES = ("blender_render.py", "blender_cycles.py")
SENSITIVE_FILENAMES = {".env", ".netrc", "id_rsa", "id_ed25519"}
SENSITIVE_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}


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
    for name in ("width", "height", "fps", "samples"):
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
    return path.name.lower() in SENSITIVE_FILENAMES or path.suffix.lower() in SENSITIVE_SUFFIXES


def copy_asset(source: Path, destination: Path, copied: list[str]) -> None:
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
        if is_sensitive(file_path):
            raise ValueError(f"Refusing to include credential-like asset: {file_path.name}")
        target = destination / relative_path
        if target.exists():
            raise ValueError(f"Asset destination collision: {target.relative_to(destination.parent)}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, target)
        copied.append(target.relative_to(destination.parent).as_posix())


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def write_bootstrap(bundle: Path, manifest: dict[str, object]) -> None:
    render = manifest["render"]
    assert isinstance(render, dict)
    command = [
        '"$BLENDER_BIN"', "--background", "scene.blend", "--python", "blender_render.py", "--",
        "--mode", "render", "--engine", "cycles", "--output", "output/frame_",
        "--report", "output/render_report.json", "--width", str(render["width"]),
        "--height", str(render["height"]), "--fps", str(render["fps"]),
        "--frame-start", str(render["frame_start"]), "--frame-end", str(render["frame_end"]),
        "--samples", str(render["samples"]), "--device", str(manifest["requested_compute_device"]),
        "--denoise" if render["denoise"] else "--no-denoise",
    ]
    if manifest["require_gpu"]:
        command.append("--require-gpu")
    if manifest["scene_script"]:
        command.extend(("--scene-script", "scene.py"))
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "# Run this only inside an explicitly authorized remote runtime.",
        'BLENDER_BIN="${BLENDER_BIN:-blender}"',
        'if ! command -v "$BLENDER_BIN" >/dev/null 2>&1; then',
        "  apt-get update",
        "  DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends blender",
        "fi",
        '"$BLENDER_BIN" --version | sed -n \'1p\'',
        " ".join(command),
        "python3 - <<'PY'",
        "from pathlib import Path",
        "frames = sorted(Path('output').glob('frame_*.png'))",
        "if not frames or any(path.stat().st_size == 0 for path in frames):",
        "    raise SystemExit('No complete PNG frame sequence was produced')",
        "print(f'REMOTE_FRAME_COUNT={len(frames)}')",
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

archive = Path('/content/render-job.tar.gz')
job_dir = Path('/content/render-job')
with tarfile.open(archive, 'r:gz') as tar:
    tar.extractall('/content', filter='data')
subprocess.run(['bash', str(job_dir / 'bootstrap.sh')], check=True)
shutil.make_archive('/content/render-output', 'gztar', job_dir / 'output')
print('COLAB_RENDER_ARCHIVE=/content/render-output.tar.gz')
"""
    (bundle / "run_colab_job.py").write_text(remote_runner, encoding="utf-8")
    session_name = f"blender-{bundle.name}".replace("_", "-")[:48]
    lines = [
        "#!/usr/bin/env bash",
        "# Authorization-required: `colab new` allocates a billable/limited runtime.",
        "# Review the bundle, authorize this work, then run commands explicitly.",
        "set -euo pipefail",
        'JOB_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)"',
        f'SESSION_NAME="${{COLAB_SESSION:-{session_name}}}"',
        f'REQUESTED_GPU="${{COLAB_GPU:-{manifest["colab_gpu"]}}}"',
        'cd "$(dirname -- "$JOB_DIR")"',
        'tar -czf "$JOB_DIR.tar.gz" "$(basename -- "$JOB_DIR")"',
        '# Authorization-required remote actions begin below.',
        'colab new -s "$SESSION_NAME" --gpu "$REQUESTED_GPU"',
        'colab upload -s "$SESSION_NAME" "$JOB_DIR.tar.gz" /content/render-job.tar.gz',
        'colab exec -s "$SESSION_NAME" -f "$JOB_DIR/run_colab_job.py"',
        'colab download -s "$SESSION_NAME" /content/render-output.tar.gz "$JOB_DIR/render-output.tar.gz"',
        'colab stop -s "$SESSION_NAME"',
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
            "render_engine": "CYCLES",
            "requested_compute_device": args.device,
            "require_gpu": args.require_gpu,
            "colab_gpu": args.colab_gpu,
            "render": {
                "width": args.width, "height": args.height, "fps": args.fps,
                "frame_start": args.frame_start, "frame_end": args.frame_end,
                "output_format": "PNG", "output_prefix": "output/frame_",
                "samples": args.samples, "denoise": args.denoise,
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
