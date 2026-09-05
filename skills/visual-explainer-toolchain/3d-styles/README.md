# 3D Styles & Visual-Fidelity Standard

This directory (`3d-styles/`) contains the visual style guides and the overarching fidelity standards for all 3D content produced by the toolchain.

## 3D Style Catalog & Navigation

Realism does **not** mean photorealism alone. Realism is the agreement of physical cues: **internal coherence, material legibility, spatial persuasiveness, and intentional craft within the chosen visual world.**

Apply relevant physical cues to the chosen style, production stage, visible scale,
and budget. This guide supports art direction; it does not prescribe a universal
camera, pacing, sound, or detail level. Deliberate abstraction and nonphysical
motion are valid when they serve the brief.

| Guide | Style Target | Visual Characteristics | Best Used For |
| --- | --- | --- | --- |
| **`README.md`** (this document) | **Quality Guidance** | Physical cues, scale, material response, camera optics, motion, hero development, and relevant verification. | 3D assets and styles across the toolchain. |
| [**`flat-shaded-low-poly.md`**](flat-shaded-low-poly.md) | **Flat-shaded Low Poly** | Un-smoothed facet normals, disciplined color blocking, deliberate geometric silhouettes, tactile toy-like physical mass, clean ambient shadows. | Conceptual explainers, playful engineering overviews, architectural diagrams, fast-rendering 3D beats. |

### How styles connect with 3D engines

```text
3D Brief & Art Direction
       │
       ▼
[3d-styles/README.md] (Realism Standard)
  │  Ensures physical cues, scale, weight, lighting logic, and motion inertia
  │
  ├─────────────────────────────────────────┬─────────────────────────────────────────┐
  ▼                                         ▼                                         ▼
[flat-shaded-low-poly.md]         [Future Style Guides]                     [Cinematic Realism]
  │                                         │                                         │
  └─────────────────────────────────────────┼─────────────────────────────────────────┘
                                            │
                                            ▼
                             3D Rendering Engine Execution
        ┌───────────────────────────────────┼───────────────────────────────────┐
        ▼                                   ▼                                   ▼
[guides/blender.md]               [guides/runpod.md]                 [guides/pygfx-taichi.md]
Blender Scene / EEVEE             Remote GPU Cycles                  WGPU / Scientific 3D
```

---

## Realism and premium visual-fidelity standard

Use this guide whenever a deliverable is expected to look physically credible, whether the subject is medical, scientific, industrial, culinary, architectural, or commercial.

This is a cross-cutting visual-fidelity standard. It governs assets, scale, geometry, materials, transformations, simulations, contact, volumes, optical credibility, rendering, and verification. It also defines the minimum craft expected when the user asks for premium editorial animation, engineering-explainer impact, or high-end documentary 3D. It does **not** decide the story, storyboard, shot order, camera language, emotional lighting, or visual emphasis. Those choices belong to the applicable direction playbook in `references/` or to the user's brief. Once those choices are made, this guide governs whether they are executed convincingly.

## Do not confuse clarity with visual poverty

Educational clarity controls **what the viewer must understand**. It does not authorize weak modeling, blank environments, uniform materials, generic lighting, or repetitive camera motion.

- Simplify the message before simplifying the visible world.
- Remove irrelevant detail, but preserve the physical cues that establish material identity, scale, depth, construction, anatomy, weight, and contact.
- Treat `clean` as deliberate hierarchy, not emptiness; `stylized` as authored design, not unresolved primitives; `calm` as controlled pacing, not static staging; and `clinical` as trustworthy restraint, not white-on-white texturelessness.
- Do not infer a low-fidelity target merely because the deliverable is educational, medical, short-form, or diagram-led.
- When the user names a premium visual benchmark, match the requested finish and impact. Surface concrete feasibility or budget issues without silently lowering the target; leave medical and editorial suitability decisions to the user.
- Borrow quality attributes from references—clarity, rhythm, spatial storytelling, material richness, composition, and polish—without copying a studio's proprietary characters, assets, or exact house style.

