"""The grounding gate — the difference between a finding and a plausible sentence.

An observation is published as a finding only when **every** one of its evidence items
resolves on all three checks of P02 §5.1:

1. the declared ``(char_start, char_end)`` interval lies inside the declared page's
   interval in ``prepared.text_layer``;
2. the document-global sequence sliced at that interval **equals the quote exactly**,
   after the one declared normalization of §4.1 and nothing else;
3. when ``block_id`` is present, the interval lies inside that block's own span in
   ``geometry.block_index``.

An item failing any check rejects the whole observation from the finding list. It is
retained only as a diagnostic, and the reason is one of exactly five values.

Why the gate is deterministic and takes no model input beyond the artifact: everything
downstream — expert usefulness rates, evidence-location correctness, the whole P04 field
study — is measured over what this gate admits. If it admits something ungrounded, those
measurements are noise and nothing reports it.

Three things this module deliberately does not do:

* **It does not normalize.** ``source_preparation`` applied the one declared
  normalization and named it in ``text_layer.normalization.id``. Comparing after a
  second normalization would let a quotation that is not in the document pass by being
  rewritten until it was. The comparison here is ``==`` on two ``str`` values.
* **It does not repair.** There is no nearest-match, no whitespace tolerance and no
  offset search. A near miss is a rejection with a reason, not a corrected anchor.
* **It does not touch the database.** The gate is a pure function over artifacts, so it
  is testable without a server and cannot be talked out of a verdict by a transaction.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final, Sequence

from auditmanager.findings.artifacts import (
    BlockIndex,
    EvidenceItem,
    Observation,
    ObservationSet,
    TextLayer,
)


class UngroundedReason(str, Enum):
    """The closed diagnostic vocabulary of P02 §5.1. Exactly five values."""

    QUOTATION_ABSENT = "quotation_absent"
    QUOTATION_ON_DIFFERENT_PAGE = "quotation_on_different_page"
    SPAN_OUTSIDE_PAGE = "span_outside_page"
    SPAN_OUTSIDE_BLOCK = "span_outside_block"
    SPAN_LENGTH_MISMATCH = "span_length_mismatch"


#: Restated as a frozen set so a caller can assert closure without importing the enum's
#: internals. The migration's own CHECK constraint is the enforcement; this is the
#: vocabulary the gate can produce.
UNGROUNDED_REASONS: Final[frozenset[str]] = frozenset(
    reason.value for reason in UngroundedReason
)


@dataclass(frozen=True, slots=True)
class EvidenceVerdict:
    """The gate's decision about one evidence item."""

    evidence_ordinal: int
    resolved: bool
    reason: UngroundedReason | None = None

    def __post_init__(self) -> None:
        # The same pairing the database enforces on the observation row, asserted here
        # so an inconsistent verdict cannot be constructed in the first place.
        if self.resolved != (self.reason is None):
            raise ValueError(
                "an evidence verdict is resolved exactly when it carries no reason"
            )


@dataclass(frozen=True, slots=True)
class ObservationVerdict:
    """The gate's decision about one observation, and why.

    ``grounded`` is true only when every evidence item resolved. ``reason`` is the
    reason of the first item that failed, in evidence order: a deterministic choice, so
    two runs over the same artifact record the same diagnostic.
    """

    observation: Observation
    evidence_verdicts: tuple[EvidenceVerdict, ...]

    @property
    def grounded(self) -> bool:
        return all(verdict.resolved for verdict in self.evidence_verdicts)

    @property
    def reason(self) -> UngroundedReason | None:
        for verdict in self.evidence_verdicts:
            if not verdict.resolved:
                return verdict.reason
        return None

    @property
    def failing_evidence_ordinal(self) -> int | None:
        for verdict in self.evidence_verdicts:
            if not verdict.resolved:
                return verdict.evidence_ordinal
        return None


@dataclass(frozen=True, slots=True)
class GateResult:
    """Every observation the gate judged, with the normalization it judged under."""

    verdicts: tuple[ObservationVerdict, ...]
    normalization_id: str

    @property
    def grounded(self) -> tuple[ObservationVerdict, ...]:
        return tuple(verdict for verdict in self.verdicts if verdict.grounded)

    @property
    def ungrounded(self) -> tuple[ObservationVerdict, ...]:
        return tuple(verdict for verdict in self.verdicts if not verdict.grounded)

    @property
    def grounded_count(self) -> int:
        return len(self.grounded)

    @property
    def ungrounded_count(self) -> int:
        return len(self.ungrounded)

    def reason_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for verdict in self.ungrounded:
            reason = verdict.reason
            assert reason is not None  # an ungrounded verdict always carries one
            counts[reason.value] = counts.get(reason.value, 0) + 1
        return counts


