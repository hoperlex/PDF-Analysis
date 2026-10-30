"""Recorded phase execution, durable chunk acceptance and response-loss fencing."""

from __future__ import annotations

import copy
import json
import threading
from types import SimpleNamespace

from auditmanager.comparison.ai_jobs.recorded import RecordedAnswers
from auditmanager.comparison.spend.model import CallRoute
from auditmanager.comparison.spend.errors import CallFailed
from auditmanager.comparison.stage_ai.runtime import StageAiRuntime
from auditmanager.comparison.stage_ai.validation import digest
from auditmanager.comparison.work.model import Failed, Yielded


def uid(prefix, number):
    return f"{prefix}_{number:026d}"


def snapshot(size=1):
    fragments, differences = [], []
    for number in range(1, size + 1):
        for side, profile, offset, value in (("left", 1, 0, "10"), ("right", 2, 1, "20")):
            fragment_id = uid("stf", number * 2 + offset)
            text = f"Нагрузка {value} кВт"
            fragments.append({"stage_text_fragment_id": fragment_id, "page_profile_id": uid("cpr", profile),
                              "side": side, "normalised_text": text, "content_key": digest([fragment_id, text]),
                              "box_anchor": {"x0": 10, "top": 10 + number, "x1": 80, "bottom": 18 + number},
                              "version_uid": uid("ver", profile)})
        differences.append({"stage_text_difference_id": uid("std", number),
                            "left_fragment_id": uid("stf", number * 2),
                            "right_fragment_id": uid("stf", number * 2 + 1),
                            "status": "changed", "content_key": digest(["diff", number])})
    return {"stage_pair_id": uid("stp", 1), "stage_link_revision_id": uid("slk", 1),
            "project_uid": uid("prj", 1), "document_uid": uid("doc", 1),
            "links": [{"stage_link_item_id": uid("sli", 1), "left_profile_id": uid("cpr", 1),
                       "right_profile_id": uid("cpr", 2), "relation": "paired", "confidence": "manual"}],
            "all_profiles": [{"profile_id": uid("cpr", n), "version_uid": uid("ver", n)} for n in (1, 2)],
            "fragments": fragments, "differences": differences, "hints": []}


class Session:
    def commit(self): pass
    def rollback(self): pass
    def close(self): pass


class Repo:
    def __init__(self, source):
        self.source = source
        self.units = {}
        self.answers = {}
        self.priors = {}
        self.pauses = []

    def run(self, session, run_id):
        return {"project_uid": self.source["project_uid"], "comparison_ai_job_id": uid("cai", 1)}

    def unit(self, session, *, run_id, kind, group_id, source_sha256, payload, job_id=None):
        key = (run_id, kind, group_id, source_sha256)
        if key not in self.units:
            self.units[key] = {"stage_ai_unit_id": uid("saunit", len(self.units) + 1),
                               "stage_chain_run_id": run_id, "kind": kind, "group_id": group_id,
                               "source_sha256": source_sha256, "payload": copy.deepcopy(payload), "state": "queued"}
        unit = self.units[key]
        if unit["payload"]["content_key"] != payload["content_key"]:
            unit.update(payload=copy.deepcopy(payload), state="queued")
        return copy.deepcopy(unit)

    def update_unit(self, session, unit_id, *, payload, state, reason=None, job_id=None):
        unit = next(u for u in self.units.values() if u["stage_ai_unit_id"] == unit_id)
        unit.update(payload=copy.deepcopy(payload), state=state, failure_reason=reason)

    def answer(self, session, *, run_id, kind, content_key):
        return self.answers.get((run_id, kind, content_key))

    def latest_answers(self, session, *, run_id, kind):
        return {row["group_id"]: row for (run, phase, _key), row in self.answers.items()
                if run == run_id and phase == kind}

    def save_answer(self, session, *, run_id, kind, unit, content_key, value, model_identity):
        field = {"review": "decisions", "classify": "cards", "synthesize": "result"}[kind]
        self.answers[(run_id, kind, content_key)] = {"group_id": unit["group_id"],
            "source_sha256": unit["source_sha256"], field: copy.deepcopy(value), "model_identity": model_identity}

    def prior_call(self, session, *, job_id, request_sha256):
        return self.priors.get(request_sha256)

    def not_checked_graphics(self, session, *, run_id, snapshot): return 1
    def pause_run(self, session, run_id, reason): self.pauses.append(reason)


