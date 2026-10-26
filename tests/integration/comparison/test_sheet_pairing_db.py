"""Approved sheet pairings against PostgreSQL (`COMPARE-PERSISTED-SUMMARY-01`, B1).

The version half is real -- ``project``, ``document`` and ``document_version`` rows in a
rolled-back transaction, the command receipt (``command_record``), the append-only
``comparison_sheet_link`` history with its chain trigger, and the ``audit_event`` trail -- and
classifications, runs and page text come from port fakes, as in ``test_service_db.py``.

Needs a database migrated to ``0035_comparison_records`` or later (``make migrate``); the shared
lane database is not migrated by this lane, so the suite is run on a private database
(``DATABASE_URL`` pointing at it).
"""

from __future__ import annotations

import hashlib

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from auditmanager.comparison import audit as comparison_audit
from auditmanager.comparison.public import (
    EVIDENCE_NONE,
    EVIDENCE_SEALED,
    EVIDENCE_TEXT_CHANGED,
    LINK_TEXT_CHANGED,
    LINK_VERIFIED,
    ApproveSheetPairingRequest,
    ComparisonRequest,
    RunCandidate,
    SavedPageText,
    SheetLinkRepository,
    SheetPairingService,
    SuppliedVersionClassification,
    VersionComparisonService,
    WithdrawSheetPairingRequest,
)
from auditmanager.comparison.raw_text import ApprovedSheetPair as RawPair
from auditmanager.comparison.raw_text import diff_approved_pairs
from auditmanager.shared.errors import DomainError, ErrorCode

PROJECT = "prj_01M2545JSD15ETSNNV904XB001"
DOCUMENT = "doc_01M2545JSD15ETSNNV904XB001"
V1 = "ver_01M2545JSD15ETSNNV904XB001"
V2 = "ver_01M2545JSD15ETSNNV904XB002"
R1 = "run_01M2545JSD15ETSNNV904XB001"
R2 = "run_01M2545JSD15ETSNNV904XB002"
EXPERT = "usr_01M2545JSD15ETSNNV904XB001"
ADMIN = "usr_01M2545JSD15ETSNNV904XB002"
PAGES = 40
EXPERT_ROLES = frozenset({"expert"})


def _seed(session) -> None:
    session.execute(text("INSERT INTO project (project_uid, name) VALUES (:p, 'Сравнение')"),
                    {"p": PROJECT})
    session.execute(
        text("INSERT INTO document (document_uid, project_uid, display_title) "
             "VALUES (:d, :p, 'Комплект')"),
        {"d": DOCUMENT, "p": PROJECT},
    )
    for version, ordinal, digest in ((V1, 1, "a" * 64), (V2, 2, "b" * 64)):
        session.execute(
            text("INSERT INTO document_version (version_uid, document_uid, version_ordinal, "
                 "media_type, byte_size, sha256, page_count) "
                 "VALUES (:v, :d, :o, 'application/pdf', 4096, :s, :n)"),
            {"v": version, "d": DOCUMENT, "o": ordinal, "s": digest, "n": PAGES},
        )


def _page(number: int, revision: str) -> str:
    frame = "\n".join(f"Штамп строка {k}" for k in range(12))
    body = "\n".join(f"Лист {number} позиция {k} размер {k * 10}" for k in range(40))
    return f"{frame}\nЛист {number} изм. {revision}\n{body}\n"


def _pages(revision: str) -> dict[int, str]:
    return {n: _page(n, revision) for n in range(1, PAGES + 1)}


SOURCE_PAGES = _pages("1")
# Page 7 is redrawn in the newer set; every other sheet changes only its revision mark.
TARGET_PAGES = _pages("2") | {
    7: _page(7, "2").replace("позиция 3 размер 30", "позиция 3 размер 35"),
}


class _Classifications:
    def read_classification(self, session, *, version_uid):
        return SuppliedVersionClassification(version_uid, "R", "KJ")


