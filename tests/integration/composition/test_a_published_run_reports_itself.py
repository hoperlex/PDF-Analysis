"""What a published run tells a client about itself.

`W15-RUN` drove this product through a browser and read, on a run that had published
three findings in eleven seconds:

    Published findings: not reported
    Started   -     Finished   -
    Created 23:07:31 UTC / Terminal at 23:07:31 UTC

Every layer below the response had the answer. `stage_result` carried real per-stage
timings, the frozen `StageState` declares `started_at` and `finished_at`, the frozen
`RunStatus` declares `published_finding_count` and `diagnostic_observation_count`, and
`api/schemas/runs.py` serialises all four the moment a view carries them. Nothing between
the rows and the body produced them, so four declared, stored, serialisable fields had no
reader -- and the run reported a duration of exactly zero.

**These are two defects, not one**, and this module keeps them apart on purpose:

* `W17VIEW-1`, the four missing fields, was an omission in two readers --
  `runs/repository.py::_SELECT_STAGE_RESULTS`, which never selected the two timing
  columns its own upsert writes, and `bootstrap/adapters.py::_run_status_view`, which
  never set the two counts.
* `W17VIEW-2`, the collapsed timestamps, was a SQL defect with nothing to do with the
  above: **`now()` is `transaction_timestamp()`**, constant for the whole transaction,
  and `RunAdapter.start_run` creates *and executes* a run inside one `_write(...)`. So
  `created_at`, `updated_at` and `terminal_at` were three copies of the instant the
  transaction opened. The repair is `statement_timestamp()`.

A test per defect, so reverting either repair reddens its own test and not the other's.

Driven end to end through the composed ASGI application: the counts and the timings are
read off a response body, never from the modules that produce them.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from starlette.testclient import TestClient

from auditmanager.api.routers.idempotency import IDEMPOTENCY_HEADER
from auditmanager.api.security import API_TOKEN_VARIABLE

#: `T-6`. Written out, not imported from the seam it authenticates against.
STATIC_TOKEN = "published-run-reports-itself-token"

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BASELINE_PDF = REPOSITORY_ROOT / "fixtures" / "synthetic" / "ar" / "ar_baseline.pdf"

#: The four PC-01 stages, written out rather than imported from `runs.PC01_STAGES`: an
#: expectation read from the module it checks cannot report that the module moved.
EXPECTED_STAGES = frozenset(
    {
        "source_preparation",
        "page_geometry_extraction",
        "document_context_build",
        "text_analysis",
    }
)


def _instant(value: str) -> datetime:
    """A contract timestamp, as the frozen `date-time` format writes it."""
    assert value.endswith("Z"), value
    return datetime.fromisoformat(value[:-1] + "+00:00")


@pytest.fixture(scope="module")
def published_run() -> dict[str, Any]:
    """One recorded run, driven through the edge, with the bodies it answered.

    The provider mode is named out loud because the root `conftest` strips every
    provider-selecting variable for the whole session; a suite that wants a mode has to
    say so, and this one must never be able to spend.
    """
    assert os.environ.get("DATABASE_URL"), "this suite needs the lane's .env loaded"
    for leaked in ("ANTHROPIC_API_KEY", "PROXY_LLM_BASE_URL", "PROXY_LLM_TOKEN"):
        assert leaked not in os.environ, (
            f"{leaked} reached this suite; a recorded run must not be able to spend"
        )

    from auditmanager.api.app import create_asgi_app

    environ = dict(os.environ) | {
        "AUDITMANAGER_PROVIDER_MODE": "recorded",
        API_TOKEN_VARIABLE: STATIC_TOKEN,
    }
    asgi_app = create_asgi_app(environ=environ)
    client = TestClient(asgi_app, raise_server_exceptions=False)
    auth = {"Authorization": f"Bearer {STATIC_TOKEN}"}
    tag = uuid.uuid4().hex[:12]

    answer = client.post(
        "/projects",
        headers=auth
        | {IDEMPOTENCY_HEADER: f"w17view-{tag}-prj", "Content-Type": "application/json"},
        content=json.dumps({"name": f"W17-VIEW {tag}"}).encode("utf-8"),
    )
    assert answer.status_code == 201, answer.content
    project_uid = answer.json()["project_uid"]

    boundary = "w17viewboundary"
    head = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
        f'filename="ar_baseline.pdf"\r\nContent-Type: application/pdf\r\n\r\n'
    ).encode("utf-8")
    tail = (
        f"\r\n--{boundary}\r\nContent-Disposition: form-data; "
        f'name="display_title"\r\n\r\nAR baseline\r\n--{boundary}--\r\n'
    ).encode("utf-8")
    answer = client.post(
        f"/projects/{project_uid}/documents",
        headers=auth
        | {
            IDEMPOTENCY_HEADER: f"w17view-{tag}-doc",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        content=head + BASELINE_PDF.read_bytes() + tail,
    )
    assert answer.status_code == 201, answer.content
    version_uid = answer.json()["version_uid"]

    answer = client.post(
        "/runs",
        headers=auth
        | {IDEMPOTENCY_HEADER: f"w17view-{tag}-run", "Content-Type": "application/json"},
        content=json.dumps({"version_uid": version_uid}).encode("utf-8"),
    )
    assert answer.status_code == 202, answer.content
    started = answer.json()
    # `D-20`. The `202` reports what was **accepted**, and execution happens on a carrier
    # thread; the published shape this module reads is the one `getRunStatus` answers once
    # the run has finished. The wait is on the carrier's own futures --
    # `ThreadCarrier.drain` -- so this waits for the work to be done rather than for a
    # duration somebody guessed, and no reading below can race the executor.
    assert started["state"] == "queued", started
    assert asgi_app.state.run_carrier.drain(timeout=300), "the run never finished"

    answer = client.get(f"/runs/{started['run_id']}", headers=auth)
    assert answer.status_code == 200, answer.content
    status = answer.json()

    answer = client.get(f"/runs/{started['run_id']}/findings", headers=auth)
    assert answer.status_code == 200, answer.content
    findings = answer.json()["items"]

    return {"started": started, "status": status, "findings": findings}


class TestTheFourDeclaredFieldsHaveAProducer:
    """`W17VIEW-1`. Reverting either reader reddens here and nowhere else."""

    def test_every_stage_reports_when_it_started_and_when_it_finished(
        self, published_run: dict[str, Any]
    ) -> None:
        """`started_at` and `finished_at` come back off the wire, on every stage.

        The upsert has written both columns since the first migration and
        `_SELECT_STAGE_RESULTS` did not read them back, so they were write-only and a
        user was shown an em dash for each. Asserted on the response body, because the
        row having the value was never the thing in doubt.
        """
        stages = published_run["status"]["stages"]
        assert {stage["stage_id"] for stage in stages} == EXPECTED_STAGES, stages
        for stage in stages:
            assert stage["status"] == "succeeded", stage
            assert stage.get("started_at"), (
                f"{stage['stage_id']} reports no start; the run screen shows an em dash "
                "for a stage whose row holds a real timestamp"
            )
            assert stage.get("finished_at"), f"{stage['stage_id']} reports no finish"
            started, finished = _instant(stage["started_at"]), _instant(stage["finished_at"])
            assert finished >= started, stage

    def test_the_stage_timings_are_per_stage_and_not_one_repeated_instant(
        self, published_run: dict[str, Any]
    ) -> None:
        """Four stages that ran in sequence report four distinct starts.

        Without this, a reader that answered the *same* timestamp four times -- the
        `W17VIEW-2` failure one aggregate over -- would satisfy the test above.
        """
        starts = {stage["started_at"] for stage in published_run["status"]["stages"]}
        assert len(starts) == len(EXPECTED_STAGES), (
            f"the four stages report {len(starts)} distinct start instants: {sorted(starts)}"
        )

    def test_a_published_run_reports_how_many_findings_it_published(
        self, published_run: dict[str, Any]
    ) -> None:
        """The count, and the count agreeing with the list the same run serves.

        A number that is merely *present* would pass a weaker test; the badge a user
        reads has to be the number of findings they can then open.
        """
        status = published_run["status"]
        assert "published_finding_count" in status, (
            "a published run still reports no finding count, so the run screen reads "
            "'Published findings: not reported'"
        )
        assert status["published_finding_count"] == len(published_run["findings"]), status
        assert status["published_finding_count"] > 0, (
            "the baseline corpus publishes findings; a zero here means the count is "
            "being reported from somewhere that is not this run"
        )

    def test_a_published_run_reports_its_diagnostic_observation_count(
        self, published_run: dict[str, Any]
    ) -> None:
        """Declared by the frozen `RunStatus`, and separately produced.

        It is not a finding count and must not be one: `findings/queries.py` keeps the
        two reads apart by name so they cannot be obtained from a single call.
        """
        status = published_run["status"]
        assert "diagnostic_observation_count" in status, status
        assert isinstance(status["diagnostic_observation_count"], int), status
        assert status["diagnostic_observation_count"] >= 0, status

    def test_start_run_and_get_run_status_report_the_same_four_fields(
        self, published_run: dict[str, Any]
    ) -> None:
        """The frozen document renders both operations with the same `RunStatus`.

        `startRun` builds its body through the same view, so a repair applied to one
        path and not the other would leave the 202 a client actually receives poorer
        than the 200 it polls for.
        """
        started, status = published_run["started"], published_run["status"]
        for field in ("published_finding_count", "diagnostic_observation_count"):
            assert started.get(field) == status.get(field), (field, started, status)
        by_stage = {stage["stage_id"]: stage for stage in status["stages"]}
        for stage in started["stages"]:
            assert stage.get("started_at") == by_stage[stage["stage_id"]].get("started_at")
            assert stage.get("finished_at") == by_stage[stage["stage_id"]].get("finished_at")


class TestTheRunDoesNotBeginAndEndAtTheSameInstant:
    """`W17VIEW-2`, and nothing else. Reverting `statement_timestamp()` reddens here."""

    def test_a_run_that_did_work_reports_a_duration_greater_than_zero(
        self, published_run: dict[str, Any]
    ) -> None:
        """`created_at` and `terminal_at` were identical to the microsecond.

        `now()` is `transaction_timestamp()` and the whole run is one transaction, so
        every duration a client computed was exactly zero -- on runs that really took
        9.9 and 11.1 seconds. This is the first question anyone asks about a model run.
        """
        status = published_run["status"]
        created, terminal = _instant(status["created_at"]), _instant(status["terminal_at"])
        assert terminal > created, (
            "the run reports the same instant for its creation and its terminal, so its "
            f"duration is zero: created_at={status['created_at']} "
            f"terminal_at={status['terminal_at']}"
        )

    def test_the_reported_span_contains_the_work_the_stages_report(
        self, published_run: dict[str, Any]
    ) -> None:
        """The run's own span must cover the stages inside it.

        A `terminal_at` that merely differs from `created_at` could still be an unrelated
        clock. This ties the two aggregates together: the run began before its first
        stage did and ended after its last one did.
        """
        status = published_run["status"]
        created, terminal = _instant(status["created_at"]), _instant(status["terminal_at"])
        starts = [_instant(stage["started_at"]) for stage in status["stages"]]
        finishes = [_instant(stage["finished_at"]) for stage in status["stages"]]
        assert created <= min(starts), (status["created_at"], min(starts).isoformat())
        assert terminal >= max(finishes), (status["terminal_at"], max(finishes).isoformat())
