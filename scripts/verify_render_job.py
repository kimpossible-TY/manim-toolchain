#!/usr/bin/env python3
"""Validate the local structure and safety boundary of a prepared render job."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_FILES = {
    "scene.blend",
    "blender_render.py",
    "blender_cycles.py",
    "render_manifest.json",
    "bootstrap.sh",
    "colab_commands.sh",
    "run_colab_job.py",
}
FORBIDDEN_NAMES = {".env", ".netrc", "id_rsa", "id_ed25519"}
FORBIDDEN_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--frame-start", type=int, required=True)
    parser.add_argument("--frame-end", type=int, required=True)
    args = parser.parse_args()
    job = args.job.resolve()
    missing = sorted(name for name in REQUIRED_FILES if not (job / name).is_file())
    if missing:
        raise SystemExit("Missing render-job files: " + ", ".join(missing))
    manifest = json.loads((job / "render_manifest.json").read_text(encoding="utf-8"))
    if manifest.get("remote_authorization_required") is not True:
        raise SystemExit("Render job lacks explicit remote authorization boundary")
    render = manifest.get("render", {})
    if render.get("output_format") != "PNG" or render.get("frame_start") != args.frame_start:
        raise SystemExit("Render manifest has unexpected frame output settings")
    if render.get("frame_end") != args.frame_end:
        raise SystemExit("Render manifest has unexpected frame range")
    for asset in manifest.get("assets", []):
        asset_path = Path(asset)
        if asset_path.is_absolute() or ".." in asset_path.parts:
            raise SystemExit(f"Render manifest contains non-portable asset path: {asset}")
    for path in job.rglob("*"):
        if path.is_file() and (path.name.lower() in FORBIDDEN_NAMES or path.suffix.lower() in FORBIDDEN_SUFFIXES):
            raise SystemExit(f"Render job contains credential-like file: {path.relative_to(job)}")
    commands = (job / "colab_commands.sh").read_text(encoding="utf-8")
    if "Authorization-required" not in commands or "colab new" not in commands:
        raise SystemExit("Colab commands do not document their allocation boundary")
    if "colab upload" not in commands or "colab download" not in commands or "colab stop" not in commands:
        raise SystemExit("Colab commands do not provide a resumable upload/download/stop flow")
    if any((job / "output").iterdir()):
        raise SystemExit("Prepared render job unexpectedly contains rendered output")
    print(f"RENDER_JOB_VERIFIED={job}")
    print("RENDER_JOB_VALIDATION=PASS")


if __name__ == "__main__":
    main()
