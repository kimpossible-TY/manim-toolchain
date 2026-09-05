#!/usr/bin/env python3
"""Validate the portable input contract for a Runpod Pod render."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from runpod_job_utils import is_sensitive, load_manifest


REQUIRED_FILES = (
    "scene.blend",
    "render_manifest.json",
    "scripts/blender_render.py",
    "scripts/blender_cycles.py",
    "scripts/verify_frame_sequence.py",
)


def validate(bundle: Path) -> list[str]:
    errors: list[str] = []
    try:
        manifest = load_manifest(bundle)
    except ValueError as exc:
        return [str(exc)]
    for relative in REQUIRED_FILES:
        if not (bundle / relative).is_file():
            errors.append(f"missing required bundle file: {relative}")
    if manifest.get("backend") != "runpod-pod":
        errors.append("render manifest backend must be runpod-pod")
    if manifest.get("render_engine") != "CYCLES":
        errors.append("Runpod render manifest must use CYCLES")
    render = manifest.get("render")
    if not isinstance(render, dict):
        errors.append("render manifest render must be an object")
    else:
        for key in ("width", "height", "fps", "frame_end", "samples"):
            if not isinstance(render.get(key), int) or render[key] <= 0:
                errors.append(f"render.{key} must be a positive integer")
        if not isinstance(render.get("frame_start"), int) or render["frame_start"] < 0:
            errors.append("render.frame_start must be a non-negative integer")
        if (
            isinstance(render.get("frame_start"), int)
            and isinstance(render.get("frame_end"), int)
            and render["frame_start"] > render["frame_end"]
        ):
            errors.append("render.frame_start cannot exceed render.frame_end")
    scene_script = manifest.get("scene_script")
    if scene_script is not None and not (bundle / str(scene_script)).is_file():
        errors.append(f"missing scene script: {scene_script}")
    assets = manifest.get("assets", [])
    if not isinstance(assets, list):
        errors.append("assets must be a list")
    else:
        for relative in assets:
            if not isinstance(relative, str):
                errors.append("asset entries must be strings")
                continue
            asset = bundle / relative
            if is_sensitive(Path(relative)) or not asset.is_file():
                errors.append(f"invalid or sensitive asset entry: {relative}")
    for path in bundle.rglob("*"):
        if path.is_file() and is_sensitive(path.relative_to(bundle)):
            errors.append(f"credential-like file is present in bundle: {path.relative_to(bundle)}")
    output = bundle / "output"
    if output.exists() and any(output.iterdir()):
        errors.append("output directory must be empty before submission")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", type=Path, required=True)
    args = parser.parse_args()
    bundle = args.job.expanduser().resolve()
    errors = validate(bundle)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print("RUNPOD_RENDER_JOB_VALIDATION=FAIL")
        return 2
    manifest = json.loads((bundle / "render_manifest.json").read_text(encoding="utf-8"))
    render = manifest["render"]
    print(
        "RUNPOD_RENDER_JOB_VALIDATION=PASS "
        f"frames={render['frame_start']}-{render['frame_end']} "
        "pod=single-gpu"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
