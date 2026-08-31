"""Offline regression tests for generated render-job bundles."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
PREPARE = ROOT / "scripts" / "prepare_blender_render_job.py"
VERIFY = ROOT / "scripts" / "verify_render_job.py"
STOP = ROOT / "bin" / "visual-colab-stop"


def run_prepare(output: Path, scene: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(PREPARE),
            "--scene",
            str(scene),
            "--output",
            str(output),
            "--width",
            "96",
            "--height",
            "54",
            "--fps",
            "12",
            "--frame-start",
            "1",
            "--frame-end",
            "2",
            "--samples",
            "2",
            "--device",
            "cpu",
            "--skip-scene-validation",
            *extra,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


FAKE_COLAB_REMOTE = r'''
import json
import os
from pathlib import Path
import struct
import sys
import tarfile
import tempfile
import zlib


def log(message):
    with Path(os.environ["FAKE_LOG"]).open("a", encoding="utf-8") as handle:
        handle.write(message + "\n")


def png(width, height):
    raw = b"".join(b"\0" + bytes((64, 96, 128, 255)) * width for _ in range(height))

    def chunk(kind, data):
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


command = sys.argv[1]
if command == "sessions":
    print(os.environ.get("FAKE_SESSIONS", ""))
elif command == "status":
    print(os.environ["FAKE_STATUS"])
elif command == "ls":
    log("LS")
    print("content")
elif command == "new":
    log("NEW " + " ".join(sys.argv[2:]))
elif command == "upload":
    log("UPLOAD " + " ".join(sys.argv[2:]))
elif command == "exec":
    log("EXEC " + " ".join(sys.argv[2:]))
elif command == "download":
    local_path = Path(sys.argv[-1])
    local_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "output"
        output.mkdir()
        for frame in (1, 2):
            (output / f"frame_{frame:04d}.png").write_bytes(png(96, 54))
        (output / "render_report.json").write_text(
            json.dumps({"engine": "CYCLES", "render_executed": True, "render_device": "CPU"}),
            encoding="utf-8",
        )
        with tarfile.open(local_path, "w:gz") as archive:
            archive.add(output, arcname="output")
    log("DOWNLOAD " + " ".join(sys.argv[2:]))
elif command == "stop":
    log("STOP " + " ".join(sys.argv[2:]))
else:
    raise SystemExit(f"unexpected fake colab command: {sys.argv}")
'''


class RenderJobBundleTests(unittest.TestCase):
    def test_prepared_bundle_passes_existing_verifier(self) -> None:
        with TemporaryDirectory() as directory:
            temp = Path(directory)
            scene = temp / "scene.blend"
            scene.write_bytes(b"offline fixture")
            job = temp / "render-job"
            prepared = run_prepare(job, scene)
            self.assertEqual(prepared.returncode, 0, prepared.stderr)

            verified = subprocess.run(
                [
                    sys.executable,
                    str(VERIFY),
                    "--job",
                    str(job),
                    "--frame-start",
                    "1",
                    "--frame-end",
                    "2",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(verified.returncode, 0, verified.stderr + verified.stdout)
            self.assertIn("RENDER_JOB_VALIDATION=PASS", verified.stdout)
            manifest = json.loads((job / "render_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["colab_session"], "visual-render")
            self.assertEqual(manifest["colab_gpu"], "T4")
            self.assertEqual(manifest["colab_session_policy"], "reuse-before-create")

    def test_sensitive_asset_is_rejected_before_bundle_creation(self) -> None:
        with TemporaryDirectory() as directory:
            temp = Path(directory)
            scene = temp / "scene.blend"
            scene.write_bytes(b"offline fixture")
            secret = temp / ".env.local"
            secret.write_text("TOKEN=not-for-upload\n", encoding="utf-8")
            job = temp / "render-job"
            result = run_prepare(job, scene, "--asset-file", str(secret))
            self.assertEqual(result.returncode, 2)
            self.assertIn("credential-like", result.stderr)
            self.assertFalse(job.exists())

    def test_generated_shell_has_reusable_defaults_and_no_unconditional_stop(self) -> None:
        with TemporaryDirectory() as directory:
            bundle = Path(directory) / "bundle"
            bundle.mkdir()
            (bundle / "output").mkdir()
            import importlib.util

            spec = importlib.util.spec_from_file_location("prepare_bundle", PREPARE)
            self.assertIsNotNone(spec)
            module = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            spec.loader.exec_module(module)
            manifest = {
                "colab_gpu": "T4",
                "render": {
                    "width": 96,
                    "height": 54,
                    "fps": 12,
                    "frame_start": 1,
                    "frame_end": 2,
                    "samples": 2,
                    "denoise": True,
                },
                "requested_compute_device": "cpu",
                "require_gpu": False,
                "scene_script": None,
            }
            module.write_bootstrap(bundle, manifest)
            module.write_colab_files(bundle, manifest)

            commands = (bundle / "colab_commands.sh").read_text(encoding="utf-8")
            self.assertEqual(
                subprocess.run(["bash", "-n", str(bundle / "colab_commands.sh")], check=False).returncode,
                0,
            )
            self.assertIn('SESSION_NAME="${COLAB_SESSION:-visual-render}"', commands)
            self.assertIn('REQUESTED_GPU="${COLAB_GPU:-T4}"', commands)
            self.assertIn("colab sessions", commands)
            self.assertIn("colab status", commands)
            self.assertIn("colab ls", commands)
            self.assertIn("--allow-new-session", commands)
            self.assertIn("--stop-after-job", commands)
            self.assertIn('if [[ "$STOP_AFTER_JOB" == "1" ]]; then', commands)
            self.assertEqual(commands.count('colab stop -s "$SESSION_NAME"'), 1)
            self.assertNotIn("/content/render-job.tar.gz", commands)
            self.assertNotIn("/content/render-output.tar.gz", commands)
            self.assertIn('REMOTE_JOB_DIRECTORY="/content/manim-toolchain/jobs/$JOB_ID"', commands)
            self.assertIn('REMOTE_INPUT_ARCHIVE="/content/manim-toolchain-upload-$JOB_ID.tar.gz"', commands)
            self.assertIn('REMOTE_OUTPUT_ARCHIVE="/content/manim-toolchain-output-$JOB_ID.tar.gz"', commands)
            self.assertIn("COLAB_SESSION_LEFT_RUNNING", commands)

            bootstrap = (bundle / "bootstrap.sh").read_text(encoding="utf-8")
            self.assertEqual(
                subprocess.run(["bash", "-n", str(bundle / "bootstrap.sh")], check=False).returncode,
                0,
            )
            self.assertIn('BLENDER_VERSION="${BLENDER_VERSION:-4.2.3}"', bootstrap)
            self.assertIn("BLENDER_TARBALL_URL", bootstrap)
            self.assertIn("tar -xf", bootstrap)
            self.assertNotIn("apt-get install", bootstrap)
            subprocess.run(
                [sys.executable, "-m", "py_compile", str(bundle / "run_colab_job.py"), str(bundle / "cleanup_colab_job.py")],
                cwd=ROOT,
                check=True,
            )

    def test_explicit_stop_wrapper_is_valid_and_defaults_to_visual_render(self) -> None:
        self.assertEqual(subprocess.run(["bash", "-n", str(STOP)], check=False).returncode, 0)
        help_result = subprocess.run([str(STOP), "--help"], capture_output=True, text=True, check=False)
        self.assertEqual(help_result.returncode, 0)
        self.assertIn("visual-render", help_result.stdout)

    def test_job_paths_include_runtime_unique_id(self) -> None:
        with TemporaryDirectory() as directory:
            bundle = Path(directory) / "bundle"
            bundle.mkdir()
            (bundle / "output").mkdir()
            import importlib.util

            spec = importlib.util.spec_from_file_location("prepare_paths", PREPARE)
            assert spec is not None and spec.loader is not None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            manifest = {
                "colab_gpu": "T4",
                "render": {
                    "width": 96,
                    "height": 54,
                    "fps": 12,
                    "frame_start": 1,
                    "frame_end": 2,
                    "samples": 2,
                    "denoise": True,
                },
                "requested_compute_device": "cpu",
                "require_gpu": False,
                "scene_script": None,
            }
            module.write_colab_files(bundle, manifest)
            commands = (bundle / "colab_commands.sh").read_text(encoding="utf-8")
            self.assertIn("$(date -u +%Y%m%dT%H%M%SZ)-$$", commands)
            self.assertIn("COLAB_JOB_ID", commands)
            remote_runner = (bundle / "run_colab_job.py").read_text(encoding="utf-8")
            self.assertIn("__REMOTE_JOB_DIRECTORY__", remote_runner)
            self.assertIn("cwd=job_dir", remote_runner)

    def test_generated_workflow_reuses_without_stop_and_supports_created_disposable_job(self) -> None:
        with TemporaryDirectory() as directory:
            temp = Path(directory)
            fake_bin = temp / "bin"
            fake_bin.mkdir()
            fake_colab = fake_bin / "colab"
            fake_colab.write_text(f"#!{sys.executable}\n" + FAKE_COLAB_REMOTE, encoding="utf-8")
            fake_colab.chmod(0o755)
            environment = os.environ.copy()
            environment["PATH"] = f"{fake_bin}:{environment['PATH']}"

            scene = temp / "scene.blend"
            scene.write_bytes(b"offline fixture")
            reused_job = temp / "reused-job"
            self.assertEqual(run_prepare(reused_job, scene).returncode, 0)
            reused_log = temp / "reused.log"
            environment.update(
                {
                    "FAKE_LOG": str(reused_log),
                    "FAKE_SESSIONS": "[visual-render] endpoint-t4 | Hardware: T4 | Variant: GPU",
                    "FAKE_STATUS": "[visual-render] endpoint-t4 | Hardware: T4 | Variant: GPU | Status: IDLE",
                }
            )
            reused = subprocess.run(
                [str(reused_job / "colab_commands.sh")],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(reused.returncode, 0, reused.stderr + reused.stdout)
            self.assertIn("COLAB_SESSION_ACTION=reused", reused.stdout)
            self.assertIn("REMOTE_EXECUTION=completed", reused.stdout)
            self.assertIn("COLAB_SESSION_LEFT_RUNNING=yes", reused.stdout)
            self.assertNotIn("STOP", reused_log.read_text(encoding="utf-8"))
            self.assertTrue((reused_job / "output" / "frame_0001.png").is_file())

            created_job = temp / "created-job"
            self.assertEqual(run_prepare(created_job, scene).returncode, 0)
            created_log = temp / "created.log"
            environment.update(
                {
                    "FAKE_LOG": str(created_log),
                    "FAKE_SESSIONS": "",
                    "FAKE_STATUS": "[visual-render] endpoint-t4 | Hardware: T4 | Variant: GPU | Status: IDLE",
                }
            )
            created = subprocess.run(
                [str(created_job / "colab_commands.sh"), "--allow-new-session", "--stop-after-job"],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(created.returncode, 0, created.stderr + created.stdout)
            self.assertIn("COLAB_SESSION_ACTION=created", created.stdout)
            self.assertIn("COLAB_SESSION_LEFT_RUNNING=no", created.stdout)
            created_log_text = created_log.read_text(encoding="utf-8")
            self.assertIn("NEW -s visual-render --gpu T4", created_log_text)
            self.assertIn("STOP -s visual-render", created_log_text)

    def test_parallel_render_bundle_configuration(self) -> None:
        with TemporaryDirectory() as directory:
            temp = Path(directory)
            scene = temp / "scene.blend"
            scene.write_bytes(b"offline fixture")
            job = temp / "parallel-job"
            prepared = run_prepare(job, scene, "--workers", "6", "--engine", "eevee")
            self.assertEqual(prepared.returncode, 0, prepared.stderr)

            manifest = json.loads((job / "render_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["render_engine"], "EEVEE")
            self.assertEqual(manifest["render"]["workers"], 6)
            self.assertTrue((job / "parallel_blender_render.py").is_file())

            bootstrap = (job / "bootstrap.sh").read_text(encoding="utf-8")
            self.assertIn("parallel_blender_render.py", bootstrap)
            self.assertIn("--workers 6", bootstrap)
            self.assertIn("--engine eevee", bootstrap)


if __name__ == "__main__":
    unittest.main()
