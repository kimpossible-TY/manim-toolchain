"""Offline tests for the reusable Colab session policy."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts" / "colab_session.py"


FAKE_COLAB = """#!/bin/sh
case "$1" in
    sessions)
        printf '%s\\n' "$FAKE_SESSIONS"
        exit "${FAKE_SESSIONS_EXIT:-0}"
        ;;
    status)
        printf '%s\\n' "$FAKE_STATUS"
        exit "${FAKE_STATUS_EXIT:-0}"
        ;;
    ls)
        printf '%s\\n' "${FAKE_LS_OUTPUT:-frame_0001.png}"
        exit "${FAKE_LS_EXIT:-0}"
        ;;
    new)
        printf 'NEW_ARGS=%s\\n' "$*" >> "$FAKE_LOG"
        printf '%s\\n' "${FAKE_NEW_OUTPUT:-[visual-render] endpoint | Hardware: T4 | Variant: GPU}"
        exit "${FAKE_NEW_EXIT:-0}"
        ;;
    *)
        printf 'unexpected fake colab command: %s\\n' "$*" >&2
        exit 99
        ;;
esac
"""


class ColabSessionPolicyTests(unittest.TestCase):
    def run_helper(
        self,
        *,
        sessions: str,
        status: str = "",
        session: str = "visual-render",
        requested_gpu: str | None = None,
        allow_new: bool = False,
        status_exit: int = 0,
        ls_exit: int = 0,
    ) -> subprocess.CompletedProcess[str]:
        with TemporaryDirectory() as directory:
            temp = Path(directory)
            fake_bin = temp / "bin"
            fake_bin.mkdir()
            fake_colab = fake_bin / "colab"
            fake_colab.write_text(FAKE_COLAB, encoding="utf-8")
            fake_colab.chmod(0o755)
            log_path = temp / "colab.log"
            environment = os.environ.copy()
            environment.update(
                {
                    "PATH": f"{fake_bin}:{environment['PATH']}",
                    "FAKE_SESSIONS": sessions,
                    "FAKE_STATUS": status,
                    "FAKE_STATUS_EXIT": str(status_exit),
                    "FAKE_LS_EXIT": str(ls_exit),
                    "FAKE_LOG": str(log_path),
                }
            )
            arguments = ["--session", session]
            if requested_gpu is not None:
                arguments.extend(("--requested-gpu", requested_gpu))
            if allow_new:
                arguments.append("--allow-new-session")
            result = subprocess.run(
                [sys.executable, str(HELPER), *arguments],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            result.log_text = log_path.read_text(encoding="utf-8") if log_path.exists() else ""  # type: ignore[attr-defined]
            return result

    def test_absent_session_requires_explicit_creation_authorization(self) -> None:
        result = self.run_helper(sessions="")
        self.assertEqual(result.returncode, 3)
        self.assertIn("COLAB_SESSION_ACTION=unavailable", result.stdout)
        self.assertIn("COLAB_SESSION_REASON=session_absent_and_creation_not_authorized", result.stdout)
        self.assertNotIn("NEW_ARGS=", result.log_text)  # type: ignore[attr-defined]

    def test_healthy_default_session_is_reused(self) -> None:
        listing = "[visual-render] endpoint-t4 | Hardware: T4 | Variant: GPU"
        status = listing + " | Status: IDLE"
        result = self.run_helper(sessions=listing, status=status)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("COLAB_SESSION_ACTION=reused", result.stdout)
        self.assertIn("COLAB_REQUESTED_GPU=T4", result.stdout)
        self.assertIn("COLAB_ACTUAL_GPU=T4", result.stdout)
        self.assertIn("COLAB_SESSION_HEALTH=reachable", result.stdout)
        self.assertNotIn("NEW_ARGS=", result.log_text)  # type: ignore[attr-defined]

    def test_custom_session_name_is_used(self) -> None:
        listing = "[blender-l4] endpoint-l4 | Hardware: L4 | Variant: GPU"
        status = listing + " | Status: IDLE"
        result = self.run_helper(
            sessions=listing,
            status=status,
            session="blender-l4",
            requested_gpu="L4",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("COLAB_SESSION=blender-l4", result.stdout)
        self.assertIn("COLAB_SESSION_ACTION=reused", result.stdout)
        self.assertIn("COLAB_ACTUAL_GPU=L4", result.stdout)

    def test_authorized_creation_uses_default_t4(self) -> None:
        result = self.run_helper(
            sessions="",
            status="[visual-render] endpoint-t4 | Hardware: T4 | Variant: GPU | Status: IDLE",
            allow_new=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("COLAB_SESSION_ACTION=created", result.stdout)
        self.assertIn("COLAB_REQUESTED_GPU=T4", result.stdout)
        self.assertIn("NEW_ARGS=new -s visual-render --gpu T4", result.log_text)  # type: ignore[attr-defined]

    def test_authorized_accelerator_override_is_used_for_new_session(self) -> None:
        result = self.run_helper(
            sessions="",
            status="[visual-render] endpoint-l4 | Hardware: L4 | Variant: GPU | Status: IDLE",
            requested_gpu="L4",
            allow_new=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("COLAB_SESSION_ACTION=created", result.stdout)
        self.assertIn("COLAB_ACTUAL_GPU=L4", result.stdout)
        self.assertIn("NEW_ARGS=new -s visual-render --gpu L4", result.log_text)  # type: ignore[attr-defined]

    def test_cpu_override_omits_unsupported_gpu_flag(self) -> None:
        result = self.run_helper(
            sessions="",
            status="[visual-render] endpoint-cpu | Hardware: CPU | Variant: DEFAULT | Status: IDLE",
            requested_gpu="cpu",
            allow_new=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("NEW_ARGS=new -s visual-render", result.log_text)  # type: ignore[attr-defined]
        self.assertNotIn("--gpu", result.log_text)  # type: ignore[attr-defined]

    def test_fixed_accelerator_mismatch_fails_without_creating_another_session(self) -> None:
        listing = "[visual-render] endpoint-l4 | Hardware: L4 | Variant: GPU"
        status = listing + " | Status: IDLE"
        result = self.run_helper(sessions=listing, status=status)
        self.assertEqual(result.returncode, 1)
        self.assertIn("COLAB_SESSION_ACTION=incompatible", result.stdout)
        self.assertIn("COLAB_ACCELERATOR_COMPATIBLE=no", result.stdout)
        self.assertIn("COLAB_SESSION_REASON=session_accelerator_is_fixed", result.stdout)
        self.assertNotIn("NEW_ARGS=", result.log_text)  # type: ignore[attr-defined]

    def test_stale_or_busy_session_fails_without_recreation(self) -> None:
        listing = "[visual-render] endpoint-t4 | Hardware: T4 | Variant: GPU"
        stale = "[colab] Session 'visual-render' not found."
        result = self.run_helper(sessions=listing, status=stale)
        self.assertEqual(result.returncode, 1)
        self.assertIn("COLAB_SESSION_REASON=stale_or_unreachable", result.stdout)
        self.assertNotIn("NEW_ARGS=", result.log_text)  # type: ignore[attr-defined]

        busy = listing + " | Status: BUSY (exec)"
        result = self.run_helper(sessions=listing, status=busy)
        self.assertEqual(result.returncode, 1)
        self.assertIn("COLAB_SESSION_REASON=session_busy", result.stdout)
        self.assertNotIn("NEW_ARGS=", result.log_text)  # type: ignore[attr-defined]


if __name__ == "__main__":
    unittest.main()
