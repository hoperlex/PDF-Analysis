"""Reference data for a `review:main` task: the consent's policy, the claim's descriptor and the answer of ``getExecutorTaskContext``
(`CTX-STAND`, ``ADR-0029`` decision 3, plan-v5 sections 3.2 and 3.5).

**The idea.** The critic's prompt stays static; the agent brings the data. A task of the cell ``review:main`` of a run on the stage layout that
asks for plan v3 carries ``context_request`` -- one entry per candidate text it was given, ``{input_id, text_sha256, section}`` -- and the agent
may ask the stand once per kind (``similar_cases``, ``patterns``) for the decisions of experts on findings like those. The stand answers by
``input_id`` and writes what it gave to ``executor_task_context_delivery`` (KEEP, no text).

**The switch and the consent.** ``executor_context_policy`` is placed in the consent only while the «контекст критику» switch
(``precedent_setting_event``, name ``critic_context``) is on, and only for a run on the stage layout; a run without the switch, a legacy run
and a v2 run therefore carry nothing new and behave as before. The policy is built like ``norm_paragraph_context_policy``
(``runs/norm_context.py``): a version, the digest of the code that serves it, the kinds, the scope, the method and the budget. The stand serves a
task only when the consent holds **the same** policy as the one it would write now (:func:`policy_in_force`): a consent frozen under another
digest is not served, and the agent calls the model without the data.

**The refusals (404).** The task is not a model call of a run; the run has no stage plan or asks for no v3 review; the cell is not
``review:main``; the task carries no ``context_request``; the consent lacks the same policy. A comparison task is a task that is not a model call
of a run. A task is not told apart from one that does not exist.

**Idempotent by (task, kind).** The first request writes the journal row and, for a delivered block, remembers the answer in the task's own
payload (a PRODUCT row that is cleared with the task and erased with the project: the journal holds no text, so it cannot return the block). A
repeat finds the row and returns the same answer; nothing is asked of the source and no budget is spent. Two kinds make the two requests of the
policy; there is no third.

**While temporary decision 2 stands** (``ADR-0029``: the encoder runs only at night, on our own server) the stand has no vectors to answer with:
:class:`UntilMoveSource` is the source and the answer is ``status: unavailable, reason: until_move``, journalled as ``unavailable``. A later lane
hands :func:`~auditmanager.executors.runner.get_task_context` a source that searches; the budget rule (:func:`select_within_budget`: window order,
at most three cases per candidate, 12 000 characters, then «не уместилось: N») is applied here, to whatever a source returns.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import logging
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Protocol

from sqlalchemy.orm import Session

from auditmanager.executors.runner_repository import RunnerRepository, TaskRecord
from auditmanager.executors.task_context_repository import ContextDeliveryRepository
from auditmanager.precedents.public import (
    MAX_CASES_PER_ENTRY,
    MAX_CHARACTERS,
    VECTOR_PROFILE,
    BudgetCase,
    BudgetEntry,
    latest_setting_value,
    select_within_budget,
)
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "CELL_REVIEW",
    "CRITIC_CONTEXT_SETTING",
    "KINDS",
    "MAX_INPUTS",
    "POLICY_VERSION",
    "REASON_NO_CASES",
    "REASON_PATTERNS_NOT_BUILT",
    "REASON_UNTIL_MOVE",
    "ContextInput",
    "ContextSource",
    "RunContextFacts",
    "SourceCase",
    "TaskContextAnswer",
    "UNTIL_MOVE",
    "Unavailable",
    "UntilMoveSource",
    "candidate_words",
    "context_eligible",
    "context_request_of",
    "critic_context_enabled",
    "executor_context_policy",
    "policy_in_force",
    "read_descriptor",
    "read_run_context_facts",
    "serve_context",
]

_log = logging.getLogger(__name__)

#: The only cell whose tasks are offered reference data: the critic of the v3 review.
CELL_REVIEW: Final[str] = "review:main"
#: The name of the switch in ``precedent_setting_event.setting_name`` (``0064``); its value is ``{"enabled": bool}``.
CRITIC_CONTEXT_SETTING: Final[str] = "critic_context"
KINDS: Final[tuple[str, ...]] = ("similar_cases", "patterns")
POLICY_VERSION: Final[str] = "executor-reference-context-v1"
PLAN_V3: Final[str] = "extended-review-v3"
#: At most this many candidates in one descriptor (the contract's ``ClaimedExecutorTask.context_request`` bound).
MAX_INPUTS: Final[int] = 64
#: ``executor_task_context_delivery.case_ids`` holds at most this many identities (its CHECK).
MAX_JOURNALLED_CASES: Final[int] = 64
#: What the policy reserves in the estimate for the block of one critic call: 12 000 characters at about 2,5 characters a token is about 4 800.
INPUT_TOKENS_RESERVED_PER_CALL: Final[int] = 5_000
REASON_UNTIL_MOVE: Final[str] = "until_move"
REASON_PATTERNS_NOT_BUILT: Final[str] = "patterns_not_available"
REASON_NO_CASES: Final[str] = "no_similar_cases"

_SHA256: Final = re.compile(r"[0-9a-f]{64}\Z")
_SECTION: Final = re.compile(r"[A-Z0-9_]{1,8}\Z")


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# -- the policy ------------------------------------------------------------------------------------------------


def _bundle_sha256() -> str:
    """The digest of the code that serves the data: this module and the selection rule it applies. Another code is another policy, and a consent
    frozen under the old digest is not served (the agent calls the model without the data); that is the same bargain as the norms' policy."""
    selection_path = inspect.getsourcefile(select_within_budget)
    assert selection_path is not None
    return _sha256(_canonical({
        "application": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "selection": hashlib.sha256(Path(selection_path).read_bytes()).hexdigest()}))


