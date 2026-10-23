"""The registry of connection kinds this release can serve: one adapter factory per kind.

`EXEC-HTTP-01` (`R-143`, plan section 3). **This is the seam a new kind plugs into.**
``EXEC-PULL-01`` and ``EXEC-SSH-01`` call :func:`register_adapter_factory` for their kind; nothing
else in the run path changes for them. A kind with no factory is *not served*: it can be created,
its probe ends ``kind_not_served``, and a route to it is refused with ``validation_failed``
(``constraint: kind_not_served``). A factory receives the revision, the **opened** secret and the
Attempt's context, and returns an object that satisfies the model-adapter seam.

A **channel kind** (``pull``, `EXEC-PULL-01`) is the other shape: the remote party calls the stand,
so there is no key to open and no address to reach. It is registered with
:func:`register_channel_kind`; its factory is handed the revision, the Attempt's context and the
:class:`KindRuntime` (the database access the worker already holds) instead of a secret.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from auditmanager.executors.destinations import DestinationPolicy
from auditmanager.executors.http_adapter import build_http_adapter
from auditmanager.executors.model import RevisionRecord
from auditmanager.executors.pull import build_pull_adapter
from auditmanager.executors.ssh_adapter import build_ssh_command_adapter
from auditmanager.executors.ssh_tunnel_adapter import build_ssh_tunnel_adapter

__all__ = [
    "KindAdapter",
    "AdapterSecrets",
    "KindRuntime",
    "adapter_for",
    "register_adapter_factory",
    "register_channel_kind",
    "unregister_adapter_factory",
]

#: ``factory(revision, secret_value, policy, attempt_context) -> adapter``
@dataclass(frozen=True, slots=True, repr=False)
class AdapterSecrets:
    """The opened primary secret and any additional secrets of one revision."""

    primary: str
    additional: dict[str, str]


AdapterFactory = Callable[[RevisionRecord, Any, DestinationPolicy, Any], Any]


@dataclass(frozen=True, slots=True)
class KindRuntime:
    """What a channel kind's adapter needs of the worker that serves the Attempt: short database
    transactions, and the engine a ``LISTEN`` connection is taken from (``None`` polls)."""

    session_factory: Callable[[], Session]
    engine: Engine | None = None


#: ``channel(revision, attempt_context, runtime) -> adapter``
ChannelFactory = Callable[[RevisionRecord, Any, KindRuntime], Any]


@dataclass(frozen=True, slots=True)
class KindAdapter:
    kind: str
    factory: AdapterFactory
    #: The purpose of the secret the factory is handed (``api_key`` or ``ssh_private_key``);
    #: ``None`` for a channel kind, which keeps no sealed secret.
    purpose: str | None
    #: Whether *this revision* of the kind is served (a transport a later slice adds, say).
    serves: Callable[[RevisionRecord], bool]
    #: The label recorded as the call row's ``provider``.
    provider_label: Callable[[RevisionRecord], str]
    #: Set for a channel kind: the factory used instead of ``factory``.
    channel: ChannelFactory | None = None
    additional_purposes: Callable[[RevisionRecord], tuple[str, ...]] = lambda revision: ()


_REGISTRY: dict[str, KindAdapter] = {}


def register_adapter_factory(
    kind: str, factory: AdapterFactory, *, purpose: str = "api_key",
    serves: Callable[[RevisionRecord], bool] = lambda revision: True,
    provider_label: Callable[[RevisionRecord], str] = lambda revision: revision.settings.api_flavour or "unknown",
    additional_purposes: Callable[[RevisionRecord], tuple[str, ...]] = lambda revision: (),
) -> None:
    _REGISTRY[kind] = KindAdapter(kind, factory, purpose, serves, provider_label,
                                  additional_purposes=additional_purposes)


def _no_secret_factory(revision: RevisionRecord, secret: str, policy: DestinationPolicy, context: Any) -> Any:
    raise AssertionError("a channel kind is built from its runtime, not from a secret")


def register_channel_kind(
    kind: str, channel: ChannelFactory, *,
    serves: Callable[[RevisionRecord], bool] = lambda revision: True,
    provider_label: Callable[[RevisionRecord], str] = lambda revision: kind,
) -> None:
    """Serve a kind whose remote party calls the stand (``pull``): no key, no destination."""
    _REGISTRY[kind] = KindAdapter(
        kind, _no_secret_factory, None, serves, provider_label, channel=channel)


def unregister_adapter_factory(kind: str) -> None:
    _REGISTRY.pop(kind, None)


def adapter_for(kind: str) -> KindAdapter | None:
    return _REGISTRY.get(kind)


def _http_api(revision: RevisionRecord, api_key: str | AdapterSecrets,
              policy: DestinationPolicy, context: Any) -> Any:
    settings = revision.settings
    assert settings.api_flavour and settings.base_url and settings.transport
    if settings.transport == "ssh_tunnel":
        assert isinstance(api_key, AdapterSecrets)
        return build_ssh_tunnel_adapter(
            revision, api_key.primary, api_key.additional["ssh_private_key"], policy, context)
    assert isinstance(api_key, str)
    return build_http_adapter(
        api_flavour=settings.api_flavour, base_url=settings.base_url, api_key=api_key,
        gateway_model=settings.gateway_model, timeout_seconds=settings.timeout_seconds,
        transport=settings.transport, policy=policy, context=context,
    )


register_adapter_factory(
    "http_api", _http_api, purpose="api_key",
    serves=lambda revision: revision.settings.transport in ("direct", "vpn", "ssh_tunnel"),
    additional_purposes=lambda revision: ("ssh_private_key",)
    if revision.settings.transport == "ssh_tunnel" else (),
)


register_adapter_factory(
    "ssh_command", build_ssh_command_adapter, purpose="ssh_private_key",
    serves=lambda revision: revision.settings.ssh_profile in ("claude_code_headless", "custom_command"),
    provider_label=lambda revision: revision.settings.ssh_profile or "ssh_command",
)


def _pull(revision: RevisionRecord, context: Any, runtime: KindRuntime) -> Any:
    return build_pull_adapter(
        session_factory=runtime.session_factory, revision=revision, context=context,
        engine=runtime.engine,
    )


# `EXEC-PULL-01` wired by `EXEC-CANDIDATE-2`: the answer is a task a runner takes (plan section 2.1),
# so a `pull` revision is served whatever its client; the call row's provider names the client.
register_channel_kind(
    "pull", _pull, provider_label=lambda revision: revision.settings.pull_client or "pull",
)
