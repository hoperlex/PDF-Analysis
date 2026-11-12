"""Focused custody, distant-context, linked-group and substantive-pass regressions."""
from copy import deepcopy
from hashlib import sha256
import json

import pytest

from auditmanager.analysis.extended.consolidation import consolidate_observations
from auditmanager.analysis.extended.input_passport import build_input_passport, verify_passport_crop
from auditmanager.analysis.extended.related_context import build_related_index, select_related_context
from auditmanager.analysis.extended.substantive_review import parse_substantive_reply, review_schema
from auditmanager.analysis.extended.v2_quality import quality_policy, validate_quality_policy


def test_passport_freezes_bytes_and_register_uncertainty_without_inventing_absence():
    raw = b"unchanged crop"
    source = {"source_id": "s1", "kind": "image", "page_number": 2, "blob_id": "blob_1",
        "bbox_norm": [0, 0, 1, 1], "size_bytes": len(raw), "crop_sha256": sha256(raw).hexdigest()}
    pages = [{"page_number": 1, "text": "Ведомость рабочих чертежей\n1 | Схема ВРУ\n2 | Спецификация\n3 | см. том 2"},
             {"page_number": 2, "text": "Лист 1\nВРУ-К 294 кВт"}, {"page_number": 3, "text": ""}]
    passport = build_input_passport(version_uid="ver", pdf_sha256="a" * 64, page_count=3, pages=pages, sources=[source])
    assert passport["pdf_sha256"] == "a" * 64
    assert [entry["status"] for entry in passport["sheet_register"]["entries"]] == ["found", "unresolved", "external"]
    assert passport["sheet_register"]["absence_proved"] is False
    before = deepcopy(passport["crops"])
    verify_passport_crop(passport, source, raw)
    assert passport["crop_verification"] == "verified" and passport["crops"] == before
    with pytest.raises(ValueError, match="crop_digest"):
        verify_passport_crop(passport, source, b"different")


def test_passport_distinguishes_unrepresented_page_from_no_image_on_a_text_page():
    passport = build_input_passport(version_uid="v", pdf_sha256=None, page_count=3,
        pages=[{"page_number": 1, "text": "Текст"}, {"page_number": 2, "text": "Текст"}], sources=[])
    assert passport["unrepresented_pages"] == [3]
    assert passport["pdf_hash_status"] == "unavailable"
    assert passport["crop_verification"] == "not_required"
    assert passport["document_completeness_claimed"] is False


def test_distant_context_is_literal_and_object_bound_not_just_matching_numbers():
    pages = [{"page_number": 1, "text": "Схема ВРУ-К: установленная мощность 294 кВт"},
        {"page_number": 40, "text": "Спецификация ВРУ-К: расчётная мощность 336 кВт; кабель 5×35"},
        {"page_number": 50, "text": "Другой объект ЩРО20: 294 кВт, кабель 5×6"}]
    index = build_related_index(pages, version_uid="v")
    context = select_related_context(index, texts=[pages[0]["text"]], page_numbers={1})
    assert context["sources"][0]["page_number"] == 40
    assert {row["page_number"] for row in context["sources"]} == {1, 40}
    for row in context["sources"]:
        text = next(page["text"] for page in pages if page["page_number"] == row["page_number"])
        assert row["quote"] == text[row["character_start"]:row["character_end"]]
    omitted = select_related_context(index, texts=[pages[0]["text"]], page_numbers={1}, character_budget=1)
    assert omitted["complete"] is False and omitted["omitted_source_ids"]


def linked_inputs(relation="match"):
    rows = []
    for index in (1, 2):
        rows.append({"observation_id": f"o{index}", "title": f"Описание {index}", "description": f"Полное наблюдение {index}",
            "source_ids": ["s1"], "provenance": {"batch": "blocks:0", "ref": f"leg{index}:001", "relation": relation,
                "counterpart_refs": [f"leg{3-index}:001"]}})
    batches = [{"batch": "blocks:0", "relationships": [{"left_ref": "leg1:001", "right_ref": "leg2:001",
        "relation": relation, "extends": "right", "reason": "Один вопрос", "confidence": 0.9}]}]
    return rows, batches