def executor_context_policy() -> dict[str, Any]:
    """The policy a consent freezes while the switch is on (plan-v5 section 3.5), the one the stand serves now."""
    return {
        "version": POLICY_VERSION, "bundle_sha256": _bundle_sha256(), "kinds": list(KINDS),
        "scope": ["same_section", "installation_data_class", "any_project_with_quotes", "not_this_run", "not_withdrawn_or_forgotten"],
        "methods": [VECTOR_PROFILE], "max_requests_per_task": len(KINDS), "max_characters_per_task": MAX_CHARACTERS,
        "selection": {"order": "window", "max_cases_per_candidate": MAX_CASES_PER_ENTRY, "remainder": "not_fitted_count"},
        "input_tokens_reserved_per_call": INPUT_TOKENS_RESERVED_PER_CALL,
    }


def policy_in_force(value: object) -> bool:
    """Is ``value`` exactly the policy the stand would write now? ``None`` and anything else is not."""
    return isinstance(value, Mapping) and dict(value) == executor_context_policy()


def critic_context_enabled(session: Session) -> bool:
    """Is the «контекст критику» switch on right now? Nothing journalled, or a flag that is not exactly ``true``, is off."""
    value = latest_setting_value(session, CRITIC_CONTEXT_SETTING)
    return value is not None and value.get("enabled") is True


# -- what a run says about its consent ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RunContextFacts:
    """What the stand needs to know of a run to serve its tasks: whether it is on the stage layout, the plan its consent asks for, the section
    the consent froze and the consent's own ``executor_context_policy`` (``None`` when it holds none or cannot be read)."""

    stage_plan: bool
    plan_version: str | None
    section: str | None
    policy: Mapping[str, Any] | None


NO_FACTS: Final[RunContextFacts] = RunContextFacts(False, None, None, None)


