#!/usr/bin/env python3
"""Create, monitor, and terminate Runpod Pods for Blender/Cycles renders.

The control plane is deliberately Pod-first: each submitted bundle is rendered
by one disposable GPU Pod. The Pod downloads a SHA-256-checked bundle from R2,
renders every requested frame in one Blender process, uploads its result archive
and a small status document, and is then terminated by this client.

Only this program receives Runpod and R2 credentials. URLs in the local state
file are presigned and therefore never printed to stdout or stderr.
"""

from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import signal
import shutil
import subprocess
import sys
import tempfile
import time
from uuid import uuid4
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from r2_storage import R2Storage
from runpod_job_utils import archive_directory, load_manifest, safe_extract_tar, sha256_file
from verify_runpod_render_job import validate as validate_bundle


TERMINAL_STATUSES = {"COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT"}
RUNNING_STATUSES = {"IN_PROGRESS", "RUNNING", "EXECUTING"}
QUEUED_STATUSES = {"PROVISIONING", "QUEUED", "IN_QUEUE", "STARTING"}
POD_EXITED_STATUSES = {"EXITED", "FAILED", "STOPPED", "TERMINATED", "CANCELLED"}
STATE_SCHEMA_VERSION = 2
_DURATION_RE = re.compile(r"^(?P<amount>[1-9][0-9]*)(?P<unit>[smhdw])$")
_SAFE_NAME_RE = re.compile(r"[^a-z0-9-]+")


class RunpodError(RuntimeError):
    """A user-actionable Pod-control failure."""


def _runpod_api_key() -> str:
    """Read the key from the process environment only; never read or persist it."""

    return os.environ.get("RUNPOD_API_KEY", "")


def _atomic_write_json(path: Path, value: object) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.chmod(0o600)
    os.replace(temporary, path)
    path.chmod(0o600)


def _renderpulse_registry_path() -> Path:
    configured = os.environ.get("RENDER_PULSE_REGISTRY_FILE")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path.home() / "Library" / "Application Support" / "RenderPulse" / "works.json"


