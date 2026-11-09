"""Executor hosts: the vocabulary, the rules that need no database, and the records (`HOSTS-BACKEND-01`, ADR-0028 decisions 1 to 4, 16).

Pure: no SQL, no I/O, no clock. A *host* is one machine with one agent process and one host token. What the agent last said about
itself is a :class:`HostReport` (providers, the state of each model, the slots, the key file); everything else about the host
-- is it on line, is a model available, is a slot free -- is *derived at read time* from stored facts and never stored:

* the report snapshot (written only when its content changes: :meth:`HostReport.change_key`), the token's ``last_seen_at`` (the pulse),
* the «Использовать» journal (the latest event is the switch), the slot journal (the latest event of a provider is the number in force),
* the passive cooldown of a (host, provider, model) (``executor_model_cooldown``).

**Availability** (ADR-0028 decision 16). A model on a host is available when the host is enabled, its pulse is at most
:data:`HEARTBEAT_FRESH_SECONDS` old, the provider's login is present, the model is verified and the pair is not cooling down.
:func:`model_reasons` returns every reason that fails, in :data:`REASON_ORDER`; ``at_capacity`` is not one of them (a model whose
every slot is taken is *busy*, not unavailable).

**The capacity pool.** The unit of capacity is the pair (run, ``capacity_pool``) where the pool is ``<host_id>:<provider>`` and the
number of units is the slots in force (:func:`slots_in_force`): the administrator's latest slot event, else the default of the
provider's access (subscription 1, API 2).

**System objects.** For every found quadruple host, provider, access, model that the catalogue serves, the stand keeps one
system-managed ``pull`` connection (:func:`desired_quadruples`); the billing of its revision follows the access
(:func:`billing_of_access`). The group of a (model, access) holds every such connection; only a host being connected or archived revises
it.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Final

from auditmanager.executors.catalogue import Catalogue
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "ACCESSES",
    "ACCESS_API",
    "ACCESS_SUBSCRIPTION",
    "COOLDOWN_REASONS",
    "COOLDOWN_SECONDS",
    "DEFAULT_SLOTS",
    "HEARTBEAT_FRESH_SECONDS",
    "HostReport",
    "MODEL_STATES",
    "ModelFact",
    "PROVIDERS",
    "ProviderFact",
    "Quadruple",
    "REASON_ORDER",
    "SLOTS_MAX",
    "SLOTS_MIN",
    "access_of_billing",
    "billing_of_access",
    "cooldown_reason_of",
    "cooldown_until_for",
    "desired_quadruples",
    "host_state",
    "model_reasons",
    "model_state",
    "normalise_host_report",
    "pair_group_name",
    "pool_of",
    "slots_in_force",
    "split_pool",
]

PROVIDERS: Final[tuple[str, ...]] = ("claude_code", "codex", "anthropic_api", "openai_api", "openrouter_api")
ACCESS_SUBSCRIPTION: Final[str] = "subscription"
ACCESS_API: Final[str] = "api"
ACCESSES: Final[tuple[str, ...]] = (ACCESS_SUBSCRIPTION, ACCESS_API)
#: The direct API providers are ``api`` access only; a CLI is ``subscription`` or ``api`` by the login it holds.
_API_ONLY_PROVIDERS: Final[frozenset[str]] = frozenset({"anthropic_api", "openai_api", "openrouter_api"})
AUTH_STATES: Final[tuple[str, ...]] = ("valid", "login_required", "unknown")
MODEL_STATES: Final[tuple[str, ...]] = ("verified", "not_verified", "failed")
#: How old the host's pulse may be for the host to be on line: the figure of ``executors.repository.RUNNER_ONLINE_SECONDS``
#: (decision 16: a pulse older than this is no pulse).
HEARTBEAT_FRESH_SECONDS: Final[int] = 120
#: A real refusal (access, quota, no such model) takes the pair out of availability for this long, or until a changed report.
COOLDOWN_SECONDS: Final[int] = 15 * 60
COOLDOWN_REASONS: Final[tuple[str, ...]] = ("access_denied", "quota_exceeded", "model_not_found")
#: Slots per provider and host (``SLOTS_MIN`` to ``SLOTS_MAX`` is ``ck_executor_host_slot_event_slots``); the default is by access.
SLOTS_MIN: Final[int] = 1
SLOTS_MAX: Final[int] = 16
DEFAULT_SLOTS: Final[Mapping[str, int]] = {ACCESS_SUBSCRIPTION: 1, ACCESS_API: 2}

#: ``ModelUnavailableReason`` of the contract, in the order a list of reasons is given.
REASON_HOST_DISABLED: Final[str] = "host_disabled"
REASON_HOST_OFFLINE: Final[str] = "host_offline"
REASON_LOGIN_REQUIRED: Final[str] = "login_required"
REASON_MODEL_NOT_VERIFIED: Final[str] = "model_not_verified"
REASON_MODEL_COOLING_DOWN: Final[str] = "model_cooling_down"
REASON_NOT_ON_ANY_SERVER: Final[str] = "not_on_any_server"
REASON_ORDER: Final[tuple[str, ...]] = (
    REASON_HOST_DISABLED, REASON_HOST_OFFLINE, REASON_LOGIN_REQUIRED, REASON_MODEL_NOT_VERIFIED,
    REASON_MODEL_COOLING_DOWN, REASON_NOT_ON_ANY_SERVER,
)

_FAILURE_CODE: Final[re.Pattern[str]] = re.compile(r"[a-z][a-z0-9_]{0,63}")
_CLI_VERSION: Final[re.Pattern[str]] = re.compile(r"[0-9A-Za-z][0-9A-Za-z._+-]{0,63}")
_MODEL_ID: Final[re.Pattern[str]] = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}")
_POOL: Final[re.Pattern[str]] = re.compile(r"(exh_[0-9A-HJKMNP-TV-Z]{26}):([a-z_]+)")
#: The failure codes the agent uses for a host's access, grouped into the three cooldown reasons (RUNNER_API 10.10 item 5).
_COOLDOWN_BY_FAILURE: Final[Mapping[str, str]] = {
    "quota_exceeded": "quota_exceeded", "rate_limited": "quota_exceeded",
    "auth_failed": "access_denied", "login_required": "access_denied", "access_denied": "access_denied",
    "model_not_found": "model_not_found", "model_not_available": "model_not_found",
}


# --- records ------------------------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ModelFact:
    """One model of a provider as the agent last checked it."""

    model_id: str
    state: str
    checked_at: str
    failure_code: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderFact:
    """One provider found on the host: how it is paid for, whether it is logged in and the state of each catalogue model on it."""

    provider: str
    access: str
    auth_state: str
    cli_version: str | None
    accept_images: bool | None
    models: tuple[ModelFact, ...]

    def model(self, model_id: str) -> ModelFact | None:
        return next((item for item in self.models if item.model_id == model_id), None)


@dataclass(frozen=True, slots=True)
class HostReport:
    """A validated host report: nothing in it is free text. ``slots`` is what the agent is configured with (informational: the
    stand's slots are the journal's); ``key_file`` is the diagnostic state of the service key file."""

    agent_version: str
    providers: tuple[ProviderFact, ...]
    slots: Mapping[str, int]
    key_file: Mapping[str, str] | None = None

    def provider(self, provider: str, access: str | None = None) -> ProviderFact | None:
        return next((item for item in self.providers
                     if item.provider == provider and (access is None or item.access == access)), None)

    def change_key(self) -> str:
        """The digest of what a *change* is: everything but the instants (``checked_at``). A report with the same key as the stored
        one is not written (decision 16: «снимок пишется только при изменении»)."""
        body = {
            "agent_version": self.agent_version,
            "providers": [
                {"provider": item.provider, "access": item.access, "auth_state": item.auth_state,
                 "cli_version": item.cli_version, "accept_images": item.accept_images,
                 "models": [{"model_id": model.model_id, "state": model.state, "failure_code": model.failure_code}
                            for model in item.models]}
                for item in self.providers
            ],
            "slots": dict(sorted(self.slots.items())),
            "key_file": None if self.key_file is None else dict(sorted(self.key_file.items())),
        }
        return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()

    def providers_json(self) -> list[dict[str, Any]]:
        """The providers as stored (``executor_host_report.providers``): no key, no path."""
        found: list[dict[str, Any]] = []
        for item in self.providers:
            row: dict[str, Any] = {
                "provider": item.provider, "access": item.access, "auth_state": item.auth_state,
                "models": [
                    {"model_id": model.model_id, "state": model.state, "checked_at": model.checked_at,
                     **({} if model.failure_code is None else {"failure_code": model.failure_code})}
                    for model in item.models
                ],
            }
            if item.cli_version is not None:
                row["cli_version"] = item.cli_version
            if item.accept_images is not None:
                row["accept_images"] = item.accept_images
            found.append(row)
        return found

    @classmethod
    def from_stored(cls, *, agent_version: str, providers: Any, slots: Any) -> HostReport:
        """The report as ``executor_host_report`` holds it (already validated when it was written)."""
        return cls(
            agent_version=agent_version,
            providers=tuple(_provider_from_stored(item) for item in providers),
            slots={str(key): int(value) for key, value in dict(slots).items()},
        )


@dataclass(frozen=True, slots=True, order=True)
class Quadruple:
    """The key of a system connection: a provider on a host with an access serving one model. Ordered for a stable write."""

    provider: str
    access: str
    model_id: str


def _provider_from_stored(raw: Mapping[str, Any]) -> ProviderFact:
    return ProviderFact(
        provider=str(raw["provider"]), access=str(raw["access"]), auth_state=str(raw["auth_state"]),
        cli_version=raw.get("cli_version"), accept_images=raw.get("accept_images"),
        models=tuple(
            ModelFact(model_id=str(model["model_id"]), state=str(model["state"]),
                      checked_at=str(model["checked_at"]), failure_code=model.get("failure_code"))
            for model in raw.get("models", ())
        ),
    )


# --- pools and accesses ------------------------------------------------------------------------------------


def pool_of(host_id: str, provider: str) -> str:
    """``<host_id>:<provider>``: the capacity pool, the form ``ck_executor_connection_pool`` holds."""
    return f"{host_id}:{provider}"


def split_pool(pool: str) -> tuple[str, str]:
    """``(host_id, provider)`` of a pool; ``ValueError`` for text that is not one."""
    found = _POOL.fullmatch(pool)
    if found is None:
        raise ValueError("a capacity pool is <host_id>:<provider>")
    return found.group(1), found.group(2)


def pair_group_name(model_id: str, access: str) -> str:
    """The display name of the system group of a (model, access) pair: ``<model> · <access>`` (the name an administrator would never type)."""
    return f"{model_id} · {access}"[:120]


def billing_of_access(access: str) -> str:
    """``not_metered`` for a subscription, ``metered`` for an API key (ADR-0028 decision 2)."""
    if access not in ACCESSES:
        raise ValueError("an access is subscription or api")
    return "not_metered" if access == ACCESS_SUBSCRIPTION else "metered"


def access_of_billing(billing: str) -> str:
    if billing not in ("metered", "not_metered"):
        raise ValueError("a billing is metered or not_metered")
    return ACCESS_SUBSCRIPTION if billing == "not_metered" else ACCESS_API


def slots_in_force(provider_access: str | None, journal: int | None) -> int:
    """The slots of a provider on a host: the administrator's latest event when there is one, else the default of the access the
    current report gives the provider (1 for a provider the report no longer names: nothing is assumed beyond one)."""
    if journal is not None:
        if not SLOTS_MIN <= journal <= SLOTS_MAX:
            raise ValueError("slots are 1 to 16")
        return journal
    return DEFAULT_SLOTS.get(provider_access or "", SLOTS_MIN)


# --- the report -------------------------------------------------------------------------------------------


def _refused(field_name: str, constraint: str) -> DomainError:
    return DomainError(
        ErrorCode.VALIDATION_FAILED, message="the host report is not acceptable", field=field_name, constraint=constraint,
    )


def _text(value: Any, field_name: str, pattern: re.Pattern[str]) -> str:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise _refused(field_name, "pattern")
    return value


def _instant(value: Any) -> str:
    """``checked_at`` as an RFC 3339 text (a ``datetime`` from the wire model, or the text itself)."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str) and 0 < len(value) <= 64:
        return value
    raise _refused("providers", "checked_at")


