#!/usr/bin/env python3
"""Run one isolated Blender/Cycles chunk inside a Runpod worker."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.parse import urlparse


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


def handle_event(event: dict[str, object]) -> dict[str, object]:
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
        _curl_download(bundle_url, input_archive)
        actual_bundle_sha256 = sha256_file(input_archive)
        if actual_bundle_sha256.lower() != expected_bundle_sha256.lower():
            raise ValueError("bundle SHA-256 does not match the submitted digest")

        bundle = root / "bundle"
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

        output = bundle / "output"
        output.mkdir(parents=True, exist_ok=True)
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
            str(chunk["frame_start"]),
            "--frame-end",
            str(chunk["frame_end"]),
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
        _run(command, cwd=bundle, label="Cycles chunk render")

        report_path = output / "render_report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if report.get("engine") != "CYCLES" or report.get("render_executed") is not True:
            raise RuntimeError("Blender report does not prove a completed Cycles render")
        if bool(manifest.get("require_gpu", True)) and report.get("render_device") != "GPU":
            raise RuntimeError("Blender report does not prove GPU rendering")
        _verify_chunk(bundle, chunk["frame_start"], chunk["frame_end"], render["width"], render["height"])

        output_archive = root / "output.tar.gz"
        archive_directory(output, output_archive)
        _curl_upload(output_upload_url, output_archive)
        return {
            "schema_version": 1,
            "chunk_id": chunk_id,
            "chunk_index": chunk["index"],
            "frame_start": chunk["frame_start"],
            "frame_end": chunk["frame_end"],
            "render_device": report.get("render_device"),
            "render_engine": report.get("engine"),
            "archive_sha256": sha256_file(output_archive),
            "archive_size": output_archive.stat().st_size,
            "output_download_url": output_download_url,
        }
