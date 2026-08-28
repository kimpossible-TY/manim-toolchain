"""Offline regression tests for semantic delivery and expressive Gemini requests."""

from __future__ import annotations

import inspect
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from manim_toolchain.narration import (
    GeminiPromptBuilder,
    GeminiSpeechRenderer,
    NarrationProfile,
    NarrationSegment,
    math_speech,
    narration,
    resolve_delivery,
)
from manim_toolchain.voiceover import ExpressiveGeminiService, ExpressiveVoiceoverScene


class FakeGeminiModels:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def generate_content(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return SimpleNamespace(
            candidates=[
                SimpleNamespace(
                    content=SimpleNamespace(
                        parts=[SimpleNamespace(inline_data=SimpleNamespace(data=b"\x00\x00" * 240))]
                    )
                )
            ]
        )


class FakeGeminiClient:
    def __init__(self) -> None:
        self.models = FakeGeminiModels()


class NarrationModelTests(unittest.TestCase):
    def test_model_normalises_and_validates_values(self) -> None:
        segment = NarrationSegment(
            text="  This is   the key idea. ",
            subtitle="  This is the visible transcript. ",
            emotion="discovery",
            emphasis=["key idea", " key idea "],
            pause_after="brief",
        )
        self.assertEqual(segment.text, "This is the key idea.")
        self.assertEqual(segment.subtitle_text, "This is the visible transcript.")
        self.assertEqual(segment.emotion.value, "discovery")
        self.assertEqual(segment.emphasis, ("key idea",))
        self.assertEqual(segment.pause_after, 0.35)
        with self.assertRaises(ValueError):
            NarrationSegment(text="", pace="unhurried")
        with self.assertRaises(ValueError):
            NarrationSegment(text="valid", pause_before=-0.1)
        with self.assertRaises(ValueError):
            NarrationProfile(default_pace=None)  # type: ignore[arg-type]

    def test_inference_and_explicit_override_precedence(self) -> None:
        question = resolve_delivery(NarrationSegment("But why should we care about this?"))
        self.assertEqual(question.intent.value, "question")
        self.assertEqual(question.emotion.value, "curious")

        reveal = resolve_delivery(NarrationSegment("And this is exactly what a distribution does."))
        self.assertEqual(reveal.intent.value, "reveal")
        self.assertEqual(reveal.emotion.value, "discovery")
        self.assertEqual(reveal.pace.value, "slow")

        overridden = resolve_delivery(
            NarrationSegment(
                "But why should we care about this?",
                intent="summarize",
                emotion="reassuring",
                pace="fast",
                energy="high",
            )
        )
        self.assertEqual(overridden.intent.value, "summarize")
        self.assertEqual(overridden.emotion.value, "reassuring")
        self.assertEqual(overridden.pace.value, "fast")
        self.assertEqual(overridden.energy.value, "high")

    def test_convenience_constructor_resolves_delivery(self) -> None:
        segment = narration("But here is the key idea.")
        self.assertEqual(segment.intent.value, "reveal")
        self.assertEqual(segment.emotion.value, "discovery")


class PromptAndRendererTests(unittest.TestCase):
    def test_prompt_is_expressive_but_subtitle_stays_outside_it(self) -> None:
        request = GeminiSpeechRenderer().build_request(
            NarrationSegment(
                text="f belongs to L two of R n.",
                subtitle="f ∈ L²(Rⁿ)",
                intent="define",
                pace="slow",
                emphasis="L two",
                pause_after="medium",
            ),
            NarrationProfile(),
            scene_context="A moving probe introduces a distribution.",
        )
        self.assertEqual(request.subtitle, "f ∈ L²(Rⁿ)")
        self.assertIn("Audio Profile:", request.prompt)
        self.assertIn("Director's Notes:", request.prompt)
        self.assertIn("Transcript:\nf belongs to L two of R n.", request.prompt)
        self.assertNotIn("f ∈ L²(Rⁿ)", request.prompt)

    def test_opt_in_math_speech_avoids_general_markup_parsing(self) -> None:
        self.assertEqual(
            math_speech(r"f(x) \in L^2(\mathbb{R}^n)"),
            "f of x belongs to L two (R n)",
        )


class GeminiCacheTests(unittest.TestCase):
    def make_service(self, cache_dir: Path) -> tuple[ExpressiveGeminiService, FakeGeminiClient]:
        client = FakeGeminiClient()
        return (
            ExpressiveGeminiService(
                voice="Iapetus",
                model="fake-model",
                cache_dir=cache_dir,
                client=client,
            ),
            client,
        )

    def test_plain_voiceover_text_falls_back_to_inferred_request(self) -> None:
        with TemporaryDirectory() as directory:
            service, client = self.make_service(Path(directory))
            result = service._wrap_generate_from_text("But why should we care about this?")
            self.assertEqual(result["input_text"], "But why should we care about this?")
            prompt = client.models.calls[0]["contents"]
            self.assertIsInstance(prompt, str)
            self.assertIn("Intent: question; emotion: curious", prompt)

    def test_cache_changes_for_delivery_but_stays_stable_for_equivalent_values(self) -> None:
        with TemporaryDirectory() as directory:
            service, client = self.make_service(Path(directory))
            plain = NarrationSegment("This is the key idea.", emotion="neutral", pace="slow")
            discovery = NarrationSegment("This is the key idea.", emotion="discovery", pace="slow")
            equivalent = NarrationSegment("  This is the key idea.  ", emotion=" discovery ", pace=" slow ")

            service._wrap_generate_from_text(plain.text, narration_segment=plain)
            service._wrap_generate_from_text(discovery.text, narration_segment=discovery)
            service._wrap_generate_from_text(equivalent.text, narration_segment=equivalent)

            self.assertEqual(len(client.models.calls), 2)
            first_input = client.models.calls[0]["contents"]
            second_input = client.models.calls[1]["contents"]
            self.assertNotEqual(first_input, second_input)

    def test_cache_input_records_profile_and_delivery(self) -> None:
        with TemporaryDirectory() as directory:
            service, _ = self.make_service(Path(directory))
            request = service.renderer.build_request(
                NarrationSegment("This is the key idea.", emotion="discovery"),
                service.profile,
            )
            input_data = service._input_data_for_request(request.transcript, request)
            delivery = input_data["config"]["delivery"]
            self.assertEqual(delivery["emotion"], "discovery")
            self.assertEqual(input_data["config"]["profile"]["persona"], service.profile.persona)


class CompatibilityTests(unittest.TestCase):
    def test_expressive_scene_retains_plain_voiceover_shape_and_short_aliases(self) -> None:
        parameters = inspect.signature(ExpressiveVoiceoverScene.voiceover).parameters
        self.assertIn("text", parameters)
        self.assertIn("intent", parameters)
        self.assertIn("emotion", parameters)
        self.assertTrue(callable(ExpressiveVoiceoverScene.narrated))
        self.assertTrue(callable(ExpressiveVoiceoverScene.say))
        self.assertTrue(callable(ExpressiveVoiceoverScene.narration_pause))


if __name__ == "__main__":
    unittest.main()
