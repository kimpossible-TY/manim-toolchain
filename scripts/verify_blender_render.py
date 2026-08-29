#!/usr/bin/env python3
"""Verify a real Blender-rendered PNG and its runner report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--engine", choices=("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT", "CYCLES"), required=True)
    parser.add_argument("--width", type=int, required=True)
    parser.add_argument("--height", type=int, required=True)
    args = parser.parse_args()

    if not args.image.is_file() or args.image.stat().st_size == 0:
        raise SystemExit(f"Missing or empty Blender image: {args.image}")
    report = json.loads(args.report.read_text(encoding="utf-8"))
    if not report.get("render_executed") or report.get("engine") != args.engine:
        raise SystemExit(f"Unexpected Blender report: {report}")
    if args.engine == "CYCLES" and report.get("render_device") not in {"CPU", "GPU"}:
        raise SystemExit(f"Cycles render device was not recorded: {report.get('render_device')}")
    raw = subprocess.run(
        [
            "ffmpeg", "-v", "error", "-i", str(args.image), "-frames:v", "1",
            "-f", "rawvideo", "-pix_fmt", "rgba", "pipe:1",
        ],
        check=True,
        capture_output=True,
    ).stdout
    frame = np.frombuffer(raw, dtype=np.uint8)
    expected_size = args.width * args.height * 4
    if frame.size != expected_size:
        raise SystemExit(
            f"Unexpected Blender frame dimensions: {frame.size} bytes, expected {expected_size}"
        )
    standard_deviation = float(frame.std())
    if standard_deviation < 2.0:
        raise SystemExit(f"Blender image is uniformly blank: std={standard_deviation:.3f}")
    print(f"BLENDER_VERIFIED_ENGINE={report['engine']}")
    print(f"BLENDER_VERIFIED_DEVICE={report['render_device']}")
    print(f"BLENDER_FRAME_STD={standard_deviation:.3f}")
    print("BLENDER_IMAGE_VERIFICATION=PASS")


if __name__ == "__main__":
    main()
