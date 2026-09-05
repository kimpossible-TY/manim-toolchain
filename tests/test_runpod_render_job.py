"""Offline contracts for the disposable Runpod Pod render workflow."""

from __future__ import annotations

from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zlib


ROOT = Path(__file__).resolve().parents[1]
PREPARE = ROOT / "scripts" / "prepare_runpod_render_job.py"
VERIFY = ROOT / "scripts" / "verify_runpod_render_job.py"
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def png(width: int, height: int) -> bytes:
    raw = b"".join(b"\0" + bytes((40, 80, 120, 255)) * width for _ in range(height))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


class RunpodPodRenderTests(unittest.TestCase):
    def prepare(self, temp: Path, *extra: str) -> Path:
        scene = temp / "scene.blend"
        scene.write_bytes(b"offline fixture")
        job = temp / "render-job"
        result = subprocess.run(
            [
                sys.executable, str(PREPARE), "--scene", str(scene), "--output", str(job),
                "--width", "96", "--height", "54", "--fps", "12", "--frame-start", "0",
                "--frame-end", "1", "--samples", "2", "--device", "auto", *extra,
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return job

    def test_prepare_and_verify_pod_bundle(self) -> None:
        with TemporaryDirectory() as directory:
            job = self.prepare(Path(directory))
            verified = subprocess.run(
                [sys.executable, str(VERIFY), "--job", str(job)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(verified.returncode, 0, verified.stderr + verified.stdout)
            manifest = json.loads((job / "render_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["backend"], "runpod-pod")
            self.assertNotIn("chunk_size", manifest["render"])
            self.assertTrue(manifest["require_gpu"])
            self.assertFalse(any((job / "output").iterdir()))

    def test_sensitive_asset_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            temp = Path(directory)
            scene = temp / "scene.blend"
            scene.write_bytes(b"fixture")
            secret = temp / ".env.local"
            secret.write_text("TOKEN=not-for-upload\n", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable, str(PREPARE), "--scene", str(scene), "--asset-file", str(secret),
                    "--output", str(temp / "render-job"), "--width", "96", "--height", "54",
                    "--fps", "12", "--frame-start", "1", "--frame-end", "1",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("credential-like", result.stderr)

    def test_worker_accepts_one_full_pod_range(self) -> None:
        worker = load_module("runpod_pod_worker_contract", ROOT / "runpod" / "worker" / "core.py")
        with TemporaryDirectory() as directory:
            job = self.prepare(Path(directory))
            manifest, chunk = worker._manifest_and_chunk(
                {"chunk": {"index": 0, "frame_start": 0, "frame_end": 1}}, job
            )
            self.assertEqual(manifest["backend"], "runpod-pod")
            self.assertEqual(chunk["frame_end"], 1)

    def test_worker_progress_is_frame_based(self) -> None:
        worker = load_module("runpod_pod_worker_progress", ROOT / "runpod" / "worker" / "core.py")
        with TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "frame_0000.png").write_bytes(b"non-empty")
            event = worker._frame_progress(output, 0, 2)
            self.assertEqual(event["frames_completed"], 1)
            self.assertEqual(event["percent"], 33.3)

    def test_api_key_is_read_from_environment_only(self) -> None:
        client = load_module("runpod_pod_client_auth", ROOT / "scripts" / "runpod_client.py")
        with TemporaryDirectory() as directory:
            config = Path(directory) / "config.toml"
            config.write_text("[runpod]\napi_key = 'config-key'\n", encoding="utf-8")
            with patch.dict("os.environ", {"RUNPOD_CONFIG_FILE": str(config)}, clear=True):
                self.assertEqual(client._runpod_api_key(), "")
            with patch.dict("os.environ", {"RUNPOD_API_KEY": "env-key"}, clear=True):
                self.assertEqual(client._runpod_api_key(), "env-key")

    def test_controller_creates_pod_with_a_duration_termination_guard(self) -> None:
        client = load_module("runpod_pod_controller", ROOT / "scripts" / "runpod_client.py")
        commands: list[list[str]] = []

        def fake_run(command, **_kwargs):
            commands.append(command)
            if command[-1] == "--help":
                return SimpleNamespace(returncode=0, stdout="--terminate-after", stderr="")
            return SimpleNamespace(returncode=0, stdout='{"id":"pod-123"}', stderr="")

        settings = {
            "image": "registry.example/blender:1", "gpu_id": "NVIDIA GeForce RTX 4090",
            "container_disk_gb": 30, "terminate_after": "4h", "registry_auth_id": None,
            "data_center_ids": "US-CA-2",
        }
        with patch.object(client.subprocess, "run", side_effect=fake_run):
            pod_id = client.RunpodPodController("runpodctl").create(
                settings, {"RENDER_JOB_INPUT_B64": "abc"}, "cycles-smoke"
            )
        self.assertEqual(pod_id, "pod-123")
        self.assertIn("--terminate-after", commands[1])
        self.assertIn("--ssh=false", commands[1])
        self.assertIn("--env", commands[1])
        self.assertIn("--data-center-ids", commands[1])

    def test_controller_treats_missing_pod_as_terminal_and_delete_is_idempotent(self) -> None:
        client = load_module("runpod_pod_controller_missing", ROOT / "scripts" / "runpod_client.py")
        controller = client.RunpodPodController("runpodctl")
        with patch.object(
            controller,
            "_run",
            side_effect=client.RunpodError("failed to get pod: pod not found"),
        ):
            self.assertEqual(controller.runtime_status("pod-gone"), "TERMINATED")
            controller.delete("pod-gone")

    def test_controller_omits_unsupported_optional_termination_flag(self) -> None:
        client = load_module("runpod_pod_controller_legacy_cli", ROOT / "scripts" / "runpod_client.py")
        commands: list[list[str]] = []

        def fake_run(command, **_kwargs):
            commands.append(command)
            if command[-1] == "--help":
                return SimpleNamespace(returncode=0, stdout="--wait-timeout", stderr="")
            return SimpleNamespace(returncode=0, stdout='{"id":"pod-legacy"}', stderr="")

        settings = {
            "image": "registry.example/blender:1", "gpu_id": "NVIDIA GeForce RTX 4090",
            "container_disk_gb": 30, "terminate_after": "4h", "registry_auth_id": None,
            "data_center_ids": None,
        }
        with patch.object(client.subprocess, "run", side_effect=fake_run):
            pod_id = client.RunpodPodController("runpodctl").create(
                settings, {"RENDER_JOB_INPUT_B64": "abc"}, "cycles-legacy"
            )
        self.assertEqual(pod_id, "pod-legacy")
        self.assertNotIn("--terminate-after", commands[1])
        self.assertIn("--ssh=false", commands[1])

    def test_remote_progress_never_regresses_during_archive_upload(self) -> None:
        client = load_module("runpod_pod_client_progress_order", ROOT / "scripts" / "runpod_client.py")
        record = {
            "status": "RUNNING",
            "progress": {"frame": 1, "frames_completed": 1, "percent": 100.0, "samples_completed": 4},
        }
        client._apply_remote_status(
            record,
            {
                "status": "RUNNING",
                "progress": {"frame": 0, "frames_completed": 0, "percent": 0.0, "samples_completed": 0},
            },
        )
        progress = record["progress"]
        self.assertIsInstance(progress, dict)
        self.assertEqual(progress["frames_completed"], 1)
        self.assertEqual(progress["percent"], 100.0)
        self.assertEqual(record["pod_runtime_status"], "RUNNING")

    def test_late_running_status_does_not_downgrade_terminal_record(self) -> None:
        client = load_module("runpod_pod_client_status_order", ROOT / "scripts" / "runpod_client.py")
        record = {"status": "RESULT_PENDING", "completion_error": "waiting for digest"}
        client._apply_remote_status(record, {"status": "RUNNING", "progress": {"frames_completed": 0}})
        self.assertEqual(record["status"], "RESULT_PENDING")

    def test_termination_guard_keeps_runpod_duration_syntax(self) -> None:
        client = load_module("runpod_pod_duration", ROOT / "scripts" / "runpod_client.py")
        args = client.build_parser().parse_args(
            ["submit", "--bundle", "/tmp/render", "--r2", "--pod-image", "image", "--gpu-id", "gpu", "--terminate-after", "2h"]
        )
        settings = client._pod_settings_from_args(args)
        self.assertEqual(settings["terminate_after"], "2h")

    def test_submit_uses_one_pod_and_never_persists_input_urls_in_stdout(self) -> None:
        client = load_module("runpod_pod_client_submit", ROOT / "scripts" / "runpod_client.py")

        class FakeR2:
            bucket = "render-bucket"
            prefix = "manim-render"
            url_expiry_seconds = 3600

            def new_batch_id(self, label: str) -> str:
                return f"{label}-batch"

            def object_key(self, batch_id: str, *parts: str) -> str:
                return "/".join((self.prefix, batch_id, *parts))

            def put_url(self, key: str) -> str:
                return f"https://storage.example/put/{key}"

            def get_url(self, key: str) -> str:
                return f"https://storage.example/get/{key}"

        class FakeController:
            instances: list["FakeController"] = []

            def __init__(self) -> None:
                self.calls: list[tuple[dict[str, object], dict[str, str], str]] = []
                type(self).instances.append(self)

            def create(self, settings, environment, name):
                self.calls.append((settings, environment, name))
                return "pod-test"

        with TemporaryDirectory() as directory:
            temp = Path(directory)
            job = self.prepare(temp)
            args = client.build_parser().parse_args(
                [
                    "submit", "--bundle", str(job), "--r2", "--pod-image", "registry.example/blender:1",
                    "--gpu-id", "NVIDIA GeForce RTX 4090", "--jobs-file", str(temp / "jobs.json"),
                ]
            )
            captured = io.StringIO()
            with (
                patch.object(client.R2Storage, "from_args", return_value=FakeR2()),
                patch.object(client, "RunpodPodController", FakeController),
                patch.object(client, "_upload_with_curl") as upload,
                patch.dict("os.environ", {"RUNPOD_API_KEY": "test-key"}, clear=False),
                redirect_stdout(captured),
            ):
                self.assertEqual(client.submit(args), 0)
            upload.assert_called_once()
            state = json.loads((temp / "jobs.json").read_text(encoding="utf-8"))
            self.assertEqual(state["backend"], "runpod-pod")
            self.assertEqual(state["jobs"][0]["pod_id"], "pod-test")
            self.assertEqual(len(FakeController.instances[0].calls), 1)
            self.assertNotIn("https://", captured.getvalue())

    def test_remote_status_updates_renderpulse_payload_without_urls(self) -> None:
        client = load_module("runpod_pod_client_status", ROOT / "scripts" / "runpod_client.py")
        digest = "a" * 64
        state = {
            "schema_version": 2,
            "backend": "runpod-pod",
            "jobs": [
                {
                    "chunk_id": "pod-000000-000003", "frame_start": 0, "frame_end": 3,
                    "pod_id": "pod-1", "status_download_url": "https://storage.example/status",
                    "status": "STARTING",
                }
            ],
        }
        remote = {
            "status": "COMPLETED",
            "result": {"archive_sha256": digest, "render_device": "GPU"},
        }
        with TemporaryDirectory() as directory, patch.object(client, "_remote_status", return_value=remote):
            path = Path(directory) / "jobs.json"
            captured = io.StringIO()
            with redirect_stdout(captured):
                completed, failed = client.refresh_state(object(), state, path)
        self.assertEqual((completed, failed), (1, 0))
        payload = client.work_status_payload(state)
        self.assertEqual(payload["status"], "COMPLETED")
        self.assertEqual(payload["progress"]["percent"], 100.0)
        self.assertNotIn("https://", json.dumps(payload))
        self.assertNotIn("https://", captured.getvalue())

    def test_download_verifies_one_pod_archive(self) -> None:
        client = load_module("runpod_pod_client_download", ROOT / "scripts" / "runpod_client.py")
        utils = load_module("runpod_pod_utils_download", ROOT / "scripts" / "runpod_job_utils.py")
        with TemporaryDirectory() as directory:
            temp = Path(directory)
            job = self.prepare(temp)
            remote = temp / "remote-output"
            remote.mkdir()
            for frame in (0, 1):
                (remote / f"frame_{frame:04d}.png").write_bytes(png(96, 54))
            (remote / "render_report.json").write_text(
                json.dumps({"engine": "CYCLES", "render_executed": True, "render_device": "GPU"}),
                encoding="utf-8",
            )
            archive = temp / "pod.tar.gz"
            utils.archive_directory(remote, archive)
            state_path = temp / "jobs.json"
            state_path.write_text(
                json.dumps(
                    {
                        "schema_version": 2, "backend": "runpod-pod", "jobs_file": str(state_path),
                        "bundle": str(job), "jobs": [{"chunk_id": "pod-000000-000001", "index": 0,
                        "frame_start": 0, "frame_end": 1, "pod_id": "pod-1", "status": "COMPLETED",
                        "output_download_url": "https://storage.example/output", "result": {"archive_sha256": utils.sha256_file(archive), "render_device": "GPU"}}],
                    }
                ),
                encoding="utf-8",
            )

            def fake_download(_url: str, destination: Path) -> None:
                shutil.copy2(archive, destination)

            with patch.object(client, "_download_file", side_effect=fake_download):
                self.assertEqual(client.download_results(state_path), 0)
            report = json.loads((job / "output" / "render_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["backend"], "runpod-pod")
            self.assertTrue((job / "output" / "frame_0001.png").is_file())

    def test_renderpulse_registry_stays_free_of_state_contents(self) -> None:
        client = load_module("runpod_pod_client_registry", ROOT / "scripts" / "runpod_client.py")
        with TemporaryDirectory() as directory:
            registry = Path(directory) / "works.json"
            jobs = Path(directory) / "one.runpod.json"
            with patch.dict("os.environ", {"RENDER_PULSE_REGISTRY_FILE": str(registry)}):
                first = client.register_work("Pod render", [str(jobs)])
                second = client.register_work("Renamed", [str(jobs)], first["id"])
            content = json.loads(registry.read_text(encoding="utf-8"))
            self.assertEqual(len(content), 1)
            self.assertEqual(content[0]["name"], "Renamed")
            self.assertNotIn("output_download_url", json.dumps(content))

    def test_pod_runner_publishes_progress_and_result(self) -> None:
        worker_directory = ROOT / "runpod" / "worker"
        sys.path.insert(0, str(worker_directory))
        try:
            runner = load_module("runpod_pod_runner", worker_directory / "pod_runner.py")
        finally:
            sys.path.remove(str(worker_directory))
        event = {"chunk_id": "pod-000000-000001"}
        published: list[dict[str, object]] = []
        outputs = iter(
            [
                {"type": "progress", "phase": "render", "frames_completed": 1},
                {"type": "result", "archive_sha256": "b" * 64},
            ]
        )
        with (
            patch.dict(
                "os.environ",
                {
                    "RENDER_STATUS_UPLOAD_URL": "https://storage.example/status",
                    "RENDER_JOB_INPUT_B64": __import__("base64").b64encode(json.dumps(event).encode()).decode(),
                },
                clear=True,
            ),
            patch.object(runner, "handle_event", return_value=outputs),
            patch.object(runner, "_publish", side_effect=lambda _url, value: published.append(value)),
        ):
            self.assertEqual(runner.main(), 0)
        self.assertEqual([item["status"] for item in published], ["STARTING", "RUNNING", "COMPLETED"])


if __name__ == "__main__":
    unittest.main()
