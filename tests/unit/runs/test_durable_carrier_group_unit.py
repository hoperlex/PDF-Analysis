"""`EXEC2-GROUP-RUN-01` (ADR-0026 decisions 12, 15 and 16): the in-process claimant's wait sweep and its group dispatch flag,
and the terminal a Run whose cost consent no longer holds ends with. Container-free: the carrier's poller is driven on this
thread with a session factory and a repository that are values.

* the wait sweep is a step of its own: when it fails the failure is logged **by category** and ``next_queued_run`` still runs
  in the same pass (it used to share one ``try`` with the hint, so a failing sweep stopped the hint);
* ``AUDITMANAGER_GROUP_OFFLINE_WAIT_SECONDS`` is validated when the carrier is built, so a bad value stops the start and is not
  met again on every pass;
* the hint is asked through a repository that knows whether this process dispatches groups (the provider source is
  ``database``), and ``run_to_terminal`` builds its claiming repository the same way;
* a Run whose consent lapsed ends ``analysis_input_invalid`` with the Run path's own ``cost_estimate_binding_changed`` reason and
  a detail the catalogue screens as safe.

Written and **not run** in EXEC-2 (`R-149d`).
"""

from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Any

import pytest

import auditmanager.runs.carrier as carrier_module
import auditmanager.runs.public as runs_public
from auditmanager.jobs.repository import GROUP_OFFLINE_WAIT_ENV, JobRepository
from auditmanager.runs.carrier import GROUP_WAIT_SECONDS, DurableCarrier, run_to_terminal
from auditmanager.shared.errors import ErrorCode
from auditmanager.shared.errors.envelope import screen_details


class _Session:
    def __enter__(self) -> "_Session":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def commit(self) -> None:
        return None


@pytest.fixture
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(GROUP_OFFLINE_WAIT_ENV, raising=False)


def _carrier(**options: Any) -> DurableCarrier:
    return DurableCarrier(_Session, **options)  # type: ignore[arg-type]


def _drive_one_pass(monkeypatch: pytest.MonkeyPatch, carrier: DurableCarrier, *, sweep: Any, hint: Any) -> None:
    """Run the poller's loop body once on this thread: the hint stops it, and the clock makes every interval due."""
    monkeypatch.setattr(carrier_module, "monotonic", lambda: 10_000.0)
    monkeypatch.setattr(JobRepository, "reclaim_expired", lambda self, session, **keywords: 0)
    monkeypatch.setattr(JobRepository, "refresh_group_waits", sweep)

    def asked(self: JobRepository, session: Any, **keywords: Any) -> str | None:
        found = hint(self, session, **keywords)
        carrier._stop.set()
        carrier._wake.set()                        # the poller would wait a second for work
        return found

    monkeypatch.setattr(JobRepository, "next_queued_run", asked)
    carrier.configure_runner(lambda run_id: (lambda: None))
    carrier._poll()


def test_a_failing_wait_sweep_is_logged_by_category_and_never_stops_the_hint(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, clean_environment: None,
) -> None:
    carrier = _carrier()
    asked: list[bool] = []

    def failing_sweep(self: JobRepository, session: Any, **keywords: Any) -> None:
        raise RuntimeError("row run_01M2545JSD15ETSNNV904X991K says secret detail")

    def hint(self: JobRepository, session: Any, **keywords: Any) -> None:
        asked.append(self.dispatch_groups)

    try:
        with caplog.at_level(logging.ERROR, logger=carrier_module.__name__):
            _drive_one_pass(monkeypatch, carrier, sweep=failing_sweep, hint=hint)
    finally:
        carrier.shutdown()
    assert asked == [True], "the hint was asked in the pass whose sweep failed"
    assert "RuntimeError" in caplog.text, "the category is logged"
    assert "secret detail" not in caplog.text and "run_01M2545JSD15ETSNNV904X991K" not in caplog.text, "never the text"
    assert not any(record.exc_info for record in caplog.records), "and no traceback, which quotes the text"


def test_the_sweep_gets_the_validated_offline_wait_and_the_hint_the_dispatch_flag(
    monkeypatch: pytest.MonkeyPatch, clean_environment: None,
) -> None:
    carrier = _carrier(dispatch_groups=False, group_offline_wait_seconds=90)
    swept: list[dict[str, Any]] = []
    flags: list[bool] = []
    try:
        _drive_one_pass(
            monkeypatch, carrier,
            sweep=lambda self, session, **keywords: swept.append(keywords),
            hint=lambda self, session, **keywords: flags.append(self.dispatch_groups),
        )
    finally:
        carrier.shutdown()
    assert swept == [{"offline_wait_seconds": 90.0}] and flags == [False]
    assert carrier.dispatch_groups is False


