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
retained only as a diagnostic. This v1 evidence gate emits five reasons; the closed
0023 vocabulary also covers recognised-text and later normative citation refusals.

**Gate v2: a block as evidence** (`F8-GATE`, ADR-0029 decision 7), for a run whose
``publication_mode`` is ``one_list`` only. A candidate grounded by blocks passes only when,
for every evidence item:

1. the item's ``blk_…`` (and page) is in **this run's** ``geometry.portal_blocks``
   (``block_not_in_run_geometry``);
2. the item's crop digest equals the SHA-256 of that block's crop in this run's
   ``geometry.page_crops`` (``block_crop_mismatch``);
3. a quote, when the item has one, occurs verbatim in the recognised text of that block in
   this run's ``prepared.recognised_text`` (``block_quote_not_in_recognised``).

**A block link proves a place, not a content.** The checks above establish that the model
looked at a block of this document and that the crop it was shown is the crop on record.
They do not establish that the block says what the candidate claims; that is the expert's
to judge. For that reason the text gate's refusal ``quote_in_recognised_text`` (a quote
found only in recognised text) does not apply to block evidence: a quote in the recognised
text of a block is exactly what the third check admits. For text evidence the rule is
unchanged, and ``check_evidence`` is not touched. The block gate fails closed: an input it
cannot verify (no geometry at all, no crop on record, a quote the store cannot keep) is a
refusal with a reason, never a pass.

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
    MAX_BLOCK_QUOTE_CHARS,
    BlockEvidenceItem,
    BlockGateInputs,
    BlockIndex,
    BlockObservation,
    EvidenceItem,
    Observation,
    ObservationSet,
    TextLayer,
)


class UngroundedReason(str, Enum):
    """The diagnostic vocabulary: ``ck_finding_observation_ungrounded_reason`` as ``0064`` left it.

    The text gate emits its original five; the block gate (gate v2) emits the last three.
    """

    QUOTATION_ABSENT = "quotation_absent"
    QUOTATION_ON_DIFFERENT_PAGE = "quotation_on_different_page"
    SPAN_OUTSIDE_PAGE = "span_outside_page"
    SPAN_OUTSIDE_BLOCK = "span_outside_block"
    SPAN_LENGTH_MISMATCH = "span_length_mismatch"
    QUOTE_IN_RECOGNISED_TEXT = "quote_in_recognised_text"
    NORM_LABEL_UNKNOWN = "norm_label_unknown"
    NORM_QUOTE_TOO_SHORT = "norm_quote_too_short"
    NORM_QUOTE_AMBIGUOUS = "norm_quote_ambiguous"
    NORM_QUOTE_ABSENT = "norm_quote_absent"
    NORM_VALUE_NOT_IN_QUOTE = "norm_value_not_in_quote"
    STATED_VALUE_NOT_IN_EVIDENCE = "stated_value_not_in_evidence"
    #: `F8-GATE` (``0064``): the refusals of a block as evidence.
    BLOCK_NOT_IN_RUN_GEOMETRY = "block_not_in_run_geometry"
    BLOCK_CROP_MISMATCH = "block_crop_mismatch"
    BLOCK_QUOTE_NOT_IN_RECOGNISED = "block_quote_not_in_recognised"


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

    observation: Observation | BlockObservation
    evidence_verdicts: tuple[EvidenceVerdict, ...]

    @property
    def grounding_kind(self) -> str:
        """How the observation was grounded (``text_span`` or ``portal_block``): what the publisher records on its row."""
        return self.observation.grounding_kind

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



# ---------------------------------------------------------------------------------------------
# Gate v2: a block as evidence (`F8-GATE`)
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BlockGateResult:
    """Every block observation the gate judged. A verdict is the same type the text gate's is."""

    verdicts: tuple[ObservationVerdict, ...]

    @property
    def grounded(self) -> tuple[ObservationVerdict, ...]:
        return tuple(verdict for verdict in self.verdicts if verdict.grounded)

    @property
    def ungrounded(self) -> tuple[ObservationVerdict, ...]:
        return tuple(verdict for verdict in self.verdicts if not verdict.grounded)

    def reason_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for verdict in self.ungrounded:
            reason = verdict.reason
            assert reason is not None  # an ungrounded verdict always carries one
            counts[reason.value] = counts.get(reason.value, 0) + 1
        return counts


def _refused(item: BlockEvidenceItem, reason: UngroundedReason) -> EvidenceVerdict:
    return EvidenceVerdict(evidence_ordinal=item.evidence_ordinal, resolved=False, reason=reason)


def check_block_evidence(item: BlockEvidenceItem, inputs: BlockGateInputs) -> EvidenceVerdict:
    """Resolve one block as evidence against this run's geometry, crops and recognised text.

    The order makes each reason attributable: the place first, because a block that is not
    in this run's geometry has no crop and no text worth looking up; then the crop on record;
    then the quote. The comparison of the quote is ``in`` on two ``str`` values: no strip,
    no casefold, no whitespace collapsing, no second normalisation.
    """
    # --- check 1: the block is in this run's geometry, on the page the item names ------
    place = inputs.geometry.place(item.portal_block_id)
    if place is None or place.page_number != item.page_number:
        # A block of another run or version, a malformed identifier, and a real block under
        # a page it does not stand on are one verdict: the place the item names is not in
        # this run's geometry.
        return _refused(item, UngroundedReason.BLOCK_NOT_IN_RUN_GEOMETRY)

    # --- check 2: the crop is the crop on record ------------------------------------------
    recorded = inputs.crops.sha256(item.portal_block_id)
    if recorded is None or recorded != item.crop_sha256:
        # No crop on record cannot match anything: an unverifiable crop is a mismatch, not a pass.
        return _refused(item, UngroundedReason.BLOCK_CROP_MISMATCH)

    # --- check 3: a quote, when there is one, is verbatim in the block's recognised text ---
    quote = item.recognised_quote
    if quote is not None:
        if (
            # "" is a substring of every string; the store holds no such quote (1 to 2000 characters).
            not quote
            or len(quote) > MAX_BLOCK_QUOTE_CHARS
            or not any(quote in body for body in inputs.recognised.texts(item.portal_block_id))
        ):
            return _refused(item, UngroundedReason.BLOCK_QUOTE_NOT_IN_RECOGNISED)

    return EvidenceVerdict(evidence_ordinal=item.evidence_ordinal, resolved=True)


def check_block_observation(observation: BlockObservation, inputs: BlockGateInputs) -> ObservationVerdict:
    """Judge one block observation. Every item is checked, as the text gate does, so the per-item record is whole."""
    return ObservationVerdict(
        observation=observation,
        evidence_verdicts=tuple(check_block_evidence(item, inputs) for item in observation.evidence),
    )


def run_block_gate(
    observations: Sequence[BlockObservation],
    inputs: BlockGateInputs | None,
) -> BlockGateResult:
    """Run gate v2 over block observations. Pure: no I/O, no clock, no randomness.

    ``inputs`` is ``None`` for a run that has none (a run in ``text_only`` mode builds none, and a
    version without a portal bundle has no geometry): every block is then refused as not being in
    this run's geometry. A ``text_only`` run therefore cannot publish a block even if a caller offers one.
    """
    judged = inputs if inputs is not None else BlockGateInputs.empty()
    return BlockGateResult(
        verdicts=tuple(check_block_observation(observation, judged) for observation in observations)
    )
