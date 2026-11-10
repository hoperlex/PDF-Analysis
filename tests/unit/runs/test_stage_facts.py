"""`RUN-STAGES-01` (contract 1.46.0): the facts of a run's stages, plan and fact, over what the three places hold.

No database, no network: :func:`assemble_run_stage_facts` is pure, and the journal rows are fed to :func:`_call_from_row` as the dictionaries
the SQL would return. Three runs are built here -- a **planned** run (it froze a ``stage_plan`` and was bound cell by cell), a **legacy** run
(it froze none; it started on the route as before) and a run whose journal rows are **old** (written before migration ``0062``: no
``stage_key``, the chip derived from ``parameters ->> 'extended_phase'``) -- and the viewer's reading of each.

Every guard here is shown able to fail: the break-it-once runs of `HOSTS-SEAL-2` plant the defect each guard exists to catch (the omission of the
viewer, the chip map, the plan shape, the journal vocabularies) and record that this file turns red.
"""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from auditmanager.api.schemas import models
from auditmanager.runs import stage_facts as sf
from auditmanager.runs.stage_facts import (
    CHIPS,
    CallRow,
    CellBinding,
    RunBinding,
    RunRow,
    StageRow,
    assemble_run_stage_facts,
    chip_of_call,
    chip_of_phase,
)
from auditmanager.shared.errors import DomainError, ErrorCode

RUN = "run_01M2545JSD15ETSNNV904X991K"
EARLIER = "run_01M2545JSD15ETSNNV904X991M"
T0 = datetime(2026, 11, 10, 9, 0, 0, tzinfo=timezone.utc)


def at(minutes: float) -> datetime:
    return T0 + timedelta(minutes=minutes)


def call(chip: str, outcome: str = "succeeded", *, n: int = 0, request: str | None = None, start: float = 0, end: float | None = 1,
         tokens: tuple[int, int] = (100, 20), cost: int = 0, subscription: bool = False, error: str | None = None,
         model: str = "claude-sonnet-5-5") -> CallRow:
    return CallRow(
        call_id=f"mc_{chip}_{n}", chip=chip, outcome=outcome, request_key=(request or f"sha-{chip}-{n}", model),
        started_at=at(start), finished_at=None if end is None else at(end), input_tokens=tokens[0], output_tokens=tokens[1],
        cost_micros=cost, subscription=subscription, error_code=error, model_id=model,
    )


def cell(key: str, model: str, **extra: Any) -> dict[str, Any]:
    return {"cell_key": key, "model_id": model, "effort": "medium", "access": "subscription", **extra}


PLAN = {"cells": [
    cell("text:main", "claude-sonnet-5-5"),
    cell("blocks:main", "claude-opus-5-5"),
    cell("cross_check:main", "claude-sonnet-5-5"),
    cell("norms:main", "claude-sonnet-5-5", access="api"),
    cell("review:main", "claude-sonnet-5-5"),
    cell("correction:main", "claude-sonnet-5-5"),
]}
BINDINGS = {
    "text:main": CellBinding("adm1.hlab.kz", "subscription"),
    "blocks:main": CellBinding("adm1.hlab.kz", "subscription"),
    "norms:main": CellBinding("api.hlab.kz", "api"),
}
PROCEDURES = [
    {"id": "block_analysis", "title": "Анализ блоков", "status": "running"},
    {"id": "comprehensive_analysis", "title": "Комплексная сверка", "status": "queued"},
    {"id": "finding_merge", "title": "Свод", "status": "queued"},
    {"id": "norm_verification", "title": "Нормы", "status": "queued"},
    {"id": "finding_review", "title": "Критик", "status": "queued"},
    {"id": "finding_correction", "title": "Уточнение", "status": "queued"},
    {"id": "report_generation", "title": "Отчёт", "status": "queued"},
]


def review(procedures: list[dict[str, Any]] | None = None, **result: Any) -> dict[str, Any]:
    return {"run_id": RUN, "status": "running", "result": {"procedures": PROCEDURES if procedures is None else procedures, **result}}