def test_a_carrier_dispatches_groups_unless_told_otherwise(clean_environment: None) -> None:
    carrier = _carrier()
    try:
        assert carrier.dispatch_groups is True
    finally:
        carrier.shutdown()


@pytest.mark.parametrize("value", ["", " ", "0", "-5", "1.5", "thirty", str(7 * 24 * 3600 + 1)])
def test_a_bad_offline_wait_in_the_environment_stops_the_carrier_at_construction(
    monkeypatch: pytest.MonkeyPatch, value: str,
) -> None:
    monkeypatch.setenv(GROUP_OFFLINE_WAIT_ENV, value)
    with pytest.raises(ValueError, match=GROUP_OFFLINE_WAIT_ENV):
        _carrier()


def test_a_good_offline_wait_in_the_environment_is_read_once_at_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(GROUP_OFFLINE_WAIT_ENV, "900")
    carrier = _carrier()
    try:
        monkeypatch.setenv(GROUP_OFFLINE_WAIT_ENV, "not a number")       # changing it later changes nothing
        assert carrier._group_offline_wait_seconds == 900.0
    finally:
        carrier.shutdown()


def test_a_wait_that_is_not_positive_is_refused_at_construction(clean_environment: None) -> None:
    with pytest.raises(ValueError):
        _carrier(group_offline_wait_seconds=0)


def test_the_carrier_and_the_worker_sweep_at_one_interval() -> None:
    assert GROUP_WAIT_SECONDS == 5.0


def test_the_claiming_repository_of_run_to_terminal_carries_the_dispatch_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    built: list[dict[str, Any]] = []

    class Repository:
        def __init__(self, **options: Any) -> None:
            built.append(options)

    monkeypatch.setattr(carrier_module, "JobRepository", Repository)
    monkeypatch.setattr(carrier_module, "execute_run", lambda *args, **keywords: SimpleNamespace())
    for flag in (False, True):
        run_to_terminal(
            _Session, "run_x", blob_store=None, adapter=None, provider_config=None,  # type: ignore[arg-type]
            runs=SimpleNamespace(), worker_id="wrk_x", dispatch_groups=flag)
    run_to_terminal(
        _Session, "run_x", blob_store=None, adapter=None, provider_config=None,  # type: ignore[arg-type]
        runs=SimpleNamespace(), worker_id="wrk_x")
    assert built == [
        {"worker_id": "wrk_x", "dispatch_groups": False}, {"worker_id": "wrk_x", "dispatch_groups": True},
        {"worker_id": "wrk_x", "dispatch_groups": True}]


def test_the_composition_root_dispatches_groups_for_the_database_source_only() -> None:
    from auditmanager.bootstrap.composition import _dispatches_groups

    assert _dispatches_groups(SimpleNamespace(provider_source="database")) is True        # type: ignore[arg-type]
    assert _dispatches_groups(SimpleNamespace(provider_source="environment")) is False    # type: ignore[arg-type]


# --- the terminal of a Run whose consent no longer holds -------------------------------------------------------------------------


def test_a_run_whose_consent_lapsed_ends_with_the_run_paths_own_cost_binding_refusal(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    class Runs:
        def terminate(self, session: object, **keywords: Any) -> None:
            calls.append(("terminate", keywords))

        def clear_wait(self, session: object, **keywords: Any) -> None:
            calls.append(("clear_wait", keywords))

    monkeypatch.setattr(runs_public, "RunRepository", Runs)
    runs_public.fail_run_consent_lapsed(None, run_id="run_x", from_state="queued")  # type: ignore[arg-type]
    assert calls == [
        ("terminate", {
            "run_id": "run_x", "from_state": "queued", "to_state": "failed", "terminal_reason": "analysis_input_invalid",
            "terminal_detail": {"stage_id": "text_analysis", "reason": "cost_estimate_binding_changed"}}),
        ("clear_wait", {"run_id": "run_x"}),
    ], "the failed edge with the reason and detail, then the wait the Run no longer has is cleared"
    detail = calls[0][1]["terminal_detail"]
    assert screen_details(ErrorCode.ANALYSIS_INPUT_INVALID, detail) == detail, "a detail the catalogue declares safe, as stored"
    assert set(detail) <= set(ErrorCode.ANALYSIS_INPUT_INVALID.safe_detail_keys)
