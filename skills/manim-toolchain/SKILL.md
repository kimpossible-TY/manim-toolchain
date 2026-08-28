---
name: manim-toolchain
description: Use the central uv-managed mathematical visualization toolchain on this Mac when creating, rendering, debugging, or verifying Manim explanations, PyGfx 3D scenes, Taichi simulations, Typst mathematics, Gemini narration, or mixed FFmpeg-composed videos. Favor intuition-led storytelling and keep dependencies and credentials out of individual video repositories.
---

# Mathematical Visualization Toolchain

Use the maintained project at `~/Developer/manim-toolchain`. Its `pyproject.toml` and `uv.lock` define the available versions and APIs for ManimCE, Manim Voiceover, Gemini, Typst, PyGfx, wgpu/rendercanvas, and Taichi.

## Choose the lightest capable engine

Plan the conceptual story first, then route each segment by what must be communicated. Do not choose an engine based on novelty. Choose the simplest engine that communicates the intended intuition.

Use Manim when:

- equations and notation are central;
- the explanation is primarily conceptual;
- graphs, arrows, transformations, annotations, or geometric reasoning communicate the idea;
- ordinary 2D educational animation is appropriate;
- simple Manim 3D is enough.

Use PyGfx when:

- actual 3D mesh or surface rendering matters;
- perspective, lighting, camera motion, or spatial depth matters;
- the scene is primarily 3D geometry, a point cloud, or scientific visualization;
- mesh deformation, scalar fields, or vector fields are easier to express directly than in Manim.

Use NumPy + PyGfx when motion is analytically prescribed or state updates are light enough that no simulation engine is needed. An object moving, rotating, or deforming does not by itself justify Taichi.

Use Taichi + PyGfx when:

- many state variables must evolve numerically;
- particle count is large;
- a grid, cellular system, many-body model, or numerical PDE must evolve;
- parallel numerical computation is the bottleneck.

Taichi is the compute layer, not the general scene-authoring layer. Normally transfer its fields to NumPy arrays and update PyGfx geometry. Prefer a Taichi-native renderer only when it is clearly sufficient and materially simpler.

Use mixed rendering when the educational story benefits from both mathematical explanation and physical or numerical manifestation. Render segments with their natural engines and compose them with FFmpeg.

Typical routing:

```text
"Explain divergence visually"                         -> Manim
"Rotate a triangulated sphere and show its faces"     -> PyGfx
"Animate an analytically deforming surface"           -> NumPy + PyGfx
"Advect 20,000 particles through a vortex"            -> Taichi + PyGfx
"Explain the wave equation, then simulate the wave"   -> Manim + Taichi + PyGfx + FFmpeg
```

The user does not need to name an engine. Respect an explicit override unless it conflicts with a concrete technical constraint, in which case explain the constraint.

## Preserve the central architecture

- Treat Homebrew as the owner of system executables only: `uv`, `python@3.13`, `typst`, `ffmpeg`/`ffprobe`, and `sox`. Inspect formula and executable state before installing anything; do not reinstall working formulas.
- Keep Manim, Manim Voiceover, `google-genai`, Python `typst`, PyGfx, wgpu, rendercanvas, Taichi, and all other Python libraries exclusively in the central uv project. Never install them with Homebrew or global/user `pip`.
- Base the central `.venv` on `/opt/homebrew/opt/python@3.13/bin/python3.13` and use uv with managed-Python fallback disabled. Rebuild with `uv venv --python /opt/homebrew/opt/python@3.13/bin/python3.13 --clear .venv`, then `uv sync --frozen --no-managed-python`.
- Use `manim-video` for Manim and `visual-python` for ordinary Python/PyGfx/Taichi scripts.
- Run both wrappers from the video repository. They preserve its working directory, relative assets, and output paths while selecting `~/Developer/manim-toolchain/.venv`.
- Do not add Manim, Manim Voiceover, `google-genai`, Python `typst`, PyGfx, wgpu, rendercanvas, or Taichi to a video repository's `pyproject.toml`.
- Do not create or activate a visualization `.venv` in a video repository. Its unrelated Python project and `.venv` must remain untouched.
- Do not migrate the toolchain to `uv tool install` or another environment manager.
- Keep shared Manim defaults in the central `manim.cfg`; allow project-local overrides.
- Do not introduce Blender, Unity, Unreal, Three.js, a required Jupyter runtime, ParaView, a heavy CFD framework, a web frontend, Docker, or a GUI editor for this workflow.
- Use Typst rather than LaTeX. Do not install a TeX distribution unless the user explicitly changes this constraint and a required feature cannot work with Typst.

