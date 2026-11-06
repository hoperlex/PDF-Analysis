"""`UI-B-14` (contract 1.37.0): carrying the decisions of an earlier version's pass over to a later one.

Real PostgreSQL and MinIO. The document set gets a second version, a newer price-list revision in which the door's analog is
cheaper, and a second pass; the first pass's decisions are carried into it. What the suite holds:

* a decision is matched by **content**, so a proposal whose positions were re-read from a newer revision (new identities)
  is still found, and one whose price changed is not;
* a carried decision is an ordinary appended event: authored by the confirming expert, the source's verdict and comment,
  ``carried_from`` naming the source decision, pass, version and ordinal; the source pass is untouched;
* a proposal an expert has touched is not overwritten, a repeat of the request carries nothing more, an exact repeat of the
  key answers the stored report, and a key is not reusable for another payload;
* the source must be a pass of the same document set over an earlier version; every refusal writes nothing.
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.optimisation.proposals.public import (
    carry_over_proposal_decisions,
    decide_optimisation_proposal,
    get_optimisation_pass,
    list_optimisation_proposals,
    list_proposal_decisions,
    start_optimisation_pass,
)
from auditmanager.documents.public import ManifestEntry
from auditmanager.optimisation.project_match import RunCandidate, SavedPageText
from auditmanager.shared.db.session import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DocumentUid
from auditmanager.storage import S3BlobStore, sha256_of
from auditmanager.storage.blob_repository import BlobMetadataRepository
from auditmanager.storage.models import VerifiedBlob, parse_blob_role

from .conftest import (
    LAYER_SHA256,
    NEWER_PRICE_LIST,
    PAGES,
    Reader,
    World,
    _run_row,
    classify,
    documents,
    published_reader,
    upload,
)


def _refused(code: ErrorCode, call: Any, *args: Any, **kwargs: Any) -> DomainError:
    with pytest.raises(DomainError) as caught:
        call(*args, **kwargs)
    assert caught.value.code is code, (caught.value.code, dict(caught.value.detail_fields))
    return caught.value


def _proposals(unit, pass_id: str) -> list[Any]:
    page = unit(
        list_optimisation_proposals,
        optimisation_pass_id=pass_id,
        actor_roles=frozenset({"expert"}),
        limit=200,
    )
    return list(page.items)


def _decide(unit, cast, proposal: str, verdict: str, key: str, comment: str | None = None, **extra):
    arguments: dict[str, Any] = {
        "proposal_id": proposal,
        "verdict": verdict,
        "comment": comment,
        "idempotency_key": key,
        "actor_uid": cast.expert,
    }
    arguments.update(extra)
    return unit(decide_optimisation_proposal, **arguments)


def _carry(unit, cast, target: str, source: str, key: str = "carry-1", **extra):
    arguments: dict[str, Any] = {
        "optimisation_pass_id": target,
        "source_optimisation_pass_id": source,
        "idempotency_key": key,
        "actor_uid": cast.other_expert,
    }
    arguments.update(extra)
    return unit(carry_over_proposal_decisions, **arguments)


def _counts(factory: sessionmaker[Session]) -> dict[str, int]:
    with session_scope(factory) as session:
        return {
            table: int(session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one())
            for table in ("optimisation_proposal_decision", "command_record")
        }


def _publish_second_version(session: Session, store: S3BlobStore, world: World) -> tuple[str, str]:
    """A second version of the document set, with its own run: the set's current version from now on."""
    payload = b"%PDF-1.7 synthetic version two of the first set"
    digest = sha256_of(payload)
    published = store.put_blob(
        payload,
        declared_sha256=digest,
        declared_size=len(payload),
        role=parse_blob_role("source_document"),
        media_type="application/pdf",
    )
    blobs = BlobMetadataRepository()
    blobs.record_verified(
        session,
        VerifiedBlob(
            blob_id=published.blob_id,
            upload_token="seeded-version-two",
            sha256=published.sha256,
            size=published.size,
            role=published.role,
            media_type=published.media_type,
        ),
    )
    blobs.mark_available(session, published.blob_id)
    version_uid = documents.publish_version(
        session,
        document_uid=DocumentUid.parse(world.document),
        media_type="application/pdf",
        byte_size=len(payload),
        sha256=digest,
        page_count=len(PAGES),
        source_filename=None,
        entries=(
            ManifestEntry(
                role="source_document",
                blob_id=published.blob_id,
                sha256=published.sha256,
                size_bytes=published.size,
                media_type=published.media_type,
            ),
        ),
    )
    run = _run_row(session, world.project, str(version_uid))
    session.commit()
    return str(version_uid), run


