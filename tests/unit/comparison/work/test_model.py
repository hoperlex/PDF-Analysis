"""The vocabulary of the comparison queue (`CMP-WORK-01`): outcomes, the token, the states the code
names against the states the migration declares. Container-free."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from auditmanager.comparison.work import model
from auditmanager.comparison.work.repository import RETRY_BACKOFF_CAP_SECONDS, retry_delay_seconds

ROOT = Path(__file__).resolve().parents[4]


def _migration():  # type: ignore[no-untyped-def]
    path = ROOT / "db/migrations/versions/20261028_0038_comparison_foundation.py"
    spec = importlib.util.spec_from_file_location("cmp_work_01_migration_0038", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_states_the_code_names_are_the_states_the_migration_declares() -> None:
    migration = _migration()
    assert model.WORK_STATES == migration.WORK_STATES
    assert model.ATTEMPT_STATES == migration.ATTEMPT_STATES
    assert model.TERMINAL_STATES == frozenset(migration.WORK_TERMINAL)
    assert model.LIVE_STATES == frozenset(migration.WORK_STATES) - frozenset(migration.WORK_TERMINAL)


def test_the_kind_shape_is_the_columns() -> None:
    assert model.KIND_PATTERN.pattern == "^[a-z][a-z0-9_]{2,63}$"
    assert "ck_comparison_work_kind CHECK (kind ~ '^[a-z][a-z0-9_]{{2,63}}$')" in (
        ROOT / "db/migrations/versions/20261028_0038_comparison_foundation.py").read_text(encoding="utf-8")
    assert model.KIND_PATTERN.match("page_profile") and not model.KIND_PATTERN.match("Page")


@pytest.mark.parametrize("reason", ["", "Upper", "1starts_with_digit", "has space", "x" * 129])
def test_a_failure_reason_is_a_code_not_text(reason: str) -> None:
    with pytest.raises(ValueError):
        model.Failed(reason)


def test_a_failure_reason_the_column_holds_is_accepted() -> None:
    assert model.Failed("page_unreadable").retry is False
    assert model.Failed("x" * 128, retry=True).retry is True


@pytest.mark.parametrize("delay", [-0.1, 86_401.0])
def test_a_yield_delays_an_item_by_a_bounded_time(delay: float) -> None:
    with pytest.raises(ValueError):
        model.Yielded(delay_seconds=delay)
    assert model.Yielded().delay_seconds == 0.0


def test_the_execution_token_is_in_no_repr_or_str() -> None:
    authority = model.ItemAuthority("cq_X", "cqa_X", "SECRET-TOKEN-VALUE")
    assert "SECRET-TOKEN-VALUE" not in repr(authority)
    assert "SECRET-TOKEN-VALUE" not in str(authority)
    item = model.WorkItem(
        work_id="cq_X", attempt_id="cqa_X", attempt_no=1, project_uid="prj_X", module="versions",
        kind="page_profile", payload={}, comparison_upload_id=None, created_by_user_uid=None,
        max_attempts=3, authority=authority,
    )
    assert "SECRET-TOKEN-VALUE" not in repr(item)


def test_an_item_that_was_not_claimed_through_a_repository_cannot_fence() -> None:
    item = model.WorkItem(
        work_id="cq_X", attempt_id="cqa_X", attempt_no=1, project_uid="prj_X", module="versions",
        kind="page_profile", payload={}, comparison_upload_id=None, created_by_user_uid=None,
        max_attempts=3, authority=model.ItemAuthority("cq_X", "cqa_X", "t"),
    )
    with pytest.raises(RuntimeError):
        item.require_current(None)  # type: ignore[arg-type]
    assert not item.lease_lost.is_set() and not item.cancelled.is_set()


def test_the_retry_backoff_doubles_from_five_seconds_and_is_capped() -> None:
    assert [retry_delay_seconds(n) for n in (0, 1, 2, 3, 4)] == [5.0, 5.0, 10.0, 20.0, 40.0]
    assert retry_delay_seconds(50) == RETRY_BACKOFF_CAP_SECONDS == 300.0


def test_the_lease_is_the_jobs_lease_and_three_heartbeats_fit_in_it() -> None:
    from auditmanager.jobs.public import ATTEMPT_WATCHDOG_SECONDS, JobRepository
    from auditmanager.jobs.lease import HEARTBEAT_SECONDS

    assert model.LEASE_SECONDS == JobRepository.lease_seconds == 60.0
    assert model.HEARTBEAT_SECONDS == HEARTBEAT_SECONDS == 20.0
    assert model.ATTEMPT_WATCHDOG_SECONDS == ATTEMPT_WATCHDOG_SECONDS
    assert model.LEASE_SECONDS / model.HEARTBEAT_SECONDS == 3
