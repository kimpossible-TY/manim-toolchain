#!/usr/bin/env python3
"""Hardware-accelerated video composition and encoding helper.

Auto-detects macOS VideoToolbox (h264_videotoolbox / hevc_videotoolbox) or Linux NVENC,
with graceful fallback to libx264.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Sequence


def get_available_encoders() -> set[str]:
    """Return the set of encoder names supported by the local FFmpeg."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
            check=False,
        )
        encoders: set[str] = set()
        for line in result.stdout.splitlines():
            parts = line.strip().split()
            if len(parts) >= 2 and parts[0].startswith("V"):
                encoders.add(parts[1])
        return encoders
    except Exception:
        return set()


def get_optimal_encoder_args(
    codec: str = "h264",
    bitrate: str | None = None,
    pixel_format: str = "yuv420p",
) -> list[str]:
    """Select the best hardware encoder on the current platform with CPU fallback."""
    encoders = get_available_encoders()
    codec_lower = codec.lower()

    if codec_lower in {"h264", "avc"}:
        if sys.platform == "darwin" and "h264_videotoolbox" in encoders:
            rate = bitrate or "12M"
            return ["-c:v", "h264_videotoolbox", "-b:v", rate, "-pix_fmt", pixel_format]
        if "h264_nvenc" in encoders:
            rate = bitrate or "12M"
            return ["-c:v", "h264_nvenc", "-b:v", rate, "-pix_fmt", pixel_format]
        return ["-c:v", "libx264", "-crf", "18", "-preset", "fast", "-pix_fmt", pixel_format]

    if codec_lower in {"h265", "hevc"}:
        if sys.platform == "darwin" and "hevc_videotoolbox" in encoders:
            rate = bitrate or "18M"
            return ["-c:v", "hevc_videotoolbox", "-b:v", rate, "-tag:v", "hvc1", "-pix_fmt", pixel_format]
        if "hevc_nvenc" in encoders:
            rate = bitrate or "18M"
            return ["-c:v", "hevc_nvenc", "-b:v", rate, "-tag:v", "hvc1", "-pix_fmt", pixel_format]
        return ["-c:v", "libx265", "-crf", "22", "-preset", "fast", "-tag:v", "hvc1", "-pix_fmt", pixel_format]

    if codec_lower == "prores":
        if sys.platform == "darwin" and "prores_videotoolbox" in encoders:
            return ["-c:v", "prores_videotoolbox", "-profile:v", "standard"]
        return ["-c:v", "prores_ks", "-profile:v", "3"]

    return ["-c:v", codec, "-pix_fmt", pixel_format]


def sequence_to_mp4(
    pattern_or_dir: str | Path,
    output: Path,
    *,
    fps: int = 30,
    start_number: int = 1,
    codec: str = "h264",
    bitrate: str | None = None,
    audio: Path | None = None,
) -> None:
    """Convert an image sequence to an MP4 video."""
    input_path = Path(pattern_or_dir)
    if input_path.is_dir():
        found = list(input_path.glob("frame_*.png"))
        if found:
            pattern = str(input_path / "frame_%04d.png")
        else:
            raise FileNotFoundError(f"No frame_*.png images found in {input_path}")
    else:
        pattern = str(pattern_or_dir)

    output.parent.mkdir(parents=True, exist_ok=True)
    encoder_args = get_optimal_encoder_args(codec=codec, bitrate=bitrate)

    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-start_number", str(start_number),
        "-i", pattern,
    ]
    if audio and audio.is_file():
        cmd.extend(["-i", str(audio), "-c:a", "aac", "-b:a", "192k", "-shortest"])
    else:
        cmd.append("-an")

    cmd.extend(encoder_args)
    cmd.extend(["-movflags", "+faststart", str(output)])

    subprocess.run(cmd, check=True)