def prep(*, finished: bool = True) -> list[StageRow]:
    ids = ("source_preparation", "page_geometry_extraction", "document_context_build")
    return [StageRow(stage_id, "succeeded", started_at=at(i), finished_at=at(i + 1) if finished else None) for i, stage_id in enumerate(ids)]


def planned(**override: Any) -> dict[str, Any]:
    args: dict[str, Any] = dict(
        run=RunRow(RUN, "running", PLAN, None),
        stage_rows=[*prep(), StageRow("text_analysis", "succeeded", started_at=at(3), finished_at=at(9))],
        calls=[
            call("text", n=0, start=3.2, end=4, tokens=(1000, 200), subscription=True),
            call("text", n=1, start=4, end=5, tokens=(2000, 300), subscription=True),
            call("text", "failed", n=2, request="same", start=5, end=6, error="dependency_unavailable", subscription=True),
            call("text", n=3, request="same", start=6.5, end=9, tokens=(500, 50), subscription=True),
            call("blocks", n=0, start=9.5, end=11, tokens=(4000, 800), subscription=True, model="claude-opus-5-5"),
            call("blocks", "in_flight", n=1, start=11, end=None, tokens=(0, 0), subscription=True, model="claude-opus-5-5"),
            call("norms", n=0, start=12, end=13, tokens=(3000, 400), cost=250000),
        ],
        review=review(phase_coverage={"block_analysis": {"planned": 40, "completed": 12, "remaining": 28, "limit": 40}}),
        cell_bindings=BINDINGS,
        include_server=True,
    )
    args.update(override)
    return assemble_run_stage_facts(**args)


def item(doc: dict[str, Any], chip: str) -> dict[str, Any]:
    return next(entry for entry in doc["items"] if entry["chip"] == chip)


