#!/usr/bin/env python3
"""Measure one representative local Blender render without changing its command."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import resource
import subprocess
import time


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frame-count", type=int, help="Optional production-frame estimate")
    parser.add_argument("--report", type=Path, help="Optional JSON benchmark report")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command after --")
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("provide the Blender command after --")
    if args.frame_count is not None and args.frame_count <= 0:
        parser.error("--frame-count must be positive")
    before = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    started = time.perf_counter()
    subprocess.run(command, check=True)
    wall_seconds = time.perf_counter() - started
    peak_rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    rss_unit = "bytes" if platform.system() == "Darwin" else "KiB"
    report: dict[str, object] = {
        "command": command,
        "wall_seconds": wall_seconds,
        "peak_rss": peak_rss,
        "peak_rss_unit": rss_unit,
    }
    if args.frame_count is not None:
        report["estimated_total_seconds"] = wall_seconds * args.frame_count
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"BLENDER_BENCHMARK_SECONDS={wall_seconds:.3f}")
    print(f"BLENDER_BENCHMARK_PEAK_RSS={peak_rss} {rss_unit}")
    if "estimated_total_seconds" in report:
        print(f"BLENDER_BENCHMARK_ESTIMATE_SECONDS={report['estimated_total_seconds']:.3f}")


if __name__ == "__main__":
    main()
