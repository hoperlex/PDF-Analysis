"""`CTX-CRITIC` (`ADR-0029` decision 3, plan-v5 section 3.5): the critic's paragraph about the reference section, and the tolerant window parse.

The critic's prompt stays static; the executor's agent may put a section ``=== СПРАВОЧНО (не основание) ===`` after the JSON of a
`review:main` task (`CTX-STAND`, `CTX-RUNNER`). Only a run whose critic task can carry that section is told about it, and its prompt then
drops the sentence «Изображения здесь повторно не приложены». Every other prompt -- a v3 run without the policy, the corrector, every v2
request -- keeps the text it had at `ac76c1ce5`, which the digests below pin. The critic's windowed reply is read record by record, so a quote
taken from the reference section (it is in no source of the project) costs one record, never the paid reply.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from auditmanager.analysis.extended import core, review, workflow
from auditmanager.runs import extended_review as runtime

ROOT = Path(__file__).resolve().parents[3]
MARKER = "АДАПТАЦИЯ ТЕКУЩЕГО ЭТАПА"
OLD_SENTENCE = "Изображения здесь повторно не приложены"
QUOTE = "Размер проёма 1200 мм принят по проекту"
SOURCES = [{"source_id": "s1", "kind": "text", "source_type": "native_text", "page_number": 1, "quote": QUOTE}]
#: What a model that echoes the reference section would quote: a case text of the section, found in no source of the project.
FROM_REFERENCE = "Замечание о проёме отклонено экспертом как уже учтённое"
POLICY = {"version": "executor-reference-context-v1", "kinds": ["similar_cases", "patterns"]}

# The digests of the text `review.py` and the builders produced at `ac76c1ce5`, before this lane. `*_TAIL` is the adaptation and the instruction of the
# request (the part `review.py` owns; the taxonomy and the section rubric before it are other files' text), the v2 ones the whole system text.
BASE_CRITIC_TAIL = "d16b760637748f90bece5a4ae268b41748b2473f547783c3d522f87d309204bf"
BASE_CORRECTOR_TAIL = "6d79d9bb98ab186c8309f1063a2b8c660d3b430292abcd2d016e4a83ab65cf6e"
BASE_V2_SYSTEM = {
    "blocks": "b5d68237286de813497fc28acfc80349248dd82cd025bc91f0147793f91ac613",
    "merge": "fc3f081d2a37ab2cf2484d264531c7c9e3e2ea9feb8a807c0100ff9d5eabea10",
    "comprehensive": "24e403a135767735534eb2d73c88d4f2d0f544633827a2d11cf77a29db9f9575",
}


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def tail(request) -> str:
    system = request.body["system"]
    return system[system.index(MARKER):]


def _observations(*keys):
    return {key: {"title": f"Наблюдение {key}", "description": "Описание", "source_ids": ["s1"]} for key in keys}


def _critic(**kw):
    return review.build_critic_request(model_id="m", run_id="run", section="AR", observations=_observations("i1"),
        sources=SOURCES, window_id="w1", **kw)


# -- the prompt -------------------------------------------------------------------------------------------------------------------


def test_a_critic_without_the_reference_section_keeps_the_text_it_had_at_the_base_byte_for_byte():
    for request in (_critic(), _critic(reference_section=False)):
        assert OLD_SENTENCE in request.body["system"]
        assert sha(tail(request)) == BASE_CRITIC_TAIL
    # the pin tells the two texts apart: the paragraph's tail is another digest
    assert sha(tail(_critic(reference_section=True))) != BASE_CRITIC_TAIL


def test_the_corrector_and_every_v2_request_keep_the_text_they_had_at_the_base():
    critiques = [{"input_id": "i1", "source_ids": ["s1"], "llm_decision": "needs_human", "human_taxonomy_reason": "other",
        "confidence": 0.5, "explanation": "x", "evidence_checked": False, "source_dependency": "needs_context",
        "needs_correction": True, "suggested_fix": "", "source_evidence": []}]
    corrector = review.build_corrector_request(model_id="m", run_id="run", section="AR", observations=_observations("i1"),
        critiques=critiques, sources=SOURCES, window_id="w1")
    assert OLD_SENTENCE in corrector.body["system"] and sha(tail(corrector)) == BASE_CORRECTOR_TAIL
    blocks = core.build_request(model_id="m", run_id="run", phase="blocks", section="EOM", payload={"sources": []})
    merge = core.build_request(model_id="m", run_id="run", phase="merge", section="AR", payload={})
    comprehensive = workflow.build_comprehensive_request(model_id="m", run_id="run", section="AR",
        payload={"visual_observations": [], "text_observations": [], "sources": [], "native_context": []})
    for name, request in (("blocks", blocks), ("merge", merge), ("comprehensive", comprehensive)):
        assert sha(request.body["system"]) == BASE_V2_SYSTEM[name], name
        assert "СПРАВОЧНО" not in request.body["system"], name
    # a v2 request carries no digest of the rules at all: the rules digest is a v3 consent's
    assert "rules_sha256" not in blocks.body["messages"][0]["content"]


def test_the_critic_of_a_run_with_the_policy_gets_the_paragraph_and_loses_the_old_sentence():
    request = _critic(reference_section=True)
    system = request.body["system"]
    assert OLD_SENTENCE not in system
    for fragment in ("=== СПРАВОЧНО (не основание) ===", "Справочные данные недоступны: <причина>", "не цитируй его в source_evidence",
                     "Если к запросу приложены изображения страниц норм"):
        assert fragment in system
    # what stays: the instruction and the rule about what the critic may evaluate
    assert "оценивай только реально переданные текстовые контексты" in system and "Верни объект reviews" in system
    # only the adaptation moved: the user text of the request is the same but for the rules digest the file moved
    plain = json.loads(_critic().body["messages"][0]["content"])
    marked = json.loads(request.body["messages"][0]["content"])
    assert plain == marked


def test_the_prompt_names_the_heading_and_the_notice_the_agent_writes():
    """The words of the paragraph are the client's own (`tools/executor-runner/host_mode.py`), not a copy that can drift."""
    client = (ROOT / "tools/executor-runner/host_mode.py").read_text(encoding="utf-8")
    heading = re.search(r'^REFERENCE_HEADING = "(.+)"$', client, re.M).group(1)
    notice = re.search(r'^REFERENCE_UNAVAILABLE = "(.+?) "$', client, re.M).group(1)  # «Справочные данные недоступны:»
    system = _critic(reference_section=True).body["system"]
    assert heading in system and notice + " <причина>" in system


