from manim import BLUE, DOWN, FadeIn, MathTypst, Scene, Typst, UP, Write


class TypstSmokeTest(Scene):
    """Render text and mathematics through Manim's Typst integration only."""

    def construct(self):
        heading = Typst(
            r"*Typst* renders this ordinary text directly.",
            font_size=42,
        ).shift(UP)
        formula = MathTypst(
            r"T(phi) = integral_(-infinity)^infinity f(x) phi(x) dif x",
            font_size=54,
        ).next_to(heading, DOWN, buff=0.8)

        self.play(FadeIn(heading, shift=0.2 * UP))
        self.play(Write(formula))
        self.play(formula.animate.set_color(BLUE).scale(1.05), run_time=1.0)
        self.wait(0.5)
