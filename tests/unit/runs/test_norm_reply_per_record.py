"""`NORM-REPLY-PER-RECORD-01`: the v2 norm review reads its reply per record and the model names paragraphs only.

Prod run run_01M758J041ABF9KW9E2340TMMT (2026-11-11, section ЭОМ): one ``norms:main`` call with 35 inputs, a 58 406-char reply, 38
citations -- 36 byte-exact, 2 with a different text in ``quote``. ``parse_norm_review`` raised on the first bad record, the stage failed,
and the critic and the corrector were skipped. Here: the request that asks for ``paragraph_id`` only, the parser that fills the quote
from the input's own candidate and judges each record alone, and the runtime that keeps the records that were accepted.
"""

from __future__ import annotations

import json
from copy import deepcopy
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.analysis.extended import workflow
from auditmanager.analysis.extended.core import digest
from auditmanager.analysis.extended.workflow import (build_norm_review_request, build_norm_review_request_v3,
                                                     parse_norm_review)
from auditmanager.runs import extended_review as er
from tests.unit.analysis_extended import test_original_review_runtime as original_review
from tests.unit.analysis_extended.test_workflow_runtime import WorkflowAdapter

SNAPSHOT = "ns_01M59N8QNBVN91ACA2HCE6VE74"

#: Requests after the owner removed the norm-query count limit (`BLOCK-ANALYSIS-LIMITS-01`), with the bundle digest held at "r" * 64.
#: The default quote-echo shape remains shared with v3; ids-only mode still changes just its citation schema and instruction.
PAYLOAD = {"observations": [
    {"title": "T1", "description": "D1", "source_ids": ["s1"], "input_id": "xni_a", "norm_candidate_ids": ["p1", "p2"]},
    {"title": "T2", "description": "D2", "source_ids": ["s2"], "input_id": "xni_b", "norm_candidate_ids": ["p3"]}],
    "norm_context": [{"paragraph_id": "p1", "quote": "Q1"}, {"paragraph_id": "p2", "quote": "Q2"},
                     {"paragraph_id": "p3", "quote": "Q3"}], "source_sha256": "0" * 64}
V2_SHA = "b6be6cf5796be07104306e77caf2a3ed3759245cac65319990b54c5b6ad04cd9"
V2_SCOPE = "run_x:norm-review:90a09b0f63d77f71cb598cb17462fb0b4eecf4b51b0386c2f93397f68110e53d"
V3_SHA = "a6aca7e1ae7d072a6f527a9def7c4eec7cef5774815d1439ba59cdb6953b36bd"
V3_SCOPE = "run_x:v3:window-1:norm_verification:a6aca7e1ae7d072a6f527a9def7c4eec7cef5774815d1439ba59cdb6953b36bd"

OLD_RULE = ("Объясни связь и приведи реальные paragraph_id и ДОСЛОВНО ПОЛНУЮ переданную quote в citations; "
            "новые нормы и цитаты запрещены. ")
NEW_RULE = ("Объясни связь и в citations укажи только paragraph_id из norm_candidate_ids этого входа, каждый не более одного раза; "
            "текст цитаты не переписывай — его подставит сервер; новые нормы запрещены. ")


def request(**kwargs: Any) -> Any:
    return build_norm_review_request(model_id="m-1", run_id="run_x", section="EOM", payload=PAYLOAD, **kwargs)


def citation_schema(built: Any) -> dict[str, Any]:
    schema = built.body["output_config"]["format"]["schema"]
    return schema["properties"]["observations"]["items"]["properties"]["norm_assessment"]["anyOf"][1]["properties"]["citations"]


# ---------------------------------------------------------------------------------------------------------------- the request


def test_the_default_requests_keep_their_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(workflow, "review_bundle_digest", lambda section: "r" * 64)
    v2 = request()
    assert (v2.request_sha256, v2.idempotency_scope) == (V2_SHA, V2_SCOPE)
    assert v2.body == request(quote_echo=True).body
    v3 = build_norm_review_request_v3(model_id="m-1", run_id="run_x", section="EOM", payload=PAYLOAD, window_id="window-1")
    assert (v3.request_sha256, v3.idempotency_scope) == (V3_SHA, V3_SCOPE)
    assert OLD_RULE in v2.body["system"] and OLD_RULE in v3.body["system"] and NEW_RULE not in v3.body["system"]
    assert citation_schema(v2)["items"]["required"] == ["paragraph_id", "quote"]


