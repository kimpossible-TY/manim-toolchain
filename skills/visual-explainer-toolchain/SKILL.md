---
name: visual-explainer-toolchain
description: Create or verify clear explanatory videos, scientific 3D visualizations, simulations, and selectively high-fidelity mixed-media segments with the shared Manim, PyGfx, Taichi, Blender, and FFmpeg toolchain.
---

# Visualization & Video Toolchain

Use the maintained central project at `~/Developer/visual-explainer-toolchain`. Its
`pyproject.toml` and `uv.lock` own ManimCE, Manim Voiceover, Gemini, Python
Typst, PyGfx/wgpu/rendercanvas, and Taichi. Video projects own only their
scenes, assets, configuration, and generated media.

The governing principle is:

> Select the simplest engine that communicates the intended idea, and justify every escalation in terms of visible benefit.

The user normally describes the desired visual result. Choose the engine, but
honor an explicit override unless a concrete constraint makes it impossible.

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
## Route each segment

Choose technology after identifying the visual job that each segment must do.

| Need | Route |
| --- | --- |
| Animated diagrams, labels, graphs, motion graphics, explanatory 2D, or simple clear 3D | Manim |
| Meshes, surfaces, point clouds, spatial fields, camera perspective, or lightweight scientific 3D | PyGfx |
| Analytically prescribed motion with modest state | NumPy + PyGfx |
| Many evolving particles/grids/fields, PDEs, or compute-heavy deformation | Taichi + PyGfx |
| Materials, lighting, anatomy, imported assets, volumetrics, rigging, or a cinematic shot that materially benefits | Blender (Runpod Serverless) |
| Beats that need different rendering strengths | Mixed segments + FFmpeg |

Do not choose Blender because an object is three-dimensional, or Taichi because
an object moves. Blender normally contributes one or a few shots whose material
or lighting makes a visible difference; Manim keeps explanatory graphics clear.

Useful routing checks:

- An annotated process or product-flow diagram: Manim.
- A triangulated model or spatial dataset: PyGfx.
- Tens of thousands of evolving particles: Taichi + PyGfx; benchmark locally
  before considering remote compute.
- A realistic translucent organ, material, or environment: Blender (rendered
  via Runpod Serverless).
- An explainer plus one photorealistic establishing shot: Manim + short Blender
  shot (Runpod Serverless) + FFmpeg.
- A rotating object: Manim or PyGfx unless realistic rendering is explicitly
  valuable.

For PyGfx and Taichi implementation details, including deterministic offscreen
rendering, backend policy, and reproducibility fields, read
[`references/pygfx-taichi.md`](references/pygfx-taichi.md).

## Apply subject-specific direction deliberately

Technology selection is not a story template. Decide the viewer, message,
emotional tone, and information sequence from the subject instead of forcing a
mathematical-explainer structure onto every topic.

For a mathematics educational video, read
[`references/math-educational-video.md`](references/math-educational-video.md)
before storyboarding. Its pedagogy, equation timing, and notation guidance are
specific to that format and must not be applied by default to other subjects.

For a medical, clinical-procedure, vaccine, pharmaceutical, or healthcare
marketing video, read
[`references/medical-video.md`](references/medical-video.md) before drafting
claims or storyboarding. It defines patient-education direction and mandatory
clinical, regulatory, and advertising-review gates; it is not medical or legal
approval for a particular script.

For any multi-segment video or independently produced narration, read
[`references/composition.md`](references/composition.md) before rendering to
settle shared technical delivery settings and transitions.

## Required Blender render-mode confirmation

Before starting any Blender render, determine whether the user wants a local
EEVEE test/preview or a Runpod Serverless Cycles production render. If the
request does not explicitly identify the mode, pause and ask one concise
question before running a render command:

> 이번 Blender 렌더는 (1) 로컬 EEVEE 테스트/프리뷰로 실행할까요, 아니면
> (2) Runpod Serverless Cycles 제작 렌더로 실행할까요?

Do not infer the mode from the presence of a Blender scene, a `--workers`
option, or a previous command. Do not start an expensive render while waiting
for the answer. A request that explicitly says `preview`, `test`, `local`, or
`EEVEE` selects the local path; a request that explicitly says `production`,
`Cycles`, `GPU`, or `Runpod` selects the Runpod path.

Once the mode is selected, state the choice briefly before execution and keep
the paths separate:

- **Local EEVEE test/preview:** use `visual-blender-preview` for a frame or a
  small diagnostic range. If multiple local workers are required, write PNGs
  and reports to `/private/tmp` (or another explicitly local scratch path),
  never to an iCloud-synchronized project directory. This path is for
  validation and framing, not final production quality.
