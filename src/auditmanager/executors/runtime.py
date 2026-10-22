"""The run-path and worker surface of the executors boundary (`EXEC-HTTP-01`).

``public.py`` is what the ``api`` side uses (commands, queries, sealing). This module is what the
**composition root** wires into a worker and a run: freeze a route at run start, bind a connection
per Attempt, run probes, apply the destination rules, serve a new kind. It exists as a second
facade so that ``public.py`` stays free of the modules that import it.
"""

from __future__ import annotations

from auditmanager.executors.destinations import (
    ALLOWED_HOSTS_ENV,
    DestinationPolicy,
    DestinationRefused,
    DestinationUnresolvable,
)
from auditmanager.executors.kinds import (
    adapter_for,
    register_adapter_factory,
    unregister_adapter_factory,
)
from auditmanager.executors.probe_runner import ProbeRunner, runner_for
from auditmanager.executors.probes import ProbeResult, probe_http_api
from auditmanager.executors.resolver import (
    BoundConnection,
    FrozenConnection,
    bind_connection,
    freeze_connection,
    route_missing,
)
from auditmanager.executors.usability import is_probed_ok, is_served

__all__ = [
    "ALLOWED_HOSTS_ENV",
    "BoundConnection",
    "DestinationPolicy",
    "DestinationRefused",
    "DestinationUnresolvable",
    "FrozenConnection",
    "ProbeResult",
    "ProbeRunner",
    "adapter_for",
    "bind_connection",
    "freeze_connection",
    "is_probed_ok",
    "is_served",
    "probe_http_api",
    "register_adapter_factory",
    "route_missing",
    "runner_for",
    "unregister_adapter_factory",
]