def test_a_request_without_the_echo_asks_for_paragraph_ids_only() -> None:
    default, ids_only = request(), request(quote_echo=False)
    assert citation_schema(ids_only)["items"] == {"type": "object", "additionalProperties": False, "required": ["paragraph_id"],
                                                   "properties": {"paragraph_id": {"type": "string"}}}
    assert {k: v for k, v in citation_schema(ids_only).items() if k != "items"} == {
        k: v for k, v in citation_schema(default).items() if k != "items"}, "minItems and maxItems stay"
    assert citation_schema(ids_only)["minItems"] == 1 and citation_schema(ids_only)["maxItems"] == 6
    assert NEW_RULE in ids_only.body["system"] and OLD_RULE not in ids_only.body["system"]
    assert ids_only.body["system"].replace(NEW_RULE, OLD_RULE) == default.body["system"], "only that sentence differs"
    assert ids_only.idempotency_scope == f"run_x:norm-review-ids:{digest(PAYLOAD)}"
    assert ids_only.request_sha256 != default.request_sha256
    rest = lambda built: {k: v for k, v in built.body.items() if k not in {"system", "output_config"}}  # noqa: E731
    assert rest(ids_only) == rest(default)
    assert default.body["output_config"]["format"]["schema"]["properties"]["observations"]["items"]["properties"][
        "norm_assessment"]["anyOf"][1]["properties"]["citations"]["items"]["required"] == ["paragraph_id", "quote"], "no shared state"


# ---------------------------------------------------------------------------------------------------------------- the parser


def candidates(*pairs: tuple[str, str]) -> list[dict[str, Any]]:
    return [{"paragraph_id": paragraph, "quote": quote, "document_id": "ndoc_1"} for paragraph, quote in pairs]


def inputs() -> dict[str, dict[str, Any]]:
    return {
        "xni_a": {"title": "Заголовок A", "description": "Описание A", "source_ids": ["src_1"],
                  "norm_candidates": candidates(("pa1", "Текст «a1» с кавычками и ё"), ("pa2", "Текст a2"))},
        "xni_b": {"title": "Заголовок B", "description": "Описание B", "source_ids": ["src_2"],
                  "norm_candidates": candidates(("pb1", "Текст b1"))},
        "xni_c": {"title": "Заголовок C", "description": "Описание C", "source_ids": ["src_1", "src_2"],
                  "norm_candidates": candidates(("pc1", "Текст c1"))}}


def record(key: str, observations: dict[str, dict[str, Any]], *paragraphs: str, **over: Any) -> dict[str, Any]:
    source = observations[key]
    row = {"title": source["title"], "description": source["description"], "source_ids": list(source["source_ids"]),
           "norm_queries": [], "input_ids": [key],
           "norm_assessment": {"relation": "supports", "explanation": "Связь описана",
                               "citations": [{"paragraph_id": p} for p in (paragraphs or (source["norm_candidates"][0]["paragraph_id"],))]}}
    row.update(over)
    return row


def reply(*rows: dict[str, Any]) -> str:
    return json.dumps({"observations": list(rows)}, ensure_ascii=False)