@pytest.fixture
def two_passes(unit, store, factory, session, cast, ready: World) -> dict[str, Any]:
    """Pass 1 over version 1 with four decisions' worth of proposals, pass 2 over version 2 over a newer price list."""
    first = unit(
        start_optimisation_pass,
        project_uid=ready.project,
        document_uid=ready.document,
        idempotency_key="pass-1",
        actor_uid=cast.expert,
        reader=published_reader(ready),
    ).optimisation_pass
    version_two, run_two = _publish_second_version(session, store, ready)
    classify(unit, cast, ready, version=version_two)
    upload(store, factory, cast, NEWER_PRICE_LIST, "prices-2")
    reader = Reader(
        by_version={
            ready.version: (RunCandidate(ready.run, "published"),),
            version_two: (RunCandidate(run_two, "published"),),
        },
        texts={
            ready.run: SavedPageText(ready.run, LAYER_SHA256, dict(PAGES)),
            run_two: SavedPageText(run_two, LAYER_SHA256, dict(PAGES)),
        },
    )
    second = unit(
        start_optimisation_pass,
        project_uid=ready.project,
        document_uid=ready.document,
        idempotency_key="pass-2",
        actor_uid=cast.expert,
        reader=reader,
    ).optimisation_pass
    assert second.version_uid == version_two and second.price_list_id != first.price_list_id
    return {
        "first": first,
        "second": second,
        "old": _proposals(unit, first.optimisation_pass_id),
        "new": _proposals(unit, second.optimisation_pass_id),
        "version_two": version_two,
    }


def _by_row(proposals: list[Any]) -> dict[str, Any]:
    """The proposals of a pass by what the specification row says, the first of each (a row may have several)."""
    named: dict[str, Any] = {}
    for proposal in proposals:
        named.setdefault(proposal.row_text.split()[0], proposal)
    return named


def test_decisions_are_carried_by_content_into_the_later_pass(unit, factory, cast, two_passes) -> None:
    old, new = _by_row(two_passes["old"]), _by_row(two_passes["new"])
    assert set(old) == set(new) and len(old) == 4  # the four rows of the specification: door, window, anchor, tape
    door, window, anchor, tape = (old[name] for name in ("Дверь", "Окно", "Анкер", "Монтажная"))
    _decide(unit, cast, door.optimisation_proposal_id, "accept", "d-1", "подходит")
    _decide(unit, cast, window.optimisation_proposal_id, "reject", "d-2", "хуже по теплотехнике")
    _decide(unit, cast, anchor.optimisation_proposal_id, "revise", "d-3", "уточнить поставщика")
    # `tape` stays undecided: nothing in force, nothing carried.
    first_id = two_passes["first"].optimisation_pass_id
    second_id = two_passes["second"].optimisation_pass_id
    before = unit(get_optimisation_pass, optimisation_pass_id=first_id, actor_roles=frozenset({"expert"}))

    report = _carry(unit, cast, second_id, first_id)
    # The door's analog costs 20000 now, not 21000: another proposal. The window and the anchor read as before.
    assert (report.carried, report.target_decided, report.ambiguous, report.unmatched) == (2, 0, 0, 1)
    assert report.source_decided == 3 and report.source_version_ordinal == 1
    assert (report.optimisation_pass_id, report.source_optimisation_pass_id) == (second_id, first_id)

    carried_window = new["Окно"]
    history = unit(
        list_proposal_decisions,
        optimisation_proposal_id=carried_window.optimisation_proposal_id,
        actor_roles=frozenset({"expert"}),
    )
    (decision,) = history
    assert (decision.verdict, decision.comment, decision.seq) == ("reject", "хуже по теплотехнике", 1)
    assert decision.actor_user_uid == cast.other_expert  # the confirming expert, not the source's author
    assert decision.carried_from is not None
    assert decision.carried_from.optimisation_pass_id == first_id
    assert decision.carried_from.version_uid == two_passes["first"].version_uid
    assert decision.carried_from.version_ordinal == 1
    source_history = unit(
        list_proposal_decisions,
        optimisation_proposal_id=window.optimisation_proposal_id,
        actor_roles=frozenset({"expert"}),
    )
    assert decision.carried_from.proposal_decision_id == source_history[0].proposal_decision_id
    assert source_history[0].carried_from is None  # a direct decision names no source

    after = _proposals(unit, second_id)
    states = {proposal.row_text.split()[0]: proposal for proposal in after}
    assert states["Окно"].current_verdict == "reject" and states["Окно"].current_decision.carried_from is not None
    assert states["Анкер"].current_verdict == "revise"
    assert states["Анкер"].current_decision.comment == "уточнить поставщика"  # a revise carries its required comment
    assert states["Дверь"].current_verdict == "pending" and states["Дверь"].current_decision is None
    assert states["Монтажная"].current_verdict == "pending"

    # The source pass is exactly as it was.
    assert unit(get_optimisation_pass, optimisation_pass_id=first_id, actor_roles=frozenset({"expert"})) == before
    counts = unit(get_optimisation_pass, optimisation_pass_id=second_id, actor_roles=frozenset({"expert"}))
    assert dict(counts.decision_counts)["reject"] == 1 and dict(counts.decision_counts)["revise"] == 1
    # The proposal list reads the same provenance as the history does.
    assert states["Окно"].current_decision.carried_from == decision.carried_from