class _Analyses:
    def __init__(self, source, target) -> None:
        self.source, self.target = source, target

    def runs_newest_first(self, session, *, version_uid):
        return {V1: (RunCandidate(R1, "published"),), V2: (RunCandidate(R2, "published"),)}.get(
            version_uid, (),
        )

    def saved_page_text(self, session, *, run_id, version):
        return SavedPageText(run_id, "e" * 64, {R1: self.source, R2: self.target}[run_id])

    def published_findings(self, session, *, run_id):
        return ()


def _world(source=None, target=None):
    links = SheetLinkRepository()
    comparisons = VersionComparisonService(
        classifications=_Classifications(),
        analyses=_Analyses(SOURCE_PAGES if source is None else source,
                           TARGET_PAGES if target is None else target),
        section_codes=frozenset({"AR", "KJ"}),
        links=links,
    )
    return comparisons, SheetPairingService(comparisons=comparisons, links=links)


def _request(**changes):
    return ComparisonRequest(**({
        "project_uid": PROJECT, "document_uid": DOCUMENT,
        "source_version_uid": V1, "target_version_uid": V2,
    } | changes))


def _proposal(session, comparisons, page: int) -> str:
    result = comparisons.compare(session, _request())
    return next(
        row.suggestion_sha256 for row in result.sheets
        if row.source_page_number == page and row.target_page_number == page
    )


def _approve(session, pairings, comparisons, page: int, *, key: str, roles=EXPERT_ROLES, **changes):
    values = {
        "project_uid": PROJECT, "document_uid": DOCUMENT,
        "source_version_uid": V1, "target_version_uid": V2,
        "source_page_number": page, "target_page_number": page,
        "suggestion_sha256": _proposal(session, comparisons, page),
    } | changes
    return pairings.approve(
        session, ApproveSheetPairingRequest(**values), actor_uid=EXPERT,
        actor_label="Иванов И. И.", actor_roles=roles, idempotency_key=key,
    )


def _withdraw(session, pairings, sheet_link_id: str, *, key: str, roles=EXPERT_ROLES):
    return pairings.withdraw(
        session,
        WithdrawSheetPairingRequest(
            project_uid=PROJECT, document_uid=DOCUMENT, source_version_uid=V1,
            sheet_link_id=sheet_link_id,
        ),
        actor_uid=EXPERT, actor_label="Иванов И. И.", actor_roles=roles, idempotency_key=key,
    )


def _rows(session) -> list[tuple]:
    return list(session.execute(text(
        "SELECT link_revision, event_kind, sheet_link_id, raw_evidence_seal_sha256 "
        "FROM comparison_sheet_link ORDER BY link_revision"
    )).all())


def _conflict_reason(error: DomainError) -> str:
    return str(error.detail_fields["conflict_reason"])


@pytest.fixture
def seeded(comparison_session):
    _seed(comparison_session)
    return comparison_session


def test_an_approval_is_stored_with_digests_actor_seal_and_an_audit_event(seeded) -> None:
    comparisons, pairings = _world()
    outcome = _approve(seeded, pairings, comparisons, 7, key="pairing-key-1")
    event = outcome.event
    assert outcome.replayed is False
    assert (event.link_revision, event.event_kind) == (1, "approved")
    assert event.comparison_id.startswith("cmp_") and event.sheet_link_id.startswith("sln_")
    assert (event.source_version_uid, event.target_version_uid) == (V1, V2)
    assert (event.source_page_number, event.target_page_number) == (7, 7)
    # Identity is by content: the digests of the two page texts the expert saw.
    assert event.source_page_text_sha256 == hashlib.sha256(SOURCE_PAGES[7].encode()).hexdigest()
    assert event.target_page_text_sha256 == hashlib.sha256(TARGET_PAGES[7].encode()).hexdigest()
    assert (event.actor_user_uid, event.actor_label) == (EXPERT, "Иванов И. И.")
    assert event.raw_evidence_seal_sha256 and len(event.raw_evidence_seal_sha256) == 64

    audit = seeded.execute(text(
        "SELECT event_type, aggregate_type, aggregate_id, payload FROM audit_event "
        "WHERE event_type LIKE 'comparison.%'"
    )).all()
    assert [(a[0], a[1], a[2]) for a in audit] == [
        ("comparison.sheet_link_approved", "Comparison", event.comparison_id),
    ]
    payload = audit[0][3]
    assert set(payload) == set(comparison_audit.PAYLOAD_KEYS[comparison_audit.EVENT_SHEET_LINK_APPROVED][0])
    assert payload["raw_evidence_seal_sha256"] == event.raw_evidence_seal_sha256
    assert "Иванов" not in str(payload) and "Лист" not in str(payload)


