"""Small helpers of the matrix integration tests: the calls an expert makes, and the rows they read back."""

from __future__ import annotations

from typing import Any

from auditmanager.comparison.public import MatrixEditInput, MatrixPageRef
from auditmanager.shared.identity import new_ulid

EXPERT = frozenset({"expert"})
LABEL = "Эксперт Т."


def key() -> str:
    return f"matrix-{new_ulid()}"


def page(version: str, number: int) -> MatrixPageRef:
    return MatrixPageRef(version, number)


def link(a: MatrixPageRef, b: MatrixPageRef) -> MatrixEditInput:
    return MatrixEditInput(kind="link", page=a, other_page=b)


def unlink(a: MatrixPageRef) -> MatrixEditInput:
    return MatrixEditInput(kind="unlink", page=a)


def absent(a: MatrixPageRef, version: str) -> MatrixEditInput:
    return MatrixEditInput(kind="mark_absent", page=a, absent_version_uid=version)


def apply(service: Any, doc: Any, matrix: dict[str, Any], edits: list[MatrixEditInput], user: str, *,
          idempotency_key: str | None = None, roles: frozenset[str] = EXPERT) -> dict[str, Any]:
    return service.apply_edits(
        project_uid=doc.project_uid, document_uid=doc.document_uid,
        base_matrix_id=matrix["revision"]["matrix_id"], base_edit_no=matrix["revision"]["edit_no"], edits=edits,
        user_uid=user, actor_label=LABEL, actor_roles=roles, idempotency_key=idempotency_key or key(),
    )


def undo(service: Any, doc: Any, matrix: dict[str, Any], user: str, *, roles: frozenset[str] = EXPERT) -> dict[str, Any]:
    return service.undo_edit(
        project_uid=doc.project_uid, document_uid=doc.document_uid,
        base_matrix_id=matrix["revision"]["matrix_id"], base_edit_no=matrix["revision"]["edit_no"],
        user_uid=user, actor_label=LABEL, actor_roles=roles, idempotency_key=key(),
    )


def get(service: Any, doc: Any) -> dict[str, Any]:
    return service.get_matrix(project_uid=doc.project_uid, document_uid=doc.document_uid)


def cell_of(matrix: dict[str, Any], doc: Any, version_index: int, number: int) -> tuple[dict[str, Any], dict[str, Any]]:
    """``(row, cell)`` holding page ``number`` of the version at ``version_index``."""
    for row in matrix["rows"]:
        cell = row["cells"][version_index]
        if cell["state"] == "matched" and cell["page"]["page_number"] == number:
            return row, cell
    raise AssertionError(f"no cell for page {number} of version {version_index}")


def edits_of(service: Any, doc: Any, limit: int = 100) -> list[dict[str, Any]]:
    return service.list_edits(project_uid=doc.project_uid, document_uid=doc.document_uid, before_edit_no=None, limit=limit).items
