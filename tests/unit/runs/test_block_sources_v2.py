"""`BLOCK-SOURCES-V2-01`: a v2 block request names its batch's sources, and a batch the model read counts as read.

Container-free. The first half holds the request builders (the default bytes, the guard of ``bind_sources=True`` and its single definition);
the second half runs the real workflow of ``extended_review._run_workflow_v2`` on the harness of ``test_blocks_ensemble`` -- the legs of the
ensemble and the single call -- and reads the coverage counter and the stage's status the run leaves.

The pinned digests below were measured on the tree BEFORE the change (``git archive 82aeca640``): the default v2 request and the v3 request
of the same payload must stay byte-identical. The v3 request carries ``rules_sha256``, the digest of the review bundle, which hashes
``core.py`` itself; it is held constant here, so that the pin checks the request and not the file that builds it.

Every guard has been shown able to fail: the break-it-once runs are recorded in the commit that added this file (the counter back to
``if not refused:``, the stage status back to ``blocks_remaining`` alone, ``bind_sources`` not passed by the loop, the guard left out of
``build_request``).
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

import pytest

from auditmanager.analysis.extended import workflow as extended_workflow
from auditmanager.analysis.extended.core import build_request, build_request_v3
from auditmanager.runs import stage_layout as layout
from tests.unit.runs.test_blocks_ensemble import ASTRA, Harness, batch_of, block_batches, block_calls, default_answer, observation

# --- the pinned bytes ----------------------------------------------------------------------------------------------------------

PAYLOAD = {"section": "EOM",
           "sources": [{"source_id": "blk_" + "b" * 32, "page_number": 2, "kind": "image"},
                       {"source_id": "blk_" + "a" * 32, "page_number": 1, "kind": "image"}],
           "page_contexts": [{"page_number": 1, "native_text": "Текст", "recognised_context": "", "context_truncated": False}],
           "context_sections": [], "coverage": {"blocks_total": 2}}
EMPTY = {"section": "EOM", "sources": []}

# (request_sha256, idempotency_scope) measured before the change.
PINNED = {
    ("v2", "blocks", "fixed"): ("6b5ddeda12e5a805928af1259d52dfab77ef24b27f4dc5d8d472c25ada5aa4a4",
                                "run:blocks:d4aaf30274a6215f3739ebc4c94705c2c8410ec65bad8c73f79b0f56636f30e4"),
    ("v2", "merge", "fixed"): ("47a494dd2281b30888345d36a8cf685722e80c0854a63ae7df1bd1c12e0cdf55",
                               "run:merge:d4aaf30274a6215f3739ebc4c94705c2c8410ec65bad8c73f79b0f56636f30e4"),
    ("v2", "blocks", "empty"): ("916ab1a7454d0e7bf490f8915a9c6db95a6a5920033a4cfc31e625aadebe072e",
                                "run:blocks:d52ff0e098f924eccac6aeafd8e7472d7bce88e80ce71d3f99243de67683757b"),
    ("v2", "merge", "empty"): ("68326ee6fe049e30d7b5e85ffa9f485308d2c49622b5f9c2f3c10cc1f9190bf4",
                               "run:merge:d52ff0e098f924eccac6aeafd8e7472d7bce88e80ce71d3f99243de67683757b"),
    ("v3", "blocks", "fixed"): ("dbd206a4a4ff54ae29b465a51a57a63c7cb78ffe12850d9891f8d0572de7e079",
                                "run:v3:w001:blocks:9f0ba1b6f4e8c594e296180a0d760918db33733ce7fb6bde63d24ad51b67d7be"),
    ("v3", "blocks", "empty"): ("ba72d5b7286c2e500e2b379eaef8a8ad164d6a4dddd1179aacbf9c1b5fff088d",
                                "run:v3:w001:blocks:1532ec29c42a7a6a802dd1ced97f05b17cac08e43f25ae47dc567bca01a33a9e"),
}
INSTRUCTION = ("\nsource_ids каждой записи копируй только из sources этого пакета. "
               "Не используй context_fact_id, fact_id, text_id или идентификаторы из соседнего пакета. "
               "Не повторяй source_id внутри одной записи. Если проверяемого наблюдения нет, верни пустой observations.")
SOURCE_IDS = ["blk_" + "a" * 32, "blk_" + "b" * 32]


@pytest.fixture
def frozen_bundle(monkeypatch):
    monkeypatch.setattr(extended_workflow, "review_bundle_digest", lambda section: "r" * 64)


def built(kind: str, phase: str, which: str, **more: Any):
    payload = PAYLOAD if which == "fixed" else EMPTY
    common = dict(model_id="selected", run_id="run", phase=phase, section="EOM", payload=payload)
    return build_request(**common, **more) if kind == "v2" else build_request_v3(**common, window_id="w001")


@pytest.mark.parametrize("key", sorted(PINNED))
def test_the_default_v2_request_and_the_v3_request_keep_their_bytes_and_scopes(key, frozen_bundle):
    request = built(*key)
    assert (request.request_sha256, request.idempotency_scope) == PINNED[key]


def enum_of(request: Any) -> Any:
    items = request.body["output_config"]["format"]["schema"]["properties"]["observations"]["items"]
    return items["properties"]["source_ids"]["items"].get("enum")


def test_bind_sources_adds_the_enum_and_the_instruction_once_and_nothing_else():
    default = built("v2", "blocks", "fixed")
    bound = built("v2", "blocks", "fixed", bind_sources=True)
    assert enum_of(default) is None and INSTRUCTION not in default.body["system"]
    assert enum_of(bound) == SOURCE_IDS, "the sorted source ids of the batch"
    assert bound.body["system"].count(INSTRUCTION) == 1 and bound.body["system"] == default.body["system"] + INSTRUCTION
    # Everything else is the default request's: take the guard away and the bodies are equal.
    stripped = deepcopy(dict(bound.body))
    stripped["system"] = default.body["system"]
    del stripped["output_config"]["format"]["schema"]["properties"]["observations"]["items"]["properties"]["source_ids"]["items"]["enum"]
    assert stripped == dict(default.body)
    assert bound.idempotency_scope == default.idempotency_scope
    assert bound.request_sha256 != default.request_sha256


def test_the_default_schema_object_is_never_mutated_by_the_guard():
    first = built("v2", "blocks", "fixed", bind_sources=True)
    second = built("v2", "blocks", "fixed")
    assert enum_of(first) == SOURCE_IDS and enum_of(second) is None, "a bound request does not leak into the next default one"


def test_without_sources_the_instruction_stays_and_no_empty_enum_is_written():
    bound = built("v2", "blocks", "empty", bind_sources=True)
    assert enum_of(bound) is None and bound.body["system"].endswith(INSTRUCTION)


@pytest.mark.parametrize("which", ["fixed", "empty"])
def test_the_guard_applies_to_the_block_phase_only(which):
    assert built("v2", "merge", which, bind_sources=True).request_sha256 == PINNED[("v2", "merge", which)][0]


def test_v2_and_v3_apply_the_one_definition_of_the_guard(frozen_bundle):
    v2 = built("v2", "blocks", "fixed", bind_sources=True)
    v3 = built("v3", "blocks", "fixed")
    assert enum_of(v3) == enum_of(v2) == SOURCE_IDS
    assert v3.body["system"].endswith(INSTRUCTION) and v3.body["system"].count(INSTRUCTION) == 1


# --- the v2 loop -------------------------------------------------------------------------------------------------------------


def block_requests(harness: Harness, roles: tuple[str, ...]) -> list[tuple[str, Any]]:
    return [(key, request) for key, request in harness.log if key in {f"blocks:{role}" for role in roles}]


def single_harness(monkeypatch: pytest.MonkeyPatch, answer=default_answer) -> Harness:
    cells = tuple(c for c in layout.preset_cells("codex_only") if c.row != "blocks") + (layout.CellSettings("blocks:main", ASTRA, "medium"),)
    return Harness(monkeypatch, kit="custom", cells=tuple(sorted(cells, key=layout._position)), answer=answer)


def assert_bound(request: Any) -> None:
    sources = json.loads(request.body["messages"][0]["content"])["sources"]
    assert enum_of(request) == sorted(s["source_id"] for s in sources) and request.body["system"].count(INSTRUCTION) == 1


@pytest.mark.parametrize("kit,roles", [("claude_only", ("leg1",)), ("codex_only", ("leg1", "leg2"))])
def test_the_v2_loop_binds_the_sources_of_every_leg_of_the_ensemble(monkeypatch, kit, roles):
    harness = Harness(monkeypatch, kit=kit)
    harness.run_v2(monkeypatch, blocks=10)
    legs = block_requests(harness, roles)
    assert len(legs) == 2 * len(roles), "two batches, every leg asked in each"
    for _, request in legs:
        assert_bound(request)
    # the judge keeps its own closed list: the guard of the legs is not written on it
    judges = block_requests(harness, ("judge",))
    assert len(judges) == 2 and all(INSTRUCTION not in request.body["system"] for _, request in judges)


def test_the_v2_loop_binds_the_sources_of_the_single_call(monkeypatch):
    harness = single_harness(monkeypatch)
    harness.run_v2(monkeypatch, blocks=10)
    calls = block_requests(harness, ("main",))
    assert block_calls(harness) == ["blocks:main"] * 2
    for _, request in calls:
        assert_bound(request)


def test_the_v3_window_carries_the_guard_once_and_through_its_own_builder(monkeypatch):
    harness = Harness(monkeypatch, kit="claude_only")
    harness.run_v3_window(monkeypatch, blocks=8)
    (_, request), = block_requests(harness, ("leg1",))
    assert_bound(request) and "window_id" in json.loads(request.body["messages"][0]["content"])


# --- the counter and the stage's status -----------------------------------------------------------------------------------------


def stage(state: dict[str, Any]) -> dict[str, Any]:
    return next(p for p in state["procedures"] if p["id"] == "block_analysis")


def with_foreign_record(first_batch_only: bool = True):
    """The first leg's reply holds its own observation and one that cites a source of no batch: valid JSON, one record refused."""
    def answer(cell_key, request, nth):
        reply = default_answer(cell_key, request, nth)
        if cell_key in ("blocks:leg1", "blocks:main") and (batch_of(request) == 0 or not first_batch_only):
            document = json.loads(reply)
            document["observations"].append(observation("blk_" + "f" * 32, "чужой источник"))
            return json.dumps(document, ensure_ascii=False)
        return reply
    return answer


