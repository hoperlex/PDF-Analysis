"""The offset rule, and what happens to a quotation that is not in the document.

``P02_SEAMS.md`` section 4.1 calls the offset rule the single most expensive thing in
that document to get wrong, and says why: the corpus is Russian, so a byte offset
misplaces every anchor while still looking plausible in a test written in English.
These tests are therefore written so that a byte-counting implementation **fails**
them - the corpus text is Cyrillic throughout, where one code point is two UTF-8
bytes, and several assertions compare against ``len(quote)`` and against the
UTF-8-encoded length explicitly.

The second half covers the grounding boundary. The model does not compute offsets, so
this stage resolves each quotation itself and emits an evidence item only when the
quotation is actually found. An observation that keeps at least one resolved item is
still emitted, and ``B4`` re-verifies every one of them.
"""

from __future__ import annotations

import json

import pytest

from auditmanager.analysis.text import (
    STATUS_SUCCEEDED,
    BlockIndex,
    RecordedAdapter,
    ResolvedAnchor,
    UnresolvedAnchor,
    load_text_layer,
    run_text_analysis,
)
from auditmanager.analysis.text.anchors import (
    REASON_ABSENT,
    REASON_DIFFERENT_PAGE,
    resolve_anchor,
)
from auditmanager.shared.identity import RunId

CONTRADICTION_QUOTE = "Степень огнестойкости здания — II."


# --- the document-global sequence -----------------------------------------------


def test_pages_concatenate_with_no_separator(text_layer_document):
    text_layer = load_text_layer(text_layer_document)
    assert text_layer.pages[0].char_start == 0
    for previous, page in zip(text_layer.pages, text_layer.pages[1:]):
        assert page.char_start == previous.char_end
    assert text_layer.pages[-1].char_end == text_layer.total_char_count
    assert text_layer.document_text == "".join(page.text for page in text_layer.pages)


def test_offsets_are_code_points_and_not_bytes(text_layer_document):
    """The assertion a byte-counting implementation cannot pass.

    Every page of this corpus is Cyrillic, so its UTF-8 length is close to twice its
    code-point length. An implementation that measured bytes would put the last page's
    ``char_end`` at roughly double the true total.
    """
    text_layer = load_text_layer(text_layer_document)
    for page in text_layer.pages:
        assert page.char_end - page.char_start == len(page.text)
        assert len(page.text.encode("utf-8")) > len(page.text)
    total_bytes = len(text_layer.document_text.encode("utf-8"))
    assert total_bytes > text_layer.total_char_count * 1.5


def test_emitted_anchors_slice_back_to_their_own_quotation(
    text_layer_document, recorded_adapter
):
    outcome = run_text_analysis(
        run_id=RunId.new(), text_layer_document=text_layer_document, adapter=recorded_adapter
    )
    assert outcome.status == STATUS_SUCCEEDED
    text_layer = load_text_layer(text_layer_document)

    for observation in outcome.artifact["observations"]:
        assert observation["evidence"], "section 4.7: an observation with no evidence is malformed"
        for item in observation["evidence"]:
            start, end, quote = item["char_start"], item["char_end"], item["quote"]
            # The three things B4's gate will re-check, checked here on the emitted
            # document rather than on an internal value.
            assert end - start == len(quote)
            assert text_layer.slice(start, end) == quote
            page = text_layer.page(item["page_number"])
            assert page.char_start <= start and end <= page.char_end


def test_ordinals_are_positions_and_not_identities(text_layer_document, recorded_adapter):
    outcome = run_text_analysis(
        run_id=RunId.new(), text_layer_document=text_layer_document, adapter=recorded_adapter
    )
    for expected, observation in enumerate(outcome.artifact["observations"]):
        assert observation["observation_ordinal"] == expected
        for index, item in enumerate(observation["evidence"]):
            assert item["evidence_ordinal"] == index
    # finding_uid and finding_observation_id are allocated by B4 at publication.
    rendered = json.dumps(outcome.artifact, ensure_ascii=False)
    assert "finding_uid" not in rendered
    assert "finding_observation_id" not in rendered
    assert "fnd_" not in rendered and "fobs_" not in rendered


# --- resolving one quotation ----------------------------------------------------


def test_a_present_quotation_resolves_to_its_interval(text_layer_document):
    text_layer = load_text_layer(text_layer_document)
    anchor = resolve_anchor(text_layer, page_number=2, quote=CONTRADICTION_QUOTE)
    assert isinstance(anchor, ResolvedAnchor)
    assert text_layer.slice(anchor.char_start, anchor.char_end) == CONTRADICTION_QUOTE
    assert anchor.char_end - anchor.char_start == len(CONTRADICTION_QUOTE)
    assert anchor.block_id is None


def test_an_absent_quotation_does_not_resolve(text_layer_document):
    text_layer = load_text_layer(text_layer_document)
    outcome = resolve_anchor(
        text_layer, page_number=2, quote="Класс энергетической эффективности здания — A."
    )
    assert isinstance(outcome, UnresolvedAnchor)
    assert outcome.reason == REASON_ABSENT


