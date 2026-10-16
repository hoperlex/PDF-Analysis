"""Saved retrieval-set bytes become candidate v3 prompt and grounding input."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy

import pytest

from auditmanager.analysis.profiles.ar_v3.citation_grounding import ground_v3_proposals
from auditmanager.analysis.profiles.ar_v3.response import parse_response
from auditmanager.analysis.profiles.ar_v3.set_input import (
    V3SetInputRefused,
    parse_v3_set_input,
)
from auditmanager.analysis.text.textlayer import Page, TextLayer
from auditmanager.norms.retrieval.artifact import (
    SetIdentity, SnapshotBinding, SourceParagraph, build_retrieval_set,
    canonical_json_bytes,
)
from auditmanager.norms.retrieval.ranking import (
    PromptRow, PromptSelection, RetrievalParagraph,
)


SNAPSHOT = "ns_01K7F4N2A9R8T6V5W3X2Y1Z0QH"
DOCUMENT = "ndoc_01K7F4N2A9R8T6V5W3X2Y1Z0QJ"
PARAGRAPH = "npar_01K7F4N2A9R8T6V5W3X2Y1Z0QK"
MAP_SHA = "a" * 64
QUOTE = "Минимальная ширина прохода составляет 1,4 м"
PDF_QUOTE = "Ширина прохода 1,2 м"


def _bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _payload():
    source = {
        "norm_document_id": DOCUMENT, "norm_paragraph_id": PARAGRAPH,
        "designation": "СП 54", "title": "Жилые здания", "ordinal": 0,
        "clause_number": "7.1.4", "page_label": "7", "text": QUOTE,
        "text_sha256": hashlib.sha256(QUOTE.encode()).hexdigest(),
    }
    selected = [dict(source, item_id=item, label=f"N{ordinal}")
                for ordinal, item in enumerate(("item_a", "item_b"), 1)]
    part = _bytes({
        "builder_version": "norm-ranking-prep-v1", "paragraphs": selected,
    }).decode()
    return {
        "builder_version": "norm-retrieval-set-prep-v1",
        "identity": {
            "map_sha256": MAP_SHA, "reviewed_content_key": "reviewed-key",
            "norms_snapshot_id": SNAPSHOT, "embedding_build": "bge-m3-dense-v1",
        },
        "snapshot_content_digest": "b" * 64,
        "ranking_version": "norm-ranking-prep-v1",
        "norm_quote_version": "norm-quote-v1",
        "norm_value_version": "norm-value-v1",
        "prompt_part": part, "prompt_part_characters": len(part),
        "windows_per_item": 0, "inside_target_windows_dropped": True,
        "rebinding_paragraphs": [source],
    }


def _parse(value):
    raw = _bytes(value)
    return parse_v3_set_input(
        raw, expected_sha256=hashlib.sha256(raw).hexdigest(),
        expected_snapshot_id=SNAPSHOT, expected_map_sha256=MAP_SHA,
    )


def _change_selected(payload, key, value):
    prompt = json.loads(payload["prompt_part"])
    prompt["paragraphs"][0][key] = value
    payload["prompt_part"] = _bytes(prompt).decode()
    payload["prompt_part_characters"] = len(payload["prompt_part"])


def test_two_labels_for_one_canonical_paragraph_ground_without_duplicate_identity():
    material = _parse(_payload())
    assert len(material.paragraphs) == 1
    assert [(item.label, item.paragraph_id) for item in material.label_bindings] == [
        ("N1", PARAGRAPH), ("N2", PARAGRAPH),
    ]
    body = "АР. " + PDF_QUOTE + "."
    layer = TextLayer("ver_fixture", "NFC", (Page(1, 0, len(body), body),), body)
    proposed = {
        "category": "evacuation", "finding_text": "Проход уже нормы",
        "recommendation_text": "Проверить ширину", "proposed_severity": "operational",
        "evidence": [{"page_number": 1, "quote": PDF_QUOTE}],
        "norm_citations": [{"label": "N2", "quote": QUOTE}],
        "required_value": "1,4 м", "stated_value": "1,2 м",
    }
    parsed = parse_response(json.dumps({"observations": [proposed]}, ensure_ascii=False),
                            truncated=False)
    result = ground_v3_proposals(
        parsed, layer, paragraphs=material.paragraphs,
        label_bindings=material.label_bindings,
    )
    assert result.rejected == ()
    assert result.accepted[0].norm_citations[0].paragraph_id == PARAGRAPH


def test_actual_set_builder_bytes_roundtrip_to_grounding_inputs():
    mapping = canonical_json_bytes({
        "reviewed_content_key": "reviewed-key", "norms_snapshot_id": SNAPSHOT,
        "embedding_build": "bge-m3-dense-v1", "mapped_document_ids": [DOCUMENT],
        "items": [{"id": "item_a"}, {"id": "item_b"}],
    })
    map_sha = hashlib.sha256(mapping).hexdigest()
    paragraph = RetrievalParagraph(
        DOCUMENT, PARAGRAPH, "СП 54", "Жилые здания", 0, "7.1.4", "7", QUOTE,
    )
    digest = hashlib.sha256(QUOTE.encode()).hexdigest()
    rows = tuple(PromptRow(
        item, f"N{ordinal}", DOCUMENT, PARAGRAPH, "СП 54", "Жилые здания",
        0, "7.1.4", "7", QUOTE, digest,
    ) for ordinal, item in enumerate(("item_a", "item_b"), 1))
    part = _bytes({
        "builder_version": "norm-ranking-prep-v1",
        "paragraphs": [dict(_payload()["rebinding_paragraphs"][0],
                            item_id=row.item_id, label=row.label) for row in rows],
    }).decode()
    blob = build_retrieval_set(
        identity=SetIdentity(map_sha, SNAPSHOT, "reviewed-key", "bge-m3-dense-v1"),
        map_bytes=mapping,
        snapshot=SnapshotBinding(SNAPSHOT, "reviewed-key", "b" * 64,
                                 "bge-m3-dense-v1", 1),
        selection=PromptSelection(rows, part, 0, True),
        paragraphs=(SourceParagraph(paragraph, digest),),
    )
    material = parse_v3_set_input(
        blob.data, expected_sha256=blob.sha256, expected_snapshot_id=SNAPSHOT,
        expected_map_sha256=map_sha,
    )
    assert material.prompt_part == part
    assert [item.label for item in material.label_bindings] == ["N1", "N2"]


@pytest.mark.parametrize("mutation", [
    "wrong_label", "altered_prompt_text", "altered_full_digest",
    "foreign_map", "foreign_snapshot", "wrong_part_length", "non_nfc",
    "duplicate_item_paragraph", "oversized_part",
])
def test_inconsistent_or_foreign_set_refuses(mutation):
    payload = deepcopy(_payload())
    if mutation == "wrong_label":
        _change_selected(payload, "label", "N9")
    elif mutation == "altered_prompt_text":
        _change_selected(payload, "text", "Другая нормативная фраза")
    elif mutation == "altered_full_digest":
        payload["rebinding_paragraphs"][0]["text_sha256"] = "c" * 64
    elif mutation == "foreign_map":
        payload["identity"]["map_sha256"] = "c" * 64
    elif mutation == "foreign_snapshot":
        payload["identity"]["norms_snapshot_id"] = "ns_01K7F4N2A9R8T6V5W3X2Y1Z0QM"
    elif mutation == "wrong_part_length":
        payload["prompt_part_characters"] -= 1
    elif mutation == "non_nfc":
        payload["rebinding_paragraphs"][0]["title"] = "е\u0301таж"
    elif mutation == "duplicate_item_paragraph":
        prompt = json.loads(payload["prompt_part"])
        prompt["paragraphs"][1]["item_id"] = "item_a"
        payload["prompt_part"] = _bytes(prompt).decode()
        payload["prompt_part_characters"] = len(payload["prompt_part"])
    elif mutation == "oversized_part":
        long_text = "Н" * 22_001
        payload["rebinding_paragraphs"][0]["text"] = long_text
        payload["rebinding_paragraphs"][0]["text_sha256"] = hashlib.sha256(
            long_text.encode()).hexdigest()
        prompt = json.loads(payload["prompt_part"])
        for row in prompt["paragraphs"]:
            row["text"] = long_text
            row["text_sha256"] = payload["rebinding_paragraphs"][0]["text_sha256"]
        payload["prompt_part"] = _bytes(prompt).decode()
        payload["prompt_part_characters"] = len(payload["prompt_part"])
    with pytest.raises(V3SetInputRefused):
        _parse(payload)


def test_duplicate_json_keys_and_noncanonical_bytes_refuse():
    raw = _bytes(_payload())
    for candidate in (b'{"builder_version":1,"builder_version":2}', raw + b" "):
        with pytest.raises(V3SetInputRefused):
            parse_v3_set_input(
                candidate, expected_sha256=hashlib.sha256(candidate).hexdigest(),
                expected_snapshot_id=SNAPSHOT, expected_map_sha256=MAP_SHA,
            )


def test_mismatched_blob_digest_refuses_before_json_parse():
    with pytest.raises(V3SetInputRefused, match="set_input_identity_invalid"):
        parse_v3_set_input(
            _bytes(_payload()), expected_sha256="0" * 64,
            expected_snapshot_id=SNAPSHOT, expected_map_sha256=MAP_SHA,
        )


def test_duplicate_canonical_ordinal_refuses_even_with_distinct_paragraph_ids():
    payload = _payload()
    second = dict(payload["rebinding_paragraphs"][0])
    second["norm_paragraph_id"] = "npar_01K7F4N2A9R8T6V5W3X2Y1Z0QM"
    payload["rebinding_paragraphs"].append(second)
    with pytest.raises(V3SetInputRefused, match="rebinding_row_invalid"):
        _parse(payload)
