#!/usr/bin/env python3
"""Resolve and validate a named Colab session without silently allocating one.

This helper intentionally speaks only the installed official CLI.  The CLI
does not expose machine-readable session output, so the parser is kept small
and strict around its current ``sessions``/``status`` display format.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import subprocess
import sys


DEFAULT_SESSION_NAME = "visual-render"
DEFAULT_GPU = "T4"
SUPPORTED_GPU_NAMES = frozenset({"T4", "L4", "G4", "H100", "A100"})


@dataclass(frozen=True)
class SessionDisplay:
    hardware: str
    variant: str
    status: str | None = None


def canonical_requested_gpu(value: str) -> str:
    """Return a supported canonical request, with CPU as an explicit sentinel."""

    normalized = value.strip().upper()
    if normalized == "CPU":
        return "CPU"
    if normalized in SUPPORTED_GPU_NAMES:
        return normalized
    supported = ", ".join((*sorted(SUPPORTED_GPU_NAMES), "cpu"))
    raise ValueError(f"unsupported Colab accelerator {value!r}; choose one of: {supported}")


def canonical_reported_gpu(value: str) -> str:
    """Normalize the CLI's ``Hardware:`` value for compatibility checks."""

    normalized = value.strip().upper()
    if normalized in {"CPU", "NONE"}:
        return "CPU"
    if normalized in SUPPORTED_GPU_NAMES:
        return normalized
    raise ValueError(f"Colab reported an unsupported hardware value: {value!r}")


def _run_colab(arguments: list[str]) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            ["colab", *arguments],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None


def _command_output(result: subprocess.CompletedProcess[str]) -> str:
    return "\n".join(part for part in (result.stdout, result.stderr) if part)


def _forward_diagnostics(result: subprocess.CompletedProcess[str]) -> None:
    output = _command_output(result).strip()
    if output:
        print(output, file=sys.stderr)


def _parse_session_display(output: str, session_name: str) -> SessionDisplay | None:
    prefix = f"[{session_name}] "
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line.startswith(prefix):
            continue
        fields: dict[str, str] = {}
        for field in line.split(" | ")[1:]:
            if ": " in field:
                key, value = field.split(": ", 1)
                fields[key] = value
        hardware = fields.get("Hardware")
        variant = fields.get("Variant")
        if hardware is None or variant is None:
            return None
        return SessionDisplay(
            hardware=hardware,
            variant=variant,
            status=fields.get("Status"),
        )
    return None


def _emit(
    *,
    session_name: str,
    requested_gpu: str,
    action: str,
    health: str | None = None,
    status: str | None = None,
    actual_gpu: str | None = None,
    compatible: bool | None = None,
    reason: str | None = None,
) -> None:
    print(f"COLAB_SESSION={session_name}")
    print(f"COLAB_REQUESTED_GPU={requested_gpu}")
    print(f"COLAB_SESSION_ACTION={action}")
    if health is not None:
        print(f"COLAB_SESSION_HEALTH={health}")
    if status is not None:
        print(f"COLAB_SESSION_STATUS={status}")
    if actual_gpu is not None:
        print(f"COLAB_ACTUAL_GPU={actual_gpu}")
    if compatible is not None:
        print(f"COLAB_ACCELERATOR_COMPATIBLE={'yes' if compatible else 'no'}")
    if reason is not None:
        print(f"COLAB_SESSION_REASON={reason}")


def _failure_for_action(action: str) -> str:
    return "unavailable" if action == "reused" else "created"


