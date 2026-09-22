"""The process entry point, and the ASGI application it serves.

Importing this module builds nothing; calling :func:`create_app` does. An application that
is built has everything it needs -- ``build_application`` resolves settings, opens the
engine, constructs the store and the model adapter and only then assembles the router, so a
missing or misconfigured dependency fails at construction and not at first request. That is
the Gate C contract and `T-1` does not change it.

What `T-1` adds is :func:`create_asgi_app`, which wraps the built application in the FastAPI
app that actually serves HTTP, and :func:`create_documentation_app`, which builds the same
shape with nothing behind the ports so that the served document can be read without a
database.

**The health plane is not here.** ``api/health.py`` builds a separate application for a
separate port; see its module note for why it is not a route on this one.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import sys
from collections.abc import AsyncIterator
from typing import Any, Final, Mapping

from fastapi import Depends, FastAPI

from auditmanager.api.composition import Application, ConfigurationError, build_application
from auditmanager.api.routers import (
    BASE_PATH,
    CONTRACT_VERSION,
    BodyCapMiddleware,
    CorrelationMiddleware,
    FailureEnvelopeMiddleware,
    Router,
    build_router,
    declare_correlation_id,
    install_exception_handlers,
)
from auditmanager.api.security import build_authorization_dependency

_log = logging.getLogger(__name__)

__all__ = [
    "BASE_PATH",
    "CONTRACT_VERSION",
    "Application",
    "ConfigurationError",
    "create_app",
    "create_asgi_app",
    "create_documentation_app",
    "main",
]

#: ``info.title`` and ``info.description`` of the served document. Prose: the conformance
#: gate drops both under `N4`, and ``info.version`` is the one field in here that is not
#: prose -- it is :data:`CONTRACT_VERSION`, and the ``ErrorEnvelope.contract_version`` const
#: is the same string.
_TITLE: Final[str] = "AuditManager API"
_DESCRIPTION: Final[str] = (
    "The sixteen operations of the PC-01 surface. Every failure is one `ErrorEnvelope` "
    "carrying a catalog `error_code`, and every response carries `X-Correlation-Id`."
)

#: ``servers`` of the sealed document, verbatim. The paths are declared relative to
#: it rather than carrying it, so the document describes the same surface the contract does.
_SERVERS: Final[list[dict[str, str]]] = [
    {
        "url": BASE_PATH,
        "description": "Version-prefixed base path. A breaking change is a new contract "
        "version, never an edit here.",
    }
]

#: ``tags`` of the frozen document. Dropped by the conformance gate under `N4` -- an
#: operation's membership of a group is the operation's own ``tags``, which *is* compared.
_TAGS: Final[list[dict[str, str]]] = [
    {"name": "projects", "description": "Projects, and the documents published under them."},
    {"name": "documents", "description": "Published document versions and their bytes."},
    {"name": "runs", "description": "Audit runs over one published version."},
    {"name": "findings", "description": "Published, grounded findings of one run."},
    {"name": "decisions", "description": "The append-only expert decision ledger."},
    {"name": "export", "description": "The CSV export of one run."},
    # The contract declares this tag at its root and the served document omitted it, so
    # the exchange was grouped under no description at all. Conformance does not catch it:
    # it drops root `tags` as annotation. Found by `JUDGE-CLAIM` reading the served
    # document rather than the contract.
    {"name": "auth", "description": "Exchanging a login and a password for a credential."},
]


def create_app(environ: dict[str, str] | None = None) -> Application:
    """Build the application or raise. Never returns a half-wired one."""
    return build_application(environ=environ)


def create_asgi_app(
    environ: dict[str, str] | None = None,
    *,
    application: Application | None = None,
) -> FastAPI:
    """The ASGI application: the sixteen operations, the seam, and the four middlewares.

    ``application`` lets a caller that has already built one -- a test driving two
    applications in one process, for instance -- avoid building it twice. When it is omitted
    the composition root builds one from ``environ``.
    """
    resolved_environ: Mapping[str, str] = dict(os.environ) if environ is None else environ
    built = application if application is not None else create_app(dict(resolved_environ))
    return _assemble(built.router, resolved_environ, application=built)


def create_documentation_app(environ: Mapping[str, str] | None = None) -> FastAPI:
    """The same application shape, with nothing wired behind the six ports.

    The served document is a function of the fifteen declarations and the 46 models and not
    of what sits behind the ports, so this builds it without a database, an object store or
    a credential -- which is what lets the conformance gate read
    ``create_documentation_app().openapi()`` on any checkout. It **cannot serve a request**:
    every handler would call ``None``. ``test_the_documented_and_the_wired_app_agree`` is
    the assertion that keeps the two documents the same one.
    """
    router = build_router(
        projects=None,  # type: ignore[arg-type]
        documents=None,  # type: ignore[arg-type]
        runs=None,  # type: ignore[arg-type]
        findings=None,  # type: ignore[arg-type]
        decisions=None,  # type: ignore[arg-type]
        exports=None,  # type: ignore[arg-type]
    )
    return _assemble(router, environ if environ is not None else {}, application=None)


#: Exactly what FastAPI injects at ``fastapi/openapi/utils.py:522`` for an operation that
#: has parameters and declares no 422 of its own. Compared as a whole object, never by
#: status code: a 422 this application really declares is a different object and is kept.
_FASTAPIS_OWN_422: Final[dict[str, Any]] = {
    "description": "Validation Error",
    "content": {
        "application/json": {
            "schema": {"$ref": "#/components/schemas/HTTPValidationError"}
        }
    },
}


def _drop_the_422_this_surface_cannot_answer(document: dict[str, Any]) -> dict[str, Any]:
    """Remove FastAPI's injected ``422``, and the two schemas that only it referenced.

    **Why this is not document surgery, and how you can tell.** `W13-CONF` measured that
    FastAPI's own 422 must be *displaced, not deleted*: declaring the contract's own
    ``422: {"model": ErrorEnvelope, ...}`` replaces it and keeps ``HTTPValidationError`` and
    ``ValidationError`` out of ``components.schemas``. Eleven of the sixteen operations do
    exactly that. **Four cannot**, because the contract declares no ``422`` for them:
    ``getRunStatus``, ``getDocumentVersion``, ``getFinding`` and ``exportRunCsv``. FastAPI
    injects one anyway, for any operation with parameters, and there is no switch
    (``fastapi/openapi/utils.py:517-535`` -- the condition is on the *absence* of a declared
    422, ``4XX`` or ``default``).

    Those four take a path identity and the optional correlation header and nothing else.
    A malformed path identity is ``404 not_found`` by design -- the frozen ``NotFound``
    response says this surface "never reveals the existence of a resource the caller may not
    see" -- and the correlation header is declared but deliberately not enforced. **So a 422
    is unreachable on all four, and FastAPI's claim that they answer one is false.** What is
    removed here is a false statement about this application, not a difference from the
    contract, and the narrowness is what makes that checkable: an operation's 422 is removed
    only when the response object is byte-for-byte :data:`_FASTAPIS_OWN_422`, so a declared
    one is never touched. The two schemas go only if nothing still references them, and the
    function refuses rather than leave a dangling ``$ref``.
    """
    removed = 0
    for path_item in (document.get("paths") or {}).values():
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            responses = operation.get("responses") or {}
            if responses.get("422") == _FASTAPIS_OWN_422:
                del responses["422"]
                removed += 1
    if not removed:
        return document
    schemas = (document.get("components") or {}).get("schemas") or {}
    for name in ("HTTPValidationError", "ValidationError"):
        if name in schemas and f'"#/components/schemas/{name}"' in json.dumps(
            document.get("paths")
        ):  # pragma: no cover - refused below rather than shipped
            raise RuntimeError(
                f"{name} is still referenced by an operation; refusing to leave a "
                "dangling $ref in the served document"
            )
        schemas.pop(name, None)
    return document


class _ContractApplication(FastAPI):
    """A ``FastAPI`` whose document declares only what this surface can answer."""

    def openapi(self) -> dict[str, Any]:  # noqa: D102 - see the function above
        if self.openapi_schema is None:
            self.openapi_schema = _drop_the_422_this_surface_cannot_answer(super().openapi())
        return self.openapi_schema


def _run_lifespan(application: Application) -> Any:
    """`D-20`. What a *serving* process does before it answers and after it stops.

    **Startup: reconcile, then serve.** ``execute_run`` now commits ``running`` before the
    analysis begins (:mod:`auditmanager.runs.carrier`), so a process that is killed leaves
    that row behind and no ``except`` clause runs. ``OD-10``'s reconciler has existed since
    `B5` and had nothing to find, because the pre-`D-20` architecture never committed an
    intermediate state. This is the call that gives it something to do, and it happens
    **before the socket is bound**, so a client cannot read a stranded run from the
    previous process's crash and be told it is in flight.

    Why here and not in ``build_application``: constructing an ``Application`` is not
    starting a process. Suites build several per session, some while another's run is in
    flight, and ``STARTUP_THRESHOLD`` is ``0 seconds`` -- a reconciliation on every
    construction would terminate live runs. A lifespan runs when something *serves*.

    **Shutdown: stop accepting, do not wait.** PC-01 cannot resume, so a run interrupted
    by a shutdown is going to be ``failed`` whatever this does; the only question is
    whether it is marked now or at the next start. Marking it here would be a second
    implementation of the rule the reconciler already owns, and it would cover strictly
    fewer cases -- a ``SIGKILL`` reaches no shutdown hook at all. One mechanism, at
    startup, where it works for every way a process can end.
    """

    @contextlib.asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        from auditmanager.runs import reconcile_at_startup

        report = reconcile_at_startup(application.session_factory)
        if report.run_count or report.abandoned_count:
            _log.warning(
                "startup reconciliation: %d run(s) were left non-terminal by a previous "
                "process and are now failed; %d command record(s) abandoned",
                report.run_count,
                report.abandoned_count,
            )
        try:
            yield
        finally:
            application.carrier.shutdown()

    return lifespan


def _assemble(
    router: Router,
    environ: Mapping[str, str],
    *,
    application: Application | None = None,
) -> FastAPI:
    """One router, one environment, one served application.

    ``application`` is ``None`` for :func:`create_documentation_app`, which has nothing
    behind its six ports: it must not reconcile, because there is no database to reconcile
    against, and it cannot serve a request anyway.
    """
    app = _ContractApplication(
        title=_TITLE,
        description=_DESCRIPTION,
        version=CONTRACT_VERSION,
        servers=list(_SERVERS),
        openapi_tags=list(_TAGS),
        # A model with a default would otherwise be emitted twice, as `X-Input` and
        # `X-Output`. The 48 schema names are pinned by the contract and by the frontend's
        # generated client, so the split is a conformance failure -- and the fix belongs
        # here, in the application, never in the gate's normalization. `W13-CONF` measured
        # it: `test_the_gate_catches_a_split_input_and_output_schema`.
        separate_input_output_schemas=False,
        **(
            {}
            if application is None
            else {"lifespan": _run_lifespan(application)}
        ),
    )
    if application is not None:
        # `D-20`. The carrier, reachable from the served application. A caller holding the
        # ASGI app -- a test, the acceptance driver -- can then wait for a run on the real
        # completion of the real work instead of on a duration somebody guessed.
        app.state.run_carrier = application.carrier
    install_exception_handlers(app)
    app.include_router(
        router,
        dependencies=[
            Depends(declare_correlation_id),
            build_authorization_dependency(environ),
        ],
    )
    # Outermost first. `add_middleware` puts the last one added on the outside, so the
    # order below is the reverse of the order a request meets them:
    #   CorrelationMiddleware -> FailureEnvelopeMiddleware -> BodyCapMiddleware -> routing.
    # The correlation id is resolved before anything can fail, so every envelope the two
    # inner layers build can carry it; and the body cap runs before any parser
    # materialises a body.
    app.add_middleware(BodyCapMiddleware)
    app.add_middleware(FailureEnvelopeMiddleware)
    app.add_middleware(CorrelationMiddleware)
    return app


def main(argv: list[str] | None = None) -> int:
    """Construct everything and report what was wired, without serving.

    This entry point exists so an operator can ask "would this process start?" and get an
    answer that costs nothing and touches no request.
    """
    del argv
    try:
        app = create_app()
    except ConfigurationError as failure:
        print(f"auditmanager: refusing to start: {failure}", file=sys.stderr)
        return 2
    print(f"auditmanager: wired, provider_mode={app.settings.provider_mode}")
    print(f"auditmanager: operations={len(app.router.routes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
