# Blender previews, Cycles, and portable scenes

Read this when a request genuinely needs Blender-level materials, lighting,
assets, transparency, cinematic camera work, rigging, volumetrics, or geometry
work.

## Workflow: Local EEVEE preview -> Colab CLI Cycles render -> Local FFmpeg

1. **Local EEVEE preview**:
   Validate composition, materials, camera, and timing locally at configurable
   low resolution/samples without modifying the production `.blend`:

   ```sh
   visual-blender-preview --scene scene.blend --scene-script scenes/hero.py \
     --output media/previews/hero.png --report media/previews/hero.json
   ```

   `VISUAL_BLENDER_PREVIEW_WIDTH`, `VISUAL_BLENDER_PREVIEW_HEIGHT`,
   `VISUAL_BLENDER_PREVIEW_SAMPLES`, and `VISUAL_BLENDER_PREVIEW_SCALE` configure
   local preview defaults.

2. **Asset validation & packaging**:
   Before packaging, ensure external assets use packed data or Blender-relative
   `//` paths. Missing assets and unresolved absolute local paths will fail
   bundle validation. Pack small assets directly; put large licensed assets in
   the explicit `assets/` directory.

3. **Colab CLI execution (default for all Blender production renders)**:
   Package the portable bundle and execute remote rendering on the reusable
   `visual-render` GPU worker session:

   ```sh
   visual-colab-prepare \
     --scene scene.blend --scene-script scenes/hero.py --asset-dir assets \
     --output render-job --width 1920 --height 1080 --fps 30 \
     --frame-start 1 --frame-end 240 --samples 128 --device auto

   # Execute on Colab CLI (reuses existing visual-render worker instantly):
   ./render-job/colab_commands.sh
   ```

4. **Local frame verification & FFmpeg composition**:
   The downloaded image sequence and render report are verified locally:

   ```sh
   visual-python ~/Developer/manim-toolchain/scripts/verify_frame_sequence.py \
     --directory render-job/output --prefix frame_ --frame-start 1 --frame-end 240 \
     --width 1920 --height 1080
   ```

   The verifier rejects missing, zero-byte, corrupt, and inconsistent-dimension
   PNG frames. Combine the verified PNG sequence with other story beats using
   local FFmpeg.

## Local diagnostic renderers

For local CPU fallback diagnostics or transparent CLI access, `visual-blender`
and `visual-blender-render` remain available:

```sh
visual-blender-render --scene scene.blend --scene-script scenes/hero.py \
  --output media/blender/frame_ --frame-start 1 --frame-end 10 \
  --width 1280 --height 720 --samples 32 --device cpu
```