class Jobs:
    def __init__(self):
        self.state = "running"
        self.failures = []
        self.finished = []
        self.record = SimpleNamespace(pinned_model="recorded-pin", connection_revision_id=uid("ecr", 1), provider_mode="recorded")

    def mark_running(self, session, job_id): return self.state
    def job(self, session, job_id): return self.record
    def consent_for_calls(self, session, job_id): return None
    def fail(self, session, job_id, reason): self.failures.append(reason)
    def pause_for_spend(self, session, job_id, reason): self.state = "paused"
    def pause_system(self, session, job_id, reason): self.state = "paused"
    def complete_if_drained(self, session, job_id, *, excluding_work_id): self.finished.append(excluding_work_id)


class Caller:
    def __init__(self, repo, adapter):
        self.repo, self.adapter = repo, adapter
        self.calls = 0
        self.pause_next = False
        self.transform = lambda _source, answer, _number: answer

    def call(self, item, route, request, *, estimate, consent):
        self.calls += 1
        source = json.loads(request.body["messages"][0]["content"].split("\nINPUT\n", 1)[1])
        if "chunk_id" in source:
            answer = {"group_id": source["group_id"], "chunk_id": source["chunk_id"],
                      "source_sha256": source["source_sha256"], "decisions": [{
                          "left_fragment_ids": row["left_fragment_ids"], "right_fragment_ids": row["right_fragment_ids"],
                          "status": "CHANGED", "confidence": "high", "summary": "Нагрузка 10 кВт → 20 кВт",
                          "reason": "Изменён исходный текст.", "actual_right_profile_ids": [],
                      } for row in source["items"]]}
        elif "cards" not in source:
            answer = {"group_id": source["group_id"], "source_sha256": source["source_sha256"],
                      "cards": [{"class": "PROJECT_CHANGE", "category": "electrical_load",
                                 "title": "Изменена нагрузка", "system": "electrical",
                                 "evidence_ids": [row["evidence_id"]]} for row in source["atomic_evidence"]]}
        else:
            answer = {"group_id": source["group_id"], "source_sha256": source["source_sha256"],
                      "evidence_ids": [row["evidence_id"] for row in source["atomic_evidence"]],
                      "decision": "INSUFFICIENT_CONTEXT", "type": "UNRESOLVED_HIGH_LEVEL_CHANGE",
                      "title": "Требуется проверка", "reason": "Контекста недостаточно."}
        answer = self.transform(source, answer, self.calls)
        self.adapter.record(request, json.dumps(answer, ensure_ascii=False))
        response = self.adapter.complete(request)
        self.repo.priors[request.request_sha256] = {"state": "completed", "comparison_model_call_id": uid("cmc", self.calls)}
        pause = SimpleNamespace(reason="comparison_estimate_overrun") if self.pause_next else None
        self.pause_next = False
        return SimpleNamespace(response=response, call_id=uid("cmc", self.calls), pause=pause)


class Runtime(StageAiRuntime):
    def _checked(self, session, item, run_id):
        item.require_current(session)
        return self.test_run, self._repo.source


def scene(size=1):
    source = snapshot(size)
    repo, jobs, adapter = Repo(source), Jobs(), RecordedAnswers()
    caller = Caller(repo, adapter)
    route = CallRoute(adapter, "recorded-pin", unmetered=True)
    runtime = Runtime(Session, repository=repo, caller=caller,
                      jobs_factory=lambda _method: jobs,
                      routes=SimpleNamespace(route_for=lambda _session, _job: route))
    runtime.test_run = {"comparison_ai_job_id": uid("cai", 1)}
    item = SimpleNamespace(project_uid=uid("prj", 1), work_id=uid("cq", 1),
                           payload={"ai_job_id": uid("cai", 1)}, lease_lost=threading.Event(),
                           cancelled=threading.Event(), require_current=lambda _session: None)
    return runtime, item, repo, jobs, caller


def phase_to_end(runtime, item, phase):
    for _ in range(12):
        outcome = runtime.advance(item, run_id=uid("crn", 1), phase=phase)
        if isinstance(outcome, dict) or isinstance(outcome, Failed):
            return outcome
        assert isinstance(outcome, Yielded)
    raise AssertionError("phase failed to finish")


