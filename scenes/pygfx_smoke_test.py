"""Render a short, deterministic PyGfx mesh clip entirely offscreen."""

from __future__ import annotations

import argparse
import math
from pathlib import Path
import subprocess

import numpy as np
import pygfx as gfx
import pylinalg as la
from rendercanvas.offscreen import RenderCanvas


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--width", type=int, default=320)
    parser.add_argument("--height", type=int, default=240)
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--frames", type=int, default=24)
    args = parser.parse_args()
    if args.width <= 0 or args.height <= 0 or args.width % 2 or args.height % 2:
        parser.error("width and height must be positive even integers for H.264")
    if args.fps <= 0 or args.frames < 2:
        parser.error("fps must be positive and frames must be at least 2")
    return args


def start_encoder(output: Path, width: int, height: int, fps: int) -> subprocess.Popen[bytes]:
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
        f"{width}x{height}",
        "-framerate",
        str(fps),
        "-i",
        "pipe:0",
        "-an",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output),
    ]
    return subprocess.Popen(command, stdin=subprocess.PIPE)


def main() -> None:
    args = parse_args()
    canvas = RenderCanvas(size=(args.width, args.height), pixel_ratio=1)
    renderer = gfx.WgpuRenderer(canvas)

    scene = gfx.Scene()
    scene.add(gfx.Background.from_color("#080d18", "#18243a"))

    geometry = gfx.sphere_geometry(radius=1, width_segments=16, height_segments=10)
    surface = gfx.Mesh(
        geometry,
        gfx.MeshPhongMaterial(color="#318ce7", shininess=36, flat_shading=True),
    )
    wireframe = gfx.Mesh(
        geometry,
        gfx.MeshBasicMaterial(color="#d9efff", wireframe=True, wireframe_thickness=1.2),
    )
    wireframe.local.scale = (1.003, 1.003, 1.003)

    model = gfx.Group()
    model.add(surface, wireframe)
    scene.add(model)
    scene.add(gfx.AmbientLight(intensity=0.65))
    key_light = gfx.DirectionalLight(intensity=2.8)
    key_light.local.position = (3, 4, 5)
    scene.add(key_light)

    camera = gfx.PerspectiveCamera(48, args.width / args.height)
    camera.show_object(model, view_dir=(2.8, 1.8, 3.6), scale=1.25)
    canvas.request_draw(lambda: renderer.render(scene, camera))

    encoder = start_encoder(args.output, args.width, args.height, args.fps)
    if encoder.stdin is None:
        raise RuntimeError("FFmpeg stdin pipe was not created")

    first_frame: np.ndarray | None = None
    last_frame: np.ndarray | None = None
    try:
        for frame_index in range(args.frames):
            phase = frame_index / (args.frames - 1)
            model.local.rotation = la.quat_from_euler(
                (0.28 + 0.22 * phase, -0.45 + 0.9 * phase), order="XY"
            )
            orbit = 0.18 * math.sin(math.tau * phase)
            camera.local.x += orbit / args.frames
            camera.look_at(model.world.position)

            frame = np.asarray(canvas.draw()).copy()
            if frame.shape != (args.height, args.width, 4) or frame.dtype != np.uint8:
                raise RuntimeError(f"Unexpected offscreen frame: {frame.shape} {frame.dtype}")
            if first_frame is None:
                first_frame = frame
            last_frame = frame
            encoder.stdin.write(frame.tobytes())
    finally:
        encoder.stdin.close()
        return_code = encoder.wait()

    if return_code:
        raise RuntimeError(f"FFmpeg exited with status {return_code}")
    if first_frame is None or last_frame is None:
        raise RuntimeError("No frames were rendered")
    if float(first_frame.std()) < 5:
        raise RuntimeError("Rendered frame lacks visual variation")
    mean_frame_change = float(
        np.abs(last_frame.astype(np.int16) - first_frame.astype(np.int16)).mean()
    )
    if mean_frame_change < 0.25:
        raise RuntimeError("Rendered frames did not change across the animation")
    if not args.output.is_file() or args.output.stat().st_size == 0:
        raise RuntimeError(f"Video was not created: {args.output}")

    adapter = renderer.device.adapter.info
    print(f"PYGFX_BACKEND={adapter.get('backend_type', 'unknown')}")
    print(f"PYGFX_DEVICE={adapter.get('device', 'unknown')}")
    print(f"PYGFX_FRAME_SHAPE={first_frame.shape}")
    print(f"PYGFX_MEAN_FRAME_CHANGE={mean_frame_change:.3f}")
    print(f"PYGFX_OUTPUT={args.output.resolve()}")
    print("PYGFX_OFFSCREEN=PASS")


if __name__ == "__main__":
    main()
