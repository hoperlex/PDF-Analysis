"""`RUN-RESTART-01`: the pure rules of a restart -- the chips, the text a restart takes byte for byte, the price of the chips it computes."""

from __future__ import annotations

from types import SimpleNamespace as NS

import pytest

from auditmanager.analysis.public import ARTIFACT_ROLE as TEXT_OBSERVATIONS_ROLE
from auditmanager.analysis.public import TEXT_STAGE_VERSION
from auditmanager.runs.preflight import RestartPricing
from auditmanager.runs.restart import (
    REASON_TEXT_NOT_REUSABLE, RESTART_POINTS, STAGE_OF_POINT, chips_before, chips_from, kept_procedures_reached_their_end, refusal,
    replay_rows, require_restart_point, takes_preparation, takes_text, untaken_rows,
)
from auditmanager.runs.restart_text import find_saved_text
from auditmanager.runs.repository import StageResultRow
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import derive_blob_id

SHA = "a" * 64


def test_the_eight_chips_are_the_contracts_and_each_names_a_stage() -> None:
    assert RESTART_POINTS == ("preparation", "text", "blocks", "cross_check", "merge", "norms", "review", "correction")
    assert set(STAGE_OF_POINT) == set(RESTART_POINTS)
    for point in RESTART_POINTS:
        assert chips_before(point) + chips_from(point) == RESTART_POINTS and point in chips_from(point) and point not in chips_before(point)


def test_what_a_restart_takes_follows_the_chip() -> None:
    assert [takes_preparation(p) for p in RESTART_POINTS] == [False] + [True] * 7
    assert [takes_text(p) for p in RESTART_POINTS] == [False, False] + [True] * 6
    # A row before the chip makes no call at all (the text row included, from the third chip on); the chip's own row is priced.
    assert untaken_rows("preparation") == frozenset() and untaken_rows("text") == frozenset()
    assert untaken_rows("blocks") == {"text"} and untaken_rows("norms") == {"text", "blocks", "cross_check"}
    assert untaken_rows("correction") == {"text", "blocks", "cross_check", "norms", "review"}
    assert replay_rows("blocks") == frozenset() and "text" not in replay_rows("correction")


def test_a_point_that_is_not_a_chip_is_refused_before_anything_is_read() -> None:
    for bad in ("stage", None, 3, "Text"):
        with pytest.raises(DomainError) as refused:
            require_restart_point(bad)
        assert refused.value.code is ErrorCode.VALIDATION_FAILED and refused.value.detail_fields["field"] == "restart_point"
    assert require_restart_point("norms") == "norms"


def test_a_refusal_names_its_chip_and_the_stage_it_covers_in_the_catalogs_words() -> None:
    error = refusal("restart_reply_missing", "review")
    assert error.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert error.detail_fields == {"stage_id": "finding_review", "reason": "restart_reply_missing", "restart_point": "review"}
    plain = refusal("restart_source_not_v2")
    assert plain.detail_fields == {"stage_id": "text_analysis", "reason": "restart_source_not_v2"}


def test_a_kept_procedure_that_did_not_reach_its_end_is_the_first_chip_that_cannot_be_taken() -> None:
    done = {"extended_block_analysis": "completed", "extended_comprehensive_analysis": "partial", "extended_finding_merge": "completed",
            "extended_norm_verification": "unavailable", "extended_finding_review": "completed"}
    assert kept_procedures_reached_their_end("correction", done) is None
    assert kept_procedures_reached_their_end("blocks", {}) is None, "nothing is kept: nothing is asked of the source"
    for status in ("failed", "running", "queued", "skipped"):
        assert kept_procedures_reached_their_end("review", {**done, "extended_norm_verification": status}) == "norms"
    # A procedure the source never started has no status at all.
    assert kept_procedures_reached_their_end("norms", {"extended_block_analysis": "completed"}) == "cross_check"
    # A chip at or after the restart point is computed, so its source status is not asked.
    assert kept_procedures_reached_their_end("cross_check", {"extended_block_analysis": "completed", "extended_comprehensive_analysis": "failed"}) is None


# -- the text a restart takes ----------------------------------------------------------------------------------------------------------


