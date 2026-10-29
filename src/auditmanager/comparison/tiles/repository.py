"""SQL of the pair tile: one sheet pair and the result it points at. Read-only.

`CMP-VIEWER-01`. ``comparison_sheet_pair`` (``ctp_``) names the two page profiles of a transition's sheet pair and, once
compared, the content-keyed result (``csp_``) it uses; the result holds the status, the versioned ``result`` jsonb
(canvas, ``how_compared``, ``aligned_blocks``, the mask description) and the write-once mask blob. A result is shared by
pairs of equal content, so the tiles of a pair come from the **pair's own pages** and only the evidence from the result.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

__all__ = ["PairRow", "PairTileRepository", "ResultRow"]

_SELECT = text(
    "SELECT p.comparison_sheet_pair_id, p.state, p.status, p.page_a_profile_id, p.page_b_profile_id, p.result_id, "
    "r.status, r.mask_blob_id, r.result "
    "FROM comparison_sheet_pair p "
    "LEFT JOIN comparison_sheet_pair_result r ON r.comparison_sheet_pair_result_id = p.result_id "
    "WHERE p.comparison_sheet_pair_id = :pair_id"
)


@dataclass(frozen=True, slots=True)
class PairRow:
    sheet_pair_id: str
    state: str
    status: str | None
    page_a_profile_id: str | None
    page_b_profile_id: str | None
    result_id: str | None


@dataclass(frozen=True, slots=True)
class ResultRow:
    result_id: str
    status: str
    mask_blob_id: str | None
    result: dict[str, Any]


class PairTileRepository:
    def get(self, session: Session, pair_id: str) -> tuple[PairRow, ResultRow | None] | None:
        row = session.execute(_SELECT, {"pair_id": pair_id}).first()
        if row is None:
            return None
        (pair_id_, state, status, page_a, page_b, result_id, result_status, mask_blob, result) = tuple(row)
        pair = PairRow(pair_id_, state, status, page_a, page_b, result_id)
        if result_id is None:
            return pair, None
        document = result if isinstance(result, dict) else json.loads(result)
        return pair, ResultRow(result_id, result_status, mask_blob, document if isinstance(document, dict) else {})
