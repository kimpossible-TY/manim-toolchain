#!/usr/bin/env python3
"""Check a resumable PNG sequence for missing, corrupt, or inconsistent frames."""

from __future__ import annotations

import argparse
from pathlib import Path
import struct
import zlib


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def png_dimensions_and_verify(path: Path) -> tuple[int, int]:
    payload = path.read_bytes()
    if not payload.startswith(PNG_SIGNATURE):
        raise ValueError("invalid PNG signature")
    position = len(PNG_SIGNATURE)
    width = height = None
    idat = bytearray()
    while position < len(payload):
        if position + 12 > len(payload):
            raise ValueError("truncated PNG chunk")
        length = struct.unpack(">I", payload[position : position + 4])[0]
        chunk_type = payload[position + 4 : position + 8]
        data_start = position + 8
        data_end = data_start + length
        if data_end + 4 > len(payload):
            raise ValueError("truncated PNG data")
        data = payload[data_start:data_end]
        expected_crc = struct.unpack(">I", payload[data_end : data_end + 4])[0]
        if zlib.crc32(chunk_type + data) & 0xFFFFFFFF != expected_crc:
            raise ValueError("PNG CRC mismatch")
        if chunk_type == b"IHDR":
            width, height = struct.unpack(">II", data[:8])
        elif chunk_type == b"IDAT":
            idat.extend(data)
        elif chunk_type == b"IEND":
            break
        position = data_end + 4
    if width is None or height is None or not idat:
        raise ValueError("PNG lacks IHDR or IDAT data")
    zlib.decompress(idat)
    return width, height


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--frame-start", type=int, required=True)
    parser.add_argument("--frame-end", type=int, required=True)
    parser.add_argument("--padding", type=int, default=4)
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    args = parser.parse_args()
    if args.frame_start > args.frame_end:
        parser.error("--frame-start cannot exceed --frame-end")
    expected = [
        args.directory / f"{args.prefix}{frame:0{args.padding}d}.png"
        for frame in range(args.frame_start, args.frame_end + 1)
    ]
    missing = [path.name for path in expected if not path.is_file() or path.stat().st_size == 0]
    if missing:
        raise SystemExit("Missing or empty frames: " + ", ".join(missing))
    dimensions: set[tuple[int, int]] = set()
    for path in expected:
        try:
            dimensions.add(png_dimensions_and_verify(path))
        except (OSError, ValueError, zlib.error) as error:
            raise SystemExit(f"Corrupt frame {path.name}: {error}") from error
    if len(dimensions) != 1:
        raise SystemExit(f"Inconsistent frame dimensions: {sorted(dimensions)}")
    width, height = dimensions.pop()
    if (args.width is not None and width != args.width) or (
        args.height is not None and height != args.height
    ):
        raise SystemExit(f"Unexpected dimensions: {width}x{height}")
    print(f"FRAME_SEQUENCE_COUNT={len(expected)}")
    print(f"FRAME_SEQUENCE_DIMENSIONS={width}x{height}")
    print("FRAME_SEQUENCE=PASS")


if __name__ == "__main__":
    main()
