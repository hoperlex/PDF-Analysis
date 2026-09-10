"""The twelve operations of ``contracts/api/v1/openapi.json``, and nothing else.

:func:`build_router` assembles the operation table from the six router modules. It
takes its dependencies as arguments and constructs none of them: choosing what sits
behind each port is the composition root's job (``api/composition.py``, owned by the
integrator in Gate C), and a factory that reached for a concrete implementation would
have taken that decision away from it.

``tests/integration/api`` asserts this table's ``(operationId, method, template)`` set
against the frozen document itself, so a thirteenth operation fails the suite and a
missing one cannot be overlooked.
"""

from __future__ import annotations

from typing import Final

from auditmanager.api.routers.correlation import (
    CORRELATION_HEADER,
    new_correlation_id,
    resolve_correlation_id,
)
from auditmanager.api.routers.decisions import build_decision_routes
from auditmanager.api.routers.documents import build_document_routes
from auditmanager.api.routers.errors import (
    dispatch,
    envelope_response,
    error_code_for,
    to_domain_error,
)
from auditmanager.api.routers.export import build_export_routes
from auditmanager.api.routers.findings import build_finding_routes
from auditmanager.api.routers.http import (
    Headers,
    Request,
    Response,
    Route,
    Router,
)
from auditmanager.api.routers.idempotency import (
    IDEMPOTENCY_HEADER,
    require_idempotency_key,
)
from auditmanager.api.routers.ports import (
    CsvExportPort,
    DecisionPort,
    DocumentPort,
    FindingPort,
    ProjectPort,
    RunPort,
)
from auditmanager.api.routers.projects import build_project_routes
from auditmanager.api.routers.runs import build_run_routes

__all__ = [
    "BASE_PATH",
    "CORRELATION_HEADER",
    "CONTRACT_VERSION",
    "IDEMPOTENCY_HEADER",
    "CsvExportPort",
    "DecisionPort",
    "DocumentPort",
    "FindingPort",
    "Headers",
    "ProjectPort",
    "Request",
    "Response",
    "Route",
    "Router",
    "RunPort",
    "build_router",
    "dispatch",
    "envelope_response",
    "error_code_for",
    "new_correlation_id",
    "require_idempotency_key",
    "resolve_correlation_id",
    "to_domain_error",
]

#: ``servers[0].url`` of the frozen document. A breaking change is a new contract
#: version, never an edit here. Stripping it from an inbound path is the composition
#: root's business; the routes below are relative to it.
BASE_PATH: Final[str] = "/api/v1"

#: ``info.version`` of the frozen document, and the ``ErrorEnvelope.contract_version``
#: const. The two are one value on purpose.
CONTRACT_VERSION: Final[str] = "1.0.0-draft.1"


def build_router(
    *,
    projects: ProjectPort,
    documents: DocumentPort,
    runs: RunPort,
    findings: FindingPort,
    decisions: DecisionPort,
    exports: CsvExportPort,
) -> Router:
    """Assemble the twelve operations.

    Keyword-only, because six same-shaped dependencies passed positionally is a wiring
    defect waiting to happen and the type checker cannot see it.
    """
    return Router(
        (
            *build_project_routes(projects),
            *build_document_routes(documents),
            *build_run_routes(runs),
            *build_finding_routes(findings),
            *build_decision_routes(decisions),
            *build_export_routes(exports),
        )
    )
