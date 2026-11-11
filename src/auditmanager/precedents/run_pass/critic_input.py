"""The critic's records of a run, read into the inputs of the core (`ADR-0029` decisions 5 and 14, plan-v5 2.4, V3).

Pure: a saved extended-review document in, plain values out. The core takes «critic in plan» and «reviewed» as inputs and never looks at a plan; this
module is the mapping the core's own notes leave to the pass.

**Two critics, one rule for «reviewed», two rules for the veto.**

* Plan **v3** (``workflow_version`` ``extended-review-v3``) has the AI critic. A candidate it reviewed carries ``critic`` (with ``llm_decision``) and
  ``review_status: reviewed``; one it did not reach (outside the window of 40 records and 16 000 characters, or its call was refused) carries
  ``review_status: not_reviewed`` and no ``critic``. Its ``llm_decision`` is the decision the core reads: ``accept`` and ``needs_human`` are the veto
  (owner ruling Р4, «вето ИИ»). A record whose decision this module does not know is read as ``needs_human``: an advice it cannot read cannot be shown
  as «no objection».
* Plan **v2** with the marker ``original_review: deterministic-v1`` has the original's deterministic critic (`V2-ORIGINAL-REVIEW-01`): no model, rows
  marked ``mode: deterministic`` and ``model_called: false``. It **counts as a review** for V3 (a finding it reviewed may get «снять», subject to every other
  rule) but it **never vetoes** (the integrator's ruling): its verdicts are mapped onto accept / needs_human / rewrite for the expert's eyes, and none of
  them is an objection to a precedent. Here its record is :data:`DECISION_DETERMINISTIC`, which is not in the core's veto set.
* A run with neither (a v2 run without the marker, a legacy run, an artifact that is missing, failed or not an object) has **no critic in plan**: no
  finding of it is reviewed, in v2 or in v3.

**Linking.** A candidate-finding of a ``one_list`` run is linked through the ``extended_observation_ref`` of its observations. A text finding is linked
to the candidates that restate it: a candidate with a primary-text source (``primary_text_<key>`` in v3, ``text:<index>`` in v2) whose restated words
are the finding's. The finding's observation row keeps no ordinal of the text observation it came from (the number is a position in an artifact, not an
identity), so the link is by the words the candidate copied from it: v3 keeps the whole original observation on the candidate
(``original_primary_observation``), v2 copies the category into ``title`` and the text, cut at 3 000 characters, into ``description``
(`analysis/extended/core.py:145-160`). Every candidate that restates the finding is linked, so a veto on any of them counts.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

from auditmanager.precedents.models import (
    CRITIC_ACCEPT,
    CRITIC_NEEDS_HUMAN,
    CRITIC_REJECT,
    CriticCandidate,
)

__all__ = [
    "CandidateRow", "CriticPlan", "DECISION_DETERMINISTIC", "LINK_TOKEN_PREFIX", "NO_CRITIC", "NormRow", "WORKFLOW_V2", "WORKFLOW_V3",
    "candidates_from_projection", "critic_projection", "link", "link_token", "possible_norms", "read_critic_plan",
]

WORKFLOW_V2: Final[str] = "extended-review-v2"
WORKFLOW_V3: Final[str] = "extended-review-v3"
#: ``analysis.extended.original_deterministic.ORIGINAL_REVIEW_V2``, restated: the precedents context does not import the analysis context for a word.
_ORIGINAL_REVIEW_V2: Final[str] = "deterministic-v1"

#: A candidate the deterministic critic reviewed. It is **not** a verdict the core knows, so it is never a veto and never makes the critic «diverge».
DECISION_DETERMINISTIC: Final[str] = "deterministic"
_AI_DECISIONS: Final[frozenset[str]] = frozenset({CRITIC_ACCEPT, CRITIC_REJECT, "borderline", CRITIC_NEEDS_HUMAN, "rewrite"})
#: What an AI record whose decision is missing or not in the vocabulary is read as: an objection, not silence.
_UNREADABLE_AI_DECISION: Final[str] = CRITIC_NEEDS_HUMAN

#: A candidate's source that restates a text finding (`runs/extended_review.py`, ``_PRIMARY_TEXT_SOURCE_ID``): v3 ``primary_text_<key>``, v2 ``text:<index>``.
_PRIMARY_TEXT_SOURCE: Final[re.Pattern[str]] = re.compile(r"primary_text_[0-9a-f]+|text:[0-9]+")
_NORM_DOCUMENT_ID: Final[re.Pattern[str]] = re.compile(r"ndoc_[0-9A-HJKMNP-TV-Z]{26}")
_NORM_PARAGRAPH_ID: Final[re.Pattern[str]] = re.compile(r"npar_[0-9A-HJKMNP-TV-Z]{26}")
#: The cut ``analysis/extended/core.py`` makes of a text observation's words when it copies them to a v2 candidate.
_V2_TITLE_CHARS: Final[int] = 200
_V2_DESCRIPTION_CHARS: Final[int] = 3000
#: ``PossibleNorm`` has room for five; ``decision_memory_precedent_advice.votes`` has room for this many linked records (``ck``: 2048 octets).
MAX_POSSIBLE_NORMS: Final[int] = 5
_MAX_PROJECTED_RECORDS: Final[int] = 8

#: The synthetic source every candidate linked to a finding carries in the finding's own view, so the core's rule (a source or a reference that matches) holds.
LINK_TOKEN_PREFIX: Final[str] = "link:"


def link_token(finding_uid: str) -> str:
    """The one id the core is asked to match for ``finding_uid``: every linked candidate is handed to it carrying this source."""
    return LINK_TOKEN_PREFIX + finding_uid


@dataclass(frozen=True, slots=True)
class NormRow:
    """A paragraph of the norms a candidate stands on (``norm_candidates``), as the card's «Возможные нормы» show it."""

    norm_document_id: str
    norm_paragraph_id: str
    designation: str
    clause_number: str | None
    page_label: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "norm_document_id": self.norm_document_id, "norm_paragraph_id": self.norm_paragraph_id, "designation": self.designation,
            "clause_number": self.clause_number, "page_label": self.page_label,
        }


