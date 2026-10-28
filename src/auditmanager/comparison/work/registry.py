"""The handler registry: one handler per ``kind`` (ADR-0025 decision 4).

``comparison.public.HANDLER_FACTORIES`` is one tuple of factories; ``build_worker_runtime`` builds one
dependency bundle and applies every factory to it. The registry refuses to build on a duplicate
kind, on a kind outside the shape the column allows, and on a handler that cannot run; a slice adds
a handler by appending to the tuple and a test proves the tuple makes a registry.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from auditmanager.comparison.work.errors import HandlerRegistryError
from auditmanager.comparison.work.model import (
    KIND_PATTERN,
    HandlerFactory,
    WorkDependencies,
    WorkHandler,
)

__all__ = ["HandlerRegistry"]


class HandlerRegistry:
    """``{kind: handler}``, built once; immutable afterwards."""

    def __init__(self, handlers: Mapping[str, WorkHandler]) -> None:
        self._handlers: dict[str, WorkHandler] = dict(handlers)

    @classmethod
    def build(
        cls, factories: Iterable[HandlerFactory], dependencies: WorkDependencies,
    ) -> "HandlerRegistry":
        """Apply every factory to ``dependencies``; refuse a duplicate or malformed kind."""
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
