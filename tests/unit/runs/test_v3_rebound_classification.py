"""AR-V3-JUDGE-FIXES-01 finding 1: a proposal is provisional by the paragraph its citations
were GROUNDED to, not by the label the model wrote.

``ground_norm_observation`` may *rebind* a citation: the quote is not in the labelled paragraph but
is in exactly one other reliable paragraph of the same document, and the citation is grounded to
that one (``state == "rebound"``). The rebinding search covers every reliable paragraph of the
mapped documents, so the target can be a paragraph that the beta policy forbids citing
(``context_only``), a paragraph that no item selected, or a paragraph of another topic. The beta
classification must follow the paragraph, not the label.

Pure: no database, no object store, no network. The set is real (``parse_v3_set_input`` validates it)
and the response is evaluated by the real ``evaluate_v3_supplied_response``; only the custody read is
replaced, exactly as ``tests/integration/runs/test_v3_corpus_citation_bridge.py`` replaces it.

Layout of the synthetic F2 set (items ``C04`` ``C07`` are ``provisional_citation``; ``C05`` ``C06``
``C08`` ``C09`` ``C10`` are ``context_only``)::

    D1 ordinal 0  C04 own row           (provisional)
    D1 ordinal 1  C04 second row        (provisional, the same item)
    D1 ordinal 2  C06 row               (context only)
    D1 ordinal 3  C07 row               (provisional, another topic)
    D1 ordinal 4  carried by no item    (a reliable paragraph the model never saw under a label)
    D2 ordinals 0-3  one row each for C05 C08 C09 C10
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from auditmanager.analysis.profiles.ar_v3.scope_partition import scope_membership
from auditmanager.analysis.public import ModelResponse, SuppliedV3Response, TextLayer, sha256_hex
from auditmanager.analysis.text.textlayer import Page
from auditmanager.findings.public import VerifiedRetrievalSetInput
from auditmanager.jobs.public import AttemptAuthority
from auditmanager.runs import v3_citations, v3_review_artifact
from auditmanager.runs.repository import RunRow
from auditmanager.runs.v3_cite_preflight import V3CitePreflight

D1 = "ndoc_01K7F4N2A9R8T6V5W3X2Y1Z0QJ"
D2 = "ndoc_01K7F4N2A9R8T6V5W3X2Y1Z0QK"
SNAPSHOT = "ns_01M59N8QNBVN91ACA2HCE6VE74"
MAP_SHA = "a" * 64
PROFILE = "ap_01K7F4N2A9R8T6V5W3X2Y1Z0QH"
BUNDLE = "pb_01K7F4N2A9R8T6V5W3X2Y1Z0QH"
AUTHORITY = AttemptAuthority("run_test", "job_test", "att_test", "lease_test", "secret")
PDF_QUOTE = "Ширина прохода 1,2 м"

#: key -> (document, ordinal, text). Every text holds "1,4 м" (the required value) and is unique.
PARAGRAPHS: dict[str, tuple[str, int, str]] = {
    "c04": (D1, 0, "Минимальная ширина прохода в свету составляет 1,4 м"),
    "c04b": (D1, 1, "Ширина двери эвакуационного выхода должна быть не менее 1,4 м"),
    "c06": (D1, 2, "Контекстный абзац о ширине лестничной клетки не менее 1,4 м"),
    "c07": (D1, 3, "Другая тема: ширина пандуса для маломобильных групп 1,4 м"),
    "out": (D1, 4, "Вне решённых диапазонов: ширина тамбура принимается 1,4 м"),
    "c05": (D2, 0, "Прочий абзац темы пять о ширине коридора не менее 1,4 м"),
    "c08": (D2, 1, "Прочий абзац темы восемь о ширине марша не менее 1,4 м"),
    "c09": (D2, 2, "Прочий абзац темы девять о ширине площадки не менее 1,4 м"),
    "c10": (D2, 3, "Прочий абзац темы десять о ширине проёма не менее 1,4 м"),
}
#: item -> paragraph keys the set sends to the model under that item's labels.
LAYOUT: dict[str, tuple[str, ...]] = {
    "C04": ("c04", "c04b"), "C05": ("c05",), "C06": ("c06",), "C07": ("c07",),
    "C08": ("c08",), "C09": ("c09",), "C10": ("c10",),
}


def _pid(key: str) -> str:
    return f"npar_01K7F4N2A9R8T6V5W3X2Y1Z{list(PARAGRAPHS).index(key) + 100:03d}"


def _json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _row(key: str) -> dict[str, object]:
    document, ordinal, value = PARAGRAPHS[key]
    return dict(
        norm_document_id=document, norm_paragraph_id=_pid(key),
        designation="СП 1.13130.2020" if document == D1 else "СП 54.13330.2022",
        title="Норма", ordinal=ordinal, clause_number=f"7.{ordinal}", page_label="7",
        text=value, text_sha256=hashlib.sha256(value.encode()).hexdigest(),
    )


def _ordered(item_id: str, layout: dict[str, tuple[str, ...]]) -> list[str]:
    """Within an item the set orders rows by (designation, ordinal, document)."""
    return sorted(layout[item_id],
                  key=lambda k: (_row(k)["designation"], PARAGRAPHS[k][1], PARAGRAPHS[k][0]))


def _labels(layout: dict[str, tuple[str, ...]]) -> dict[tuple[str, str], str]:
    """(item, paragraph key) -> the label the prompt part gives that row."""
    out: dict[tuple[str, str], str] = {}
    for item_id in scope_membership("F2").item_ids:
        for key in _ordered(item_id, layout):
            out[(item_id, key)] = f"N{len(out) + 1}"
    return out


def _set(layout: dict[str, tuple[str, ...]]) -> bytes:
    prompt_rows = []
    for item_id in scope_membership("F2").item_ids:
        for key in _ordered(item_id, layout):
            prompt_rows.append(dict(_row(key), item_id=item_id, label=f"N{len(prompt_rows) + 1}"))
    prompt = _json({"builder_version": "norm-ranking-prep-v1", "paragraphs": prompt_rows}).decode("utf-8")
    source_rows = sorted((_row(key) for key in PARAGRAPHS),
                         key=lambda r: (r["norm_document_id"], r["ordinal"]))
    return _json({
        "builder_version": "norm-retrieval-set-prep-v1",
        "identity": {"map_sha256": MAP_SHA, "reviewed_content_key": "reviewed-key",
                     "norms_snapshot_id": SNAPSHOT, "embedding_build": "bge-m3-dense-v1"},
        "snapshot_content_digest": "b" * 64,
        "ranking_version": "norm-ranking-prep-v1", "norm_quote_version": "norm-quote-v1",
        "norm_value_version": "norm-value-v1",
        "prompt_part": prompt, "prompt_part_characters": len(prompt),
        "windows_per_item": 0, "inside_target_windows_dropped": True,
        "rebinding_paragraphs": source_rows,
    })


def _run() -> RunRow:
    return RunRow(
        run_id=AUTHORITY.run_id, project_uid="proj_test", version_uid="ver_test",
        state="running", analysis_profile_id=PROFILE, prompt_bundle_id=BUNDLE,
        norms_snapshot_id=SNAPSHOT, provider_mode="recorded", frozen_input_digest="c" * 64,
        command_id=None, terminal_reason=None, terminal_detail=None, interrupted_reason=None,
        degradation_set=(), created_at=datetime(2026, 10, 23, tzinfo=timezone.utc),
        terminal_at=None, norm_retrieval_set_id="nrs_test",
    )


def _layer() -> TextLayer:
    text = "АР. " + PDF_QUOTE + "."
    return TextLayer("ver_test", "NFC", (Page(1, 0, len(text), text),), text)


def _request(monkeypatch: pytest.MonkeyPatch, layout: dict[str, tuple[str, ...]]):
    raw = _set(layout)
    verified = VerifiedRetrievalSetInput(
        AUTHORITY.run_id, SNAPSHOT, "nrs_test", MAP_SHA, "blob_test",
        hashlib.sha256(raw).hexdigest(), raw,
    )
    monkeypatch.setattr(v3_citations, "load_verified_retrieval_set", lambda *a, **k: verified)
    return v3_citations.prepare_v3_corpus_request(
        object(), run=_run(), authority=AUTHORITY, blob_store=object(), text_layer=_layer(),
        profile_id=PROFILE, bundle_id=BUNDLE, map_sha256=MAP_SHA, scope_id="F2",
        composition_sha256=scope_membership("F2").composition_sha256,
    )


def _response(digest: str, citations: list[tuple[str, str]]) -> SuppliedV3Response:
    """One normative proposal; each citation is (label, the text of the paragraph it quotes)."""
    return SuppliedV3Response(digest, _json({"observations": [{
        "category": "evacuation", "finding_text": "Проверить ширину прохода.",
        "recommendation_text": "Сверить проект и норму.", "proposed_severity": "operational",
        "evidence": [{"page_number": 1, "quote": PDF_QUOTE}],
        "norm_citations": [{"label": label, "quote": quote} for label, quote in citations],
        "required_value": "1,4 м", "stated_value": "1,2 м",
    }]}).decode("utf-8"), False)


def _classify(monkeypatch: pytest.MonkeyPatch, citations: list[tuple[str, str]],
              layout: dict[str, tuple[str, ...]] | None = None):
    layout = layout or LAYOUT
    request = _request(monkeypatch, layout)
    return v3_citations.plan_v3_beta_citation_review(
        request, _response(request.candidate.request_sha256, citations), _layer(),
    )


def _text(key: str) -> str:
    return PARAGRAPHS[key][2]


def _states(review) -> list[tuple[str, str, str]]:
    (accepted,) = review.evaluation.grounding.accepted
    return [(c.label, c.paragraph_id, c.state) for c in accepted.norm_citations]


LABEL = _labels(LAYOUT)
PROVISIONAL = ((0,), ())
WITHHELD = ((), (0,))


def _outcome(review) -> tuple[tuple[int, ...], tuple[int, ...]]:
    return review.provisional_proposal_ordinals, review.withheld_proposal_ordinals


# --- controls: what already worked must keep working --------------------------------------------


def test_a_citation_verified_in_its_own_provisional_row_is_provisional(monkeypatch):
    review = _classify(monkeypatch, [(LABEL[("C04", "c04")], _text("c04"))])
    assert _states(review) == [(LABEL[("C04", "c04")], _pid("c04"), "verified")]
    assert _outcome(review) == PROVISIONAL


def test_a_citation_under_a_context_only_label_is_withheld(monkeypatch):
    review = _classify(monkeypatch, [(LABEL[("C06", "c06")], _text("c06"))])
    assert _outcome(review) == WITHHELD


def test_a_mixed_provisional_and_context_only_proposal_is_withheld(monkeypatch):
    review = _classify(monkeypatch, [
        (LABEL[("C04", "c04")], _text("c04")), (LABEL[("C05", "c05")], _text("c05"))])
    assert _outcome(review) == WITHHELD


# --- the judge's finding: the grounded paragraph decides, not the label --------------------------


def test_a_quote_rebound_to_a_paragraph_of_a_context_only_item_is_withheld(monkeypatch):
    """N(C04) names provisional C04, but the quote is C06's text: C06 may not be cited."""
    review = _classify(monkeypatch, [(LABEL[("C04", "c04")], _text("c06"))])
    assert _states(review) == [(LABEL[("C04", "c04")], _pid("c06"), "rebound")]
    assert _outcome(review) == WITHHELD