A frame may be highly stylized and still meet this standard. Realism here means that the chosen visual world is internally coherent, materially legible, spatially persuasive, and finished to the intended level.

## Set the realism target

Before production, state what must be physically convincing and what may remain stylized or schematic.

- Describe production stage, finish, and pacing independently; reuse project choices instead of requiring a new specification for each edit. Example labels:
  - **Production stage:** `previz`, `look-dev`, or `final`.
  - **Finish target:** `diagrammatic`, `premium-stylized`, `cinematic-realistic`, `dynamic-kinetic`, or an explicitly described hybrid.
  - **Pacing target:** `calm-editorial`, `snappy-social`, or a brief-specific rhythm. Shot lengths follow the content and intended effect, not numeric limits.
- For kinetic sequences, micro-shots can connect an establishing view, detail, and insert. Sustained observations, target-locked shots, and static compositions remain available at any duration that serves the scene.
- Do not let `final` describe a polished render of a low-detail placeholder, and do not let `look-dev` silently become the shipped visual target.
- Identify the hero subjects and the details that will be visible at their closest intended viewing distance.
- Identify the hero shots where visual impact is part of the communication goal. Allocate modeling, shading, lighting, camera, simulation, and render budget to them deliberately instead of distributing effort uniformly.
- Establish dimensions, forces, material families, and expected behavior where they affect the visible explanation; identify intentionally illustrative scales or motion.
- Collect references for shape, surface breakup, deformation, phase change, fluid or gas behavior, wear, residue, and contact—not merely for mood.
- For major benchmark references, note useful attributes such as asset fidelity, material response, lighting, or rhythm, at a level proportional to the task.
- Define which physical cues the viewer will use to judge credibility, such as scale, weight, inertia, softness, wetness, heat, translucency, or turbulence.
- For image-led hero shots, define the subject and action that carry the plate. For diagram-led or mixed-media scenes, judge the intended composite; text may be essential to its meaning.

Never describe a render as photorealistic solely because it uses Cycles, high sample counts, depth of field, or a filmic grade. Realism is the agreement of many physical cues.

## Build realism in layers

### 1. Asset and geometry fidelity

- Start from real-world scale and keep units consistent across modeling, simulation, lighting, and camera-independent render settings.
- Match the subject's primary silhouette before adding detail.
- Add secondary forms that explain construction, anatomy, thickness, joints, folds, seams, layers, or manufacturing logic.
- Reserve tertiary detail for what the final resolution and viewing distance can reveal: pores, scratches, fibers, bubbles, droplets, char, crumbs, or micro-bevels.
- Use primitives freely for blocking, but do not leave a hero subject as a generic cube, sphere, torus, slab, or mannequin in a `premium-stylized` or `cinematic-realistic` final unless the deliberate art direction makes that abstraction unmistakable.
- Avoid infinitely sharp manufactured edges unless the object truly requires them. Small bevels create believable highlight roll-off.
- Use enough subdivision for curved silhouettes and deformation, but do not substitute polygon count for accurate form.
- Model hidden thickness or interior layers when transmission, translucency, deformation, cutting, melting, or tearing can expose them.
- Verify that objects sit, press, hang, float, or interpenetrate in a physically plausible way. Contact errors destroy scale quickly.
- Build enough environment to establish scale and context. A hero object isolated in a blank cyclorama often reads as a product mockup rather than a lived, engineered, or biological system.
- Use foreground, midground, and background forms where spatial depth matters. Occlusion, repetition, atmosphere, and parallax are information-bearing cues, not decorative clutter.

### 2. Camera, optics, and spatial storytelling

The direction playbook chooses the camera language. This standard requires the chosen camera to behave like an intentional optical and spatial system.