def _inspect_session(
    *,
    session_name: str,
    requested_gpu: str,
    action: str,
) -> int:
    """Confirm hardware, idle state, and a responsive contents endpoint."""

    status_result = _run_colab(["status", "-s", session_name])
    if status_result is None:
        _emit(
            session_name=session_name,
            requested_gpu=requested_gpu,
            action=_failure_for_action(action),
            health="unavailable",
            reason="colab_cli_not_found",
        )
        return 127
    if status_result.returncode != 0:
        _forward_diagnostics(status_result)
        _emit(
            session_name=session_name,
            requested_gpu=requested_gpu,
            action=_failure_for_action(action),
            health="unavailable",
            reason="session_status_failed",
        )
        return 1

    display = _parse_session_display(_command_output(status_result), session_name)
    if display is None:
        _emit(
            session_name=session_name,
            requested_gpu=requested_gpu,
            action=_failure_for_action(action),
            health="unavailable",
            reason="stale_or_unreachable",
        )
        return 1

    try:
        actual_gpu = canonical_reported_gpu(display.hardware)
    except ValueError as error:
        _emit(
            session_name=session_name,
            requested_gpu=requested_gpu,
            action=_failure_for_action(action),
            health="unavailable",
            status=display.status,
            reason="unknown_reported_accelerator",
        )
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    if actual_gpu != requested_gpu:
        _emit(
            session_name=session_name,
            requested_gpu=requested_gpu,
            action="incompatible" if action == "reused" else "created",
            health="reachable",
            status=display.status,
            actual_gpu=actual_gpu,
            compatible=False,
            reason="session_accelerator_is_fixed",
        )
        return 1

    status = (display.status or "").strip()
    if not status.startswith("IDLE"):
        _emit(
            session_name=session_name,
            requested_gpu=requested_gpu,
            action=_failure_for_action(action),
            health="reachable",
            status=status or None,
            actual_gpu=actual_gpu,
            compatible=True,
            reason="session_busy",
        )
        return 1

    ls_result = _run_colab(["ls", "-s", session_name, "/content"])
    if ls_result is None:
        _emit(
            session_name=session_name,
            requested_gpu=requested_gpu,
            action=_failure_for_action(action),
            health="unavailable",
            status=status,
            actual_gpu=actual_gpu,
            compatible=True,
            reason="colab_cli_not_found",
        )
        return 127
    if ls_result.returncode != 0:
        _forward_diagnostics(ls_result)
        _emit(
            session_name=session_name,
            requested_gpu=requested_gpu,
            action=_failure_for_action(action),
            health="unavailable",
            status=status,
            actual_gpu=actual_gpu,
            compatible=True,
            reason="stale_or_unreachable",
        )
        return 1

    _emit(
        session_name=session_name,
        requested_gpu=requested_gpu,
        action=action,
        health="reachable",
        status=status,
        actual_gpu=actual_gpu,
        compatible=True,
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", default=DEFAULT_SESSION_NAME)
    parser.add_argument("--requested-gpu", default=DEFAULT_GPU)
    parser.add_argument(
        "--allow-new-session",
        action="store_true",
        help="authorize allocation when the requested named session is absent",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.session or any(character in args.session for character in "\r\n"):
        print("COLAB_SESSION_ACTION=unavailable")
        print("COLAB_SESSION_REASON=invalid_session_name")
        return 2

    try:
        requested_gpu = canonical_requested_gpu(args.requested_gpu)
    except ValueError as error:
        print("COLAB_SESSION_ACTION=unavailable")
        print("COLAB_SESSION_REASON=unsupported_accelerator")
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    sessions_result = _run_colab(["sessions"])
    if sessions_result is None:
        _emit(
            session_name=args.session,
            requested_gpu=requested_gpu,
            action="unavailable",
            health="unavailable",
            reason="colab_cli_not_found",
        )
        return 127
    if sessions_result.returncode != 0:
        _forward_diagnostics(sessions_result)
        _emit(
            session_name=args.session,
            requested_gpu=requested_gpu,
            action="unavailable",
            health="unavailable",
            reason="session_list_failed",
        )
        return 1

    existing = _parse_session_display(_command_output(sessions_result), args.session)
    if existing is not None:
        return _inspect_session(
            session_name=args.session,
            requested_gpu=requested_gpu,
            action="reused",
        )

    if not args.allow_new_session:
        _emit(
            session_name=args.session,
            requested_gpu=requested_gpu,
            action="unavailable",
            health="absent",
            reason="session_absent_and_creation_not_authorized",
        )
        print(
            "A new Colab runtime was not allocated. Re-run with "
            "--allow-new-session only after explicit authorization.",
            file=sys.stderr,
        )
        return 3

    create_args = ["new", "-s", args.session]
    if requested_gpu != "CPU":
        create_args.extend(("--gpu", requested_gpu))
    create_result = _run_colab(create_args)
    if create_result is None:
        _emit(
            session_name=args.session,
            requested_gpu=requested_gpu,
            action="unavailable",
            health="unavailable",
            reason="colab_cli_not_found",
        )
        return 127
    _forward_diagnostics(create_result)
    if create_result.returncode != 0:
        _emit(
            session_name=args.session,
            requested_gpu=requested_gpu,
            action="unavailable",
            health="unavailable",
            reason="session_allocation_failed",
        )
        return 1

    return _inspect_session(
        session_name=args.session,
        requested_gpu=requested_gpu,
        action="created",
    )


if __name__ == "__main__":
    raise SystemExit(main())
