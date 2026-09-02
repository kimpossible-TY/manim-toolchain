"""Robust procedural 삼겹살 shot for a Runpod Cycles test render.

This deliberately uses basic meshes and node materials so it is portable across
the pinned worker Blender build. It is the fallback shot if the richer smoke
variant needs another look-dev pass.
"""

from __future__ import annotations

import math

import bpy
from mathutils import Vector


def set_socket(node, name: str, value) -> None:
    item = node.inputs.get(name)
    if item is not None:
        item.default_value = value


def principled(name: str, color: tuple[float, float, float, float], roughness: float, metallic: float = 0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    node = mat.node_tree.nodes.get("Principled BSDF")
    assert node is not None
    set_socket(node, "Base Color", color)
    set_socket(node, "Roughness", roughness)
    set_socket(node, "Metallic", metallic)
    return mat


def add_cube(name, location, dimensions, mat, bevel_width=0.05, rotation=0.0):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    obj.rotation_euler[2] = rotation
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel_width:
        mod = obj.modifiers.new("rounded edge", "BEVEL")
        mod.width = bevel_width
        mod.segments = 4
    obj.data.materials.append(mat)
    return obj


def add_cylinder(name, location, radius, depth, mat, rotation=(0.0, 0.0, 0.0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=radius, depth=depth, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    mod = obj.modifiers.new("soft grill bar edge", "BEVEL")
    mod.width = min(radius * 0.22, depth * 0.18)
    mod.segments = 3
    obj.data.materials.append(mat)
    return obj


def add_area(name, location, energy, color, size, target):
    bpy.ops.object.light_add(type="AREA", location=location)
    light = bpy.context.object
    light.name = name
    light.data.energy = energy
    light.data.color = color
    light.data.shape = "DISK"
    light.data.size = size
    light.rotation_euler = (Vector(target) - light.location).to_track_quat("-Z", "Y").to_euler()
    return light


def key_camera(camera, frame, location, target, lens):
    camera.location = location
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = lens
    camera.keyframe_insert(data_path="location", frame=frame)
    camera.keyframe_insert(data_path="rotation_euler", frame=frame)
    camera.data.keyframe_insert(data_path="lens", frame=frame)


def build_scene():
    scene = bpy.context.scene
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    scene.frame_start = 1
    scene.frame_end = 24
    scene.render.fps = 24
    scene.render.fps_base = 1.0
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.render.engine = "CYCLES"
    scene.cycles.max_bounces = 4
    scene.cycles.diffuse_bounces = 2
    scene.cycles.glossy_bounces = 2
    scene.cycles.use_denoising = True
    try:
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass

    scene.world.use_nodes = True
    world_bg = scene.world.node_tree.nodes.get("Background")
    if world_bg:
        set_socket(world_bg, "Color", (0.006, 0.003, 0.002, 1))
        set_socket(world_bg, "Strength", 0.10)

    counter_mat = principled("black stone", (0.025, 0.014, 0.010, 1), 0.30)
    grill_mat = principled("seasoned iron", (0.012, 0.013, 0.016, 1), 0.28, 0.72)
    steel_mat = principled("hot steel", (0.11, 0.12, 0.13, 1), 0.22, 0.88)
    meat_mat = principled("seared pork", (0.22, 0.018, 0.006, 1), 0.30)
    fat_mat = principled("pork fat", (0.88, 0.45, 0.15, 1), 0.25)
    char_mat = principled("char", (0.004, 0.001, 0.0005, 1), 0.55)
    ember_mat = principled("ember", (0.72, 0.018, 0.002, 1), 0.30)

    add_cube("counter", (0, 0, -0.86), (16, 16, 0.2), counter_mat, 0.0)
    add_cube("grill body", (0, 0, -0.40), (7.4, 4.8, 0.85), grill_mat, 0.22)
    add_cube("cooking plate", (0, 0, 0.06), (6.9, 4.2, 0.20), grill_mat, 0.13)
    for x in (-2.5, -1.7, -0.85, 0.0, 0.85, 1.7, 2.5):
        add_cylinder("raised grill bar", (x, 0, 0.23), 0.10, 4.1, steel_mat, rotation=(0, math.pi / 2, 0))

    for index, (x, y, r) in enumerate(((-2.2, -0.7, 0.26), (-1.0, 0.5, 0.20), (0.2, -0.65, 0.24), (1.45, 0.56, 0.28), (2.3, -0.45, 0.20))):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=r, location=(x, y, -0.18))
        coal = bpy.context.object
        coal.name = "glowing coal"
        coal.scale = (1.2, 0.72, 0.70)
        coal.data.materials.append(ember_mat if index % 2 == 0 else char_mat)

    # Three thick slices with longitudinal fat layers and fresh grill marks.
    strips = ((-1.22, -0.52, -0.06), (0.05, 0.28, 0.03), (1.30, -0.18, -0.04))
    for strip_index, (cx, cy, angle) in enumerate(strips):
        base = add_cube(f"삼겹살 {strip_index + 1}", (cx, cy, 0.58), (3.55, 0.72, 0.30), meat_mat, 0.13, angle)
        for lane in (-0.23, 0.0, 0.23):
            lane_obj = add_cube("fat layer", (cx, cy, 0.755), (3.20, 0.12, 0.045), fat_mat, 0.035, angle)
            # Offset layers in the strip's local Y direction.
            lane_obj.location.x += -math.sin(angle) * lane
            lane_obj.location.y += math.cos(angle) * lane
        for mark_index, offset in enumerate((-1.18, -0.58, 0.03, 0.67, 1.24)):
            mark = add_cube("dark sear mark", (cx, cy, 0.81), (0.10, 0.62, 0.055), char_mat, 0.02, angle + math.radians(7 if mark_index % 2 else -7))
            mark.location.x += math.cos(angle) * offset
            mark.location.y += math.sin(angle) * offset
        # Animate one droplet of rendered fat per slice.
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.06, location=(cx, cy, 0.86))
        droplet = bpy.context.object
        droplet.name = "sizzling fat droplet"
        droplet.data.materials.append(fat_mat)
        droplet.keyframe_insert(data_path="location", frame=1)
        droplet.location.z += 0.23
        droplet.keyframe_insert(data_path="location", frame=10 + strip_index * 2)
        droplet.location.z = 0.86
        droplet.scale = (0.45, 0.45, 0.45)
        droplet.keyframe_insert(data_path="scale", frame=24)

    ember = bpy.data.lights.new("coal glow", type="POINT")
    ember.energy = 260
    ember.color = (1.0, 0.06, 0.01)
    ember.shadow_soft_size = 1.5
    ember_obj = bpy.data.objects.new("coal glow", ember)
    scene.collection.objects.link(ember_obj)
    ember_obj.location = (0, 0, 0.15)
    ember.keyframe_insert(data_path="energy", frame=1)
    ember.energy = 390
    ember.keyframe_insert(data_path="energy", frame=9)
    ember.energy = 220
    ember.keyframe_insert(data_path="energy", frame=24)

    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0.62))
    focus = bpy.context.object
    bpy.ops.object.camera_add(location=(5.8, -7.8, 3.25))
    camera = bpy.context.object
    camera.name = "grill closeup camera"
    camera.data.sensor_width = 36
    camera.data.dof.use_dof = True
    camera.data.dof.focus_object = focus
    camera.data.dof.aperture_fstop = 1.2
    scene.camera = camera
    key_camera(camera, 1, (5.8, -7.8, 3.25), (0, 0, 0.55), 54)
    key_camera(camera, 12, (3.2, -5.6, 2.45), (0.2, 0, 0.62), 68)
    key_camera(camera, 24, (-4.2, -6.5, 2.85), (0, 0, 0.58), 58)

    add_area("warm kitchen key", (3.5, -3.5, 6.5), 850, (1.0, 0.45, 0.16), 4.0, (0, 0, 0.5))
    add_area("cool rim", (-4.0, -1.5, 3.4), 320, (0.18, 0.30, 1.0), 3.0, (0, 0, 0.6))
    add_area("top softbox", (0, 0, 7.2), 920, (1.0, 0.72, 0.45), 3.8, (0, 0, 0))
    add_area("red backlight", (2.2, 2.4, 3.0), 560, (1.0, 0.06, 0.015), 1.6, (0, 0, 0.5))

    return scene


build_scene()
