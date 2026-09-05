---
name: visual-explainer-toolchain
description: Create or verify explanatory videos, scientific 3D visualizations, simulations, and mixed-media scenes with the shared Manim, PyGfx, Taichi, Blender, and FFmpeg toolchain, matching the user's visual direction and production budget.
---

# Visualization & Video Toolchain

Use the maintained central project at `~/Developer/visual-explainer-toolchain`. Its
`pyproject.toml` and `uv.lock` own ManimCE, Manim Voiceover, Gemini, Python
Typst, PyGfx/wgpu/rendercanvas, and Taichi. Video projects own only their
scenes, assets, configuration, and generated media.

The governing principle is:

> Match the engine and production effort to the requested visual result, iteration needs, and available budget.

The user normally describes the desired visual result. Choose the engine, but
honor an explicit override unless a concrete constraint makes it impossible.

Creative techniques in this skill and its references are options. User direction
and established project choices take precedence over example pacing, cameras,
sound, or visual styles. Keep technical output checks separate from editorial
judgment; pending medical or advertising review does not block generation.

## Preserve the central architecture

- Use `manim-video` for Manim and `visual-python` for ordinary PyGfx/Taichi
  scripts. They preserve the caller's working directory and relative outputs
  while ignoring the caller's `.venv`, uv project selection, and dotenv files.
- Do not install or declare Manim, Manim Voiceover, PyGfx, wgpu, rendercanvas,
  Taichi, `google-genai`, or Python Typst in a video project. Do not create a
  visualization `.venv` there.
- Homebrew/system tools own Blender, FFmpeg/FFprobe, Typst CLI, SoX, uv, and
  compatible Python. Blender scripts run under Blender's embedded Python;
  never add `bpy` to this uv project.
- Keep credentials solely in the protected central `.env`. `visual-python`,
  `manim-video`, and local Blender wrappers remove Runpod/R2 credentials;
  `visual-runpod` is the only wrapper allowed to load them. Never put keys, ADC
  paths, browser profiles, or secrets into a scene, `.blend`, manifest, render
  bundle, or log.

### macOS local Blender process boundary

On macOS, `visual-blender`, `visual-blender-preview`, and
`visual-blender-render` need hardware access from their parent runner. Blender
5.x initializes Metal before running Python even in `--background` mode. A
restricted runner can withhold the Metal device identity, causing Blender 5.2
to exit during GPU backend detection before a scene script starts.

This permission belongs to the parent process runner; it is not a Blender CLI
flag and the wrapper must not attempt to elevate itself. When the runner already
has unrestricted hardware access, execute normally without an approval request.
Only if an actual restricted runner blocks access, use its supported narrow
host-execution approval mechanism if available. If access remains unavailable,
do not repeatedly launch Blender or try `--gpu-backend opengl`; continue
independent work, use an authorized remote path, or report the local limitation.
The central `visual-blender` wrapper performs a
macOS hardware-access preflight and exits with status 77 plus an actionable
message instead of allowing the known Metal startup crash.

## Route each segment

Choose technology after identifying the visual job that each segment must do.

| Need | Route |
| --- | --- |
| Kinetic typography, punchy elastic UI, animated timelines/counters, vector diagrams, explanatory 2D, fast-paced YouTube/short-form motion graphics, or simple clear 3D | Manim |
| Meshes, surfaces, point clouds, spatial fields, camera perspective, or lightweight scientific 3D | PyGfx |
| Analytically prescribed motion with modest state | NumPy + PyGfx |
| Many evolving particles/grids/fields, PDEs, or compute-heavy deformation | Taichi + PyGfx |
| Materials, lighting, anatomy, imported assets, volumetrics, rigging, or cinematic shots | Blender (local iteration; Runpod by default for substantial production) |
| Beats that need different rendering strengths | Mixed segments + FFmpeg |

Consider the whole sequence, existing assets, and cost of crossing engines.
Blender can own one shot or the complete video when that suits the brief.
Use Manim for graphics and Taichi for evolving state when they help; an engine
choice does not need a separate creative approval or a per-shot justification.

Useful routing checks:

- An annotated process or product-flow diagram: Manim.
- Kinetic typography, word-by-word emphasis, animated counters/gauges, or rapid-fire UI cards: Manim (elastic easing and MovingCameraScene are optional techniques).
- Transparent motion graphics plates over 3D backgrounds: Manim with alpha output.
- A triangulated model or spatial dataset: PyGfx.
- Tens of thousands of evolving particles: Taichi + PyGfx; benchmark locally
  before considering remote compute.
- A realistic translucent organ, material, or environment: Blender; choose the
  render location using the mode guidance below.
- An explainer plus one photorealistic establishing shot: Manim + short Blender
  shot (Runpod Pod) + FFmpeg.
- A rotating object: Manim or PyGfx unless realistic rendering is explicitly
  valuable.

For fast-paced YouTube/short-form motion graphics patterns, elastic easing curves,
and transparent overlay rendering in Manim, read
[`guides/dynamic-manim.md`](guides/dynamic-manim.md).

