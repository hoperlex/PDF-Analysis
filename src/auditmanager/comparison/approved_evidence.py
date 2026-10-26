"""The deterministic evidence of the approved pairs: recomputed, verified, sealed.

`COMPARE-PERSISTED-SUMMARY-01`. A stored approval says *which* pages an expert paired and the
digests of what they saw; it stores no text. Everything served about an approved pair is
recomputed here from the immutable inputs by the modules written for it:

1. each approved page must still have the SHA-256 the expert saw (a page of another text is
   ``text_changed`` and no difference is served for any pair of the set);
2. :func:`~auditmanager.comparison.raw_text.diff_approved_pairs` computes the raw line differences
   of the approved pairs only -- an unapproved proposal never gets this view;
3. :func:`~auditmanager.comparison.raw_evidence_seal.seal_raw_version_evidence` binds them to the
   version bytes and the link revision; the seal must equal the one stored with the latest
   event, or the evidence is ``seal_changed``.

Nothing here writes, and nothing here reads a model's output: a summary is a separate record that
*refers* to the hunk identities defined here (``<sheet_link_id>:<n>``) and cannot reach the
differences.

**Bounds, never truncation.** ``diff_approved_pairs`` refuses an input beyond its page and total
ceilings and the served differences are held to the response budget of the proposal diffs
(:data:`MAX_APPROVED_CHANGED_CHARACTERS`); a set beyond either is ``too_large`` and serves none.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from typing import Final

from auditmanager.comparison.raw_evidence_seal import (
    RawEvidenceSeal,
    RawEvidenceSealRefused,
    seal_raw_version_evidence,
)
from auditmanager.comparison.raw_text import (
    ApprovedSheetPair as RawApprovedPair,
)
from auditmanager.comparison.raw_text import (
    RawTextDiff,
    RawTextDiffRefused,
    diff_approved_pairs,
)
from auditmanager.comparison.read_model import (
    EVIDENCE_NONE,
    EVIDENCE_SEAL_CHANGED,
    EVIDENCE_SEALED,
    EVIDENCE_TEXT_CHANGED,
    EVIDENCE_TOO_LARGE,
    LINK_TEXT_CHANGED,
    LINK_VERIFIED,
    ApprovedDiffHunk,
    ApprovedSheetDiff,
    ApprovedSheetPair,
    ApprovedSheetPairs,
)
from auditmanager.comparison.sheet_links import LinkEvent, LinkState
from auditmanager.comparison.version_reader import OrderedVersionPair

#: The response budget of the proposal diffs (``service.MAX_DIFF_PAGE_CHARACTERS``), restated so
#: that this module does not import the service; a test holds the two equal.
MAX_APPROVED_CHANGED_CHARACTERS: Final[int] = 500_000


class ApprovedEvidenceRefused(ValueError):
    """The approved set cannot yield one bounded, verifiable raw artifact."""


def hunk_id(sheet_link_id: str, ordinal: int) -> str:
    """The identity of the ``ordinal``-th non-equal span of a link's raw diff (from 0)."""
    return f"{sheet_link_id}:{ordinal}"