def test_a_quote_rebound_to_a_paragraph_that_no_item_carries_is_withheld(monkeypatch):
    """The reliable paragraph is outside every decided span: the model never saw it under a label."""
    review = _classify(monkeypatch, [(LABEL[("C04", "c04")], _text("out"))])
    assert _states(review) == [(LABEL[("C04", "c04")], _pid("out"), "rebound")]
    assert _outcome(review) == WITHHELD


def test_a_quote_rebound_to_the_span_of_another_provisional_item_is_withheld(monkeypatch):
    """Decision: the label names the topic; a quote found in another topic's paragraph does not
    ground that topic, so the proposal is withheld rather than re-attributed to C07."""
    review = _classify(monkeypatch, [(LABEL[("C04", "c04")], _text("c07"))])
    assert _states(review) == [(LABEL[("C04", "c04")], _pid("c07"), "rebound")]
    assert _outcome(review) == WITHHELD


def test_a_quote_rebound_to_another_row_of_the_same_provisional_item_stays_provisional(monkeypatch):
    """The model mislabelled the row but the text is in the same topic's own span: unchanged."""
    review = _classify(monkeypatch, [(LABEL[("C04", "c04")], _text("c04b"))])
    assert _states(review) == [(LABEL[("C04", "c04")], _pid("c04b"), "rebound")]
    assert _outcome(review) == PROVISIONAL


