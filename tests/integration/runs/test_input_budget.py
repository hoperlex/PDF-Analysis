"""`W55B-BUDGET-01` on real PostgreSQL: ``startRun`` and ``reauditRun`` refuse a version above the budget.

Plan `W55-PLAN.md` section B3.3 (G-11, R-118). The command refuses **up front** -- after the
version is read, before the idempotency key is claimed -- when the version's recorded
``text_character_count`` is strictly above ``input_budget_characters``:

* `SECTION-CHUNKED-ANALYSIS-01`: ``input_budget_characters`` is the budget of one model call and a
  section run above it is analysed in whole-page windows, so the limit is ``MAX_ANALYSIS_WINDOWS`` calls'
  worth (``LIMIT`` below): a count of ``LIMIT + 1`` is refused, a count of exactly ``LIMIT`` is accepted, a
  count between ``BUDGET + 1`` and ``LIMIT`` is accepted (it is windowed), a version with no recorded count
  (published before the bundle upload) is accepted, for a start **and** for a re-audit;
* the refusal's details are exactly ``character_count`` and ``budget_characters``, integers;
  the envelope is ``422 analysis_input_budget_exceeded``;
* **nothing is created**: no run, no job, no command record, no event -- the whole database is
  counted before and after, table by table;
* a re-audit faces **today's** budget, not the one its source run was accepted under;
* a retry of a refused key, after the operator raised the budget, is a fresh start; a key the
  ledger already knows is replayed whatever the budget now is;
* the shipped ``RunAdapter`` and ``ExecutionAdapter`` carry the budget to the commands.

HEAVY: the lane's PostgreSQL and S3 (the harness's ``seeded`` version puts its PDF in the
bucket). Everything runs in the harness's rolled-back transaction.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.analysis.public import MAX_ANALYSIS_WINDOWS, windowed_budget_characters
from auditmanager.api.routers.errors import envelope_response
from auditmanager.bootstrap.adapters import ExecutionAdapter, RunAdapter
from auditmanager.documents.public import DocumentRepository
from auditmanager.ingest.public import CommandRepository
from auditmanager.runs import COMMAND_TYPE_START_RUN, RunRepository
from auditmanager.runs.commands import reaudit_run, start_audit_run
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DocumentUid, IdempotencyKey, VersionUid

BUDGET = 50_000
#: What a run takes: ``MAX_ANALYSIS_WINDOWS`` calls of ``BUDGET`` (`SECTION-CHUNKED-ANALYSIS-01`).
LIMIT = windowed_budget_characters(BUDGET)


def _key(label: str = "budget") -> str:
    return f"w55b-{label}-" + uuid4().hex


def _counted_version(session: Session, seeded, count: int | None) -> str:
    """A further published version of the seeded document, with ``count`` recorded.

    The bundle's three counts are all set or all absent (the database refuses a half-set
    row), so a counted version carries the other two as an empty ``textless_pages`` and a
    zero ``recognised_character_count``. The manifest is the seeded version's own: the same
    blob, a different version row.
    """
    documents = DocumentRepository()
    base = documents.get_version(session, VersionUid.parse(seeded.version_uid))
    counts = (
        {}
        if count is None
        else {
            "text_character_count": count,
            "textless_pages": (),
            "recognised_character_count": 0,
        }
    )
    uid = documents.publish_version(
        session,
        document_uid=DocumentUid.parse(seeded.document_uid),
        media_type=base.media_type,
        byte_size=base.byte_size,
        sha256=base.sha256,
        page_count=base.page_count,
        source_filename=None,
        entries=base.manifest,
        **counts,
    )
    stored = documents.get_version(session, uid)
    assert stored.text_character_count == count, "the fixture did not record the count it was given"
    return str(uid)


def _start(session: Session, seeded, version_uid: str, key: str, budget: int | None):
    return start_audit_run(
        session,
        version_uid=version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded",
        idempotency_key=key,
        input_budget_characters=budget,
    )


def _terminal(session: Session, seeded, version_uid: str) -> str:
    """A terminal source run of ``version_uid``, written by the owning repository."""
    from auditmanager.shared.identity import RunId

    run_id = str(RunId.new())
    runs = RunRepository()
    runs.create(
        session,
        run_id=run_id,
        project_uid=seeded.project_uid,
        version_uid=version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded",
        frozen_input_digest="a" * 64,
        command_id=None,
    )
    runs.advance(session, run_id=run_id, from_state="created", to_state="queued")
    runs.advance(session, run_id=run_id, from_state="queued", to_state="running")
    runs.terminate(
        session,
        run_id=run_id,
        from_state="running",
        to_state="failed",
        terminal_reason=ErrorCode.ANALYSIS_FAILED.value,
    )
    return run_id


def _reaudit(session: Session, seeded, source_id: str, key: str, budget: int | None,
             roles: frozenset[str] = frozenset({"expert"})):
    return reaudit_run(
        session,
        source_run_id=source_id,
        roles=roles,
        idempotency_key=key,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded",
        input_budget_characters=budget,
    )


def _table_counts(session: Session) -> dict[str, int]:
    """Every base table in ``public`` with its row count: 'nothing was created', literally."""
    names = session.execute(
        text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY table_name"
        )
    ).scalars().all()
    assert len(names) > 30, "the lane database is not the migrated schema"
    return {
        name: int(session.execute(text(f'SELECT count(*) FROM "{name}"')).scalar_one())
        for name in names
    }


def _refusal(call) -> DomainError:
    with pytest.raises(DomainError) as refused:
        call()
    assert refused.value.code is ErrorCode.ANALYSIS_INPUT_BUDGET_EXCEEDED, refused.value.code
    return refused.value


# --- startRun --------------------------------------------------------------------------------


def test_a_start_above_the_budget_is_refused_with_both_figures(session, seeded) -> None:
    version = _counted_version(session, seeded, LIMIT + 1)
    refused = _refusal(lambda: _start(session, seeded, version, _key(), BUDGET))
    assert dict(refused.detail_fields) == {"character_count": LIMIT + 1, "budget_characters": LIMIT}
    assert all(type(value) is int for value in refused.detail_fields.values())


def test_a_start_exactly_at_the_budget_is_accepted(session, seeded, helpers) -> None:
    version = _counted_version(session, seeded, BUDGET)
    started = _start(session, seeded, version, _key(), BUDGET)
    assert started.replayed is False
    assert helpers.audit_run_row(session, started.run_id)["version_uid"] == version


def test_a_start_one_below_the_budget_is_accepted(session, seeded) -> None:
    version = _counted_version(session, seeded, BUDGET - 1)
    assert _start(session, seeded, version, _key(), BUDGET).replayed is False


def test_a_start_over_a_version_with_no_recorded_count_is_accepted(session, seeded) -> None:
    """Published before the bundle upload: NULL is not zero and not infinity -- it is not refused."""
    assert seeded.version_uid  # the seeded version is a bare-PDF version: three NULL counts
    stored = DocumentRepository().get_version(session, VersionUid.parse(seeded.version_uid))
    assert stored.text_character_count is None
    assert _start(session, seeded, seeded.version_uid, _key(), 0).replayed is False
    assert _start(session, seeded, seeded.version_uid, _key(), 1).replayed is False


def test_a_budget_of_zero_refuses_any_counted_version_and_admits_an_empty_one(session, seeded) -> None:
    _refusal(lambda: _start(session, seeded, _counted_version(session, seeded, 1), _key(), 0))
    assert _start(session, seeded, _counted_version(session, seeded, 0), _key(), 0).replayed is False


def test_no_configured_budget_means_no_check(session, seeded) -> None:
    """``None`` is "no configuration": reachable from tests only, and it checks nothing."""
    huge = _counted_version(session, seeded, 2_000_000_000)
    assert _start(session, seeded, huge, _key(), None).replayed is False


@pytest.mark.parametrize("bad", [-1, 1.5, "50000", True])
def test_a_budget_that_is_not_a_whole_number_of_characters_is_a_wiring_fault(
    session, seeded, bad
) -> None:
    with pytest.raises(ValueError):
        _start(session, seeded, seeded.version_uid, _key(), bad)


def test_a_refused_start_creates_nothing_at_all(session, seeded) -> None:
    """Up front: no run, no job, no command record, no event -- every table counted."""
    version = _counted_version(session, seeded, LIMIT + 1)
    key = _key()
    before = _table_counts(session)
    _refusal(lambda: _start(session, seeded, version, key, BUDGET))
    assert _table_counts(session) == before
    assert (
        CommandRepository().find(
            session, command_type=COMMAND_TYPE_START_RUN, idempotency_key=IdempotencyKey(key)
        )
        is None
    ), "a refusal left the idempotency key claimed"


def test_the_same_key_after_the_budget_is_raised_is_a_fresh_start_not_a_replayed_refusal(
    session, seeded, helpers
) -> None:
    version = _counted_version(session, seeded, LIMIT + 1)
    key = _key()
    _refusal(lambda: _start(session, seeded, version, key, BUDGET))
    runs_before = helpers.count_runs(session)

    started = _start(session, seeded, version, key, BUDGET + 1)
    assert started.replayed is False, "the refusal was recorded, so the retry replayed it"
    assert helpers.count_runs(session) == runs_before + 1
    assert helpers.audit_run_row(session, started.run_id)["version_uid"] == version


def test_the_same_key_replays_after_an_accepted_start(session, seeded, helpers) -> None:
    version = _counted_version(session, seeded, BUDGET)
    key = _key()
    first = _start(session, seeded, version, key, BUDGET)
    runs_after_first = helpers.count_runs(session)
    again = _start(session, seeded, version, key, BUDGET)
    assert again.replayed is True and again.run_id == first.run_id
    assert helpers.count_runs(session) == runs_after_first


def test_a_key_the_ledger_knows_replays_even_when_the_budget_has_since_fallen(
    session, seeded, helpers
) -> None:
    """A client retrying an accepted start is told what happened, not that the version it
    already started is now too large for today's configuration."""
    version = _counted_version(session, seeded, BUDGET)
    key = _key()
    first = _start(session, seeded, version, key, BUDGET)
    before = _table_counts(session)
    replay = _start(session, seeded, version, key, BUDGET - 1)
    assert replay.replayed is True and replay.run_id == first.run_id
    assert _table_counts(session) == before