@pytest.mark.parametrize("value", ["yes", 1, None])
def test_the_flag_is_a_bool_or_the_request_is_refused(value):
    with pytest.raises(ValueError, match="review_reference_section_invalid"):
        _critic(reference_section=value)


# -- the rules digest -------------------------------------------------------------------------------------------------------------


def test_review_py_is_in_the_v3_rules_digest_so_a_prompt_change_moves_it(tmp_path, monkeypatch):
    """The digest is over the bytes of `review.py`: this lane's paragraph moves `rules_sha256` of every v3 run, the queued ones included.

    The consequence is the plan's own (section 3.5): a v3 run frozen before the deploy refuses with `extended_rules_changed_requires_consent`,
    so the deploy waits for an empty v3 queue or comes with a re-consent note. v2 and legacy consents hold no such digest."""
    source = Path(workflow.__file__).parent
    mirror = tmp_path / "extended"
    mirror.mkdir()
    for name in ("core.py", "workflow.py", "review.py", "native_pages.py", "coverage.py", "cross_window.py", "cross_window_review.py",
                 "block_ensemble.py"):
        shutil.copy2(source / name, mirror / name)
    shutil.copytree(source / "original_review", mirror / "original_review")
    real = workflow.review_bundle_digest("AR")
    # a v3 request carries the digest, which is how the runtime compares it with the consent's
    assert json.loads(_critic().body["messages"][0]["content"])["rules_sha256"] == real
    monkeypatch.setattr(workflow, "__file__", str(mirror / "workflow.py"))
    assert workflow.review_bundle_digest("AR") == real, "the mirror is the digest's input"
    with (mirror / "review.py").open("a", encoding="utf-8") as changed:
        changed.write("\n# a changed byte\n")
    assert workflow.review_bundle_digest("AR") != real


# -- the tolerant parse -----------------------------------------------------------------------------------------------------------


def _row(key, *, fix=False, quote=None):
    row = {"input_id": key, "source_ids": ["s1"], "llm_decision": "rewrite" if fix else "accept", "human_taxonomy_reason": "other",
        "confidence": 0.5, "explanation": "Пояснение", "evidence_checked": True, "source_dependency": "enough_source",
        "needs_correction": fix, "suggested_fix": "Уточнить" if fix else "", "source_evidence": []}
    if quote is not None:
        row.update(llm_decision="reject", confidence=0.9, source_evidence=[{"source_id": "s1", "quote": quote}])
    return row


def test_a_quote_from_the_reference_costs_one_row_and_not_the_whole_reply():
    text = json.dumps({"reviews": [_row("o1"), _row("o2", quote=FROM_REFERENCE), _row("o3")]}, ensure_ascii=False)
    keys = ("o1", "o2", "o3")
    # the strict reading, which the window path used to apply, refuses everything
    with pytest.raises(ValueError, match="review_quote_not_in_source"):
        review.parse_critic_reply(text, observations=_observations(*keys), sources=SOURCES)
    rejected = []
    kept = review.parse_critic_reply(text, observations=_observations(*keys), sources=SOURCES, rejected=rejected)
    assert [row["input_id"] for row in kept] == ["o1", "o3"]
    assert [(row["input_id"], row["reply_ordinal"], row["reason"]) for row in rejected] == [("o2", 1, "review_quote_not_in_source")]


