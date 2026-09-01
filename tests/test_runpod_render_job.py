"""Offline contract tests for the Runpod bundle, client, and worker boundary."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tarfile
from tempfile import TemporaryDirectory
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


class RunpodRenderJobTests(unittest.TestCase):
    def test_runpod_api_key_can_use_cli_config_without_printing_it(self) -> None:
        client = load_module("runpod_client_auth_test", ROOT / "scripts" / "runpod_client.py")
        with TemporaryDirectory() as directory:
            config = Path(directory) / "config.toml"
            config.write_text("[runpod]\napi_key = 'config-key'\n", encoding="utf-8")
            with patch.dict("os.environ", {"RUNPOD_CONFIG_FILE": str(config)}, clear=True):
                self.assertEqual(client._runpod_api_key(), "config-key")

    def prepare(self, temp: Path, *extra: str) -> Path:
        scene = temp / "scene.blend"
        scene.write_bytes(b"offline fixture")
        job = temp / "render-job"
        result = subprocess.run(
            [
                sys.executable,
                str(PREPARE),
                "--scene",
                str(scene),
                "--output",
                str(job),
                "--width",
                "96",
                "--height",
                "54",
                "--fps",
                "12",
                "--frame-start",
                "0",
                "--frame-end",
                "121",
                "--chunk-size",
                "60",
                "--samples",
                "2",
                "--device",
                "auto",
                *extra,
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return job

    def test_prepare_and_verify_runpod_bundle(self) -> None:
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
            self.assertEqual(manifest["backend"], "runpod-serverless")
            self.assertEqual(manifest["render_engine"], "CYCLES")
            self.assertTrue(manifest["require_gpu"])
            self.assertEqual(manifest["render"]["chunk_size"], 60)
            self.assertFalse(any((job / "output").iterdir()))

    def test_sensitive_asset_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            temp = Path(directory)
            scene = temp / "scene.blend"
            scene.write_bytes(b"offline fixture")
            secret = temp / ".env.local"
            secret.write_text("TOKEN=not-for-upload\n", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(PREPARE),
                    "--scene",
                    str(scene),
                    "--asset-file",
                    str(secret),
                    "--output",
                    str(temp / "render-job"),
                    "--width",
                    "96",
                    "--height",
                    "54",
                    "--fps",
                    "12",
                    "--frame-start",
                    "1",
                    "--frame-end",
                    "1",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("credential-like", result.stderr)

    def test_chunk_ids_and_worker_contract(self) -> None:
        client = load_module("runpod_client_test", ROOT / "scripts" / "runpod_client.py")
        worker = load_module("runpod_worker_test", ROOT / "runpod" / "worker" / "core.py")
        with TemporaryDirectory() as directory:
            job = self.prepare(Path(directory))
            manifest = json.loads((job / "render_manifest.json").read_text(encoding="utf-8"))
            chunks = client._chunk_records(manifest, 60)
            self.assertEqual(
                [(item["frame_start"], item["frame_end"]) for item in chunks],
                [(0, 59), (60, 119), (120, 121)],
            )
            loaded, chunk = worker._manifest_and_chunk(
                {
                    "chunk": chunks[1],
                },
                job,
            )
            self.assertEqual(loaded["backend"], "runpod-serverless")
            self.assertEqual(chunk["frame_start"], 60)

    def test_safe_extract_rejects_traversal(self) -> None:
        utils = load_module("runpod_utils_test", ROOT / "scripts" / "runpod_job_utils.py")
        with TemporaryDirectory() as directory:
            temp = Path(directory)
            archive_path = temp / "unsafe.tar.gz"
            with tarfile.open(archive_path, "w:gz") as archive:
                info = tarfile.TarInfo("../escape.txt")
                payload = b"nope"
                info.size = len(payload)
                import io

                archive.addfile(info, io.BytesIO(payload))
            with self.assertRaises(ValueError):
                utils.safe_extract_tar(archive_path, temp / "extract")

    def test_submit_fans_out_chunks_without_networking_in_test(self) -> None:
        client = load_module("runpod_client_submit_test", ROOT / "scripts" / "runpod_client.py")

        class FakeApi:
            def __init__(self, endpoint_id: str, api_key: str, base_url: str) -> None:
                self.calls = []

            def submit(self, payload: dict[str, object], policy: dict[str, int]) -> dict[str, object]:
                self.calls.append((payload, policy))
                return {"id": f"fake-job-{len(self.calls)}"}

        with TemporaryDirectory() as directory:
            temp = Path(directory)
            job = self.prepare(temp)
            args = client.build_parser().parse_args(
                [
                    "--endpoint-id",
                    "endpoint-test",
                    "submit",
                    "--bundle",
                    str(job),
                    "--input-url",
                    "https://storage.example/input.tar.gz",
                    "--output-url-template",
                    "https://storage.example/{chunk_id}.tar.gz",
                    "--jobs-file",
                    str(temp / "jobs.json"),
                ]
            )
            with patch.object(client, "RunpodApi", FakeApi), patch.dict(
                "os.environ", {"RUNPOD_API_KEY": "test-key"}, clear=False
            ):
                result = client.submit(args)
            self.assertEqual(result, 0)
            state = json.loads((temp / "jobs.json").read_text(encoding="utf-8"))
            self.assertEqual([item["job_id"] for item in state["jobs"]], [
                "fake-job-1",
                "fake-job-2",
                "fake-job-3",
            ])
            self.assertTrue((temp / "jobs.json").stat().st_mode & 0o077 == 0)

    def test_r2_mode_uploads_once_and_generates_chunk_urls(self) -> None:
        client = load_module("runpod_client_r2_submit_test", ROOT / "scripts" / "runpod_client.py")

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

        class FakeApi:
            calls: list[dict[str, object]] = []

            def __init__(self, endpoint_id: str, api_key: str, base_url: str) -> None:
                self.calls = []
                type(self).calls = self.calls

            def submit(self, payload: dict[str, object], policy: dict[str, int]) -> dict[str, object]:
                self.calls.append(payload)
                return {"id": f"fake-r2-job-{len(self.calls)}"}

        with TemporaryDirectory() as directory:
            temp = Path(directory)
            job = self.prepare(temp)
            args = client.build_parser().parse_args(
                [
                    "--endpoint-id",
                    "endpoint-test",
                    "submit",
                    "--bundle",
                    str(job),
                    "--r2",
                    "--jobs-file",
                    str(temp / "jobs.json"),
                ]
            )
            with patch.object(client.R2Storage, "from_args", return_value=FakeR2()), patch.object(
                client, "RunpodApi", FakeApi
            ), patch.object(client, "_upload_with_curl") as upload, patch.dict(
                "os.environ", {"RUNPOD_API_KEY": "test-key"}, clear=False
            ):
                result = client.submit(args)
            self.assertEqual(result, 0)
            upload.assert_called_once()
            self.assertEqual(len(FakeApi.calls), 3)
            self.assertTrue(all("bundle_url" in payload for payload in FakeApi.calls))
            self.assertEqual(len({payload["output_upload_url"] for payload in FakeApi.calls}), 3)
            state = json.loads((temp / "jobs.json").read_text(encoding="utf-8"))
            self.assertEqual(state["storage"]["provider"], "cloudflare-r2")
            self.assertEqual(state["storage"]["bucket"], "render-bucket")

    def test_download_verifies_and_merges_a_completed_chunk(self) -> None:
        client = load_module("runpod_client_download_test", ROOT / "scripts" / "runpod_client.py")
        utils = load_module("runpod_utils_download_test", ROOT / "scripts" / "runpod_job_utils.py")

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

        with TemporaryDirectory() as directory:
            temp = Path(directory)
            job = self.prepare(temp)
            manifest_path = job / "render_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["render"]["frame_end"] = 1
            manifest["render"]["chunk_size"] = 2
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            remote_output = temp / "remote-output"
            remote_output.mkdir()
            for frame in (0, 1):
                (remote_output / f"frame_{frame:04d}.png").write_bytes(png(96, 54))
            (remote_output / "render_report.json").write_text(
                json.dumps({"engine": "CYCLES", "render_executed": True, "render_device": "GPU"}),
                encoding="utf-8",
            )
            archive = temp / "chunk.tar.gz"
            utils.archive_directory(remote_output, archive)
            jobs_path = temp / "jobs.json"
            state = {
                "schema_version": 1,
                "bundle": str(job),
                "jobs": [
                    {
                        "chunk_id": "chunk-0000-000000-000001",
                        "index": 0,
                        "frame_start": 0,
                        "frame_end": 1,
                        "job_id": "job-1",
                        "status": "COMPLETED",
                        "output_download_url": "https://storage.example/chunk.tar.gz",
                        "result": {
                            "archive_sha256": utils.sha256_file(archive),
                            "render_device": "GPU",
                        },
                    }
                ],
            }
            jobs_path.write_text(json.dumps(state), encoding="utf-8")

            def fake_download(_url: str, destination: Path) -> None:
                shutil.copy2(archive, destination)

            with patch.object(client, "_download_file", side_effect=fake_download):
                result = client.download_results(jobs_path)
            self.assertEqual(result, 0)
            self.assertTrue((job / "output" / "frame_0000.png").is_file())
            self.assertTrue((job / "output" / "frame_0001.png").is_file())
            report = json.loads((job / "output" / "render_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["backend"], "runpod-serverless")
            self.assertEqual(report["render_device"], "GPU")

    def test_retry_resubmits_only_failed_r2_chunks_with_fresh_urls(self) -> None:
        client = load_module("runpod_client_retry_test", ROOT / "scripts" / "runpod_client.py")

        class FakeR2:
            bucket = "render-bucket"
            prefix = "manim-render"
            url_expiry_seconds = 3600

            def object_key(self, batch_id: str, *parts: str) -> str:
                return "/".join((self.prefix, batch_id, *parts))

            def get_url(self, key: str) -> str:
                return f"https://storage.example/get/{key}"

            def put_url(self, key: str) -> str:
                return f"https://storage.example/put/{key}"

        class FakeApi:
            def __init__(self, endpoint_id: str, api_key: str, base_url: str) -> None:
                self.calls = []

            def submit(self, payload: dict[str, object], policy: dict[str, int]) -> dict[str, object]:
                self.calls.append((payload, policy))
                return {"id": "retry-job-1"}

        with TemporaryDirectory() as directory:
            temp = Path(directory)
            job = self.prepare(temp)
            jobs_path = temp / "jobs.json"
            state = {
                "schema_version": 1,
                "endpoint_id": "endpoint-test",
                "bundle": str(job),
                "bundle_sha256": "a" * 64,
                "storage": {
                    "provider": "cloudflare-r2",
                    "batch_id": "render-job-batch",
                    "input_key": "manim-render/render-job-batch/input.tar.gz",
                },
                "jobs": [
                    {
                        "chunk_id": "chunk-0000-000000-000059",
                        "index": 0,
                        "frame_start": 0,
                        "frame_end": 59,
                        "job_id": "failed-job-1",
                        "status": "FAILED",
                    },
                    {
                        "chunk_id": "chunk-0001-000060-000119",
                        "index": 1,
                        "frame_start": 60,
                        "frame_end": 119,
                        "job_id": "completed-job-1",
                        "status": "COMPLETED",
                    },
                ],
            }
            jobs_path.write_text(json.dumps(state), encoding="utf-8")
            args = client.build_parser().parse_args(
                [
                    "--endpoint-id",
                    "endpoint-test",
                    "retry",
                    "--jobs-file",
                    str(jobs_path),
                ]
            )
            with patch.object(client.R2Storage, "from_args", return_value=FakeR2()), patch.object(
                client, "RunpodApi", FakeApi
            ), patch.dict("os.environ", {"RUNPOD_API_KEY": "test-key"}, clear=False):
                result = client.retry_failed_jobs(args, jobs_path)
            self.assertEqual(result, 0)
            updated = json.loads(jobs_path.read_text(encoding="utf-8"))
            self.assertEqual(updated["jobs"][0]["job_id"], "retry-job-1")
            self.assertEqual(updated["jobs"][0]["status"], "IN_QUEUE")
            self.assertTrue(updated["jobs"][0]["output_download_url"].startswith("https://storage.example/get/"))
            self.assertEqual(updated["jobs"][1]["job_id"], "completed-job-1")

    def test_cleanup_deletes_exact_r2_batch_objects_and_marks_state(self) -> None:
        client = load_module("runpod_client_cleanup_test", ROOT / "scripts" / "runpod_client.py")

        class FakeR2:
            prefix = "manim-render"

            def object_key(self, batch_id: str, *parts: str) -> str:
                return "/".join((self.prefix, batch_id, *parts))

            def delete_url(self, key: str) -> str:
                return f"https://storage.example/delete/{key}"

        with TemporaryDirectory() as directory:
            temp = Path(directory)
            jobs_path = temp / "jobs.json"
            jobs_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "storage": {
                            "provider": "cloudflare-r2",
                            "batch_id": "render-job-batch",
                            "input_key": "manim-render/render-job-batch/input.tar.gz",
                        },
                        "jobs": [
                            {"chunk_id": "chunk-0000-000000-000059"},
                            {"chunk_id": "chunk-0001-000060-000119"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            args = client.build_parser().parse_args(
                ["cleanup", "--jobs-file", str(jobs_path), "--confirm"]
            )
            deleted: list[str] = []
            with patch.object(client.R2Storage, "from_args", return_value=FakeR2()), patch.object(
                client, "_delete_with_curl", side_effect=lambda url: deleted.append(url)
            ):
                result = client.cleanup_r2_objects(args, jobs_path)
            self.assertEqual(result, 0)
            self.assertEqual(len(deleted), 3)
            self.assertTrue(all(url.startswith("https://storage.example/delete/") for url in deleted))
            updated = json.loads(jobs_path.read_text(encoding="utf-8"))
            self.assertTrue(updated["cleaned_up"])


if __name__ == "__main__":
    unittest.main()