def test_a_known_key_over_a_different_payload_is_still_a_key_reuse_not_a_budget_answer(
    session, seeded
) -> None:
    key = _key()
    small = _counted_version(session, seeded, 10)
    _start(session, seeded, small, key, BUDGET)
    large = _counted_version(session, seeded, LIMIT + 1)
    with pytest.raises(DomainError) as reused:
        _start(session, seeded, large, key, BUDGET)
    assert reused.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE


def test_the_refusal_is_a_422_envelope_carrying_exactly_the_two_integers(session, seeded) -> None:
    version = _counted_version(session, seeded, LIMIT + 7)
    refused = _refusal(lambda: _start(session, seeded, version, _key(), BUDGET))
    response = envelope_response(refused, "cid-input-budget-0001")
    body = json.loads(response.body)
    assert response.status_code == 422
    assert body["error_code"] == "analysis_input_budget_exceeded"
    assert body["retryable"] is False
    assert body["details"] == {"character_count": LIMIT + 7, "budget_characters": LIMIT}


# --- SECTION-CHUNKED-ANALYSIS-01: above one call, within the windows -------------------------


def test_the_limit_is_that_many_calls_of_the_budget() -> None:
    assert LIMIT == BUDGET * MAX_ANALYSIS_WINDOWS and MAX_ANALYSIS_WINDOWS > 1


