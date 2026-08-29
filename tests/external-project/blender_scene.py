"""A Blender-owned scene proving the wrapper preserves an external project."""

from pathlib import Path

import bpy
from mathutils import Vector


print(f"EXTERNAL_BLENDER_CWD={Path.cwd()}", flush=True)
scene = bpy.context.scene
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
cube = bpy.context.object
material = bpy.data.materials.new("external-blue")
material.diffuse_color = (0.15, 0.55, 0.95, 1.0)
cube.data.materials.append(material)
bpy.ops.object.light_add(type="AREA", location=(3, -3, 4))
bpy.context.object.data.energy = 500
bpy.context.object.data.size = 4
bpy.ops.object.camera_add(location=(0, -5, 1.8))
camera = bpy.context.object
camera.rotation_euler = (Vector((0, 0, 0)) - camera.location).to_track_quat("-Z", "Y").to_euler()
scene.camera = camera
