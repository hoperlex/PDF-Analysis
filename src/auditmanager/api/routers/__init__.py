"""The sixteen operations of ``contracts/api/v1/openapi.json``, and nothing else.

:func:`build_router` assembles one ``APIRouter`` from the seven router modules. It takes its
dependencies as arguments and constructs none of them: choosing what sits behind each port
is the composition root's job (``api/composition.py``), and a factory that reached for a
concrete implementation would have taken that decision away from it.

``tests/contract/api_v1/test_openapi_conformance.py`` asserts the generated document's
``(operationId, method, path)`` set against the frozen document itself, so a thirteenth
operation fails the suite and a missing one cannot be overlooked. ``web/tests/contract/
openapi-drift.contract.test.ts`` counts them from the other side.

**The signature is still the one ``api/app.py`` already calls.** ``build_router`` took six
keyword-only ports before `T-1` and takes the same six now; `W34-API` added a seventh with a
default rather than a seventh argument, so the two call sites in that file -- which this
session does not own -- did not have to move. ``Router`` is still the name of what it
returns.
"""

from __future__ import annotations

from typing import Final

from fastapi import APIRouter

from auditmanager.api.routers.auth import build_auth_routes
from auditmanager.api.routers.correlation import (
    CORRELATION_HEADER,
    CorrelationMiddleware,
    current_correlation_id,
    new_correlation_id,
    resolve_correlation_id,
)
from auditmanager.api.routers.decisions import build_decision_routes
from auditmanager.api.routers.declarations import declare_correlation_id
from auditmanager.api.routers.documents import build_document_routes
from auditmanager.api.routers.errors import (
    METHOD_NOT_ALLOWED_CODE,
    envelope_response,
    error_code_for,
    guarded,
    to_domain_error,
)
from auditmanager.api.routers.export import build_export_routes
from auditmanager.api.routers.findings import build_finding_routes
from auditmanager.api.routers.handlers import (
    FailureEnvelopeMiddleware,
    install_exception_handlers,
)
from auditmanager.api.routers.idempotency import (
    IDEMPOTENCY_HEADER,
    require_idempotency_key,
)
from auditmanager.api.routers.multipart import MAX_BODY, BodyCapMiddleware
from auditmanager.api.routers.ports import (
    CredentialPort,
    CsvExportPort,
    DecisionPort,
    DocumentPort,
    FindingPort,
    ProjectPort,
    RunPort,
)
from auditmanager.api.routers.projects import build_project_routes
from auditmanager.api.routers.runs import build_run_routes
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response

#: What ``build_router`` returns. The name the composition root's type annotation uses.
Router = APIRouter

__all__ = [
    "BASE_PATH",
    "CONTRACT_VERSION",
    "CORRELATION_HEADER",
    "IDEMPOTENCY_HEADER",
    "MAX_BODY",
    "METHOD_NOT_ALLOWED_CODE",
    "BodyCapMiddleware",
    "CorrelationMiddleware",
    "CredentialPort",
    "CsvExportPort",
    "DecisionPort",
    "DocumentPort",
    "FailureEnvelopeMiddleware",
    "FindingPort",
    "ProjectPort",
    "Router",
    "RunPort",
    "WireResponse",
    "build_auth_routes",
    "build_router",
    "current_correlation_id",
    "declare_correlation_id",
    "encode_json",
    "envelope_response",
    "error_code_for",
    "guarded",
    "install_exception_handlers",
    "json_response",
    "new_correlation_id",
    "require_idempotency_key",
    "resolve_correlation_id",
    "to_domain_error",
]

#: ``servers[0].url`` of the frozen document. A breaking change is a new contract version,
#: never an edit here. The paths are declared **relative to it** and the prefix is
#: not pushed into them: `W13-CONF`'s ``test_a_changed_base_path_is_caught`` compares
#: ``servers``, and a document whose paths carried ``/api/v1`` would declare a different
#: surface from the one the contract does.
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
    credentials: CredentialPort | None = None,
) -> Router:
    """Assemble the sixteen operations.

    Keyword-only, because seven same-shaped dependencies passed positionally is a wiring
    defect waiting to happen and the type checker cannot see it.

    ``credentials`` has a default and the other six do not, for one reason that is not
    taste: ``api/app.py`` -- another session's file -- calls this with exactly the six it
    has called it with since `B6`, and ``create_documentation_app`` builds the served
    document with nothing behind any port at all. A seventh *required* argument would have
    made the credential exchange a change to that file. The exchange is therefore
    **declared** in every router and **answerable** only in one that was handed a port,
    which is the same bargain ``create_documentation_app`` already makes with the other six:
    the document is a function of the declarations, and serving a request is not.
    ``test_the_wired_application_can_answer_the_exchange`` is what says the composition root
    really hands one over.
    """
    router = APIRouter()
    # One router, registered onto directly, rather than six included into a seventh.
    # ``include_router`` wraps each sub-router instead of copying its routes, so
    # ``router.routes`` would carry seven opaque wrappers and the whole-surface
    # assertions -- the route count, the ``(operationId, method, path)`` set,
    # ``tests/integration/api/test_operation_surface.py`` -- could not see an operation at
    # all. A table nobody can enumerate is a table nobody can check.
    build_project_routes(router, projects)
    build_document_routes(router, documents)
    build_run_routes(router, runs)
    build_finding_routes(router, findings)
    build_decision_routes(router, decisions)
    build_export_routes(router, exports)
    build_auth_routes(router, credentials)  # type: ignore[arg-type]
    _refuse_a_duplicate_operation_id(router)
    return router


def _refuse_a_duplicate_operation_id(router: APIRouter) -> None:
    """Two routes may not share an ``operationId``.

    Not a defensive nicety, and not FastAPI's job either -- it logs a warning and carries
    on. An ``operationId`` is an operation's **identity**: the frozen document keys on it,
    the frontend's generated client names a function after it, and
    ``tests/integration/api/test_operation_surface.py`` compares the set. A duplicate makes
    the served document declare one id at two places, so a caller generating a client gets
    one of them and cannot address the other -- while ``len(router.routes) == 15`` still
    passes, which is exactly what that assertion cannot see.
    """
    seen: set[str] = set()
    for route in router.routes:
        operation_id = getattr(route, "operation_id", None)
        if operation_id is None:
            continue
        if operation_id in seen:
            raise ValueError(f"duplicate operationId {operation_id!r}")
        seen.add(operation_id)