The wrapper commands are conceptually:

```sh
manim-video -pql scenes/explanation.py Explanation
visual-python scenes/mesh_scene.py --output media/renders/mesh.mp4
visual-python scenes/simulation.py --output media/simulations/vortex.mp4
```

`visual-python` never loads the central `.env` and removes narration credential variables from its child process. Use `manim-video` for the existing protected Gemini credential path.

## Inspect before changing infrastructure

Inspect the target repository and preserve existing files, structure, and unrelated changes. Before changing this central toolchain, authentication, wrappers, shared configuration, or locked dependencies, read `~/Developer/manim-toolchain/README.md` and inspect Git state.

Useful checks:

```sh
brew config
brew doctor
brew list --versions uv python@3.13 typst ffmpeg sox
command -v manim-video
command -v visual-python
cd ~/Developer/manim-toolchain
./scripts/check_environment.sh
```

Ordinary scene authoring does not require rereading the central README.

## Build explanations around intuition

Identify the single conceptual takeaway before authoring. Establish the motivating question, a concrete mental model, and the key change in viewpoint before formal notation.

- Treat equations as landmarks that name or summarize an idea, not as the default sequence.
- Do not default to line-by-line expansion or rearrangement. Include symbolic steps when they reveal why something works, change the interpretation, or supply requested rigor.
- Prefer visual evidence—geometry, motion, comparison, examples, units, invariants, or physical behavior—before symbolic manipulation.
- Keep on-screen mathematics selective enough to absorb while animation moves.
- If the user requests a derivation or proof, organize it around purpose and insight rather than an uninterrupted wall of equations.

Use the same principle across mixed scenes. A simulator is evidence inside the explanation, not a disconnected technology demonstration.

## Design mixed scenes as one story

A useful sequence is:

```text
Manim: mathematical question
  -> Manim: equation and geometric intuition
  -> PyGfx/Taichi: physical or spatial manifestation
  -> Manim: interpretation and abstraction
```

For a wave equation scene:

```text
show u_tt = c² Δu
  -> explain local curvature visually
  -> numerically evolve a surface
  -> render the propagating wave in 3D
  -> return to the equation and interpret what changed
```

Define shared visual continuity before rendering: aspect ratio, frame size, FPS, background/color language, camera intent, narration cadence, and transition frames. Let each engine render what it expresses best.

## Author Manim segments

Use the installed Typst classes:

```python
from manim import MathTypst, Typst
```

- Use `Typst` for ordinary markup.
- Use `MathTypst` for math-mode content without surrounding `$` delimiters.
- For selectable mathematical subexpressions, prefer labeled `{{ ... }}` groups and `.select()`.
- Do not translate LaTeX examples mechanically. LaTeX commands, packages, `TexTemplate`, TeX-string matching helpers, and `TransformMatchingTex` are not drop-in Typst APIs.

For non-trivial Typst authoring, also load `$my-typst-style` from `~/.codex/skills/my-typst-style/SKILL.md`. Apply only syntax, imports, and macros available to the scene's Typst compilation context. Project-local conventions take precedence.

Development and production:

```sh
manim-video -pql scenes/example.py ExampleScene
manim-video -qh scenes/example.py ExampleScene
```

Forward user-provided Manim flags and scene arguments unchanged. Output normally lands under the caller's configured `media/` directory.

## Author PyGfx segments

Write normal, human-readable Python using upstream PyGfx APIs. For production:

