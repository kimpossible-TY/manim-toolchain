# PyGfx and Taichi

Read this when a segment needs genuine scientific 3D or numerical evolution.

Use ordinary upstream PyGfx APIs. Production rendering should use
`rendercanvas.offscreen.RenderCanvas`, deterministic frame indices or simulated
time, explicit dimensions/FPS/frame count, and FFmpeg H.264 `yuv420p` output.
An interactive window is useful for development but must not be required for a
production render. Verify the RGBA frame shape, non-uniform pixels, output
existence, and observed wgpu backend after a real draw.

```text
Python scene -> PyGfx/wgpu -> offscreen RGBA frames -> FFmpeg -> segment.mp4
```

Use NumPy directly when state is small and analytically prescribed. Do not add
Taichi only for rotation or simple animation.

Use Taichi for particles, grids, fields, many-body systems, PDEs, or expensive
deformation. Keep the simulation and scene authoring separate:

```text
Taichi kernels -> arrays/fields -> .to_numpy() -> PyGfx geometry -> frames
```

Initialize portably: verify Metal on Apple Silicon when requested, provide an
explicit CPU option, and use CUDA only after a Runpod GPU worker is selected
and tested.
Do not silently change precision or algorithms between backends. Record random
seed, time step, steps per presented frame, simulation dimensions, chosen
backend, and floating-point precision in scene configuration or output metadata.

Taichi 1.7.4 on the central Python 3.13 stack rejects postponed annotations in
kernel files. Do not add `from __future__ import annotations` to files that
define kernels; let annotations such as `ti.f32` evaluate normally.

For a potentially remote simulation, run a reduced local simulation first,
measure representative step/render time and memory, estimate production cost,
then include Runpod image cold-start, dependency setup, transfer, and download
time in the decision. Prefer returning `simulation.npz` to the Mac and
rendering it with local PyGfx unless remote headless PyGfx has been explicitly
verified. The Blender Runpod worker in this repository is not a generic PyGfx
worker; create a separate image when remote simulation is truly justified.
