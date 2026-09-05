# 3D Styles & Visual-Fidelity Standard

This directory (`3d-styles/`) contains the visual style guides and the overarching fidelity standards for all 3D content produced by the toolchain.

## 3D Style Catalog & Navigation

Realism does **not** mean photorealism alone. Realism is the agreement of physical cues: **internal coherence, material legibility, spatial persuasiveness, and intentional craft within the chosen visual world.**

Whether creating high-precision biomedical models, cinematic documentary scenes, or stylized low-poly graphics, every 3D asset must meet the physical credibility standards defined in this document.

| Guide | Style Target | Visual Characteristics | Best Used For |
| --- | --- | --- | --- |
| **`README.md`** (this document / `realism.md`) | **Governing Standard** | Cross-cutting quality gates, physical cues, scale, material response, camera optics, motion physics, hero shots, anti-patterns. | All 3D assets and styles across the toolchain. |
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
- When the user names a premium visual benchmark, treat its level of finish, shot design, and audience impact as a hard requirement unless a safety, accuracy, schedule, or budget constraint is explicitly negotiated.
- Borrow quality attributes from references—clarity, rhythm, spatial storytelling, material richness, composition, and polish—without copying a studio's proprietary characters, assets, or exact house style.

A frame may be highly stylized and still meet this standard. Realism here means that the chosen visual world is internally coherent, materially legible, spatially persuasive, and finished to the intended level.

## Set the realism target

Before production, state what must be physically convincing and what may remain stylized or schematic.

- Record three independent labels:
  - **Production stage:** `previz`, `look-dev`, or `final`.
  - **Finish target:** `diagrammatic`, `premium-stylized`, `cinematic-realistic`, `dynamic-kinetic`, or an explicitly described hybrid.
  - **Pacing target:** `calm-editorial` (average shot length 6–10s, deliberate documentary/waiting-room) or `snappy-social` (average shot length 1.5–3.5s, fast-paced YouTube/short-form/reel).
- For `snappy-social` or modern dynamic explainers, enforce micro-beat pacing: never hold a single target-locked camera or static composition for longer than 3.5 seconds. Divide an informational beat into 2–3 micro-shots (establishing -> punch-in/detail -> kinetic insert).
- Do not let `final` describe a polished render of a low-detail placeholder, and do not let `look-dev` silently become the shipped visual target.
- Identify the hero subjects and the details that will be visible at their closest intended viewing distance.
- Identify the hero shots where visual impact is part of the communication goal. Allocate modeling, shading, lighting, camera, simulation, and render budget to them deliberately instead of distributing effort uniformly.
- Establish real-world dimensions, gravity, material families, environmental conditions, and expected behavior.
- Collect references for shape, surface breakup, deformation, phase change, fluid or gas behavior, wear, residue, and contact—not merely for mood.
- For each benchmark reference, record the quality being borrowed: asset fidelity, lens and camera behavior, depth staging, material response, lighting structure, transition logic, motion rhythm, or finishing. A mood board without this mapping is not a production specification.
- Define which physical cues the viewer will use to judge credibility, such as scale, weight, inertia, softness, wetness, heat, translucency, or turbulence.
- Define what should make the shot compelling before any labels or narration are added. A textless hero plate should still have a clear subject, readable action, and intentional composition.

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
- For dynamic explainer beats, ban target-locked linear camera drift. Use intentional S-curve speed ramping (Bezier easing: brisk approach -> momentary hold on the focal detail -> dynamic snap away).
- Use snap zooms and optical punch-ins (1.25x–1.4x scale shifts or focal jumps) to punctuate critical voiceover statements and structural reveals.
- Add subtle organic handheld micro-inertia or secondary motion rather than sterile mechanical tracks when filming lived or physical subjects.
- Stage depth intentionally with near, middle, and far elements. A slow push-in on a centered object against an empty background does not become visually rich merely because depth of field is enabled.
- Use depth of field to direct attention, not to conceal unfinished geometry or create arbitrary blur. Check that the focus transition is motivated and temporally stable.
- Use motion blur and shutter settings (180° shutter equivalent) that support scale and motion readability while preventing 30fps strobe artifacts during fast sweeps.
- Design separately for substantially different aspect ratios. A 16:9 widescreen composition and a 9:16 short require distinct blocking, safe areas, and camera paths. In 9:16 vertical formats, enforce a central 55% safe zone to prevent UI headers, captions, and platform overlays from obscuring critical cues.
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
- In dynamic explainer and UI motion, arriving graphic callouts, cards, and markers must not stop dead with robotic rigidity; apply 5–10% spring overshoot (elastic recoil / `ease_out_back`) to convey tangible physical mass, tension, and kinetic snap.
- Apply velocity-aligned squash and stretch during rapid linear transitions to eliminate brittle plastic rigidity while preserving overall volume.
- For biological, culinary, or soft materials, coordinate shape change with surface response: compression, moisture loss, swelling, blistering, sagging, rendering, charring, or tearing should not occur independently.
- For fluids and gases, match source scale, viscosity or buoyancy, turbulence scale, dissipation, obstacle interaction, and time scale.
- Bake deterministic caches before final rendering. Record cache locations, frame ranges, domain resolutions, and seed values.
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
- Distinguish literal scale, illustrative scale, and metaphorical scale. Label explanatory depictions where a viewer could mistake the image for microscopy, patient data, measured simulation, or an exact molecular model.
- A close medical or scientific hero should not remain a glossy generic sphere or stacked slab if the narration depends on shell, layer, surface, interior, or interaction. Resolve those features visually or choose a clearer schematic medium.
- An engineering hero should expose construction logic, thickness, repetition, connection, deformation, or load transfer rather than presenting featureless blocks with labels.

