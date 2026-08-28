# Central Mathematical Visualization Toolchain

This repository is the reusable, command-line environment for mathematical animation, lightweight 3D rendering, numerical simulation, narration, typesetting, and final encoding on this Mac. Individual video repositories keep only their scene code, assets, local configuration, and outputs.

The locked top-level stack is:

- Homebrew Python 3.13 as the base interpreter for the central `.venv`
- Manim Community Edition 0.21.0 with Python Typst support
- Manim Voiceover 0.4.0 with Gemini support
- PyGfx 0.17.0, wgpu 0.32.0, and rendercanvas 2.7.2
- Taichi 1.7.4
- system uv, Typst, FFmpeg/FFprobe, and SoX from Homebrew

The project intentionally has no Blender, GUI editor, web frontend, notebook runtime, CFD framework, Docker layer, second environment manager, or TeX distribution.

## System and Python ownership

Homebrew owns system-level executables only:

- `uv`
- `python@3.13`
- `typst`
- `ffmpeg` and its `ffprobe` executable
- `sox`

Before installing or changing a formula, inspect `brew config`, `brew doctor`, `brew list --versions <formula>`, and the resolved executable path. Do not reinstall a working formula merely to refresh it.

The central uv project owns every Python library, including Manim, Manim Voiceover, PyGfx, wgpu, rendercanvas, Taichi, `google-genai`, and the Python Typst binding. They belong only in `~/Developer/manim-toolchain/.venv`; never install them through Homebrew or global/user `pip`.

When rebuilding the environment, use the Homebrew interpreter explicitly and restore only the frozen lock:

```sh
uv venv --python /opt/homebrew/opt/python@3.13/bin/python3.13 --clear .venv
uv sync --frozen --no-managed-python
```

## Choose the lightest capable engine

```text
request
  -> mathematical explanation, equations, diagrams        -> Manim
  -> mesh, surface, point cloud, camera, scientific 3D     -> PyGfx
  -> analytically prescribed dynamic geometry              -> NumPy + PyGfx
  -> particle/grid/PDE computation                          -> Taichi + PyGfx
  -> explanation plus physical or numerical manifestation  -> mixed segments + FFmpeg
```

Manim remains the default for educational explanation, notation, vector diagrams, graphs, transformations, and simple 3D it can communicate clearly. Use PyGfx when actual mesh rendering, lighting, perspective, or camera motion is central. Add Taichi only when numerical evolution or parallel computation is genuinely useful. Novelty is not a reason to select a heavier engine.

## Central environment and wrappers

`pyproject.toml` and `uv.lock` are the only dependency source of truth. The global commands are symlinks into this repository:

```text
~/.local/bin/manim-video   -> ~/Developer/manim-toolchain/bin/manim-video
~/.local/bin/visual-python -> ~/Developer/manim-toolchain/bin/visual-python
```

`manim-video` runs the central Manim CLI and may load Gemini settings only from this repository's protected `.env`. `visual-python` runs ordinary Python with the central PyGfx/Taichi stack and always uses `--no-env-file`; it removes narration credential variables from its child process.

Both wrappers deliberately keep the caller's working directory. They ignore caller uv-project selection, `VIRTUAL_ENV`, `pyproject.toml`, and `.venv`, so relative assets and outputs remain in the video repository while its dependencies remain untouched. They do not use `uv tool install` and do not `cd` into this repository.

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

- `skills/manim-toolchain` routes and verifies the shared mathematical visualization workflow.
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

## Mixed educational scenes

Design a mixed result as one conceptual story—for example: motivating question in Manim, equation and geometric intuition in Manim, physical manifestation in PyGfx/Taichi, then interpretation back in Manim. Render each segment to a common frame size and rate, then compose reproducibly with FFmpeg.

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

Use Manim Voiceover for Manim-owned narration when convenient. A mixed scene may generate narration separately and combine it during final composition; Manim Voiceover does not need to own non-Manim segments.

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
                persona="A thoughtful mathematical educator speaking directly to one curious student",
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

The default profile is a warm, precise, intellectually curious educator speaking to one student. Definitions are calm and deliberate; questions are gently curious; geometric intuition is conversational; reveals have restrained discovery; technical derivations slow down; summaries settle calmly. The target is clarity before expressiveness—never a commercial, movie-trailer, or constantly excited voice.

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

The tests prove more than imports: the narration tests mock Gemini while exercising prompt construction and Manim Voiceover's real cache layer; Manim compiles Typst and produces video; PyGfx produces changing offscreen frames and an H.264 MP4; Taichi runs numerical kernels on Metal and CPU; Taichi particle data produces a PyGfx frame; and both wrappers are exercised from a temporary Python 3.14 project whose `.venv` and dependency file remain unchanged.

## Apple Silicon notes

- wgpu ships a native macOS ARM64 wheel and normally uses its Metal backend.
- PyGfx production rendering is verified through an offscreen RenderCanvas, not a visible window.
- Taichi 1.7.4 ships a CPython 3.13 macOS ARM64 wheel. Metal is the preferred accelerated backend here, with native ARM CPU as the safe fallback.
- Taichi emits an upstream `SyntaxWarning` from `taichi.tools.image` on its first Python 3.13 import; this does not affect tested kernels or PyGfx transfer.
- Renderer and simulation backends are printed by the smoke tests so runtime behavior is observable.

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