For PyGfx and Taichi implementation details, including deterministic offscreen
rendering, backend policy, and reproducibility fields, read
[`guides/pygfx-taichi.md`](guides/pygfx-taichi.md).

## Apply direction playbooks and realism separately

Technology selection is not a story template. Decide the viewer, message,
emotional tone, and information sequence from the subject instead of forcing a
mathematical-explainer structure onto every topic.

The `references/` directory contains subject- or format-specific direction
playbooks. A playbook decides what to communicate and how to stage the viewer's
experience; it may define story structure, camera and lighting direction,
language, claims, or review gates for that kind of video.

For a mathematics educational video, read
[`references/math-educational-video.md`](references/math-educational-video.md)
before storyboarding. Its pedagogy, equation timing, and notation guidance are
specific to that format and must not be applied by default to other subjects.

For a medical, clinical-procedure, vaccine, pharmaceutical, or healthcare
marketing video, read
[`references/medical-video.md`](references/medical-video.md) before drafting
claims or storyboarding. It offers direction and source-note practices while
leaving clinical, regulatory, and advertising decisions to the user. Those
decisions are not prerequisites for drafting, rendering, or delivering a video.

When 3D assets, styles, or physical credibility are part of the deliverable,
**you must read [`3d-styles/README.md`](3d-styles/README.md) before authoring any
3D scene, asset, or style decision.** It is the governing quality standard and
navigation hub for all 3D visual styles in this toolchain.

After reading `3d-styles/README.md`, also read the per-style guide that matches
the requested or most appropriate visual style:

| Style | Guide |
| --- | --- |
| Flat-shaded Low Poly | [`3d-styles/flat-shaded-low-poly.md`](3d-styles/flat-shaded-low-poly.md) |

If the requested style has no dedicated guide yet, derive the production spec
from the governing standard in `3d-styles/README.md` and note the gap.

`3d-styles/README.md` defines cross-cutting asset, geometry, material,
transformation, simulation, and verification standards. It does not choose the
story, storyboard, camera language, or emotional lighting; those decisions belong
to the applicable direction playbook or user brief.

For any multi-segment video or independently produced narration, read
[`guides/composition.md`](guides/composition.md) before rendering to
settle shared technical delivery settings and transitions.

## Select and retain the Blender render mode

Use the current request, earlier user choices, project configuration, and resource
budget to select the mode. Retain that choice for related iterations without
reconfirming it. `Cycles` or `GPU` specifies a renderer/device preference, not
automatically a paid remote job.

- **Local iteration:** use `visual-blender-preview` for inexpensive EEVEE frames
  and short ranges. Use bounded low-sample local Cycles tests when transmission,
  SSS, volumes, or another feature needs the production renderer. An unspecified
  diagnostic preview can start locally without a mode question.
- **Production:** Runpod Pod Cycles is the default for substantial workloads.
  Local Cycles or EEVEE output is also valid when it meets the requested finish
  within the local budget. Do not downgrade a requested final to preview quality.
- **Remote execution:** use `visual-runpod-prepare` → `visual-runpod submit`
  with R2. One Pod maps to one GPU/Blender process and the requested frame range.
  Keep submissions within the user's existing cost/resource authorization.
  Explain Runpod cost and show the live progress command before or alongside
  submission. Ask only for a material new cost/scope decision not already covered;
  complete bundle preparation and independent local work first.

If both local validation and remote production are already requested and
authorized, validate locally and proceed to the remote render without an
additional transition approval. Revisit the choice only for a concrete failure,
quality mismatch, or budget change.

For multiple local workers, write PNGs and reports to `/private/tmp` or another
explicitly local scratch path, not an iCloud-synchronized project directory.
Render mode is not evidence of quality; inspect the resulting frames.

## Local Blender iteration and remote production

Use local Blender for scene authoring, short render tests, and suitable bounded
production jobs. Use a **Runpod Pod** (`visual-runpod-prepare` →
`visual-runpod submit`) for substantial Cycles sequences within the selected
budget. Asset portability validation runs in the remote worker by default.

Local preview example:

```sh
visual-blender-preview --scene-script scenes/hero.py \
  --output media/previews/hero.png --width 1280 --height 720 --frame 1
```

`visual-blender-preview` uses configurable EEVEE defaults and does not save over
the source `.blend`. For transparent CLI or batch inspection, `visual-blender`
and `visual-blender-render` remain available locally. When using local parallel
workers, point frame and report outputs to `/private/tmp` or another local
scratch directory, especially when the project is inside iCloud Drive. Read
[`guides/blender.md`](guides/blender.md) for scene preparation, portable
assets, and local preview commands.

## Runpod Pod production workflow

Manim, ordinary PyGfx, Taichi simulations, EEVEE previews, and final FFmpeg
composition stay local by default. Use this workflow when Runpod is selected
for Blender Cycles production rendering.

Prepare a portable Blender bundle locally:

```sh
visual-runpod-prepare \
  --scene scene.blend --scene-script scenes/hero.py --asset-dir assets \
  --output render-job --width 1920 --height 1080 --fps 30 \
  --frame-start 1 --frame-end 240 --samples 128 --device auto
```

