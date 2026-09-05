# Flat-Shaded Low-Poly Style Guide

This guide defines the aesthetic, modeling, shading, lighting, and motion standards for **Flat-shaded Low-Poly** assets and scenes.

All assets created under this style must adhere to the overarching credibility and craft principles in [`README.md`](README.md). Low polygon count controls geometric density; it does **not** justify lazy topology, arbitrary colors, weightless motion, or disconnected staging.

---

## 1. Aesthetic Philosophy: "Crafted Toy Diorama"

Flat-shaded low-poly is a deliberate aesthetic of geometric abstraction, reminiscent of tactile papercraft, machined wood, or injection-molded figurines.

- **Authored Form**: Every vertex and polygon edge must serve a communicative and silhouette purpose.
- **Readable Facets**: Surfaces are defined by un-smoothed face normals where adjacent polygons catch light at distinct angles, creating crisp value gradients across the form.
- **Chunky Proportions**: Thicken thin features (stems, antennas, struts, wheels, walls) so the object conveys physical substance and toy-like durability.
- **Tactile Grounding**: Objects must feel like physical miniatures arranged in a diorama, anchored by contact shadows, soft ambient occlusion, and coherent gravity.

---

## 2. Geometry & Topology Standards

### Flat Shading & Normal Integrity
- **Strict Flat Shading**: Never enable smooth shading across geometric facets. Face normals must remain planar and distinct.
- **Triangulation Control**: Non-planar quads can interpolate shading unpredictably across render engines. Explicitly triangulate curved transitions (`Decimate` or `Triangulate` modifier) so every triangular facet has an intentional, planar light response.
- **Silhouette Purity**: Match the subject's iconic silhouette in 12–40 facets. If an object is not immediately recognizable by its outer contour alone, revise its primary masses before adding accessory details.

### Level of Detail (LOD) & Poly Budget
- **Hero Objects**: 500 to 2,500 polygons. Sufficient density to reveal doors, joints, wheels, blades, or layered shells.
- **Environment & Props**: 50 to 400 polygons per asset (trees, rocks, buildings, containers).
- **Edge Consistency**: Maintain comparable polygon density across assets in the same shot. A 10,000-poly car parked next to a 12-poly tree breaks internal coherence.

---

## 3. Materials, Palette & Shading

### Material Properties
- **Principled Matte**: Base materials should mimic matte plastic, colored cardstock, or matte resin:
  - Base Color: Solid authored hex/RGB values.
  - Roughness: `0.65` – `0.85` (diffuse matte response; avoid glossy mirror highlights).
  - Specular: `0.2` – `0.35` (subtle highlight roll-off across facet edges).
  - Metallic: `0.0` for organic/plastic/wood; `0.8` – `1.0` for metallic elements (gold, chrome, steel), maintaining flat face normals.
  - Subsurface Scattering (optional): `0.02` – `0.05` on organic or fleshy elements to add subtle internal warmth without blurring facet edges.

### Color Palette Strategy
- **Palette Discipline**: Limit each scene or hero model to 3–5 cohesive colors.
- **Value Contrast for Facets**: Test colors under the scene light rig to verify that illuminated facets, mid-tone facets, and shadow facets maintain at least a 20% luminance delta.
- **No Procedural Noise Textures**: Avoid high-frequency procedural noise (Perlin, Voronoi) on surfaces. Detail should come from geometric subdivisions and deliberate facet color zoning.

---

## 4. Lighting & Environment

Flat-shaded objects rely entirely on light angle to define their 3D shape. Flat, uniform lighting renders low-poly models as illegible 2D silhouette blobs.

- **Strong Directional Key**: Sun or directional light positioned at a 35°–50° elevation and 45° off-camera angle. This ensures adjacent polygons receive clearly differentiated incident light.
- **Colored Fill / Ambient**: Use a complementary cool fill (sky blue or soft lavender) opposite a warm key (warm sunlight) to enrich facet color variation between lit and shaded sides.
- **Contact Shadows & Ambient Occlusion**:
  - Ground planes must receive crisp contact shadows directly beneath objects.
  - Use Raytraced AO or Screen Space Ambient Occlusion (radius 0.2m–0.5m) to darken crevices, seams, and ground contacts, rooting the low-poly models in their space.
- **Environment Staging**: Place objects on an authored diorama plinth, floating island, or minimal studio sweep with a subtle gradient, avoiding infinite pure-white void space.

---

## 5. Motion, Physics & Camera

Adhere strictly to the kinetic standards of [`README.md`](README.md):

- **Tactile Weight & Recoil**: When low-poly objects drop, assemble, or slide into frame, apply 5–10% spring overshoot (`ease_out_back`) and slight secondary settles. Avoid robotic linear deceleration.
- **Squash & Stretch**: For rapid movement (e.g. hops, impacts, pop-ins), apply volume-preserving velocity-aligned squash and stretch (1.1x / 0.9x).
- **Camera Staging**:
  - **Isometric / Long Lens**: Orthographic or narrow FOV (85mm–135mm focal length equivalent) enhances the miniature diorama feel.
  - **Dynamic Explainer Cuts**: For fast-paced social explainers, use brisk S-curve camera moves, 1.25x snap punch-ins, and micro-beat cuts (< 3.5s per composition).
- **SFX Synchronization**: Low-poly motion must hit with acoustic weight. Pair arrivals, clicks, and rotations with wooden, plastic, or damped percussive clicks within ±1 frame.

---

## 6. Engine Implementation Recipes

### Blender Setup

```python
import bpy

# 1. Ensure flat shading on mesh
for obj in bpy.context.selected_objects:
    if obj.type == 'MESH':
        for poly in obj.data.polygons:
            poly.use_smooth = False

# 2. Material recipe (Principled Matte)
mat = bpy.data.materials.new(name="LowPoly_Matte")
mat.use_nodes = True
nodes = mat.node_tree.nodes
principled = nodes.get("Principled BSDF")
principled.inputs["Roughness"].default_value = 0.72
principled.inputs["Specular IOR Level"].default_value = 0.25
principled.inputs["Subsurface Weight"].default_value = 0.03
```

- In EEVEE or Cycles:
  - Add a `Sun` light (`Color = (1.0, 0.95, 0.9)`, `Energy = 3.5`, `Angle = 2°`).
  - Add a soft ambient `Sky Texture` or low-strength HDRI (`Energy = 0.4`).
  - Enable `Ambient Occlusion` (Distance: 0.3m, Factor: 1.2).

### PyGfx Setup

```python
import pygfx as gfx

# Use MeshPhongMaterial with flat_shading=True
material = gfx.MeshPhongMaterial(
    color="#4A90E2",
    flat_shading=True,
    shininess=15,
)
```

---

## 7. Quality Gate Checklist

Before publishing or rendering final low-poly shots:

- [ ] All mesh faces use authored flat shading; no accidental vertex-normal smoothing.
- [ ] Non-planar quads are triangulated to prevent engine-specific shading artifacts.
- [ ] Silhouette communicates the object's identity and function without labels.
- [ ] Lighting angles produce distinct luminance on adjacent polygon facets.
- [ ] Color palette is constrained (3–5 tones) with clear value hierarchy.
- [ ] Ambient occlusion and contact shadows firmly anchor the object to its ground plane.
- [ ] Animations employ spring overshoot (`ease_out_back`) and tangible physical mass.
- [ ] Audio effects (clicks, thuds, pops) are synchronized within ±1 frame.
