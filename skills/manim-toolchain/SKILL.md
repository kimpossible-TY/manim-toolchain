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
| Materials, lighting, anatomy, imported assets, volumetrics, rigging, or a cinematic hero shot that materially benefits | Blender |
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
- Realistic translucent bladder: Blender.
- Equations, anatomical shot, and flow-rate graph: Manim + short Blender shot
  + FFmpeg.
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
  -> optional Blender hero shot -> Manim interpretation
```

Set resolution, FPS, background/color language, narration cadence, and
transition frames before rendering. Use the composition reference when the
result combines segments or separate narration:
[`references/composition.md`](references/composition.md).

## Blender is conditional and local-first

For normal Blender work, author an ordinary scene script and use the transparent
`visual-blender` wrapper, or the small convenience wrappers:

```sh
visual-blender-preview --scene-script scenes/hero.py \
  --output media/previews/hero.png --width 1280 --height 720 --frame 1

visual-blender-render --scene scene.blend --scene-script scenes/hero.py \
  --output media/blender/frame_ --frame-start 1 --frame-end 240 \
  --width 1920 --height 1080 --fps 30 --samples 128
```

`visual-blender-preview` uses configurable EEVEE defaults and does not save the
source `.blend`. `visual-blender-render` emits PNG sequences by default, with a
JSON report of engine, color settings, render configuration, and configured
Cycles device. A device listing is not proof of success: require a real render
and verify its output before reporting a GPU result.

Before a final Cycles run: make an EEVEE preview, render representative Cycles
frames including an expensive one, measure time and memory pressure, estimate
the full cost, then compare that with remote setup and transfer overhead. Read
[`references/blender.md`](references/blender.md) for device handling, portable
assets, frame batches, and local commands.

## Local first; remote only with authorization

Manim, ordinary PyGfx, EEVEE previews, short Blender renders, and final FFmpeg
composition stay local by default. Route Taichi CUDA or costly Cycles batches to
Colab only after a reduced local benchmark shows a useful advantage.

`visual-colab-prepare` only creates a minimal validated bundle and explicit
commands; it never logs in, uploads, provisions a runtime, or starts a job.
Colab remains optional and local-first. Before an action that uploads assets,
starts remote computation, consumes GPU quota/credits, or allocates a new
runtime, obtain explicit authorization in the current request. Never upload
credentials, ADC files, SSH/private keys, browser profiles, unrelated
repository files, `.env` files, or confidential datasets that were not
explicitly included. If login is interactive, stop and ask the user to
complete it.

The default reusable remote worker is named `visual-render` and requests a T4.
The generated workflow checks the installed official Colab CLI for that named
session before creating anything:

```text
job lifecycle:     prepare -> upload -> execute -> download -> verify
session lifecycle: create -> reuse for zero or more jobs -> explicit stop
```

If `visual-render` is healthy and reachable, reuse it without another
allocation prompt; do not ask for a second allocation authorization solely
because that already-authorized worker is reused for another job in the same
explicit remote workflow. If it is absent, `colab_commands.sh` refuses to allocate a
runtime unless it is run with the explicit `--allow-new-session` flag (or
`COLAB_ALLOW_NEW_SESSION=1`). A session's accelerator is fixed for its
lifetime: never report an existing T4 as L4/A100/H100, and use a different
named session or stop the old one before requesting another accelerator.
`COLAB_GPU` overrides the request for a new or explicitly named session, but
the backend's actual hardware is checked before upload; there is no silent
fallback. T4 is the default, and no accelerator is escalated automatically.

Normal jobs leave the reusable session running. Use the separate
`visual-colab-stop` helper (or `./bin/visual-colab-stop`) when remote work is
finished. The generated script also supports the explicitly disposable
`--stop-after-job` mode. A failed job does not stop a healthy shared session.

Remote `/content` storage is ephemeral cache, not durable storage. Every job
uses a unique remote directory under `/content/manim-toolchain/jobs/`, and
important PNG/OpenEXR outputs and reports must return to local storage. For
Blender, keep the flow `remote Cycles PNG sequence -> local verification ->
local FFmpeg composition`; never depend on an artifact left in `/content` for
correctness. The bundle is self-contained enough to bootstrap a fresh
authorized session, while reusing an already-installed compatible Blender
instead of reinstalling it on every job.

Read [`references/colab.md`](references/colab.md) when preparing or evaluating
remote work. It covers the `render-job/` manifest, upload boundary, and
reusable-session policy, job isolation, and resumable image-sequence return
flow.

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
