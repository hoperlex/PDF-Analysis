"""`CTX-STAND` (ADR-0029 decision 3): the reference data of a `review:main` task, without a database.

What is shown, and what each case would let through if the rule were missing:

* the **policy** is one fixed document and a consent is served only when it holds exactly that one;
* the **descriptor** names every observation of a critic request once, by the digest of its words, and names nothing it cannot name in full;
* the **refusals**: a comparison task, a run without a stage plan, a run that asks for plan v2, any cell but `review:main`, a task with no
  descriptor and a consent without the same policy each answer `404` -- and the source is never asked and the journal is never written;
* **while temporary decision 2 stands** the answer is `unavailable / until_move` and is journalled as such;
* **idempotency**: a repeat of (task, kind) is the same answer, asks nothing of the source and writes no second row; the budget of the task is the
  two kinds and 12 000 characters, and what does not fit is counted, not cut;
* the **journal** holds identities and a digest, never a word of the cases.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

import pytest

from auditmanager.executors import task_context as tc
from auditmanager.executors.runner_repository import TaskRecord
from auditmanager.executors.task_context import (
    ContextInput,
    RunContextFacts,
    SourceCase,
    Unavailable,
    UntilMoveSource,
    serve_context,
)
from auditmanager.executors.task_context_repository import DeliveryRecord
from auditmanager.shared.errors import DomainError, ErrorCode

NOW = datetime(2026, 11, 11, 9, 0, tzinfo=timezone.utc)
RUN = "run_01M2545JSD15ETSNNV904X991K"
TASK = "ext_01M2545JSD15ETSNNV904X991K"
CALL = "mc_01M2545JSD15ETSNNV904X991K"
SHA = "a" * 64


def descriptor(*ids: str, section: str = "AR") -> list[dict[str, str]]:
    return [{"input_id": identity, "text_sha256": SHA, "section": section} for identity in ids]


def payload(*, cell: str | None = "review:main", ids: tuple[str, ...] = ("xri_1", "xri_2")) -> dict[str, Any]:
    value: dict[str, Any] = {"system": "s", "user_text": "{}", "output_schema": {"type": "object"}}
    if cell is not None:
        value["host"] = {"provider": "claude_code", "access": "subscription", "model_id": "m", "effort": "medium",
                         "timeout_seconds": 600, "cell_key": cell}
    if ids:
        value["context_request"] = descriptor(*ids)
    return value


def task(*, origin: str = "run_call", run_id: str | None = RUN) -> TaskRecord:
    return TaskRecord(
        task_id=TASK, connection_id="exc_C", revision_id="excr_R", origin=origin, run_id=run_id, attempt_id="att_A", model_call_id=CALL,
        probe_id=None, state="claimed", expected_model="m", created_at=NOW, deadline_at=NOW, claimed_by_token_id="ern_T",
        claim_expires_at=NOW, first_claimed_at=NOW, claim_count=1, declared_model=None, declared_input_tokens=None,
        declared_output_tokens=None, fail_reason=None, terminal_at=None, payload_cleared_at=None, past_deadline=False)


ELIGIBLE = RunContextFacts(True, "extended-review-v3", "AR", tc.executor_context_policy())


class Journal:
    """``ContextDeliveryRepository`` in memory: the unique (task, kind) and nothing else."""

    def __init__(self) -> None:
        self.rows: dict[tuple[str, str], DeliveryRecord] = {}
        self.inserts = 0

    def get(self, session: Any, task_id: str, kind: str) -> DeliveryRecord | None:
        return self.rows.get((task_id, kind))

    def insert(self, session: Any, *, task_id: str, run_id: str, model_call_id: str | None, kind: str, status: str, reason: str | None,
               case_ids: Any, characters: int, block_sha256: str | None) -> DeliveryRecord:
        self.inserts += 1
        assert (task_id, kind) not in self.rows, "the table is unique by (task, kind): a second insert is refused"
        assert (status == "unavailable") == (reason is not None) and (status == "delivered") == (block_sha256 is not None)
        self.rows[(task_id, kind)] = row = DeliveryRecord(
            f"etd_{len(self.rows):026d}", task_id, run_id, model_call_id, kind, status, reason, tuple(case_ids), characters, block_sha256, NOW)
        return row


class Tasks:
    """The part of ``RunnerRepository`` the answer touches: where a delivered block is remembered."""

    def __init__(self) -> None:
        self.remembered: dict[tuple[str, str], Any] = {}

    def remember_context_answer(self, session: Any, *, task_id: str, kind: str, answer: Any) -> None:
        assert (task_id, kind) not in self.remembered
        self.remembered[(task_id, kind)] = json.loads(json.dumps(answer))


class Source:
    """A source that counts what it is asked, and answers what it was told to."""

    def __init__(self, answer: Any) -> None:
        self.answer = answer
        self.asked: list[tuple[str, str]] = []

    def read(self, session: Any, *, run_id: str, kind: str, inputs: Any) -> Any:
        self.asked.append((run_id, kind))
        return self.answer


def case(n: int, *, size: int = 100, comment: str | None = None) -> SourceCase:
    return SourceCase(f"dmc_{n:026d}", "rejected", "dimensions", 0.9, "Ф" * size, "Р" * size, comment)


def run(*, kind: str = "similar_cases", source: Any = None, facts: RunContextFacts = ELIGIBLE, pay: dict[str, Any] | None = None,
        record: TaskRecord | None = None, journal: Journal | None = None, tasks: Tasks | None = None, payloads: dict[str, Any] | None = None):
    journal = journal if journal is not None else Journal()
    tasks = tasks if tasks is not None else Tasks()
    source = source if source is not None else Source(Unavailable("until_move"))
    pay = pay if pay is not None else payload()
    answer = serve_context(None, task=record or task(), payload=pay, kind=kind, source=source, tasks=tasks,  # type: ignore[arg-type]
                           deliveries=journal, facts=lambda session, run_id: facts)  # type: ignore[arg-type]
    return answer, journal, tasks, source


# -- the policy ---------------------------------------------------------------------------------------------


def test_the_policy_is_the_one_document_of_plan_v5_and_a_consent_is_served_only_under_exactly_it() -> None:
    policy = tc.executor_context_policy()
    assert policy["kinds"] == ["similar_cases", "patterns"] and policy["methods"] == ["bge-m3-dense-v1"]
    assert (policy["max_requests_per_task"], policy["max_characters_per_task"], policy["input_tokens_reserved_per_call"]) == (2, 12_000, 5_000)
    assert policy["selection"] == {"order": "window", "max_cases_per_candidate": 3, "remainder": "not_fitted_count"}
    assert len(policy["bundle_sha256"]) == 64 and policy == tc.executor_context_policy(), "the same document every time"
    assert tc.policy_in_force(policy)
    # each way of not holding it: nothing, another digest, another figure, a member more, a member less
    assert not tc.policy_in_force(None) and not tc.policy_in_force({}) and not tc.policy_in_force("x")
    assert not tc.policy_in_force({**policy, "bundle_sha256": "0" * 64})
    assert not tc.policy_in_force({**policy, "max_characters_per_task": 18_000})
    assert not tc.policy_in_force({**policy, "extra": 1})
    assert not tc.policy_in_force({key: value for key, value in policy.items() if key != "scope"})


def test_the_policys_budget_is_the_budgets_own_figure_not_a_second_copy_of_it() -> None:
    from auditmanager.precedents.public import MAX_CASES_PER_ENTRY, MAX_CHARACTERS

    policy = tc.executor_context_policy()
    assert policy["max_characters_per_task"] == MAX_CHARACTERS and policy["selection"]["max_cases_per_candidate"] == MAX_CASES_PER_ENTRY


# -- the descriptor -----------------------------------------------------------------------------------------


def request_text(*observations: dict[str, Any]) -> str:
    return json.dumps({"workflow_version": "v3", "observations": list(observations)}, ensure_ascii=False)


def test_the_descriptor_names_each_observation_once_in_order_by_the_digest_of_its_words() -> None:
    import hashlib

    text = request_text({"input_id": "xri_a", "title": "Заголовок", "description": "Описание"},
                        {"input_id": "xri_b", "title": "Т", "description": "Т и продолжение"})
    entries = tc.context_request_of(text, section="AR")
    assert [entry["input_id"] for entry in entries] == ["xri_a", "xri_b"] and {entry["section"] for entry in entries} == {"AR"}
    # the title over the description, as the publisher states a candidate's words; a description that starts with the title stands alone
    assert entries[0]["text_sha256"] == hashlib.sha256("Заголовок\n\nОписание".encode()).hexdigest()
    assert entries[1]["text_sha256"] == hashlib.sha256("Т и продолжение".encode()).hexdigest()


@pytest.mark.parametrize("text", [
    "not json", "[]", "{}", request_text(),
    request_text({"input_id": "a", "title": "t", "description": "d"}, {"input_id": "a", "title": "u", "description": "e"}),
    request_text({"input_id": "x" * 129, "title": "t", "description": "d"}),
    request_text({"input_id": "a", "title": " ", "description": " "}),
    request_text({"input_id": "a"}), request_text({"title": "t", "description": "d"}),
    request_text(*({"input_id": f"i{n}", "title": "t", "description": "d"} for n in range(65))),
])
def test_a_request_that_cannot_be_named_in_full_is_offered_nothing(text: str) -> None:
    assert tc.context_request_of(text, section="AR") is None


def test_a_descriptor_that_is_not_exactly_the_contracts_shape_reads_as_none() -> None:
    assert tc.read_descriptor(None) == () and tc.read_descriptor({}) == () and tc.read_descriptor({"context_request": []}) == ()
    assert tc.read_descriptor({"context_request": descriptor("a")}) == (ContextInput("a", SHA, "AR"),)
    for bad in ([{"input_id": "a", "text_sha256": SHA}], [{**descriptor("a")[0], "x": 1}], [{**descriptor("a")[0], "text_sha256": "A" * 64}],
                [{**descriptor("a")[0], "input_id": ""}], [{**descriptor("a")[0], "section": "x" * 65}], "a"):
        assert tc.read_descriptor({"context_request": bad}) == (), bad


# -- the eligibility of a run --------------------------------------------------------------------------------


def test_a_run_is_eligible_only_on_the_stage_layout_under_v3_with_a_section_and_the_same_policy() -> None:
    assert tc.context_eligible(ELIGIBLE)
    assert not tc.context_eligible(replace(ELIGIBLE, stage_plan=False))
    assert not tc.context_eligible(replace(ELIGIBLE, plan_version="extended-review-v2"))
    assert not tc.context_eligible(replace(ELIGIBLE, plan_version=None))
    assert not tc.context_eligible(replace(ELIGIBLE, section=None)) and not tc.context_eligible(replace(ELIGIBLE, section="a b"))
    assert not tc.context_eligible(replace(ELIGIBLE, policy=None))
    assert not tc.context_eligible(replace(ELIGIBLE, policy={**tc.executor_context_policy(), "bundle_sha256": "1" * 64}))


# -- the refusals --------------------------------------------------------------------------------------------


REFUSED = {
    "a comparison task": dict(record=task(origin="comparison_call", run_id=None)),
    "a probe": dict(record=task(origin="probe", run_id=None)),
    "a comparison task, even one that named a run": dict(record=task(origin="comparison_call", run_id=RUN)),
    "a probe, even one that named a run": dict(record=task(origin="probe", run_id=RUN)),
    "a legacy run (no stage plan)": dict(facts=replace(ELIGIBLE, stage_plan=False)),
    "a run that asks for plan v2": dict(facts=replace(ELIGIBLE, plan_version="extended-review-v2")),
    "a consent without the policy": dict(facts=replace(ELIGIBLE, policy=None)),
    "a consent with another digest": dict(facts=replace(ELIGIBLE, policy={**tc.executor_context_policy(), "bundle_sha256": "2" * 64})),
    "a consent that cannot be read": dict(facts=tc.NO_FACTS),
    "the cell text:main": dict(pay=payload(cell="text:main")),
    "the cell correction:main": dict(pay=payload(cell="correction:main")),
    "the cell review:main of no host (a task without host members)": dict(pay=payload(cell=None)),
    "a task with no descriptor": dict(pay=payload(ids=())),
}


@pytest.mark.parametrize("name", sorted(REFUSED))
def test_a_task_that_may_not_be_given_reference_data_is_not_found_and_costs_nothing(name: str) -> None:
    source = Source(Unavailable("until_move"))
    journal = Journal()
    with pytest.raises(DomainError) as refused:
        run(source=source, journal=journal, **REFUSED[name])
    assert refused.value.code is ErrorCode.NOT_FOUND
    assert source.asked == [] and journal.inserts == 0, "nothing was asked of the source and nothing was journalled"


def test_every_refusal_above_is_the_refusal_of_that_one_rule_the_same_task_is_served_when_the_rule_holds() -> None:
    answer, journal, _, source = run()
    assert answer.status == "unavailable" and journal.inserts == 1 and len(source.asked) == 1


def test_a_kind_the_stand_does_not_serve_is_a_validation_failure_not_a_search() -> None:
    source = Source({})
    with pytest.raises(DomainError) as refused:
        run(kind="norm_excerpts", source=source)
    assert refused.value.code is ErrorCode.VALIDATION_FAILED and source.asked == []


# -- while temporary decision 2 stands -------------------------------------------------------------------------


def test_the_encoder_that_runs_by_night_gives_unavailable_until_move_and_the_journal_says_so() -> None:
    answer, journal, tasks, _ = run(source=UntilMoveSource())
    assert answer.wire() == {"kind": "similar_cases", "status": "unavailable", "reason": "until_move", "items": [], "not_fitted": 0}
    row = journal.rows[(TASK, "similar_cases")]
    assert (row.status, row.reason, row.case_ids, row.characters, row.block_sha256, row.run_id, row.model_call_id) == (
        "unavailable", "until_move", (), 0, None, RUN, CALL)
    assert tasks.remembered == {}, "an answer with no data keeps nothing in the task"


def test_patterns_have_no_source_yet_and_say_so_in_their_own_word() -> None:
    answer, journal, _, _ = run(kind="patterns", source=UntilMoveSource())
    assert (answer.status, answer.reason) == ("unavailable", "patterns_not_available")
    assert journal.rows[(TASK, "patterns")].reason == "patterns_not_available"


# -- idempotency and the budget --------------------------------------------------------------------------------


def test_a_repeat_of_an_unavailable_answer_is_the_same_answer_and_asks_and_writes_nothing() -> None:
    source, journal, tasks = Source(Unavailable("until_move")), Journal(), Tasks()
    first, *_ = run(source=source, journal=journal, tasks=tasks)
    again, *_ = run(source=source, journal=journal, tasks=tasks)
    assert again == first and len(source.asked) == 1 and journal.inserts == 1 and len(journal.rows) == 1


def test_the_two_kinds_are_the_two_requests_of_a_task_and_each_is_paid_for_once() -> None:
    source, journal, tasks = Source(Unavailable("until_move")), Journal(), Tasks()
    for kind in ("similar_cases", "patterns", "similar_cases", "patterns", "similar_cases"):
        run(kind=kind, source=source, journal=journal, tasks=tasks)
    assert sorted(kind for _, kind in source.asked) == ["patterns", "similar_cases"] and len(journal.rows) == 2 == tc.executor_context_policy()[
        "max_requests_per_task"]


def delivering(ids: tuple[str, ...] = ("xri_1", "xri_2"), per: int = 2, size: int = 100) -> Source:
    return Source({identity: [case(index * 10 + n, size=size) for n in range(per)] for index, identity in enumerate(ids, start=1)})


def test_a_delivered_block_is_journalled_by_identity_and_digest_and_a_repeat_returns_it_without_asking_again() -> None:
    source, journal, tasks = delivering(), Journal(), Tasks()
    first, *_ = run(source=source, journal=journal, tasks=tasks)
    wire = first.wire()
    assert wire["status"] == "available" and "reason" not in wire and wire["not_fitted"] == 0
    assert [item["input_id"] for item in wire["items"]] == ["xri_1", "xri_2"] and all(len(item["cases"]) == 2 for item in wire["items"])
    row = journal.rows[(TASK, "similar_cases")]
    assert row.status == "delivered" and row.reason is None and row.block_sha256 == wire["context_sha256"]
    assert row.case_ids == tuple(c["case_id"] for item in wire["items"] for c in item["cases"]) and row.characters > 0
    # a repeat: the same answer, byte for byte, no second question to the source, no second row, no second remembered block
    again, *_ = run(source=source, journal=journal, tasks=tasks, pay={**payload(), "context_answers": {"similar_cases": tasks.remembered[(TASK, "similar_cases")]}})
    assert again.wire() == wire and len(source.asked) == 1 and journal.inserts == 1 and len(tasks.remembered) == 1


def test_a_delivered_block_that_is_journalled_and_not_remembered_is_a_defect_not_a_guess() -> None:
    source, journal = delivering(), Journal()
    run(source=source, journal=journal)
    with pytest.raises(DomainError) as defect:
        run(source=source, journal=journal)  # the payload carries no remembered block
    assert defect.value.code is ErrorCode.INTERNAL_ERROR and len(source.asked) == 1


def test_the_journal_holds_no_word_of_the_cases() -> None:
    source, journal = delivering(), Journal()
    answer, *_ = run(source=source, journal=journal)
    row = journal.rows[(TASK, "similar_cases")]
    kept = json.dumps([getattr(row, name) for name in row.__slots__], default=str, ensure_ascii=False)
    for item in answer.items:
        for chosen in item["cases"]:
            assert chosen["finding_text"] not in kept and chosen["recommendation_text"] not in kept
    assert {"finding_text", "recommendation_text", "comment", "text"}.isdisjoint(row.__slots__)


def test_at_most_three_cases_a_candidate_in_window_order_and_the_rest_are_not_taken() -> None:
    source = Source({"xri_2": [case(n) for n in range(1, 6)], "xri_1": [case(n) for n in range(11, 14)]})
    answer, journal, *_ = run(source=source)
    # the descriptor's order (the critic's window order) is the order of the items, not the order the source answered in
    assert [(item["input_id"], len(item["cases"])) for item in answer.items] == [("xri_1", 3), ("xri_2", 3)]
    assert answer.not_fitted == 0, "the cases beyond three are by design never sent and are not «не уместилось»"


def test_what_does_not_fit_twelve_thousand_characters_is_counted_and_never_cut() -> None:
    # every case is about 270 characters of JSON, so not all sixty fit under 12 000 less the line: the first that does not ends the selection
    source = Source({f"xri_{n}": [case(n * 10 + m, size=90) for m in range(3)] for n in range(1, 21)})
    ids = tuple(f"xri_{n}" for n in range(1, 21))
    answer, journal, tasks, _ = run(source=source, pay=payload(ids=ids))
    delivered = [chosen for item in answer.items for chosen in item["cases"]]
    assert 0 < len(delivered) < 60 and answer.not_fitted == 60 - len(delivered) > 0
    assert sum(len(json.dumps(chosen, ensure_ascii=False, sort_keys=True, separators=(",", ":"))) for chosen in delivered) <= 12_000
    assert all(len(chosen["finding_text"]) == 90 for chosen in delivered), "a case is taken whole or not at all"
    # a strict prefix: the delivered cases are the first ones in window order
    expected = [f"dmc_{n * 10 + m:026d}" for n in range(1, 21) for m in range(3)][: len(delivered)]
    assert [chosen["case_id"] for chosen in delivered] == expected
    assert journal.rows[(TASK, "similar_cases")].case_ids == tuple(expected) and tasks.remembered[(TASK, "similar_cases")]["not_fitted"] == answer.not_fitted


def test_the_journal_never_names_more_than_its_sixty_four_cases_the_surplus_is_not_fitted() -> None:
    ids = tuple(f"xri_{n}" for n in range(1, 41))
    source = Source({identity: [case(index * 10 + m, size=1) for m in range(3)] for index, identity in enumerate(ids, start=1)})
    answer, journal, *_ = run(source=source, pay=payload(ids=ids))
    kept = journal.rows[(TASK, "similar_cases")].case_ids
    assert len(kept) == 64 and sum(len(item["cases"]) for item in answer.items) == 64 and answer.not_fitted == 120 - 64


def test_a_search_that_found_nothing_is_unavailable_with_its_own_reason_never_an_empty_block() -> None:
    answer, journal, tasks, _ = run(source=Source({}))
    assert (answer.status, answer.reason, answer.items) == ("unavailable", "no_similar_cases", ())
    assert journal.rows[(TASK, "similar_cases")].status == "unavailable" and tasks.remembered == {}
    other, *_ = run(source=Source({"xri_1": []}))
    assert other.reason == "no_similar_cases"


def test_a_case_the_source_gave_for_an_input_the_task_never_named_is_never_delivered() -> None:
    source = Source({"xri_stranger": [case(1)], "xri_1": [case(2)]})
    answer, *_ = run(source=source)
    assert [item["input_id"] for item in answer.items] == ["xri_1"]


def test_the_answers_digest_is_the_digest_of_its_items_as_delivered() -> None:
    import hashlib

    answer, *_ = run(source=delivering())
    canonical = json.dumps(list(answer.items), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert answer.context_sha256 == hashlib.sha256(canonical.encode()).hexdigest()
    assert answer.wire()["context_sha256"] == answer.context_sha256 and answer.status == "available"


def test_the_answer_is_the_contracts_shape() -> None:
    from auditmanager.api.schemas import models

    delivered, *_ = run(source=delivering())
    models.ExecutorTaskContext.model_validate(delivered.wire())
    unavailable, *_ = run(kind="patterns", source=UntilMoveSource())
    shaped = models.ExecutorTaskContext.model_validate(unavailable.wire()).model_dump(mode="json", exclude_unset=True)
    assert shaped == {"kind": "patterns", "status": "unavailable", "reason": "patterns_not_available", "items": [], "not_fitted": 0}


def test_the_same_case_found_for_two_candidates_keeps_its_own_similarity_for_each() -> None:
    source = Source({"xri_1": [replace(case(1), similarity=0.95)], "xri_2": [replace(case(1), similarity=0.8)]})
    answer, journal, *_ = run(source=source)
    assert {item["input_id"]: item["cases"][0]["similarity"] for item in answer.items} == {"xri_1": 0.95, "xri_2": 0.8}
    assert journal.rows[(TASK, "similar_cases")].case_ids == (case(1).case_id, case(1).case_id), "named once for each candidate it was shown for"
