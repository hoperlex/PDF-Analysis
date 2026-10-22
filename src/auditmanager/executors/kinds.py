"""The registry of connection kinds this release can serve: one adapter factory per kind.

`EXEC-HTTP-01` (`R-143`, plan section 3). **This is the seam a new kind plugs into.**
``EXEC-PULL-01`` and ``EXEC-SSH-01`` call :func:`register_adapter_factory` for their kind; nothing
else in the run path changes for them. A kind with no factory is *not served*: it can be created,
its probe ends ``kind_not_served``, and a route to it is refused with ``validation_failed``
(``constraint: kind_not_served``). A factory receives the revision, the **opened** secret and the
Attempt's context, and returns an object that satisfies the model-adapter seam.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from auditmanager.executors.destinations import DestinationPolicy
from auditmanager.executors.http_adapter import build_http_adapter
from auditmanager.executors.model import RevisionRecord

__all__ = ["KindAdapter", "adapter_for", "register_adapter_factory", "unregister_adapter_factory"]

#: ``factory(revision, secret_value, policy, attempt_context) -> adapter``
AdapterFactory = Callable[[RevisionRecord, str, DestinationPolicy, Any], Any]


@dataclass(frozen=True, slots=True)
class KindAdapter:
    kind: str
    factory: AdapterFactory
    #: The purpose of the secret the factory is handed (``api_key`` or ``ssh_private_key``).
    purpose: str
    #: Whether *this revision* of the kind is served (a transport a later slice adds, say).
    serves: Callable[[RevisionRecord], bool]
    #: The label recorded as the call row's ``provider``.
    provider_label: Callable[[RevisionRecord], str]


_REGISTRY: dict[str, KindAdapter] = {}


def register_adapter_factory(
    kind: str, factory: AdapterFactory, *, purpose: str = "api_key",
    serves: Callable[[RevisionRecord], bool] = lambda revision: True,
    provider_label: Callable[[RevisionRecord], str] = lambda revision: revision.settings.api_flavour or "unknown",
) -> None:
    _REGISTRY[kind] = KindAdapter(kind, factory, purpose, serves, provider_label)


def unregister_adapter_factory(kind: str) -> None:
    _REGISTRY.pop(kind, None)


def adapter_for(kind: str) -> KindAdapter | None:
    return _REGISTRY.get(kind)


def _http_api(revision: RevisionRecord, api_key: str, policy: DestinationPolicy, context: Any) -> Any:
    settings = revision.settings
    assert settings.api_flavour and settings.base_url and settings.transport
    return build_http_adapter(
        api_flavour=settings.api_flavour, base_url=settings.base_url, api_key=api_key,
        gateway_model=settings.gateway_model, timeout_seconds=settings.timeout_seconds,
        transport=settings.transport, policy=policy, context=context,
    )


register_adapter_factory(
    "http_api", _http_api, purpose="api_key",
    serves=lambda revision: revision.settings.transport in ("direct", "vpn"),
)