def test_a_touched_target_stands_and_a_repeat_carries_nothing_more(unit, factory, cast, two_passes) -> None:
    old, new = _by_row(two_passes["old"]), _by_row(two_passes["new"])
    first_id, second_id = two_passes["first"].optimisation_pass_id, two_passes["second"].optimisation_pass_id
    _decide(unit, cast, old["Окно"].optimisation_proposal_id, "accept", "d-1")
    _decide(unit, cast, old["Анкер"].optimisation_proposal_id, "reject", "d-2", "дороже")
    # An expert already decided the new window (against the old decision) and withdrew an earlier decision on the anchor.
    _decide(unit, cast, new["Окно"].optimisation_proposal_id, "reject", "n-1", "на этой версии иначе")
    _decide(unit, cast, new["Анкер"].optimisation_proposal_id, "accept", "n-2")
    _decide(unit, cast, new["Анкер"].optimisation_proposal_id, "revoke", "n-3")

    report = _carry(unit, cast, second_id, first_id)
    assert (report.carried, report.target_decided, report.ambiguous, report.unmatched) == (0, 2, 0, 0)
    window = unit(
        list_proposal_decisions,
        optimisation_proposal_id=new["Окно"].optimisation_proposal_id,
        actor_roles=frozenset({"expert"}),
    )
    assert [(entry.verdict, entry.carried_from) for entry in window] == [("reject", None)]
    anchor = unit(
        list_proposal_decisions,
        optimisation_proposal_id=new["Анкер"].optimisation_proposal_id,
        actor_roles=frozenset({"expert"}),
    )
    assert [entry.verdict for entry in anchor] == ["accept", "revoke"]  # a withdrawal is not resurrected

    # The door and the tape are undecided in the source; deciding the door makes the next carryover find it unmatched.
    _decide(unit, cast, old["Дверь"].optimisation_proposal_id, "accept", "d-3")
    again = _carry(unit, cast, second_id, first_id, key="carry-2")
    assert (again.carried, again.target_decided, again.unmatched) == (0, 2, 1)


def test_a_key_replays_its_report_and_is_not_reusable_for_another_payload(unit, factory, cast, two_passes) -> None:
    old = _by_row(two_passes["old"])
    first_id, second_id = two_passes["first"].optimisation_pass_id, two_passes["second"].optimisation_pass_id
    _decide(unit, cast, old["Окно"].optimisation_proposal_id, "accept", "d-1")
    _decide(unit, cast, old["Монтажная"].optimisation_proposal_id, "reject", "d-2")
    report = _carry(unit, cast, second_id, first_id)
    assert report.carried == 2
    written = _counts(factory)

    replay = _carry(unit, cast, second_id, first_id)
    assert replay == report
    assert _counts(factory) == written  # nothing appended, nothing claimed

    # The same key for another caller, or for a pass that is not the stored one, is a different payload.
    for changed in ({"actor_uid": cast.expert}, {"source_optimisation_pass_id": second_id}):
        reused = _refused(ErrorCode.IDEMPOTENCY_KEY_REUSE, _carry, unit, cast, second_id, first_id, **changed)
        assert reused.detail_fields["command_type"] == "carry_over_proposal_decisions"
    assert _counts(factory) == written

    # A new key repeats the matching: both targets are decided now, and the report says so.
    fresh = _carry(unit, cast, second_id, first_id, key="carry-2")
    assert (fresh.carried, fresh.target_decided) == (0, 2) and _counts(factory)["optimisation_proposal_decision"] == written["optimisation_proposal_decision"]


