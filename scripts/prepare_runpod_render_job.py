#!/usr/bin/env python3
"""Create a portable Blender/Cycles bundle for Runpod Serverless chunks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from runpod_job_utils import copy_asset, copy_file


TOOLCHAIN_DIR = Path(__file__).resolve().parents[1]
RUNNER_FILES = (
    "blender_render.py",
    "blender_cycles.py",
    "verify_frame_sequence.py",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", type=Path, required=True, help="Source .blend file")
    parser.add_argument("--scene-script", type=Path)
    parser.add_argument("--asset-dir", type=Path, action="append", default=[])
    parser.add_argument("--asset-file", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True, help="New local bundle directory")
    parser.add_argument("--width", type=int, required=True)
    parser.add_argument("--height", type=int, required=True)
    parser.add_argument("--fps", type=int, required=True)
    parser.add_argument("--frame-start", type=int, required=True)
    parser.add_argument("--frame-end", type=int, required=True)
    parser.add_argument("--chunk-size", type=int, default=60)
    parser.add_argument("--samples", type=int, default=128)
    parser.add_argument("--denoise", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument(
        "--device",
        choices=("auto", "cpu", "gpu", "cuda", "optix", "metal", "hip", "oneapi"),
        default="auto",
    )
    parser.add_argument(
        "--require-gpu",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Fail the remote job instead of silently falling back to CPU (default: on)",
    )
    parser.add_argument(
        "--validate-source",
        action="store_true",
        help="Run local Blender portability validation before creating the bundle",
    )
    args = parser.parse_args()
    for name in ("width", "height", "fps", "chunk_size", "samples"):
        if getattr(args, name) <= 0:
            parser.error(f"--{name.replace('_', '-')} must be positive")
    if args.frame_start > args.frame_end:
        parser.error("--frame-start cannot exceed --frame-end")
    if args.frame_start < 0:
        parser.error("--frame-start cannot be negative")
    return args


def resolved_file(path: Path, description: str, suffix: str | None = None) -> Path:
    candidate = path.expanduser()
    if candidate.is_symlink():
        raise ValueError(f"{description} must not be a symlink: {candidate}")
    resolved = candidate.resolve()
    if not resolved.is_file():
        raise ValueError(f"{description} is not a file: {resolved}")
    if suffix is not None and resolved.suffix.lower() != suffix:
        raise ValueError(f"{description} must have the {suffix} suffix: {resolved}")
    return resolved


def blender_binary() -> str:
    configured = shutil.which("blender")
    if configured:
        return configured
    app_binary = Path("/Applications/Blender.app/Contents/MacOS/Blender")
    if app_binary.is_file():
        return str(app_binary)
    raise RuntimeError(
        "Blender is required only when --validate-source is used; install Blender or omit that flag"
    )


def validate_source(bundle: Path, manifest: dict[str, object]) -> None:
    render = manifest["render"]
    assert isinstance(render, dict)
    report = bundle / "source_validation_report.json"
    command = [
        blender_binary(),
        "--background",
        "--python",
        str(bundle / "blender_render.py"),
        "--",
        "--mode",
        "validate",
        "--scene",
        str(bundle / "scene.blend"),
        "--report",
        str(report),
        "--validate-assets",
        "--require-portable-assets",
    ]
    if manifest["scene_script"]:
        command.extend(("--scene-script", str(bundle / "scene.py")))
    completed = subprocess.run(command, cwd=bundle, check=False)
    if completed.returncode != 0 or not report.is_file():
        raise RuntimeError(
            "Local Blender source validation failed. The Runpod worker will still validate the "
            "bundle when --validate-source is omitted."
        )
    manifest["source_validation"] = {
        "checked": True,
        "portable": True,
        "report": report.name,
    }


def prepare(args: argparse.Namespace) -> Path:
    scene = resolved_file(args.scene, "--scene", ".blend")
    scene_script = (
        resolved_file(args.scene_script, "--scene-script", ".py") if args.scene_script else None
    )
    output = args.output.expanduser().resolve()
    if output.exists():
        raise ValueError(f"Refusing to overwrite existing bundle: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, object] = {
        "format_version": 2,
        "backend": "runpod-serverless",
        "scene": "scene.blend",
        "scene_script": "scene.py" if scene_script else None,
        "assets": [],
        "render_engine": "CYCLES",
        "requested_compute_device": args.device,
        "require_gpu": args.require_gpu,
        "render": {
            "width": args.width,
            "height": args.height,
            "fps": args.fps,
            "frame_start": args.frame_start,
            "frame_end": args.frame_end,
            "output_format": "PNG",
            "output_prefix": "output/frame_",
            "samples": args.samples,
            "denoise": args.denoise,
            "chunk_size": args.chunk_size,
        },
        "source_validation": {"checked": False, "portable": None},
        "remote_authorization_required": True,
    }

    with tempfile.TemporaryDirectory(prefix=f"{output.name}.", dir=output.parent) as temp_dir:
        bundle = Path(temp_dir)
        (bundle / "output").mkdir()
        copy_file(scene, bundle / "scene.blend")
        if scene_script:
            copy_file(scene_script, bundle / "scene.py")
        copied_assets: list[str] = []
        for asset_dir in args.asset_dir:
            copy_asset(asset_dir, bundle / "assets", copied_assets)
        for asset_file in args.asset_file:
            copy_asset(asset_file, bundle / "assets", copied_assets)
        manifest["assets"] = sorted(copied_assets)

        scripts_dir = bundle / "scripts"
        for runner_file in RUNNER_FILES:
            copy_file(TOOLCHAIN_DIR / "scripts" / runner_file, scripts_dir / runner_file)

        if args.validate_source:
            validate_source(bundle, manifest)
        (bundle / "render_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        shutil.move(str(bundle), str(output))
    return output


def main() -> int:
    args = parse_args()
    try:
        output = prepare(args)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"runpod bundle error: {exc}", file=sys.stderr)
        return 2
    print(f"RUNPOD_BUNDLE={output}")
    print(f"RUNPOD_MANIFEST={output / 'render_manifest.json'}")
    print("Next: upload the bundle as a tar.gz to object storage, then run visual-runpod submit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
