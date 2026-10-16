"""Unserved W59 review choices for one immutable document version.

Every catalogue entry remains available for an explicit expert choice, even
when the filename and text heuristics find no evidence. This packet is display
input only: it cannot confirm a section or authorize a run.
"""

from __future__ import annotations

from dataclasses import dataclass

from auditmanager.sections.suggestion import SectionSuggestion, _catalogue, suggest_sections
from auditmanager.shared.identity import IdentityError, VersionUid


class SectionReviewUnavailable(ValueError):
    """The version or candidate catalogue cannot produce a reliable review."""


@dataclass(frozen=True, slots=True)
class SectionReviewOption:
    code: str
    name: str
    suggestion: SectionSuggestion | None


@dataclass(frozen=True, slots=True)
class SectionReviewPacket:
    version_uid: str
    options: tuple[SectionReviewOption, ...]


def prepare_section_review(
    *, version_uid: str, filename: str, extracted_text: str
) -> SectionReviewPacket:
    """List all candidate choices without selecting the highest suggestion.

    The future caller must load the requested version and authorize its actor.
    This function validates only the opaque identity format and local
    candidate evidence; it has no persistence, profile or routing authority.
    """
    try:
        VersionUid.parse(version_uid)
    except IdentityError:
        raise SectionReviewUnavailable("version_identity_invalid") from None
    if not isinstance(filename, str) or not isinstance(extracted_text, str):
        raise SectionReviewUnavailable("review_evidence_invalid")

    catalogue = _catalogue()
    codes = {entry.code for entry in catalogue}
    if len(catalogue) != 15 or len(codes) != 15:
        raise SectionReviewUnavailable("section_catalogue_invalid")

    suggestions = suggest_sections(filename, extracted_text)
    evidence = {item.code: item for item in suggestions}
    if len(evidence) != len(suggestions) or not evidence.keys() <= codes:
        raise SectionReviewUnavailable("section_suggestion_invalid")
    if any(
        evidence[entry.code].name != entry.name
        for entry in catalogue
        if entry.code in evidence
    ):
        raise SectionReviewUnavailable("section_suggestion_invalid")

    return SectionReviewPacket(
        version_uid=version_uid,
        options=tuple(
            SectionReviewOption(entry.code, entry.name, evidence.get(entry.code))
            for entry in sorted(catalogue, key=lambda item: item.code)
        ),
    )
