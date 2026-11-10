"""The cross-context surface of the executors boundary (`EXEC-SEAL-01`).

What ``EXEC-HTTP-01`` relies on:

* :func:`resolve_route` and :func:`current_revision` -- which connection serves a kind of model
  work and the revision to freeze at run start;
* :func:`pinned_models` -- the models a revision may name, with their rates, from the provider
  lock (the same list validates a revision);
* :func:`record_probe_started` and :func:`record_probe_result` -- how the worker writes a probe;
* :func:`open_secret` -- **worker only**. The caller recomputes the destination from the
  revision it is about to call (:func:`destination_for`) and passes it; the associated data is
  built from that argument and never from the stored row. A revision that changed the address
  leaves the old secret :class:`SecretUnreadableError` for it.

The ``api`` never imports :func:`open_secret`'s ring: it loads public keys only
(:func:`load_public_ring`).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from auditmanager.analysis.public import ModelPin, pinned_models
from auditmanager.executors.commands import (
    GeneratedKey,
    archive_connection,
    create_connection,
    generate_ssh_key,
    request_probe,
    revise_connection,
    set_route,
    set_secret,
)
# `EXEC2-ENROLL-01` (ADR-0026 decisions 4 to 9): the enrollment grant and the exchange, the agent's health, the
# package the image holds, the API side of an install over SSH and the integration-authorisation mark.
from auditmanager.executors.agent_install import (
    authorized_keys_line,
    confirm_agent_install_host_key,
    create_agent_install,
    get_agent_install,
    install_destination,
    observed_fingerprint,
)
from auditmanager.executors.agent_install_repository import InstallRecord
from auditmanager.executors.agent_package import (
    AgentPackage,
    available_versions,
    latest_package,
    load_package,
)
from auditmanager.executors.enrollment import (
    EnrollmentPrincipal,
    IssuedEnrollment,
    RedeemedToken,
    authenticate_enrollment,
    enrollments_of,
    issue_executor_enrollment,
    redeem_enrollment,
    report_runner_health,
    token_health_of,
)
from auditmanager.executors.enrollment_repository import (
    EnrollmentRecord,
    TokenHealth,
)
from auditmanager.executors.integration_mark import (
    IntegrationMark,
    integration_marks_of,
    set_integration_authorisation,
)
from auditmanager.executors.destinations import DestinationPolicy
from auditmanager.executors.image_input import (
    MAX_IMAGE_BYTES,
    MAX_IMAGES,
    MAX_TOTAL_IMAGE_BYTES,
    CropImage,
    ImageLoad,
    attach_images,
    checked_descriptors,
    checked_pngs,
    image_load,
)
from auditmanager.executors.model import (
    IDENTITY_BASIS_BY_KIND,
    ConnectionRecord,
    ConnectionSummary,
    ProbeRecord,
    ResolvedRoute,
    RevisionRecord,
    RevisionSettings,
    RouteRecord,
    SecretRecord,
    destination_for,
    host_key_fingerprint,
)
from auditmanager.executors.preset_commands import (
    archive_preset,
    choose_preset,
    create_preset,
    list_presets,
    preset_of_revision,
    revise_preset,
)
from auditmanager.executors.presets import ChosenPreset, PresetRecord, RunPresetRecord
from auditmanager.executors.pull import (
    PullAdapter,
    TaskWaiter,
    answer_window,
    build_pull_adapter,
    probe_pull,
)
from auditmanager.executors.queries import (
    ConnectionDetail,
    RunExecutor,
    connection_detail,
    executor_of_revision,
    list_connection_summaries,
    list_routes,
    resolve_route,
    sweep,
)
from auditmanager.executors.repository import ExecutorRepository
from auditmanager.executors.runner import (
    CLAIM_LEASE_SECONDS,
    ClaimedTask,
    IssuedToken,
    RunnerPrincipal,
    TaskAck,
    authenticate_runner,
    claim_task,
    claimed_image,
    extend_claim,
    fail_task,
    issue_runner_token,
    open_task_count,
    revoke_runner_token,
    runner_tokens_of,
    submit_answer,
)
from auditmanager.executors.runner_repository import RunnerTokenRecord
from auditmanager.executors.sealing import (
    PrivateRing,
    PublicRing,
    SealingConfigurationError,
    SecretUnreadable,
    associated_data,
    load_private_ring,
    load_public_ring,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from sqlalchemy.orm import Session

# EXEC2-CAP-01 (ADR-0026 decision 1): the capacity reads of a connection, for the `api` adapters and for
# `EXEC2-GROUP-RUN-01` / `EXEC2-GROUP-CMP-01`.
from auditmanager.executors.queries import (
    Occupancy,
    capacity_of,
    occupancies,
    occupancy_of,
    run_queue_reason,
    used_units,
)

# EXEC2-GROUP-STORE-01 (ADR-0026 decisions 10, 11 and 14): executor groups, the routing rule of a work kind, the
# routing mode as the journal states it, the capacity of a group and the pure selection among its members. The
# dispatch lanes (`EXEC2-GROUP-RUN-01`, `EXEC2-GROUP-CMP-01`) call these and never read the group tables.
from auditmanager.executors.group_commands import (
    advance_group_rotation,
    archive_group,
    create_group,
    group_capacity,
    group_detail,
    group_revision_of,
    group_summary,
    list_group_summaries,
    list_routing_rules,
    member_facts,
    resolve_rule,
    revise_group,
    routing_mode,
    set_routing_rule,
)
from auditmanager.executors.group_selection import (
    GroupMember,
    MemberFacts,
    choose,
    member_issue,
)
# HOSTS-BACKEND-01 (ADR-0028): the servers, the system objects kept for them, availability, and the binding of a planned run's cells.
from auditmanager.executors.catalogue import Catalogue, CatalogueEntry, catalogue, load_catalogue
from auditmanager.executors.cell_binding import (
    AT_CAPACITY,
    CAPACITY_WAIT_REASON,
    WAIT_MODEL_UNAVAILABLE,
    BindOutcome,
    BoundCell,
    CellRequest,
    CellWait,
    bind_cells,
    bound_pools_of_run,
    cell_binding_of,
    cell_requests,
    evaluate_wait,
    pool_has_room,
    pools_of,
    write_bindings,
)
from auditmanager.executors.host_commands import (
    HostDetails,
    HostFacts,
    HostHealthAck,
    ModelAvailability,
    SlotUse,
    archive_host,
    confirm_host_agent_install_host_key,
    create_host_agent_install,
    ensure_upgrade_allowed,
    get_host_agent_install,
    host_claim_limit,
    host_details,
    issue_host_enrollment,
    issue_host_grant,
    member_reasons,
    model_availability,
    read_hosts,
    record_task_failure,
    refuse_host_members_for_connection_token,
    report_host_health,
    report_host_runner_health,
    set_host_enabled,
    set_host_slots,
    sync_system_objects,
)
from auditmanager.executors.host_repository import ActiveTask, HostRecord, HostRepository
from auditmanager.executors.hosts import REASON_ORDER, access_of_billing, pair_group_name, split_pool  # pair_group_name: HOSTS-CMP-01, the comparison finds the system group of a pair
from auditmanager.executors.pull import HostCall
# EXEC2-CUTOVER-01 (ADR-0026 decision 17): the cut-over preview, the mode change and the guard on the legacy routes.
from auditmanager.executors.routing_mode import (
    MappingEntry,
    ModeChange,
    PreviewItem,
    RoutingPreview,
    ensure_legacy_routing,
    preview_routing,
    set_routing_mode,
)
from auditmanager.executors.groups import (
    GroupCapacity,
    GroupDetail,
    GroupMemberRecord,
    GroupRecord,
    GroupRevisionRecord,
    GroupSettings,
    GroupSummary,
    MemberRequest,
    MemberStatus,
    ModeState,
    RuleListing,
    RuleRecord,
)

if TYPE_CHECKING:
    from auditmanager.executors.agent_install_runner import AgentInstallRunner, install_runner_for
    from auditmanager.executors.operations import OperationRefused, import_env

__all__ = [
    # `EXEC2-ENROLL-SSH-01`: the worker's half of path A, resolved on first use (see `__getattr__`).
    "AgentInstallRunner",
    "install_runner_for",
    # `EXEC2-ENROLL-01`.
    "AgentPackage",
    "EnrollmentPrincipal",
    "EnrollmentRecord",
    "InstallRecord",
    "IntegrationMark",
    "IssuedEnrollment",
    "RedeemedToken",
    "TokenHealth",
    "authenticate_enrollment",
    "authorized_keys_line",
    "available_versions",
    "confirm_agent_install_host_key",
    "create_agent_install",
    "enrollments_of",
    "get_agent_install",
    "install_destination",
    "integration_marks_of",
    "issue_executor_enrollment",
    "latest_package",
    "load_package",
    "observed_fingerprint",
    "redeem_enrollment",
    "report_runner_health",
    "set_integration_authorisation",
    "token_health_of",
    "CLAIM_LEASE_SECONDS",
    "MAX_IMAGES",
    "MAX_IMAGE_BYTES",
    "MAX_TOTAL_IMAGE_BYTES",
    "ChosenPreset",
    "ClaimedTask",
    "CropImage",
    "ImageLoad",
    "attach_images",
    "request_with_provider_images",
    "checked_descriptors",
    "checked_pngs",
    "claimed_image",
    "image_load",
    "ConnectionDetail",
    "ConnectionRecord",
    "ConnectionSummary",
    "DestinationPolicy",
    "GeneratedKey",
    "IssuedToken",
    "ModelPin",
    "OperationRefused",
    "PresetRecord",
    "PrivateRing",
    "ProbeRecord",
    "PublicRing",
    "PullAdapter",
    "ResolvedRoute",
    "RevisionRecord",
    "RevisionSettings",
    "RouteRecord",
    "RunExecutor",
    "RunPresetRecord",
    "RunnerPrincipal",
    "RunnerTokenRecord",
    "SealingConfigurationError",
    "SecretRecord",
    "SecretUnreadableError",
    "TaskAck",
    "TaskWaiter",
    "answer_window",
    "archive_connection",
    "archive_preset",
    "authenticate_runner",
    "build_pull_adapter",
    "choose_preset",
    "claim_task",
    "connection_detail",
    "create_connection",
    "create_preset",
    "current_revision",
    "destination_for",
    "executor_of_revision",
    "extend_claim",
    "fail_task",
    "generate_ssh_key",
    "host_key_fingerprint",
    "import_env",
    "issue_runner_token",
    "list_connection_summaries",
    "list_presets",
    "list_routes",
    "load_private_ring",
    "load_public_ring",
    "open_secret",
    "open_task_count",
    "pinned_models",
    "preset_of_revision",
    "probe_pull",
    "record_probe_result",
    "record_probe_started",
    "request_probe",
    "resolve_route",
    "revise_connection",
    "revise_preset",
    "revoke_runner_token",
    "runner_tokens_of",
    "set_route",
    "set_secret",
    "submit_answer",
    "sweep",
    # EXEC2-CAP-01
    "Occupancy",
    "capacity_of",
    "occupancies",
    "occupancy_of",
    "run_queue_reason",
    "used_units",
    # EXEC2-GROUP-STORE-01
    "GroupCapacity",
    "GroupDetail",
    "GroupMember",
    "GroupMemberRecord",
    "GroupRecord",
    "GroupRevisionRecord",
    "GroupSettings",
    "GroupSummary",
    "MemberFacts",
    "MemberRequest",
    "MemberStatus",
    "ModeState",
    "RuleListing",
    "RuleRecord",
    "advance_group_rotation",
    "archive_group",
    "choose",
    "create_group",
    "group_capacity",
    "group_detail",
    "group_revision_of",
    "group_summary",
    "list_group_summaries",
    "list_routing_rules",
    "member_facts",
    "member_issue",
    "resolve_rule",
    "revise_group",
    "routing_mode",
    "set_routing_rule",
    # HOSTS-BACKEND-01
    "AT_CAPACITY",
    "CAPACITY_WAIT_REASON",
    "WAIT_MODEL_UNAVAILABLE",
    "BindOutcome",
    "BoundCell",
    "CellRequest",
    "CellWait",
    "bind_cells",
    "bound_pools_of_run",
    "cell_binding_of",
    "cell_requests",
    "evaluate_wait",
    "pool_has_room",
    "pools_of",
    "write_bindings",
    "Catalogue",
    "CatalogueEntry",
    "catalogue",
    "load_catalogue",
    "HostDetails",
    "HostFacts",
    "HostHealthAck",
    "ModelAvailability",
    "SlotUse",
    "archive_host",
    "confirm_host_agent_install_host_key",
    "create_host_agent_install",
    "ensure_upgrade_allowed",
    "get_host_agent_install",
    "host_claim_limit",
    "host_details",
    "issue_host_enrollment",
    "issue_host_grant",
    "member_reasons",
    "model_availability",
    "read_hosts",
    "record_task_failure",
    "refuse_host_members_for_connection_token",
    "report_host_health",
    "report_host_runner_health",
    "set_host_enabled",
    "set_host_slots",
    "sync_system_objects",
    "ActiveTask",
    "HostRecord",
    "HostRepository",
    "HostCall",
    # HOSTS-INT-WIRE-01: what the composition root's availability port and member binder read (the capacity pool and the reasons' order).
    "REASON_ORDER",
    "access_of_billing",
    "pair_group_name",  # HOSTS-CMP-01
    "split_pool",
    "IDENTITY_BASIS_BY_KIND",  # HOSTS-DEBTS-01 (D-673): how a kind's model identity is known, read without building an adapter
    # EXEC2-CUTOVER-01
    "MappingEntry",
    "ModeChange",
    "PreviewItem",
    "RoutingPreview",
    "ensure_legacy_routing",
    "preview_routing",
    "set_routing_mode",
]


#: The worker's baseline import (`EXEC-ENV-OPENROUTER-01`). Resolved on first use, because
#: ``operations`` imports this module (and so do ``probe_runner`` and ``resolver``): a top-level
#: import here would break ``import auditmanager.executors.operations`` on the cycle.
_OPERATIONS_EXPORTS = frozenset({"OperationRefused", "import_env"})
#: The same for the install runner (`EXEC2-ENROLL-SSH-01`): ``agent_install_runner`` imports ``open_secret`` and
#: ``SecretUnreadableError`` from this module, so it cannot be imported at the top of it.
_INSTALL_RUNNER_EXPORTS = frozenset({"AgentInstallRunner", "install_runner_for"})


def __getattr__(name: str) -> object:
    if name in _OPERATIONS_EXPORTS:
        from auditmanager.executors import operations

        return getattr(operations, name)
    if name in _INSTALL_RUNNER_EXPORTS:
        from auditmanager.executors import agent_install_runner

        return getattr(agent_install_runner, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


class SecretUnreadableError(DomainError):
    """``dependency_unavailable``, ``dependency: secret_unreadable``: the secret cannot be opened
    here, for this destination. Carries no bytes and no key material."""

    def __init__(self) -> None:
        super().__init__(
            ErrorCode.DEPENDENCY_UNAVAILABLE, message="the sealed secret cannot be opened",
            dependency="secret_unreadable",
        )


def current_revision(
    session: Session, connection_id: str, repository: ExecutorRepository | None = None
) -> RevisionRecord | None:
    """The highest-numbered revision of a connection, or ``None`` when it has none."""
    return (repository or ExecutorRepository()).current_revisions(
        session, [connection_id]
    ).get(connection_id)


def open_secret(
    session: Session, ring: PrivateRing | None, *, secret_id: str, destination: str,
    repository: ExecutorRepository | None = None,
) -> str:
    """Open one secret for ``destination``. Worker only: ``ring`` is the private ring.

    Raises :class:`SecretUnreadableError` for every reason it cannot: no ring, no such secret,
    a key id missing from the ring, a corrupt envelope, or a destination other than the one
    the secret was sealed for. The reason is not distinguished, and no byte is in the error.
    """
    sealed = (repository or ExecutorRepository()).sealed_secret(session, secret_id)
    if ring is None or sealed is None:
        raise SecretUnreadableError()
    connection_id, purpose, kid, ciphertext = sealed
    associated = associated_data(
        secret_id=secret_id, connection_id=connection_id, purpose=purpose, kid=kid,
        destination=destination,
    )
    try:
        return ring.open(kid, ciphertext, associated).decode("utf-8")
    except (SecretUnreadable, UnicodeDecodeError):
        raise SecretUnreadableError() from None


def record_probe_started(
    session: Session, probe_id: str, repository: ExecutorRepository | None = None
) -> bool:
    """``requested -> running``; ``False`` when the probe was no longer ``requested``."""
    return (repository or ExecutorRepository()).start_probe(session, probe_id)


def record_probe_result(
    session: Session, probe_id: str, *, outcome: str, reported_model: str | None = None,
    identity_basis: str | None = None, latency_ms: int | None = None,
    http_status: int | None = None, rate_check: str | None = None,
    observed_host_key: str | None = None, detail: str | None = None,
    repository: ExecutorRepository | None = None,
) -> bool:
    """Finish a probe. ``False`` when it had already finished (the api's sweep ended it first):
    a late worker never overwrites ``no_worker`` or ``timeout``. ``detail`` is cut to the 500
    characters the schema allows; the caller scrubs it first and never passes a body."""
    return (repository or ExecutorRepository()).finish_probe(
        session, probe_id, outcome=outcome, reported_model=reported_model,
        identity_basis=identity_basis, latency_ms=latency_ms, http_status=http_status,
        rate_check=rate_check, observed_host_key=observed_host_key,
        detail=None if detail is None else detail[:500],
    )


def request_with_provider_images(body, request, provider):
    from auditmanager.executors.image_input import checked_pngs, add_anthropic_images, add_openai_images
    images = checked_pngs(request)
    clean = dict(body)
    clean.pop("images", None)
    if images:
        clean = add_anthropic_images(clean, images) if provider == "anthropic" else add_openai_images(clean, images)
    return clean
