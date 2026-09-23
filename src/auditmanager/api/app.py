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

from fastapi import Depends, FastAPI, Request
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)
from fastapi.responses import HTMLResponse, JSONResponse

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
    "DOCUMENTATION_PATHS",
    "OPENAPI_PATH",
    "Application",
    "ConfigurationError",
    "create_app",
    "create_asgi_app",
    "create_documentation_app",
    "main",
]

#: Where this application serves its own description, and the three pages built from it.
#:
#: **They are declared here rather than left to FastAPI, and `R-31` is why.** ``setup()``
#: installs these four with ``self.add_route(...)`` -- Starlette's ``Router.add_route``,
#: which builds a plain ``starlette.routing.Route``. A ``Route`` has no dependant tree, so
#: **no** dependency reaches it: not one passed to ``include_router``, and not one passed to
#: the ``FastAPI`` constructor either. Measured on FastAPI 0.141.1 rather than reasoned
#: about, because the reasoned answer -- "move the argument up one level" -- produces four
#: routes that still answer ``200`` to a caller with no credential and a suite that stays
#: green. `D-73` is exactly that: every real operation answered ``401`` while the full
#: description of the surface, ``/auth/token``'s shape included, was on the doorstep.
#:
#: So the four built-in routes are suppressed (``openapi_url=None`` and the three below it
#: in :func:`_assemble`) and the same four routes are declared as ``APIRoute``s, which do
#: carry the application's dependencies. They stay out of the document --
#: ``include_in_schema=False`` -- because the contract declares fifteen paths and these are
#: not among them.
OPENAPI_PATH: Final[str] = "/openapi.json"
_DOCS_PATH: Final[str] = "/docs"
_REDOC_PATH: Final[str] = "/redoc"
_OAUTH2_REDIRECT_PATH: Final[str] = "/docs/oauth2-redirect"

#: The four, as one value a guard can read. `R-31` closed them together and they are
#: guarded together.
DOCUMENTATION_PATHS: Final[tuple[str, ...]] = (
    OPENAPI_PATH,
    _DOCS_PATH,
    _REDOC_PATH,
    _OAUTH2_REDIRECT_PATH,
)

