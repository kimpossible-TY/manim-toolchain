---
name: manim-toolchain
description: Create or verify intuition-first mathematical animation, scientific 3D visualization, simulation, or selectively high-fidelity mixed video with the shared Manim, PyGfx, Taichi, Blender, and FFmpeg toolchain.
---

# Mathematical Visualization Toolchain

Use the maintained central project at `~/Developer/manim-toolchain`. Its
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
- Prefer `from manim import Typst, MathTypst`; do not add a LaTeX distribution.

## Route each segment

Plan the intuition and visual transformation before choosing technology.

| Need | Route |
| --- | --- |
| Equations, diagrams, labels, transformations, graphs, explanatory 2D, or simple clear 3D | Manim |
| Meshes, surfaces, point clouds, spatial fields, camera perspective, or lightweight scientific 3D | PyGfx |
| Analytically prescribed motion with modest state | NumPy + PyGfx |
| Many evolving particles/grids/fields, PDEs, or compute-heavy deformation | Taichi + PyGfx |
| Materials, lighting, anatomy, imported assets, volumetrics, rigging, or a cinematic hero shot that materially benefits | Blender (Runpod Serverless) |
| Distinct explanatory and high-fidelity/numerical beats in one story | Mixed segments + FFmpeg |

Do not choose Blender because an object is three-dimensional, or Taichi because
an object moves. Blender normally contributes one or a few valuable shots;
Manim keeps the mathematical story legible.

Useful routing checks:

- Moving vector-field divergence: Manim; use PyGfx only if genuine spatial 3D
  adds insight.
- Triangulated sphere: PyGfx.
- Twenty-thousand particles in a vortex: Taichi + PyGfx, then benchmark local
  before considering remote compute.
- Realistic translucent bladder: Blender (rendered via Runpod Serverless).
- Equations, anatomical shot, and flow-rate graph: Manim + short Blender shot
  (Runpod Serverless) + FFmpeg.
- A rotating cube: Manim or PyGfx unless realistic rendering is explicitly
  valuable.

For PyGfx and Taichi implementation details, including deterministic offscreen
rendering, backend policy, and reproducibility fields, read
[`references/pygfx-taichi.md`](references/pygfx-taichi.md).

## Tell one mixed educational story

Use engines for successive beats of one idea, not as disconnected demos:

```text
Manim question/equation -> Manim geometric intuition
  -> PyGfx or Taichi/PyGfx numerical manifestation
  -> optional Blender hero shot (Runpod Serverless) -> Manim interpretation
```

Set resolution, FPS, background/color language, narration cadence, and
transition frames before rendering. Use the composition reference when the
result combines segments or separate narration:
[`references/composition.md`](references/composition.md).

## Blender renders via Runpod Serverless; EEVEE for local preview

All Blender production rendering and Cycles image-sequence workloads are executed
remotely via **Runpod Serverless** (`visual-runpod-prepare` →
`visual-runpod submit`). Local Blender is used for scene authoring and rapid
composition/framing validation with lightweight EEVEE previews. Asset
portability validation runs in the worker by default.

Local preview workflow:

```sh
visual-blender-preview --scene-script scenes/hero.py \
  --output media/previews/hero.png --width 1280 --height 720 --frame 1
```

`visual-blender-preview` uses configurable EEVEE defaults and does not save over
the source `.blend`. For transparent CLI or batch inspection, `visual-blender`
and `visual-blender-render` remain available locally. Read
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
visual-runpod wait --jobs-file render-job.runpod.json --download
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

Read [`references/runpod.md`](references/runpod.md) for the manifest, signed URL
boundary, worker image, chunk orchestration, and verification details.

## Keep narration separate from notation

Use visual Typst independently from spoken prose:

```python
visual = MathTypst(r"u_(t t) = c^2 Delta u")
narration = "Each point accelerates according to its local curvature."
```

Never send raw Typst, LaTeX-like source, code, or implementation notation to
Gemini TTS. Use Manim Voiceover only where it owns the timing naturally; create
narration for PyGfx/Blender independently when that makes the composition
clearer. Do not force a non-Manim segment into Manim Voiceover.

## Verify observable results

Do not claim success based on imports or device enumeration. Render requested
scenes and inspect valid, non-empty, non-uniform outputs; check Taichi numerical
state; use FFprobe for video; and retain seeds, step count, time step, backend,
and floating-point policy where they affect reproducibility.

Central credential-independent validation:

```sh
cd ~/Developer/manim-toolchain
./scripts/check_environment.sh
./scripts/render_smoke_tests.sh --typst-only
./scripts/render_smoke_tests.sh --visualization-only
./scripts/verify_external_wrapper.sh
```

After deliberate dependency changes, keep `pyproject.toml` and `uv.lock`
together, run `uv lock`, then `uv sync --frozen --no-managed-python`. Do not
change the central stack casually while authoring a video.
