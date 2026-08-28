"""Backend-neutral narration content, delivery planning, and prompt helpers."""

from .inference import narration, resolve_delivery
from .models import (
    DEFAULT_NARRATION_PROFILE,
    NarrationEmotion,
    NarrationEnergy,
    NarrationIntent,
    NarrationPace,
    NarrationProfile,
    NarrationSegment,
    ResolvedNarration,
    resolve_pause,
)
from .prompt_builder import GeminiPromptBuilder
from .pronunciation import math_speech
from .renderer import GeminiSpeechRenderer, SpeechRenderer, SpeechRequest

__all__ = [
    "DEFAULT_NARRATION_PROFILE",
    "GeminiPromptBuilder",
    "GeminiSpeechRenderer",
    "NarrationEmotion",
    "NarrationEnergy",
    "NarrationIntent",
    "NarrationPace",
    "NarrationProfile",
    "NarrationSegment",
    "ResolvedNarration",
    "SpeechRenderer",
    "SpeechRequest",
    "math_speech",
    "narration",
    "resolve_delivery",
    "resolve_pause",
]