@dataclass(frozen=True, slots=True)
class CandidateRow:
    """One saved candidate with what the pass reads from it. ``decision`` is ``None`` when no critic record exists for it."""

    candidate_id: str
    source_ids: tuple[str, ...]
    decision: str | None
    context_kinds: frozenset[str]
    #: The words a text finding is matched on, when this candidate restates a primary text: ``(category, text)``; ``None`` for any other candidate.
    restates: tuple[str, str] | None
    norms: tuple[NormRow, ...]


@dataclass(frozen=True, slots=True)
class CriticPlan:
    """What a run's plan did about critics: whether one was in it, and its candidates."""

    in_plan: bool
    kind: str
    candidates: tuple[CandidateRow, ...]


NO_CRITIC: Final[CriticPlan] = CriticPlan(in_plan=False, kind="none", candidates=())


def _strings(value: object) -> tuple[str, ...]:
    return tuple(item for item in value if isinstance(item, str)) if isinstance(value, list) else ()


def _is_deterministic(critic: Mapping[str, Any]) -> bool:
    return critic.get("mode") == "deterministic" or critic.get("model_called") is False


def _decision_of(item: Mapping[str, Any], *, deterministic_plan: bool) -> str | None:
    """The record's decision as the core reads it, or ``None`` when the candidate has no critic record."""
    critic = item.get("critic")
    if item.get("review_status") != "reviewed" or not isinstance(critic, Mapping):
        return None
    if deterministic_plan or _is_deterministic(critic):
        return DECISION_DETERMINISTIC
    decision = critic.get("llm_decision")
    return decision if isinstance(decision, str) and decision in _AI_DECISIONS else _UNREADABLE_AI_DECISION


def _restates(item: Mapping[str, Any], source_ids: Sequence[str]) -> tuple[str, str] | None:
    if not any(_PRIMARY_TEXT_SOURCE.fullmatch(source) for source in source_ids):
        return None
    original = item.get("original_primary_observation")
    if isinstance(original, Mapping):
        category, words = original.get("category"), original.get("finding_text")
        return (category, words) if isinstance(category, str) and isinstance(words, str) else None
    title, description = item.get("title"), item.get("description")
    return (title, description) if isinstance(title, str) and isinstance(description, str) else None


def _norms(item: Mapping[str, Any]) -> tuple[NormRow, ...]:
    rows: list[NormRow] = []
    candidates = item.get("norm_candidates")
    for entry in candidates if isinstance(candidates, list) else []:
        if not isinstance(entry, Mapping):
            continue
        document, paragraph = entry.get("document_id"), entry.get("paragraph_id")
        designation, clause, page = entry.get("designation"), entry.get("clause_number"), entry.get("page_label")
        if not (isinstance(document, str) and _NORM_DOCUMENT_ID.fullmatch(document) and isinstance(paragraph, str)
                and _NORM_PARAGRAPH_ID.fullmatch(paragraph) and isinstance(designation, str) and 1 <= len(designation) <= 500
                and type(page) is int and page >= 1):
            continue
        rows.append(NormRow(document, paragraph, designation, clause if isinstance(clause, str) and 1 <= len(clause) <= 100 else None, page))
    return tuple(rows)