def test_one_bad_citation_withholds_the_whole_proposal(monkeypatch):
    review = _classify(monkeypatch, [
        (LABEL[("C04", "c04")], _text("c04")),          # verified, provisional
        (LABEL[("C04", "c04")], _text("out"))])         # rebound outside every span
    assert _outcome(review) == WITHHELD


def test_a_paragraph_that_a_context_only_item_also_carries_is_withheld_whatever_the_label(monkeypatch):
    """C06 also sends C04's paragraph (under its own label): a citation of it is a citation of a
    context-only span, even when the model used C04's provisional label and the quote is verified."""
    layout = dict(LAYOUT, C06=("c04", "c06"))
    labels = _labels(layout)
    review = _classify(monkeypatch, [(labels[("C04", "c04")], _text("c04"))], layout)
    assert _states(review) == [(labels[("C04", "c04")], _pid("c04"), "verified")]
    assert _outcome(review) == WITHHELD


def test_a_paragraph_that_two_provisional_items_carry_is_provisional(monkeypatch):
    """Two provisional topics may select one paragraph (the real map does: C12/C13, C19/C20)."""
    layout = dict(LAYOUT, C07=("c04", "c07"))
    labels = _labels(layout)
    review = _classify(monkeypatch, [(labels[("C04", "c04")], _text("c04"))], layout)
    assert _outcome(review) == PROVISIONAL