@pytest.mark.parametrize("relation", ["match", "extension"])
def test_accepted_relationship_produces_one_group_without_changing_raw_records(relation):
    rows, batches = linked_inputs(relation)
    before = deepcopy(rows)
    result = consolidate_observations(rows, sources=[{"source_id": "s1", "kind": "image"}], version_uid="v", ensemble_batches=batches)
    assert result["consolidation"]["group_count"] == 1
    group, = result["consolidated_observations"]
    assert group["origin_count"] == 2 and [entry["observation_id"] for entry in group["origin_records"]] == ["o1", "o2"]
    assert [entry["description"] for entry in group["origin_records"]] == [row["description"] for row in rows]
    if relation == "extension":
        assert group["description"] == rows[1]["description"]
    assert rows == before


def test_disputed_even_identical_rows_have_distinct_group_identities():
    rows, batches = linked_inputs("disputed")
    rows[1].update(title=rows[0]["title"], description=rows[0]["description"])
    result = consolidate_observations(rows, sources=[{"source_id": "s1"}], version_uid="v", ensemble_batches=batches)
    assert result["consolidation"]["group_count"] == 2
    assert len({group["group_id"] for group in result["consolidated_observations"]}) == 2


@pytest.mark.parametrize("fault", ["foreign", "asymmetric", "other_batch"])
def test_relationships_cannot_group_unknown_or_unbound_origins(fault):
    rows, batches = linked_inputs()
    if fault == "foreign":
        rows[1]["source_ids"] = ["not_supplied"]
    elif fault == "asymmetric":
        rows[1]["provenance"]["counterpart_refs"] = []
    else:
        rows[1]["provenance"]["batch"] = "blocks:1"
    result = consolidate_observations(rows, sources=[{"source_id": "s1"}], version_uid="v", ensemble_batches=batches)
    assert result["consolidation"]["group_count"] == 2


def review_record(**changes):
    return {"input_id": "o1", "source_ids": ["s1"], "llm_decision": "accept", "human_taxonomy_reason": "other",
        "confidence": 0.9, "explanation": "Рассмотрено по источнику", "evidence_checked": True,
        "source_dependency": "enough_source", "needs_correction": False, "suggested_fix": "",
        "source_evidence": [{"source_id": "s1", "quote": "Реальная цитата"}], "visual_evidence": [],
        "substantive_checks": {key: {"checked": True, "explanation": "Проверено с учётом исходных условий"}
            for key in ("evidence", "alternatives", "materiality")}, **changes}


def parse(row, **changes):
    inputs = {"o1": {"source_ids": ["s1"], "evidence_source_ids": ["s1"], "context_complete": True, **changes}}
    return parse_substantive_reply(json.dumps({"reviews": [row]}), inputs=inputs,
        sources=[{"source_id": "s1", "quote": "Реальная цитата"}], attached_image_ids={"s1"})


def test_pass_requires_substantive_review_and_bound_evidence():
    assert parse(review_record())[0]["original_verdict"] == "pass"
    for key in ("evidence", "alternatives", "materiality"):
        row = review_record()
        row["substantive_checks"][key]["checked"] = False
        assert parse(row)[0]["llm_decision"] == "needs_human"
    assert parse(review_record(source_evidence=[]))[0]["original_verdict"] != "pass"
    assert parse(review_record(), context_complete=False)[0]["original_verdict"] != "pass"
    assert parse(review_record(), structural_checks={"original_verdict": "page_mismatch"})[0]["original_verdict"] != "pass"


@pytest.mark.parametrize("change", [{"source_ids": ["foreign"]},
    {"source_evidence": [{"source_id": "s1", "quote": "Выдуманная цитата"}]},
    {"visual_evidence": [{"source_id": "foreign", "explanation": "Модель утверждает, что видела"}]}])
def test_substantive_critic_refuses_forged_evidence(change):
    with pytest.raises(ValueError):
        parse(review_record(**change))


def test_changed_quality_code_requires_a_fresh_consent():
    policy = quality_policy()
    assert validate_quality_policy(policy)
    policy["bundle_sha256"] = "f" * 64
    assert validate_quality_policy(policy, compare_bundle=False)
    with pytest.raises(ValueError, match="requires_consent"):
        validate_quality_policy(policy)
