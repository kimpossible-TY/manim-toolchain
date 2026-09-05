import os
from importlib import metadata
from pathlib import Path
import sys

from manim import FadeIn, MathTypst, Scene, Typst, UP


class TestScene(Scene):
    def construct(self):
        toolchain = Path("/Users/taeyoung/Developer/visual-explainer-toolchain")
        interpreter = Path(sys.executable).absolute()
        expected_environment = (toolchain / ".venv").absolute()

        if not interpreter.is_relative_to(expected_environment):
            raise RuntimeError(f"Interpreter escaped the central environment: {interpreter}")

        print(f"EXTERNAL_SCENE_CWD={Path.cwd()}", flush=True)
        print(f"EXTERNAL_SCENE_PYTHON={interpreter}", flush=True)
        print(f"EXTERNAL_SCENE_MANIM={metadata.version('manim')}", flush=True)
        print(f"EXTERNAL_SCENE_TYPST={metadata.version('typst')}", flush=True)

        cloud_credentials = (
            "RUNPOD_API_KEY",
            "RUNPOD_ENDPOINT_ID",
            "RUNPOD_API_BASE_URL",
            "RUNPOD_POD_IMAGE",
            "RUNPOD_POD_GPU_ID",
            "RUNPOD_POD_CONTAINER_DISK_GB",
            "RUNPOD_POD_TERMINATE_AFTER",
            "RUNPOD_POD_DATA_CENTER_IDS",
            "RUNPOD_REGISTRY_AUTH_ID",
            "RUNPODCTL_BIN",
            "R2_ACCOUNT_ID",
            "R2_BUCKET",
            "R2_ACCESS_KEY_ID",
            "R2_SECRET_ACCESS_KEY",
            "R2_ENDPOINT_URL",
            "R2_PREFIX",
            "R2_URL_EXPIRY_SECONDS",
        )
        if any(name in os.environ for name in cloud_credentials):
            raise RuntimeError("External Manim scene received cloud credentials")
        print("EXTERNAL_SCENE_CLOUD_CREDENTIALS_ABSENT=True", flush=True)

        heading = Typst("*Central toolchain* from an external project", font_size=38).shift(UP)
        formula = MathTypst(r"integral_0^1 x^2 dif x = 1/3", font_size=58)
        self.play(FadeIn(heading), FadeIn(formula))
        self.wait(0.25)
