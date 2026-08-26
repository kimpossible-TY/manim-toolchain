from importlib import metadata
from pathlib import Path
import sys

from manim import FadeIn, MathTypst, Scene, Typst, UP


class TestScene(Scene):
    def construct(self):
        toolchain = Path("/Users/taeyoung/Projects/manim-toolchain")
        interpreter = Path(sys.executable).absolute()
        expected_environment = (toolchain / ".venv").absolute()

        if not interpreter.is_relative_to(expected_environment):
            raise RuntimeError(f"Interpreter escaped the central environment: {interpreter}")

        print(f"EXTERNAL_SCENE_CWD={Path.cwd()}", flush=True)
        print(f"EXTERNAL_SCENE_PYTHON={interpreter}", flush=True)
        print(f"EXTERNAL_SCENE_MANIM={metadata.version('manim')}", flush=True)
        print(f"EXTERNAL_SCENE_TYPST={metadata.version('typst')}", flush=True)

        heading = Typst("*Central toolchain* from an external project", font_size=38).shift(UP)
        formula = MathTypst(r"integral_0^1 x^2 dif x = 1/3", font_size=58)
        self.play(FadeIn(heading), FadeIn(formula))
        self.wait(0.25)
