"""SQL of ``comparison_sheet_pair_result``: the only place that table is read or written by the engine.

`CMP-ENGINE-01`. Migration ``0039`` gives the table its guards: ``UNIQUE (project_uid, content_key)``; a row is frozen
apart from the write-once ``mask_blob_id`` (``trg_..._frozen_guard`` and ``_write_once``); a ``same`` result holds no
mask (``ck_..._same_has_no_mask``); both pages must be pages of the project (``am_check_comparison_sheet_pair_result``).
So a row is **inserted once, complete** -- with its mask blob already published and named in it -- and never updated;
the insert is ``ON CONFLICT (project_uid, content_key) DO NOTHING`` so that two workers computing one pair do not fail
each other, and the one that finds nothing inserted reads the row that is there.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from auditmanager.shared.identity import ComparisonSheetPairResultId

__all__ = ["PairResultRepository", "StoredResult"]

_COLUMNS = (
    "comparison_sheet_pair_result_id, project_uid, content_key, algo_version, status, reasons, channels, result, "
    "page_a_profile_id, page_b_profile_id, mask_blob_id"
)
_FIND = text(f"SELECT {_COLUMNS} FROM comparison_sheet_pair_result WHERE project_uid = :project AND content_key = :key")
_GET = text(f"SELECT {_COLUMNS} FROM comparison_sheet_pair_result WHERE comparison_sheet_pair_result_id = :id")
_INSERT = text(
    "INSERT INTO comparison_sheet_pair_result (comparison_sheet_pair_result_id, project_uid, content_key, algo_version, "
    "status, reasons, channels, result, page_a_profile_id, page_b_profile_id, mask_blob_id) VALUES ("
    ":id, :project, :key, :algo, :status, CAST(:reasons AS jsonb), CAST(:channels AS jsonb), CAST(:result AS jsonb), "
    ":page_a, :page_b, :mask) ON CONFLICT (project_uid, content_key) DO NOTHING "
    "RETURNING comparison_sheet_pair_result_id"
)
_OWNED = text(
    "SELECT p.comparison_page_profile_id FROM comparison_page_profile p "
    "JOIN document_version v ON v.version_uid = p.version_uid "
    "JOIN document d ON d.document_uid = v.document_uid "
    "WHERE d.project_uid = :project AND p.comparison_page_profile_id IN :ids"
).bindparams(bindparam("ids", expanding=True))


@dataclass(frozen=True, slots=True)
class StoredResult:
    result_id: str
    project_uid: str
    content_key: str
    algo_version: str
    status: str
    reasons: list[str]
    channels: dict[str, Any]
    result: dict[str, Any]
    page_a_profile_id: str
    page_b_profile_id: str
    mask_blob_id: str | None


def _json(value: Any) -> Any:
    return value if not isinstance(value, (str, bytes)) else json.loads(value)


def _stored(row: Any) -> StoredResult:
    (result_id, project, key, algo, status, reasons, channels, result, page_a, page_b, mask) = tuple(row)
    return StoredResult(result_id, project, key, algo, status, list(_json(reasons)), dict(_json(channels)),
                        dict(_json(result)), page_a, page_b, mask)


class PairResultRepository:
    def find(self, session: Session, project_uid: str, content_key: str) -> StoredResult | None:
        row = session.execute(_FIND, {"project": project_uid, "key": content_key}).first()
        return None if row is None else _stored(row)

    def get(self, session: Session, result_id: str) -> StoredResult | None:
        row = session.execute(_GET, {"id": result_id}).first()
        return None if row is None else _stored(row)

    def pages_of_project(self, session: Session, project_uid: str, page_ids: list[str]) -> set[str]:
        """Which of the page profiles belong to the project (through their version and document)."""
        rows = session.execute(_OWNED, {"project": project_uid, "ids": list(page_ids)}).all()
        return {tuple(r)[0] for r in rows}

    def insert(
        self,
        session: Session,
        *,
        project_uid: str,
        content_key: str,
        algo_version: str,
        status: str,
        reasons: list[str],
        channels: dict[str, Any],
        result: dict[str, Any],
        page_a_profile_id: str,
        page_b_profile_id: str,
        mask_blob_id: str | None,
    ) -> str | None:
        """The new identity, or ``None`` when another worker wrote this key first."""
        new_id = str(ComparisonSheetPairResultId.new())
        dump = {"separators": (",", ":"), "ensure_ascii": False}
        inserted = session.execute(
            _INSERT,
            {
                "id": new_id, "project": project_uid, "key": content_key, "algo": algo_version, "status": status,
                "reasons": json.dumps(reasons, **dump), "channels": json.dumps(channels, **dump),
                "result": json.dumps(result, **dump), "page_a": page_a_profile_id, "page_b": page_b_profile_id,
                "mask": mask_blob_id,
            },
        ).first()
        return None if inserted is None else str(tuple(inserted)[0])
