"""The shared core of consented AI jobs: start with consent, the state edges, the system pauses, the reads
(`CMP-AI-JOBS-01`, ADR-0025 decisions 10, 11 and 19).

The four method lanes (`pair_check`, `sheet_changes`, `spec`, `report`) build on :class:`ComparisonAiJobService`. A lane supplies an
:class:`~.model.AiMethod` (the counts of what it would send and the work items of a job) and wires its operations to the
service; it writes no row of ``comparison_ai_job`` itself.

**Transaction rules.**

* A *command* (``start``, ``pause``, ``resume``, ``cancel``, ``finish``, ``dequeue``, ``retry``) opens one unit of work with
  ``session_scope`` and is keyed: it claims the idempotency key first, so a repeat of the same key and payload replays the
  recorded job and a repeat with another payload is ``idempotency_key_reuse``. Every refusal raises inside the unit of work, so
  **a refused command writes nothing** (not the job, not the items, not the key). The module flag is checked first, before any
  read or write; the role is an expert's.
* A *worker-side* function (``mark_running``, ``complete_if_drained``, ``fail``, ``pause_for_spend``, ``consent_for_calls``,
  ``state_of``) takes the caller's session and **never commits**; the handler owns the transaction.
* Locks are taken **items first, then the job row**, as the series do: a handler holds an item's row (``require_current``) and
  then touches the job, so a command that locked the job first could deadlock with it.

**Refusals** are registered reasons under existing codes (``CMP-SEAL-C2`` section 3): ``409 conflict`` ``comparison_estimate_stale``,
``comparison_ceiling_job``, ``comparison_ceiling_day``, ``comparison_ai_job_active``, ``comparison_ai_job_state``,
``comparison_ai_nothing_to_do``; ``422 validation_failed`` ``comparison_consent_required`` (field ``consent``);
``503 dependency_unavailable`` ``comparison_modules`` while the versions module is off and ``executor_route_missing`` for a work
kind with no route.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.ai_jobs.estimate import RouteReader, build_estimate, read_route
from auditmanager.comparison.ai_jobs.model import (
    CONFLICT_AI_JOB_ACTIVE,
    CONFLICT_AI_JOB_STATE,
    CONFLICT_CEILING_DAY,
    CONFLICT_CEILING_JOB,
    CONFLICT_ESTIMATE_STALE,
    CONFLICT_NOTHING_TO_DO,
    CONSENT_PAUSES,
    CONSTRAINT_CONSENT_REQUIRED,
    PAUSE_MODULE_OFF,
    PAUSE_OVERRUN,
    PAUSE_QUOTA,
    PAUSE_ROUTE_CHANGED,
    PAUSE_USER,
    AiEstimate,
    AiMethod,
    AiScope,
    AiConsentInput,
    AiEstimateRequest,
    AiJobRecord,
    AiJobView,
    AiMode,
    AiWaitingJobs,
    AiWorkItemSpec,
    work_kind_of,
)
from auditmanager.comparison.ai_jobs.repository import LIVE_SCOPE_INDEXES, AiJobRepository
from auditmanager.comparison.modules import MODULE_STAGES, MODULE_VERSIONS, enabled_modules, parse_modules
from auditmanager.comparison.spend.errors import (
    REASON_CONSENT_REQUIRED,
    REASON_CONSENT_STALE,
    REASON_DAY_CEILING,
    REASON_JOB_CEILING,
    REASON_OVERRUN,
)
from auditmanager.comparison.spend.model import JOB_CEILING_USD, JOB_KEY, Consent
from auditmanager.comparison.spend.repository import ComparisonSpendRepository
from auditmanager.comparison.work.repository import ComparisonWorkRepository
from auditmanager.ingest.public import CommandReplay, CommandRepository, payload_fingerprint
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdempotencyKey

__all__ = [
    "COMMAND_EDGES",
    "AiJobCommand",
    "ComparisonAiJobService",
    "MAX_UNIT_KEY_LENGTH",
    "MAX_WAITING_JOBS",
    "PAUSE_OF_SPEND_REASON",
    "pause_reason_of",
]

#: The states each command may be taken from. The database's trigger allows a superset (it knows the edges, not the commands);
#: these are what the contract's operations say («A job that is not queued or running is 409 comparison_ai_job_state»).
COMMAND_EDGES: Final[Mapping[str, tuple[str, ...]]] = {
    "pause": ("queued", "running"),
    "resume": ("paused",),
    "cancel": ("queued", "running", "paused"),
    "dequeue": ("queued",),
    # «Досчитать»: an interrupted (failed), paused or cancelled job; a job that is queued or running is moving already.
    "finish": ("paused", "cancelled", "failed", "completed"),
    # «Повторить листы с ошибкой»: a job that has ended; its failed units are queued again under a new consent.
    "retry": ("completed", "failed", "cancelled"),
}
#: A work item's dedupe key is ``<job id>:<unit key>`` and the column holds 256 characters; a job id is 30.
MAX_UNIT_KEY_LENGTH: Final[int] = 225
MAX_WAITING_JOBS: Final[int] = 200
_FAILURE_REASON = re.compile(r"^[a-z][a-z0-9_]{2,63}$")

#: How a refusal or a pause of the spend wrapper (``comparison.spend``) pauses the job. The contract has six pause reasons:
#: an overrun of the consented estimate, and the job ceiling (the job passed what it may spend), are ``overrun`` (a resume
#: carries a new consent for what is left); the installation's day ceiling is the day's ``quota`` (a resume asks for no new
#: consent, the wrapper checks the day again before the next call); a consent that no longer holds -- the route, the revision
#: or the pinned model changed -- is ``route_changed``.
PAUSE_OF_SPEND_REASON: Final[Mapping[str, str]] = {
    REASON_OVERRUN: PAUSE_OVERRUN,
    REASON_JOB_CEILING: PAUSE_OVERRUN,
    REASON_DAY_CEILING: PAUSE_QUOTA,
    REASON_CONSENT_STALE: PAUSE_ROUTE_CHANGED,
    REASON_CONSENT_REQUIRED: PAUSE_ROUTE_CHANGED,
}


def pause_reason_of(spend_reason: str) -> str | None:
    """The job's pause reason for a reason code of the spend wrapper, or ``None`` when that reason does not pause a job."""
    return PAUSE_OF_SPEND_REASON.get(spend_reason)


