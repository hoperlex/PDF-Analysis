"""``truncated`` from the provider's stop reason to the ledger, the CSV and the API.

Before wave 2 the executor mapped ``truncated`` onto ``succeeded`` and kept the real stop
reason in ``parameters.call_status``: lossless, and wrong, because the PC-02 report reads
the column. ``W2-PROV`` made the column hold the third value. That leaves **two** row
shapes in one long-lived, append-only table, and a read side that must get both right:

* written at or after migration ``0005`` -- ``status='truncated'``;
* written before it -- ``status='succeeded'`` with ``parameters.call_status='truncated'``,
  a pair migration ``0005`` could not repair because the information it would need is in
  the blob, not in the column.

``classify_call_status`` is the read side, and its rule is asymmetric on purpose: the
column is preferred *wherever it could have held the answer*, and the blob is consulted
only where it provably could not. A reader that simply trusted the blob would pass the
legacy case and fail the case that matters more -- a column that was free to disagree and
did.

This file checks both halves **against real rows**, not against dictionaries handed to
the classifier. The legacy shape is materialised by inserting the row the pre-``0005``
executor used to write, over a run this suite really executed, because no code in the
tree can produce that shape any more and a fixture dict would not have to survive the
table's CHECK constraints. Three of those constraints are load-bearing here and the
insert is subject to all of them.

The far end is checked too. A truncated call makes the stage ``partial``; a ``partial``
stage makes the run ``partial``; and ``partial`` must reach the CSV's ``run_state`` column
and the API's run body without being rounded back to ``published`` or down to ``failed``.
A run that published three findings from a reply cut short at the output ceiling is not
the same product fact as one that published three findings from a complete answer.
Mutation evidence
-----------------
Every guard below was shown to fail, against a copy of ``src/`` and ``tools/`` outside the
worktree, proved to be the imported tree before any result was believed, and reverted
afterwards.

==== ============================================================ ==========================
 id   mutation                                                     guards it reddened
==== ============================================================ ==========================
 M2   ``_record_model_calls`` restores the pre-0005 map, writing    stop-reason-reaches-the-
      ``succeeded`` for a truncated call                            column, post-0005-read,
                                                                    two-shapes
 M3   ``parameters.call_status`` dropped from the written row       stop-reason-reaches-the-
                                                                    column
 M4   ``classify_call_status`` loses its legacy branch              legacy-read, two-shapes
 M5   ``classify_call_status`` prefers the blob unconditionally     post-0005-read,
                                                                    not-overruled, two-shapes
 M6   ``RetryPolicy.retries`` returns ``True`` for any error, so    every guard in this file
      a truncated partial is re-asked                                that reads the run
 M13  the export hard-codes ``published`` in ``run_state``          csv-carries-partial
==== ============================================================ ==========================

M4 and M5 are the pair that matters. A read side with only M4 reverted passes the legacy
case; one with only M5 reverted passes the post-0005 case. Only a reader that gets the
asymmetry right passes both, which is why both directions are asserted here.
"""

from __future__ import annotations

import csv
import importlib.util
import io
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

import auditmanager
from auditmanager.runs import execute_run, start_audit_run
from auditmanager.shared.identity import ModelCallId


