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
from dataclasses import dataclass, replace
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.api.routers import Router, build_router
from auditmanager.api.security import TokenSigner, derive_signing_key
from auditmanager.bootstrap.providers import (
    DatabaseProviders,
    EnvironmentProviders,
    ProviderSource,
    UnboundAdapter,
)
from auditmanager.bootstrap.runner import RunnerAdapter
from auditmanager.comparison.public import (
    COMPARISON_MODULES_ENV,
    HANDLER_FACTORIES as COMPARISON_HANDLER_FACTORIES,
    SPEND_SETTLERS as COMPARISON_SPEND_SETTLERS,
    ComparisonWorkRepository,
    ComparisonWorkRunner,
    HandlerRegistry,
    WorkDependencies,
    WorkQueueError,
    enabled_modules as enabled_comparison_modules,
    parse_modules as parse_comparison_modules,
)
from auditmanager.bootstrap.adapters import (
    AccountAdapter,
    AnalysisProfileAdapter,
    BlockAdapter,
    ComparisonAdapter,
    DispatchAdapter,
    CredentialAdapter,
    CsvExportAdapter,
    DashboardAdapter,
    DecisionAdapter,
    DocumentAdapter,
    ExecutionAdapter,
    ExecutorAdapter,
    FindingAdapter,
    NormContentAdapter,
    NormsSearchAdapter,
    OptimisationAdapter,
    OptimisationProposalAdapter,
    ProjectAdapter,
    RegistrationAdapter,
    ReleasesAdapter,
    ComparisonUploadAdapter,
    ComparisonMatrixAdapter,
    ComparisonOverviewAdapter,
    ComparisonPairTileAdapter,
    ComparisonSeriesAdapter,
    ComparisonVersionOrderAdapter,
    VersionPageAdapter,
    RunAdapter,
    SectionAdapter,
    SectionSpecificationAdapter,
    SpecificationPricesAdapter,
    XlsxExportAdapter,
    resolve_analysis_preset,
)
from auditmanager.ingest.comparison_batch.public import BATCH_HANDLER_FACTORIES, ComparisonBatchService
from auditmanager.ingest.comparison_pdf.public import ComparisonUploadService, ComparisonVersionOrderService
from auditmanager.bootstrap.settings import AppSettings, ConfigurationError
from auditmanager.bootstrap.settings import load as load_settings
from auditmanager.runs.public import (
    PACK_MANIFEST_ENV,
    DurableCarrier,
    PackManifestRefused,
    ParsedPackManifest,
    ReclaimingCarrier,
    TrustedPackRegistry,
    load_manifest,
    run_to_terminal,
)
from auditmanager.sections.public import SECTION_CODES, section_names
from auditmanager.releases.public import (
    ReleaseRepository, compute_build_id, read_product_version,
)


def summary_model_for(provider_mode: str) -> Any:
    """The summary model of a process: the recorded replay in recorded mode, **nothing** otherwise.

    The live implementation is not wired in this release and no live call is made or tested
    (`R-29`): a process in any other mode answers `generateComparisonSummary` with
    ``dependency_unavailable`` (``dependency: comparison_summary_model``). There is no fallback from
    a missing recording to a provider: the recorded model holds no client and no credential.
    """
    from auditmanager.comparison.public import RecordedSummaryModel

    return RecordedSummaryModel() if provider_mode == "recorded" else None


def _ar_v3_installed_pack(env: dict[str, str]) -> ParsedPackManifest | None:
    """`AR-V3-BETA-PACK-INSTALL-01`: load the sealed reviewed pack named by the environment.

    Without ``AR_V3_BETA_PACK_MANIFEST`` (or with a blank value, as ``load_trusted_pack_registry``
    reads it) nothing is installed and group starts refuse. With it, a manifest that cannot be
    loaded refuses the start: an empty registry is never the answer to a pack the operator meant
    to install. The one load yields both the registry and, for `AR-V3-BETA-PACK-STATUS-API-01`,
    the attestation that came with the pack.
    """
    path = env.get(PACK_MANIFEST_ENV)
    if path is None or not path.strip():
        return None
    try:
        return load_manifest(path.strip())
    except PackManifestRefused as exc:
        raise ConfigurationError(
            f"{PACK_MANIFEST_ENV} names a reviewed-pack manifest the server refuses: {exc}"
        ) from exc


