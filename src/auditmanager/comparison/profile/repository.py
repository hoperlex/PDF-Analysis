"""SQL of ``comparison_page_profile``: the only place that table is read or written.

`CMP-PROFILE-01`. Migration ``0038`` gives the table its guards: a profile row is **frozen** apart from
write-once blob references (``trg_comparison_page_profile_frozen_guard`` and ``_write_once``), a page
beyond the version's ``page_count`` is refused (``trg_comparison_page_profile_page``), and two unique
keys hold: ``(version, content_key)`` and ``(version, page, algo_version)``. So a row is **inserted once,
complete** -- the blobs already published and named in it -- and never updated; the insert is
``ON CONFLICT DO NOTHING`` so that two workers building one version do not fail each other, and a
caller that finds nothing inserted reads the row that is there.

The one delete is :meth:`PageProfileRepository.delete_failed`: a page that ended without a result
(``needs_review`` with reason ``RENDER_FAILED``) is **not evidence**, and an operator who has freed the
host of what stopped it may build it again; a profile that is ``ready`` or ``refused`` is never deleted
here, and a row that a later table already references is refused by that table's foreign key, not by
this code.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.comparison.profile.models import PageProfileRow
from auditmanager.shared.identity import ComparisonPageProfileId

__all__ = ["PageProfileRepository"]

_COLUMNS = (
    "comparison_page_profile_id, version_uid, page_number, content_key, algo_version, status, reason, "
    "profile, profile_blob_id, preview_blob_id, thumbnail_blob_id, created_at"
)
_SELECT_ONE = text(f"SELECT {_COLUMNS} FROM comparison_page_profile WHERE comparison_page_profile_id = :id")
_SELECT_PAGE = text(
    f"SELECT {_COLUMNS} FROM comparison_page_profile "
    "WHERE version_uid = :version_uid AND page_number = :page_number AND algo_version = :algo"
)
_LIST = text(
    f"SELECT {_COLUMNS} FROM comparison_page_profile "
    "WHERE version_uid = :version_uid AND algo_version = :algo AND page_number > :after "
    "ORDER BY page_number LIMIT :limit"
)
_EXISTING = text(
    "SELECT page_number, status, reason FROM comparison_page_profile "
    "WHERE version_uid = :version_uid AND algo_version = :algo"
)
_VERSION_EXISTS = text("SELECT 1 FROM document_version WHERE version_uid = :version_uid")
_INSERT = text(
    "INSERT INTO comparison_page_profile ("
    "comparison_page_profile_id, version_uid, page_number, content_key, algo_version, status, reason, "
    "profile, profile_blob_id, preview_blob_id, thumbnail_blob_id) VALUES ("
    ":id, :version_uid, :page_number, :content_key, :algo, :status, :reason, "
    "CAST(:summary AS jsonb), :profile_blob_id, :preview_blob_id, :thumbnail_blob_id) "
    "ON CONFLICT DO NOTHING RETURNING comparison_page_profile_id"
)
_DELETE_FAILED = text(
    "DELETE FROM comparison_page_profile WHERE version_uid = :version_uid AND algo_version = :algo "
    "AND status = 'needs_review' AND reason = 'RENDER_FAILED'"
)


def _row(row: Any) -> PageProfileRow:
    (profile_id, version_uid, page_number, content_key, algo, status, reason, summary,
     profile_blob, preview_blob, thumbnail_blob, created_at) = tuple(row)
    return PageProfileRow(
        page_profile_id=profile_id,
        version_uid=version_uid,
        page_number=int(page_number),
        content_key=content_key,
        algo_version=algo,
        status=status,
        reason=reason,
        summary=summary if isinstance(summary, dict) else json.loads(summary),
        profile_blob_id=profile_blob,
        preview_blob_id=preview_blob,
        thumbnail_blob_id=thumbnail_blob,
        created_at=created_at,
    )


class PageProfileRepository:
    def version_exists(self, session: Session, version_uid: str) -> bool:
        return session.execute(_VERSION_EXISTS, {"version_uid": version_uid}).first() is not None

    def get(self, session: Session, page_profile_id: str) -> PageProfileRow | None:
        row = session.execute(_SELECT_ONE, {"id": page_profile_id}).first()
        return None if row is None else _row(row)

    def get_for_page(
        self, session: Session, version_uid: str, page_number: int, algo_version: str
    ) -> PageProfileRow | None:
        row = session.execute(
            _SELECT_PAGE, {"version_uid": version_uid, "page_number": page_number, "algo": algo_version}
        ).first()
        return None if row is None else _row(row)

    def list_after(
        self, session: Session, version_uid: str, algo_version: str, *, after_page: int, limit: int
    ) -> list[PageProfileRow]:
        rows = session.execute(
            _LIST,
            {"version_uid": version_uid, "algo": algo_version, "after": after_page, "limit": limit},
        ).all()
        return [_row(row) for row in rows]

    def existing(self, session: Session, version_uid: str, algo_version: str) -> dict[int, tuple[str, str | None]]:
        """``{page_number: (status, reason)}`` of the rows of one algorithm version."""
        rows = session.execute(_EXISTING, {"version_uid": version_uid, "algo": algo_version}).all()
        return {int(page): (status, reason) for page, status, reason in (tuple(r) for r in rows)}

    def insert(
        self,
        session: Session,
        *,
        version_uid: str,
        page_number: int,
        content_key: str,
        algo_version: str,
        status: str,
        reason: str | None,
        summary: dict[str, Any],
        profile_blob_id: str | None,
        preview_blob_id: str | None,
        thumbnail_blob_id: str | None,
    ) -> str | None:
        """Insert one complete row; its new identity, or ``None`` when the page already has one."""
        new_id = str(ComparisonPageProfileId.new())
        inserted = session.execute(
            _INSERT,
            {
                "id": new_id,
                "version_uid": version_uid,
                "page_number": page_number,
                "content_key": content_key,
                "algo": algo_version,
                "status": status,
                "reason": reason,
                "summary": json.dumps(summary, ensure_ascii=False, separators=(",", ":")),
                "profile_blob_id": profile_blob_id,
                "preview_blob_id": preview_blob_id,
                "thumbnail_blob_id": thumbnail_blob_id,
            },
        ).first()
        return None if inserted is None else str(tuple(inserted)[0])

    def delete_failed(self, session: Session, version_uid: str, algo_version: str) -> int:
        """Remove the rows of pages that ended without a result; the count removed."""
        return int(session.execute(_DELETE_FAILED, {"version_uid": version_uid, "algo": algo_version}).rowcount)
