"""`NORM-STATUS-ORIGINAL-01`: when the norm stage is complete, read the way the original PDF-proverka reads it.

The stage is ``completed`` when every input of the norm verification reached a **terminal outcome without a technical failure**. What the
norm review found about a finding -- confirmed, not confirmed, no paragraph found, no norm named, quoted context incomplete -- is a label
on that finding (``finding_norm_status``, ``norm_review_reason``), never a reason for the whole stage to be ``partial``. The stage is
``partial`` only when the work itself did not finish:

* the corpus or its lookup was unavailable, the search window was exhausted, the semantic lookup failed (an ``unavailable`` lookup whose
  reason is not one of :data:`NO_NORM_NAMED_REASONS`);
* the norm model's reply for an input was refused (after its one repair) or never arrived: the input was sent and has no accepted record
  (``refused``);
* an input has no stored outcome at all (``pending``, ``technical`` key ``no_stored_outcome``).

Before this module the flow path counted two kinds of outcome as unresolved by construction (prod run ``run_01M7HH1MPV5W1FEZMX5ZK29PTA``,
section KJ: 25 of 43 inputs asked no determined norm question, 14 more were assessed on a paragraph context cut by the context budget):
the stage, the ``text_analysis`` row that carries it and the run were all ``partial`` although no model call failed.

The module is pure (no I/O, no clock, no model). It reads the fields the lookup and the review already write on each observation:
``norm_status`` / ``norm_reason`` (the lookup), ``norm_review_status`` (the review) and ``normative_context.complete`` (the quoted context).
It writes nothing and decides nothing about a finding.

``input_accounting`` keeps the five numbers the reader draws (``expected``, ``valid``, ``pending``, ``refused``, ``excluded``; their sum is
``expected``) and adds two breakdowns that never change that sum:

* ``outcomes`` -- how the terminal inputs split: ``reviewed`` and ``reviewed_context_incomplete`` and ``not_found`` are counted in ``valid``;
  ``not_applicable`` and ``no_norm_named`` are counted in ``excluded``;
* ``technical`` -- the reasons of ``pending``, each with its count (``refused`` has its own number).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Final

__all__ = [
    "EXCLUSION_REASON",
    "NORM_INPUTS_UNRESOLVED",
    "NORM_REPLY_REFUSED",
    "NO_NORM_NAMED_REASONS",
    "NO_STORED_OUTCOME",
    "NormStageAccounting",
    "account_norm_inputs",
    "classify_norm_input",
]

#: The reason of a norm stage in which a reply record was refused or an input got no accepted record.
NORM_REPLY_REFUSED: Final[str] = "norm_verification_reply_refused"
#: The reason of a norm stage with a technical gap that is not a refused reply (a lookup that failed, an input with no stored outcome).
NORM_INPUTS_UNRESOLVED: Final[str] = "norm_inputs_unresolved"
#: The ``technical`` key of an input that was sent (or had a lookup) and has no stored outcome.
NO_STORED_OUTCOME: Final[str] = "no_stored_outcome"
#: The reason of a completed stage whose every input is excluded (no determined normative question).
EXCLUSION_REASON: Final[str] = "no_normative_question"

#: The ``unavailable`` lookup reasons that are an outcome, not a failure: the observation named no determined norm, so nothing was searched.
#: ``normative_query_required`` is the flow plan's (``norm_queries.plan_flow_norm_queries``: a norm claim with no usable question);
#: ``query_not_proposed`` and ``no_normative_question`` are the older paths' (a primary text finding, a point with no query).
NO_NORM_NAMED_REASONS: Final[frozenset[str]] = frozenset({"normative_query_required", "query_not_proposed", "no_normative_question"})

#: The terminal outcomes, in the order ``outcomes`` lists them.
TERMINAL_OUTCOMES: Final[tuple[str, ...]] = (
    "reviewed", "reviewed_context_incomplete", "not_found", "no_norm_named", "not_applicable")
_VALID_OUTCOMES: Final = frozenset({"reviewed", "reviewed_context_incomplete", "not_found"})
_EXCLUDED_OUTCOMES: Final = frozenset({"no_norm_named", "not_applicable"})


def classify_norm_input(item: Mapping[str, Any]) -> tuple[str, str | None]:
    """The outcome of one observation: ``(outcome, technical_reason)``.

    ``outcome`` is one of :data:`TERMINAL_OUTCOMES`, ``refused`` (sent, no accepted record) or ``technical`` (a failure of the work, with
    its reason). Anything the function does not recognise is ``technical`` -- an unknown state is never read as done.
    """
    status = item.get("norm_status")
    if status == "not_applicable":
        return "not_applicable", None
    if status == "not_found":
        return "not_found", None
    if status == "unavailable":
        reason = item.get("norm_reason")
        if reason in NO_NORM_NAMED_REASONS:
            return "no_norm_named", None
        return "technical", reason if isinstance(reason, str) and reason else "unknown"
    if status == "candidates":
        review = item.get("norm_review_status")
        if review == "reviewed":
            context = item.get("normative_context")
            incomplete = isinstance(context, Mapping) and context.get("complete") is False
            return ("reviewed_context_incomplete" if incomplete else "reviewed"), None
        if review == "not_reviewed":
            return "refused", None
    return "technical", NO_STORED_OUTCOME


@dataclass(frozen=True, slots=True)
class NormStageAccounting:
    """The stage's ``input_accounting`` and the status and reason that follow from it."""

    accounting: dict[str, Any]
    status: str
    reason: str | None

    @property
    def technical_gap(self) -> bool:
        return self.accounting["pending"] > 0 or self.accounting["refused"] > 0


def account_norm_inputs(items: Iterable[Mapping[str, Any]]) -> NormStageAccounting:
    """Account every observation once and say whether the stage is complete (see the module docstring)."""
    tally: Counter[str] = Counter()
    technical: Counter[str] = Counter()
    expected = 0
    for item in items:
        expected += 1
        outcome, reason = classify_norm_input(item)
        tally[outcome] += 1
        if reason is not None:
            technical[reason] += 1
    accounting: dict[str, Any] = {
        "expected": expected,
        "valid": sum(tally[name] for name in _VALID_OUTCOMES),
        "pending": tally["technical"],
        "refused": tally["refused"],
        "excluded": sum(tally[name] for name in _EXCLUDED_OUTCOMES),
        "exclusion_reason": EXCLUSION_REASON,
        "outcomes": {name: tally[name] for name in TERMINAL_OUTCOMES},
        "technical": dict(sorted(technical.items())),
    }
    if tally["refused"]:
        return NormStageAccounting(accounting, "partial", NORM_REPLY_REFUSED)
    if tally["technical"]:
        return NormStageAccounting(accounting, "partial", NORM_INPUTS_UNRESOLVED)
    return NormStageAccounting(accounting, "completed", EXCLUSION_REASON if accounting["excluded"] == expected else None)