def _registry_of(installed: ParsedPackManifest | None) -> TrustedPackRegistry:
    return TrustedPackRegistry.empty() if installed is None else installed.registry


def _ar_v3_pack_registry(env: dict[str, str]) -> TrustedPackRegistry:
    """The registry alone: what the worker needs, and what group start decides from."""
    return _registry_of(_ar_v3_installed_pack(env))


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
    #: `W54-WORKER-01` (R-105). ``all`` claims in-process (W53); ``api`` claims nothing
    #: and its carrier only reclaims expired leases, because the worker service claims.
    execution_role: str = "all"


@dataclass(frozen=True, slots=True)
class WorkerRuntime:
    """Everything ``python -m auditmanager.workers serve`` needs, already built.

    The same engine, store, provider and profile wiring as :class:`Application`, without
    a router and without the deployment secret: the worker answers no request (R-105).
    """

    settings: AppSettings
    engine: Any
    session_factory: sessionmaker[Session]
    #: ``execute(run_id, worker_id)`` runs one claimed run to a terminal, recording the
    #: worker on its Lease (:func:`auditmanager.runs.public.run_to_terminal`).
    execute: Callable[[str, str], None]
    #: What the registry row says this process is: the product version and build id.
    version: str
    slots: int
    state_dir: Path | None
    #: `EXEC-HTTP-01`: ``probe_runner()`` takes the ``requested`` connection probes and runs them
    #: on this process's network path; ``None`` when the process holds no private ring.
    probe_runner: Callable[[], int] | None = None
    #: `CMP-WORK-01`: the comparison loop the worker hosts as a second claimant
    #: (:class:`~auditmanager.comparison.public.ComparisonWorkRunner`). Always built by
    #: :func:`build_worker_runtime`; with ``AUDITMANAGER_COMPARISON_MODULES=none`` (the default)
    #: it claims nothing and only reclaims expired leases.
    comparison_work: ComparisonWorkRunner | None = None


def build_comparison_work(
    *, sessions: sessionmaker[Session], engine: Any, blob_store: Any, environ: Mapping[str, str],
) -> ComparisonWorkRunner:
    """`CMP-WORK-01` (ADR-0025 decisions 4, 6, 23): the comparison loop's brain, or a refusal.

    The module set is read once from ``AUDITMANAGER_COMPARISON_MODULES`` (an unknown value stops the
    worker while it is wiring, as it stops the API); one dependency bundle is built and every
    factory of ``comparison.public.HANDLER_FACTORIES`` is applied to it, refusing a duplicate kind.
    """
    try:
        modules = enabled_comparison_modules(
            parse_comparison_modules(environ.get(COMPARISON_MODULES_ENV))
        )
    except ValueError as exc:
        raise ConfigurationError(str(exc)) from exc
    work = ComparisonWorkRepository()
    try:
        # `CMP-INGEST-02`: the two work kinds of the batch operations are appended here, not in
        # ``comparison.public`` (a ``comparison`` module may not import ``ingest``); the registry
        # still refuses a duplicate kind.
        registry = HandlerRegistry.build(
            (*COMPARISON_HANDLER_FACTORIES, *BATCH_HANDLER_FACTORIES),
            WorkDependencies(
                engine=engine, session_factory=sessions, blob_store=blob_store, work=work,
            ),
        )
    except WorkQueueError as exc:
        raise ConfigurationError(str(exc)) from exc
    return ComparisonWorkRunner(
        sessions, registry=registry, modules=modules, repository=work,
        spend_settlers=COMPARISON_SPEND_SETTLERS,
    )


