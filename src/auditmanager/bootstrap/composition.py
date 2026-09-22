"""The composition root. The only place that reads configuration and builds anything.

Its contract, from the Gate C task: every accepted module is constructed from
configuration, and **a missing or misconfigured dependency fails at construction, not at
first use**. So :func:`build_application` resolves settings, opens the engine, constructs
the store and the model adapter, and only then assembles the router. A process that starts
has everything it needs; one that does not, does not start.

Nothing below imports a module for a use case that is not wired. `B6`'s ``build_router``
takes six protocols and constructs none of them, and this is the other half of that seam.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from collections.abc import Mapping
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.api.routers import Router, build_router
from auditmanager.api.security import TokenSigner, derive_signing_key
from auditmanager.bootstrap.adapters import (
    CredentialAdapter,
    CsvExportAdapter,
    DecisionAdapter,
    DocumentAdapter,
    FindingAdapter,
    ProjectAdapter,
    RunAdapter,
)
from auditmanager.bootstrap.settings import AppSettings, ConfigurationError
from auditmanager.bootstrap.settings import load as load_settings
from auditmanager.runs import ThreadCarrier


@dataclass(frozen=True, slots=True)
class Application:
    """Everything a server needs, already built."""

    router: Router
    settings: AppSettings
    session_factory: sessionmaker[Session]
    #: The provider configuration actually wired, exposed so that "constructed from
    #: configuration" is checkable rather than asserted. Without it the ceiling the run
    #: will enforce is invisible from outside, which is how `W5CERT-DEF-2` survived.
    provider_config: Any
    #: `D-20`. What carries a run off the request thread. Exposed for the same reason
    #: ``provider_config`` is: "this application does not execute on the request thread"
    #: is then a property a test can read off the built object, rather than a claim about
    #: a line inside an adapter. It is also the only honest way to *wait* for a run --
    #: ``carrier.drain(timeout)`` waits on the real work, where a sleep waits on a guess.
    carrier: Any


def build_application(
    settings: AppSettings | None = None,
    *,
    environ: dict[str, str] | None = None,
) -> Application:
    """Wire the application, or refuse to."""
    # Resolve the environment once. Everything built below reads *this* mapping, so an
    # injected environ governs the whole wiring rather than just the half that happens to
    # take a parameter. `W5CERT-DEF-2`: `_build_provider` used to reach for `os.environ`
    # directly, so `create_app(environ=...)` set `AppSettings.run_cost_ceiling_usd` and the
    # provider then enforced a different one read from the process. The two could disagree
    # and nothing would say so.
    env: dict[str, str] = dict(os.environ) if environ is None else dict(environ)
    resolved = settings if settings is not None else load_settings(env)

    from auditmanager.ingest import IngestService
    from auditmanager.shared.db import create_database_engine, create_session_factory
    from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
    from auditmanager.storage import S3BlobStore, S3StorageSettings

    # parse_database_url refuses a URL with the wrong drivername, so a misconfigured
    # DATABASE_URL is a startup failure rather than a first-request one.
    engine = create_database_engine(
        DatabaseSettings(url=parse_database_url(resolved.database_url))
    )
    sessions = create_session_factory(engine)

    store = S3BlobStore(
        S3StorageSettings(
            endpoint_url=resolved.s3_endpoint_url,
            region=resolved.s3_region,
            access_key_id=resolved.s3_access_key_id,
            secret_access_key=resolved.s3_secret_access_key,
            bucket=resolved.s3_bucket,
        )
    )

    model_adapter, provider_config, profile_id, bundle_id = _build_provider(resolved, env)

    ingest = IngestService(store, session_factory=sessions)

    # `W34-API`. The credential exchange, wired from the two halves that exist for it:
    # `W34-DOM`'s user repository, and a signer derived from the deployment secret
    # `load_settings` has already refused to start without. The derivation reads
    # ``resolved.api_token`` rather than ``env`` directly, so an injected settings object
    # governs the whole wiring -- ``W5CERT-DEF-2`` is what happens when one component takes
    # the injected value and another reaches past it for the same name.
    #
    # The import is here rather than at module scope for the reason the four imports above
    # are: the composition root is the only thing that knows which boundaries this
    # application is made of, and ``access`` is a boundary the routers must not import.
    from auditmanager.access.repository import UserRepository as UserAccessRepository

    try:
        signer = TokenSigner(derive_signing_key(resolved.api_token))
    except ValueError as exc:  # pragma: no cover - settings.load refuses an empty one first
        raise ConfigurationError(
            "the deployment secret derives no signing key, so this application could "
            "neither issue a credential nor verify one; it refuses to start rather than "
            "answer authentication_required to every request"
        ) from exc

    # `D-20`. One carrier per built application, constructed here like everything else:
    # a process that starts has its executor, and `RunAdapter` takes it as a required
    # argument so no application can be assembled that quietly executes on the request
    # thread. `ThreadCarrier` is `RUN_CONCURRENCY` wide -- one, per `PROTOTYPE_PROFILE.md`
    # section 2 -- so a second run waits in `queued` instead of competing for the
    # provider budget with the first.
    carrier = ThreadCarrier()

    router = build_router(
        projects=ProjectAdapter(ingest),
        documents=DocumentAdapter(ingest),
        runs=RunAdapter(
            sessions,
            blob_store=store,
            adapter=model_adapter,
            provider_config=provider_config,
            # The **provenance** mode, not the transport. `proxy` is how the call travels;
            # `live` is what the run records, because a model really answered. Two things
            # enforce that independently and both would refuse `proxy` here: the database
            # CHECK on audit_run.provider_mode admits only live and recorded, and execute_run
            # refuses a run whose declared mode disagrees with its adapter - and the proxy
            # adapter reports `live`. Translating here is the only place that knows both.
            provider_mode=_provenance_mode(resolved.provider_mode),
            analysis_profile_id=profile_id,
            prompt_bundle_id=bundle_id,
            carrier=carrier,
        ),
        findings=FindingAdapter(sessions),
        decisions=DecisionAdapter(sessions),
        exports=CsvExportAdapter(sessions),
        credentials=CredentialAdapter(
            sessions, users=UserAccessRepository(), signer=signer
        ),
    )
    return Application(
        router=router,
        settings=resolved,
        session_factory=sessions,
        provider_config=provider_config,
        carrier=carrier,
    )


def _provenance_mode(transport: str) -> str:
    """What the run records, given how the call travels.

    The live-or-recorded vocabulary answers one question: did a model produce this, or was
    it replayed. A proxy changes neither answer, so it maps to `live`.
    """
    return "recorded" if transport == "recorded" else "live"


def _build_provider(
    settings: AppSettings, environ: Mapping[str, str]
) -> tuple[Any, Any, str, str]:
    """Construct the model adapter the configured mode names.

    Constructing it here rather than at first run is what makes a broken provider a startup
    failure: a recorded adapter whose recordings are missing, or a live one with no
    credential, is discovered before a document has been uploaded and a run row written.

    ``analysis.text`` publishes no single factory, so the root assembles from the pieces it
    does publish - which is the composition root's job, and is why the pieces are public.
    """
    from auditmanager.analysis.text import (
        LiveAdapter,
        ProxyAdapter,
        ProxySettings,
        RecordedAdapter,
        load_provider_config,
        resolve_profile,
    )

    if settings.provider_mode == "proxy":
        # A proxied call is `live` in the run's provenance, because a model really answered
        # it. The proxy is the transport, and the transport is not the question the
        # live-or-recorded vocabulary asks.
        adapter: Any = ProxyAdapter(
            ProxySettings(
                base_url=settings.proxy_base_url or "",
                token=settings.proxy_token or "",
                model=settings.proxy_model,
            )
        )
    elif settings.provider_mode == "live":
        if settings.api_key is None:  # pragma: no cover - settings.load refuses first
            raise ConfigurationError("live mode requires a credential")
        adapter = LiveAdapter(api_key=settings.api_key)
    else:
        adapter = RecordedAdapter()

    # `analysis.text` parses the provider mode from the environment itself and its
    # vocabulary is live-or-recorded, by design: it is asking about provenance, and a
    # transport is not an answer to that question. So it is handed the **provenance** mode
    # rather than taught a third value. The translation stays in one place - here - which is
    # the only place that knows both the transport and what the run will record.
    config = load_provider_config(
        dict(environ) | {"AUDITMANAGER_PROVIDER_MODE": _provenance_mode(settings.provider_mode)}
    )
    profile = resolve_profile()
    return adapter, config, str(profile.analysis_profile_id), str(profile.prompt_bundle.prompt_bundle_id)