- Specify sensor or projection model, focal length, focus distance, aperture, camera height, subject distance, shutter behavior, and delivery aspect ratio when they materially affect the shot.
- Use camera movement to reveal a relationship that a static view cannot: enter a layer, trace a load path, pass an obstruction, expose an interior, compare scales, or connect stages of a process.
- Prefer authored paths, arcs, cranes, tracking moves, motivated reframes, and match moves when the subject calls for them. Repeating one target-locked linear dolly across every shot is not cinematic coverage.
- Preserve believable acceleration, deceleration, horizon behavior, parallax, and clearance around geometry. Avoid weightless camera drift and rotations that feel detached from the scene's scale.
- Choose target-locked moves, linear tracks, eased paths, or speed ramps for their narrative role. Review unintended repetition without banning a camera technique.
- Snap zooms and optical punch-ins are optional accents; select amplitude and timing from the scene.
- Handheld micro-inertia can support a lived-camera look; stable or mechanical tracks can be intentional.
- Stage depth intentionally with near, middle, and far elements. A slow push-in on a centered object against an empty background does not become visually rich merely because depth of field is enabled.
- Use depth of field to direct attention, not to conceal unfinished geometry or create arbitrary blur. Check that the focus transition is motivated and temporally stable.
- Choose motion blur and shutter settings for readability and the intended look; a 180° shutter is a starting point, not a requirement.
- Check each requested aspect ratio against its actual crop and destination overlays. Reuse a composition when it survives that check; reblock when needed. Derive safe areas from the destination instead of a universal central percentage.
- Across a multi-shot final, verify purposeful variation in shot size, elevation, lens behavior, direction of travel, and spatial reveal. Consistency should come from the art direction, not from reusing one camera recipe.

### 3. Material and surface response

- Treat base color, roughness, specular response, transmission, subsurface scattering, normal detail, displacement, and clearcoat as related physical properties.
- Build variation at multiple spatial scales. A single procedural noise node rarely resembles a real surface.
- Keep surface features consistent with object scale. Oversized pores, scratches, bubbles, or roughness patches make objects look miniature.
- Distinguish material identity through response to light, not color alone. Fat, water, skin, steel, ceramic, smoke, and char should differ in highlight shape, roughness, transmission, and absorption.
- Do not assign the same soft pastel response to unrelated materials for the sake of visual calm. Paper, tissue, glass, protein, painted metal, fabric, ceramic, and wood must retain distinct edge, highlight, transmission, and micro-surface behavior within the palette.
- Give hero materials a reference-based hierarchy of macro form, meso breakup, and micro detail. Random texture is not a substitute for formation logic, grain direction, fiber structure, cell organization, machining, wear, or moisture behavior.
- Use displacement only when the surface relief should affect silhouette, parallax, contact, or shadowing. Use bump or normal detail for shallower structure.
- Validate important materials under a neutral light rig before applying a direction playbook's artistic lighting.
- When a material changes state, animate or simulate the underlying properties coherently. Color change alone is rarely enough.

### 4. Transformation, motion, and simulation

- Decide whether each phenomenon needs keyframes, modifiers, rigid or soft-body dynamics, cloth, particles, fluid, smoke, geometry nodes, shader animation, or a hybrid.
- Use keyframes for intentional art-directed motion; use simulation when emergent behavior, collision, turbulence, settling, or coupling materially affects the result.
- Preserve believable mass, inertia, acceleration, damping, elasticity, and collision response.
- Choose easing appropriate to the object and art direction. Spring overshoot (for example 5–10%) is optional; precise or restrained motion may use no overshoot.
- Squash and stretch is available for expressive transitions; preserve anatomical or geometric form where distortion would obscure the explanation.
- For biological, culinary, or soft materials, coordinate shape change with surface response: compression, moisture loss, swelling, blistering, sagging, rendering, charring, or tearing should not occur independently.
- For fluids and gases, match source scale, viscosity or buoyancy, turbulence scale, dissipation, obstacle interaction, and time scale.
- Bake and record caches when simulation needs them for repeatable or portable rendering. Keyframed and analytic motion do not need an artificial simulation workflow.
- Inspect simulations at playback speed and frame by frame. A stable still image can hide implausible temporal behavior.
- In explanatory animation, make the transformation itself carry meaning. Parts should assemble, deform, separate, flow, collide, or reveal according to the mechanism—not merely pulse, scale up, or slide sideways as generic emphasis.

