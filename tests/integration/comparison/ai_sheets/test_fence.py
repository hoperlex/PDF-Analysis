"""A worker that lost its lease publishes nothing (`CMP-VC-AISHEET-01`; the fence of ``CMP-WORK-01``).

The description is written, the sheet's item moves to ``done`` and the job's end is handed on in **one** transaction that begins with
``WorkItem.require_current``. The lease is taken away (the watchdog fences the attempt) after the model has answered and before the
publication; the publication must be refused and leave no description, no ``done`` item.
"""

from __future__ import annotations

from typing import Any

import pytest

from auditmanager.comparison.ai_sheets.handler import SheetChangesHandler
from auditmanager.comparison.public import ComparisonModelCaller, settle_lost_attempt
from auditmanager.comparison.work.model import WorkDependencies
from auditmanager.shared.errors import DomainError, ErrorCode


class Racing(SheetChangesHandler):
    """The handler, with the lease taken from it between the answer and the publication."""

    def __init__(self, *args: Any, lab: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._lab = lab

    def _publish(self, item: Any, *args: Any, **kwargs: Any) -> Any:
        with self._lab.db.sessions() as session:
            self._lab.db.work.reclaim_expired(
                session, spend_settlers=(settle_lost_attempt,), force_attempt_id=item.attempt_id, reason="item_watchdog",
            )
            session.commit()
        return super()._publish(item, *args, **kwargs)


def test_a_worker_whose_lease_was_taken_publishes_no_description_and_no_done_item(lab: Any) -> None:
    lab.record("p1")
    job = lab.start_pair("p1")
    racing = Racing(
        WorkDependencies(engine=None, session_factory=lab.db.sessions, blob_store=None, work=lab.db.work),  # type: ignore[arg-type]
        routes=lab.routes, material=lab.material, jobs=lab.jobs, caller=ComparisonModelCaller(lab.db.sessions), lab=lab,
    )
    item = lab.db.claim(lab.worker_id, "comparison_sheet_changes")
    with pytest.raises(DomainError) as fenced:
        racing.run(item)
    assert fenced.value.code in (ErrorCode.STALE_ATTEMPT, ErrorCode.EXECUTION_TOKEN_INVALID)
    assert lab.descriptions() == []
    assert lab.items(job["job_id"]) == {"p1": "running"}, "the row is not done; the next attempt takes the sheet up again"
    assert lab.answers.calls == 1, "the answer was paid for once; the fenced publication wrote nothing"
