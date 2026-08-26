from manim import FadeIn, MathTypst, UP
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gemini import GeminiService


class GeminiVoiceoverSmokeTest(VoiceoverScene):
    """Synchronize one Typst animation with Gemini-generated narration."""

    def construct(self):
        # Iapetus is the Gemini voice documented as "Clear". Authentication
        # defaults to an API key, while GEMINI_AUTH_MODE=adc selects ADC.
        self.set_speech_service(GeminiService(voice="Iapetus"))

        visual_math = MathTypst(
            r"integral_0^1 f(x) dif x",
            font_size=72,
        )
        narration = (
            "A smooth function becomes easier to understand when each "
            "transformation unfolds gently."
        )

        with self.voiceover(text=narration) as tracker:
            self.play(
                FadeIn(visual_math, shift=0.25 * UP),
                run_time=tracker.duration,
            )
