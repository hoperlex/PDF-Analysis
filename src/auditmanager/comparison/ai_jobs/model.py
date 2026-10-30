"""The vocabulary of the consented AI jobs of the version comparison (`CMP-AI-JOBS-01`, ADR-0025 decisions 10, 11, 19).

One object, ``ComparisonAiJob`` (table ``comparison_ai_job`` of migration ``0040``), serves the four methods of model work:
``pair_check``, ``sheet_changes``, ``spec`` and ``report``. This module names what the core and a method say to each other, and
nothing here reads a database or calls a model:

* the **scope** of a job (:class:`AiScope`) -- the same shape rule the table's CHECK enforces, so a malformed scope is refused
  before a statement is made;
* the **counts** a method supplies for an estimate (:class:`AiCallGroup`, :class:`AiCounts`): what would be sent, per call, with the
  A-12 limits on the images of a call checked at construction;
* the **estimate** the core derives (:class:`AiEstimate`) and its stable digest;
* the **route** the calls would travel (:class:`AiRoute`);
* the **job row** and the **views** the reads answer (:class:`AiJobRecord`, :class:`AiJobView`, :class:`AiProgress`, :class:`AiJobSpend`).

Money is integer micro-USD, as in the spend journal. The state edges and the pause reasons are the database's
(``comparison_ai_job`` trigger and CHECKs); the constants here only name them.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Final, Protocol, runtime_checkable

from auditmanager.comparison.spend.model import (
    DAY_CEILING_MICROS,
    JOB_CEILING_MICROS,
)

if TYPE_CHECKING:  # the types only: this module never imports another context at run time
    from sqlalchemy.orm import Session

    from auditmanager.analysis.public import ModelPin

__all__ = [
    "AiCounts",
    "AiEstimate",
    "AiMethod",
    "AiScope",
    "CHARS_PER_TOKEN_DENOMINATOR",
    "CHARS_PER_TOKEN_NUMERATOR",
    "CONFLICT_AI_JOB_ACTIVE",
    "CONFLICT_AI_JOB_STATE",
    "CONFLICT_CEILING_DAY",
    "CONFLICT_CEILING_JOB",
    "CONFLICT_ESTIMATE_STALE",
    "CONFLICT_NOTHING_TO_DO",
    "CONSENT_PAUSES",
    "CONSTRAINT_CONSENT_REQUIRED",
    "AiCallGroup",
    "AiConsentInput",
    "AiEstimateRequest",
    "JOB_LIVE_STATES",
    "JOB_STATES",
    "JOB_TERMINAL_STATES",
    "AiJobRecord",
    "AiJobSpend",
    "AiJobView",
    "METHODS",
    "METHOD_PAIR_CHECK",
    "METHOD_REPORT",
    "METHOD_SHEET_CHANGES",
    "METHOD_SPEC",
    "AiMode",
    "PAUSE_AUTH",
    "PAUSE_MODULE_OFF",
    "PAUSE_OVERRUN",
    "PAUSE_QUOTA",
    "PAUSE_REASONS",
    "PAUSE_ROUTE_CHANGED",
    "PAUSE_USER",
    "AiProgress",
    "AiRoute",
    "TOKENS_PER_IMAGE",
    "AiTotals",
    "AiWaitingJobs",
    "AiWorkItemSpec",
    "digest_of",
    "work_kind_of",
]

METHOD_PAIR_CHECK: Final[str] = "pair_check"
METHOD_SHEET_CHANGES: Final[str] = "sheet_changes"
METHOD_SPEC: Final[str] = "spec"
METHOD_REPORT: Final[str] = "report"
METHOD_STAGE_REVIEW: Final[str] = "stage_review"
METHODS: Final[tuple[str, ...]] = (METHOD_PAIR_CHECK, METHOD_SHEET_CHANGES, METHOD_SPEC, METHOD_REPORT, METHOD_STAGE_REVIEW)

#: The states of ``comparison_ai_job`` (the CHECK of migration ``0040``).
JOB_STATES: Final[tuple[str, ...]] = ("queued", "running", "paused", "completed", "failed", "cancelled")
JOB_LIVE_STATES: Final[tuple[str, ...]] = ("queued", "running", "paused")
JOB_TERMINAL_STATES: Final[tuple[str, ...]] = ("completed", "failed", "cancelled")

PAUSE_USER: Final[str] = "user"
PAUSE_QUOTA: Final[str] = "quota"
PAUSE_AUTH: Final[str] = "auth"
PAUSE_OVERRUN: Final[str] = "overrun"
PAUSE_ROUTE_CHANGED: Final[str] = "route_changed"
PAUSE_MODULE_OFF: Final[str] = "module_off"
PAUSE_REASONS: Final[tuple[str, ...]] = (
    PAUSE_USER, PAUSE_QUOTA, PAUSE_AUTH, PAUSE_OVERRUN, PAUSE_ROUTE_CHANGED, PAUSE_MODULE_OFF,
)
#: A resume after one of these carries a new consent (the contract's ``ComparisonAiPauseReason``).
CONSENT_PAUSES: Final[frozenset[str]] = frozenset({PAUSE_OVERRUN, PAUSE_ROUTE_CHANGED})

#: The registered reasons of ``409 conflict`` (``CMP-SEAL-C2`` section 3).
CONFLICT_ESTIMATE_STALE: Final[str] = "comparison_estimate_stale"
CONFLICT_CEILING_JOB: Final[str] = "comparison_ceiling_job"
CONFLICT_CEILING_DAY: Final[str] = "comparison_ceiling_day"
CONFLICT_AI_JOB_ACTIVE: Final[str] = "comparison_ai_job_active"
CONFLICT_AI_JOB_STATE: Final[str] = "comparison_ai_job_state"
CONFLICT_NOTHING_TO_DO: Final[str] = "comparison_ai_nothing_to_do"
#: The registered constraint of ``422 validation_failed`` (field ``consent``).
CONSTRAINT_CONSENT_REQUIRED: Final[str] = "comparison_consent_required"

#: Token estimates are integers and round up. A thousand characters of the drawings' Russian text and of the JSON a
#: model is asked for are priced at 400 tokens (2.5 characters per token): above the real rate of the pinned models, so
#: an estimate is not exceeded by its own conversion (the x1.2 pause measures the rest).
CHARS_PER_TOKEN_NUMERATOR: Final[int] = 400
CHARS_PER_TOKEN_DENOMINATOR: Final[int] = 1000
#: One image of a request is priced at the most a model charges for one (a drawing crop is resized to about 1.15
#: megapixels, 1590 tokens); an estimate never under-counts the images (ADR-0025 decision 18).
TOKENS_PER_IMAGE: Final[int] = 1600

_ESTIMATE_DIGEST_VERSION: Final[int] = 1


def work_kind_of(method: str) -> str:
    """The executor work kind of a method (``ExecutorWorkKind``): ``comparison_<method>``, routed in «Назначения»."""
    if method not in METHODS:
        raise ValueError(f"{method!r} is not a method of the version comparison AI")
    return f"comparison_{method}"


class AiMode(str, Enum):
    """Which work an estimate and a set of work items are for.

    ``START`` is a new job (everything the scope needs that has no stored answer); ``LEFT`` is what an existing job still has to
    do (a resume after ``overrun`` or ``route_changed``, «Досчитать»); ``FAILED`` is the units that failed (the retry).
    """

    START = "start"
    LEFT = "left"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class AiScope:
    """What a job is about: the document set and one of a build, a series, a transition or a sheet pair.

    The shape is the CHECK ``ck_comparison_ai_job_scope``: ``pair_check`` names a build; ``sheet_changes`` names a series or a
    sheet pair (exactly one); ``spec`` names a transition; ``report`` names a series. ``restart`` is the sheet run's «Описать
    заново». The scope belongs to the document (the table's trigger refuses otherwise).
    """

    method: str
    project_uid: str
    document_uid: str
    matrix_id: str | None = None
    series_id: str | None = None
    transition_id: str | None = None
    sheet_pair_id: str | None = None
    restart: bool = False
    stage_chain_run_id: str | None = None
    stage_link_revision_id: str | None = None

    def __post_init__(self) -> None:
        if self.method not in METHODS:
            raise ValueError(f"{self.method!r} is not a method of the version comparison AI")
        named = (self.matrix_id, self.series_id, self.transition_id, self.sheet_pair_id)
        shapes = {
            METHOD_PAIR_CHECK: (True, False, False, False),
            METHOD_SPEC: (False, False, True, False),
            METHOD_REPORT: (False, True, False, False),
        }
        if self.method == METHOD_STAGE_REVIEW:
            fits = self.stage_link_revision_id is not None and not any(value is not None for value in named)
        elif self.stage_chain_run_id is not None or self.stage_link_revision_id is not None:
            fits = False
        elif self.method == METHOD_SHEET_CHANGES:
            fits = (
                self.matrix_id is None and self.transition_id is None
                and (self.series_id is None) != (self.sheet_pair_id is None)
            )
        else:
            fits = tuple(value is not None for value in named) == shapes[self.method]
        if not fits:
            raise ValueError(f"the scope of a {self.method} job is not the one its method needs")
        if self.restart and self.method != METHOD_SHEET_CHANGES:
            raise ValueError("only a sheet run is restarted")

    @property
    def work_kind(self) -> str:
        return work_kind_of(self.method)

    def as_document(self) -> dict[str, Any]:
        """The scope as the digest and the command fingerprint see it."""
        return {
            "method": self.method, "project_uid": self.project_uid, "document_uid": self.document_uid,
            "matrix_id": self.matrix_id, "series_id": self.series_id, "transition_id": self.transition_id,
            "sheet_pair_id": self.sheet_pair_id, "restart": self.restart,
            **({"stage_link_revision_id": self.stage_link_revision_id} if self.method == METHOD_STAGE_REVIEW else {}),
        }


def _natural(value: object, what: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{what} is a non-negative integer")
    return value


@dataclass(frozen=True, slots=True)
class AiCallGroup:
    """``calls`` requests of one shape: what ONE of them sends and the answer it allows.

    ``prompt_chars`` is the characters of the prompt and the data in it; ``prompt_tokens`` is the same in tokens when the method
    knows it (it then wins over the conversion of the characters). ``images`` and ``image_bytes`` are the crops of one call and
    their total size: a request carries at most ``MAX_IMAGES`` images and ``MAX_TOTAL_IMAGE_BYTES`` bytes (the executors'
    limits, ADR-0025 decision 18, ``A-12``), so a group over them cannot be a request and is refused here. ``output_tokens`` is
    the ceiling the request allows (its ``max_tokens``).
    """

    calls: int
    prompt_chars: int
    output_tokens: int
    images: int = 0
    image_bytes: int = 0
    prompt_tokens: int | None = None

    def __post_init__(self) -> None:
        from auditmanager.executors.public import MAX_IMAGES, MAX_TOTAL_IMAGE_BYTES

        for value, what in (
            (self.calls, "calls"), (self.prompt_chars, "prompt_chars"), (self.output_tokens, "output_tokens"),
            (self.images, "images"), (self.image_bytes, "image_bytes"),
        ):
            _natural(value, what)
        if self.prompt_tokens is not None:
            _natural(self.prompt_tokens, "prompt_tokens")
        if self.images > MAX_IMAGES:
            raise ValueError(f"a request carries at most {MAX_IMAGES} images")
        if self.image_bytes > MAX_TOTAL_IMAGE_BYTES:
            raise ValueError(f"the images of a request weigh at most {MAX_TOTAL_IMAGE_BYTES} bytes")
        if self.image_bytes and not self.images:
            raise ValueError("image bytes without an image")

    @property
    def input_tokens_per_call(self) -> int:
        prompt = (
            self.prompt_tokens if self.prompt_tokens is not None
            else -(-self.prompt_chars * CHARS_PER_TOKEN_NUMERATOR // CHARS_PER_TOKEN_DENOMINATOR)
        )
        return prompt + self.images * TOKENS_PER_IMAGE


@dataclass(frozen=True, slots=True)
class AiTotals:
    """The sums over the call groups of an estimate."""

    calls: int
    images: int
    image_bytes: int
    prompt_chars: int
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True, slots=True)
class AiCounts:
    """What a method supplies for an estimate: how many units the job works on, how many already have a stored answer under
    the same content key (never sent again), and the shapes of the calls that remain.

    ``units`` is what the job works on (questions, sheets, transitions, versions or report parts); ``questions``, ``pairs``,
    ``sheets``, ``transitions`` and ``versions`` are the contract's optional named figures, given when the method has them.
    """

    groups: tuple[AiCallGroup, ...]
    units: int
    reused: int = 0
    questions: int | None = None
    pairs: int | None = None
    sheets: int | None = None
    transitions: int | None = None
    versions: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "groups", tuple(self.groups))
        _natural(self.units, "units")
        _natural(self.reused, "reused")
        if self.reused > self.units:
            raise ValueError("more units are reused than there are")
        for value, what in (
            (self.questions, "questions"), (self.pairs, "pairs"), (self.sheets, "sheets"),
            (self.transitions, "transitions"), (self.versions, "versions"),
        ):
            if value is not None:
                _natural(value, what)

    def totals(self) -> AiTotals:
        return AiTotals(
            calls=sum(g.calls for g in self.groups),
            images=sum(g.calls * g.images for g in self.groups),
            image_bytes=sum(g.calls * g.image_bytes for g in self.groups),
            prompt_chars=sum(g.calls * g.prompt_chars for g in self.groups),
            input_tokens=sum(g.calls * g.input_tokens_per_call for g in self.groups),
            output_tokens=sum(g.calls * g.output_tokens for g in self.groups),
        )


@dataclass(frozen=True, slots=True)
class AiRoute:
    """The connection that would serve a method's calls: the revision of the routed connection of the work kind, the model it
    pins, how it is billed, and the process's provider mode (``recorded`` means every answer is a recorded test answer)."""

    work_kind: str
    connection_id: str
    revision_id: str
    pinned_model: str
    gateway_model: str
    billing: str
    provider_mode: str
    pin: "ModelPin | None" = None

    @property
    def metered(self) -> bool:
        return self.billing != "not_metered"

    def as_document(self) -> dict[str, Any]:
        return {
            "connection_id": self.connection_id, "revision_id": self.revision_id,
            "pinned_model": self.pinned_model, "billing": self.billing, "provider_mode": self.provider_mode,
        }


@dataclass(frozen=True, slots=True)
class AiEstimateRequest:
    """What a method is asked to count: the scope and which work (:class:`AiMode`)."""

    scope: AiScope
    mode: AiMode = AiMode.START


@dataclass(frozen=True, slots=True)
class AiEstimate:
    """The contract's ``ComparisonAiEstimate``, derived without a model call.

    ``estimate_digest`` binds the method, the scope, the mode, the route (connection, revision, pinned model, billing, provider
    mode), the prompt version, the two hard ceilings and every figure; a moved input moves it. ``day_remaining_micros`` and
    ``blocked_by`` depend on what the installation has spent and are NOT in the digest: they are checked when the job starts.
    """

    scope: AiScope
    mode: AiMode
    route: AiRoute
    prompt_version: str
    counts: AiCounts
    totals: AiTotals
    estimate_micros: int
    ceiling_micros: int
    estimate_digest: str
    day_remaining_micros: int | None = None
    blocked_by: str | None = None  # "job" or "day"

    @property
    def method(self) -> str:
        return self.scope.method

    def as_dict(self, *, with_state: bool = True) -> dict[str, Any]:
        """The contract shape. ``with_state`` false leaves out ``day_remaining_micros`` and ``blocked_by``: that is the
        frozen estimate a job stores (what was consented to, not what the day looked like)."""
        counts = self.counts
        document: dict[str, Any] = {
            "method": self.scope.method, "estimate_digest": self.estimate_digest, "route": self.route.as_document(),
            "units": counts.units, "reused": counts.reused, "calls": self.totals.calls, "images": self.totals.images,
            "image_bytes": self.totals.image_bytes, "prompt_chars": self.totals.prompt_chars,
            "input_tokens": self.totals.input_tokens, "output_tokens": self.totals.output_tokens,
            "estimate_micros": self.estimate_micros, "ceiling_micros": self.ceiling_micros,
        }
        for name in ("questions", "pairs", "sheets", "transitions", "versions"):
            value = getattr(counts, name)
            if value is not None:
                document[name] = value
        if with_state:
            if self.day_remaining_micros is not None:
                document["day_remaining_micros"] = self.day_remaining_micros
            if self.blocked_by is not None:
                document["blocked_by"] = self.blocked_by
        return document


def digest_of(*, scope: AiScope, mode: AiMode, route: AiRoute, prompt_version: str, counts: AiCounts, totals: AiTotals,
              estimate_micros: int, ceiling_micros: int) -> str:
    """The stable ``estimate_digest`` (lower-case SHA-256 hex): a canonical JSON of everything the estimate binds."""
    document = {
        "digest_version": _ESTIMATE_DIGEST_VERSION, "scope": scope.as_document(), "mode": mode.value,
        "route": route.as_document(), "prompt_version": prompt_version,
        "ceilings": {"job_micros": JOB_CEILING_MICROS, "day_micros": DAY_CEILING_MICROS},
        "figures": {
            "units": counts.units, "reused": counts.reused, "questions": counts.questions, "pairs": counts.pairs,
            "sheets": counts.sheets, "transitions": counts.transitions, "versions": counts.versions,
            "calls": totals.calls, "images": totals.images, "image_bytes": totals.image_bytes,
            "prompt_chars": totals.prompt_chars, "input_tokens": totals.input_tokens,
            "output_tokens": totals.output_tokens,
        },
        "estimate_micros": estimate_micros, "ceiling_micros": ceiling_micros,
    }
    encoded = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class AiConsentInput:
    """The user's consent as the operation carries it (the contract's ``ComparisonAiConsent``)."""

    estimate_digest: str
    confirmed: bool


@dataclass(frozen=True, slots=True)
class AiWorkItemSpec:
    """One work item a method asks for. The core adds the job: the module, the dedupe key (the job and ``unit_key``), the job
    identity in the payload and the column ``comparison_work.comparison_ai_job_id``.

    ``unit_key`` names the unit of work within the job (a question, a sheet pair); the same unit queued again for the same job
    (a finish, a retry) has the same key, which is how progress counts a unit once. ``kind`` is the work kind the item is
    claimed under (the method's work kind when absent).
    """

    unit_key: str
    payload: Mapping[str, Any]
    priority: int = 0
    delay_seconds: float = 0.0
    max_attempts: int = 3
    kind: str | None = None


@runtime_checkable
class AiMethod(Protocol):
    """What a method supplies to the core. Nothing else of the method is the core's business."""

    @property
    def method(self) -> str:
        """One of :data:`METHODS`."""

    @property
    def prompt_version(self) -> str:
        """The version of the method's prompt: it is part of the estimate digest (a new prompt is a new estimate)."""

    def counts(self, session: "Session", request: AiEstimateRequest) -> AiCounts:
        """The counts of what the request would send. Read-only. Units that already have a stored answer under their content key
        are ``reused`` and need no call."""

    def work_items(self, session: "Session", job: "AiJobRecord", mode: AiMode) -> Sequence[AiWorkItemSpec]:
        """The work items a job needs for ``mode``, in the caller's transaction (the job row already exists, in the state it will
        be in). An empty sequence is «nothing to do»."""


@dataclass(frozen=True, slots=True)
class AiJobRecord:
    """One row of ``comparison_ai_job`` as a reader sees it."""

    job_id: str
    project_uid: str
    document_uid: str
    method: str
    state: str
    pause_reason: str | None
    failure_reason: str | None
    matrix_id: str | None
    series_id: str | None
    transition_id: str | None
    sheet_pair_id: str | None
    restart: bool
    connection_revision_id: str
    pinned_model: str
    provider_mode: str
    estimate: Mapping[str, Any]
    estimate_digest: str
    estimate_micros: int
    ceiling_micros: int
    consent_no: int
    consented_by_user_uid: str
    consented_at: datetime
    command_id: str
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None
    stage_chain_run_id: str | None = None
    stage_link_revision_id: str | None = None

    @property
    def scope(self) -> AiScope:
        return AiScope(
            method=self.method, project_uid=self.project_uid, document_uid=self.document_uid, matrix_id=self.matrix_id,
            series_id=self.series_id, transition_id=self.transition_id, sheet_pair_id=self.sheet_pair_id,
            restart=self.restart, stage_chain_run_id=self.stage_chain_run_id,
            stage_link_revision_id=self.stage_link_revision_id,
        )

    @property
    def live(self) -> bool:
        return self.state in JOB_LIVE_STATES


@dataclass(frozen=True, slots=True)
class AiProgress:
    """The units of a job, counted once each by their latest work item: ``total``, ``done`` (succeeded), ``failed`` and
    ``unknown`` (a call whose outcome is not known: ``spend_unknown``). The rest are waiting, running, paused or cancelled."""

    total: int
    done: int
    failed: int
    unknown: int
    by_state: Mapping[str, int]


@dataclass(frozen=True, slots=True)
class AiJobSpend:
    """The spend of a job so far, read from the journal through its work items (never stored on the job)."""

    spent_micros: int
    reserved_micros: int
    calls: int
    unknown_calls: int
    input_tokens: int
    output_tokens: int

    @property
    def committed_micros(self) -> int:
        return self.spent_micros + self.reserved_micros


@dataclass(frozen=True, slots=True)
class AiJobView:
    """A job with what a reader shows next to it."""

    record: AiJobRecord
    progress: AiProgress
    spend: AiJobSpend
    queue_position: int | None = None

    def as_dict(self) -> dict[str, Any]:
        """The contract's ``ComparisonAiJob``."""
        record = self.record
        document: dict[str, Any] = {
            "job_id": record.job_id, "method": record.method, "project_uid": record.project_uid,
            "document_uid": record.document_uid, "state": record.state, "estimate": dict(record.estimate),
            "consented_by": record.consented_by_user_uid, "consented_at": record.consented_at,
            "spend": {
                "spent_micros": self.spend.spent_micros, "reserved_micros": self.spend.reserved_micros,
                "calls": self.spend.calls, "unknown_calls": self.spend.unknown_calls,
                "input_tokens": self.spend.input_tokens, "output_tokens": self.spend.output_tokens,
            },
            "counts": {
                "total": self.progress.total, "done": self.progress.done, "failed": self.progress.failed,
                "unknown": self.progress.unknown,
            },
            "created_at": record.created_at, "updated_at": record.updated_at,
        }
        for name, value in (
            ("series_id", record.series_id), ("transition_id", record.transition_id),
            ("sheet_pair_id", record.sheet_pair_id), ("pause_reason", record.pause_reason),
            ("failure_reason", record.failure_reason), ("queue_position", self.queue_position),
            ("finished_at", record.finished_at),
        ):
            if value is not None:
                document[name] = value
        return document

    def as_queue_item(self) -> dict[str, Any]:
        """The contract's ``ComparisonAiQueueItem``."""
        record = self.record
        document: dict[str, Any] = {
            "job_id": record.job_id, "method": record.method, "state": record.state, "project_uid": record.project_uid,
            "document_uid": record.document_uid,
            "counts": {
                "total": self.progress.total, "done": self.progress.done, "failed": self.progress.failed,
                "unknown": self.progress.unknown,
            },
            "created_at": record.created_at,
        }
        if record.series_id is not None:
            document["series_id"] = record.series_id
        if self.queue_position is not None:
            document["queue_position"] = self.queue_position
        return document


@dataclass(frozen=True, slots=True)
class AiWaitingJobs:
    """The installation's AI jobs that are queued, running or paused: running first, then in the order they will start."""

    items: tuple[AiJobView, ...]
    queued: int
    running: int
    paused: int

    def as_dict(self) -> dict[str, Any]:
        """The contract's ``ComparisonAiQueue``."""
        return {
            "items": [item.as_queue_item() for item in self.items],
            "queued": self.queued, "running": self.running, "paused": self.paused,
        }