def test_recorded_three_phase_runtime_replays_saved_units_without_resend() -> None:
    runtime, item, repo, jobs, caller = scene()
    original = copy.deepcopy(repo.source["differences"])
    for phase in ("review", "classify", "synthesize"):
        assert phase_to_end(runtime, item, phase)["completed"] == 1
    assert caller.calls == 3
    for phase in ("review", "classify", "synthesize"):
        assert isinstance(runtime.advance(item, run_id=uid("crn", 1), phase=phase), dict)
    assert caller.calls == 3 and len(repo.answers) == 3
    assert repo.source["differences"] == original
    assert jobs.finished == [item.work_id, item.work_id]


def test_review_chunks_do_not_publish_partial_group() -> None:
    runtime, item, repo, _jobs, caller = scene(41)
    assert isinstance(runtime.advance(item, run_id=uid("crn", 1), phase="review"), Yielded)
    assert caller.calls == 1 and not repo.answers
    assert isinstance(runtime.advance(item, run_id=uid("crn", 1), phase="review"), Yielded)
    assert caller.calls == 2 and not repo.answers
    assert isinstance(runtime.advance(item, run_id=uid("crn", 1), phase="review"), Yielded)
    assert caller.calls == 2 and len(repo.answers) == 1
    stored = next(iter(repo.answers.values()))
    assert len(stored["decisions"]) == 41


def test_prior_paid_request_without_saved_reply_is_never_sent_again() -> None:
    runtime, item, repo, jobs, caller = scene()
    bundles = runtime._bundles(Session(), run_id=uid("crn", 1), snapshot=repo.source,
                                phase="review", model="recorded-pin")
    from auditmanager.comparison.stage_ai.runtime import request_for_plan
    request = request_for_plan(bundles[0][1][0])
    repo.priors[request.request_sha256] = {"state": "completed", "comparison_model_call_id": uid("cmc", 1)}
    outcome = runtime.advance(item, run_id=uid("crn", 1), phase="review")
    assert isinstance(outcome, Failed) and outcome.reason == "stage_ai_response_lost"
    assert caller.calls == 0 and jobs.failures == ["stage_ai_response_lost"]


def test_pause_keeps_response_and_resume_uses_it_without_another_call() -> None:
    runtime, item, repo, jobs, caller = scene()
    caller.pause_next = True
    assert isinstance(runtime.advance(item, run_id=uid("crn", 1), phase="review"), Yielded)
    assert caller.calls == 1 and jobs.state == "paused" and not repo.answers
    jobs.state = "running"
    assert phase_to_end(runtime, item, "review")["completed"] == 1
    assert caller.calls == 1 and repo.answers


def test_constructor_is_registry_safe_without_dependencies() -> None:
    runtime = StageAiRuntime(None)
    assert runtime._sessions is None


def test_missing_prerequisite_fails_shared_job_before_unit_creation() -> None:
    runtime, item, repo, jobs, caller = scene()
    outcome = runtime.advance(item, run_id=uid("crn", 1), phase="classify")
    assert isinstance(outcome, Failed) and outcome.reason == "stage_ai_source_invalid"
    assert jobs.failures == ["stage_ai_source_invalid"]
    assert caller.calls == 0 and not repo.units


def test_durable_context_then_coverage_keeps_every_reply_and_publishes_once() -> None:
    runtime, item, repo, jobs, caller = scene(2)

    def response(_source, answer, number):
        if number == 1:
            answer["decisions"] = []
            answer["context_requests"] = [{"kind": "mark", "value": "Нагрузка", "side": "right"}]
        elif number == 2:
            answer["decisions"] = answer["decisions"][:1]
        return answer

    caller.transform = response
    assert phase_to_end(runtime, item, "review")["completed"] == 1
    assert caller.calls == 3 and len(repo.answers) == 1 and not jobs.failures
    progress = next(iter(repo.units.values()))["payload"]
    saved = next(iter(progress["responses"].values()))
    assert [row["step"] for row in saved["history"]] + [saved["step"]] == ["main", "context", "coverage"]
    matches = saved["history"][1]["context"][0]["matches"]
    assert len(matches) == 2 and all(match["side"] == "right" for match in matches)
    assert len({row["request_sha256"] for row in saved["history"] + [saved]}) == 3
    assert phase_to_end(runtime, item, "review")["completed"] == 1 and caller.calls == 3