def normalise_host_report(
    *, agent_version: Any, providers: Any, slots: Any, key_file: Any = None,
) -> HostReport:
    """The report as the stand will store it, or ``validation_failed`` naming the field.

    Only closed enumerations and bounded strings survive, rebuilt from the accepted fields -- an extra key is dropped by construction
    (no key, no path, no text of a provider's answer can pass). A provider is named once with one access; a direct API provider is
    ``api`` access only; a provider that is not logged in has no verified model; ``slots`` names only providers that are present."""
    version = _text(agent_version, "agent_version", re.compile(r"[0-9A-Za-z][0-9A-Za-z.+_-]{0,63}"))
    if not isinstance(providers, Sequence) or isinstance(providers, (str, bytes)) or len(providers) > 8:
        raise _refused("providers", "length")
    found: list[ProviderFact] = []
    seen: set[str] = set()
    for item in providers:
        if not isinstance(item, Mapping):
            raise _refused("providers", "type")
        name, access, auth = _enum(item.get("provider")), _enum(item.get("access")), _enum(item.get("auth_state"))
        if name not in PROVIDERS:
            raise _refused("providers", "enum")
        if access not in ACCESSES or (name in _API_ONLY_PROVIDERS and access != ACCESS_API):
            raise _refused("providers", "access")
        if auth not in AUTH_STATES:
            raise _refused("providers", "auth_state")
        if name in seen:
            raise _refused("providers", "unique")
        seen.add(name)
        cli_version = item.get("cli_version")
        if cli_version is not None:
            cli_version = _text(cli_version, "providers", _CLI_VERSION)
        accept_images = item.get("accept_images")
        if accept_images is not None and not isinstance(accept_images, bool):
            raise _refused("providers", "accept_images")
        raw_models = item.get("models", ())
        if not isinstance(raw_models, Sequence) or isinstance(raw_models, (str, bytes)) or len(raw_models) > 16:
            raise _refused("providers", "models")
        models: list[ModelFact] = []
        model_ids: set[str] = set()
        for raw in raw_models:
            if not isinstance(raw, Mapping):
                raise _refused("providers", "models")
            model_id = _text(raw.get("model_id"), "providers", _MODEL_ID)
            state = _enum(raw.get("state"))
            if state not in MODEL_STATES or model_id in model_ids:
                raise _refused("providers", "models")
            model_ids.add(model_id)
            code = raw.get("failure_code")
            if code is not None:
                code = _text(code, "providers", _FAILURE_CODE)
            if (state == "failed") != (code is not None):
                raise _refused("providers", "failure_code")
            if state == "verified" and auth != "valid":
                # a model cannot be verified through a provider that is not logged in
                raise _refused("providers", "verified_without_login")
            models.append(ModelFact(model_id=model_id, state=state, checked_at=_instant(raw.get("checked_at")),
                                    failure_code=code))
        found.append(ProviderFact(
            provider=name, access=access, auth_state=auth, cli_version=cli_version, accept_images=accept_images,
            models=tuple(models)))
    reported_slots: dict[str, int] = {}
    if slots is not None:
        if not isinstance(slots, Mapping):
            raise _refused("slots", "type")
        for key, value in slots.items():
            if key not in seen:
                raise _refused("slots", "provider_not_reported")
            if type(value) is not int or not SLOTS_MIN <= value <= SLOTS_MAX:
                raise _refused("slots", "range")
            reported_slots[str(key)] = value
    key_report: dict[str, str] | None = None
    if key_file is not None:
        if not isinstance(key_file, Mapping) or _enum(key_file.get("state")) not in ("ok", "absent", "ignored"):
            raise _refused("key_file", "enum")
        key_report = {"state": _enum(key_file.get("state"))}
        reason = key_file.get("reason")
        if reason is not None:
            key_report["reason"] = _text(reason, "key_file", _FAILURE_CODE)
    return HostReport(agent_version=version, providers=tuple(found), slots=reported_slots, key_file=key_report)


