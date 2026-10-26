"""`W60-OPT-PROPOSALS-01` phase A: starting optimisation passes on real PostgreSQL and MinIO.

A pass pins the current AR version, its newest published run and that run's text layer, the
current price-list revision and the effective AR vendor list, and stores immutable
cheaper-analog proposals whose prices come only from price-list positions and whose saving
exists only with a numeric quantity. Each precondition that fails is an explicit refusal
that leaves nothing behind; an exact repeat answers the stored pass.
"""

from __future__ import annotations

import threading
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.optimisation.project_match import RunCandidate
from auditmanager.optimisation.proposals.public import (
    GENERATOR_VERSION,
    PassStart,
    get_optimisation_pass,
    list_optimisation_passes,
    list_optimisation_proposals,
    start_optimisation_pass,
)
from auditmanager.shared.db.session import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DocumentUid, ProjectUid

from .conftest import (
    HOSTILE_VENDOR,
    LAYER_SHA256,
    NEWER_PRICE_LIST,
    PRICE_LIST,
    Reader,
    World,
    classify,
    global_vendors,
    project_vendors,
    published_reader,
    upload,
)

WRITTEN = (
    "optimisation_pass",
    "optimisation_proposal",
    "optimisation_proposal_decision",
    "command_record",
)
FINDINGS = ("finding", "finding_observation", "finding_evidence", "expert_decision_event")


def _counts(factory: sessionmaker[Session], tables: tuple[str, ...] = WRITTEN) -> dict[str, int]:
    with session_scope(factory) as session:
        return {
            table: int(session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one())
            for table in tables
        }


def _start(unit: Any, cast: Any, world: World, reader: Reader | None = None, **extra: Any) -> PassStart:
    arguments: dict[str, Any] = {
        "project_uid": world.project,
        "document_uid": world.document,
        "idempotency_key": "pass-1",
        "actor_uid": cast.expert,
        "reader": reader or published_reader(world),
    }
    arguments.update(extra)
    return unit(start_optimisation_pass, **arguments)


def _refused(code: ErrorCode, call: Any, *args: Any, **kwargs: Any) -> DomainError:
    with pytest.raises(DomainError) as caught:
        call(*args, **kwargs)
    assert caught.value.code is code, (caught.value.code, dict(caught.value.detail_fields))
    return caught.value


def _proposals(unit: Any, cast: Any, pass_id: str, **extra: Any):
    return unit(
        list_optimisation_proposals,
        optimisation_pass_id=pass_id,
        actor_roles=frozenset({"expert"}),
        limit=200,
        **extra,
    )


# -- the pass and its proposals ------------------------------------------------------------


def test_a_pass_pins_its_inputs_and_stores_cheaper_analogs(unit, factory, cast, ready) -> None:
    findings_before = _counts(factory, FINDINGS)
    started = _start(unit, cast, ready)
    assert (started.created, started.replayed) == (True, False)
    record = started.optimisation_pass
    assert (record.project_uid, record.document_uid, record.version_uid, record.run_id) == (
        ready.project, ready.document, ready.version, ready.run,
    )
    assert record.text_layer_sha256 == LAYER_SHA256
    assert record.vendor_list_source == "global"
    assert (record.extraction_algorithm, record.match_algorithm, record.generator_version) == (
        "specification-text-v1", "price-match-v1", GENERATOR_VERSION,
    )
    # Six rows; the profile is unit-mismatched and the foam ambiguous, so four are matched.
    assert (record.specification_row_count, record.matched_row_count) == (6, 4)
    assert (record.proposed_row_count, record.proposal_count) == (4, 4)
    assert dict(record.decision_counts) == {"pending": 4, "accept": 0, "reject": 0, "revise": 0}
    assert record.started_by_user_uid == cast.expert

    page = _proposals(unit, cast, record.optimisation_pass_id)
    door, window, anchor, tape = page.items
    assert [item.ordinal for item in page.items] == [1, 2, 3, 4]
    assert (door.row_text, door.page_number, door.row_position) == (
        "Дверь противопожарная ДПМ-01/60 EI60 ООО «Промет»", 1, "1",
    )
    assert door.spec_row_key.startswith("sr-") and door.line_start == door.line_end == 3
    assert (door.matched_position.mark, door.proposed_position.mark) == ("ДПМ-01/60", "ДПМ-02/60")
    assert (door.matched_basis, door.analog_basis) == ("mark", "code_family")
    assert (door.current_unit_price, door.proposed_unit_price, door.currency) == (
        Decimal("25000"), Decimal("21000"), "RUB",
    )
    assert (door.quantity, door.saving, door.proposed_vendor) == (Decimal("4"), Decimal("16000"), "Кнауф Гипс")
    assert window.proposed_position.name.endswith("эконом")
    assert window.saving == Decimal("30006.0")  # (18500.5 - 16000) x 12
    assert (anchor.currency, anchor.saving, anchor.proposed_vendor) == ("EUR", Decimal("650.00"), HOSTILE_VENDOR)
    # The tape's quantity is a dash: both prices are shown, the saving is absent -- not 0.
    assert (tape.quantity, tape.quantity_text, tape.saving) == (None, "-", None)
    assert tape.current_unit_price == Decimal("450") and tape.proposed_unit_price == Decimal("300")
    assert all(item.current_verdict == "pending" for item in page.items)
    # Findings are never read for writing or changed.
    assert _counts(factory, FINDINGS) == findings_before