def test_a_clean_run_counts_every_batch_and_the_stage_completes(monkeypatch):
    harness = Harness(monkeypatch, kit="claude_only")
    state = harness.run_v2(monkeypatch, blocks=10)
    assert (state["coverage"]["blocks_processed"], state["coverage"]["blocks_remaining"]) == (10, 0)
    assert stage(state)["status"] == "completed" and "reason" not in stage(state) and not state.get("reply_refusals")


def test_a_leg_with_one_refused_record_still_counts_its_batch_and_the_stage_stays_partial(monkeypatch):
    harness = Harness(monkeypatch, kit="claude_only", answer=with_foreign_record())
    state = harness.run_v2(monkeypatch, blocks=10)
    assert (state["coverage"]["blocks_processed"], state["coverage"]["blocks_remaining"]) == (10, 0), "both batches were read"
    assert (stage(state)["status"], stage(state).get("reason")) == ("partial", "block_analysis_reply_refused")
    (receipt,) = state["reply_refusals"]
    assert receipt["phase_key"] == "blocks:0:leg1" and receipt["accepted_record_count"] == 1
    assert [r["reason"] for r in receipt["rejected_records"]] == ["observation_sources_or_limits_invalid"]
    assert any(o["title"].startswith("leg1 находка") for o in state["observations"]), "the valid record of the refused reply survives"
    assert not any(o["title"] == "чужой источник" for o in state["observations"])


