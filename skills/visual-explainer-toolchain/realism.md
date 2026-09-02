# Realism standard

Use this guide whenever a deliverable is expected to look physically credible, whether the subject is medical, scientific, industrial, culinary, architectural, or commercial.

This is a cross-cutting visual-fidelity standard. It governs assets, scale, geometry, materials, transformations, simulations, contact, volumes, rendering, and verification. It does **not** decide the story, storyboard, shot order, camera language, emotional lighting, or visual emphasis. Those choices belong to the applicable direction playbook in `references/` or to the user's brief.

## Set the realism target

Before production, state what must be physically convincing and what may remain stylized or schematic.

- Label the intended stage honestly: `previz`, `look-dev`, or `final`.
- Identify the hero subjects and the details that will be visible at their closest intended viewing distance.
- Establish real-world dimensions, gravity, material families, environmental conditions, and expected behavior.
- Collect references for shape, surface breakup, deformation, phase change, fluid or gas behavior, wear, residue, and contact—not merely for mood.
- Define which physical cues the viewer will use to judge credibility, such as scale, weight, inertia, softness, wetness, heat, translucency, or turbulence.

Never describe a render as photorealistic solely because it uses Cycles, high sample counts, depth of field, or a filmic grade. Realism is the agreement of many physical cues.

## Build realism in layers

### 1. Asset and geometry fidelity

- Start from real-world scale and keep units consistent across modeling, simulation, lighting, and camera-independent render settings.
- Match the subject's primary silhouette before adding detail.
- Add secondary forms that explain construction, anatomy, thickness, joints, folds, seams, layers, or manufacturing logic.
- Reserve tertiary detail for what the final resolution and viewing distance can reveal: pores, scratches, fibers, bubbles, droplets, char, crumbs, or micro-bevels.
- Avoid infinitely sharp manufactured edges unless the object truly requires them. Small bevels create believable highlight roll-off.
- Use enough subdivision for curved silhouettes and deformation, but do not substitute polygon count for accurate form.
- Model hidden thickness or interior layers when transmission, translucency, deformation, cutting, melting, or tearing can expose them.
- Verify that objects sit, press, hang, float, or interpenetrate in a physically plausible way. Contact errors destroy scale quickly.

### 2. Material and surface response

- Treat base color, roughness, specular response, transmission, subsurface scattering, normal detail, displacement, and clearcoat as related physical properties.
- Build variation at multiple spatial scales. A single procedural noise node rarely resembles a real surface.
- Keep surface features consistent with object scale. Oversized pores, scratches, bubbles, or roughness patches make objects look miniature.
- Distinguish material identity through response to light, not color alone. Fat, water, skin, steel, ceramic, smoke, and char should differ in highlight shape, roughness, transmission, and absorption.
- Use displacement only when the surface relief should affect silhouette, parallax, contact, or shadowing. Use bump or normal detail for shallower structure.
- Validate important materials under a neutral light rig before applying a direction playbook's artistic lighting.
- When a material changes state, animate or simulate the underlying properties coherently. Color change alone is rarely enough.

### 3. Transformation, motion, and simulation

- Decide whether each phenomenon needs keyframes, modifiers, rigid or soft-body dynamics, cloth, particles, fluid, smoke, geometry nodes, shader animation, or a hybrid.
- Use keyframes for intentional art-directed motion; use simulation when emergent behavior, collision, turbulence, settling, or coupling materially affects the result.
- Preserve believable mass, inertia, acceleration, damping, elasticity, and collision response.
- For biological, culinary, or soft materials, coordinate shape change with surface response: compression, moisture loss, swelling, blistering, sagging, rendering, charring, or tearing should not occur independently.
- For fluids and gases, match source scale, viscosity or buoyancy, turbulence scale, dissipation, obstacle interaction, and time scale.
- Bake deterministic caches before final rendering. Record cache locations, frame ranges, domain resolutions, and seed values.
- Inspect simulations at playback speed and frame by frame. A stable still image can hide implausible temporal behavior.

### 4. Physical integration

A convincing object must appear to share the same world as its surroundings.

- Check contact shadows, compression, occlusion, reflected color, reflected geometry, and surface contamination at interfaces.
- Ensure wet, oily, dusty, hot, cold, or charred subjects affect nearby surfaces when the phenomenon calls for it.
- Use environment and source lighting that produces coherent shadow direction, reflection structure, falloff, and exposure. Emotional or narrative lighting choices remain the responsibility of the direction playbook.
- Avoid unsupported floating details. Droplets, particles, crumbs, sparks, foam, residue, and debris need emitters, collisions, adhesion, gravity, or airflow consistent with the scene.
- Confirm that scale cues agree across geometry, texture frequency, depth haze, motion, particle size, and shadow softness.

