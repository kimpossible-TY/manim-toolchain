"""Manim Voiceover adapters for structured educational narration."""

from .gemini_expressive import ExpressiveGeminiService
from .scene import ExpressiveVoiceoverScene

__all__ = ["ExpressiveGeminiService", "ExpressiveVoiceoverScene"]