### 5. Physical integration

A convincing object must appear to share the same world as its surroundings.

- Check contact shadows, compression, occlusion, reflected color, reflected geometry, and surface contamination at interfaces.
- Ensure wet, oily, dusty, hot, cold, or charred subjects affect nearby surfaces when the phenomenon calls for it.
- Use environment and source lighting that produces coherent shadow direction, reflection structure, falloff, and exposure. Emotional or narrative lighting choices remain the responsibility of the direction playbook.
- Avoid unsupported floating details. Droplets, particles, crumbs, sparks, foam, residue, and debris need emitters, collisions, adhesion, gravity, or airflow consistent with the scene.
- Confirm that scale cues agree across geometry, texture frequency, depth haze, motion, particle size, and shadow softness.
- Avoid the showroom-table default unless the subject is genuinely a product still life. Engineering, biological, architectural, and clinical processes usually need a contextual system around the hero object.

### 6. Volumes, atmosphere, and color integrity

- Treat smoke, steam, mist, dust, fire, and underwater media as participating volumes with density, anisotropy, temperature or emission, and extinction—not as transparent meshes by default.
- Give volumes a plausible source, evolution, interaction, and disappearance. They should not pop, freeze, or pass through obstacles without reason.
- Match volume detail to scale. Fine wisps and broad billows should not share the same turbulence frequency.
- Use compositing for integration and finishing, not to conceal missing geometry, unstable simulation, broken contact, or incorrect material response.
- Keep color management, view transform, exposure, bit depth, alpha handling, and output transforms consistent across local tests, remote renders, and final encoding.
- Watch for clipped highlights, crushed shadows, banding, denoising artifacts, fireflies, and temporal shimmer.

### 7. Premium stylization and scientific credibility

`Premium-stylized` is a demanding finish target, not a waiver from realism. It replaces literal detail with designed detail and must remain coherent at every visible scale.

- Build a bespoke shape language, controlled proportions, consistent edge treatment, disciplined palettes, layered depth, and purposeful negative space.
- Preserve enough material response, shadow structure, contact, and parallax for the objects to inhabit one world even when proportions or colors are stylized.
- Keep informational overlays graphically simple while allowing the underlying 3D plate to be spatially and materially rich. A simple caption does not require a simple scene.
- Use transitions that transform or connect meaningful objects and spaces. Decorative wipes and generic fades should not replace a spatially motivated reveal when the mechanism can support one.
- Base scientific, medical, and engineering hero forms on reviewable references. Simplify nonessential structure, but preserve the morphology, layer logic, shell construction, joints, load paths, and scale cues needed for the explanation.
- Distinguish literal, illustrative, and metaphorical scale. Flag ambiguity about microscopy, patient data, measured simulation, or molecular precision in review notes. Apply on-screen labels according to the brief or user review; do not claim illustrative data is measured.
- A close medical or scientific hero should not remain a glossy generic sphere or stacked slab if the narration depends on shell, layer, surface, interior, or interaction. Resolve those features visually or choose a clearer schematic medium.
- An engineering hero should expose construction logic, thickness, repetition, connection, deformation, or load transfer rather than presenting featureless blocks with labels.

### 8. Kinetic typography and spatial graphics integration

Choose whether graphics inhabit the 3D world or form a separate reading layer.
Either treatment can be deliberate and well finished.

- Use static overlays, sustained captions, or animated entrances according to the intended hierarchy and reading time.
- For kinetic emphasis, word or phrase reveals can follow narration. Phoneme-level animation, bounces, and flashes are optional accents.
- Anchor callouts to spatial points when that relationship matters. Screen-space caption bars remain valid for narration and sustained reading.
- When pairing a 3D plate with 2D motion graphics, ensure graphics respect scene depth: allow foreground particles or geometry to pass in front of secondary annotations when motivated.

### 9. Acoustic realism and SFX synchronization

Sound design follows the intended listening experience. Motion can be carried by
narration, ambience, music, selected effects, or deliberate silence.