def _enum(value: Any) -> str:
    """An enumeration member as text: the wire model hands an ``Enum``, a test a plain string."""
    raw = getattr(value, "value", value)
    return raw if isinstance(raw, str) else ""


# --- availability ------------------------------------------------------------------------------------------------


def model_reasons(
    *, enabled: bool, pulse_age_seconds: float | None, provider: ProviderFact | None, model: ModelFact | None,
    cooldown_until: datetime | None, now: datetime,
) -> list[str]:
    """Every reason a model cannot be used on a host now, in :data:`REASON_ORDER`; an empty list is available.

    ``pulse_age_seconds`` is ``None`` for a host that never reported. ``provider`` and ``model`` are ``None`` when the current report
    does not name them (a provider or a model that is gone): that is ``model_not_verified``, and nothing is assumed."""
    reasons: list[str] = []
    if not enabled:
        reasons.append(REASON_HOST_DISABLED)
    if pulse_age_seconds is None or pulse_age_seconds > HEARTBEAT_FRESH_SECONDS:
        reasons.append(REASON_HOST_OFFLINE)
    if provider is not None and provider.auth_state == "login_required":
        reasons.append(REASON_LOGIN_REQUIRED)
    if model is None or model.state != "verified":
        reasons.append(REASON_MODEL_NOT_VERIFIED)
    if cooldown_until is not None and cooldown_until > now:
        reasons.append(REASON_MODEL_COOLING_DOWN)
    return reasons


