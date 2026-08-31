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
- Keep credentials solely in the protected central `.env`. `visual-python`
  removes narration credentials. Never put keys, ADC paths, browser profiles,
  or secrets into a scene, `.blend`, manifest, render bundle, or log.
- Prefer `from manim import Typst, MathTypst`; do not add a LaTeX distribution.

## Route each segment

Plan the intuition and visual transformation before choosing technology.

| Need | Route |
| --- | --- |
| Equations, diagrams, labels, transformations, graphs, explanatory 2D, or simple clear 3D | Manim |
| Meshes, surfaces, point clouds, spatial fields, camera perspective, or lightweight scientific 3D | PyGfx |
| Analytically prescribed motion with modest state | NumPy + PyGfx |
| Many evolving particles/grids/fields, PDEs, or compute-heavy deformation | Taichi + PyGfx |
| Materials, lighting, anatomy, imported assets, volumetrics, rigging, or a cinematic hero shot that materially benefits | Blender (Colab CLI) |
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
- Realistic translucent bladder: Blender (rendered via Colab CLI).
- Equations, anatomical shot, and flow-rate graph: Manim + short Blender shot
  (Colab CLI) + FFmpeg.
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
  -> optional Blender hero shot (Colab CLI) -> Manim interpretation
```

Set resolution, FPS, background/color language, narration cadence, and
transition frames before rendering. Use the composition reference when the
result combines segments or separate narration:
[`references/composition.md`](references/composition.md).

## Blender renders via Colab CLI; EEVEE for local preview

All Blender production rendering and Cycles image-sequence workloads are executed
remotely via **Colab CLI** (`visual-colab-prepare` → `colab_commands.sh`).
Local Blender is used strictly for scene authoring, rapid composition/framing
validation with lightweight EEVEE previews, and asset portability checks.

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

## Colab CLI for all Blender production rendering

Manim, ordinary PyGfx, EEVEE previews, and final FFmpeg composition stay local
by default. **All Blender Cycles renders and heavy simulation compute are
routed to Colab CLI.**

Prepare a portable Blender bundle locally:

```sh
visual-colab-prepare \
  --scene scene.blend --scene-script scenes/hero.py --asset-dir assets \
  --output render-job --width 1920 --height 1080 --fps 30 \
  --frame-start 1 --frame-end 240 --samples 128 --device auto
```

`visual-colab-prepare` creates a self-contained, validated bundle with portable
asset checks, `render_manifest.json`, `bootstrap.sh`, and `colab_commands.sh`.
Starting a session, uploading assets, or consuming GPU quota requires explicit
user authorization in that request. Never upload credentials, `.env` files, ADC
paths, SSH keys, browser profiles, or unrelated repository data.

The default reusable remote worker is named `visual-render` (requesting a T4 or
configured GPU). Thanks to pre-built portable tarball installation and persistent
session reuse (`reuse-before-create`):

```text
job lifecycle:     prepare -> upload -> execute -> download -> verify
session lifecycle: create -> reuse for zero or more jobs -> explicit stop
```

- If `visual-render` is running and reachable, subsequent jobs reuse it
  instantly (`COLAB_SESSION_ACTION=reused`, `REMOTE_BLENDER_ACTION=reused`) with
  zero re-installation overhead.
- If absent, `colab_commands.sh` allocates a runtime when authorized with
  `--allow-new-session` (or `COLAB_ALLOW_NEW_SESSION=1`).
- Normal jobs leave the reusable session running. Use `visual-colab-stop`
  (or `./bin/visual-colab-stop`) when all remote rendering work is finished.

Remote `/content` storage is ephemeral cache. Every job uses a unique remote
directory under `/content/manim-toolchain/jobs/`, and generated PNG sequences
and reports return to local storage. For Blender, maintain the standard flow:
`remote Cycles PNG sequence -> local verification -> local FFmpeg composition`.

Read [`references/colab.md`](references/colab.md) for manifest structure,
upload boundaries, session lifecycle, and verification details.

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
