"""The `spec` method of the consented AI jobs and the handler of its work kind (`CMP-VC-SPEC-01`, part B).

`ComparisonAiJobService` (`CMP-AI-JOBS-01`) owns the job: the estimate and its digest, the consent, the ceilings, the state edges, the
spend. This module supplies what the core asks of a method (:class:`SpecMethod`) and the worker's side (:class:`SpecHandler`, kind
``comparison_spec``):

* **the estimate.** A job reads the two versions of a transition. A side whose specification text is already stored under its content
  key is *reused* (never sent again); a side that cannot be read as a table (:data:`~.transition.REASON_NOT_PARSED`) needs no request
  (it ends the comparison ``incomplete`` and the sheet-by-sheet description covers it); every other side is **one request** of the size
  of its text. No image goes to a model (the text of the sheet is authoritative, ``docs/whole_specification_comparison.md`` lines
  18-21). A transition with nothing to send is the core's ``comparison_ai_nothing_to_do``.
* **the unit.** One work item is one transition. Its payload names the transition; the core adds the job. The row of the transition's
  whole-specification comparison is opened in the start's transaction (the one write beside the core's: ``comparison_spec_comparison``
  is this lane's table).
* **the handler.** It starts the job (``queued -> running``), proves the lease and the job's state before each request and before it
  writes, reads each side with :class:`~.transition.TransitionRun` (the store first), asks the model **only through the spend
  wrapper** (:class:`~auditmanager.comparison.spend.caller.ComparisonModelCaller`: the journal row is written ``prepared`` before the
  request), and records the comparison. A refusal that pauses the job pauses it through the core; a reply that takes the job over a
  ceiling is kept and stored and the job pauses before the next request.

**What binds a connection is not here.** The worker's dependency bundle carries no key ring and no destination policy, so the live
binding of the routed executor connection (``bind_connection``) cannot be built by a handler factory. :class:`SpecHandler` takes a
``binder(session, job) -> CallRoute``; the shipped default refuses with ``executor_route_missing`` (so nothing is ever sent by a
worker that cannot bind) and the tests supply a recorded one. Wiring the live binder is a FIX item of the wave (report section 9).
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Final

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.analysis.public import ModelRequest, ModelResponse
from auditmanager.comparison.ai_jobs.model import AiCallGroup, AiCounts, AiEstimateRequest, AiJobRecord, AiMode, AiWorkItemSpec
from auditmanager.comparison.ai_jobs.service import ComparisonAiJobService
from auditmanager.comparison.specification import prompt, batches
from auditmanager.comparison.specification.reader import SpecificationReader
from auditmanager.comparison.specification.repository import SpecificationRepository, TransitionScope
from auditmanager.comparison.specification.transition import Answer, PreparedSide, TransitionRun, prepare_side
from auditmanager.comparison.spend.caller import ComparisonModelCaller
from auditmanager.comparison.spend.errors import CallRefused, SpendError
from auditmanager.comparison.spend.model import CallEstimate, CallRoute
from auditmanager.comparison.work.model import Completed, Failed, Outcome, WorkDependencies, WorkItem, Yielded
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "Binder",
    "MAX_OUTPUT_TOKENS",
    "SPEC_KIND",
    "SpecHandler",
    "SpecMethod",
    "build_request",
    "spec_handler",
    "spec_scope",
]

_LOG = logging.getLogger(__name__)

SPEC_KIND: Final[str] = "comparison_spec"
#: The ``max_tokens`` of a request, and the most an estimate assumes (the original runs a CLI with no such cap; a whole specification
#: of a few hundred rows is a few tens of thousands of tokens of JSON). ``[own design]``: the overrun pause measures the truth.
MAX_OUTPUT_TOKENS: Final[int] = 32_000
_OUTPUT_BASE_TOKENS: Final[int] = 600
_OUTPUT_PER_LINE_TOKENS: Final[int] = 160
REASON_PAYLOAD_INVALID: Final[str] = "spec_payload_invalid"
REASON_TRANSITION_NOT_FOUND: Final[str] = "spec_transition_not_found"
REASON_ROUTE_UNBOUND: Final[str] = "spec_route_unbound"
REASON_ANSWER_NOT_JSON: Final[str] = "spec_answer_not_json"
_LEASE_GONE: Final[frozenset[ErrorCode]] = frozenset({ErrorCode.STALE_ATTEMPT, ErrorCode.EXECUTION_TOKEN_INVALID})
#: A job paused at a ceiling gives its item back; the item is looked at again after this many seconds.
_PAUSED_RETRY_SECONDS: Final[float] = 30.0

Binder = Callable[[Session, AiJobRecord], CallRoute]


def build_request(model_identity: str, prompt_text: str, *, idempotency_scope: str | None = None) -> ModelRequest:
    """The request of a side's reading: the rules and the text in one user message, the answer held to the schema. A test files the
    recorded answer under this request's digest."""
    body = {
        "model": model_identity,
        "max_tokens": MAX_OUTPUT_TOKENS,
        "messages": [{"role": "user", "content": prompt_text}],
        "output_config": {"format": {"type": "json_schema", "schema": prompt.extraction_schema()}},
    }
    return ModelRequest(model_id=model_identity, body=body, idempotency_scope=idempotency_scope)


