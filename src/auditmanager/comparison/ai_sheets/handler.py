"""The work handler of kind ``comparison_sheet_changes`` (`CMP-VC-AISHEET-01`): one item is one sheet pair of a job.

What one run does, in order, each step a short transaction of its own (the model call is never inside one):

1. **Start**: the job must be ``running`` (the first claimed item starts it); a job that was paused or cancelled while the item waited
   sends nothing. The sheet's item row moves ``queued -> running``. The content key of the description is computed from the pair's stored
   result, the prompt version and the job's pinned model; **a stored description under that key ends the item at once with no call**
   ("a stored description is never re-requested").
2. **The packet** is built from the stored rows and pages (no transaction is open); a pair with no candidate gets a deterministic
   description and no call.
3. **The call(s)** through :class:`~auditmanager.comparison.spend.caller.ComparisonModelCaller`; the checkpoint before each one proves the
   lease and looks for a cancel.
4. **Publish**: the lease is proved again in the publishing transaction (``WorkItem.require_current``), the description is stored under
   its key (a second writer finds the stored one), the item row moves to ``done`` with its calls, tokens and time, and a job that has
   spent more than its consent allows is paused (the reply is kept; the job makes no further call).

Typed spend errors become the item's outcome as ``CMP-SPEND-01`` defines: a refusal that pauses the job pauses it and **yields the item**
(it continues when the job is resumed); a call whose outcome is unknown is a failed sheet with the reason ``spend_unknown`` and is never
sent again until «Повторить»; a lost lease publishes nothing.

**The job completes in a separate, unlinked item** (``drain``): ``ComparisonAiJobService.complete_if_drained`` counts every live item of
the job, the caller's own included, so the last sheet cannot complete its job from inside its own run. The sheet's run enqueues one
``drain`` item for the job (dedupe key ``sheet_drain:<job>``, **not** linked to the job, no model call); it polls while sheets are live and
completes the job when none is. (`FIX` item for the wave: the core could take an ``excluding_work_id``.)

The handler takes three seams, so that a test runs it in recorded mode and the composition root supplies the live ones: ``routes`` (the
call route of a job: adapter, pinned model, revision -- ``bind_connection`` needs the worker's private ring and destination policy, which
``WorkDependencies`` does not carry), ``material`` (words, lines and pictures of the stored pages) and ``stager`` (the crops reaching the
runner of a pull connection). Without ``routes`` the item ends the job as failed with the reason ``executor_adapter_unavailable`` --
nothing falls back silently.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Final, Protocol

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.ai_jobs.model import AiJobRecord
from auditmanager.comparison.ai_jobs.repository import AiJobRepository
from auditmanager.comparison.ai_jobs.service import ComparisonAiJobService
from auditmanager.comparison.ai_sheets import describe as ds
from auditmanager.comparison.ai_sheets import packet as pk
from auditmanager.comparison.ai_sheets.check import state_of
from auditmanager.comparison.ai_sheets.description import build_description
from auditmanager.comparison.ai_sheets.material import ProfileMaterial, SheetMaterial
from auditmanager.comparison.ai_sheets.method import SheetChangesMethod, facts_of, keys_for, kind_of, prompt_for
from auditmanager.comparison.ai_sheets.model import KIND_PAIR, KIND_SINGLE, SINGLE_TEXT_LIMIT, WORK_KIND
from auditmanager.comparison.ai_sheets.repository import AiSheetRepository, PairFacts
from auditmanager.comparison.modules import MODULE_VERSIONS
from auditmanager.comparison.spend.caller import ComparisonModelCaller
from auditmanager.comparison.spend.errors import CallLost, CallRefused, OutcomeUnknown
from auditmanager.comparison.spend.model import JOB_KEY, CallRoute, Consent
from auditmanager.comparison.work.model import Completed, Failed, Outcome, WorkDependencies, WorkItem, Yielded
from auditmanager.comparison.work.repository import ComparisonWorkRepository
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "DRAIN_POLL_SECONDS",
    "PAUSED_WAIT_SECONDS",
    "ModelRoutes",
    "SheetChangesHandler",
    "UnavailableRoutes",
    "drain_dedupe_key",
    "sheet_changes_handler",
]

_LOG = logging.getLogger(__name__)
#: An item of a job that is paused (it was in hand when the job paused) is offered again after this; a job that is resumed continues it.
PAUSED_WAIT_SECONDS: Final[float] = 30.0
#: The drain item looks again after this while sheets of the job are live.
DRAIN_POLL_SECONDS: Final[float] = 10.0
REASON_NO_ADAPTER: Final[str] = "executor_adapter_unavailable"
REASON_NO_PAIR: Final[str] = "sheet_pair_missing"
REASON_ROUTE: Final[str] = "executor_route_missing"
REASON_NO_RESULT: Final[str] = "sheet_result_missing"
_JOB_LIVE: Final[tuple[str, ...]] = ("queued", "running", "paused")


class ModelRoutes(Protocol):
    """Where the call route of a job comes from: the adapter of the job's connection revision, with the model it is pinned to."""

    def route_for(self, session: Session, job: AiJobRecord) -> CallRoute:
        """The :class:`~auditmanager.comparison.spend.model.CallRoute` for the job's calls; a ``DomainError`` when there is none."""


