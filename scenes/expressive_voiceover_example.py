"""A compact moving-probe scene showing narration designed with the visuals."""

from manim import Axes, Create, Dot, FadeIn, MathTypst, RIGHT, UP

from manim_toolchain import NarrationProfile
from manim_toolchain.voiceover import ExpressiveGeminiService, ExpressiveVoiceoverScene


class MovingProbeNarrationExample(ExpressiveVoiceoverScene):
    """Use questions, contrast, reveal, silence, and separate spoken math."""

    def construct(self):
        self.set_narration_profile(
            NarrationProfile(
                persona="A thoughtful mathematical educator speaking directly to one curious student",
                tone="Warm, precise, and intellectually curious",
                default_pace="moderate",
                expressiveness="moderate",
            )
        )
        self.set_speech_service(ExpressiveGeminiService(voice="Iapetus", profile=self.narration_profile))

        axes = Axes(x_range=[-3, 3], y_range=[-1, 2], x_length=8, y_length=4)
        curve = axes.plot(lambda x: 0.55 * x * x / 3 + 0.25, color="#6EC5FF")
        probe = Dot(axes.c2p(-2.2, 0.25), color="#F5D76E")
        function_label = MathTypst(r"f(x)")
        function_label.next_to(axes.c2p(2.1, 1.1), UP)

        with self.narrated("Normally, we ask for the value of a function at each point.") as tracker:
            self.play(Create(axes), Create(curve), FadeIn(function_label), run_time=tracker.duration)

        with self.say("But a moving probe asks a completely different question.", emphasis="completely different question") as tracker:
            self.play(FadeIn(probe), run_time=tracker.duration)

        self.narration_pause("medium")
        with self.voiceover(
            text="How does the function respond as the probe slides across it?",
            intent="question",
            emotion="curious",
            pace="slow",
            pause_after="long",
        ) as tracker:
            self.play(probe.animate.shift(4.4 * RIGHT), run_time=tracker.duration)

        pairing = MathTypst(r"integral f(x) phi(x-a) dif x")
        pairing.to_edge(UP)
        with self.voiceover(
            text="And this is exactly what the pairing measures.",
            intent="reveal",
            emotion="discovery",
            pace="slow",
            subtitle="∫ f(x) φ(x − a) dx",
            emphasis="exactly",
            pause_after=0.7,
        ) as tracker:
            self.play(FadeIn(pairing), run_time=tracker.duration)

        # Spoken and displayed mathematics can intentionally differ.
        with self.voiceover(
            text="f belongs to L two of R n.",
            subtitle="f ∈ L²(Rⁿ)",
            intent="define",
            pace="slow",
        ):
            pass
