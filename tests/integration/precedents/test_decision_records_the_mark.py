"""`CRIT-CAPTURE-01` part D, on real PostgreSQL: a decision records what the server was showing when the expert decided.

The harness is the pass's own (``test_precedent_pass.py``): a published run, the cases of the memory with their vectors, the pass computed through the
window's import function and the services over one rolled-back transaction. What is added is the decision: ``record_decision`` through the ledger with the
composition root's capture port registered, exactly as ``build_application`` registers it, so the mark is read **in the transaction of the decision**.

Shown, each by the case that must come out the other way next to it:

* a ✕ taken while the section's refusal labels are off records ``few``; the next decision of the same finding, after the administrator turned the section
  on, records ``cancel_suggested`` and the pass revision it comes from, and the verdict of the document's history (P5) that the card showed;
* the second decision on the same observation is no conflict: the mark is decision metadata and the case's digest is untouched;
* a finding with no answer (no vector) records none: the three columns are NULL, which says «none was known»;
* a **carried** decision (the system's) and the **sweep's repair** of an earlier decision record none even when a mark is in force now -- the control asks
  ``shown_at_decision`` for it and gets one, so the NULL is the assembler's choice and not an absence of data;
* a capture error cancels the decision (``ADR-0027`` decision 4): a mark the table refuses propagates and no ledger event survives it.
"""

from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.bootstrap.adapters import MemoryCaptureAssembler, MemoryCaptureSweep
from auditmanager.decisions import record_decision
from auditmanager.decisions.public import register_decision_recorded, registered_decision_recorded
from auditmanager.precedents import public as precedents_public
from auditmanager.precedents.public import ShownAtDecision, shown_at_decision
from auditmanager.shared.errors import DomainError, ErrorCode
from tests.integration.precedents.test_precedent_pass import (  # noqa: F401  (stand and session are fixtures of that module)
    Run,
    Stand,
    ai,
    axis,
    give_vectors,
    review_of,
    seed_case,
    seed_refusals,
    seed_run,
    session,
    stand,
    turn_section_on,
    unit,
)


class _Geometry:
    def evidence_boxes_in(self, session: Session, run_id: str) -> dict[str, Any]:
        return {}

    def portal_crops_in(self, session: Session, run_id: str) -> tuple[dict[str, Any], ...]:
        return ()


@pytest.fixture
def capture() -> Iterator[SimpleNamespace]:
    """The capture port registered the way the composition root registers it (``register_decision_recorded(MemoryCaptureAssembler(...))``)."""
    before = registered_decision_recorded()
    assembler = MemoryCaptureAssembler(geometry=_Geometry())
    register_decision_recorded(assembler)
    try:
        yield SimpleNamespace(assembler=assembler)
    finally:
        register_decision_recorded(before)


def _observation(session: Session, finding_uid: str) -> str:
    return str(session.execute(text("SELECT canonical_observation_id FROM finding WHERE finding_uid = :f"), {"f": finding_uid}).scalar_one())


def _decide(session: Session, run: Run, event_type: str, *, position: int = 0, **extra: Any) -> Any:
    uid = run.findings[position]
    return record_decision(
        session, finding_uid=uid, finding_observation_id=_observation(session, uid), event_type=event_type,
        comment=None if extra.get("origin_kind") == "carried" else "по существу", author_label="Петрова А.", author_user_uid=None, **extra)


def _marks(session: Session, decision_id: str) -> tuple[Any, ...]:
    return tuple(session.execute(text(
        "SELECT precedent_label_at_decision, precedent_revision, precedent_history_verdict_shown FROM decision_memory_decision WHERE source_decision_id = :d"),
        {"d": decision_id}).one())


def _answered_run(stand: Stand, session: Session, *, texts: tuple[str, ...] = ("Находка про высоту этажа",), history: bool = False) -> Run:
    """A run whose first finding stands next to seven independent refusals (and, if asked, one in the same document, which is the history of P5)."""
    run = seed_run(session, list(texts))
    seed_refusals(session)
    if history:
        seed_case(session, verdict="rejected", vector=unit(0.95), days_ago=20, document=run.document_uid, comment="Показано на другом листе")
    stand.reviews[run.run_id] = review_of(run, critic=ai("reject"))
    stand.pass_.compute_run(run.run_id)
    give_vectors(session, run, {0: axis(0)})
    assert stand.pass_.compute_run(run.run_id).status == "computed"
    return run


