"""Compact Gemini-specific performance instructions built from semantic narration."""

from __future__ import annotations

from .models import NarrationProfile, ResolvedNarration


class GeminiPromptBuilder:
    """Build a compact instruction while keeping the transcript isolated at the end."""

    prompt_version = "gemini-expressive-v1"

    def build(
        self,
        resolved: ResolvedNarration,
        *,
        scene_context: str | None = None,
    ) -> str:
        lines = [
            "Audio Profile:",
            f"{resolved.profile.persona}. Tone: {resolved.profile.tone}. "
            f"Expressiveness: {resolved.profile.expressiveness}; remain natural and restrained.",
        ]
        if scene_context:
            lines.extend(("Scene Context:", " ".join(scene_context.split())))

        director_notes = self._director_notes(resolved)
        if director_notes:
            lines.extend(("Director's Notes:", director_notes))

        emphasis = ", ".join(f'"{phrase}"' for phrase in resolved.segment.emphasis) or "none"
        lines.extend(
            (
                "Delivery:",
                f"Intent: {resolved.intent.value}; emotion: {resolved.emotion.value}; "
                f"pace: {resolved.pace.value}; energy: {resolved.energy.value}; emphasize: {emphasis}.",
                "Transcript:",
                resolved.text,
            )
        )
        return "\n".join(lines)

    @staticmethod
    def _director_notes(resolved: ResolvedNarration) -> str:
        notes: list[str] = []
        if resolved.intent.value == "question":
            notes.append("Use a slight, natural rising intonation.")
        if resolved.intent.value == "reveal":
            notes.append("Let the conceptual reveal land with restrained discovery.")
        if resolved.intent.value == "define":
            notes.append("Be calm, deliberate, and precise.")
        if resolved.segment.pause_before:
            notes.append("Enter after a short moment of visual breathing room.")
        if resolved.segment.pause_after:
            notes.append("Finish cleanly and leave room for the visual to settle.")
        if resolved.segment.delivery_notes:
            notes.append(resolved.segment.delivery_notes)
        return " ".join(notes)
