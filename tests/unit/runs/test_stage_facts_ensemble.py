"""`HOSTS-ENSEMBLE-01`: `getRunStages` over a run whose blocks row is an ensemble -- legs and a judge on one chip.

`HOSTS-SEAL-2` built the reader before the ensemble existed. This file holds it to the ensemble the run now executes: the three cells of the
blocks row are drawn on the «Блоки» chip in role order with their own model and server, every call of the legs and of the judge is counted on
that chip (by the ``stage_key`` of its journal row, or by its ``blocks:N:leg1`` phase when the row is older), the batches stay the unit of
``planned`` and ``completed``, and a leg asked again is a retry while two legs of one batch are not.

No database, no network: the assembly is pure and the journal rows are the dictionaries the SQL would return.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from auditmanager.runs import stage_facts as sf
from auditmanager.runs.stage_facts import CallRow, CellBinding, RunRow, StageRow, assemble_run_stage_facts, chip_of_call, chip_of_phase

RUN = "run_01M2545JSD15ETSNNV904X991K"
T0 = datetime(2026, 11, 10, 9, 0, 0, tzinfo=timezone.utc)
ASTRA, SOL, SOL61 = "gpt-6-astra", "gpt-6-sol", "gpt-6.1-sol"


def at(minutes: float) -> datetime:
    return T0 + timedelta(minutes=minutes)


def cell(key: str, model: str, **extra: Any) -> dict[str, Any]:
    return {"cell_key": key, "model_id": model, "effort": "medium", "access": "subscription", **extra}


# the judge and the legs are listed out of role order on purpose: the reader orders them
PLAN = {"cells": [
    cell("text:main", SOL61),
    cell("blocks:judge", SOL61),
    cell("blocks:leg2", SOL),
    cell("blocks:leg1", ASTRA),
    cell("cross_check:main", SOL),
]}
BINDINGS = {
    "blocks:leg1": CellBinding("adm1.hlab.kz", "subscription"),
    "blocks:leg2": CellBinding("adm2.hlab.kz", "subscription"),
    "blocks:judge": CellBinding("adm1.hlab.kz", "subscription"),
}


def call(cell_key: str, outcome: str = "succeeded", *, n: int, request: str | None = None, start: float = 0.0,
         tokens: tuple[int, int] = (1000, 200), error: str | None = None) -> CallRow:
    """One journal row of a blocks cell: the chip is the row of the layout, the model the cell's, the request what the call asked."""
    model = {"leg1": ASTRA, "leg2": SOL, "judge": SOL61}[cell_key.partition(":")[2]]
    return CallRow(call_id=f"mc_{cell_key}_{n}", chip=chip_of_call("blocks", None), outcome=outcome,
                   request_key=(request or f"sha-{cell_key}-{n}", model), started_at=at(start),
                   finished_at=None if outcome == "in_flight" else at(start + 0.5), input_tokens=tokens[0], output_tokens=tokens[1],
                   cost_micros=0, subscription=True, error_code=error, model_id=model)


def facts_of(calls: list[CallRow], **coverage: Any) -> dict[str, Any]:
    document = assemble_run_stage_facts(
        run=RunRow(RUN, "running", PLAN, None),
        stage_rows=[StageRow("text_analysis", "succeeded", started_at=at(0), finished_at=at(1))],
        calls=calls,
        review={"run_id": RUN, "status": "running", "result": {
            "procedures": [{"id": "block_analysis", "title": "Анализ блоков", "status": "running"}],
            "phase_coverage": {"block_analysis": {"planned": 2, "completed": 1, "remaining": 1, "limit": 2, **coverage}}}},
        cell_bindings=BINDINGS, include_server=True)
    return next(item for item in document["items"] if item["chip"] == "blocks")


