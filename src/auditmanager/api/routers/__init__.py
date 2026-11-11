"""The 325 operations of ``contracts/api/v1/openapi.json``, and nothing else.

:func:`build_router` assembles one ``APIRouter`` from the forty-three router modules. It takes
its dependencies as arguments and constructs none of them: choosing what sits behind each
port is the composition root's job (``api/composition.py``), and a factory that reached for
a concrete implementation would have taken that decision away from it.

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
from auditmanager.api.routers.blocks import build_block_routes
from auditmanager.api.routers.comparison_uploads import build_comparison_upload_routes
from auditmanager.api.routers.comparison_version_orders import (
    build_comparison_version_order_routes,
)
from auditmanager.api.routers.correlation import (
    CORRELATION_HEADER,
    CorrelationMiddleware,
    current_correlation_id,
    new_correlation_id,
    resolve_correlation_id,
)
from auditmanager.api.routers.dashboard import build_dashboard_routes
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
from auditmanager.api.routers.execution import build_execution_routes
from auditmanager.api.routers.executor_enrollment import build_enrollment_routes
from auditmanager.api.routers.executor_groups import build_executor_group_routes  # EXEC2-GROUP-STORE-01
from auditmanager.api.routers.hosts import build_host_routes  # HOSTS-SEAL-1
from auditmanager.api.routers.hosts_ports import ExecutorHostPort, RunStagePort, StageModelPort  # HOSTS-SEAL-1, HOSTS-SEAL-2
from auditmanager.api.routers.executors import build_executor_routes
from auditmanager.api.routers.runner import ExecutorTaskContextPort, build_runner_routes, build_task_context_route  # CTX-STAND
from auditmanager.api.routers.findings import build_finding_routes
from auditmanager.api.routers.handlers import (
    FailureEnvelopeMiddleware,
    install_exception_handlers,
)
from auditmanager.api.routers.idempotency import (
    IDEMPOTENCY_HEADER,
    require_idempotency_key,
)
from auditmanager.api.routers.analysis_profiles import build_analysis_profile_routes
from auditmanager.api.routers.section_specification import build_section_specification_routes
from auditmanager.api.routers.specification_prices import build_specification_price_routes
from auditmanager.api.routers.comparison import build_comparison_routes
from auditmanager.api.routers.dispatch import build_dispatch_routes
from auditmanager.api.routers.decision_memory import build_decision_memory_routes
from auditmanager.api.routers.schedule import build_schedule_routes
from auditmanager.api.routers.me import build_me_routes
from auditmanager.api.routers.norms import build_norm_routes
from auditmanager.api.routers.optimisation import build_optimisation_routes
from auditmanager.api.routers.optimisation_proposals import build_optimisation_proposal_routes
from auditmanager.api.routers.releases import build_release_routes
from auditmanager.api.routers.version_pages import build_version_page_routes
from auditmanager.api.routers.comparison_ai_pairs import build_comparison_ai_pair_routes
from auditmanager.api.routers.comparison_ai_sheets import build_comparison_ai_sheet_routes
from auditmanager.api.routers.comparison_launch_queue import build_comparison_launch_queue_routes
from auditmanager.api.routers.comparison_matrix import build_comparison_matrix_routes
from auditmanager.api.routers.comparison_overview import build_comparison_overview_routes
from auditmanager.api.routers.comparison_pair_tiles import build_comparison_pair_tile_routes
from auditmanager.api.routers.comparison_reports import build_comparison_report_routes
from auditmanager.api.routers.comparison_series import build_comparison_series_routes
from auditmanager.api.routers.comparison_specification import build_comparison_specification_routes
from auditmanager.api.routers.comparison_stage_pairs import build_comparison_stage_pair_routes
from auditmanager.api.routers.comparison_stage_uploads import build_comparison_stage_upload_routes
from auditmanager.api.routers.comparison_stage_links import build_comparison_stage_link_routes
from auditmanager.api.routers.comparison_stage_text import build_comparison_stage_text_routes
from auditmanager.api.routers.comparison_stage_runs import build_comparison_stage_run_routes
from auditmanager.api.routers.comparison_stage_c4 import build_comparison_stage_c4_routes
from auditmanager.api.routers.multipart import (
    MAX_BODY,
    MAX_CONCURRENT_UPLOADS,
    UPLOAD_MAX_BODY,
    BodyCapMiddleware,
)
from auditmanager.api.routers.ports import (
    AccountPort,
    AnalysisProfilePort,
    OptimisationPort,
    OptimisationProposalPort,
    BlockPort,
    ComparisonPort,
    ComparisonUploadPort,
    ComparisonVersionOrderPort,
    VersionPagePort,
    ComparisonMatrixPort,
    ComparisonOverviewPort,
    ComparisonPairTilePort,
    ComparisonSeriesPort,
    ComparisonAiPairPort,
    ComparisonAiSheetPort,
    ComparisonLaunchQueuePort,
    ComparisonReportPort,
    ComparisonSpecificationPort,
    ComparisonStagePairPort,
    ComparisonStageUploadPort,
    ComparisonStageLinkPort,
    ComparisonStageTextPort,
    ComparisonStageRunPort,
    ComparisonStageC4Port,
    DispatchPort,
    DecisionMemoryPort,
    SchedulePort,
    CredentialPort,
    CsvExportPort,
    DashboardPort,
    DecisionPort,
    DocumentPort,
    ExecutionPort,
    ExecutorGroupPort,
    ExecutorPort,
    RunnerPort,
    EnrollmentPort,
    FindingPort,
    NormContentPort,
    NormsSearchPort,
    ProjectPort,
    RegistrationPort,
    ReleasesPort,
    RunPort,
    SectionPort,
    SectionSpecificationPort,
    SpecificationPricesPort,
    XlsxExportPort,
)
from auditmanager.api.routers.projects import build_project_routes
from auditmanager.api.routers.registrations import build_registration_routes
from auditmanager.api.routers.runs import build_run_routes
from auditmanager.api.routers.sections import build_section_routes
from auditmanager.api.routers.run_stages import build_run_stage_routes  # HOSTS-SEAL-2
from auditmanager.api.routers.precedents import build_precedent_routes  # CRIT-SEAL-50
from auditmanager.api.routers.precedents_ports import (  # EMBED-01, PREC-SETTINGS-01, PREC-PASS, CRIT-SEAL-53
    DecisionPatternsPort, PrecedentSettingsPort, PrecedentsPort, StageQualityPort, VectorControlPort,
)
from auditmanager.api.routers.stage_models import build_stage_model_routes  # HOSTS-SEAL-1
from auditmanager.api.routers.users import build_user_routes
from auditmanager.api.routers.wire import WireResponse, encode_json, json_response

class Router(APIRouter):
    """What ``build_router`` returns: the surface, and the credential port behind it.

    It was ``Router = APIRouter`` until wave 39. What made it a class is that the
    authorization seam now needs a **database read** -- an account's credential generation,
    compared against the one the presented credential carries -- and the seam is assembled in
    ``api/app.py`` from an environment, which knows nothing about ports.

    ``api/app.py`` is handed exactly two things: this router, and the environment. So the
    port travels on the router, which is the object that already went through the composition
    root holding it. The alternative was to reach for the port on an ``Application`` field, and
    that field does not exist: ``bootstrap/composition.py`` is a single-owner hotspot, and a
    seam that depended on a field being added there would be a seam nobody could wire without
    taking that lock.

    ``credentials`` is ``None`` for ``create_documentation_app``, which is handed no ports at
    all. A ``None`` here is a refusal downstream, never an open door: see
    :func:`auditmanager.api.security.build_authorization_dependency`.
    """

    __slots__ = ("credentials", "runner_tokens", "enrollment")

    def __init__(
        self, *, credentials: CredentialPort | None = None,
        runner_tokens: RunnerPort | None = None,
        enrollment: EnrollmentPort | None = None,
    ) -> None:
        super().__init__()
        self.credentials = credentials
        #: `EXEC-PULL-01`. The pull channel's port, which is also what authenticates a runner
        #: token: the seam reads it from here for the same reason it reads ``credentials``.
        self.runner_tokens = runner_tokens
        #: `EXEC2-ENROLL-01`. The universal agent's port, which also authenticates an enrollment secret: the
        #: seam reads it from here, as it reads ``runner_tokens``.
        self.enrollment = enrollment

__all__ = [
    "BASE_PATH",
    "CONTRACT_VERSION",
    "CORRELATION_HEADER",
    "IDEMPOTENCY_HEADER",
    "MAX_BODY",
    "MAX_CONCURRENT_UPLOADS",
    "METHOD_NOT_ALLOWED_CODE",
    "UPLOAD_MAX_BODY",
    "AccountPort",
    "BlockPort",
    "BodyCapMiddleware",
    "CorrelationMiddleware",
    "CredentialPort",
    "CsvExportPort",
    "DashboardPort",
    "DecisionPort",
    "DocumentPort",
    "ExecutionPort",
    "ExecutorGroupPort",
    "ExecutorHostPort",
    "RunStagePort",
    "StageModelPort",
    "ExecutorPort",
    "RunnerPort",
    "EnrollmentPort",
    "FailureEnvelopeMiddleware",
    "FindingPort",
    "NormContentPort",
    "NormsSearchPort",
    "ProjectPort",
    "RegistrationPort",
    "ReleasesPort",
    "Router",
    "RunPort",
    "SectionPort",
    "ComparisonPort",
    "ComparisonUploadPort",
    "ComparisonVersionOrderPort",
    "VersionPagePort",
    "ComparisonMatrixPort",
    "ComparisonOverviewPort",
    "ComparisonPairTilePort",
    "ComparisonSeriesPort",
    "ComparisonAiPairPort",
    "ComparisonAiSheetPort",
    "ComparisonLaunchQueuePort",
    "ComparisonReportPort",
    "ComparisonSpecificationPort",
    "AnalysisProfilePort",
    "DispatchPort",
    "DecisionMemoryPort",
    "SchedulePort",
    "OptimisationPort",
    "SectionSpecificationPort",
    "SpecificationPricesPort",
    "OptimisationProposalPort",
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
CONTRACT_VERSION: Final[str] = "1.52.0"


def build_router(
    *,
    projects: ProjectPort,
    documents: DocumentPort,
    runs: RunPort,
    findings: FindingPort,
    decisions: DecisionPort,
    exports: CsvExportPort,
    credentials: CredentialPort | None = None,
    blocks: BlockPort | None = None,
    dashboard: DashboardPort | None = None,
    accounts: AccountPort | None = None,
    registrations: RegistrationPort | None = None,
    releases: ReleasesPort | None = None,
    execution: ExecutionPort | None = None,
    norms: NormsSearchPort | None = None,
    norm_content: NormContentPort | None = None,
    sections: SectionPort | None = None,
    comparisons: ComparisonPort | None = None,
    analysis_profiles: AnalysisProfilePort | None = None,
    xlsx_exports: XlsxExportPort | None = None,
    dispatch: DispatchPort | None = None,
    schedule: SchedulePort | None = None,
    decision_memory: DecisionMemoryPort | None = None,
    optimisation: OptimisationPort | None = None,
    specification_prices: SpecificationPricesPort | None = None,
    optimisation_proposals: OptimisationProposalPort | None = None,
    section_specifications: SectionSpecificationPort | None = None,
    executors: ExecutorPort | None = None,
    runner: RunnerPort | None = None,
    enrollment: EnrollmentPort | None = None,
    executor_groups: ExecutorGroupPort | None = None,
    executor_hosts: ExecutorHostPort | None = None,
    stage_models: StageModelPort | None = None,
    run_stages: RunStagePort | None = None,
    comparison_uploads: ComparisonUploadPort | None = None,
    comparison_version_orders: ComparisonVersionOrderPort | None = None,
    version_pages: VersionPagePort | None = None,
    comparison_matrices: ComparisonMatrixPort | None = None,
    comparison_series: ComparisonSeriesPort | None = None,
    comparison_pair_tiles: ComparisonPairTilePort | None = None,
    comparison_overview: ComparisonOverviewPort | None = None,
    comparison_ai_pairs: ComparisonAiPairPort | None = None,
    comparison_ai_sheets: ComparisonAiSheetPort | None = None,
    comparison_specifications: ComparisonSpecificationPort | None = None,
    comparison_launch_queue: ComparisonLaunchQueuePort | None = None,
    comparison_reports: ComparisonReportPort | None = None,
    comparison_stage_pairs: ComparisonStagePairPort | None = None,
    comparison_stage_uploads: ComparisonStageUploadPort | None = None,
    comparison_stage_links: ComparisonStageLinkPort | None = None,
    comparison_stage_text: ComparisonStageTextPort | None = None,
    comparison_stage_runs: ComparisonStageRunPort | None = None,
    comparison_stage_c4: ComparisonStageC4Port | None = None,
    vector_control: VectorControlPort | None = None,
    precedent_settings: PrecedentSettingsPort | None = None,
    precedents: PrecedentsPort | None = None,
    task_context: ExecutorTaskContextPort | None = None,
    decision_patterns: DecisionPatternsPort | None = None,
    stage_quality: StageQualityPort | None = None,
) -> Router:
    """Assemble the 328 operations, from the router modules -- ``me``,
    ``registrations`` and ``users`` are `W49-SEAL-01`'s three, ``sections``
    `W59-SECTION-SEAL-01`'s, ``comparison`` `W59-VERSION-COMPARE-01`'s,
    ``analysis_profiles`` `W59-ANALYSIS-SETTINGS-01`'s, ``dispatch`` `W61-DISPATCHER-01`'s and
    ``optimisation`` `W60-PRICE-LIST-01`'s, ``optimisation_proposals`` `W60-OPT-PROPOSALS-01`'s;
    `W57B-NORMS-CATALOGUE-XLSX-01` adds
    ``listNormDocuments`` to the norms router and ``exportRunXlsx`` (on ``xlsx_exports``) to
    the export router; ``specification_prices`` is `W60-OPT-MATCH-01`'s.

    ``accounts`` and ``registrations`` are two more ports with a default, for the reason
    the paragraph below gives for the first three: every caller that does not serve them
    -- ``create_documentation_app``, the test-only wirings -- keeps working unchanged, and
    an operation whose port is ``None`` is declared in the document and answerable only
    in an application that was handed one.

    Keyword-only, because eight same-shaped dependencies passed positionally is a wiring
    defect waiting to happen and the type checker cannot see it.

    ``credentials``, ``blocks`` and ``dashboard`` have a default and the other six do not,
    for one reason that is not taste: ``api/app.py`` -- another session's file -- calls
    this with exactly the six it has called it with since `B6`, and
    ``create_documentation_app`` builds the served document with nothing behind any port
    at all. A seventh, eighth or ninth *required* argument would have made any of the
    three additions a change to that file. All three are therefore **declared** in every
    router and **answerable** only in an application that was handed a port, which is the
    same bargain ``create_documentation_app`` already makes with the other six: the
    document is a function of the declarations, and serving a request is not.
    ``test_the_wired_application_can_answer_the_exchange`` is what says the composition
    root really hands the credential port over; `W45-BLOCKS`'s integration suite is the
    equivalent for ``blocks``, and this wave's is the equivalent for ``dashboard``.

    **Since wave 39 the returned router also carries the credential port**, because the
    authorization seam reads an account's credential generation on every request it guards
    and is assembled in ``api/app.py``, which is handed the router and an environment and
    nothing else. See :class:`Router`. Nothing about the six changes, and an application
    built with no credential port refuses every guarded request rather than serving one.
    """
    router = Router(credentials=credentials, runner_tokens=runner, enrollment=enrollment)
    # One router, registered onto directly, rather than six included into a seventh.
    # ``include_router`` wraps each sub-router instead of copying its routes, so
    # ``router.routes`` would carry seven opaque wrappers and the whole-surface
    # assertions -- the route count, the ``(operationId, method, path)`` set,
    # ``tests/integration/api/test_operation_surface.py`` -- could not see an operation at
    # all. A table nobody can enumerate is a table nobody can check.
    build_project_routes(router, projects)
    build_document_routes(router, documents)
    build_block_routes(router, blocks)  # type: ignore[arg-type]
    build_run_routes(router, runs)
    # `D-67`. Two collections address a parent that another port owns: `listRunFindings`
    # hangs off a run and `listDecisionHistory` off a finding. Each builder is handed the
    # port that can answer whether that parent exists, so the operation can refuse an
    # identity that names nothing instead of rendering an empty page over it. Positional
    # and required, not a keyword with a `None` default: a default would be a silent
    # fallback to the behaviour this closes.
    build_finding_routes(router, findings, runs)
    build_decision_routes(router, decisions, findings)
    # `W57B-NORMS-CATALOGUE-XLSX-01`. The workbook on its own port, optional with a default
    # for the reason `blocks` gives above.
    build_export_routes(router, exports, xlsx_exports)  # type: ignore[arg-type]
    build_auth_routes(router, credentials)  # type: ignore[arg-type]
    build_dashboard_routes(router, dashboard)  # type: ignore[arg-type]
    build_me_routes(router, accounts)  # type: ignore[arg-type]
    build_registration_routes(router, registrations)  # type: ignore[arg-type]
    build_user_routes(router, accounts)  # type: ignore[arg-type]
    build_release_routes(router, releases)  # type: ignore[arg-type]
    build_execution_routes(router, execution)  # type: ignore[arg-type]
    # `W55A-SEAL-01`. The seven norms operations: six on the search port, the PDF on the
    # content port. Optional with a default, for the reason `blocks` gives above.
    build_norm_routes(router, norms, norm_content)  # type: ignore[arg-type]
    # `W59-SECTION-SEAL-01`. A version's classification and its section review. Optional
    # with a default, for the reason `blocks` gives above.
    build_section_routes(router, sections)  # type: ignore[arg-type]
    # `W59-VERSION-COMPARE-01`. Two versions of one set compared, read-only. Optional with
    # a default, for the reason `blocks` gives above.
    build_comparison_routes(router, comparisons)  # type: ignore[arg-type]
    # `W59-ANALYSIS-SETTINGS-01`. The text-profile registry, read-only. Optional with a
    # default, for the reason `blocks` gives above.
    build_analysis_profile_routes(router, analysis_profiles)  # type: ignore[arg-type]
    # `W61-DISPATCHER-01`. «Диспетчер»: work assignments and their history. Optional with a
    # default, for the reason `blocks` gives above.
    build_dispatch_routes(router, dispatch)  # type: ignore[arg-type]
    # `UI-PARITY-P0P`. «График работ»: done work against plans, the calendar and the reserve.
    build_schedule_routes(router, schedule)  # type: ignore[arg-type]
    # `DECISION-MEMORY-01` phase M2 (contract 1.44.0). The expert decision memory: cases, standing, status.
    build_decision_memory_routes(router, decision_memory)  # type: ignore[arg-type]
    # `W60-PRICE-LIST-01`. Project price lists and vendor lists. Optional with a default, for
    # the reason `blocks` gives above.
    build_optimisation_routes(router, optimisation)  # type: ignore[arg-type]
    # `W60-OPT-MATCH-01`. A document set's AR specification priced from the project's price
    # list, read-only. Optional with a default, for the reason `blocks` gives above.
    build_specification_price_routes(router, specification_prices)  # type: ignore[arg-type]
    # `W60-OPT-PROPOSALS-01`. The optimisation passes, their proposals and the experts'
    # decisions. Optional with a default, for the reason `blocks` gives above.
    build_optimisation_proposal_routes(router, optimisation_proposals)  # type: ignore[arg-type]
    # `W63-SECTION-FORM7-01`. A section's combined Form-7 specification across projects,
    # read-only. Optional with a default, for the reason `blocks` gives above.
    build_section_specification_routes(router, section_specifications)  # type: ignore[arg-type]
    # `EXEC-SEAL-01`. The executor connections, secrets, probes and routes (`R-143`). Optional
    # with a default, for the reason `blocks` gives above.
    build_executor_routes(router, executors)  # type: ignore[arg-type]
    # `EXEC-PULL-01`. The pull channel: two administrator operations on runner tokens and the
    # four a runner calls with one. Optional with a default, for the reason `blocks` gives.
    build_runner_routes(router, runner)  # type: ignore[arg-type]
    # `CTX-STAND` (contract 1.51.0): `getExecutorTaskContext`, the agent's ask for reference data, moved here from the seal's sleeping route in
    # `api/routers/precedents.py` with its declaration word for word, so the served document is unchanged. Declared whatever the port; with none it
    # answers `503 dependency_unavailable` (`executor_task_context`) as the seal did.
    build_task_context_route(router, task_context)
    # `EXEC2-ENROLL-01`. The universal agent: the enrollment grant and its exchange, the agent's health, the
    # public package, the API side of an install over SSH and the integration-authorisation mark. Optional
    # with a default, for the reason `blocks` gives; declared whatever the port, answerable only with one.
    build_enrollment_routes(router, enrollment)  # type: ignore[arg-type]
    # `EXEC2-GROUP-STORE-01`. Executor groups and the routing rule of a work kind, and with them the cut-over reads and
    # writes of contract 1.16.0 (`previewExecutorRouting` and `setExecutorRoutingMode` are `EXEC2-CUTOVER-01`'s, declared
    # in the same module). Optional with a default, for the reason `blocks` gives; declared whatever the port, answerable
    # only with one.
    build_executor_group_routes(router, executor_groups)  # type: ignore[arg-type]
    # `HOSTS-SEAL-1` (ADR-0028, contract 1.45.0). The servers (hosts): list, read, details, the «Использовать» switch, slots, archive and
    # the host-targeted enrollment and install; and the models of the analysis stages: the layout, the catalogue and the readiness of a
    # start. Optional with a default, for the reason `blocks` gives; declared whatever the port, answerable only with one. The shipped
    # implementations are the stubs of `bootstrap/hosts_adapter.py` and `bootstrap/stage_plan_adapter.py` (`503 dependency_unavailable`);
    # the integrator wires them into the composition root.
    build_host_routes(router, executor_hosts)  # type: ignore[arg-type]
    build_stage_model_routes(router, stage_models)  # type: ignore[arg-type]
    # `HOSTS-SEAL-2` (ADR-0028, contract 1.46.0). The stages of a run, plan and fact (`getRunStages`). Optional with a default, for the
    # reason `blocks` gives; declared whatever the port, answerable only with one. The implementation is `runs/stage_facts.py` behind
    # `bootstrap/run_stage_adapter.py`; the integrator wires it into the composition root as `run_stages=`.
    build_run_stage_routes(router, run_stages)  # type: ignore[arg-type]
    # `CRIT-SEAL-50` (contract 1.51.0, plan-v5 section 3.2). The «Прецеденты» surface: the labels and the card of
    # a finding, the pause of the vectors and the settings (the reference data of a task is the runner's, declared above). Sealed and asleep: no port, every body answers `503 dependency_unavailable`
    # until the lane that owns it fills it (`api/routers/precedents.py`). `EMBED-01` filled the vector control: `vector_control` is its port,
    # optional with a default for the reason `blocks` gives above; None keeps the sleeping answer. `PREC-SETTINGS-01` filled the settings:
    # `precedent_settings` is its port, with the same default. `PREC-PASS` filled the labels and the card: `precedents` is its port, with the same default.
    # `CRIT-SEAL-53` (contract 1.53.0) added the failure patterns (`PAT-01`: `decision_patterns` is its port) and the quality table (`QUAL-01`:
    # `stage_quality`), both optional with the same default: None keeps the sleeping answer.
    build_precedent_routes(router, vector_control, precedent_settings, precedents, decision_patterns, stage_quality)
    # `CMP-SEAL-C0` (ADR-0025). The comparison modules' upload, version-order and page reads,
    # sealed as stubs answering `503 dependency_unavailable` until `CMP-INGEST-01`,
    # `CMP-INGEST-02` and `CMP-PROFILE-01` wire their ports. Optional with a default, for the
    # reason `blocks` gives above.
    build_comparison_upload_routes(router, comparison_uploads)  # type: ignore[arg-type]
    build_comparison_version_order_routes(router, comparison_version_orders)  # type: ignore[arg-type]
    build_version_page_routes(router, version_pages)  # type: ignore[arg-type]
    # `CMP-SEAL-C1` (ADR-0025). The version comparison core: the effective matrix and its edits,
    # the series and its sheet pairs, the pair tiles, the overview and the queue block, sealed as
    # stubs answering `503 dependency_unavailable` until `CMP-MATRIX-01`, `CMP-SERIES-01`,
    # `CMP-VIEWER-01` and `CMP-VC-OVERVIEW-01` wire their ports. Optional with a default, for the
    # reason `blocks` gives above.
    build_comparison_matrix_routes(router, comparison_matrices)  # type: ignore[arg-type]
    build_comparison_series_routes(router, comparison_series)  # type: ignore[arg-type]
    build_comparison_pair_tile_routes(router, comparison_pair_tiles)  # type: ignore[arg-type]
    build_comparison_overview_routes(router, comparison_overview)  # type: ignore[arg-type]
    # `CMP-SEAL-C2` (ADR-0025). The version comparison AI, specifications, launch queue and reports,
    # sealed as stubs answering `503 dependency_unavailable` until `CMP-VC-AIPAIR-01`,
    # `CMP-VC-AISHEET-01`, `CMP-VC-SPEC-01`, `CMP-VC-QUEUE-01` and `CMP-VC-REPORT-01` wire their ports.
    build_comparison_ai_pair_routes(router, comparison_ai_pairs)  # type: ignore[arg-type]
    build_comparison_ai_sheet_routes(router, comparison_ai_sheets)  # type: ignore[arg-type]
    build_comparison_specification_routes(router, comparison_specifications)  # type: ignore[arg-type]
    build_comparison_launch_queue_routes(router, comparison_launch_queue)  # type: ignore[arg-type]
    build_comparison_report_routes(router, comparison_reports)  # type: ignore[arg-type]
    build_comparison_stage_pair_routes(router, comparison_stage_pairs)  # type: ignore[arg-type]
    build_comparison_stage_upload_routes(router, comparison_stage_uploads)  # type: ignore[arg-type]
    build_comparison_stage_link_routes(router, comparison_stage_links)  # type: ignore[arg-type]
    build_comparison_stage_text_routes(router, comparison_stage_text)  # type: ignore[arg-type]
    build_comparison_stage_run_routes(router, comparison_stage_runs)  # type: ignore[arg-type]
    build_comparison_stage_c4_routes(router, comparison_stage_c4)  # type: ignore[arg-type]
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