class _Runs:
    def __init__(self, rows: dict[str, list[StageResultRow]]) -> None:
        self.rows = rows

    def stage_results(self, session, run_id):
        return tuple(self.rows.get(run_id, ()))


class _Blobs:
    def __init__(self, record) -> None:
        self.record = record

    def get(self, session, blob_id):
        return self.record


def _ref(**changes) -> dict:
    return {"role": TEXT_OBSERVATIONS_ROLE, "blob_id": str(derive_blob_id(sha256=SHA, size=10)), "sha256": SHA, "size_bytes": 10,
            "media_type": "application/json", **changes}


def _text_row(**changes) -> StageResultRow:
    base = dict(stage_id="text_analysis", stage_version=TEXT_STAGE_VERSION, status="partial", artifacts=(_ref(),),
                metrics={"pages_total": 8, "pages_analysed": 8, "provider_mode": "recorded", "extended_review_status": "partial"},
                error=None)
    return StageResultRow(**{**base, **changes})


def _find(rows, record=NS(is_available=True, sha256=SHA, size_bytes=10), chain=("run_source",), mode="recorded"):
    import auditmanager.runs.restart_text as module

    original = module.parse_blob_id
    module.parse_blob_id = lambda value: value  # the blob ids here are opaque
    try:
        return find_saved_text(None, chain=chain, provider_mode=mode, runs=_Runs(rows), blobs=_Blobs(record))
    finally:
        module.parse_blob_id = original


def test_the_text_of_a_partial_source_is_taken_although_its_row_is_partial() -> None:
    """``plan_stage_reuse`` would refuse the row (it demands ``succeeded``); only the extended review degraded it, the text was complete."""
    saved = _find({"run_source": [_text_row()]})
    assert saved.run_id == "run_source" and saved.ref.sha256 == SHA and saved.metrics["pages_analysed"] == 8


def test_the_text_is_found_in_the_nearest_run_of_the_chain_that_holds_it() -> None:
    failed_restart = _text_row(status="failed", artifacts=(), metrics={})
    saved = _find({"run_restart": [failed_restart], "run_source": [_text_row()]}, chain=("run_restart", "run_source"))
    assert saved.run_id == "run_source"
    nearest = _find({"run_restart": [_text_row(metrics={**_text_row().metrics, "reused_from_run_id": "run_source"})], "run_source": [_text_row()]},
                    chain=("run_restart", "run_source"))
    assert nearest.run_id == "run_restart", "a restart that took the text holds it by reference: it is the nearest holder"


@pytest.mark.parametrize("name, rows, record, mode", [
    ("no run of the chain made the text", {"run_source": [_text_row(status="failed", artifacts=(), metrics={})]}, NS(is_available=True, sha256=SHA, size_bytes=10), "recorded"),
    ("another stage version", {"run_source": [_text_row(stage_version="0.0.1")]}, NS(is_available=True, sha256=SHA, size_bytes=10), "recorded"),
    ("the blob is gone", {"run_source": [_text_row()]}, None, "recorded"),
    ("the blob is not available", {"run_source": [_text_row()]}, NS(is_available=False, sha256=SHA, size_bytes=10), "recorded"),
    ("another digest", {"run_source": [_text_row()]}, NS(is_available=True, sha256="b" * 64, size_bytes=10), "recorded"),
    ("another size", {"run_source": [_text_row()]}, NS(is_available=True, sha256=SHA, size_bytes=11), "recorded"),
    ("pages missing", {"run_source": [_text_row(metrics={"pages_total": 8, "pages_analysed": 5, "provider_mode": "recorded"})]},
     NS(is_available=True, sha256=SHA, size_bytes=10), "recorded"),
    ("no page count", {"run_source": [_text_row(metrics={"provider_mode": "recorded"})]}, NS(is_available=True, sha256=SHA, size_bytes=10), "recorded"),
    ("another provider mode", {"run_source": [_text_row()]}, NS(is_available=True, sha256=SHA, size_bytes=10), "live"),
])
def test_a_text_that_is_not_the_one_a_full_run_would_have_produced_is_not_taken(name, rows, record, mode) -> None:
    with pytest.raises(DomainError) as refused:
        _find(rows, record=record, mode=mode)
    assert refused.value.detail_fields == {"stage_id": "text_analysis", "reason": REASON_TEXT_NOT_REUSABLE, "restart_point": "text"}, name