def read_run_context_facts(session: Session, run_id: str) -> RunContextFacts:
    """The facts of a run, from its accepted consent (``runs.public.read_run_cost_policy``, the reader the worker uses). A consent that cannot be
    read states nothing, so it grants nothing: the run reads as one that holds no policy, and the reason is logged without any content."""
    from auditmanager.runs.public import read_run_cost_policy

    try:
        cost = read_run_cost_policy(session, run_id=run_id, default_ceiling_usd=1.0)
    except DomainError as failure:
        _log.warning("executor context: the consent of run=%s cannot be read (%s)", run_id, failure.code.value)
        return NO_FACTS
    extended = cost.extended_review if isinstance(cost.extended_review, Mapping) else {}
    policy = extended.get("executor_context_policy")
    section = extended.get("section_code")
    return RunContextFacts(
        stage_plan=cost.stage_plan_digest is not None, plan_version=extended.get("plan_version"),
        section=section if isinstance(section, str) else None, policy=policy if isinstance(policy, Mapping) else None)


def context_eligible(facts: RunContextFacts) -> bool:
    """May the tasks of this run be offered reference data: on the stage layout, plan v3, a valid section and the same policy in the consent."""
    return (facts.stage_plan and facts.plan_version == PLAN_V3 and facts.section is not None
            and _SECTION.fullmatch(facts.section) is not None and policy_in_force(facts.policy))


# -- the descriptor ------------------------------------------------------------------------------------------------


def candidate_words(title: object, description: object) -> str | None:
    """The finding text of a candidate: its title over its description. The same rule the publisher states
    (``runs/extended_review._candidate_words``), so the digest names the words the finding will carry."""
    title = title.strip() if isinstance(title, str) else ""
    description = description.strip() if isinstance(description, str) else ""
    words = description if not title or description.startswith(title) else (f"{title}\n\n{description}" if description else title)
    return words or None


def context_request_of(user_text: str, *, section: str) -> list[dict[str, str]] | None:
    """The descriptor of a critic task, from the request it was written for: one ``{input_id, text_sha256, section}`` per observation, in the
    request's order (the critic's window order). ``text_sha256`` is the SHA-256 of :func:`candidate_words`.

    ``None`` when the request is not a critic's (no observations) or when one of its inputs cannot be named in the contract's shape (an identity
    of more than 128 characters, no words, a repeated identity, more than :data:`MAX_INPUTS`): a task is then offered nothing, never a part."""
    try:
        document = json.loads(user_text)
    except ValueError:
        return None
    observations = document.get("observations") if isinstance(document, dict) else None
    if not isinstance(observations, list) or not 1 <= len(observations) <= MAX_INPUTS:
        return None
    entries: list[dict[str, str]] = []
    for item in observations:
        identity = item.get("input_id") if isinstance(item, dict) else None
        words = candidate_words(item.get("title"), item.get("description")) if isinstance(item, dict) else None
        if not isinstance(identity, str) or not 1 <= len(identity) <= 128 or words is None:
            return None
        entries.append({"input_id": identity, "text_sha256": _sha256(words), "section": section})
    if len({entry["input_id"] for entry in entries}) != len(entries):
        return None
    return entries


@dataclass(frozen=True, slots=True)
class ContextInput:
    input_id: str
    text_sha256: str
    section: str


def read_descriptor(payload: Mapping[str, Any] | None) -> tuple[ContextInput, ...]:
    """The task's ``context_request`` as the stand wrote it; ``()`` when there is none or it is not exactly the contract's shape."""
    raw = None if payload is None else payload.get("context_request")
    if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_INPUTS:
        return ()
    entries: list[ContextInput] = []
    for item in raw:
        if (not isinstance(item, Mapping) or set(item) != {"input_id", "text_sha256", "section"}
                or not isinstance(item["input_id"], str) or not 1 <= len(item["input_id"]) <= 128
                or not isinstance(item["text_sha256"], str) or _SHA256.fullmatch(item["text_sha256"]) is None
                or not isinstance(item["section"], str) or not 1 <= len(item["section"]) <= 64):
            return ()
        entries.append(ContextInput(item["input_id"], item["text_sha256"], item["section"]))
    return tuple(entries)