def read(text: str, observations: dict[str, dict[str, Any]], **kwargs: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rejected: list[dict[str, Any]] = []
    accepted = parse_norm_review(text, observations=observations, rejected=rejected, quote_echo=False, **kwargs)
    return accepted, rejected


def test_the_server_fills_each_quote_from_the_inputs_own_candidate() -> None:
    observations = inputs()
    text = reply(record("xni_a", observations, "pa2", ), record("xni_b", observations), record("xni_c", observations))
    accepted, rejected = read(text, observations)
    assert rejected == [] and [row["input_ids"] for row in accepted] == [["xni_a"], ["xni_b"], ["xni_c"]]
    assert accepted[0]["norm_assessment"]["citations"] == [{"paragraph_id": "pa2", "quote": "Текст a2"}]
    assert accepted[1]["norm_assessment"]["citations"] == [{"paragraph_id": "pb1", "quote": "Текст b1"}]
    strict = parse_norm_review(text, observations=observations, quote_echo=False)
    assert strict == accepted, "no rejected list: the same records, read strictly"


def test_a_record_that_cites_another_inputs_paragraph_is_refused_and_the_others_survive() -> None:
    observations = inputs()
    text = reply(record("xni_a", observations), record("xni_b", observations, "pa1"), record("xni_c", observations))
    accepted, rejected = read(text, observations)
    assert [row["input_ids"] for row in accepted] == [["xni_a"], ["xni_c"]]
    assert [(row["reply_ordinal"], row["reason"]) for row in rejected] == [(1, "norm_citation_not_in_context")]
    assert rejected[0]["record"]["input_ids"] == ["xni_b"]
    with pytest.raises(ValueError, match="norm_citation_not_in_context"):
        parse_norm_review(text, observations=observations, quote_echo=False)


def test_only_a_bare_paragraph_id_is_filled_everything_else_is_left_for_the_core_parser() -> None:
    observations = inputs()
    paragraph = observations["xni_a"]["norm_candidates"][0]
    echoed_right = record("xni_a", observations)
    echoed_right["norm_assessment"]["citations"] = [{"paragraph_id": "pa1", "quote": paragraph["quote"]}]
    echoed_wrong = record("xni_b", observations)
    echoed_wrong["norm_assessment"]["citations"] = [{"paragraph_id": "pb1", "quote": "другой текст"}]
    extra_key = record("xni_c", observations)
    extra_key["norm_assessment"]["citations"] = [{"paragraph_id": "pc1", "note": "x"}]
    accepted, rejected = read(reply(echoed_right, echoed_wrong, extra_key), observations)
    assert [row["input_ids"] for row in accepted] == [["xni_a"]], "an echo is judged as it always was"
    assert [row["reason"] for row in rejected] == ["norm_citation_not_in_context"] * 2
    unknown = record("xni_a", observations, "unknown")
    twice = record("xni_b", observations, "pb1", "pb1")
    merged = record("xni_c", observations, "pc1", input_ids=["xni_a", "xni_c"])
    accepted, rejected = read(reply(unknown, twice, merged), observations)
    assert accepted == [], "an unknown id, a repeated id and a record that binds two inputs are not filled and not accepted"
    assert [row["reason"] for row in rejected] == ["norm_citation_not_in_context"] * 3


def test_the_default_parse_does_not_fill_a_bare_paragraph_id() -> None:
    observations = inputs()
    rows = [record(key, observations) for key in observations]
    with pytest.raises(ValueError, match="norm_citation_not_in_context"):
        parse_norm_review(reply(*rows), observations=observations)
    with pytest.raises(ValueError, match="norm_citation_not_in_context"):
        parse_norm_review(reply(*rows), observations=observations, quote_echo=True)


def test_the_partition_is_judged_per_record_when_a_rejected_list_is_given() -> None:
    observations = inputs()
    good = record("xni_a", observations)
    repeated = record("xni_a", observations, "pa2")
    queried = record("xni_b", observations, norm_queries=["СП 1"])
    changed = record("xni_c", observations, title="Другой заголовок")
    accepted, rejected = read(reply(good, repeated, queried, changed), observations)
    assert [row["input_ids"] for row in accepted] == [["xni_a"]]
    assert [(row["reply_ordinal"], row["reason"]) for row in rejected] == [
        (None, "norm_review_input_partition_invalid"), (None, "norm_review_input_partition_invalid"),
        (None, "norm_review_observation_changed")]
    assert [row["record"]["input_ids"] for row in rejected] == [["xni_a"], ["xni_b"], ["xni_c"]]
    assert rejected[0]["record"]["norm_assessment"]["citations"][0]["quote"] == "Текст a2", "a copy of the refused record"
    with pytest.raises(ValueError, match="norm_review_input_partition_invalid"):
        parse_norm_review(reply(good, repeated), observations=observations, quote_echo=False)
    with pytest.raises(ValueError, match="norm_review_input_partition_invalid"):
        parse_norm_review(reply(queried), observations=observations, quote_echo=False)
    with pytest.raises(ValueError, match="norm_review_observation_changed"):
        parse_norm_review(reply(changed), observations=observations, quote_echo=False)


def test_an_input_the_reply_did_not_carry_is_not_an_error_with_a_rejected_list_and_is_one_without() -> None:
    observations = inputs()
    accepted, rejected = read(reply(record("xni_b", observations)), observations)
    assert [row["input_ids"] for row in accepted] == [["xni_b"]] and rejected == []
    with pytest.raises(ValueError, match="norm_review_input_partition_invalid"):
        parse_norm_review(reply(record("xni_b", observations)), observations=observations, quote_echo=False)


@pytest.mark.parametrize("text,code", [
    ("not json", None),
    ("", None),
    ('{"observations": [], "observations": []}', "duplicate_key"),
    ('{"observations": [{"x": NaN}]}', "nonfinite"),
    ('["observations"]', "reply_shape_invalid"),
    ('{"other": []}', "reply_shape_invalid"),
    ('{"observations": {}}', "reply_shape_invalid")])
def test_a_reply_invalid_as_a_whole_still_raises(text: str, code: str | None) -> None:
    rejected: list[dict[str, Any]] = []
    with pytest.raises(ValueError) as caught:
        parse_norm_review(text, observations=inputs(), rejected=rejected, quote_echo=False)
    if code is not None:
        assert str(caught.value) == code
    assert rejected == []


def test_a_malformed_record_is_one_refusal_and_never_an_exception() -> None:
    observations = inputs()
    odd = [None, 3, "text", [], {"input_ids": "xni_a"}, {"input_ids": [["xni_a"]], "norm_assessment": {"citations": [1]}},
           record("xni_a", observations) | {"norm_assessment": {"relation": "supports", "explanation": "e", "citations": [None, 3]}},
           record("xni_b", observations) | {"norm_assessment": {"citations": {"paragraph_id": "pb1"}}}]
    accepted, rejected = read(reply(*odd, record("xni_c", observations)), observations)
    assert [row["input_ids"] for row in accepted] == [["xni_c"]] and len(rejected) == len(odd)
    assert all(row["reply_ordinal"] is not None for row in rejected)


# ---------------------------------------------------------------------------------------------------------------- the runtime


def hit(paragraph: str, text: str) -> Any:
    return SimpleNamespace(norms_snapshot_id=SNAPSHOT, norm_document_id="ndoc_1", norm_paragraph_id=paragraph,
                           designation="СП 16.13330.2017", clause_number="14.1.7", page_label="42",
                           fragment=SimpleNamespace(text=text))


class Phases:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, identity: str, status: str, reason: str | None = None) -> None:
        self.calls.append((identity, status, reason))