@dataclass(frozen=True, slots=True)
class AiJobCommand:
    """Who acts and how the act is keyed: the lane's registered ``command_type`` (the snake case of the operationId), the
    caller's ``Idempotency-Key``, the user and the roles the credential carries."""

    command_type: str
    idempotency_key: str
    user_uid: str
    actor_roles: frozenset[str]


def _conflict(reason: str) -> DomainError:
    return DomainError(ErrorCode.CONFLICT, conflict_reason=reason)


def _not_found() -> DomainError:
    return DomainError(ErrorCode.NOT_FOUND, aggregate_type="ComparisonAiJob")


def _consent_required() -> DomainError:
    return DomainError(ErrorCode.VALIDATION_FAILED, field="consent", constraint=CONSTRAINT_CONSENT_REQUIRED)


def _require_expert(roles: frozenset[str]) -> None:
    """An AI start and every steering of a job is an expert's act (ADR-0025 decision 16, ``R-60``): an administrator alone is
    refused. The edge refuses it too; this is the command's own check, in the transaction that would act."""
    if "expert" not in roles:
        raise DomainError(ErrorCode.PERMISSION_DENIED, required_capability="role:expert")


class ComparisonAiJobService:
    """Estimate, start, steer and read consented AI jobs. One instance serves any number of methods; a lane builds it with its
    own method, the composition root may build one with all four.

    ``comparison_modules`` is the module set the deployment serves (``AUDITMANAGER_COMPARISON_MODULES``, parsed); ``provider_mode``
    is the process's (``live`` or ``recorded``); ``route_reader`` reads «Назначения» and is replaceable by a test.
    """

    def __init__(
        self, session_factory: "sessionmaker[Session]", *, methods: Sequence[AiMethod] | Mapping[str, AiMethod],
        work: ComparisonWorkRepository | None = None, comparison_modules: str = "none", provider_mode: str = "live",
        repository: AiJobRepository | None = None, spend: ComparisonSpendRepository | None = None,
        commands: CommandRepository | None = None, route_reader: RouteReader = read_route,
    ) -> None:
        if provider_mode not in ("live", "recorded"):
            raise ValueError("the provider mode is live or recorded")
        self._factory = session_factory
        by_method = dict(methods) if isinstance(methods, Mapping) else {m.method: m for m in methods}
        for name, method in by_method.items():
            if method.method != name:
                raise ValueError("a method is registered under its own name")
            work_kind_of(name)
        self._methods = by_method
        self._work = work or ComparisonWorkRepository()
        self._enabled_modules = enabled_modules(parse_modules(comparison_modules))
        self._versions_module_on = MODULE_VERSIONS in self._enabled_modules
        self._provider_mode = provider_mode
        self._repo = repository or AiJobRepository()
        self._spend = spend or ComparisonSpendRepository()
        self._commands = commands or CommandRepository()
        self._route_reader = route_reader

    # -- the module flag ----------------------------------------------------------------------------
    def _require_versions_module(self, method: str | None = None) -> None:
        """``503 dependency_unavailable`` (``comparison_modules``) unless «Сравнение версий» is on (ADR-0025 decision 23,
        ``A-12``: drawings reach a model only when the owner enabled the module). The first statement of every command."""
        required = MODULE_STAGES if method == "stage_review" else MODULE_VERSIONS
        if required not in self._enabled_modules:
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="comparison_modules")

    def _method_of(self, name: str) -> AiMethod:
        try:
            return self._methods[name]
        except KeyError:
            raise ValueError(f"this service has no method {name!r}") from None

    # -- the estimate -------------------------------------------------------------------------------
    def estimate(self, scope: AiScope, mode: AiMode = AiMode.START) -> AiEstimate:
        """The estimate of a start (or of what a job has left) in a unit of work of its own: no model call, no write."""
        self._require_versions_module(scope.method)
        with session_scope(self._factory) as session:
            if mode is AiMode.START:
                live = self._repo.live_on_scope(session, scope)
                if live is not None and live.state == "paused" and live.pause_reason in ("overrun", "route_changed"):
                    return self.estimate_in(session, live.scope, AiMode.LEFT, job=live)
            return self.estimate_in(session, scope, mode)

    def estimate_in(
        self, session: Session, scope: AiScope, mode: AiMode = AiMode.START, *, job: AiJobRecord | None = None,
    ) -> AiEstimate:
        """The estimate in the caller's session. ``job`` is the job it is for (a resume, a finish, a retry): what that job has
        already spent or reserved counts against the USD 10 ceiling."""
        method = self._method_of(scope.method)
        route = self._route_reader(session, scope.work_kind, self._provider_mode)
        counts = method.counts(session, AiEstimateRequest(scope=scope, mode=mode))
        spent = 0 if job is None else self._repo.spend(session, job.job_id).committed_micros
        return build_estimate(
            scope=scope, mode=mode, prompt_version=method.prompt_version, counts=counts, route=route,
            job_spent_micros=spent, day_committed_micros=self._spend.day_spend(session).committed_micros,
        )

    @staticmethod
    def _require_consentable(estimate: AiEstimate, consent: AiConsentInput) -> None:
        """The checks a consent must pass, in this order: the digest the user saw is the estimate now computed; there is
        something to send; neither ceiling is passed."""
        if consent.estimate_digest != estimate.estimate_digest:
            raise _conflict(CONFLICT_ESTIMATE_STALE)
        if estimate.totals.calls == 0:
            raise _conflict(CONFLICT_NOTHING_TO_DO)
        if estimate.blocked_by == "job":
            raise _conflict(CONFLICT_CEILING_JOB)
        if estimate.blocked_by == "day":
            raise _conflict(CONFLICT_CEILING_DAY)

    # -- start --------------------------------------------------------------------------------------
    def start(self, *, scope: AiScope, consent: AiConsentInput, command: AiJobCommand) -> AiJobView:
        """Start a consented job in the service-owned transaction."""
        with session_scope(self._factory) as session:
            return self.start_in_session(session, scope=scope, consent=consent, command=command)

    def start_in_session(
        self, session: Session, *, scope: AiScope, consent: AiConsentInput, command: AiJobCommand,
        queue_items: bool = True, estimate_mode: AiMode = AiMode.START,
        estimate_job: AiJobRecord | None = None,
    ) -> AiJobView:
        """Prepare a consented job and its work in the caller's transaction; never commit.

        C4 uses this after inserting the pinned stage run, so its run, AI job, consent
        and queue items commit atomically. Stage estimates bind immutable source revision
        rather than a not-yet-allocated run identity.
        """
        self._require_versions_module(scope.method)
        _require_expert(command.actor_roles)
        method = self._method_of(scope.method)
        if not consent.confirmed:
            raise _consent_required()
        fingerprint = payload_fingerprint({
            "command": f"{command.command_type}.v1", "scope": scope.as_document(),
            "estimate_digest": consent.estimate_digest,
        })
        if scope.method == "stage_review" and scope.stage_chain_run_id is None:
            raise ValueError("a persisted stage AI job requires its chain run")
        if estimate_mode is not AiMode.START:
            if (estimate_mode is not AiMode.LEFT or scope.method != "stage_review" or queue_items
                    or estimate_job is None):
                raise ValueError("only caller-owned stage recovery can start from a LEFT estimate")
            prior = self._job(session, estimate_job.job_id)
            if (prior.scope.stage_chain_run_id != scope.stage_chain_run_id
                    or prior.scope.project_uid != scope.project_uid or prior.scope.document_uid != scope.document_uid
                    or prior.state not in {"completed", "failed", "cancelled"}):
                raise _conflict(CONFLICT_AI_JOB_ACTIVE)
            estimate_job = prior
            fingerprint = payload_fingerprint({"base": str(fingerprint), "estimate_mode": "left",
                                               "estimate_job_id": prior.job_id})
        claim = self._commands.begin(
            session, command_type=command.command_type, idempotency_key=IdempotencyKey(command.idempotency_key),
            fingerprint=fingerprint,
        )
        if isinstance(claim, CommandReplay):
            return self.view_in(session, str(claim.outcome["ai_job_id"]))
        if self._repo.live_on_scope(session, scope) is not None:
            raise _conflict(CONFLICT_AI_JOB_ACTIVE)
        estimate = self.estimate_in(session, scope, estimate_mode, job=estimate_job)
        self._require_consentable(estimate, consent)
        try:
            job_id = self._repo.insert(
                session, estimate=estimate, user_uid=command.user_uid, command_id=str(claim.command_id),
            )
        except IntegrityError as error:
            if _is_live_scope_violation(error):  # the race the look-before-insert lost
                raise _conflict(CONFLICT_AI_JOB_ACTIVE) from None
            raise
        job = self._job(session, job_id)
        if queue_items:
            self._queue_items(session, job, method.work_items(session, job, AiMode.START), user_uid=command.user_uid)
        self._commands.succeed(session, claim.command_id, {"ai_job_id": job_id})
        return self.view_in(session, job_id)

    # -- the state edges ----------------------------------------------------------------------------
    def pause(self, *, job_id: str, method: str, command: AiJobCommand) -> AiJobView:
        """«Пауза»: a queued or running job pauses (reason ``user``); its waiting items pause and the call in hand finishes."""

        def apply(session: Session, job: AiJobRecord) -> None:
            self._require_edge(job, "pause")
            self._pause_items(session, job.job_id)
            self._move(session, job, "pause", to_state="paused", pause_reason=PAUSE_USER)

        return self._steer(job_id=job_id, method=method, command=command, extra={}, apply=apply)

    def resume(self, *, job_id: str, method: str, command: AiJobCommand, consent: AiConsentInput | None = None) -> AiJobView:
        """«Продолжить»: a paused job goes back to the queue. After ``overrun`` and ``route_changed`` the request carries a new
        consent for what is left (a new estimate; ``consent_no`` rises by one); after the other reasons the consent is ignored."""

        def apply(session: Session, job: AiJobRecord) -> None:
            self._require_edge(job, "resume")
            if job.pause_reason in CONSENT_PAUSES:
                self._renew_consent(session, job, consent, AiMode.LEFT, command.user_uid)
            self._resume_items(session, job.job_id)
            self._move(session, job, "resume", to_state="queued")

        extra = {"estimate_digest": None if consent is None else consent.estimate_digest}
        return self._steer(job_id=job_id, method=method, command=command, extra=extra, apply=apply)

    def resume_in_session(
        self, session: Session, *, job_id: str, method: str, command: AiJobCommand,
        consent: AiConsentInput | None = None, queue_items: bool = True,
    ) -> AiJobView:
        """Resume inside a caller transaction; a chain-owned job need not queue independent AI items."""
        def apply(current: Session, job: AiJobRecord) -> None:
            self._require_edge(job, "resume")
            if job.pause_reason in CONSENT_PAUSES:
                self._renew_consent(current, job, consent, AiMode.LEFT, command.user_uid)
            if queue_items:
                self._resume_items(current, job.job_id)
            self._move(current, job, "resume", to_state="queued")
        return self._steer_in_session(
            session, job_id=job_id, method=method, command=command,
            extra={"estimate_digest": None if consent is None else consent.estimate_digest}, apply=apply,
        )

    def cancel(self, *, job_id: str, method: str, command: AiJobCommand) -> AiJobView:
        """«Отменить»: a live job is cancelled. Items at rest end, the item in flight is asked to stop; what is done stays done
        (a «Досчитать» takes it up)."""

        with session_scope(self._factory) as session:
            return self.cancel_in_session(session, job_id=job_id, method=method, command=command)

    def cancel_in_session(
        self, session: Session, *, job_id: str, method: str, command: AiJobCommand,
        queue_items: bool = True,
    ) -> AiJobView:
        """Cancel through the shared policy in the caller's transaction."""
        def apply(current: Session, job: AiJobRecord) -> None:
            self._require_edge(job, "cancel")
            if queue_items:
                self._cancel_items(current, job.job_id)
            self._move(current, job, "cancel", to_state="cancelled")

        return self._steer_in_session(session, job_id=job_id, method=method,
                                      command=command, extra={}, apply=apply)

    def dequeue(self, *, job_id: str, method: str, command: AiJobCommand) -> AiJobView:
        """«Убрать из очереди»: a job that has not started leaves the queue and is cancelled. A job that has started -- it is not
        ``queued``, or any of its items was ever claimed -- is ``comparison_ai_job_state``."""

        def apply(session: Session, job: AiJobRecord) -> None:
            self._require_edge(job, "dequeue")
            items = self._repo.items(session, job.job_id)
            if any(item.attempt_count > 0 for item in items):
                raise _conflict(CONFLICT_AI_JOB_STATE)
            self._cancel_items(session, job.job_id)
            self._move(session, job, "dequeue", to_state="cancelled")

        return self._steer(job_id=job_id, method=method, command=command, extra={}, apply=apply)

    def finish(self, *, job_id: str, method: str, command: AiJobCommand) -> AiJobView:
        """«Досчитать»: queue what an interrupted, paused or cancelled job has no result for, **under the consent the job already
        holds**. A job paused for ``overrun`` or ``route_changed`` needs a new consent and is ``comparison_ai_job_state`` here
        (use ``resume``); nothing left is ``comparison_ai_nothing_to_do``. The spend wrapper re-checks the held consent before
        every call, so a job that has overrun pauses again at once instead of spending."""
        ai = self._method_of(method)

        def apply(session: Session, job: AiJobRecord) -> None:
            self._require_edge(job, "finish")
            if job.state == "paused" and job.pause_reason in CONSENT_PAUSES:
                raise _conflict(CONFLICT_AI_JOB_STATE)
            self._require_scope_free(session, job)
            resumed = self._resume_items(session, job.job_id)
            self._move(session, job, "finish", to_state="queued")
            queued = self._job(session, job.job_id)
            # What the paused items already cover is not queued twice: nothing new is fine when some were resumed.
            self._queue_items(
                session, queued, ai.work_items(session, queued, AiMode.LEFT), user_uid=command.user_uid,
                allow_empty=resumed > 0,
            )

        return self._steer(job_id=job_id, method=method, command=command, extra={}, apply=apply)

    def retry(self, *, job_id: str, method: str, command: AiJobCommand, consent: AiConsentInput) -> AiJobView:
        """«Повторить листы с ошибкой»: queue only the units that failed, as a new spend -- the consent is to the estimate of
        ``AiMode.FAILED``; the checks of a start apply (stale digest, ceilings, nothing to do, a live job on the scope)."""
        ai = self._method_of(method)

        def apply(session: Session, job: AiJobRecord) -> None:
            self._require_edge(job, "retry")
            self._require_scope_free(session, job)
            self._renew_consent(session, job, consent, AiMode.FAILED, command.user_uid)
            self._move(session, job, "retry", to_state="queued")
            queued = self._job(session, job.job_id)
            self._queue_items(session, queued, ai.work_items(session, queued, AiMode.FAILED), user_uid=command.user_uid)

        extra = {"estimate_digest": consent.estimate_digest, "confirmed": consent.confirmed}
        return self._steer(job_id=job_id, method=method, command=command, extra=extra, apply=apply)

    # -- the shared body of a steering command ------------------------------------------------------
    def _steer(
        self, *, job_id: str, method: str, command: AiJobCommand, extra: Mapping[str, object],
        apply: Callable[[Session, AiJobRecord], None],
    ) -> AiJobView:
        with session_scope(self._factory) as session:
            return self._steer_in_session(session, job_id=job_id, method=method, command=command, extra=extra, apply=apply)

    def _steer_in_session(
        self, session: Session, *, job_id: str, method: str, command: AiJobCommand,
        extra: Mapping[str, object], apply: Callable[[Session, AiJobRecord], None],
    ) -> AiJobView:
        self._require_versions_module(method)
        _require_expert(command.actor_roles)
        fingerprint = payload_fingerprint({"command": f"{command.command_type}.v1", "job_id": job_id, **extra})
        job = self._repo.get(session, job_id)
        if job is None or job.method != method:
            raise _not_found()
        claim = self._commands.begin(
            session, command_type=command.command_type, idempotency_key=IdempotencyKey(command.idempotency_key),
            fingerprint=fingerprint,
        )
        if isinstance(claim, CommandReplay):
            return self.view_in(session, job_id)
        apply(session, job)
        self._commands.succeed(session, claim.command_id, {"ai_job_id": job_id})
        return self.view_in(session, job_id)

    @staticmethod
    def _require_edge(job: AiJobRecord, command: str) -> None:
        if job.state not in COMMAND_EDGES[command]:
            raise _conflict(CONFLICT_AI_JOB_STATE)

    def _move(
        self, session: Session, job: AiJobRecord, command: str, *, to_state: str, pause_reason: str | None = None,
        failure_reason: str | None = None,
    ) -> None:
        """The job's edge, guarded by the states the command may be taken from; a lost race is ``comparison_ai_job_state``."""
        try:
            moved = self._repo.move(
                session, job.job_id, from_states=COMMAND_EDGES[command], to_state=to_state,
                pause_reason=pause_reason, failure_reason=failure_reason,
            )
        except IntegrityError as error:  # a terminal job back to queued, with another job live on the scope
            if _is_live_scope_violation(error):
                raise _conflict(CONFLICT_AI_JOB_ACTIVE) from None
            raise
        if not moved:
            raise _conflict(CONFLICT_AI_JOB_STATE)

    def _require_scope_free(self, session: Session, job: AiJobRecord) -> None:
        """A job going back to ``queued`` takes its scope again: refused while another live job holds it."""
        holder = self._repo.live_on_scope(session, job.scope)
        if holder is not None and holder.job_id != job.job_id:
            raise _conflict(CONFLICT_AI_JOB_ACTIVE)

    def _renew_consent(
        self, session: Session, job: AiJobRecord, consent: AiConsentInput | None, mode: AiMode, user_uid: str,
    ) -> AiEstimate:
        """A new consent on an existing job (a resume after ``overrun`` or ``route_changed``, a retry): the estimate is computed
        for ``mode`` with what the job has already spent counted against the ceiling; the same checks as a start."""
        if consent is None or not consent.confirmed:
            raise _consent_required()
        estimate = self.estimate_in(session, job.scope, mode, job=job)
        self._require_consentable(estimate, consent)
        if not self._repo.renew_consent(
            session, job.job_id, estimate=estimate, user_uid=user_uid, consent_no=job.consent_no,
            from_states=(job.state,),
        ):
            raise _conflict(CONFLICT_AI_JOB_STATE)
        return estimate

    # -- the work items of a job --------------------------------------------------------------------
    def _queue_items(
        self, session: Session, job: AiJobRecord, specs: Sequence[AiWorkItemSpec], *, user_uid: str,
        allow_empty: bool = False,
    ) -> int:
        """Enqueue the method's items for ``job``, each written with its job. The core owns the module, the dedupe key
        (``<job>:<unit key>``), the job identity in the payload and the column ``comparison_ai_job_id``. Answers how many
        items were created (a unit that already has a live item is not queued twice)."""
        if not specs:
            if allow_empty:
                return 0
            raise _conflict(CONFLICT_NOTHING_TO_DO)
        seen: set[str] = set()
        created = 0
        for spec in specs:
            if not 1 <= len(spec.unit_key) <= MAX_UNIT_KEY_LENGTH:
                raise ValueError("a unit key is 1 to 225 characters")
            if spec.unit_key in seen:
                raise ValueError("a method names a unit twice")
            seen.add(spec.unit_key)
            if JOB_KEY in spec.payload:
                raise ValueError("the job identity in a payload is the core's")
            work_id = self._repo.insert_item(
                session, job=job, kind=spec.kind or work_kind_of(job.method), payload={**spec.payload, JOB_KEY: job.job_id},
                dedupe_key=f"{job.job_id}:{spec.unit_key}", priority=spec.priority, delay_seconds=spec.delay_seconds,
                max_attempts=spec.max_attempts, user_uid=user_uid,
            )
            created += work_id is not None
        if created:
            self._repo.wake_workers(session)
        elif not allow_empty:
            raise _conflict(CONFLICT_NOTHING_TO_DO)
        return created

    def _pause_items(self, session: Session, job_id: str) -> None:
        """Pause the items that wait. An item claimed in the meantime is not paused: its holder finishes it (an item is one call's
        worth of work) and the handler sees the job paused."""
        for item in self._repo.items(session, job_id):
            if item.state in ("queued", "retry_wait"):
                try:
                    self._work.pause(session, item.work_id)
                except DomainError as error:
                    if error.code is not ErrorCode.STATE_TRANSITION_NOT_ALLOWED:
                        raise

    def _resume_items(self, session: Session, job_id: str) -> int:
        resumed = 0
        for item in self._repo.items(session, job_id):
            if item.state == "paused":
                self._work.resume(session, item.work_id)
                resumed += 1
        return resumed

    def _cancel_items(self, session: Session, job_id: str) -> None:
        for item in self._repo.items(session, job_id):
            if not item.terminal:
                self._work.cancel(session, item.work_id)

    # -- the worker's side: the handler of a method's items ------------------------------------------
    def state_of(self, session: Session, job_id: str) -> str:
        """The job's state now (a handler checks it before it calls a model: a paused or cancelled job sends nothing)."""
        return self._job(session, job_id).state

    def mark_running(self, session: Session, job_id: str) -> str:
        """The first claimed item starts the job: ``queued -> running``. Idempotent. Answers the job's state afterwards -- a
        handler that does not get ``running`` stops (the job was paused or cancelled while the item waited)."""
        self._repo.move(session, job_id, from_states=("queued",), to_state="running")
        return self._job(session, job_id).state

    def complete_if_drained(self, session: Session, job_id: str, *, excluding_work_id: str | None = None) -> bool:
        """``running -> completed`` once no item of the job is live. A job with failed units still completes (the original's
        «частично»; ``counts.failed`` says so). ``False`` while an item is live or when the job is not running."""
        if excluding_work_id is not None and not any(
            item.work_id == excluding_work_id and item.state == "running"
            for item in self._repo.items(session, job_id)
        ):
            raise ValueError("only the current running item of this job may be excluded")
        if self._repo.live_item_count(session, job_id, excluding_work_id=excluding_work_id) > 0:
            return False
        return self._repo.move(session, job_id, from_states=("running",), to_state="completed")

    def fail(self, session: Session, job_id: str, reason: str) -> bool:
        """``queued | running -> failed`` for a reason that ends the whole job (a code); its live items are cancelled."""
        if not _FAILURE_REASON.match(reason):
            raise ValueError("a failure reason is a lower-case code of 3 to 64 characters")
        self._cancel_items(session, job_id)
        return self._repo.move(
            session, job_id, from_states=("queued", "running"), to_state="failed", failure_reason=reason,
        )

    def pause_for_spend(self, session: Session, job_id: str, spend_reason: str) -> bool:
        """The job pauses because the spend wrapper said so (``SpendPause.reason``, or the ``reason`` of a ``CallRefused`` whose
        ``pauses_job`` is set): ``overrun`` and the job ceiling pause ``overrun``, the day ceiling ``quota``, a consent that no
        longer holds ``route_changed`` (:data:`PAUSE_OF_SPEND_REASON`). Its waiting items pause. ``False`` when the reason does
        not pause a job or the job is not queued or running (already paused or over)."""
        reason = pause_reason_of(spend_reason)
        if reason is None:
            return False
        return self.pause_system(session, job_id, reason)

    def pause_system(self, session: Session, job_id: str, reason: str) -> bool:
        """Pause a queued or running job for a reason of the system (``quota``, ``auth``, ``module_off``, ``route_changed``,
        ``overrun``). Idempotent."""
        if reason == PAUSE_USER:
            raise ValueError("a user's pause is the pause command")
        job = self._job(session, job_id)
        if job.state not in COMMAND_EDGES["pause"]:
            return False
        self._pause_items(session, job_id)
        return self._repo.move(
            session, job_id, from_states=COMMAND_EDGES["pause"], to_state="paused", pause_reason=reason,
        )

    def pause_for_module_off(self, session: Session, job_id: str) -> bool:
        return self.pause_system(session, job_id, PAUSE_MODULE_OFF)

    def consent_for_calls(self, session: Session, job_id: str) -> Consent:
        """The :class:`~auditmanager.comparison.spend.model.Consent` the spend wrapper checks every live call against, built from
        the job's stored consent.

        The wrapper judges the overrun on the job's **whole** spend against the consent's estimate. After a new consent (a resume
        or a retry) the estimate is for what was left, so the consent given to the wrapper is the estimate **plus what the job had
        actually spent before that consent**; otherwise a resumed job would overrun on its first call."""
        job = self._job(session, job_id)
        baseline = self._repo.spent_before(session, job_id, job.consented_at) if job.consent_no > 1 else 0
        ceiling = job.ceiling_micros / 1_000_000 if job.ceiling_micros > 0 else float(JOB_CEILING_USD)
        return Consent(
            estimate_digest=job.estimate_digest, estimate_usd=(baseline + job.estimate_micros) / 1_000_000,
            ceiling_usd=ceiling, connection_revision_id=job.connection_revision_id, pinned_model=job.pinned_model,
        )

    # -- reads --------------------------------------------------------------------------------------
    def _job(self, session: Session, job_id: str) -> AiJobRecord:
        job = self._repo.get(session, job_id)
        if job is None:
            raise _not_found()
        return job

    def job(self, session: Session, job_id: str) -> AiJobRecord:
        """The job row (``404`` when there is none)."""
        return self._job(session, job_id)

    def view_in(self, session: Session, job_id: str) -> AiJobView:
        """The job with its progress, its spend so far (from the journal) and its queue place, in the caller's session."""
        job = self._job(session, job_id)
        return AiJobView(
            record=job, progress=self._repo.progress(session, job_id), spend=self._repo.spend(session, job_id),
            queue_position=self._repo.queue_position(session, job_id) if job.state == "queued" else None,
        )

    def view(self, job_id: str, *, method: str | None = None) -> AiJobView:
        """The job view in a unit of work of its own. ``method`` makes a job of another method ``404``."""
        with session_scope(self._factory) as session:
            found = self._job(session, job_id)
            if method is not None and found.method != method:
                raise _not_found()
            return self.view_in(session, job_id)

    def latest(self, scope: AiScope) -> AiJobView | None:
        """The newest job of ``scope`` in any state, or ``None`` (a lane's GET)."""
        with session_scope(self._factory) as session:
            found = self._repo.latest_on_scope(session, scope)
            return None if found is None else self.view_in(session, found.job_id)

    def waiting(self, *, limit: int = MAX_WAITING_JOBS) -> AiWaitingJobs:
        """The installation's AI jobs that are queued, running or paused, running first, then in the order they will start (for
        ``getComparisonAiQueue``, wired by the queue lane). Reading starts nothing."""
        if not 1 <= limit <= MAX_WAITING_JOBS:
            raise ValueError("the queue shows 1 to 200 jobs")
        with session_scope(self._factory) as session:
            rows, totals = self._repo.waiting(session, limit=limit)
            items = tuple(
                AiJobView(
                    record=record, progress=self._repo.progress(session, record.job_id),
                    spend=self._repo.spend(session, record.job_id), queue_position=position,
                )
                for record, position in rows
            )
        return AiWaitingJobs(
            items=items, queued=totals.get("queued", 0), running=totals.get("running", 0), paused=totals.get("paused", 0),
        )


def _is_live_scope_violation(error: IntegrityError) -> bool:
    """Whether ``error`` is a unique violation of one of the four live-scope indexes: "one live job per scope", held by the
    database and reached when two starts (or a start and a job going back to ``queued``) race past the look-before-insert."""
    constraint = getattr(getattr(getattr(error, "orig", None), "diag", None), "constraint_name", None)
    return constraint in LIVE_SCOPE_INDEXES