class UnavailableRoutes:
    """The route source of a process that was not given one: it says so (nothing is called, nothing falls back)."""

    def route_for(self, session: Session, job: AiJobRecord) -> CallRoute:
        raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="executor_adapter")


def drain_dedupe_key(job_id: str) -> str:
    return f"sheet_drain:{job_id}"


class _Stop(Exception):
    """The lease is gone or a cancel was requested: stop, publish nothing."""


class SheetChangesHandler:
    """The one handler of kind ``comparison_sheet_changes`` (a :class:`~auditmanager.comparison.work.model.WorkHandler`)."""

    kind: str = WORK_KIND

    def __init__(
        self, dependencies: WorkDependencies, *, routes: ModelRoutes | None = None, material: SheetMaterial | None = None,
        jobs: ComparisonAiJobService | None = None, caller: ComparisonModelCaller | None = None,
        repository: AiSheetRepository | None = None, recorded: Callable[[CallRoute], bool] | None = None,
    ) -> None:
        self._deps = dependencies
        self._routes: ModelRoutes = routes or UnavailableRoutes()
        self._material = material
        self._jobs = jobs
        self._caller = caller
        self._repo = repository or AiSheetRepository()
        self._ai_repo = AiJobRepository()
        self._recorded = recorded or _is_recorded

    # -- lazily built from the dependencies (a factory is applied to bare dependencies in the registry tests) -----------
    @property
    def _sessions(self) -> "sessionmaker[Session]":
        return self._deps.session_factory

    def _material_(self) -> SheetMaterial:
        if self._material is None:
            from auditmanager.comparison.profile.reader import PageProfileReader

            self._material = ProfileMaterial(PageProfileReader(self._deps.session_factory, self._deps.blob_store))
        return self._material

    def _jobs_(self) -> ComparisonAiJobService:
        if self._jobs is None:
            self._jobs = ComparisonAiJobService(
                self._deps.session_factory, methods=[SheetChangesMethod(self._material_)], work=self._deps.work,
                comparison_modules=MODULE_VERSIONS,
            )
        return self._jobs

    def _caller_(self) -> ComparisonModelCaller:
        if self._caller is None:
            self._caller = ComparisonModelCaller(self._deps.session_factory)
        return self._caller

    # -- the run ----------------------------------------------------------------------------------------------------------
    def run(self, item: WorkItem) -> Outcome:
        payload = item.payload
        if "drain_job_id" in payload:
            return self._drain(item, str(payload["drain_job_id"]))
        pair_id, job_id = str(payload.get("sheet_pair_id", "")), str(payload.get(JOB_KEY, ""))
        if not pair_id or not job_id:
            return Failed("sheet_item_payload_invalid")
        try:
            return self._sheet(item, pair_id, job_id)
        except _Stop:
            return Yielded(0.0)

    def _checkpoint(self, item: WorkItem) -> None:
        """Prove the lease, extend it, and stop on a cancel or a lease that is gone (the engine handler's checkpoint)."""
        if item.lease_lost.is_set() or item.cancelled.is_set():
            raise _Stop
        with self._sessions() as session:
            try:
                item.check_current(session)
            except DomainError as refusal:
                if refusal.code in (ErrorCode.STALE_ATTEMPT, ErrorCode.EXECUTION_TOKEN_INVALID):
                    item.lease_lost.set()
                    raise _Stop from refusal
                raise
            holds = self._deps.work.heartbeat(session, item.authority)
            cancel = holds and self._deps.work.cancel_requested(session, item.work_id)
            session.commit()
        if not holds:
            item.lease_lost.set()
            raise _Stop
        if cancel:
            item.cancelled.set()
            raise _Stop

    def _sheet(self, item: WorkItem, pair_id: str, job_id: str) -> Outcome:
        jobs = self._jobs_()
        # 1. start: the job runs, the pair exists, the sheet's row is running, a stored description ends the item
        with self._sessions() as session:
            item.require_current(session)
            if jobs.mark_running(session, job_id) != "running":
                state = jobs.state_of(session, job_id)
                session.commit()
                return Yielded(PAUSED_WAIT_SECONDS) if state in ("paused", "queued") else Completed()
            job = jobs.job(session, job_id)
            pair = self._repo.pair(session, pair_id)
            if pair is None or pair.project_uid != job.project_uid:
                session.commit()
                return Failed(REASON_NO_PAIR)
            if pair.subject_key is None:
                session.commit()
                return Failed(REASON_NO_RESULT)
            key = keys_for([pair], job.pinned_model)[pair_id]
            self._repo.ensure_item(session, job_id=job_id, project_uid=job.project_uid, pair_id=pair_id)
            self._repo.requeue_item(session, job_id=job_id, pair_id=pair_id)
            self._repo.move_item(session, job_id=job_id, pair_id=pair_id, from_states=("queued",), to_state="running")
            current = self._repo.item(session, job_id, pair_id)
            if current is not None and current.state == "done":
                session.commit()
                return Completed()
            stored = self._repo.description_by_key(session, job.project_uid, key)
            if stored is not None:
                self._repo.move_item(
                    session, job_id=job_id, pair_id=pair_id, from_states=("running",), to_state="done", description_id=stored.description_id,
                )
                self._after_item(session, item, job)
                session.commit()
                return Completed()
            consent = jobs.consent_for_calls(session, job_id)
            try:
                route = self._routes.route_for(session, job)
            except DomainError as unavailable:
                reason = REASON_NO_ADAPTER if unavailable.detail_fields.get("dependency") == "executor_adapter" else REASON_ROUTE
                self._repo.move_item(session, job_id=job_id, pair_id=pair_id, from_states=("running",), to_state="failed", reason=reason)
                jobs.fail(session, job_id, reason)
                session.commit()
                return Failed(reason)
            session.commit()
        # 2. the packet and 3. the calls: no transaction is open
        recorded = self._recorded(route)
        try:
            run = self._describe(item, job, pair, route, consent, key, recorded)
        except ds.SheetInterrupted as stopped:
            return self._interrupted(item, job, pair, stopped)
        except _Stop:
            self._release(item, job_id, pair_id)
            raise
        return self._publish(item, job, pair, key, run, recorded)

    def _describe(
        self, item: WorkItem, job: AiJobRecord, pair: PairFacts, route: CallRoute, consent: Consent | None, key: str, recorded: bool,
    ) -> ds.SheetRun:
        material = self._material_()
        facts = facts_of(pair)
        caller = self._caller_()

        def checkpoint() -> None:
            self._checkpoint(item)

        if pair.one_sided:
            return self._describe_single(item, job, pair, route, consent, facts, material, recorded, checkpoint)
        with self._sessions() as session:
            result = self._repo.result_document(session, pair.result_id) if pair.result_id else None
        if result is None:
            run = ds.SheetRun()
            run.failure = REASON_NO_RESULT
            return run
        packet = pk.assemble(facts, result, material, render=True, xrefs=True)
        if not packet.candidates:
            # nothing to ask about: a description with no change and no call (the engine's notes decide "partial", ``validate.py:250-253``)
            checked = {
                "ok": True, "changes": [], "unresolved": [], "excluded": [], "issues": [],
                "coverage": {"candidates": 0, "in_changes": 0, "in_unresolved": 0, "excluded": 0, "not_reviewed": []},
            }
            run = ds.SheetRun()
            run.state = state_of(checked, packet.document)
            run.description = build_description(packet.document, checked, run.state, calls=[], launches=0, recorded=False)
            return run
        return ds.describe_pair(
            caller, item, route, consent, job.pinned_model, packet, material, facts, checkpoint=checkpoint, recorded=recorded,
        )

    def _describe_single(
        self, item: WorkItem, job: AiJobRecord, pair: PairFacts, route: CallRoute, consent: Consent | None, facts: pk.SheetFacts,
        material: SheetMaterial, recorded: bool, checkpoint: Callable[[], None],
    ) -> ds.SheetRun:
        kind = str(pair.single_kind)
        side = "B" if kind == "added" else "A"
        profile_id = pair.subject_page_profile or ""
        page = material.page(profile_id)
        words = sorted(page.words, key=lambda w: (round(float(w.top) / 4.0), float(w.x0)))
        text = " ".join(w.text for w in words)[: SINGLE_TEXT_LIMIT * 2]
        return ds.describe_single(
            self._caller_(), item, route, consent, job.pinned_model, kind=kind, side=side,
            page=(pair.page_b if side == "B" else pair.page_a) or 0, title=pair.title,
            label=facts.label_b if side == "B" else facts.label_a, project=facts.designation or facts.project_title, sheet_text=text,
            image=material.overview(profile_id), material_tag=pair.subject_key or "", checkpoint=checkpoint, recorded=recorded,
        )

    # -- the ends of a run ------------------------------------------------------------------------------------------------
    def _publish(self, item: WorkItem, job: AiJobRecord, pair: PairFacts, key: str, run: ds.SheetRun, recorded: bool) -> Outcome:
        jobs = self._jobs_()
        with self._sessions() as session:
            item.require_current(session)  # the fence: a worker that lost its lease writes nothing
            counts = {"calls": len(run.calls), "input_tokens": run.input_tokens, "output_tokens": run.output_tokens,
                      "elapsed_ms": run.elapsed_ms}
            if run.description is None:
                reason = run.failure or "model_answer_invalid"
                self._repo.move_item(
                    session, job_id=job.job_id, pair_id=pair.pair_id, from_states=("running",), to_state="failed", reason=reason, **counts,
                )
                self._pause_if(session, job, run)
                self._after_item(session, item, job)
                session.commit()
                return Failed(reason)
            description_id, _created = self._repo.insert_description(
                session, project_uid=job.project_uid, key=key, result_id=None if pair.one_sided else pair.result_id,
                page_profile_id=pair.subject_page_profile if pair.one_sided else None, state=run.state,
                prompt_version=prompt_for(kind_of(pair)), model_identity=_model_identity(job, run, recorded),
                recorded=bool(recorded and run.calls),
                description=run.description, calls=len(run.calls), input_tokens=run.input_tokens, output_tokens=run.output_tokens,
                model_call_id=run.last_call_id,
            )
            self._repo.move_item(
                session, job_id=job.job_id, pair_id=pair.pair_id, from_states=("running",), to_state="done",
                description_id=description_id, **counts,
            )
            self._pause_if(session, job, run)
            self._after_item(session, item, job)
            session.commit()
        return Completed()

    def _pause_if(self, session: Session, job: AiJobRecord, run: ds.SheetRun) -> None:
        """A call that took the job over its consent (``CallResult.pause``): the reply is kept and the job stops asking."""
        if run.pause is not None:
            self._jobs_().pause_for_spend(session, job.job_id, run.pause)

    def _interrupted(self, item: WorkItem, job: AiJobRecord, pair: PairFacts, stopped: ds.SheetInterrupted) -> Outcome:
        jobs = self._jobs_()
        cause, run = stopped.cause, stopped.run
        counts = {"calls": len(run.calls), "input_tokens": run.input_tokens, "output_tokens": run.output_tokens, "elapsed_ms": run.elapsed_ms}
        if isinstance(cause, CallLost):
            return Yielded(0.0)  # the lease is gone: nothing is published (the reclaim settles the call)
        with self._sessions() as session:
            item.require_current(session)
            if isinstance(cause, CallRefused):
                if cause.pauses_job:
                    jobs.pause_for_spend(session, job.job_id, cause.reason)
                    self._repo.move_item(session, job_id=job.job_id, pair_id=pair.pair_id, from_states=("running",), to_state="queued")
                    session.commit()
                    return Yielded(PAUSED_WAIT_SECONDS)
                if cause.reason == "connection_busy":
                    self._repo.move_item(session, job_id=job.job_id, pair_id=pair.pair_id, from_states=("running",), to_state="queued")
                    session.commit()
                    return cause.as_outcome()
                reason = cause.reason
            else:
                reason = cause.reason  # OutcomeUnknown: "spend_unknown", never sent again by itself
            self._repo.move_item(
                session, job_id=job.job_id, pair_id=pair.pair_id, from_states=("running",), to_state="failed", reason=reason, **counts,
            )
            self._after_item(session, item, job)
            session.commit()
        return cause.as_outcome()

    def _release(self, item: WorkItem, job_id: str, pair_id: str) -> None:
        """The item stopped (a cancel or a lost lease): its row goes back to ``queued`` so the sheet is not left ``running``."""
        try:
            with self._sessions() as session:
                self._repo.move_item(session, job_id=job_id, pair_id=pair_id, from_states=("running",), to_state="queued")
                session.commit()
        except Exception:  # noqa: BLE001 - the reclaim and the job's state still say what the sheet is
            _LOG.warning("a sheet item could not be released after a stop")

    # -- the end of a job ---------------------------------------------------------------------------------------------------
    def _after_item(self, session: Session, item: WorkItem, job: AiJobRecord) -> None:
        """Hand the job its end: one unlinked ``drain`` item per job completes it when no sheet is live (dedupe keeps it single)."""
        self._deps.work.enqueue(
            session, project_uid=job.project_uid, module=MODULE_VERSIONS, kind=WORK_KIND, payload={"drain_job_id": job.job_id},
            dedupe_key=drain_dedupe_key(job.job_id), delay_seconds=DRAIN_POLL_SECONDS, created_by_user_uid=item.created_by_user_uid,
        )

    def _drain(self, item: WorkItem, job_id: str) -> Outcome:
        jobs = self._jobs_()
        with self._sessions() as session:
            item.require_current(session)
            job = self._ai_repo.get(session, job_id)
            if job is None or job.state != "running":
                session.commit()
                return Completed()  # paused, cancelled, over: a resume or a finish makes the next drain with its next sheet
            if self._ai_repo.live_item_count(session, job_id) > 0:
                session.commit()
                return Yielded(DRAIN_POLL_SECONDS)
            jobs.complete_if_drained(session, job_id)
            session.commit()
        return Completed()


def _model_identity(job: AiJobRecord, run: ds.SheetRun, recorded: bool) -> str:
    """What produced the description: ``program`` when no model was asked (a sheet with no candidate), ``recorded`` for a recorded
    (test) answer, else the pinned model of the job."""
    if not run.calls:
        return "program"
    return "recorded" if recorded else job.pinned_model


def _is_recorded(route: CallRoute) -> bool:
    mode = getattr(route.adapter, "provider_mode", None)
    return getattr(mode, "value", mode) == "recorded"


def sheet_changes_handler(dependencies: WorkDependencies) -> SheetChangesHandler:
    """The factory ``comparison.public.HANDLER_FACTORIES`` holds (a ``HandlerFactory``). Built with no seams of its own: a process whose
    composition root supplies a route source builds the handler with it (see the module note)."""
    return SheetChangesHandler(dependencies)
