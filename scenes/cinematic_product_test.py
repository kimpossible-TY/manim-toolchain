"""Short cinematic product-ad test scene for local Blender EEVEE preview.

The scene is intentionally self-contained: it uses only procedural geometry and
materials so it can be rendered locally for a fast lighting/camera test and can
later be packaged for a Cycles production render.
"""

from __future__ import annotations

import math

import bpy
from mathutils import Vector


def set_input(node, name: str, value) -> None:
    socket = node.inputs.get(name)
    if socket is not None:
        socket.default_value = value


def principled_material(
    name: str,
    color: tuple[float, float, float, float],
    *,
    metallic: float = 0.0,
    roughness: float = 0.35,
    coat: float = 0.0,
) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    assert bsdf is not None
    set_input(bsdf, "Base Color", color)
    set_input(bsdf, "Metallic", metallic)
    set_input(bsdf, "Roughness", roughness)
    set_input(bsdf, "Coat Weight", coat)
    set_input(bsdf, "Clearcoat", coat)
    return material


def emission_material(name: str, color: tuple[float, float, float, float], strength: float):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = color
    emission.inputs["Strength"].default_value = strength
    output = nodes.new("ShaderNodeOutputMaterial")
    links.new(emission.outputs[0], output.inputs[0])
    return material


def apply_material(obj: bpy.types.Object, material: bpy.types.Material) -> None:
    obj.data.materials.clear()
    obj.data.materials.append(material)


def bevel(obj: bpy.types.Object, amount: float, segments: int = 4) -> None:
    modifier = obj.modifiers.new("soft product edges", "BEVEL")
    modifier.width = amount
    modifier.segments = segments
    modifier.limit_method = "ANGLE"


