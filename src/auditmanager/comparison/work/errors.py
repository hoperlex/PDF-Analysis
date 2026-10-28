"""Refusals of the comparison work queue that are about the process, not about one item."""

from __future__ import annotations

__all__ = ["HandlerRegistryError", "UnhandledKindError", "WorkQueueError"]


class WorkQueueError(Exception):
    """A configuration or start-up refusal of the comparison queue."""


class HandlerRegistryError(WorkQueueError):
    """The handler factories do not make a registry: a duplicate or malformed ``kind``.

    Raised while wiring, so the worker does not start (ADR-0025 decision 4): a kind with two
    handlers has no honest answer to "which one ran this item".
    """


class UnhandledKindError(WorkQueueError):
    """A live ``comparison_work`` item of an enabled module has a ``kind`` no handler serves.

    Raised by :meth:`~auditmanager.comparison.work.runner.ComparisonWorkRunner.verify` before the
    worker registers (ADR-0025 decision 4): the item would otherwise wait for a handler that this
    build does not have, and a project with such an item cannot be erased.
    """

    def __init__(self, kinds: frozenset[str]) -> None:
        self.kinds = frozenset(kinds)
        super().__init__(
            "live comparison work of kind(s) " + ", ".join(sorted(self.kinds))
            + " has no handler in this build; deploy the build that has it or cancel the items"
        )
