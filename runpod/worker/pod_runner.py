#!/usr/bin/env python3
"""Pod entry point for the portable Blender/Cycles render worker.

The local controller provides a base64-encoded render event and a presigned R2
PUT URL.  This process converts the worker's bounded progress events into one
overwritable status document.  It never receives a Runpod API key or R2 secret.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from core import handle_event


def _required_https_environment(name: str) -> str:
    value = os.environ.get(name, "")
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise RuntimeError(f"{name} must be an HTTPS URL")
    return value


def _event_from_environment() -> dict[str, object]:
    encoded = os.environ.get("RENDER_JOB_INPUT_B64", "")
    if not encoded:
        raise RuntimeError("RENDER_JOB_INPUT_B64 is required")
    try:
        value = json.loads(base64.b64decode(encoded, validate=True).decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("RENDER_JOB_INPUT_B64 is invalid") from exc
    if not isinstance(value, dict):
        raise RuntimeError("RENDER_JOB_INPUT_B64 must contain an object")
    return value


def _publish(url: str, payload: dict[str, object]) -> None:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    request = Request(url, data=body, method="PUT")
    try:
        with urlopen(request, timeout=60) as response:
            response.read()
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise RuntimeError("could not publish Pod render status") from exc


def _status(chunk_id: str, status: str, **fields: object) -> dict[str, object]:
    return {
        "schema_version": 1,
        "chunk_id": chunk_id,
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **fields,
    }


def main() -> int:
    status_url = _required_https_environment("RENDER_STATUS_UPLOAD_URL")
    event = _event_from_environment()
    chunk_id = event.get("chunk_id")
    if not isinstance(chunk_id, str) or not chunk_id:
        raise RuntimeError("render event has no chunk_id")
    _publish(status_url, _status(chunk_id, "STARTING"))
    try:
        for output in handle_event(event):
            if output.get("type") == "progress":
                _publish(status_url, _status(chunk_id, "RUNNING", progress=output))
                phase = output.get("phase", "unknown")
                print(f"RUNPOD_POD_PROGRESS phase={phase}", flush=True)
            elif output.get("type") == "result":
                _publish(status_url, _status(chunk_id, "COMPLETED", result=output))
                print("RUNPOD_POD_RENDER=PASS", flush=True)
                return 0
        raise RuntimeError("render worker returned without a result")
    except Exception as exc:
        error = str(exc)
        try:
            _publish(status_url, _status(chunk_id, "FAILED", error=error))
        except Exception as publish_error:
            print(f"failed to publish render failure: {publish_error}", file=sys.stderr, flush=True)
        print(f"RUNPOD_POD_RENDER=FAIL error={error}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
