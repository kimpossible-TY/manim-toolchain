# Blender previews, Runpod Cycles, and portable scenes

Read this when a request genuinely needs Blender-level materials, lighting,
assets, transparency, cinematic camera work, rigging, volumetrics, or geometry
work.

## Workflow: Local EEVEE preview -> Runpod Cycles chunks -> Local FFmpeg

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

3. **Runpod Serverless execution (default for all Blender production renders)**:
   Package the portable bundle, submit one Runpod job per frame chunk, and let
   the endpoint scale workers horizontally:

   ```sh
   visual-runpod-prepare \
     --scene scene.blend --scene-script scenes/hero.py --asset-dir assets \
     --output render-job --width 1920 --height 1080 --fps 30 \
     --frame-start 1 --frame-end 240 --chunk-size 60 --samples 128 --device auto

   # Set RUNPOD_* and R2_* variables first; --r2 creates all signed URLs.
   visual-runpod submit --bundle render-job --r2
   visual-runpod wait --jobs-file render-job.runpod.json --download
   ```

   Manual signed URL options remain available for another S3-compatible
   provider; see [`references/runpod.md`](runpod.md).

4. **Local frame verification & FFmpeg composition**:
   The downloaded image sequence and render report are verified locally:

   ```sh
   visual-python ~/Developer/visual-explainer-toolchain/scripts/verify_frame_sequence.py \
     --directory render-job/output --prefix frame_ --frame-start 1 --frame-end 240 \
     --width 1920 --height 1080
   ```

   The client and worker reject missing, zero-byte, corrupt, and
   inconsistent-dimension PNG frames. Combine the verified PNG sequence with
   other story beats using local FFmpeg.

The worker image is built from `runpod/Dockerfile`. It contains Blender and the
small helper scripts, so a serverless invocation does not install Blender at
request time. Keep the invariant `one worker request = one GPU = one Blender
process`; chunk parallelism belongs to the endpoint queue.

## Local multi-worker & diagnostic rendering

For local rendering with parallel worker chunking or CPU fallback diagnostics,
`visual-blender-render` supports `--workers N`:

```sh
visual-blender-render --scene scene.blend --scene-script scenes/hero.py \
  --output media/blender/frame_ --frame-start 1 --frame-end 240 \
  --width 1920 --height 1080 --workers 6 --engine eevee
```