class Model:
    """A recorded model: ``answers`` turns the request into the reply text; every request it saw is kept."""

    def __init__(self, answers: Any) -> None:
        self.answers, self.requests, self.identities = answers, [], []

    def __call__(self, request: Any, identity: str) -> Any:
        self.requests.append(request)
        self.identities.append(identity)
        return SimpleNamespace(output_text=self.answers(request), truncated=False, response_sha256="a" * 64)


@pytest.fixture
def corpus(monkeypatch: pytest.MonkeyPatch) -> None:
    def search(session: Any, *, q: str, norms_snapshot_id: str, cursor: Any, limit: int, timeout_ms: int) -> Any:
        number = q.rsplit(" ", 1)[-1]
        return SimpleNamespace(items=[hit(f"npar_{number}", f"Текст пункта {number} «дословно»")], next_cursor=None)

    monkeypatch.delenv("AUDITMANAGER_NORM_EMBED_URL", raising=False)
    monkeypatch.setattr(er, "search_norms", search)


def observations_of(count: int) -> list[dict[str, Any]]:
    return [{"observation_id": f"obs_{n}", "title": f"Замечание {n}", "description": f"Описание {n}", "source_ids": ["src_1"],
             "norm_queries": [f"СП 16.13330 пункт {n}"]} for n in range(1, count + 1)]