def test_the_classification_is_the_same_for_the_same_inputs(monkeypatch):
    first = _classify(monkeypatch, [(LABEL[("C04", "c04")], _text("c06"))])
    second = _classify(monkeypatch, [(LABEL[("C04", "c04")], _text("c06"))])
    assert _outcome(first) == _outcome(second) == WITHHELD


# --- the CITE writer and the terminal classify through one function ------------------------------


def _preflight(request, review, supplied) -> V3CitePreflight:
    """What ``prepare_v3_cite_preflight`` hands the artifact builder, built from the real review."""
    model_response = ModelResponse(supplied.output_text, "end_turn", 11, 13, 17, 0.012)
    digest = request.candidate.request_sha256
    verified = request.verified_set
    binding = SimpleNamespace(
        run_id=AUTHORITY.run_id, group_id="arg_test", scope_id="F2", version_uid="ver_test",
        norms_snapshot_id=SNAPSHOT, norm_retrieval_set_id="nrs_test", analysis_profile_id=PROFILE,
        prompt_bundle_id=BUNDLE, map_sha256=MAP_SHA, set_sha256=verified.set_sha256,
        policy_sha256=review.source_policy_sha256,
    )
    prepared = SimpleNamespace(
        pinned_corpus=request, binding=binding, candidate_sha256=digest, provider_body_sha256="b" * 64,
    )
    call = SimpleNamespace(
        run_id=AUTHORITY.run_id, scope_id="F2", model_call_id="call_test",
        set_sha256=verified.set_sha256, candidate_sha256=digest, request_sha256="b" * 64,
        response_sha256=model_response.response_sha256,
        reply_blob_id="blob_01M2545JSD15ETSNNV904X991J", reply_blob_sha256="e" * 64,
        reply_blob_size=401,
    )
    return V3CitePreflight(prepared, call, SimpleNamespace(model_response=model_response), review)


def test_the_sealed_review_and_the_terminals_rebuild_agree_and_publish_nothing_for_a_rebound_into_context(
        monkeypatch):
    """The CITE writer seals, the terminal rebuilds the same review from the same saved inputs and
    compares bytes. Both go through ``plan_v3_beta_citation_review``, so a proposal rebound into a
    context-only paragraph is withheld in the seal, in the rebuild, and yields no candidate."""
    request = _request(monkeypatch, LAYOUT)
    supplied = _response(request.candidate.request_sha256, [(LABEL[("C04", "c04")], _text("c06"))])

    def build():
        review = v3_citations.plan_v3_beta_citation_review(request, supplied, _layer())
        return review, v3_review_artifact.build_v3_beta_review_artifact(_preflight(request, review, supplied))

    review, sealed = build()
    rebuilt_review, rebuilt = build()
    assert rebuilt.sha256 == sealed.sha256 and rebuilt.size_bytes == sealed.size_bytes
    document = json.loads(sealed.payload)
    assert document["provisional_citations"] == []
    assert document["withheld_proposals"] == [
        {"proposal_ordinal": 0, "reason": "context_only_or_mixed_source"}]
    assert all(topic["provisional_citation_count"] == 0 for topic in document["topics"])
    assert v3_citations.provisional_publication_candidates(rebuilt_review) == ()
    assert review.provisional_proposal_ordinals == () and review.withheld_proposal_ordinals == (0,)


