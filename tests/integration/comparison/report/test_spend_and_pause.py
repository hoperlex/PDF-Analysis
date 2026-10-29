"""`CMP-VC-REPORT-01`: the money of a report job, in live mode with a scripted adapter that calls nothing (database, bucket, PDF child).

The journal row of a call is written ``prepared`` **before** the adapter is called and settled after it; a call that takes the job past 1.2 times its
estimate is paid for and kept, and the job makes no further call (a pause for ``overrun`` that a resume with a new consent lifts); an outcome that cannot
be known is never sent again. The adapter says ``live`` (so the spend wrapper applies its money rules) and returns the reply the test chose."""

from __future__ import annotations

from typing import Any

import pytest

from auditmanager.analysis.public import ModelResponse, ProviderMode
from auditmanager.comparison.public import ReportStaticModelSource
from auditmanager.shared.errors import DomainError, ErrorCode
from tests.integration.comparison.report.conftest import EXPERT, support
from tests.integration.comparison.report.run_support import pdf_text, record_client, reread, start


class LiveModel:
    """The model seam of a money test: says ``live``, answers from the recorded answers by digest with the cost the test chose, and writes down what
    the journal held at the moment it was called."""

    provider_mode = ProviderMode.LIVE

    def __init__(self, db: Any, costs: list[float], *, fail: Exception | None = None) -> None:
        self._db, self._costs, self._fail = db, list(costs), fail
        self.journal_at_call: list[list[dict[str, Any]]] = []
        self.digests: list[str] = []

    def complete(self, request: Any) -> ModelResponse:
        self.digests.append(request.request_sha256)
        self.journal_at_call.append(self._db.rows(
            "SELECT state, request_sha256, estimate_micros FROM comparison_model_call ORDER BY prepared_at"))
        if self._fail is not None:
            raise self._fail
        text = self._db.answers._answers[request.request_sha256].output_text
        return ModelResponse(
            output_text=text, stop_reason="end_turn", input_tokens=1000, output_tokens=200, latency_ms=10,
            reported_cost_usd=self._costs.pop(0), model=support.base.GATEWAY,
        )


def live(db: Any, adapter: LiveModel, **over: Any) -> Any:
    return db.handler(model_source=ReportStaticModelSource(adapter, pin=support.base.PIN, expected_model=support.base.GATEWAY, **over))


@pytest.fixture
def two(db: Any, world: Any, route: Any) -> Any:
    support.describe(db.connection, world["project"], world["pairs"][1]["result"])
    return world


def started_live(db: Any, world: Any, make: Any, route: Any, *, labels: tuple[str, ...] = ("V1→V2",)) -> dict[str, Any]:
    service = db.service(provider_mode="live")
    report = make(world, service=service)
    for label in labels:
        record_client(db, world, report, route, label=label)
    start(db, report, service=service)
    return report


def test_the_journal_row_is_written_before_the_adapter_is_called_and_settled_after_it(db: Any, world: Any, make: Any, route: Any) -> None:
    report = started_live(db, world, make, route)
    adapter = LiveModel(db, [0.01])
    db.drain(live(db, adapter))
    assert len(adapter.journal_at_call) == 1
    before = adapter.journal_at_call[0]
    assert [(row["state"], row["request_sha256"]) for row in before] == [("sent", adapter.digests[0])]  # prepared, committed, then marked sent: before the call
    assert before[0]["estimate_micros"] > 0
    row = db.rows("SELECT state, cost_basis, cost_micros, provider_mode FROM comparison_model_call")[0]
    assert (row["state"], row["cost_basis"], row["cost_micros"], row["provider_mode"]) == ("completed", "measured", 10_000, "live")
    final = reread(db, report)
    assert final["state"] == "completed" and final["job"]["spend"]["spent_micros"] == 10_000