- use `rendercanvas.offscreen.RenderCanvas`;
- set width, height, FPS, frame count/duration, and output explicitly;
- use deterministic time or frame-index loops rather than GUI event timing;
- retrieve RGBA frames with `canvas.draw()` and pipe them to FFmpeg;
- encode H.264 MP4 with `yuv420p` for broad compatibility;
- report or verify the wgpu backend when environment behavior matters;
- use interactive rendercanvas backends only as optional previews.

The maintained `scenes/pygfx_smoke_test.py` is a direct-API template for an offscreen mesh, deterministic rotation, and FFmpeg pipe. Copy or adapt the relevant pattern into a target project; do not import smoke-test code as a framework.

Keep generated code close to PyGfx. Do not invent a scene DSL, wrap every object, or hide cameras/materials/render loops behind excessive abstraction. A tiny project-local helper is justified only when it removes repeated boilerplate without obscuring upstream APIs.

## Author Taichi simulations

Keep state and numerical kernels in Taichi, then expose only the arrays needed for visualization. Avoid per-frame Python loops over large state.

Prefer portable initialization:

```python
import taichi as ti

ti.init(arch=ti.gpu, enable_fallback=True)
```

On this Apple Silicon machine, Metal is the preferred accelerated backend and native ARM CPU is the safe fallback. Provide an explicit CPU option when determinism, debugging, or deployment portability matters. Do not blindly hardcode Metal in reusable target scenes.

With Taichi 1.7.4 on Python 3.13, do not enable postponed annotations in a file that defines kernels. Leave no-return kernels without a return annotation, and let parameter annotations such as `ti.f32` evaluate normally; stringified annotations are rejected by this version's kernel parser.

Transfer render data explicitly:

```text
Taichi fields -> .to_numpy() -> PyGfx Geometry/Buffer update -> offscreen render
```

For long simulations, separate state stepping from presentation cadence: multiple simulation steps may feed one rendered frame. Keep seeds, time step, particle/grid size, and output duration explicit.

## Plan narration and animation together

Narration is part of the animation, not a flat TTS pass added after visual work. For every meaningful beat, plan a synchronized unit:

```text
idea -> visual action -> spoken transcript -> delivery function -> timing -> performance
```

Before coding, write a compact beat table in scene notes or the task response when it helps:

| Beat | Visual action | Narration | Delivery | Timing |
| --- | --- | --- | --- | --- |
| 1 | Show the object and its familiar values | "Normally, we ask for the value at each point." | explain, neutral, moderate | animate with tracker |
| 2 | Fade values; introduce a smooth probe | "But a distribution asks a completely different question." | contrast, thoughtful, slow; emphasize the contrast | leave a visual beat after |
| 3 | Slide the probe | "How does this object respond to a probe?" | question, curious, slow | let the question land before motion continues |

Use direct-attention phrases only when a corresponding change is genuinely visible: “Look at this region,” “Now watch what happens here,” “But notice what disappeared,” or “This is the important part.” Do not narrate visual facts the viewer can comfortably inspect in silence.

Prefer a question -> visual anticipation -> pause -> reveal sequence over uninterrupted exposition. Add visual-only room when an equation appears, a diagram transforms, a comparison becomes obvious, a geometric relation needs inspection, or a reveal should land. Never fill silence merely because audio could be continuous.

The expressive narrator is deliberately restrained. The priority is:

```text
clarity > naturalness > intellectual curiosity > emotional expressiveness
```

Avoid commercial, announcer, trailer, or permanently excited delivery. Definitions are calm and precise; questions are gently curious; geometric intuition is fluid and conversational; conceptual reveals have restrained discovery; derivations are slower and exact; summaries are calm and confident.

## Use structured narration with Manim

For new narrated Manim scenes, use the toolchain adapter:

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

        # Existing plain usage remains valid and gets sensible inferred delivery.
        with self.voiceover(text="A function maps points to values.") as tracker:
            self.play(..., run_time=tracker.duration)

        with self.voiceover(
            text="But here is the key idea.",
            intent="reveal",
            emotion="discovery",
            pace="slow",
            emphasis="key idea",
            pause_after="medium",
        ) as tracker:
            self.play(..., run_time=tracker.duration)