def test_the_read_serves_the_approved_pair_sealed_and_only_that_pair(seeded) -> None:
    comparisons, pairings = _world()
    outcome = _approve(seeded, pairings, comparisons, 7, key="pairing-key-2")
    result = comparisons.compare(seeded, _request())
    approved = result.approved_pairs
    assert approved is not None and approved.evidence_state == EVIDENCE_SEALED
    assert approved.link_revision == 1
    assert approved.raw_evidence_seal_sha256 == outcome.event.raw_evidence_seal_sha256
    (item,) = approved.items
    assert item.state == LINK_VERIFIED and item.sheet_link_id == outcome.event.sheet_link_id
    assert (item.source_page_number, item.target_page_number) == (7, 7)
    assert item.approved_by_label == "Иванов И. И."

    # The differences are exactly diff_approved_pairs' own, recomputed independently.
    (expected,) = diff_approved_pairs(
        comparison_id=outcome.event.comparison_id, source_version_uid=V1, target_version_uid=V2,
        link_revision=1,
        approved_pairs=[RawPair(outcome.event.comparison_id, outcome.event.sheet_link_id, 1,
                                V1, V2, 7, 7)],
        source_pages={7: SOURCE_PAGES[7]}, target_pages={7: TARGET_PAGES[7]},
    )
    assert item.diff is not None and item.diff.evidence_sha256 == expected.evidence_sha256
    changed = [h for h in item.diff.hunks if h.tag != "equal"]
    # Two changed spans: the revision mark and the redrawn size; ids count the non-equal spans.
    assert [h.hunk_id for h in changed] == [f"{item.sheet_link_id}:0", f"{item.sheet_link_id}:1"]
    assert all(h.hunk_id is None for h in item.diff.hunks if h.tag == "equal")
    assert changed[0].source_lines == ("Лист 7 изм. 1\n",)
    assert changed[0].target_lines == ("Лист 7 изм. 2\n",)
    assert changed[1].source_lines == ("Лист 7 позиция 3 размер 30\n",)
    assert changed[1].target_lines == ("Лист 7 позиция 3 размер 35\n",)
    # Every other proposed pair stays a proposal: it has no approved view.
    assert len(result.sheets) == PAGES


def test_before_any_approval_the_read_says_none(seeded) -> None:
    comparisons, _ = _world()
    approved = comparisons.compare(seeded, _request()).approved_pairs
    assert approved is not None
    assert (approved.link_revision, approved.evidence_state, approved.items) == (
        None, EVIDENCE_NONE, (),
    )


def test_a_page_whose_text_changed_is_text_changed_and_serves_no_difference(seeded) -> None:
    comparisons, pairings = _world()
    _approve(seeded, pairings, comparisons, 7, key="pairing-key-3")
    # The same pages, as page numbers, but the target page 7 now holds another text.
    redrawn = TARGET_PAGES | {7: TARGET_PAGES[7].replace("размер 35", "размер 36")}
    changed, _ = _world(target=redrawn)
    approved = changed.compare(seeded, _request()).approved_pairs
    assert approved.evidence_state == EVIDENCE_TEXT_CHANGED
    assert approved.raw_evidence_seal_sha256 is None
    (item,) = approved.items
    assert item.state == LINK_TEXT_CHANGED and item.diff is None


def test_only_a_proposed_pair_under_its_digest_is_approved(seeded) -> None:
    comparisons, pairings = _world()
    digest = _proposal(seeded, comparisons, 7)
    for changes in (
        {"suggestion_sha256": "0" * 64},                       # the digest was not the one shown
        {"suggestion_sha256": digest, "target_page_number": 8},  # other pages under that digest
    ):
        # The served adapter rolls the whole transaction back on a refusal; a savepoint does the same.
        with pytest.raises(DomainError) as refused, seeded.begin_nested():
            _approve(seeded, pairings, comparisons, 7, key="pairing-key-4", **changes)
        assert refused.value.code is ErrorCode.CONFLICT
        assert _conflict_reason(refused.value) == "sheet_pair_not_proposed"
    assert _rows(seeded) == []


