"""`D-668` (`HOSTS-DEBTS-01`): the journal row of a planned call is **checked** against the member its cell was bound to.

``call_journal_columns`` is what the two journals of the run path (`_DurableCallJournal.prepare`, `extended_review._call`) spread into
``prepare_provider_call``. ``prepare_provider_call`` reads the member of the cell from ``audit_run_cell_binding`` and refuses a host or an access
that is not the member's -- but only when it is told the cell (``cell_key``). Until this lane the columns carried the stage, the host and the
access and no cell, so the check ran only in tests that passed ``cell_key`` by hand and never for a call the runs layer made.

No database: the real ``JobRepository.prepare_provider_call`` is driven through a recording session, and the binding row is a fake of
``cell_binding_of`` (which is what the repository imports at the call). What PostgreSQL does with the same call is the second half of
``tests/integration/executors/test_hosts_int_wire.py`` (the loop over the cells refuses a binding that names another host or access).
"""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.analysis.text.binding import CallBinding
from auditmanager.executors import public as executors_public
from auditmanager.jobs import repository as jobs_repository
from auditmanager.jobs.repository import JobRepository
from auditmanager.runs import stage_layout as layout
from auditmanager.runs.stage_plan import call_journal_columns
from auditmanager.shared.errors import DomainError, ErrorCode

HOST_A = "exh_01M2545JSD15ETSNNV904X991A"
HOST_B = "exh_01M2545JSD15ETSNNV904X991B"
REVISION = "excr_01M2545JSD15ETSNNV904X991R"
RUN = "run_01M2545JSD15ETSNNV904X991K"


class _Recorder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def execute(self, statement: Any, params: dict[str, Any] | None = None) -> Any:
        self.calls.append((str(statement), dict(params or {})))
        return SimpleNamespace(rowcount=1)


def _planned(cell_key: str, *, host: str = HOST_A, access: str = "subscription") -> CallBinding:
    return CallBinding(
        provider_label="agent", expected_model="claude-opus-5-5", check_identity=True, unmetered=access == "subscription",
        identity_basis="declared", connection_revision_id=REVISION, cell_key=cell_key, access=access, host_id=host)


@pytest.fixture
def journal(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """The real repository; ``asked`` records every cell the binding was read for, ``bound`` is the member the cell is bound to."""
    state = SimpleNamespace(asked=[], bound=SimpleNamespace(host_id=HOST_A, access="subscription", connection_revision_id=REVISION))
    repo = JobRepository()
    monkeypatch.setattr(repo, "require_current", lambda session, authority: None)
    monkeypatch.setattr(jobs_repository, "append_execution_event", lambda *args, **kwargs: None)

    def cell_binding_of(session: Any, run_id: str, cell_key: str) -> Any:
        state.asked.append((run_id, cell_key))
        return state.bound

    monkeypatch.setattr(executors_public, "cell_binding_of", cell_binding_of)
    state.repo = repo
    return state


def _prepare(state: SimpleNamespace, call: CallBinding) -> dict[str, Any]:
    session = _Recorder()
    state.repo.prepare_provider_call(
        session, SimpleNamespace(run_id=RUN, job_id="job_x", attempt_id="att_x"), provider=call.provider_label,
        model_identity="claude-opus-5-5", provider_mode="live", parameters={}, request_sha256="a" * 64,
        connection_revision_id=call.connection_revision_id, identity_basis=call.identity_basis, **call_journal_columns(call))
    (sql, params), = session.calls
    assert "INSERT INTO provider_call_effect" in sql
    return params


def test_the_columns_of_a_planned_call_name_its_cell() -> None:
    plan = layout.preset_cells("claude_only")
    assert plan, "the preset has cells"
    for cell in plan:
        columns = call_journal_columns(_planned(cell.cell_key))
        assert columns["cell_key"] == cell.cell_key, "the cell the call belongs to, as 'row:role'"
        assert columns["stage_key"] == cell.cell_key.partition(":")[0]
        assert set(columns) == {"stage_key", "host_id", "access", "cell_key"}


def test_a_call_that_is_not_planned_carries_no_cell_and_reads_no_binding(journal: SimpleNamespace) -> None:
    assert call_journal_columns(None) == {}
    assert call_journal_columns(CallBinding(expected_model="m", check_identity=True)) == {}
    params = _prepare(journal, replace(_planned("blocks:leg1"), cell_key=None, access=None, host_id=None, check_identity=False, expected_model=None,
                                       connection_revision_id=None, identity_basis=None))
    assert journal.asked == [] and (params["host_id"], params["access"], params["stage_key"]) == (None, None, None)


def test_a_planned_calls_journal_row_is_read_against_the_member_of_its_cell(journal: SimpleNamespace) -> None:
    params = _prepare(journal, _planned("blocks:leg1"))
    assert journal.asked == [(RUN, "blocks:leg1")], "the binding of exactly this run and this cell was read"
    assert (params["host_id"], params["access"], params["stage_key"]) == (HOST_A, "subscription", "blocks")


@pytest.mark.parametrize("call", [_planned("blocks:leg1", host=HOST_B), _planned("blocks:leg1", access="api")], ids=["another_host", "another_access"])
def test_a_planned_call_that_names_another_host_or_access_than_its_cell_was_bound_to_is_refused(journal: SimpleNamespace, call: CallBinding) -> None:
    with pytest.raises(DomainError) as refused:
        _prepare(journal, call)
    assert refused.value.code is ErrorCode.INTERNAL_ERROR and "another host or access" in str(refused.value.custom_message)
    assert journal.asked == [(RUN, "blocks:leg1")]


def test_a_cell_with_no_binding_row_is_refused_not_journalled(journal: SimpleNamespace) -> None:
    journal.bound = None
    with pytest.raises(DomainError) as refused:
        _prepare(journal, _planned("norms:main"))
    assert refused.value.code is ErrorCode.INTERNAL_ERROR
