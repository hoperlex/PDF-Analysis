"""Part B over PostgreSQL (`CMP-VC-SPEC-01`): the whole specification of each version is read by a model once, checked by the program,
stored under its content key and never re-requested, and the two versions of a transition are compared order-independently.

The model is ``ask``: a function the test supplies (recorded mode: no provider is called). The oracle is the answer key of the synthetic
corpus -- V4 to V5, the specification sheet: position 7 added, position 6 removed, the quantity of position 3 from 2 to 3 -- read from the
real page profiles of the corpus by the real parser.
"""

from __future__ import annotations

import copy
from typing import Any

import pytest
from sqlalchemy import text

from auditmanager.comparison.public import SpecificationService, TransitionRun
from auditmanager.comparison.specification import transition as transition_module
from auditmanager.comparison.specification.repository import SpecificationRepository
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode

from .conftest import faithful_answer


class Model:
    """A scripted model: answers a prompt with the faithful answer for the packet inside it, and counts the requests."""

    def __init__(self, edit: Any = None) -> None:
        self.prompts: list[str] = []
        self.edit = edit

    def __call__(self, prompt_text: str) -> transition_module.Answer:
        import json

        self.prompts.append(prompt_text)
        packet = json.loads(prompt_text.split("Входные данные (JSON):\n", 1)[1])
        answer = faithful_answer(packet)
        if self.edit is not None:
            answer = self.edit(copy.deepcopy(answer), len(self.prompts))
        return transition_module.Answer(payload=answer, model_identity="recorded", recorded=True)


@pytest.fixture
def run(sessions, blob_store) -> TransitionRun:
    return TransitionRun(sessions, blob_store)


@pytest.fixture
def service(sessions, blob_store) -> SpecificationService:
    return SpecificationService(sessions, blob_store)


@pytest.fixture
def transition(lab, started, sessions):
    """The transition V4 -> V5 of a fresh document set, its scope and an open ``whole`` row with its job."""
    doc, series = started()
    repository = SpecificationRepository()
    with session_scope(sessions) as session:
        scope = repository.transition(session, next(t["transition_id"] for t in series["transitions"] if t["source_version_uid"] == doc.versions[1]))
    return doc, series, scope


def _open(sessions, job_for, scope) -> str:
    job = job_for(scope)
    repository = SpecificationRepository()
    with session_scope(sessions) as session:
        repository.open_whole(session, scope, job_id=job, sheets_a=1, sheets_b=1)
        assert repository.set_state(session, scope.transition_id, to_state="running", from_states=("queued",), phase="comparing")
    return job


def test_the_key_transition_is_compared_whole_and_the_changes_are_those_of_the_key(sessions, job_for, transition, run, service) -> None:
    _doc, _series, scope = transition
    _open(sessions, job_for, scope)
    model = Model()
    outcome = run.run(scope, ask=model)
    assert outcome.state == "completed" and outcome.reason is None and len(model.prompts) == 2
    assert outcome.totals == {"changed": 1, "removed": 1, "added": 1, "unclear": 0, "renumbered": 0, "moved": 0}
    assert [c["kind"] for c in outcome.changes] == ["changed", "removed", "added"]
    assert outcome.changes[0]["fields"] == [{"field": "quantity", "was": "2", "now": "3"}]
    assert outcome.coverage_a == {"blocks_total": 1, "blocks_covered": 1, "rows_total": 6, "rows_unresolved": 0}

    view = service.get_specification(transition_id=scope.transition_id)
    assert view["state"] == "completed" and view["method"] == "whole" and view["totals"]["changed"] == 1
    assert view["extraction_a_id"].startswith("cse_") and view["extraction_b_id"].startswith("cse_") and view["comparison_id"].startswith("cscp_")
    changes, nxt = service.list_changes(transition_id=scope.transition_id, kind=None, offset=0, limit=2)
    assert [c["kind"] for c in changes] == ["changed", "removed"] and nxt == 2
    rest, nxt = service.list_changes(transition_id=scope.transition_id, kind=None, offset=nxt, limit=2)
    assert [c["kind"] for c in rest] == ["added"] and nxt is None
    only, _ = service.list_changes(transition_id=scope.transition_id, kind="removed", offset=0, limit=10)
    assert [c["old"]["pos"] for c in only] == ["6"]


def test_a_stored_extraction_is_never_requested_again(sessions, job_for, transition, run) -> None:
    """The mutation proof of the rule: with the store lookup removed, the second run sends two more requests."""
    _doc, _series, scope = transition
    _open(sessions, job_for, scope)
    first = Model()
    run.run(scope, ask=first)
    assert len(first.prompts) == 2
    repository = SpecificationRepository()
    with session_scope(sessions) as session:  # a re-run: the terminal row goes back to queued, then running
        repository.open_whole(session, scope, job_id=_job_of(session, scope), sheets_a=1, sheets_b=1)
        repository.set_state(session, scope.transition_id, to_state="running", from_states=("queued",), phase="comparing")
    second = Model()
    again = run.run(scope, ask=second)
    assert second.prompts == [] and again.state == "completed" and again.totals["changed"] == 1


def _job_of(session, scope) -> str:
    return str(session.execute(text("SELECT comparison_ai_job_id FROM comparison_spec_comparison WHERE comparison_transition_id = :t AND source = 'whole'"),
                               {"t": scope.transition_id}).scalar_one())