`visual-runpod-prepare` creates a self-contained input bundle with portable
asset metadata, an empty output directory, and a `runpod-pod`
`render_manifest.json`. Local Blender validation is optional; the worker checks
the bundle before rendering. Never upload credentials, `.env` files, ADC
paths, SSH keys, browser profiles, or unrelated repository data.

The worker image is built from `runpod/Dockerfile`, contains a pinned Blender
runtime, and runs in a disposable Runpod Pod. One Pod maps to one GPU and one
Blender process; do not run multiple Blender processes inside that Pod:

```text
job lifecycle:     prepare -> archive/upload -> create Pod -> read R2 status -> download -> verify
Pod lifecycle:     create -> boot -> render full range -> upload -> delete
```

The production worker uses a digest-pinned CUDA base image and is tested with
Ubuntu 22.04/Python 3.10. Keep worker code compatible with that interpreter
(for example, use `datetime.timezone.utc` rather than Python 3.11's
`datetime.UTC`). The client creates this one-shot Pod with SSH disabled and no
port 22 because the worker communicates through environment variables and R2
presigned URLs.

Export `RUNPOD_API_KEY` in the shell that launches `visual-runpod`, and set
`RUNPOD_POD_IMAGE` and `RUNPOD_POD_GPU_ID`, plus the bucket-scoped
`R2_ACCOUNT_ID`, `R2_BUCKET`, `R2_ACCESS_KEY_ID`, and `R2_SECRET_ACCESS_KEY`, in
the protected central `.env` (mode `600`). `visual-runpod` never reads or writes
the Runpod key from a config file; generic visualization wrappers do not inherit
these credentials. Set a finite
`RUNPOD_POD_TERMINATE_AFTER` as the client's wait/cost budget (and use a
create-time guard or external watchdog for unattended runs), then submit with
automatic R2 presigning:

```sh
visual-runpod submit --bundle render-job --r2
# Follow R2-backed Pod/frame progress and delete a terminal Pod automatically:
visual-runpod progress --jobs-file render-job.runpod.json --download
# Retry a failed render in a new Pod:
visual-runpod retry --jobs-file render-job.runpod.json
# Stop a non-terminal Pod explicitly:
visual-runpod terminate --jobs-file render-job.runpod.json --confirm
# After verifying and retaining the local output, delete this batch from R2:
visual-runpod cleanup --jobs-file render-job.runpod.json --confirm
```

The client and worker use SHA-256-checked tar archives rather than embedding PNG
data in Runpod JSON. The worker writes metadata and a signed output download
URL to R2; the client verifies the full sequence locally. For
Blender, maintain the standard flow:
`remote Cycles PNG sequence -> local verification -> local FFmpeg composition`.

The installed `runpodctl` version is probed at runtime because current v2.12
help output does not include `--terminate-after`. Terminal and bounded-timeout
cleanup are idempotent if a Pod disappears out of band. R2 status writes can
arrive out of order during archive upload; the client therefore keeps aggregate
frame progress monotonic for RenderPulse.

`progress` reads bounded worker status from R2 and prints phase,
completed-frame count, and percentage without printing signed URLs. Frame
progress is based on non-empty PNGs and remains reliable across Blender builds;
sample fields are included when Blender emits sample statistics. `wait` provides
the same terminal-state handling without progress lines.

Before a first production range on a new GPU type,
submit a one-frame Cycles compatibility probe and inspect its worker report.
GPU enumeration alone is not proof that a backend can compile its render kernel.
Record the selected backend and GPU model. The worker retries a recognized
OptiX/PTX initialization failure once with CUDA for `auto` or `gpu`; an explicit
OptiX request fails as requested. Inspect that fallback report before submitting
a long range. A Runpod job is successful
only when `COMPLETED` includes a worker result with an output archive digest;
`COMPLETED` without that result remains pending or failed, never render success.

Read [`guides/runpod.md`](guides/runpod.md) for the manifest, signed URL
boundary, worker image, Pod lifecycle, and verification details.

## Keep narration separate from visual source

Write spoken prose separately from on-screen copy, code, markup, and rendering
notation. Never send raw source or implementation syntax to Gemini TTS. Use
Manim Voiceover only where it owns the timing naturally; create narration for
PyGfx or Blender independently when that makes the composition clearer. Do not
force a non-Manim segment into Manim Voiceover.

## Verify observable results

Do not claim success based on imports or device enumeration. Render requested
scenes and inspect valid, non-empty, non-uniform outputs; check simulation
state; use FFprobe for video; and retain seeds, step count, time step, backend,
and floating-point policy where they affect reproducibility.

Central credential-independent validation:

```sh
cd ~/Developer/visual-explainer-toolchain
./scripts/check_environment.sh
./scripts/render_smoke_tests.sh --typst-only
./scripts/render_smoke_tests.sh --visualization-only
./scripts/verify_external_wrapper.sh
```

After deliberate dependency changes, keep `pyproject.toml` and `uv.lock`
together, run `uv lock`, then `uv sync --frozen --no-managed-python`. Do not
change the central stack casually while authoring a video.