```

`self.narrated(...)` and `self.say(...)` are aliases for `self.voiceover(...)`; all yield the normal `VoiceoverTracker`. Always derive synchronous animation duration from `tracker.duration`; do not guess speech duration. Use `self.narration_pause("brief" | "medium" | "long" | seconds)` for intentional visual-only silence. `pause_before` and `pause_after` add the same silence around a segment without contaminating the audio transcript.

The backend-neutral `NarrationSegment` supports `text`, optional `subtitle`, `intent`, `emotion`, `pace`, `energy`, `emphasis`, pauses, and delivery notes. Use concise semantic values:

```python
with self.voiceover(
    text="f belongs to L two of R n.",
    subtitle="f ∈ L²(Rⁿ)",
    intent="define",
    pace="slow",
):
    ...
```

Keep spoken transcript, displayed notation, subtitles, and Gemini performance instructions separate. Never send raw Typst, symbolic markup, or code to Gemini TTS. Do not leak prompt directions into captions. Use explicit spoken prose for mathematical pronunciation; `math_speech()` is an opt-in helper for only a small set of common forms, not a general markup parser.

When no metadata is supplied, deterministic inference uses questions, definition/contrast/reveal/summary/transition cues, equation density, and sentence length. It is a starting point, not an excuse to skip deliberate beat planning. Explicit values always override it.

The Gemini adapter converts profile plus resolved delivery into a compact Audio Profile, Scene Context, Director's Notes, Delivery, and Transcript prompt. Its cache input includes normalized transcript, voice, model, profile, delivery metadata, and prompt version. Never manually reuse a cache recording across materially different delivery directions.

For PyGfx/Taichi segments, generate structured narration separately if that keeps composition clearer, then combine visual segments and audio with FFmpeg. Do not force Manim Voiceover to own a non-Manim scene just to obtain narration; retain the same transcript/performance/subtitle separation.

The central `.env` is the only toolchain credential file. Never read, print, echo, copy, or log credential values. Never place keys, ADC tokens, or credential paths in scene source, command lines, video repositories, dependency files, or generated outputs. Interactive ADC login belongs to the user.

## Compose and verify outputs

Prefer explicit output directories while preserving existing project conventions:

```text
media/manim/
media/renders/
media/simulations/
```

Render mixed segments to common dimensions and FPS. Compose with reproducible FFmpeg concat/filter commands, attach narration/audio, then inspect the final file with FFprobe. Do not introduce a heavyweight NLE or timeline framework unless the user explicitly requires one.

For syntax checks through the central environment:

```sh
visual-python -m py_compile scenes/mesh_scene.py scenes/simulation.py
```

Do not claim success from imports alone. Render requested scenes, check numerical invariants, verify non-empty and non-uniform frames, inspect produced videos with FFprobe, and investigate warnings or backend fallbacks that affect correctness.

Toolchain-wide credential-independent validation:

```sh
cd ~/Developer/manim-toolchain
./scripts/check_environment.sh
./scripts/render_smoke_tests.sh --typst-only
./scripts/render_smoke_tests.sh --visualization-only
./scripts/verify_external_wrapper.sh
```

After Gemini credentials are configured privately:

```sh
./scripts/render_smoke_tests.sh --voiceover-only
```

## Maintain the central toolchain only when requested

Dependency, wrapper, shared-config, credential-mode, and skill changes belong in `~/Developer/manim-toolchain`, never in a video repository. Preserve Git history and unrelated changes. Keep `pyproject.toml` and `uv.lock` together, run `uv lock` after declaration changes, install with `uv sync --frozen --no-managed-python`, and rerun real render plus external-isolation checks.

The tracked skill is `~/Developer/manim-toolchain/skills/manim-toolchain`. Its installed path, `~/.codex/skills/manim-toolchain`, is a symlink to that directory. Edit and validate the tracked package.