def test_the_same_text_in_another_transition_of_the_project_reuses_the_extraction(sessions, job_for, transition, run) -> None:
    """V4 is the newer side of V3 -> V4 and the older side of V4 -> V5, and V3 has the very same specification text (the answer key says
    the sheet did not change): the text is read once for the project, whichever version and whichever side it is."""
    doc, series, scope = transition
    repository = SpecificationRepository()
    _open(sessions, job_for, scope)
    first = Model()
    run.run(scope, ask=first)
    assert len(first.prompts) == 2
    with session_scope(sessions) as session:
        earlier = repository.transition(session, next(t["transition_id"] for t in series["transitions"] if t["target_version_uid"] == doc.versions[1]))
    _open(sessions, job_for, earlier)
    second = Model()
    outcome = run.run(earlier, ask=second)
    assert second.prompts == []  # V3 and V4 read the same text, and V4 is stored
    assert outcome.state == "completed" and outcome.totals == {"changed": 0, "removed": 0, "added": 0, "unclear": 0, "renumbered": 0, "moved": 0}


def test_an_answer_that_fails_the_check_makes_the_side_incomplete_and_nothing_is_compared(sessions, job_for, transition, run, service) -> None:
    """A quote that is not in the text is never confirmed: no row of the side exists, so no change can be built on it."""
    _doc, _series, scope = transition

    def forge(answer, call_no):
        if call_no == 2:  # the newer version
            answer["blocks"][0]["rows"][2]["evidence"][0]["quote"] = "| 3 | СИНТ-АВ.63 | Выключатель автоматический 63 А | 30 | 0,45 | |"
        return answer

    _open(sessions, job_for, scope)
    outcome = run.run(scope, ask=Model(forge))
    assert outcome.state == "incomplete" and outcome.reason == "SPEC_ANSWER_UNCONFIRMED" and outcome.changes == [] and outcome.totals is None
    view = service.get_specification(transition_id=scope.transition_id)
    assert view["state"] == "incomplete" and view["method"] == "sheet_ai" and view["reason"] == "SPEC_ANSWER_UNCONFIRMED" and "totals" not in view
    assert service.list_changes(transition_id=scope.transition_id, kind=None, offset=0, limit=10) == ([], None)


def test_an_answer_that_failed_the_check_is_kept_and_not_paid_for_twice(sessions, job_for, transition, run) -> None:
    _doc, _series, scope = transition

    def forge(answer, call_no):
        if call_no == 2:
            answer["blocks"][0]["rows"].pop()
        return answer

    job = _open(sessions, job_for, scope)
    run.run(scope, ask=Model(forge))
    repository = SpecificationRepository()
    with session_scope(sessions) as session:
        repository.open_whole(session, scope, job_id=job, sheets_a=1, sheets_b=1)
        repository.set_state(session, scope.transition_id, to_state="running", from_states=("queued",), phase="comparing")
    again = Model()
    outcome = run.run(scope, ask=again)
    assert again.prompts == [] and outcome.state == "incomplete"


def test_a_side_whose_table_cannot_be_read_is_not_sent(sessions, job_for, transition, run, monkeypatch) -> None:
    from auditmanager.comparison.specification import reader as reader_module

    _doc, _series, scope = transition
    real = reader_module.parse_data
    monkeypatch.setattr(reader_module, "parse_data", lambda data: {"parsed": False, "reason": "колонки таблицы не найдены"} if real(data) is not None else None)
    _open(sessions, job_for, scope)
    model = Model()
    outcome = run.run(scope, ask=model)
    assert model.prompts == [] and outcome.state == "incomplete" and outcome.reason == "SPEC_NOT_PARSED"


def test_a_cancelled_row_takes_nothing(sessions, job_for, transition, run) -> None:
    _doc, _series, scope = transition
    _open(sessions, job_for, scope)
    repository = SpecificationRepository()
    with session_scope(sessions) as session:
        assert repository.set_state(session, scope.transition_id, to_state="cancelled", from_states=("running",), phase="done")
    run.run(scope, ask=Model())
    with session_scope(sessions) as session:
        row = repository.whole(session, scope.transition_id)
    assert row is not None and row.state == "cancelled" and row.changes == [] and row.totals is None


def test_the_states_of_a_transition_that_has_not_been_started(sessions, transition, service, lab) -> None:
    doc, series, scope = transition
    view = service.get_specification(transition_id=scope.transition_id)
    assert view["state"] == "not_started" and view["method"] == "whole" and (view["sheets_a"], view["sheets_b"]) == (1, 1)
    first = next(t for t in series["transitions"] if t["source_version_uid"] == doc.versions[0])
    assert service.get_specification(transition_id=first["transition_id"])["state"] == "not_started"
    page = service.list_specifications(series_id=series["series_id"], after_no=0, limit=1)
    assert len(page.items) == 1 and page.next_after == 1
    rest = service.list_specifications(series_id=series["series_id"], after_no=page.next_after, limit=5)
    assert len(rest.items) == 1 and rest.next_after is None
    with pytest.raises(DomainError) as failure:
        service.get_specification(transition_id="ctn_01ARZ3NDEKTSV4RRFFQ69G5FAV")
    assert failure.value.code is ErrorCode.NOT_FOUND
    with pytest.raises(DomainError):
        service.list_specifications(series_id="cser_01ARZ3NDEKTSV4RRFFQ69G5FAV", after_no=0, limit=5)
