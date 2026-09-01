from importlib import metadata
import os
from pathlib import Path
import sys

import numpy as np
import pygfx as gfx
from manim_toolchain import narration
from rendercanvas.offscreen import RenderCanvas


toolchain = Path("/Users/taeyoung/Developer/visual-explainer-toolchain")
interpreter = Path(sys.executable).absolute()
expected_environment = (toolchain / ".venv").absolute()
if not interpreter.is_relative_to(expected_environment):
    raise RuntimeError(f"Interpreter escaped the central environment: {interpreter}")

canvas = RenderCanvas(size=(96, 72), pixel_ratio=1)
renderer = gfx.WgpuRenderer(canvas)
scene = gfx.Scene()
scene.add(gfx.Background.from_color("#101820"))
cube = gfx.Mesh(gfx.box_geometry(1, 1, 1), gfx.MeshBasicMaterial(color="#4da3ff"))
scene.add(cube)
camera = gfx.PerspectiveCamera(55, 4 / 3)
camera.show_object(cube, view_dir=(1.8, 1.2, 2.6), scale=1.4)
canvas.request_draw(lambda: renderer.render(scene, camera))
frame = np.asarray(canvas.draw()).copy()
if frame.shape != (72, 96, 4) or float(frame.std()) < 5:
    raise RuntimeError(f"Invalid external frame: {frame.shape}, std={frame.std():.3f}")

output = Path("external-renders/frame.rgba")
output.parent.mkdir(parents=True, exist_ok=True)
output.write_bytes(frame.tobytes())

credential_names = (
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_AUTH_MODE",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "RUNPOD_API_KEY",
    "RUNPOD_ENDPOINT_ID",
    "RUNPOD_API_BASE_URL",
    "R2_ACCOUNT_ID",
    "R2_BUCKET",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "R2_ENDPOINT_URL",
    "R2_PREFIX",
    "R2_URL_EXPIRY_SECONDS",
)
credentials_absent = not any(name in os.environ for name in credential_names)
planned_question = narration("But why should we care about this?")
if planned_question.intent.value != "question" or planned_question.emotion.value != "curious":
    raise RuntimeError("Central narration package did not infer a question delivery")

print(f"EXTERNAL_VISUAL_CWD={Path.cwd()}", flush=True)
print(f"EXTERNAL_VISUAL_PYTHON={interpreter}", flush=True)
print(f"EXTERNAL_VISUAL_PYGFX={metadata.version('pygfx')}", flush=True)
print(f"EXTERNAL_VISUAL_WGPU={metadata.version('wgpu')}", flush=True)
print(f"EXTERNAL_VISUAL_TAICHI={metadata.version('taichi')}", flush=True)
print(f"EXTERNAL_VISUAL_NARRATION={planned_question.intent.value}/{planned_question.emotion.value}", flush=True)
print(f"EXTERNAL_VISUAL_CREDENTIALS_ABSENT={credentials_absent}", flush=True)
print(f"EXTERNAL_VISUAL_OUTPUT={output.resolve()}", flush=True)
