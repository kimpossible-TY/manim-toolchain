"""CPU look-dev preview for the cinematic product test.

This is a graceful fallback for machines where Blender's GPU backend cannot
initialize. It is intentionally a stylized, lighting-first proxy: the
production scene lives in ``scenes/cinematic_product_test.py``.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--hero-frame", type=Path)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=360)
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--frames", type=int, default=96)
    args = parser.parse_args()
    if args.width <= 0 or args.height <= 0 or args.width % 2 or args.height % 2:
        parser.error("width and height must be positive even integers")
    if args.fps <= 0 or args.frames < 2:
        parser.error("fps must be positive and frames must be at least 2")
    return args


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for candidate in candidates:
        if Path(candidate).is_file():
            try:
                return ImageFont.truetype(candidate, size)
            except OSError:
                continue
    return ImageFont.load_default()


def add_glow(base: Image.Image, layer: Image.Image, blur: float = 16, opacity: int = 170) -> Image.Image:
    softened = layer.filter(ImageFilter.GaussianBlur(blur))
    if opacity < 255:
        alpha = softened.getchannel("A").point(lambda value: value * opacity // 255)
        softened.putalpha(alpha)
    return Image.alpha_composite(base, softened)


def background(width: int, height: int, phase: float) -> Image.Image:
    yy, xx = np.mgrid[0:height, 0:width]
    x = xx / max(width - 1, 1)
    y = yy / max(height - 1, 1)
    # Dark navy studio with a soft pool behind the product and a slightly
    # warmer floor. The moving pool suggests a controlled light sweep.
    pool_x = 0.48 + 0.08 * math.sin(math.tau * phase)
    pool = np.exp(-(((x - pool_x) / 0.36) ** 2 + ((y - 0.43) / 0.55) ** 2) * 2.0)
    floor = np.clip((y - 0.57) / 0.43, 0, 1)
    r = 3 + 7 * pool + 6 * floor
    g = 8 + 15 * pool + 5 * floor
    b = 25 + 35 * pool + 13 * floor
    vignette = 1.0 - 0.35 * np.clip(((x - 0.5) / 0.72) ** 2 + ((y - 0.48) / 0.8) ** 2, 0, 1)
    rgb = np.clip(np.stack((r, g, b), axis=2) * vignette[..., None], 0, 255).astype(np.uint8)
    return Image.fromarray(rgb, mode="RGB").convert("RGBA")


def render_frame(width: int, height: int, phase: float) -> Image.Image:
    img = background(width, height, phase)
    draw = ImageDraw.Draw(img, "RGBA")

    # Thin cyan and amber practicals in the deep background.
    practicals = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    pd = ImageDraw.Draw(practicals, "RGBA")
    cyan_x = int(width * (0.17 + 0.012 * math.sin(phase * math.tau)))
    amber_x = int(width * (0.82 - 0.01 * math.sin(phase * math.tau)))
    pd.rounded_rectangle((cyan_x - 2, int(height * 0.17), cyan_x + 2, int(height * 0.88)), radius=2, fill=(24, 137, 255, 210))
    pd.rounded_rectangle((amber_x - 2, int(height * 0.25), amber_x + 2, int(height * 0.83)), radius=2, fill=(255, 65, 18, 200))
    img = add_glow(img, practicals, blur=15, opacity=125)
    img = Image.alpha_composite(img, practicals)

    # Product camera choreography: the proxy follows the same three-beat arc
    # as the Blender scene (wide -> macro -> reveal).
    if phase < 0.35:
        beat = phase / 0.35
        camera_yaw = -0.30 + 0.10 * beat
        scale = 0.88 + 0.17 * beat
        center_x = width * (0.52 - 0.06 * beat)
    elif phase < 0.70:
        beat = (phase - 0.35) / 0.35
        camera_yaw = -0.20 - 0.48 * beat
        scale = 1.05 + 0.12 * math.sin(math.pi * beat)
        center_x = width * (0.46 - 0.10 * beat)
    else:
        beat = (phase - 0.70) / 0.30
        camera_yaw = -0.68 + 0.68 * beat
        scale = 1.04 - 0.06 * beat
        center_x = width * (0.36 + 0.14 * beat)
    center_y = height * (0.57 - 0.035 * math.sin(phase * math.tau))
    body_w = width * 0.285 * scale
    body_h = height * 0.60 * scale
    depth = body_w * (0.18 + 0.12 * abs(math.sin(camera_yaw)))
    skew = depth * math.sin(camera_yaw)
    left = center_x - body_w / 2
    right = center_x + body_w / 2
    top = center_y - body_h / 2
    bottom = center_y + body_h / 2

    # Soft floor halo under the bottle.
    halo = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    hd = ImageDraw.Draw(halo, "RGBA")
    hd.ellipse((center_x - body_w * 0.75, bottom - 3, center_x + body_w * 0.75, bottom + body_w * 0.28), fill=(235, 105, 34, 110))
    img = add_glow(img, halo, blur=18, opacity=130)
    draw = ImageDraw.Draw(img, "RGBA")

    # Bottle side plane: dark cobalt with an orange rim light.
    side = [(right, top + body_w * 0.10), (right + skew, top + body_w * 0.20), (right + skew, bottom - body_w * 0.12), (right, bottom)]
    draw.polygon(side, fill=(6, 25, 75, 245))
    draw.line(side[:2], fill=(255, 94, 37, 220), width=max(1, int(width / 320)))
    draw.line([side[1], side[2]], fill=(214, 75, 32, 150), width=max(1, int(width / 420)))

    # Front face with a vertical lacquer gradient clipped to a rounded mask.
    face_mask = Image.new("L", (width, height), 0)
    md = ImageDraw.Draw(face_mask)
    md.rounded_rectangle((left, top, right, bottom), radius=int(body_w * 0.09), fill=255)
    fy = np.linspace(0, 1, height)[:, None]
    fx = np.linspace(0, 1, width)[None, :]
    sheen = np.exp(-((fx - (0.50 + 0.12 * math.sin(phase * math.tau))) / 0.075) ** 2)
    rr = 6 + 8 * fy + 15 * sheen
    gg = 28 + 27 * fy + 34 * sheen
    bb = 82 + 72 * fy + 90 * sheen
    front_rgb = np.clip(np.stack((rr, gg, bb), axis=2), 0, 255).astype(np.uint8)
    front = Image.fromarray(front_rgb, mode="RGB").convert("RGBA")
    front.putalpha(face_mask)
    img = Image.alpha_composite(img, front)
    draw = ImageDraw.Draw(img, "RGBA")
    draw.rounded_rectangle((left, top, right, bottom), radius=int(body_w * 0.09), outline=(63, 134, 255, 230), width=max(1, int(width / 420)))

    # Cap and top plate, with a brushed champagne highlight.
    cap_h = body_h * 0.12
    cap_left = center_x - body_w * 0.28
    cap_right = center_x + body_w * 0.28
    cap_top = top - cap_h * 0.42
    draw.rounded_rectangle((cap_left, cap_top, cap_right, top + cap_h * 0.18), radius=int(cap_h * 0.20), fill=(5, 8, 17, 255), outline=(118, 129, 152, 230), width=max(1, int(width / 360)))
    draw.ellipse((cap_left + cap_h * 0.06, cap_top - cap_h * 0.15, cap_right - cap_h * 0.06, cap_top + cap_h * 0.22), fill=(172, 73, 24, 245), outline=(255, 174, 84, 210), width=max(1, int(width / 420)))
    draw.line((cap_left + cap_h * 0.13, cap_top + cap_h * 0.04, cap_right - cap_h * 0.14, cap_top + cap_h * 0.02), fill=(255, 206, 133, 230), width=max(1, int(width / 520)))

    # Ivory/gold label and wordmark. The label slightly narrows with the
    # camera angle, retaining the impression of a real wrapped bottle label.
    label_w = body_w * 0.67
    label_h = body_h * 0.24
    label_top = center_y - label_h * 0.10
    label_bottom = label_top + label_h
    draw.rounded_rectangle((center_x - label_w / 2, label_top, center_x + label_w / 2 + skew * 0.18, label_bottom), radius=int(label_h * 0.07), fill=(192, 143, 72, 245), outline=(250, 209, 136, 220), width=max(1, int(width / 480)))
    title_font = font(max(12, int(body_w * 0.19)), bold=True)
    small_font = font(max(7, int(body_w * 0.055)), bold=False)
    draw.text((center_x + skew * 0.04, label_top + label_h * 0.46), "NOVA", font=title_font, anchor="mm", fill=(9, 14, 28, 255), stroke_width=0)
    draw.text((center_x + skew * 0.04, label_top + label_h * 0.79), "01  /  EDP", font=small_font, anchor="mm", fill=(33, 27, 21, 245))

    # Controlled specular streak and a subtle lower reflection.
    streak = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    sd = ImageDraw.Draw(streak, "RGBA")
    highlight_x = center_x - body_w * (0.22 - 0.05 * math.sin(phase * math.tau))
    sd.rounded_rectangle((highlight_x - body_w * 0.028, top + body_h * 0.10, highlight_x + body_w * 0.028, bottom - body_h * 0.16), radius=int(body_w * 0.02), fill=(180, 219, 255, 165))
    streak.putalpha(Image.composite(streak.getchannel("A"), Image.new("L", (width, height), 0), face_mask))
    img = add_glow(img, streak, blur=12, opacity=80)
    img = Image.alpha_composite(img, streak)

    # Filmic vignette and a little grain for a finished commercial look.
    arr = np.asarray(img.convert("RGB")).astype(np.float32)
    yy, xx = np.mgrid[0:height, 0:width]
    vignette = 1.0 - 0.12 * np.clip(((xx - width / 2) / (width * 0.7)) ** 2 + ((yy - height / 2) / (height * 0.8)) ** 2, 0, 1)
    noise = np.random.default_rng(int(phase * 100000 + 7)).normal(0, 0.9, arr.shape[:2])
    arr = np.clip(arr * vignette[..., None] + noise[..., None], 0, 255).astype(np.uint8)
    return Image.fromarray(arr, mode="RGB").convert("RGBA")


def main() -> None:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pixel_format", "rgba",
        "-video_size", f"{args.width}x{args.height}",
        "-framerate", str(args.fps), "-i", "-", "-an",
        "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(args.output),
    ]
    encoder = subprocess.Popen(command, stdin=subprocess.PIPE)
    assert encoder.stdin is not None
    hero = None
    try:
        for index in range(args.frames):
            phase = index / (args.frames - 1)
            frame = render_frame(args.width, args.height, phase)
            if hero is None:
                hero = frame.copy()
            encoder.stdin.write(frame.tobytes())
    finally:
        encoder.stdin.close()
        return_code = encoder.wait()
    if return_code != 0:
        raise RuntimeError(f"FFmpeg exited with status {return_code}")
    if hero is None or not args.output.is_file() or args.output.stat().st_size == 0:
        raise RuntimeError("Preview video was not created")
    if args.hero_frame is not None:
        args.hero_frame.parent.mkdir(parents=True, exist_ok=True)
        hero.convert("RGB").save(args.hero_frame)
    print(f"CPU_PREVIEW_FRAMES={args.frames}")
    print(f"CPU_PREVIEW_OUTPUT={args.output.resolve()}")
    print("CPU_PREVIEW=PASS")


if __name__ == "__main__":
    main()
