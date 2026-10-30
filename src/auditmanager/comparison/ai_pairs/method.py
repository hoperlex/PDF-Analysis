"""The ``pair_check`` method of the shared AI-job core (`CMP-VC-AIPAIR-01`, `CMP-AI-JOBS-01` section 2).

:class:`PairCheckMethod` supplies the two things the core asks of a method: the **counts** of what a check would send (for the
estimate: the calls still to make, their images and prompt size, how many questions already have a stored answer), and the
**work items** of a job (one per question, plus the closing step). It writes no job row and no money figure; the core does.

* **A question is a unit.** ``work_items`` writes the question rows (``comparison_ai_pair_question``, ``queued``) of the cells the
  effective matrix calls doubtful and answers one ``ask`` item for each. An item makes up to two calls -- the forward question and,
  when the answer can be accepted, the reverse one -- and stores both answers; it decides nothing, because one decision depends on
  the others (two sheets that chose the same B).
* **One closing item decides.** ``work_items`` also enqueues one ``close`` item. It is **not** linked to the job (so the job's
  progress counts questions only, and the core's ``complete_if_drained`` can complete the job from inside it: an item cannot see
  the job drained while it is itself one of the job's live items). It yields while any question item is live or the job is
  paused, and when every question has ended it makes all the decisions in one transaction, writes the accepted links and
  completes the job.
* **A stored answer costs nothing.** An answer is stored under its content key; a question whose every call is stored is
  ``reused`` in the estimate, is never in a call group, and its item makes no call.

The estimate is an upper bound: a forward call that is not stored is counted with one reverse call (the heaviest the question
could need), because whether a reverse question is asked depends on the answer.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

from sqlalchemy.orm import Session

from auditmanager.comparison.ai_jobs.estimate import read_route
from auditmanager.comparison.ai_jobs.model import (
    AiCallGroup,
    AiCounts,
    AiEstimateRequest,
    AiJobRecord,
    AiMode,
    AiRoute,
    AiWorkItemSpec,
)
from auditmanager.comparison.ai_pairs.decide import needs_reverse
from auditmanager.comparison.ai_pairs.model import (
    CONFLICT_MATRIX_STALE,
    KIND_NO_PAIR,
    MAX_OUTPUT_TOKENS,
    PAIR_CHECK_KIND,
    PROMPT_VERSION,
    Answer,
    Question,
)
from auditmanager.comparison.ai_pairs.plans import CallPlan, PlanContext, forward_plan, reverse_plan
from auditmanager.comparison.ai_pairs.questions import derive_questions
from auditmanager.comparison.ai_pairs.repository import AiPairRepository, StoredAnswer
from auditmanager.comparison.matrix.effective import effective_matrix
from auditmanager.comparison.matrix.model import BuildRecord
from auditmanager.comparison.matrix.repository import MatrixRepository
from auditmanager.comparison.profile.limits import ALGO_VERSION as PAGE_PROFILE_ALGO_VERSION
from auditmanager.comparison.spend.model import JOB_KEY as SPEND_JOB_KEY
from auditmanager.comparison.work.repository import ComparisonWorkRepository
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "ASK_STEP",
    "CLOSE_POLL_SECONDS",
    "CLOSE_STEP",
    "PairCheckMethod",
    "Snapshot",
    "answer_from_row",
    "load_snapshot",
    "question_unit_key",
]

ASK_STEP: Final[str] = "ask"
CLOSE_STEP: Final[str] = "close"
#: How long the closing item waits before it looks at the job again.
CLOSE_POLL_SECONDS: Final[float] = 15.0
_LIVE_ITEM_STATES: Final[tuple[str, ...]] = ("queued", "leased", "running", "retry_wait", "paused")
_FAILED_ITEM_STATES: Final[tuple[str, ...]] = ("failed",)


def question_unit_key(question_id: str) -> str:
    """The unit of a question within its job (the core makes the dedupe key ``<job>:<unit>`` of it)."""
    return f"q:{question_id}"


def stale_matrix() -> DomainError:
    """``409 conflict`` ``comparison_matrix_stale``: the matrix the check was asked of is not the latest build."""
    return DomainError(ErrorCode.CONFLICT, conflict_reason=CONFLICT_MATRIX_STALE)


@dataclass(frozen=True, slots=True)
class Snapshot:
    """The effective matrix of one build and what the stored profiles say of its pages."""

    build: BuildRecord
    order: tuple[str, ...]
    page_counts: Mapping[str, int]
    rows: Sequence[Mapping[str, Any]]
    facts: Mapping[tuple[str, int], Any]
    document_title: str

    def questions(self) -> list[Question]:
        return derive_questions(order=self.order, page_counts=self.page_counts, rows=self.rows, facts=self.facts)


def load_snapshot(
    session: Session, matrices: MatrixRepository, pairs: AiPairRepository, *, project_uid: str, document_uid: str,
    matrix_id: str | None, latest_only: bool,
) -> Snapshot:
    """The effective matrix (the build, the accepted AI links, the manual edits) of ``matrix_id`` -- the latest build when it
    is ``None``. ``latest_only`` makes any other build ``comparison_matrix_stale`` (an estimate and a start are for the latest);
    the closing step reads the build its questions were asked of, whatever has been built since."""
    title = pairs.require_document(session, project_uid, document_uid)
    latest = matrices.latest_build(session, document_uid)
    if latest is None:
        raise stale_matrix()
    build = latest
    if matrix_id is not None and matrix_id != latest.matrix_id:
        if latest_only:
            raise stale_matrix()
        found = matrices.build_by_id(session, matrix_id)
        if found is None:
            raise stale_matrix()
        build = found
    counts = {str(k): int(v) for k, v in (build.summary.get("page_counts") or {}).items()}
    effective = effective_matrix(
        build, matrices.all_edits(session, document_uid), matrices.ai_links(session, document_uid), page_counts=counts,
    )
    order = tuple(build.order)
    return Snapshot(
        build=build, order=order, page_counts=counts, rows=effective.rows,
        facts=pairs.page_facts(session, order, PAGE_PROFILE_ALGO_VERSION), document_title=title,
    )


def answer_from_row(stored: StoredAnswer) -> Answer:
    """A stored answer as the rule reads it."""
    document = stored.answer
    return Answer(
        ok=True, choice=int(document.get("choice", 0)), page=int(document.get("page", 0)),
        confidence=str(document.get("confidence", stored.confidence)), reason=str(document.get("reason", "")),
        cands=tuple(int(n) for n in document.get("cands", ())),
    )


@dataclass(frozen=True, slots=True)
class _Assessment:
    """What one question still needs: the calls not stored (empty: it is reused)."""

    question: Question
    calls: tuple[CallPlan, ...]


class PairCheckMethod:
    """The :class:`~auditmanager.comparison.ai_jobs.model.AiMethod` of the AI pair check."""

    method: str = "pair_check"
    prompt_version: str = PROMPT_VERSION

    def __init__(
        self, *, provider_mode: str, route_reader: Callable[[Session, str, str], AiRoute] = read_route,
        pairs: AiPairRepository | None = None, matrices: MatrixRepository | None = None,
        work: ComparisonWorkRepository | None = None,
    ) -> None:
        if provider_mode not in ("live", "recorded"):
            raise ValueError("the provider mode is live or recorded")
        self._provider_mode = provider_mode
        self._route_reader = route_reader
        self._pairs = pairs or AiPairRepository()
        self._matrices = matrices or MatrixRepository()
        self._work = work or ComparisonWorkRepository()

    # -- the estimate --------------------------------------------------------------------------------
    def counts(self, session: Session, request: AiEstimateRequest) -> AiCounts:
        scope = request.scope
        snapshot = load_snapshot(
            session, self._matrices, self._pairs, project_uid=scope.project_uid, document_uid=scope.document_uid,
            matrix_id=scope.matrix_id, latest_only=True,
        )
        context = self.context(session, snapshot, scope.project_uid, scope.work_kind)
        questions = self._questions_for(session, snapshot, request.mode, scope.document_uid)
        assessed = self._assess(session, questions, context)
        groups: dict[int, list[CallPlan]] = {}
        for item in assessed:
            for call in item.calls:
                groups.setdefault(call.images, []).append(call)
        return AiCounts(
            groups=tuple(
                AiCallGroup(
                    calls=len(plans), prompt_chars=max(len(plan.prompt) for plan in plans), output_tokens=MAX_OUTPUT_TOKENS,
                    images=images, image_bytes=max(plan.image_bytes for plan in plans),
                )
                for images, plans in sorted(groups.items())
            ),
            units=len(assessed), reused=sum(1 for item in assessed if not item.calls), questions=len(assessed),
            pairs=sum(1 for item in assessed if item.question.kind == KIND_NO_PAIR),
        )

    def context(self, session: Session, snapshot: Snapshot, project_uid: str, work_kind: str) -> PlanContext:
        """The plan context of this process: the pinned model of the routed connection answers (``recorded`` in a recorded
        process), the versions are named by their place in the matrix's order."""
        route = self._route_reader(session, work_kind, self._provider_mode)
        return plan_context(snapshot, project_uid=project_uid, model_identity=route.pinned_model, provider_mode=self._provider_mode)

    def _questions_for(self, session: Session, snapshot: Snapshot, mode: AiMode, document_uid: str) -> list[Question]:
        if mode is AiMode.START:
            return snapshot.questions()
        job_id = (
            self._pairs.live_job_of(session, document_uid) if mode is AiMode.LEFT else self._pairs.latest_job_of(session, document_uid)
        )
        if job_id is None:
            return []
        states = _LIVE_ITEM_STATES if mode is AiMode.LEFT else _FAILED_ITEM_STATES
        return [Question.from_payload(payload["question"]) for payload in self._pairs.ask_payloads(session, job_id, states)]

    def _assess(self, session: Session, questions: Sequence[Question], context: PlanContext) -> list[_Assessment]:
        """The calls each question still needs, given the answers already stored."""
        forward = [forward_plan(question, context) for question in questions]
        stored = self._pairs.stored_answers(session, context.project_uid, [plan.key for plan in forward])
        pending: list[tuple[Question, CallPlan, CallPlan | None]] = []
        reverse_keys: list[str] = []
        for question, plan in zip(questions, forward, strict=True):
            found = stored.get(plan.key)
            if found is None:
                pending.append((question, plan, self._heaviest_reverse(question, context)))
                continue
            pick = needs_reverse(question, answer_from_row(found))
            reverse = None if pick is None else reverse_plan(question, pick, context)
            pending.append((question, None, reverse))  # type: ignore[arg-type]
            if reverse is not None:
                reverse_keys.append(reverse.key)
        stored_reverse = self._pairs.stored_answers(session, context.project_uid, reverse_keys)
        out: list[_Assessment] = []
        for question, plan, reverse in pending:
            calls: list[CallPlan] = []
            if plan is not None:
                calls.append(plan)
            if reverse is not None and reverse.key not in stored_reverse:
                calls.append(reverse)
            out.append(_Assessment(question, tuple(calls)))
        return out

    @staticmethod
    def _heaviest_reverse(question: Question, context: PlanContext) -> CallPlan | None:
        """When the forward answer is not known the reverse call that might follow is: the heaviest over the candidates it
        could name. A ``medium_pair`` question has none (its decision never reads a reverse answer)."""
        if question.kind != KIND_NO_PAIR or question.multi:
            return None
        plans = [
            plan for page in question.candidates
            if page.page_number not in question.taken_b and (plan := reverse_plan(question, page.page_number, context)) is not None
        ]
        return max(plans, key=lambda plan: (plan.images, plan.image_bytes, len(plan.prompt)), default=None)

    # -- the work items of a job ---------------------------------------------------------------------
    def work_items(self, session: Session, job: AiJobRecord, mode: AiMode) -> list[AiWorkItemSpec]:
        if mode is AiMode.LEFT:
            return []  # the job's own items are still there; the core resumes the paused ones
        if mode is AiMode.FAILED:
            specs = self._requeue_failed(session, job)
        else:
            specs = self._ask_items(session, job)
        if specs:
            self._enqueue_close(session, job)
        return specs

    def _ask_items(self, session: Session, job: AiJobRecord) -> list[AiWorkItemSpec]:
        if job.matrix_id is None:
            raise ValueError("a pair check names a build")
        snapshot = load_snapshot(
            session, self._matrices, self._pairs, project_uid=job.project_uid, document_uid=job.document_uid,
            matrix_id=job.matrix_id, latest_only=True,
        )
        specs: list[AiWorkItemSpec] = []
        for question in snapshot.questions():
            question_id = self._pairs.insert_question(
                session, job_id=job.job_id, project_uid=job.project_uid, document_uid=job.document_uid, matrix_id=job.matrix_id,
                kind=question.kind, page_version_uid=question.a.version_uid, page_number=question.a.page_number,
                version_uid=question.b_version_uid, candidates=candidate_documents(question),
            )
            specs.append(AiWorkItemSpec(
                unit_key=question_unit_key(question_id),
                payload={"step": ASK_STEP, "question_id": question_id, "question": question.payload()},
            ))
        return specs

    def _requeue_failed(self, session: Session, job: AiJobRecord) -> list[AiWorkItemSpec]:
        specs: list[AiWorkItemSpec] = []
        for payload in self._pairs.ask_payloads(session, job.job_id, _FAILED_ITEM_STATES):
            question_id = str(payload["question_id"])
            self._pairs.requeue_question(session, question_id)
            # the stored payload carries the job's identity, which the core writes itself and refuses in a spec
            specs.append(AiWorkItemSpec(
                unit_key=question_unit_key(question_id), payload={k: v for k, v in payload.items() if k != SPEND_JOB_KEY},
            ))
        return specs

    def _enqueue_close(self, session: Session, job: AiJobRecord) -> None:
        """The closing item, written beside the job's items but **not** linked to the job (see the module docstring)."""
        self._work.enqueue(
            session, project_uid=job.project_uid, module="versions", kind=PAIR_CHECK_KIND,
            payload={"step": CLOSE_STEP, "job_id": job.job_id}, dedupe_key=f"{job.job_id}:{CLOSE_STEP}", priority=-10,
            delay_seconds=CLOSE_POLL_SECONDS, max_attempts=10, created_by_user_uid=job.consented_by_user_uid,
        )


def plan_context(snapshot: Snapshot, *, project_uid: str, model_identity: str, provider_mode: str) -> PlanContext:
    return PlanContext(
        project_uid=project_uid, model_identity=model_identity, provider_mode=provider_mode, order=snapshot.order,
        page_counts=snapshot.page_counts, facts=snapshot.facts, document_title=snapshot.document_title,
    )


def candidate_documents(question: Question) -> list[dict[str, Any]]:
    """The candidates as the question row stores them: the page and its profile, and ``algo`` on the algorithm's own page of a
    ``medium_pair`` question (the decision of such a question needs to know which page the algorithm chose)."""
    return [
        {
            "page_number": page.page_number, "page_profile_id": page.page_profile_id,
            **({"algo": True} if question.algo_b == page.page_number else {}),
        }
        for page in question.candidates
    ]
