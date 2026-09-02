"""Cinematic 삼겹살 grill shot for Runpod Cycles.

The scene is procedural and self-contained so the render bundle contains no
external food or environment assets. It emphasizes close camera work, warm
coal light, glossy fat, char marks, and slow curling smoke.
"""

from __future__ import annotations

import math

import bpy
from mathutils import Vector


def socket(node, name: str, value) -> None:
    item = node.inputs.get(name)
    if item is not None:
        item.default_value = value


def material_principled(
    name: str,
    color: tuple[float, float, float, float],
    *,
    metallic: float = 0.0,
    roughness: float = 0.4,
    coat: float = 0.0,
) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    assert bsdf is not None
    socket(bsdf, "Base Color", color)
    socket(bsdf, "Metallic", metallic)
    socket(bsdf, "Roughness", roughness)
    socket(bsdf, "Coat Weight", coat)
    socket(bsdf, "Clearcoat", coat)
    return mat


def meat_material() -> bpy.types.Material:
    mat = bpy.data.materials.new("marbled pork belly")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    assert bsdf is not None
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 3.8
    noise.inputs["Detail"].default_value = 5.0
    noise.inputs["Roughness"].default_value = 0.72
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.18
    ramp.color_ramp.elements[0].color = (0.055, 0.008, 0.004, 1)
    ramp.color_ramp.elements[1].position = 0.82
    ramp.color_ramp.elements[1].color = (0.36, 0.038, 0.012, 1)
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.22
    bump.inputs["Distance"].default_value = 0.08
    socket(bsdf, "Roughness", 0.3)
    socket(bsdf, "Coat Weight", 0.28)
    socket(bsdf, "Specular IOR Level", 0.42)
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def fat_material() -> bpy.types.Material:
    mat = bpy.data.materials.new("rendered pork fat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    assert bsdf is not None
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 8.0
    noise.inputs["Detail"].default_value = 2.5
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.35, 0.12, 0.035, 1)
    ramp.color_ramp.elements[1].color = (0.95, 0.62, 0.22, 1)
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.16
    bump.inputs["Distance"].default_value = 0.04
    socket(bsdf, "Roughness", 0.26)
    socket(bsdf, "Coat Weight", 0.22)
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def volume_material(name: str, density: float, color: tuple[float, float, float, float]) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    volume = nodes.new("ShaderNodeVolumePrincipled")
    socket(volume, "Density", density)
    socket(volume, "Color", color)
    socket(volume, "Anisotropy", 0.25)
    output = nodes.new("ShaderNodeOutputMaterial")
    links.new(volume.outputs["Volume"], output.inputs["Volume"])
    return mat


def apply(obj: bpy.types.Object, mat: bpy.types.Material) -> None:
    obj.data.materials.clear()
    obj.data.materials.append(mat)