- Place effects at meaningful accents, not every visual event. Align selected hits perceptually; use frame-accurate timing when the effect needs it.
- Whooshes, risers, and damped hits are options for high-energy transitions; omit them when another treatment serves the moment.
- Set music/effect levels and ducking from actual narration intelligibility, mix headroom, and delivery needs. Do not apply a fixed attenuation to every mix.

## Develop hero shots before scaling production

For a new or substantially changed premium look, develop a representative shot
before committing a large render budget. Reuse established look-development
results for routine edits; this technical checkpoint does not require an extra
user approval. Scale the following workflow to the actual uncertainty:

1. Select the hardest and most representative hero shot.
2. Write its visual proposition in one sentence: what the viewer should feel and what spatial or physical relationship the shot reveals.
3. Establish the final hero asset, closest-detail geometry, material stack, environment depth, light logic, camera path, and intended composite treatment.
4. Produce representative wide, medium, and closest-detail frames, plus a short motion test at playback speed.
5. Inspect silhouette, scale, depth, materials, contact, hierarchy, and motion in the intended plate or composite.
6. Propagate the useful asset, lighting, camera, and compositing choices to supporting shots without making every shot a copy of the hero.

Do not spend a full production render budget proving that an unresolved look-development scene is cleanly encoded.

## Choose a rendering strategy

Use a renderer and test range that answer the current visual question efficiently,
including the final renderer when its behavior is the question.

- Use viewport modes or EEVEE for blocking, scale checks, silhouette, contacts, transformation timing, simulation iteration, and coarse material behavior.
- Use local low-sample Cycles tests for transmission, subsurface scattering, displacement, volumes, reflection structure, and denoising stability.
- Use Runpod Cycles by default for substantial production, following the main skill's established mode and cost authorization. Suitable bounded local production is also valid.
- Test representative frames before a full remote sequence: a neutral frame, a peak-action frame, and the closest-detail frame.
- Estimate cost from measured representative-frame time rather than from optimistic defaults.
- Do not increase samples until geometry, scale, material parameters, light transport, simulation, and denoising problems have been checked.

For renderer setup and remote execution, follow [`../guides/blender.md`](../guides/blender.md) and [`../guides/runpod.md`](../guides/runpod.md). For scientific 3D and real-time GPU pipelines, follow [`../guides/pygfx-taichi.md`](../guides/pygfx-taichi.md).

## Make assets and caches portable

- Prefer repository-owned or deliberately packaged assets over machine-specific absolute paths.
- Pack small textures when practical; otherwise use relative paths and copy all dependencies to the remote workspace.
- Package simulation caches explicitly and verify that a fresh process can resolve them.
- Treat missing textures, substitutions, uncached domains, and version-dependent node behavior as render failures.
- Record Blender version, renderer, device, color-management settings, important add-ons, and external asset licenses.

## Relevant quality checks

Apply checks that match the brief and changed work. Reuse valid prior observations;
do not turn this checklist into mandatory paperwork or repeated full-scene testing
for a small edit. Editorial acceptance and human medical review are separate.

Before final rendering:

- [ ] The production stage, finish target, and pacing target are labeled independently.
- [ ] Premium benchmarks are translated into explicit asset, material, lighting, camera, motion, and finishing requirements.
- [ ] The physically critical subjects and cues are named.
- [ ] Hero shots and supporting shots are identified, and the representative hero shot has passed a motion look-development review.
- [ ] Holds, reading time, and transitions serve the chosen rhythm.
- [ ] Easing and any deformation fit the intended motion style.
- [ ] Selected SFX are synchronized and the narration remains intelligible.
- [ ] Hero assets match real-world scale, primary silhouette, visible construction, and intended close-detail distance.
- [ ] Visible assets meet the requested final finish; deliberate primitive forms, sparse environments, and graphic abstraction follow the art direction.
- [ ] Contacts and intersections have been inspected from more than one angle.
- [ ] Critical materials pass a neutral-light test and use correctly scaled surface detail.
- [ ] Distinct materials remain distinguishable by light response, not color alone.
- [ ] The camera path, lens, focus, parallax, easing, and motion blur have been reviewed at playback speed.
- [ ] The frame has intentional foreground, midground, and background structure wherever spatial depth is part of the brief.
- [ ] Major camera moves or object transformations reveal explanatory meaning rather than serving as generic motion.
- [ ] State changes coordinate geometry, material properties, emitted matter, and timing where applicable.
- [ ] Relevant simulations are temporally stable, appropriately collision-checked, and reproducible/portable where required.
- [ ] Textures, caches, fonts, add-ons, and linked assets are portable.
- [ ] Representative-frame render time, memory use, and estimated remote cost are known.