def test_the_project_override_is_used_and_recorded(unit, cast, ready) -> None:
    override = project_vendors(unit, cast, "list", [{"vendor": "Кнауф Гипс"}])
    started = _start(unit, cast, ready)
    record = started.optimisation_pass
    assert (record.vendor_list_source, record.vendor_list_id) == ("project", override.vendor_list_id)
    vendors = {item.proposed_vendor for item in _proposals(unit, cast, record.optimisation_pass_id).items}
    assert vendors == {"Кнауф Гипс"} and record.proposal_count == 3

    inherited = project_vendors(unit, cast, "inherit")
    assert inherited is not None and inherited.mode == "inherit"
    again = _start(unit, cast, ready, idempotency_key="pass-2")
    assert again.created and again.optimisation_pass.vendor_list_source == "global"
    assert again.optimisation_pass.proposal_count == 4


def test_an_empty_vendor_list_is_a_pass_with_no_proposals(unit, cast, ready) -> None:
    project_vendors(unit, cast, "list", [])
    started = _start(unit, cast, ready)
    assert started.created and started.optimisation_pass.proposal_count == 0
    assert started.optimisation_pass.matched_row_count == 4
    assert started.optimisation_pass.proposed_row_count == 0


# -- refusals ------------------------------------------------------------------------------


def _refused_pass(unit, factory, cast, world, reason: str, reader: Reader | None = None) -> None:
    before = _counts(factory)
    error = _refused(ErrorCode.CONFLICT, _start, unit, cast, world, reader)
    assert error.detail_fields["conflict_reason"] == reason
    assert error.detail_fields["aggregate_type"] == "OptimisationPass"
    assert _counts(factory) == before  # not even the key's claim survives


def test_an_unclassified_version_is_refused(unit, factory, store, cast, world) -> None:
    upload(store, factory, cast, PRICE_LIST, "prices-1")
    global_vendors(unit, cast)
    _refused_pass(unit, factory, cast, world, "version_unclassified")


@pytest.mark.parametrize("section", ["PB", "OV", "KJ", "EOM"])
def test_a_version_of_another_section_takes_a_pass_with_that_sections_vendor_list(
    unit, factory, store, cast, world, section: str
) -> None:
    """Was ``section_not_ar``. The pass pins the vendor list of the version's own section; the
    database accepts it (migration ``0034``) and the proposals are the AR ones for the same inputs."""
    classify(unit, cast, world, section)
    upload(store, factory, cast, PRICE_LIST, "prices-1")
    vendor_list = global_vendors(unit, cast, section=section)
    started = _start(unit, cast, world)
    record = started.optimisation_pass
    assert (started.created, record.vendor_list_id, record.vendor_list_source) == (
        True, vendor_list.vendor_list_id, "global",
    )
    assert (record.specification_row_count, record.matched_row_count) == (6, 4)
    assert (record.proposed_row_count, record.proposal_count) == (4, 4)
    assert [item.proposed_vendor for item in _proposals(unit, cast, record.optimisation_pass_id).items] == [
        "Кнауф Гипс", "Кнауф Гипс", HOSTILE_VENDOR, "Кнауф Гипс",
    ]


def test_the_vendor_list_of_another_section_does_not_apply_to_the_versions_section(
    unit, factory, store, cast, world
) -> None:
    classify(unit, cast, world, "PB")
    upload(store, factory, cast, PRICE_LIST, "prices-1")
    global_vendors(unit, cast, section="AR")  # a list exists, but not for ПБ
    _refused_pass(unit, factory, cast, world, "vendor_list_missing")


def test_a_project_override_of_the_versions_section_is_the_list_used(
    unit, factory, store, cast, world
) -> None:
    classify(unit, cast, world, "PB")
    upload(store, factory, cast, PRICE_LIST, "prices-1")
    global_vendors(unit, cast, section="PB")
    override = project_vendors(unit, cast, "list", [{"vendor": "Кнауф Гипс"}], section="PB")
    project_vendors(unit, cast, "list", [{"vendor": "Промет"}], section="AR")  # another section's override
    record = _start(unit, cast, world).optimisation_pass
    assert (record.vendor_list_source, record.vendor_list_id) == ("project", override.vendor_list_id)
    assert record.proposal_count == 3