def bevel(obj: bpy.types.Object, width: float, segments: int = 4) -> None:
    mod = obj.modifiers.new("soft edge", "BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = "ANGLE"


def local_box(
    name: str,
    parent: bpy.types.Object,
    location: tuple[float, float, float],
    scale: tuple[float, float, float],
    mat: bpy.types.Material,
    bevel_width: float = 0.05,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
    obj = bpy.context.object
    obj.name = name
    obj.parent = parent
    obj.location = location
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel(obj, bevel_width, 4)
    apply(obj, mat)
    return obj


def local_cylinder(
    name: str,
    parent: bpy.types.Object,
    location: tuple[float, float, float],
    radius: float,
    depth: float,
    mat: bpy.types.Material,
    rotation: tuple[float, float, float] = (0, 0, 0),
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=radius, depth=depth, location=(0, 0, 0))
    obj = bpy.context.object
    obj.name = name
    obj.parent = parent
    obj.location = location
    obj.rotation_euler = rotation
    bevel(obj, min(radius * 0.22, depth * 0.25), 3)
    apply(obj, mat)
    return obj


def add_area(name: str, location: tuple[float, float, float], energy: float, color: tuple[float, float, float], size: float, target: Vector) -> bpy.types.Object:
    bpy.ops.object.light_add(type="AREA", location=location)
    light = bpy.context.object
    light.name = name
    light.data.energy = energy
    light.data.color = color
    light.data.shape = "DISK"
    light.data.size = size
    light.rotation_euler = (target - light.location).to_track_quat("-Z", "Y").to_euler()
    return light


def add_point(name: str, location: tuple[float, float, float], energy: float, color: tuple[float, float, float], radius: float) -> bpy.types.Object:
    bpy.ops.object.light_add(type="POINT", location=location)
    light = bpy.context.object
    light.name = name
    light.data.energy = energy
    light.data.color = color
    light.data.shadow_soft_size = radius
    return light


def camera_key(camera: bpy.types.Object, frame: int, location: tuple[float, float, float], target: Vector, lens: float) -> None:
    camera.location = location
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = lens
    camera.keyframe_insert(data_path="location", frame=frame)
    camera.keyframe_insert(data_path="rotation_euler", frame=frame)
    camera.data.keyframe_insert(data_path="lens", frame=frame)


def bezier(action: bpy.types.Action | None) -> None:
    if action is None:
        return
    for curve in action.fcurves:
        for point in curve.keyframe_points:
            point.interpolation = "BEZIER"


def create_pork_strip(parent: bpy.types.Object, location: tuple[float, float, float], angle: float, meat: bpy.types.Material, fat: bpy.types.Material, char: bpy.types.Material) -> bpy.types.Object:
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0))
    strip = bpy.context.object
    strip.name = "삼겹살 strip"
    strip.parent = parent
    strip.location = location
    strip.rotation_euler[2] = angle

    local_box("pork belly seared base", strip, (0, 0, 0), (1.78, 0.36, 0.15), meat, 0.12)
    for lane in (-0.22, 0.0, 0.22):
        local_box("fat marbling", strip, (0, lane, 0.145), (1.62, 0.075, 0.028), fat, 0.035)
    # Dark sear marks cross the fatty layers and give the grill contact points
    # a readable rhythm in the close shot.
    for index, x in enumerate((-1.22, -0.62, 0.02, 0.67, 1.23)):
        mark = local_box("charred grill mark", strip, (x, 0, 0.185), (0.055, 0.33, 0.022), char, 0.02)
        mark.rotation_euler[2] = math.radians(-7 if index % 2 else 7)

    # A few hot fat beads animate upward as the pan sizzles.
    for index, (x, y) in enumerate(((-0.82, -0.18), (0.56, 0.13), (1.08, -0.12))):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.045, location=(0, 0, 0))
        bead = bpy.context.object
        bead.name = "hot fat bead"
        bead.parent = strip
        bead.location = (x, y, 0.25)
        apply(bead, fat)
        bead.scale = (1, 1, 0.65)
        bead.keyframe_insert(data_path="location", frame=1)
        bead.location.z += 0.18 + index * 0.025
        bead.keyframe_insert(data_path="location", frame=18 + index * 5)
        bead.location.z = 0.25
        bead.keyframe_insert(data_path="location", frame=48)
        bead.scale = (0.5, 0.5, 0.3)
        bead.keyframe_insert(data_path="scale", frame=48)
    return strip


