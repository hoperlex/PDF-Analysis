"""``Project``, ``ProjectPage`` and ``CreateProjectRequest``."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

from auditmanager.api.schemas.common import timestamp
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = ["ProjectView", "parse_create_project_request", "project_body"]

#: ``#/components/schemas/CreateProjectRequest.properties.name``.
MAX_PROJECT_NAME = 200


@dataclass(frozen=True, slots=True)
class ProjectView:
    """Exactly the frozen ``Project`` shape.

    ``document_count`` is optional in the document, so a producer that does not count
    documents leaves it ``None`` and the field is omitted rather than sent as a wrong
    zero. Omitting an optional field is valid; sending a fabricated one is not.
    """

    project_uid: str
    name: str
    created_at: datetime
    document_count: int | None = None


def project_body(view: ProjectView) -> dict[str, Any]:
    body: dict[str, Any] = {
        "project_uid": view.project_uid,
        "name": view.name,
        "created_at": timestamp(view.created_at),
    }
    if view.document_count is not None:
        body["document_count"] = view.document_count
    return body


def parse_create_project_request(payload: Mapping[str, Any]) -> str:
    """Validate ``CreateProjectRequest`` and return the project name.

    The schema is closed (``additionalProperties: false``), so an unknown property is
    refused here rather than dropped: a client that sent ``{"nmae": ...}`` has a bug,
    and silently creating a project called something else hides it.
    """
    if set(payload) - {"name"}:
        # The offending property name is **not** echoed. It is caller-controlled text,
        # and `details` values are not screened the way `message` is, so echoing one
        # would reflect whatever the caller sent -- a path, a URL -- straight back out
        # inside the envelope. `tests/integration/api/test_no_internal_identifiers.py`
        # found exactly that here.
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="The request body carries a property the schema does not declare.",
            field="body",
            constraint="additionalProperties",
        )
    name = payload.get("name")
    if not isinstance(name, str):
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="The project name is required and must be a string.",
            field="name",
            constraint="type",
        )
    if not 1 <= len(name) <= MAX_PROJECT_NAME:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message=f"The project name must be 1 to {MAX_PROJECT_NAME} characters.",
            field="name",
            constraint="length",
        )
    return name
