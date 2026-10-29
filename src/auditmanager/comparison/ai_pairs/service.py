"""The seven operations of the AI pair check over the shared AI-job core (`CMP-VC-AIPAIR-01`, ADR-0025 decisions 3, 14, 16, 19, 23).

:class:`ComparisonAiPairService` returns plain dictionaries in the contract's shapes; the bootstrap adapter maps them to the
pydantic models, the cursors and the actor. It owns **no state edge** and writes **no job row**: every estimate, start, pause,
resume and cancel is one call of :class:`~auditmanager.comparison.ai_jobs.service.ComparisonAiJobService`.

What it adds to the core:

* **the scope** -- a check is of the latest matrix build of a document set, and only of a ``ready`` one: a matrix that is
  absent, building, stale or failed is ``409 conflict`` ``comparison_matrix_stale`` (the estimate and the start; a moved build is
  caught again inside the core's transaction, where the scope is read once more);
* **the module flag** first, before any read, then the role (an expert's act) and the consent, in the core's own order;
* **the reads** the core does not have: the latest job with «вопросов · пар · подсказок · против», and the hints.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.ai_jobs.estimate import read_route
from auditmanager.comparison.ai_jobs.model import AiConsentInput, AiRoute, AiScope
from auditmanager.comparison.ai_jobs.service import AiJobCommand, ComparisonAiJobService
from auditmanager.comparison.ai_pairs.method import PairCheckMethod, stale_matrix
from auditmanager.comparison.ai_pairs.model import DECISIONS
from auditmanager.comparison.ai_pairs.repository import AiPairRepository, HintRow
from auditmanager.comparison.matrix.repository import MatrixRepository
from auditmanager.comparison.matrix.service import ComparisonMatrixService
from auditmanager.comparison.modules import MODULE_VERSIONS, enabled_modules, parse_modules
from auditmanager.comparison.profile.limits import ALGO_VERSION as PAGE_PROFILE_ALGO_VERSION
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = ["COMMAND_TYPES", "ComparisonAiPairService", "HintsPage"]

#: The registered command types (``product_purge.py``): the snake case of the operationId.
COMMAND_TYPES: Final[Mapping[str, str]] = {
    "start": "start_comparison_ai_pair_check",
    "pause": "pause_comparison_ai_pair_check",
    "resume": "resume_comparison_ai_pair_check",
    "cancel": "cancel_comparison_ai_pair_check",
}
_MAX_HINTS: Final[int] = 200


@dataclass(frozen=True, slots=True)
class HintsPage:
    items: list[dict[str, Any]]
    #: ``(created_at, question id)`` of the last item when more follow, else ``None``.
    next_after: tuple[datetime, str] | None


class ComparisonAiPairService:
    """Estimate, start, steer and read the AI check of the doubtful pairs of a document set."""

    def __init__(
        self, session_factory: "sessionmaker[Session]", *, blob_store: Any = None, comparison_modules: str = "none",
        provider_mode: str = "live", route_reader: Callable[[Session, str, str], AiRoute] = read_route,
        jobs: ComparisonAiJobService | None = None, matrix: ComparisonMatrixService | None = None,
        pairs: AiPairRepository | None = None, method: PairCheckMethod | None = None,
    ) -> None:
        self._factory = session_factory
        self._versions_module_on = MODULE_VERSIONS in enabled_modules(parse_modules(comparison_modules))
        self._pairs = pairs or AiPairRepository()
        self._matrices = MatrixRepository()
        self._matrix = matrix or ComparisonMatrixService(session_factory=session_factory, blob_store=blob_store)
        self._method = method or PairCheckMethod(provider_mode=provider_mode, route_reader=route_reader)
        self._jobs = jobs or ComparisonAiJobService(
            session_factory, methods=[self._method], comparison_modules=comparison_modules, provider_mode=provider_mode,
            route_reader=route_reader,
        )

    @property
    def jobs(self) -> ComparisonAiJobService:
        return self._jobs

    @property
    def method(self) -> PairCheckMethod:
        return self._method

    def _require_versions_module(self) -> None:
        """``503 dependency_unavailable`` (``comparison_modules``) while the versions module is off: the first statement of every
        operation, before any read, write or model call (ADR-0025 decision 23, ``A-12``)."""
        if not self._versions_module_on:
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="comparison_modules")

    # -- the scope ---------------------------------------------------------------------------------------
    def _scope(self, project_uid: str, document_uid: str) -> AiScope:
        """The scope of a check: the latest build of the document set, which must be ``ready``. An unknown project or a document
        of another project is ``404`` (the matrix read says so first)."""
        matrix = self._matrix.get_matrix(project_uid=project_uid, document_uid=document_uid)
        revision = matrix.get("revision")
        if matrix.get("state") != "ready" or not revision:
            raise stale_matrix()
        return AiScope(method="pair_check", project_uid=project_uid, document_uid=document_uid, matrix_id=str(revision["matrix_id"]))

    # -- the operations ----------------------------------------------------------------------------------
    def estimate(self, *, project_uid: str, document_uid: str) -> dict[str, Any]:
        self._require_versions_module()
        return self._jobs.estimate(self._scope(project_uid, document_uid)).as_dict()

    def start(
        self, *, project_uid: str, document_uid: str, consent: AiConsentInput, user_uid: str, actor_roles: frozenset[str],
        idempotency_key: str,
    ) -> dict[str, Any]:
        self._require_versions_module()
        # The core refuses a non-expert and an unconfirmed consent before it reads anything; the scope below is a read, so
        # the same two refusals come first here (a refused command writes nothing either way).
        if "expert" not in actor_roles:
            raise DomainError(ErrorCode.PERMISSION_DENIED, required_capability="role:expert")
        if not consent.confirmed:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="consent", constraint="comparison_consent_required")
        scope = self._scope(project_uid, document_uid)
        view = self._jobs.start(
            scope=scope, consent=consent, command=self._command("start", user_uid, actor_roles, idempotency_key),
        )
        return view.as_dict()

    def pause(self, *, job_id: str, user_uid: str, actor_roles: frozenset[str], idempotency_key: str) -> dict[str, Any]:
        self._require_versions_module()
        return self._jobs.pause(
            job_id=job_id, method="pair_check", command=self._command("pause", user_uid, actor_roles, idempotency_key),
        ).as_dict()

    def resume(
        self, *, job_id: str, consent: AiConsentInput | None, user_uid: str, actor_roles: frozenset[str], idempotency_key: str,
    ) -> dict[str, Any]:
        self._require_versions_module()
        return self._jobs.resume(
            job_id=job_id, method="pair_check", consent=consent,
            command=self._command("resume", user_uid, actor_roles, idempotency_key),
        ).as_dict()

    def cancel(self, *, job_id: str, user_uid: str, actor_roles: frozenset[str], idempotency_key: str) -> dict[str, Any]:
        self._require_versions_module()
        return self._jobs.cancel(
            job_id=job_id, method="pair_check", command=self._command("cancel", user_uid, actor_roles, idempotency_key),
        ).as_dict()

    @staticmethod
    def _command(kind: str, user_uid: str, actor_roles: frozenset[str], idempotency_key: str) -> AiJobCommand:
        return AiJobCommand(
            command_type=COMMAND_TYPES[kind], idempotency_key=idempotency_key, user_uid=user_uid, actor_roles=actor_roles,
        )

    # -- the reads ---------------------------------------------------------------------------------------
    def get(self, *, project_uid: str, document_uid: str) -> dict[str, Any]:
        """The latest job of the document set and its counts; both are absent until a check was started."""
        self._require_versions_module()
        with session_scope(self._factory) as session:
            self._pairs.require_document(session, project_uid, document_uid)
            job_id = self._pairs.latest_job_of(session, document_uid)
        document: dict[str, Any] = {"document_uid": document_uid}
        if job_id is None:
            return document
        view = self._jobs.view(job_id, method="pair_check")
        with session_scope(self._factory) as session:
            figures = self._pairs.figures(session, job_id)
        document["job"] = view.as_dict()
        document["counts"] = {
            "questions": figures.questions, "answered": figures.answered, "pairs": figures.pairs, "hints": figures.hints,
            "against": figures.against, "failed": figures.failed, "reused": figures.reused,
        }
        return document

    def hints(
        self, *, project_uid: str, document_uid: str, after: tuple[datetime, str] | None, limit: int,
    ) -> HintsPage:
        """The questions that have a decision, newest first, for the matrix cells they concern."""
        self._require_versions_module()
        bounded = max(1, min(limit, _MAX_HINTS))
        with session_scope(self._factory) as session:
            self._pairs.require_document(session, project_uid, document_uid)
            rows = self._pairs.hints(
                session, document_uid, algo_version=PAGE_PROFILE_ALGO_VERSION, after=after, limit=bounded + 1,
            )
        page = rows[:bounded]
        more = len(rows) > bounded and bool(page)
        return HintsPage(
            items=[_hint(row) for row in page], next_after=(page[-1].created_at, page[-1].question_id) if more else None,
        )


def _page(version_uid: str, page_number: int, profile_id: str | None) -> dict[str, Any]:
    document: dict[str, Any] = {"version_uid": version_uid, "page_number": page_number}
    if profile_id:
        document["page_profile_id"] = profile_id
    return document


def _hint(row: HintRow) -> dict[str, Any]:
    if row.decision not in DECISIONS:  # pragma: no cover - the table's CHECK says otherwise
        raise ValueError("a hint with a decision the contract does not know")
    document: dict[str, Any] = {
        "question_id": row.question_id, "job_id": row.job_id, "matrix_id": row.matrix_id, "kind": row.kind,
        "decision": row.decision, "page": _page(row.page_version_uid, row.page_number, row.page_profile_id),
        "version_uid": row.version_uid,
        "candidates": [_page(row.version_uid, int(c["page_number"]), c.get("page_profile_id")) for c in row.candidates],
        "stale": row.stale, "created_at": row.created_at,
    }
    if row.hint_version_uid is not None and row.hint_page_number is not None:
        document["hint_page"] = _page(row.hint_version_uid, row.hint_page_number, row.hint_profile_id)
    if row.confidence:
        document["confidence"] = row.confidence
    if row.link_id:
        document["link_id"] = row.link_id
    if row.reason:
        document["reason"] = row.reason
    return document