def spec_scope(project_uid: str, document_uid: str, transition_id: str) -> Any:
    from auditmanager.comparison.ai_jobs.model import AiScope

    return AiScope(method="spec", project_uid=project_uid, document_uid=document_uid, transition_id=transition_id)


def _output_tokens(source: Mapping[str, Any]) -> int:
    lines = sum(len(block["lines"]) for block in source["blocks"])
    return min(MAX_OUTPUT_TOKENS, _OUTPUT_BASE_TOKENS + _OUTPUT_PER_LINE_TOKENS * lines)


class SpecMethod:
    """The `spec` method as the core asks for it (:class:`~auditmanager.comparison.ai_jobs.model.AiMethod`)."""

    method: str = "spec"
    prompt_version: str = batches.PROMPT_VERSION

    def __init__(self, session_factory: sessionmaker[Session], blob_store: Any, *, reader: SpecificationReader | None = None,
                 repository: SpecificationRepository | None = None) -> None:
        self._factory = session_factory
        self._reader = reader or SpecificationReader(session_factory, blob_store)
        self._repository = repository or SpecificationRepository()
        self._zero_ready=False

    @property
    def can_run_without_model(self)->bool:
        return self._zero_ready

    def _scope(self, session: Session, transition_id: str | None, project_uid: str) -> TransitionScope:
        scope = None if transition_id is None else self._repository.transition(session, transition_id)
        if scope is None or scope.project_uid != project_uid:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="ComparisonTransition")
        return scope

    def prepared(self, scope: TransitionScope) -> tuple[PreparedSide, PreparedSide]:
        return (
            prepare_side(self._factory, self._reader, self._repository, project_uid=scope.project_uid, version_uid=scope.source_version_uid),
            prepare_side(self._factory, self._reader, self._repository, project_uid=scope.project_uid, version_uid=scope.target_version_uid),
        )

    def counts(self, session: Session, request: AiEstimateRequest) -> AiCounts:
        scope = self._scope(session, request.scope.transition_id, request.scope.project_uid)
        groups: list[AiCallGroup] = []
        reused = 0
        sides = self.prepared(scope)
        pending_assembly=0
        for side in sides:
            if side.stored is not None:
                reused += 1
            elif side.sendable:
                assert side.source is not None
                for batch in side.batches:
                    if batch['stored'] is None and batch['raw'] is None:
                        groups.append(AiCallGroup(calls=1,prompt_chars=len(prompt.prompt_for(batch['source'])),
                            output_tokens=MAX_OUTPUT_TOKENS))
                if side.batches and all(batch['stored'] is not None or batch['raw'] is not None for batch in side.batches):
                    pending_assembly+=1
        row=self._repository.whole(session,scope.transition_id)
        pending_compare=bool((row is None or row.state in {'queued','running','failed','cancelled'})
            and all(side.source is not None and side.source['complete'] for side in sides))
        self._zero_ready=not groups and bool(pending_assembly or pending_compare)
        units=len(sides) if groups else pending_assembly or (1 if pending_compare else 0)
        return AiCounts(groups=tuple(groups), units=units, reused=reused, versions=len(sides))

    def work_items(self, session: Session, job: AiJobRecord, mode: AiMode) -> Sequence[AiWorkItemSpec]:
        scope = self._scope(session, job.transition_id, job.project_uid)
        sides = self.prepared(scope)
        previous=self._repository.whole(session,scope.transition_id)
        keys=[side.key for side in sides]
        if mode is not AiMode.START and (previous is None or any(
                (coverage or {}).get('planning_revision')!=batches.REVISION or
                (coverage or {}).get('source_key')!=key
                for coverage,key in zip((previous.coverage_a,previous.coverage_b),keys))):
            raise DomainError(ErrorCode.CONFLICT,conflict_reason='comparison_ai_estimate_stale')
        if not any(side.sendable for side in sides) and not self._zero_ready:
            return []
        if mode is AiMode.START or previous is not None and previous.state in {'failed','cancelled','incomplete'}:
            # The row of the transition's comparison starts with the job (a terminal one goes back to ``queued``).
            self._repository.open_whole(
                session, scope, job_id=job.job_id, sheets_a=sides[0].side.sheets, sheets_b=sides[1].side.sheets)
        self._repository.pin_plan(session,scope.transition_id,keys)
        return [AiWorkItemSpec(unit_key=f"transition:{scope.transition_id}", payload={"transition_id": scope.transition_id,
            'planning_revision':batches.REVISION,'source_keys':keys})]