def _load_work_registry() -> list[dict[str, object]]:
    try:
        value = json.loads(_renderpulse_registry_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def register_work(
    name: str,
    jobs_files: list[str],
    work_id: str | None = None,
    *,
    preserve_existing_name: bool = False,
) -> dict[str, object]:
    """Register local, credential-free display metadata for RenderPulse."""

    paths = [str(Path(path).expanduser().resolve()) for path in jobs_files]
    if not paths:
        raise RunpodError("at least one --jobs-file is required")
    name = name.strip()
    if not name:
        raise RunpodError("--work-name cannot be empty")
    registry = _load_work_registry()
    matching = next(
        (
            item
            for item in registry
            if (work_id and item.get("id") == work_id)
            or item.get("jobs_file_paths") == paths
        ),
        None,
    )
    if matching is None:
        matching = {
            "id": work_id or str(uuid4()),
            "name": name,
            "jobs_file_paths": paths,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        registry.append(matching)
    else:
        if not preserve_existing_name:
            matching["name"] = name
        matching["jobs_file_paths"] = paths
        if work_id:
            matching["id"] = work_id
    _atomic_write_json(_renderpulse_registry_path(), registry)
    return matching


def default_work_name(jobs_path: Path) -> str:
    folder = jobs_path.parent.name
    match = re.fullmatch(r"runpod-prod-(.+)-v\d+", folder)
    if match:
        return f"{match.group(1)} render"
    return folder.replace("_", " ").replace("-", " ").strip() or "RunPod render"


def _load_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.expanduser().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RunpodError(f"could not read jobs file: {path}") from exc
    if not isinstance(value, dict):
        raise RunpodError(f"unsupported jobs file: {path}")
    if value.get("schema_version") != STATE_SCHEMA_VERSION or value.get("backend") != "runpod-pod":
        raise RunpodError(
            "this is not a Runpod Pod state file; create a new render with visual-runpod submit"
        )
    return value


def _runpodctl_path() -> str:
    configured = os.environ.get("RUNPODCTL_BIN")
    candidates = [configured] if configured else []
    candidates.extend(
        filter(None, (shutil.which("runpodctl"), "/opt/homebrew/bin/runpodctl", "/usr/local/bin/runpodctl"))
    )
    for candidate in candidates:
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return candidate
    raise RunpodError(
        "runpodctl is required for Pod control. Install it with Runpod's official installer, "
        "then export RUNPOD_API_KEY in this shell."
    )


def _error_message(stderr: str) -> str:
    try:
        value = json.loads(stderr)
    except json.JSONDecodeError:
        return stderr.strip().splitlines()[0] if stderr.strip() else "runpodctl failed"
    if isinstance(value, dict) and isinstance(value.get("error"), str):
        return value["error"]
    return "runpodctl failed"


def _is_pod_not_found(error: RunpodError) -> bool:
    """Recognize an already-removed Pod so cleanup remains idempotent."""

    message = str(error).lower()
    return "pod not found" in message or (
        "failed to get pod" in message and "not found" in message
    )


class RunpodPodController:
    """Small, testable adapter around the supported ``runpodctl pod`` surface."""

    def __init__(self, binary: str | None = None) -> None:
        self.binary = binary or _runpodctl_path()
        self._create_flag_support: dict[str, bool] = {}

    def supports_create_flag(self, flag: str) -> bool:
        """Probe the installed CLI without contacting the Runpod control plane."""

        if flag not in self._create_flag_support:
            try:
                completed = subprocess.run(
                    [self.binary, "pod", "create", "--help"],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                help_text = f"{completed.stdout}\n{completed.stderr}"
                self._create_flag_support[flag] = (
                    completed.returncode == 0 and flag in help_text
                )
            except OSError:
                self._create_flag_support[flag] = False
        return self._create_flag_support[flag]

    def _run(self, arguments: list[str], *, parse_json: bool = True) -> object:
        completed = subprocess.run(
            [self.binary, *arguments], check=False, capture_output=True, text=True
        )
        if completed.returncode != 0:
            raise RunpodError(_error_message(completed.stderr))
        if not parse_json or not completed.stdout.strip():
            return {}
        try:
            return json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise RunpodError("runpodctl returned an invalid response") from exc

    @staticmethod
    def _pod_id(value: object) -> str:
        if isinstance(value, dict):
            for key in ("id", "podId", "pod_id"):
                candidate = value.get(key)
                if isinstance(candidate, str) and candidate:
                    return candidate
            for key in ("pod", "data"):
                nested = value.get(key)
                if isinstance(nested, dict):
                    try:
                        return RunpodPodController._pod_id(nested)
                    except RunpodError:
                        pass
        raise RunpodError("runpodctl pod create did not return a Pod id")

    def create(self, settings: dict[str, object], environment: dict[str, str], name: str) -> str:
        command = [
            "pod", "create", "--name", name, "--image", str(settings["image"]), "--gpu-id",
            str(settings["gpu_id"]), "--container-disk-in-gb", str(settings["container_disk_gb"]),
            # This is a one-shot worker; it needs no public SSH endpoint.
            "--ssh=false",
        ]
        # The current runpodctl release does not expose the documented
        # create-time termination flag. Use it when a newer CLI provides it,
        # otherwise rely on the controller's terminal/timeout cleanup paths.
        if self.supports_create_flag("--terminate-after"):
            command.extend(("--terminate-after", str(settings["terminate_after"])))
        command.extend(("--env", json.dumps(environment, separators=(",", ":"))))
        if data_centers := settings.get("data_center_ids"):
            command.extend(("--data-center-ids", str(data_centers)))
        if registry_auth := settings.get("registry_auth_id"):
            command.extend(("--registry-auth-id", str(registry_auth)))
        return self._pod_id(self._run(command))

    def runtime_status(self, pod_id: str) -> str:
        try:
            value = self._run(["pod", "get", pod_id])
        except RunpodError as exc:
            # A user or an external watchdog may have removed the Pod already.
            if _is_pod_not_found(exc):
                return "TERMINATED"
            raise
        if not isinstance(value, dict):
            return "UNKNOWN"
        for key in ("runtimeStatus", "runtime_status", "status"):
            status = value.get(key)
            if isinstance(status, str) and status:
                return status.upper()
        return "UNKNOWN"

    def delete(self, pod_id: str) -> None:
        try:
            self._run(["pod", "delete", pod_id], parse_json=False)
        except RunpodError as exc:
            # Deleting an already-gone Pod is the desired final state.
            if not _is_pod_not_found(exc):
                raise


def _upload_with_curl(url: str, source: Path) -> None:
    completed = subprocess.run(
        ["curl", "--fail", "--silent", "--show-error", "--location", "--upload-file", str(source), url],
        check=False, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
    )
    if completed.returncode != 0:
        raise RunpodError(f"R2 upload failed with exit code {completed.returncode}")


def _download_file(url: str, destination: Path) -> None:
    try:
        with urlopen(Request(url, method="GET"), timeout=3600) as response, destination.open("wb") as output:
            shutil.copyfileobj(response, output, length=1024 * 1024)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise RunpodError("output archive download failed") from exc


def _delete_with_curl(url: str) -> None:
    completed = subprocess.run(
        ["curl", "--fail", "--silent", "--show-error", "--location", "--request", "DELETE", url],
        check=False, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
    )
    if completed.returncode != 0:
        raise RunpodError(f"R2 cleanup failed with exit code {completed.returncode}")


def _remote_status(url: str) -> dict[str, object] | None:
    try:
        with urlopen(Request(url, method="GET"), timeout=30) as response:
            value = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 404:
            return None
        raise RunpodError(f"Pod status download returned HTTP {exc.code}") from exc
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise RunpodError("Pod status download failed") from exc
    return value if isinstance(value, dict) else None


def _state_path(bundle: Path, requested: str | None) -> Path:
    return Path(requested).expanduser().resolve() if requested else bundle.parent / f"{bundle.name}.runpod.json"


def _single_pod_record(manifest: dict[str, object]) -> dict[str, object]:
    render = manifest.get("render")
    if not isinstance(render, dict):
        raise RunpodError("manifest render must be an object")
    start, end = render.get("frame_start"), render.get("frame_end")
    if not isinstance(start, int) or not isinstance(end, int) or start > end:
        raise RunpodError("manifest frame range is invalid")
    return {
        "chunk_id": f"pod-{start:06d}-{end:06d}", "index": 0, "frame_start": start,
        "frame_end": end, "status": "PROVISIONING",
    }


def _required_setting(args: argparse.Namespace, argument: str, environment: str) -> str:
    value = getattr(args, argument, None) or os.environ.get(environment, "")
    if not isinstance(value, str) or not value.strip():
        raise RunpodError(f"--{argument.replace('_', '-')} or {environment} is required")
    return value.strip()


def _terminate_after_duration(value: str) -> str:
    """Validate the duration syntax used by the local Pod wait budget."""

    if not _DURATION_RE.fullmatch(value):
        raise RunpodError("--terminate-after must be a duration such as 2h, 45m, or 1d")
    return value


def _pod_settings_from_args(args: argparse.Namespace) -> dict[str, object]:
    terminate_input = args.terminate_after or os.environ.get("RUNPOD_POD_TERMINATE_AFTER", "8h")
    terminate_after = _terminate_after_duration(terminate_input)
    disk = args.container_disk_gb
    if disk is None:
        disk = int(os.environ.get("RUNPOD_POD_CONTAINER_DISK_GB", "30"))
    if disk <= 0:
        raise RunpodError("--container-disk-gb must be positive")
    return {
        "image": _required_setting(args, "pod_image", "RUNPOD_POD_IMAGE"),
        "gpu_id": _required_setting(args, "gpu_id", "RUNPOD_POD_GPU_ID"),
        "container_disk_gb": disk,
        "terminate_after": terminate_after,
        "registry_auth_id": args.registry_auth_id or os.environ.get("RUNPOD_REGISTRY_AUTH_ID") or None,
        "data_center_ids": args.data_center_ids or os.environ.get("RUNPOD_POD_DATA_CENTER_IDS") or None,
    }


def _pod_name(bundle: Path) -> str:
    label = _SAFE_NAME_RE.sub("-", bundle.name.lower()).strip("-") or "render"
    return f"cycles-{label[:32]}-{uuid4().hex[:8]}"


def _has_valid_result(record: dict[str, object]) -> bool:
    result = record.get("result")
    digest = result.get("archive_sha256") if isinstance(result, dict) else None
    return isinstance(digest, str) and bool(re.fullmatch(r"[0-9a-fA-F]{64}", digest))


def _is_completed_record(record: dict[str, object]) -> bool:
    return record.get("status") == "COMPLETED" and _has_valid_result(record)


def _pod_event(
    record: dict[str, object], bundle_url: str, bundle_sha256: str, output_upload_url: str, output_download_url: str
) -> dict[str, object]:
    return {
        "schema_version": 1, "chunk_id": record["chunk_id"], "bundle_url": bundle_url,
        "bundle_sha256": bundle_sha256, "output_upload_url": output_upload_url,
        "output_download_url": output_download_url,
        "chunk": {"index": record["index"], "frame_start": record["frame_start"], "frame_end": record["frame_end"]},
        "validate_assets": True,
    }


def _pod_environment(event: dict[str, object], status_upload_url: str) -> dict[str, str]:
    encoded = base64.b64encode(
        json.dumps(event, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    return {"RENDER_JOB_INPUT_B64": encoded, "RENDER_STATUS_UPLOAD_URL": status_upload_url}


def _create_pod(
    controller: RunpodPodController, state: dict[str, object], record: dict[str, object], *,
    bundle_url: str, settings: dict[str, object], r2: R2Storage, batch_id: str,
) -> None:
    chunk_id = str(record["chunk_id"])
    output_key = r2.object_key(batch_id, "output.tar.gz")
    status_key = r2.object_key(batch_id, "status.json")
    output_upload_url, output_download_url = r2.put_url(output_key), r2.get_url(output_key)
    status_upload_url, status_download_url = r2.put_url(status_key), r2.get_url(status_key)
    event = _pod_event(record, bundle_url, str(state["bundle_sha256"]), output_upload_url, output_download_url)
    record.update({
        "output_download_url": output_download_url, "status_download_url": status_download_url,
        "status": "PROVISIONING", "pod_name": _pod_name(Path(str(state["bundle"]))),
    })
    jobs_file = Path(str(state["jobs_file"]))
    _atomic_write_json(jobs_file, state)
    try:
        supports_guard = getattr(controller, "supports_create_flag", None)
        if callable(supports_guard) and not supports_guard("--terminate-after"):
            print(
                "warning: installed runpodctl has no --terminate-after; "
                "the local monitor will delete the Pod on terminal status or timeout",
                file=sys.stderr,
            )
        record["pod_id"] = controller.create(settings, _pod_environment(event, status_upload_url), str(record["pod_name"]))
    except Exception as exc:
        record["status"] = "FAILED"
        record["completion_error"] = str(exc)
        _atomic_write_json(jobs_file, state)
        raise
    record["status"] = "STARTING"
    _atomic_write_json(jobs_file, state)
    print(f"RUNPOD_POD_CREATED pod={record['pod_id']} frames={record['frame_start']}-{record['frame_end']}")


def submit(args: argparse.Namespace) -> int:
    if not args.r2:
        raise RunpodError("Pod rendering requires --r2 so the Pod can receive inputs and publish outputs")
    if not _runpod_api_key():
        raise RunpodError("RUNPOD_API_KEY must be exported in the current shell")
    bundle = args.bundle.expanduser().resolve()
    errors = validate_bundle(bundle)
    if errors:
        raise RunpodError("bundle validation failed: " + "; ".join(errors))
    manifest, r2, settings = load_manifest(bundle), R2Storage.from_args(args), _pod_settings_from_args(args)
    controller = RunpodPodController()
    batch_id, jobs_path, record = r2.new_batch_id(bundle.name), _state_path(bundle, args.jobs_file), _single_pod_record(manifest)
    state: dict[str, object] = {
        "schema_version": STATE_SCHEMA_VERSION, "backend": "runpod-pod", "jobs_file": str(jobs_path),
        "bundle": str(bundle), "pod_settings": settings, "jobs": [record],
        "storage": {"provider": "cloudflare-r2", "bucket": r2.bucket, "prefix": r2.prefix, "batch_id": batch_id, "url_expiry_seconds": r2.url_expiry_seconds},
    }
    with tempfile.TemporaryDirectory(prefix="runpod-pod-submit-") as temporary:
        archive = Path(temporary) / f"{bundle.name}.tar.gz"
        archive_directory(bundle, archive, arcname=bundle.name)
        state["bundle_sha256"] = sha256_file(archive)
        input_key = r2.object_key(batch_id, "input.tar.gz")
        storage = state["storage"]
        assert isinstance(storage, dict)
        storage["input_key"] = input_key
        _atomic_write_json(jobs_path, state)
        _upload_with_curl(r2.put_url(input_key), archive)
    storage = state["storage"]
    assert isinstance(storage, dict)
    _create_pod(controller, state, record, bundle_url=r2.get_url(str(storage["input_key"])), settings=settings, r2=r2, batch_id=batch_id)
    print(f"RUNPOD_JOBS_FILE={jobs_path}")
    if args.wait or args.download:
        return wait_for_jobs(args, jobs_path, download=args.download)
    return 0


def _apply_remote_status(record: dict[str, object], remote: dict[str, object]) -> None:
    status = str(remote.get("status", "UNKNOWN")).upper()
    current_status = str(record.get("status", "UNKNOWN")).upper()
    if isinstance(remote.get("progress"), dict):
        incoming = remote["progress"]
        previous = record.get("progress")
        if isinstance(previous, dict):
            # Status PUTs can arrive out of order while the worker uploads its
            # archive. Keep aggregate progress monotonic so the UI never jumps
            # from a completed frame back to zero.
            merged = {**previous, **incoming}
            for field in ("frames_completed", "percent", "frame"):
                old_value, new_value = previous.get(field), incoming.get(field)
                if isinstance(old_value, (int, float)) and isinstance(new_value, (int, float)):
                    merged[field] = max(old_value, new_value)
            record["progress"] = merged
        else:
            record["progress"] = incoming
    if isinstance(remote.get("result"), dict):
        record["result"] = remote["result"]
    if isinstance(remote.get("error"), str):
        record["completion_error"] = remote["error"]
    if status == "COMPLETED" and not _has_valid_result(record):
        record["status"] = "RESULT_PENDING"
        record["completion_error"] = "Pod completed without an integrity-verifiable result"
    elif status in TERMINAL_STATUSES | RUNNING_STATUSES | QUEUED_STATUSES:
        # A late R2 write may contain an older RUNNING/QUEUED event. Never
        # downgrade a terminal record because that would keep a finished Pod
        # alive or make RenderPulse show a completed job as active again.
        if current_status not in TERMINAL_STATUSES | {"RESULT_PENDING"} or status in TERMINAL_STATUSES:
            record["status"] = status
            record["pod_runtime_status"] = status
    record["updated_at"] = remote.get("updated_at", datetime.now(timezone.utc).isoformat())


def refresh_state(
    controller: RunpodPodController, state: dict[str, object], jobs_path: Path, *, emit_events: bool = True,
) -> tuple[int, int]:
    jobs = state.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        raise RunpodError("jobs file has no Pod record")
    completed = failed = 0
    for record in jobs:
        if not isinstance(record, dict):
            raise RunpodError("jobs file contains an invalid Pod record")
        previous = str(record.get("status", "UNKNOWN"))
        if _is_completed_record(record):
            completed += 1
            continue
        if str(record.get("status")) in TERMINAL_STATUSES:
            failed += 1
            continue
        status_url = record.get("status_download_url")
        remote = _remote_status(status_url) if isinstance(status_url, str) else None
        if remote is not None:
            _apply_remote_status(record, remote)
        elif pod_id := record.get("pod_id"):
            runtime = controller.runtime_status(str(pod_id))
            record["pod_runtime_status"] = runtime
            if runtime in POD_EXITED_STATUSES:
                record["status"] = "FAILED"
                record["completion_error"] = "Pod exited before publishing a terminal render status"
        if _is_completed_record(record):
            completed += 1
        elif str(record.get("status")) in TERMINAL_STATUSES | {"RESULT_PENDING"}:
            failed += 1
        if emit_events and record.get("status") != previous:
            print(f"RUNPOD_POD_STATUS pod={record.get('pod_id', 'pending')} status={record.get('status')}")
    _atomic_write_json(jobs_path, state)
    return completed, failed


def work_status_payload(state: dict[str, object]) -> dict[str, object]:
    """Return the credential-safe aggregate consumed by RenderPulse."""

    jobs = state.get("jobs")
    if not isinstance(jobs, list):
        raise RunpodError("jobs file has no Pod record")
    completed = running = queued = failed = warnings = 0
    frames_completed = frames_total = 0
    for record in jobs:
        if not isinstance(record, dict):
            continue
        start, end = record.get("frame_start"), record.get("frame_end")
        chunk_frames = end - start + 1 if isinstance(start, int) and isinstance(end, int) and end >= start else 0
        frames_total += chunk_frames
        status = str(record.get("status", "UNKNOWN"))
        if _is_completed_record(record):
            completed += 1
            frames_completed += chunk_frames
        elif status in TERMINAL_STATUSES | {"RESULT_PENDING"}:
            failed += 1
        else:
            progress = record.get("progress")
            if isinstance(progress, dict) and isinstance(progress.get("frames_completed"), int):
                frames_completed += min(max(int(progress["frames_completed"]), 0), chunk_frames)
            if status in RUNNING_STATUSES:
                running += 1
            else:
                queued += 1
        if bool(record.get("completion_error")) or (isinstance(record.get("result"), dict) and record["result"].get("compute_device_fallback")):
            warnings += 1
    if failed:
        work_status = "ERROR"
    elif jobs and completed == len(jobs):
        work_status = "COMPLETED"
    elif running:
        work_status = "RUNNING"
    elif queued:
        work_status = "QUEUED"
    else:
        work_status = "WAITING"
    return {
        "schema_version": 1, "status": work_status,
        "progress": {"percent": round(frames_completed / frames_total * 100, 1) if frames_total else 0.0, "frames_completed": frames_completed, "frames_total": frames_total},
        "workers": {"active": running, "queued": queued, "total": len(jobs)},
        "warnings": {"count": warnings}, "errors": {"count": failed}, "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _print_batch_progress(state: dict[str, object]) -> None:
    payload = work_status_payload(state)
    progress = payload["progress"]
    assert isinstance(progress, dict)
    print("RUNPOD_PROGRESS " f"status={payload['status']} frames={progress['frames_completed']}/{progress['frames_total']} percent={progress['percent']}")


def _terminate_finished_pods(
    controller: RunpodPodController, state: dict[str, object], *, keep: bool, emit: bool = True,
) -> None:
    if keep:
        return
    jobs = state.get("jobs")
    if not isinstance(jobs, list):
        return
    changed = False
    for record in jobs:
        if not isinstance(record, dict) or record.get("pod_deleted") or not record.get("pod_id"):
            continue
        if str(record.get("status")) not in TERMINAL_STATUSES | {"RESULT_PENDING"}:
            continue
        controller.delete(str(record["pod_id"]))
        record["pod_deleted"] = True
        changed = True
        if emit:
            print(f"RUNPOD_POD_TERMINATED pod={record['pod_id']}")
    if changed:
        _atomic_write_json(Path(str(state["jobs_file"])), state)


def _terminate_active_pods(
    controller: RunpodPodController, state: dict[str, object], *, emit: bool = True,
) -> None:
    """Delete every still-owned Pod when a bounded wait is interrupted."""

    jobs = state.get("jobs")
    if not isinstance(jobs, list):
        return
    changed = False
    failures: list[str] = []
    previous_sigint = None
    try:
        # A Ctrl-C that triggered this cleanup must not interrupt the delete
        # subprocess itself. Restore the handler after all owned Pods are gone.
        previous_sigint = signal.signal(signal.SIGINT, signal.SIG_IGN)
    except (OSError, ValueError):
        pass
    try:
        for record in jobs:
            if not isinstance(record, dict) or record.get("pod_deleted") or not record.get("pod_id"):
                continue
            try:
                controller.delete(str(record["pod_id"]))
            except Exception as exc:  # preserve the original timeout/interruption error
                failures.append(f"{record['pod_id']}: {exc}")
                continue
            record["pod_deleted"] = True
            if str(record.get("status")) not in TERMINAL_STATUSES:
                record["status"] = "CANCELLED"
            changed = True
            if emit:
                print(f"RUNPOD_POD_TERMINATED pod={record['pod_id']}")
    finally:
        if previous_sigint is not None:
            try:
                signal.signal(signal.SIGINT, previous_sigint)
            except (OSError, ValueError):
                pass
    if changed:
        _atomic_write_json(Path(str(state["jobs_file"])), state)
    for failure in failures:
        print(f"warning: could not terminate Pod {failure}", file=sys.stderr)


def wait_for_jobs(args: argparse.Namespace, jobs_path: Path, *, download: bool) -> int:
    state = _load_json(jobs_path)
    try:
        register_work(getattr(args, "work_name", None) or default_work_name(jobs_path), [str(jobs_path)], preserve_existing_name=True)
    except (OSError, RunpodError) as exc:
        print(f"warning: could not register RenderPulse work: {exc}", file=sys.stderr)
    controller, started = RunpodPodController(), time.monotonic()
    keep_pod = bool(getattr(args, "keep_pod", False))
    try:
        while True:
            completed, failed = refresh_state(controller, state, jobs_path)
            _print_batch_progress(state)
            if completed + failed == len(state["jobs"]):
                _terminate_finished_pods(controller, state, keep=keep_pod)
                if failed:
                    return 2
                return download_results(jobs_path) if download else 0
            maximum = getattr(args, "max_wait_seconds", None)
            if maximum is not None and time.monotonic() - started >= maximum:
                if not keep_pod:
                    _terminate_active_pods(controller, state)
                raise RunpodError("timed out while waiting for Runpod Pod")
            time.sleep(float(getattr(args, "poll_seconds", 5.0)))
    except KeyboardInterrupt as exc:
        if not keep_pod:
            _terminate_active_pods(controller, state)
        raise RunpodError("interrupted while waiting for Runpod Pod") from exc


def _record_archive_url(record: dict[str, object]) -> str:
    value = record.get("output_download_url")
    if not isinstance(value, str) or not value.startswith("https://"):
        raise RunpodError("completed Pod record has no output download URL")
    return value


def _verify_frames(bundle: Path, directory: Path, start: int, end: int, width: int, height: int) -> None:
    completed = subprocess.run(
        [sys.executable, str(bundle / "scripts" / "verify_frame_sequence.py"), "--directory", str(directory), "--prefix", "frame_", "--frame-start", str(start), "--frame-end", str(end), "--width", str(width), "--height", str(height)],
        cwd=bundle, check=False, capture_output=True, text=True,
    )
    if completed.returncode != 0:
        raise RunpodError(f"frame verification failed for {start}-{end}")


def download_results(jobs_path: Path) -> int:
    state = _load_json(jobs_path)
    bundle = Path(str(state.get("bundle", ""))).expanduser().resolve()
    manifest = load_manifest(bundle)
    render, jobs = manifest.get("render"), state.get("jobs")
    if not isinstance(render, dict) or not isinstance(jobs, list) or not jobs:
        raise RunpodError("Pod state is missing render metadata")
    if any(not isinstance(record, dict) or not _is_completed_record(record) for record in jobs):
        raise RunpodError("the Pod has not completed with a verifiable output archive")
    output = bundle / "output"
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="runpod-pod-download-") as temporary:
        root = Path(temporary)
        for record in jobs:
            assert isinstance(record, dict)
            archive = root / f"{record['chunk_id']}.tar.gz"
            _download_file(_record_archive_url(record), archive)
            result = record["result"]
            assert isinstance(result, dict)
            if sha256_file(archive).lower() != str(result["archive_sha256"]).lower():
                raise RunpodError("output archive digest mismatch")
            extracted = root / str(record["chunk_id"])
            safe_extract_tar(archive, extracted)
            chunk_output = extracted / "output"
            if not chunk_output.is_dir():
                raise RunpodError("Pod archive has no output directory")
            _verify_frames(bundle, chunk_output, int(record["frame_start"]), int(record["frame_end"]), int(render["width"]), int(render["height"]))
            for frame in range(int(record["frame_start"]), int(record["frame_end"]) + 1):
                source, target = chunk_output / f"frame_{frame:04d}.png", output / f"frame_{frame:04d}.png"
                if target.exists() and sha256_file(target) != sha256_file(source):
                    raise RunpodError(f"conflicting output frame: {target.name}")
                if not target.exists():
                    shutil.copy2(source, target)
            report = chunk_output / "render_report.json"
            if report.is_file():
                shutil.copy2(report, output / "render_report_pod.json")
    _verify_frames(bundle, output, int(render["frame_start"]), int(render["frame_end"]), int(render["width"]), int(render["height"]))
    result = jobs[0]["result"]
    assert isinstance(result, dict)
    consolidated = {
        "backend": "runpod-pod", "engine": "CYCLES", "render_executed": True,
        "render_device": result.get("render_device"), "resolution": {"width": render["width"], "height": render["height"]},
        "frame_rate": render["fps"], "frame_range": [render["frame_start"], render["frame_end"]], "pod_id": jobs[0].get("pod_id"),
    }
    (output / "render_report.json").write_text(json.dumps(consolidated, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    state["downloaded"] = True
    _atomic_write_json(jobs_path, state)
    print(f"RUNPOD_OUTPUT={output}")
    print("RUNPOD_RENDER=PASS")
    return 0


def retry_failed_pod(args: argparse.Namespace, jobs_path: Path) -> int:
    state = _load_json(jobs_path)
    jobs, storage_info, settings = state.get("jobs"), state.get("storage"), state.get("pod_settings")
    if not isinstance(jobs, list) or not isinstance(storage_info, dict) or not isinstance(settings, dict):
        raise RunpodError("Pod state is missing retry metadata")
    record = jobs[0] if jobs else None
    if not isinstance(record, dict) or str(record.get("status")) not in TERMINAL_STATUSES | {"RESULT_PENDING"}:
        print("RUNPOD_RETRY none")
        return 0
    batch_id, input_key = storage_info.get("batch_id"), storage_info.get("input_key")
    if not isinstance(batch_id, str) or not isinstance(input_key, str):
        raise RunpodError("Pod state is missing R2 object metadata")
    r2 = R2Storage.from_args(args)
    for key in ("result", "completion_error", "pod_deleted", "pod_id", "progress"):
        record.pop(key, None)
    record["status"] = "PROVISIONING"
    _create_pod(RunpodPodController(), state, record, bundle_url=r2.get_url(input_key), settings=settings, r2=r2, batch_id=batch_id)
    return 0


def cleanup_r2_objects(args: argparse.Namespace, jobs_path: Path) -> int:
    state = _load_json(jobs_path)
    storage, jobs = state.get("storage"), state.get("jobs")
    if not isinstance(storage, dict) or not isinstance(jobs, list):
        raise RunpodError("Pod state is missing R2 cleanup metadata")
    batch_id, input_key = storage.get("batch_id"), storage.get("input_key")
    if not isinstance(batch_id, str) or not isinstance(input_key, str):
        raise RunpodError("Pod state is missing R2 object metadata")
    r2, keys = R2Storage.from_args(args), {input_key}
    for record in jobs:
        if not isinstance(record, dict) or not isinstance(record.get("chunk_id"), str):
            raise RunpodError("Pod state has an invalid render record")
        keys.add(r2.object_key(batch_id, "output.tar.gz"))
        keys.add(r2.object_key(batch_id, "status.json"))
    for key in sorted(keys):
        _delete_with_curl(r2.delete_url(key))
        print(f"RUNPOD_CLEANED object={key}")
    state["cleaned_up"] = True
    _atomic_write_json(jobs_path, state)
    return 0


def terminate_pods(jobs_path: Path) -> int:
    state = _load_json(jobs_path)
    jobs = state.get("jobs")
    if not isinstance(jobs, list):
        raise RunpodError("jobs file has no Pod record")
    controller = RunpodPodController()
    for record in jobs:
        if not isinstance(record, dict) or record.get("pod_deleted") or not record.get("pod_id"):
            continue
        controller.delete(str(record["pod_id"]))
        record["pod_deleted"] = True
        if str(record.get("status")) not in TERMINAL_STATUSES:
            record["status"] = "CANCELLED"
        print(f"RUNPOD_POD_TERMINATED pod={record['pod_id']}")
    _atomic_write_json(jobs_path, state)
    return 0


def _r2_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--r2-bucket")
    parser.add_argument("--r2-endpoint-url")
    parser.add_argument("--r2-prefix")
    parser.add_argument("--r2-url-expiry-seconds", type=int)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    register = subparsers.add_parser("register-work", help="register a render for RenderPulse")
    register.add_argument("--work-name", required=True)
    register.add_argument("--jobs-file", action="append", required=True)
    register.add_argument("--work-id")

    submit_parser = subparsers.add_parser("submit", help="create one disposable GPU Pod for a render bundle")
    submit_parser.add_argument("--bundle", type=Path, required=True)
    submit_parser.add_argument("--r2", action="store_true", help="use the configured Cloudflare R2 bucket")
    _r2_arguments(submit_parser)
    submit_parser.add_argument("--pod-image", help="or set RUNPOD_POD_IMAGE")
    submit_parser.add_argument("--gpu-id", help="or set RUNPOD_POD_GPU_ID")
    submit_parser.add_argument("--container-disk-gb", type=int)
    submit_parser.add_argument(
        "--terminate-after",
        help="local wait/cost budget (for example 8h, 45m, or 1d); default: 8h",
    )
    submit_parser.add_argument("--registry-auth-id")
    submit_parser.add_argument("--data-center-ids")
    submit_parser.add_argument("--jobs-file")
    submit_parser.add_argument("--wait", action="store_true")
    submit_parser.add_argument("--download", action="store_true")
    submit_parser.add_argument("--keep-pod", action="store_true", help="do not delete a terminal Pod")
    submit_parser.add_argument("--poll-seconds", type=float, default=5.0)
    submit_parser.add_argument("--max-wait-seconds", type=float)

    for name in ("status", "wait", "progress"):
        command = subparsers.add_parser(name, help=f"{name} a Pod render")
        command.add_argument("--jobs-file", required=True)
        command.add_argument("--poll-seconds", type=float, default=5.0)
        command.add_argument("--max-wait-seconds", type=float)
        command.add_argument("--download", action="store_true")
        command.add_argument("--keep-pod", action="store_true")
        command.add_argument("--work-name")
        command.add_argument("--stream", action="store_true", help="compatibility flag; Pod progress is stored in R2")
        if name == "status":
            command.add_argument("--json", action="store_true", help="emit one RenderPulse-safe status object")
    download = subparsers.add_parser("download", help="download and verify a completed Pod output")
    download.add_argument("--jobs-file", required=True)
    retry = subparsers.add_parser("retry", help="create a new Pod for a failed render")
    retry.add_argument("--jobs-file", required=True)
    _r2_arguments(retry)
    cleanup = subparsers.add_parser("cleanup", help="delete this render's R2 objects")
    cleanup.add_argument("--jobs-file", required=True)
    cleanup.add_argument("--confirm", action="store_true")
    _r2_arguments(cleanup)
    terminate = subparsers.add_parser("terminate", help="terminate Pods for a render immediately")
    terminate.add_argument("--jobs-file", required=True)
    terminate.add_argument("--confirm", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "register-work":
            work = register_work(args.work_name, args.jobs_file, args.work_id)
            print(f"RENDERPULSE_WORK={work['id']}")
            return 0
        if args.command in {"submit", "status", "wait", "progress"}:
            if args.poll_seconds <= 0:
                raise RunpodError("--poll-seconds must be positive")
            if args.max_wait_seconds is not None and args.max_wait_seconds <= 0:
                raise RunpodError("--max-wait-seconds must be positive")
        if args.command == "submit":
            return submit(args)
        if args.command == "status":
            path = Path(args.jobs_file).expanduser().resolve()
            state = _load_json(path)
            controller = RunpodPodController()
            _, failed = refresh_state(controller, state, path, emit_events=not args.json)
            _terminate_finished_pods(
                controller, state, keep=bool(args.keep_pod), emit=not args.json
            )
            if args.json:
                print(json.dumps(work_status_payload(state), sort_keys=True))
            else:
                _print_batch_progress(state)
            return 2 if failed else 0
        if args.command in {"wait", "progress"}:
            return wait_for_jobs(args, Path(args.jobs_file).expanduser().resolve(), download=args.download)
        if args.command == "download":
            return download_results(Path(args.jobs_file).expanduser().resolve())
        if args.command == "retry":
            return retry_failed_pod(args, Path(args.jobs_file).expanduser().resolve())
        if args.command == "cleanup":
            if not args.confirm:
                raise RunpodError("cleanup is destructive; pass --confirm")
            return cleanup_r2_objects(args, Path(args.jobs_file).expanduser().resolve())
        if args.command == "terminate":
            if not args.confirm:
                raise RunpodError("terminate is destructive; pass --confirm")
            return terminate_pods(Path(args.jobs_file).expanduser().resolve())
    except (OSError, RunpodError, ValueError) as exc:
        print(f"runpod pod client error: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