def rounded_box(
    name: str,
    location: tuple[float, float, float],
    scale: tuple[float, float, float],
    material: bpy.types.Material,
    bevel_amount: float = 0.12,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel(obj, bevel_amount, 6)
    apply_material(obj, material)
    return obj


def add_area(
    name: str,
    location: tuple[float, float, float],
    energy: float,
    color: tuple[float, float, float],
    size: float,
    target: Vector = Vector((0.0, 0.0, 0.3)),
    shape: str = "DISK",
) -> bpy.types.Object:
    bpy.ops.object.light_add(type="AREA", location=location)
    light = bpy.context.object
    light.name = name
    light.data.energy = energy
    light.data.color = color
    light.data.shape = shape
    light.data.size = size
    light.rotation_euler = (target - light.location).to_track_quat("-Z", "Y").to_euler()
    return light


def key_camera(camera: bpy.types.Object, frame: int, location: tuple[float, float, float], target: Vector, lens: float) -> None:
    camera.location = location
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = lens
    camera.keyframe_insert(data_path="location", frame=frame)
    camera.keyframe_insert(data_path="rotation_euler", frame=frame)
    camera.data.keyframe_insert(data_path="lens", frame=frame)


def linearize(action: bpy.types.Action | None) -> None:
    if action is None:
        return
    for curve in action.fcurves:
        for point in curve.keyframe_points:
            point.interpolation = "BEZIER"


def build_scene() -> bpy.types.Scene:
    scene = bpy.context.scene
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.materials, bpy.data.curves, bpy.data.cameras, bpy.data.lights):
        # Keep Blender's built-in datablocks out of the way, but remove only
        # orphaned items created by this script.
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)

    scene.frame_start = 1
    scene.frame_end = 96
    scene.render.fps = 24
    scene.render.fps_base = 1.0
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    if hasattr(scene, "eevee"):
        scene.eevee.taa_render_samples = 32
    try:
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass

    # Deep blue studio world; the large area lights create the commercial-ad
    # look and keep the silhouette readable without a flat educational style.
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    if background is not None:
        set_input(background, "Color", (0.004, 0.008, 0.022, 1.0))
        set_input(background, "Strength", 0.16)

    floor_mat = principled_material("studio graphite", (0.012, 0.018, 0.032, 1), metallic=0.35, roughness=0.2)
    backdrop_mat = principled_material("backdrop blue", (0.006, 0.012, 0.034, 1), metallic=0.0, roughness=0.32)
    bottle_mat = principled_material("midnight cobalt lacquer", (0.012, 0.07, 0.22, 1), metallic=0.68, roughness=0.17, coat=0.45)
    dark_mat = principled_material("cap black chrome", (0.008, 0.01, 0.018, 1), metallic=0.92, roughness=0.12, coat=0.28)
    gold_mat = principled_material("brushed champagne metal", (0.75, 0.29, 0.055, 1), metallic=0.9, roughness=0.2, coat=0.25)
    label_mat = principled_material("label ivory", (0.72, 0.55, 0.28, 1), metallic=0.25, roughness=0.25, coat=0.35)
    cyan_emission = emission_material("cyan light strip", (0.02, 0.35, 1.0, 1), 7.0)
    amber_emission = emission_material("amber light strip", (1.0, 0.16, 0.025, 1), 6.0)

    # Floor and a vertical sweep-like wall.
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, -1.62))
    floor = bpy.context.object
    floor.name = "studio floor"
    apply_material(floor, floor_mat)
    bpy.ops.mesh.primitive_plane_add(size=24, location=(0, 3.2, 5.0), rotation=(math.pi / 2.0, 0, 0))
    backdrop = bpy.context.object
    backdrop.name = "studio backdrop"
    apply_material(backdrop, backdrop_mat)

    # Product rig: a beveled cobalt bottle, a stepped metal cap, and a thin
    # illuminated label. All product pieces rotate as one turntable.
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0))
    rig = bpy.context.object
    rig.name = "PRODUCT_RIG"
    body = rounded_box("NOVA bottle", (0, 0, 0.05), (1.18, 0.82, 1.55), bottle_mat, 0.18)
    body.parent = rig
    shoulder = rounded_box("bottle shoulder", (0, 0, 1.44), (1.03, 0.73, 0.22), bottle_mat, 0.1)
    shoulder.parent = rig
    base_ring = rounded_box("base metal ring", (0, 0, -1.5), (1.02, 0.7, 0.09), gold_mat, 0.05)
    base_ring.parent = rig

    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=0.66, depth=0.38, location=(0, 0, 1.92))
    cap = bpy.context.object
    cap.name = "cap black chrome"
    bevel(cap, 0.08, 5)
    apply_material(cap, dark_mat)
    cap.parent = rig
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=0.49, depth=0.07, location=(0, 0, 2.14))
    cap_top = bpy.context.object
    cap_top.name = "cap gold accent"
    bevel(cap_top, 0.035, 3)
    apply_material(cap_top, gold_mat)
    cap_top.parent = rig

    label = rounded_box("front label", (0, -0.835, 0.18), (0.83, 0.032, 0.58), label_mat, 0.05)
    label.parent = rig

    # Text faces the camera (the front of the bottle is -Y).
    bpy.ops.object.text_add(location=(0, -0.875, 0.37), rotation=(math.pi / 2.0, 0, 0))
    text = bpy.context.object
    text.name = "NOVA wordmark"
    text.data.body = "NOVA"
    text.data.align_x = "CENTER"
    text.data.align_y = "CENTER"
    text.data.size = 0.42
    text.data.space_character = 1.08
    text.data.extrude = 0.012
    text.data.bevel_depth = 0.004
    apply_material(text, dark_mat)
    text.parent = rig
    bpy.ops.object.text_add(location=(0, -0.875, -0.12), rotation=(math.pi / 2.0, 0, 0))
    edition = bpy.context.object
    edition.name = "01 edition mark"
    edition.data.body = "01 / EDP"
    edition.data.align_x = "CENTER"
    edition.data.align_y = "CENTER"
    edition.data.size = 0.12
    edition.data.extrude = 0.006
    apply_material(edition, dark_mat)
    edition.parent = rig

    bpy.ops.mesh.primitive_torus_add(major_radius=1.35, minor_radius=0.025, major_segments=128, location=(0, 0, -1.55))
    halo = bpy.context.object
    halo.name = "gold floor halo"
    apply_material(halo, gold_mat)
    halo.parent = rig

    # Vertical emissive accents give the camera a moving highlight to catch.
    strip_a = rounded_box("cyan accent", (-2.65, 2.92, 0.5), (0.035, 0.025, 2.8), cyan_emission, 0.02)
    strip_b = rounded_box("amber accent", (2.55, 2.90, 0.15), (0.028, 0.025, 2.3), amber_emission, 0.02)

    key = add_area("large warm key", (4.2, -4.0, 5.6), 1050, (1.0, 0.72, 0.52), 4.2, Vector((0, 0, 0.5)), "RECTANGLE")
    key.data.size_y = 2.2
    fill = add_area("cool blue fill", (-4.8, -2.5, 2.4), 700, (0.18, 0.42, 1.0), 3.6, Vector((0, 0, 0.7)))
    rim = add_area("hard rim", (2.5, 2.0, 4.4), 1250, (0.95, 0.25, 0.08), 1.4, Vector((0, 0, 0.8)))
    top = add_area("top softbox", (0, -0.4, 6.8), 950, (0.74, 0.86, 1.0), 3.5, Vector((0, 0, 0)))
    top.data.shape = "RECTANGLE"
    top.data.size_y = 1.5

    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0.35))
    focus = bpy.context.object
    focus.name = "focus target"

    bpy.ops.object.camera_add(location=(4.8, -7.6, 3.25))
    camera = bpy.context.object
    camera.name = "cinematic camera"
    camera.data.lens = 58
    camera.data.sensor_width = 36
    camera.data.dof.use_dof = True
    camera.data.dof.focus_object = focus
    camera.data.dof.aperture_fstop = 1.45
    scene.camera = camera
    key_camera(camera, 1, (4.8, -7.6, 3.25), Vector((0, 0, 0.25)), 58)
    key_camera(camera, 34, (3.0, -6.0, 2.05), Vector((0, 0, 0.35)), 72)
    key_camera(camera, 68, (-3.7, -6.4, 2.55), Vector((0, 0, 0.35)), 64)
    key_camera(camera, 96, (0.0, -7.8, 2.0), Vector((0, 0, 0.25)), 60)
    linearize(camera.animation_data.action if camera.animation_data else None)

    rig.rotation_euler = (0, 0, 0)
    rig.keyframe_insert(data_path="rotation_euler", frame=1)
    rig.rotation_euler = (0, 0, math.radians(330))
    rig.keyframe_insert(data_path="rotation_euler", frame=96)
    linearize(rig.animation_data.action if rig.animation_data else None)

    # Subtle highlight breathing keeps the shot from feeling static.
    key.data.energy = 900
    key.data.keyframe_insert(data_path="energy", frame=1)
    key.data.energy = 1250
    key.data.keyframe_insert(data_path="energy", frame=48)
    key.data.energy = 1020
    key.data.keyframe_insert(data_path="energy", frame=96)
    linearize(key.animation_data.action if key.animation_data else None)

    # Minimal bloom/glare in the compositor; the result remains clean enough
    # for a product spot and visibly separates highlights from the background.
    scene.use_nodes = True
    nodes = scene.node_tree.nodes
    links = scene.node_tree.links
    nodes.clear()
    render_layers = nodes.new("CompositorNodeRLayers")
    glare = nodes.new("CompositorNodeGlare")
    glare.glare_type = "FOG_GLOW"
    glare.quality = "HIGH"
    glare.threshold = 1.2
    glare.size = 6
    glare.mix = -0.94
    composite = nodes.new("CompositorNodeComposite")
    links.new(render_layers.outputs["Image"], glare.inputs["Image"])
    links.new(glare.outputs["Image"], composite.inputs["Image"])

    return scene


build_scene()
