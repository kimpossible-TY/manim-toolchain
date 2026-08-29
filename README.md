# Explanation Visualization and Simulation Toolchain

[![Python 3.13.15](https://img.shields.io/badge/Python-3.13.15-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Manim 0.21.0](https://img.shields.io/badge/Manim-0.21.0-333333)](https://www.manim.community/)
[![Manim Voiceover 0.4.0](https://img.shields.io/badge/Manim%20Voiceover-0.4.0-333333)](https://github.com/ManimCommunity/manim-voiceover)
[![Typst Python 0.15.0](https://img.shields.io/badge/Typst%20Python-0.15.0-239DAD?logo=typst&logoColor=white)](https://typst.app/)
[![Typst CLI 0.15.1](https://img.shields.io/badge/Typst%20CLI-0.15.1-239DAD?logo=typst&logoColor=white)](https://github.com/typst/typst)
[![PyGfx 0.17.0](https://img.shields.io/badge/PyGfx-0.17.0-6E56CF)](https://pygfx.org/)
[![wgpu 0.32.0](https://img.shields.io/badge/wgpu-0.32.0-6E56CF)](https://wgpu-py.readthedocs.io/)
[![rendercanvas 2.7.2](https://img.shields.io/badge/rendercanvas-2.7.2-6E56CF)](https://rendercanvas.readthedocs.io/)
[![Taichi 1.7.4](https://img.shields.io/badge/Taichi-1.7.4-F29111)](https://www.taichi-lang.org/)
[![google-genai 2.20.0](https://img.shields.io/badge/google--genai-2.20.0-4285F4?logo=google&logoColor=white)](https://github.com/googleapis/python-genai)
[![Blender 5.2.1](https://img.shields.io/badge/Blender-5.2.1-E87D0D?logo=blender&logoColor=white)](https://www.blender.org/)
[![FFmpeg 9.0.1](https://img.shields.io/badge/FFmpeg-9.0.1-007808?logo=ffmpeg&logoColor=white)](https://ffmpeg.org/)
[![SoX 14.4.2](https://img.shields.io/badge/SoX-14.4.2-6B4FBB)](https://sourceforge.net/projects/sox/)
[![uv 0.12.7](https://img.shields.io/badge/uv-0.12.7-6B4FBB)](https://docs.astral.sh/uv/)
[![Colab CLI 0.6.0](https://img.shields.io/badge/Colab%20CLI-0.6.0-F9AB00?logo=googlecolab&logoColor=white)](https://github.com/googlecolab/google-colab-cli)

This repository is a reusable, command-line environment for explaining ideas through visual stories: mathematical, scientific, technical, medical, product, process, or conceptual. It supports animation, scientific 3D, numerical simulation, selective high-fidelity Blender shots, narration, typesetting, and final FFmpeg composition. Math is a strong use case, not a boundary; video is one output format, not the only purpose. Individual projects keep only their scene code, assets, local configuration, and outputs.

The locked top-level stack is:

- Homebrew Python 3.13 as the base interpreter for the central `.venv`
- Manim Community Edition 0.21.0 with Python Typst support
- Manim Voiceover 0.4.0 with Gemini support
- PyGfx 0.17.0, wgpu 0.32.0, and rendercanvas 2.7.2
- Taichi 1.7.4
- system uv, Typst, FFmpeg/FFprobe, SoX, and native Blender from Homebrew

The project intentionally has no `bpy` dependency, GUI editor workflow, web frontend, notebook runtime, CFD framework, Docker layer, second Python environment manager, or TeX distribution. Blender remains a native application and its scripts use Blender's embedded Python.

## System and Python ownership

Homebrew owns system-level executables only:

- `uv`
- `python@3.13`
- `typst`
- `ffmpeg` and its `ffprobe` executable
- `sox`
- Blender, normally as a native macOS application or Homebrew cask
- the optional `google-colab-cli`, installed separately using its current official method

Before installing or changing a formula, inspect `brew config`, `brew doctor`, `brew list --versions <formula>`, and the resolved executable path. Do not reinstall a working formula merely to refresh it.

The central uv project owns every Python library, including Manim, Manim Voiceover, PyGfx, wgpu, rendercanvas, Taichi, `google-genai`, and the Python Typst binding. They belong only in `~/Developer/manim-toolchain/.venv`; never install them through Homebrew or global/user `pip`. Do not add `bpy` from PyPI; invoke Blender as `blender --background --python scene.py`.

When rebuilding the environment, use the Homebrew interpreter explicitly and restore only the frozen lock:

```sh
uv venv --python /opt/homebrew/opt/python@3.13/bin/python3.13 --clear .venv
uv sync --frozen --no-managed-python
```

## Choose the lightest capable engine for the explanation

```text
request
  -> mathematical explanation, equations, diagrams        -> Manim
  -> mesh, surface, point cloud, camera, scientific 3D     -> PyGfx
  -> analytically prescribed dynamic geometry              -> NumPy + PyGfx
  -> particle/grid/PDE computation                          -> Taichi + PyGfx
  -> realistic materials, anatomy, assets, cinematic shots -> Blender
  -> distinct explanatory and numerical/high-fidelity beats -> mixed segments + FFmpeg
```

Manim remains the default for clear explanation, notation, vector diagrams, graphs, transformations, and simple 3D it can communicate clearly. Use PyGfx when actual mesh rendering, lighting, perspective, or camera motion is central. Add Taichi only when numerical evolution or parallel computation is genuinely useful. Use Blender only when its materials, lighting, anatomy, imported assets, rigging, volumetrics, or cinematic presentation materially improve a small number of high-value shots. Novelty is not a reason to select a heavier engine.

## Central environment and wrappers

`pyproject.toml` and `uv.lock` are the only dependency source of truth. The global commands are symlinks into this repository:

```text
~/.local/bin/manim-video   -> ~/Developer/manim-toolchain/bin/manim-video
~/.local/bin/visual-python -> ~/Developer/manim-toolchain/bin/visual-python
~/.local/bin/visual-blender -> ~/Developer/manim-toolchain/bin/visual-blender
~/.local/bin/visual-blender-preview -> ~/Developer/manim-toolchain/bin/visual-blender-preview
~/.local/bin/visual-blender-render -> ~/Developer/manim-toolchain/bin/visual-blender-render
~/.local/bin/visual-colab-prepare -> ~/Developer/manim-toolchain/bin/visual-colab-prepare
~/.local/bin/visual-colab-stop (optional) -> ~/Developer/manim-toolchain/bin/visual-colab-stop
```

`manim-video` runs the central Manim CLI and may load Gemini settings only from this repository's protected `.env`. `visual-python` runs ordinary Python with the central PyGfx/Taichi stack and always uses `--no-env-file`; it removes narration credential variables from its child process.

Both wrappers deliberately keep the caller's working directory. They ignore caller uv-project selection, `VIRTUAL_ENV`, `pyproject.toml`, and `.venv`, so relative assets and outputs remain in the video repository while its dependencies remain untouched. They do not use `uv tool install` and do not `cd` into this repository.

`visual-blender` is a transparent call to the installed Blender executable. The preview/render helpers run Blender background mode with Blender's own Python; they never create or alter a caller Python environment. `visual-colab-prepare` only creates a local bundle and explicit commands—it cannot authenticate, upload, allocate a runtime, or begin remote work. `visual-colab-stop` is the explicit shutdown helper for the reusable Colab worker.

The equivalent generic invocation is:

```sh
uv run \
  --project /Users/taeyoung/Developer/manim-toolchain \
  --frozen \
  --no-managed-python \
  --no-env-file \
  -- python scenes/example.py
```

The shared Manim config is also owned here:

```text
~/.config/manim/manim.cfg -> ~/Developer/manim-toolchain/manim.cfg
```

A video repository may override it with a local `manim.cfg`.

## Codex skills

The repository owns two tracked skills:

- `skills/manim-toolchain` routes and verifies the shared explanation visualization workflow.
- `skills/publish-typst-supplement` publishes large generated supplements as versioned GitHub Release assets.

Codex discovers them through symlinks in `~/.codex/skills`. Keep the repository copies authoritative. For non-trivial Typst scene authoring, pair `manim-toolchain` with the separately maintained [`my-typst-style`](https://github.com/kimpossible-TY/typst-packages/tree/main/skills/my-typst-style) skill.

## Use from another video repository

Manim preview and production renders:

```sh
manim-video -pql scenes/explanation.py DivergenceExplanation
manim-video -qh scenes/explanation.py DivergenceExplanation
```

PyGfx or Taichi scene with explicit local output:

```sh
visual-python scenes/mesh_scene.py --output media/renders/mesh.mp4
visual-python scenes/simulation.py --output media/simulations/vortex.mp4
```

A useful new-project layout is:

```text
video-project/
├── scenes/
├── assets/
├── media/
│   ├── manim/
│   ├── renders/
│   └── simulations/
└── manim.cfg
```

This is a convention, not a requirement. Preserve an existing project's layout and use explicit output arguments for non-Manim scenes.

## Offscreen PyGfx rendering

Production PyGfx scenes use `rendercanvas.offscreen.RenderCanvas`, render deterministic RGBA frames, and pipe them to FFmpeg. No visible window or manual interaction is required. The maintained smoke scene is a small, readable template using upstream APIs directly:

```sh
visual-python /Users/taeyoung/Developer/manim-toolchain/scenes/pygfx_smoke_test.py \
  --output media/renders/mesh-smoke.mp4
```

The repository does not add a PyGfx scene DSL: direct RenderCanvas/PyGfx/FFmpeg code remains short and debuggable. The only small installed helper package is `manim_toolchain`, which supplies the reusable narration adapter below; it does not wrap graphics or simulation APIs. Interactive previews may use a supported rendercanvas GUI backend when useful, but they are not part of automated production rendering.

## Taichi computation

Taichi owns simulation state and kernels; PyGfx normally owns visualization:

```text
Taichi fields and kernels -> NumPy arrays -> PyGfx geometry -> offscreen frames -> FFmpeg
```

Prefer `ti.init(arch=ti.gpu, enable_fallback=True)` with Taichi 1.7.4. On this Apple Silicon machine that selects Metal when available and falls back to native CPU when needed; accept an explicit CPU option for reproducibility. Do not hardcode a GPU backend unless the simulation actually needs it.

Taichi 1.7.4's kernel parser is not compatible with postponed annotations on Python 3.13. In files that define kernels, omit `from __future__ import annotations`, keep kernel return values unannotated when there is no return, and let annotations such as `ti.f32` evaluate normally.

The combined smoke test supports explicit backend checks:

```sh
visual-python /Users/taeyoung/Developer/manim-toolchain/scenes/taichi_pygfx_smoke_test.py \
  --arch metal \
  --output media/simulations/particles.png

visual-python /Users/taeyoung/Developer/manim-toolchain/scenes/taichi_pygfx_smoke_test.py \
  --arch cpu --numerical-only
```

## Blender escalation and local preview

Blender is a conditional high-fidelity renderer, not the default 3D engine. Use it for a realistic translucent bladder, a product/anatomical model, complex shadows, depth of field, volumetrics, rigging, imported assets, or another shot where PyGfx cannot communicate the result efficiently. A rotating cube, triangulated sphere, or wave surface normally belongs in Manim, PyGfx, or Taichi + PyGfx.

Author reproducible scenes with regular Blender Python. Start with a local EEVEE background preview; the defaults are configurable through `VISUAL_BLENDER_PREVIEW_WIDTH`, `VISUAL_BLENDER_PREVIEW_HEIGHT`, `VISUAL_BLENDER_PREVIEW_SAMPLES`, and `VISUAL_BLENDER_PREVIEW_SCALE` and do not save over the source `.blend`:

```sh
visual-blender-preview --scene-script scenes/anatomy.py \
  --output media/previews/anatomy.png --width 1280 --height 720 --frame 1
```

Then render one representative Cycles frame—including an expensive frame—and compare local render time, memory pressure, and estimated total duration with remote setup/transfer cost. For final animation, use a PNG sequence rather than a remote MP4:

```sh
visual-blender-render --scene scene.blend --scene-script scenes/anatomy.py \
  --output media/blender/frame_ --frame-start 1 --frame-end 240 \
  --width 1920 --height 1080 --fps 30 --samples 128 --device auto

visual-python /Users/taeyoung/Developer/manim-toolchain/scripts/verify_frame_sequence.py \
  --directory media/blender --prefix frame_ --frame-start 1 --frame-end 240 \
  --width 1920 --height 1080
```

For a repeatable benchmark (wall time, peak child RSS where available, and an optional whole-range estimate):

```sh
visual-python /Users/taeyoung/Developer/manim-toolchain/scripts/benchmark_blender_render.py \
  --frame-count 240 --report media/benchmarks/cycles.json -- \
  visual-blender-render --scene scene.blend --output media/benchmarks/frame.png \
  --width 1920 --height 1080 --samples 128 --frame 120 --device cpu
```

The render helper records engine, resolution, color management, and configured Cycles device in a JSON report. It detects supported backends, falls back to CPU safely, and fails with `--require-gpu` when a requested GPU cannot be configured. A real Cycles image must exist before treating device configuration as a successful render.

## Optional Colab render and compute offload

Local execution is the default. Consider Colab only after a reduced local Taichi or Cycles benchmark shows that a GPU/memory advantage outweighs provisioning, dependency installation, upload, render, download, and final local composition. Colab is not the default for Manim, normal PyGfx, EEVEE previews, short renders, or FFmpeg composition.

Prepare a small, portable Blender bundle locally:

```sh
visual-colab-prepare \
  --scene scene.blend --scene-script scenes/anatomy.py --asset-dir assets \
  --output render-job --width 1920 --height 1080 --fps 30 \
  --frame-start 1 --frame-end 240 --samples 128 --device auto
```

This validates missing and unresolved absolute asset paths, copies only explicitly named assets, and creates `render_manifest.json`, `bootstrap.sh`, and authorization-marked `colab_commands.sh`. It does not perform a remote action. Starting a session, logging in, uploading assets, or consuming quota/credits requires explicit user authorization in that request. Never include `.env` files, credentials, browser profiles, unrelated repository files, private media, or datasets in a bundle.

The generated Colab commands use the separately installed official `google-colab-cli`; do not add it to this project. The normal reusable worker is `visual-render` with a default T4. Each job checks `colab sessions`, `colab status`, and a read-only `/content` probe before reusing it; an absent worker requires the explicit `--allow-new-session` flag (or `COLAB_ALLOW_NEW_SESSION=1`) before `colab new` can allocate one. A successful job leaves the session running for later jobs. When remote work is finished, run `visual-colab-stop` (or `./bin/visual-colab-stop`); `--stop-after-job` remains available for explicit disposable mode. Download PNG frames, verify their count/corruption/dimensions and completed Cycles report locally, then encode with local FFmpeg. The requested GPU flag is never treated as proof of actual GPU rendering.

```sh
# Reuse visual-render when it exists; authorize first allocation explicitly if absent.
./render-job/colab_commands.sh
./render-job/colab_commands.sh --allow-new-session

# After all remote jobs are downloaded and verified:
./bin/visual-colab-stop
```

## Mixed explanation scenes and composition

Design a mixed result as one conceptual story—for example: a motivating question in Manim, a diagram or notation beat, a PyGfx/Taichi manifestation, an optional short Blender hero shot, then a clear interpretation. The same structure works for a mathematical proof, a scientific process, a technical system, a medical explanation, or a product concept. Blender should not replace the clearest explanatory portions. Render each segment to a common frame size and rate, then compose reproducibly with FFmpeg.

For segments with matching stream parameters, create an ignored `segments.txt`:

```text
file 'media/manim/question.mp4'
file 'media/renders/wave-surface.mp4'
file 'media/manim/interpretation.mp4'
```

Then concatenate and attach separately generated narration:

```sh
ffmpeg -f concat -safe 0 -i segments.txt \
  -c:v libx264 -pix_fmt yuv420p -an media/combined-video.mp4

ffmpeg -i media/combined-video.mp4 -i media/narration.wav \
  -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -shortest media/final.mp4

ffprobe -v error -show_streams -show_format media/final.mp4
```

Reconcile FPS, resolution, pixel aspect ratio, alpha, audio sample rate, codec, and segment naming before rendering. Preserve each Blender render report with its image sequence: Blender's view transform/color management can differ from Manim and PyGfx, so inspect transition frames before final encoding. Use Manim Voiceover for Manim-owned narration when convenient. A mixed scene may generate narration separately and combine it during final composition; Manim Voiceover does not need to own non-Manim segments.

## Typst and expressive narration policy

Use `from manim import Typst, MathTypst` rather than LaTeX. `MathTypst` takes Typst math syntax without surrounding `$` delimiters. No MacTeX, BasicTeX, TinyTeX, or other LaTeX distribution is required.

Keep spoken prose independent from visual notation:

```python
visual = MathTypst(r"u_(t t) = c^2 Delta u")
narration = "Local curvature determines how the disturbance accelerates."
```

Never pass raw Typst or symbolic markup to Gemini TTS.

Narration is planned as performance, not appended to a completed animation. The runtime keeps three representations separate:

```text
spoken transcript + semantic delivery -> Gemini performance prompt -> audio
display subtitle -------------------------------------------------> captions
```

`NarrationSegment` and `NarrationProfile` are backend-neutral; Gemini-specific prompt construction lives in the `ExpressiveGeminiService` adapter. This keeps a future OpenAI, ElevenLabs, or local renderer from changing scene code.

Use the expressive scene and service for new Manim scenes:

```python
from manim_toolchain import NarrationProfile
from manim_toolchain.voiceover import ExpressiveGeminiService, ExpressiveVoiceoverScene


class Explanation(ExpressiveVoiceoverScene):
    def construct(self):
        self.set_narration_profile(
            NarrationProfile(
                persona="A thoughtful explainer speaking directly to one curious listener",
                tone="Warm, precise, and intellectually curious",
            )
        )
        self.set_speech_service(ExpressiveGeminiService(voice="Iapetus"))

        # Backward-compatible plain usage: sensible delivery is inferred.
        with self.voiceover(text="A distribution does not need a pointwise value.") as tracker:
            self.play(..., run_time=tracker.duration)

        # Explicit metadata overrides only the properties that need direction.
        with self.voiceover(
            text="But this is where something surprising happens.",
            intent="reveal",
            emotion="discovery",
            pace="slow",
            emphasis="something surprising",
            pause_after="medium",
        ) as tracker:
            self.play(..., run_time=tracker.duration)
```

The default profile is a warm, precise, intellectually curious explainer speaking to one listener. Definitions are calm and deliberate; questions are gently curious; mechanisms and intuition are conversational; reveals have restrained discovery; technical details slow down; summaries settle calmly. The target is clarity before expressiveness—never a commercial, movie-trailer, or constantly excited voice.

For common prose, delivery is inferred deterministically without another model. Questions infer `question`/`curious`; definition, contrast, reveal, transition, warning, and summary phrases supply corresponding defaults; equation-dense or long sentences slow down. Explicit `intent`, `emotion`, `pace`, `energy`, `emphasis`, and `delivery_notes` always win.

Use silence intentionally, rather than filling every animation beat with speech:

```python
with self.narrated("Now watch what happens when the probe moves.", intent="transition") as tracker:
    self.play(probe.animate.shift(RIGHT * 4), run_time=tracker.duration)

self.narration_pause("medium")  # visual-only breathing room

with self.say("How does the object respond to a probe?", pace="slow", pause_after="long"):
    pass
```

`narrated` and `say` are readable aliases for `voiceover`; all yield the ordinary `VoiceoverTracker`, so `tracker.duration`, bookmarks, captions, and Manim synchronization continue to work. `pause_before` and `pause_after` accept seconds or `brief` (0.35s), `medium` (0.6s), and `long` (0.9s). The actual timing comes from Manim, while Gemini receives only a compact natural-delivery instruction.

For pronunciation, use spoken prose and an optional visual subtitle instead of asking TTS to read source notation:

```python
with self.voiceover(
    text="f belongs to L two of R n.",
    subtitle="f ∈ L²(Rⁿ)",
    intent="define",
    pace="slow",
):
    ...
```

The opt-in `math_speech()` helper recognizes only a small set of common forms (`f(x)`, `L^2`, `R^n`, `nabla`, `lambda`, and partial derivatives). It deliberately is not a general Typst/LaTeX parser.

The Gemini cache key includes the normalized transcript, voice, model, profile, intent, emotion, pace, energy, emphasis, pauses, delivery notes, and prompt version. A discovery delivery cannot reuse the neutral recording of the same words. Captions always use only `subtitle` or the spoken transcript—never Gemini directions.

See [`scenes/expressive_voiceover_example.py`](scenes/expressive_voiceover_example.py) for a complete moving-probe scene with neutral explanation, question, contrast, reveal, silence, tracker-timed animation, and separate mathematical pronunciation.

## Gemini credentials

Gemini credentials remain isolated in this repository. `manim-video` loads only the protected central `.env` through uv's dotenv parser and refuses unsafe file permissions. Never put a key, ADC token, or credential path in scene code, a command line, a video repository, dependency files, logs, or generated media.

Configure API-key mode privately:

```sh
cd /Users/taeyoung/Developer/manim-toolchain
cp .env.example .env
chmod 600 .env
${EDITOR:-vi} .env
```

ADC remains available when the central `.env` selects `GEMINI_AUTH_MODE=adc` and provides non-secret project/location settings. Interactive authentication belongs to the user.

## Checks and smoke tests

Install exactly the committed environment and run credential-independent validation:

```sh
cd /Users/taeyoung/Developer/manim-toolchain
uv sync --frozen --no-managed-python
./scripts/check_environment.sh
./scripts/render_smoke_tests.sh --typst-only
./scripts/render_smoke_tests.sh --narration-only
./scripts/render_smoke_tests.sh --visualization-only
./scripts/render_smoke_tests.sh --blender-only
./scripts/verify_external_wrapper.sh
```

Targeted graphics checks are also available:

```sh
./scripts/render_smoke_tests.sh --pygfx-only
./scripts/render_smoke_tests.sh --taichi-only
```

After Gemini credentials are configured:

```sh
./scripts/render_smoke_tests.sh --voiceover-only
```

The tests prove more than imports: the narration tests mock Gemini while exercising prompt construction and Manim Voiceover's real cache layer; Manim compiles Typst and produces video; PyGfx produces changing offscreen frames and an H.264 MP4; Taichi runs numerical kernels on Metal and CPU; Taichi particle data produces a PyGfx frame; Blender produces a real EEVEE image and a real Cycles CPU image; and all wrappers are exercised from a temporary Python 3.14 project whose `.venv` and dependency file remain unchanged.

## Apple Silicon notes

- wgpu ships a native macOS ARM64 wheel and normally uses its Metal backend.
- PyGfx production rendering is verified through an offscreen RenderCanvas, not a visible window.
- Taichi 1.7.4 ships a CPython 3.13 macOS ARM64 wheel. Metal is the preferred accelerated backend here, with native ARM CPU as the safe fallback.
- Taichi emits an upstream `SyntaxWarning` from `taichi.tools.image` on its first Python 3.13 import; this does not affect tested kernels or PyGfx transfer.
- Renderer and simulation backends are printed by the smoke tests so runtime behavior is observable.
- Blender 5.2.1 LTS is installed as a native Apple Silicon application. Local EEVEE previews and Cycles CPU are tested; GPU success is reported only if an actual Cycles GPU render completes.
- `google-colab-cli` 0.6.0 is installed separately as an optional uv tool. It is not contacted by local validation.

## Maintain the toolchain

After deliberate dependency changes:

```sh
uv lock
uv sync --frozen --no-managed-python
```

Commit `pyproject.toml` and `uv.lock` together only after the real render and isolation tests pass. Never install these dependencies manually into `.venv` or add them to individual video projects.

The tracked Codex skill lives at `skills/manim-toolchain`; its installed path is a symlink back to this repository. Edit the tracked copy and validate it with the Codex skill validator.

## Official references

- [PyGfx offscreen rendering](https://docs.pygfx.org/stable/_gallery/introductory/offscreen.html)
- [wgpu-py](https://wgpu-py.readthedocs.io/)
- [rendercanvas](https://rendercanvas.readthedocs.io/)
- [Taichi documentation](https://docs.taichi-lang.org/)
- [Manim Typst classes](https://docs.manim.community/en/stable/reference/manim.mobject.text.typst_mobject.html)
- [Manim Voiceover](https://github.com/ManimCommunity/manim-voiceover)
- [uv `run --project`](https://docs.astral.sh/uv/reference/cli/#uv-run)
- [Blender command line](https://docs.blender.org/manual/en/latest/advanced/command_line/arguments.html)
- [Official google-colab-cli](https://github.com/googlecolab/google-colab-cli)