def test_a_rebound_inside_the_labelled_item_is_sealed_and_rebuilt_as_one_candidate(monkeypatch):
    request = _request(monkeypatch, LAYOUT)
    supplied = _response(request.candidate.request_sha256, [(LABEL[("C04", "c04")], _text("c04b"))])
    review = v3_citations.plan_v3_beta_citation_review(request, supplied, _layer())
    sealed = v3_review_artifact.build_v3_beta_review_artifact(_preflight(request, review, supplied))
    (entry,) = json.loads(sealed.payload)["provisional_citations"]
    assert [(c["item_id"], c["state"], c["paragraph_id"]) for c in entry["citations"]] == [
        ("C04", "rebound", _pid("c04b"))]
    assert len(v3_citations.provisional_publication_candidates(review)) == 1


# --- the shared pure rule ------------------------------------------------------------------------


def _index(rows):
    return v3_citations.index_prompt_rows(rows)


def _grounded(label, paragraph, state="verified"):
    from auditmanager.norms.public import GroundedNormCitation
    return GroundedNormCitation(label, D1, paragraph, 0, "q" * 20, state)


MODES = {"C04": "provisional_citation", "C06": "context_only", "C07": "provisional_citation"}
def _rule(labels, grounded):
    rows = _index([
        {"label": "N1", "item_id": "C04", "norm_paragraph_id": "p_a"},
        {"label": "N2", "item_id": "C06", "norm_paragraph_id": "p_b"},
        {"label": "N3", "item_id": "C07", "norm_paragraph_id": "p_c"},
    ])
    return v3_citations.grounded_citations_are_provisional(labels, grounded, rows=rows, modes=MODES)


def test_the_rule_in_one_place_verified_own_row():
    assert _rule(["N1"], [_grounded("N1", "p_a")]) is True


@pytest.mark.parametrize(("paragraph", "expected"), [("p_a", True), ("p_b", False), ("p_c", False), ("p_z", False)])
def test_the_rule_in_one_place_rebound_targets(paragraph, expected):
    assert _rule(["N1"], [_grounded("N1", paragraph, "rebound")]) is expected


def test_the_rule_refuses_an_unknown_label_a_mismatch_and_an_unknown_state():
    with pytest.raises(v3_citations.V3CorpusCitationRefused, match="beta_citation_label_invalid"):
        _rule(["N9"], [_grounded("N9", "p_a")])
    with pytest.raises(v3_citations.V3CorpusCitationRefused, match="beta_citation_grounding_mismatch"):
        _rule(["N1"], [_grounded("N2", "p_a")])
    with pytest.raises(v3_citations.V3CorpusCitationRefused, match="beta_citation_grounding_mismatch"):
        _rule(["N1", "N1"], [_grounded("N1", "p_a")])
    with pytest.raises(v3_citations.V3CorpusCitationRefused, match="beta_citation_state_invalid"):
        _rule(["N1"], [replace(_grounded("N1", "p_a"), state="guessed")])


def test_the_prompt_row_index_refuses_a_duplicate_label_and_a_row_without_a_paragraph():
    with pytest.raises(v3_citations.V3CorpusCitationRefused, match="beta_set_labels_invalid"):
        _index([{"label": "N1", "item_id": "C04", "norm_paragraph_id": "p_a"},
                {"label": "N1", "item_id": "C06", "norm_paragraph_id": "p_b"}])
    with pytest.raises(v3_citations.V3CorpusCitationRefused, match="beta_set_labels_invalid"):
        _index([{"label": "N1", "item_id": "C04"}])