def test_a_call_past_1_2_times_the_estimate_is_kept_and_pauses_the_report_until_a_resume_with_a_new_consent(db: Any, two: Any, make: Any, route: Any) -> None:
    report = started_live(db, two, make, route, labels=("V1→V2", "V2→V3"))
    estimate = reread(db, report)["job"]["estimate"]["estimate_micros"]
    assert estimate > 0
    adapter = LiveModel(db, [0.5, 0.01])
    handler = live(db, adapter)
    worker = db.worker()
    item = db.claim(worker)
    outcome = handler.run(item)
    with db.sessions() as session:
        db.work.finish(session, item.authority, outcome)
        session.commit()
    paused = reread(db, report)
    assert (paused["state"], paused["job"]["state"], paused["job"]["pause_reason"]) == ("paused", "paused", "overrun")
    assert paused["parts"][0]["selection"] == "done" and paused["parts"][1]["selection"] == "pending"  # the paid answer is kept
    assert paused["job"]["spend"]["spent_micros"] == 500_000 and len(adapter.digests) == 1
    assert db.drain(handler) == [] and len(adapter.digests) == 1  # a paused job's items are paused: nothing is claimed, nothing is sent
    refused = pytest.raises(DomainError, db.service().continue_report, report_id=report["report_id"], consent=None, user_uid=support.ACTOR,
                            actor_roles=EXPERT, idempotency_key="resume-0").value
    assert refused.code is ErrorCode.VALIDATION_FAILED and refused.detail_fields["constraint"] == "comparison_consent_required"
    left = paused["estimate"]  # what the report has left, to consent to
    assert left["calls"] == 1 and left["estimate_digest"] != paused["job"]["estimate"]["estimate_digest"]
    resumed = db.service().continue_report(
        report_id=report["report_id"], consent=db.consent(left["estimate_digest"]), user_uid=support.ACTOR, actor_roles=EXPERT, idempotency_key="resume-1")
    assert resumed["state"] == "queued" and resumed["job"]["state"] == "queued"
    db.drain(handler)
    done = reread(db, report)
    assert done["state"] == "completed" and len(adapter.digests) == 2 and "V2→V3" in " ".join(pdf_text(db.service().read_report_pdf(report_id=report["report_id"])))


def test_the_last_call_over_the_estimate_pauses_nothing_because_the_pdf_is_no_call(db: Any, world: Any, make: Any, route: Any) -> None:
    report = started_live(db, world, make, route)
    adapter = LiveModel(db, [0.9])
    db.drain(live(db, adapter))
    final = reread(db, report)
    assert final["state"] == "completed" and final["job"]["spend"]["spent_micros"] == 900_000


def test_an_outcome_that_cannot_be_known_is_never_sent_again_and_the_report_is_not_finished_behind_it(db: Any, world: Any, make: Any, route: Any) -> None:
    report = started_live(db, world, make, route)
    adapter = LiveModel(db, [], fail=RuntimeError("the connection dropped after the request"))
    handler = live(db, adapter)
    db.drain(handler)
    assert len(adapter.digests) == 1
    row = db.rows("SELECT state FROM comparison_model_call")
    assert [r["state"] for r in row] == ["unknown"]
    assert db.drain(handler) == [] and len(adapter.digests) == 1  # the item is spend_unknown: no worker claims it again
    stopped = reread(db, report)
    assert stopped["state"] == "partial" and stopped["parts"][0]["selection"] == "failed"  # honest: no file is written behind a call nobody can account for
    assert db.state("SELECT facts ->> 'error' FROM comparison_report_part WHERE comparison_report_id = :r ORDER BY created_at LIMIT 1", r=report["report_id"]) == "spend_unknown"
    assert [a["kind"] for a in stopped["artifacts"]] == ["source_md"]


def test_a_live_call_with_no_consent_to_a_connection_that_changed_is_refused_and_the_job_pauses_for_the_route(db: Any, world: Any, make: Any, route: Any) -> None:
    report = started_live(db, world, make, route)
    revision = support.base.new_revision(db.connection, route)  # the connection moved on after the consent
    adapter = LiveModel(db, [0.01])
    db.drain(live(db, adapter, revision_id=revision))
    assert adapter.digests == []  # nothing was sent
    paused = reread(db, report)
    assert (paused["state"], paused["job"]["pause_reason"]) == ("paused", "route_changed")
