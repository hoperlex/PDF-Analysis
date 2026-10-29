"""The handler of the ``comparison_pair_check`` work kind (`CMP-VC-AIPAIR-01`, ADR-0025 decisions 4, 5, 10, 11, 18, 19, 20).

Two kinds of item share the kind (the payload's ``step``):

``ask`` -- one doubtful cell of a job. It asks the **forward** question and, when the answer can be accepted, the **reverse** one,
and stores both answers; it decides nothing. Each call goes through the one door to a model, the spend wrapper
(:class:`~auditmanager.comparison.spend.caller.ComparisonModelCaller`): the journal row is written ``prepared`` before the
request, the ceilings and the consent are checked before it, an unknown outcome is never retried. A **stored answer is never asked
again**: the content key is looked up first and a hit costs nothing. The pictures are the stored page previews, at most eight in a
request (the C0 image channel), each a blob the page profile already owns.

``close`` -- one per job, not linked to the job. It waits while the job is not running or any question item is live, then, in
one transaction, decides every question (:mod:`.decide`), writes the accepted links, ends the questions and completes the job.
See :mod:`.method` for why it is a separate item.

Nothing here makes a model call by itself: the route that serves a call is handed in by a :class:`ModelBinder` (a live
connection's adapter, or the recorded one in a test). Without one, an item fails loudly (``model_binder_missing``) -- there is no
fall back to anything else.
"""

from __future__ import annotations

import hashlib
import logging
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any, Final

from sqlalchemy.orm import Session

from auditmanager.analysis.public import ModelRequest, ProxyDispatchError
from auditmanager.comparison.ai_jobs.model import JOB_TERMINAL_STATES, AiCallGroup, AiJobRecord
from auditmanager.comparison.ai_jobs.service import ComparisonAiJobService
from auditmanager.comparison.ai_pairs.decide import decide, mark_shared, needs_reverse, pick_of
from auditmanager.comparison.ai_pairs.method import (
    ASK_STEP,
    CLOSE_STEP,
    PairCheckMethod,
    answer_from_row,
    load_snapshot,
    question_unit_key,
)
from auditmanager.comparison.ai_pairs.model import (
    DECISION_FAILED,
    DECISION_LINK_ACCEPTED,
    MAX_OUTPUT_TOKENS,
    PAIR_CHECK_KIND,
    PROMPT_VERSION,
    Answer,
    Question,
    QuestionPage,
)
from auditmanager.comparison.ai_pairs.plans import CallPlan, PlanContext, forward_plan, reverse_plan
from auditmanager.comparison.ai_pairs.prompt import build_request, crop_ids, validate_answer
from auditmanager.comparison.ai_pairs.questions import paired_pages
from auditmanager.comparison.ai_pairs.repository import AiPairRepository, QuestionRow, StoredAnswer
from auditmanager.comparison.matrix.repository import MatrixRepository
from auditmanager.comparison.profile.limits import ALGO_VERSION as PAGE_PROFILE_ALGO_VERSION
from auditmanager.comparison.profile.reader import PageProfileReader
from auditmanager.comparison.spend.caller import ComparisonModelCaller
from auditmanager.comparison.spend.errors import CallRefused, SpendError
from auditmanager.comparison.spend.model import CallEstimate, CallRoute
from auditmanager.comparison.work.model import (
    Completed,
    Failed,
    Outcome,
    WorkDependencies,
    WorkItem,
    Yielded,
)
from auditmanager.executors.public import CropImage, attach_images
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ComparisonAiJobId, ComparisonAiPairQuestionId, IdentityError

__all__ = [
    "ModelBinder",
    "NOT_RUNNING_WAIT_SECONDS",
    "PairCheckHandler",
    "REASON_ANSWER_INVALID",
    "REASON_BINDER_MISSING",
    "REASON_PAYLOAD_INVALID",
    "pair_check_handler",
]

_LOG = logging.getLogger(__name__)

