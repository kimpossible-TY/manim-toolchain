#!/usr/bin/env python3
"""Configure, validate, and render a Blender scene without GUI interaction.

Invoke this only through Blender, for example::

    blender --background --python blender_render.py -- --mode preview ...

Scene scripts are ordinary Blender Python and can create or adjust the active
scene.  This runner does not save the source .blend unless --save-blend is
explicitly supplied.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import runpy
import sys
from typing import Any

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from blender_cycles import configure_cycles


def blender_argv() -> list[str]:
    try:
        separator = sys.argv.index("--")
    except ValueError:
        return []
    return sys.argv[separator + 1 :]


def absolute_path(value: Path) -> Path:
    return value.expanduser().resolve()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("preview", "render", "validate"), required=True)
    parser.add_argument("--scene", type=Path, help="Optional existing .blend file to open")
    parser.add_argument("--scene-script", type=Path, help="Optional Python scene script to run")
    parser.add_argument("--output", type=Path, help="PNG output path or image-sequence prefix")
    parser.add_argument("--report", type=Path, help="JSON report written after validation or render")
    parser.add_argument("--engine", choices=("eevee", "cycles"), default="eevee")
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--fps", type=int)
    parser.add_argument("--resolution-percentage", type=int, default=100)
    parser.add_argument("--samples", type=int)
    parser.add_argument("--frame", type=int)
    parser.add_argument("--frame-start", type=int)
    parser.add_argument("--frame-end", type=int)
    parser.add_argument(
        "--device",
        choices=("auto", "cpu", "gpu", "cuda", "optix", "metal", "hip", "oneapi"),
        default="auto",
    )
    parser.add_argument("--require-gpu", action="store_true")
    parser.add_argument("--denoise", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--validate-assets", action="store_true")
    parser.add_argument("--require-portable-assets", action="store_true")
    parser.add_argument("--pack-assets", action="store_true")
    parser.add_argument("--make-paths-relative", action="store_true")
    parser.add_argument("--save-blend", type=Path)
    args = parser.parse_args(blender_argv())
    if args.mode != "validate" and args.output is None:
        parser.error("--output is required for preview and render modes")
    if (args.frame_start is None) != (args.frame_end is None):
        parser.error("--frame-start and --frame-end must be used together")
    if args.frame_start is not None and args.frame_start > args.frame_end:
        parser.error("--frame-start cannot exceed --frame-end")
    if args.frame is not None and args.frame_start is not None:
        parser.error("--frame cannot be combined with --frame-start/--frame-end")
    if (
        args.width is not None
        and args.width <= 0
        or args.height is not None
        and args.height <= 0
        or args.fps is not None
        and args.fps <= 0
    ):
        parser.error("--width, --height, and --fps must be positive")
    if not 1 <= args.resolution_percentage <= 100:
        parser.error("--resolution-percentage must be between 1 and 100")
    if args.samples is not None and args.samples <= 0:
        parser.error("--samples must be positive")
    if args.require_portable_assets:
        args.validate_assets = True
    return args


def load_scene(args: argparse.Namespace) -> None:
    if args.scene is not None:
        scene_path = absolute_path(args.scene)
        if scene_path.suffix.lower() != ".blend" or not scene_path.is_file():
            raise RuntimeError(f"--scene must name an existing .blend file: {scene_path}")
        bpy.ops.wm.open_mainfile(filepath=str(scene_path))
    if args.scene_script is not None:
        script_path = absolute_path(args.scene_script)
        if not script_path.is_file():
            raise RuntimeError(f"Scene script does not exist: {script_path}")
        sys.path.insert(0, str(script_path.parent))
        try:
            runpy.run_path(str(script_path), run_name="__main__")
        finally:
            sys.path.pop(0)


def asset_records() -> list[dict[str, object]]:
    """Return external Blender data paths without changing the scene."""

    records: list[dict[str, object]] = []
    collections = (
        ("images", bpy.data.images),
        ("movieclips", bpy.data.movieclips),
        ("sounds", bpy.data.sounds),
        ("fonts", bpy.data.fonts),
        ("volumes", bpy.data.volumes),
        ("cache_files", bpy.data.cache_files),
    )
    for kind, collection in collections:
        for data_block in collection:
            raw_path = str(getattr(data_block, "filepath", "") or "")
            if not raw_path:
                continue
            packed = bool(getattr(data_block, "packed_file", None))
            library = getattr(data_block, "library", None)
            try:
                resolved = bpy.path.abspath(raw_path, library=library)
            except TypeError:
                resolved = bpy.path.abspath(raw_path)
            records.append(
                {
                    "kind": kind,
                    "name": str(data_block.name),
                    "source_path": raw_path,
                    "relative": raw_path.startswith("//"),
                    "packed": packed,
                    "exists": packed or Path(resolved).is_file(),
                }
            )
    return records


def validate_assets(*, require_portable: bool) -> dict[str, object]:
    records = asset_records()
    missing = [record for record in records if not record["exists"]]
    absolute = [
        record
        for record in records
        if not record["packed"] and not record["relative"]
    ]
    if missing:
        details = ", ".join(f"{item['kind']}:{item['name']}" for item in missing)
        raise RuntimeError(f"Missing external Blender assets: {details}")
    if require_portable and absolute:
        details = ", ".join(f"{item['kind']}:{item['name']}" for item in absolute)
        raise RuntimeError(
            "Remote render bundles require packed assets or Blender-relative paths; "
            f"found absolute paths in {details}"
        )
    return {
        "checked": True,
        "asset_count": len(records),
        "portable": not absolute,
        "assets": records,
    }


def configure_scene(args: argparse.Namespace, scene: Any) -> dict[str, object]:
    if args.width is not None:
        scene.render.resolution_x = args.width
    if args.height is not None:
        scene.render.resolution_y = args.height
    if args.fps is not None:
        scene.render.fps = args.fps
        scene.render.fps_base = 1.0
    scene.render.resolution_percentage = args.resolution_percentage
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.use_file_extension = True

    cycles_report: dict[str, object] | None = None
    if args.engine == "cycles":
        cycles_report = configure_cycles(
            bpy,
            scene,
            requested_device=args.device,
            require_gpu=args.require_gpu,
        )
        if args.samples is not None:
            scene.cycles.samples = args.samples
        scene.cycles.use_denoising = args.denoise
    else:
        available_engines = {
            item.identifier
            for item in scene.render.bl_rna.properties["engine"].enum_items
        }
        eevee_engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in available_engines else "BLENDER_EEVEE"
        scene.render.engine = eevee_engine
        if args.samples is not None and hasattr(scene, "eevee"):
            scene.eevee.taa_render_samples = args.samples

    if args.frame is not None:
        scene.frame_set(args.frame)
    if args.frame_start is not None:
        scene.frame_start = args.frame_start
        scene.frame_end = args.frame_end
    return {"cycles": cycles_report}


def color_management(scene: Any) -> dict[str, object]:
    settings = scene.view_settings
    display = scene.display_settings
    return {
        "view_transform": str(settings.view_transform),
        "look": str(settings.look),
        "exposure": float(settings.exposure),
        "gamma": float(settings.gamma),
        "display_device": str(display.display_device),
        "film_transparent": bool(scene.render.film_transparent),
    }


def report_for(scene: Any, args: argparse.Namespace, configuration: dict[str, object]) -> dict[str, object]:
    report: dict[str, object] = {
        "blender_version": bpy.app.version_string,
        "mode": args.mode,
        "engine": scene.render.engine,
        "render_executed": False,
        "render_device": (
            configuration["cycles"]["configured_device"]
            if configuration["cycles"] is not None
            else "N/A"
        ),
        "cycles": configuration["cycles"],
        "resolution": {
            "width": scene.render.resolution_x,
            "height": scene.render.resolution_y,
            "percentage": scene.render.resolution_percentage,
        },
        "frame_rate": float(scene.render.fps) / float(scene.render.fps_base),
        "frame_range": [scene.frame_start, scene.frame_end],
        "color_management": color_management(scene),
    }
    if args.output is not None:
        report["output"] = str(args.output)
    return report


def render(scene: Any, args: argparse.Namespace, report: dict[str, object]) -> None:
    assert args.output is not None
    output = absolute_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(output)
    if args.frame_start is not None:
        bpy.ops.render.render(animation=True)
        rendered = sorted(output.parent.glob(f"{output.name}*.png"))
        expected_count = args.frame_end - args.frame_start + 1
        if len(rendered) != expected_count or any(path.stat().st_size == 0 for path in rendered):
            raise RuntimeError(
                f"Expected {expected_count} non-empty PNG frames at {output}; found {len(rendered)}"
            )
        report["frames"] = [path.name for path in rendered]
    else:
        bpy.ops.render.render(write_still=True)
        if not output.is_file() or output.stat().st_size == 0:
            raise RuntimeError(f"Blender did not create a non-empty render: {output}")
        report["frames"] = [output.name]
    report["render_executed"] = True
    report["output_exists"] = True


def write_report(report: dict[str, object], report_path: Path | None) -> None:
    if report_path is None:
        return
    target = absolute_path(report_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BLENDER_REPORT={target}")


def main() -> None:
    args = parse_args()
    load_scene(args)
    scene = bpy.context.scene
    configuration = configure_scene(args, scene)
    report = report_for(scene, args, configuration)
    if args.validate_assets:
        report["asset_validation"] = validate_assets(
            require_portable=args.require_portable_assets
        )
    if args.pack_assets:
        bpy.ops.file.pack_all()
    if args.make_paths_relative:
        bpy.ops.file.make_paths_relative()
    if args.save_blend is not None:
        target = absolute_path(args.save_blend)
        target.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(target))
        report["saved_blend"] = str(args.save_blend)
    if args.mode != "validate":
        render(scene, args, report)
    write_report(report, args.report)
    if report["render_executed"]:
        print(f"BLENDER_RENDER_ENGINE={report['engine']}")
        print(f"BLENDER_RENDER_DEVICE={report['render_device']}")
        print("BLENDER_RENDER=PASS")
    else:
        print("BLENDER_ASSET_VALIDATION=PASS")


if __name__ == "__main__":
    main()
