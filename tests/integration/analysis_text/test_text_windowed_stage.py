"""`SECTION-CHUNKED-ANALYSIS-01`: ``run_text_analysis_windows`` over scripted adapters, no container.

A volume above the one-call budget is analysed in whole-page windows, one call each, under one cost
ceiling, with a journal entry per window and a restart that does not pay for a finished window twice. The
stage is driven here with a scripted adapter (it answers a window request by quoting one place on the first page
it was shown, so the findings can be checked against the saved text), a journal that records what it was
told, and a custody that keeps what it is given: the database and blob store versions of the same cases are
``tests/integration/runs/test_text_windows_executor.py``.
"""

from __future__ import annotations

import json
import re
from typing import Any

import pytest

from auditmanager.analysis.text import (
    CostMeter,
    ModelResponse,
    ProviderConfig,
    ProviderMode,
    load_text_layer,
    run_text_analysis,
)
from auditmanager.analysis.text.proxy import ProxyDispatchError
from auditmanager.analysis.text.stage import STATUS_FAILED, STATUS_PARTIAL, STATUS_SUCCEEDED
from auditmanager.analysis.text.windowed import run_text_analysis_windows
from auditmanager.analysis.text.windows import (
    PARAM_KEY,
    PARAM_REPLY_BLOB_ID,
    PARAM_REPLY_BLOB_SHA256,
    PARAM_REPLY_BLOB_SIZE,
    RecoveredWindow,
    WINDOWS_NOTE,
    WindowPolicy,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ModelCallId, RunId
from tests.support.v1_reference_profile import V1_REFERENCE_PROFILE

PAGE = "Страница {n}. Высота потолка {n} м. Дверь {n}."
PAGE_LENGTH = len(PAGE.format(n=1))
#: Three pages fit one window; four do not: nine pages are three windows.
THREE_PAGES = WindowPolicy(window_characters=3 * PAGE_LENGTH + 5, max_windows=12)
BANNER = re.compile(r"=== Страница (\d+) ===")


def layer_document(count: int = 9) -> dict[str, Any]:
    pages, offset = [], 0
    for number in range(1, count + 1):
        body = PAGE.format(n=number)
        pages.append({
            "page_number": number, "char_start": offset, "char_end": offset + len(body), "text": body,
        })
        offset += len(body)
    return {
        "artifact_role": "prepared.text_layer", "artifact_version": "1.0.0",
        "version_uid": "ver_01M2545JSD15ETSNNV904X991J",
        "normalization": {"id": "nfc_v1", "description": "NFC"},
        "total_char_count": offset, "pages": pages,
    }


def config(ceiling: float = 1.0) -> ProviderConfig:
    return ProviderConfig(
        mode=ProviderMode.RECORDED, model_id="claude-opus-5", run_cost_ceiling_usd=ceiling,
        api_key=None, ceiling_is_explicit=True,
    )


def reply(observations: list[dict[str, Any]], *, stop_reason: str = "end_turn", cost: float = 0.1) -> ModelResponse:
    return ModelResponse(
        output_text=json.dumps({"observations": observations}, ensure_ascii=False),
        stop_reason=stop_reason, input_tokens=100, output_tokens=10, latency_ms=5,
        reported_cost_usd=cost,
    )


def observation(page: int, quote: str | None = None) -> dict[str, Any]:
    return {
        "category": "internal_contradiction",
        "finding_text": f"Расхождение на странице {page}",
        "recommendation_text": "Согласовать значение",
        "evidence": [{"page_number": page, "quote": quote or f"Высота потолка {page} м"}],
    }


class Scripted:
    """Answers each window request; ``overrides`` maps the window's first page to a response or an error."""

    def __init__(
        self, mode: ProviderMode = ProviderMode.RECORDED, *, cost: float = 0.1,
        overrides: dict[int, Any] | None = None,
    ) -> None:
        self._mode = mode
        self._cost = cost
        self._overrides = overrides or {}
        self.pages_seen: list[list[int]] = []

    @property
    def provider_mode(self) -> ProviderMode:
        return self._mode

    @property
    def calls(self) -> int:
        return len(self.pages_seen)

    def complete(self, request: Any) -> ModelResponse:
        pages = [int(n) for n in BANNER.findall(request.body["messages"][0]["content"])]
        self.pages_seen.append(pages)
        outcome = self._overrides.get(pages[0])
        if isinstance(outcome, BaseException):
            raise outcome
        if callable(outcome):
            return outcome(pages)
        if outcome is not None:
            return outcome
        return reply([observation(pages[0])], cost=self._cost)


class World:
    """The call journal and the window custody the executor supplies, in memory."""

    def __init__(self) -> None:
        self.events: list[tuple[str, str]] = []
        self.records: list[Any] = []
        self.completed: dict[str, RecoveredWindow] = {}
        self.preserved: list[str] = []
        self._answers: dict[str, ModelResponse] = {}
        self.recover_calls = 0

    # the journal
    def prepare(self, request: Any, *, mode: ProviderMode) -> ModelCallId:
        call_id = ModelCallId.new()
        self.events.append(("prepare", str(call_id)))
        return call_id

    def response_received(self, call_id: ModelCallId, response: Any) -> None:
        self.events.append(("response_received", str(call_id)))

    def complete(self, call: Any) -> None:
        self.events.append(("complete", str(call.model_call_id)))
        self.records.append(call)
        key = call.parameters.get(PARAM_KEY)
        if key is not None and str(call.model_call_id) in self._answers:
            self.completed[key] = RecoveredWindow(call.model_call_id, self._answers[str(call.model_call_id)])

    def outcome_unknown(self, call_id: ModelCallId, error: DomainError) -> None:
        self.events.append(("outcome_unknown", str(call_id)))

    def not_processed(self, call_id: ModelCallId, error: DomainError, dispatch_class: str) -> None:
        self.events.append(("not_processed", str(call_id)))

    # the custody
    def recover(self, key: str) -> RecoveredWindow | None:
        self.recover_calls += 1
        return self.completed.get(key)

    def preserve(self, *, model_call_id: ModelCallId, window: Any, request: Any, response: ModelResponse) -> dict[str, Any]:
        self._answers[str(model_call_id)] = response
        self.preserved.append(window.key)
        return {
            PARAM_REPLY_BLOB_ID: "blob_" + "0" * 26,
            PARAM_REPLY_BLOB_SHA256: "0" * 64,
            PARAM_REPLY_BLOB_SIZE: 1,
        }


def run(
    adapter: Any, *, world: World | None = None, document: dict[str, Any] | None = None,
    policy: WindowPolicy = THREE_PAGES, meter: CostMeter | None = None, ceiling: float = 1.0,
    custody: bool = True, journal: bool = True, call: Any = None,
):
    world = world if world is not None else World()
    return run_text_analysis_windows(
        run_id=RunId.new(), text_layer_document=document or layer_document(), adapter=adapter,
        config=config(ceiling), profile=V1_REFERENCE_PROFILE, policy=policy,
        meter=meter, call_journal=world if journal else None,
        custody=world if custody else None, call=call,
    ), world


# -- every window is read, and every quote binds where it would in a single call ---------------


def test_a_three_window_text_yields_findings_from_all_three_with_global_offsets_that_bind() -> None:
    adapter = Scripted()
    outcome, world = run(adapter)

    assert outcome.status == STATUS_SUCCEEDED and outcome.error is None
    assert adapter.pages_seen == [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    layer = load_text_layer(layer_document())
    observations = outcome.artifact["observations"]
    assert [o["evidence"][0]["page_number"] for o in observations] == [1, 4, 7]
    assert [o["observation_ordinal"] for o in observations] == [0, 1, 2]
    for item in (o["evidence"][0] for o in observations):
        # The offsets are the document's: the slice of the whole sequence is the quote.
        assert layer.slice(item["char_start"], item["char_end"]) == item["quote"]
        assert layer.page(item["page_number"]).contains(item["char_start"], item["char_end"])
    assert observations[1]["evidence"][0]["char_start"] >= layer.pages[3].char_start > 0
    assert observations[2]["evidence"][0]["char_start"] >= layer.pages[6].char_start

    # One call, one model_call, one id per window; each observation names its own window's call.
    call_ids = [o["model_call_id"] for o in observations]
    assert len(set(call_ids)) == 3 == len(world.records)
    assert call_ids == [str(record.model_call_id) for record in world.records]
    assert outcome.artifact["pages_analysed"] == list(range(1, 10))


def test_the_run_says_the_windows_were_analysed_independently() -> None:
    outcome, _ = run(Scripted())
    metrics = outcome.metrics
    assert metrics["windows_total"] == 3 and metrics["windows_analysed"] == 3
    assert metrics["windows_recovered"] == 0 and metrics["windows_independent"] is True
    assert metrics["windows_note"] == WINDOWS_NOTE and "каждое окно проверено отдельно" in WINDOWS_NOTE
    assert metrics["window_characters_ceiling"] == THREE_PAGES.window_characters
    assert metrics["windows_limit"] == 12
    assert "request_sha256" not in metrics and len(metrics["windows_request_sha256"]) == 64
    assert all(isinstance(v, (str, int, float, bool, type(None))) for v in metrics.values())


def test_every_fresh_window_is_one_journal_entry_with_its_identity_and_reply_reference() -> None:
    _, world = run(Scripted())
    kinds = [kind for kind, _ in world.events]
    assert kinds == ["prepare", "response_received", "complete"] * 3
    assert len(world.preserved) == 3
    for index, record in enumerate(world.records):
        parameters = record.parameters
        assert parameters[PARAM_KEY] == world.preserved[index]
        assert parameters["text_window_index"] == index and parameters["text_window_count"] == 3
        assert parameters[PARAM_REPLY_BLOB_ID].startswith("blob_")
        assert parameters["max_tokens"] and parameters["thinking"] and parameters["output_config"]


def test_a_claim_on_a_page_outside_its_window_is_dropped_and_counted_never_published() -> None:
    adapter = Scripted(overrides={
        1: reply([observation(1), observation(5, "Высота потолка 5 м")]),  # page 5 is window 2's
    })
    outcome, _ = run(adapter)
    assert outcome.status == STATUS_SUCCEEDED
    pages = [o["evidence"][0]["page_number"] for o in outcome.artifact["observations"]]
    assert pages == [1, 4, 7], "the stray claim is not published"
    assert outcome.metrics["evidence_outside_window"] == 1
    assert outcome.metrics["observations_dropped_unresolved"] == 1


def test_a_quote_not_in_the_text_is_dropped_like_a_single_call_drops_it() -> None:
    adapter = Scripted(overrides={4: reply([observation(4, "такой фразы в тексте нет")])})
    outcome, _ = run(adapter)
    assert outcome.status == STATUS_SUCCEEDED
    assert [o["evidence"][0]["page_number"] for o in outcome.artifact["observations"]] == [1, 7]
    assert outcome.metrics["observations_dropped_unresolved"] == 1
    assert outcome.metrics["evidence_unresolved"] == 1


# -- one window is the single call, byte for byte ------------------------------------------------


def test_a_text_that_fits_one_window_is_the_single_call_and_publishes_the_same_artifact() -> None:
    document = layer_document()
    huge = WindowPolicy(window_characters=10**6, max_windows=12)
    windowed_adapter, single_adapter = Scripted(), Scripted()
    windowed, windowed_world = run(windowed_adapter, document=document, policy=huge)
    single = run_text_analysis(
        run_id=RunId.new(), text_layer_document=document, adapter=single_adapter, config=config(),
        profile=V1_REFERENCE_PROFILE, call_journal=World(),
    )
    assert windowed_adapter.calls == single_adapter.calls == 1
    assert windowed_adapter.pages_seen == single_adapter.pages_seen == [list(range(1, 10))]
    assert windowed.status == single.status == STATUS_SUCCEEDED

    def stripped(outcome):
        document = json.loads(json.dumps(outcome.artifact))
        document.pop("run_id")
        for item in document["observations"]:
            item.pop("model_call_id")
        return document

    assert stripped(windowed) == stripped(single)
    assert {k: v for k, v in windowed.metrics.items()} == {k: v for k, v in single.metrics.items()}
    assert "windows_total" not in windowed.metrics, "a single window carries no window metrics"
    assert windowed_world.preserved == [], "a single window writes no custody"
    assert PARAM_KEY not in windowed_world.records[0].parameters


# -- a finished window is not paid for twice -------------------------------------------------------


def test_a_second_call_recovers_finished_windows_and_calls_only_the_rest() -> None:
    first_adapter = Scripted(overrides={4: ProxyDispatchError(
        ErrorCode.DEPENDENCY_UNAVAILABLE, dispatch_class="not_sent", retry_safe=True,
        message="the model proxy could not be reached",
    )})
    failed, world = run(first_adapter)
    assert failed.status == STATUS_FAILED and failed.provider_retry_allowed is True
    assert first_adapter.pages_seen == [[1, 2, 3], [4, 5, 6]]
    assert failed.metrics["windows_completed"] == 1 and failed.metrics["failed_window"] == 2
    assert world.events[-1][0] == "not_processed"

    second_adapter = Scripted()
    done, _ = run(second_adapter, world=world, meter=CostMeter(ceiling_usd=1.0, spent_usd=0.1))
    assert done.status == STATUS_SUCCEEDED
    assert second_adapter.pages_seen == [[4, 5, 6], [7, 8, 9]], "window 1 is not called again"
    assert done.metrics["windows_recovered"] == 1
    assert [o["evidence"][0]["page_number"] for o in done.artifact["observations"]] == [1, 4, 7]
    first_call = str(world.records[0].model_call_id)
    assert done.artifact["observations"][0]["model_call_id"] == first_call, (
        "the recovered window's finding keeps the call that produced it"
    )


def test_the_recovered_run_publishes_what_an_uninterrupted_run_publishes() -> None:
    uninterrupted, _ = run(Scripted())
    first = Scripted(overrides={7: ProxyDispatchError(
        ErrorCode.DEPENDENCY_UNAVAILABLE, dispatch_class="not_sent", retry_safe=True, message="x",
    )})
    _, world = run(first)
    resumed, _ = run(Scripted(), world=world)

    def shape(outcome):
        return [
            (o["category"], o["finding_text"], [(e["page_number"], e["char_start"], e["char_end"]) for e in o["evidence"]])
            for o in outcome.artifact["observations"]
        ]

    assert shape(resumed) == shape(uninterrupted)
    assert resumed.artifact["pages_analysed"] == uninterrupted.artifact["pages_analysed"]


def test_a_changed_text_never_replays_an_old_reply() -> None:
    _, world = run(Scripted())
    assert len(world.completed) == 3
    changed = layer_document()
    changed["pages"][7]["text"] += "!"
    offset = 0
    for page in changed["pages"]:
        page["char_start"], page["char_end"] = offset, offset + len(page["text"])
        offset = page["char_end"]
    changed["total_char_count"] = offset
    adapter = Scripted()
    outcome, _ = run(adapter, world=world, document=changed)
    assert outcome.status == STATUS_SUCCEEDED
    assert adapter.calls == 3, "none of the old windows answers the changed text"
    assert outcome.metrics["windows_recovered"] == 0


def test_a_custody_that_refuses_its_evidence_stops_the_run_it_does_not_call_the_window_again() -> None:
    class Refusing(World):
        def recover(self, key: str) -> RecoveredWindow | None:
            raise DomainError(
                ErrorCode.ANALYSIS_INPUT_INVALID, message="the saved window reply does not match its completed call",
                stage_id="text_analysis", reason="window_reply_blob_digest_mismatch",
            )

    adapter = Scripted()
    outcome, _ = run(adapter, world=Refusing())
    assert outcome.status == STATUS_FAILED and adapter.calls == 0
    assert outcome.error.detail_fields["reason"] == "window_reply_blob_digest_mismatch"
    assert outcome.artifact is None


# -- one ceiling over every window ------------------------------------------------------------------


def test_the_ceiling_counts_all_windows_and_the_call_that_crosses_it_is_recorded_and_named() -> None:
    adapter = Scripted(cost=0.3)
    outcome, world = run(adapter, ceiling=0.5)
    assert outcome.status == STATUS_FAILED and outcome.artifact is None
    assert outcome.error.code is ErrorCode.COST_BUDGET_EXCEEDED
    assert "window 2 of 3 (pages 4-6)" in str(outcome.error)
    assert adapter.calls == 2, "the run stops at the window that crossed the ceiling"
    assert outcome.metrics["failed_window"] == 2 and outcome.metrics["cost_usd"] == pytest.approx(0.6)
    assert [kind for kind, _ in world.events].count("complete") == 2, "the crossing call is journaled"
    assert outcome.model_calls and len(outcome.model_calls) == 2


def test_a_run_at_the_ceiling_stops_at_the_window_boundary_before_it_calls() -> None:
    adapter = Scripted(cost=0.3)
    outcome, world = run(adapter, ceiling=0.6)
    assert outcome.status == STATUS_FAILED and outcome.error.code is ErrorCode.COST_BUDGET_EXCEEDED
    assert "stopped before window 3 of 3 (pages 7-9)" in str(outcome.error)
    assert adapter.calls == 2 and len(world.records) == 2
    assert outcome.artifact is None, "the findings of the windows that did finish are not published"


def test_the_meter_the_caller_hands_over_is_the_meter_every_window_charges() -> None:
    meter = CostMeter(ceiling_usd=1.0)
    outcome, _ = run(Scripted(cost=0.2), meter=meter)
    assert outcome.status == STATUS_SUCCEEDED
    assert meter.spent_usd == pytest.approx(0.6) and meter.call_count == 3
    assert outcome.metrics["cost_usd"] == pytest.approx(0.6)


def test_recovered_windows_charge_nothing() -> None:
    _, world = run(Scripted(cost=0.2))
    meter = CostMeter(ceiling_usd=1.0, spent_usd=0.6)
    outcome, _ = run(Scripted(cost=0.2), world=world, meter=meter)
    assert outcome.metrics["windows_recovered"] == 3
    assert meter.spent_usd == pytest.approx(0.6) and meter.call_count == 0


# -- a bad window fails the run and is named ---------------------------------------------------------


def test_a_reply_that_is_not_an_observation_list_fails_the_run_naming_the_window() -> None:
    garbled = ModelResponse(
        output_text="это не JSON", stop_reason="end_turn", input_tokens=10, output_tokens=2,
        latency_ms=3, reported_cost_usd=0.1,
    )
    adapter = Scripted(overrides={4: garbled})
    outcome, _ = run(adapter)
    assert outcome.status == STATUS_FAILED and outcome.artifact is None
    assert outcome.error.code is ErrorCode.ANALYSIS_FAILED
    assert "window 2 of 3 (pages 4-6)" in str(outcome.error)
    assert outcome.metrics["failed_window"] == 2 and outcome.metrics["failed_window_first_page"] == 4
    assert adapter.calls == 2, "the run does not go on to read window 3 after window 2 failed"


def test_an_empty_observation_list_is_a_real_answer_not_an_invalid_one() -> None:
    adapter = Scripted(overrides={4: reply([])})
    outcome, _ = run(adapter)
    assert outcome.status == STATUS_SUCCEEDED
    assert [o["evidence"][0]["page_number"] for o in outcome.artifact["observations"]] == [1, 7]


def test_a_json_document_without_an_observation_list_is_invalid() -> None:
    wrong_shape = ModelResponse(
        output_text='{"findings": []}', stop_reason="end_turn", input_tokens=10, output_tokens=2,
        latency_ms=3, reported_cost_usd=0.1,
    )
    outcome, _ = run(Scripted(overrides={7: wrong_shape}))
    assert outcome.status == STATUS_FAILED and "window 3 of 3" in str(outcome.error)


def test_a_cut_short_window_with_findings_makes_the_run_partial_with_the_pages_it_covers() -> None:
    adapter = Scripted(overrides={4: reply([observation(5)], stop_reason="max_tokens")})
    outcome, _ = run(adapter)
    assert outcome.status == STATUS_PARTIAL
    assert outcome.error.code is ErrorCode.PARTIAL_RESULT_NOT_PUBLISHABLE
    analysed = outcome.artifact["pages_analysed"]
    assert analysed == [1, 2, 3, 4, 5, 7, 8, 9], "the pages past the truncated window's frontier are not claimed"
    assert outcome.metrics["call_status"] == "truncated"


def test_a_cut_short_window_with_no_usable_finding_fails_the_run_naming_the_window() -> None:
    adapter = Scripted(overrides={7: reply([], stop_reason="max_tokens")})
    outcome, _ = run(adapter)
    assert outcome.status == STATUS_FAILED and outcome.artifact is None
    assert "window 3 of 3 (pages 7-9) was cut short" in str(outcome.error)


# -- before any call --------------------------------------------------------------------------------


def test_a_plan_above_the_limit_is_refused_before_any_call_with_both_figures() -> None:
    adapter = Scripted()
    outcome, world = run(adapter, policy=WindowPolicy(THREE_PAGES.window_characters, max_windows=2))
    assert outcome.status == STATUS_FAILED and adapter.calls == 0 and world.events == []
    assert outcome.error.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert outcome.error.detail_fields["reason"] == "window_plan_over_limit"
    assert "3 windows" in str(outcome.error) and "at most 2" in str(outcome.error)


def test_a_plan_of_exactly_the_limit_runs() -> None:
    adapter = Scripted()
    outcome, _ = run(adapter, policy=WindowPolicy(THREE_PAGES.window_characters, max_windows=3))
    assert outcome.status == STATUS_SUCCEEDED and adapter.calls == 3


def test_a_live_run_in_windows_needs_a_durable_journal_and_durable_custody() -> None:
    adapter = Scripted(ProviderMode.LIVE)
    no_custody, _ = run(adapter, custody=False)
    assert no_custody.status == STATUS_FAILED and adapter.calls == 0
    assert no_custody.error.detail_fields["reason"] == "durable_window_custody_required"
    no_journal, _ = run(adapter, journal=False)
    assert no_journal.error.detail_fields["reason"] == "durable_call_journal_required"
    assert adapter.calls == 0


def test_a_recorded_run_may_go_without_custody_it_replays_for_free() -> None:
    adapter = Scripted(ProviderMode.RECORDED)
    outcome, _ = run(adapter, custody=False, journal=False)
    assert outcome.status == STATUS_SUCCEEDED and adapter.calls == 3


def test_a_document_graph_of_an_unknown_version_still_fails_closed() -> None:
    outcome = run_text_analysis_windows(
        run_id=RunId.new(), text_layer_document=layer_document(), adapter=Scripted(),
        config=config(), profile=V1_REFERENCE_PROFILE, policy=THREE_PAGES,
        document_graph={"artifact_role": "context.document_graph", "artifact_version": "9.9.9"},
    )
    assert outcome.status == STATUS_FAILED
    assert outcome.error.detail_fields["reason"] == "artifact_version_unsupported"


def test_a_failed_provider_call_is_journaled_and_carries_the_transport_facts_unchanged() -> None:
    error = ProxyDispatchError(
        ErrorCode.DEPENDENCY_UNAVAILABLE, dispatch_class="outcome_unknown", retry_safe=False,
        message="the proxy connection ended without a complete answer",
    )
    adapter = Scripted(ProviderMode.LIVE, overrides={1: error})
    outcome, world = run(adapter)
    assert outcome.status == STATUS_FAILED and outcome.error is error
    assert outcome.provider_effect_uncertain is True and outcome.provider_retry_allowed is False
    assert [kind for kind, _ in world.events] == ["prepare", "outcome_unknown"]