# -- the price -------------------------------------------------------------------------------------------------------------------------


def _ledger() -> dict:
    return {"text:main": [1, 1000, 100], "blocks:leg1": [10, 10_000, 1000], "blocks:leg2": [10, 10_000, 1000], "blocks:judge": [10, 10_000, 1000],
            "cross_check:main": [20, 20_000, 2000], "norms:main": [30, 30_000, 3000], "review:main": [40, 40_000, 4000]}


PLAN = NS(cells_of_row=lambda row: {"blocks": (1, 2, 3)}.get(row, (1,)))


def test_the_rows_before_the_chip_are_priced_at_zero_and_keep_their_cells() -> None:
    ledger = _ledger()
    RestartPricing(zero_rows=untaken_rows("norms")).apply(ledger, PLAN)
    assert set(ledger) == set(_ledger()), "the cells stay: the rows the estimate priced are the rows the consent holds"
    assert [ledger[key] for key in ("text:main", "blocks:leg1", "blocks:judge", "cross_check:main")] == [[0, 0, 0]] * 4
    assert ledger["norms:main"] == [30, 30_000, 3000] and ledger["review:main"] == [40, 40_000, 4000]


def test_a_row_the_source_chain_ran_to_its_end_is_bounded_by_the_calls_it_actually_made() -> None:
    ledger = _ledger()
    pricing = RestartPricing(zero_rows=untaken_rows("norms"), completed_rows=frozenset({"norms", "review"}),
                             actual_calls={"norms": 6, "review": 100, "blocks": 3})
    pricing.apply(ledger, PLAN)
    assert ledger["norms:main"] == [6, 6_000, 600], "tokens follow the calls"
    assert ledger["review:main"] == [40, 40_000, 4000], "the estimate stays the bound when the chain made more calls than it priced"


def test_the_calls_of_a_row_are_shared_by_its_cells() -> None:
    ledger = _ledger()
    RestartPricing(zero_rows=frozenset(), completed_rows=frozenset({"blocks"}), actual_calls={"blocks": 9}).apply(ledger, PLAN)
    assert [ledger[key][0] for key in ("blocks:leg1", "blocks:leg2", "blocks:judge")] == [3, 3, 3], "nine calls by three cells: three each"


def test_a_row_the_chain_did_not_finish_keeps_the_estimates_own_bound() -> None:
    ledger = _ledger()
    RestartPricing(zero_rows=frozenset(), completed_rows=frozenset(), actual_calls={"norms": 1}).apply(ledger, PLAN)
    assert ledger == _ledger()


# -- the norm lookups a restart takes instead of asking the corpus again -------------------------------------------------------------------


def _lookup_item(identity: str, **fields) -> dict:
    return {"observation_id": identity, "title": "Сверка", "norm_queries": ["СП 256"], **fields}


def test_the_lookup_is_saved_as_the_answers_of_the_corpus_and_nothing_the_review_adds_after_it() -> None:
    from auditmanager.runs.extended_review import NORM_LOOKUP_RESULTS, _norm_lookup_results

    answered = _lookup_item("xobs_1", norm_status="candidates", norm_reason=None, norm_lookup_method="semantic",
                            norm_candidates=[{"paragraph_id": "p1", "quote": "Цитата"}], norm_query_plan={"queries": ["СП 256"]},
                            norm_review_status="reviewed", norm_assessment={"relation": "supports"}, finding_norm_status="partially_verified")
    saved = _norm_lookup_results([answered], ["norm_lookup_window_exhausted", "norm_lookup_window_exhausted"], [{"observation_id": "xobs_1"}])
    assert NORM_LOOKUP_RESULTS == "norm_lookup_results"
    assert saved["version"] == "norm-lookup-results/1" and saved["warnings"] == ["norm_lookup_window_exhausted"]
    assert saved["items"]["xobs_1"] == {
        "norm_status": "candidates", "norm_reason": None, "norm_lookup_method": "semantic", "norm_candidates": [{"paragraph_id": "p1", "quote": "Цитата"}],
        "norm_query_plan": {"queries": ["СП 256"]}, "norm_review_status": "reviewed"}, "the review's own fields are not the lookup's"
    answered["norm_candidates"].append("mutated")
    assert saved["items"]["xobs_1"]["norm_candidates"] == [{"paragraph_id": "p1", "quote": "Цитата"}], "a copy: later work on the item cannot change it"