#: ``(session, job) -> CallRoute``: the adapter that serves the job's calls and what the spend wrapper holds the reply to (the
#: pinned model, the connection revision, the rates). A live deployment binds the routed connection's revision; a test hands a
#: recorded one. The composition root provides it; this module builds none.
ModelBinder = Callable[[Session, AiJobRecord], CallRoute]

REASON_PAYLOAD_INVALID: Final[str] = "pair_check_payload_invalid"
REASON_BINDER_MISSING: Final[str] = "model_binder_missing"
REASON_ANSWER_INVALID: Final[str] = "pair_answer_invalid"
REASON_PREVIEW_MISSING: Final[str] = "pair_preview_missing"
REASON_PREVIEW_CHANGED: Final[str] = "pair_preview_changed"
REASON_IMAGES_INVALID: Final[str] = "pair_images_invalid"
REASON_PAGE_PROFILE_MISSING: Final[str] = "pair_page_profile_missing"
REASON_ASK_FAILED: Final[str] = "pair_question_not_asked"
#: How long an item waits when its job is not running (paused, over) before it looks again; a yield spends no attempt.
NOT_RUNNING_WAIT_SECONDS: Final[float] = 60.0
CLOSE_WAIT_RUNNING_SECONDS: Final[float] = 10.0
_LEASE_GONE: Final[frozenset[ErrorCode]] = frozenset({ErrorCode.STALE_ATTEMPT, ErrorCode.EXECUTION_TOKEN_INVALID})
_ITEM_ENDED: Final[frozenset[str]] = frozenset({"succeeded", "failed", "cancelled"})
_REASON = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
_RECORDED_IDENTITY: Final[str] = "recorded"


class _Stop(Exception):
    """An item ends here with this outcome (a refusal of the wrapper, a paused job, a lease that is gone)."""

    def __init__(self, outcome: Outcome) -> None:
        super().__init__(type(outcome).__name__)
        self.outcome = outcome


@dataclass(frozen=True, slots=True)
class _Obtained:
    answer: Answer
    stored: StoredAnswer
    #: The call took the job over a ceiling or past 1.2 x its estimate: the job is paused, no further call is made.
    paused: bool = False


def _sanitise(reason: str | None, default: str) -> str:
    return reason if isinstance(reason, str) and _REASON.match(reason) else default


