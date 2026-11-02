"""Comparison versions are capped at 500 pages: the tables CHECK it, so the readers refuse it first.

`REVIEW-FIX-BOUNDS-1102` (finding S4-02 and the lift in ``c5cfc04e``). A relaxed intake may store a
longer document (migration 0044), but the comparison tables still hold page numbers
``BETWEEN 1 AND 500``. The version reader refuses a longer version up front, and the two modules that
re-check the pair keep a limit of their own, so neither depends on the reader's constant.
"""

from __future__ import annotations

import pytest

from auditmanager.comparison import finding_match_suggestions as suggestions
from auditmanager.comparison import raw_evidence_seal as seal
from auditmanager.comparison import version_reader
from auditmanager.comparison.version_reader import (
    OrderedVersionPair, VersionFacts, VersionPairRefused, _version_facts,
)

PROJECT = "prj_01M2545JSD15ETSNNV904X991J"
DOCUMENT = "doc_01M2545JSD15ETSNNV904X991J"
OLDER = "ver_01M2545JSD15ETSNNV904X991J"
NEWER = "ver_01M2545JSD15ETSNNV904X991K"


def row(pages: int) -> dict:
    return {"version_uid": OLDER, "version_document_uid": DOCUMENT, "set_document_uid": DOCUMENT,
            "project_uid": PROJECT, "version_ordinal": 1, "state": "published", "sha256": "a" * 64,
            "byte_size": 1, "page_count": pages, "media_type": "application/pdf"}


def facts(uid: str, ordinal: int, pages: int) -> VersionFacts:
    return VersionFacts(uid, DOCUMENT, PROJECT, ordinal, "a" * 64, 1, pages, "application/pdf")


def pair(source_pages: int, target_pages: int) -> OrderedVersionPair:
    return OrderedVersionPair(PROJECT, DOCUMENT, facts(OLDER, 1, source_pages), facts(NEWER, 2, target_pages))


def test_the_reader_admits_500_pages_and_refuses_501_before_any_table_is_touched() -> None:
    assert version_reader.MAX_VERSION_PAGES == 500
    assert _version_facts(row(500), project_uid=PROJECT, document_uid=DOCUMENT).page_count == 500
    with pytest.raises(VersionPairRefused, match="version_page_count_invalid"):
        _version_facts(row(501), project_uid=PROJECT, document_uid=DOCUMENT)


def test_the_two_re_checks_have_limits_of_their_own() -> None:
    assert (suggestions.MAX_SUGGESTED_PAGES, suggestions.MAX_SUGGESTED_SHEET_PAIRS) == (500, 500)
    assert seal.MAX_SEALED_PAGES == 500
    assert not hasattr(suggestions, "MAX_VERSION_PAGES") and not hasattr(seal, "MAX_VERSION_PAGES")


def test_the_re_checks_do_not_follow_the_readers_constant(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mutation: import ``MAX_VERSION_PAGES`` back into either module -- this test fails once it is lifted."""
    monkeypatch.setattr(version_reader, "MAX_VERSION_PAGES", 2**31 - 1)
    assert suggestions._check_versions(pair(500, 500))  # noqa: SLF001
    for source_pages, target_pages in ((501, 10), (10, 501)):
        with pytest.raises(suggestions.FindingMatchSuggestionRefused, match="version_pair_invalid"):
            suggestions._check_versions(pair(source_pages, target_pages))  # noqa: SLF001


def test_the_seal_does_not_follow_the_readers_constant_either(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(version_reader, "MAX_VERSION_PAGES", 2**31 - 1)
    for source_pages, target_pages in ((501, 10), (10, 501)):
        with pytest.raises(seal.RawEvidenceSealRefused, match="version_pair_invalid"):
            seal.seal_raw_version_evidence(
                version_pair=pair(source_pages, target_pages), comparison_id="cmp_01M2545JSD15ETSNNV904X991J",
                link_revision=1, raw_diffs=[object()])


def test_the_suggested_sheet_pairs_are_bounded_by_their_own_limit() -> None:
    too_many = [object()] * (suggestions.MAX_SUGGESTED_SHEET_PAIRS + 1)
    with pytest.raises(suggestions.FindingMatchSuggestionRefused, match="sheet_suggestions_invalid"):
        suggestions._suggested_links(too_many, source_pages=500, target_pages=500)  # noqa: SLF001
