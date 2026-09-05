"""Test Blender scene replicating the high-end 3D product cut from OpenAI ChatGPT Work.

Subject: 'Plümveil Echo' luxury perfume bottle suspended among floating petals.
Engine: Compatible with local EEVEE Next preview and Runpod Pod Cycles production.
Adheres to: realism.md (material credibility, optical depth, hero staging).
"""

from __future__ import annotations

import math
import random
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector, Euler, Matrix


def set_input(bsdf: bpy.types.Node, socket_name: str, value) -> None:
    """Safely set socket value on Principled BSDF across Blender versions."""
    socket = bsdf.inputs.get(socket_name)
    if socket is not None:
        try:
            socket.default_value = value
        except Exception:
            pass


def create_pbr_material(
    name: str,
    base_color: tuple[float, float, float, float],
    *,
    metallic: float = 0.0,
    roughness: float = 0.2,
    transmission: float = 0.0,
    ior: float = 1.45,
    coat: float = 0.0,
    subsurface: float = 0.0,
    subsurface_color: tuple[float, float, float, float] | None = None,
    emission_color: tuple[float, float, float, float] | None = None,
    emission_strength: float = 0.0,
) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    assert bsdf is not None

    set_input(bsdf, "Base Color", base_color)
    set_input(bsdf, "Metallic", metallic)
    set_input(bsdf, "Roughness", roughness)
    set_input(bsdf, "IOR", ior)
    set_input(bsdf, "Transmission Weight", transmission)
    set_input(bsdf, "Coat Weight", coat)
    set_input(bsdf, "Subsurface Weight", subsurface)

    if subsurface_color is not None:
        set_input(bsdf, "Subsurface Radius", (subsurface_color[0], subsurface_color[1], subsurface_color[2]))

    if emission_color is not None and emission_strength > 0:
        set_input(bsdf, "Emission Color", emission_color)
        set_input(bsdf, "Emission Strength", emission_strength)

    return mat


def create_petal_mesh(name: str, material: bpy.types.Material) -> bpy.types.Object:
    """Create a curved organic flower petal mesh."""
    bm = bmesh.new()
    w, h = 0.18, 0.32
    # Create a small grid of vertices with curved curvature
    verts = []
    rows, cols = 5, 4
    for r in range(rows):
        v_row = []
        u = r / (rows - 1)  # 0 to 1 along length
        y = (u - 0.5) * h
        # Taper at base and tip, widest in middle
        row_width = w * math.sin(u * math.pi) * (1.0 + 0.3 * (1.0 - u))
        for c in range(cols):
            v = c / (cols - 1)  # 0 to 1 along width
            x = (v - 0.5) * row_width
            # Curvature: cupped spoon shape + longitudinal wave
            z = -0.06 * (4.0 * (v - 0.5) ** 2) + 0.04 * math.sin(u * math.pi * 1.2)
            v_row.append(bm.verts.new((x, y, z)))
        verts.append(v_row)

    bm.verts.ensure_lookup_table()
    for r in range(rows - 1):
        for c in range(cols - 1):
            bm.faces.new([verts[r][c], verts[r + 1][c], verts[r + 1][c + 1], verts[r][c + 1]])

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    # Smooth shading
    for poly in mesh.polygons:
        poly.use_smooth = True

    # Subdivision modifier for soft organic edges
    subsurf = obj.modifiers.new("Subsurf", "SUBSURF")
    subsurf.levels = 2
    subsurf.render_levels = 2

    # Solidify modifier for micro-thickness
    solid = obj.modifiers.new("Solidify", "SOLIDIFY")
    solid.thickness = 0.003

    obj.data.materials.append(material)
    return obj


