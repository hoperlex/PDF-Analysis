"""Which crop images a case references: selection rule ``page_images/1`` (`Q6`, `DECISION-MEMORY-01` section 3.5).

A pure function over plain values, so the rule is testable without a database. The ledger does not link an evidence item to a portal
block (`P6`), so the rule is a heuristic and says so: for each evidence item in order, the IMAGE-block crops the version's portal
geometry has on the page the item names, in manifest order, until the case holds :data:`CROP_CAP` of them. There is **no geometric
test** against the evidence block's box (`D-392`) -- the two coordinate systems (points of the text layer, normalised portal
coordinates) are not joined yet -- which is why the rule is named, and the name is stored on every crop, so a better rule is
distinguishable later. A portal description longer than :data:`DESCRIPTION_MAX_CHARS` is cut at that length: the cut is the rule's,
stated here, not a silent loss.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final

from auditmanager.decision_memory.models import CROP_CAP, SELECTION_RULE_PAGE_IMAGES, CropRef, EvidenceItem

#: The width of ``decision_memory_crop.portal_description``.
DESCRIPTION_MAX_CHARS: Final[int] = 4000


def select_page_image_crops(
    evidence: Sequence[EvidenceItem], records: Sequence[Mapping[str, Any]]
) -> tuple[CropRef, ...]:
    """Pick at most :data:`CROP_CAP` crop records for the pages the evidence names.

    ``records`` are the crop records of ``geometry.page_crops`` (``portal_block_id``, ``page_number``, ``bbox_norm``, ``blob_id``,
    ``sha256``, ``size_bytes``, ``width_px``, ``height_px``), each optionally with ``portal_description``. A record is taken once; the
    evidence item that first named its page is the one it is recorded against.
    """
    chosen: list[CropRef] = []
    taken: set[str] = set()
    for item in sorted(evidence, key=lambda candidate: candidate.ordinal):
        for record in records:
            block = str(record["portal_block_id"])
            if int(record["page_number"]) != item.page_number or block in taken:
                continue
            taken.add(block)
            description = record.get("portal_description")
            chosen.append(
                CropRef(
                    ordinal=len(chosen) + 1,
                    evidence_ordinal=item.ordinal,
                    selection_rule=SELECTION_RULE_PAGE_IMAGES,
                    page_number=item.page_number,
                    bbox=tuple(float(value) for value in record["bbox_norm"]),  # type: ignore[arg-type]
                    blob_id=str(record["blob_id"]),
                    sha256=str(record["sha256"]),
                    size_bytes=int(record["size_bytes"]),
                    width_px=int(record["width_px"]),
                    height_px=int(record["height_px"]),
                    source_ref=block,
                    portal_description=(str(description)[:DESCRIPTION_MAX_CHARS] or None) if description else None,
                )
            )
            if len(chosen) == CROP_CAP:
                return tuple(chosen)
    return tuple(chosen)
