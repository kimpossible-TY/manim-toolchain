"""A small renderer boundary so narration semantics do not belong to Gemini."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from .inference import resolve_delivery
from .models import NarrationProfile, NarrationSegment, ResolvedNarration
from .prompt_builder import GeminiPromptBuilder


@dataclass(frozen=True)
class SpeechRequest:
    transcript: str
    subtitle: str
    prompt: str
    resolved: ResolvedNarration


class SpeechRenderer(ABC):
    """Backend request builder; audio APIs can implement this without changing scenes."""

    @abstractmethod
    def build_request(
        self,
        segment: NarrationSegment,
        profile: NarrationProfile,
        *,
        scene_context: str | None = None,
    ) -> SpeechRequest:
        raise NotImplementedError


class GeminiSpeechRenderer(SpeechRenderer):
    """Gemini adapter that turns semantic delivery into a Gemini content prompt."""

    def __init__(self, prompt_builder: GeminiPromptBuilder | None = None) -> None:
        self.prompt_builder = prompt_builder or GeminiPromptBuilder()

    def build_request(
        self,
        segment: NarrationSegment,
        profile: NarrationProfile,
        *,
        scene_context: str | None = None,
    ) -> SpeechRequest:
        resolved = resolve_delivery(segment, profile)
        return SpeechRequest(
            transcript=resolved.text,
            subtitle=resolved.subtitle_text,
            prompt=self.prompt_builder.build(resolved, scene_context=scene_context),
            resolved=resolved,
        )
