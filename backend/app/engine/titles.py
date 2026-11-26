"""Single source of truth for comparing movie titles across sources.

BookMyShow and District decorate the same film differently — ``"The Paradise
(Telugu)"``, ``"The Paradise [Hindi]"``, ``"The Paradise 3D"``. Every place that
needs to decide "is this the same movie?" must use these helpers so the rules
never drift apart.
"""

from __future__ import annotations

import re

_LANGUAGES = "telugu|hindi|tamil|kannada|malayalam|english|bengali|marathi|punjabi"
_FORMATS = "2d|3d|imax|4dx|dolby"
_DECORATIONS = f"{_LANGUAGES}|{_FORMATS}"

_PAREN_RE = re.compile(rf"\((?:{_DECORATIONS})\)", re.IGNORECASE)
_BRACKET_RE = re.compile(rf"\[(?:{_DECORATIONS})\]", re.IGNORECASE)
_FORMAT_WORD_RE = re.compile(r"\b(?:2d|3d|imax|4dx)\b", re.IGNORECASE)
_LANGUAGE_WORD_RE = re.compile(rf"\b(?:{_LANGUAGES})\b", re.IGNORECASE)
_LEADING_THE_RE = re.compile(r"^the\s+", re.IGNORECASE)
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]")


def normalize_title(title: str, *, strip_languages: bool = False) -> str:
    """Reduce a title to a comparable key.

    ``strip_languages`` also removes bare language words (``"Paradise Telugu"``),
    which the TMDB lookup needs but the catalog matcher does not.
    """
    text = _PAREN_RE.sub("", title or "")
    text = _BRACKET_RE.sub("", text)
    text = _FORMAT_WORD_RE.sub("", text)
    if strip_languages:
        text = _LANGUAGE_WORD_RE.sub("", text)
    text = _LEADING_THE_RE.sub("", text.strip())
    return _NON_ALNUM_RE.sub("", text.lower())


def names_match(a: str, b: str) -> bool:
    """Whether two decorated titles refer to the same film."""
    norm_a = normalize_title(a)
    norm_b = normalize_title(b)
    if not norm_a or not norm_b:
        return False
    return norm_a == norm_b or (
        len(norm_a) >= 4 and len(norm_b) >= 4 and (norm_a in norm_b or norm_b in norm_a)
    )
