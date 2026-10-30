"""Conservative coverage, content-bound carryover and real export readers."""

import io
import zipfile
from xml.etree import ElementTree

import pytest
from pypdf import PdfReader

from auditmanager.comparison.stage_review.cards import carryover_match, prepare_cards
from auditmanager.comparison.stage_review.writers import render_html, render_pdf, render_xlsx
from auditmanager.shared.errors import DomainError


def _source(before="Нагрузка 10 кВт", after="Нагрузка 20 кВт"):
    return {"kind": "TEXT", "before": before, "after": after, "parts": [
        {"side": "left", "profile_id": "left", "content_key": before,
         "box_anchor": {"x0": 1.0, "top": 2.0, "x1": 3.0, "bottom": 4.0}},
        {"side": "right", "profile_id": "right", "content_key": after, "box_anchor": {}}]}


def _classification(ids, class_name="PROJECT_CHANGE"):
    return {"classification_id": "classification", "cards": [{
        "class_name": class_name, "category": "electrical_load", "system": "electrical",
        "title": "Нагрузка 10 → 20 кВт", "evidence_ids": ids}]}


def test_no_ai_and_uncovered_evidence_remain_review_without_absence_claim():
    sources = {"std_a": _source(), "std_b": _source("", "Добавленная строка")}
    raw = prepare_cards(sources, [])
    assert len(raw) == 2 and {c["class_name"] for c in raw} == {"REVIEW"}
    classified = prepare_cards(sources, [_classification(["std_a"])])
    assert {c["class_name"] for c in classified} == {"PROJECT_CHANGE", "REVIEW"}
    assert sum(len(c["evidence_ids"]) for c in classified) == 2


def test_digest_binds_source_and_anchors_but_not_model_class_or_revision_id():
    first = prepare_cards({"std_a": _source()}, [_classification(["std_a"])])[0]
    renamed = prepare_cards({"std_new": _source()}, [_classification(["std_new"], "REVIEW")])[0]
    assert first["card_key"] != renamed["card_key"]
    assert first["evidence_digest"] == renamed["evidence_digest"]
    changed = prepare_cards({"std_a": _source(after="Нагрузка 30 кВт")}, [])[0]
    assert changed["evidence_digest"] != first["evidence_digest"]


@pytest.mark.parametrize("answers", [
    [_classification(["std_unknown"])],
    [_classification(["std_a"]), _classification(["std_a"])],
    [_classification(["std_a", "std_a"])],
])
def test_stored_classification_cannot_drop_reuse_or_invent_evidence(answers):
    with pytest.raises(DomainError):
        prepare_cards({"std_a": _source()}, answers)


def test_only_unanimous_exact_digest_carries_an_expert_act():
    current = {"evidence_digest": "current", "evidence_ids": ["a", "b"]}
    exact = current | {"decision": "accepted"}
    assert carryover_match(current, [exact])[0] == "full"
    assert carryover_match(current, [exact, exact | {"decision": "rejected"}])[0] == "stale"
    assert carryover_match(current, [exact | {"evidence_digest": "changed"}])[0] == "stale"
    assert carryover_match(current, [exact | {"evidence_digest": "changed", "evidence_ids": ["a"]}])[0] == "partial"
    assert carryover_match(current | {"anchor_keys": ["location"]}, [exact | {
        "evidence_digest": "changed", "evidence_ids": ["new_id"], "anchor_keys": ["location"]}])[0] == "stale"


def _journal():
    return {"run_id": "run", "groups": [{"key": "group", "label": "Раздел ЭОМ", "rows": [{
        "class_name": "REVIEW", "category": "uncertain", "system": "unknown",
        "title": "Нагрузка <20> & кабель", "before": '=HYPERLINK("https://invalid")',
        "after": "<script>alert(1)</script>\nСтрока", "evidence_ids": ["std_a"],
        "verdict": {"decision": "accepted", "reason": "Проверено"}}]}],
        "accepted_count": 1, "ai_hidden_same_count": 2, "ai_service_count": 3, "stale": False}


def test_html_escapes_evidence_and_has_counts_and_provenance():
    result = render_html(_journal()).decode()
    assert "<script>" not in result and "&lt;script&gt;" in result
    assert "Принято: 1" in result and "AI SAME/MOVED: 2" in result
    assert "само по себе не доказывает" in result and "std_a" in result


def test_xlsx_is_deterministic_readable_and_formula_safe():
    data = render_xlsx(_journal())
    assert render_xlsx(_journal()) == data
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        assert archive.testzip() is None
        root = ElementTree.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        assert not root.findall(".//s:f", ns)
        values = [v.text for v in root.findall(".//s:t", ns)]
        assert '=HYPERLINK("https://invalid")' in values
        assert "<script>alert(1)</script>\nСтрока" in values


def test_pdf_has_extractable_cyrillic_evidence_and_deterministic_bytes():
    data = render_pdf(_journal())
    assert data == render_pdf(_journal())
    text = "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(data)).pages)
    assert "Журнал изменений" in text and "Проверено" in text and "std_a" in text
    assert "Нагрузка <20> & кабель" in text
