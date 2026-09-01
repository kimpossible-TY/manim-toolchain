# Mathematics educational-video direction

Read this reference only when the main learning outcome is a mathematical idea,
proof, model, or quantitative relationship. It can also serve a science video
whose point is to teach that mathematical model. Do not use its equation-first
structure, notation rules, or pedagogical pacing as a default for history,
product, narrative, cultural, or other non-mathematical videos.

## Define the learning transformation

Before selecting scenes, write one sentence describing what the viewer should
be able to see or predict by the end. Build every beat around that
transformation rather than around available effects or engines. Prefer one
central relationship per short sequence; introduce a second only when the
first is visually grounded.

The usual order is visual meaning before compact notation:

```text
question or surprising observation
  -> concrete/geometric intuition
  -> quantity and notation
  -> controlled change, numerical manifestation, or simulation
  -> interpretation and transferable takeaway
```

This is a flexible teaching pattern, not a compulsory shot list. Omit or
reorder a beat when the mathematical problem calls for it, but do not open with
unmotivated symbols or turn every statement into a diagram. Keep a stable
visual anchor while a quantity changes, and use motion to reveal a dependency
that prose alone would hide.

## Route mathematical beats

| Mathematical need | Route |
| --- | --- |
| Equations, diagrams, labels, transformations, graphs, or explanatory 2D | Manim |
| A mesh, surface, point cloud, spatial field, or camera perspective that genuinely adds 3D insight | PyGfx |
| Analytically prescribed motion with modest state | NumPy + PyGfx |
| Many evolving particles, grids, fields, PDEs, or compute-heavy deformation | Taichi + PyGfx |
| Material, anatomy, lighting, volumetrics, rigging, or a cinematic hero shot with clear explanatory value | Blender (Runpod Serverless) |
| Explanation, simulation, and high-fidelity shot in one lesson | Independently rendered segments + FFmpeg |

Do not use Blender merely because an object is three-dimensional, or Taichi
merely because it moves. A short Blender shot can provide a perceptual anchor;
Manim should return to make the mathematical claim legible. Benchmark a
Taichi/PyGfx simulation locally before escalating it to remote compute.

A common mixed lesson is:

```text
Manim question/equation -> Manim geometric intuition
  -> PyGfx or Taichi/PyGfx numerical manifestation
  -> optional Blender hero shot -> Manim interpretation
```

Use the shared [composition guide](composition.md) to choose common frame rate,
resolution, color handling, audio delivery, and transition checks before those
segments are rendered.

## Notation and narration

Use visual Typst independently from spoken prose:

```python
visual = MathTypst(r"u_(t t) = c^2 Delta u")
narration = "Each point accelerates according to its local curvature."
```

Prefer `from manim import Typst, MathTypst`; do not add a LaTeX distribution.
Never send raw Typst, LaTeX-like source, code, or implementation notation to
Gemini TTS. Read symbols aloud for their meaning, not their source syntax.

Let Manim Voiceover own timing only for a Manim segment. For PyGfx, Taichi, or
Blender footage, create narration independently when that produces a clearer
timeline; do not force another engine into Manim Voiceover. Preserve the
spoken transcript separately from the visual notation.
