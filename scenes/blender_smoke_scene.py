"""Minimal scene used by Blender's real EEVEE and Cycles smoke renders."""

import bpy
from mathutils import Vector


scene = bpy.context.scene
scene.world.color = (0.012, 0.02, 0.04)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, location=(0, 0, 0))
sphere = bpy.context.object
material = bpy.data.materials.new("smoke-blue")
material.diffuse_color = (0.08, 0.42, 0.9, 1.0)
material.metallic = 0.15
material.roughness = 0.28
sphere.data.materials.append(material)

bpy.ops.object.light_add(type="AREA", location=(3.5, -2.5, 4.5))
key = bpy.context.object
key.data.energy = 700
key.data.shape = "DISK"
key.data.size = 4.0

bpy.ops.object.light_add(type="AREA", location=(-3.0, 1.5, 2.0))
fill = bpy.context.object
fill.data.energy = 280
fill.data.size = 3.0

bpy.ops.object.camera_add(location=(0.0, -6.0, 1.4))
camera = bpy.context.object
camera.data.lens = 52
camera.rotation_euler = (Vector((0, 0, 0.15)) - camera.location).to_track_quat("-Z", "Y").to_euler()
scene.camera = camera
