"""Opt-in helpers for a few common mathematical spoken forms.

This intentionally does not try to pronounce arbitrary Typst, LaTeX, or source
code. Use an explicit ``NarrationSegment(text=..., subtitle=...)`` whenever a
formula needs a carefully chosen spoken form.
"""

from __future__ import annotations

import re


_MATH_SPEECH_REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\\mathbb\{R\}\^n|R\^n|ℝ\^n"), "R n"),
    (re.compile(r"L\^2|L²"), "L two"),
    (re.compile(r"\\nabla|∇"), "nabla"),
    (re.compile(r"\\lambda|λ"), "lambda"),
    (re.compile(r"\\partial|∂"), "partial"),
    (re.compile(r"\bf\(x\)"), "f of x"),
    (re.compile(r"\\in\b|\bin\b|∈"), " belongs to "),
)


def math_speech(display_math: str) -> str:
    """Convert a small, documented set of common symbols into spoken prose.

    Call this only for source the author intends to be spoken. It is not a
    general parser and deliberately leaves unknown markup visible for review.
    """

    spoken = display_math
    for pattern, replacement in _MATH_SPEECH_REPLACEMENTS:
        spoken = pattern.sub(replacement, spoken)
    spoken = re.sub(r"(?<=\w)\(", " (", spoken)
    return " ".join(spoken.split())
