# Central Manim Toolchain

This is the reusable, user-level Manim environment for all local video repositories on this Mac. It owns Python and animation dependencies; individual repositories contain only scene code, assets, generated media exclusions, and optional repository-specific `manim.cfg` files.

The locked top-level stack is:

- native Apple Silicon Python 3.13 in `.venv`
- Manim Community Edition 0.21.0 with the `typst` extra
- Manim Voiceover 0.4.0 with the `gemini` extra
- Google Gen AI Python SDK selected by that extra
- system Typst CLI, FFmpeg/FFprobe, and SoX from Homebrew

No MacTeX, BasicTeX, TinyTeX, or other TeX distribution is required.

## Architecture

The globally available command is a symlink:

```text
~/.local/bin/manim-video -> ~/Developer/manim-toolchain/bin/manim-video
```

The wrapper executes the equivalent of:

```sh
uv run --project /Users/taeyoung/Developer/manim-toolchain --frozen -- manim ...
```

It deliberately does not change directories. `uv --project` selects this toolchain's `pyproject.toml`, `uv.lock`, `.python-version`, and `.venv`, while relative scene paths and output paths remain relative to the caller. Arguments after `manim` are forwarded unchanged. Inherited uv project-selection variables and `VIRTUAL_ENV` are cleared only in the wrapper process, so a caller repository's environment is neither activated nor modified.

The shared Manim configuration is also a symlink owned here:

```text
~/.config/manim/manim.cfg -> ~/Developer/manim-toolchain/manim.cfg
```

Manim loads that user-wide file first, then lets a `manim.cfg` beside a scene override it. Command-line flags have the highest precedence.

## Codex skill

The repository owns the `manim-toolchain` skill at `skills/manim-toolchain`. Codex discovers that tracked copy through this symlink:

```text
~/.codex/skills/manim-toolchain -> ~/Developer/manim-toolchain/skills/manim-toolchain
```

For Typst authoring, use this skill together with [`my-typst-style`](https://github.com/kimpossible-TY/typst-packages/tree/main/skills/my-typst-style). That companion skill is maintained in the separate `typst-packages` repository and supplies the reusable mathematical-writing, diagram, annotation, and layout conventions used by this toolchain.

Edit and commit the repository copy when changing the skill. After cloning the repository on this Mac, recreate the link with:

```sh
mkdir -p ~/.codex/skills
ln -s /Users/taeyoung/Developer/manim-toolchain/skills/manim-toolchain ~/.codex/skills/manim-toolchain
```

## Use from any video repository

From the directory containing a scene:

```sh
manim-video scene.py SceneClass
manim-video -pql scenes/chapter_one.py ChapterOne
```

For production-quality 1080p output:

```sh
manim-video -qh scenes/chapter_one.py ChapterOne
```

The repository does not need Manim dependencies in its own `pyproject.toml`. It may have an unrelated Python project and `.venv`; the absolute `--project` selection keeps the toolchains separate.

## Gemini credentials

The wrapper only loads credentials from this toolchain's `.env`, using uv's `--env-file` parser. It never shell-sources the file, prints it, or searches caller repositories for credentials. It also refuses a central `.env` that is readable by group or other users.

For the default Gemini Developer API key mode, create a key in [Google AI Studio](https://aistudio.google.com/app/apikey), then edit the ignored central file:

```sh
cd /Users/taeyoung/Developer/manim-toolchain
cp .env.example .env
chmod 600 .env
${EDITOR:-vi} .env
```

Keep the variable name `GEMINI_API_KEY` and replace only the placeholder. Do not put the key in shell commands, scene source, video repositories, or `pyproject.toml`.

`GeminiService` also supports Google Cloud Application Default Credentials. After interactive authentication:

```sh
gcloud auth application-default login
```

Select it with non-secret values in the central `.env`:

```dotenv
GEMINI_AUTH_MODE=adc
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=global
```

## Toolchain checks and smoke tests

```sh
cd /Users/taeyoung/Developer/manim-toolchain
./scripts/check_environment.sh
./scripts/render_smoke_tests.sh --typst-only
./scripts/verify_external_wrapper.sh
```

After Gemini credentials are present:

```sh
./scripts/render_smoke_tests.sh --voiceover-only
```

The external-wrapper test creates a temporary independent project with its own Python 3.14 `.venv` and dependency-free `pyproject.toml`, runs exactly `manim-video scene.py TestScene`, checks that the central Python 3.13 interpreter and locked packages were used, and verifies that the external `.venv` was unchanged.

## Maintain the central environment

Install exactly the committed lockfile:

```sh
cd /Users/taeyoung/Developer/manim-toolchain
uv sync --frozen
```

Review upstream release notes before updating, then upgrade selected packages and rerun all credential-independent tests:

```sh
uv lock --upgrade-package manim --upgrade-package manim-voiceover --upgrade-package google-genai
uv sync --frozen
./scripts/check_environment.sh
./scripts/render_smoke_tests.sh --typst-only
./scripts/verify_external_wrapper.sh
```

Commit `pyproject.toml` and `uv.lock` together after verification. Never install project dependencies manually into `.venv`.

## Writing scenes with Typst and narration

Use `Typst` for ordinary Typst markup and `MathTypst` for visual mathematics. Keep spoken prose separate from Typst notation:

```python
visual_math = MathTypst(r"integral_0^1 f(x) dif x")
narration = "We now measure the accumulated contribution over the interval."

with self.voiceover(text=narration) as tracker:
    self.play(FadeIn(visual_math), run_time=tracker.duration)
```

`MathTypst` does not accept LaTeX commands, packages, or `TexTemplate` preambles. Manim 0.21.0 supports labeled Typst groups with `{{ ... }}` and `.select()`, but TeX-string helpers and `TransformMatchingTex` are not drop-in Typst APIs.

## Official references

- [uv `run --project` CLI reference](https://docs.astral.sh/uv/reference/cli/#uv-run)
- [uv environment-file configuration](https://docs.astral.sh/uv/configuration/files/#environment-variable-files)
- [Manim configuration precedence](https://docs.manim.community/en/stable/guides/configuration.html)
- [Manim Typst classes](https://docs.manim.community/en/stable/reference/manim.mobject.text.typst_mobject.html)
- [Manim Voiceover](https://github.com/ManimCommunity/manim-voiceover)