def model_state(reasons: Collection[str], *, pool_full: bool) -> str:
    """``available``, ``busy`` (no reason, every slot of the pool is taken) or ``unavailable``."""
    if reasons:
        return "unavailable"
    return "busy" if pool_full else "available"


def host_state(*, pulse_age_seconds: float | None, slots_total: int, slots_in_use: int) -> str:
    """``offline`` (no pulse within the window, or never), ``busy`` (on line, every slot in use) or ``online``."""
    if pulse_age_seconds is None or pulse_age_seconds > HEARTBEAT_FRESH_SECONDS:
        return "offline"
    if slots_total > 0 and slots_in_use >= slots_total:
        return "busy"
    return "online"


def cooldown_reason_of(failure: str) -> str | None:
    """The cooldown reason a runner's failure word names, or ``None`` when the failure is not about the host's access (a timeout, a
    bad answer, a lost claim take no model out of service). The word is the first of ``<code>: <detail>`` (RUNNER_API 2.4)."""
    word = failure.split(":", 1)[0].strip().lower()
    return _COOLDOWN_BY_FAILURE.get(word)


def cooldown_until_for(now: datetime) -> datetime:
    return now + timedelta(seconds=COOLDOWN_SECONDS)


# --- system objects ---------------------------------------------------------------------------------------


def desired_quadruples(report: HostReport, catalogue: Catalogue) -> list[Quadruple]:
    """The system connections the report calls for: every (provider, access, model) the report names whose model the catalogue serves
    with that provider and access. Verified or not -- composition is what is found; eligibility is what decides use. Sorted."""
    wanted: set[Quadruple] = set()
    for provider in report.providers:
        for model in provider.models:
            if catalogue.serves(provider.provider, model.model_id, provider.access):
                wanted.add(Quadruple(provider.provider, provider.access, model.model_id))
    return sorted(wanted)


def providers_of(quadruples: Iterable[Quadruple]) -> set[str]:
    return {item.provider for item in quadruples}
