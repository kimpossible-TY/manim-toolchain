"""Semantic, backend-independent models for educational narration."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Iterable


class NarrationIntent(StrEnum):
    EXPLAIN = "explain"
    QUESTION = "question"
    CONTRAST = "contrast"
    REVEAL = "reveal"
    SUMMARIZE = "summarize"
    TRANSITION = "transition"
    WARN = "warn"
    DEFINE = "define"


class NarrationEmotion(StrEnum):
    NEUTRAL = "neutral"
    CURIOUS = "curious"
    THOUGHTFUL = "thoughtful"
    DISCOVERY = "discovery"
    EXCITED = "excited"
    SERIOUS = "serious"
    REASSURING = "reassuring"


class NarrationPace(StrEnum):
    SLOW = "slow"
    MODERATE = "moderate"
    FAST = "fast"


class NarrationEnergy(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PauseLength(StrEnum):
    BRIEF = "brief"
    MEDIUM = "medium"
    LONG = "long"


PAUSE_SECONDS: dict[PauseLength, float] = {
    PauseLength.BRIEF: 0.35,
    PauseLength.MEDIUM: 0.6,
    PauseLength.LONG: 0.9,
}


def _coerce_enum[T: StrEnum](value: T | str | None, enum_type: type[T], field_name: str) -> T | None:
    if value is None:
        return None
    if isinstance(value, enum_type):
        return value
    if isinstance(value, str):
        try:
            return enum_type(value.strip().lower())
        except ValueError as exc:
            choices = ", ".join(item.value for item in enum_type)
            raise ValueError(f"{field_name} must be one of: {choices}") from exc
    raise TypeError(f"{field_name} must be a string, {enum_type.__name__}, or None")


def resolve_pause(value: float | int | PauseLength | str | None, field_name: str = "pause") -> float:
    """Turn a semantic pause name or seconds into a non-negative duration."""

    if value is None:
        return 0.0
    if isinstance(value, bool):
        raise TypeError(f"{field_name} must be seconds or a semantic pause name")
    if isinstance(value, (int, float)):
        if value < 0:
            raise ValueError(f"{field_name} must not be negative")
        return round(float(value), 3)
    if isinstance(value, PauseLength):
        return PAUSE_SECONDS[value]
    if isinstance(value, str):
        try:
            return PAUSE_SECONDS[PauseLength(value.strip().lower())]
        except ValueError as exc:
            choices = ", ".join(item.value for item in PauseLength)
            raise ValueError(f"{field_name} must be seconds or one of: {choices}") from exc
    raise TypeError(f"{field_name} must be seconds or a semantic pause name")


def _normalise_text(value: str, field_name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    normalised = " ".join(value.split())
    if not normalised and not allow_empty:
        raise ValueError(f"{field_name} must not be empty")
    return normalised


def _normalise_emphasis(values: Iterable[str] | None) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, str):
        values = (values,)
    cleaned: dict[str, str] = {}
    for value in values:
        phrase = _normalise_text(value, "emphasis")
        cleaned.setdefault(phrase.casefold(), phrase)
    return tuple(sorted(cleaned.values(), key=str.casefold))


@dataclass(frozen=True)
class NarrationSegment:
    """One spoken line, optionally distinct from the text displayed as subtitles."""

    text: str
    subtitle: str | None = None
    intent: NarrationIntent | str | None = None
    emotion: NarrationEmotion | str | None = None
    pace: NarrationPace | str | None = None
    energy: NarrationEnergy | str | None = None
    emphasis: tuple[str, ...] | Iterable[str] = field(default_factory=tuple)
    pause_before: float | int | PauseLength | str | None = None
    pause_after: float | int | PauseLength | str | None = None
    delivery_notes: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "text", _normalise_text(self.text, "text"))
        if self.subtitle is not None:
            object.__setattr__(self, "subtitle", _normalise_text(self.subtitle, "subtitle"))
        object.__setattr__(self, "intent", _coerce_enum(self.intent, NarrationIntent, "intent"))
        object.__setattr__(self, "emotion", _coerce_enum(self.emotion, NarrationEmotion, "emotion"))
        object.__setattr__(self, "pace", _coerce_enum(self.pace, NarrationPace, "pace"))
        object.__setattr__(self, "energy", _coerce_enum(self.energy, NarrationEnergy, "energy"))
        object.__setattr__(self, "emphasis", _normalise_emphasis(self.emphasis))
        object.__setattr__(self, "pause_before", resolve_pause(self.pause_before, "pause_before"))
        object.__setattr__(self, "pause_after", resolve_pause(self.pause_after, "pause_after"))
        if self.delivery_notes is not None:
            object.__setattr__(
                self,
                "delivery_notes",
                _normalise_text(self.delivery_notes, "delivery_notes"),
            )

    @property
    def subtitle_text(self) -> str:
        """The human-readable transcript used for captions, never directions."""

        return self.subtitle or self.text


@dataclass(frozen=True)
class NarrationProfile:
    """Stable voice identity and default delivery for an educational project."""

    persona: str = "A thoughtful mathematical educator speaking directly to one curious student"
    tone: str = "Warm, precise, and intellectually curious; conversational, never announcer-like"
    default_pace: NarrationPace | str = NarrationPace.MODERATE
    default_energy: NarrationEnergy | str = NarrationEnergy.MEDIUM
    expressiveness: str = "moderate"

    def __post_init__(self) -> None:
        object.__setattr__(self, "persona", _normalise_text(self.persona, "persona"))
        object.__setattr__(self, "tone", _normalise_text(self.tone, "tone"))
        default_pace = _coerce_enum(self.default_pace, NarrationPace, "default_pace")
        default_energy = _coerce_enum(self.default_energy, NarrationEnergy, "default_energy")
        if default_pace is None or default_energy is None:
            raise ValueError("NarrationProfile defaults must be explicit semantic values")
        object.__setattr__(self, "default_pace", default_pace)
        object.__setattr__(self, "default_energy", default_energy)
        object.__setattr__(self, "expressiveness", _normalise_text(self.expressiveness, "expressiveness").lower())

    def cache_dict(self) -> dict[str, str]:
        return {
            "persona": self.persona,
            "tone": self.tone,
            "default_pace": self.default_pace.value,
            "default_energy": self.default_energy.value,
            "expressiveness": self.expressiveness,
        }


DEFAULT_NARRATION_PROFILE = NarrationProfile()


@dataclass(frozen=True)
class ResolvedNarration:
    """A segment after deterministic defaults and delivery inference are resolved."""

    segment: NarrationSegment
    profile: NarrationProfile
    intent: NarrationIntent
    emotion: NarrationEmotion
    pace: NarrationPace
    energy: NarrationEnergy

    @property
    def text(self) -> str:
        return self.segment.text

    @property
    def subtitle_text(self) -> str:
        return self.segment.subtitle_text

    def cache_dict(self) -> dict[str, object]:
        return {
            "intent": self.intent.value,
            "emotion": self.emotion.value,
            "pace": self.pace.value,
            "energy": self.energy.value,
            "emphasis": list(self.segment.emphasis),
            "pause_before": self.segment.pause_before,
            "pause_after": self.segment.pause_after,
            "delivery_notes": self.segment.delivery_notes or "",
        }