def _payload(payload: Mapping[str, Any]) -> tuple[str, str]:
    """``(transition_id, ai_job_id)`` of an item's payload, or ``ValueError``."""
    from auditmanager.shared.identity import ComparisonAiJobId, ComparisonTransitionId

    transition, job = payload.get("transition_id"), payload.get("ai_job_id")
    if not isinstance(transition, str) or not isinstance(job, str):
        raise ValueError("the payload of a comparison_spec item names a transition and a job")
    ComparisonTransitionId(transition)
    ComparisonAiJobId(job)
    return transition, job


def unbound_binder(session: Session, job: AiJobRecord) -> CallRoute:
    """The shipped binder: the worker cannot build the live binding (see the module), so it refuses and nothing is sent."""
    raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="executor_route_missing")


class _Stop(Exception):
    """The item stops without writing: the lease is gone, a cancel was requested, or the job is not running."""


class _SpecFailure(Exception):
    def __init__(self,reason:str)->None:
        self.reason=reason


class SpecHandler:
    """The one handler of kind ``comparison_spec`` (a :class:`~auditmanager.comparison.work.model.WorkHandler`)."""

    kind: str = SPEC_KIND

    def __init__(
        self, dependencies: WorkDependencies, *, binder: Binder = unbound_binder, caller: ComparisonModelCaller | None = None,
        jobs: ComparisonAiJobService | None = None,
    ) -> None:
        #: Read when an item runs, not when the factory is applied (the registry builds a handler to learn its kind).
        self._dependencies = dependencies
        self._binder = binder
        self._repository = SpecificationRepository()
        self._given = (caller, jobs)
        self._built: tuple[ComparisonModelCaller, TransitionRun, ComparisonAiJobService] | None = None

    def _parts(self) -> tuple[ComparisonModelCaller, TransitionRun, ComparisonAiJobService]:
        if self._built is None:
            dependencies = self._dependencies
            caller, jobs = self._given
            run = TransitionRun(dependencies.session_factory, dependencies.blob_store, repository=self._repository)
            self._built = (
                caller or ComparisonModelCaller(dependencies.session_factory), run,
                # The worker's side of the core needs no module flag or provider mode (the loop does not claim while the module is off).
                jobs or ComparisonAiJobService(
                    dependencies.session_factory, methods=[SpecMethod(dependencies.session_factory, dependencies.blob_store)],
                    comparison_modules="versions"),
            )
        return self._built

    def run(self, item: WorkItem) -> Outcome:
        try:
            transition_id, job_id = _payload(item.payload)
        except ValueError:
            _LOG.error("comparison work %s: the comparison_spec payload is not valid", item.work_id)
            return Failed(REASON_PAYLOAD_INVALID)
        sessions = self._dependencies.session_factory
        caller, runner, jobs = self._parts()
        try:
            with session_scope(sessions) as session:
                self._checkpoint(item, session)
                if jobs.mark_running(session, job_id) != "running":
                    return Yielded(_PAUSED_RETRY_SECONDS)  # paused or cancelled while the item waited: nothing is sent
                job = jobs.job(session, job_id)
                consent = jobs.consent_for_calls(session, job_id)
                scope = self._repository.transition(session, transition_id)
                if scope is None:
                    return Failed(REASON_TRANSITION_NOT_FOUND)
                self._repository.set_state(session, transition_id, to_state="running", from_states=("queued",), phase="preparing")
                try:
                    route = self._binder(session, job)
                except DomainError as refusal:
                    if refusal.code in (ErrorCode.DEPENDENCY_UNAVAILABLE, ErrorCode.DEPENDENCY_CREDENTIAL_REFUSED):
                        return Failed(REASON_ROUTE_UNBOUND, retry=True)
                    raise
        except _Stop as stop:
            _LOG.info("comparison work %s (comparison_spec): stopped: %s", item.work_id, stop)
            return Yielded()
        except DomainError as refusal:
            if refusal.code in _LEASE_GONE:
                item.lease_lost.set()
                return Yielded()
            raise
        paused = {"now": False}
        expected_keys=dict(zip((scope.source_version_uid,scope.target_version_uid),item.payload.get('source_keys') or []))

        prepared=runner.prepared(scope)
        if item.payload.get('planning_revision')!=batches.REVISION or item.payload.get('source_keys')!=[side.key for side in prepared]:
            with session_scope(sessions) as session:
                self._checkpoint(item,session)
                jobs.fail(session,job_id,'spec_source_changed')
                self._repository.set_state(session,transition_id,to_state='failed',from_states=('queued','running'),
                    phase='done',reason='SPEC_INPUT_PLAN_CHANGED')
            return Failed('spec_source_changed')

        def ask(prompt_text: str, metadata:dict) -> Answer:
            if metadata.get('source_key')!=expected_keys.get(metadata.get('version_uid')):
                raise _SpecFailure('spec_source_changed')
            with sessions() as session:
                raw=self._repository.find_extraction(session,scope.project_uid,metadata['raw_key'])
            if raw is not None:
                if raw.coverage.get('prompt_sha256')!=metadata['prompt_sha256']:
                    raise _SpecFailure('spec_source_changed')
                response=ModelResponse(**raw.coverage['response'])
                if response.response_sha256!=raw.coverage.get('response_sha256'):
                    raise _SpecFailure('spec_saved_reply_invalid')
                return Answer(None if response.truncated else batches.parse_reply(response.output_text),
                    raw.model_identity,raw.recorded,raw.model_call_id)
            if paused["now"]:
                raise _Stop("the job paused at a ceiling")
            with sessions() as session:
                self._checkpoint(item, session)
                if jobs.state_of(session, job_id) != "running":
                    raise _Stop("the job is not running")
            request = build_request(job.pinned_model, prompt_text, idempotency_scope=f"{job_id}:{item.work_id}")
            with sessions() as session:
                status=self._repository.paid_dispatch_fence(session,project_uid=scope.project_uid,
                    job_id=job_id,request_sha256=request.request_sha256)
            if status in {'prepared','sent'}:raise _Stop('a paid request is in flight')
            if status is not None:raise _SpecFailure('spend_unknown')
            input_tokens = AiCallGroup(calls=1, prompt_chars=len(prompt_text), output_tokens=MAX_OUTPUT_TOKENS).input_tokens_per_call
            result = caller.call(
                item, route, request, estimate=CallEstimate(input_tokens=input_tokens, output_tokens=MAX_OUTPUT_TOKENS), consent=consent)
            # Immutable raw custody precedes parsing and an overrun pause. If the
            # process ends before this write, the paid journal row forbids resend.
            with session_scope(sessions) as session:
                self._checkpoint(item,session)
                self._repository.insert_extraction(session,project_uid=scope.project_uid,
                    version_uid=metadata['version_uid'],content_key=metadata['raw_key'],state='partial',
                    prompt_version=batches.RAW_VERSION,model_identity=route.model_identity,recorded=_recorded(route),
                    source_sha256=metadata['source_sha256'],positions=[],model_call_id=result.call_id,
                    coverage={'record_kind':'raw_reply','planning_revision':batches.REVISION,
                        'batch_id':metadata['batch_id'],'prompt_sha256':metadata['prompt_sha256'],
                        'request_sha256':request.request_sha256,'response_sha256':result.response.response_sha256,
                        'response':asdict(result.response),'truncated':result.response.truncated})
            if result.pause is not None:
                with session_scope(sessions) as session:
                    jobs.pause_for_spend(session, job_id, result.pause.reason)
                paused["now"] = True  # the reply is paid for and kept; no further request is made
            payload=None if result.response.truncated else batches.parse_reply(result.response.output_text)
            return Answer(
                payload=payload, model_identity=route.model_identity, recorded=_recorded(route), model_call_id=result.call_id)

        try:
            def progress(version_uid,coverage):
                with session_scope(sessions) as session:
                    self._checkpoint(item,session)
                    self._repository.progress(session,transition_id,
                        'a' if version_uid==scope.source_version_uid else 'b',coverage)
            old, new = runner.read(scope, ask=None,ask_batch=ask,progress=progress)
            with session_scope(sessions) as session:
                self._repository.set_state(session, transition_id, to_state="running", from_states=("running",), phase="comparing")
            outcome = runner.compare(scope, old, new)

            def fence(session: Session) -> None:
                item.require_current(session)
                if jobs.state_of(session, job_id) != "running":
                    raise _Stop("the job is not running")

            written = runner.finish(scope, outcome, fence=fence)
            if written:
                with session_scope(sessions) as session:
                    self._complete(jobs, session, job_id)
        except _Stop as stop:
            _LOG.info("comparison work %s (comparison_spec): stopped: %s", item.work_id, stop)
            return Yielded(_PAUSED_RETRY_SECONDS) if paused["now"] else Yielded()
        except _SpecFailure as failure:
            with session_scope(sessions) as session:
                self._checkpoint(item,session)
                jobs.fail(session,job_id,failure.reason)
                self._repository.set_state(session,transition_id,to_state='failed',from_states=('queued','running'),
                    phase='done',reason='SPEC_PAID_INPUT_UNCONFIRMED')
            return Failed(failure.reason)
        except CallRefused as refused:
            if refused.pauses_job:
                with session_scope(sessions) as session:
                    jobs.pause_for_spend(session, job_id, refused.reason)
            return refused.as_outcome()
        except SpendError as error:
            return error.as_outcome()
        except DomainError as refusal:
            if refusal.code in _LEASE_GONE:
                item.lease_lost.set()
                return Yielded()
            raise
        return Yielded(_PAUSED_RETRY_SECONDS) if paused["now"] and not written else Completed()

    def _complete(self, jobs: ComparisonAiJobService, session: Session, job_id: str) -> None:
        """The job has one unit, and it is this one: it is done. ``complete_if_drained`` counts the item that is calling as live,
        so it cannot say so from inside the handler (a FIX item of the core, report section 9); the job's one item is ended by the
        queue right after this transaction."""
        if not jobs.complete_if_drained(session, job_id):
            jobs._repo.move(session, job_id, from_states=("running",), to_state="completed")  # noqa: SLF001

    def _checkpoint(self, item: WorkItem, session: Session) -> None:
        if item.lease_lost.is_set():
            raise _Stop("the lease is gone")
        if item.cancelled.is_set():
            raise _Stop("a cancel was requested")
        try:
            item.check_current(session)
        except DomainError as refusal:
            if refusal.code in _LEASE_GONE:
                item.lease_lost.set()
                raise _Stop("the lease is gone") from refusal
            raise


def _recorded(route: CallRoute) -> bool:
    from auditmanager.analysis.public import ProviderMode

    return getattr(route.adapter, "provider_mode", None) == ProviderMode.RECORDED


def spec_handler(dependencies: WorkDependencies) -> SpecHandler:
    """The factory ``comparison.public.HANDLER_FACTORIES`` holds (a ``HandlerFactory``)."""
    routes = getattr(dependencies, "routes", None)
    return SpecHandler(dependencies, binder=unbound_binder if routes is None else routes.route)
