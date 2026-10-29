"""Bounded text fragments with PDF-point box anchors from stored page profiles.

The profile's words are raw deterministic evidence. A missing text layer (a scan)
produces no text fragment; it does not prove that the drawing contains no text.
"""

from __future__ import annotations

import hashlib
import json
import math
import unicodedata
from dataclasses import dataclass

from auditmanager.comparison.profile.models import PageProfileData, Word

__all__ = ["FragmentRefused", "TextFragment", "canonical_text", "extract_fragments"]

_ALGORITHM = "stage-profile-lines-v1"
_MAX_WORDS = 10_000
_MAX_CHARACTERS = 200_000
_MAX_FRAGMENTS = 2_000
_MAX_FRAGMENT_CHARACTERS = 20_000
_ROW_TOLERANCE_PT = 3.0


class FragmentRefused(ValueError):
    """A profile cannot yield complete, attributable fragments within the budget."""


@dataclass(frozen=True, slots=True)
class TextFragment:
    content_key: str
    profile_id: str
    side: str
    page_number: int
    text: str
    normalised_text: str
    box_anchor: dict[str, float]


def canonical_text(value: str) -> str:
    """Only typographic equivalence; numbers, units and punctuation stay distinct."""
    return " ".join(unicodedata.normalize("NFKC", value).casefold().replace("ё", "е").split())


def _valid_word(word: Word, width: float, height: float) -> bool:
    coords = (word.x0, word.top, word.x1, word.bottom)
    return (
        isinstance(word.text, str)
        and all(isinstance(v, (int, float)) and math.isfinite(v) for v in coords)
        and 0 <= word.x0 < word.x1 <= width
        and 0 <= word.top < word.bottom <= height
    )


def _key(profile_id: str, ordinal: int, canonical: str, box: dict[str, float]) -> str:
    body = [_ALGORITHM, profile_id, ordinal, canonical, box]
    return hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def extract_fragments(profile: PageProfileData, *, side: str) -> tuple[TextFragment, ...]:
    """Extract complete visual text rows; refuse malformed or oversized evidence.

    Text rows are independent fragments. The caller must read the profile by its
    immutable ID through the comparison public reader and validate pair scope.
    """
    if side not in {"left", "right"} or not profile.row.is_ready:
        raise FragmentRefused("profile_not_ready_or_side_invalid")
    width, height = profile.width_pt, profile.height_pt
    if not all(math.isfinite(v) and v > 0 for v in (width, height)):
        raise FragmentRefused("page_dimensions_invalid")
    words = profile.words
    if len(words) > _MAX_WORDS or any(not isinstance(w.text, str) for w in words):
        raise FragmentRefused("profile_text_invalid_or_too_large")
    if sum(len(w.text) for w in words) > _MAX_CHARACTERS:
        raise FragmentRefused("profile_text_too_large")
    if any(not _valid_word(w, width, height) for w in words):
        raise FragmentRefused("word_box_invalid")
    ordered = sorted((w for w in words if w.text.strip()),
                     key=lambda w: ((w.top + w.bottom) / 2, w.x0, w.x1, w.text))
    rows: list[list[Word]] = []
    for word in ordered:
        center = (word.top + word.bottom) / 2
        if rows and abs(center - (rows[-1][0].top + rows[-1][0].bottom) / 2) <= _ROW_TOLERANCE_PT:
            rows[-1].append(word)
        else:
            rows.append([word])
        if len(rows) > _MAX_FRAGMENTS:
            raise FragmentRefused("too_many_fragments")
    out: list[TextFragment] = []
    for ordinal, row in enumerate(rows, 1):
        row.sort(key=lambda w: (w.x0, w.top, w.text))
        line = " ".join(w.text.strip() for w in row)
        if len(line) > _MAX_FRAGMENT_CHARACTERS:
            raise FragmentRefused("fragment_too_large")
        try:
            line.encode("utf-8")
        except UnicodeEncodeError:
            raise FragmentRefused("text_not_utf8_encodable") from None
        canonical = canonical_text(line)
        if not canonical:
            continue
        box = {
            "x0": min(w.x0 for w in row), "top": min(w.top for w in row),
            "x1": max(w.x1 for w in row), "bottom": max(w.bottom for w in row),
        }
        out.append(TextFragment(
            _key(profile.row.page_profile_id, ordinal, canonical, box),
            profile.row.page_profile_id, side, profile.row.page_number,
            line, canonical, box,
        ))
    return tuple(out)
