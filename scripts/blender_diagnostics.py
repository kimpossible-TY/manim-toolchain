"""Run real tiny EEVEE and Cycles CPU renders for environment diagnostics."""

from __future__ import annotations

from pathlib import Path
import tempfile
import sys

import bpy
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from blender_cycles import configure_cycles


def build_scene() -> object:
    scene = bpy.context.scene
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
    cube = bpy.context.object
    material = bpy.data.materials.new("diagnostic-blue")
    material.diffuse_color = (0.08, 0.35, 0.85, 1.0)
    cube.data.materials.append(material)
    bpy.ops.object.light_add(type="AREA", location=(3, -3, 4))
    bpy.context.object.data.energy = 500
    bpy.context.object.data.size = 4
    bpy.ops.object.camera_add(location=(0, -5, 1.8))
    camera = bpy.context.object
    camera.rotation_euler = (Vector((0, 0, 0)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = camera
    scene.render.resolution_x = 64
    scene.render.resolution_y = 64
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    return scene


def render(scene: object, output: Path) -> None:
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError(f"Blender did not produce {output}")


def main() -> None:
    scene = build_scene()
    with tempfile.TemporaryDirectory(prefix="manim-toolchain-blender-") as directory:
        output_dir = Path(directory)
        available_engines = {
            item.identifier for item in scene.render.bl_rna.properties["engine"].enum_items
        }
        eevee_engine = (
            "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in available_engines else "BLENDER_EEVEE"
        )
        scene.render.engine = eevee_engine
        render(scene, output_dir / "eevee.png")
        print("BLENDER_EEVEE_BACKGROUND=PASS")
        cycles = configure_cycles(bpy, scene, requested_device="cpu")
        scene.cycles.samples = 1
        render(scene, output_dir / "cycles-cpu.png")
        print("BLENDER_CYCLES_CPU=PASS")
        print(f"BLENDER_CYCLES_DEVICE={cycles['configured_device']}")
        devices = cycles.get("devices", [])
        print("BLENDER_CYCLES_DEVICES=" + ", ".join(str(device) for device in devices))
    print(f"BLENDER_VERSION={bpy.app.version_string}")
    print(f"BLENDER_RENDER_ENGINES={eevee_engine},CYCLES")


if __name__ == "__main__":
    main()
