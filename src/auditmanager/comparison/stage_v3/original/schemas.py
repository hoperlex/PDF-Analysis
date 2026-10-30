"""Pure schema excerpts from original contracts.py; see SOURCE.json."""

from __future__ import annotations

from typing import Any

def obj(**properties: Any) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }

S = {"type": "string"}

N = {"type": "number", "minimum": 0, "maximum": 1}

STRINGS = {"type": "array", "items": S}

PAGES = {"type": "array", "items": {"type": "integer", "minimum": 1}}

PAIR_ID = {"type": "string", "minLength": 1}

BLOCK_REF = obj(
    side={"type": "string", "enum": ["OLD", "NEW"]},
    physical_page={"type": "integer", "minimum": 1},
    block_id=S,
    block_type={"type": "string", "enum": ["TEXT", "TABLE", "GRAPHIC"]},
    relevance=S,
)

REGION = obj(
    region_id=S,
    old_pages=PAGES,
    new_pages=PAGES,
    engineering_domain=S,
    scope=S,
    locations=STRINGS,
    reason_for_correspondence=S,
    important_text_blocks={"type": "array", "items": BLOCK_REF},
    important_table_blocks={"type": "array", "items": BLOCK_REF},
    important_graphic_blocks={"type": "array", "items": BLOCK_REF},
    confidence=N,
)

MAP_SCHEMA = obj(
    pair=PAIR_ID,
    regions={"type": "array", "items": REGION},
    unmatched_old=PAGES,
    unmatched_new=PAGES,
    coverage_notes=STRINGS,
)

DETAIL = obj(name=S, old_value=S, new_value=S, unit=S, location=S)

EVIDENCE = obj(
    side={"type": "string", "enum": ["OLD", "NEW"]},
    source_pdf=S,
    physical_page={"type": "integer", "minimum": 1},
    block_id=S,
    block_type={"type": "string", "enum": ["TEXT", "TABLE", "GRAPHIC"]},
    bbox={"type": "array", "items": {"type": "number"}, "minItems": 4, "maxItems": 4},
    crop_ref=S,
    relevant_fragment=S,
    evidence_role=S,
)

PROJECTCHANGE = obj(
    projectchange_id=S,
    engineering_subject=S,
    scope=S,
    locations=STRINGS,
    change_summary=S,
    old_state=S,
    new_state=S,
    changed_parameters={"type": "array", "items": DETAIL},
    old_pages=PAGES,
    new_pages=PAGES,
    evidence_items={"type": "array", "items": EVIDENCE},
    modalities={
        "type": "array",
        "items": {"type": "string", "enum": ["TEXT", "TABLE", "GRAPHIC"]},
    },
    confidence=N,
    why_one_event=S,
)

HINT = obj(
    hint_id=S,
    kind={"type": "string", "enum": ["UNRESOLVED_HINT", "SOURCE_CONFLICT"]},
    engineering_subject=S,
    suspected_change=S,
    old_pages=PAGES,
    new_pages=PAGES,
    evidence_items={"type": "array", "items": EVIDENCE},
    missing_proof_or_conflict=S,
)

MINER_SCHEMA = obj(
    pair=PAIR_ID,
    region_id=S,
    projectchanges={"type": "array", "items": PROJECTCHANGE},
    unresolved_hints={"type": "array", "items": HINT},
    coverage_notes=STRINGS,
)

DEDUPE_ITEM = obj(
    decision={"type": "string", "enum": ["KEEP_SEPARATE", "MERGE_DUPLICATES"]},
    projectchange_ids=STRINGS,
    reason=S,
)

DEDUPE_SCHEMA = obj(
    pair=PAIR_ID,
    decisions={"type": "array", "items": DEDUPE_ITEM},
    notes=STRINGS,
)

VERIFICATION_RESULT = obj(
    work_item_id=S,
    verdict={"type": "string", "enum": ["CONFIRMED", "CORRECTED", "CONFLICT", "UNREADABLE"]},
    old_value=S,
    new_value=S,
    unit=S,
    explanation=S,
    evidence_refs={
        "type": "array",
        "items": obj(
            side={"type": "string", "enum": ["OLD", "NEW"]},
            physical_page={"type": "integer", "minimum": 1},
            block_id=S,
        ),
    },
)

VERIFICATION_SCHEMA = obj(
    pair=PAIR_ID,
    results={"type": "array", "items": VERIFICATION_RESULT},
)
