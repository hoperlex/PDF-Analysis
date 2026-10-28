"""`COMPARE-PERSISTED-SUMMARY-01`: what the read says about the approved pairs, without a database.

The stored history (``LinkState``) is supplied directly; the texts are the immutable pages of two
versions. Every state of ``evidence_state`` and of a link is shown, and the one guard that matters
most -- a page whose text changed serves no difference -- is shown against the digest, not against
the page number.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from auditmanager.comparison import approved_evidence as evidence
from auditmanager.comparison.sheet_links import KIND_APPROVED, KIND_WITHDRAWN, LinkEvent, LinkState
from auditmanager.comparison.version_reader import OrderedVersionPair, VersionFacts

PROJECT = "prj_01M2545JSD15ETSNNV904XC001"
DOCUMENT = "doc_01M2545JSD15ETSNNV904XC001"
V1 = "ver_01M2545JSD15ETSNNV904XC001"
V2 = "ver_01M2545JSD15ETSNNV904XC002"
CMP = "cmp_01M2545JSD15ETSNNV904XC001"
LINK = "sln_01M2545JSD15ETSNNV904XC001"
LINK_B = "sln_01M2545JSD15ETSNNV904XC002"
USER = "usr_01M2545JSD15ETSNNV904XC001"
CMD = "cmd_01M2545JSD15ETSNNV904XC001"
NOW = datetime(2026, 10, 27, tzinfo=timezone.utc)

SOURCE = {1: "общие данные\nлист 1\n", 2: "план\nразмер 30\n", 3: "разрез\n"}
TARGET = {1: "общие данные\nлист 1\n", 2: "план\nразмер 35\n", 3: "разрез\n"}


def _pair() -> OrderedVersionPair:
    def facts(uid: str, ordinal: int, sha: str) -> VersionFacts:
        return VersionFacts(uid, DOCUMENT, PROJECT, ordinal, sha, 4096, 3, "application/pdf")

    return OrderedVersionPair(PROJECT, DOCUMENT, facts(V1, 1, "a" * 64), facts(V2, 2, "b" * 64))


def _event(revision, kind, link=LINK, source=2, target=2, seal=None, source_pages=SOURCE,
           target_pages=TARGET) -> LinkEvent:
    return LinkEvent(
        CMP, revision, kind, link, PROJECT, DOCUMENT, V1, V2, source, target,
        evidence.page_text_sha256(source_pages[source]),
        evidence.page_text_sha256(target_pages[target]),
        "c" * 64, seal, USER, "Иванов И.", CMD, NOW,
    )


def _sealed_state(links=((LINK, 2, 2),)) -> LinkState:
    pair = _pair()
    revision = len(links)
    _, seal = evidence.raw_artifact(
        pair=pair, comparison_id=CMP, link_revision=revision, links=list(links),
        source_pages=SOURCE, target_pages=TARGET,
    )
    events = tuple(
        _event(n, KIND_APPROVED, link, s, t, seal.seal_sha256 if n == revision else "d" * 64)
        for n, (link, s, t) in enumerate(links, start=1)
    )
    return LinkState(events)


def _project(state, source=SOURCE, target=TARGET):
    return evidence.project_approved_pairs(
        pair=_pair(), state=state, source_pages=source, target_pages=target,
    )


def test_no_active_link_is_none() -> None:
    assert _project(LinkState(())).evidence_state == "none"
    approved = _event(1, KIND_APPROVED, seal="d" * 64)
    withdrawn = _event(2, KIND_WITHDRAWN)
    state = LinkState((approved, withdrawn))
    result = _project(state)
    assert (result.evidence_state, result.items, result.link_revision) == ("none", (), 2)


def test_a_verified_set_is_sealed_with_the_recomputed_seal_and_its_hunks() -> None:
    state = _sealed_state()
    result = _project(state)
    assert result.evidence_state == "sealed"
    assert result.raw_evidence_seal_sha256 == state.latest_seal_sha256
    (item,) = result.items
    assert item.state == "verified" and item.diff is not None
    assert [h.hunk_id for h in item.diff.hunks if h.tag != "equal"] == [f"{LINK}:0"]
    assert (item.diff.added_line_count, item.diff.removed_line_count) == (1, 1)


def test_a_changed_digest_withholds_every_difference_whatever_the_page_number() -> None:
    state = _sealed_state()
    edited = TARGET | {2: "план\nразмер 36\n"}   # page 2 is still page 2; its text is not
    result = _project(state, target=edited)
    assert result.evidence_state == "text_changed"
    assert result.raw_evidence_seal_sha256 is None
    (item,) = result.items
    assert item.state == "text_changed" and item.diff is None


def test_a_stored_seal_that_the_recomputation_does_not_reproduce_is_seal_changed() -> None:
    sealed = _sealed_state()
    forged = LinkState((_event(1, KIND_APPROVED, seal="e" * 64),))
    assert _project(sealed).evidence_state == "sealed"
    result = _project(forged)
    assert result.evidence_state == "seal_changed" and result.raw_evidence_seal_sha256 is None
    assert result.items[0].state == "verified" and result.items[0].diff is None


def test_a_set_beyond_the_response_budget_is_too_large_and_is_not_truncated(monkeypatch) -> None:
    monkeypatch.setattr(evidence, "MAX_APPROVED_CHANGED_CHARACTERS", 5)
    result = _project(_sealed_state())
    assert result.evidence_state == "too_large"
    assert all(item.diff is None for item in result.items)


def test_two_links_are_ordered_by_source_page_and_share_one_seal() -> None:
    state = _sealed_state(((LINK, 2, 2), (LINK_B, 3, 3)))
    result = _project(state)
    assert result.evidence_state == "sealed"
    assert [i.source_page_number for i in result.items] == [2, 3]
    assert result.link_revision == 2


@pytest.mark.parametrize("revision", [0, -1, True, "1"])
def test_the_raw_modules_refuse_a_bad_revision(revision) -> None:
    with pytest.raises(evidence.ApprovedEvidenceRefused):
        evidence.raw_artifact(
            pair=_pair(), comparison_id=CMP, link_revision=revision,
            links=[(LINK, 2, 2)], source_pages=SOURCE, target_pages=TARGET,
        )


def test_an_unknown_page_is_refused_not_invented() -> None:
    with pytest.raises(evidence.ApprovedEvidenceRefused):
        evidence.raw_artifact(
            pair=_pair(), comparison_id=CMP, link_revision=1,
            links=[(LINK, 9, 9)], source_pages=SOURCE, target_pages=TARGET,
        )