def test_a_page_held_by_an_active_link_cannot_be_paired_again(seeded) -> None:
    comparisons, pairings = _world()
    held = _approve(seeded, pairings, comparisons, 7, key="pairing-key-5").event
    # The exact pair again is an exact repeat, not a second link.
    again = _approve(seeded, pairings, comparisons, 7, key="pairing-key-6")
    assert again.replayed is True and again.event.sheet_link_id == held.sheet_link_id
    assert len(_rows(seeded)) == 1

    # The newer set swaps the texts of its pages 7 and 8, so the comparison now proposes the
    # source's page 7 against the target's page 8: a pair that needs the source page the active
    # link holds.
    swapped = TARGET_PAGES | {7: TARGET_PAGES[8], 8: TARGET_PAGES[7]}
    moved, moved_pairings = _world(target=swapped)
    result = moved.compare(seeded, _request())
    proposal = next(r for r in result.sheets if r.source_page_number == 7)
    assert proposal.target_page_number == 8
    with pytest.raises(DomainError) as refused, seeded.begin_nested():
        moved_pairings.approve(
            seeded,
            ApproveSheetPairingRequest(
                project_uid=PROJECT, document_uid=DOCUMENT, source_version_uid=V1,
                target_version_uid=V2, source_page_number=7, target_page_number=8,
                suggestion_sha256=proposal.suggestion_sha256,
            ),
            actor_uid=EXPERT, actor_label="Иванов И. И.", actor_roles=EXPERT_ROLES,
            idempotency_key="pairing-key-6b",
        )
    assert _conflict_reason(refused.value) == "sheet_page_already_paired"
    assert len(_rows(seeded)) == 1


def test_the_thirty_third_active_link_is_refused(seeded) -> None:
    comparisons, pairings = _world()
    for page in range(1, 33):
        _approve(seeded, pairings, comparisons, page, key=f"pairing-limit-{page}")
    with pytest.raises(DomainError) as refused, seeded.begin_nested():
        _approve(seeded, pairings, comparisons, 33, key="pairing-limit-33")
    assert _conflict_reason(refused.value) == "sheet_pair_limit_reached"
    assert len(_rows(seeded)) == 32


def test_an_account_without_the_expert_role_approves_nothing(seeded) -> None:
    comparisons, pairings = _world()
    with pytest.raises(DomainError) as refused:
        _approve(seeded, pairings, comparisons, 7, key="pairing-key-7", roles=frozenset({"admin"}))
    assert refused.value.code is ErrorCode.PERMISSION_DENIED
    assert refused.value.detail_fields["required_capability"] == "role:expert"
    assert _rows(seeded) == []
    assert seeded.execute(text("SELECT count(*) FROM command_record")).scalar_one() == 0
    assert seeded.execute(text(
        "SELECT count(*) FROM audit_event WHERE event_type LIKE 'comparison.%'")).scalar_one() == 0


def test_a_withdrawal_is_a_new_row_and_the_approval_stays(seeded) -> None:
    comparisons, pairings = _world()
    first = _approve(seeded, pairings, comparisons, 7, key="pairing-key-8").event
    before = _rows(seeded)
    withdrawn = _withdraw(seeded, pairings, first.sheet_link_id, key="pairing-key-9")
    assert withdrawn.replayed is False
    assert (withdrawn.event.event_kind, withdrawn.event.link_revision) == ("withdrawn", 2)
    assert withdrawn.event.sheet_link_id == first.sheet_link_id
    assert withdrawn.event.raw_evidence_seal_sha256 is None  # nothing remains to seal
    after = _rows(seeded)
    assert after[:1] == before and len(after) == 2          # the approval row is untouched
    assert comparisons.compare(seeded, _request()).approved_pairs.evidence_state == EVIDENCE_NONE
    events = [row[0] for row in seeded.execute(text(
        "SELECT event_type FROM audit_event WHERE event_type LIKE 'comparison.%' "
        "ORDER BY sequence_no")).all()]
    assert events == ["comparison.sheet_link_approved", "comparison.sheet_link_withdrawn"]

    # A withdrawn link cannot be withdrawn again; approving the pages anew is a new link.
    with pytest.raises(DomainError) as refused, seeded.begin_nested():
        _withdraw(seeded, pairings, first.sheet_link_id, key="pairing-key-10")
    assert _conflict_reason(refused.value) == "sheet_link_not_active"
    renewed = _approve(seeded, pairings, comparisons, 7, key="pairing-key-11").event
    assert renewed.sheet_link_id != first.sheet_link_id and renewed.link_revision == 3
    assert renewed.comparison_id == first.comparison_id