def page_text_sha256(text: str) -> str:
    """The digest ``raw_text`` records for a page text: SHA-256 of its UTF-8 bytes."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _digest_or_none(text: str) -> str | None:
    try:
        return page_text_sha256(text)
    except UnicodeEncodeError:
        return None


def link_is_verified(
    link: LinkEvent, source_pages: Mapping[int, str], target_pages: Mapping[int, str],
) -> bool:
    """Both approved pages still have exactly the text digest the expert saw."""
    source = source_pages.get(link.source_page_number)
    target = target_pages.get(link.target_page_number)
    return (
        source is not None
        and target is not None
        and _digest_or_none(source) == link.source_page_text_sha256
        and _digest_or_none(target) == link.target_page_text_sha256
    )


def raw_artifact(
    *,
    pair: OrderedVersionPair,
    comparison_id: str,
    link_revision: int,
    links: Sequence[tuple[str, int, int]],
    source_pages: Mapping[int, str],
    target_pages: Mapping[int, str],
) -> tuple[tuple[RawTextDiff, ...], RawEvidenceSeal]:
    """The raw differences and the seal of a set of ``(sheet_link_id, source page, target page)``.

    Raises :class:`ApprovedEvidenceRefused` when the set is beyond the bounds of the raw modules.
    """
    approved = [
        RawApprovedPair(
            comparison_id, sheet_link_id, link_revision,
            pair.source.version_uid, pair.target.version_uid, source_page, target_page,
        )
        for sheet_link_id, source_page, target_page in links
    ]
    try:
        diffs = diff_approved_pairs(
            comparison_id=comparison_id,
            source_version_uid=pair.source.version_uid,
            target_version_uid=pair.target.version_uid,
            link_revision=link_revision,
            approved_pairs=approved,
            source_pages={source: source_pages[source] for _, source, _ in links},
            target_pages={target: target_pages[target] for _, _, target in links},
        )
        seal = seal_raw_version_evidence(
            version_pair=pair, comparison_id=comparison_id,
            link_revision=link_revision, raw_diffs=diffs,
        )
    except (RawTextDiffRefused, RawEvidenceSealRefused, KeyError) as refusal:
        raise ApprovedEvidenceRefused(str(refusal)) from None
    return diffs, seal


def _projected(diff: RawTextDiff) -> ApprovedSheetDiff:
    hunks: list[ApprovedDiffHunk] = []
    ordinal = 0
    for change in diff.changes:
        if change.tag == "equal":
            hunks.append(ApprovedDiffHunk(
                change.tag, change.source_start, change.source_end,
                change.target_start, change.target_end, (), (), None,
            ))
            continue
        hunks.append(ApprovedDiffHunk(
            change.tag, change.source_start, change.source_end,
            change.target_start, change.target_end,
            change.source_lines, change.target_lines, hunk_id(diff.sheet_link_id, ordinal),
        ))
        ordinal += 1
    return ApprovedSheetDiff(
        sum(c.source_end - c.source_start for c in diff.changes),
        sum(c.target_end - c.target_start for c in diff.changes),
        sum(c.target_end - c.target_start for c in diff.changes if c.tag in ("insert", "replace")),
        sum(c.source_end - c.source_start for c in diff.changes if c.tag in ("delete", "replace")),
        tuple(hunks),
        diff.evidence_sha256,
    )


def changed_characters(diffs: Sequence[RawTextDiff]) -> int:
    return sum(
        sum(map(len, change.source_lines)) + sum(map(len, change.target_lines))
        for diff in diffs for change in diff.changes if change.tag != "equal"
    )


def project_approved_pairs(
    *,
    pair: OrderedVersionPair,
    state: LinkState,
    source_pages: Mapping[int, str],
    target_pages: Mapping[int, str],
) -> ApprovedSheetPairs:
    """What ``compareDocumentVersions`` says about the active approvals of ``pair``."""
    revision = state.latest_revision or None
    active = state.active
    if not active:
        return ApprovedSheetPairs(revision, EVIDENCE_NONE, None, ())
    comparison_id = state.comparison_id
    assert comparison_id is not None  # an active link implies a stored history

    def items(diffs: Mapping[str, RawTextDiff], verified: Mapping[str, bool]) -> tuple[ApprovedSheetPair, ...]:
        return tuple(
            ApprovedSheetPair(
                link.sheet_link_id, link.source_page_number, link.target_page_number,
                LINK_VERIFIED if verified[link.sheet_link_id] else LINK_TEXT_CHANGED,
                link.suggestion_sha256, link.actor_label, link.decided_at, link.link_revision,
                _projected(diffs[link.sheet_link_id]) if link.sheet_link_id in diffs else None,
            )
            for link in active
        )

    verified = {
        link.sheet_link_id: link_is_verified(link, source_pages, target_pages) for link in active
    }
    if not all(verified.values()):
        return ApprovedSheetPairs(revision, EVIDENCE_TEXT_CHANGED, None, items({}, verified))
    try:
        diffs, seal = raw_artifact(
            pair=pair, comparison_id=comparison_id, link_revision=state.latest_revision,
            links=[(l.sheet_link_id, l.source_page_number, l.target_page_number) for l in active],
            source_pages=source_pages, target_pages=target_pages,
        )
    except ApprovedEvidenceRefused:
        return ApprovedSheetPairs(revision, EVIDENCE_TOO_LARGE, None, items({}, verified))
    if seal.seal_sha256 != state.latest_seal_sha256:
        return ApprovedSheetPairs(revision, EVIDENCE_SEAL_CHANGED, None, items({}, verified))
    if changed_characters(diffs) > MAX_APPROVED_CHANGED_CHARACTERS:
        return ApprovedSheetPairs(revision, EVIDENCE_TOO_LARGE, None, items({}, verified))
    return ApprovedSheetPairs(
        revision, EVIDENCE_SEALED, seal.seal_sha256,
        items({diff.sheet_link_id: diff for diff in diffs}, verified),
    )


__all__ = [
    "ApprovedEvidenceRefused", "MAX_APPROVED_CHANGED_CHARACTERS", "changed_characters",
    "hunk_id", "link_is_verified", "page_text_sha256", "project_approved_pairs", "raw_artifact",
]
