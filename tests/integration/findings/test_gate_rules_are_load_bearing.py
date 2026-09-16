"""The rules *inside* the grounding gate, one at a time.

`W5-CERT` and `W6-CERT` each proved by mutation that a ``grounded = false`` row is never
written. Neither established **which rule inside the gate carries that**, and the `W10-FND`
sweep found four that nothing could redden:

* ``ObservationVerdict.reason`` promises "the reason of the first item that failed, in
  evidence order"; reversing the scan reddened nothing, because every existing perturbation
  builds an observation with exactly **one** failing item, where first and last coincide;
* ``ObservationVerdict.failing_evidence_ordinal`` promises the same ordering, with the same
  gap;
* ``EvidenceVerdict.__post_init__`` refuses an incoherent verdict, and deleting the refusal
  reddened nothing — although the identical invariant on ``TerminalSelection`` **is**
  covered, by ``test_an_incoherent_selection_cannot_be_constructed``;
* ``run_grounding_gate`` documents that omitting ``block_index`` leaves check 3 failing
  **closed**; no test anywhere calls it without one.

Every expected value below is written out as a literal. Nothing here imports a constant from
the module and then builds the expectation from it: that is what made five of wave 9's tests
pass under mutation, because both sides of the comparison moved together.
"""

from __future__ import annotations

import pytest

from auditmanager.findings import (
    EvidenceVerdict,
    UngroundedReason,
    run_grounding_gate,
)


def _observation(anchors, *, category="internal_contradiction", finding_text="Расхождение."):
    return {
        "category": category,
        "finding_text": finding_text,
        "recommendation_text": "Согласовать значения между разделами.",
        "evidence": anchors,
    }


def _length_mismatch(anchor):
    """An anchor whose declared width is the quote's **byte** length. Fails check 0."""
    broken = dict(anchor)
    broken["char_end"] = anchor["char_start"] + len(anchor["quote"].encode("utf-8"))
    broken["block_id"] = None
    return broken


def _page_the_document_does_not_have(anchor):
    """An anchor on page 99 of an eight-page document. Fails check 1."""
    broken = dict(anchor)
    broken["page_number"] = 99
    broken["block_id"] = None
    return broken


# ---------------------------------------------------------------------------
# The diagnostic is the FIRST failing item's, in evidence order
# ---------------------------------------------------------------------------


class TestTheDiagnosticIsTheFirstFailingItemInEvidenceOrder:
    """Two items failing for two *different* reasons, in both orders.

    One failing item cannot tell "first" from "last" apart, which is exactly why reversing
    the scan reddened nothing. Two items failing differently can, and the two orders are
    asserted against opposite literals so neither passes by accident.
    """

    def test_the_reason_is_the_first_failing_items_reason(
        self, corpus, text_layer, block_index, make_observations
    ) -> None:
        anchor = corpus.seeded_anchors()[0]
        observations = make_observations(
            [
                _observation(
                    [_length_mismatch(anchor), _page_the_document_does_not_have(anchor)]
                ),
                _observation(
                    [_page_the_document_does_not_have(anchor), _length_mismatch(anchor)]
                ),
            ]
        )
        result = run_grounding_gate(observations, text_layer, block_index)

        length_first, page_first = result.verdicts
        assert not length_first.grounded and not page_first.grounded

        # Both items of both observations failed, so "the first" is a real choice and not
        # the only available answer.
        assert [v.resolved for v in length_first.evidence_verdicts] == [False, False]
        assert [v.resolved for v in page_first.evidence_verdicts] == [False, False]

        # Literal wire values, not `UngroundedReason.X.value`: a renamed enum member must
        # redden here as well as in the vocabulary test.
        assert length_first.reason is UngroundedReason.SPAN_LENGTH_MISMATCH
        assert length_first.reason.value == "span_length_mismatch"
        assert page_first.reason is UngroundedReason.SPAN_OUTSIDE_PAGE
        assert page_first.reason.value == "span_outside_page"

    def test_the_failing_ordinal_is_the_first_failing_items_ordinal(
        self, corpus, text_layer, block_index, make_observations
    ) -> None:
        anchor = corpus.seeded_anchors()[0]
        observations = make_observations(
            [
                _observation(
                    [_length_mismatch(anchor), _page_the_document_does_not_have(anchor)]
                )
            ]
        )
        verdict = run_grounding_gate(observations, text_layer, block_index).verdicts[0]

        assert [v.evidence_ordinal for v in verdict.evidence_verdicts] == [0, 1]
        assert [v.resolved for v in verdict.evidence_verdicts] == [False, False]
        assert verdict.failing_evidence_ordinal == 0, (
            "the failing ordinal is the *first* failing item's, so two runs over one "
            "artifact record the same diagnostic"
        )

    def test_a_resolving_item_before_a_failing_one_does_not_become_the_diagnostic(
        self, corpus, text_layer, block_index, make_observations
    ) -> None:
        """The scan skips resolved items rather than reporting ordinal 0 regardless."""
        anchor = corpus.seeded_anchors()[0]
        observations = make_observations(
            [_observation([dict(anchor), _page_the_document_does_not_have(anchor)])]
        )
        verdict = run_grounding_gate(observations, text_layer, block_index).verdicts[0]

        assert [v.resolved for v in verdict.evidence_verdicts] == [True, False]
        assert verdict.failing_evidence_ordinal == 1
        assert verdict.reason is UngroundedReason.SPAN_OUTSIDE_PAGE

    def test_the_reason_counts_follow_the_same_first_failing_rule(
        self, corpus, text_layer, block_index, make_observations
    ) -> None:
        anchor = corpus.seeded_anchors()[0]
        observations = make_observations(
            [
                _observation(
                    [_length_mismatch(anchor), _page_the_document_does_not_have(anchor)]
                ),
                _observation(
                    [_page_the_document_does_not_have(anchor), _length_mismatch(anchor)]
                ),
            ]
        )
        result = run_grounding_gate(observations, text_layer, block_index)
        assert result.reason_counts() == {
            "span_length_mismatch": 1,
            "span_outside_page": 1,
        }, "reason_counts() attributes each observation to its first failing item"