# -- the source ------------------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SourceCase:
    """One earlier decision, as ``ExecutorTaskContextCase`` carries it. The source ranks them, best first."""

    case_id: str
    verdict: str
    category: str
    similarity: float
    finding_text: str
    recommendation_text: str
    comment: str | None = None

    def wire(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "case_id": self.case_id, "verdict": self.verdict, "category": self.category, "similarity": self.similarity,
            "finding_text": self.finding_text, "recommendation_text": self.recommendation_text}
        if self.comment is not None:
            value["comment"] = self.comment
        return value


@dataclass(frozen=True, slots=True)
class Unavailable:
    """The source has nothing to give, and says why (a stable code: ``^[a-z][a-z0-9_]{0,63}$``)."""

    reason: str


class ContextSource(Protocol):
    """What answers a request: the cases found for each input, ranked best first, or why there are none.

    The cases are those of the same section and data class, of any project, never of the task's run, never withdrawn or forgotten (the policy's
    scope). The source never decides the budget; :func:`serve_context` does."""

    def read(
        self, session: Session, *, run_id: str, kind: str, inputs: Sequence[ContextInput],
    ) -> Mapping[str, Sequence[SourceCase]] | Unavailable: ...


class UntilMoveSource:
    """The source while temporary decision 2 stands (``ADR-0029``): no vectors can be searched by day, so nothing is given and the stand says so.
    ``patterns`` are the programme's fifth wave and have no source at all yet."""

    def read(
        self, session: Session, *, run_id: str, kind: str, inputs: Sequence[ContextInput],
    ) -> Mapping[str, Sequence[SourceCase]] | Unavailable:
        return Unavailable(REASON_UNTIL_MOVE if kind == "similar_cases" else REASON_PATTERNS_NOT_BUILT)


UNTIL_MOVE: Final[UntilMoveSource] = UntilMoveSource()


# -- the answer ------------------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TaskContextAnswer:
    """``ExecutorTaskContext``: ``reason`` exactly when ``unavailable``, ``context_sha256`` exactly when ``available``."""

    kind: str
    status: str
    reason: str | None
    items: tuple[Mapping[str, Any], ...]
    not_fitted: int
    context_sha256: str | None

    def wire(self) -> dict[str, Any]:
        value: dict[str, Any] = {"kind": self.kind, "status": self.status}
        if self.reason is not None:
            value["reason"] = self.reason
        value["items"] = [dict(item) for item in self.items]
        value["not_fitted"] = self.not_fitted
        if self.context_sha256 is not None:
            value["context_sha256"] = self.context_sha256
        return value


def _unavailable(kind: str, reason: str) -> TaskContextAnswer:
    return TaskContextAnswer(kind, "unavailable", reason, (), 0, None)


def _delivered(kind: str, items: Sequence[Mapping[str, Any]], not_fitted: int) -> TaskContextAnswer:
    return TaskContextAnswer(kind, "available", None, tuple(items), not_fitted, _sha256(_canonical(list(items))))


def not_served() -> DomainError:
    """The one answer to every task that may not be given reference data (it is not told apart from a task that does not exist)."""
    return DomainError(ErrorCode.NOT_FOUND, aggregate_type="ExecutorTask")


def _fit(inputs: Sequence[ContextInput], found: Mapping[str, Sequence[SourceCase]]) -> tuple[list[dict[str, Any]], list[str], int, int]:
    """The budget rule over what the source found: ``(items, case ids, characters, not fitted)``. Candidates are taken in the descriptor's (window)
    order, at most three cases each, within 12 000 characters; the cases that did not fit are counted, never cut. At most
    :data:`MAX_JOURNALLED_CASES` cases are delivered (the journal's bound): the surplus is counted as not fitted too."""
    # The same earlier case may be found for two candidates, with a similarity of its own to each: a case is named within its candidate.
    wires = {item.input_id: [case.wire() for case in found.get(item.input_id, ())] for item in inputs}
    entries = [BudgetEntry(item.input_id, tuple(BudgetCase(wire["case_id"], _canonical(wire)) for wire in wires[item.input_id]))
               for item in inputs]
    selection = select_within_budget(entries)
    items: list[dict[str, Any]] = []
    ids: list[str] = []
    not_fitted = selection.not_fitted
    for entry in selection.entries:
        kept = []
        for position, chosen in enumerate(entry.cases):
            if len(ids) >= MAX_JOURNALLED_CASES:
                not_fitted += 1
                continue
            ids.append(chosen.case_id)
            kept.append(wires[entry.input_id][position])  # the selection is a prefix of the candidate's ranked cases
        if kept:
            items.append({"input_id": entry.input_id, "cases": kept})
    characters = sum(len(_canonical(case)) for item in items for case in item["cases"])
    return items, ids, characters, not_fitted