def test_a_refused_record_of_a_single_call_counts_its_batch_and_the_stage_says_why(monkeypatch):
    harness = single_harness(monkeypatch, answer=with_foreign_record(first_batch_only=False))
    state = harness.run_v2(monkeypatch, blocks=10)
    assert (state["coverage"]["blocks_processed"], state["coverage"]["blocks_remaining"]) == (10, 0)
    assert (stage(state)["status"], stage(state).get("reason")) == ("partial", "block_analysis_reply_refused")
    assert [r["phase_key"] for r in state["reply_refusals"]] == ["blocks:0", "blocks:1"]


def test_a_single_reply_refused_whole_does_not_count_its_batch(monkeypatch):
    def answer(cell_key, request, nth):
        return "это не JSON" if cell_key == "blocks:main" and batch_of(request) == 0 else default_answer(cell_key, request, nth)

    harness = single_harness(monkeypatch, answer=answer)
    state = harness.run_v2(monkeypatch, blocks=10)
    assert (state["coverage"]["blocks_processed"], state["coverage"]["blocks_remaining"]) == (2, 8), "only the second batch of two was read"
    assert (stage(state)["status"], stage(state).get("reason")) == ("partial", "block_analysis_reply_refused")
    (receipt,) = state["reply_refusals"]
    assert receipt["phase_key"] == "blocks:0" and receipt["accepted_record_count"] == 0


def test_a_single_call_whose_only_batch_is_refused_whole_reads_nothing(monkeypatch):
    harness = single_harness(monkeypatch, answer=lambda cell_key, request, nth: "{" if cell_key == "blocks:main" else default_answer(cell_key, request, nth))
    state = harness.run_v2(monkeypatch, blocks=8)
    assert (state["coverage"]["blocks_processed"], state["coverage"]["blocks_remaining"]) == (0, 8)
    assert stage(state)["status"] == "partial"


def test_a_stage_with_a_refusal_stays_partial_whichever_batch_it_was_in(monkeypatch):
    """The status does not depend on the counter: the same refusal in the last batch leaves the same stage."""
    def answer(cell_key, request, nth):
        reply = default_answer(cell_key, request, nth)
        if cell_key == "blocks:leg1" and batch_of(request) == 1:
            document = json.loads(reply)
            document["observations"].append(observation("blk_" + "f" * 32, "чужой источник"))
            return json.dumps(document, ensure_ascii=False)
        return reply

    harness = Harness(monkeypatch, kit="claude_only", answer=answer)
    state = harness.run_v2(monkeypatch, blocks=10)
    assert state["coverage"]["blocks_remaining"] == 0
    assert (stage(state)["status"], stage(state).get("reason")) == ("partial", "block_analysis_reply_refused")
    assert [r["phase_key"] for r in state["reply_refusals"]] == ["blocks:1:leg1"]


def test_a_v3_window_is_not_changed_by_this_task_a_refused_batch_is_still_not_counted(monkeypatch):
    harness = Harness(monkeypatch, kit="claude_only", answer=with_foreign_record())
    state = harness.run_v3_window(monkeypatch, blocks=10)
    batches = {b["index"]: b for b in block_batches(state)}
    assert (batches[0]["status"], batches[1]["status"]) == ("partial", "completed")
    assert state["coverage"]["blocks_processed"] == 2 and state["coverage"]["blocks_remaining"] == 8