def test_a_decision_records_the_mark_the_revision_and_the_history_verdict_that_were_shown(
    stand: Stand, session: Session, journalled_sessions: sessionmaker[Session], admin_uid: str, capture: SimpleNamespace,
) -> None:
    run = _answered_run(stand, session, history=True)
    # the section's refusal labels are off: the mark in force is ``few`` and no history verdict is shown with it
    first = _decide(session, run, "accept")
    assert _marks(session, first.decision_id) == ("few", 1, None), "the mark that WAS shown, with the revision of the pass it comes from"
    # the administrator turns the section on: the same finding now carries the refusal mark and the card shows the document's history
    turn_section_on(journalled_sessions, admin_uid)
    shown = shown_at_decision(session, run.findings[0])
    assert shown is not None and (shown.label, shown.history_verdict_shown) == ("cancel_suggested", "rejected"), "the control: the mark is in force now"
    second = _decide(session, run, "reject")
    assert _marks(session, second.decision_id) == ("cancel_suggested", 1, "rejected")
    # one case, two decisions, no conflict: the marks are decision metadata, the case's digest is the one it always was
    assert session.execute(text(
        "SELECT count(DISTINCT case_id) FROM decision_memory_decision WHERE source_decision_id IN (:a, :b)"), {"a": first.decision_id, "b": second.decision_id}
    ).scalar_one() == 1


def test_a_finding_with_no_answer_records_none_and_the_columns_stay_null(stand: Stand, session: Session, capture: SimpleNamespace) -> None:
    run = _answered_run(stand, session, texts=("Находка с ответом", "Находка без вектора"))
    answered, silent = _decide(session, run, "reject"), _decide(session, run, "reject", position=1)
    assert _marks(session, answered.decision_id)[:2] == ("few", 1)
    assert shown_at_decision(session, run.findings[1]) is None, "no vector, no answer"
    assert _marks(session, silent.decision_id) == (None, None, None), "«none was known» is NULL, never a made-up mark"


def test_a_carried_decision_and_the_sweeps_repair_record_none_though_a_mark_is_in_force_now(
    stand: Stand, session: Session, journalled_sessions: sessionmaker[Session],
) -> None:
    run = _answered_run(stand, session, texts=("Находка перенесённая", "Находка до памяти"))
    assert shown_at_decision(session, run.findings[0]) is not None and shown_at_decision(session, run.findings[1]) is None
    # (1) a carried decision: the system wrote it, no expert was shown anything
    before = registered_decision_recorded()
    register_decision_recorded(MemoryCaptureAssembler(geometry=_Geometry()))
    try:
        carried = _decide(session, run, "accept", origin_kind="carried")
    finally:
        register_decision_recorded(before)
    assert _marks(session, carried.decision_id) == (None, None, None)
    # (2) a decision recorded before there was a memory, repaired by the sweep: the mark in force NOW is not the one in force THEN
    register_decision_recorded(None)
    try:
        earlier = _decide(session, run, "reject")
    finally:
        register_decision_recorded(before)
    assert session.execute(text("SELECT count(*) FROM decision_memory_decision WHERE source_decision_id = :d"), {"d": earlier.decision_id}).scalar_one() == 0
    sweep = MemoryCaptureSweep(journalled_sessions, MemoryCaptureAssembler(geometry=_Geometry()), batch=5000, interval_seconds=0)
    assert sweep.run_once().captured >= 1
    assert _marks(session, earlier.decision_id) == (None, None, None), "the sweep stamps no mark on a decision it did not see taken"


def test_a_mark_the_table_refuses_is_a_capture_error_and_cancels_the_decision(
    stand: Stand, session: Session, monkeypatch: pytest.MonkeyPatch, capture: SimpleNamespace,
) -> None:
    run = _answered_run(stand, session)
    # a revision of 0 is the table's own refusal (``ck_decision_memory_decision_precedent_revision``) and the value object's before it
    monkeypatch.setattr(precedents_public, "shown_at_decision", lambda session, finding_uid, **kw: ShownAtDecision("few", 0, None))
    savepoint = session.begin_nested()
    with pytest.raises(DomainError) as refused:
        _decide(session, run, "reject")
    assert refused.value.code is ErrorCode.VALIDATION_FAILED, "the capture's refusal reaches the caller of ``record_decision``, which is the decision"
    savepoint.rollback()
    assert session.execute(text("SELECT count(*) FROM expert_decision_event WHERE finding_uid = :f"), {"f": run.findings[0]}).scalar_one() == 0, \
        "no ledger event survives a failed capture"