@pytest.mark.parametrize("count", [BUDGET + 1, 2 * BUDGET, LIMIT - 1, LIMIT])
def test_a_start_above_one_call_and_within_the_windows_is_accepted(
    session, seeded, helpers, count
) -> None:
    """Before this task these counts were the refusal; now the run is analysed in windows."""
    version = _counted_version(session, seeded, count)
    started = _start(session, seeded, version, _key(), BUDGET)
    assert started.replayed is False
    assert helpers.audit_run_row(session, started.run_id)["version_uid"] == version


@pytest.mark.parametrize("count", [BUDGET + 1, 2 * BUDGET, LIMIT])
def test_a_reaudit_above_one_call_and_within_the_windows_is_accepted(
    session, seeded, helpers, count
) -> None:
    version = _counted_version(session, seeded, count)
    source = _terminal(session, seeded, version)
    started = _reaudit(session, seeded, source, _key("reaudit"), BUDGET)
    assert started.replayed is False
    assert helpers.audit_run_row(session, started.run_id)["reaudit_of_run_id"] == source


def test_one_window_as_the_limit_restores_the_one_call_refusal(
    session, seeded, monkeypatch
) -> None:
    """The rollback of the whole feature: ``MAX_ANALYSIS_WINDOWS = 1`` is the refusal it always was."""
    import auditmanager.runs.commands as commands

    monkeypatch.setattr(commands, "MAX_ANALYSIS_WINDOWS", 1)
    version = _counted_version(session, seeded, BUDGET + 1)
    refused = _refusal(lambda: _start(session, seeded, version, _key(), BUDGET))
    assert dict(refused.detail_fields) == {"character_count": BUDGET + 1, "budget_characters": BUDGET}
    at = _counted_version(session, seeded, BUDGET)
    assert _start(session, seeded, at, _key(), BUDGET).replayed is False