def test_a_saved_lookup_is_written_into_the_observations_instead_of_asking_the_corpus() -> None:
    from auditmanager.runs.extended_review import NORM_LOOKUP_RESULTS, _norm_lookup_results, _replay_norm_lookup

    first = [_lookup_item("xobs_1", norm_status="candidates", norm_candidates=[{"paragraph_id": "p1"}], norm_query_plan={"queries": ["a"]}),
             _lookup_item("xobs_2", norm_status="unavailable", norm_reason="lookup_unavailable")]
    saved = _norm_lookup_results(first, ["w"], [{"observation_id": "xobs_1"}, {"observation_id": "xobs_2"}])
    again = [_lookup_item("xobs_1"), _lookup_item("xobs_2")]
    state = {"warnings": ["earlier"]}
    _replay_norm_lookup(again, state, saved)
    assert all("norm_queries" not in item for item in again)
    assert again[0]["norm_status"] == "candidates" and again[0]["norm_candidates"] == [{"paragraph_id": "p1"}]
    assert again[1]["norm_status"] == "unavailable" and again[1]["norm_reason"] == "lookup_unavailable", "a lookup that timed out in the source stays timed out"
    assert state["warnings"] == ["earlier", "w"] and state["norm_lookup_receipts"] == saved["receipts"] and state[NORM_LOOKUP_RESULTS] == saved


def test_an_observation_the_saved_lookup_never_saw_is_a_changed_request_not_a_live_lookup() -> None:
    from auditmanager.runs.extended_review import _norm_lookup_results, _replay_norm_lookup
    from auditmanager.runs.restart import REASON_REQUEST_CHANGED, RestartRefused

    saved = _norm_lookup_results([_lookup_item("xobs_1", norm_status="not_found")], [], [])
    with pytest.raises(RestartRefused) as refused:
        _replay_norm_lookup([_lookup_item("xobs_1"), _lookup_item("xobs_2")], {"warnings": []}, saved)
    assert (refused.value.reason, refused.value.restart_point) == (REASON_REQUEST_CHANGED, "norms")


def test_the_lookup_of_a_run_made_before_this_task_is_not_found_and_the_nearest_run_that_saved_it_wins(monkeypatch) -> None:
    import hashlib
    import json

    import auditmanager.runs.extended_review as module
    from auditmanager.runs.repository import StageResultRow

    def review(result: dict) -> tuple[dict, bytes]:
        raw = json.dumps({"result": result}).encode()
        return {"role": "analysis.extended_review", "blob_id": "blb", "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}, raw

    lookup = {"version": "norm-lookup-results/1", "items": {"xobs_1": {"norm_status": "not_found"}}, "warnings": [], "receipts": []}
    refs = {"run_new": review({"norm_lookup_results": lookup}), "run_old": review({"observations": []}), "run_older": review({"norm_lookup_results": {**lookup, "items": {}}})}

    class Runs:
        current = None

        def stage_results(self, session, run_id):
            Runs.current = run_id
            ref, _ = refs[run_id]
            return (StageResultRow("text_analysis", "v", "partial", (ref,), {}, None),)

    class RunStore:
        def read(self, blob_id, verify=True):
            return refs[Runs.current][1]

    monkeypatch.setattr(module, "RunRepository", lambda: Runs())
    monkeypatch.setattr(module, "parse_blob_id", lambda value: value)
    session = type("Session", (), {"commit": lambda self: None})()
    assert module._saved_norm_lookup_results(session, store=RunStore(), run_ids=("run_new", "run_old")) == lookup
    assert module._saved_norm_lookup_results(session, store=RunStore(), run_ids=("run_old",)) is None, "a run made before this task saved none: the lookup is live"
    assert module._saved_norm_lookup_results(session, store=RunStore(), run_ids=("run_old", "run_older"))["items"] == {}, "the next run of the chain is asked in turn"
