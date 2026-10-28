"""The records of the matrix as the rest of the package reads them: immutable, no database, no framework.

`CMP-MATRIX-01`. A *page* is the version it belongs to and its number inside that immutable version
(:class:`PageRef`); ``page_profile_id`` is the identity of its stored profile once there is one. A number alone,
a file name or a display label is never an identity (``AGENTS.md`` section 4).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Final

__all__ = [
    "AiLinkRecord",
    "BuildRecord",
    "EDIT_KINDS",
    "EditRecord",
    "PageRef",
    "SOURCE_EXPERT",
    "SOURCE_MIGRATED",
]

EDIT_KINDS: Final[tuple[str, ...]] = ("link", "unlink", "mark_absent", "undo")
SOURCE_EXPERT: Final[str] = "expert"
SOURCE_MIGRATED: Final[str] = "migrated_sheet_link"


@dataclass(frozen=True, slots=True)
class PageRef:
    """A page of a version: the version's identity and the page's number inside it."""

    version_uid: str
    page_number: int
    page_profile_id: str | None = None

    @property
    def key(self) -> tuple[str, int]:
        return (self.version_uid, self.page_number)

    def wire(self) -> dict[str, Any]:
        out: dict[str, Any] = {"version_uid": self.version_uid, "page_number": self.page_number}
        if self.page_profile_id is not None:
            out["page_profile_id"] = self.page_profile_id
        return out


@dataclass(frozen=True, slots=True)
class EditRecord:
    """One event of the append-only edit history (a row of ``comparison_matrix_edit``)."""

    edit_id: str
    edit_no: int
    kind: str
    source: str
    page: PageRef | None
    other_page: PageRef | None
    absent_version_uid: str | None
    undoes_edit_id: str | None
    order_id: str | None
    actor_user_uid: str
    decided_at: datetime
    provenance: dict[str, Any] = field(default_factory=dict)
    batch_position: int = 1


@dataclass(frozen=True, slots=True)
class BuildRecord:
    """One algorithmic build (a row of ``comparison_matrix``): immutable."""

    matrix_id: str
    build_no: int
    order_id: str | None
    profile_signature: str
    rules_version: str
    algo_version: str
    rows: list[dict[str, Any]]
    unassigned: list[dict[str, Any]]
    summary: dict[str, Any]
    created_at: datetime

    @property
    def order(self) -> list[str]:
        """The versions the build walked, oldest first."""
        return list(self.summary.get("order", []))


@dataclass(frozen=True, slots=True)
class AiLinkRecord:
    """An accepted AI link (a row of ``comparison_ai_link``): read here, written by wave C2."""

    ai_link_id: str
    document_uid: str
    matrix_id: str
    page: PageRef
    other_page: PageRef
    answered_state: str
    created_at: datetime