class PairCheckHandler:
    """The one handler of kind ``comparison_pair_check`` (a :class:`~auditmanager.comparison.work.model.WorkHandler`)."""

    kind: str = PAIR_CHECK_KIND

    def __init__(
        self, dependencies: WorkDependencies, *, binder: ModelBinder | None = None, caller: ComparisonModelCaller | None = None,
        jobs: ComparisonAiJobService | None = None, previews: PageProfileReader | None = None,
        pairs: AiPairRepository | None = None, matrices: MatrixRepository | None = None,
    ) -> None:
        #: Read when an item runs, not when the factory is applied: the registry builds a handler to learn its kind, and that
        #: must cost nothing and touch nothing.
        self._deps = dependencies
        self._binder = binder
        self._caller = caller
        self._jobs_service = jobs
        self._previews = previews
        self._pairs = pairs or AiPairRepository()
        self._matrices = matrices or MatrixRepository()

    # -- the collaborators, built on first use ---------------------------------------------------------
    def _jobs(self) -> ComparisonAiJobService:
        if self._jobs_service is None:
            self._jobs_service = ComparisonAiJobService(
                self._deps.session_factory, methods=[PairCheckMethod(provider_mode="live")], work=self._deps.work,
            )
        return self._jobs_service

    def _spend(self) -> ComparisonModelCaller:
        if self._caller is None:
            self._caller = ComparisonModelCaller(self._deps.session_factory)
        return self._caller

    def _reader(self) -> PageProfileReader:
        if self._previews is None:
            self._previews = PageProfileReader(self._deps.session_factory, self._deps.blob_store)
        return self._previews

    # -- the entry -------------------------------------------------------------------------------------
    def run(self, item: WorkItem) -> Outcome:
        payload = item.payload
        step = payload.get("step")
        try:
            if step == ASK_STEP:
                return self._ask(item, payload)
            if step == CLOSE_STEP:
                return self._close(item, payload)
        except _Stop as stop:
            return stop.outcome
        except LookupError:  # a page of the question has no stored profile (a version re-profiled since the question was made)
            _LOG.error("comparison work %s: a page of the pair_check question has no stored profile", item.work_id)
            return Failed(REASON_PAGE_PROFILE_MISSING)
        except DomainError as refusal:
            if refusal.code in _LEASE_GONE:
                item.lease_lost.set()
                return Yielded()
            raise
        _LOG.error("comparison work %s: the pair_check payload has no known step", item.work_id)
        return Failed(REASON_PAYLOAD_INVALID)

    # -- ask ---------------------------------------------------------------------------------------------
    def _ask(self, item: WorkItem, payload: Mapping[str, Any]) -> Outcome:
        try:
            job_id = str(ComparisonAiJobId.parse(str(payload["ai_job_id"])))
            question_id = str(ComparisonAiPairQuestionId.parse(str(payload["question_id"])))
            question = Question.from_payload(payload["question"])
        except (KeyError, TypeError, ValueError, IdentityError):
            _LOG.error("comparison work %s: the pair_check ask payload is not valid", item.work_id)
            return Failed(REASON_PAYLOAD_INVALID)
        sessions = self._deps.session_factory
        jobs = self._jobs()
        self._checkpoint(item)
        with sessions() as session:
            item.check_current(session)
            state = jobs.mark_running(session, job_id)
            session.commit()
        if state != "running":
            return Yielded(NOT_RUNNING_WAIT_SECONDS)  # paused or over while the item waited: it sends nothing
        with sessions() as session:
            job = jobs.job(session, job_id)
            row = self._pairs.question(session, question_id)
            if row is None or row.state != "queued":
                return Completed()  # already ended (a replay of a finished item)
            context = self._context(session, job, question)
        forward = self._obtain(item, job, context, forward_plan(question, context))
        self._remember(item, question_id, answer_id=forward.stored.answer_id)
        pick = needs_reverse(question, forward.answer)
        reverse_plan_ = None if pick is None else reverse_plan(question, pick, context)
        if reverse_plan_ is None:
            return Completed()
        if forward.paused and not self._is_stored(reverse_plan_, job):
            return Yielded(NOT_RUNNING_WAIT_SECONDS)  # the job paused after the forward call: the reverse waits for the resume
        reverse = self._obtain(item, job, context, reverse_plan_)
        self._remember(item, question_id, reverse_answer_id=reverse.stored.answer_id)
        return Completed()  # nothing is left to ask; a job paused by this call waits for its resume at the closing item

    def _is_stored(self, plan: CallPlan, job: AiJobRecord) -> bool:
        with self._deps.session_factory() as session:
            return plan.key in self._pairs.stored_answers(session, job.project_uid, [plan.key])

    def _context(self, session: Session, job: AiJobRecord, question: Question) -> PlanContext:
        """The pages the question and its reverse can show, read from the stored profiles of the build it was asked of."""
        build = self._matrices.build_by_id(session, job.matrix_id or "")
        if build is None:
            raise _Stop(Failed(REASON_PAYLOAD_INVALID))
        order = tuple(build.order)
        counts = {str(k): int(v) for k, v in (build.summary.get("page_counts") or {}).items()}
        a = question.a
        wanted = {(a.version_uid, a.page_number)}
        wanted |= {(a.version_uid, n) for n in (a.page_number - 1, a.page_number + 1) if n >= 1}
        for page in question.candidates:
            wanted.add((question.b_version_uid, page.page_number))
            wanted |= {(a.version_uid, n) for n in question.back.get(page.page_number, ())}
        facts = self._pairs.page_facts_of(session, sorted(wanted), PAGE_PROFILE_ALGO_VERSION)
        title = self._pairs.require_document(session, job.project_uid, job.document_uid)
        return PlanContext(
            project_uid=job.project_uid, model_identity=job.pinned_model, provider_mode=job.provider_mode, order=order,
            page_counts=counts, facts=facts, document_title=title,
        )

    def _obtain(self, item: WorkItem, job: AiJobRecord, context: PlanContext, plan: CallPlan) -> _Obtained:
        """The answer to a plan: the stored one when its key is stored (no call, nothing spent), otherwise one call through the
        spend wrapper, validated and stored. A refusal, a failed call or a reply that is not the schema ends the item."""
        sessions = self._deps.session_factory
        with sessions() as session:
            stored = self._pairs.stored_answers(session, job.project_uid, [plan.key]).get(plan.key)
        if stored is not None:
            return _Obtained(answer_from_row(stored), stored)
        self._checkpoint(item)
        jobs = self._jobs()
        with sessions() as session:
            if jobs.state_of(session, job.job_id) != "running":
                raise _Stop(Yielded(NOT_RUNNING_WAIT_SECONDS))
            if self._binder is None:
                raise _Stop(Failed(REASON_BINDER_MISSING))
            route = self._binder(session, job)
            consent = jobs.consent_for_calls(session, job.job_id)
        request = self._request(job, plan)
        input_tokens = AiCallGroup(
            calls=1, prompt_chars=len(plan.prompt), output_tokens=MAX_OUTPUT_TOKENS, images=plan.images,
            image_bytes=plan.image_bytes,
        ).input_tokens_per_call
        try:
            result = self._spend().call(
                item, route, request, estimate=CallEstimate(input_tokens=input_tokens, output_tokens=MAX_OUTPUT_TOKENS),
                consent=consent,
            )
        except CallRefused as refused:
            if refused.pauses_job:
                with sessions() as session:
                    jobs.pause_for_spend(session, job.job_id, refused.reason)
                    session.commit()
            raise _Stop(refused.as_outcome()) from None
        except SpendError as error:
            raise _Stop(error.as_outcome()) from None
        answer = validate_answer(result.response.output_text, plan.cands)
        paused = False
        if result.pause is not None:
            with sessions() as session:
                paused = jobs.pause_for_spend(session, job.job_id, result.pause.reason)
                session.commit()
        if not answer.ok:
            # The reply was paid for and is not an answer: it is not stored (an unusable reply must not stop a retry from asking),
            # and the item retries within its budget.
            raise _Stop(Failed(REASON_ANSWER_INVALID, retry=True))
        with sessions() as session:
            item.require_current(session)
            stored = self._pairs.store_answer(
                session, project_uid=job.project_uid, content_key=plan.key, kind=plan.kind, prompt_version=PROMPT_VERSION,
                model_identity=_RECORDED_IDENTITY if job.provider_mode == "recorded" else job.pinned_model,
                confidence=answer.confidence, call_id=result.call_id,
                answer={
                    "choice": answer.choice, "page": answer.page, "confidence": answer.confidence, "reason": answer.reason,
                    "cands": list(answer.cands),
                },
            )
            session.commit()
        return _Obtained(answer_from_row(stored), stored, paused=bool(paused))

    def _request(self, job: AiJobRecord, plan: CallPlan) -> ModelRequest:
        """The request with its pictures: the stored previews of the plan's pages, in order, at most eight (the C0 channel
        checks it again). A preview that is not the one the key was made of is a typed failure, never a silent re-read."""
        reader = self._reader()
        crops: list[CropImage] = []
        for crop_id, page in zip(crop_ids(len(plan.pages) - 1), plan.pages, strict=True):
            try:
                data = reader.read_preview(page.page_profile_id)
            except DomainError as refusal:
                if refusal.code is ErrorCode.NOT_FOUND:
                    raise _Stop(Failed(REASON_PREVIEW_MISSING)) from None
                raise
            if hashlib.sha256(data).hexdigest() != page.preview_sha256:
                raise _Stop(Failed(REASON_PREVIEW_CHANGED))
            crops.append(CropImage(crop_id=crop_id, data=data))
        try:
            return attach_images(build_request(model_id=job.pinned_model, prompt=plan.prompt), crops)
        except ProxyDispatchError:
            raise _Stop(Failed(REASON_IMAGES_INVALID)) from None

    def _remember(self, item: WorkItem, question_id: str, *, answer_id: str | None = None, reverse_answer_id: str | None = None) -> None:
        with self._deps.session_factory() as session:
            item.require_current(session)
            self._pairs.set_answers(session, question_id, answer_id=answer_id, reverse_answer_id=reverse_answer_id)
            session.commit()

    # -- close -------------------------------------------------------------------------------------------
    def _close(self, item: WorkItem, payload: Mapping[str, Any]) -> Outcome:
        try:
            job_id = str(ComparisonAiJobId.parse(str(payload["job_id"])))
        except (KeyError, TypeError, ValueError, IdentityError):
            return Failed(REASON_PAYLOAD_INVALID)
        jobs = self._jobs()
        self._checkpoint(item)
        with self._deps.session_factory() as session:
            item.require_current(session)
            state = jobs.state_of(session, job_id)
            if state in JOB_TERMINAL_STATES:
                if state != "completed":  # cancelled or failed: nothing is decided, and what was not asked is not pending any more
                    for row in self._pairs.questions_of_job(session, job_id):
                        if row.state == "queued":
                            self._pairs.settle(session, row.question_id, state="cancelled", decision=None)
                session.commit()
                return Completed()
            if state != "running":
                return Yielded(NOT_RUNNING_WAIT_SECONDS)
            progress = jobs.view_in(session, job_id).progress
            if any(name not in _ITEM_ENDED for name in progress.by_state):
                return Yielded(CLOSE_WAIT_RUNNING_SECONDS)
            self.decide_job(session, jobs.job(session, job_id))
            jobs.complete_if_drained(session, job_id)
            session.commit()
        return Completed()

    def decide_job(self, session: Session, job: AiJobRecord) -> None:
        """Decide every question of the job that is still ``queued`` and end it; write the accepted links. In the caller's
        transaction (the closing item's), never committing. The decision reads the effective matrix of the build the
        questions were asked of **as it is now**: a B an expert linked meanwhile is ``hint_taken``, and an answer of a cell
        that has since been settled by anyone else is never turned into a link."""
        pairs = self._pairs
        rows = [row for row in pairs.questions_of_job(session, job.job_id) if row.state == "queued"]
        if not rows or job.matrix_id is None:
            return
        items = pairs.item_states(session, job.job_id)
        snapshot = load_snapshot(
            session, self._matrices, pairs, project_uid=job.project_uid, document_uid=job.document_uid,
            matrix_id=job.matrix_id, latest_only=False,
        )
        fresh = {question.key: question for question in snapshot.questions()}
        decided: list[tuple[QuestionRow, Question, str, int | None, StoredAnswer | None, StoredAnswer | None]] = []
        for row in rows:
            item_state, item_reason = items.get(f"{job.job_id}:{question_unit_key(row.question_id)}", (None, None))
            if item_state == "cancelled":
                pairs.settle(session, row.question_id, state="cancelled", decision=None)
                continue
            if item_state != "succeeded" or row.answer_id is None:
                reason = _sanitise(item_reason, REASON_ASK_FAILED) if item_state == "failed" else REASON_ASK_FAILED
                pairs.settle(session, row.question_id, state="failed", decision=DECISION_FAILED, failure_reason=reason)
                continue
            forward = pairs.answer(session, row.answer_id)
            reverse = None if row.reverse_answer_id is None else pairs.answer(session, row.reverse_answer_id)
            question = self._question_now(row, fresh, snapshot.rows)
            choice = decide(
                question, None if forward is None else answer_from_row(forward), None if reverse is None else answer_from_row(reverse),
            )
            pick, _confidence = pick_of(None if forward is None else answer_from_row(forward))
            decided.append((row, question, choice, pick, forward, reverse))
        final = mark_shared([(question, choice, pick) for _row, question, choice, pick, _f, _r in decided])
        for (row, question, _choice, pick, forward, reverse), decision in zip(decided, final, strict=True):
            if decision == DECISION_FAILED:
                pairs.settle(session, row.question_id, state="failed", decision=DECISION_FAILED, failure_reason="pair_answer_missing")
                continue
            link_id = None
            if decision == DECISION_LINK_ACCEPTED:
                if pick is None or pick <= 0 or forward is None:  # the rule cannot accept without a page; it is not a link
                    pairs.settle(session, row.question_id, state="failed", decision=DECISION_FAILED, failure_reason="pair_answer_missing")
                    continue
                link_id = pairs.insert_link(
                    session, document_uid=job.document_uid, matrix_id=job.matrix_id, page_version_uid=question.a.version_uid,
                    page_number=question.a.page_number, other_version_uid=question.b_version_uid, other_page_number=pick,
                    answered_state="unmatched", call_id=forward.call_id,
                    details={
                        "question_id": row.question_id, "answer_id": forward.answer_id,
                        "reverse_answer_id": None if reverse is None else reverse.answer_id, "prompt_version": PROMPT_VERSION,
                        "job_id": job.job_id,
                    },
                )
            hint = (question.b_version_uid, pick) if pick is not None and pick > 0 else None
            pairs.settle(session, row.question_id, state="answered", decision=decision, hint=hint, link_id=link_id)

    @staticmethod
    def _question_now(row: QuestionRow, fresh: Mapping[tuple[str, int, str], Question], rows: Sequence[Mapping[str, Any]]) -> Question:
        """The question as the matrix poses it now. ``multi`` is read again, and ``taken_b`` is every page of B that stands in a
        row with a sheet of A **now** -- not only the candidates the cell still offers: a page an expert paired meanwhile is gone
        from the candidates and is still taken. A cell the matrix no longer asks about -- settled meanwhile by an expert or by an
        earlier check -- is a question whose every candidate is taken: any page the model named can only be a hint."""
        key = (row.page_version_uid, row.page_number, row.version_uid)
        found = fresh.get(key)
        paired = paired_pages(rows, row.page_version_uid, row.version_uid)
        if found is not None and found.kind == row.kind:
            return replace(found, taken_b=found.taken_b | paired)
        candidates = tuple(
            QuestionPage(row.version_uid, int(c["page_number"]), str(c["page_profile_id"])) for c in row.candidates
        )
        algo = next((int(c["page_number"]) for c in row.candidates if c.get("algo")), None)
        return Question(
            kind=row.kind, a=QuestionPage(row.page_version_uid, row.page_number, ""), b_version_uid=row.version_uid,
            candidates=candidates, algo_b=algo, multi=False, taken_b=frozenset(p.page_number for p in candidates) | paired,
        )

    # -- the lease ---------------------------------------------------------------------------------------
    def _checkpoint(self, item: WorkItem) -> None:
        """Stop on a lease that is gone or a cancel that was requested (the queue ends a requested cancel ``cancelled``)."""
        if item.lease_lost.is_set():
            raise _Stop(Yielded())
        if item.cancelled.is_set():
            raise _Stop(Yielded())


def pair_check_handler(dependencies: WorkDependencies) -> PairCheckHandler:
    """The factory ``comparison.public.HANDLER_FACTORIES`` holds (a ``HandlerFactory``). The binder of a live route is the
    composition root's; until it hands one in, a live item fails with ``model_binder_missing``."""
    return PairCheckHandler(dependencies)