# ---------------------------------------------------------------------------
# An incoherent evidence verdict cannot be constructed
# ---------------------------------------------------------------------------


class TestAnIncoherentEvidenceVerdictCannotBeConstructed:
    """``resolved`` is true exactly when ``reason`` is absent.

    This is the same pairing the migration enforces on ``finding_observation``
    (``grounded = (ungrounded_reason IS NULL)``, `0002_pc01_schema`), asserted at the point
    of construction. Deleting the refusal reddened nothing before this class existed.
    """

    MESSAGE = "an evidence verdict is resolved exactly when it carries no reason"

    def test_a_resolved_verdict_carrying_a_reason_is_refused(self) -> None:
        with pytest.raises(ValueError) as caught:
            EvidenceVerdict(
                evidence_ordinal=0,
                resolved=True,
                reason=UngroundedReason.SPAN_OUTSIDE_PAGE,
            )
        assert str(caught.value) == self.MESSAGE

    def test_an_unresolved_verdict_carrying_no_reason_is_refused(self) -> None:
        with pytest.raises(ValueError) as caught:
            EvidenceVerdict(evidence_ordinal=0, resolved=False)
        assert str(caught.value) == self.MESSAGE

    def test_the_two_coherent_pairings_are_accepted(self) -> None:
        resolved = EvidenceVerdict(evidence_ordinal=0, resolved=True)
        assert resolved.reason is None
        refused = EvidenceVerdict(
            evidence_ordinal=1,
            resolved=False,
            reason=UngroundedReason.QUOTATION_ABSENT,
        )
        assert refused.reason.value == "quotation_absent"


# ---------------------------------------------------------------------------
# An omitted block index fails check 3 CLOSED
# ---------------------------------------------------------------------------


class TestAnOmittedBlockIndexStillFailsCheckThreeClosed:
    """``block_index`` is optional on ``run_grounding_gate``; check 3 is not.

    Of the call sites in `src/` and `tests/`, every single one passes a block index, so
    the documented fail-closed behaviour of the default was asserted nowhere. An anchor
    that declares a ``block_id`` against an empty index must be **refused**, not admitted:
    failing open would publish an anchor whose declared geometry nobody checked.
    """

    def test_an_anchor_declaring_a_block_is_refused_when_no_index_is_supplied(
        self, corpus, text_layer, make_observations
    ) -> None:
        anchor = next(a for a in corpus.seeded_anchors() if a["block_id"] is not None)
        observations = make_observations([_observation([dict(anchor)])])

        # No third argument. This is the call the default exists for.
        result = run_grounding_gate(observations, text_layer)

        assert result.grounded_count == 0
        assert result.ungrounded_count == 1
        assert result.verdicts[0].reason is UngroundedReason.SPAN_OUTSIDE_BLOCK
        assert result.reason_counts() == {"span_outside_block": 1}

    def test_the_same_anchor_grounds_when_the_index_is_supplied(
        self, corpus, text_layer, block_index, make_observations
    ) -> None:
        """The control: the refusal above is the missing index, not a broken anchor."""
        anchor = next(a for a in corpus.seeded_anchors() if a["block_id"] is not None)
        observations = make_observations([_observation([dict(anchor)])])

        result = run_grounding_gate(observations, text_layer, block_index)

        assert result.grounded_count == 1
        assert result.ungrounded_count == 0

    def test_an_anchor_declaring_no_block_still_grounds_without_an_index(
        self, corpus, text_layer, make_observations
    ) -> None:
        """Fail-closed applies to a declared block, not to every anchor: an item with no
        ``block_id`` never reaches check 3 and must still ground."""
        anchor = dict(next(a for a in corpus.seeded_anchors() if a["block_id"] is not None))
        anchor["block_id"] = None
        observations = make_observations([_observation([anchor])])

        result = run_grounding_gate(observations, text_layer)

        assert result.grounded_count == 1
        assert result.ungrounded_count == 0