def build_scene() -> bpy.types.Scene:
    scene = bpy.context.scene

    # Reset scene datablocks
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.materials, bpy.data.meshes, bpy.data.cameras, bpy.data.lights):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)

    scene.frame_start = 1
    scene.frame_end = 60
    scene.render.fps = 30
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100

    # Engine settings: Default to EEVEE for rapid local tests
    scene.render.engine = "BLENDER_EEVEE"
    if hasattr(scene, "eevee"):
        try:
            scene.eevee.use_raytracing = True
            scene.eevee.taa_render_samples = 48
            scene.eevee.use_shadows = True
        except Exception:
            pass

    # World: Soft luminous studio ambient
    scene.world.use_nodes = True
    bg_node = scene.world.node_tree.nodes.get("Background")
    if bg_node is not None:
        set_input(bg_node, "Color", (0.04, 0.025, 0.07, 1.0))
        set_input(bg_node, "Strength", 0.3)

    # Materials
    # 1. Outer Glass: high transmission, refraction, subtle clearcoat
    mat_glass = create_pbr_material(
        "Luxury Glass",
        (0.96, 0.94, 0.98, 1.0),
        roughness=0.03,
        ior=1.52,
        transmission=0.92,
        coat=0.6,
    )

    # 2. Fragrance Liquid (Deep Royal Violet/Plum)
    mat_liquid = create_pbr_material(
        "Plumveil Liquid",
        (0.28, 0.05, 0.65, 1.0),
        roughness=0.02,
        ior=1.34,
        transmission=0.75,
        coat=0.4,
    )

    # 3. Cap: Glossy Black Chrome
    mat_cap = create_pbr_material(
        "Black Chrome Cap",
        (0.015, 0.015, 0.02, 1.0),
        metallic=0.95,
        roughness=0.12,
        coat=0.3,
    )

    # 4. Gold Ring Accent
    mat_gold = create_pbr_material(
        "Champagne Gold",
        (0.95, 0.76, 0.38, 1.0),
        metallic=0.92,
        roughness=0.18,
        coat=0.2,
    )

    # 5. Label Material (Satin Off-White with gold frame)
    mat_label = create_pbr_material(
        "Satin Paper Label",
        (0.96, 0.95, 0.93, 1.0),
        roughness=0.35,
        coat=0.15,
    )

    # 6. Petals Material (Translucent Rose Pink with Subsurface Scattering)
    mat_petal = create_pbr_material(
        "Translucent Petal",
        (0.98, 0.42, 0.58, 1.0),
        roughness=0.32,
        subsurface=0.45,
        subsurface_color=(1.0, 0.4, 0.3, 1.0),
        transmission=0.15,
    )

    # 7. Subtle background card/glow
    mat_glow = create_pbr_material(
        "Soft Lavender Glow",
        (0.12, 0.08, 0.22, 1.0),
        roughness=0.6,
        emission_color=(0.35, 0.22, 0.55, 1.0),
        emission_strength=0.8,
    )

    # --- Geometry Setup ---

    # Master Rig for Bottle
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0))
    bottle_rig = bpy.context.object
    bottle_rig.name = "BOTTLE_RIG"

    # Outer Glass Body (Rounded Cylinder with Bevel and Smooth Shading)
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=0.62, depth=1.45, location=(0, 0, 0.1))
    glass_body = bpy.context.object
    glass_body.name = "Glass Body"
    glass_body.data.materials.append(mat_glass)
    glass_body.parent = bottle_rig
    for poly in glass_body.data.polygons:
        poly.use_smooth = True

    bev_glass = glass_body.modifiers.new("Bevel", "BEVEL")
    bev_glass.width = 0.08
    bev_glass.segments = 6
    bev_glass.limit_method = "ANGLE"

    # Inner Liquid Core (Smooth Shaded)
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=0.52, depth=1.22, location=(0, 0, 0.05))
    liquid_core = bpy.context.object
    liquid_core.name = "Liquid Core"
    liquid_core.data.materials.append(mat_liquid)
    liquid_core.parent = bottle_rig
    for poly in liquid_core.data.polygons:
        poly.use_smooth = True

    # Gold Neck Ring (Smooth shaded with subtle bevel)
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.28, depth=0.16, location=(0, 0, 0.92))
    neck_ring = bpy.context.object
    neck_ring.name = "Neck Ring"
    neck_ring.data.materials.append(mat_gold)
    neck_ring.parent = bottle_rig
    for poly in neck_ring.data.polygons:
        poly.use_smooth = True

    # Black Chrome Sphere Cap (Subdivided and smooth shaded)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=48, radius=0.46, location=(0, 0, 1.35))
    cap = bpy.context.object
    cap.name = "Cap Spherical"
    cap.scale = (1.0, 0.92, 0.88)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    cap.data.materials.append(mat_cap)
    cap.parent = bottle_rig
    for poly in cap.data.polygons:
        poly.use_smooth = True
    sub_cap = cap.modifiers.new("Subsurf", "SUBSURF")
    sub_cap.levels = 1

    # Front Label: Pure curved ribbon plate via bmesh (No internal artifacts)
    bm_label = bmesh.new()
    l_rows, l_cols = 10, 20
    l_height = 0.58
    l_angle_span = math.radians(70.0)
    l_radius = 0.628
    grid_verts = []
    for r in range(l_rows):
        row_verts = []
        z = (r / (l_rows - 1) - 0.5) * l_height + 0.08
        for c in range(l_cols):
            theta = (c / (l_cols - 1) - 0.5) * l_angle_span - (math.pi / 2.0)  # Centered at -Y
            x = l_radius * math.cos(theta)
            y = l_radius * math.sin(theta)
            row_verts.append(bm_label.verts.new((x, y, z)))
        grid_verts.append(row_verts)

    bm_label.verts.ensure_lookup_table()
    for r in range(l_rows - 1):
        for c in range(l_cols - 1):
            bm_label.faces.new([grid_verts[r][c], grid_verts[r + 1][c], grid_verts[r + 1][c + 1], grid_verts[r][c + 1]])

    mesh_label = bpy.data.meshes.new("FrontLabelMesh")
    bm_label.to_mesh(mesh_label)
    bm_label.free()

    label_obj = bpy.data.objects.new("Front Label", mesh_label)
    bpy.context.collection.objects.link(label_obj)
    for poly in mesh_label.polygons:
        poly.use_smooth = True
    label_obj.data.materials.append(mat_label)
    label_obj.parent = bottle_rig

    # Subtle solidify for paper thickness
    sol_label = label_obj.modifiers.new("Solidify", "SOLIDIFY")
    sol_label.thickness = 0.002

    # Brand Text on Label ("PLÜMVEIL ECHO")
    bpy.ops.object.text_add(location=(0, -0.635, 0.14), rotation=(math.pi / 2.0, 0, 0))
    text_brand = bpy.context.object
    text_brand.name = "Text Brand"
    text_brand.data.body = "PLÜMVEIL"
    text_brand.data.align_x = "CENTER"
    text_brand.data.align_y = "CENTER"
    text_brand.data.size = 0.095
    text_brand.data.space_character = 1.25
    text_brand.data.extrude = 0.003
    text_brand.data.materials.append(mat_cap)
    text_brand.parent = bottle_rig

    bpy.ops.object.text_add(location=(0, -0.635, -0.02), rotation=(math.pi / 2.0, 0, 0))
    text_sub = bpy.context.object
    text_sub.name = "Text Sub"
    text_sub.data.body = "ECHO"
    text_sub.data.align_x = "CENTER"
    text_sub.data.align_y = "CENTER"
    text_sub.data.size = 0.075
    text_sub.data.space_character = 1.4
    text_sub.data.extrude = 0.002
    text_sub.data.materials.append(mat_cap)
    text_sub.parent = bottle_rig

    # Convert text to permanent polygon mesh for 100% portable assets
    bpy.context.view_layer.objects.active = text_brand
    bpy.ops.object.convert(target="MESH")
    bpy.context.view_layer.objects.active = text_sub
    bpy.ops.object.convert(target="MESH")

    # Tilt the entire bottle rig slightly for cinematic dynamism
    bottle_rig.rotation_euler = Euler((math.radians(16.0), math.radians(-14.0), math.radians(10.0)), "XYZ")
    bottle_rig.location = Vector((0.15, 0.0, 0.0))

    # --- Floating Petals Scatter with Animation ---
    random.seed(42)  # Deterministic seed per realism.md
    petal_coords = [
        # Foreground petals (frame left & right, soft DoF)
        (-1.4, -1.8, 0.8, math.radians(45), math.radians(25), 1.2),
        (1.5, -1.5, -0.4, math.radians(-35), math.radians(60), 1.1),
        (-0.9, -2.2, -0.6, math.radians(80), math.radians(-20), 1.0),
        # Midground petals (dancing around the bottle)
        (-1.2, -0.6, 1.2, math.radians(30), math.radians(-45), 0.95),
        (1.3, -0.4, 0.9, math.radians(-50), math.radians(30), 0.9),
        (-1.6, 0.0, -0.2, math.radians(60), math.radians(70), 0.85),
        (1.1, 0.3, -0.8, math.radians(-20), math.radians(-40), 0.9),
        # Background petals (farther back for depth layers)
        (-1.8, 1.2, 0.6, math.radians(15), math.radians(80), 0.8),
        (1.6, 1.4, 1.3, math.radians(-65), math.radians(20), 0.75),
        (-0.4, 1.6, -1.0, math.radians(40), math.radians(-55), 0.85),
        (0.6, 1.8, 1.5, math.radians(-10), math.radians(45), 0.7),
        (-1.1, 1.0, 1.6, math.radians(25), math.radians(-15), 0.75),
        (1.4, 0.8, -0.3, math.radians(50), math.radians(40), 0.8),
    ]

    for i, (px, py, pz, rx, ry, pscale) in enumerate(petal_coords):
        petal = create_petal_mesh(f"Petal_{i+1:02d}", mat_petal)
        petal.location = Vector((px, py, pz))
        petal.rotation_euler = Euler((rx, ry, random.uniform(0, math.pi * 2)), "XYZ")
        petal.scale = Vector((pscale, pscale, pscale))
        petal.keyframe_insert(data_path="location", frame=1)
        petal.keyframe_insert(data_path="rotation_euler", frame=1)

        # Subtle floating drift over 30 frames
        drift_z = -0.12 * (0.8 + 0.4 * random.random())
        drift_x = 0.05 * (random.random() - 0.5)
        petal.location = Vector((px + drift_x, py, pz + drift_z))
        petal.rotation_euler = Euler((rx + 0.15, ry - 0.1, petal.rotation_euler.z + 0.2), "XYZ")
        petal.keyframe_insert(data_path="location", frame=30)
        petal.keyframe_insert(data_path="rotation_euler", frame=30)

    # Animate bottle rig rotation and gentle vertical hover
    bottle_rig.rotation_euler = Euler((math.radians(16.0), math.radians(-14.0), math.radians(6.0)), "XYZ")
    bottle_rig.location = Vector((0.15, 0.0, -0.04))
    bottle_rig.keyframe_insert(data_path="rotation_euler", frame=1)
    bottle_rig.keyframe_insert(data_path="location", frame=1)

    bottle_rig.rotation_euler = Euler((math.radians(16.0), math.radians(-14.0), math.radians(16.0)), "XYZ")
    bottle_rig.location = Vector((0.15, 0.0, 0.04))
    bottle_rig.keyframe_insert(data_path="rotation_euler", frame=30)
    bottle_rig.keyframe_insert(data_path="location", frame=30)

    # Background Backdrop (Soft Curved Sweep)
    bpy.ops.mesh.primitive_plane_add(size=18, location=(0, 3.5, 0), rotation=(math.pi / 2.0, 0, 0))
    backdrop = bpy.context.object
    backdrop.name = "Studio Backdrop"
    backdrop.data.materials.append(mat_glow)

    # --- Lighting Rig (Studio Commercial Setup) ---

    # 1. Main Key Light (Soft Warm Area Light from upper-right)
    bpy.ops.object.light_add(type="AREA", location=(3.8, -3.2, 4.0))
    key = bpy.context.object
    key.name = "Key Warm Light"
    key.data.energy = 550.0
    key.data.color = (1.0, 0.92, 0.86)
    key.data.shape = "DISK"
    key.data.size = 3.2
    key.rotation_euler = (Vector((0, 0, 0.2)) - key.location).to_track_quat("-Z", "Y").to_euler()

    # 2. Strong Rim / Backlight (Essential for Glass Refraction & Silhouette)
    bpy.ops.object.light_add(type="AREA", location=(-0.8, 2.8, 2.2))
    rim = bpy.context.object
    rim.name = "Rim Backlight"
    rim.data.energy = 1100.0
    rim.data.color = (0.8, 0.9, 1.0)
    rim.data.shape = "RECTANGLE"
    rim.data.size = 3.6
    rim.data.size_y = 2.0
    rim.rotation_euler = (Vector((0, 0, 0.3)) - rim.location).to_track_quat("-Z", "Y").to_euler()

    # 3. Soft Cool Fill Light (from left)
    bpy.ops.object.light_add(type="AREA", location=(-4.2, -2.8, 1.8))
    fill = bpy.context.object
    fill.name = "Fill Lavender"
    fill.data.energy = 300.0
    fill.data.color = (0.7, 0.6, 0.95)
    fill.data.shape = "DISK"
    fill.data.size = 3.8
    fill.rotation_euler = (Vector((0, 0, 0.2)) - fill.location).to_track_quat("-Z", "Y").to_euler()

    # 4. Under-Glow Accent (catches bottom glass facet)
    bpy.ops.object.light_add(type="POINT", location=(0.0, -0.8, -1.2))
    under = bpy.context.object
    under.name = "Under Glow"
    under.data.energy = 140.0
    under.data.color = (0.6, 0.3, 0.95)

    # --- Camera Setup ---
    # Placed at 6.8m distance with subtle push-in over 30 frames
    bpy.ops.object.camera_add(location=(0.0, -6.8, 0.42))
    cam = bpy.context.object
    cam.name = "Ad Camera"
    cam.data.lens = 52.0
    cam.rotation_euler = (Vector((0.15, 0.0, 0.25)) - cam.location).to_track_quat("-Z", "Y").to_euler()

    cam.keyframe_insert(data_path="location", frame=1)
    cam.location = Vector((0.0, -6.2, 0.46))
    cam.keyframe_insert(data_path="location", frame=30)

    # Depth of field (F/3.5 focus on bottle rig)
    cam.data.dof.use_dof = True
    cam.data.dof.focus_object = bottle_rig
    cam.data.dof.aperture_fstop = 3.5

    scene.camera = cam
    return scene


if __name__ == "__main__" or "bpy" in locals():
    build_scene()
