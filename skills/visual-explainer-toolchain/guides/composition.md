# Video composition

Render each engine's segment independently, then compose reproducibly:

```text
Manim clips + PyGfx clips + Taichi/PyGfx clips + Blender PNG sequences/clips
  + narration + music/effects -> FFmpeg -> final video
```

Before rendering, settle shared frame rate, resolution, pixel aspect ratio,
background, alpha behavior, audio sample rate, codec, and segment names. Use
explicit directories such as `media/manim/`, `media/renders/`,
`media/simulations/`, and `media/blender/` while respecting an existing project
layout.

Blender's view transform/color management can differ from Manim and PyGfx. Keep
its render JSON report with the sequence, decide where any transform happens,
and compare a transition frame before final encoding. Do not assume brightness
or contrast will match by default. Flatten or preserve alpha deliberately rather
than relying on a player default.

For compatible clips, a simple concat plus local audio attachment is usually
enough:

```sh
# On macOS (Apple Silicon), prefer hardware acceleration via VideoToolbox:
ffmpeg -f concat -safe 0 -i segments.txt \
  -c:v h264_videotoolbox -b:v 12M -pix_fmt yuv420p -an media/combined.mp4

# Cross-platform CPU fallback:
# ffmpeg -f concat -safe 0 -i segments.txt -c:v libx264 -crf 18 -pix_fmt yuv420p -an media/combined.mp4

ffmpeg -i media/combined.mp4 -i media/narration.wav \
  -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -shortest media/final.mp4
ffprobe -v error -show_streams -show_format media/final.mp4
```

### VideoToolbox Hardware Encoding on macOS

On Apple Silicon machines, use FFmpeg's hardware encoder `h264_videotoolbox` (or `hevc_videotoolbox`) to offload video compression to the dedicated Media Engine, dropping CPU load to ~5-10%:

- **1080p 30/60fps**: `-c:v h264_videotoolbox -b:v 10M -pix_fmt yuv420p`
- **4K / High fidelity**: `-c:v h264_videotoolbox -b:v 25M -pix_fmt yuv420p` or `-c:v hevc_videotoolbox -b:v 18M -tag:v hvc1 -pix_fmt yuv420p`
- **PNG sequence to MP4**:
  ```sh
  ffmpeg -framerate 30 -start_number 1 -i output/frame_%04d.png \
    -c:v h264_videotoolbox -b:v 12M -pix_fmt yuv420p -movflags +faststart output.mp4
  ```

For mismatched segments, use a documented FFmpeg filter graph that explicitly
scales, sets FPS, controls color conversion, and handles alpha. Generate
narration independently for non-Manim scenes when that is clearer than forcing
Manim Voiceover to own their timeline. Keep the spoken transcript separate from
on-screen source, notation, or implementation syntax.
