# Optional Colab compute and Cycles rendering

Read this when a measured local Taichi or Cycles workload may justify remote
execution. Colab is an optional backend, not the normal destination for Manim,
ordinary PyGfx, EEVEE previews, short renders, or final FFmpeg composition.

The installed Colab CLI is a separate system-level uv tool, not a dependency of
the central visualization project. Consult the current official
[`google-colab-cli` installation guidance](https://github.com/googlecolab/google-colab-cli)
before changing it. Do not reinstall a working CLI just to refresh it.

Do not start a remote session, authenticate, upload, or use paid/limited GPU
quota without clear authorization in the current request. Interactive OAuth or
ADC setup is a user action. Never upload credentials, `.env` files, browser
profiles, unrelated repository files, confidential media, or private datasets.

Prepare a local bundle after validating a portable source scene:

```sh
visual-colab-prepare \
  --scene scene.blend --scene-script scenes/hero.py --asset-dir assets \
  --output render-job --width 1920 --height 1080 --fps 30 \
  --frame-start 1 --frame-end 240 --samples 128 --device auto
```

The resulting `render-job/` contains only `scene.blend`, optional `scene.py`,
explicit assets, the compact Blender helpers, `render_manifest.json`,
`bootstrap.sh`, an empty `output/`, and an authorization-marked
`colab_commands.sh`. The manifest records Blender version, Cycles settings,
resolution, frame range, sample/denoise policy, requested device, assets, and
color management. Bundle creation runs no remote command.

Once authorized, review and run `colab_commands.sh` manually. It creates a
named session, uploads only a tarball of the bundle, runs `bootstrap.sh`,
downloads a tarball of the PNG sequence/report, and stops the session. The
remote bootstrap must report its Blender version and actual completed render;
do not infer GPU use from a requested accelerator. Download PNG/OpenEXR frames,
verify them locally, then encode or compose with local FFmpeg.

For Taichi, benchmark a reduced local simulation first. If Colab CUDA is chosen,
keep algorithm, time step, precision, and seed explicit; usually download state
data and render it locally with PyGfx. Do not assume Colab headless PyGfx is
reliable until a real remote frame has been verified.