def test_a_quotation_cited_on_the_wrong_page_does_not_resolve(text_layer_document):
    """The page is part of the claim, so a wrong page is not silently repaired."""
    text_layer = load_text_layer(text_layer_document)
    outcome = resolve_anchor(text_layer, page_number=5, quote=CONTRADICTION_QUOTE)
    assert isinstance(outcome, UnresolvedAnchor)
    assert outcome.reason == REASON_DIFFERENT_PAGE


def test_surrounding_whitespace_is_trimmed_and_the_trimmed_literal_is_emitted(
    text_layer_document,
):
    text_layer = load_text_layer(text_layer_document)
    anchor = resolve_anchor(text_layer, page_number=2, quote=f"  {CONTRADICTION_QUOTE}\n")
    assert isinstance(anchor, ResolvedAnchor)
    # What is emitted is exactly what lies at the interval, never the padded original.
    assert anchor.quote == CONTRADICTION_QUOTE
    assert text_layer.slice(anchor.char_start, anchor.char_end) == anchor.quote


def test_nothing_normalizes_the_model_output(text_layer_document):
    """Section 4.3: ``B3`` must not normalize before writing an anchor.

    The corpus is NFC. The same quotation in NFD is a different string, and it must
    fail to resolve rather than be quietly folded - ``B4`` compares after the one
    declared normalization and nothing else, so a re-normalized anchor would be a
    quotation the gate cannot reproduce.
    """
    import unicodedata

    text_layer = load_text_layer(text_layer_document)
    decomposed = unicodedata.normalize("NFD", CONTRADICTION_QUOTE)
    assert decomposed != CONTRADICTION_QUOTE, "pick a quotation that NFD actually changes"
    outcome = resolve_anchor(text_layer, page_number=2, quote=decomposed)
    assert isinstance(outcome, UnresolvedAnchor)


def test_block_id_is_bound_when_a_block_index_is_supplied(text_layer_document):
    text_layer = load_text_layer(text_layer_document)
    page = text_layer.page(2)
    index = BlockIndex.from_document(
        {
            "artifact_role": "geometry.block_index",
            "artifact_version": "1.0.0",
            "blocks": [
                {
                    "block_id": "b_000002",
                    "page_number": 2,
                    "char_start": page.char_start,
                    "char_end": page.char_end,
                }
            ],
        }
    )
    anchor = resolve_anchor(
        text_layer, page_number=2, quote=CONTRADICTION_QUOTE, block_index=index
    )
    assert isinstance(anchor, ResolvedAnchor)
    assert anchor.block_id == "b_000002"


# --- an unresolvable quotation, end to end --------------------------------------


def test_unresolvable_evidence_is_dropped_and_counted(
    text_layer_document, variant_adapter
):
    """The ``ungrounded_quotation`` recording, run end to end.

    The recording carries two observations. The first cites one quotation that is not
    in the document at all; it loses every evidence item and is therefore **not
    emitted**, because section 4.7 makes an evidence-free observation malformed rather
    than ungrounded, and the artifact has no shape in which to carry it. The second
    pairs a real quotation with an invented one; it **is** emitted, carrying only the
    item that resolved, and ``B4`` re-verifies that item independently.

    Note the divergence from ``docs/program/tasks/P2-AI-01.md``, which expects an
    observation whose quotation is absent to be emitted anyway and left for the gate to
    reject. There is no honest interval for a string that is not in the text layer -
    ``char_end - char_start`` must equal the quotation's length - so emitting one would
    mean inventing offsets. The dispatch brief resolves this the other way, and the
    counts below are the observable behaviour either way.
    """
    outcome = run_text_analysis(
        run_id=RunId.new(),
        text_layer_document=text_layer_document,
        adapter=variant_adapter("ungrounded_quotation"),
    )
    assert outcome.status == STATUS_SUCCEEDED
    assert outcome.metrics["observations_proposed"] == 2
    assert outcome.metrics["observations_emitted"] == 1
    assert outcome.metrics["observations_dropped_unresolved"] == 1
    assert outcome.metrics["evidence_unresolved"] == 2
    assert outcome.metrics["evidence_emitted"] == 1

    (observation,) = outcome.artifact["observations"]
    (item,) = observation["evidence"]
    assert item["quote"] == CONTRADICTION_QUOTE

    text_layer = load_text_layer(text_layer_document)
    assert text_layer.slice(item["char_start"], item["char_end"]) == item["quote"]


def test_an_artifact_never_carries_an_evidence_free_observation(
    text_layer_document, variant_adapter
):
    outcome = run_text_analysis(
        run_id=RunId.new(),
        text_layer_document=text_layer_document,
        adapter=variant_adapter("ungrounded_quotation"),
    )
    for observation in outcome.artifact["observations"]:
        assert len(observation["evidence"]) >= 1


def test_the_stage_writes_no_verdict(text_layer_document, recorded_adapter):
    """Bible P-17: model output is never an expert verdict."""
    outcome = run_text_analysis(
        run_id=RunId.new(), text_layer_document=text_layer_document, adapter=recorded_adapter
    )
    rendered = json.dumps(outcome.artifact, ensure_ascii=False)
    for forbidden in ("verdict", "decision", "accepted", "rejected", "grounded", "published"):
        assert forbidden not in rendered
