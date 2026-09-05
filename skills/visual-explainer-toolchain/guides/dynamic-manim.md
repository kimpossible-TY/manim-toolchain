# Dynamic Manim: Kinetic Motion Graphics & Fast-Paced Explainer Design

Use Manim as a programmatic motion graphics and kinetic typography engine for modern, fast-paced explainers, YouTube educational videos, and high-impact short-form content (Shorts, Reels, TikTok).

This is an optional technique library for a requested kinetic style. Select
techniques per scene; durations, easing curves, zoom factors, and sound cues below
are examples, not quality gates. Long holds, linear motion, static captions, and
silence remain valid when they serve the brief.

Do not treat Manim as merely a math formula or coordinate graph plotter. It is a full procedural 2D/2.5D animation suite capable of spring-damper physics, elastic arrivals, optical camera moves, and millisecond-accurate audio/SFX synchronization.

---

## 1. Pacing & Micro-Beat Options

In modern dynamic explainers and short-form content:
- **Example rhythm**: Holds around 3.0–3.5 seconds can suit a fast sequence; use longer or shorter holds for reading, observation, or dramatic effect.
- **Optional beat subdivision**: A sentence can use selected parts of this pattern:
  1. *Impactor / Entrance*: Sudden kinetic arrival of the anchor element (0.2s–0.4s).
  2. *Secondary Reveal / Accent*: Branching arrows, data counter, or word highlight (0.4s–0.8s).
  3. *Camera / Focus Shift*: Snap punch-in or camera pan to the critical detail (0.2s–0.3s).
  4. *Dynamic Transition*: Whip-pan, morph, or spring scale-down to the next beat (0.2s–0.4s).

---

## 2. Kinetic Elasticity & Rate Functions

Choose easing for the intended gesture. Elastic recoil can give cards and badges
a playful or punchy arrival; linear or non-overshooting easing can suit precision,
restraint, or continuous movement. Do not add bounce to every graphic by default.

### Key Rate Functions
- `rate_func=rate_functions.ease_out_back`: An overshooting arrival for a punchy gesture; tune its visible amplitude to the object and composition.
- `rate_func=rate_functions.ease_out_elastic`: Spring bounce for playful, attention-grabbing badges or icons.
- `rate_func=rate_functions.rush_into`: High-velocity acceleration into a collision or sudden stop.
- `rate_func=rate_functions.there_and_back`: Quick pulse or heartbeat emphasis.

```python
from manim import *

# Punchy Badge Arrival with 10% overshoot
badge = RoundedRectangle(corner_radius=0.2, width=3.2, height=1.0, fill_color="#286B9C", fill_opacity=1)
label = Text("9가 백신", font="Apple SD Gothic Neo", font_size=32, weight=BOLD)
card = VGroup(badge, label)

# Animate with ease_out_back (0.35s is the sweet spot for fast-paced video)
self.play(
    GrowFromCenter(card, rate_func=rate_functions.ease_out_back),
    run_time=0.35
)
```

---

## 3. Kinetic Typography & Word-by-Word Emphasis

Use word entrances or emphasis synchronized with narration when they improve
hierarchy. Static text and conventional caption bars are useful for sustained
reading and accessibility; choose their timing from the content.

### Patterns
- **Word Pop-in**: Animate words individually or in short clusters (2–3 words) matching the spoken rhythm.
- **Text Morphing (`TransformMatchingShapes`)**: Seamlessly morph one statement or formula into another without cutting.
- **Attention Flares**: Use `Flash`, `Indicate`, or `Circumscribe` at the exact phoneme of vocal emphasis.

```python
# Word highlight burst
keyword = Text("9가지 유형", color="#D4883B", font_size=48, weight=BOLD)
self.play(
    FadeIn(keyword, shift=UP * 0.3, rate_func=rate_functions.ease_out_back),
    run_time=0.25
)
# Frame-accurate accent flash
self.play(
    Flash(keyword, color="#D4883B", flash_radius=1.2, num_lines=8),
    run_time=0.2
)
```

---

## 4. Rapid Data Counters & Visual Velocity

Data acceleration provides immediate visual reward. Use `ValueTracker` to spin numbers up in fractions of a second:

```python
tracker = ValueTracker(0)
num_display = Integer(0, font_size=96, color=WHITE).add_updater(
    lambda m: m.set_value(int(tracker.get_value()))
)
self.add(num_display)

# Fast 0.4s count-up from 0 to 9 with sharp decel
self.play(
    tracker.animate(rate_func=rate_functions.ease_out_cubic).set_value(9),
    run_time=0.4
)
```

---

## 5. Dynamic Camera Moves: Snap Zooms & Whip Pans

Use `MovingCameraScene` when a zoom or pan contributes to the selected treatment:

```python
class DynamicExplainerBeat(MovingCameraScene):
    def construct(self):
        # Initial composition
        target_obj = Circle(radius=1.0, color=BLUE)
        self.add(target_obj)
        
        # Snap Punch-in (1.4x scale shift in 0.2s)
        self.play(
            self.camera.frame.animate(rate_func=rate_functions.ease_out_expo)
                .scale(0.7)
                .move_to(target_obj),
            run_time=0.22
        )
        
        # Whip Pan transition to the right (clears the scene instantly)
        self.play(
            self.camera.frame.animate(rate_func=rate_functions.rush_into)
                .shift(RIGHT * 15),
            run_time=0.25
        )
```

---

## 6. Transparent Overlay Workflow (Manim + 3D Plates)

When combining 3D realism (Blender/PyGfx) with Manim kinetic typography:
1. **Render Manim with transparent background**:
   ```sh
   manim-video -t --format=mov --codec=prores_ks -q h scenes/overlay.py OverlayScene
   # Or PNG sequence with alpha:
   manim-video -t --format=png scenes/overlay.py OverlayScene
   ```
2. **Composite over 3D plates via FFmpeg**:
   ```sh
   ffmpeg -i blender_plate.mp4 -i manim_overlay.mov \
     -filter_complex "[0:v][1:v]overlay=0:0:shortest=1[outv]" \
     -map "[outv]" -c:v h264_videotoolbox -b:v 14M final_comp.mp4
   ```

---

## 7. Frame-Accurate SFX Mapping Table

Choose sound cues at meaningful accents; omit them where narration, ambience, or
silence carries the moment. For selected impact sounds, align perceptually with
the action and check at playback speed. The examples below are optional:

| Visual Event | Example Duration | Easing Curve | Optional SFX Pairing |
|---|---|---|---|
| Card / Badge Arrival | 0.25s–0.35s | `ease_out_back` | Crisp Pop / Tactile Mechanical Click |
| Snap Zoom / Punch-in | 0.18s–0.25s | `ease_out_expo` | Air displacement Whoosh / Camera Zoom Servo |
| Whip Pan Transition | 0.20s–0.30s | `rush_into` → `ease_out` | Fast Swish / Heavy Low-End Whoosh |
| Counter Acceleration | 0.35s–0.50s | `ease_out_cubic` | Fast Mechanical Ticks / Rising Synth Chime |
| Critical Stat Reveal | 0.20s–0.30s | `Flash` + `Indicate` | Sub-Bass Impact (Drop) + Metallic Ding |
