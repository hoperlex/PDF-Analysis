"""`M7-NORM-PNG` (plan-v5 section 3.4, ``ADR-0029`` decision 9): the critic's task is created with the page images of its own norm paragraphs.

What is pinned here is the runtime's rule, with the page service replaced by a double that would happily hand over three pages (the service's own
limit and its SQL are the integration test's). A task declares ``crop_id: norm.<nbd_...>`` images only when ALL of these hold: the run carries the
reference policy (the rule the critic's reference section uses), the ``review:main`` member of the run is not a Claude Code host and has declared
that it serves images, and the request has norm paragraphs. Every other critic request is built exactly as it was.

Each check below fails when the rule it names is taken out; the last test of each group is the contrast that shows the images were wanted.
"""

from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace as NS

import pytest
from sqlalchemy import create_engine

from auditmanager.executors.pull import _task_payload
from auditmanager.norms.public import NormPageImage, NormPageRender, PageImageSelection
from auditmanager.runs import extended_review as runtime

NBD = ["nbd_01HZZZZZZZZZZZZZZZZZZZZ0%02d" % number for number in range(1, 5)]
SNAPSHOT, DOCUMENT = "ns_01HZZZZZZZZZZZZZZZZZZZZ001", "ndoc_01HZZZZZZZZZZZZZZZZZZZ0001"
PARAGRAPHS = ["npar_01HZZZZZZZZZZZZZZZZZZZ%04d" % number for number in range(1, 5)]
POLICY = {"version": "executor-reference-context-v1", "kinds": ["similar_cases", "patterns"]}
PLANNED = NS(cells=object())
QUOTE = "Размер проёма 1200 мм принят по проекту"
SOURCES = [{"source_id": "s1", "kind": "text", "source_type": "native_text", "page_number": 1, "quote": QUOTE}]
WINDOW = {"window_id": "w1", "policy": {"phase_call_limits": {kind: 8 for kind in ("finding_review", "finding_correction")},
    "executor_context_policy": POLICY}}


def _png(seed: str) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + hashlib.sha256(seed.encode()).digest() * 4


def _image(number: int) -> NormPageImage:
    data = _png(str(number))
    render = NormPageRender(norm_custody_binding_id=NBD[number], render_profile="png-150dpi-v1",
        blob_id="blob_" + "0" * 26, sha256=hashlib.sha256(data).hexdigest(), size_bytes=len(data), media_type="image/png",
        width_px=1240, height_px=1754)
    return NormPageImage(render=render, paragraph_ids=(PARAGRAPHS[number],), data=data)


class Pages:
    """The page service double: it offers every page it is asked about, however many (so a limit it did not apply would show)."""

    def __init__(self, unavailable=()):
        self.asked, self.unavailable = [], tuple(unavailable)

    def select(self, norm_context):
        self.asked.append([row["paragraph_id"] for row in norm_context])
        return PageImageSelection(images=tuple(_image(number) for number, _ in enumerate(norm_context)), unavailable=self.unavailable)


def _candidate(number):
    return {"snapshot_id": SNAPSHOT, "document_id": DOCUMENT, "paragraph_id": PARAGRAPHS[number], "designation": "СП 1.2.3",
        "clause_number": f"{number + 1}.1", "quote": f"Текст нормы {number}", "page_label": number + 1, "status": "candidate_not_verified"}


def _state(candidates=(0, 1, 2)):
    observations = [{"title": "Наблюдение", "description": "Описание", "source_ids": ["s1"],
        "norm_candidates": [_candidate(number) for number in candidates]}]
    return {"section": "AR", "source_sha256": "a" * 64, "sources": SOURCES, "observations": observations, "warnings": [],
        "coverage": {"blocks_total": 0, "blocks_processed": 0, "blocks_remaining": 0}}


def _row(key):
    return {"input_id": key, "source_ids": ["s1"], "llm_decision": "accept", "human_taxonomy_reason": "other", "confidence": 0.5,
        "explanation": "Пояснение", "evidence_checked": True, "source_dependency": "enough_source", "needs_correction": False,
        "suggested_fix": "", "source_evidence": []}


