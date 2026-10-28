"""Vocabulary of the comparison durable queue (`CMP-WORK-01`, ADR-0025 decision 4).

The states and their edges are the database's (migration ``0038``): the trigger
``am_guard_comparison_state_edges`` refuses any other move, so the constants here only name what the
repository writes and what the worker reads. Nothing in this module touches the database.

An item is leased to one worker through an *attempt*. The attempt carries the execution token (a
secret-class equality-only capability: never logged, never repr'd, never returned), the lease expiry
and the heartbeat; the handler that runs the item is handed a :class:`WorkItem` and ends it with one
of three typed outcomes. A handler that publishes anything first calls :meth:`WorkItem.require_current`
in the publishing transaction, so a worker that lost its lease can write nothing.
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Final, Mapping, Protocol, runtime_checkable

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.engine import Engine
    from sqlalchemy.orm import Session, sessionmaker

    from auditmanager.comparison.work.repository import ComparisonWorkRepository
    from auditmanager.storage.public import BlobStore

__all__ = [
    "ATTEMPT_STATES",
    "ATTEMPT_WATCHDOG_SECONDS",
    "Completed",
    "Failed",
    "HEARTBEAT_SECONDS",
    "HandlerFactory",
    "ItemAuthority",
    "KIND_PATTERN",
    "LEASE_SECONDS",
    "LIVE_STATES",
    "Outcome",
    "REASON_ATTEMPT_BUDGET",
    "REASON_HANDLER_ERROR",
    "REASON_LEASE_EXPIRED",
    "REASON_NO_HANDLER",
    "REASON_OUTCOME_INVALID",
    "REASON_PATTERN",
    "REASON_WATCHDOG",
    "SpendSettler",
    "TERMINAL_STATES",
    "WORK_STATES",
    "WorkDependencies",
    "WorkHandler",
    "WorkItem",
    "Yielded",
]

#: The states of ``comparison_work`` (the CHECK of migration ``0038``).
WORK_STATES: Final[tuple[str, ...]] = (
    "queued", "leased", "running", "retry_wait", "paused", "spend_unknown",
    "succeeded", "failed", "cancelled",
)
TERMINAL_STATES: Final[frozenset[str]] = frozenset({"succeeded", "failed", "cancelled"})
#: The states the project erase refuses on (ADR-0025 decision 7).
LIVE_STATES: Final[frozenset[str]] = frozenset(WORK_STATES) - TERMINAL_STATES
#: The states of ``comparison_work_attempt``.
ATTEMPT_STATES: Final[tuple[str, ...]] = (
    "created", "leased", "running", "succeeded", "failed", "superseded", "lost", "cancelled",
)

#: The lease is stamped on database time at the claim and at every extension, as `jobs` does
#: (``JobRepository.lease_seconds``, the 0017 default): sixty seconds, so three heartbeats of
#: :data:`HEARTBEAT_SECONDS` fit inside one lease.
LEASE_SECONDS: Final[float] = 60.0
HEARTBEAT_SECONDS: Final[float] = 20.0
#: The longest one item may run. Past it the heartbeat stops extending the lease and fences the
#: attempt (the `jobs` watchdog, ``ATTEMPT_WATCHDOG_SECONDS``); the render and registration
#: children of ADR-0025 decision 8 are bounded by a 600 s wall, so an item that is still running
#: after 900 s has lost its child or its handler.
ATTEMPT_WATCHDOG_SECONDS: Final[float] = 900.0

#: The shape of a ``kind`` (the CHECK of migration ``0038``).
KIND_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
#: A failure reason is a code, never free text (the column holds 1..128 characters).
REASON_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-z][a-z0-9_]{0,127}$")

REASON_LEASE_EXPIRED: Final[str] = "lease_expired"
REASON_WATCHDOG: Final[str] = "item_watchdog"
REASON_ATTEMPT_BUDGET: Final[str] = "attempt_budget_exhausted"
REASON_HANDLER_ERROR: Final[str] = "handler_error"
REASON_OUTCOME_INVALID: Final[str] = "handler_outcome_invalid"
REASON_NO_HANDLER: Final[str] = "no_handler_for_kind"


@dataclass(frozen=True, slots=True)
class Completed:
    """The item's work is done; the item and its attempt end ``succeeded``."""


