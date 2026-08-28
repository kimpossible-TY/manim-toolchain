"""Run a tiny Taichi particle step and optionally render it with PyGfx."""

import argparse
from pathlib import Path
import subprocess

import numpy as np
import pygfx as gfx
from rendercanvas.offscreen import RenderCanvas
import taichi as ti


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--arch", choices=("auto", "metal", "cpu"), default="auto")
    parser.add_argument("--particles", type=int, default=256)
    parser.add_argument("--width", type=int, default=320)
    parser.add_argument("--height", type=int, default=240)
    parser.add_argument("--numerical-only", action="store_true")
    args = parser.parse_args()
    if args.particles < 8:
        parser.error("particles must be at least 8")
    if args.width <= 0 or args.height <= 0:
        parser.error("width and height must be positive")
    if not args.numerical_only and args.output is None:
        parser.error("--output is required unless --numerical-only is used")
    return args


def initialize_taichi(requested_arch: str) -> None:
    arch = {
        "auto": ti.gpu,
        "metal": ti.metal,
        "cpu": ti.cpu,
    }[requested_arch]
    ti.init(arch=arch, enable_fallback=True, offline_cache=False, default_fp=ti.f32)


def write_png(frame: np.ndarray, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "rawvideo",
        "-pixel_format",
        "rgba",
        "-video_size",
        f"{frame.shape[1]}x{frame.shape[0]}",
        "-i",
        "pipe:0",
        "-frames:v",
        "1",
        str(output),
    ]
    subprocess.run(command, input=frame.tobytes(), check=True)


def main() -> None:
    args = parse_args()
    initialize_taichi(args.arch)

    positions = ti.Vector.field(3, dtype=ti.f32, shape=args.particles)
    velocities = ti.Vector.field(3, dtype=ti.f32, shape=args.particles)

    @ti.kernel
    def initialize():
        for i in positions:
            fraction = ti.cast(i, ti.f32) / ti.cast(args.particles - 1, ti.f32)
            x = 2.0 * fraction - 1.0
            y = 0.32 * ti.sin(18.0 * fraction)
            positions[i] = ti.Vector([x, y, 0.0])
            velocities[i] = ti.Vector([-0.15 * y, 0.15 * x, 0.2])

    @ti.kernel
    def step(dt: ti.f32):
        for i in positions:
            positions[i] += velocities[i] * dt

    initialize()
    before = positions.to_numpy()
    velocity = velocities.to_numpy()
    dt = 0.5
    step(dt)
    after = positions.to_numpy()
    np.testing.assert_allclose(after, before + velocity * dt, rtol=0, atol=1e-6)

    active_arch = str(ti.lang.impl.current_cfg().arch)
    if args.arch == "metal" and ti.lang.impl.current_cfg().arch != ti.metal:
        raise RuntimeError(f"Metal was requested but Taichi selected {active_arch}")
    if args.arch == "cpu" and ti.lang.impl.current_cfg().arch != ti.cpu:
        raise RuntimeError(f"CPU was requested but Taichi selected {active_arch}")
    print(f"TAICHI_ARCH={active_arch}")
    print(f"TAICHI_PARTICLES={args.particles}")
    print("TAICHI_NUMERICAL=PASS")
    if args.numerical_only:
        return

    canvas = RenderCanvas(size=(args.width, args.height), pixel_ratio=1)
    renderer = gfx.WgpuRenderer(canvas)
    scene = gfx.Scene()
    scene.add(gfx.Background.from_color("#071018", "#132c3b"))
    points = gfx.Points(
        gfx.Geometry(positions=np.ascontiguousarray(after, dtype=np.float32)),
        gfx.PointsMaterial(color="#70f0dd", size=5, aa=True),
    )
    scene.add(points)
    camera = gfx.PerspectiveCamera(50, args.width / args.height)
    camera.show_object(points, view_dir=(0.8, 0.6, 3.5), scale=1.2)
    canvas.request_draw(lambda: renderer.render(scene, camera))
    frame = np.asarray(canvas.draw()).copy()
    if frame.shape != (args.height, args.width, 4) or float(frame.std()) < 5:
        raise RuntimeError(f"Invalid Taichi/PyGfx frame: {frame.shape}, std={frame.std():.3f}")

    assert args.output is not None
    write_png(frame, args.output)
    if not args.output.is_file() or args.output.stat().st_size == 0:
        raise RuntimeError(f"Rendered frame was not created: {args.output}")

    adapter = renderer.device.adapter.info
    print(f"TAICHI_PYGFX_BACKEND={adapter.get('backend_type', 'unknown')}")
    print(f"TAICHI_PYGFX_OUTPUT={args.output.resolve()}")
    print("TAICHI_PYGFX=PASS")


if __name__ == "__main__":
    main()
