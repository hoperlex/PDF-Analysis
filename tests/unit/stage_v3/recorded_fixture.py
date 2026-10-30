"""Source-bound synthetic V3 answers for local tests/helpers; never a model claim.

No I/O or network. The caller must label this synthetic/recorded. Unknown schemas
are refused. Original procedure validators still validate these answers.
"""
from __future__ import annotations
import json
import re
from auditmanager.analysis.public import ModelResponse


def synthetic_response(request):
    payload = json.loads(request.body["messages"][-1]["content"].split("\nINPUT\n", 1)[1])
    procedure = payload["_experimental_procedure"]
    pair = payload["pair"]
    if procedure == "mapper":
        pages = payload["pages"]
        answer = {"pair": pair, "regions": [{
            "region_id": "R001", "old_pages": [p["physical_page"] for p in pages if p["side"] == "OLD"],
            "new_pages": [p["physical_page"] for p in pages if p["side"] == "NEW"],
            "engineering_domain": "Синтетический пример", "scope": "Синтетическая native TEXT область",
            "locations": [], "reason_for_correspondence": "Тестовый ответ, не инженерное заключение.",
            "important_text_blocks": [], "important_table_blocks": [], "important_graphic_blocks": [], "confidence": 0.5,
        }], "unmatched_old": [], "unmatched_new": [], "coverage_notes": ["Синтетический тестовый ответ."]}
    elif procedure in {"miner", "unmatched"}:
        pages = payload["pages"]
        old = next(p for p in pages if p["side"] == "OLD")
        new = next(p for p in pages if p["side"] == "NEW")

        def evidence(page):
            block = page["blocks"][0]
            return {"side": page["side"], "source_pdf": page["source_pdf"],
                "physical_page": page["physical_page"], "block_id": block["block_id"], "block_type": "TEXT",
                "bbox": block["bbox"], "crop_ref": "", "relevant_fragment": block["structured_md"],
                "evidence_role": "Синтетическое исходное свидетельство"}

        before, after = old["blocks"][0]["structured_md"], new["blocks"][0]["structured_md"]
        numbers = [re.findall(r"\d+(?:[.,]\d+)?", text) for text in (before, after)]
        parameters = ([{"name": "Синтетический параметр", "old_value": numbers[0][0],
                        "new_value": numbers[1][0], "unit": "", "location": "Исходные строки"}]
                      if all(numbers) else [])
        answer = {"pair": pair, "region_id": payload["region"]["region_id"], "projectchanges": [{
            "projectchange_id": "SYNTHETIC_PC1", "engineering_subject": "Синтетический объект",
            "scope": "Проверка программного пути", "locations": [],
            "change_summary": "Синтетический ответ требует проверки", "old_state": before, "new_state": after,
            "changed_parameters": parameters, "old_pages": [old["physical_page"]], "new_pages": [new["physical_page"]],
            "evidence_items": [evidence(old), evidence(new)], "modalities": ["TEXT"],
            "confidence": 0.5, "why_one_event": "Синтетический ответ, не инженерное заключение.",
        }], "unresolved_hints": [], "coverage_notes": ["Синтетический тестовый ответ."]}
        if procedure == "unmatched":
            # Explicitly address each primary source page, rather than pretending
            # the one synthetic event analysed all unmatched content.
            answer["unresolved_hints"] = [{"hint_id": f"H{i}", "kind": "UNRESOLVED_HINT",
                "engineering_subject": "Непарная тестовая страница", "suspected_change": "Требуется проверка",
                "old_pages": [page["physical_page"]] if page["side"] == "OLD" else [],
                "new_pages": [page["physical_page"]] if page["side"] == "NEW" else [],
                "evidence_items": [evidence(page)], "missing_proof_or_conflict": "Синтетический тест не делает вывода.",
            } for i, page in enumerate(pages) if (page["side"], page["physical_page"]) in
                [tuple(k) for k in payload["_validation"]["batch"]["primary_keys"]]]
    elif procedure == "dedupe":
        answer = {"pair": pair, "decisions": [{"decision": "KEEP_SEPARATE",
            "projectchange_ids": [row["projectchange_id"]], "reason": "Синтетический тестовый ответ."}
            for row in payload["projectchanges"]], "notes": []}
    elif procedure == "verify":
        answer = {"pair": pair, "results": [{"work_item_id": item["work_item_id"], "verdict": "CONFIRMED",
            "old_value": item["parameter"]["old_value"], "new_value": item["parameter"]["new_value"],
            "unit": item["parameter"]["unit"], "explanation": "Синтетический ответ, не инженерное заключение.",
            "evidence_refs": [{k: source[k] for k in ("side", "physical_page", "block_id")} for source in item["sources"]],
        } for item in payload["items"]]}
    else:
        raise ValueError("unsupported synthetic V3 procedure; no fallback")
    return ModelResponse(output_text=json.dumps(answer, ensure_ascii=False), stop_reason="end_turn",
                         input_tokens=100, output_tokens=100, latency_ms=1), payload