After rendering:

- [ ] The frame sequence is contiguous, correctly sized, and free of missing or corrupt frames.
- [ ] A neutral frame, peak-action frame, and closest-detail frame have been inspected at full resolution.
- [ ] Surface scale, silhouettes, contacts, reflections, deformation, particles, and volume continuity remain credible over time.
- [ ] Denoising, motion, transparency, and volume integration show no objectionable temporal artifacts.
- [ ] Typography and graphics remain readable with the selected static or animated treatment.
- [ ] Image-led hero plates or the intended mixed-media composites communicate their subject and action.
- [ ] Multi-shot playback supports the intended rhythm, including purposeful repetition or variation.
- [ ] Every requested delivery aspect ratio has been checked for framing and legibility, whether cropped or separately staged.
- [ ] Renderer, device, sample count, denoiser, resolution, frame range, and color-management settings are reported.
- [ ] The encoded deliverable passes `ffprobe` checks for duration, frame rate, dimensions, and codec.
- [ ] Limitations are reported plainly; previews are not presented as final photorealistic work.

## Common realism failures

- **“Educational means visually simple.”** Simplify the information hierarchy, not the craft, material world, spatial depth, or hero imagery.
- **“Stylized means primitives plus pastel materials.”** Premium stylization requires bespoke forms, authored proportions, coherent material response, layered composition, and disciplined motion.
- **“Clinical means a white room with no texture.”** Trust can come from restraint and accuracy while tissue, paper, glass, fabric, furniture, and equipment remain materially specific.
- **“One camera move solves every scene.”** Review whether repeated moves serve the sequence; long takes, static shots, and speed ramps are all available.
- **“Every caption needs animation.”** Choose reading time and hierarchy first, then use motion where it adds meaning.
- **“Manim is only for math equations.”** Manim is a full-featured programmatic motion graphics engine capable of high-framerate kinetic typography, spring-damper UI, and rapid-fire infographic cuts.
- **“Every movement needs a sound.”** Plan the mix intentionally, including silence, and prioritize selected accents and intelligibility.
- **“Blank 3D cards will become compelling after overlays.”** Overlays can clarify meaning but cannot repair an empty plate, weak hierarchy, or missing physical context.
- **“Cycles means realistic.”** Path tracing cannot repair crude geometry, false scale, uniform materials, or implausible behavior.
- **“More samples will fix it.”** Samples reduce noise; they do not add missing physical information.
- **“A strong grade or colored light will hide weak assets.”** Finishing can unify a sound render but cannot create absent form, contact, or material structure.
- **“Transparent blobs are smoke or steam.”** Gas-like motion needs coherent sourcing, advection, turbulence, obstacle interaction, and dissipation.
- **“Changing color communicates cooking, decay, or heating.”** Convincing state change usually also affects shape, volume, roughness, moisture, translucency, residue, and emitted matter.
- **“Random noise creates natural detail.”** Detail must follow the material's formation process, directionality, scale, and wear pattern.
- **“A generic sphere is enough for a scientific hero.”** If the explanation depends on shell, layer, surface, interior, or interaction, those structures must be designed and reviewable at the intended viewing distance.
- **“One camera recipe creates consistency.”** Consistency comes from shared art direction; repeated lens, height, target, and motion can make every beat feel like the same unfinished setup.
- **“A good still proves a good simulation.”** Realistic motion must survive temporal inspection.
- **“A preview can stand in for final.”** Label the stage and report the actual asset, simulation, and rendering quality achieved.