def build_worker_runtime(
    settings: AppSettings | None = None,
    *,
    environ: dict[str, str] | None = None,
) -> WorkerRuntime:
    """Wire the worker service, or refuse to -- the same contract as the application."""
    env: dict[str, str] = dict(os.environ) if environ is None else dict(environ)
    resolved = settings if settings is not None else load_settings(env)
    if resolved.execution_role != "worker":
        raise ConfigurationError(
            f"the worker service runs only with EXECUTION_ROLE=worker, not "
            f"{resolved.execution_role!r}; compose.server.yml sets it literally on the "
            "worker service"
        )

    from auditmanager.shared.db import create_database_engine, create_session_factory
    from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
    from auditmanager.storage import S3BlobStore, S3StorageSettings

    # `EXEC-PAR-QUEUE-01`: every slot may hold a claim, a heartbeat and a final transaction at
    # once on top of the service's own threads, so the pool grows by two connections per slot
    # beyond the first. One slot keeps the pool exactly as it was (5 + 5 overflow).
    database = DatabaseSettings(url=parse_database_url(resolved.database_url))
    engine = create_database_engine(
        replace(database, pool_size=database.pool_size + 2 * (resolved.worker_slots - 1))
    )
    sessions = create_session_factory(engine)
    try:
        version = f"{read_product_version()}+{compute_build_id()}"
    except (FileNotFoundError, ValueError) as exc:
        raise ConfigurationError(f"release version or build inputs are invalid: {exc}") from exc
    store = S3BlobStore(
        S3StorageSettings(
            endpoint_url=resolved.s3_endpoint_url,
            region=resolved.s3_region,
            access_key_id=resolved.s3_access_key_id,
            secret_access_key=resolved.s3_secret_access_key,
            bucket=resolved.s3_bucket,
        )
    )
    from auditmanager.executors.runtime import KindRuntime

    model_adapter, provider_config, providers = _build_provider(
        resolved, env, runtime=KindRuntime(session_factory=sessions, engine=engine),
    )
    # `W59-SECTION-SEAL-01`. The worker runs each claimed run with the profile it pinned,
    # resolved through the same registry the application routes with.
    text_profiles = load_text_profiles()
    ar_v3_pack_registry = _ar_v3_pack_registry(env)

    def execute(run_id: str, worker_id: str) -> None:
        run_to_terminal(
            sessions,
            run_id,
            blob_store=store,
            adapter=model_adapter,
            provider_config=provider_config,
            worker_id=worker_id,
            text_profiles=text_profiles.resolve,
            providers=providers.resolve,
            ar_v3_pack_registry=ar_v3_pack_registry,
        )

    # `EXEC-PULL-PROBE-INT-01`: pull probes need no secret. Start the probe loop even
    # without a private ring; keyed probes report `secret_unreadable` in that case.
    from auditmanager.executors.runtime import runner_for

    probe_runner = runner_for(
        sessions, ring=resolved.secrets_private_ring, environ=env, engine=engine,
    )

    return WorkerRuntime(
        settings=resolved,
        engine=engine,
        session_factory=sessions,
        execute=execute,
        version=version,
        # `EXEC-PAR-QUEUE-01`: `AUDITMANAGER_WORKER_SLOTS`, validated once by `settings.load`
        # (a whole number in 1..16; anything else refused the start). Unset is one run at a time,
        # per `PROTOTYPE_PROFILE.md` section 2, which is today's behaviour and the rollback.
        slots=resolved.worker_slots,
        state_dir=None if resolved.worker_state_dir is None else Path(resolved.worker_state_dir),
        probe_runner=probe_runner,
        comparison_work=build_comparison_work(
            sessions=sessions, engine=engine, blob_store=store, environ=env,
        ),
    )


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
    if resolved.execution_role == "worker":
        raise ConfigurationError(
            "EXECUTION_ROLE=worker is the worker service's role (python -m "
            "auditmanager.workers serve); the API serves with api or all"
        )

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

    try:
        product_version = read_product_version()
        build_id = compute_build_id()
    except (FileNotFoundError, ValueError) as exc:
        raise ConfigurationError(f"release version or build inputs are invalid: {exc}") from exc
    release_repository = ReleaseRepository(sessions, product_version=product_version)
    try:
        comparison_modules = parse_comparison_modules(env.get(COMPARISON_MODULES_ENV))
    except ValueError as exc:
        raise ConfigurationError(str(exc)) from exc

    store = S3BlobStore(
        S3StorageSettings(
            endpoint_url=resolved.s3_endpoint_url,
            region=resolved.s3_region,
            access_key_id=resolved.s3_access_key_id,
            secret_access_key=resolved.s3_secret_access_key,
            bucket=resolved.s3_bucket,
        )
    )

    # `CMP-INGEST-01` / `CMP-INGEST-02`: one upload service, shared by the adapter's own operations
    # and by the batch service that reads the batch and the sets back through it.
    comparison_upload_service = ComparisonUploadService(store, session_factory=sessions)

    from auditmanager.executors.runtime import KindRuntime

    model_adapter, provider_config, providers = _build_provider(
        resolved, env, runtime=KindRuntime(session_factory=sessions, engine=engine),
    )
    # `W59-SECTION-SEAL-01`. The section-keyed text-profile registry: every `text-profile/1`
    # package (АР is not one, `PROD-11-AR-V1-V2-REMOVAL-01`). Loaded once; a bad package refuses the
    # start rather than serving a partial table. Run start routes through its table, the
    # executor resolves pinned profiles through it, and the review reports its sections.
    text_profiles = load_text_profiles()

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
    from auditmanager.access.public import AccountRepository as AccountAccessRepository
    from auditmanager.access.public import (
        RegistrationRepository as RegistrationAccessRepository,
    )
    from auditmanager.access.repository import UserRepository as UserAccessRepository

    try:
        signer = TokenSigner(derive_signing_key(resolved.api_token or ""))
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
    #
    # `W54-WORKER-01` (R-105). Under ``EXECUTION_ROLE=api`` the worker service claims and
    # this process only fences expired leases; ``all`` keeps W53's in-process claimant.
    carrier: Any = (
        ReclaimingCarrier(sessions) if resolved.execution_role == "api"
        else DurableCarrier(sessions)
    )

    ar_v3_installed_pack = _ar_v3_installed_pack(env)
    run_adapter = RunAdapter(
        sessions,
        blob_store=store,
        adapter=model_adapter,
        provider_config=provider_config,
        provider_mode=_provenance_mode(resolved.provider_mode),
        carrier=carrier,
        # `W55B-BUDGET-01`: derived once by `settings.load` from the model and the ceiling, and
        # refused there when it cannot hold the AR document set. Always passed, never None.
        input_budget_characters=resolved.input_budget_characters,
        # `W59-SECTION-SEAL-01`. Always both: a served run start routes from the version's
        # persisted classification, never from a configured pair (there is none since
        # `PROD-11-AR-V1-V2-REMOVAL-01`), and a served run executes its pinned profile.
        # ``test_the_served_application_routes_by_section``.
        section_profiles=text_profiles.section_profiles(),
        text_profiles=text_profiles.resolve,
        # `EXEC-HTTP-01`. Which source serves a run: ``providers.freeze`` is set for the
        # ``database`` source only, and then runs freeze their connection revision at start.
        providers=providers.resolve,
        route_freezer=providers.freeze,
        # `ANALYSIS-PRESETS-01`. A named preset is read in the start's own transaction and then
        # started as the executor it names; always passed, so a served start never ignores one.
        preset_resolver=resolve_analysis_preset,
        # No expert-approved six-set pack is installed in the beta candidate.
        # This keeps group start closed while allowing historical group reads.
        ar_v3_pack_registry=_registry_of(ar_v3_installed_pack),
        # `AR-V3-BETA-PACK-STATUS-API-01`: the same load, with the attestation that came with it.
        ar_v3_installed_pack=ar_v3_installed_pack,
    )
    if isinstance(carrier, DurableCarrier):
        carrier.configure_runner(run_adapter._job)

    router = build_router(
        projects=ProjectAdapter(ingest),
        documents=DocumentAdapter(ingest),
        runs=run_adapter,
        ar_v3_groups=run_adapter,
        findings=FindingAdapter(sessions),
        decisions=DecisionAdapter(sessions),
        exports=CsvExportAdapter(sessions),
        credentials=CredentialAdapter(
            sessions,
            users=UserAccessRepository(),
            accounts=AccountAccessRepository(),
            signer=signer,
        ),
        # `W45-BLOCKS`. Reads the same store and session factory as everything else here;
        # nothing new is opened for it.
        blocks=BlockAdapter(sessions, blob_store=store),
        # `W46-SEAL`, `R-44`. Reads the same session factory too.
        dashboard=DashboardAdapter(sessions),
        # `W49-SEAL-01`. The account itself, account management and registration.
        accounts=AccountAdapter(sessions, accounts=AccountAccessRepository()),
        registrations=RegistrationAdapter(
            sessions, registrations=RegistrationAccessRepository()
        ),
        releases=ReleasesAdapter(
            release_repository,
            product_version=product_version,
            build_id=build_id,
            # `CMP-SEAL-C0` (ADR-0025 decision 23): the module set reaches the web through the
            # contract (``ProductVersion.comparison_modules``), not through a client env read.
            comparison_modules=comparison_modules,
        ),
        # `CMP-SEAL-C0`. The comparison operations, sealed as stubs answering `503
        # dependency_unavailable` until `CMP-INGEST-01`, `CMP-INGEST-02` and `CMP-PROFILE-01`
        # replace the three adapters (plan section 4.0 rule 1).
        comparison_uploads=ComparisonUploadAdapter(
            sessions, service=comparison_upload_service,
            batches=ComparisonBatchService(comparison_upload_service, session_factory=sessions),
        ),
        comparison_version_orders=ComparisonVersionOrderAdapter(
            sessions, service=ComparisonVersionOrderService(session_factory=sessions)
        ),
        version_pages=VersionPageAdapter(sessions, blob_store=store),
        # `CMP-SEAL-C1`. The version comparison core, sealed as stubs answering `503
        # dependency_unavailable` until `CMP-MATRIX-01`, `CMP-SERIES-01`, `CMP-VIEWER-01` and
        # `CMP-VC-OVERVIEW-01` replace the four adapters (plan section 4.0 rule 1).
        comparison_matrices=ComparisonMatrixAdapter(sessions, blob_store=store),
        comparison_series=ComparisonSeriesAdapter(),
        comparison_pair_tiles=ComparisonPairTileAdapter(),
        comparison_overview=ComparisonOverviewAdapter(),
        execution=ExecutionAdapter(sessions, runs=run_adapter),
        # `W55A-SEAL-01` sealed them; `W55A-SEARCH-01` serves them. The norms reads and the
        # designation over the same session factory, every search under the operator's
        # statement timeout; the norm PDF through its confirmed binding from the same store.
        norms=NormsSearchAdapter(sessions, timeout_ms=resolved.norms_search_timeout_ms),
        norm_content=NormContentAdapter(sessions, blob_store=store),
        # `W57B-NORMS-CATALOGUE-XLSX-01`. The workbook: the same session factory, and the
        # version's portal companion read from the same store.
        xlsx_exports=XlsxExportAdapter(sessions, blob_store=store),
        # `W59-SECTION-SEAL-01`. Classification and review over the same sessions and store;
        # `executable` is the registry's own section set.
        sections=SectionAdapter(
            sessions,
            blob_store=store,
            executable_sections=text_profiles.executable_sections(),
        ),
        # `W59-VERSION-COMPARE-01`. Two versions of one set compared, read-only, over the
        # same sessions and store: classifications from the documents projection, the
        # section catalogue from `sections.public`, text layers held to their recorded
        # digests.
        comparisons=ComparisonAdapter(
            sessions, blob_store=store, section_codes=SECTION_CODES,
            # `COMPARE-PERSISTED-SUMMARY-01` (B2). A model for summaries exists only in recorded
            # mode, and the meter is the run ceiling; no live implementation is wired (`R-29`).
            summary_model=summary_model_for(resolved.provider_mode),
            cost_ceiling_usd=resolved.run_cost_ceiling_usd,
            # `CMP-SEAL-C1` (ADR-0025 decision 13): the module set, so the three `0035` operations are
            # withdrawn while the versions module is on.
            comparison_modules=comparison_modules,
        ),
        # `W59-ANALYSIS-SETTINGS-01`. The same registry run start routes through, listed
        # read-only for «Настройки анализа», named from the reviewed section catalogue.
        analysis_profiles=AnalysisProfileAdapter(text_profiles, section_names=section_names()),
        # `W61-DISPATCHER-01`. «Диспетчер» over the same session factory; the role set
        # and the people's labels are read through `access` in each transaction.
        dispatch=DispatchAdapter(sessions),
        # `W60-PRICE-LIST-01`. Project price lists (the uploaded file kept as a Blob in the
        # same store) and vendor lists, over the same sessions.
        optimisation=OptimisationAdapter(sessions, blob_store=store),
        # `W60-OPT-MATCH-01`. A document set's AR specification priced from the project's
        # current price list; the saved text layers are read as the comparison reads them.
        specification_prices=SpecificationPricesAdapter(sessions, blob_store=store),
        # `W60-OPT-PROPOSALS-01`. The optimisation passes, their proposals and the experts'
        # decisions over the same sessions; the saved text layers are read as the comparison
        # reads them.
        optimisation_proposals=OptimisationProposalAdapter(sessions, blob_store=store),
        # `W63-SECTION-FORM7-01`. The same saved-text port, a section's rows across projects.
        section_specifications=SectionSpecificationAdapter(sessions, blob_store=store),
        # `EXEC-SEAL-01`. The executor connections: the api seals to the public ring and holds
        # no private key, so nothing it serves can open a secret.
        executors=ExecutorAdapter(sessions, ring=resolved.secrets_public_ring),
        # `EXEC-PULL-01`. The pull channel: runner tokens, and the four operations a runner
        # calls with one. It also authenticates the token (the seam asks this port).
        runner=RunnerAdapter(sessions, blob_store=store),
    )
    return Application(
        router=router,
        settings=resolved,
        session_factory=sessions,
        provider_config=provider_config,
        carrier=carrier,
        execution_role=resolved.execution_role,
    )