def test_the_ar_v3_group_keeps_the_one_call_refusal() -> None:
    """The group start shares ``_checked_budget`` and ``_refuse_over_budget``; only the section runs window."""
    import auditmanager.runs.v3_group as v3_group
    from auditmanager.runs.commands import _refuse_over_budget

    assert v3_group._refuse_over_budget is _refuse_over_budget
    with pytest.raises(DomainError) as refused:
        _refuse_over_budget(BUDGET + 1, BUDGET)
    assert refused.value.code is ErrorCode.ANALYSIS_INPUT_BUDGET_EXCEEDED
    assert dict(refused.value.detail_fields) == {
        "character_count": BUDGET + 1, "budget_characters": BUDGET,
    }


# --- reauditRun ------------------------------------------------------------------------------


def test_a_reaudit_above_the_budget_is_refused_with_both_figures(session, seeded) -> None:
    version = _counted_version(session, seeded, LIMIT + 1)
    source = _terminal(session, seeded, version)
    refused = _refusal(lambda: _reaudit(session, seeded, source, _key("reaudit"), BUDGET))
    assert dict(refused.detail_fields) == {"character_count": LIMIT + 1, "budget_characters": LIMIT}
    assert all(type(value) is int for value in refused.detail_fields.values())


def test_a_reaudit_exactly_at_the_budget_is_accepted(session, seeded, helpers) -> None:
    version = _counted_version(session, seeded, BUDGET)
    source = _terminal(session, seeded, version)
    started = _reaudit(session, seeded, source, _key("reaudit"), BUDGET)
    assert started.replayed is False
    child = helpers.audit_run_row(session, started.run_id)
    assert child["reaudit_of_run_id"] == source and child["version_uid"] == version


def test_a_reaudit_over_a_version_with_no_recorded_count_is_accepted(session, seeded) -> None:
    source = _terminal(session, seeded, seeded.version_uid)
    assert _reaudit(session, seeded, source, _key("reaudit"), 0).replayed is False


def test_a_refused_reaudit_creates_nothing_at_all(session, seeded) -> None:
    version = _counted_version(session, seeded, LIMIT + 1)
    source = _terminal(session, seeded, version)
    key = _key("reaudit")
    before = _table_counts(session)
    _refusal(lambda: _reaudit(session, seeded, source, key, BUDGET))
    assert _table_counts(session) == before
    assert (
        CommandRepository().find(
            session, command_type="reaudit_run", idempotency_key=IdempotencyKey(key)
        )
        is None
    )