### 5. Volumes, atmosphere, and color integrity

- Treat smoke, steam, mist, dust, fire, and underwater media as participating volumes with density, anisotropy, temperature or emission, and extinction—not as transparent meshes by default.
- Give volumes a plausible source, evolution, interaction, and disappearance. They should not pop, freeze, or pass through obstacles without reason.
- Match volume detail to scale. Fine wisps and broad billows should not share the same turbulence frequency.
- Use compositing for integration and finishing, not to conceal missing geometry, unstable simulation, broken contact, or incorrect material response.
- Keep color management, view transform, exposure, bit depth, alpha handling, and output transforms consistent across local tests, remote renders, and final encoding.
- Watch for clipped highlights, crushed shadows, banding, denoising artifacts, fireflies, and temporal shimmer.

## Choose a rendering strategy

Use the cheapest renderer that can answer the current realism question, then promote only validated work to the final renderer.

- Use viewport modes or EEVEE for blocking, scale checks, silhouette, contacts, transformation timing, simulation iteration, and coarse material behavior.
- Use local low-sample Cycles tests for transmission, subsurface scattering, displacement, volumes, reflection structure, and denoising stability.
- Use Runpod Cycles when final-quality path tracing, heavy geometry, high-resolution caches, volumes, or large frame ranges exceed the practical local budget.
- Test representative frames before a full remote sequence: a neutral frame, a peak-action frame, and the closest-detail frame.
- Estimate cost from measured representative-frame time rather than from optimistic defaults.
- Do not increase samples until geometry, scale, material parameters, light transport, simulation, and denoising problems have been checked.

For renderer setup and remote execution, follow `guides/blender.md` and `guides/runpod.md`.

## Make assets and caches portable

- Prefer repository-owned or deliberately packaged assets over machine-specific absolute paths.
- Pack small textures when practical; otherwise use relative paths and copy all dependencies to the remote workspace.
- Package simulation caches explicitly and verify that a fresh process can resolve them.
- Treat missing textures, substitutions, uncached domains, and version-dependent node behavior as render failures.
- Record Blender version, renderer, device, color-management settings, important add-ons, and external asset licenses.

## Realism quality gates

Before final rendering:

- [ ] The target is labeled `previz`, `look-dev`, or `final`.
- [ ] The physically critical subjects and cues are named.
- [ ] Hero assets match real-world scale, primary silhouette, visible construction, and intended close-detail distance.
- [ ] Contacts and intersections have been inspected from more than one angle.
- [ ] Critical materials pass a neutral-light test and use correctly scaled surface detail.
- [ ] State changes coordinate geometry, material properties, emitted matter, and timing where applicable.
- [ ] Simulations are baked, reproducible, temporally stable, and collision-checked.
- [ ] Textures, caches, fonts, add-ons, and linked assets are portable.
- [ ] Representative-frame render time, memory use, and estimated remote cost are known.

After rendering:

- [ ] The frame sequence is contiguous, correctly sized, and free of missing or corrupt frames.
- [ ] A neutral frame, peak-action frame, and closest-detail frame have been inspected at full resolution.
- [ ] Surface scale, silhouettes, contacts, reflections, deformation, particles, and volume continuity remain credible over time.
- [ ] Denoising, motion, transparency, and volume integration show no objectionable temporal artifacts.
- [ ] Renderer, device, sample count, denoiser, resolution, frame range, and color-management settings are reported.
- [ ] The encoded deliverable passes `ffprobe` checks for duration, frame rate, dimensions, and codec.
- [ ] Limitations are reported plainly; previews are not presented as final photorealistic work.

## Common realism failures

- **“Cycles means realistic.”** Path tracing cannot repair crude geometry, false scale, uniform materials, or implausible behavior.
- **“More samples will fix it.”** Samples reduce noise; they do not add missing physical information.
- **“A strong grade or colored light will hide weak assets.”** Finishing can unify a sound render but cannot create absent form, contact, or material structure.
- **“Transparent blobs are smoke or steam.”** Gas-like motion needs coherent sourcing, advection, turbulence, obstacle interaction, and dissipation.
- **“Changing color communicates cooking, decay, or heating.”** Convincing state change usually also affects shape, volume, roughness, moisture, translucency, residue, and emitted matter.
- **“Random noise creates natural detail.”** Detail must follow the material's formation process, directionality, scale, and wear pattern.
- **“A good still proves a good simulation.”** Realistic motion must survive temporal inspection.
- **“A preview can stand in for final.”** Label the stage and report the actual asset, simulation, and rendering quality achieved.
