---
name: manim-toolchain
description: Use the central uv-managed Manim Community Edition toolchain on this Mac when creating, editing, rendering, debugging, or verifying Manim scenes, Typst mathematics, or Gemini voiceover. Pair Typst authoring with $my-typst-style, favor intuition-led storytelling over equation-by-equation expansion, and keep animation dependencies and credentials out of individual video repositories.
---

# Manim Toolchain

Use the maintained project at `~/Developer/manim-toolchain` and the global `manim-video` wrapper. Treat its `pyproject.toml` and `uv.lock` as the source of truth for package versions and APIs.

## Preserve the architecture

- Run Manim from the video repository's working directory with `manim-video`; relative scene paths and generated media must remain relative to that caller.
- Do not add Manim, Manim Voiceover, `google-genai`, or the Python `typst` package to a video repository's `pyproject.toml`.
- Do not create or activate a Manim `.venv` in a video repository. The wrapper selects `~/Developer/manim-toolchain/.venv` even when the caller has an unrelated `pyproject.toml` or `.venv`.
- Keep shared defaults in the central `manim.cfg`. A repository may have its own `manim.cfg` for local overrides.
- Do not use `uv tool install` as the primary installation architecture.
- Use Typst rather than LaTeX. Do not install MacTeX, BasicTeX, TinyTeX, or another TeX distribution unless the user explicitly changes this requirement and a necessary feature cannot work with Typst.

## Inspect before changing

Inspect the target repository and preserve existing files and unrelated changes. Confirm the wrapper and central project when environment state matters:

```sh
command -v manim-video
cd ~/Developer/manim-toolchain
./scripts/check_environment.sh
```

Read `~/Developer/manim-toolchain/README.md` before changing the toolchain itself, authentication mode, wrapper, shared configuration, or locked dependencies. Ordinary scene authoring does not require rereading it.

## Pair Typst work with the user's style

For tasks that author, edit, review, or generate non-trivial Typst content, load and follow `$my-typst-style` from `~/.codex/skills/my-typst-style/SKILL.md` alongside this skill. Do not load it for environment-only maintenance that does not touch Typst content.

- Inspect the target repository's style guide, imports, and available macros first. Project-local conventions and publisher requirements take precedence over the personal style.
- Apply the mathematical-writing, diagram, annotation, layout, and validation guidance that is relevant to the requested scene or companion document.
- In Manim `Typst` and `MathTypst` strings, use only syntax, imports, and macros available to that scene's Typst compilation context. Do not introduce document-specific helpers merely because they appear in another Typst project.
- Apply `$my-typst-style`'s Partial Differential Equations profile only when the target is actually that project and its identifying style guide or imports are present.

## Build explanations around intuition

Make the conceptual story the spine of educational scenes and any companion paper, notes, or prose. Establish the motivating question, a concrete mental model, and the key change in viewpoint before introducing formal notation.

- Treat equations as landmarks that name or summarize an idea, not as the default sequence of the explanation.
- Do not default to line-by-line expansion, substitution, rearrangement, or simplification. Include a symbolic step when it reveals why something works, changes the interpretation, or is necessary for the requested rigor.
- Prefer visual evidence such as geometry, motion, transformation, comparison, examples, counterexamples, units, and invariants before symbolic manipulation.
- Use narration to explain meaning, causality, and stakes. Keep on-screen mathematics selective enough that the viewer can absorb it while the animation moves.
- Apply the same principle to paper-oriented exposition: preserve rigor, but keep routine algebra concise or place it in a proof or appendix when it is not the central insight. Each displayed equation should answer a question raised by the surrounding story.
- If the user explicitly asks for a derivation or proof, provide it, but organize it around purpose and insight rather than presenting an uninterrupted wall of equations.

Before authoring, identify the single conceptual takeaway and choose a story arc that leads to it. Let equations support that arc rather than determine it.

## Author scenes

Use the installed Manim 0.21 Typst classes:

```python
from manim import MathTypst, Typst
```

- Use `Typst` for ordinary Typst markup.
- Use `MathTypst` for math-mode content without surrounding `$` delimiters.
- For selectable mathematical subexpressions, prefer labeled `{{ ... }}` groups and `.select()`.
- Do not translate LaTeX examples mechanically: LaTeX commands, packages, `TexTemplate`, TeX-string matching helpers, and `TransformMatchingTex` are not drop-in Typst APIs.

For Gemini narration, use the installed APIs:

```python
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gemini import GeminiService
```

Keep spoken prose separate from visual mathematical notation and synchronize animation with the tracker:

```python
visual_math = MathTypst(r"integral_0^1 f(x) dif x")
narration = "We now measure the accumulated contribution over the interval."

with self.voiceover(text=narration) as tracker:
    self.play(FadeIn(visual_math), run_time=tracker.duration)
```

Use a documented Gemini voice appropriate to the user's intent. The existing educational smoke test uses `GeminiService(voice="Iapetus")` for a clear voice. Verify constructor and voice support from the installed package before changing models or authentication behavior.

## Render from the caller repository

Development preview:

```sh
manim-video -pql scenes/example.py ExampleScene
```

Production 1080p:

```sh
manim-video -qh scenes/example.py ExampleScene
```

Forward user-provided Manim flags and scene arguments without rewriting them. Generated output normally lands under the caller's configured `media/` directory.

For a syntax or import check that needs the central Python environment but not Manim's CLI, preserve the caller directory and use:

```sh
uv run --project ~/Developer/manim-toolchain --frozen --no-env-file -- python -m py_compile scenes/example.py
```

## Handle Gemini credentials safely

The wrapper loads credentials only from `~/Developer/manim-toolchain/.env` through uv's dotenv parser. Never read, print, log, echo, or copy a credential value. Never put credentials in scene source, a command line, shell history, a video repository, `pyproject.toml`, or committed files.

If credentials are absent, finish all non-Gemini checks and ask the user to configure them privately:

```sh
cd ~/Developer/manim-toolchain
cp .env.example .env
chmod 600 .env
${EDITOR:-vi} .env
```

The default API-key variable is `GEMINI_API_KEY`. ADC is also supported when the central `.env` selects `GEMINI_AUTH_MODE=adc` and supplies the project/location settings. Interactive ADC login belongs to the user. Do not substitute another TTS backend merely to make a test pass.

## Verify real outcomes

Do not claim success from imports alone. For scene work, render the requested scene and inspect failures. When audio or encoding matters, inspect the produced file with `ffprobe`.

For toolchain-wide verification, use the maintained scripts:

```sh
cd ~/Developer/manim-toolchain
./scripts/render_smoke_tests.sh --typst-only
./scripts/verify_external_wrapper.sh
```

After credentials are configured:

```sh
./scripts/render_smoke_tests.sh --voiceover-only
```

The Typst smoke-test log must show Typst compilation and no LaTeX pipeline marker. The external-wrapper test must confirm that the central interpreter/packages were used while the caller's independent `.venv` remained unchanged.

## Maintain the toolchain only when requested

Dependency updates, wrapper changes, shared-config changes, and credential-mode changes belong in `~/Developer/manim-toolchain`, not a video repository. Preserve its Git history and unrelated changes. Keep `pyproject.toml` and `uv.lock` together, use `uv sync --frozen` for the committed environment, and rerun the environment, Typst, and external-wrapper checks after infrastructure changes.

The skill package itself is tracked at `~/Developer/manim-toolchain/skills/manim-toolchain`. Its installed path, `~/.codex/skills/manim-toolchain`, is a symlink to that repository-owned directory. Make skill changes in the tracked package and commit them with the toolchain repository.