def walk(node: Any) -> Any:
    """Every key of every object in a document."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk(value)


# --- the chips ---------------------------------------------------------------------------------------------------------------


def test_the_chips_are_the_dictionary_of_the_contract_in_the_order_the_rail_draws_them() -> None:
    assert [chip.id for chip in CHIPS] == [value.value for value in models.RunStageChip]
    assert [chip.id for chip in CHIPS][:8] == ["preparation", "text", "blocks", "cross_check", "merge", "norms", "review", "correction"]
    # every row of the layout is one chip, with the same name
    assert {chip.row for chip in CHIPS if chip.row} == {value.value for value in models.StageRowKey}
    assert all(chip.id == chip.row for chip in CHIPS if chip.row)
    assert [chip.id for chip in CHIPS if not chip.calls_model] == ["preparation", "merge"]


def test_every_contract_stage_belongs_to_exactly_one_chip() -> None:
    registry = json.loads((Path(__file__).resolve().parents[3] / "contracts/analysis/v1/stage-registry.json").read_text(encoding="utf-8"))
    stage_ids = {stage["stage_id"] for stage in registry["stages"]}
    covered = [stage_id for chip in CHIPS for stage_id in chip.stage_ids]
    assert len(covered) == len(set(covered))
    assert stage_ids <= set(covered), sorted(stage_ids - set(covered))
    assert set(covered) - stage_ids == {"comprehensive_analysis", "ar_v3_citation_review"}  # a procedure, and the AR v3 stage


def test_the_reused_metric_is_the_one_the_executor_writes() -> None:
    from auditmanager.runs.stage_reuse import REUSED_FROM_METRIC

    assert sf._REUSED_FROM_METRIC == REUSED_FROM_METRIC


# --- a planned run -------------------------------------------------------------------------------------------------------------


def test_a_planned_run_lists_the_chips_it_has_in_order_with_its_frozen_plan_and_its_binding() -> None:
    doc = planned()
    assert (doc["run_id"], doc["state"], doc["plan_source"]) == (RUN, "running", "stage_plan")
    assert [entry["chip"] for entry in doc["items"]] == [
        "preparation", "text", "blocks", "cross_check", "merge", "norms", "review", "correction"]
    assert item(doc, "preparation")["plan"] == [] and item(doc, "merge")["plan"] == []
    assert item(doc, "text")["plan"] == [{
        "cell_key": "text:main", "role": "main", "model_id": "claude-sonnet-5-5", "effort": "medium",
        "access": "subscription", "server": "adm1.hlab.kz"}]
    norms = item(doc, "norms")["plan"][0]
    assert (norms["access"], norms["server"]) == ("api", "api.hlab.kz")
    # a cell that is not bound yet has no server, and keeps the access it froze
    cross = item(doc, "cross_check")["plan"][0]
    assert "server" not in cross and cross["access"] == "subscription"
    # the stage ids a chip covers are the dictionary's
    assert item(doc, "preparation")["stage_ids"] == ["source_preparation", "page_geometry_extraction", "document_context_build"]
    assert item(doc, "cross_check")["stage_ids"] == ["comprehensive_analysis"]
    models.RunStages.model_validate(doc)


def test_the_facts_of_a_chip_count_its_calls_tokens_cost_and_retries() -> None:
    text = item(planned(), "text")["facts"]
    assert (text["calls_succeeded"], text["calls_failed"], text["calls_retried"]) == (3, 1, 1)  # the failed call was repeated once
    assert (text["input_tokens"], text["output_tokens"]) == (3600, 570)
    assert (text["subscription_input_tokens"], text["subscription_output_tokens"]) == (3600, 570) and text["cost_micros"] == 0
    assert text["last_error_code"] == "dependency_unavailable"
    norms = item(planned(), "norms")["facts"]
    assert (norms["input_tokens"], norms["subscription_input_tokens"], norms["cost_micros"]) == (3000, 0, 250000)


def test_a_chip_that_calls_a_model_is_timed_by_its_calls_and_finishes_only_when_none_is_in_flight() -> None:
    text = item(planned(), "text")["facts"]
    assert (text["state"], text["started_at"], text["finished_at"]) == ("done", at(3.2), at(9))  # calls, not the stage's 3 and 9
    blocks = item(planned(), "blocks")["facts"]
    assert blocks["state"] == "running" and blocks["started_at"] == at(9.5) and "finished_at" not in blocks
    assert (blocks["calls_succeeded"], blocks["calls_failed"]) == (1, 0)  # the call in flight is neither


def test_a_chip_with_no_model_is_timed_by_its_stage_results() -> None:
    preparation = item(planned(), "preparation")["facts"]
    assert (preparation["state"], preparation["started_at"], preparation["finished_at"]) == ("done", at(0), at(3))
    assert (preparation["calls_succeeded"], preparation["input_tokens"], preparation["cost_micros"]) == (0, 0, 0)


def test_the_batches_planned_and_completed_come_from_the_reviews_own_coverage() -> None:
    blocks = item(planned(), "blocks")["facts"]
    assert (blocks["planned"], blocks["completed"]) == (40, 12)
    assert "planned" not in item(planned(), "text")["facts"]  # a chip the review keeps no coverage for


def test_the_cross_check_sums_the_windows_and_the_global_phase() -> None:
    coverage = {"comprehensive_analysis": {"planned": 10, "completed": 4}}
    doc = planned(review=review(
        phase_coverage=coverage,
        global_cross_window={"phase_coverage": {"comprehensive_analysis": {"planned": 3, "completed": 1}}}))
    facts = item(doc, "cross_check")["facts"]
    assert (facts["planned"], facts["completed"]) == (13, 5)


def test_a_queued_procedure_is_pending_and_a_call_in_flight_makes_its_chip_running() -> None:
    doc = planned()
    assert item(doc, "cross_check")["facts"]["state"] == "pending"
    running = planned(calls=[call("cross_check", "in_flight", end=None)])
    assert item(running, "cross_check")["facts"]["state"] == "running"


def test_a_chip_the_plan_names_is_listed_before_anything_has_run() -> None:
    doc = assemble_run_stage_facts(run=RunRow(RUN, "queued", PLAN, None), stage_rows=[], calls=[], review=None, cell_bindings={},
                                   include_server=True)
    assert [entry["chip"] for entry in doc["items"]] == ["text", "blocks", "cross_check", "norms", "review", "correction"]
    assert {entry["facts"]["state"] for entry in doc["items"]} == {"pending"}
    assert all("server" not in cell for entry in doc["items"] for cell in entry["plan"])


def test_the_state_of_the_stage_results_is_canonical_for_the_chips_they_cover() -> None:
    failed = planned(stage_rows=[*prep(), StageRow("text_analysis", "failed", error_code="analysis_failed", started_at=at(3), finished_at=at(4))])
    text = item(failed, "text")["facts"]
    assert (text["state"], text["last_error_code"]) == ("failed", "analysis_failed")  # the stage's own code beats a failed call's
    partial = planned(stage_rows=[StageRow("source_preparation", "succeeded", started_at=at(0), finished_at=at(1))])
    assert item(partial, "preparation")["facts"]["state"] == "running"  # one of three, and the run is open
    closed = planned(run=RunRow(RUN, "failed", PLAN, None),
                     stage_rows=[StageRow("source_preparation", "succeeded", started_at=at(0), finished_at=at(1))])
    assert item(closed, "preparation")["facts"]["state"] == "partial"  # one of three, and the run is over


def test_the_procedures_say_the_state_and_the_reason_of_a_chip_the_stage_results_do_not_cover() -> None:
    procedures = [{"id": "norm_verification", "title": "Нормы", "status": "unavailable", "reason": "corpus_unavailable"},
                  {"id": "finding_review", "title": "Критик", "status": "failed", "error_code": "analysis_failed"}]
    doc = planned(review=review(procedures), stage_rows=prep())
    norms, critic = item(doc, "norms")["facts"], item(doc, "review")["facts"]
    assert (norms["state"], norms["reason"]) == ("unavailable", "corpus_unavailable")
    assert (critic["state"], critic["last_error_code"]) == ("failed", "analysis_failed")


def test_a_stage_taken_from_an_earlier_run_is_named_and_not_timed() -> None:
    rows = [StageRow(stage_id, "succeeded", started_at=at(-500), finished_at=at(-499), reused_from_run_id=EARLIER)
            for stage_id in ("source_preparation", "page_geometry_extraction", "document_context_build")]
    facts = item(planned(stage_rows=rows), "preparation")["facts"]
    assert facts["state"] == "done" and facts["reused_from_run_id"] == EARLIER
    assert "started_at" not in facts and "finished_at" not in facts
    mixed = [rows[0], rows[1], StageRow("document_context_build", "succeeded", started_at=at(1), finished_at=at(2))]
    facts = item(planned(stage_rows=mixed), "preparation")["facts"]
    assert "reused_from_run_id" not in facts and (facts["started_at"], facts["finished_at"]) == (at(1), at(2))


# --- a legacy run --------------------------------------------------------------------------------------------------------------


def legacy(**override: Any) -> dict[str, Any]:
    args: dict[str, Any] = dict(
        run=RunRow(RUN, "published", None, RunBinding("kzSonnet", "claude-sonnet-5", "subscription")),
        stage_rows=[*prep(), StageRow("text_analysis", "succeeded", started_at=at(3), finished_at=at(9))],
        calls=[call("text", n=0, start=3.1, end=8.8, subscription=True, model="claude-sonnet-5")],
        review=None, cell_bindings={}, include_server=True,
    )
    args.update(override)
    return assemble_run_stage_facts(**args)


def test_a_run_without_a_stage_plan_has_one_line_from_its_binding_per_chip_that_calls_a_model() -> None:
    doc = legacy()
    assert doc["plan_source"] == "run_binding"
    assert [entry["chip"] for entry in doc["items"]] == ["preparation", "text"]
    assert item(doc, "preparation")["plan"] == []
    assert item(doc, "text")["plan"] == [{"role": "main", "model_id": "claude-sonnet-5", "server": "kzSonnet", "access": "subscription"}]
    models.RunStages.model_validate(doc)


def test_a_legacy_run_with_no_binding_names_the_model_its_journal_names_when_it_names_one() -> None:
    doc = legacy(run=RunRow(RUN, "published", None, None))
    assert item(doc, "text")["plan"] == [{"role": "main", "model_id": "claude-sonnet-5"}]
    several = legacy(run=RunRow(RUN, "published", None, None),
                     calls=[call("text", n=0, model="claude-sonnet-5"), call("text", n=1, model="claude-opus-5")])
    assert item(several, "text")["plan"] == [{"role": "main"}]  # two models: it names neither
    none = legacy(run=RunRow(RUN, "published", None, None), calls=[])
    assert item(none, "text")["plan"] == [{"role": "main"}]


def test_an_extended_legacy_run_lists_the_chips_its_procedures_and_its_old_journal_name() -> None:
    old = [
        call("text", n=0, subscription=True),
        call("blocks", n=0, subscription=True),
        call("cross_check", n=0),
        call("norms", n=0),
    ]
    procedures = [{"id": "block_analysis", "status": "completed", "title": "b"}, {"id": "comprehensive_analysis", "status": "partial",
                  "title": "c", "reason": "approved_phase_call_limit"}]
    doc = legacy(calls=old, review=review(procedures))
    assert [entry["chip"] for entry in doc["items"]] == ["preparation", "text", "blocks", "cross_check", "norms"]
    assert item(doc, "cross_check")["facts"]["state"] == "partial" and item(doc, "cross_check")["facts"]["reason"] == "approved_phase_call_limit"
    assert item(doc, "norms")["facts"]["state"] == "pending"  # called, and no procedure says it ended


def test_a_run_of_the_ar_v3_profile_lists_its_own_chip() -> None:
    rows = [*prep(), StageRow("ar_v3_citation_review", "succeeded", started_at=at(3), finished_at=at(5))]
    doc = legacy(stage_rows=rows, calls=[call("ar_v3", n=0, start=3.1, end=4.9, subscription=True)])
    assert [entry["chip"] for entry in doc["items"]] == ["preparation", "ar_v3"]
    assert item(doc, "ar_v3")["stage_ids"] == ["ar_v3_citation_review"] and item(doc, "ar_v3")["plan"][0]["role"] == "main"


# --- the journal rows of a run written before 0062 -------------------------------------------------------------------------------


@pytest.mark.parametrize(("phase", "chip"), [
    ("blocks:3", "blocks"), ("merge", "merge"),
    ("v2:blocks:b001", "blocks"), ("v2:comprehensive", "cross_check"), ("v2:norm_verification:2", "norms"), ("v2:critic", "review"),
    ("v2:corrector", "correction"),
    ("v3:w001:blocks:b002", "blocks"), ("v3:w014:comprehensive_analysis:b001", "cross_check"),
    ("v3:w002:norm_verification:b003", "norms"), ("v3:w002:finding_review:b001", "review"),
    ("v3:w002:finding_correction:b001:repair:1", "correction"),
    ("v3:global-cross-window:comprehensive_analysis:b004", "cross_check"), ("v3:project-parameters:b001", "cross_check"),
    ("v3:w001:blocks:b002:leg1", "blocks"), ("v3:w001:blocks:b002:judge", "blocks"),  # the ensemble identities of HOSTS-ENSEMBLE-01
])
def test_an_extended_phase_is_placed_on_its_chip_by_the_map(phase: str, chip: str) -> None:
    assert chip_of_phase(phase) == chip
    assert chip_of_call(None, {"extended_phase": phase}) == chip


def test_a_row_with_no_phase_is_a_call_of_the_text_stage_and_an_ar_v3_candidate_is_the_ar_v3_call() -> None:
    assert chip_of_call(None, {"text_window_key": "w001"}) == "text"
    assert chip_of_call(None, None) == "text"
    assert chip_of_call(None, {"ar_v3_candidate_sha256": "0" * 64}) == "ar_v3"


def test_the_stage_key_of_a_new_row_wins_over_everything_else() -> None:
    assert chip_of_call("norms", {"extended_phase": "v2:critic"}) == "norms"
    for row in ("text", "blocks", "cross_check", "norms", "review", "correction"):
        assert chip_of_call(row, {}) == row


@pytest.mark.parametrize(("key", "parameters"), [
    ("merge", {}), ("blocks:main", {}), ("comparison_pairs", {}),
    (None, {"extended_phase": "v3:w001:something_new:b001"}), (None, {"extended_phase": ""}), (None, {"extended_phase": 7}),
])
def test_a_key_or_a_phase_the_map_does_not_know_is_an_integrity_error_never_a_guess(key: str | None, parameters: dict[str, Any]) -> None:
    with pytest.raises(DomainError) as refusal:
        chip_of_call(key, parameters)
    assert refusal.value.code is ErrorCode.STORAGE_INTEGRITY_ERROR


def row(**override: Any) -> dict[str, Any]:
    base: dict[str, Any] = dict(
        call_id="mc_1", effect_state=None, effect_error=None, effect_in=None, effect_out=None, effect_stage_key=None, effect_access=None,
        effect_parameters=None, request_sha256="a" * 64, model_id="claude-sonnet-5", prepared_at=None, updated_at=None, m_id="mc_1",
        call_status="succeeded", call_error=None, call_in=1000, call_out=100, cost_micros=0, cost_basis="unmetered", call_stage_key=None,
        call_access=None, call_parameters={"extended_phase": "v3:w001:blocks:b001"}, latency_ms=2000, call_created_at=at(10),
    )
    base.update(override)
    return base


def test_an_old_model_call_row_with_no_key_and_no_effect_is_placed_by_its_phase_and_read_as_a_subscription_when_unmetered() -> None:
    parsed = sf._call_from_row(row())
    assert (parsed.chip, parsed.outcome, parsed.subscription) == ("blocks", "succeeded", True)
    assert parsed.started_at == at(10) - timedelta(seconds=2) and parsed.finished_at == at(10)
    metered = sf._call_from_row(row(cost_basis="measured", cost_micros=1200))
    assert (metered.subscription, metered.cost_micros) == (False, 1200)
    assert sf._call_from_row(row(cost_basis="measured", call_access="subscription")).subscription is True  # the access of a new row decides
    assert sf._call_from_row(row(cost_basis="unmetered", call_access="api")).subscription is False


def test_an_effect_decides_how_a_call_ended_when_no_model_call_row_exists() -> None:
    def effect(state: str, **extra: Any) -> CallRow:
        return sf._call_from_row(row(m_id=None, call_status=None, call_in=None, call_out=None, cost_micros=None, cost_basis=None,
                                     call_parameters=None, call_created_at=None, latency_ms=None, effect_state=state, prepared_at=at(1),
                                     updated_at=at(2), effect_parameters={"extended_phase": "v2:critic"}, **extra))

    assert {state: effect(state).outcome for state in (
        "completed", "prepared", "response_received", "outcome_unknown", "not_processed", "abandoned")} == {
        "completed": "succeeded", "prepared": "in_flight", "response_received": "in_flight", "outcome_unknown": "failed",
        "not_processed": "failed", "abandoned": "failed"}
    in_flight = effect("prepared")
    assert in_flight.chip == "review" and in_flight.started_at == at(1) and in_flight.finished_at is None
    failed = effect("not_processed", effect_error="dependency_unavailable")
    assert failed.error_code == "dependency_unavailable" and failed.finished_at == at(2)
    received = effect("response_received", effect_in=70, effect_out=9)
    assert (received.input_tokens, received.output_tokens) == (70, 9)  # tokens the provider reported count while the call is open


def test_a_call_status_or_effect_state_the_reader_does_not_know_is_an_integrity_error() -> None:
    with pytest.raises(DomainError):
        sf._call_from_row(row(call_status="reconciled"))
    with pytest.raises(DomainError):
        sf._call_from_row(row(m_id=None, call_status=None, effect_state="reconciled"))


def test_a_truncated_reply_is_a_call_that_succeeded() -> None:
    assert sf._call_from_row(row(call_status="truncated")).outcome == "succeeded"


def test_a_new_row_is_placed_by_its_key_and_an_old_one_in_the_same_run_by_its_phase() -> None:
    new = sf._call_from_row(row(call_stage_key="review", call_access="subscription", call_parameters={"extended_phase": "v3:w001:blocks:b001"}))
    old = sf._call_from_row(row())
    assert (new.chip, old.chip) == ("review", "blocks")
    doc = planned(calls=[new, old])
    assert (item(doc, "review")["facts"]["calls_succeeded"], item(doc, "blocks")["facts"]["calls_succeeded"]) == (1, 1)


def test_a_plan_frozen_before_the_limits_left_is_read_and_shows_neither_of_them() -> None:
    """`LIMITS-01`: a run in flight at the upgrade froze an answer limit and a timeout per cell. They are not shown (the contract's cell has
    neither), and everything else of the cell is as it was."""
    old = {"cells": [{**c, "max_output_tokens": 16000, "timeout_seconds": 900} for c in PLAN["cells"]]}
    doc = planned(run=RunRow(RUN, "running", old, None))
    assert doc == planned()
    for entry in doc["items"]:
        for line in entry["plan"]:
            assert not {"max_output_tokens", "timeout_seconds"} & set(line)


def test_a_call_with_no_chip_in_the_dictionary_refuses_the_whole_answer() -> None:
    with pytest.raises(DomainError):
        planned(calls=[call("nowhere")])


# --- the plan is the run's frozen shape ----------------------------------------------------------------------------------------


@pytest.mark.parametrize("plan", [
    {"cells": "text:main"}, {"nothing": []}, {"cells": [{"model_id": "m"}]}, {"cells": [{"cell_key": "text:other", "model_id": "m"}]},
    {"cells": [cell("text:main", "m", effort="xhigh")]},
    {"cells": [cell("text:main", "m", access="free")]}, {"cells": ["text:main"]},
])
def test_a_malformed_plan_is_an_integrity_error_and_not_a_silently_smaller_plan(plan: Any) -> None:
    with pytest.raises(DomainError) as refusal:
        planned(run=RunRow(RUN, "running", plan, None))
    assert refusal.value.code is ErrorCode.STORAGE_INTEGRITY_ERROR


def test_cells_come_in_the_order_of_their_roles_and_a_row_that_is_no_stage_is_not_drawn() -> None:
    plan = {"cells": [cell("blocks:judge", "j"), cell("blocks:leg2", "b"), cell("blocks:leg1", "a"), cell("comparison_pairs:main", "c"),
                      {"cell_key": "text:main", "model_id": "t"}]}
    doc = planned(run=RunRow(RUN, "running", plan, None), cell_bindings={})
    assert [c["role"] for c in item(doc, "blocks")["plan"]] == ["leg1", "leg2", "judge"]
    assert item(doc, "text")["plan"] == [{"cell_key": "text:main", "role": "main", "model_id": "t"}]  # unknown settings are absent
    assert all(entry["chip"] != "comparison_pairs" for entry in doc["items"])


# --- the viewer reads the stages and not the server nor the access -------------------------------------------------------------------------


@pytest.mark.parametrize("build", [planned, legacy], ids=["planned", "legacy"])
def test_the_viewers_answer_has_neither_server_nor_access_anywhere_and_keeps_everything_else(build: Any) -> None:
    full, viewer = build(), build(include_server=False)
    keys = set(walk(viewer))
    assert "server" not in keys and "access" not in keys
    assert {"server", "access"} <= set(walk(full))  # the expert's answer has them: the omission is not an artefact of the data
    for doc in (full, viewer):
        models.RunStages.model_validate(doc)

    def strip(node: Any) -> Any:
        if isinstance(node, dict):
            return {k: strip(v) for k, v in node.items() if k not in ("server", "access")}
        return [strip(v) for v in node] if isinstance(node, list) else node

    assert strip(full) == viewer  # nothing but those two keys differs: the models, the facts and the order are the same


def test_the_viewer_cell_reads_no_binding() -> None:
    class Forbidden(dict):  # a binding table the viewer's read must not consult
        def get(self, *args: Any) -> Any:  # pragma: no cover - the test is that it is never called
            raise AssertionError("the binding of a cell was looked up for the viewer")

    assert "server" not in set(walk(planned(include_server=False, cell_bindings=Forbidden(BINDINGS))))