def build_scene() -> bpy.types.Scene:
    scene = bpy.context.scene
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in (bpy.data.materials, bpy.data.curves, bpy.data.cameras, bpy.data.lights):
        for block in list(collection):
            if block.users == 0:
                collection.remove(block)

    scene.frame_start = 1
    scene.frame_end = 48
    scene.render.fps = 24
    scene.render.fps_base = 1.0
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.render.engine = "CYCLES"
    scene.cycles.max_bounces = 5
    scene.cycles.diffuse_bounces = 2
    scene.cycles.glossy_bounces = 3
    scene.cycles.transmission_bounces = 3
    scene.cycles.volume_bounces = 1
    scene.cycles.use_denoising = True
    try:
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass

    scene.world.use_nodes = True
    world_bg = scene.world.node_tree.nodes.get("Background")
    if world_bg is not None:
        socket(world_bg, "Color", (0.008, 0.004, 0.003, 1))
        socket(world_bg, "Strength", 0.12)

    grill_mat = material_principled("seasoned cast iron", (0.012, 0.014, 0.018, 1), metallic=0.78, roughness=0.28)
    steel_mat = material_principled("grill steel edge", (0.13, 0.14, 0.16, 1), metallic=0.88, roughness=0.22)
    counter_mat = material_principled("dark stone counter", (0.025, 0.018, 0.016, 1), metallic=0.05, roughness=0.32)
    meat_mat = meat_material()
    fat_mat = fat_material()
    char_mat = material_principled("blackened char", (0.006, 0.002, 0.001, 1), metallic=0.0, roughness=0.56)
    coal_mat = material_principled("coal ember", (0.06, 0.005, 0.002, 1), metallic=0.0, roughness=0.8)
    ember_mat = material_principled("red hot ember", (0.55, 0.018, 0.002, 1), metallic=0.0, roughness=0.32)
    smoke_mat = volume_material("soft cooking smoke", 0.055, (0.47, 0.42, 0.38, 1))

    bpy.ops.mesh.primitive_plane_add(size=24, location=(0, 0, -0.88))
    counter = bpy.context.object
    counter.name = "stone counter"
    apply(counter, counter_mat)
    bpy.ops.mesh.primitive_plane_add(size=18, location=(0, 4.2, 3.1), rotation=(math.pi / 2, 0, 0))
    back = bpy.context.object
    back.name = "dark restaurant backdrop"
    apply(back, counter_mat)

    # Rectangular grill body and raised lip.
    bpy.ops.mesh.primitive_cube_add(location=(0, 0, -0.42), scale=(3.55, 2.18, 0.42))
    grill_group = bpy.context.object
    grill_group.name = "grill body"
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel(grill_group, 0.18, 6)
    apply(grill_group, grill_mat)

    bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0.04), scale=(3.35, 1.96, 0.12))
    plate = bpy.context.object
    plate.name = "grill cooking plate"
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel(plate, 0.12, 5)
    apply(plate, grill_mat)
    for x in (-2.55, -1.7, -0.85, 0, 0.85, 1.7, 2.55):
        local_cylinder("raised grill bar", plate, (x, 0, 0.19), 0.095, 3.62, steel_mat, rotation=(0, math.pi / 2, 0))

    # Ember bed and a few irregular glowing coals under the bars.
    for index, (x, y, scale) in enumerate(((-2.0, -0.65, 0.26), (-1.0, 0.62, 0.21), (0.1, -0.55, 0.23), (1.15, 0.58, 0.3), (2.2, -0.46, 0.22))):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=scale, location=(x, y, -0.18))
        coal = bpy.context.object
        coal.name = "glowing coal"
        apply(coal, ember_mat if index % 2 == 0 else coal_mat)
        coal.scale = (1.25, 0.72, 0.7)
    ember_light = add_point("coal orange bounce", (0, -0.1, -0.05), 220, (1.0, 0.075, 0.012), 1.8)
    ember_light.data.keyframe_insert(data_path="energy", frame=1)
    ember_light.data.energy = 340
    ember_light.data.keyframe_insert(data_path="energy", frame=17)
    ember_light.data.energy = 190
    ember_light.data.keyframe_insert(data_path="energy", frame=36)
    ember_light.data.energy = 280
    ember_light.data.keyframe_insert(data_path="energy", frame=48)

    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0))
    food_rig = bpy.context.object
    food_rig.name = "food turntable"
    create_pork_strip(food_rig, (-1.25, -0.45, 0.48), math.radians(-6), meat_mat, fat_mat, char_mat)
    create_pork_strip(food_rig, (0.15, 0.25, 0.52), math.radians(4), meat_mat, fat_mat, char_mat)
    create_pork_strip(food_rig, (1.38, -0.18, 0.50), math.radians(-3), meat_mat, fat_mat, char_mat)

    # Slow pan drift makes the shot feel filmed rather than diagrammed.
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0.65))
    focus = bpy.context.object
    focus.name = "macro focus target"
    bpy.ops.object.camera_add(location=(5.7, -7.8, 3.3))
    camera = bpy.context.object
    camera.name = "grill macro camera"
    camera.data.sensor_width = 36
    camera.data.dof.use_dof = True
    camera.data.dof.focus_object = focus
    camera.data.dof.aperture_fstop = 1.1
    scene.camera = camera
    camera_key(camera, 1, (5.7, -7.8, 3.3), Vector((0.1, 0.0, 0.55)), 55)
    camera_key(camera, 18, (4.2, -6.3, 2.45), Vector((0.2, 0.0, 0.62)), 68)
    camera_key(camera, 34, (-3.2, -6.2, 2.25), Vector((0.0, 0.0, 0.62)), 64)
    camera_key(camera, 48, (-4.7, -7.0, 2.85), Vector((0.0, 0.0, 0.58)), 58)
    bezier(camera.animation_data.action if camera.animation_data else None)

    warm = add_area("warm kitchen key", (3.8, -3.0, 6.2), 780, (1.0, 0.47, 0.19), 4.2, Vector((0, 0, 0.5)))
    warm.data.shape = "RECTANGLE"
    warm.data.size_y = 2.2
    fill = add_area("cool edge fill", (-4.0, -2.0, 3.0), 260, (0.19, 0.32, 1.0), 3.0, Vector((0, 0, 0.7)))
    rim = add_area("red grill rim", (1.2, 2.5, 3.0), 620, (1.0, 0.075, 0.02), 1.8, Vector((0, 0, 0.6)))
    top = add_area("soft overhead", (0, -0.5, 7.0), 980, (1.0, 0.73, 0.48), 3.8, Vector((0, 0, 0)))

    # Volumetric smoke puffs with gentle, looping motion.
    for index, (x, y, z, scale) in enumerate(((-0.85, 0.0, 1.12, 0.75), (0.2, 0.2, 1.28, 0.92), (1.0, -0.1, 1.08, 0.68))):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1.0, location=(x, y, z))
        puff = bpy.context.object
        puff.name = "cooking smoke puff"
        apply(puff, smoke_mat)
        puff.scale = (scale * 0.8, scale * 0.65, scale)
        puff.keyframe_insert(data_path="location", frame=1)
        puff.location.x += 0.22 * math.sin(index + 0.5)
        puff.location.y += 0.12
        puff.location.z += 0.62
        puff.scale = (scale * 1.18, scale * 0.9, scale * 1.48)
        puff.keyframe_insert(data_path="location", frame=26)
        puff.keyframe_insert(data_path="scale", frame=26)
        puff.location.x -= 0.28
        puff.location.z += 0.42
        puff.scale = (scale * 1.42, scale * 1.1, scale * 1.82)
        puff.keyframe_insert(data_path="location", frame=48)
        puff.keyframe_insert(data_path="scale", frame=48)
        bezier(puff.animation_data.action if puff.animation_data else None)

    # Subtle highlight bloom for hot grill bars and grease.
    scene.use_nodes = True
    nodes = scene.node_tree.nodes
    links = scene.node_tree.links
    nodes.clear()
    layers = nodes.new("CompositorNodeRLayers")
    glare = nodes.new("CompositorNodeGlare")
    glare.glare_type = "FOG_GLOW"
    glare.quality = "HIGH"
    glare.threshold = 1.3
    glare.size = 6
    glare.mix = -0.92
    composite = nodes.new("CompositorNodeComposite")
    links.new(layers.outputs["Image"], glare.inputs["Image"])
    links.new(glare.outputs["Image"], composite.inputs["Image"])

    return scene


build_scene()
