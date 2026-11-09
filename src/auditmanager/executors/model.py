"""Executor connections: the vocabulary, the settings rules per kind, and the records.

`EXEC-SEAL-01` (`R-143`). Pure: no SQL, no I/O. A *connection* is where a process sends model
work; a *revision* is one immutable set of its non-secret settings; the rules below say which
settings a kind takes. A secret is never a field here: it exists as ciphertext in
``executor_secret`` and as plaintext only inside the worker, for the length of one call.

Refusals use the catalogue's existing codes and their existing detail keys only
(``contracts/domain/v1/error-codes.json``): ``validation_failed`` carries ``field`` and
``constraint``, ``conflict`` carries ``conflict_reason`` and ``dependency_unavailable``
carries ``dependency``. A detail never contains a setting's value.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import ipaddress
import re
import urllib.parse
from collections.abc import Collection, Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Final

from auditmanager.executors.destinations import (
    DestinationPolicy,
    DestinationRefused,
    DestinationUnresolvable,
)
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "AGENT_INSTALL_ACCESSES",
    "AGENT_INSTALL_FAILURES",
    "AGENT_INSTALL_STATES",
    "API_FLAVOURS",
    "BILLINGS",
    "BINDING_BOUND",
    "BINDING_FROZEN_AT_START",
    "BINDING_PENDING",
    "BINDING_STATES",
    "CONFLICT_ENROLLMENT_REDEEMED",
    "CONFLICT_ENROLLMENT_SHOWN_ONCE",
    "CONFLICT_GROUP_ARCHIVED",
    "CONFLICT_GROUP_NAME_IN_USE",
    "CONFLICT_GROUP_ROUTED",
    "CONFLICT_HOST_KEY_CHANGED",
    "CONFLICT_INSTALL_IN_PROGRESS",
    "CONFLICT_INSTALL_NOT_AWAITING_HOST_KEY",
    "CONFLICT_PREVIEW_STALE",
    "CONFLICT_ROUTING_MODE_RULES",
    "CONFLICT_ROUTING_MODE_UNCHANGED",
    "CONSTRAINT_BELOW_MAX_ACTIVE_RUNS",
    "CONSTRAINT_CAPACITY_NOT_SUPPORTED_FOR_KIND",
    "CONSTRAINT_CONFLICTS_WITH_EXECUTOR_CONNECTION_ID",
    "CONSTRAINT_CONFLICTS_WITH_PRESET_ID",
    "CONSTRAINT_ENVIRONMENT_SOURCE",
    "CONSTRAINT_KIND_NOT_PULL",
    "CONSTRAINT_MAPPING_ENTRY_NOT_READY",
    "CONSTRAINT_MAPPING_NOT_ACCEPTED",
    "CONSTRAINT_MAPPING_REQUIRED",
    "CONSTRAINT_MAPPING_WORK_KIND_REPEATED",
    "CONSTRAINT_MEMBER_BILLING_MISMATCH",
    "CONSTRAINT_MEMBER_KIND_NOT_SERVED",
    "CONSTRAINT_MEMBER_MODEL_MISMATCH",
    "CONSTRAINT_MEMBER_PIN_MISMATCH",
    "CONSTRAINT_MEMBER_REPEATED",
    "CONSTRAINT_MEMBER_REVISION_NOT_OF_CONNECTION",
    "CONSTRAINT_PACKAGE_VERSION_UNKNOWN",
    "CONSTRAINT_PREVIEW_DIGEST_REQUIRED",
    "CONSTRAINT_PRIVATE_KEY_NOT_ACCEPTED",
    "CONSTRAINT_PRIVATE_KEY_REQUIRED",
    "CONSTRAINT_RANGE",
    "CONSTRAINT_TIE_BREAK_ORDER_REPEATED",
    "CONSTRAINT_UNKNOWN_EXECUTOR_CONNECTION",
    "CONSTRAINT_UNKNOWN_EXECUTOR_GROUP",
    "DEFAULT_MAX_ACTIVE_RUNS",
    "DEPENDENCY_AGENT_PACKAGE",
    "DEPENDENCY_NO_RULE_FOR_WORK_KIND",
    "DEPENDENCY_PUBLIC_ORIGIN",
    "ENROLLMENT_STATES",
    "GENERIC_PURPOSES",
    "GROUP_MEMBERS_MAX",
    "GROUP_MEMBERS_MIN",
    "GROUP_MEMBER_ISSUES",
    "GROUP_STRATEGIES",
    "GROUP_STRATEGY_LEAST_LOADED",
    "IDENTITY_BASES",
    "IDENTITY_BASIS_BY_KIND",
    "INSTALL_PURPOSES",
    "KINDS",
    "MAX_ACTIVE_RUNS_MAX",
    "MAX_ACTIVE_RUNS_MIN",
    "PROBE_OUTCOMES",
    "PROBE_RUNNING_MARGIN_SECONDS",
    "PROBE_UNTAKEN_SECONDS",
    "PULL_PROBE_WINDOW_SECONDS",
    "PURPOSES",
    "PURPOSES_BY_KIND",
    "QUEUE_REASONS",
    "RATE_CHECKS",
    "ROUTING_MODES",
    "ROUTING_MODE_LEGACY",
    "ROUTING_MODE_RULES",
    "ROUTING_PREVIEW_ISSUES",
    "ROUTING_PREVIEW_STATUSES",
    "RUNNER_CLI_AUTH_STATES",
    "RUNNER_CLI_NAMES",
    "RUNNER_EXECUTION_PROFILES",
    "RUNNER_FEATURES",
    "SERVES",
    "TRANSPORTS",
    "WAIT_REASONS",
    "WAIT_REASON_NEEDS_RECONSENT",
    "WORK_KINDS",
    "ConnectionRecord",
    "ConnectionSummary",
    "ProbeRecord",
    "ResolvedRoute",
    "RevisionSettings",
    "RevisionRecord",
    "RouteRecord",
    "SecretRecord",
    "destination_for",
    "host_key_fingerprint",
    "normalise_origin",
    "refuse_plain_http",
    "refuse_purpose",
    "refuse_system_object",
    "validate_settings",
]

KINDS: Final[tuple[str, ...]] = ("http_api", "ssh_command", "pull")
#: One run stage calls a model (plan section 2.2), and the version comparison has four kinds of model
#: work of its own (`CMP-SEAL-C2`, ADR-0025 decision 17): the AI check of doubtful pairs, the AI
#: description of changes, the comparison of whole specifications and the report. `comparison_stage_review`
#: joins with `CMP-SEAL-C4`.
WORK_KINDS: Final[tuple[str, ...]] = (
    "text_analysis",
    "comparison_pair_check",
    "comparison_sheet_changes",
    "comparison_spec",
    "comparison_report",
    "comparison_stage_review",
)
#: Which connection kinds can serve which kind of model work.
SERVES: Final[Mapping[str, frozenset[str]]] = {kind: frozenset(KINDS) for kind in WORK_KINDS}
API_FLAVOURS: Final[tuple[str, ...]] = ("openai_chat", "anthropic_messages")
TRANSPORTS: Final[tuple[str, ...]] = ("direct", "vpn", "ssh_tunnel")
SSH_PROFILES: Final[tuple[str, ...]] = ("claude_code_headless", "custom_command")
PULL_CLIENTS: Final[tuple[str, ...]] = ("claude_code_session", "agent")
BILLINGS: Final[tuple[str, ...]] = ("metered", "not_metered")
#: The purposes a connection's own secret can have: what ``setExecutorSecret`` takes
#: (``ExecutorSecretPurpose`` in the contract names exactly these two) and ``PURPOSES_BY_KIND`` distributes.
GENERIC_PURPOSES: Final[tuple[str, ...]] = ("api_key", "ssh_private_key")
#: `EXEC2-SEAL-1` (ADR-0026 decision 7). The sealed SSH key of an agent install session. It lives in
#: ``executor_secret`` (migration ``0046``) and belongs to the session that
#: ``executor_agent_install.key_secret_id`` names, **not** to a connection kind: it is in no tuple of
#: :data:`PURPOSES_BY_KIND`, so :func:`refuse_purpose` refuses it for every kind (``purpose_not_for_kind``) and the
#: generic ``setExecutorSecret`` path cannot write one. The contract's request enum does not carry it either.
INSTALL_PURPOSES: Final[tuple[str, ...]] = ("agent_install_key",)
#: Every value of ``executor_secret.purpose`` (``ck_executor_secret_purpose``).
PURPOSES: Final[tuple[str, ...]] = GENERIC_PURPOSES + INSTALL_PURPOSES
RATE_CHECKS: Final[tuple[str, ...]] = ("checked", "not_reported", "mismatch", "not_metered")
PROBE_OUTCOMES: Final[tuple[str, ...]] = (
    "ok", "ip_refused", "credential_refused", "model_mismatch", "rate_mismatch", "timeout",
    "unreachable", "protocol_error", "secret_unreadable", "host_key_unpinned",
    "host_key_changed", "no_runner_online", "destination_refused", "kind_not_served",
    "no_worker",
)
#: The identity of a call's model: the response named it, or the executor asserted it.
IDENTITY_BASES: Final[tuple[str, ...]] = ("reported", "declared")
#: ``http_api`` and ``ssh_command`` report the model in their answer; ``pull`` declares it.
IDENTITY_BASIS_BY_KIND: Final[Mapping[str, str]] = {
    "http_api": "reported", "ssh_command": "reported", "pull": "declared",
}
#: `EXEC2-SEAL-1` (ADR-0026 decision 1). The capacity of a connection: the most units (a Run in ``leased``,
#: ``running`` or ``retry_wait``, a comparison model call in ``prepared`` or ``sent``) in use at once. Absent
#: on a revision means :data:`DEFAULT_MAX_ACTIVE_RUNS`. The coupled limits of decision 2 are `EXEC2-CAP-01`.
MAX_ACTIVE_RUNS_MIN: Final[int] = 1
MAX_ACTIVE_RUNS_MAX: Final[int] = 16
DEFAULT_MAX_ACTIVE_RUNS: Final[int] = 1
#: Why a queued Run is not running (``RunQueueReason`` in the contract).
QUEUE_REASONS: Final[tuple[str, ...]] = ("executor_at_capacity", "runner_offline")
#: The state of an enrollment grant, derived at read time (``ExecutorEnrollmentState``).
ENROLLMENT_STATES: Final[tuple[str, ...]] = ("pending", "redeemed", "expired", "revoked")
#: An agent install session (``ExecutorAgentInstall*``; ``ck_executor_agent_install_*``).
AGENT_INSTALL_ACCESSES: Final[tuple[str, ...]] = ("generated_key", "pasted_key")
AGENT_INSTALL_STATES: Final[tuple[str, ...]] = (
    "requested", "scanning", "awaiting_host_key", "installing", "succeeded", "failed",
)
AGENT_INSTALL_FAILURES: Final[tuple[str, ...]] = (
    "host_unreachable", "ssh_refused", "host_key_changed", "host_key_not_confirmed",
    "sudo_password_required", "unsupported_platform", "package_unavailable", "install_failed",
    "enrollment_failed", "secret_unreadable", "no_worker", "timed_out",
)
#: What an agent reports about itself (``RunnerCliName``, ``RunnerCliAuthState``,
#: ``RunnerExecutionProfile``, ``RunnerFeature``): closed enumerations, never a credential or a path.
RUNNER_CLI_NAMES: Final[tuple[str, ...]] = ("claude", "codex")
RUNNER_CLI_AUTH_STATES: Final[tuple[str, ...]] = ("valid", "login_required", "unknown")
RUNNER_EXECUTION_PROFILES: Final[tuple[str, ...]] = ("command", "endpoint")
RUNNER_FEATURES: Final[tuple[str, ...]] = ("images",)

#: `EXEC2-SEAL-1`. The typed details of the refusals the stage-1 operations may carry, on the catalogue's
#: existing codes only (ADR-0026 decision 18); ``contracts/domain/v1/error-codes.json`` documents each. A detail
#: names a field or a class and never a value.
#:
#: ``validation_failed`` -- the ``constraint`` of a refusal (the ``field`` is named beside each):
#: the pull ``max_claimed_tasks`` or the ``http_api`` ``max_parallel_calls`` below ``max_active_runs``;
CONSTRAINT_BELOW_MAX_ACTIVE_RUNS: Final[str] = "below_max_active_runs"
#: ``max_active_runs`` above one on an ``ssh_command`` revision before its wrappers isolate invocations;
CONSTRAINT_CAPACITY_NOT_SUPPORTED_FOR_KIND: Final[str] = "capacity_not_supported_for_kind"
#: a value outside its range (``max_active_runs`` is 1 to 16; ``runner.py`` already says the same of a lifetime);
CONSTRAINT_RANGE: Final[str] = "range"
#: an enrollment, an install or an integration-authorisation mark on a connection that is not ``pull``
#: (field ``kind``; ``runner.issue_runner_token`` already says it);
CONSTRAINT_KIND_NOT_PULL: Final[str] = "kind_not_pull"
#: an install with ``pasted_key`` access and no key, or a key sent with ``generated_key`` (field ``private_key``);
CONSTRAINT_PRIVATE_KEY_REQUIRED: Final[str] = "private_key_required"
CONSTRAINT_PRIVATE_KEY_NOT_ACCEPTED: Final[str] = "private_key_not_accepted"
#: a package version the image does not hold (field ``version``).
CONSTRAINT_PACKAGE_VERSION_UNKNOWN: Final[str] = "package_version_unknown"
#: ``conflict`` -- the ``conflict_reason`` of a refusal: a repeat of the key that issued a grant, a secret already
#: exchanged, an install still unfinished, an install not at the host-key confirmation, and a fingerprint other
#: than the observed one. (``connection_archived`` and ``no_revision`` already exist.)
CONFLICT_ENROLLMENT_SHOWN_ONCE: Final[str] = "enrollment_shown_once"
CONFLICT_ENROLLMENT_REDEEMED: Final[str] = "enrollment_redeemed"
CONFLICT_INSTALL_IN_PROGRESS: Final[str] = "install_in_progress"
CONFLICT_INSTALL_NOT_AWAITING_HOST_KEY: Final[str] = "install_not_awaiting_host_key"
CONFLICT_HOST_KEY_CHANGED: Final[str] = "host_key_changed"
#: ``dependency_unavailable`` -- the ``dependency`` of a refusal: the image holds no agent package.
#: (``secrets_public_key_missing`` already exists.)
DEPENDENCY_AGENT_PACKAGE: Final[str] = "agent_package"
#: ``public_origin`` -- ``issueExecutorEnrollment`` on a stand whose configured public origin is absent or malformed.
DEPENDENCY_PUBLIC_ORIGIN: Final[str] = "public_origin"

#: `EXEC2-SEAL-2` (ADR-0026 decisions 10 to 17, contract 1.16.0, migrations ``0047`` and ``0048``). **Vocabulary only:**
#: no statement in this module reads or writes a group, a rule, the routing mode or a binding; the stage-2 and stage-3
#: lanes do, and each stops to the integrator when it needs a value that is not here.
#:
#: Whether the executor of a Run or of a comparison AI job was fixed when it started (``ExecutorBindingState``;
#: ``ck_audit_run_binding_state``, ``ck_comparison_ai_job_binding_state``). The only move is ``pending`` to ``bound``,
#: once, together with the connection revision going from ``NULL`` to a value; ``frozen_at_start`` and ``bound`` are
#: terminal for the machine (``binding_state`` in ``state-machines.json``).
BINDING_FROZEN_AT_START: Final[str] = "frozen_at_start"
BINDING_PENDING: Final[str] = "pending"
BINDING_BOUND: Final[str] = "bound"
BINDING_STATES: Final[tuple[str, ...]] = (BINDING_FROZEN_AT_START, BINDING_PENDING, BINDING_BOUND)
#: Which store decides where new model work goes (``ExecutorRoutingMode``; ``ck_executor_routing_mode_event_mode``).
#: Absent any event the mode is ``legacy``: the table is empty on a database at ``0047``.
ROUTING_MODE_LEGACY: Final[str] = "legacy"
ROUTING_MODE_RULES: Final[str] = "rules"
ROUTING_MODES: Final[tuple[str, ...]] = (ROUTING_MODE_LEGACY, ROUTING_MODE_RULES)
#: How dispatch picks among eligible members; ``least_loaded`` is the only value (``ExecutorGroupStrategy``).
GROUP_STRATEGY_LEAST_LOADED: Final[str] = "least_loaded"
GROUP_STRATEGIES: Final[tuple[str, ...]] = (GROUP_STRATEGY_LEAST_LOADED,)
#: A group revision holds one to sixteen members (``ExecutorGroupRevision.members``); ``tie_break_order`` is 1 to 16.
GROUP_MEMBERS_MIN: Final[int] = 1
GROUP_MEMBERS_MAX: Final[int] = 16
#: Why a member would not be chosen by dispatch (``ExecutorGroupMemberIssue``), in the order one is reported.
GROUP_MEMBER_ISSUES: Final[tuple[str, ...]] = (
    "revision_changed", "connection_archived", "not_served", "probe_not_ok", "runner_offline", "at_capacity",
)
#: What the cut-over would do with a work kind, and why a legacy route cannot become a one-member group
#: (``ExecutorRoutingPreviewStatus``, ``ExecutorRoutingPreviewIssue``).
ROUTING_PREVIEW_STATUSES: Final[tuple[str, ...]] = ("ready", "no_route", "incompatible")
ROUTING_PREVIEW_ISSUES: Final[tuple[str, ...]] = ("connection_archived", "no_revision", "kind_not_served")
#: Why pending work waits, as stored in ``audit_run.wait_reason`` and ``comparison_ai_job.wait_reason`` and as the
#: contract's ``RunQueueReason`` spells it: the two reasons :data:`QUEUE_REASONS` derives at read time, and
#: ``needs_reconsent`` (dispatch found the consent envelope no longer holds and called nothing). :data:`QUEUE_REASONS`
#: itself stays the derived pair, which ``tests/unit/executors/test_capacity_pins.py`` holds equal to the query's.
WAIT_REASON_NEEDS_RECONSENT: Final[str] = "needs_reconsent"
WAIT_REASONS: Final[tuple[str, ...]] = QUEUE_REASONS + (WAIT_REASON_NEEDS_RECONSENT,)
#: The typed details of the refusals the stage-2 and stage-3 operations may carry, on the catalogue's existing codes only
#: (ADR-0026 decision 18); ``contracts/domain/v1/error-codes.json`` documents each.
#:
#: ``validation_failed`` -- ``constraint``, with ``field`` ``members``: a member names a connection that does not exist,
#: a revision that is not of that connection, a connection twice, a tie-break order twice, or a connection whose kind this
#: release does not serve;
CONSTRAINT_UNKNOWN_EXECUTOR_CONNECTION: Final[str] = "unknown_executor_connection"
CONSTRAINT_MEMBER_REVISION_NOT_OF_CONNECTION: Final[str] = "member_revision_not_of_connection"
CONSTRAINT_MEMBER_REPEATED: Final[str] = "member_repeated"
CONSTRAINT_TIE_BREAK_ORDER_REPEATED: Final[str] = "tie_break_order_repeated"
CONSTRAINT_MEMBER_KIND_NOT_SERVED: Final[str] = "member_kind_not_served"
#: with ``field`` ``pin_id``, ``gateway_model`` or ``billing``: a member's revision is not the pin, the model or the billing
#: of the group revision (a group is homogeneous; mixed groups are refused);
CONSTRAINT_MEMBER_PIN_MISMATCH: Final[str] = "member_pin_mismatch"
CONSTRAINT_MEMBER_MODEL_MISMATCH: Final[str] = "member_model_mismatch"
CONSTRAINT_MEMBER_BILLING_MISMATCH: Final[str] = "member_billing_mismatch"
#: with ``field`` ``executor_group_id`` (``startRun``, ``estimateRunCost``): an unknown group, a group together with an
#: executor connection (the value ``preset_id`` already uses) or a preset, and the ``environment`` provider source, which
#: runs no group work;
CONSTRAINT_UNKNOWN_EXECUTOR_GROUP: Final[str] = "unknown_executor_group"
CONSTRAINT_CONFLICTS_WITH_EXECUTOR_CONNECTION_ID: Final[str] = "conflicts_with_executor_connection_id"
CONSTRAINT_CONFLICTS_WITH_PRESET_ID: Final[str] = "conflicts_with_preset_id"
CONSTRAINT_ENVIRONMENT_SOURCE: Final[str] = "environment_source"
#: with ``field`` ``preview_digest`` or ``mapping`` (``setExecutorRoutingMode``).
CONSTRAINT_PREVIEW_DIGEST_REQUIRED: Final[str] = "preview_digest_required"
CONSTRAINT_MAPPING_REQUIRED: Final[str] = "mapping_required"
CONSTRAINT_MAPPING_NOT_ACCEPTED: Final[str] = "mapping_not_accepted"
CONSTRAINT_MAPPING_ENTRY_NOT_READY: Final[str] = "mapping_entry_not_ready"
CONSTRAINT_MAPPING_WORK_KIND_REPEATED: Final[str] = "mapping_work_kind_repeated"
#: ``conflict`` -- ``conflict_reason``: an archived group takes no revision, rule or run; an active group holds the name; a
#: rule still names the group; ``setExecutorRoute`` while the mode is ``rules``; the mode named is the current one; the
#: cut-over preview digest is stale. (``connection_archived`` already exists and applies to an archived member.)
CONFLICT_GROUP_ARCHIVED: Final[str] = "group_archived"
CONFLICT_GROUP_NAME_IN_USE: Final[str] = "group_name_in_use"
CONFLICT_GROUP_ROUTED: Final[str] = "group_routed"
CONFLICT_ROUTING_MODE_RULES: Final[str] = "routing_mode_rules"
CONFLICT_ROUTING_MODE_UNCHANGED: Final[str] = "routing_mode_unchanged"
CONFLICT_PREVIEW_STALE: Final[str] = "preview_stale"
#: ``dependency_unavailable`` -- ``dependency``: a start of a work kind that has no rule while the mode is ``rules``.
DEPENDENCY_NO_RULE_FOR_WORK_KIND: Final[str] = "no_rule_for_work_kind"

#: A probe nobody takes in this long ends as ``no_worker``.
PROBE_UNTAKEN_SECONDS: Final[int] = 120
#: A ``running`` probe ends by its own timeout plus this margin, if its worker died.
PROBE_RUNNING_MARGIN_SECONDS: Final[int] = 30
#: A ``pull`` probe waits for a runner to take a task (120 s) and answer it (120 s); the sweep
#: never ends a running one before that, whatever the revision's own timeout says. Held equal to
#: ``pull.PROBE_CLAIM_SECONDS + pull.PROBE_ANSWER_SECONDS`` by a unit test.
PULL_PROBE_WINDOW_SECONDS: Final[int] = 240

#: Which secrets a kind can hold. ``pull`` keeps no sealed secret: its runner tokens (a later
#: slice) are stored as one-way hashes and shown once. :data:`INSTALL_PURPOSES` is deliberately in none
#: of these tuples (see there).
PURPOSES_BY_KIND: Final[Mapping[str, tuple[str, ...]]] = {
    "http_api": ("api_key", "ssh_private_key"),
    "ssh_command": ("ssh_private_key",),
    "pull": (),
}

_HOST = re.compile(r"[A-Za-z0-9]([A-Za-z0-9.-]{0,251}[A-Za-z0-9])?|\[[0-9A-Fa-f:.]{2,45}\]")
_SSH_USER = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]{0,63}")
_HOST_KEY = re.compile(r"(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp(?:256|384|521)) ([A-Za-z0-9+/=]+)( .{0,200})?")


def _refuse(field_name: str, constraint: str) -> DomainError:
    return DomainError(
        ErrorCode.VALIDATION_FAILED,
        message="the executor settings are not acceptable",
        field=field_name, constraint=constraint,
    )


@dataclass(frozen=True, slots=True)
class RevisionSettings:
    """The non-secret settings of one revision, as the API carries them."""

    pin_id: str
    gateway_model: str
    billing: str
    allow_client_documents: bool
    timeout_seconds: int
    api_flavour: str | None = None
    base_url: str | None = None
    transport: str | None = None
    max_parallel_calls: int | None = None
    ssh_host: str | None = None
    ssh_port: int | None = None
    ssh_user: str | None = None
    host_key: str | None = None
    ssh_profile: str | None = None
    pull_client: str | None = None
    answer_deadline_seconds: int | None = None
    max_claimed_tasks: int | None = None
    #: `EXEC2-SEAL-1`. The capacity of the connection; applies to every kind, so it is in no kind's
    #: required or optional set below. ``None`` reads as :data:`DEFAULT_MAX_ACTIVE_RUNS`.
    max_active_runs: int | None = None


#: Settings by kind: (required, optional). Everything else must be absent.
_REQUIRED: Final[Mapping[str, frozenset[str]]] = {
    "http_api": frozenset({"api_flavour", "base_url", "transport"}),
    "ssh_command": frozenset({"ssh_host", "ssh_port", "ssh_user", "ssh_profile"}),
    "pull": frozenset({"pull_client", "answer_deadline_seconds", "max_claimed_tasks"}),
}
_OPTIONAL: Final[Mapping[str, frozenset[str]]] = {
    "http_api": frozenset({"max_parallel_calls"}),
    "ssh_command": frozenset({"host_key"}),
    "pull": frozenset(),
}
_KIND_FIELDS: Final[frozenset[str]] = frozenset({
    "api_flavour", "base_url", "transport", "max_parallel_calls", "ssh_host", "ssh_port",
    "ssh_user", "host_key", "ssh_profile", "pull_client", "answer_deadline_seconds",
    "max_claimed_tasks",
})
_TUNNEL_REQUIRED: Final[frozenset[str]] = frozenset({"ssh_host", "ssh_port", "ssh_user"})
_TUNNEL_OPTIONAL: Final[frozenset[str]] = frozenset({"host_key"})


def normalise_origin(base_url: str) -> str:
    """``scheme://host:port`` of an ``http`` or ``https`` base URL, lower-cased with the
    scheme's default port made explicit; the path is not part of an origin. Raises the
    ``base_url_invalid`` refusal for anything else: a query or fragment (``proxy.py`` refuses
    them too), credentials in the URL, a missing host or an unparsable port."""
    if "?" in base_url or "#" in base_url or any(ch.isspace() for ch in base_url):
        raise _refuse("base_url", "base_url_invalid")
    if not base_url.startswith(("http://", "https://")):
        raise _refuse("base_url", "base_url_invalid")
    try:
        parts = urllib.parse.urlsplit(base_url)
        port = parts.port
    except ValueError:
        raise _refuse("base_url", "base_url_invalid") from None
    host = parts.hostname
    if not host or parts.username is not None or parts.password is not None:
        raise _refuse("base_url", "base_url_invalid")
    if port is None:
        port = 443 if parts.scheme == "https" else 80
    shown = f"[{host}]" if ":" in host else host
    return f"{parts.scheme}://{shown.lower()}:{port}"


def _never_resolves(host: str, port: int) -> list[str]:
    raise DestinationUnresolvable()


#: The destination rules, asked about a name or a literal address and never about the network:
#: this module is pure, so a name that is not a loopback name is not classified here.
_LITERAL_POLICY: Final[DestinationPolicy] = DestinationPolicy(
    resolver=_never_resolves, networks=lambda: ())


def refuse_plain_http(base_url: str, transport: str | None) -> None:
    """Refuse ``http://`` unless the key's route is not the open internet (`F-15`).

    An ``https://`` URL is always accepted here. A plain ``http://`` URL is accepted only when
    :mod:`~auditmanager.executors.destinations` itself classifies its host as one the key may
    cross unencrypted: a loopback name or address (for ``ssh_tunnel`` that is the remote
    host's own ``localhost``), or -- for ``transport: vpn`` alone, the one transport that module
    admits a private range for -- a private address. A public address, any other transport's
    private address, a link-local or reserved one and a name that is not a loopback name (it
    cannot be classified without resolving it, which this module never does) are refused with
    ``base_url_invalid``. Pure: nothing is resolved and nothing is sent."""
    if not base_url.startswith("http://"):
        return
    host = urllib.parse.urlsplit(base_url).hostname
    if not host:
        raise _refuse("base_url", "base_url_invalid")
    try:
        addresses = _LITERAL_POLICY.check(host, 80, transport=transport or "direct")
    except DestinationRefused as refused:
        if refused.category == "loopback":
            return
        raise _refuse("base_url", "base_url_invalid") from None
    except DestinationUnresolvable:
        raise _refuse("base_url", "base_url_invalid") from None
    if any(_LITERAL_POLICY.classify(ipaddress.ip_address(item)) != "private_range"
           for item in addresses):
        raise _refuse("base_url", "base_url_invalid")


def _ssh_endpoint(settings: RevisionSettings) -> str:
    assert settings.ssh_host is not None and settings.ssh_port is not None
    return f"{settings.ssh_host.lower()}:{settings.ssh_port}"


def destination_for(kind: str, settings: RevisionSettings, purpose: str) -> str:
    """The whole route a secret of ``purpose`` travels, ``transport|ssh_endpoint|origin``.

    * an ``http_api`` key: ``direct||scheme://host:port`` or ``vpn||scheme://host:port``, and
      ``ssh_tunnel|host:port|scheme://host:port`` through a tunnel, so a changed SSH endpoint
      unbinds the key even when the tunnelled origin stays ``http://localhost:11434``;
    * an SSH key: ``ssh_command|host:port|`` for a command connection and
      ``ssh_tunnel|host:port|`` for the tunnel of an ``http_api``.

    The worker recomputes this from the revision it is about to call; it never reads it from
    the stored row.
    """
    if purpose == "api_key" and kind == "http_api":
        assert settings.base_url is not None and settings.transport is not None
        origin = normalise_origin(settings.base_url)
        refuse_plain_http(settings.base_url, settings.transport)
        if settings.transport == "ssh_tunnel":
            return f"ssh_tunnel|{_ssh_endpoint(settings)}|{origin}"
        return f"{settings.transport}||{origin}"
    if purpose == "ssh_private_key":
        if kind == "ssh_command":
            return f"ssh_command|{_ssh_endpoint(settings)}|"
        if kind == "http_api" and settings.transport == "ssh_tunnel":
            return f"ssh_tunnel|{_ssh_endpoint(settings)}|"
    raise _refuse("purpose", "purpose_not_for_kind")


def host_key_fingerprint(host_key: str) -> str:
    """``SHA256:<base64 without padding>`` of the key blob in a public key line: what
    ``ssh-keygen -l`` prints, derived from the stored line and never stored beside it."""
    match = _HOST_KEY.fullmatch(host_key.strip())
    if match is None:
        raise _refuse("host_key", "host_key_invalid")
    try:
        blob = base64.b64decode(match.group(2), validate=True)
    except (binascii.Error, ValueError):
        raise _refuse("host_key", "host_key_invalid") from None
    digest = base64.b64encode(hashlib.sha256(blob).digest()).decode("ascii").rstrip("=")
    return f"SHA256:{digest}"


def validate_settings(
    kind: str, settings: RevisionSettings, *, pinned_model_ids: Collection[str]
) -> RevisionSettings:
    """Refuse a revision whose settings do not fit its kind, or whose model is not pinned.

    Returns the settings with the host key trimmed to one line. The refusals carry ``field``
    and ``constraint`` only, never a value."""
    if settings.pin_id not in pinned_model_ids:
        raise _refuse("pin_id", "model_not_pinned")
    if settings.billing not in BILLINGS:
        raise _refuse("billing", "enum")
    if settings.max_active_runs is not None and not (
        MAX_ACTIVE_RUNS_MIN <= settings.max_active_runs <= MAX_ACTIVE_RUNS_MAX
    ):
        raise _refuse("max_active_runs", CONSTRAINT_RANGE)
    required = set(_REQUIRED[kind])
    optional = set(_OPTIONAL[kind])
    if kind == "http_api" and settings.transport == "ssh_tunnel":
        required |= _TUNNEL_REQUIRED
        optional |= _TUNNEL_OPTIONAL
    allowed = required | optional
    for name in sorted(_KIND_FIELDS):
        value = getattr(settings, name)
        if name in required and value is None:
            raise _refuse(name, "field_required_for_kind")
        if name not in allowed and value is not None:
            raise _refuse(name, "field_not_for_kind")
    if settings.base_url is not None:
        normalise_origin(settings.base_url)
        refuse_plain_http(settings.base_url, settings.transport)
    if settings.transport is not None and settings.transport not in TRANSPORTS:
        raise _refuse("transport", "enum")
    if settings.ssh_host is not None and not _HOST.fullmatch(settings.ssh_host):
        raise _refuse("ssh_host", "pattern")
    if settings.ssh_user is not None and not _SSH_USER.fullmatch(settings.ssh_user):
        raise _refuse("ssh_user", "pattern")
    if settings.host_key is not None:
        host_key_fingerprint(settings.host_key)
        return replace(settings, host_key=settings.host_key.strip())
    return settings


def refuse_purpose(kind: str, purpose: str) -> None:
    """``purpose_not_for_kind`` unless the kind holds a secret of that purpose."""
    if purpose not in PURPOSES_BY_KIND[kind]:
        raise _refuse("purpose", "purpose_not_for_kind")


def refuse_system_object(aggregate_type: str = "ExecutorConnection") -> DomainError:
    """``conflict`` / ``system_managed``: the stand keeps this connection or group for a host (`HOSTS-BACKEND-01`, ADR-0028 decisions 2 and 3); it
    is never revised, archived, keyed, probed, routed, enrolled or named by a rule by hand. Nothing about it is echoed."""
    return DomainError(
        ErrorCode.CONFLICT, message="this object is kept by the stand for a server and cannot be changed by hand",
        conflict_reason="system_managed", aggregate_type=aggregate_type,
    )


@dataclass(frozen=True, slots=True)
class ConnectionRecord:
    connection_id: str
    kind: str
    display_name: str
    created_at: datetime
    created_by: str
    archived_at: datetime | None = None
    archived_by: str | None = None
    #: `HOSTS-BACKEND-01` (ADR-0028 decision 2): a connection the stand keeps for one found (host, provider, access, model); the user
    #: never sees, revises or archives it. ``host_id`` and ``capacity_pool`` are set exactly then (``ck_executor_connection_pool``).
    system_managed: bool = False
    host_id: str | None = None
    capacity_pool: str | None = None


@dataclass(frozen=True, slots=True)
class RevisionRecord:
    revision_id: str
    connection_id: str
    revision_no: int
    created_at: datetime
    created_by: str
    settings: RevisionSettings


@dataclass(frozen=True, slots=True)
class SecretRecord:
    """Metadata of one sealed secret. The ciphertext is not a field: only the repository's
    ``open`` path ever reads it."""

    secret_id: str
    connection_id: str
    purpose: str
    kid: str
    destination: str
    last4: str
    public_material: str | None
    set_at: datetime
    set_by: str
    replaced_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ProbeRecord:
    probe_id: str
    connection_id: str
    revision_id: str
    secret_id: str | None
    state: str
    outcome: str | None
    reported_model: str | None
    identity_basis: str | None
    latency_ms: int | None
    http_status: int | None
    rate_check: str | None
    observed_host_key: str | None
    detail: str | None
    requested_at: datetime
    requested_by: str
    started_at: datetime | None
    finished_at: datetime | None


@dataclass(frozen=True, slots=True)
class RouteRecord:
    route_event_id: str
    work_kind: str
    route_no: int
    primary_connection_id: str
    standby_connection_id: str | None
    set_at: datetime
    set_by: str


@dataclass(frozen=True, slots=True)
class ResolvedRoute:
    """What a run start resolves a kind of model work to: the route with the current revision
    of each side (``None`` when a side is archived or has no revision)."""

    work_kind: str
    primary: RevisionRecord | None
    standby: RevisionRecord | None
    route: RouteRecord


@dataclass(frozen=True, slots=True)
class ConnectionSummary:
    """A connection with what a list shows: its current revision and current secrets, and the
    kinds of model work whose route names it."""

    connection: ConnectionRecord
    current_revision: RevisionRecord | None
    secrets: tuple[SecretRecord, ...] = ()
    routed_work_kinds: tuple[str, ...] = ()
