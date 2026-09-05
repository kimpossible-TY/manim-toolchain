# Blender previews, Runpod Cycles, and portable scenes

Read this when a request genuinely needs Blender-level materials, lighting,
assets, transparency, cinematic camera work, rigging, volumetrics, or geometry
work.

## macOS hardware access

Local `visual-blender`, `visual-blender-preview`, and
`visual-blender-render` commands need hardware access on macOS. An unrestricted
runner can execute them directly without an approval request.
Blender 5.x initializes its Metal backend before Python, including in
background mode. If a restricted runner hides the hardware or Metal device
identity, Blender 5.2 can crash in device detection before the requested scene
script is evaluated.

If a restricted runner blocks access, any supported host-execution permission
must apply to the top-level wrapper invocation. A shell
wrapper cannot escape its parent sandbox, and neither `--background` nor
`--factory-startup` bypasses Metal initialization. The macOS Blender 5.2 build
does not provide OpenGL as an alternate backend, so `--gpu-backend opengl` is
not a workaround. `visual-blender` checks for restricted hardware access first
and exits with status 77 and a concise instruction when host execution is
required.

## Default workflow: Local iteration -> Runpod Pod Cycles -> Local FFmpeg

Follow the [main skill's mode selection](../SKILL.md#select-and-retain-the-blender-render-mode).
Keep the user's established mode and cost authorization across iterations.
Short local Cycles material tests and bounded local production are available
when they suit the brief and hardware budget; EEVEE is not restricted to drafts
if its output meets the requested final look.

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

3. **Runpod Pod execution (default for substantial Blender production renders)**:
   Package the portable bundle and submit its complete frame range to one
   disposable GPU Pod:

   ```sh
   visual-runpod-prepare \
     --scene scene.blend --scene-script scenes/hero.py --asset-dir assets \
     --output render-job --width 1920 --height 1080 --fps 30 \
     --frame-start 1 --frame-end 240 --samples 128 --device auto

   # Set RUNPOD_* and R2_* variables first; --r2 creates all signed URLs.
   visual-runpod submit --bundle render-job --r2
   visual-runpod wait --jobs-file render-job.runpod.json --download
   ```

   Manual signed URL options remain available for another S3-compatible
   provider; see the [Runpod guide](runpod.md).

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
small helper scripts, so a fresh Pod does not install Blender at boot. Keep the
invariant `one Pod = one GPU = one Blender process`; the Pod owns the full
frame range and is deleted after terminal status unless retained for debugging.

## Local multi-worker & diagnostic rendering

For local rendering with parallel worker chunking or CPU fallback diagnostics,
`visual-blender-render` supports `--workers N`:

```sh
visual-blender-render --scene scene.blend --scene-script scenes/hero.py \
  --output /private/tmp/visual-blender-diagnostic/frame_ --frame-start 1 --frame-end 240 \
  --width 1920 --height 1080 --workers 6 --engine eevee
```
