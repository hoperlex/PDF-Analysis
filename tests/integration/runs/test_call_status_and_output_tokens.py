"""What a truncated provider call becomes in the database, and what the ledger reads back.

Two recorded facts are under test here, and neither is about whether the chain runs.

**1. ``model_call.status`` admitted two values while ``B3``'s provenance emitted three.**
``GATE_B2_CLOSURE.md`` §5.3 records the consequence: the executor mapped ``truncated`` onto
``succeeded`` and kept the provider's real stop reason in ``parameters.call_status``, a
lossless workaround adopted because the CHECK would have refused the row. Lossless is not
the same as correct. The PC-02 report cites this ledger, and a reply cut short at the output
ceiling filed as a clean success is a different product fact from what happened.

**2. Nothing recorded how much the model actually said.** ``P4_CLOSURE.md`` §6: ``PC02-C01``
and ``PC02-C07`` returned after 10 output tokens and ``PC02-C09`` produced 530 and published
nothing. Precision evidence on this corpus is saturated — zero findings across nine
controls — so a finding count of zero has stopped discriminating and the open question
became whether the document was read at all.

Why the truncated fixture is the right instrument for the second one: its recording reports
``usage.output_tokens = 16000`` over 1199 characters of response text. A count recomputed
from that text lands near 300. The provider's figure and any recomputation of it therefore
differ by a factor of fifty on this fixture, which is what lets a test tell them apart
instead of asserting that two numbers happen to be equal.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from auditmanager.analysis.text.config import ProviderMode
from auditmanager.analysis.text.provenance import (
    CALL_STATUSES,
    CALL_SUCCEEDED,
    CALL_TRUNCATED,
    ModelCallRecord,
)
from auditmanager.runs import execute_run, start_audit_run
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ModelCallId

REPO_ROOT = Path(__file__).resolve().parents[3]
TRUNCATED_RECORDING = (
    REPO_ROOT
    / "fixtures/recorded/text_analysis/variants/truncated"
    / "6c208358cfa9ae3a7591223084f87250084c9c6f8070f211d8e2fd9e278dbd1d.json"
)


def _ledger_report() -> ModuleType:
    """The ledger tool, loaded by explicit path.

    ``tools/`` is not on ``pythonpath`` — ``pyproject.toml`` puts only ``src`` there — and
    the root config says a lane that adds ``sys.path`` juggling to a conftest is working
    around the import contract rather than extending it. Loading by path is the mechanism
    ``tests/integration/runs/conftest.py`` already uses for ``harness.py``.
    """
    path = REPO_ROOT / "tools/validation/ledger_report.py"
    spec = importlib.util.spec_from_file_location("w2prov_ledger_report", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["w2prov_ledger_report"] = module
    spec.loader.exec_module(module)
    return module


def _start(session: Session, seeded, key):
    return start_audit_run(
        session,
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded",
        idempotency_key=key,
    )


def _calls(session: Session, run_id: str) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in session.execute(
            text(
                "SELECT model_call_id, status, error_code, response_sha256, "
                "output_tokens, input_tokens, parameters "
                "FROM model_call WHERE run_id = :run_id ORDER BY model_call_id"
            ),
            {"run_id": run_id},
        )
        .mappings()
        .all()
    ]


# ---------------------------------------------------------------------------
# 1. The row a truncated call now writes
# ---------------------------------------------------------------------------


def test_a_truncated_call_is_persisted_as_truncated(
    session: Session, seeded, blob_store, variant_adapter, provider_config, new_key
):
    """The status is written through, not mapped onto a neighbour.

    Asserted against all three members of the closed vocabulary rather than against
    ``truncated`` alone. The defect this replaces mapped the value onto ``succeeded``; the
    obvious wrong repair maps it onto ``failed``, which misdescribes a call that produced
    output and would demand an error code the catalog does not have. Naming both wrong
    answers is what stops this test from passing on either of them.
    """
    started = _start(session, seeded, new_key("truncated-status"))
    result = execute_run(
        session,
        started.run_id,
        blob_store=blob_store,
        adapter=variant_adapter("truncated"),
        provider_config=provider_config,
    )

    rows = _calls(session, started.run_id)
    assert rows, "the run made a provider call and recorded none"
    assert len(rows) == 1
    row = rows[0]

    assert row["status"] == "truncated"
    assert row["status"] != "succeeded", "the pre-0005 map wrote succeeded here"
    assert row["status"] != "failed", "a call that produced output is not a failure"
    assert row["status"] in CALL_STATUSES

    # The stage is partial and the call is truncated. Two different facts about one run,
    # recorded in two places, which is the whole reason the third status was needed.
    assert result.stage_statuses["text_analysis"] == "partial"
    assert result.terminal_state == "partial"


def test_a_truncated_row_carries_a_response_and_no_catalog_error_code(
    session: Session, seeded, blob_store, variant_adapter, provider_config, new_key
):
    """The two properties that distinguish truncation from failure, as written.

    No error code is not a detail. ``GATE_B1_CLOSURE.md`` §4 item 6 is open: the catalog
    has no member meaning "usable output over a strict subset of the input", and inventing
    one here would quietly make a twenty-first code out of a call status.
    """
    started = _start(session, seeded, new_key("truncated-shape"))
    execute_run(
        session,
        started.run_id,
        blob_store=blob_store,
        adapter=variant_adapter("truncated"),
        provider_config=provider_config,
    )

    row = _calls(session, started.run_id)[0]
    assert row["status"] == "truncated"
    assert row["error_code"] is None, "a call status is not an error code"
    assert row["response_sha256"] is not None, "a truncated call answered"
    assert len(row["response_sha256"]) == 64

    # The provider's own stop reason is still kept beside the column. It is redundant for
    # this row and it is what makes a pre-0005 row legible; a key that vanished from new
    # rows would leave the reader unable to tell an old truncated call from an old clean
    # one.
    assert row["parameters"]["call_status"] == "truncated"


def test_the_database_refuses_a_truncated_row_that_claims_an_error_code(
    session: Session, seeded, blob_store, variant_adapter, provider_config, new_key
):
    """``ck_model_call_truncated_has_no_error_code`` can fire, shown by making it fire.

    The constraint is the thing that keeps the open twenty-first-code decision from being
    pre-empted one INSERT at a time, so it is worth knowing it is enforced rather than
    merely declared.
    """
    started = _start(session, seeded, new_key("truncated-code-refused"))
    execute_run(
        session,
        started.run_id,
        blob_store=blob_store,
        adapter=variant_adapter("truncated"),
        provider_config=provider_config,
    )
    row = _calls(session, started.run_id)[0]

    # ``pytest.raises`` outside the savepoint, not inside it: swallowing the error within
    # the block leaves the savepoint aborted and the RELEASE fails instead of the INSERT,
    # which would be a test that goes red for the wrong reason.
    with pytest.raises(DBAPIError) as caught:
        with session.begin_nested():
            session.execute(
                text(
                    "INSERT INTO model_call (model_call_id, run_id, stage_id, provider, "
                    "model_identity, provider_mode, parameters, request_sha256, "
                    "response_sha256, status, error_code) "
                    "SELECT :new_id, run_id, stage_id, provider, model_identity, "
                    "provider_mode, parameters, request_sha256, response_sha256, "
                    "'truncated', 'analysis_failed' "
                    "FROM model_call WHERE model_call_id = :existing"
                ),
                {"new_id": str(ModelCallId.new()), "existing": row["model_call_id"]},
            )
    assert "ck_model_call_truncated_has_no_error_code" in str(caught.value)


def test_the_database_refuses_a_truncated_row_with_no_response(
    session: Session, seeded, blob_store, variant_adapter, provider_config, new_key
):
    """``ck_model_call_truncated_has_response``: a partial answer needs an answer behind it."""
    started = _start(session, seeded, new_key("truncated-no-response"))
    execute_run(
        session,
        started.run_id,
        blob_store=blob_store,
        adapter=variant_adapter("truncated"),
        provider_config=provider_config,
    )
    row = _calls(session, started.run_id)[0]

    # ``pytest.raises`` outside the savepoint, not inside it: swallowing the error within
    # the block leaves the savepoint aborted and the RELEASE fails instead of the INSERT,
    # which would be a test that goes red for the wrong reason.
    with pytest.raises(DBAPIError) as caught:
        with session.begin_nested():
            session.execute(
                text(
                    "INSERT INTO model_call (model_call_id, run_id, stage_id, provider, "
                    "model_identity, provider_mode, parameters, request_sha256, "
                    "response_sha256, status) "
                    "SELECT :new_id, run_id, stage_id, provider, model_identity, "
                    "provider_mode, parameters, request_sha256, NULL, 'truncated' "
                    "FROM model_call WHERE model_call_id = :existing"
                ),
                {"new_id": str(ModelCallId.new()), "existing": row["model_call_id"]},
            )
    assert "ck_model_call_truncated_has_response" in str(caught.value)


def test_a_clean_call_is_still_persisted_as_succeeded(
    session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key
):
    """The counterpart. Widening the vocabulary must not relabel the ordinary case."""
    started = _start(session, seeded, new_key("clean-status"))
    execute_run(
        session,
        started.run_id,
        blob_store=blob_store,
        adapter=recorded_adapter,
        provider_config=provider_config,
    )
    row = _calls(session, started.run_id)[0]
    assert row["status"] == "succeeded"
    assert row["parameters"]["call_status"] == "succeeded"
    assert row["error_code"] is None


# ---------------------------------------------------------------------------
# 2. The provider's figure, not a recomputation of it
# ---------------------------------------------------------------------------


def test_the_output_token_count_is_the_providers_figure_not_a_recomputation(
    session: Session, seeded, blob_store, variant_adapter, provider_config, new_key
):
    """16000 reported over 1199 characters of text. Only one of those can be right.

    The recording is read here as an independent source: the assertion is against the
    number the provider put in its usage block, and explicitly against the numbers any
    plausible recomputation from the response body would produce. A test that merely
    asserted ``output_tokens > 0`` would pass on a recomputation, which is exactly the
    substitution this is here to catch.
    """
    recording = json.loads(TRUNCATED_RECORDING.read_text(encoding="utf-8"))
    reported = recording["usage"]["output_tokens"]
    body = recording["output_text"]

    # Stated rather than assumed: the fixture is only a usable instrument because the two
    # answers are far apart on it.
    assert reported == 16000
    assert len(body) == 1199
    assert reported > 10 * (len(body) // 4), "this fixture cannot discriminate"

    started = _start(session, seeded, new_key("provider-token-figure"))
    execute_run(
        session,
        started.run_id,
        blob_store=blob_store,
        adapter=variant_adapter("truncated"),
        provider_config=provider_config,
    )
    row = _calls(session, started.run_id)[0]

    assert row["output_tokens"] == reported
    assert row["input_tokens"] == recording["usage"]["input_tokens"]
    for recomputation in (len(body), len(body) // 4, len(body.split()), len(body) // 3):
        assert row["output_tokens"] != recomputation, (
            "the stored count equals a figure derived from the response text; the "
            "provider's usage block is the only source this column may carry"
        )


def test_the_stage_emits_the_output_token_count_beside_the_finding_count(
    session: Session, seeded, blob_store, variant_adapter, provider_config, new_key
):
    """Both figures in one metrics block, because neither means much alone.

    Read back out of ``stage_result.metrics`` rather than off the in-memory outcome: the
    ledger reads the row, and a metric that never reached the row is a metric that does
    not exist for the report that will cite it.
    """
    started = _start(session, seeded, new_key("stage-metrics-tokens"))
    execute_run(
        session,
        started.run_id,
        blob_store=blob_store,
        adapter=variant_adapter("truncated"),
        provider_config=provider_config,
    )
    metrics = session.execute(
        text(
            "SELECT metrics FROM stage_result "
            "WHERE run_id = :run_id AND stage_id = 'text_analysis'"
        ),
        {"run_id": started.run_id},
    ).scalar_one()

    recording = json.loads(TRUNCATED_RECORDING.read_text(encoding="utf-8"))
    assert metrics["output_tokens"] == recording["usage"]["output_tokens"]
    assert metrics["input_tokens"] == recording["usage"]["input_tokens"]
    assert metrics["output_tokens_source"] == "provider"
    assert metrics["call_status"] == "truncated"
    # The pair. 16000 output tokens and two observations is the shape P4_CLOSURE §6
    # wanted to be able to see.
    assert "observations_emitted" in metrics
    assert metrics["observations_emitted"] == 2


# ---------------------------------------------------------------------------
# 3. What the ledger reads back, including out of a row written before 0005
# ---------------------------------------------------------------------------


def test_the_ledger_reads_a_pre_migration_truncated_row_as_truncated(
    session: Session, seeded, blob_store, variant_adapter, provider_config, new_key
):
    """A row in the shape the executor wrote before ``0005``, read back correctly.

    The legacy row is **not** hand-written from memory. It is built by taking a real row
    this chain just produced and re-inserting it in the pre-0005 shape — ``status`` mapped
    onto ``succeeded``, the stop reason left where the old executor put it — so the fixture
    is the database's own round-trip of the old behaviour rather than a dict that asserts
    what it was authored to assert. ``model_call`` is immutable by trigger, so this is also
    the only way such a row can exist: nothing rewrites the old ones, and the read side is
    where they have to be understood.
    """
    ledger = _ledger_report()

    started = _start(session, seeded, new_key("legacy-shape"))
    execute_run(
        session,
        started.run_id,
        blob_store=blob_store,
        adapter=variant_adapter("truncated"),
        provider_config=provider_config,
    )
    modern = _calls(session, started.run_id)[0]
    assert modern["status"] == "truncated"

    legacy_id = str(ModelCallId.new())
    session.execute(
        text(
            "INSERT INTO model_call (model_call_id, run_id, stage_id, provider, "
            "model_identity, provider_mode, parameters, request_sha256, response_sha256, "
            "input_tokens, output_tokens, latency_ms, cost_micros, status) "
            "SELECT :new_id, run_id, stage_id, provider, model_identity, provider_mode, "
            "parameters, request_sha256, response_sha256, input_tokens, output_tokens, "
            "latency_ms, cost_micros, 'succeeded' "
            "FROM model_call WHERE model_call_id = :existing"
        ),
        {"new_id": legacy_id, "existing": modern["model_call_id"]},
    )
    legacy = next(
        row for row in _calls(session, started.run_id) if row["model_call_id"] == legacy_id
    )
    assert legacy["status"] == "succeeded", "the pre-0005 column could hold nothing else"
    assert legacy["parameters"]["call_status"] == "truncated"

    status, source, why = ledger.classify_call_status(
        stored_status=legacy["status"], parameters=legacy["parameters"]
    )
    assert status == "truncated", "a legacy truncated call read back as a clean success"
    assert source == "parameters.call_status"
    assert "0005" in why

    # And the modern row is read from the column, so the two sources stay distinguishable.
    status, source, _ = ledger.classify_call_status(
        stored_status=modern["status"], parameters=modern["parameters"]
    )
    assert status == "truncated"
    assert source == "model_call.status"


def test_the_ledger_distinguishes_all_three_statuses_and_names_its_source():
    """The classifier over every shape a row can have, including the ones it must refuse.

    ``parameters`` is a provider-shaped blob, not a second status column: it may rescue a
    status the column provably could not carry and may never overrule one it could. Both
    halves are asserted, because a classifier that simply preferred ``parameters`` would
    pass the legacy case above and quietly let any blob relabel any row.
    """
    ledger = _ledger_report()

    for stored in ("succeeded", "truncated", "failed"):
        status, source, _ = ledger.classify_call_status(
            stored_status=stored, parameters={"call_status": stored}
        )
        assert (status, source) == (stored, "model_call.status")

    # The column could not have said truncated, so parameters is consulted.
    assert ledger.classify_call_status(
        stored_status="succeeded", parameters={"call_status": "truncated"}
    )[:2] == ("truncated", "parameters.call_status")
    assert ledger.classify_call_status(
        stored_status="failed", parameters={"call_status": "truncated"}
    )[:2] == ("truncated", "parameters.call_status")

    # The column could have said anything it liked, so parameters does not overrule it.
    assert ledger.classify_call_status(
        stored_status="truncated", parameters={"call_status": "succeeded"}
    )[:2] == ("truncated", "model_call.status")
    assert ledger.classify_call_status(
        stored_status="failed", parameters={"call_status": "succeeded"}
    )[:2] == ("failed", "model_call.status")
    assert ledger.classify_call_status(
        stored_status="succeeded", parameters={"call_status": "failed"}
    )[:2] == ("succeeded", "model_call.status")

    # Nothing is asserted about a value outside the vocabulary, and it is not rounded
    # into the nearest neighbour.
    unknown, _, why = ledger.classify_call_status(stored_status="cancelled", parameters=None)
    assert unknown == "unknown"
    assert "cancelled" in why

    # Non-mapping and non-string parameters are ignored rather than crashed on.
    assert ledger.classify_call_status(stored_status="succeeded", parameters=None)[0] == (
        "succeeded"
    )
    assert ledger.classify_call_status(
        stored_status="succeeded", parameters={"call_status": 7}
    )[0] == "succeeded"


def test_a_truncated_call_is_not_counted_as_a_provider_failure():
    """The failure ledger separates truncation from an unreachable provider.

    Both shapes of truncated row are put through it — the modern one and the pre-0005 one
    — because the failure ledger reads the derived status, and a version of it reading the
    stored column would file the legacy row as a success and pass a test that only offered
    it the modern one.
    """
    ledger = _ledger_report()

    def call(model_call_id: str, *, status: str, params: dict[str, Any], code: str | None):
        row = {
            "model_call_id": model_call_id,
            "run_id": "run_01AAAAAAAAAAAAAAAAAAAAAAAA",
            "stage_id": "text_analysis",
            "status": status,
            "error_code": code,
            "provider_mode": "recorded",
            "parameters": params,
            "stage_error_message": None,
        }
        status_, source, why = ledger.classify_call_status(
            stored_status=status, parameters=params
        )
        row["call_status"] = status_
        row["call_status_stored"] = status
        row["call_status_source"] = source
        row["call_status_reason"] = why
        row["truncated"] = status_ == "truncated"
        return row

    calls = [
        call("mc_01AAAAAAAAAAAAAAAAAAAAAAAA", status="truncated",
             params={"call_status": "truncated"}, code=None),
        call("mc_01BBBBBBBBBBBBBBBBBBBBBBBB", status="succeeded",
             params={"call_status": "truncated"}, code=None),
        call("mc_01CCCCCCCCCCCCCCCCCCCCCCCC", status="succeeded",
             params={"call_status": "succeeded"}, code=None),
        call("mc_01DDDDDDDDDDDDDDDDDDDDDDDD", status="failed",
             params={"call_status": "failed"}, code="dependency_unavailable"),
    ]

    ledger_rows = ledger.collect_failures(calls, [], [])
    filed = {row["model_call_id"] for row in ledger_rows if row["surface"] == "model_call"}

    assert filed == {"mc_01DDDDDDDDDDDDDDDDDDDDDDDD"}, (
        "only the unreachable provider is a failure; a truncated call answered, in "
        "either the modern or the pre-0005 row shape"
    )


# ---------------------------------------------------------------------------
# 4. The record refuses what the row would refuse
# ---------------------------------------------------------------------------


def _record(**overrides: Any) -> ModelCallRecord:
    fields: dict[str, Any] = {
        "model_call_id": ModelCallId.new(),
        "provider": "anthropic",
        "model_id": "claude-opus-5",
        "provider_mode": ProviderMode.RECORDED,
        "parameters": {},
        "request_sha256": "a" * 64,
        "response_sha256": "b" * 64,
        "input_tokens": 2180,
        "output_tokens": 16000,
        "latency_ms": 42310,
        "status": CALL_TRUNCATED,
        "cost_usd": 0.1,
    }
    fields.update(overrides)
    return ModelCallRecord(**fields)


def test_a_model_call_record_refuses_a_status_outside_the_vocabulary():
    assert _record(status=CALL_SUCCEEDED).status == CALL_SUCCEEDED
    assert _record(status=CALL_TRUNCATED).status == CALL_TRUNCATED

    with pytest.raises(DomainError) as caught:
        _record(status="cancelled")
    assert caught.value.code is ErrorCode.ANALYSIS_FAILED
    assert "closed vocabulary" in str(caught.value)


def test_a_model_call_record_refuses_a_truncated_call_with_no_response():
    """The record-level mirror of ``ck_model_call_truncated_has_response``."""
    with pytest.raises(DomainError) as caught:
        _record(status=CALL_TRUNCATED, response_sha256="")
    assert "no response checksum" in str(caught.value)

    with pytest.raises(DomainError):
        _record(status=CALL_SUCCEEDED, response_sha256="")


def test_a_model_call_record_refuses_a_negative_token_count():
    with pytest.raises(DomainError) as caught:
        _record(output_tokens=-1)
    assert "negative token count" in str(caught.value)