def test_no_price_list_is_refused(unit, factory, cast, world) -> None:
    classify(unit, cast, world)
    global_vendors(unit, cast)
    _refused_pass(unit, factory, cast, world, "price_list_missing")


def test_no_published_run_is_refused(unit, factory, cast, ready) -> None:
    failed_only = Reader(runs=(RunCandidate(ready.run, "failed"),))
    _refused_pass(unit, factory, cast, ready, "analysis_missing", failed_only)


def test_a_run_without_saved_text_is_refused(unit, factory, cast, ready) -> None:
    textless = Reader(runs=(RunCandidate(ready.run, "published"),), texts={ready.run: None})
    _refused_pass(unit, factory, cast, ready, "text_unavailable", textless)


def test_no_vendor_list_is_refused(unit, factory, store, cast, world) -> None:
    classify(unit, cast, world)
    upload(store, factory, cast, PRICE_LIST, "prices-1")
    global_vendors(unit, cast, section="KJ")  # another section's list does not apply
    _refused_pass(unit, factory, cast, world, "vendor_list_missing")


def test_an_inherit_override_without_a_global_list_is_refused(unit, factory, store, cast, world) -> None:
    classify(unit, cast, world)
    upload(store, factory, cast, PRICE_LIST, "prices-1")
    project_vendors(unit, cast, "list", [{"vendor": "Кнауф Гипс"}])
    project_vendors(unit, cast, "inherit")
    _refused_pass(unit, factory, cast, world, "vendor_list_missing")


def test_roles_scope_and_request_values(unit, factory, cast, ready) -> None:
    before = _counts(factory)
    for actor in (cast.admin, cast.nobody):
        denied = _refused(ErrorCode.PERMISSION_DENIED, _start, unit, cast, ready, actor_uid=actor)
        assert denied.detail_fields["required_capability"] == "role:expert"
    _refused(ErrorCode.NOT_FOUND, _start, unit, cast, ready, document_uid=ready.foreign_document)
    _refused(ErrorCode.NOT_FOUND, _start, unit, cast, ready, project_uid=str(ProjectUid.new()))
    _refused(ErrorCode.NOT_FOUND, _start, unit, cast, ready, document_uid=str(DocumentUid.new()))
    for field, value in (("project_uid", "prj_bad"), ("document_uid", "x"), ("idempotency_key", "")):
        refused = _refused(ErrorCode.VALIDATION_FAILED, _start, unit, cast, ready, **{field: value})
        assert refused.detail_fields["field"] == field
    assert _counts(factory) == before
    # An account holding both roles is an expert.
    assert _start(unit, cast, ready, actor_uid=cast.admin_expert).created


# -- idempotency ---------------------------------------------------------------------------


def test_the_same_key_and_payload_replays_and_another_payload_is_refused(unit, factory, cast, ready) -> None:
    first = _start(unit, cast, ready)
    after_first = _counts(factory)
    replay = _start(unit, cast, ready, reader=Reader())  # the reader is not asked again
    assert (replay.created, replay.replayed) == (False, True)
    assert replay.optimisation_pass == first.optimisation_pass
    assert _counts(factory) == after_first
    reused = _refused(
        ErrorCode.IDEMPOTENCY_KEY_REUSE, _start, unit, cast, ready, document_uid=ready.other_document
    )
    assert reused.detail_fields["command_type"] == "start_optimisation_pass"
    other_actor = _refused(ErrorCode.IDEMPOTENCY_KEY_REUSE, _start, unit, cast, ready,
                           actor_uid=cast.other_expert)
    assert other_actor.detail_fields["command_type"] == "start_optimisation_pass"


def test_an_exact_repeat_under_a_new_key_answers_the_stored_pass(unit, factory, cast, ready) -> None:
    first = _start(unit, cast, ready)
    before = _counts(factory)
    repeat = _start(unit, cast, ready, idempotency_key="pass-2", actor_uid=cast.other_expert)
    assert (repeat.created, repeat.replayed) == (False, False)
    assert repeat.optimisation_pass.optimisation_pass_id == first.optimisation_pass.optimisation_pass_id
    assert repeat.optimisation_pass.started_by_user_uid == cast.expert  # the stored pass, as stored
    after = _counts(factory)
    assert after["optimisation_pass"] == before["optimisation_pass"]
    assert after["optimisation_proposal"] == before["optimisation_proposal"]
    assert after["command_record"] == before["command_record"] + 1  # the new key answers it