def _ledger_report() -> ModuleType:
    """The ledger tool, loaded by path **relative to the imported package**.

    ``tools/`` is not on ``pythonpath`` -- ``pyproject.toml`` puts only ``src`` there --
    so it has to be loaded by path. Resolving that path from ``auditmanager.__file__``
    rather than from this test file's location is deliberate and is what makes this
    suite mutable: a run pointed at a scratch copy of the tree with
    ``-o pythonpath=<copy>/src`` gets that copy's ledger tool too, instead of silently
    reading the pristine one beside the test and reporting green.
    """
    tree = Path(auditmanager.__file__).resolve().parents[2]
    path = tree / "tools" / "validation" / "ledger_report.py"
    assert path.is_file(), f"no ledger tool at {path} (tree resolved from {auditmanager.__file__})"
    spec = importlib.util.spec_from_file_location("w2qa_ledger_report", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["w2qa_ledger_report"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def truncated_run(journey_harness, session_factory, blob_store, variant_adapter, provider_config):
    """One run driven by the recorded reply that stops at the output ceiling."""
    h = journey_harness
    with session_factory() as session:
        seed = h.seed_version_with_contract_manifest(session, blob_store, h.new_key("trunc"))
        started = start_audit_run(
            session,
            version_uid=seed["version_uid"],
            analysis_profile_id=str(h.AR_TEXT_PROFILE.analysis_profile_id),
            prompt_bundle_id=str(h.AR_TEXT_PROMPT_BUNDLE.prompt_bundle_id),
            provider_mode="recorded",
            idempotency_key=h.new_key("trunc-run"),
        )
        session.commit()
        execute_run(
            session,
            started.run_id,
            blob_store=blob_store,
            adapter=variant_adapter("truncated"),
            provider_config=provider_config,
        )
        session.commit()
        yield {**seed, "run_id": str(started.run_id)}


@pytest.fixture(scope="module")
def clean_run(journey_harness, session_factory, blob_store, recorded_adapter, provider_config):
    """The control: the same journey over the reply that was not cut short."""
    h = journey_harness
    with session_factory() as session:
        seed = h.seed_version_with_contract_manifest(session, blob_store, h.new_key("clean"))
        run_id = h.run_from_seed(
            session,
            seed,
            blob_store=blob_store,
            adapter=recorded_adapter,
            provider_config=provider_config,
            declared_provider_mode="recorded",
            run_key=h.new_key("clean-run"),
        )
        yield {**seed, "run_id": run_id}


def _one_call(session: Session, run_id: str) -> dict[str, Any]:
    rows = (
        session.execute(
            text(
                "SELECT model_call_id, status, error_code, response_sha256, "
                "output_tokens, parameters FROM model_call WHERE run_id = :r"
            ),
            {"r": run_id},
        )
        .mappings()
        .all()
    )
    assert len(rows) == 1, f"expected one model_call for {run_id}, got {len(rows)}"
    row = dict(rows[0])
    if not isinstance(row["parameters"], dict):
        row["parameters"] = json.loads(row["parameters"])
    return row


# ---------------------------------------------------------------------------
# The column, the blob, and the constraints that bind them
# ---------------------------------------------------------------------------


def test_the_provider_stop_reason_reaches_the_status_column(truncated_run, clean_run, session):
    """Written through, not mapped -- and the control says it is not mapped either way.

    The defect this replaces collapsed ``truncated`` onto ``succeeded``. The obvious
    wrong repair collapses it onto ``failed``, which misdescribes a call that produced
    usable output. Naming the clean run beside it is what stops this passing on a
    persistence layer that writes ``truncated`` for everything.
    """
    cut_short = _one_call(session, truncated_run["run_id"])
    clean = _one_call(session, clean_run["run_id"])

    assert cut_short["status"] == "truncated"
    assert clean["status"] == "succeeded", (
        "the control call is not truncated; a layer that wrote truncated unconditionally "
        "would pass the assertion above and still be wrong"
    )
    assert cut_short["parameters"]["call_status"] == "truncated", (
        "parameters.call_status is the only thing that makes a pre-0005 row legible and "
        "must keep being written, redundant or not"
    )
    assert cut_short["error_code"] is None, (
        "a truncated call carries no error code: the catalog has no code meaning 'usable "
        "output over a strict subset of the input', and ck_model_call_truncated_has_no_"
        "error_code refuses the row that would conflate the two"
    )
    assert cut_short["response_sha256"] is not None, (
        "the provider answered; ck_model_call_truncated_has_response says so"
    )


def test_the_database_refuses_a_truncated_call_carrying_an_error_code(truncated_run, session):
    """The structural half of the claim above, exercised rather than read off a comment.

    Asserted by attempting the write the check exists to refuse. Without this, the test
    above proves only that today's executor happens to pass ``None``, and a future
    executor that passed a code would be caught by nothing.
    """
    from sqlalchemy.exc import DBAPIError

    row = _one_call(session, truncated_run["run_id"])
    with pytest.raises(DBAPIError) as refusal:
        session.execute(
            text(
                "INSERT INTO model_call (model_call_id, run_id, stage_id, provider, "
                "model_identity, provider_mode, parameters, request_sha256, "
                "response_sha256, status, error_code, cost_basis) "
                "VALUES (:id, :r, 'text_analysis', 'anthropic', 'claude-opus-5', "
                "'recorded', CAST(:p AS jsonb), :req, :resp, 'truncated', "
                "'analysis_failed', 'estimated')"
            ),
            {
                "id": str(ModelCallId.new()),
                "r": truncated_run["run_id"],
                "p": json.dumps({"call_status": "truncated"}),
                "req": "a" * 64,
                "resp": row["response_sha256"],
            },
        )
    assert "ck_model_call_truncated_has_no_error_code" in str(refusal.value)
    session.rollback()


# ---------------------------------------------------------------------------
# The read side, over both row shapes, both of them real
# ---------------------------------------------------------------------------


def test_a_post_0005_truncated_row_is_read_from_the_column(truncated_run, session):
    ledger = _ledger_report()
    row = _one_call(session, truncated_run["run_id"])
    status, source, why = ledger.classify_call_status(
        stored_status=row["status"], parameters=row["parameters"]
    )
    assert status == "truncated"
    assert source == "model_call.status", (
        "the column carried the answer, so nothing may have been taken from the blob"
    )
    assert "0005" in why


@pytest.fixture(scope="module")
def legacy_row(truncated_run, session_factory) -> str:
    """The shape migration ``0005`` could not repair, materialised as a real row.

    The pre-``0005`` executor wrote ``succeeded`` in the column because the CHECK refused
    ``truncated``, and kept the provider's stop reason in ``parameters.call_status``. No
    code in this tree writes that shape any more, so it is inserted here -- through the
    same table and subject to the same constraints as any other row, which is the part a
    fixture dictionary could not have proved.

    A fixture rather than a step inside one test, so the two tests that need this shape
    do not depend on each other's execution order.
    """
    with session_factory() as session:
        template = _one_call(session, truncated_run["run_id"])
        legacy_id = str(ModelCallId.new())
        session.execute(
            text(
                "INSERT INTO model_call (model_call_id, run_id, stage_id, provider, "
                "model_identity, provider_mode, parameters, request_sha256, "
                "response_sha256, input_tokens, output_tokens, status, error_code, "
                "cost_basis) VALUES (:id, :r, 'text_analysis', 'anthropic', "
                "'claude-opus-5', 'recorded', CAST(:p AS jsonb), :req, :resp, 4096, "
                "16000, 'succeeded', NULL, 'estimated')"
            ),
            {
                "id": legacy_id,
                "r": truncated_run["run_id"],
                "p": json.dumps({"call_status": "truncated", "max_tokens": 16000}),
                "req": "b" * 64,
                "resp": template["response_sha256"],
            },
        )
        session.commit()
    return legacy_id


def test_a_legacy_truncated_row_is_read_from_the_parameters_blob(legacy_row, session):
    """A pre-``0005`` truncated call must not read back as a clean success."""
    ledger = _ledger_report()
    stored = (
        session.execute(
            text("SELECT status, parameters FROM model_call WHERE model_call_id = :id"),
            {"id": legacy_row},
        )
        .mappings()
        .one()
    )
    parameters = stored["parameters"]
    if not isinstance(parameters, dict):
        parameters = json.loads(parameters)
    assert stored["status"] == "succeeded", (
        "the legacy shape is the point of this test; the row did not survive as written"
    )

    status, source, why = ledger.classify_call_status(
        stored_status=stored["status"], parameters=parameters
    )
    assert status == "truncated", (
        "a legacy truncated call read back as a clean success; every reply cut short at "
        "the output ceiling before migration 0005 would be filed as a complete answer"
    )
    assert source == "parameters.call_status"
    assert "before migration 0005" in why



def test_the_column_is_not_overruled_where_it_could_have_disagreed(truncated_run, session):
    """The asymmetry, which is the whole difficulty of reading two row shapes.

    A reader that simply preferred ``parameters.call_status`` would pass the legacy test
    above and be wrong here: a row whose column says ``succeeded`` and whose blob says
    ``succeeded`` is clean, and a blob saying anything other than ``truncated`` is a
    provider-shaped detail, not a second status column. Both directions are asserted
    because the failure mode is a reader that picks one source and applies it to
    everything.
    """
    ledger = _ledger_report()

    clean_status, clean_source, _ = ledger.classify_call_status(
        stored_status="succeeded", parameters={"call_status": "succeeded"}
    )
    assert (clean_status, clean_source) == ("succeeded", "model_call.status")

    noise_status, _, _ = ledger.classify_call_status(
        stored_status="succeeded", parameters={"call_status": "stop_sequence", "max_tokens": 8}
    )
    assert noise_status == "succeeded", (
        "an unrecognised provider stop reason was promoted to a status; parameters is a "
        "blob, not a second status column"
    )

    truncated_column, source, _ = ledger.classify_call_status(
        stored_status="truncated", parameters={"call_status": "succeeded"}
    )
    assert (truncated_column, source) == ("truncated", "model_call.status"), (
        "the column was free to say succeeded and said truncated; the blob may not "
        "overrule it"
    )


def test_the_ledger_counts_the_two_shapes_separately_over_the_real_table(
    truncated_run, legacy_row, session
):
    """The extraction, end to end, over rows this suite really wrote.

    ``truncated_rows_read_from_parameters`` exists so that a reader can see how much of
    the truncated population is legacy. If it ever reaches zero while legacy rows are
    present, the read side has quietly stopped consulting the blob -- and the ledger's
    own summary is where that becomes visible.
    """
    ledger = _ledger_report()
    rows = (
        session.execute(
            text(
                "SELECT status, parameters FROM model_call WHERE run_id = :r "
                "ORDER BY model_call_id"
            ),
            {"r": truncated_run["run_id"]},
        )
        .mappings()
        .all()
    )
    classified = []
    for row in rows:
        parameters = row["parameters"]
        if not isinstance(parameters, dict):
            parameters = json.loads(parameters)
        classified.append(
            ledger.classify_call_status(stored_status=row["status"], parameters=parameters)
        )
    statuses = [entry[0] for entry in classified]
    sources = [entry[1] for entry in classified]

    assert statuses.count("truncated") == len(rows) >= 2, (
        "this run carries the post-0005 row the executor wrote and the pre-0005 row the "
        f"legacy test inserted; both are truncated. got {statuses}"
    )
    assert sorted(sources) == ["model_call.status", "parameters.call_status"], (
        "the two shapes must be read from different sources; reading both from one means "
        f"one of them is being guessed. got {sources}"
    )


# ---------------------------------------------------------------------------
# The far end: the terminal, the CSV and the API
# ---------------------------------------------------------------------------


def test_a_truncated_call_makes_the_run_partial_and_not_published(
    truncated_run, clean_run, session
):
    cut_short = (
        session.execute(
            text("SELECT state, degradation_set FROM audit_run WHERE run_id = :r"),
            {"r": truncated_run["run_id"]},
        )
        .mappings()
        .one()
    )
    clean = (
        session.execute(
            text("SELECT state, degradation_set FROM audit_run WHERE run_id = :r"),
            {"r": clean_run["run_id"]},
        )
        .mappings()
        .one()
    )
    assert cut_short["state"] == "partial", (
        f"a reply cut short reached {cut_short['state']!r}; truncated was flattened"
    )
    assert "text_analysis" in list(cut_short["degradation_set"] or ()), (
        "the degradation set must name the stage that degraded, or a reader cannot tell "
        "which part of the document was not analysed"
    )
    assert clean["state"] == "published"
    assert not clean["degradation_set"]

    stage = (
        session.execute(
            text(
                "SELECT status FROM stage_result "
                "WHERE run_id = :r AND stage_id = 'text_analysis'"
            ),
            {"r": truncated_run["run_id"]},
        )
        .scalar_one()
    )
    assert stage == "partial", (
        "the stage that consumed a truncated call is partial; the call itself is "
        "truncated; the two are separate facts and neither may be flattened into the "
        f"other. stage={stage!r}"
    )


def test_the_csv_carries_partial_rather_than_rounding_it_to_published(
    truncated_run, clean_run, session
):
    """``run_state`` is column five of the frozen export and it is where this shows.

    Both exports are read, because the discriminating fact is that they differ: a CSV
    writer that hard-coded ``published``, or one that dropped a non-published run's rows
    entirely, would be caught by exactly one of the two assertions.
    """
    from auditmanager.exports import COLUMNS, export_run_csv

    def states(run_id: str) -> list[str]:
        content = export_run_csv(session, run_id).content
        rows = [r for r in csv.reader(io.StringIO(content[3:].decode("utf-8"))) if r]
        header, data = rows[0], rows[1:]
        assert tuple(header) == tuple(COLUMNS)
        return [row[header.index("run_state")] for row in data]

    cut_short = states(truncated_run["run_id"])
    clean = states(clean_run["run_id"])

    assert cut_short, (
        "the partial run exported no rows at all; findings grounded from a truncated "
        "reply are published findings and belong in the export"
    )
    assert set(cut_short) == {"partial"}, set(cut_short)
    assert set(clean) == {"published"}, set(clean)


def test_the_api_run_body_reports_partial_through_the_shipped_adapter(
    truncated_run, session_factory
):
    """Through the real router over the real ``RunAdapter``, not a suite-local double.

    ``tests/integration/api`` satisfies ``RunPort`` with an adapter of its own, written
    against the frozen declaration, so nothing in that suite can tell whether the
    shipped one reports the same thing. This dispatches a real request at the adapter
    the composition root wires.
    """
    from auditmanager.api.routers import build_router
    from auditmanager.bootstrap.adapters import (
        DecisionAdapter,
        CsvExportAdapter,
        FindingAdapter,
        RunAdapter,
    )
    from auditmanager.runs import InlineCarrier

    router = build_router(
        projects=None,
        documents=None,
        runs=RunAdapter(
            session_factory,
            blob_store=None,
            adapter=None,
            provider_config=None,
            provider_mode="recorded",
            analysis_profile_id="unused",
            prompt_bundle_id="unused",
            # `D-20`. This dispatches reads at the shipped adapter and starts no run.
            carrier=InlineCarrier(),
        ),
        findings=FindingAdapter(session_factory),
        decisions=DecisionAdapter(session_factory),
        exports=CsvExportAdapter(session_factory),
    )
    response = _request(router, f"/runs/{truncated_run['run_id']}")
    assert response.status_code == 200, response.content
    body = json.loads(response.content)
    assert body["state"] == "partial", (
        f"the API reports {body['state']!r} for a run whose model reply was cut short"
    )
    assert "text_analysis" in body.get("degradation_set", []), body
    stages = {stage["stage_id"]: stage["status"] for stage in body["stages"]}
    assert stages["text_analysis"] == "partial", stages


#: `T-6`. The credential this module configures and presents, as a literal.
_STATIC_TOKEN = "p02-journey-static-token"


class _Built:
    """Just enough of ``Application`` for ``create_asgi_app`` to take a router as given."""

    __slots__ = ("router",)

    def __init__(self, router: Any) -> None:
        self.router = router


def _client(router: Any) -> Any:
    """An ASGI client over the real application, wrapping the shipped-adapter router.

    Re-pointed by `W13-API`: ``Request.build`` plus ``dispatch`` are gone with
    ``routers/http.py``. This module's question is unchanged -- does the *shipped* adapter
    answer the same thing the suite adapters do -- and it is now asked over the transport
    that actually serves.
    """
    from starlette.testclient import TestClient

    from auditmanager.api.app import create_asgi_app
    from auditmanager.api.security import API_TOKEN_VARIABLE

    app = create_asgi_app(
        environ={API_TOKEN_VARIABLE: _STATIC_TOKEN}, application=_Built(router)
    )
    return TestClient(app, raise_server_exceptions=False)


def _request(router: Any, target: str) -> Any:
    return _client(router).get(
        target, headers={"Authorization": f"Bearer {_STATIC_TOKEN}"}
    )