@dataclass(frozen=True, slots=True)
class Failed:
    """The item could not be done.

    ``reason`` is a code (:data:`REASON_PATTERN`). With ``retry`` the item goes back to the queue
    after a backoff while its attempt budget (``max_attempts``) lasts; without it, or when the
    budget is spent, the item ends ``failed`` carrying the reason.
    """

    reason: str
    retry: bool = False

    def __post_init__(self) -> None:
        if not REASON_PATTERN.match(self.reason):
            raise ValueError("a failure reason is a lower-case code of at most 128 characters")


@dataclass(frozen=True, slots=True)
class Yielded:
    """The handler gives the item back unfinished; it is queued again after ``delay_seconds``.

    A yield is not a failure and spends none of the attempt budget (it is the way an item that
    waits for something, or that processed one step of a longer job, returns to the queue).
    """

    delay_seconds: float = 0.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.delay_seconds <= 86_400.0:
            raise ValueError("a yield delays an item by between 0 and 86400 seconds")


Outcome = Completed | Failed | Yielded


@dataclass(frozen=True, slots=True)
class ItemAuthority:
    """What proves that an attempt holds its item: the identities and the execution token.

    The token is secret-class: it is compared for equality while the item row is locked and is
    excluded from ``repr`` so that it cannot reach a log line.
    """

    work_id: str
    attempt_id: str
    execution_token: str = field(repr=False)


@dataclass(frozen=True, slots=True, eq=False)
class WorkItem:
    """One claimed item, as the handler sees it."""

    work_id: str
    attempt_id: str
    attempt_no: int
    project_uid: str
    module: str
    kind: str
    payload: Mapping[str, Any]
    comparison_upload_id: str | None
    created_by_user_uid: str | None
    max_attempts: int
    authority: ItemAuthority = field(repr=False)
    #: The series the item belongs to (a series pauses, resumes and cancels its items by it); ``None`` for any other.
    comparison_series_id: str | None = None
    #: Set by the item's heartbeat when it finds the lease gone (expired, reclaimed or forced by
    #: the watchdog). A handler that notices it stops; one that does not is fenced at its next
    #: :meth:`require_current`.
    lease_lost: threading.Event = field(default_factory=threading.Event, repr=False)
    #: Set by the item's heartbeat when a cancel was requested while the item runs.
    cancelled: threading.Event = field(default_factory=threading.Event, repr=False)
    _repository: "ComparisonWorkRepository | None" = field(default=None, repr=False)

    def require_current(self, session: Session) -> None:
        """Lock the item and refuse (``stale_attempt`` / ``execution_token_invalid``) unless this
        attempt still holds it. Call it in the transaction that publishes anything; the lock is
        kept to that transaction's end."""
        self._bound().require_current(session, self.authority)

    def check_current(self, session: Session) -> None:
        """The early, lock-free form of :meth:`require_current`, for before a slow read."""
        self._bound().check_current(session, self.authority)

    def _bound(self) -> "ComparisonWorkRepository":
        if self._repository is None:
            raise RuntimeError("this work item was not claimed through a repository")
        return self._repository


@runtime_checkable
class WorkHandler(Protocol):
    """The one handler of a ``kind``: ``run`` ends the item with a typed outcome."""

    @property
    def kind(self) -> str: ...

    def run(self, item: WorkItem) -> Outcome: ...


@dataclass(frozen=True, slots=True)
class WorkDependencies:
    """The bundle every handler factory is applied to, built once by the composition root.

    ``work`` is the queue itself, so a handler can enqueue the next item of a series; a series is
    never one item (ADR-0025 decision 6: an item is one page or one pair).
    """

    engine: Engine
    session_factory: "sessionmaker[Session]"
    blob_store: BlobStore
    work: "ComparisonWorkRepository"


#: A slice adds a handler by appending a factory to ``comparison.public.HANDLER_FACTORIES``.
HandlerFactory = Callable[[WorkDependencies], WorkHandler]

#: Called inside the reclaim transaction for each attempt whose lease was lost: ``True`` when that
#: attempt left a model call that may have spent (``CMP-SPEND-01``, decision 5), after the settler
#: has marked it ``unknown``. The item then ends ``spend_unknown`` and is never re-sent by itself.
SpendSettler = Callable[["Session", str], bool]
