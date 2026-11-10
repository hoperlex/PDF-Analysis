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

from auditmanager.decision_memory.models import (
    CROP_CAP,
    SELECTION_RULE_BLOCK_CROP,
    SELECTION_RULE_PAGE_IMAGES,
    BlockEvidenceFact,
    CropRef,
    EvidenceItem,
)

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


def select_block_crops(
    block_evidence: Sequence[BlockEvidenceFact], records: Sequence[Mapping[str, Any]]
) -> tuple[CropRef, ...]:
    """Selection rule ``block_crop/1`` (`dm-capture/2`, `F8-PUBLISH`): the crop **of the block** the evidence names, at most :data:`CROP_CAP`.

    Where ``page_images/1`` guesses (the ledger does not link a text anchor to a block), a candidate finding names its blocks, so each evidence
    item takes the record of ``geometry.page_crops`` whose ``portal_block_id`` is its own **and whose ``sha256`` is the digest the evidence
    recorded**: a record that no longer matches is not taken (nothing is substituted), and an item with no matching record has no crop. A block is
    taken once; the evidence item that names it is the one the crop is recorded against. The record's own ``bbox_norm`` is the crop's box, and its
    portal description is cut at :data:`DESCRIPTION_MAX_CHARS` as in ``page_images/1``.
    """
    chosen: list[CropRef] = []
    taken: set[str] = set()
    for item in sorted(block_evidence, key=lambda candidate: candidate.ordinal):
        if item.portal_block_id in taken:
            continue
        record = next(
            (
                candidate
                for candidate in records
                if str(candidate["portal_block_id"]) == item.portal_block_id and str(candidate["sha256"]) == item.crop_sha256
            ),
            None,
        )
        if record is None:
            continue
        taken.add(item.portal_block_id)
        description = record.get("portal_description")
        chosen.append(
            CropRef(
                ordinal=len(chosen) + 1,
                evidence_ordinal=item.ordinal,
                selection_rule=SELECTION_RULE_BLOCK_CROP,
                page_number=int(record["page_number"]),
                bbox=tuple(float(value) for value in record["bbox_norm"]),  # type: ignore[arg-type]
                blob_id=str(record["blob_id"]),
                sha256=str(record["sha256"]),
                size_bytes=int(record["size_bytes"]),
                width_px=int(record["width_px"]),
                height_px=int(record["height_px"]),
                source_ref=item.portal_block_id,
                portal_description=(str(description)[:DESCRIPTION_MAX_CHARS] or None) if description else None,
            )
        )
        if len(chosen) == CROP_CAP:
            break
    return tuple(chosen)


def select_case_crops(
    evidence: Sequence[EvidenceItem],
    block_evidence: Sequence[BlockEvidenceFact],
    records: Sequence[Mapping[str, Any]],
) -> tuple[CropRef, ...]:
    """The crops a case references: ``block_crop/1`` for a case whose evidence is blocks (``dm-capture/2``), ``page_images/1`` for every other."""
    if block_evidence:
        return select_block_crops(block_evidence, records)
    return select_page_image_crops(evidence, records)