def check_evidence(
    item: EvidenceItem,
    text_layer: TextLayer,
    block_index: BlockIndex,
) -> EvidenceVerdict:
    """Resolve one evidence item against the text layer and the block index.

    The order of the checks is what makes each reason attributable. A length mismatch is
    decided first because it makes the slice comparison meaningless; the page check
    comes next because an anchor that does not address the page it claims cannot be
    judged against that page's text; the quotation comparison follows; and the block
    check runs last, on an anchor already known to resolve.
    """
    quote = item.quote
    declared_length = item.char_end - item.char_start

    # --- structural: could the declared interval hold this quote at all? -------------
    # len() counts code points. The corpus is Russian, so a byte-length implementation
    # would report a mismatch on nearly every genuine anchor.
    if declared_length != len(quote):
        return EvidenceVerdict(
            evidence_ordinal=item.evidence_ordinal,
            resolved=False,
            reason=UngroundedReason.SPAN_LENGTH_MISMATCH,
        )

    # --- check 1: the interval lies inside the declared page's interval --------------
    page = text_layer.page(item.page_number)
    if page is None or not page.contains(item.char_start, item.char_end):
        # Covers three real cases with one verdict: a page number the document does not
        # have, an interval on some other page, and an interval that starts on this page
        # and runs across the boundary into the next one.
        return EvidenceVerdict(
            evidence_ordinal=item.evidence_ordinal,
            resolved=False,
            reason=UngroundedReason.SPAN_OUTSIDE_PAGE,
        )

    # --- check 2: the sequence at that interval equals the quote exactly -------------
    # Exact equality, after the one declared normalization and nothing else. No strip(),
    # no casefold(), no whitespace collapsing, no second normalize() call.
    if text_layer.slice(item.char_start, item.char_end) != quote:
        # The quotation is not at its declared anchor. Which of the two diagnostics
        # applies is decided by where the quotation actually lives: if some *other*
        # page wholly contains it and the declared page does not, the model named the
        # wrong page; otherwise the quotation is absent from the anchor with no page
        # mix-up to explain it.
        pages_with_quote = text_layer.pages_containing(quote)
        if pages_with_quote and item.page_number not in pages_with_quote:
            return EvidenceVerdict(
                evidence_ordinal=item.evidence_ordinal,
                resolved=False,
                reason=UngroundedReason.QUOTATION_ON_DIFFERENT_PAGE,
            )
        return EvidenceVerdict(
            evidence_ordinal=item.evidence_ordinal,
            resolved=False,
            reason=UngroundedReason.QUOTATION_ABSENT,
        )

    # --- check 3: when block_id is present, the interval lies inside that block ------
    if item.block_id is not None:
        block = block_index.block(item.block_id)
        if block is None or not block.contains(item.char_start, item.char_end):
            # A block_id the index does not carry is treated as an unresolvable
            # secondary anchor, not as an absent one: the model declared a block and
            # the interval is not inside it. Failing open here would publish an anchor
            # whose declared geometry nobody checked.
            return EvidenceVerdict(
                evidence_ordinal=item.evidence_ordinal,
                resolved=False,
                reason=UngroundedReason.SPAN_OUTSIDE_BLOCK,
            )

    return EvidenceVerdict(evidence_ordinal=item.evidence_ordinal, resolved=True)


def check_observation(
    observation: Observation,
    text_layer: TextLayer,
    block_index: BlockIndex,
) -> ObservationVerdict:
    """Judge one observation. Every evidence item is checked, not just until the first
    failure: the per-item verdicts are the diagnostic record, and stopping early would
    throw away what the later items would have said."""
    return ObservationVerdict(
        observation=observation,
        evidence_verdicts=tuple(
            check_evidence(item, text_layer, block_index) for item in observation.evidence
        ),
    )


def run_grounding_gate(
    observations: ObservationSet | Sequence[Observation],
    text_layer: TextLayer,
    block_index: BlockIndex | None = None,
) -> GateResult:
    """Run the gate over an observation set. Pure: no I/O, no clock, no randomness.

    ``block_index`` may be omitted only when no evidence item declares a ``block_id``;
    an item that declares one against an empty index fails check 3, which is the
    fail-closed behaviour §5.1 requires.
    """
    index = block_index if block_index is not None else BlockIndex.empty()
    items = (
        observations.observations
        if isinstance(observations, ObservationSet)
        else tuple(observations)
    )
    return GateResult(
        verdicts=tuple(check_observation(item, text_layer, index) for item in items),
        normalization_id=text_layer.normalization_id,
    )