class Run:
    def __init__(self):
        self.requests, self.phases = [], []

    def phase(self, identity, status, reason=None):
        self.phases.append((identity, status, reason))

    def call(self, request, identity):
        self.requests.append((identity, request))
        payload = json.loads(request.body["messages"][0]["content"])
        reply = json.dumps({"reviews": [_row(item["input_id"]) for item in payload["observations"]]}, ensure_ascii=False)
        return NS(output_text=reply, response_sha256="b" * 64, truncated=False)

    @property
    def request(self):
        return self.requests[0][1]


@pytest.fixture(autouse=True)
def _plain_cells(monkeypatch):
    monkeypatch.setattr(runtime, "_kw", lambda binding, row, role="main": {"model_id": "m", "settings": None})


def _member(monkeypatch, *, provider, features, host_id="host_1"):
    """The database facts the rule reads: the member of ``review:main`` and what its host's tokens declared. The reads are replaced, the rule is not."""
    monkeypatch.setattr(runtime, "cell_binding_of", lambda session, run_id, cell: (
        None if provider is None else NS(provider=provider, host_id=host_id, cell_key=cell)))
    monkeypatch.setattr(runtime, "HostRepository", lambda: NS(usable_tokens=lambda session, host: ["tok_1"]))
    monkeypatch.setattr(runtime, "token_health_of", lambda session, tokens: {"tok_1": NS(features=tuple(features))})


def _helper(pages):
    session = NS(get_bind=lambda: create_engine("sqlite://"))
    return runtime._CriticNormImages(session, NS(run_id="run"), store=None, pages=pages)


def _batched(state, run, *, helper, binding=PLANNED, policy=None):
    window = WINDOW if policy is None else policy
    runtime._review_batched_v3(run=NS(run_id="run"), binding=binding, state=state, phase=run.phase, call=run.call, window_context=window,
        contexts=[], norm_images=helper)


# -- who may be shown a norm page -----------------------------------------------------------------------------------------------------


def test_a_task_for_a_claude_code_cell_gets_no_norm_images_even_when_its_host_declares_images(monkeypatch):
    _member(monkeypatch, provider="claude_code", features=["images"])
    pages, run, state = Pages(), Run(), _state()
    _batched(state, run, helper=_helper(pages))
    assert "images" not in run.request.body and run.request.images_bytes == ()
    assert pages.asked == [], "the page service is not even asked"
    receipt, = state["norm_page_images"]
    assert (receipt["status"], receipt["reason"]) == ("not_offered", "provider_takes_no_images")
    assert [row[1:] for row in run.phases if row[0] == "finding_review"][-1] == ("completed", None), "the text is delivered and the call is made"


def test_a_task_for_a_member_that_declared_no_images_gets_none(monkeypatch):
    _member(monkeypatch, provider="codex", features=[])
    pages, run, state = Pages(), Run(), _state()
    _batched(state, run, helper=_helper(pages))
    assert "images" not in run.request.body and pages.asked == []
    assert state["norm_page_images"][0]["reason"] == "member_declared_no_images"


def test_a_cell_with_no_bound_member_gets_none(monkeypatch):
    _member(monkeypatch, provider=None, features=["images"])
    run, state = Run(), _state()
    _batched(state, run, helper=_helper(Pages()))
    assert "images" not in run.request.body and state["norm_page_images"][0]["reason"] == "member_not_bound"