def test_a_new_price_list_revision_is_a_new_pass(unit, store, factory, cast, ready) -> None:
    first = _start(unit, cast, ready)
    upload(store, factory, cast, NEWER_PRICE_LIST, "prices-2")
    second = _start(unit, cast, ready, idempotency_key="pass-2")
    assert second.created
    assert second.optimisation_pass.price_list_id != first.optimisation_pass.price_list_id
    door = _proposals(unit, cast, second.optimisation_pass.optimisation_pass_id).items[0]
    assert (door.proposed_unit_price, door.saving) == (Decimal("20000"), Decimal("20000"))
    # The earlier pass and its proposals are unchanged and still readable.
    old_door = _proposals(unit, cast, first.optimisation_pass.optimisation_pass_id).items[0]
    assert (old_door.proposed_unit_price, old_door.saving) == (Decimal("21000"), Decimal("16000"))


def test_concurrent_starts_of_the_same_inputs_write_one_pass(unit, factory, cast, ready) -> None:
    results: list[Any] = []
    barrier = threading.Barrier(3)

    def start(key: str) -> None:
        barrier.wait()
        try:
            results.append(_start(unit, cast, ready, idempotency_key=key))
        except Exception as exc:  # noqa: BLE001 - recorded and asserted below
            results.append(exc)

    threads = [threading.Thread(target=start, args=(f"pass-{n}",)) for n in range(3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    assert all(isinstance(result, PassStart) for result in results), results
    assert len({result.optimisation_pass.optimisation_pass_id for result in results}) == 1
    assert sorted(result.created for result in results) == [False, False, True]
    assert _counts(factory)["optimisation_pass"] == 1


# -- reads ---------------------------------------------------------------------------------


def test_passes_are_listed_newest_first_per_project_and_document(unit, store, factory, cast, ready) -> None:
    first = _start(unit, cast, ready).optimisation_pass
    classify(unit, cast, ready, document=ready.other_document, version=ready.other_version)
    other = _start(unit, cast, ready, document_uid=ready.other_document, idempotency_key="pass-2")
    listed = unit(list_optimisation_passes, project_uid=ready.project, actor_roles=frozenset({"admin"}))
    assert [record.optimisation_pass_id for record in listed] == [
        other.optimisation_pass.optimisation_pass_id, first.optimisation_pass_id,
    ]
    only = unit(list_optimisation_passes, project_uid=ready.project, document_uid=ready.document,
                actor_roles=frozenset({"expert"}))
    assert [record.optimisation_pass_id for record in only] == [first.optimisation_pass_id]
    assert unit(list_optimisation_passes, project_uid=cast.other_project,
                actor_roles=frozenset({"expert"})) == ()
    _refused(ErrorCode.NOT_FOUND, unit, list_optimisation_passes, project_uid=ready.project,
             document_uid=ready.foreign_document, actor_roles=frozenset({"expert"}))
    _refused(ErrorCode.PERMISSION_DENIED, unit, list_optimisation_passes, project_uid=ready.project,
             actor_roles=frozenset())
    _refused(ErrorCode.VALIDATION_FAILED, unit, list_optimisation_passes, project_uid=ready.project,
             actor_roles=frozenset({"expert"}), limit=101)
    stored = unit(get_optimisation_pass, optimisation_pass_id=first.optimisation_pass_id,
                  actor_roles=frozenset({"admin"}))
    assert stored == first
    _refused(ErrorCode.NOT_FOUND, unit, get_optimisation_pass,
             optimisation_pass_id="opp_01M2545JSD15ETSNNV904XA001", actor_roles=frozenset({"admin"}))
    _refused(ErrorCode.VALIDATION_FAILED, unit, get_optimisation_pass,
             optimisation_pass_id="opr_01M2545JSD15ETSNNV904XA001", actor_roles=frozenset({"admin"}))


def test_proposals_are_paged_while_counts_cover_every_proposal(unit, cast, ready) -> None:
    pass_id = _start(unit, cast, ready).optimisation_pass.optimisation_pass_id
    first = unit(list_optimisation_proposals, optimisation_pass_id=pass_id,
                 actor_roles=frozenset({"admin"}), offset=0, limit=3)
    last = unit(list_optimisation_proposals, optimisation_pass_id=pass_id,
                actor_roles=frozenset({"admin"}), offset=3, limit=3)
    assert (first.total, len(first.items), first.next_offset) == (4, 3, 3)
    assert (last.total, len(last.items), last.next_offset) == (4, 1, None)
    assert first.optimisation_pass.decision_counts == last.optimisation_pass.decision_counts
    for field, value in (("offset", -1), ("limit", 0), ("limit", 201), ("decision", "accepted")):
        refused = _refused(ErrorCode.VALIDATION_FAILED, unit, list_optimisation_proposals,
                           optimisation_pass_id=pass_id, actor_roles=frozenset({"admin"}),
                           **{field: value})
        assert refused.detail_fields["field"] == field
    _refused(ErrorCode.PERMISSION_DENIED, unit, list_optimisation_proposals,
             optimisation_pass_id=pass_id, actor_roles=frozenset())
