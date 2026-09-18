"""The ``Project`` view the ports produce, and the bytes it renders as.

The *validation* of ``CreateProjectRequest`` moved to
:class:`auditmanager.api.schemas.models.CreateProjectRequest` under `T-1`: one closed
Pydantic model that both refuses an undeclared property and puts the schema in the served
document. The hand-written parser this module used to carry was the second copy, and a
second copy of a contract is a second thing to be wrong.

:class:`ProjectView` stays, and stays exactly as it was: it is the declared return type of
``ProjectPort.create_project`` and it is constructed by ``bootstrap/adapters.py``, which is
not this session's to change.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

from auditmanager.api.schemas.common import timestamp

__all__ = ["ProjectView", "project_body"]

#: ``#/components/schemas/CreateProjectRequest.properties.name``. The bound is enforced by
#: :class:`auditmanager.api.schemas.models.CreateProjectRequest`, which is also what puts it
#: in the served document; this is the same number, named, for a reader of this module.
MAX_PROJECT_NAME = 200


@dataclass(frozen=True, slots=True)
class ProjectView:
    """Exactly the frozen ``Project`` shape.

    ``document_count`` is optional in the document, so a producer that does not count
    documents leaves it ``None`` and the field is omitted rather than sent as a wrong
    zero. Omitting an optional field is valid; sending a fabricated one is not.

    Under owner ruling `R-10` the ``listProjects`` producer **does** count, in the same
    statement that reads the row, so every item of a project page carries the field and a
    project with no documents carries ``0``. ``create_project`` still reads no documents
    and still claims no count, and its response is unchanged. The ``None`` here is
    therefore no longer "nobody has implemented this"; it is "this path genuinely did not
    count", which is the claim it was always meant to make.
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
