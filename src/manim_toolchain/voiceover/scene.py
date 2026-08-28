"""A composition-based VoiceoverScene with narration-aware conveniences."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from manim_voiceover import VoiceoverScene
from manim_voiceover.tracker import VoiceoverTracker

from ..narration import (
    DEFAULT_NARRATION_PROFILE,
    NarrationProfile,
    NarrationSegment,
    resolve_delivery,
    resolve_pause,
)


class ExpressiveVoiceoverScene(VoiceoverScene):
    """VoiceoverScene compatibility plus semantic delivery and intentional silence."""

    narration_profile: NarrationProfile = DEFAULT_NARRATION_PROFILE
    narration_scene_context: str | None = None

    def set_narration_profile(self, profile: NarrationProfile) -> None:
        if not isinstance(profile, NarrationProfile):
            raise TypeError("profile must be a NarrationProfile")
        self.narration_profile = profile
        service = getattr(self, "speech_service", None)
        if getattr(service, "supports_narration_segments", False):
            service.set_narration_profile(profile)

    def set_narration_scene_context(self, context: str | None) -> None:
        if context is not None and not isinstance(context, str):
            raise TypeError("context must be a string or None")
        self.narration_scene_context = " ".join(context.split()) if context else None

    def narration_pause(self, duration: float | int | str) -> None:
        """Reserve visual-only breathing room without generating speech."""

        self.safe_wait(resolve_pause(duration, "duration"))

    @contextmanager
    def voiceover(
        self,
        text: str | None = None,
        ssml: str | None = None,
        *,
        segment: NarrationSegment | None = None,
        subtitle: str | None = None,
        intent: str | None = None,
        emotion: str | None = None,
        pace: str | None = None,
        energy: str | None = None,
        emphasis: tuple[str, ...] | list[str] | str | None = None,
        pause_before: float | int | str | None = None,
        pause_after: float | int | str | None = None,
        delivery_notes: str | None = None,
        scene_context: str | None = None,
        **kwargs: object,
    ) -> Generator[VoiceoverTracker, None, None]:
        """Add plain or expressive narration while preserving VoiceoverTracker timing."""

        if ssml is not None:
            if segment is not None or any(
                value is not None
                for value in (
                    subtitle,
                    intent,
                    emotion,
                    pace,
                    energy,
                    emphasis,
                    pause_before,
                    pause_after,
                    delivery_notes,
                    scene_context,
                )
            ):
                raise ValueError("structured narration metadata is available for text voiceovers, not SSML")
            with super().voiceover(text=text, ssml=ssml, **kwargs) as tracker:
                yield tracker
            return

        if text is None and segment is None:
            raise ValueError("Please specify text or a NarrationSegment.")
        if segment is not None and not isinstance(segment, NarrationSegment):
            raise TypeError("segment must be a NarrationSegment")
        if segment is not None and text is not None and text != segment.text:
            raise ValueError("text and segment.text must match when both are supplied")

        raw_segment = segment or NarrationSegment(
            text=text or "",
            subtitle=subtitle,
            intent=intent,
            emotion=emotion,
            pace=pace,
            energy=energy,
            emphasis=() if emphasis is None else emphasis,
            pause_before=pause_before,
            pause_after=pause_after,
            delivery_notes=delivery_notes,
        )
        if segment is not None and any(
            value is not None
            for value in (
                subtitle,
                intent,
                emotion,
                pace,
                energy,
                emphasis,
                pause_before,
                pause_after,
                delivery_notes,
            )
        ):
            raise ValueError("pass metadata either inside segment or as voiceover keyword arguments, not both")

        resolved = resolve_delivery(raw_segment, self.narration_profile)
        subcaption = kwargs.pop("subcaption", None)
        if subcaption is not None and not isinstance(subcaption, str):
            raise TypeError("subcaption must be a string or None")
        if subtitle is not None and subcaption is not None and subtitle != subcaption:
            raise ValueError("subtitle and subcaption must match when both are supplied")
        subcaption = subcaption or resolved.subtitle_text

        service_kwargs: dict[str, object] = dict(kwargs)
        service = getattr(self, "speech_service", None)
        if getattr(service, "supports_narration_segments", False):
            service_kwargs.update(
                narration_segment=raw_segment,
                narration_profile=self.narration_profile,
                scene_context=scene_context or self.narration_scene_context,
            )

        self.narration_pause(raw_segment.pause_before)
        with super().voiceover(text=raw_segment.text, subcaption=subcaption, **service_kwargs) as tracker:
            yield tracker
        self.narration_pause(raw_segment.pause_after)

    def narrated(self, text: str, **kwargs: object) -> Generator[VoiceoverTracker, None, None]:
        """Readable alias for ``voiceover`` in new educational scenes."""

        return self.voiceover(text=text, **kwargs)

    def say(self, text: str, **kwargs: object) -> Generator[VoiceoverTracker, None, None]:
        """Short alias for ``narrated``; use it as a context manager."""

        return self.narrated(text, **kwargs)