### 8. Kinetic typography and spatial graphics integration

Informational overlays and typography are physical design entities inhabiting the visual world, not detached static stickers.

- Ban static full-frame PNG overlays that freeze for multiple seconds. Motion graphics must possess motivated entrance, dwell, and exit physics.
- Synchronize kinetic text entrances to spoken phonemes and micro-beats: use word-by-word pop-ins, elastic scale bounces, and rapid highlighter sweeps (`TransformMatchingShapes`, `Flash`, `Indicate`).
- Anchor callouts and leader lines to 3D spatial points with tracked motion or depth-aware occlusion rather than relying exclusively on flat bottom caption bars.
- When pairing a 3D plate with 2D motion graphics, ensure graphics respect scene depth: allow foreground particles or geometry to pass in front of secondary annotations when motivated.

### 9. Acoustic realism and SFX synchronization

Visual motion without acoustic impact is physically weightless and cognitively disorienting.

- Frame-accurate SFX alignment: synchronize every snap zoom, whip pan, elastic card arrival, text burst, and data counter tick with sound effects (whoosh, sub-bass thud, mechanical click, chime) within ±1 frame.
- High-energy transitions require high-energy transients: pair rapid speed ramping with pitch-swept risers or air-displacement whooshes; pair sudden stops with tactile damped thuds.
- Carve acoustic headroom: duck background music by -12dB to -18dB during vocal delivery and transient SFX hits to maintain crisp impact without clipping.

## Develop hero shots before scaling production

For a `premium-stylized`, `cinematic-realistic`, or high-end hybrid project, do not render the full sequence before the visual ceiling is proven.

1. Select the hardest and most representative hero shot.
2. Write its visual proposition in one sentence: what the viewer should feel and what spatial or physical relationship the shot reveals.
3. Establish the final hero asset, closest-detail geometry, material stack, environment depth, light logic, camera path, and intended composite treatment.
4. Produce representative wide, medium, and closest-detail frames, plus a short motion test at playback speed.
5. Review the textless plate for silhouette, scale, depth, material separation, contact, visual hierarchy, and motion meaning.
6. Lock the quality bar only after that shot is compelling without explanatory text. Then propagate its asset, lighting, camera, and compositing standards to supporting shots.

Do not spend a full production render budget proving that an unresolved look-development scene is cleanly encoded.

## Choose a rendering strategy

Use the cheapest renderer that can answer the current realism question, then promote only validated work to the final renderer.

- Use viewport modes or EEVEE for blocking, scale checks, silhouette, contacts, transformation timing, simulation iteration, and coarse material behavior.
- Use local low-sample Cycles tests for transmission, subsurface scattering, displacement, volumes, reflection structure, and denoising stability.
- Use Runpod Cycles when final-quality path tracing, heavy geometry, high-resolution caches, volumes, or large frame ranges exceed the practical local budget.
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

## Realism quality gates

Before final rendering:

