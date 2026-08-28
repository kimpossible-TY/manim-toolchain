from manim import FadeIn, MathTypst, UP
from manim_toolchain.voiceover import ExpressiveGeminiService, ExpressiveVoiceoverScene


class GeminiVoiceoverSmokeTest(ExpressiveVoiceoverScene):
    """Synchronize Typst animation with a cache-safe expressive Gemini request."""

    def construct(self):
        # Iapetus is the Gemini voice documented as "Clear". Authentication
        # defaults to an API key, while GEMINI_AUTH_MODE=adc selects ADC.
        self.set_speech_service(ExpressiveGeminiService(voice="Iapetus"))

        visual_math = MathTypst(
            r"integral_0^1 f(x) dif x",
            font_size=72,
        )
        narration = (
            "A smooth function becomes easier to understand when each "
            "transformation unfolds gently."
        )

        # No delivery metadata is required: the adapter resolves a sensible
        # explanatory default and still provides the ordinary tracker API.
        with self.voiceover(text=narration) as tracker:
            self.play(
                FadeIn(visual_math, shift=0.25 * UP),
                run_time=tracker.duration,
            )