def test_a_reaudit_faces_todays_budget_not_the_one_its_source_was_accepted_under(
    session, seeded, helpers
) -> None:
    """R-82: the budget is between the source run and the re-audit, and the re-audit sees the later one."""
    version = _counted_version(session, seeded, 30_000)
    source = _start(session, seeded, version, _key(), 40_000)  # accepted: 30 000 <= 40 000 x the windows
    runs = RunRepository()
    runs.advance(session, run_id=source.run_id, from_state="created", to_state="queued")
    runs.advance(session, run_id=source.run_id, from_state="queued", to_state="running")
    runs.terminate(
        session, run_id=source.run_id, from_state="running", to_state="failed",
        terminal_reason=ErrorCode.ANALYSIS_FAILED.value,
    )

    # The operator lowers the ceiling: today's call budget is 2 000, a limit of 2 000 x the windows
    # (24 000 at twelve), below the count. The source stays accepted.
    lowered = windowed_budget_characters(2_000)
    assert lowered < 30_000
    refused = _refusal(lambda: _reaudit(session, seeded, source.run_id, _key("reaudit"), 2_000))
    assert dict(refused.detail_fields) == {"character_count": 30_000, "budget_characters": lowered}

    # Raised again: the same source, a new key, a call budget whose limit reaches the count admits it.
    raised = -(-30_000 // MAX_ANALYSIS_WINDOWS)
    assert windowed_budget_characters(raised) >= 30_000
    again = _reaudit(session, seeded, source.run_id, _key("reaudit"), raised)
    assert again.replayed is False
    assert helpers.audit_run_row(session, again.run_id)["reaudit_of_run_id"] == source.run_id


def test_the_same_reaudit_key_after_the_budget_is_raised_is_a_fresh_start(
    session, seeded, helpers
) -> None:
    version = _counted_version(session, seeded, LIMIT + 1)
    source = _terminal(session, seeded, version)
    key = _key("reaudit")
    _refusal(lambda: _reaudit(session, seeded, source, key, BUDGET))
    started = _reaudit(session, seeded, source, key, BUDGET + 1)
    assert started.replayed is False
    assert helpers.audit_run_row(session, started.run_id)["reaudit_of_run_id"] == source


def test_a_known_reaudit_key_replays_whatever_the_budget_is_now(session, seeded) -> None:
    version = _counted_version(session, seeded, BUDGET)
    source = _terminal(session, seeded, version)
    key = _key("reaudit")
    first = _reaudit(session, seeded, source, key, BUDGET)
    before = _table_counts(session)
    replay = _reaudit(session, seeded, source, key, BUDGET - 1)
    assert replay.replayed is True and replay.run_id == first.run_id
    assert _table_counts(session) == before


def test_the_role_is_checked_before_the_budget_so_a_refusal_tells_a_stranger_nothing(
    session, seeded
) -> None:
    version = _counted_version(session, seeded, LIMIT + 1)
    source = _terminal(session, seeded, version)
    with pytest.raises(DomainError) as denied:
        _reaudit(session, seeded, source, _key("reaudit"), BUDGET, roles=frozenset())
    assert denied.value.code is ErrorCode.PERMISSION_DENIED


# --- the shipped adapters carry the budget --------------------------------------------------


class _NoCarrier:
    """Records submissions and runs nothing: only acceptance and refusal are asserted."""

    def __init__(self) -> None:
        self.submitted: list[object] = []

    def submit(self, job: object) -> None:
        self.submitted.append(job)


def _adapters(session: Session, seeded, budget: int | None):
    factory = sessionmaker(
        bind=session.connection(), expire_on_commit=False, future=True,
        join_transaction_mode="create_savepoint",
    )
    carrier = _NoCarrier()
    runs = RunAdapter(
        factory, blob_store=None, adapter=None, provider_config=None, provider_mode="recorded",
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id, carrier=carrier,
        input_budget_characters=budget,
    )
    return SimpleNamespace(runs=runs, execution=ExecutionAdapter(factory, runs=runs), carrier=carrier)


def test_the_shipped_run_adapter_refuses_a_start_above_its_budget(session, seeded) -> None:
    adapters = _adapters(session, seeded, BUDGET)
    over = _counted_version(session, seeded, LIMIT + 1)
    before = _table_counts(session)
    refused = _refusal(
        lambda: adapters.runs.start_run(version_uid=over, idempotency_key=_key())
    )
    assert dict(refused.detail_fields) == {"character_count": LIMIT + 1, "budget_characters": LIMIT}
    assert adapters.carrier.submitted == []
    assert _table_counts(session) == before

    at = _counted_version(session, seeded, LIMIT)
    view = adapters.runs.start_run(version_uid=at, idempotency_key=_key())
    assert view.state == "queued" and len(adapters.carrier.submitted) == 1


def test_the_shipped_execution_adapter_refuses_a_reaudit_above_its_budget(
    session, seeded, monkeypatch
) -> None:
    monkeypatch.setattr(
        ExecutionAdapter, "_roles", staticmethod(lambda _session, _user: frozenset({"expert"}))
    )
    adapters = _adapters(session, seeded, BUDGET)
    over = _counted_version(session, seeded, LIMIT + 1)
    source = _terminal(session, seeded, over)
    before = _table_counts(session)
    refused = _refusal(
        lambda: adapters.execution.reaudit_run(
            run_id=source, user_uid="usr_00000000000000000000000000", idempotency_key=_key("reaudit")
        )
    )
    assert dict(refused.detail_fields) == {"character_count": LIMIT + 1, "budget_characters": LIMIT}
    assert adapters.carrier.submitted == []
    assert _table_counts(session) == before

    at = _counted_version(session, seeded, LIMIT)
    admitted = _terminal(session, seeded, at)
    view = adapters.execution.reaudit_run(
        run_id=admitted, user_uid="usr_00000000000000000000000000", idempotency_key=_key("reaudit")
    )
    assert view.state == "queued" and len(adapters.carrier.submitted) == 1
