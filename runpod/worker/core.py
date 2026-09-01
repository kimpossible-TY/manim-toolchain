#!/usr/bin/env python3
"""Run one isolated Blender/Cycles chunk inside a Runpod worker."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import selectors
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlparse
from collections.abc import Iterator


SYSTEM_SCRIPTS = Path(os.environ.get("RUNPOD_SCRIPTS_DIR", "/opt/render/scripts"))
LOCAL_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
for scripts_path in (SYSTEM_SCRIPTS, LOCAL_SCRIPTS):
    if str(scripts_path) not in sys.path:
        sys.path.insert(0, str(scripts_path))

from runpod_job_utils import archive_directory, is_sensitive, safe_extract_tar, sha256_file


def _require_https_url(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an HTTPS URL")
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"{field} must be an HTTPS URL")
    return value


def _safe_bundle_file(bundle: Path, relative: object, field: str, *, required: bool = True) -> Path | None:
    if not isinstance(relative, str) or not relative:
        if required:
            raise ValueError(f"manifest {field} must be a relative path")
        return None
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"manifest {field} must be a relative path")
    resolved = (bundle / path).resolve()
    if not resolved.is_relative_to(bundle.resolve()):
        raise ValueError(f"manifest {field} escapes the bundle")
    if required and not resolved.is_file():
        raise ValueError(f"manifest {field} does not exist: {relative}")
    return resolved


def _run(command: list[str], *, cwd: Path, label: str) -> None:
    completed = subprocess.run(command, cwd=cwd, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"{label} failed with exit code {completed.returncode}")


_FRAME_FILE_RE = re.compile(r"^frame_(\d+)\.png$")
_SAMPLE_PROGRESS_RE = re.compile(
    r"(?:Rendered|Rendering)\s+(\d+)(?:\s*/\s*(\d+))?\s+samples", re.IGNORECASE
)
_BLENDER_CYCLES_PROGRESS_RE = re.compile(
    r"BLENDER_CYCLES_PROGRESS\s+frame=(\d+)\s+sample=(\d+)/(\d+)"
)


def _frame_progress(output: Path, frame_start: int, frame_end: int) -> dict[str, object]:
    """Report progress from completed PNGs, which is stable across Blender builds."""

    frames = sorted(
        int(match.group(1))
        for path in output.glob("frame_*.png")
        if (match := _FRAME_FILE_RE.fullmatch(path.name))
        and frame_start <= int(match.group(1)) <= frame_end
        and path.is_file()
        and path.stat().st_size > 0
    )
    total = frame_end - frame_start + 1
    completed = len(frames)
    current_frame = min(frame_start + completed, frame_end)
    return {
        "phase": "render",
        "status": "IN_PROGRESS",
        "frame": current_frame,
        "frame_start": frame_start,
        "frame_end": frame_end,
        "frames_completed": completed,
        "frames_total": total,
        "percent": round(completed / total * 100, 1),
    }


def _progress_from_line(
    line: str,
    *,
    output: Path,
    frame_start: int,
    frame_end: int,
) -> dict[str, object] | None:
    """Add optional Cycles sample data to the durable frame-based progress."""

    match = _SAMPLE_PROGRESS_RE.search(line)
    blender_match = _BLENDER_CYCLES_PROGRESS_RE.search(line)
    saved_match = re.search(r"frame_(\d+)\.png", line)
    if match is None and blender_match is None and saved_match is None:
        return None
    event = _frame_progress(output, frame_start, frame_end)
    if blender_match is not None:
        current_frame = int(blender_match.group(1))
        if frame_start <= current_frame <= frame_end:
            event["frame"] = current_frame
        event["samples_completed"] = int(blender_match.group(2))
        event["samples_total"] = int(blender_match.group(3))
        sample_ratio = min(
            int(blender_match.group(2)) / max(int(blender_match.group(3)), 1), 1.0
        )
        completed = int(event["frames_completed"])
        total_frames = int(event["frames_total"])
        if completed < total_frames:
            event["percent"] = round(
                (completed + sample_ratio) / total_frames * 100, 1
            )
    if saved_match is not None:
        saved_frame = int(saved_match.group(1))
        if frame_start <= saved_frame <= frame_end:
            event["frame"] = saved_frame
            event["frames_completed"] = max(
                int(event["frames_completed"]), saved_frame - frame_start + 1
            )
            total = int(event["frames_total"])
            event["percent"] = round(int(event["frames_completed"]) / total * 100, 1)
    if match is not None and blender_match is None:
        event["samples_completed"] = int(match.group(1))
        if match.group(2) is not None:
            samples_total = int(match.group(2))
            event["samples_total"] = samples_total
            sample_ratio = min(int(match.group(1)) / max(samples_total, 1), 1.0)
            completed = int(event["frames_completed"])
            total_frames = int(event["frames_total"])
            if completed < total_frames:
                event["percent"] = round(
                    (completed + sample_ratio) / total_frames * 100, 1
                )
    return event


def _tag_progress(event: dict[str, object]) -> dict[str, object]:
    return {"schema_version": 1, "type": "progress", **event}


def _run_with_progress(
    command: list[str],
    *,
    cwd: Path,
    label: str,
    output: Path,
    frame_start: int,
    frame_end: int,
) -> Iterator[dict[str, object]]:
    """Run Blender while forwarding logs and polling completed PNG frames."""

    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    selector = selectors.DefaultSelector()
    if process.stdout is not None:
        selector.register(process.stdout, selectors.EVENT_READ)
    last_signature: tuple[object, ...] | None = None
    last_emit = 0.0
    try:
        while True:
            for selected, _ in selector.select(timeout=0.5):
                stream = selected.fileobj
                line = stream.readline()
                if not line:
                    selector.unregister(stream)
                    continue
                print(line, end="", flush=True)
                event = _progress_from_line(
                    line,
                    output=output,
                    frame_start=frame_start,
                    frame_end=frame_end,
                )
                if event is not None:
                    signature = tuple(sorted(event.items()))
                    if signature != last_signature:
                        last_signature = signature
                        last_emit = time.monotonic()
                        yield _tag_progress(event)

            now = time.monotonic()
            event = _frame_progress(output, frame_start, frame_end)
            signature = tuple(sorted(event.items()))
            if signature != last_signature and (
                event["frames_completed"] != 0 or now - last_emit >= 2
            ):
                last_signature = signature
                last_emit = now
                yield _tag_progress(event)
            if process.poll() is not None and not selector.get_map():
                break
    finally:
        selector.close()
    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(f"{label} failed with exit code {return_code}")


def _curl_download(url: str, destination: Path) -> None:
    completed = subprocess.run(
        [
            "curl",
            "--fail",
            "--silent",
            "--show-error",
            "--location",
            "--max-time",
            "3600",
            "--output",
            str(destination),
            url,
        ],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"bundle download failed with exit code {completed.returncode}")


def _curl_upload(url: str, source: Path) -> None:
    completed = subprocess.run(
        [
            "curl",
            "--fail",
            "--silent",
            "--show-error",
            "--location",
            "--upload-file",
            str(source),
            url,
        ],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"output upload failed with exit code {completed.returncode}")


def _manifest_and_chunk(event_input: dict[str, object], bundle: Path) -> tuple[dict[str, object], dict[str, object]]:
    import runpod_job_utils

    manifest = runpod_job_utils.load_manifest(bundle)
    if manifest.get("backend") != "runpod-serverless":
        raise ValueError("bundle backend must be runpod-serverless")
    if manifest.get("render_engine") != "CYCLES":
        raise ValueError("Runpod worker only accepts CYCLES bundles")
    for path in bundle.rglob("*"):
        if path.is_file() and is_sensitive(path.relative_to(bundle)):
            raise ValueError(f"credential-like file is present in bundle: {path.name}")
    _safe_bundle_file(bundle, manifest.get("scene"), "scene")
    _safe_bundle_file(bundle, "scripts/blender_render.py", "blender_render")
    _safe_bundle_file(bundle, "scripts/blender_cycles.py", "blender_cycles")
    _safe_bundle_file(bundle, "scripts/verify_frame_sequence.py", "frame_verifier")
    output = bundle / "output"
    if output.exists() and not output.is_dir():
        raise ValueError("bundle output must be a directory")
    if output.exists() and any(output.iterdir()):
        raise ValueError("bundle output must be empty before rendering")
    chunk = event_input.get("chunk")
    if not isinstance(chunk, dict):
        raise ValueError("input.chunk must be an object")
    for key in ("index", "frame_start", "frame_end"):
        if not isinstance(chunk.get(key), int):
            raise ValueError(f"input.chunk.{key} must be an integer")
    render = manifest.get("render")
    if not isinstance(render, dict):
        raise ValueError("manifest render must be an object")
    frame_start = render.get("frame_start")
    frame_end = render.get("frame_end")
    if not isinstance(frame_start, int) or not isinstance(frame_end, int):
        raise ValueError("manifest frame range is invalid")
    if not frame_start <= chunk["frame_start"] <= chunk["frame_end"] <= frame_end:
        raise ValueError("chunk frame range is outside the manifest frame range")
    return manifest, chunk


def _verify_chunk(bundle: Path, start: int, end: int, width: int, height: int) -> None:
    _run(
        [
            sys.executable,
            str(bundle / "scripts" / "verify_frame_sequence.py"),
            "--directory",
            str(bundle / "output"),
            "--prefix",
            "frame_",
            "--frame-start",
            str(start),
            "--frame-end",
            str(end),
            "--width",
            str(width),
            "--height",
            str(height),
        ],
        cwd=bundle,
        label="frame verification",
    )


def _progress_event(chunk_id: str, phase: str, **fields: object) -> dict[str, object]:
    return {
        "schema_version": 1,
        "type": "progress",
        "chunk_id": chunk_id,
        "phase": phase,
        "status": "IN_PROGRESS",
        **fields,
    }


def handle_event(event: dict[str, object]) -> Iterator[dict[str, object]]:
    """Runpod handler entry point; accepts a job object or its input object."""

    event_input = event.get("input", event)
    if not isinstance(event_input, dict):
        raise ValueError("Runpod job input must be an object")
    schema_version = event_input.get("schema_version", 1)
    if schema_version != 1:
        raise ValueError(f"unsupported Runpod job schema: {schema_version}")
    chunk_id = event_input.get("chunk_id")
    if not isinstance(chunk_id, str) or not chunk_id:
        raise ValueError("input.chunk_id is required")
    bundle_url = _require_https_url(event_input.get("bundle_url"), "bundle_url")
    output_upload_url = _require_https_url(
        event_input.get("output_upload_url"), "output_upload_url"
    )
    output_download_url = event_input.get("output_download_url")
    if output_download_url is not None:
        output_download_url = _require_https_url(output_download_url, "output_download_url")
    expected_bundle_sha256 = event_input.get("bundle_sha256")
    if not isinstance(expected_bundle_sha256, str) or len(expected_bundle_sha256) != 64:
        raise ValueError("bundle_sha256 must be a 64-character hexadecimal digest")

    with tempfile.TemporaryDirectory(prefix="runpod-render-") as temp_dir:
        root = Path(temp_dir)
        input_archive = root / "input.tar.gz"
        yield _progress_event(chunk_id, "download", message="downloading bundle")
        _curl_download(bundle_url, input_archive)
        actual_bundle_sha256 = sha256_file(input_archive)
        if actual_bundle_sha256.lower() != expected_bundle_sha256.lower():
            raise ValueError("bundle SHA-256 does not match the submitted digest")
        yield _progress_event(chunk_id, "download", message="bundle verified")

        bundle = root / "bundle"
        yield _progress_event(chunk_id, "extract", message="extracting bundle")
        safe_extract_tar(input_archive, bundle)
        # The client archives the bundle under its directory name. Accept only a
        # single top-level directory so the worker cannot accidentally render a
        # caller-selected path.
        children = [child for child in bundle.iterdir()]
        if len(children) != 1 or not children[0].is_dir():
            raise ValueError("input archive must contain exactly one bundle directory")
        bundle = children[0]
        manifest, chunk = _manifest_and_chunk(event_input, bundle)
        render = manifest["render"]
        assert isinstance(render, dict)
        scene = _safe_bundle_file(bundle, manifest.get("scene"), "scene")
        script = _safe_bundle_file(
            bundle, manifest.get("scene_script"), "scene_script", required=False
        )
        assert scene is not None
        blender_bin = os.environ.get("BLENDER_BIN", "/opt/blender/blender")
        if not Path(blender_bin).is_file():
            raise RuntimeError(f"Blender binary is not available at {blender_bin}")
        common = [
            blender_bin,
            "--background",
            "--python",
            str(bundle / "scripts" / "blender_render.py"),
            "--",
        ]
        if bool(event_input.get("validate_assets", False)) and chunk["index"] == 0:
            yield _progress_event(chunk_id, "asset_validation", message="validating assets")
            validation_report = bundle / "output" / "asset_validation_report.json"
            validation = common + [
                "--mode",
                "validate",
                "--scene",
                str(scene),
                "--report",
                str(validation_report),
                "--validate-assets",
                "--require-portable-assets",
            ]
            if script is not None:
                validation.extend(("--scene-script", str(script)))
            _run(validation, cwd=bundle, label="asset validation")
            yield _progress_event(chunk_id, "asset_validation", message="asset validation passed")

        output = bundle / "output"
        output.mkdir(parents=True, exist_ok=True)
        frame_start = int(chunk["frame_start"])
        frame_end = int(chunk["frame_end"])
        yield _progress_event(
            chunk_id,
            "render",
            frame_start=frame_start,
            frame_end=frame_end,
            frames_completed=0,
            frames_total=frame_end - frame_start + 1,
            percent=0.0,
        )
        # One request owns one GPU and one Blender process. Horizontal chunking
        # is the responsibility of the client/orchestrator.
        command = common + [
            "--mode",
            "render",
            "--engine",
            "cycles",
            "--scene",
            str(scene),
            "--output",
            str(output / "frame_"),
            "--report",
            str(output / "render_report.json"),
            "--width",
            str(render["width"]),
            "--height",
            str(render["height"]),
            "--fps",
            str(render["fps"]),
            "--frame-start",
            str(frame_start),
            "--frame-end",
            str(frame_end),
            "--samples",
            str(render["samples"]),
            "--device",
            str(manifest.get("requested_compute_device", "auto")),
            "--denoise" if bool(render.get("denoise", True)) else "--no-denoise",
        ]
        if bool(manifest.get("require_gpu", True)):
            command.append("--require-gpu")
        if script is not None:
            command.extend(("--scene-script", str(script)))
        yield from _run_with_progress(
            command,
            cwd=bundle,
            label="Cycles chunk render",
            output=output,
            frame_start=frame_start,
            frame_end=frame_end,
        )

        report_path = output / "render_report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if report.get("engine") != "CYCLES" or report.get("render_executed") is not True:
            raise RuntimeError("Blender report does not prove a completed Cycles render")
        if bool(manifest.get("require_gpu", True)) and report.get("render_device") != "GPU":
            raise RuntimeError("Blender report does not prove GPU rendering")
        yield _progress_event(chunk_id, "verify", message="verifying rendered frames")
        _verify_chunk(bundle, frame_start, frame_end, render["width"], render["height"])
        yield _progress_event(chunk_id, "verify", message="frame verification passed")

        output_archive = root / "output.tar.gz"
        archive_directory(output, output_archive)
        yield _progress_event(chunk_id, "upload", message="uploading output archive")
        _curl_upload(output_upload_url, output_archive)
        yield _progress_event(chunk_id, "upload", message="output archive uploaded")
        yield {
            "schema_version": 1,
            "type": "result",
            "chunk_id": chunk_id,
            "chunk_index": chunk["index"],
            "frame_start": frame_start,
            "frame_end": frame_end,
            "render_device": report.get("render_device"),
            "render_engine": report.get("engine"),
            "archive_sha256": sha256_file(output_archive),
            "archive_size": output_archive.stat().st_size,
            "output_download_url": output_download_url,
        }
