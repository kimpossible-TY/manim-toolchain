#!/usr/bin/env python3
"""Submit, monitor, and merge chunked Runpod Serverless render jobs.

The client uses only Python's standard library. Object-storage URLs are
presigned URLs supplied by the caller; they are stored in the local jobs file
and are never printed.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from runpod_job_utils import (
    archive_directory,
    chunk_ranges,
    load_manifest,
    safe_extract_tar,
    sha256_file,
)
from r2_storage import R2Storage
from verify_runpod_render_job import validate as validate_bundle


TERMINAL_STATUSES = {"COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT"}


class RunpodError(RuntimeError):
    pass


def _runpod_api_key() -> str:
    """Resolve the API key without printing or persisting it."""

    from_environment = os.environ.get("RUNPOD_API_KEY", "")
    if from_environment:
        return from_environment

    config_path = Path(
        os.environ.get("RUNPOD_CONFIG_FILE", str(Path.home() / ".runpod" / "config.toml"))
    ).expanduser()
    try:
        with config_path.open("rb") as config_file:
            config = tomllib.load(config_file)
    except (OSError, tomllib.TOMLDecodeError):
        return ""

    def find_key(value: object) -> str:
        if isinstance(value, dict):
            for key in ("RUNPOD_API_KEY", "runpod_api_key", "api_key"):
                candidate = value.get(key)
                if isinstance(candidate, str) and candidate:
                    return candidate
            for nested in value.values():
                found = find_key(nested)
                if found:
                    return found
        return ""

    return find_key(config)


def _https_url(value: object, field: str) -> str:
    from urllib.parse import urlparse

    if not isinstance(value, str):
        raise ValueError(f"{field} must be an HTTPS URL")
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"{field} must be an HTTPS URL")
    return value


def _atomic_write_json(path: Path, value: dict[str, object]) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.chmod(0o600)
    os.replace(temporary, path)
    path.chmod(0o600)


def _load_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.expanduser().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RunpodError(f"could not read jobs file: {path}") from exc
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise RunpodError(f"unsupported jobs file: {path}")
    return value


class RunpodApi:
    def __init__(self, endpoint_id: str, api_key: str, base_url: str) -> None:
        if not endpoint_id:
            raise RunpodError("RUNPOD_ENDPOINT_ID or --endpoint-id is required")
        if not api_key:
            raise RunpodError("RUNPOD_API_KEY is required")
        self.endpoint_id = endpoint_id
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def request(self, method: str, path: str, payload: dict[str, object] | None = None) -> dict[str, object]:
        url = f"{self.base_url}/{quote(self.endpoint_id, safe='')}{path}"
        data = None
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=60) as response:
                value = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise RunpodError(f"Runpod API returned HTTP {exc.code} for {method} {path}") from exc
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise RunpodError(f"Runpod API request failed for {method} {path}") from exc
        if not isinstance(value, dict):
            raise RunpodError(f"Runpod API returned a non-object for {method} {path}")
        return value

    def submit(self, payload: dict[str, object], policy: dict[str, int]) -> dict[str, object]:
        return self.request("POST", "/run", {"input": payload, "policy": policy})

    def status(self, job_id: str) -> dict[str, object]:
        return self.request("GET", f"/status/{quote(job_id, safe='')}")


def _upload_with_curl(url: str, source: Path) -> None:
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
        raise RunpodError(f"input bundle upload failed with exit code {completed.returncode}")


def _download_file(url: str, destination: Path) -> None:
    try:
        with urlopen(Request(url, method="GET"), timeout=3600) as response, destination.open("wb") as output:
            shutil.copyfileobj(response, output, length=1024 * 1024)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise RunpodError("output archive download failed") from exc


def _delete_with_curl(url: str) -> None:
    completed = subprocess.run(
        ["curl", "--fail", "--silent", "--show-error", "--location", "--request", "DELETE", url],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        raise RunpodError(f"R2 object deletion failed with exit code {completed.returncode}")


def _output_urls(args: argparse.Namespace, chunk_id: str, index: int, start: int, end: int) -> tuple[str, str | None]:
    upload_template = getattr(args, "output_upload_url_template", None)
    download_template = getattr(args, "output_download_url_template", None)
    supplied = [bool(args.output_url), bool(args.output_url_template), bool(args.output_url_file), bool(upload_template)]
    if sum(supplied) != 1:
        raise RunpodError(
            "provide exactly one output URL mode: --output-url, --output-url-template, "
            "--output-upload-url-template, or --output-url-file"
        )
    if download_template and not upload_template:
        raise RunpodError("--output-download-url-template requires --output-upload-url-template")
    if args.output_url:
        if args.chunk_count != 1:
            raise RunpodError("--output-url is only safe for a single chunk; use a template or URL map")
        upload = _https_url(args.output_url, "--output-url")
        return upload, upload
    if args.output_url_template:
        try:
            upload = args.output_url_template.format(
                chunk_id=chunk_id, index=index, frame_start=start, frame_end=end
            )
        except (KeyError, ValueError) as exc:
            raise RunpodError("invalid --output-url-template placeholder") from exc
        upload = _https_url(upload, "--output-url-template")
        return upload, upload
    if upload_template:
        if not download_template:
            raise RunpodError("--output-upload-url-template requires --output-download-url-template")
        try:
            upload = upload_template.format(
                chunk_id=chunk_id, index=index, frame_start=start, frame_end=end
            )
            download = download_template.format(
                chunk_id=chunk_id, index=index, frame_start=start, frame_end=end
            )
        except (KeyError, ValueError) as exc:
            raise RunpodError("invalid output URL template placeholder") from exc
        return _https_url(upload, "--output-upload-url-template"), _https_url(
            download, "--output-download-url-template"
        )
    mapping_path = Path(args.output_url_file).expanduser().resolve()
    try:
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RunpodError(f"could not read output URL map: {mapping_path}") from exc
    if not isinstance(mapping, dict):
        raise RunpodError("output URL map must be a JSON object")
    entry = mapping.get(chunk_id, mapping.get(str(index)))
    if isinstance(entry, str):
        upload = _https_url(entry, f"output URL map entry {chunk_id}")
        return upload, upload
    if isinstance(entry, dict):
        upload = _https_url(entry.get("upload"), f"output URL map upload {chunk_id}")
        download = entry.get("download")
        return upload, _https_url(download, f"output URL map download {chunk_id}") if download else None
    raise RunpodError(f"output URL map has no entry for {chunk_id}")


def _chunk_records(manifest: dict[str, object], chunk_size: int) -> list[dict[str, object]]:
    render = manifest.get("render")
    if not isinstance(render, dict):
        raise RunpodError("manifest render must be an object")
    start, end = render.get("frame_start"), render.get("frame_end")
    if not isinstance(start, int) or not isinstance(end, int):
        raise RunpodError("manifest frame range is invalid")
    records = []
    for index, (frame_start, frame_end) in enumerate(chunk_ranges(start, end, chunk_size)):
        records.append(
            {
                "chunk_id": f"chunk-{index:04d}-{frame_start:06d}-{frame_end:06d}",
                "index": index,
                "frame_start": frame_start,
                "frame_end": frame_end,
            }
        )
    return records


def _state_path(bundle: Path, requested: str | None) -> Path:
    return (
        Path(requested).expanduser().resolve()
        if requested
        else bundle.parent / f"{bundle.name}.runpod.json"
    )


def _api_from_args(args: argparse.Namespace, state: dict[str, object] | None = None) -> RunpodApi:
    state_endpoint_id = str(state.get("endpoint_id", "")) if state else ""
    state_base_url = str(state.get("api_base_url", "")) if state else ""
    endpoint_id = args.endpoint_id or state_endpoint_id or os.environ.get("RUNPOD_ENDPOINT_ID", "")
    base_url = args.api_base_url or state_base_url or os.environ.get(
        "RUNPOD_API_BASE_URL", "https://api.runpod.ai/v2"
    )
    return RunpodApi(endpoint_id, _runpod_api_key(), base_url)


def submit(args: argparse.Namespace) -> int:
    bundle = args.bundle.expanduser().resolve()
    errors = validate_bundle(bundle)
    if errors:
        raise RunpodError("bundle validation failed: " + "; ".join(errors))
    manifest = load_manifest(bundle)
    render = manifest["render"]
    assert isinstance(render, dict)
    chunk_size = args.chunk_size or int(render["chunk_size"])
    chunks = _chunk_records(manifest, chunk_size)
    args.chunk_count = len(chunks)
    r2 = R2Storage.from_args(args) if args.r2 else None
    manual_url_options = (
        args.input_url,
        args.input_upload_url,
        args.output_url,
        args.output_url_template,
        args.output_upload_url_template,
        args.output_url_file,
        args.output_download_url_template,
    )
    if r2 and any(option is not None for option in manual_url_options):
        raise RunpodError("--r2 cannot be combined with manual input/output URL options")
    if not r2:
        input_url = _https_url(args.input_url, "--input-url")
    batch_id = r2.new_batch_id(bundle.name) if r2 else None
    archive_path: Path
    with tempfile.TemporaryDirectory(prefix="runpod-submit-") as temporary:
        archive_path = Path(temporary) / f"{bundle.name}.tar.gz"
        archive_directory(bundle, archive_path, arcname=bundle.name)
        bundle_sha256 = sha256_file(archive_path)
        input_key = r2.object_key(batch_id, "input.tar.gz") if r2 and batch_id else None
        input_upload_url = r2.put_url(input_key) if r2 and input_key else None
        if input_upload_url:
            _upload_with_curl(input_upload_url, archive_path)
            input_url = r2.get_url(input_key)
        elif args.input_upload_url:
            _upload_with_curl(_https_url(args.input_upload_url, "--input-upload-url"), archive_path)

        jobs_path = _state_path(bundle, args.jobs_file)
        state: dict[str, object] = {
            "schema_version": 1,
            "endpoint_id": args.endpoint_id or os.environ.get("RUNPOD_ENDPOINT_ID", ""),
            "api_base_url": args.api_base_url or os.environ.get("RUNPOD_API_BASE_URL", "https://api.runpod.ai/v2"),
            "bundle": str(bundle),
            "bundle_sha256": bundle_sha256,
            "chunk_size": chunk_size,
            "jobs": [],
        }
        if r2 and batch_id:
            state["storage"] = {
                "provider": "cloudflare-r2",
                "bucket": r2.bucket,
                "prefix": r2.prefix,
                "batch_id": batch_id,
                "input_key": input_key,
                "url_expiry_seconds": r2.url_expiry_seconds,
            }
        _atomic_write_json(jobs_path, state)
        api = _api_from_args(args, state)
        policy = {"executionTimeout": args.execution_timeout_ms, "ttl": args.ttl_ms}
        records: list[dict[str, object]] = []
        try:
            for chunk in chunks:
                chunk_id = str(chunk["chunk_id"])
                if r2 and batch_id:
                    output_key = r2.object_key(batch_id, "chunks", f"{chunk_id}.tar.gz")
                    upload_url = r2.put_url(output_key)
                    download_url = r2.get_url(output_key)
                else:
                    upload_url, download_url = _output_urls(
                        args, chunk_id, int(chunk["index"]), int(chunk["frame_start"]), int(chunk["frame_end"])
                    )
                payload = {
                    "schema_version": 1,
                    "chunk_id": chunk_id,
                    "bundle_url": input_url,
                    "bundle_sha256": bundle_sha256,
                    "output_upload_url": upload_url,
                    "output_download_url": download_url,
                    "chunk": chunk,
                    "validate_assets": bool(chunk["index"] == 0),
                }
                response = api.submit(payload, policy)
                job_id = response.get("id")
                if not isinstance(job_id, str) or not job_id:
                    raise RunpodError("Runpod submit response did not contain a job id")
                records.append(
                    {
                        **chunk,
                        "job_id": job_id,
                        "output_upload_url": upload_url,
                        "output_download_url": download_url,
                        "status": "IN_QUEUE",
                    }
                )
                state["jobs"] = records
                _atomic_write_json(jobs_path, state)
                print(f"RUNPOD_SUBMITTED chunk={chunk_id} job={job_id}")
        except Exception:
            state["jobs"] = records
            _atomic_write_json(jobs_path, state)
            raise
    print(f"RUNPOD_JOBS_FILE={jobs_path}")
    if args.wait or args.download:
        return wait_for_jobs(args, jobs_path, download=args.download)
    return 0


def refresh_state(api: RunpodApi, state: dict[str, object], jobs_path: Path) -> tuple[int, int]:
    jobs = state.get("jobs")
    if not isinstance(jobs, list):
        raise RunpodError("jobs file has no jobs list")
    completed = failed = 0
    for record in jobs:
        if not isinstance(record, dict):
            raise RunpodError("jobs file contains an invalid job record")
        status = str(record.get("status", ""))
        if status in TERMINAL_STATUSES:
            if status == "COMPLETED":
                completed += 1
            else:
                failed += 1
            continue
        job_id = record.get("job_id")
        if not isinstance(job_id, str):
            raise RunpodError("job record has no job id")
        response = api.status(job_id)
        status = str(response.get("status", "UNKNOWN"))
        record["status"] = status
        record["last_status"] = response
        output = response.get("output")
        if isinstance(output, dict):
            record["result"] = output
            if not record.get("output_download_url") and output.get("output_download_url"):
                record["output_download_url"] = output["output_download_url"]
        if status == "COMPLETED":
            completed += 1
        elif status in TERMINAL_STATUSES:
            failed += 1
        print(f"RUNPOD_STATUS chunk={record.get('chunk_id')} status={status}")
    _atomic_write_json(jobs_path, state)
    return completed, failed


def wait_for_jobs(args: argparse.Namespace, jobs_path: Path, *, download: bool = False) -> int:
    state = _load_json(jobs_path)
    api = _api_from_args(args, state)
    jobs = state.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        raise RunpodError("jobs file contains no jobs")
    deadline = time.monotonic() + args.max_wait_seconds if args.max_wait_seconds else None
    while True:
        completed, failed = refresh_state(api, state, jobs_path)
        total = len(jobs)
        print(f"RUNPOD_PROGRESS completed={completed} failed={failed} total={total}")
        if completed + failed == total:
            if failed:
                return 2
            if download:
                download_results(jobs_path)
            return 0
        if deadline is not None and time.monotonic() >= deadline:
            raise RunpodError("timed out while waiting for Runpod jobs")
        time.sleep(args.poll_seconds)


def _record_archive_url(record: dict[str, object]) -> str:
    result = record.get("result")
    value = record.get("output_download_url")
    if not value and isinstance(result, dict):
        value = result.get("output_download_url")
    if not value:
        raise RunpodError(f"no output download URL for chunk {record.get('chunk_id')}")
    return _https_url(value, "output download URL")


def _verify_frames(bundle: Path, directory: Path, start: int, end: int, width: int, height: int) -> None:
    command = [
        sys.executable,
        str(bundle / "scripts" / "verify_frame_sequence.py"),
        "--directory",
        str(directory),
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
    ]
    completed = subprocess.run(command, cwd=bundle, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RunpodError(f"chunk frame verification failed for {start}-{end}")


def download_results(jobs_path: Path) -> int:
    state = _load_json(jobs_path)
    bundle = Path(str(state.get("bundle", ""))).expanduser().resolve()
    manifest = load_manifest(bundle)
    render = manifest.get("render")
    if not isinstance(render, dict):
        raise RunpodError("manifest render must be an object")
    jobs = state.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        raise RunpodError("jobs file contains no jobs")
    if any(not isinstance(record, dict) or record.get("status") != "COMPLETED" for record in jobs):
        raise RunpodError("all Runpod jobs must be COMPLETED before download")

    output = bundle / "output"
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="runpod-download-") as temporary:
        temporary_root = Path(temporary)
        for record in sorted(jobs, key=lambda item: int(item["index"])):
            assert isinstance(record, dict)
            archive = temporary_root / f"{record['chunk_id']}.tar.gz"
            _download_file(_record_archive_url(record), archive)
            result = record.get("result")
            if isinstance(result, dict) and result.get("archive_sha256"):
                if sha256_file(archive).lower() != str(result["archive_sha256"]).lower():
                    raise RunpodError(f"archive digest mismatch for chunk {record['chunk_id']}")
            extracted = temporary_root / str(record["chunk_id"])
            safe_extract_tar(archive, extracted)
            chunk_output = extracted / "output"
            if not chunk_output.is_dir():
                raise RunpodError(f"chunk archive has no output directory: {record['chunk_id']}")
            _verify_frames(bundle, chunk_output, int(record["frame_start"]), int(record["frame_end"]), int(render["width"]), int(render["height"]))
            for frame in range(int(record["frame_start"]), int(record["frame_end"]) + 1):
                source = chunk_output / f"frame_{frame:04d}.png"
                target = output / source.name
                if target.exists():
                    if sha256_file(target) != sha256_file(source):
                        raise RunpodError(f"conflicting output frame: {target.name}")
                else:
                    shutil.copy2(source, target)
            report = chunk_output / "render_report.json"
            if report.is_file():
                safe_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(record["chunk_id"]))
                shutil.copy2(report, output / f"render_report_{safe_id}.json")
            print(f"RUNPOD_DOWNLOADED chunk={record['chunk_id']}")

    _verify_frames(bundle, output, int(render["frame_start"]), int(render["frame_end"]), int(render["width"]), int(render["height"]))
    devices = {str(record.get("result", {}).get("render_device")) for record in jobs if isinstance(record.get("result"), dict)}
    consolidated = {
        "backend": "runpod-serverless",
        "engine": "CYCLES",
        "render_executed": True,
        "render_device": "GPU" if devices == {"GPU"} else "MIXED",
        "resolution": {"width": render["width"], "height": render["height"]},
        "frame_rate": render["fps"],
        "frame_range": [render["frame_start"], render["frame_end"]],
        "chunks": [
            {
                "chunk_id": record.get("chunk_id"),
                "job_id": record.get("job_id"),
                "frame_start": record.get("frame_start"),
                "frame_end": record.get("frame_end"),
                "render_device": record.get("result", {}).get("render_device") if isinstance(record.get("result"), dict) else None,
            }
            for record in jobs
        ],
    }
    (output / "render_report.json").write_text(json.dumps(consolidated, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    state["downloaded"] = True
    _atomic_write_json(jobs_path, state)
    print(f"RUNPOD_OUTPUT={output}")
    print("RUNPOD_RENDER=PASS")
    return 0


def retry_failed_jobs(args: argparse.Namespace, jobs_path: Path) -> int:
    """Resubmit only terminal failures using fresh R2 URLs."""

    state = _load_json(jobs_path)
    jobs = state.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        raise RunpodError("jobs file contains no jobs")
    failed = [
        record
        for record in jobs
        if isinstance(record, dict) and str(record.get("status", "")) in TERMINAL_STATUSES - {"COMPLETED"}
    ]
    if not failed:
        print("RUNPOD_RETRY none")
        return 0

    storage_info = state.get("storage")
    if not isinstance(storage_info, dict) or storage_info.get("provider") != "cloudflare-r2":
        raise RunpodError("retry currently requires a Cloudflare R2 jobs file")
    batch_id = storage_info.get("batch_id")
    input_key = storage_info.get("input_key")
    if not isinstance(batch_id, str) or not isinstance(input_key, str):
        raise RunpodError("R2 jobs file is missing its input object metadata")

    bundle = Path(str(state.get("bundle", ""))).expanduser().resolve()
    errors = validate_bundle(bundle)
    if errors:
        raise RunpodError("bundle validation failed: " + "; ".join(errors))
    manifest = load_manifest(bundle)
    render = manifest.get("render")
    if not isinstance(render, dict):
        raise RunpodError("manifest render must be an object")

    storage = R2Storage.from_args(args)
    input_url = storage.get_url(input_key)
    api = _api_from_args(args, state)
    policy = {"executionTimeout": args.execution_timeout_ms, "ttl": args.ttl_ms}
    for record in failed:
        chunk_id = record.get("chunk_id")
        if not isinstance(chunk_id, str):
            raise RunpodError("failed job record has no chunk id")
        try:
            chunk = {
                "chunk_id": chunk_id,
                "index": int(record["index"]),
                "frame_start": int(record["frame_start"]),
                "frame_end": int(record["frame_end"]),
            }
        except (KeyError, TypeError, ValueError) as exc:
            raise RunpodError(f"failed job record is missing chunk metadata: {chunk_id}") from exc
        output_key = storage.object_key(batch_id, "chunks", f"{chunk_id}.tar.gz")
        upload_url = storage.put_url(output_key)
        download_url = storage.get_url(output_key)
        payload = {
            "schema_version": 1,
            "chunk_id": chunk_id,
            "bundle_url": input_url,
            "bundle_sha256": str(state["bundle_sha256"]),
            "output_upload_url": upload_url,
            "output_download_url": download_url,
            "chunk": chunk,
            "validate_assets": bool(chunk["index"] == 0),
        }
        response = api.submit(payload, policy)
        job_id = response.get("id")
        if not isinstance(job_id, str) or not job_id:
            raise RunpodError(f"Runpod retry response did not contain a job id for {chunk_id}")
        record.update(
            {
                "job_id": job_id,
                "output_upload_url": upload_url,
                "output_download_url": download_url,
                "status": "IN_QUEUE",
            }
        )
        record.pop("result", None)
        record.pop("last_status", None)
        _atomic_write_json(jobs_path, state)
        print(f"RUNPOD_RETRIED chunk={chunk_id} job={job_id}")
    return 0


def cleanup_r2_objects(args: argparse.Namespace, jobs_path: Path) -> int:
    """Delete exactly the R2 objects belonging to a completed jobs file."""

    state = _load_json(jobs_path)
    storage_info = state.get("storage")
    if not isinstance(storage_info, dict) or storage_info.get("provider") != "cloudflare-r2":
        raise RunpodError("cleanup requires a Cloudflare R2 jobs file")
    batch_id = storage_info.get("batch_id")
    input_key = storage_info.get("input_key")
    jobs = state.get("jobs")
    if not isinstance(batch_id, str) or not isinstance(input_key, str) or not isinstance(jobs, list):
        raise RunpodError("R2 jobs file is missing cleanup metadata")
    storage = R2Storage.from_args(args)
    keys = {input_key}
    for record in jobs:
        if not isinstance(record, dict) or not isinstance(record.get("chunk_id"), str):
            raise RunpodError("jobs file contains an invalid chunk record")
        keys.add(storage.object_key(batch_id, "chunks", f"{record['chunk_id']}.tar.gz"))
    for key in sorted(keys):
        _delete_with_curl(storage.delete_url(key))
        print(f"RUNPOD_CLEANED object={key}")
    state["cleaned_up"] = True
    _atomic_write_json(jobs_path, state)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint-id", default=None)
    parser.add_argument("--api-base-url", default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)

    submit_parser = subparsers.add_parser("submit", help="archive and submit all frame chunks")
    submit_parser.add_argument("--bundle", type=Path, required=True)
    submit_parser.add_argument("--input-url", help="HTTPS signed GET URL for the bundle")
    submit_parser.add_argument("--input-upload-url", help="HTTPS signed PUT URL for the bundle archive")
    submit_parser.add_argument(
        "--r2", action="store_true", help="upload the bundle and create output URLs using Cloudflare R2"
    )
    submit_parser.add_argument("--r2-bucket", help="override R2_BUCKET")
    submit_parser.add_argument("--r2-endpoint-url", help="override R2_ENDPOINT_URL")
    submit_parser.add_argument("--r2-prefix", help="override R2_PREFIX (default: manim-render)")
    submit_parser.add_argument(
        "--r2-url-expiry-seconds", type=int, help="R2 presigned URL lifetime (default: 86400)"
    )
    output_group = submit_parser.add_mutually_exclusive_group(required=False)
    output_group.add_argument("--output-url", help="single-chunk signed PUT/GET URL")
    output_group.add_argument("--output-url-template", help="signed URL template with chunk placeholders")
    output_group.add_argument(
        "--output-upload-url-template", help="signed PUT URL template with chunk placeholders"
    )
    output_group.add_argument("--output-url-file", help="JSON map of chunk id/index to upload/download URLs")
    submit_parser.add_argument(
        "--output-download-url-template", help="signed GET URL template paired with the upload template"
    )
    submit_parser.add_argument("--chunk-size", type=int)
    submit_parser.add_argument("--execution-timeout-ms", type=int, default=3_600_000)
    submit_parser.add_argument("--ttl-ms", type=int, default=86_400_000)
    submit_parser.add_argument("--jobs-file")
    submit_parser.add_argument("--wait", action="store_true")
    submit_parser.add_argument("--download", action="store_true")
    submit_parser.add_argument("--poll-seconds", type=float, default=5.0)
    submit_parser.add_argument("--max-wait-seconds", type=float)

    for name in ("status", "wait"):
        command_parser = subparsers.add_parser(name, help=f"{name} submitted jobs")
        command_parser.add_argument("--jobs-file", required=True)
        command_parser.add_argument("--poll-seconds", type=float, default=5.0)
        command_parser.add_argument("--max-wait-seconds", type=float)
        command_parser.add_argument("--download", action="store_true")
    download_parser = subparsers.add_parser("download", help="download and merge completed chunks")
    download_parser.add_argument("--jobs-file", required=True)
    retry_parser = subparsers.add_parser("retry", help="resubmit terminally failed R2 chunks")
    retry_parser.add_argument("--jobs-file", required=True)
    retry_parser.add_argument("--r2-bucket")
    retry_parser.add_argument("--r2-endpoint-url")
    retry_parser.add_argument("--r2-prefix")
    retry_parser.add_argument("--r2-url-expiry-seconds", type=int)
    retry_parser.add_argument("--execution-timeout-ms", type=int, default=3_600_000)
    retry_parser.add_argument("--ttl-ms", type=int, default=86_400_000)
    cleanup_parser = subparsers.add_parser("cleanup", help="delete this batch's R2 input/output objects")
    cleanup_parser.add_argument("--jobs-file", required=True)
    cleanup_parser.add_argument("--confirm", action="store_true", help="confirm deletion of the batch objects")
    cleanup_parser.add_argument("--r2-bucket")
    cleanup_parser.add_argument("--r2-endpoint-url")
    cleanup_parser.add_argument("--r2-prefix")
    cleanup_parser.add_argument("--r2-url-expiry-seconds", type=int)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command in {"submit", "status", "wait"}:
            if args.poll_seconds <= 0:
                raise RunpodError("--poll-seconds must be positive")
            if args.max_wait_seconds is not None and args.max_wait_seconds <= 0:
                raise RunpodError("--max-wait-seconds must be positive")
        if args.command == "submit":
            if args.chunk_size is not None and args.chunk_size <= 0:
                raise RunpodError("--chunk-size must be positive")
            if args.execution_timeout_ms <= 0 or args.ttl_ms <= 0:
                raise RunpodError("execution timeout and TTL must be positive")
            return submit(args)
        if args.command == "status":
            path = Path(args.jobs_file).expanduser().resolve()
            state = _load_json(path)
            completed, failed = refresh_state(_api_from_args(args, state), state, path)
            print(f"RUNPOD_PROGRESS completed={completed} failed={failed} total={len(state['jobs'])}")
            return 2 if failed else 0
        if args.command == "wait":
            return wait_for_jobs(args, Path(args.jobs_file).expanduser().resolve(), download=args.download)
        if args.command == "download":
            return download_results(Path(args.jobs_file).expanduser().resolve())
        if args.command == "retry":
            if args.execution_timeout_ms <= 0 or args.ttl_ms <= 0:
                raise RunpodError("execution timeout and TTL must be positive")
            return retry_failed_jobs(args, Path(args.jobs_file).expanduser().resolve())
        if args.command == "cleanup":
            if not args.confirm:
                raise RunpodError("cleanup is destructive; pass --confirm to delete R2 objects")
            return cleanup_r2_objects(args, Path(args.jobs_file).expanduser().resolve())
    except (OSError, RunpodError, ValueError) as exc:
        print(f"runpod client error: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