def test_only_an_expert_carries_and_the_source_must_be_an_earlier_pass_of_the_same_set(
    unit, store, factory, cast, ready, two_passes
) -> None:
    first_id, second_id = two_passes["first"].optimisation_pass_id, two_passes["second"].optimisation_pass_id
    old = _by_row(two_passes["old"])
    _decide(unit, cast, old["Окно"].optimisation_proposal_id, "accept", "d-1")
    # A pass of another document set of the same project.
    classify(unit, cast, ready, document=ready.other_document, version=ready.other_version)
    other = unit(
        start_optimisation_pass,
        project_uid=ready.project,
        document_uid=ready.other_document,
        idempotency_key="pass-other",
        actor_uid=cast.expert,
        reader=published_reader(ready),
    ).optimisation_pass
    written = _counts(factory)

    for actor in (cast.admin, cast.nobody):
        denied = _refused(ErrorCode.PERMISSION_DENIED, _carry, unit, cast, second_id, first_id, actor_uid=actor)
        assert denied.detail_fields["required_capability"] == "role:expert"
        assert denied.detail_fields["aggregate_type"] == "OptimisationPass"

    unknown = "opp_01M2545JSD15ETSNNV904XA001"
    reasons = {
        "unknown": _refused(ErrorCode.CONFLICT, _carry, unit, cast, second_id, unknown),
        "itself": _refused(ErrorCode.CONFLICT, _carry, unit, cast, second_id, second_id),
        # The later pass is not an earlier version's: the direction matters.
        "later": _refused(ErrorCode.CONFLICT, _carry, unit, cast, first_id, second_id),
        "other set": _refused(ErrorCode.CONFLICT, _carry, unit, cast, second_id, other.optimisation_pass_id),
    }
    assert {name: error.detail_fields["conflict_reason"] for name, error in reasons.items()} == {
        "unknown": "carryover_source_unknown",
        "itself": "carryover_source_is_target",
        "later": "carryover_source_not_earlier",
        "other set": "carryover_source_other_document",
    }
    missing = _refused(ErrorCode.NOT_FOUND, _carry, unit, cast, unknown, first_id)
    assert missing.detail_fields["aggregate_type"] == "OptimisationPass"
    for field, arguments in (
        ("optimisation_pass_id", {"optimisation_pass_id": "prj_01M2545JSD15ETSNNV904XA001"}),
        ("source_optimisation_pass_id", {"source_optimisation_pass_id": "not-a-pass"}),
        ("idempotency_key", {"idempotency_key": ""}),
    ):
        invalid = _refused(ErrorCode.VALIDATION_FAILED, _carry, unit, cast, second_id, first_id, **arguments)
        assert invalid.detail_fields["field"] == field
    # Every refusal wrote nothing: no decision, and no claimed key either.
    assert _counts(factory) == written


