"""The run of one sheet through a scripted caller (`CMP-VC-AISHEET-01`; the port of ``run.py`` and ``single.py``).

No database and no model: ``Scripted`` stands where ``ComparisonModelCaller`` stands and answers what the test wrote. What is proved:
the launches of a sheet are at most three; a technical retry is for an unusable answer or a proven non-delivery only; an outcome nobody
knows is never retried; a call that took the job over its consent ends the run; every request carries at most eight pictures; the context
request is executed by the program inside the two versions.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from auditmanager.analysis.public import ModelResponse
from auditmanager.comparison.ai_sheets import describe as ds
from auditmanager.comparison.ai_sheets import packet as pk
from auditmanager.comparison.spend.errors import CallFailed, CallLost, CallRefused, OutcomeUnknown
from auditmanager.comparison.spend.model import CallResult, CallRoute, SpendPause


def _fx() -> Any:
    name = "cmp_ai_sheets_fixtures"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent / "sheet_fixtures.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


fx = _fx()
NO_OTHER = {"what": "", "value_a": "", "value_b": "", "image_id": ""}


class Scripted:
    """The caller: ``steps`` are consumed one per call; an exception is raised, a callable is asked for the answer text."""

    def __init__(self, *steps: Any) -> None:
        self.steps = list(steps)
        self.requests: list[Any] = []
        self.estimates: list[Any] = []

    def call(self, item: Any, route: Any, request: Any, *, estimate: Any, consent: Any) -> CallResult:
        self.requests.append(request)
        self.estimates.append(estimate)
        step = self.steps.pop(0)
        if isinstance(step, BaseException):
            raise step
        pause = None
        if isinstance(step, tuple):
            step, pause = step
        text = step(request) if callable(step) else step
        response = ModelResponse(output_text=text if isinstance(text, str) else json.dumps(text, ensure_ascii=False), stop_reason="end_turn",
                                 input_tokens=100, output_tokens=50, latency_ms=1)
        return CallResult(response=response, call_id=f"cmc_{len(self.requests)}", cost_basis="unmetered", cost_micros=0,
                          pause=None if pause is None else SpendPause(pause))


def setup() -> tuple[Any, pk.SheetFacts, Any, Any]:
    a, b = fx.table_pages("cpr_a", "cpr_b", "ver_a", "ver_b")
    material = fx.FakeMaterial({"cpr_a": a, "cpr_b": b})
    facts = pk.SheetFacts(
        sheet_pair_id="ctp_1", title="План", project_title="Объект", designation="ЭМ-12", label_a="версия №1", label_b="версия №2",
        page_a=1, page_b=1, sheet_number="7", status="different", reasons=(), page_profile_a="cpr_a", page_profile_b="cpr_b",
        version_a="ver_a", version_b="ver_b",
    )
    packet = pk.assemble(facts, fx.table_result(), material, render=True, xrefs=False)
    route = CallRoute(adapter=object(), model_identity="claude-opus-5")  # type: ignore[arg-type]
    return packet, facts, material, route


def good(packet: pk.Packet, *, covered: bool = True, requests: list[dict[str, str]] | None = None) -> dict[str, Any]:
    change = {
        "object": "Люк Лк-1", "place": "таблица люков", "kind": "quantity", "summary": "Лк-1 — количество 2 → 3.",
        "fields": [{"name": "количество", "before": "2", "after": "3", "unit": "шт", "source": "text", "certainty": "confirmed"}],
        "members": [], "mapping": "one_to_one", "candidate_ids": ["O1"], "image_ids": ["I2"], "other_representation": NO_OTHER,
        "limitation": "",
    }
    rest = [{"candidate_ids": [c], "reason": "formatting", "note": ""} for c in ("O2", "O3")] if covered else []
    return {"packet_id": packet.packet_id, "part_id": "P1", "changes": [change], "unresolved": [], "excluded": rest,
            "context_requests": requests or []}


def run(caller: Scripted, packet: Any, facts: Any, material: Any, route: Any, **over: Any) -> ds.SheetRun:
    return ds.describe_pair(
        caller, object(), route, None, "claude-opus-5", packet, material, facts, checkpoint=lambda: None, recorded=True, **over,
    )


def test_a_good_answer_is_one_launch_and_a_done_description_that_says_it_is_recorded_and_unconfirmed() -> None:
    packet, facts, material, route = setup()
    caller = Scripted(lambda _r: good(packet))
    sheet = run(caller, packet, facts, material, route)
    assert (sheet.state, sheet.launches, sheet.failure, sheet.pause) == ("done", 1, None, None)
    assert sheet.description is not None and sheet.description["engineer_confirmed"] is False and sheet.description["recorded"] is True
    assert sheet.description["disclaimer"].endswith("инженером не подтверждено.")
    assert (sheet.input_tokens, sheet.output_tokens, sheet.call_ids) == (100, 50, ["cmc_1"])


def test_every_request_carries_the_pictures_of_the_packet_and_never_more_than_eight() -> None:
    packet, facts, material, route = setup()
    caller = Scripted(lambda _r: good(packet))
    run(caller, packet, facts, material, route)
    request = caller.requests[0]
    assert len(request.images_bytes) == len(packet.images) == 4 and len(request.body["images"]) == 4
    assert [d["crop_id"] for d in request.body["images"]] == ["I1", "I2", "I3", "I4"]
    assert caller.estimates[0].output_tokens == 8192 and caller.estimates[0].input_tokens > 4 * 1600


def test_an_answer_that_is_not_json_or_not_in_the_schema_gets_one_technical_retry() -> None:
    packet, facts, material, route = setup()
    caller = Scripted("not json at all", lambda _r: good(packet))
    sheet = run(caller, packet, facts, material, route)
    assert (sheet.state, sheet.launches) == ("done", 2)
    assert [c["ok"] for c in sheet.calls] == [False, True] and sheet.calls[0]["error_kind"] == "INVALID_JSON"
    broken = Scripted({"changes": []}, {"changes": []}, {"changes": []})
    failed = run(broken, packet, facts, material, route)
    assert failed.description is None and failed.failure == "model_answer_invalid" and failed.launches == 3
    assert broken.steps == [], "three launches in all, and no more (run.py:33)"


def test_a_refusal_that_proves_nothing_was_processed_is_tried_again_and_one_that_does_not_is_not() -> None:
    packet, facts, material, route = setup()
    safe = CallFailed("dependency_unavailable", call_id="cmc_x", retry_safe=True)
    caller = Scripted(safe, lambda _r: good(packet))
    assert run(caller, packet, facts, material, route).state == "done"
    final = CallFailed("analysis_input_invalid", call_id="cmc_y", retry_safe=False)
    caller = Scripted(final)
    sheet = run(caller, packet, facts, material, route)
    assert sheet.description is None and sheet.failure == "analysis_input_invalid" and sheet.launches == 1


def test_an_outcome_nobody_knows_is_never_sent_again() -> None:
    packet, facts, material, route = setup()
    caller = Scripted(OutcomeUnknown(call_id="cmc_u"), lambda _r: good(packet))
    with pytest.raises(ds.SheetInterrupted) as stopped:
        run(caller, packet, facts, material, route)
    assert isinstance(stopped.value.cause, OutcomeUnknown) and stopped.value.cause.reason == "spend_unknown"
    assert len(caller.requests) == 1 and len(caller.steps) == 1, "the second step was never taken"
    assert stopped.value.run.call_ids == ["cmc_u"]


def test_a_refusal_before_the_call_and_a_lost_lease_end_the_run_and_publish_nothing() -> None:
    packet, facts, material, route = setup()
    for cause in (CallRefused("overrun", pauses_job=True), CallLost(call_id=None)):
        caller = Scripted(cause)
        with pytest.raises(ds.SheetInterrupted) as stopped:
            run(caller, packet, facts, material, route)
        assert stopped.value.cause is cause and stopped.value.run.description is None


def test_a_call_that_took_the_job_over_its_consent_keeps_its_answer_and_makes_no_further_call() -> None:
    packet, facts, material, route = setup()
    # the answer leaves two candidates unsorted: a coverage pass would follow, but the job must stop asking
    caller = Scripted((lambda _r: good(packet, covered=False), "overrun"), lambda _r: good(packet))
    sheet = run(caller, packet, facts, material, route)
    assert sheet.pause == "overrun" and sheet.launches == 1 and len(caller.requests) == 1
    assert sheet.description is not None and sheet.state == "partial"


def test_the_program_executes_the_context_request_inside_the_two_versions() -> None:
    packet, facts, material, route = setup()
    request = {"kind": "zoom", "value": "O2", "side": "AB", "candidate_ids": ["O2"], "reason": "мелкий текст"}
    caller = Scripted(lambda _r: good(packet, requests=[request]), lambda _r: good(packet))
    sheet = run(caller, packet, facts, material, route)
    assert sheet.launches == 2 and [c["purpose"] for c in sheet.calls] == ["primary", "context"]
    followup = caller.requests[1]
    assert len(followup.images_bytes) == 4 + 2, "the packet's pictures and the two crops the program cut"
    assert "Новые изображения приложены после прежних: IX1, IX2" in followup.body["messages"][0]["content"]
    assert {crop[0] for crop in material.crops if crop not in material.crops[:0]} <= {"cpr_a", "cpr_b"}
    assert sheet.description is not None and sheet.description["context_requests"] == [request]
    assert sheet.description["diagnostics"]["context"][0]["status"] == "done"


def test_a_follow_up_request_keeps_to_eight_pictures_and_the_overview_first() -> None:
    from dataclasses import replace

    a, b = fx.table_pages("cpr_a", "cpr_b", "ver_a", "ver_b")
    a, b = replace(a, width_pt=3000.0, height_pt=2000.0), replace(b, width_pt=3000.0, height_pt=2000.0)
    result = fx.table_result()
    for n in range(12):
        x, y = 700 + (n % 4) * 600, 300 + (n // 4) * 600
        result["text_changes"].append({"kind": "changed", "before": f"Щ-{n}", "after": f"Щ-{n + 1}", "box": fx.box(x, y, x + 30, y + 10)})
    material = fx.FakeMaterial({"cpr_a": a, "cpr_b": b})
    _packet, facts, _material, route = setup()
    packet = pk.assemble(facts, result, material, render=True, xrefs=False)
    assert len(packet.images) == 8
    requests = [{"kind": "zoom", "value": "O4", "side": "AB", "candidate_ids": [], "reason": "?"},
                {"kind": "zoom", "value": "O5", "side": "AB", "candidate_ids": [], "reason": "?"}]
    caller = Scripted(lambda _r: {**good(packet, covered=False), "context_requests": requests},
                      lambda _r: {**good(packet, covered=False), "context_requests": []}, lambda _r: good(packet))
    ds.describe_pair(caller, object(), route, None, "claude-opus-5", packet, material, facts, checkpoint=lambda: None, recorded=True)
    assert [len(r.images_bytes) for r in caller.requests] == [8, 8, 8]
    assert [d["crop_id"] for d in caller.requests[1].body["images"]][0] == "I1"
    ids = [d["crop_id"] for d in caller.requests[1].body["images"]]
    assert ids[-4:] == ["IX1", "IX2", "IX3", "IX4"] and ids[:4] == ["I1", "I2", "I3", "I4"]


def test_a_context_request_with_a_strange_value_or_an_unknown_candidate_is_rejected_not_executed() -> None:
    packet, facts, material, route = setup()
    cut_before = len(material.crops)
    out = ds.resolve_context(packet.document, [
        {"kind": "mark", "value": "$(rm -rf /)", "side": "AB", "candidate_ids": [], "reason": ""},
        {"kind": "zoom", "value": "O99", "side": "AB", "candidate_ids": [], "reason": ""},
        {"kind": "shell", "value": "ls", "side": "AB", "candidate_ids": [], "reason": ""},
    ], material, facts)
    assert [entry["status"] for entry in out["log"]] == ["rejected", "rejected", "rejected"]
    assert out["images"] == [] and material.mark_requests == [] and len(material.crops) == cut_before


def test_the_coverage_pass_is_taken_only_when_it_leaves_fewer_candidates_unsorted() -> None:
    packet, facts, material, route = setup()
    caller = Scripted(lambda _r: good(packet, covered=False), lambda _r: good(packet, covered=True))
    sheet = run(caller, packet, facts, material, route)
    assert sheet.state == "done" and [c["purpose"] for c in sheet.calls] == ["primary", "coverage"]
    worse = Scripted(lambda _r: good(packet, covered=False), lambda _r: good(packet, covered=False))
    assert run(worse, packet, facts, material, route).state == "partial"


def test_a_stop_at_the_checkpoint_sends_nothing() -> None:
    packet, facts, material, route = setup()

    class Stop(Exception):
        pass

    def checkpoint() -> None:
        raise Stop

    caller = Scripted(lambda _r: good(packet))
    with pytest.raises(Stop):
        ds.describe_pair(caller, object(), route, None, "m", packet, material, facts, checkpoint=checkpoint, recorded=True)
    assert caller.requests == []


def test_a_single_sheet_is_described_by_what_is_on_it_and_a_mark_not_on_it_is_dropped() -> None:
    answer = {"sheet_kind": "план этажа", "summary": "План 2 этажа, щиты ЩР-1.", "objects": [{"name": "щит", "detail": "ЩР-1"}],
              "marks": ["ЩР-1", "ЩР-77"], "limitation": ""}
    caller = Scripted(answer)
    route = CallRoute(adapter=object(), model_identity="claude-opus-5")  # type: ignore[arg-type]
    sheet = ds.describe_single(
        caller, object(), route, None, "claude-opus-5", kind="added", side="B", page=3, title="План", label="версия №2",
        project="ЭМ-12", sheet_text="План 2 этажа ЩР-1 щит", image=fx.png(40, 30), material_tag="k", checkpoint=lambda: None,
        recorded=True,
    )
    single = sheet.description["single"]
    assert sheet.state == "done" and single["marks"] == ["ЩР-1"] and single["label"] == "Лист добавлен"
    assert any(i["code"] == "MARK_UNVERIFIED" for i in sheet.description["diagnostics"]["issues"])
    assert len(caller.requests[0].images_bytes) == 1 and sheet.description["changes"] == []
