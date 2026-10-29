"""The AI description of sheet changes (`CMP-VC-AISHEET-01`), over the AI-job core.

The service answers the contract's shapes as plain dictionaries; the adapter in the composition root validates them with the generated
models and owns the cursors. **Every job object, estimate, consent and state edge is** ``ComparisonAiJobService``'s: this service
supplies the scope and the method (:class:`.method.SheetChangesMethod`) and writes no row of ``comparison_ai_job``.

Decisions that are this lane's (each one place to change):

1. **The estimate op answers by what the series is doing.** ``estimateComparisonAiSheetChanges`` has no ``restart`` and no job in its
   address, but a consent is to *one* digest, and the digest binds the scope's ``restart`` flag and the mode. So: while the latest job is
   paused for ``overrun`` or ``route_changed`` the estimate is the one of **what is left** (the consent a resume asks for, otherwise the
   client could never learn its digest); with ``only_failed`` it is the estimate of the failed sheets, for the latest job's ``restart``
   flag (the consent of a retry); otherwise it is the start's (no restart).
2. **A start with ``restart`` is consented to the digest of the start without it.** The client has only that estimate; the service checks
   the presented digest against it (a stale one is still ``comparison_estimate_stale``) and then starts the restart scope under the
   restart scope's own digest. Re-describing changes which sheets the job lists, not the money: a sheet with a stored description is
   resolved without a call.
3. **A sheet with a stored description is never asked again** -- in the estimate (``reused``), in the items of a job, and in the handler
   (the key is looked up before any call).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.ai_jobs.model import CONSENT_PAUSES, AiConsentInput, AiJobRecord, AiMode, AiScope
from auditmanager.comparison.ai_jobs.service import AiJobCommand, ComparisonAiJobService
from auditmanager.comparison.ai_sheets.description import sheet_markdown
from auditmanager.comparison.ai_sheets.method import SheetChangesMethod, facts_of
from auditmanager.comparison.ai_sheets.model import METHOD
from auditmanager.comparison.ai_sheets.repository import AiSheetRepository, PairFacts
from auditmanager.comparison.ai_sheets.views import (
    current_prompt_of,
    declared_of,
    derive_state,
    description_view,
    eligible,
    history_item,
    review_item,
    state_eligible,
    transition_progress,
)
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = ["ComparisonAiSheetService", "HistoryPage", "ReviewPage"]

CONFLICT_STALE = "comparison_estimate_stale"
CONFLICT_NOTHING = "comparison_ai_nothing_to_do"
CONFLICT_MISSING = "comparison_description_missing"
_LIVE = ("queued", "running")


@dataclass(frozen=True, slots=True)
class HistoryPage:
    items: list[dict[str, Any]]
    next_after: tuple[datetime, str] | None


@dataclass(frozen=True, slots=True)
class ReviewPage:
    items: list[dict[str, Any]]
    next_after: int | None


def _not_found(aggregate: str) -> DomainError:
    return DomainError(ErrorCode.NOT_FOUND, aggregate_type=aggregate)


def _conflict(reason: str) -> DomainError:
    return DomainError(ErrorCode.CONFLICT, conflict_reason=reason)


class ComparisonAiSheetService:
    def __init__(
        self, session_factory: "sessionmaker[Session]", *, jobs: ComparisonAiJobService, method: SheetChangesMethod,
        repository: AiSheetRepository | None = None,
    ) -> None:
        self._factory = session_factory
        self._jobs = jobs
        self._method = method
        self._repo = repository or AiSheetRepository()

    # -- scopes ---------------------------------------------------------------------------------------------------------
    def _series_scope(self, series_id: str, *, restart: bool = False) -> tuple[AiScope, Mapping[str, Any]]:
        with session_scope(self._factory) as session:
            series = self._repo.series(session, series_id)
        if series is None:
            raise _not_found("ComparisonSeries")
        return AiScope(
            method=METHOD, project_uid=series["project_uid"], document_uid=series["document_uid"], series_id=series_id, restart=restart,
        ), series

    def _pair_scope(self, pair_id: str) -> tuple[AiScope, PairFacts]:
        with session_scope(self._factory) as session:
            pair = self._repo.pair(session, pair_id)
        if pair is None:
            raise _not_found("ComparisonSheetPair")
        return AiScope(method=METHOD, project_uid=pair.project_uid, document_uid=pair.document_uid, sheet_pair_id=pair_id), pair

    # -- the series -----------------------------------------------------------------------------------------------------
    def estimate_series(self, *, series_id: str, only_failed: bool) -> dict[str, Any]:
        scope, _series = self._series_scope(series_id)
        with session_scope(self._factory) as session:
            if not any(t["state"] == "completed" for t in self._repo.transitions_of(session, series_id)):
                raise _conflict(CONFLICT_NOTHING)
        latest = self._jobs.latest(scope)
        if latest is not None and latest.record.state == "paused" and latest.record.pause_reason in CONSENT_PAUSES:
            with session_scope(self._factory) as session:
                return self._jobs.estimate_in(session, latest.record.scope, AiMode.LEFT, job=latest.record).as_dict()
        if only_failed:
            failed_scope = replace(scope, restart=bool(latest and latest.record.restart))
            return self._jobs.estimate(failed_scope, AiMode.FAILED).as_dict()
        return self._jobs.estimate(scope, AiMode.START).as_dict()

    def start_series(
        self, *, series_id: str, consent: AiConsentInput, restart: bool, command: AiJobCommand,
    ) -> dict[str, Any]:
        scope, _series = self._series_scope(series_id, restart=restart)
        consent = self._consented(scope, AiMode.START, consent, command)
        return self._jobs.start(scope=scope, consent=consent, command=command).as_dict()

    def _consented(self, scope: AiScope, mode: AiMode, consent: AiConsentInput, command: AiJobCommand) -> AiConsentInput:
        """The consent a core call checks. For a scope with ``restart`` the client holds the digest of the estimate without it (decision 2)."""
        if not scope.restart or not consent.confirmed or "expert" not in command.actor_roles:
            return consent  # the core refuses what must be refused, in its own order
        if consent.estimate_digest != self._jobs.estimate(replace(scope, restart=False), mode).estimate_digest:
            raise _conflict(CONFLICT_STALE)
        return AiConsentInput(estimate_digest=self._jobs.estimate(scope, mode).estimate_digest, confirmed=True)

    def get_series(self, *, series_id: str) -> dict[str, Any]:
        scope, _series = self._series_scope(series_id)
        view = self._jobs.latest(scope)
        with session_scope(self._factory) as session:
            transitions = self._repo.transitions_of(session, series_id)
            rows = self._repo.states_of_series(session, series_id)
            spend = self._repo.job_spend_by_transition(session, view.record.job_id) if view is not None else {}
        by_transition: dict[str, list[tuple[Any, str]]] = {str(t["comparison_transition_id"]): [] for t in transitions}
        for ps in rows:
            if state_eligible(ps) and ps.transition_state == "completed":
                by_transition.setdefault(ps.transition_id, []).append((ps, derive_state(ps, current_prompt=current_prompt_of(ps))))
        document: dict[str, Any] = {
            "series_id": series_id,
            "transitions": [
                transition_progress(str(t["comparison_transition_id"]), by_transition[str(t["comparison_transition_id"])],
                                    spend.get(str(t["comparison_transition_id"])))
                for t in transitions
            ],
        }
        if view is not None:
            document["job"] = view.as_dict()
        return document

    # -- the steering of a job (every edge is the core's) ----------------------------------------------------------------
    def pause(self, *, job_id: str, command: AiJobCommand) -> dict[str, Any]:
        return self._jobs.pause(job_id=job_id, method=METHOD, command=command).as_dict()

    def resume(self, *, job_id: str, consent: AiConsentInput | None, command: AiJobCommand) -> dict[str, Any]:
        return self._jobs.resume(job_id=job_id, method=METHOD, command=command, consent=consent).as_dict()

    def cancel(self, *, job_id: str, command: AiJobCommand) -> dict[str, Any]:
        return self._jobs.cancel(job_id=job_id, method=METHOD, command=command).as_dict()

    def finish(self, *, job_id: str, command: AiJobCommand) -> dict[str, Any]:
        return self._jobs.finish(job_id=job_id, method=METHOD, command=command).as_dict()

    def dequeue(self, *, job_id: str, command: AiJobCommand) -> dict[str, Any]:
        return self._jobs.dequeue(job_id=job_id, method=METHOD, command=command).as_dict()

    def retry(self, *, job_id: str, consent: AiConsentInput, command: AiJobCommand) -> dict[str, Any]:
        return self._jobs.retry(job_id=job_id, method=METHOD, command=command, consent=consent).as_dict()

    # -- a sheet pair ---------------------------------------------------------------------------------------------------
    def _subject(self, pair: PairFacts) -> dict[str, Any]:
        return {
            "project_uid": pair.project_uid, "result_id": None if pair.one_sided else pair.result_id,
            "page_profile_id": pair.subject_page_profile if pair.one_sided else None,
        }

    def get_description(self, *, sheet_pair_id: str) -> dict[str, Any]:
        _scope, pair = self._pair_scope(sheet_pair_id)
        with session_scope(self._factory) as session:
            ps = self._repo.state_of_pair(session, sheet_pair_id)
            assert ps is not None  # the pair exists
            state = derive_state(ps, current_prompt=current_prompt_of(ps))
            subject = self._subject(pair)
            latest = self._repo.latest_description(session, **subject) if (subject["result_id"] or subject["page_profile_id"]) else None
            count = self._repo.history_count(session, **subject) if latest is not None else 0
        return description_view(pair, state, latest=latest, history_count=count, job_id=ps.job_id)

    def estimate_description(self, *, sheet_pair_id: str) -> dict[str, Any]:
        scope, pair = self._pair_scope(sheet_pair_id)
        if not eligible(pair):
            raise _conflict(CONFLICT_NOTHING)
        return self._jobs.estimate(scope, AiMode.START).as_dict()

    def start_description(self, *, sheet_pair_id: str, consent: AiConsentInput, command: AiJobCommand) -> dict[str, Any]:
        scope, pair = self._pair_scope(sheet_pair_id)
        if not eligible(pair) and "expert" in command.actor_roles and consent.confirmed:
            raise _conflict(CONFLICT_NOTHING)
        return self._jobs.start(scope=scope, consent=consent, command=command).as_dict()

    def list_history(self, *, sheet_pair_id: str, after: tuple[datetime, str] | None, limit: int) -> HistoryPage:
        _scope, pair = self._pair_scope(sheet_pair_id)
        subject = self._subject(pair)
        if not (subject["result_id"] or subject["page_profile_id"]):
            return HistoryPage([], None)
        with session_scope(self._factory) as session:
            rows = self._repo.history(session, after=after, limit=limit + 1, **subject)
        page = rows[:limit]
        more = len(rows) > limit
        return HistoryPage(
            [history_item(r) for r in page], (page[-1].created_at, page[-1].description_id) if (more and page) else None,
        )

    def read_md(self, *, sheet_pair_id: str) -> bytes:
        _scope, pair = self._pair_scope(sheet_pair_id)
        subject = self._subject(pair)
        with session_scope(self._factory) as session:
            latest = (
                self._repo.latest_description(session, **subject) if (subject["result_id"] or subject["page_profile_id"]) else None
            )
        if latest is None:
            raise _conflict(CONFLICT_MISSING)
        facts = facts_of(pair)
        header = {
            "sheet_pair_id": pair.pair_id, "title": pair.title, "page_a": facts.page_a or None, "page_b": facts.page_b or None,
            "label_a": facts.label_a, "label_b": facts.label_b,
        }
        text = sheet_markdown(header, latest.description, declared=declared_of(pair))
        return text.encode("utf-8")

    def descriptions_of_transition(self, *, transition_id: str) -> list[dict[str, Any]]:
        """For the Markdown summary and the report (`CMP-VC-REPORT-01`): each sheet pair of a transition, in the order of the matrix
        rows, with its derived state and its newest stored description (``None`` when it has none). Reading starts nothing."""
        with session_scope(self._factory) as session:
            if self._repo.transition(session, transition_id) is None:
                raise _not_found("ComparisonTransition")
            pairs = {p.pair_id: p for p in self._repo.pairs_of_transition(session, transition_id)}
            out: list[dict[str, Any]] = []
            for ps in self._repo.states_of_transition(session, transition_id):
                pair = pairs[ps.pair_id]
                subject = self._subject(pair)
                latest = (
                    self._repo.latest_description(session, **subject) if (subject["result_id"] or subject["page_profile_id"]) else None
                )
                out.append({
                    "sheet_pair_id": ps.pair_id, "pair_no": ps.pair_no, "status": ps.status,
                    "state": derive_state(ps, current_prompt=current_prompt_of(ps)),
                    "description": None if latest is None else dict(latest.description),
                    "description_id": None if latest is None else latest.description_id,
                    "recorded": bool(latest and latest.recorded), "declared": declared_of(pair),
                })
        return out

    def list_review_sheets(self, *, transition_id: str, after: int, limit: int) -> ReviewPage:
        with session_scope(self._factory) as session:
            if self._repo.transition(session, transition_id) is None:
                raise _not_found("ComparisonTransition")
            rows = self._repo.states_of_transition(session, transition_id, after=after)
        items: list[tuple[int, dict[str, Any]]] = []
        for ps in rows:
            if not state_eligible(ps):
                continue
            entry = review_item(ps, derive_state(ps, current_prompt=current_prompt_of(ps)))
            if entry is not None:
                items.append((ps.pair_no, entry))
        page = items[:limit]
        return ReviewPage([e for _n, e in page], page[-1][0] if len(items) > limit and page else None)
