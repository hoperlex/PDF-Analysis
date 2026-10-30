"""The handler of the ``comparison_report`` work kind (`CMP-VC-REPORT-01`, ADR-0025 decisions 4, 5, 6, 8, 10, 11, 19, wave brief section 1).

A report job is a handful of items: **one per transition** (the client kind: one call over the facts of the transition; the analytic kind: the
analyst, then the verifier) and **one final item**. Every model call goes through ``comparison.spend`` -- the journal row is written ``prepared``
**before** the request and settled after, the consent and the ceilings are checked before each call, an outcome that cannot be known is never
retried blindly -- and a call is made only for a job that is ``running``: a paused or cancelled job sends nothing.

A transition item is finished when its part is stored (``comparison_report_part``: the marks, the counts and, in ``facts``, the content key and the
checked result); a part that is already finished under its content key is **never requested again**, and a retry of an item that had finished its
analyst call goes on with the verifier. The program's checks decide what is kept: a point the facts do not confirm is dropped, an answer that fails
a hard check is asked again with the program's remarks up to the original's retry limits, and a unit that never gives a fit answer is a failed
part (the report is then partial, never silently complete).

The final item waits (a ``Yielded``) until every other item of the job has ended, then: with a unit unfinished the report is **partial** and no
PDF is written (the original's «неполный результат», ``md_report/runner.py:925-928``); otherwise the client view or, for the analytic kind, the
composer's checked answer is made into the document and written to a PDF **by a program in a child under the ceilings of decision 8**
(``pdf/``), checked, stored as artifacts and the job is completed. A report that fails its checks, or whose PDF does not, fails with a reason that
names it; «Продолжить» then finishes it under the held consent.

The model route comes from a :class:`ModelSource`. The live binding of a routed connection (its secret, its address, the executors' adapter) is the
composition root's: the factory in ``HANDLER_FACTORIES`` holds a source that answers ``executor_route_missing``, so a worker with no binding fails an
item with that reason and calls nothing -- never a silent fallback. Tests supply :class:`StaticModelSource` over ``RecordedAnswers``.

How an item ends: ``Completed`` when its part (or the final stage) is written; ``Yielded`` while the job is not running or other items still run;
``Failed`` with a code for a unit that gave no fit answer or a call that failed; a ``CallRefused`` that pauses the job pauses it (``comparison.ai_jobs``).
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass, asdict
from typing import Any, Final, Protocol

from sqlalchemy.orm import Session

from auditmanager.comparison.ai_jobs.model import CHARS_PER_TOKEN_DENOMINATOR, CHARS_PER_TOKEN_NUMERATOR, AiJobRecord
from auditmanager.comparison.ai_jobs.repository import AiJobRepository
from auditmanager.comparison.ai_jobs.service import ComparisonAiJobService
from auditmanager.comparison.report import analytic, client, disciplines, document as document_module, chunks as chunk_module
from auditmanager.analysis.public import ModelResponse
from auditmanager.comparison.report import plan as plan_module
from auditmanager.comparison.report.method import part_done
from auditmanager.comparison.report.model import (
    ARTIFACT_PDF,
    ARTIFACT_TEXT,
    FAIL_CHECK,
    FAIL_PDF,
    FAIL_PDF_CHECK,
    FAIL_SOURCE,
    KIND_CLIENT,
    STAGE_COMPOSITION,
    STAGE_PDF_WRITING,
    STAGE_VERIFICATION,
    STAGE_TRANSITION_ANALYSIS,
    WORK_KIND,
)
from auditmanager.comparison.report.pdf.runner import ChildStartError, PdfFailed, write_pdf
from auditmanager.comparison.report.plan import ANALYTIC_RETRIES, CLIENT_RETRIES, MAX_TOKENS, SYSTEM_TEXT, SourceDoc, Unit
from auditmanager.comparison.report.repository import PartRow, ReportRepository, ReportRow
from auditmanager.comparison.report.service import ROLE_PDF, ROLE_TEXT, ComparisonReportService
from auditmanager.comparison.report.sync import sync_report
from auditmanager.comparison.spend.caller import ComparisonModelCaller
from auditmanager.comparison.spend.errors import CallFailed, CallLost, CallRefused, OutcomeUnknown
from auditmanager.comparison.spend.model import CallEstimate, CallResult, CallRoute
from auditmanager.comparison.work.model import Completed, Failed, Outcome, WorkDependencies, WorkItem, Yielded
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "FINAL_POLL_SECONDS",
    "PAYLOAD_KEYS",
    "PAUSED_POLL_SECONDS",
    "REASON_MODEL_SOURCE",
    "ReportHandler",
    "StaticModelSource",
    "UnavailableModelSource",
    "program_unit_result",
    "read_payload",
    "report_handler",
]

_LOG = logging.getLogger(__name__)
PAYLOAD_KEYS: Final[frozenset[str]] = frozenset({"report_id", "unit", "transition_id", "number", "ai_job_id"})
#: How long the final item waits before it looks at the other items again, and a yielded item of a job that is not running.
FINAL_POLL_SECONDS: Final[float] = 5.0
PAUSED_POLL_SECONDS: Final[float] = 30.0
REASON_PAYLOAD_INVALID: Final[str] = "report_payload_invalid"
REASON_NOT_FOUND: Final[str] = "report_not_found"
REASON_MODEL_SOURCE: Final[str] = "executor_route_missing"
REASON_ANSWER_INVALID: Final[str] = "model_answer_invalid"
REASON_ANSWER_UNFIT: Final[str] = "model_answer_unfit"
REASON_SOURCE_INVALID: Final[str] = "report_source_invalid"
_LEASE_GONE: Final[frozenset[ErrorCode]] = frozenset({ErrorCode.STALE_ATTEMPT, ErrorCode.EXECUTION_TOKEN_INVALID})
#: The program's remarks, sent back with an answer it did not accept (client_edit.py:864-865; runner.py:771-777).
_FEEDBACK: Final[str] = "\n\nПРЕДЫДУЩИЙ ОТВЕТ НЕ ПРОШЁЛ ПРОВЕРКУ ПРОГРАММЫ:\n- {problems}\nВерни полный исправленный ответ по той же схеме.\n"


# ------------------------------------------------------------------ the model source

class ModelSource(Protocol):
    """Where a job's calls go: the route of the job's pinned connection revision, as the spend wrapper takes it."""

    def route(self, session: Session, job: AiJobRecord) -> CallRoute: ...


class UnavailableModelSource:
    """A worker with no binding of a routed connection: every call is refused by name, none is made."""

    def route(self, session: Session, job: AiJobRecord) -> CallRoute:
        raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency=REASON_MODEL_SOURCE)


class StaticModelSource:
    """One adapter for every job (a test's ``RecordedAnswers`` or a scripted live adapter): the route names the job's own revision and model."""

    def __init__(
        self, adapter: Any, *, pin: Any = None, expected_model: str | None = None, unmetered: bool = False, revision_id: str | None = None,
    ) -> None:
        """``revision_id`` is the revision the calls travel on when it is not the one the job consented to (a test of «the route changed»)."""
        self._adapter, self._pin, self._expected, self._unmetered, self._revision = adapter, pin, expected_model, unmetered, revision_id

    def route(self, session: Session, job: AiJobRecord) -> CallRoute:
        return CallRoute(
            adapter=self._adapter, model_identity=job.pinned_model, connection_revision_id=self._revision or job.connection_revision_id,
            expected_model=self._expected, unmetered=self._unmetered, pin=self._pin,
        )


class _Ended(Exception):
    """An item ends here with this outcome."""

    def __init__(self, outcome: Outcome) -> None:
        super().__init__(type(outcome).__name__)
        self.outcome = outcome


@dataclass(frozen=True, slots=True)
class _Run:
    report: ReportRow
    job: AiJobRecord
    consent: Any


def read_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """The payload of an item: ``report_id`` and ``unit`` (``transition`` with its ``transition_id`` and ``number``, or ``final``); ``ValueError`` otherwise."""
    if set(payload) - PAYLOAD_KEYS or not isinstance(payload.get("report_id"), str) or payload.get("unit") not in ("transition", "final"):
        raise ValueError("the payload of a report item names its report and its unit")
    if payload["unit"] == "transition" and not (isinstance(payload.get("transition_id"), str) and isinstance(payload.get("number"), int)):
        raise ValueError("a transition item names its transition")
    return dict(payload)


def program_unit_result(transition: Mapping[str, Any]) -> dict[str, Any]:
    """The verified result of a transition the program finishes without a model (the confirmed absence of changes), in the verifier's shape."""
    return {
        "run_id": "program", "unit_id": "program", "claims": [], "significant_candidates": [], "unresolved_questions": [],
        "missing_transitions_or_blocks": [],
        "transitions": [{
            "transition_id": transition["transition_id"], "content_status": "no_content_changes",
            "change_scope": "Нет изменений содержания", "significance": "Нет новых технических изменений",
            "assessment_basis": "в сводке явная отметка «изменений содержания нет»", "main_changes": "Изменений содержания нет.",
            "construction_impact": "Дополнительных технических последствий в этом переходе не выявлено.", "key_claim_ids": [], "evidence": [],
        }],
    }


def _tokens(chars: int) -> int:
    return -(-chars * CHARS_PER_TOKEN_NUMERATOR // CHARS_PER_TOKEN_DENOMINATOR)


def _json(text: str) -> dict[str, Any] | None:
    try:
        value = json.loads(text)
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


class ReportHandler:
    """The one handler of kind ``comparison_report`` (a :class:`~auditmanager.comparison.work.model.WorkHandler`)."""

    kind: str = WORK_KIND

    def __init__(
        self, dependencies: WorkDependencies, *, model_source: ModelSource | None = None, caller: ComparisonModelCaller | None = None,
        pdf_runner: Any = None, service: ComparisonAiJobService | None = None,
    ) -> None:
        #: Nothing of the dependencies is read here: the registry builds a handler only to learn its kind (with an empty namespace in
        #: a unit test), and a worker's dependencies are read when an item runs (``_wire``).
        self._deps = dependencies
        self._given = (model_source, caller, pdf_runner, service)
        self._wired = False

    def _wire(self) -> None:
        """Build the collaborators on the first item (the dependencies are complete by then)."""
        if self._wired:
            return
        model_source, caller, pdf_runner, service = self._given
        dependencies = self._deps
        self._sessions = dependencies.session_factory
        self._source = model_source or UnavailableModelSource()
        self._caller = caller or ComparisonModelCaller(self._sessions)
        self._runner = pdf_runner
        self._repo = ReportRepository()
        self._jobs = service or ComparisonAiJobService(self._sessions, methods=[], comparison_modules="versions", provider_mode="live")
        self._reports = ComparisonReportService(
            self._sessions, blob_store=dependencies.blob_store, comparison_modules="versions", provider_mode="live",
        )
        self._wired = True

    # -- the entry ----------------------------------------------------------------------------------
    def run(self, item: WorkItem) -> Outcome:
        self._wire()
        try:
            payload = read_payload(item.payload)
        except ValueError:
            _LOG.error("comparison work %s: the report payload is not valid", item.work_id)
            return Failed(REASON_PAYLOAD_INVALID)
        try:
            if payload["unit"] == "final":
                return self._final(item, payload)
            return self._transition(item, payload)
        except _Ended as ended:
            self._mark_failed_part(item, payload, ended.outcome)
            return ended.outcome
        except DomainError as error:
            if error.code in _LEASE_GONE:
                item.lease_lost.set()
                return Yielded()
            raise

    # -- the start of an item -------------------------------------------------------------------------
    def _begin(self, item: WorkItem, payload: Mapping[str, Any]) -> _Run:
        """The item starts the job (``queued -> running``); a job that is not running sends nothing."""
        with self._sessions() as session:
            row = self._repo.get(session, payload["report_id"])
            if row is None or row.job_id is None or row.job_id != item.payload.get("ai_job_id"):
                raise _Ended(Failed(REASON_NOT_FOUND))
            state = self._jobs.mark_running(session, row.job_id)
            job = self._jobs.job(session, row.job_id)
            consent = self._jobs.consent_for_calls(session, row.job_id)
            sync_report(session, self._repo, row.report_id, job)
            session.commit()
        if state != "running":
            raise _Ended(Yielded(PAUSED_POLL_SECONDS) if state in ("queued", "paused") else Yielded())
        return _Run(row, job, consent)

    def _guard(self, item: WorkItem, run: _Run) -> None:
        """Between two calls: stop on a cancel, a lost lease or a job that is no longer running."""
        if item.lease_lost.is_set() or item.cancelled.is_set():
            raise _Ended(Yielded())
        with self._sessions() as session:
            state = self._jobs.state_of(session, run.job.job_id)
        if state != "running":
            raise _Ended(Yielded(PAUSED_POLL_SECONDS) if state in ("queued", "paused") else Yielded())

    # -- one model call -------------------------------------------------------------------------------
    def _ask(self, item: WorkItem, run: _Run, user_text: str, schema: Mapping[str, Any], max_tokens: int) -> CallResult:
        with self._sessions() as session:
            try:
                route = self._source.route(session, run.job)
            except DomainError:
                raise _Ended(Failed(REASON_MODEL_SOURCE)) from None
        request = plan_module.request_for(route.model_identity, user_text, schema, max_tokens)
        estimate = CallEstimate(input_tokens=_tokens(len(SYSTEM_TEXT) + len(user_text)), output_tokens=max_tokens)
        try:
            return self._caller.call(item, route, request, estimate=estimate, consent=run.consent)
        except CallRefused as refused:
            if refused.pauses_job:
                with self._sessions() as session:
                    self._jobs.pause_for_spend(session, run.job.job_id, refused.reason)
                    sync_report(session, self._repo, run.report.report_id, self._jobs.job(session, run.job.job_id))
                    session.commit()
            raise _Ended(refused.as_outcome()) from None
        except (CallFailed, OutcomeUnknown, CallLost) as error:
            raise _Ended(error.as_outcome()) from None

    def _pause_after(self, session: Session, run: _Run, item: WorkItem, result: CallResult) -> None:
        """The call that took the job past 1.2 x its estimate was paid for and is kept; the job makes no further call. A job with no model work
        left (the client kind's last transition; the PDF is no call) is not paused: a pause would hold back a file that costs nothing, and a resume
        would have no work to take a new consent for."""
        if result.pause is None:
            return
        if run.report.kind == KIND_CLIENT and not self._repo.other_live_units(session, run.job.job_id, item.work_id):
            return
        self._jobs.pause_for_spend(session, run.job.job_id, result.pause.reason)

    # -- a transition ----------------------------------------------------------------------------------
    def _transition(self, item: WorkItem, payload: Mapping[str, Any]) -> Outcome:
        run = self._begin(item, payload)
        transition_id = payload["transition_id"]
        with self._sessions() as session:
            try:
                doc = self._reports.source_doc(session, run.report)
            except DomainError:
                raise _Ended(Failed(FAIL_SOURCE)) from None
            part = self._repo.part(session, run.report.report_id, transition_id)
            unchanged = self._reports.unchanged_from(session, run.report)
            profile = disciplines.resolve(doc.manifest.get("project_code"))
            units = plan_module.build_units(
                run.report.kind, doc, profile, project_uid=run.report.project_uid, model=run.job.pinned_model, unchanged=unchanged,
                only=int(payload["number"]),
            )
        if part is None:  # a unit item of a report with no part for its transition is a defect of the job, never a quiet success
            raise _Ended(Failed(REASON_NOT_FOUND))
        if not units or not units[0].editable:
            return Completed()  # finished by the program (no change, or nothing described): no call
        unit = units[0]
        if run.report.kind != KIND_CLIENT and (part.facts or {}).get("content_key")!=unit.key:
            raise _Ended(Failed(FAIL_SOURCE))
        if part_done(part, run.report.kind):
            return Completed()  # a finished part is never requested again
        if run.report.kind == KIND_CLIENT:
            return self._client_unit(item, run, doc, unit, profile, transition_id)
        return self._analytic_chunks(item, run, doc, unit, part, transition_id)

    def _store(
        self, item: WorkItem, run: _Run, transition_id: str, *, result: CallResult | None, analysis: str | None, verification: str | None,
        selection: str | None, facts: Mapping[str, Any], warnings: int | None = None, points: int | None = None, questions: int | None = None,
        stage: str | None = None,
    ) -> None:
        with self._sessions() as session:
            item.require_current(session)
            self._repo.set_part(
                session, run.report.report_id, transition_id, analysis=analysis, verification=verification, selection=selection,
                facts=facts, warnings=warnings, points=points, questions=questions,
            )
            if result is not None:
                self._pause_after(session, run, item, result)
            sync_report(session, self._repo, run.report.report_id, self._jobs.job(session, run.job.job_id), stage=stage)
            session.commit()

    def _client_unit(
        self, item: WorkItem, run: _Run, doc: SourceDoc, unit: Unit, profile: Mapping[str, Any], transition_id: str,
    ) -> Outcome:
        """One call over the facts of the transition; the program's check keeps the points the facts confirm (client_edit.py:775-908)."""
        transition = unit.transition
        text, groups, support = client.packet(doc.registry["facts"], transition["label"], profile)
        base = client.prompt_for(transition, text, client.prompt_text(), f"{unit.key}:{transition['label']}", dict(profile))
        feedback, reason = "", REASON_ANSWER_UNFIT
        for attempt in range(1, CLIENT_RETRIES + 2):
            self._guard(item, run)
            result = self._ask(item, run, base + feedback, client.schema(), MAX_TOKENS["client"])
            answer = _json(result.response.output_text)
            if answer is None:
                reason, feedback = REASON_ANSWER_INVALID, _FEEDBACK.format(problems="the answer is not a JSON object")
            else:
                checked = client.check(answer, transition, doc.registry["facts"], groups, support)
                if not checked["hard"]:
                    stored = {
                        "answer": answer, "kept": checked["kept"], "dropped": checked["dropped"], "impact": checked["impact"],
                        "fixes": checked["fixes"],
                    }
                    self._store(
                        item, run, transition_id, result=result, analysis=None, verification=None, selection="done",
                        facts={"content_key": unit.key, "attempts": attempt, "discipline": profile["key"], "result": stored},
                        points=len(checked["kept"]), questions=len(answer.get("questions") or []),
                    )
                    return Completed()
                reason, feedback = REASON_ANSWER_UNFIT, _FEEDBACK.format(problems="\n- ".join(client.problems_text(checked)))
            if result.pause is not None:  # a paid answer that was no use, and the job is over its estimate: stop here
                self._store(
                    item, run, transition_id, result=result, analysis=None, verification=None, selection="pending",
                    facts={"content_key": unit.key},
                )
                raise _Ended(Yielded(PAUSED_POLL_SECONDS))
        self._store(
            item, run, transition_id, result=None, analysis=None, verification=None, selection="failed",
            facts={"content_key": unit.key, "error": reason},
        )
        raise _Ended(Failed(reason))

    def _durable_ask(self, item, run, transition_id, facts, slot, user_text, schema, max_tokens):
        """Read a saved paid response before routes/spend, and never blindly repeat its request."""
        if len(user_text)>chunk_module.MAX_PROMPT_CHARS:
            raise _Ended(Failed(FAIL_CHECK))
        request=plan_module.request_for(run.job.pinned_model,user_text,schema,max_tokens)
        saved=facts.setdefault('paid_replies',{}).get(slot)
        if saved is not None:
            if saved.get('request_sha256')!=request.request_sha256:
                raise _Ended(Failed(FAIL_SOURCE))
            response=ModelResponse(**saved['response'])
            if response.response_sha256!=saved.get('response_sha256'):
                raise _Ended(Failed(FAIL_SOURCE))
            return response
        self._guard(item,run)
        with self._sessions() as session:
            fence=self._repo.paid_dispatch_fence(session,job_id=run.job.job_id,request_sha256=request.request_sha256)
            if fence in {'prepared','sent'}:
                raise _Ended(Yielded(FINAL_POLL_SECONDS))
            if fence is not None:
                raise _Ended(Failed('spend_unknown'))
            try:
                route=self._source.route(session,run.job)
            except DomainError:
                raise _Ended(Failed(REASON_MODEL_SOURCE)) from None
            if route.model_identity!=run.job.pinned_model:
                raise _Ended(Failed(REASON_MODEL_SOURCE))
        estimate=CallEstimate(input_tokens=_tokens(len(SYSTEM_TEXT)+len(user_text)),output_tokens=max_tokens)
        try:
            result=self._caller.call(item,route,request,estimate=estimate,consent=run.consent)
        except CallRefused as refused:
            if refused.pauses_job:
                with self._sessions() as session:
                    self._jobs.pause_for_spend(session,run.job.job_id,refused.reason)
                    sync_report(session,self._repo,run.report.report_id,self._jobs.job(session,run.job.job_id))
                    session.commit()
            raise _Ended(refused.as_outcome()) from None
        except (CallFailed,OutcomeUnknown,CallLost) as error:
            raise _Ended(error.as_outcome()) from None
        # Persist raw reply before parsing/checking or honouring an overrun pause.
        # A crash in the caller->custody gap is fenced by the completed journal row.
        facts['paid_replies'][slot]={'request_sha256':request.request_sha256,'call_id':result.call_id,
            'response_sha256':result.response.response_sha256,'response':asdict(result.response)}
        if slot.startswith('composer:'):
            with self._sessions() as session:
                current=self._repo.part(session,run.report.report_id,transition_id)
            if current is None:raise _Ended(Failed(FAIL_SOURCE))
            self._store(item,run,transition_id,result=result,analysis=current.analysis,
                verification=current.verification,selection=current.selection,facts=facts,
                warnings=current.warnings,points=current.points,questions=current.questions)
        else:
            self._save_chunk_facts(item,run,transition_id,facts,result=result)
        return result.response

    def _save_chunk_facts(self,item,run,transition_id,facts,*,result=None):
        coverage=chunk_module.coverage(facts)
        facts['chunk_coverage']=coverage
        rows=facts.get('chunks',[])
        complete=bool(rows) and coverage['verified']==len(rows)
        all_analysed=bool(rows) and coverage['analysed']==len(rows)
        warnings=sum(len(row.get('analysis_result',{}).get('soft',[]))+
            len(row.get('verification_result',{}).get('soft',[])) for row in rows)
        self._store(item,run,transition_id,result=result,
            analysis='done' if all_analysed else 'running',verification='done' if complete else
                'running' if any(row.get('verification') in {'running','done'} for row in rows) else 'pending',
            selection=None,facts=facts,warnings=warnings,
            stage=STAGE_VERIFICATION if any(row.get('verification')=='running' for row in rows)
                else STAGE_TRANSITION_ANALYSIS)

    def _chunk_attempts(self,item,run,transition_id,facts,chunk,stage,prompt,schema,check):
        feedback=''
        for attempt in range(ANALYTIC_RETRIES+1):
            self._guard(item,run)
            slot=f'{chunk["chunk_id"]}:{stage}:{attempt}'
            response=self._durable_ask(item,run,transition_id,facts,slot,prompt+feedback,schema,MAX_TOKENS[stage])
            answer=None if response.truncated else chunk_module.parse_reply(response.output_text)
            checked={'hard':['answer is truncated, too large, or not a JSON object'],'soft':[]}
            if answer is not None:
                try:
                    chunk_module.validate_shape(answer,schema)
                    checked=check(answer)
                except (KeyError,TypeError,ValueError):
                    checked={'hard':['answer schema or source references are invalid'],'soft':[]}
                if not checked['hard']:
                    return answer,checked
            feedback=_FEEDBACK.format(problems='\n- '.join(checked['hard']))
            if len(feedback)>8_000:
                feedback=_FEEDBACK.format(problems='the answer failed the exact input/source partition; return only the assigned records')
        raise _Ended(Failed(REASON_ANSWER_UNFIT))

    def _analytic_chunks(self,item,run,doc,unit,part,transition_id):
        facts=dict(part.facts or {})
        if (facts.get('content_key')!=unit.key or facts.get('planning_revision')!=chunk_module.REVISION
                or len(facts.get('chunks',[]))!=len(unit.chunks)):
            raise _Ended(Failed(FAIL_SOURCE))
        for chunk,row in zip(unit.chunks,facts['chunks']):
            if any(row.get(key)!=chunk[key] for key in ('chunk_id','line_start','line_end','source_sha256')):
                raise _Ended(Failed(FAIL_SOURCE))
            if row.get('verification')=='done':
                continue
            self._guard(item,run)
            manifest,plan,group,verify_unit=chunk_module.context(doc.manifest,unit.transition,chunk)
            if row.get('analysis')!='done':
                row['analysis']='running'
                self._save_chunk_facts(item,run,transition_id,facts)
                prompt=analytic.analyst_prompt(run.report.report_id,doc.source,manifest,plan,group,doc.lines)
                prompt+=chunk_module.note(chunk,len(unit.chunks))
                answer,checked=self._chunk_attempts(item,run,transition_id,facts,chunk,'analyst',prompt,
                    analytic.ANALYST_SCHEMA,
                    lambda value:chunk_module.check_analyst(value,run.report.report_id,group,plan,manifest))
                row.update(analysis='done',analysis_result={'answer':answer,'soft':checked['soft']})
                row.pop('error',None)
                self._save_chunk_facts(item,run,transition_id,facts)
            answer=row['analysis_result']['answer']
            results={group['group_id']:answer}
            claims=analytic.claims_for_unit(results)
            prompt,shown=analytic.verifier_prompt(run.report.report_id,doc.source,manifest,plan,
                verify_unit,results,claims,doc.lines)
            prompt+=chunk_module.note(chunk,len(unit.chunks))
            row['verification']='running'
            self._save_chunk_facts(item,run,transition_id,facts)
            verified,checked=self._chunk_attempts(item,run,transition_id,facts,chunk,'verifier',prompt,
                analytic.VERIFIER_SCHEMA,
                lambda value:chunk_module.check_verifier(value,run.report.report_id,verify_unit,claims,shown))
            cleaned=analytic.clean_verifier(verified,claims,shown)
            row.update(verification='done',verification_result={'unit_id':verify_unit['unit_id'],
                'result':cleaned,'soft':checked['soft']})
            row.pop('error',None)
            verdicts=[claim['verdict'] for record in facts['chunks'] for claim in
                record.get('verification_result',{}).get('result',{}).get('claims',[])]
            facts.update(found=len(verdicts),confirmed=sum(v in ('supported','qualified') for v in verdicts),
                contradicted=sum(v=='contradictory' for v in verdicts),
                unconfirmed=sum(v in ('insufficient','rejected') for v in verdicts))
            self._save_chunk_facts(item,run,transition_id,facts)
        return Completed()

    def _analytic_unit(self, item: WorkItem, run: _Run, doc: SourceDoc, unit: Unit, part: PartRow, transition_id: str) -> Outcome:
        """The analyst, then the verifier (md_report/runner.py ``_analyse_and_verify``); each answer is checked, each stage stored when done."""
        manifest, report_id = doc.manifest, run.report.report_id
        plan = analytic.make_plan(manifest)
        index = next(i for i, t in enumerate(manifest["transitions"]) if t["transition_id"] == unit.transition_id)
        group, plan_unit = plan["groups"][index], plan["units"][index]
        facts = dict(part.facts or {"content_key": unit.key})
        facts["content_key"] = unit.key
        stored_analysis = facts.get("analysis")
        if part.analysis != "done" or not stored_analysis:
            prompt = analytic.analyst_prompt(report_id, doc.source, manifest, plan, group, doc.lines)
            answer, check, result, reason = self._attempts(
                item, run, prompt, analytic.ANALYST_SCHEMA, MAX_TOKENS["analyst"],
                lambda a: analytic.check_analyst(a, report_id, group, plan, manifest),
            )
            if answer is None:
                self._store(
                    item, run, transition_id, result=None, analysis="failed", verification="pending", selection=None,
                    facts={**facts, "error": reason}, warnings=None,
                )
                raise _Ended(Failed(reason))
            facts["analysis"] = stored_analysis = {"answer": answer, "soft": check["soft"]}
            facts.pop("error", None)
            self._store(
                item, run, transition_id, result=result, analysis="done", verification="running", selection=None, facts=facts,
                stage=STAGE_VERIFICATION,
            )
        answer = stored_analysis["answer"]
        results = {group["group_id"]: answer}
        claims = analytic.claims_for_unit(results)
        prompt, shown = analytic.verifier_prompt(report_id, doc.source, manifest, plan, plan_unit, results, claims, doc.lines)
        verified, check, result, reason = self._attempts(
            item, run, prompt, analytic.VERIFIER_SCHEMA, MAX_TOKENS["verifier"],
            lambda a: analytic.check_verifier(a, report_id, plan_unit, claims, shown),
        )
        if verified is None:
            self._store(
                item, run, transition_id, result=None, analysis="done", verification="failed", selection=None,
                facts={**facts, "error": reason},
            )
            raise _Ended(Failed(reason))
        cleaned = analytic.clean_verifier(verified, claims, shown)
        verdicts = [c["verdict"] for c in cleaned["claims"]]
        counts = {
            "found": len(verdicts), "confirmed": sum(v in ("supported", "qualified") for v in verdicts),
            "contradicted": sum(v == "contradictory" for v in verdicts), "unconfirmed": sum(v in ("insufficient", "rejected") for v in verdicts),
        }
        facts.update(counts)
        facts["verification"] = {"unit_id": plan_unit["unit_id"], "result": cleaned, "soft": check["soft"]}
        facts.pop("error", None)
        warnings = len(check["soft"]) + len(stored_analysis.get("soft") or [])
        self._store(
            item, run, transition_id, result=result, analysis="done", verification="done", selection=None, facts=facts, warnings=warnings,
        )
        return Completed()

    def _attempts(
        self, item: WorkItem, run: _Run, prompt: str, schema: Mapping[str, Any], max_tokens: int, check: Any,
    ) -> tuple[dict[str, Any] | None, dict[str, Any], CallResult | None, str]:
        """Ask until an answer passes the program's check (a retry carries the program's remarks), up to the original's retry limit."""
        feedback, reason, last = "", REASON_ANSWER_UNFIT, None
        for _ in range(ANALYTIC_RETRIES + 1):
            self._guard(item, run)
            result = self._ask(item, run, prompt + feedback, schema, max_tokens)
            last = result
            answer = _json(result.response.output_text)
            if answer is None:
                reason, feedback = REASON_ANSWER_INVALID, _FEEDBACK.format(problems="the answer is not a JSON object")
                continue
            checked = check(answer)
            if not checked["hard"]:
                return answer, checked, result, reason
            reason, feedback = REASON_ANSWER_UNFIT, _FEEDBACK.format(problems="\n- ".join(checked["hard"]))
        return None, {}, last, reason

    def _mark_failed_part(self, item: WorkItem, payload: Mapping[str, Any], outcome: Outcome) -> None:
        """A unit that ends for good (a failure with no retry) is a failed part; one that waits or retries is left as it was."""
        if payload.get("unit") != "transition" or not isinstance(outcome, Failed) or outcome.retry:
            return
        try:
            with self._sessions() as session:
                item.require_current(session)
                row = self._repo.get(session, payload["report_id"])
                part = self._repo.part(session, payload["report_id"], payload["transition_id"])
                if row is None or part is None or part_done(part, row.kind):
                    return
                facts = dict(part.facts or {})
                facts.setdefault("error", outcome.reason)
                if facts.get("planning_revision")==chunk_module.REVISION:
                    for chunk in facts.get("chunks",[]):
                        for stage in ("analysis","verification"):
                            if chunk.get(stage)=="running":
                                chunk[stage]="failed"
                                chunk["error"]=outcome.reason
                    facts["chunk_coverage"]=chunk_module.coverage(facts)
                client_kind = row.kind == KIND_CLIENT
                self._repo.set_part(
                    session, row.report_id, part.transition_id,
                    analysis=None if client_kind else ("failed" if part.analysis != "done" else "done"),
                    verification=None if client_kind else ("failed" if part.analysis == "done" else "pending"),
                    selection="failed" if client_kind else None, facts=facts, warnings=part.warnings, points=part.points,
                    questions=part.questions,
                )
                session.commit()
        except DomainError:
            return

    # -- the final item --------------------------------------------------------------------------------
    def _final(self, item: WorkItem, payload: Mapping[str, Any]) -> Outcome:
        run = self._begin(item, payload)
        try:
            return self._final_stage(item, run)
        except _Ended as ended:
            # The last item of a job has no other item to make the job's end: a failure that ends it for good (no retry) fails the report's job, so
            # the report reads ``failed`` and «Продолжить» can finish it, never a job that stays ``running`` with nothing left to run.
            if isinstance(ended.outcome, Failed) and not ended.outcome.retry:
                return self._fail(item, run, ended.outcome.reason)
            raise

    def _final_stage(self, item: WorkItem, run: _Run) -> Outcome:
        report, job = run.report, run.job
        with self._sessions() as session:
            if self._repo.other_live_items(session, job.job_id, item.work_id):
                return Yielded(FINAL_POLL_SECONDS)  # every other item of the job has to end first
            try:
                doc = self._reports.source_doc(session, report)
            except DomainError:
                return self._fail(item, run, FAIL_SOURCE)
            parts = {p.transition_id: p for p in self._repo.parts(session, report.report_id)}
            transitions = self._reports.repository.transition_numbers(session, report.series_id)
            unchanged = self._reports.unchanged_from(session, report)
            profile = disciplines.resolve(doc.manifest.get("project_code"))
            units = plan_module.build_units(
                report.kind, doc, profile, project_uid=report.project_uid, model=job.pinned_model, unchanged=unchanged,
            )
            object_name = self._repo.project_name(session, report.project_uid)
        by_unit = {u.transition_id: parts.get(transitions.get(u.number, "")) for u in units}
        if report.kind!=KIND_CLIENT and any(part is not None and (part.facts or {}).get("content_key")!=unit.key
                for unit in units for part in [by_unit[unit.transition_id]]):
            return self._fail(item,run,FAIL_SOURCE)
        unfinished = [u for u in units if u.editable and not part_done(by_unit[u.transition_id], report.kind)]
        if unfinished:
            return self._finish_partial(item, run)  # the original's «неполный результат»: no PDF is written
        recorded = job.provider_mode == "recorded"
        code = str(doc.manifest.get("project_code") or report.source_name or "серия")
        analysed_at = job.consented_at.strftime("%d.%m.%Y %H:%M")
        if report.kind == KIND_CLIENT:
            stored = {u.transition_id: self._stored_result(u, by_unit[u.transition_id]) for u in units}
            dropped = sum(len((r or {}).get("dropped") or []) for r in stored.values())
            document = document_module.client_document(
                manifest=doc.manifest, registry=doc.registry, stored=stored, code=code, object_name=object_name, dropped=dropped,
                recorded=recorded,
            )
        else:
            composed = self._compose(item, run, doc, units, by_unit)
            report_v2, dropped = composed
            document = document_module.analytic_document(
                manifest=doc.manifest, registry=doc.registry, report=report_v2, code=code, dropped=dropped, recorded=recorded,
                analysed_at=analysed_at, sha256=doc.sha256,
            )
        with self._sessions() as session:
            item.require_current(session)
            self._repo.set_stage(session, report.report_id, STAGE_PDF_WRITING)
            session.commit()
        try:
            written = write_pdf(document, runner=self._runner)
        except (PdfFailed, ChildStartError) as failure:
            _LOG.warning("comparison work %s: the PDF child ended without a result: %s", item.work_id, getattr(failure, "end", "no start"))
            return self._fail(item, run, FAIL_PDF)
        if written.problems:
            _LOG.warning("comparison work %s: the PDF did not pass its check: %s", item.work_id, "; ".join(written.problems[:5]))
            return self._fail(item, run, FAIL_PDF_CHECK)
        text = json.dumps(document, ensure_ascii=False, sort_keys=True).encode("utf-8")
        text_blob = self._reports.publish(text, ROLE_TEXT, "application/json")
        pdf_blob = self._reports.publish(written.content, ROLE_PDF, "application/pdf")
        with self._sessions() as session:
            item.require_current(session)
            if AiJobRepository().get(session, job.job_id, lock=True) is None or self._jobs.state_of(session, job.job_id) != "running":
                return Yielded(PAUSED_POLL_SECONDS)  # paused or cancelled while the PDF was written: nothing is recorded, the item waits
            self._repo.add_artifact(
                session, report.report_id, kind=ARTIFACT_TEXT, blob_id=text_blob, sha256=hashlib.sha256(text).hexdigest(), size_bytes=len(text),
            )
            self._repo.add_artifact(
                session, report.report_id, kind=ARTIFACT_PDF, blob_id=pdf_blob, sha256=hashlib.sha256(written.content).hexdigest(),
                size_bytes=len(written.content),
            )
            self._complete_job(session, run)
            session.commit()
        return Completed()

    @staticmethod
    def _stored_result(unit: Unit, part: PartRow | None) -> dict[str, Any] | None:
        """The stored result of a transition for the customer's table: the model's checked result, a mark for a transition the summary does not
        describe, or nothing for the confirmed absence of changes."""
        if unit.editable:
            return (part.facts or {}).get("result") if part is not None else None
        return {"undescribed": True} if unit.reason == "undescribed" else None

    def _complete_job(self, session: Session, run: _Run) -> None:
        """``running -> completed``. The core's ``complete_if_drained`` counts the item that is asking as live, so the last item of a job can
        never complete it from inside its handler (FIX item 1 of the report); this item is the only one left by construction (it waited), and
        the statement is the core's repository's own."""
        AiJobRepository().move(session, run.job.job_id, from_states=("running",), to_state="completed")
        sync_report(session, self._repo, run.report.report_id, self._jobs.job(session, run.job.job_id))

    def _finish_partial(self, item: WorkItem, run: _Run) -> Outcome:
        with self._sessions() as session:
            item.require_current(session)
            self._complete_job(session, run)
            session.commit()
        return Completed()

    def _fail(self, item: WorkItem, run: _Run, reason: str) -> Outcome:
        """The report cannot be finished: its job fails with ``reason`` (its live items, this one included, are cancelled)."""
        with self._sessions() as session:
            item.require_current(session)
            self._jobs.fail(session, run.job.job_id, reason)
            sync_report(session, self._repo, run.report.report_id, self._jobs.job(session, run.job.job_id))
            session.commit()
        return Failed(reason)

    # -- the composer (the analytic kind's last call) -----------------------------------------------------
    def _compose(
        self, item: WorkItem, run: _Run, doc: SourceDoc, units: list[Unit], by_unit: Mapping[str, PartRow | None],
    ) -> tuple[dict[str, Any], int]:
        """The composer's checked answer assembled into ``report_v2``; a report that does not pass its checks fails (md_report/runner.py:1147-1188)."""
        manifest, report_id = doc.manifest, run.report.report_id
        with self._sessions() as session:
            item.require_current(session)
            self._repo.set_stage(session, report_id, STAGE_COMPOSITION)
            session.commit()
        verified: dict[str, dict[str, Any]] = {}
        transitions = {t["transition_id"]: t for t in manifest["transitions"]}
        plan = analytic.make_plan(manifest)
        for index, unit in enumerate(units):
            part = by_unit[unit.transition_id]
            chunk_rows=(part.facts or {}).get("chunks",[]) if part is not None else []
            if unit.chunks and chunk_rows:
                for chunk in chunk_rows:
                    record=chunk.get("verification_result",{})
                    if chunk.get("verification")!="done" or not record.get("result"):
                        raise _Ended(self._fail(item,run,FAIL_CHECK))
                    verified[record["unit_id"]]=record["result"]
                continue
            result = ((part.facts or {}).get("verification") or {}).get("result") if unit.editable and part is not None else None
            verified[plan["units"][index]["unit_id"]] = result or program_unit_result(transitions[unit.transition_id])
        mode=plan_module.composition_mode(units)
        if mode=="deterministic_chunk_sections":
            report=chunk_module.assemble_sections(run_id=report_id,doc=doc,units=units,by_unit=by_unit,verified=verified)
            if analytic.validate_report(report,manifest["lines_total"])+analytic.consistency(report,manifest):
                raise _Ended(self._fail(item,run,FAIL_CHECK))
            return report,0
        host=next((part for part in by_unit.values() if part is not None),None)
        host_facts={} if host is None else dict(host.facts or {})
        feedback, reason, accepted, last = "", FAIL_CHECK, None, None
        for attempt in range(ANALYTIC_RETRIES + 1):
            self._guard(item, run)
            prompt = analytic.composer_prompt(report_id, doc.source, manifest, verified, retry_note=feedback, registry=doc.registry)
            if host is None:
                raise _Ended(self._fail(item,run,FAIL_CHECK))
            response=self._durable_ask(item,run,host.transition_id,host_facts,
                f'composer:{report_id}:{attempt}',prompt,analytic.COMPOSER_SCHEMA,MAX_TOKENS["composer"])
            answer = None if response.truncated else chunk_module.parse_reply(response.output_text)
            if answer is None:
                feedback = _FEEDBACK.format(problems="the answer is not a JSON object")
                continue
            try:
                chunk_module.validate_shape(answer,analytic.COMPOSER_SCHEMA)
                checked = analytic.check_composer(answer, report_id, manifest, verified, doc.lines, doc.registry)
            except (ValueError,KeyError,TypeError):
                feedback=_FEEDBACK.format(problems="the answer failed its exact schema/source partition")
                continue
            last = (answer, checked)
            if checked["ok"]:
                accepted = last
                break
            if checked["hard"]:
                last = None
            feedback = _FEEDBACK.format(problems="\n- ".join(checked["hard"] + checked["fixable"]))
        if accepted is None and last is not None and not last[1]["hard"]:
            accepted = last  # only fixable remarks remain after the last attempt: accepted with warnings (runner.py:791-793)
        if accepted is None:
            raise _Ended(self._fail(item, run, reason))
        answer, checked = accepted
        report = analytic.assemble(answer, manifest, verified, doc.source, doc.lines, doc.registry)
        report=chunk_module.decorate(report,doc=doc,units=units,by_unit=by_unit,verified=verified,mode=mode)
        problems = analytic.validate_report(report, manifest["lines_total"]) + analytic.consistency(report, manifest)
        if problems:
            _LOG.warning("comparison work %s: the report did not pass its checks: %s", item.work_id, "; ".join(problems[:5]))
            raise _Ended(self._fail(item, run, FAIL_CHECK))
        if checked["fixable"]:  # accepted after the last attempt with only fixable remarks (runner.py:791-793): the report says so
            report["check_warnings"] = list(checked["fixable"])
        rejected = sum(c["verdict"] == "rejected" for v in verified.values() for c in v["claims"])
        return report, rejected + len(report.get("reference_warnings") or [])


def report_handler(dependencies: WorkDependencies) -> ReportHandler:
    """The factory ``comparison.public.HANDLER_FACTORIES`` holds (a ``HandlerFactory``)."""
    return ReportHandler(dependencies, model_source=getattr(dependencies, "routes", None))