def load_text_profiles() -> Any:
    """The section-keyed text-profile registry, or a start-up refusal (`W59-SECTION-SEAL-01`).

    ``analysis.text`` publishes no registry factory through ``analysis.public``; the
    composition root assembles from the module that defines it, as ``_build_provider`` does
    for the adapters.
    """
    from auditmanager.analysis.text.profile_registry import (
        TextProfileLoadError,
        load_text_profile_registry,
    )

    try:
        return load_text_profile_registry()
    except TextProfileLoadError as exc:
        raise ConfigurationError(
            f"the text-profile packages cannot be registered ({exc}); the application "
            "refuses to start rather than route runs through a partial registry"
        ) from exc


def _provenance_mode(transport: str) -> str:
    """What the run records, given how the call travels.

    The live-or-recorded vocabulary answers one question: did a model produce this, or was
    it replayed. A proxy changes neither answer, so it maps to `live`.
    """
    return "recorded" if transport == "recorded" else "live"


def _build_provider(
    settings: AppSettings, environ: Mapping[str, str], *, runtime: Any = None,
) -> tuple[Any, Any, ProviderSource]:
    """Construct the model adapter the configured mode and source name.

    Constructing it here rather than at first run is what makes a broken provider a startup
    failure: a recorded adapter whose recordings are missing, or a live one with no
    credential, is discovered before a document has been uploaded and a run row written.

    ``analysis.text`` publishes no single factory, so the root assembles from the pieces it
    does publish - which is the composition root's job, and is why the pieces are public.

    ``runtime`` (`EXEC-PULL-01`) is the database access a ``pull`` connection's adapter is built
    from (the worker's session factory and engine); only the ``database`` source uses it.

    The last element is the **provider source** (`EXEC-HTTP-01`): ``environment`` hands every run
    the adapter built here; ``database`` binds each run to the connection revision it froze.
    """
    from auditmanager.analysis.text import (
        CallBinding,
        LiveAdapter,
        ProxyAdapter,
        ProxySettings,
        RecordedAdapter,
        load_provider_config,
    )
    from auditmanager.executors.runtime import DestinationPolicy

    # `analysis.text` parses the provider mode from the environment itself and its
    # vocabulary is live-or-recorded, by design: it is asking about provenance, and a
    # transport is not an answer to that question. So it is handed the **provenance** mode
    # rather than taught a third value. The translation stays in one place - here - which is
    # the only place that knows both the transport and what the run will record.
    config = load_provider_config(
        dict(environ) | {"AUDITMANAGER_PROVIDER_MODE": _provenance_mode(settings.provider_mode)}
    )

    if settings.provider_source == "database":
        # Every connection is a live transport. This process holds no adapter of its own: a run
        # is bound to the revision it froze, with that connection's key (`settings.load` has
        # already refused the old variables and demanded the private ring).
        source: ProviderSource = DatabaseProviders(
            ring=settings.secrets_private_ring,
            policy=DestinationPolicy.from_environment(dict(environ)),
            base_config=config, ceiling_usd=settings.run_cost_ceiling_usd, runtime=runtime,
        )
        return UnboundAdapter(), config, source

    call: CallBinding | None
    if settings.execution_role == "api":
        # The `api` makes no model call when a separate worker runs, and no longer receives the
        # provider credential (plan section 6): its adapter only declares the mode.
        adapter: Any = UnboundAdapter()
        call = None
    elif settings.provider_mode == "proxy":
        # A proxied call is `live` in the run's provenance, because a model really answered
        # it. The proxy is the transport, and the transport is not the question the
        # live-or-recorded vocabulary asks.
        adapter = ProxyAdapter(
            ProxySettings(
                base_url=settings.proxy_base_url or "",
                token=settings.proxy_token or "",
                model=settings.proxy_model,
            )
        )
        # `R-133`: the stage holds the reply to the configured name; the stub says nothing was
        # selected and fails closed.
        call = CallBinding(expected_model=settings.proxy_model, check_identity=True)
    elif settings.provider_mode == "live":
        if settings.api_key is None:  # pragma: no cover - settings.load refuses first
            raise ConfigurationError("live mode requires a credential")
        adapter = LiveAdapter(api_key=settings.api_key)
        call = CallBinding(expected_model=config.model_id, check_identity=True)
    else:
        adapter = RecordedAdapter()
        call = None
        # `PROD-11C` (`D-225` piece 2): a replayed reply costs nothing and carries no amount, so the
        # AR v3 worker's cost check (`a metered AR v3 call has no verifiable cost amount`) refused
        # every recorded v3 Run after its provider call. The AR v3 beta Runs of a *recorded* process
        # are told the replay is unmetered; the live and proxy branches above build no such binding,
        # and `EnvironmentProviders` refuses one for a non-recorded adapter.
        replay = CallBinding(unmetered=True)
        return adapter, config, EnvironmentProviders(adapter, config, call, ar_v3_replay_call=replay)
    return adapter, config, EnvironmentProviders(adapter, config, call)