def test_a_member_that_serves_images_gets_the_pages_of_its_own_norm_paragraphs_declared(monkeypatch):
    """The contrast of the three above: the same request, a member that takes images."""
    _member(monkeypatch, provider="codex", features=["images"])
    pages, run, state = Pages(), Run(), _state(candidates=(0, 1))
    _batched(state, run, helper=_helper(pages))
    request = run.request
    declared = request.body["images"]
    assert [item["crop_id"] for item in declared] == ["norm." + NBD[0], "norm." + NBD[1]]
    assert all(set(item) == {"blob_id", "crop_id", "sha256", "size_bytes", "media_type"} and item["media_type"] == "image/png" for item in declared)
    assert request.images_bytes == (_png("0"), _png("1"))
    # the task the pull adapter writes carries the same descriptors, in order, and the executor's own checks accepted them
    assert [item["crop_id"] for item in _task_payload(request)["images"]] == ["norm." + NBD[0], "norm." + NBD[1]]
    # what the page service was asked about is the paragraphs this request's norm_context holds, no others
    norm_context = json.loads(request.body["messages"][0]["content"])["norm_context"]
    assert pages.asked == [[row["paragraph_id"] for row in norm_context]] and set(pages.asked[0]) == {PARAGRAPHS[0], PARAGRAPHS[1]}
    receipt, = state["norm_page_images"]
    assert receipt["status"] == "declared" and [item["crop_id"] for item in receipt["images"]] == ["norm." + NBD[0], "norm." + NBD[1]]


def test_the_candidate_whose_paragraph_was_shown_is_marked_as_having_seen_images(monkeypatch):
    _member(monkeypatch, provider="codex", features=["images"])
    state = _state(candidates=(0,))
    _batched(state, Run(), helper=_helper(Pages()))
    assert state["observations"][0]["context_kinds"] == ["norm_text", "norm_images"]
    # a request that carried none is marked as before
    _member(monkeypatch, provider="claude_code", features=["images"])
    state = _state(candidates=(0,))
    _batched(state, Run(), helper=_helper(Pages()))
    assert state["observations"][0]["context_kinds"] == ["norm_text"]


def test_a_page_that_cannot_be_produced_is_listed_with_its_reason_and_the_text_still_goes(monkeypatch):
    _member(monkeypatch, provider="codex", features=["images"])

    class NoPages(Pages):
        def select(self, norm_context):
            self.asked.append([row["paragraph_id"] for row in norm_context])
            return PageImageSelection(images=(), unavailable=tuple((row["paragraph_id"], "page_not_in_custody") for row in norm_context))

    run, state = Run(), _state(candidates=(0, 1))
    _batched(state, run, helper=_helper(NoPages()))
    assert "images" not in run.request.body and run.request.body["messages"], "the request is the one it always was"
    receipt, = state["norm_page_images"]
    assert receipt["status"] == "none" and receipt["unavailable"] == [
        {"paragraph_id": PARAGRAPHS[0], "reason": "page_not_in_custody"}, {"paragraph_id": PARAGRAPHS[1], "reason": "page_not_in_custody"}]
    assert state["observations"][0]["context_kinds"] == ["norm_text"] and state["observations"][0]["review_status"] == "reviewed"


def test_a_request_without_norm_paragraphs_asks_nothing_and_leaves_no_receipt(monkeypatch):
    _member(monkeypatch, provider="codex", features=["images"])
    pages, run, state = Pages(), Run(), _state(candidates=())
    _batched(state, run, helper=_helper(pages))
    assert pages.asked == [] and "images" not in run.request.body and "norm_page_images" not in state


# -- the window path takes the same rule ----------------------------------------------------------------------------------------------


def _window(state, run, *, helper, binding=PLANNED):
    runtime._review_window_v3(session=None, run=NS(run_id="run"), binding=binding, state=state, phase=run.phase, call=run.call,
        window_id="w1", section="AR", contexts=[], reference_section=runtime._reference_section(binding, WINDOW["policy"]),
        norm_images=helper)


def test_the_window_critic_declares_pages_for_a_member_that_serves_images_and_none_for_claude_code(monkeypatch):
    _member(monkeypatch, provider="codex", features=["images"])
    run, state = Run(), _state(candidates=(0,))
    _window(state, run, helper=_helper(Pages()))
    assert [item["crop_id"] for item in run.requests[0][1].body["images"]] == ["norm." + NBD[0]]
    _member(monkeypatch, provider="claude_code", features=["images"])
    run, state = Run(), _state(candidates=(0,))
    _window(state, run, helper=_helper(Pages()))
    assert "images" not in run.requests[0][1].body and state["norm_page_images"][0]["status"] == "not_offered"


# -- a run that is not offered the reference section is built exactly as before -----------------------------------------------------------