def test_repeated_model_context_request_fails_without_third_call() -> None:
    runtime, item, repo, jobs, caller = scene()
    caller.transform = lambda _source, answer, _number: answer | {
        "context_requests": [{"kind": "rows", "value": "Нагрузка", "side": "both"}]}
    outcome = phase_to_end(runtime, item, "review")
    assert isinstance(outcome, Failed) and caller.calls == 2 and not repo.answers
    assert jobs.failures == ["stage_ai_answer_invalid"]


def test_coverage_pass_is_attempted_once_then_group_fails_atomically() -> None:
    runtime, item, repo, jobs, caller = scene()
    caller.transform = lambda _source, answer, _number: answer | {"decisions": []}
    outcome = phase_to_end(runtime, item, "review")
    assert isinstance(outcome, Failed) and caller.calls == 2 and not repo.answers
    assert jobs.failures == ["stage_ai_answer_invalid"]


def test_one_technical_retry_is_shared_by_main_and_context() -> None:
    runtime, item, repo, jobs, caller = scene()
    original = caller.call
    attempts = []

    def call(*args, **kwargs):
        attempts.append(1)
        if len(attempts) in {1, 3}:
            raise CallFailed("dependency_unavailable", call_id=uid("cmc", len(attempts)), retry_safe=True)
        return original(*args, **kwargs)

    caller.call = call
    caller.transform = lambda _source, answer, _number: answer | {
        "context_requests": [{"kind": "rows", "value": "Нагрузка", "side": "both"}]}
    outcome = phase_to_end(runtime, item, "review")
    assert isinstance(outcome, Failed) and len(attempts) == 3 and caller.calls == 1
    assert not repo.answers and jobs.failures == ["stage_ai_call_failed"]


def test_rate_limit_waits_are_durable_and_bounded_without_consuming_technical_retry() -> None:
    runtime, item, repo, jobs, caller = scene()
    now = [1000.0]
    runtime._now = lambda: now[0]
    attempts = []

    def limited(_item, _route, request, **_kwargs):
        call_id = uid("cmc", len(attempts) + 1)
        attempts.append(call_id)
        repo.priors[request.request_sha256] = {"state": "failed", "comparison_model_call_id": call_id}
        raise CallFailed("dependency_unavailable", call_id=call_id, retry_safe=True,
                         dispatch_class="rate_limited", provider_failure_kind="rate_limit")

    caller.call = limited
    for number, delay in enumerate((20, 60, 120, 300, 600), 1):
        outcome = runtime.advance(item, run_id=uid("crn", 1), phase="review")
        assert isinstance(outcome, Yielded) and outcome.delay_seconds == delay
        assert len(attempts) == number
        assert isinstance(runtime.advance(item, run_id=uid("crn", 1), phase="review"), Yielded)
        assert len(attempts) == number
        now[0] += delay
    outcome = runtime.advance(item, run_id=uid("crn", 1), phase="review")
    assert isinstance(outcome, Failed) and outcome.reason == "stage_ai_rate_limit"
    assert len(attempts) == 6 and jobs.failures == ["stage_ai_rate_limit"]
    assert not next(iter(repo.units.values()))["payload"]["technical_retries"]


def test_auth_refusal_pauses_without_automatic_resend() -> None:
    runtime, item, repo, jobs, caller = scene()
    attempts = []

    def refused(_item, _route, request, **_kwargs):
        attempts.append(1)
        repo.priors[request.request_sha256] = {"state": "failed", "comparison_model_call_id": uid("cmc", 1)}
        raise CallFailed("dependency_credential_refused", call_id=uid("cmc", 1),
                         dispatch_class="definite_refusal", provider_failure_kind="auth")

    caller.call = refused
    assert isinstance(runtime.advance(item, run_id=uid("crn", 1), phase="review"), Yielded)
    assert jobs.state == "paused" and repo.pauses == ["auth"]
    jobs.state = "running"
    outcome = runtime.advance(item, run_id=uid("crn", 1), phase="review")
    assert isinstance(outcome, Failed) and outcome.reason == "stage_ai_response_lost" and len(attempts) == 1