def test_the_three_cells_of_the_blocks_row_are_drawn_in_role_order_with_their_model_effort_and_server():
    chip = facts_of([call("blocks:leg1", n=0)])
    assert [(c["cell_key"], c["role"], c["model_id"], c["server"]) for c in chip["plan"]] == [
        ("blocks:leg1", "leg1", ASTRA, "adm1.hlab.kz"), ("blocks:leg2", "leg2", SOL, "adm2.hlab.kz"),
        ("blocks:judge", "judge", SOL61, "adm1.hlab.kz")]
    assert {(c["effort"], c["access"]) for c in chip["plan"]} == {("medium", "subscription")}
    viewer = assemble_run_stage_facts(run=RunRow(RUN, "running", PLAN, None), stage_rows=[], calls=[call("blocks:leg1", n=0)], review=None,
                                      cell_bindings=BINDINGS, include_server=False)
    blocks = next(item for item in viewer["items"] if item["chip"] == "blocks")
    assert all("server" not in c and "access" not in c for c in blocks["plan"]), "the viewer sees no server and no access (`R-150w`)"


def test_every_call_of_every_cell_is_counted_on_the_one_chip_and_the_batches_stay_the_unit_of_coverage():
    # two batches: leg1, leg2, judge each; the second batch's judge is still in flight
    calls = [call(f"blocks:{role}", n=n, start=n * 2 + i, tokens=(1000 + i, 100 + i))
             for n in range(2) for i, role in enumerate(("leg1", "leg2", "judge")) if not (n == 1 and role == "judge")]
    calls.append(call("blocks:judge", "in_flight", n=1, start=4.5, tokens=(0, 0)))
    facts = facts_of(calls)["facts"]
    assert facts["calls_succeeded"] == 5 and facts["calls_failed"] == 0 and facts["calls_retried"] == 0
    assert facts["input_tokens"] == 2 * 1000 + 2 * 1001 + 1002 and facts["output_tokens"] == 2 * 100 + 2 * 101 + 102
    assert facts["subscription_input_tokens"] == facts["input_tokens"], "a subscription cell is counted and never charged"
    assert (facts["planned"], facts["completed"]) == (2, 1), "coverage is the review's own count of batches, not the journal's count of calls"
    assert facts["state"] == "running" and "finished_at" not in facts


def test_a_leg_asked_again_is_a_retry_and_two_legs_of_one_batch_are_not():
    # leg1's first ask is refused (proven not sent) and its second succeeds: one failed call, one retry; leg2 asks a different question of
    # a different model, which is no retry of leg1's
    calls = [call("blocks:leg1", "failed", n=0, request="same", start=0, error="dependency_unavailable"),
             call("blocks:leg1", n=1, request="same", start=1),
             call("blocks:leg2", n=0, start=1.5), call("blocks:judge", n=0, start=2)]
    facts = facts_of(calls)["facts"]
    assert (facts["calls_succeeded"], facts["calls_failed"], facts["calls_retried"]) == (3, 1, 1)
    assert facts["last_error_code"] == "dependency_unavailable"
    # the same request body to the same model is a retry whatever the cell: the key is the request and the model, never the cell
    twins = facts_of([call("blocks:leg1", n=0, request="same"), call("blocks:leg1", n=1, request="same")])["facts"]
    assert twins["calls_retried"] == 1


def test_a_batch_that_lost_a_leg_is_a_partial_chip_whose_reason_is_the_procedures():
    document = assemble_run_stage_facts(
        run=RunRow(RUN, "published", PLAN, None), stage_rows=[],
        calls=[call("blocks:leg1", n=0), call("blocks:judge", n=0, start=1)] + [
            call("blocks:leg2", "failed", n=k, request="r", start=2 + k, error="dependency_unavailable") for k in range(6)],
        review={"run_id": RUN, "status": "partial", "result": {
            "procedures": [{"id": "block_analysis", "title": "Анализ блоков", "status": "partial", "reason": "block_ensemble_leg_failed"}],
            "phase_coverage": {"block_analysis": {"planned": 1, "completed": 0, "remaining": 1, "limit": 2}}}},
        cell_bindings=BINDINGS, include_server=True)
    facts = next(item for item in document["items"] if item["chip"] == "blocks")["facts"]
    assert facts["state"] == "partial" and facts["reason"] == "block_ensemble_leg_failed"
    assert (facts["calls_succeeded"], facts["calls_failed"], facts["calls_retried"]) == (2, 6, 5), "one ask and five more, all failed"
    assert (facts["planned"], facts["completed"]) == (1, 0)


