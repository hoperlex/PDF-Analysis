"""Durable Stage AI phases through the shared consent and spend runtime."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping

from sqlalchemy import text

from auditmanager.access.public import AccountRepository
from auditmanager.analysis.public import ModelRequest
from auditmanager.comparison.ai_jobs.estimate import read_route
from auditmanager.comparison.ai_jobs.model import (
    AiConsentInput, AiScope, CHARS_PER_TOKEN_NUMERATOR, CHARS_PER_TOKEN_DENOMINATOR,
)
from auditmanager.comparison.ai_jobs.service import AiJobCommand, ComparisonAiJobService
from auditmanager.comparison.spend.caller import ComparisonModelCaller
from auditmanager.comparison.spend.errors import CallFailed, CallLost, CallRefused, OutcomeUnknown
from auditmanager.comparison.spend.model import CallEstimate, JOB_KEY
from auditmanager.comparison.work.model import Failed, Yielded
from auditmanager.ingest.comparison_pdf.public import require_expert
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode

from .classifier import build_classification_request, parse_classification
from .model import ClassifiedCard, SynthesisGroup
from .planning import StageAiMethod
from .repository import ANSWER_TABLES, StageAiRepository
from .reviewer import accept_review_group, build_review_requests
from .source import build_source_groups
from .synthesis import build_synthesis_request, parse_synthesis
from .validation import StageAiValidationError, canonical_json, digest

__all__ = ["StageAiRuntime", "request_for_plan"]


def request_for_plan(plan) -> ModelRequest:
    """Use the existing structured model wire shape; never choose a provider here."""
    return ModelRequest(model_id=plan.model, body={
        "model": plan.model, "max_tokens": plan.max_output_tokens,
        "messages": [{"role": "user", "content": plan.instructions + "\nINPUT\n" + plan.payload_json}],
        "output_config": {"effort": "medium", "format": {"type": "json_schema", "schema": plan.response_schema}},
    }, idempotency_scope="stage-ai:" + plan.content_key)


def _consent(value) -> AiConsentInput | None:
    if value is None or isinstance(value, AiConsentInput):
        return value
    if isinstance(value, Mapping):
        return AiConsentInput(str(value.get("estimate_digest", "")), value.get("confirmed") is True)
    return AiConsentInput(str(value.estimate_digest), value.confirmed is True)


class StageAiRuntime:
    """No I/O in construction. Root owns chain scheduling and shared registry wiring."""

    def __init__(self, session_factory, *, blob_store=None, routes=None, provider_mode="recorded",
                 repository=None, caller=None, jobs_factory=None, route_reader=read_route, profile_reader=None):
        self._sessions = session_factory
        self._store = blob_store
        self._routes = routes
        self._mode = provider_mode
        self._repo = repository or StageAiRepository()
        self._caller = caller
        self._jobs_factory = jobs_factory
        self._route_reader = route_reader
        self._profile_reader = profile_reader

    def _method(self):
        return StageAiMethod(self._repo, sessions=self._sessions, blob_store=self._store,
                             profile_reader=self._profile_reader)

    def _jobs(self, method=None):
        method = method or self._method()
        if self._jobs_factory is not None:
            return self._jobs_factory(method)
        return ComparisonAiJobService(
            self._sessions, methods=[method], comparison_modules="versions,stages",
            provider_mode=self._mode, route_reader=self._route_reader,
        )

    def _scope(self, snapshot, *, run_id=None):
        try:
            return AiScope(method="stage_review", project_uid=str(snapshot["project_uid"]),
                           document_uid=str(snapshot["document_uid"]), stage_chain_run_id=run_id,
                           stage_link_revision_id=str(snapshot.get("revision_id") or snapshot["stage_link_revision_id"]))
        except TypeError:
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="comparison_stage_ai_seal") from None

    @staticmethod
    def _roles(session, user_uid):
        roles = AccountRepository().roles_of(session, user_uid)
        require_expert(roles)
        return roles

    def estimate(self, *, revision_id: str, user_uid: str):
        method = self._method()
        with session_scope(self._sessions) as session:
            self._roles(session, user_uid)
            snapshot = self._repo.revision(session, revision_id)
            return self._jobs(method).estimate_in(session, self._scope(snapshot))

    def prepare(self, session, *, run_id: str, user_uid: str, consent) -> str | None:
        roles = self._roles(session, user_uid)
        run = self._repo.run(session, run_id)
        if run.get("comparison_ai_job_id"):
            return str(run["comparison_ai_job_id"])
        method = self._method()
        jobs = self._jobs(method)
        scope = self._scope(run, run_id=run_id)
        estimate = jobs.estimate_in(session, scope)
        if estimate.totals.calls == 0:
            payload = {"content_key": method.source_signature, "not_checked": "no_text_evidence",
                       "profiles": method.source_profiles, "pinned_model": estimate.route.pinned_model,
                       "responses": {}, "immutable_source": {"profiles": method.source_profiles,
                                                                "not_checked": "no_text_evidence"}}
            unit = self._repo.unit(session, run_id=run_id, kind="review", group_id="no-text",
                                   source_sha256=method.source_signature, payload=payload)
            self._repo.update_unit(session, unit["stage_ai_unit_id"], payload=unit["payload"], state="completed")
            return None
        chosen = _consent(consent)
        if chosen is None:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="consent", constraint="comparison_consent_required")
        start = getattr(jobs, "start_in_session", None)
        if start is None:
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="comparison_stage_ai_seal")
        view = start(session, scope=scope, consent=chosen, queue_items=False,
                     command=AiJobCommand("start_stage_review_ai", f"stage-ai-prepare-{run_id}", user_uid, roles))
        return str(view.record.job_id)

    def resume(self, session, *, run_id: str, user_uid: str, consent=None) -> str | None:
        roles = self._roles(session, user_uid)
        run = self._repo.run(session, run_id)
        job_id = run.get("comparison_ai_job_id")
        if not job_id:
            return self.prepare(session, run_id=run_id, user_uid=user_uid, consent=consent)
        jobs = self._jobs()
        resume = getattr(jobs, "resume_in_session", None)
        if resume is None:
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="comparison_stage_ai_resume")
        chosen = _consent(consent)
        key = digest({"run_id": run_id, "consent": None if chosen is None else chosen.estimate_digest})
        view = resume(session, job_id=str(job_id), method="stage_review", consent=chosen, queue_items=False,
                      command=AiJobCommand("resume_stage_review_ai", "stage-ai-resume-" + key, user_uid, roles))
        return str(view.record.job_id)

    def _checked(self, session, item, run_id):
        item.require_current(session)
        run = self._repo.run(session, run_id)
        if run["project_uid"] != item.project_uid or run["state"] not in {"queued", "running", "paused"}:
            raise DomainError(ErrorCode.CONFLICT, conflict_reason="stage_ai_run_scope_or_state")
        snapshot = self._repo.revision(session, run["revision_id"])
        current = session.execute(text(
            "SELECT stage_link_revision_id FROM stage_link_revision WHERE stage_pair_id=:pair "
            "ORDER BY revision_no DESC LIMIT 1"
        ), {"pair": run["stage_pair_id"]}).scalar_one_or_none()
        if current != run["revision_id"] or set(run["pinned_version_uids"]) != {
            profile["version_uid"] for profile in snapshot["all_profiles"]
        }:
            raise DomainError(ErrorCode.CONFLICT, conflict_reason="stage_ai_input_stale")
        job_id = run.get("comparison_ai_job_id")
        if job_id and item.payload.get(JOB_KEY) != job_id:
            raise DomainError(ErrorCode.CONFLICT, conflict_reason="stage_ai_work_job_pin_mismatch")
        return run, snapshot

    def _bundles(self, session, *, run_id, snapshot, phase, model):
        raw_groups = build_source_groups(snapshot)
        reviews = self._repo.latest_answers(session, run_id=run_id, kind="review")
        matching = {}
        for group in raw_groups:
            plans = build_review_requests(group.review, model=model)
            source_sha = plans[0].payload["full_group_sha256"] if plans else digest({})
            row = reviews.get(group.review.group_id)
            if row is not None and row["source_sha256"] == source_sha:
                matching[group.review.group_id] = row
        groups = build_source_groups(snapshot, matching)
        classes = self._repo.latest_answers(session, run_id=run_id, kind="classify")
        bundles = []
        for group in groups:
            if phase == "review":
                plans = build_review_requests(group.review, model=model)
                source_sha = plans[0].payload["full_group_sha256"]
            else:
                if group.review.group_id not in matching:
                    raise StageAiValidationError("stage_ai_review_missing")
                class_plan = build_classification_request(group.evidence, model=model)
                if phase == "classify":
                    plans, source_sha = (class_plan,), class_plan.source_sha256
                else:
                    row = classes.get(group.review.group_id)
                    if row is None or row["source_sha256"] != class_plan.source_sha256:
                        raise StageAiValidationError("stage_ai_classification_missing")
                    cards = tuple(ClassifiedCard(**(dict(card) | {
                        "evidence_ids": tuple(card["evidence_ids"]),
                        "policy_reasons": tuple(card.get("policy_reasons", ())),
                    })) for card in row["cards"])
                    plan = build_synthesis_request(SynthesisGroup(
                        group.evidence.group_id, group.evidence.evidence, cards,
                        group.evidence.source_link_uncertain,
                    ), model=model)
                    plans, source_sha = (plan,), plan.source_sha256
            key = digest({"phase": phase, "source_sha256": source_sha,
                          "plans": [plan.content_key for plan in plans]})
            bundles.append((group, plans, source_sha, key))
        return bundles

    def _pause(self, session, jobs, *, run_id, job_id, reason, spend=True):
        if spend:
            jobs.pause_for_spend(session, job_id, reason)
        else:
            jobs.pause_system(session, job_id, reason)
        self._repo.pause_run(session, run_id, reason)

    def _failed(self, item, run_id, unit, jobs, job_id, reason):
        try:
            with session_scope(self._sessions) as session:
                item.require_current(session)
                run = self._repo.run(session, run_id)
                actual_job = run.get("comparison_ai_job_id")
                if run["project_uid"] != item.project_uid or (job_id is not None and actual_job != job_id):
                    return Failed("stage_ai_run_scope_or_state")
                if actual_job and item.payload.get(JOB_KEY) != actual_job:
                    return Failed("stage_ai_work_job_pin_mismatch")
                if unit is not None:
                    self._repo.update_unit(session, unit["stage_ai_unit_id"], payload=unit["payload"],
                                           state="failed", reason=reason, job_id=actual_job)
                if actual_job:
                    jobs.fail(session, actual_job, reason)
        except DomainError as error:
            if error.code in {ErrorCode.STALE_ATTEMPT, ErrorCode.EXECUTION_TOKEN_INVALID}:
                return Yielded()
            raise
        return Failed(reason)

    def advance(self, item, *, run_id: str, phase: str):
        if phase not in ANSWER_TABLES:
            return Failed("stage_ai_phase_invalid")
        jobs = self._jobs()
        try:
            with session_scope(self._sessions) as session:
                run, snapshot = self._checked(session, item, run_id)
                job_id = run.get("comparison_ai_job_id")
                if phase == "review":
                    graphics = self._repo.not_checked_graphics(session, run_id=run_id, snapshot=snapshot)
                else:
                    graphics = 0
                if not job_id:
                    return {"groups": 0, "text_not_checked": 1, "graphic_not_checked": graphics}
                job_id = str(job_id)
                state = jobs.mark_running(session, job_id)
                if state not in {"running", "completed"}:
                    return Yielded(30) if state in {"queued", "paused"} else Failed("stage_ai_job_not_active")
                job = jobs.job(session, job_id)
                bundles = self._bundles(session, run_id=run_id, snapshot=snapshot, phase=phase, model=job.pinned_model)
                if state == "completed":
                    if all(self._repo.answer(session, run_id=run_id, kind=phase, content_key=key) is not None
                           for _group, _plans, _source_sha, key in bundles):
                        return {"groups": len(bundles), "completed": len(bundles), "graphic_not_checked": graphics}
                    return Failed("stage_ai_job_not_active")
                pending = []
                for group, plans, source_sha, key in bundles:
                    payload = {"content_key": key, "pinned_model": job.pinned_model,
                               "plan_keys": [plan.content_key for plan in plans], "responses": {},
                               "technical_retries": {}, "immutable_source": {
                                   "sources": [plan.payload for plan in plans],
                               }}
                    unit = self._repo.unit(session, run_id=run_id, kind=phase,
                                           group_id=group.review.group_id, source_sha256=source_sha,
                                           payload=payload, job_id=job_id)
                    answer = self._repo.answer(session, run_id=run_id, kind=phase, content_key=key)
                    if answer is not None:
                        self._repo.update_unit(session, unit["stage_ai_unit_id"], payload=unit["payload"],
                                               state="completed", job_id=job_id)
                        continue
                    if unit["state"] == "failed":
                        return Failed(unit.get("failure_reason") or "stage_ai_unit_failed")
                    pending.append((group, plans, key, unit))
                if not pending:
                    if phase == "synthesize":
                        jobs.complete_if_drained(session, job_id, excluding_work_id=item.work_id)
                    return {"groups": len(bundles), "completed": len(bundles), "graphic_not_checked": graphics}
                group, plans, key, unit = pending[0]
                unit["payload"] = dict(unit["payload"])
                self._repo.update_unit(session, unit["stage_ai_unit_id"], payload=unit["payload"], state="running", job_id=job_id)
                route_source = self._routes
                if route_source is None:
                    return self._fail_in(session, unit, jobs, job_id, "executor_route_missing")
                route = (route_source.route_for(session, job) if hasattr(route_source, "route_for")
                         else route_source.route(session, job))
                consent = jobs.consent_for_calls(session, job_id)
                waiting = next((plan for plan in plans if plan.content_key not in unit["payload"].get("responses", {})), None)
                if waiting is not None:
                    request = request_for_plan(waiting)
                    prior = self._repo.prior_call(session, job_id=job_id, request_sha256=request.request_sha256)
                    retries = unit["payload"].get("technical_retries", {}).get(waiting.content_key, 0)
                    if prior is not None and not (prior["state"] == "failed" and retries == 1):
                        return self._fail_in(session, unit, jobs, job_id, "stage_ai_response_lost")
            if waiting is not None:
                if item.lease_lost.is_set() or item.cancelled.is_set():
                    return Yielded()
                caller = self._caller or ComparisonModelCaller(self._sessions)
                try:
                    result = caller.call(item, route, request,
                                         estimate=CallEstimate(input_tokens=-(-waiting.prompt_chars * CHARS_PER_TOKEN_NUMERATOR
                                                                              // CHARS_PER_TOKEN_DENOMINATOR),
                                                               output_tokens=waiting.max_output_tokens), consent=consent)
                except CallLost:
                    return Yielded()
                except CallFailed as error:
                    retries = unit["payload"].get("technical_retries", {}).get(waiting.content_key, 0)
                    if error.retry_safe and retries == 0:
                        unit["payload"].setdefault("technical_retries", {})[waiting.content_key] = 1
                        with session_scope(self._sessions) as session:
                            self._checked(session, item, run_id)
                            self._repo.update_unit(session, unit["stage_ai_unit_id"], payload=unit["payload"], state="queued", job_id=job_id)
                        return Yielded()
                    return self._failed(item, run_id, unit, jobs, job_id, "stage_ai_call_failed")
                except OutcomeUnknown:
                    return self._failed(item, run_id, unit, jobs, job_id, "stage_ai_outcome_unknown")
                except CallRefused as error:
                    if error.pauses_job:
                        with session_scope(self._sessions) as session:
                            self._checked(session, item, run_id)
                            self._pause(session, jobs, run_id=run_id, job_id=job_id, reason=error.reason)
                        return Yielded(30)
                    outcome = error.as_outcome()
                    return (self._failed(item, run_id, unit, jobs, job_id, "stage_ai_call_refused")
                            if isinstance(outcome, Failed) else outcome)
                with session_scope(self._sessions) as session:
                    self._checked(session, item, run_id)
                    unit["payload"].setdefault("responses", {})[waiting.content_key] = {
                        "output_text": result.response.output_text, "call_id": result.call_id,
                        "stop_reason": result.response.stop_reason, "request_sha256": request.request_sha256,
                        "model_identity": route.model_identity,
                    }
                    self._repo.update_unit(session, unit["stage_ai_unit_id"], payload=unit["payload"], state="running", job_id=job_id)
                    if result.pause is not None:
                        self._pause(session, jobs, run_id=run_id, job_id=job_id, reason=result.pause.reason)
                        return Yielded(30)
                if len(unit["payload"]["responses"]) < len(plans):
                    return Yielded()
            responses = unit["payload"].get("responses", {})
            if any(value["stop_reason"] == "max_tokens" for value in responses.values()):
                return self._failed(item, run_id, unit, jobs, job_id, "stage_ai_response_truncated")
            if phase == "review":
                parsed = accept_review_group(group.review, plans, {
                    plan.unit_key: responses[plan.content_key]["output_text"] for plan in plans
                })
                value = [asdict(decision) for decision in parsed.decisions]
                if len(value) > 800:
                    raise StageAiValidationError("stage_ai_review_result_budget")
            elif phase == "classify":
                parsed = parse_classification(plans[0], responses[plans[0].content_key]["output_text"])
                value = [asdict(card) for card in parsed.cards]
            else:
                parsed = parse_synthesis(plans[0], responses[plans[0].content_key]["output_text"])
                value = asdict(parsed)
            with session_scope(self._sessions) as session:
                self._checked(session, item, run_id)
                self._repo.save_answer(session, run_id=run_id, kind=phase, unit=unit, content_key=key,
                                       value=value, model_identity={"model": job.pinned_model,
                                       "connection_revision_id": job.connection_revision_id,
                                       "provider_mode": job.provider_mode,
                                       "calls": [row["call_id"] for row in responses.values()]})
                self._repo.update_unit(session, unit["stage_ai_unit_id"], payload=unit["payload"], state="completed", job_id=job_id)
            return Yielded()
        except (StageAiValidationError, ValueError):
            reason = "stage_ai_answer_invalid" if "unit" in locals() else "stage_ai_source_invalid"
            return self._failed(item, run_id, locals().get("unit"), jobs, locals().get("job_id"), reason)
        except DomainError as error:
            if error.code in {ErrorCode.STALE_ATTEMPT, ErrorCode.EXECUTION_TOKEN_INVALID}:
                return Yielded()
            if error.code is ErrorCode.CONFLICT:
                reason = "stage_ai_input_stale"
            else:
                reason = "stage_ai_dependency_unavailable"
            if error.code is ErrorCode.NOT_FOUND:
                return Failed(reason)
            return self._failed(item, run_id, locals().get("unit"), jobs, locals().get("job_id"), reason)

    def _fail_in(self, session, unit, jobs, job_id, reason):
        self._repo.update_unit(session, unit["stage_ai_unit_id"], payload=unit["payload"],
                               state="failed", reason=reason, job_id=job_id)
        jobs.fail(session, job_id, reason)
        return Failed(reason)
