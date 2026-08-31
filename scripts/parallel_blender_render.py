#!/usr/bin/env python3
"""Execute parallel Blender render workers across frame chunks with live streaming.

Spawns concurrent Blender worker processes dividing the total frame range,
streams non-blocking progress logs from all workers with worker-ID prefixes,
and consolidates individual worker reports into a single render report.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import threading
from typing import Any


def stream_worker_output(process: subprocess.Popen, worker_id: int) -> None:
    assert process.stdout is not None
    for line in iter(process.stdout.readline, ""):
        line_s = line.strip()
        if not line_s:
            continue
        if any(
            token in line_s
            for token in (
                "Saved:",
                "Fra:",
                "Time:",
                "Error",
                "Finished",
                "BLENDER_",
                "Sample",
                "Rendering",
            )
        ):
            print(f"[Worker {worker_id}] {line_s}", flush=True)


def run_parallel_render(
    blender_bin: str,
    output_prefix: str,
    report_file: str,
    *,
    scene: str | None = None,
    scene_script: str | None = None,
    engine: str = "cycles",
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
    samples: int | None = None,
    device: str = "auto",
    denoise: bool = True,
    frame_start: int = 1,
    frame_end: int = 1,
    num_workers: int = 4,
) -> dict[str, Any]:
    total_frames = max(1, frame_end - frame_start + 1)
    actual_workers = max(1, min(num_workers, total_frames))
    chunk_size = (total_frames + actual_workers - 1) // actual_workers

    out_p = Path(output_prefix)
    out_dir = out_p.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    report_p = Path(report_file)
    report_p.parent.mkdir(parents=True, exist_ok=True)

    script_dir = Path(__file__).resolve().parent
    render_helper = script_dir / "blender_render.py"

    print(
        f"Starting {engine.upper()} parallel render: frames {frame_start}..{frame_end} ({total_frames} frames) "
        f"across {actual_workers} workers (~{chunk_size} frames/worker)...",
        flush=True,
    )

    processes: list[subprocess.Popen] = []
    threads: list[threading.Thread] = []
    worker_reports: list[Path] = []

    for w_idx in range(actual_workers):
        w_start = frame_start + w_idx * chunk_size
        w_end = min(frame_end, w_start + chunk_size - 1)
        if w_start > frame_end:
            break

        w_report = out_dir / f".report_w{w_idx:02d}.json"
        worker_reports.append(w_report)

        cmd: list[str] = [
            blender_bin,
            "--background",
        ]
        if scene and not scene_script:
            cmd.append(scene)

        cmd.extend([
            "--python",
            str(render_helper),
            "--",
            "--mode",
            "render",
            "--engine",
            engine,
            "--output",
            output_prefix,
            "--report",
            str(w_report),
            "--width",
            str(width),
            "--height",
            str(height),
            "--fps",
            str(fps),
            "--frame-start",
            str(w_start),
            "--frame-end",
            str(w_end),
            "--device",
            device,
        ])
        if samples is not None:
            cmd.extend(("--samples", str(samples)))
        if denoise:
            cmd.append("--denoise")
        else:
            cmd.append("--no-denoise")
        if scene_script:
            cmd.extend(("--scene-script", scene_script))

        p = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        processes.append(p)

        t = threading.Thread(target=stream_worker_output, args=(p, w_idx + 1))
        t.daemon = True
        t.start()
        threads.append(t)

    # Wait for all workers to complete
    failures: list[int] = []
    for idx, p in enumerate(processes):
        ret = p.wait()
        if ret != 0:
            failures.append(ret)

    for t in threads:
        t.join(timeout=2.0)

    if failures:
        raise RuntimeError(f"Parallel render encountered {len(failures)} worker failure(s): exit codes {failures}")

    # Consolidate reports
    detected_device = "UNKNOWN"
    for r_path in worker_reports:
        if r_path.is_file() and r_path.stat().st_size > 0:
            try:
                data = json.loads(r_path.read_text(encoding="utf-8"))
                if data.get("render_device"):
                    detected_device = str(data["render_device"])
                    break
            except Exception:
                pass
            finally:
                r_path.unlink(missing_ok=True)

    consolidated: dict[str, Any] = {
        "engine": engine.upper(),
        "render_executed": True,
        "render_device": detected_device,
        "frame_start": frame_start,
        "frame_end": frame_end,
        "num_workers": actual_workers,
        "width": width,
        "height": height,
        "fps": fps,
    }
    if samples is not None:
        consolidated["samples"] = samples

    report_p.write_text(json.dumps(consolidated, indent=2), encoding="utf-8")
    print(f"All {actual_workers} parallel render worker(s) finished successfully!", flush=True)
    return consolidated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender-bin", default="blender")
    parser.add_argument("--scene", help="Optional .blend file")
    parser.add_argument("--scene-script", help="Optional Python scene script")
    parser.add_argument("--output", required=True, help="Output PNG sequence prefix")
    parser.add_argument("--report", required=True, help="Output JSON report file")
    parser.add_argument("--engine", choices=("cycles", "eevee"), default="cycles")
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--samples", type=int)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--denoise", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--frame-start", type=int, default=1)
    parser.add_argument("--frame-end", type=int, default=1)
    parser.add_argument("--workers", type=int, default=4)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_parallel_render(
        blender_bin=args.blender_bin,
        output_prefix=args.output,
        report_file=args.report,
        scene=args.scene,
        scene_script=args.scene_script,
        engine=args.engine,
        width=args.width,
        height=args.height,
        fps=args.fps,
        samples=args.samples,
        device=args.device,
        denoise=args.denoise,
        frame_start=args.frame_start,
        frame_end=args.frame_end,
        num_workers=args.workers,
    )