def serve_context(
    session: Session, *, task: TaskRecord, payload: Mapping[str, Any] | None, kind: str, source: ContextSource,
    tasks: RunnerRepository, deliveries: ContextDeliveryRepository,
    facts: Callable[[Session, str], RunContextFacts] = read_run_context_facts,
) -> TaskContextAnswer:
    """Answer ``getExecutorTaskContext`` for a task the caller has already shown to be this runner's live claim.

    Refuses with :func:`not_served` (404) unless the task is a model call of a run, of the cell ``review:main``, carries a ``context_request``,
    and its run is on the stage layout under plan v3 with the same ``executor_context_policy`` in its consent. Then, idempotently by (task, kind):
    a journalled answer is returned as it was; otherwise the source is asked once, the budget is applied, the journal row is written and the
    answer is returned. The caller's transaction holds the task row (``FOR UPDATE``), so two requests of one task are one after the other."""
    if kind not in KINDS:
        raise DomainError(ErrorCode.VALIDATION_FAILED, message="the kind of reference data is not served", field="kind", constraint="kind")
    host = None if payload is None else payload.get("host")
    inputs = read_descriptor(payload)
    if (task.origin != "run_call" or task.run_id is None or not isinstance(host, Mapping) or host.get("cell_key") != CELL_REVIEW
            or not inputs):
        raise not_served()
    if not context_eligible(facts(session, task.run_id)):
        raise not_served()
    assert payload is not None
    journalled = deliveries.get(session, task.task_id, kind)
    if journalled is not None:
        if journalled.status == "unavailable":
            assert journalled.reason is not None
            return _unavailable(kind, journalled.reason)
        remembered = (payload.get("context_answers") or {}).get(kind)
        if not isinstance(remembered, Mapping):
            raise DomainError(ErrorCode.INTERNAL_ERROR, message="a delivered block is journalled and not remembered")
        return TaskContextAnswer(
            kind, "available", None, tuple(remembered["items"]), int(remembered["not_fitted"]), journalled.block_sha256)
    found = source.read(session, run_id=task.run_id, kind=kind, inputs=inputs)
    if isinstance(found, Unavailable):
        answer = _unavailable(kind, found.reason)
        deliveries.insert(
            session, task_id=task.task_id, run_id=task.run_id, model_call_id=task.model_call_id, kind=kind, status="unavailable",
            reason=found.reason, case_ids=(), characters=0, block_sha256=None)
        return answer
    items, ids, characters, not_fitted = _fit(inputs, found)
    if not items:
        answer = _unavailable(kind, REASON_NO_CASES)
        deliveries.insert(
            session, task_id=task.task_id, run_id=task.run_id, model_call_id=task.model_call_id, kind=kind, status="unavailable",
            reason=REASON_NO_CASES, case_ids=(), characters=0, block_sha256=None)
        return answer
    answer = _delivered(kind, items, not_fitted)
    deliveries.insert(
        session, task_id=task.task_id, run_id=task.run_id, model_call_id=task.model_call_id, kind=kind, status="delivered", reason=None,
        case_ids=ids, characters=characters, block_sha256=answer.context_sha256)
    tasks.remember_context_answer(session, task_id=task.task_id, kind=kind, answer={"items": list(answer.items), "not_fitted": not_fitted})
    return answer
