# Blender previews, Cycles, and portable scenes

Read this only when a request genuinely needs Blender-level materials, lighting,
assets, transparency, cinematic camera work, rigging, volumetrics, or geometry
work. Start with local EEVEE: validate composition, materials, camera, and
timing at configurable low resolution/samples without saving over the production
scene. `VISUAL_BLENDER_PREVIEW_WIDTH`, `VISUAL_BLENDER_PREVIEW_HEIGHT`,
`VISUAL_BLENDER_PREVIEW_SAMPLES`, and `VISUAL_BLENDER_PREVIEW_SCALE` set local
defaults; command-line flags override them per render.

Use `visual-blender` for unmodified Blender CLI access. The preview/render
helpers run Blender background mode with `scripts/blender_render.py`; they do
not use uv Python and leave the source `.blend` untouched unless `--save-blend`
is explicit.

```sh
visual-blender-preview --scene scene.blend --scene-script scenes/hero.py \
  --output media/previews/hero.png --report media/previews/hero.json

visual-blender-render --scene scene.blend --scene-script scenes/hero.py \
  --output media/blender/frame_ --frame-start 1 --frame-end 240 \
  --width 1920 --height 1080 --fps 30 --samples 128 --device auto
```

The `--device` values include `auto`, `cpu`, `gpu`, and specific Cycles backends
such as `metal` or `cuda`; `--require-gpu` turns an unavailable compatible GPU
into a clear failure instead of a fallback. The helper records the configured
Cycles state, but report GPU success only after the actual Cycles render and its
image have been verified. Blender version-specific device logic stays in
`scripts/blender_cycles.py`.

For animation, render image sequences rather than an MP4. Use ranges or chunks
such as `1–120`, `121–240`, then check completed PNGs locally:

```sh
visual-python ~/Developer/manim-toolchain/scripts/verify_frame_sequence.py \
  --directory media/blender --prefix frame_ --frame-start 1 --frame-end 240 \
  --width 1920 --height 1080
```

The verifier rejects missing, zero-byte, corrupt, and inconsistent-dimension
PNG frames. Keep Blender color settings from the JSON render report alongside
the manifest so composition can reconcile color transforms deliberately.

Before remote packaging, validate external assets. A remote bundle accepts only
packed data or Blender-relative `//` paths; missing assets and unresolved
absolute local paths fail validation. Pack genuinely small assets where that is
reasonable; put large licensed assets in the explicit `assets/` directory.
Never add third-party assets to the repository without verifying their license.

Make a local EEVEE preview first. For any expensive final render, measure at
least one representative expensive Cycles frame before deciding whether local
Cycles or Colab offers a real benefit. The small benchmark helper records wall
time and peak child RSS where the operating system exposes it, and can estimate
the cost of a frame range:

```sh
visual-python ~/Developer/manim-toolchain/scripts/benchmark_blender_render.py \
  --frame-count 240 --report media/benchmarks/cycles.json -- \
  visual-blender-render --scene scene.blend --output media/benchmarks/frame.png \
  --width 1920 --height 1080 --samples 128 --frame 120 --device cpu
```