def concat_clips(
    clips_or_manifest: Sequence[Path] | Path,
    output: Path,
    *,
    reencode: bool = False,
    codec: str = "h264",
    bitrate: str | None = None,
) -> None:
    """Concatenate multiple video clips into a single video."""
    output.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(clips_or_manifest, (list, tuple)):
        manifest_text = "\n".join(f"file '{clip.resolve()}'" for clip in clips_or_manifest)
        manifest_path = output.parent / f".concat_{output.stem}.txt"
        manifest_path.write_text(manifest_text, encoding="utf-8")
        clean_manifest = True
    else:
        manifest_path = clips_or_manifest
        clean_manifest = False

    try:
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(manifest_path),
        ]
        if not reencode:
            cmd.extend(["-c:v", "copy", "-c:a", "copy"])
        else:
            cmd.extend(get_optimal_encoder_args(codec=codec, bitrate=bitrate))
            cmd.extend(["-c:a", "aac", "-b:a", "192k"])

        cmd.extend(["-movflags", "+faststart", str(output)])
        subprocess.run(cmd, check=True)
    finally:
        if clean_manifest and manifest_path.is_file():
            manifest_path.unlink(missing_ok=True)


def mux_audio(
    video: Path,
    audio: Path,
    output: Path,
) -> None:
    """Attach narration or music audio to a video clip using stream copy for video."""
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video),
        "-i", str(audio),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(output),
    ]
    subprocess.run(cmd, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: sequence
    seq_parser = subparsers.add_parser("sequence", help="Convert an image sequence to MP4")
    seq_parser.add_argument("--input", required=True, help="Path to frames dir or pattern (e.g. dir/frame_%%04d.png)")
    seq_parser.add_argument("--output", type=Path, required=True, help="Output MP4 file path")
    seq_parser.add_argument("--fps", type=int, default=30, help="Framerate (default: 30)")
    seq_parser.add_argument("--start-number", type=int, default=1, help="First frame number (default: 1)")
    seq_parser.add_argument("--codec", choices=("h264", "hevc", "prores"), default="h264")
    seq_parser.add_argument("--bitrate", help="Target bitrate (e.g. 12M)")
    seq_parser.add_argument("--audio", type=Path, help="Optional audio track to attach")

    # Subcommand: concat
    concat_parser = subparsers.add_parser("concat", help="Concatenate multiple MP4 clips")
    concat_parser.add_argument("--inputs", nargs="+", type=Path, help="List of video files to concatenate")
    concat_parser.add_argument("--manifest", type=Path, help="Path to segments.txt manifest file")
    concat_parser.add_argument("--output", type=Path, required=True, help="Output MP4 file path")
    concat_parser.add_argument("--reencode", action="store_true", help="Re-encode instead of stream copy")
    concat_parser.add_argument("--codec", choices=("h264", "hevc"), default="h264")
    concat_parser.add_argument("--bitrate", help="Target bitrate if re-encoding")

    # Subcommand: mux-audio
    audio_parser = subparsers.add_parser("mux-audio", help="Attach audio track to video")
    audio_parser.add_argument("--video", type=Path, required=True, help="Input video file")
    audio_parser.add_argument("--audio", type=Path, required=True, help="Input audio file (.wav, .mp3, etc.)")
    audio_parser.add_argument("--output", type=Path, required=True, help="Output MP4 file path")

    # Subcommand: info
    subparsers.add_parser("info", help="Show detected hardware encoders and optimal arguments")

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.command == "info":
        encoders = get_available_encoders()
        print(f"Platform: {sys.platform}")
        print(f"Detected hardware encoders: {[e for e in encoders if any(k in e for k in ('videotoolbox', 'nvenc', 'qsv'))]}")
        print(f"Default H.264 args: {get_optimal_encoder_args('h264')}")
        print(f"Default HEVC args: {get_optimal_encoder_args('hevc')}")
        return

    if args.command == "sequence":
        sequence_to_mp4(
            args.input,
            args.output,
            fps=args.fps,
            start_number=args.start_number,
            codec=args.codec,
            bitrate=args.bitrate,
            audio=args.audio,
        )
        print(f"COMPOSE_SEQUENCE_OUTPUT={args.output.resolve()}")

    elif args.command == "concat":
        if args.manifest:
            concat_clips(args.manifest, args.output, reencode=args.reencode, codec=args.codec, bitrate=args.bitrate)
        elif args.inputs:
            concat_clips(args.inputs, args.output, reencode=args.reencode, codec=args.codec, bitrate=args.bitrate)
        else:
            raise ValueError("Must provide either --inputs or --manifest")
        print(f"COMPOSE_CONCAT_OUTPUT={args.output.resolve()}")

    elif args.command == "mux-audio":
        mux_audio(args.video, args.audio, args.output)
        print(f"COMPOSE_MUX_OUTPUT={args.output.resolve()}")


if __name__ == "__main__":
    main()