def run_norm_stage(model: Model, items: list[dict[str, Any]]) -> tuple[Phases, dict[str, Any]]:
    phases = Phases()
    state = {"observations": items, "warnings": [], "sources": [{"source_id": "src_1"}], "source_sha256": "0" * 64}
    er._full_norm_verification(session=SimpleNamespace(rollback=lambda: None), run=SimpleNamespace(run_id="run_1"),
                               model_id="m-1", section="EOM", state=state, snapshot_id=SNAPSHOT, call=model,
                               phase=phases, checkpoint=None)
    return phases, state


def answer(request: Any, *, foreign: int | None = None) -> str:
    """The reply the owner asked for: ``paragraph_id`` only; the record ``foreign`` cites the paragraph of the first input."""
    payload = json.loads(request.body["messages"][0]["content"])
    rows = []
    for ordinal, original in enumerate(payload["observations"]):
        cited = payload["observations"][0]["norm_candidate_ids"] if ordinal == foreign else original["norm_candidate_ids"]
        rows.append({"title": original["title"], "description": original["description"], "source_ids": original["source_ids"],
                     "norm_queries": [], "input_ids": [original["input_id"]],
                     "norm_assessment": {"relation": "supports", "explanation": "Связь описана",
                                         "citations": [{"paragraph_id": cited[0]}]}})
    return json.dumps({"observations": rows}, ensure_ascii=False)


def test_one_bad_record_costs_only_itself_and_the_stage_is_partial(corpus: None) -> None:
    items = observations_of(3)
    model = Model(lambda request: answer(request, foreign=1))
    phases, state = run_norm_stage(model, items)
    assert phases.calls == [("norm_verification", "partial", "norm_verification_reply_refused")]
    assert model.identities == ["norm_verification:0"], "one question, no repair call"
    assert citation_schema(model.requests[0])["items"]["required"] == ["paragraph_id"]
    assert [item["norm_review_status"] for item in items] == ["reviewed", "not_reviewed", "reviewed"]
    assert [item["norm_review_reason"] for item in items] == [None, "norm_verification_reply_refused", None]
    for item in (items[0], items[2]):
        citation = item["norm_assessment"]["citations"][0]
        assert citation["quote"] == item["norm_candidates"][0]["quote"] and citation["paragraph_id"] == item["norm_candidates"][0]["paragraph_id"]
    assert "norm_assessment" not in items[1]
    (receipt,) = state["reply_refusals"]
    assert receipt["phase_key"] == "norm_verification:0" and receipt["status"] == "unresolved" and receipt["accepted_record_count"] == 2
    assert [row["reason"] for row in receipt["rejected_records"]] == ["norm_citation_not_in_context"]
    assert receipt["rejected_records"][0]["record"]["title"] == "Замечание 2"


def test_a_good_reply_completes_the_stage_with_every_input_reviewed(corpus: None) -> None:
    items = observations_of(3)
    phases, state = run_norm_stage(Model(answer), items)
    assert phases.calls == [("norm_verification", "completed", None)]
    assert [item["norm_review_status"] for item in items] == ["reviewed"] * 3 and "reply_refusals" not in state


@pytest.mark.parametrize("text", ["I cannot answer this.", "", "{", '{"observations": [], "observations": []}'])
def test_a_reply_that_is_not_json_refuses_every_input_without_an_exception(corpus: None, text: str) -> None:
    items = observations_of(3)
    phases, state = run_norm_stage(Model(lambda _request: text), items)
    assert phases.calls == [("norm_verification", "partial", "norm_verification_reply_refused")]
    assert {item["norm_review_status"] for item in items} == {"not_reviewed"}
    assert {item["norm_review_reason"] for item in items} == {"norm_verification_reply_refused"}
    assert all("norm_assessment" not in item for item in items)
    (receipt,) = state["reply_refusals"]
    assert receipt["accepted_record_count"] == 0 and receipt["rejected_records"][0]["reply_ordinal"] is None


