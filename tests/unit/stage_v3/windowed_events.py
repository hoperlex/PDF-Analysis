"""Hand-made Miner events and hints for the windowed tests that do not need a provider round trip."""
from __future__ import annotations


def event(identity, *, parameters=(), blocks=(), subject="Ширина прохода", summary="Изменена ширина прохода",
          old_pages=(1,), new_pages=(1,), **extra):
    """A Miner project change with every field the dedupe/ledger/consolidation code reads.

    `blocks` are block ids; each becomes one evidence item (the side is not material to these tests).
    `parameters` are `(old_value, new_value)` pairs.
    """
    row = {"projectchange_id": identity, "engineering_subject": subject, "scope": "Тест", "locations": [],
           "change_summary": summary, "old_state": "до", "new_state": "после",
           "changed_parameters": [{"name": "Параметр", "old_value": old, "new_value": new, "unit": "мм", "location": "Тест"}
                                  for old, new in parameters],
           "old_pages": list(old_pages), "new_pages": list(new_pages),
           "evidence_items": [{"side": "OLD", "source_pdf": "ver", "physical_page": 1, "block_id": block,
                               "block_type": "TEXT", "bbox": [1, 2, 3, 4], "crop_ref": "",
                               "relevant_fragment": "цитата " + block, "evidence_role": "тест"} for block in blocks],
           "modalities": ["TEXT"], "confidence": 0.5, "why_one_event": "тест"}
    row.update(extra)
    return row


def hint(identity, *, blocks=(), kind="UNRESOLVED_HINT", old_pages=(1,), new_pages=(1,)):
    return {"hint_id": identity, "kind": kind, "engineering_subject": "Тест", "suspected_change": "Тест",
            "old_pages": list(old_pages), "new_pages": list(new_pages),
            "evidence_items": [{"side": "OLD", "source_pdf": "ver", "physical_page": 1, "block_id": block,
                                "block_type": "TEXT", "bbox": [1, 2, 3, 4], "crop_ref": "",
                                "relevant_fragment": "цитата " + block, "evidence_role": "тест"} for block in blocks],
            "missing_proof_or_conflict": "Нет доказательства " + identity}


def miner_result(*events, hints=()):
    return {"pair": "pair-test", "region_id": "R", "projectchanges": list(events),
            "unresolved_hints": list(hints), "coverage_notes": []}