# -- the runtime ------------------------------------------------------------------------------------------------------------------


class Window:
    """The `phase` and `call` doubles of one run of the window path (and of the batched path): replies are chosen by identity."""

    def __init__(self, replies):
        self.replies, self.phases, self.requests = replies, [], []

    def phase(self, identity, status, reason=None):
        self.phases.append((identity, status, reason))

    def call(self, request, identity):
        self.requests.append((identity, request))
        payload = json.loads(request.body["messages"][0]["content"])
        return NS(output_text=self.replies[identity](payload), response_sha256="b" * 64, truncated=False)

    @property
    def identities(self):
        return [identity for identity, _ in self.requests]

    def last(self, identity):
        return [row[1:] for row in self.phases if row[0] == identity][-1]


def _state(count=3):
    observations = [{"title": f"Наблюдение {number}", "description": "Описание", "source_ids": ["s1"]} for number in range(count)]
    return {"section": "AR", "source_sha256": "a" * 64, "sources": SOURCES, "observations": observations, "warnings": [],
        "coverage": {"blocks_total": 0, "blocks_processed": 0, "blocks_remaining": 0}}


def _critic_reply(*, refuse=(), fix=True):
    """A reply with one record per candidate; the ordinals in ``refuse`` quote the reference section."""
    def reply(payload):
        rows = [_row(item["input_id"], fix=fix and ordinal not in refuse, quote=FROM_REFERENCE if ordinal in refuse else None)
            for ordinal, item in enumerate(payload["observations"])]
        return json.dumps({"reviews": rows}, ensure_ascii=False)
    return reply


def _corrector_reply(payload):
    return json.dumps({"corrections": [{"input_id": row["input_id"], "action": "retain", "source_ids": row["source_ids"],
        "proposed_title": row["title"], "proposed_description": row["description"], "proposed_source_ids": row["source_ids"],
        "source_evidence": [], "explanation": "Достаточно", "required_context": []} for row in payload["observations"]]},
        ensure_ascii=False)


@pytest.fixture(autouse=True)
def _plain_cells(monkeypatch):
    """No stage plan machinery: the cell of a row is the model ``m`` with no settings, whatever the binding."""
    monkeypatch.setattr(runtime, "_kw", lambda binding, row, role="main": {"model_id": "m", "settings": None})


def _window(state, run, *, binding=NS(), reference_section=False):
    runtime._review_window_v3(session=None, run=NS(run_id="run"), binding=binding, state=state, phase=run.phase, call=run.call,
        window_id="w1", section="AR", contexts=[], reference_section=reference_section)


def test_a_reference_quote_in_the_window_critic_costs_its_row_and_the_window_goes_on():
    state = _state()
    run = Window({"critic": _critic_reply(refuse={1}), "corrector": _corrector_reply})
    _window(state, run)
    assert run.identities == ["critic", "corrector"], "the paid reply is kept and the corrector still runs; no repair call is made"
    first, second, third = state["observations"]
    assert [item["review_status"] for item in (first, second, third)] == ["reviewed", "not_reviewed", "reviewed"]
    assert second["review_reason"] == "finding_review_reply_refused" and "critic" not in second
    assert len(state["reviews"]) == 2 and state["critiques"] == state["reviews"]
    receipt, = state["reply_refusals"]
    assert (receipt["phase_key"], receipt["status"], receipt["accepted_record_count"]) == ("critic", "unresolved", 2)
    assert receipt["rejected_records"][0]["reason"] == "review_quote_not_in_source" and receipt["rejected_records"][0]["reply_ordinal"] == 1
    assert run.last("finding_review") == ("partial", "finding_review_reply_refused")
    # the corrector is asked about the two rows the critic answered, never about the refused one
    corrector = json.loads(dict(run.requests)["corrector"].body["messages"][0]["content"])
    assert len(corrector["observations"]) == 2 and second["title"] not in {row["title"] for row in corrector["observations"]}
    assert len(state["corrections"]) == 2 and run.last("finding_correction") == ("completed", None)
    assert run.last("report_generation") == ("completed", None) and state["report"]["observation_count"] == 3