def test_an_input_the_reply_left_out_is_not_reviewed_and_makes_the_stage_partial(corpus: None) -> None:
    items = observations_of(3)

    def answer_two(request: Any) -> str:
        rows = json.loads(answer(request))["observations"]
        return json.dumps({"observations": rows[:2]}, ensure_ascii=False)
    phases, state = run_norm_stage(Model(answer_two), items)
    assert phases.calls == [("norm_verification", "partial", "norm_verification_reply_refused")]
    assert [item["norm_review_status"] for item in items] == ["reviewed", "reviewed", "not_reviewed"]
    assert "reply_refusals" not in state, "the model refused nothing: it left an input out"


def test_a_truncated_reply_keeps_what_parsed_and_is_partial(corpus: None) -> None:
    items = observations_of(2)

    class Truncated(Model):
        def __call__(self, request: Any, identity: str) -> Any:
            response = super().__call__(request, identity)
            response.truncated = True
            return response
    phases, state = run_norm_stage(Truncated(answer), items)
    assert phases.calls == [("norm_verification", "partial", "norm_verification_reply_refused")]
    assert [item["norm_review_status"] for item in items] == ["reviewed"] * 2
    assert state["reply_refusals"][0]["rejected_records"] == [{"reason": "extended_response_truncated", "reply_ordinal": None}]


def test_the_refusals_of_every_batch_are_kept_and_a_later_batch_is_still_asked(corpus: None) -> None:
    items = observations_of(45)  # two batches: 40 and 5
    asked = iter([True, False])
    model = Model(lambda request: answer(request, foreign=1) if next(asked) else answer(request))
    phases, state = run_norm_stage(model, items)
    assert model.identities == ["norm_verification:0", "norm_verification:1"]
    assert phases.calls == [("norm_verification", "partial", "norm_verification_reply_refused")]
    assert sum(item["norm_review_status"] == "not_reviewed" for item in items) == 1
    assert sum(item["norm_review_status"] == "reviewed" for item in items) == 44
    assert [receipt["phase_key"] for receipt in state["reply_refusals"]] == ["norm_verification:0"]


def test_a_transport_failure_is_not_a_reply_and_still_propagates(corpus: None) -> None:
    def failing(_request: Any, _identity: str) -> Any:
        raise RuntimeError("provider outcome unknown")
    with pytest.raises(RuntimeError):
        run_norm_stage(failing, observations_of(2))  # type: ignore[arg-type]


def test_a_per_record_norm_refusal_does_not_skip_the_critic_and_the_corrector(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(original_review, "WorkflowAdapter", lambda: WorkflowAdapter(bad_norm=True))
    result, _adapter, saved = original_review.run_v2(monkeypatch, original_review.MARKED, observations_document=original_review.PRIMARY)
    procedures = {p["id"]: p for p in result["procedures"]}
    assert (procedures["norm_verification"]["status"], procedures["norm_verification"]["reason"]) == (
        "partial", "norm_verification_reply_refused")
    assert procedures["finding_review"]["status"] == procedures["finding_correction"]["status"] == "completed"
    assert not any(p.get("reason") == "dependency_failed" for p in result["procedures"])
    assert saved[-1][0] == "partial"
    assert result["observations"] and all(o["review_status"] == "reviewed" for o in result["observations"])


def test_the_review_annotates_an_observation_and_changes_nothing_else_of_it(corpus: None) -> None:
    items = observations_of(2)
    before = deepcopy(items)
    run_norm_stage(Model(answer), items)
    for item, original in zip(items, before):
        assert all(item[key] == original[key] for key in ("observation_id", "title", "description", "source_ids"))
        assert set(item) - set(original) == {"norm_status", "norm_candidates", "norm_assessment", "norm_review_status",
                                             "norm_review_reason"}
    assert items[0]["norm_assessment"]["citations"] == [{"paragraph_id": "npar_1", "quote": "Текст пункта 1 «дословно»"}]