- **Runpod Serverless Cycles production:** use
  `visual-runpod-prepare` → `visual-runpod submit` and the configured R2
  storage flow. Do not substitute local `parallel_blender_render.py`; one
  request maps to one remote GPU/Blender process, and chunk parallelism belongs
  to the endpoint queue. Tell the user that the job incurs Runpod usage cost
  and show the live progress command before or alongside submission.

If the user asks for both, run the local EEVEE validation first, report its
result, and request or confirm the transition to the Runpod production render
before submitting the paid job.

## Blender renders via Runpod Serverless; EEVEE for local preview

All Blender production rendering and Cycles image-sequence workloads are executed
remotely via **Runpod Serverless** (`visual-runpod-prepare` →
`visual-runpod submit`). Local Blender is used for scene authoring and rapid
composition/framing validation with lightweight EEVEE previews. Asset
portability validation runs in the worker by default.

Local preview workflow (explicitly selected local mode only):

```sh
visual-blender-preview --scene-script scenes/hero.py \
  --output media/previews/hero.png --width 1280 --height 720 --frame 1
```

`visual-blender-preview` uses configurable EEVEE defaults and does not save over
the source `.blend`. For transparent CLI or batch inspection, `visual-blender`
and `visual-blender-render` remain available locally. When using local parallel
workers, point frame and report outputs to `/private/tmp` or another local
scratch directory, especially when the project is inside iCloud Drive. Read
[`references/blender.md`](references/blender.md) for scene preparation, portable
assets, and local preview commands.

## Runpod Serverless for all Blender production rendering

Manim, ordinary PyGfx, Taichi simulations, EEVEE previews, and final FFmpeg
composition stay local by default. **Blender Cycles production rendering is
routed to Runpod Serverless.**

Prepare a portable Blender bundle locally:

```sh
visual-runpod-prepare \
  --scene scene.blend --scene-script scenes/hero.py --asset-dir assets \
  --output render-job --width 1920 --height 1080 --fps 30 \
  --frame-start 1 --frame-end 240 --chunk-size 60 --samples 128 --device auto
```

`visual-runpod-prepare` creates a self-contained input bundle with portable
asset metadata, an empty output directory, and a `runpod-serverless`
`render_manifest.json`. Local Blender validation is optional; the worker checks
the first chunk before rendering. Never upload credentials, `.env` files, ADC
paths, SSH keys, browser profiles, or unrelated repository data.

The worker image is built from `runpod/Dockerfile`, contains a pinned Blender
runtime, and is deployed to a Runpod Serverless endpoint. One request maps to
one GPU and one Blender process; horizontal parallelism comes from the endpoint
queue rather than multiple Blender processes inside one worker:

```text
job lifecycle:     prepare -> archive/upload -> submit chunks -> poll -> download -> verify
worker lifecycle:  cold start -> render one chunk -> upload -> idle/terminate
```

Put `RUNPOD_API_KEY` and `RUNPOD_ENDPOINT_ID`, plus the bucket-scoped
`R2_ACCOUNT_ID`, `R2_BUCKET`, `R2_ACCESS_KEY_ID`, and `R2_SECRET_ACCESS_KEY`, in
the protected central `.env` (mode `600`). `visual-runpod` loads that file and
can also use the standard `~/.runpod/config.toml` API-key fallback; generic
visualization wrappers do not inherit these credentials. Then submit the chunk
batch with automatic R2 presigning:

```sh
visual-runpod submit --bundle render-job --r2
# Follow live chunk/frame progress through Runpod /stream:
visual-runpod progress --jobs-file render-job.runpod.json --download
# Retry only failed R2 chunks with fresh signed URLs:
visual-runpod retry --jobs-file render-job.runpod.json
# After verifying and retaining the local output, delete this batch from R2:
visual-runpod cleanup --jobs-file render-job.runpod.json --confirm
```

The client and worker use SHA-256-checked tar archives rather than embedding PNG
data in Runpod JSON. The worker returns metadata and a signed output download
URL; the client verifies every chunk and the merged sequence locally. For
Blender, maintain the standard flow:
`remote Cycles PNG sequence -> local verification -> local FFmpeg composition`.

`progress` drains bounded worker events from Runpod `/stream` and prints phase,
chunk, completed-frame count, and percentage without printing signed URLs. Frame
progress is based on non-empty PNGs and remains reliable across Blender builds;
sample fields are included when Blender emits sample statistics. Use
`wait --stream` when a script should retain the normal wait command while
showing the same live progress.

Read [`references/runpod.md`](references/runpod.md) for the manifest, signed URL
boundary, worker image, chunk orchestration, and verification details.

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
