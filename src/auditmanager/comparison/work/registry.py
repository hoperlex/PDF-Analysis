"""The handler registry: one handler per ``kind`` (ADR-0025 decision 4).

``comparison.public.HANDLER_FACTORIES`` is one tuple of factories; ``build_worker_runtime`` builds one
dependency bundle and applies every factory to it. The registry refuses to build on a duplicate
kind, on a kind outside the shape the column allows, and on a handler that cannot run; a slice adds
a handler by appending to the tuple and a test proves the tuple makes a registry.

`EXEC2-GROUP-CMP-01` (ADR-0026 decisions 12 and 14): the route source the registry hands to every factory is the composition
root's, wrapped so that a comparison AI job admitted by a rule or a group -- ``pending``, no connection yet -- is opened with the means
to bind a member at its first call (:class:`~auditmanager.comparison.spend.dispatch.GroupRoutes`). Every other job is opened by the
composition root's source exactly as before; a bundle with no route source stays without one.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterable, Mapping

from auditmanager.comparison.work.errors import HandlerRegistryError
from auditmanager.comparison.work.model import (
    KIND_PATTERN,
    HandlerFactory,
    WorkDependencies,
    WorkHandler,
)

__all__ = ["HandlerRegistry"]


def _with_group_dispatch(dependencies: WorkDependencies) -> WorkDependencies:
    """``dependencies`` whose route source opens a ``pending`` job with its first-call binding. A bundle that is not a
    :class:`WorkDependencies` (a registry test's stand-in) or has no route source is returned as it is."""
    routes = getattr(dependencies, "routes", None)
    if routes is None or not isinstance(dependencies, WorkDependencies):
        return dependencies
    # Imported here: the registry is generic and `ai_jobs` reaches the queue through `work.model`, not through this module.
    from auditmanager.comparison.ai_jobs.repository import AiJobRepository
    from auditmanager.comparison.spend.dispatch import group_aware

    wrapped = group_aware(routes, jobs=AiJobRepository())
    return dependencies if wrapped is routes else dataclasses.replace(dependencies, routes=wrapped)


class HandlerRegistry:
    """``{kind: handler}``, built once; immutable afterwards."""

    def __init__(self, handlers: Mapping[str, WorkHandler]) -> None:
        self._handlers: dict[str, WorkHandler] = dict(handlers)

    @classmethod
    def build(
        cls, factories: Iterable[HandlerFactory], dependencies: WorkDependencies,
    ) -> "HandlerRegistry":
        """Apply every factory to ``dependencies``; refuse a duplicate or malformed kind."""
        dependencies = _with_group_dispatch(dependencies)
        handlers: dict[str, WorkHandler] = {}
        for factory in factories:
            handler = factory(dependencies)
            kind = getattr(handler, "kind", None)
            if not isinstance(kind, str) or not KIND_PATTERN.match(kind):
                raise HandlerRegistryError(
                    "a work handler's kind is a lower-case code of 3 to 64 characters "
                    f"(got a {type(kind).__name__} of {len(kind) if isinstance(kind, str) else 0} characters)"
                )
            if not callable(getattr(handler, "run", None)):
                raise HandlerRegistryError(f"the handler of kind {kind} has no run(item)")
            if kind in handlers:
                raise HandlerRegistryError(f"two handlers are registered for the kind {kind}")
            handlers[kind] = handler
        return cls(handlers)

    @property
    def kinds(self) -> frozenset[str]:
        return frozenset(self._handlers)

    def handler(self, kind: str) -> WorkHandler:
        try:
            return self._handlers[kind]
        except KeyError:
            raise HandlerRegistryError(f"no handler is registered for the kind {kind}") from None