def test_a_link_of_another_path_is_not_found(seeded) -> None:
    comparisons, pairings = _world()
    with pytest.raises(DomainError) as refused, seeded.begin_nested():
        _withdraw(seeded, pairings, "sln_01M2545JSD15ETSNNV904XB777", key="pairing-key-12")
    assert refused.value.code is ErrorCode.NOT_FOUND
    assert _rows(seeded) == []


def test_a_withdrawal_leaves_the_remaining_set_sealed(seeded) -> None:
    comparisons, pairings = _world()
    keep = _approve(seeded, pairings, comparisons, 7, key="pairing-key-13").event
    drop = _approve(seeded, pairings, comparisons, 8, key="pairing-key-14").event
    withdrawn = _withdraw(seeded, pairings, drop.sheet_link_id, key="pairing-key-15").event
    assert withdrawn.raw_evidence_seal_sha256 is not None
    approved = comparisons.compare(seeded, _request()).approved_pairs
    assert approved.evidence_state == EVIDENCE_SEALED and approved.link_revision == 3
    assert [i.sheet_link_id for i in approved.items] == [keep.sheet_link_id]
    assert approved.raw_evidence_seal_sha256 == withdrawn.raw_evidence_seal_sha256


def test_the_same_key_replays_and_another_payload_under_it_is_refused(seeded) -> None:
    comparisons, pairings = _world()
    first = _approve(seeded, pairings, comparisons, 7, key="pairing-key-16")
    again = _approve(seeded, pairings, comparisons, 7, key="pairing-key-16")
    assert again.replayed is True and again.event == first.event
    other = _approve(seeded, pairings, comparisons, 7, key="pairing-key-17")
    assert other.replayed is True and other.event.sheet_link_id == first.event.sheet_link_id
    assert len(_rows(seeded)) == 1
    with pytest.raises(DomainError) as refused, seeded.begin_nested():
        _approve(seeded, pairings, comparisons, 8, key="pairing-key-16")
    assert refused.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE


def test_the_row_and_its_audit_event_commit_or_roll_back_together(seeded, monkeypatch) -> None:
    comparisons, pairings = _world()
    digest = _proposal(seeded, comparisons, 7)

    def broken(*args, **kwargs):
        raise RuntimeError("the audit trail is unavailable")

    monkeypatch.setattr("auditmanager.comparison.pairing.record_sheet_link_approved", broken)
    with pytest.raises(RuntimeError):
        with seeded.begin_nested():
            _approve(seeded, pairings, comparisons, 7, key="pairing-key-18",
                     suggestion_sha256=digest)
    assert _rows(seeded) == []
    assert seeded.execute(text(
        "SELECT count(*) FROM command_record WHERE command_type = 'approve_sheet_pairing'"
    )).scalar_one() == 0


def test_the_database_refuses_to_update_or_delete_an_approval(seeded) -> None:
    comparisons, pairings = _world()
    _approve(seeded, pairings, comparisons, 7, key="pairing-key-19")
    for statement in (
        "UPDATE comparison_sheet_link SET actor_label = 'Другой'",
        "UPDATE comparison_sheet_link SET event_kind = 'withdrawn'",
        "DELETE FROM comparison_sheet_link",
    ):
        with pytest.raises(DBAPIError) as refused:
            with seeded.begin_nested():
                seeded.execute(text(statement))
        assert str(getattr(refused.value.orig, "sqlstate", "")) == "AM003", statement
    assert len(_rows(seeded)) == 1
