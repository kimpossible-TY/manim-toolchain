# Mixed-scene composition

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
ffmpeg -f concat -safe 0 -i segments.txt -c:v libx264 -pix_fmt yuv420p -an media/combined.mp4
ffmpeg -i media/combined.mp4 -i media/narration.wav \
  -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -shortest media/final.mp4
ffprobe -v error -show_streams -show_format media/final.mp4
```

For mismatched segments, use a documented FFmpeg filter graph that explicitly
scales, sets FPS, controls color conversion, and handles alpha. Generate
narration independently for non-Manim scenes when that is clearer than forcing
Manim Voiceover to own their timeline. Keep the spoken transcript separate from
on-screen Typst or implementation syntax.