@pytest.mark.parametrize("binding,policy", [
    (NS(), {"executor_context_policy": POLICY}),   # a legacy run: no stage plan, no cells
    (PLANNED, {}),                                  # a planned run without the «контекст критику» switch
    (PLANNED, {"executor_context_policy": None}),
    (NS(cells=None), {"executor_context_policy": POLICY}),
])
def test_a_run_without_the_reference_policy_is_never_asked_for_images(binding, policy):
    assert runtime._critic_norm_images(NS(), NS(run_id="run"), None, binding, policy) is None


def test_a_run_with_the_reference_policy_is_asked():
    helper = runtime._critic_norm_images(NS(), NS(run_id="run"), None, PLANNED, {"executor_context_policy": POLICY})
    assert isinstance(helper, runtime._CriticNormImages)


class Tripwire:
    """A helper that fails the test if the critic of a legacy or v2 run so much as asks it."""

    def attach(self, request, *, state, identity):
        raise AssertionError("a run that is not offered the reference section must not reach the page images")


def _critic_request_and_state(*, binding, policy, helper):
    run, state = Run(), _state()
    window = {"window_id": "w1", "policy": {"phase_call_limits": WINDOW["policy"]["phase_call_limits"], **policy}}
    runtime._review_batched_v3(run=NS(run_id="run"), binding=binding, state=state, phase=run.phase, call=run.call, window_context=window,
        contexts=[], norm_images=helper)
    return run.request, state


@pytest.mark.parametrize("binding,policy", [(NS(), {"executor_context_policy": POLICY}), (PLANNED, {})])
def test_a_legacy_or_v2_critic_request_is_byte_identical_with_and_without_the_images_parameter(binding, policy):
    without, state_without = _critic_request_and_state(binding=binding, policy=policy, helper=None)
    # what the dispatcher passes for such a run is None; the tripwire shows that nothing could have been asked of a helper
    assert runtime._critic_norm_images(NS(), NS(run_id="run"), None, binding, policy) is None
    again, state_again = _critic_request_and_state(binding=binding, policy=policy, helper=None)
    assert without.request_sha256 == again.request_sha256 and "images" not in without.body and without.images_bytes == ()
    assert json.dumps(without.body, sort_keys=True) == json.dumps(again.body, sort_keys=True)
    assert "norm_page_images" not in state_without and state_without == state_again
    assert state_without["observations"][0]["context_kinds"] == ["norm_text"]
    with pytest.raises(AssertionError):
        _critic_request_and_state(binding=binding, policy=policy, helper=Tripwire())  # the tripwire does fire when a helper is passed


def test_the_images_change_nothing_but_the_images_in_the_request(monkeypatch):
    """The request with pages is the request without them plus ``images``: the prompt and the payload are the same bytes."""
    _member(monkeypatch, provider="codex", features=["images"])
    plain, _ = _critic_request_and_state(binding=PLANNED, policy={"executor_context_policy": POLICY}, helper=None)
    imaged, _ = _critic_request_and_state(binding=PLANNED, policy={"executor_context_policy": POLICY}, helper=_helper(Pages()))
    assert {key: value for key, value in imaged.body.items() if key != "images"} == dict(plain.body)
    assert imaged.request_sha256 != plain.request_sha256, "the digest of the call binds the pages it carried"


def test_the_member_is_read_once_per_run(monkeypatch):
    reads = []
    _member(monkeypatch, provider="codex", features=["images"])
    original = runtime.cell_binding_of
    monkeypatch.setattr(runtime, "cell_binding_of", lambda *args: reads.append(args[1:]) or original(*args))
    helper = _helper(Pages())
    for _ in range(3):
        _batched(_state(candidates=(0,)), Run(), helper=helper)
    assert reads == [("run", "review:main")]


def test_the_global_cell_name_is_the_critics_cell():
    assert runtime._CRITIC_CELL == "review:main"


def test_the_runtime_names_the_kind_the_programme_does():
    from auditmanager.precedents.models import CONTEXT_NORM_IMAGES
    assert runtime.CONTEXT_NORM_IMAGES == CONTEXT_NORM_IMAGES == "norm_images"