- [ ] The production stage, finish target, and pacing target are labeled independently.
- [ ] Premium benchmarks are translated into explicit asset, material, lighting, camera, motion, and finishing requirements.
- [ ] The physically critical subjects and cues are named.
- [ ] Hero shots and supporting shots are identified, and the representative hero shot has passed a motion look-development review.
- [ ] In `snappy-social` or `dynamic-kinetic` deliverables, no single static composition or camera holds longer than 3.5 seconds; beats are divided into micro-shots.
- [ ] Kinetic transitions, UI arrivals, and graphic callouts use spring/overshoot easing (`ease_out_back`) rather than rigid linear stops.
- [ ] Frame-accurate SFX cues (whoosh, hit, click) are mapped to all dynamic camera transitions and graphic bursts within ±1 frame.
- [ ] Hero assets match real-world scale, primary silhouette, visible construction, and intended close-detail distance.
- [ ] No unresolved primitive, blank card, generic mannequin, placeholder environment, or one-material proxy remains in a premium final unless explicitly approved as the art direction.
- [ ] Contacts and intersections have been inspected from more than one angle.
- [ ] Critical materials pass a neutral-light test and use correctly scaled surface detail.
- [ ] Distinct materials remain distinguishable by light response, not color alone.
- [ ] The camera path, lens, focus, parallax, easing, and motion blur have been reviewed at playback speed.
- [ ] The frame has intentional foreground, midground, and background structure wherever spatial depth is part of the brief.
- [ ] Major camera moves or object transformations reveal explanatory meaning rather than serving as generic motion.
- [ ] State changes coordinate geometry, material properties, emitted matter, and timing where applicable.
- [ ] Simulations are baked, reproducible, temporally stable, and collision-checked.
- [ ] Textures, caches, fonts, add-ons, and linked assets are portable.
- [ ] Representative-frame render time, memory use, and estimated remote cost are known.

After rendering:

- [ ] The frame sequence is contiguous, correctly sized, and free of missing or corrupt frames.
- [ ] A neutral frame, peak-action frame, and closest-detail frame have been inspected at full resolution.
- [ ] Surface scale, silhouettes, contacts, reflections, deformation, particles, and volume continuity remain credible over time.
- [ ] Denoising, motion, transparency, and volume integration show no objectionable temporal artifacts.
- [ ] Overlaid typography and graphics exhibit kinetic life and motivated entrance/exit physics rather than remaining static full-frame PNGs.
- [ ] The textless hero plates remain visually legible and compelling before captions, branding, or narration are used to explain them.
- [ ] Multi-shot playback shows purposeful variation rather than repeated centered compositions, identical lenses, or the same slow push-in.
- [ ] Every requested delivery aspect ratio has been checked as an authored composition, not merely as a crop.
- [ ] Renderer, device, sample count, denoiser, resolution, frame range, and color-management settings are reported.
- [ ] The encoded deliverable passes `ffprobe` checks for duration, frame rate, dimensions, and codec.
- [ ] Limitations are reported plainly; previews are not presented as final photorealistic work.

## Common realism failures

- **“Educational means visually simple.”** Simplify the information hierarchy, not the craft, material world, spatial depth, or hero imagery.
- **“Stylized means primitives plus pastel materials.”** Premium stylization requires bespoke forms, authored proportions, coherent material response, layered composition, and disciplined motion.
- **“Clinical means a white room with no texture.”** Trust can come from restraint and accuracy while tissue, paper, glass, fabric, furniture, and equipment remain materially specific.
- **“A slow camera move makes the shot cinematic (Ken Burns Fallacy).”** Repeating a centered linear push-in or slow 10-second drift adds motion but turns an explainer into a static, lethargic slide show. Dynamic explainer beats require speed ramping, snap zooms, and micro-beat cuts.
- **“Static PNG overlays are enough for clean graphics (Floating Sticker Syndrome).”** A 10-second motionless caption bar pinned over a 3D plate kills visual rhythm and detaches typography from the underlying space. Use kinetic typography and dynamic UI.
- **“Manim is only for math equations.”** Manim is a full-featured programmatic motion graphics engine capable of high-framerate kinetic typography, spring-damper UI, and rapid-fire infographic cuts.
- **“Audio can be an afterthought (Mute Physics Failure).”** Visual momentum without frame-synced impact sound effects (whooshes, pops, sub-hits) feels hollow and disorienting.
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
