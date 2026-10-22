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
import re
import urllib.parse
from collections.abc import Collection, Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Final

from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "API_FLAVOURS",
    "BILLINGS",
    "IDENTITY_BASES",
    "IDENTITY_BASIS_BY_KIND",
    "KINDS",
    "PROBE_RUNNING_MARGIN_SECONDS",
    "PROBE_UNTAKEN_SECONDS",
    "SERVES",
    "PROBE_OUTCOMES",
    "PURPOSES",
    "PURPOSES_BY_KIND",
    "RATE_CHECKS",
    "TRANSPORTS",
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
    "refuse_purpose",
    "validate_settings",
]

KINDS: Final[tuple[str, ...]] = ("http_api", "ssh_command", "pull")
#: Today exactly one run stage calls a model (plan section 2.2).
WORK_KINDS: Final[tuple[str, ...]] = ("text_analysis",)
#: Which connection kinds can serve which kind of model work.
SERVES: Final[Mapping[str, frozenset[str]]] = {"text_analysis": frozenset(KINDS)}
API_FLAVOURS: Final[tuple[str, ...]] = ("openai_chat", "anthropic_messages")
TRANSPORTS: Final[tuple[str, ...]] = ("direct", "vpn", "ssh_tunnel")
SSH_PROFILES: Final[tuple[str, ...]] = ("claude_code_headless", "custom_command")
PULL_CLIENTS: Final[tuple[str, ...]] = ("claude_code_session", "agent")
BILLINGS: Final[tuple[str, ...]] = ("metered", "not_metered")
PURPOSES: Final[tuple[str, ...]] = ("api_key", "ssh_private_key")
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
#: A probe nobody takes in this long ends as ``no_worker``.
PROBE_UNTAKEN_SECONDS: Final[int] = 120
#: A ``running`` probe ends by its own timeout plus this margin, if its worker died.
PROBE_RUNNING_MARGIN_SECONDS: Final[int] = 30

#: Which secrets a kind can hold. ``pull`` keeps no sealed secret: its runner tokens (a later
#: slice) are stored as one-way hashes and shown once.
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


@dataclass(frozen=True, slots=True)
class ConnectionRecord:
    connection_id: str
    kind: str
    display_name: str
    created_at: datetime
    created_by: str
    archived_at: datetime | None = None
    archived_by: str | None = None


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