def test_an_unreadable_window_critic_reply_fails_no_window_and_the_corrector_has_nothing_to_do():
    state = _state()
    run = Window({"critic": lambda _: "not json at all"})
    _window(state, run)
    assert run.identities == ["critic"]
    assert all(item["review_status"] == "not_reviewed" and item["review_reason"] == "finding_review_reply_refused"
        for item in state["observations"])
    receipt, = state["reply_refusals"]
    assert [row["reason"] for row in receipt["rejected_records"]] == ["reply_unreadable"] and receipt["accepted_record_count"] == 0
    assert run.last("finding_review") == ("partial", "finding_review_reply_refused")
    assert run.last("finding_correction") == ("unavailable", "critic_inputs_unavailable")
    assert run.last("report_generation") == ("completed", None) and state["corrections"] == []


def test_a_clean_window_reply_leaves_the_state_as_it_was_before():
    state = _state()
    run = Window({"critic": _critic_reply(), "corrector": _corrector_reply})
    _window(state, run)
    assert run.last("finding_review") == ("completed", None) and run.last("finding_correction") == ("completed", None)
    assert "reply_refusals" not in state
    assert all(item["review_status"] == "reviewed" and "review_reason" not in item for item in state["observations"])
    assert len(state["reviews"]) == 3 and len(state["corrections"]) == 3


def test_a_reference_quote_in_the_batched_critic_costs_its_row_too():
    state = _state()
    run = Window({"finding_review:b000": _critic_reply(refuse={0}, fix=False)})
    window = {"window_id": "w1", "policy": {"phase_call_limits": {kind: 8 for kind in ("finding_review", "finding_correction")}}}
    runtime._review_batched_v3(run=NS(run_id="run"), binding=NS(), state=state, phase=run.phase, call=run.call,
        window_context=window, contexts=[])
    refusal, = state["reply_refusals"]
    assert [row["reason"] for row in refusal["rejected_records"]] == ["review_quote_not_in_source"]
    assert refusal["accepted_record_count"] == 2 and len(state["reviews"]) == 2
    assert [item["review_status"] for item in state["observations"]] == ["not_reviewed", "reviewed", "reviewed"]
    assert run.last("finding_review") == ("partial", "finding_review_reply_refused")


# -- who is told about the section --------------------------------------------------------------------------------------------------

PLANNED = NS(cells=object())


@pytest.mark.parametrize("binding,policy,expected", [
    (PLANNED, {"executor_context_policy": POLICY}, True),
    (NS(), {"executor_context_policy": POLICY}, False),   # a run without a stage plan has no cells: legacy
    (PLANNED, {}, False),                                  # a planned run without the switch: its consent holds no policy
    (PLANNED, {"executor_context_policy": None}, False),
    (NS(cells=None), {"executor_context_policy": POLICY}, False),
])
def test_only_a_planned_run_whose_consent_holds_the_policy_is_told_about_the_section(binding, policy, expected):
    assert runtime._reference_section(binding, policy) is expected


def test_the_global_cross_window_critic_is_told_too_and_its_virtual_window_carries_nothing_else_new():
    accepted = {"call_limits": {"finding_review": 2}}
    consent = {"norm_paragraph_context_policy": {"version": "n"}, "completion_policy": "source-complete-v1", "semantic_repair_attempts": 1}
    without = runtime._virtual_window_policy(accepted, consent)
    with_policy = runtime._virtual_window_policy(accepted, {**consent, "executor_context_policy": POLICY})
    assert "executor_context_policy" not in without and runtime._reference_section(PLANNED, without) is False
    assert with_policy == {**without, "executor_context_policy": POLICY} and runtime._reference_section(PLANNED, with_policy) is True
    assert without["phase_call_limits"] == {"finding_review": 2} and without["semantic_repair_attempts"] == 1


@pytest.mark.parametrize("binding,policy,told", [
    (PLANNED, {"executor_context_policy": POLICY}, True),
    (NS(), {"executor_context_policy": POLICY}, False),
    (PLANNED, {}, False),
])
def test_the_runtime_asks_for_the_paragraph_exactly_when_it_is_told_about_the_section(binding, policy, told):
    window = {"window_id": "w1", "policy": {"phase_call_limits": {kind: 8 for kind in ("finding_review", "finding_correction")}, **policy}}
    # the batched path
    run = Window({"finding_review:b000": _critic_reply(fix=False)})
    runtime._review_batched_v3(run=NS(run_id="run"), binding=binding, state=_state(), phase=run.phase, call=run.call,
        window_context=window, contexts=[])
    system = run.requests[0][1].body["system"]
    assert ("=== СПРАВОЧНО (не основание) ===" in system) is told and (OLD_SENTENCE in system) is not told
    # the window path takes the flag the same way the dispatcher computes it
    run = Window({"critic": _critic_reply(fix=False)})
    _window(_state(), run, binding=binding, reference_section=runtime._reference_section(binding, window["policy"]))
    system = run.requests[0][1].body["system"]
    assert ("=== СПРАВОЧНО (не основание) ===" in system) is told and (OLD_SENTENCE in system) is not told