def read_critic_plan(document: Mapping[str, Any] | None) -> CriticPlan:
    """The critic of a run from ``runs.public.read_extended_review``'s answer (``{"status", "result"}``), or :data:`NO_CRITIC`.

    ``None``, a document that is not an object, one without a result and a workflow that is neither v2 nor v3 read as :data:`NO_CRITIC`. A v2 result
    without the marker keeps its candidates but has no critic in plan (``in_plan`` false: nothing is reviewed)."""
    result = document.get("result") if isinstance(document, Mapping) else None
    if not isinstance(result, Mapping):
        return NO_CRITIC
    workflow = result.get("workflow_version")
    if workflow == WORKFLOW_V3:
        in_plan, deterministic, kind = True, False, "ai"
    elif workflow == WORKFLOW_V2:
        original = result.get("original_review")
        in_plan = isinstance(original, Mapping) and original.get("version") == _ORIGINAL_REVIEW_V2
        deterministic, kind = True, "deterministic" if in_plan else "none"
    else:
        return NO_CRITIC
    rows: list[CandidateRow] = []
    items = result.get("observations")
    for item in items if isinstance(items, list) else []:
        identity = item.get("observation_id") if isinstance(item, Mapping) else None
        if not isinstance(item, Mapping) or not isinstance(identity, str) or not identity:
            continue
        sources = _strings(item.get("source_ids"))
        # A run whose plan has no critic keeps its candidates (the card's «Возможные нормы» come from them) and none of them is reviewed.
        decision = _decision_of(item, deterministic_plan=deterministic) if in_plan else None
        rows.append(CandidateRow(
            candidate_id=identity, source_ids=sources, decision=decision,
            context_kinds=frozenset(_strings(item.get("context_kinds"))) if decision is not None else frozenset(),
            restates=_restates(item, sources), norms=_norms(item)))
    return CriticPlan(in_plan=in_plan, kind=kind, candidates=tuple(rows))


def link(
    plan: CriticPlan, *, extended_observation_refs: Iterable[str], category: str, finding_text: str,
) -> tuple[CandidateRow, ...]:
    """The candidates a finding stands on, in the saved order: those its observations name (``extended_observation_ref``), and those that restate it.

    A candidate-finding names its candidates; a text finding has none to name, and is matched by words (the module's note says why): the category and
    the text, whole for v3 (the original observation is kept on the candidate) and as the cut v2 makes for a ``text:<index>`` source."""
    refs = {ref for ref in extended_observation_refs if ref}
    linked: list[CandidateRow] = []
    for row in plan.candidates:
        if row.candidate_id in refs:
            linked.append(row)
        elif row.restates is not None and _restated_by(row.restates, category, finding_text):
            linked.append(row)
    return tuple(linked)


def _restated_by(restates: tuple[str, str], category: str, finding_text: str) -> bool:
    words_category, words = restates
    return words_category == category and words == finding_text or (
        words_category[:_V2_TITLE_CHARS] == category[:_V2_TITLE_CHARS] and words == finding_text[:_V2_DESCRIPTION_CHARS])


def possible_norms(linked: Sequence[CandidateRow]) -> tuple[NormRow, ...]:
    """The paragraphs the linked candidates stand on, in order, each once, at most five (`PossibleNorm`): the very paragraphs the critic gets."""
    seen: set[str] = set()
    found: list[NormRow] = []
    for row in linked:
        for norm in row.norms:
            if norm.norm_paragraph_id not in seen:
                seen.add(norm.norm_paragraph_id)
                found.append(norm)
    return tuple(found[:MAX_POSSIBLE_NORMS])


# -- the stored projection: what the advice row keeps of the critic, so a read-time evaluation needs no artifact --------------------------------


def critic_projection(plan: CriticPlan, linked: Sequence[CandidateRow]) -> dict[str, Any]:
    """The part of the critic's work the core needs for one finding, small enough for a row: ``{"in_plan", "linked", "records": [{"d", "k"}, ...]}``.

    ``linked`` counts every linked candidate (the hint P4 asks for exactly one); ``records`` are the critic's records among them, the decisions
    that can veto first so the cap on the list never drops an objection. The pass stores it with the counts of the votes; a read that must evaluate
    again (a case withdrawn since) builds the core's inputs from it with :func:`candidates_from_projection`."""
    records = [row for row in linked if row.decision is not None]
    records.sort(key=lambda row: (row.decision not in (CRITIC_ACCEPT, CRITIC_NEEDS_HUMAN), row.candidate_id))
    return {
        "in_plan": plan.in_plan,
        "linked": len(linked),
        "records": [{"d": row.decision, "k": sorted(row.context_kinds)} for row in records[:_MAX_PROJECTED_RECORDS]],
    }


def candidates_from_projection(projection: Mapping[str, Any] | None, finding_uid: str) -> tuple[bool, tuple[CriticCandidate, ...]]:
    """``(critic_in_plan, candidates)`` for the core, from a stored projection; each carries the finding's link token as its source.

    A projection that is missing or not the shape means **no critic in plan** (nothing reviewed, so no «снять»): the safe reading, never an invented review."""
    if not isinstance(projection, Mapping) or projection.get("in_plan") is not True:
        return False, ()
    records = projection.get("records") if isinstance(projection.get("records"), list) else []
    linked = projection.get("linked")
    count = linked if type(linked) is int and linked >= len(records) else len(records)
    token = link_token(finding_uid)
    out: list[CriticCandidate] = []
    for index, record in enumerate(records):
        decision = record.get("d") if isinstance(record, Mapping) else None
        kinds = frozenset(_strings(record.get("k"))) if isinstance(record, Mapping) else frozenset()
        if isinstance(decision, str):
            out.append(CriticCandidate(candidate_id=f"{token}#{index}", source_ids=(token,), decision=decision, context_kinds=kinds))
    for index in range(len(out), count):
        out.append(CriticCandidate(candidate_id=f"{token}#{index}", source_ids=(token,), decision=None))
    return True, tuple(out)