def test_a_leg_the_breaker_skipped_makes_no_call_and_the_chip_counts_only_the_calls_made():
    """D-662: after three failed batches leg1 is no longer asked. Its later batches have no journal row at all; the chip says what the review
    says (a partial batch, the reason `block_ensemble_leg_skipped`) and counts the calls the journal holds, not the ones the plan implies."""
    calls = [call("blocks:leg1", "failed", n=k, request="r", start=k, error="dependency_unavailable") for k in range(6)]     # the batch that failed it
    calls += [call("blocks:leg2", n=0, start=7), call("blocks:judge", n=0, start=8)]
    calls += [call("blocks:leg2", n=1, start=9), call("blocks:judge", n=1, start=10)]     # the batch after it: no leg1 call, so no row
    document = assemble_run_stage_facts(
        run=RunRow(RUN, "published", PLAN, None), stage_rows=[], calls=calls,
        review={"run_id": RUN, "status": "partial", "result": {
            "procedures": [{"id": "block_analysis", "title": "Анализ блоков", "status": "partial", "reason": "block_ensemble_leg_skipped"}],
            "phase_coverage": {"block_analysis": {"planned": 2, "completed": 0, "remaining": 2, "limit": 2}}}},
        cell_bindings=BINDINGS, include_server=True)
    chip = next(item for item in document["items"] if item["chip"] == "blocks")
    assert [c["cell_key"] for c in chip["plan"]] == ["blocks:leg1", "blocks:leg2", "blocks:judge"], "the frozen plan still draws the leg"
    facts = chip["facts"]
    assert (facts["calls_succeeded"], facts["calls_failed"], facts["calls_retried"]) == (4, 6, 5), "no phantom call for the skipped leg"
    assert facts["state"] == "partial" and facts["reason"] == "block_ensemble_leg_skipped"
    assert (facts["planned"], facts["completed"]) == (2, 0)


@pytest.mark.parametrize("phase", [
    "v3:w001:blocks:0:leg1", "v3:w001:blocks:0:leg2", "v3:w001:blocks:3:judge", "v3:w002:blocks:b001:leg1:repair:1",
    "v3:w001:blocks:0:judge:repair:1", "v2:blocks:1:leg2",
])
def test_the_phase_of_an_ensemble_call_is_the_blocks_chip(phase):
    assert chip_of_phase(phase) == "blocks"
    assert chip_of_call(None, {"extended_phase": phase}) == "blocks", "a row older than `stage_key` is placed by its phase"
    assert chip_of_call("blocks", {"extended_phase": "something else"}) == "blocks", "and a row that has one by its stage key"


def test_a_journal_row_of_a_leg_is_read_as_a_call_of_the_blocks_chip():
    row = dict(call_id="mc_1", effect_state="completed", effect_error=None, effect_in=None, effect_out=None, effect_stage_key="blocks",
               effect_access="subscription", effect_parameters={"extended_phase": "v3:w001:blocks:0:leg2"}, request_sha256="r" * 64,
               model_id=SOL, prepared_at=at(0), updated_at=at(1), m_id="mc_1", call_status="succeeded", call_error=None, call_in=900,
               call_out=80, cost_micros=0, cost_basis="unmetered", call_stage_key="blocks", call_access="subscription",
               call_parameters={"extended_phase": "v3:w001:blocks:0:leg2"}, latency_ms=700, call_created_at=at(1))
    parsed = sf._call_from_row(row)
    assert (parsed.chip, parsed.outcome, parsed.model_id, parsed.subscription) == ("blocks", "succeeded", SOL, True)
    assert parsed.request_key == ("r" * 64, SOL)
