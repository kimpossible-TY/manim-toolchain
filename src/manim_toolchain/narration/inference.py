"""Small deterministic delivery heuristics for ordinary educational prose."""

from __future__ import annotations

from dataclasses import replace
import re

from .models import (
    DEFAULT_NARRATION_PROFILE,
    NarrationEmotion,
    NarrationEnergy,
    NarrationIntent,
    NarrationPace,
    NarrationProfile,
    NarrationSegment,
    ResolvedNarration,
)


_QUESTION_RE = re.compile(r"\?\s*$")
_DEFINE_RE = re.compile(r"\b(we call|is called|by .* we mean|means|is a|is an|define)\b")
_CONTRAST_RE = re.compile(r"\b(but|however|instead|rather than|different question|on the other hand)\b")
_REVEAL_RE = re.compile(r"\b(key idea|important part|surprising|this is exactly|here is|changes everything|notice what)\b")
_SUMMARY_RE = re.compile(r"\b(in summary|therefore|so the point is|this means|to summarize)\b")
_TRANSITION_RE = re.compile(r"\b(now|next|let us|let's|watch|turn to|move to)\b")
_WARN_RE = re.compile(r"\b(careful|warning|do not|does not mean|not the same)\b")
_MATH_RE = re.compile(r"[=∈∂∇λΔ^]|\\|\b(l two|r n|partial derivative|nabla|lambda)\b", re.IGNORECASE)


def _infer_intent(text: str) -> NarrationIntent:
    if _QUESTION_RE.search(text):
        return NarrationIntent.QUESTION
    if _WARN_RE.search(text):
        return NarrationIntent.WARN
    if _REVEAL_RE.search(text):
        return NarrationIntent.REVEAL
    if _CONTRAST_RE.search(text):
        return NarrationIntent.CONTRAST
    if _DEFINE_RE.search(text):
        return NarrationIntent.DEFINE
    if _SUMMARY_RE.search(text):
        return NarrationIntent.SUMMARIZE
    if _TRANSITION_RE.search(text):
        return NarrationIntent.TRANSITION
    return NarrationIntent.EXPLAIN


def _inferred_emotion(intent: NarrationIntent) -> NarrationEmotion:
    return {
        NarrationIntent.QUESTION: NarrationEmotion.CURIOUS,
        NarrationIntent.CONTRAST: NarrationEmotion.THOUGHTFUL,
        NarrationIntent.REVEAL: NarrationEmotion.DISCOVERY,
        NarrationIntent.SUMMARIZE: NarrationEmotion.REASSURING,
        NarrationIntent.TRANSITION: NarrationEmotion.CURIOUS,
        NarrationIntent.WARN: NarrationEmotion.SERIOUS,
        NarrationIntent.DEFINE: NarrationEmotion.NEUTRAL,
        NarrationIntent.EXPLAIN: NarrationEmotion.NEUTRAL,
    }[intent]


def _inferred_pace(text: str, intent: NarrationIntent, profile: NarrationProfile) -> NarrationPace:
    word_count = len(text.split())
    if _MATH_RE.search(text) or word_count >= 25:
        return NarrationPace.SLOW
    if intent in {NarrationIntent.REVEAL, NarrationIntent.CONTRAST, NarrationIntent.DEFINE, NarrationIntent.WARN}:
        return NarrationPace.SLOW
    return profile.default_pace


def _inferred_energy(intent: NarrationIntent, profile: NarrationProfile) -> NarrationEnergy:
    if intent is NarrationIntent.REVEAL:
        return NarrationEnergy.MEDIUM
    if intent in {NarrationIntent.DEFINE, NarrationIntent.WARN}:
        return NarrationEnergy.LOW
    return profile.default_energy


def resolve_delivery(
    segment: NarrationSegment,
    profile: NarrationProfile | None = None,
) -> ResolvedNarration:
    """Resolve only absent fields; explicit delivery metadata always wins."""

    if not isinstance(segment, NarrationSegment):
        raise TypeError("segment must be a NarrationSegment")
    profile = profile or DEFAULT_NARRATION_PROFILE
    if not isinstance(profile, NarrationProfile):
        raise TypeError("profile must be a NarrationProfile")

    intent = segment.intent or _infer_intent(segment.text.casefold())
    return ResolvedNarration(
        segment=segment,
        profile=profile,
        intent=intent,
        emotion=segment.emotion or _inferred_emotion(intent),
        pace=segment.pace or _inferred_pace(segment.text.casefold(), intent, profile),
        energy=segment.energy or _inferred_energy(intent, profile),
    )


def narration(
    text: str,
    *,
    subtitle: str | None = None,
    profile: NarrationProfile | None = None,
    **delivery: object,
) -> NarrationSegment:
    """Convenience constructor that returns a segment with inferred defaults filled in."""

    raw = NarrationSegment(text=text, subtitle=subtitle, **delivery)
    resolved = resolve_delivery(raw, profile)
    return replace(
        raw,
        intent=resolved.intent,
        emotion=resolved.emotion,
        pace=resolved.pace,
        energy=resolved.energy,
    )