def test_the_shipped_adapter_answers_the_frozen_shapes(unit, factory, cast, two_passes) -> None:
    """The wire models: the report as the contract names it, and ``carried_from`` on a decision, on the history and on
    the proposal list, ``null`` for a decision made directly."""
    import json
    from pathlib import Path

    from auditmanager.bootstrap.adapters import OptimisationProposalAdapter

    contract = json.loads(Path("contracts/api/v1/openapi.json").read_text(encoding="utf-8"))["components"]["schemas"]
    old, new = _by_row(two_passes["old"]), _by_row(two_passes["new"])
    first_id, second_id = two_passes["first"].optimisation_pass_id, two_passes["second"].optimisation_pass_id
    _decide(unit, cast, old["Окно"].optimisation_proposal_id, "accept", "d-1", "ok")
    adapter = OptimisationProposalAdapter(factory, blob_store=None)

    report = adapter.carry_over_proposal_decisions(
        optimisation_pass_id=second_id, source_optimisation_pass_id=first_id, idempotency_key="carry-http",
        user_uid=cast.other_expert,
    )
    body = report.model_dump(mode="json")
    assert set(body) == set(contract["ProposalDecisionCarryoverReport"]["properties"])
    assert body == {
        "optimisation_pass_id": second_id, "source_optimisation_pass_id": first_id, "source_version_ordinal": 1,
        "source_decided": 1, "carried": 1, "target_decided": 0, "ambiguous": 0, "unmatched": 0,
    }
    carried = adapter.list_proposal_decisions(
        optimisation_proposal_id=new["Окно"].optimisation_proposal_id, user_uid=cast.expert
    ).items[0].model_dump(mode="json")
    assert set(carried) == set(contract["ProposalDecision"]["properties"])
    assert set(carried["carried_from"]) == set(contract["ProposalDecisionCarriedFrom"]["properties"])
    assert carried["carried_from"]["optimisation_pass_id"] == first_id and carried["carried_from"]["version_ordinal"] == 1
    direct = adapter.list_proposal_decisions(
        optimisation_proposal_id=old["Окно"].optimisation_proposal_id, user_uid=cast.expert
    ).items[0].model_dump(mode="json")
    assert direct["carried_from"] is None
    # The proposal list carries the same provenance, and the pass says which version it was started over.
    page = adapter.list_optimisation_proposals(
        optimisation_pass_id=second_id, decision=None, offset=0, limit=50, user_uid=cast.expert
    ).model_dump(mode="json")
    assert page["optimisation_pass"]["version_ordinal"] == 2
    assert set(page["optimisation_pass"]) == set(contract["OptimisationPass"]["properties"])
    window = next(item for item in page["items"] if item["row_text"].startswith("Окно"))
    assert window["current_decision"]["carried_from"] == carried["carried_from"]


def test_a_carried_decision_is_written_only_into_a_proposal_that_has_no_event(unit, factory, cast, two_passes) -> None:
    """The insert itself: ``ON CONFLICT DO NOTHING`` on ``(proposal, seq)`` leaves an event that got there first alone, so
    a concurrent ordinary decision is never overwritten and no lock per proposal is needed; and the foreign key refuses a
    source that names no decision."""
    from sqlalchemy.exc import IntegrityError

    from auditmanager.ingest.public import CommandRepository, payload_fingerprint
    from auditmanager.optimisation.proposals.identity import ProposalDecisionId
    from auditmanager.optimisation.proposals.repository import ProposalRepository
    from auditmanager.shared.identity import IdempotencyKey

    old, new = _by_row(two_passes["old"]), _by_row(two_passes["new"])
    source = _decide(unit, cast, old["Окно"].optimisation_proposal_id, "accept", "d-1").decision
    free = new["Окно"].optimisation_proposal_id
    touched = new["Анкер"].optimisation_proposal_id
    _decide(unit, cast, touched, "reject", "n-1", "уже решено")

    def attempt(session: Session, proposal: str, tag: str, carried_from: str) -> Any:
        claim = CommandRepository().begin(
            session,
            command_type="carry_over_proposal_decision",
            idempotency_key=IdempotencyKey(f"cry-race-{tag}-0123456789"),
            fingerprint=payload_fingerprint({"command": "race", "tag": tag}),
        )
        return ProposalRepository().insert_carried_decision(
            session,
            decision_id=ProposalDecisionId.new(),
            proposal_id=proposal,
            verdict="accept",
            comment=None,
            actor_user_uid=cast.expert,
            command_id=str(claim.command_id),
            carried_from_decision_id=carried_from,
        )

    with session_scope(factory) as session:
        written = attempt(session, free, "a", source.proposal_decision_id)
        assert written is not None and written.seq == 1
        assert written.carried_from is not None and written.carried_from.proposal_decision_id == source.proposal_decision_id
        assert attempt(session, free, "b", source.proposal_decision_id) is None  # seq 1 is taken
        assert attempt(session, touched, "c", source.proposal_decision_id) is None  # a direct decision got there first
    histories = {
        proposal: unit(list_proposal_decisions, optimisation_proposal_id=proposal, actor_roles=frozenset({"expert"}))
        for proposal in (free, touched)
    }
    assert [(entry.verdict, entry.carried_from is not None) for entry in histories[free]] == [("accept", True)]
    assert [(entry.verdict, entry.comment, entry.carried_from) for entry in histories[touched]] == [
        ("reject", "уже решено", None)
    ]
    with pytest.raises(IntegrityError) as refused:
        with session_scope(factory) as session:
            attempt(session, new["Монтажная"].optimisation_proposal_id, "d", "opd_01M2545JSD15ETSNNV904XA001")
    assert "fk_optimisation_proposal_decision_carried_from" in str(refused.value)