#: ``info.title`` and ``info.description`` of the served document. Prose: the conformance
#: gate drops both under `N4`, and ``info.version`` is the one field in here that is not
#: prose -- it is :data:`CONTRACT_VERSION`, and the ``ErrorEnvelope.contract_version`` const
#: is the same string.
_TITLE: Final[str] = "AuditManager API"
_DESCRIPTION: Final[str] = (
    "The eighteen operations of the PC-01 surface. Every failure is one `ErrorEnvelope` "
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
    """The ASGI application: the eighteen operations, the seam, and the four middlewares.

    ``application`` lets a caller that has already built one -- a test driving two
    applications in one process, for instance -- avoid building it twice. When it is omitted
    the composition root builds one from ``environ``.
    """
    resolved_environ: Mapping[str, str] = dict(os.environ) if environ is None else environ
    built = application if application is not None else create_app(dict(resolved_environ))
    return _assemble(built.router, resolved_environ, application=built)


def create_documentation_app(environ: Mapping[str, str] | None = None) -> FastAPI:
    """The same application shape, with nothing wired behind the six ports.

    The served document is a function of the eighteen declarations and the 51 models and not
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
    ``ValidationError`` out of ``components.schemas``. **Fourteen** of the eighteen
    operations do exactly that -- measured from the contract, not recalled: this paragraph
    read *"Twelve of the seventeen"* until wave 39, and twelve plus the four below is
    sixteen, which was never the size of this surface. It was thirteen of seventeen before
    ``changePassword``, which declares its own 422 like every other operation with a body.
    **Four cannot**, because the contract declares no ``422`` for them:
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


def _declare_the_documentation_routes(app: FastAPI) -> None:
    """The four of :data:`DOCUMENTATION_PATHS`, as routes the seam can reach.

    **Nothing about what they serve is reimplemented.** The document comes from
    ``app.openapi()`` -- the same call the conformance gate reads -- and the three pages
    come from ``fastapi.openapi.docs``, which is where ``setup()`` gets them too. What
    changes is only the *kind* of route: an ``APIRoute``, which carries
    ``app.router.dependencies``, instead of a ``starlette.routing.Route``, which carries
    nothing.

    ``include_in_schema=False`` on all four. The contract declares fifteen paths and these
    are not among them; a documentation route that described itself would be a sixteenth.

    None of them declares an ``operation_id``, so
    :func:`auditmanager.api.security._operation_of` answers ``None`` for each, ``None`` is
    in no register, and the seam guards them under the rule it already states: an
    unreadable route is a closed route. **Nothing was added to
    ``UNAUTHENTICATED_OPERATIONS``**, which is still exactly ``{"issueToken"}`` -- the one
    door with a handle on the inside.
    """

    @app.get(OPENAPI_PATH, include_in_schema=False)
    def served_document(request: Request) -> JSONResponse:
        # The `root_path` rewrite is FastAPI's own, kept verbatim rather than dropped: this
        # deployment sets no `root_path` and the branch is unreachable today, but a
        # difference introduced here would be a difference nobody asked for and nobody
        # would find. `_SERVERS` already declares `/api/v1`, so the rewrite has nothing to
        # add even when it does fire.
        root_path = request.scope.get("root_path", "").rstrip("/")
        document = app.openapi()
        if root_path and app.root_path_in_servers:
            declared = {server.get("url") for server in document.get("servers", [])}
            if root_path not in declared:
                document = dict(document)
                document["servers"] = [{"url": root_path}, *document.get("servers", [])]
        return JSONResponse(document)

    @app.get(_DOCS_PATH, include_in_schema=False)
    def swagger_ui(request: Request) -> HTMLResponse:
        root_path = request.scope.get("root_path", "").rstrip("/")
        return get_swagger_ui_html(
            openapi_url=root_path + OPENAPI_PATH,
            title=f"{app.title} - Swagger UI",
            oauth2_redirect_url=root_path + _OAUTH2_REDIRECT_PATH,
        )

    @app.get(_OAUTH2_REDIRECT_PATH, include_in_schema=False)
    def swagger_ui_redirect() -> HTMLResponse:
        return get_swagger_ui_oauth2_redirect_html()

    @app.get(_REDOC_PATH, include_in_schema=False)
    def redoc(request: Request) -> HTMLResponse:
        root_path = request.scope.get("root_path", "").rstrip("/")
        return get_redoc_html(
            openapi_url=root_path + OPENAPI_PATH, title=f"{app.title} - ReDoc"
        )

    del served_document, swagger_ui, swagger_ui_redirect, redoc


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
        # `R-31`. The four documentation routes FastAPI would install itself are
        # suppressed here and declared below, because the ones `setup()` builds are plain
        # Starlette routes that no dependency can reach. See :data:`DOCUMENTATION_PATHS`.
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
        swagger_ui_oauth2_redirect_url=None,
        # `R-31`, the other half. These seed `app.router.dependencies`, which
        # `add_api_route` copies onto **every** route the application carries -- the
        # eighteen merged in by `include_router` below and the four declared beneath it.
        # They were arguments to `include_router` until this wave, which is what left the
        # four outside the seam. The order is unchanged: an included route ends up with
        # `app.router.dependencies + <include_router's> + <the route's own>`, so moving
        # both of these up moves them together and the generated document does not shift.
        dependencies=[
            Depends(declare_correlation_id),
            # `W39-REVOKE`. The seam verifies a credential's signature with the key this
            # environment derives, and then asks the account whether it still accepts that
            # credential's generation. The second half needs a port, and the port travels
            # on the router: see `auditmanager.api.routers.Router`. A router assembled with
            # no credential port -- `create_documentation_app` -- yields `None` here, and
            # the dependency refuses every guarded request rather than admitting it, which
            # is the same rule the module already applies to a missing deployment secret.
            build_authorization_dependency(
                environ, epochs=getattr(router, "credentials", None)
            ),
        ],
        # A model with a default would otherwise be emitted twice, as `X-Input` and
        # `X-Output`. The 51 schema names are pinned by the contract and by the frontend's
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
    # No `dependencies=` here, and that absence is the repair. They are on the application
    # now; an argument added back to this call would guard the eighteen and leave the four
    # below open again, which is `D-73`.
    app.include_router(router)
    _declare_the_documentation_routes(app)
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
