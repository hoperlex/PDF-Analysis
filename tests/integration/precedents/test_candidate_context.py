"""Warm V2 context from real human decisions/capture and imported deterministic vectors.

Only PostgreSQL is used. No encoder, LLM, external storage or production state is
touched; the shared fixture rolls back every row, including operator-like events.
"""
from __future__ import annotations

from dataclasses import replace
from copy import deepcopy
import hashlib
import json
import struct
from types import SimpleNamespace

import pytest
from sqlalchemy import event, text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.analysis.extended.flow_repair import build_flow_repair_request, build_flow_review_request
from auditmanager.analysis.public import CostMeter, ModelResponse, ProviderConfig, ProviderMode
from auditmanager.bootstrap.adapters import MemoryCaptureAssembler
from auditmanager.decisions import record_decision
from auditmanager.decisions.public import register_decision_recorded, registered_decision_recorded
from auditmanager.decision_memory.public import COMMENT_LOCK_PREFIX, STATUS_LOCK_PREFIX, withdraw_case
from auditmanager.precedents.public import PrecedentSettingService, candidate_context_receipt, candidate_context_request
from auditmanager.precedents.candidate_context import MAX_CHARACTERS
from auditmanager.precedents.vectors import repository as vectors
from auditmanager.precedents.vectors.intents import EMBEDDING_PROFILE, MODEL_REVISION, EncodedVector
from auditmanager.runs.extended_review import _call
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import AttemptId, DecisionMemoryStatusEventId, FindingObservationId, FindingUid, JobId, ModelCallId, RunId
from auditmanager.storage.public import derive_blob_id
from tests.integration.precedents.test_decision_records_the_mark import capture  # noqa: F401 - fixture
from tests.integration.precedents.test_precedent_pass import axis, seed_run, session  # noqa: F401 - fixture

WORDS = "Установленная и расчётная мощности ВРУ-2 различаются."
RECOMMENDATION = "Привести в соответствие."
HUMAN_REASON = "Это разные режимы; проверено инженером по полной схеме."
HUMAN_COMMENT = "Нельзя сравнивать установленную нагрузку с расчётной."


def _setting(sessions: sessionmaker[Session], actor: str, enabled: bool) -> None:
    PrecedentSettingService(sessions, roles_of=lambda _s, _u: frozenset({"admin"})).append_precedent_setting(
        setting_name="critic_context", value={"enabled": enabled}, user_uid=actor,
        idempotency_key=f"candidate-context-{enabled}")


@pytest.fixture
def history(session: Session, capture, journalled_sessions: sessionmaker[Session], admin_uid: str, request: pytest.FixtureRequest) -> SimpleNamespace:
    _setting(journalled_sessions, admin_uid, True)
    options = getattr(request, "param", {})
    old = seed_run(session, [WORDS], section=options.get("section", "AR"))
    observation = session.execute(text("SELECT canonical_observation_id FROM finding WHERE finding_uid = :f"), {"f": old.findings[0]}).scalar_one()
    before = registered_decision_recorded()
    if "data_class" in options:
        geometry = SimpleNamespace(evidence_boxes_in=lambda *_: {}, portal_crops_in=lambda *_: ())
        register_decision_recorded(MemoryCaptureAssembler(geometry=geometry, data_class=options["data_class"]))
    try:
        record_decision(session, finding_uid=old.findings[0], finding_observation_id=observation,
            event_type="reject", comment=HUMAN_REASON, author_label="Инженер", author_user_uid=None)
        record_decision(session, finding_uid=old.findings[0], finding_observation_id=observation,
            event_type="comment", comment=HUMAN_COMMENT, author_label="Инженер", author_user_uid=None)
    finally:
        register_decision_recorded(before)
    case_id = session.execute(text("SELECT case_id FROM decision_memory_case WHERE origin_observation_id = :o"), {"o": observation}).scalar_one()
    current = RunId.new().value
    current_scope = old if options.get("section", "AR") == "AR" else seed_run(session, [], section="AR")
    session.execute(text("""
        INSERT INTO audit_run (run_id, project_uid, version_uid, state, analysis_profile_id, prompt_bundle_id, provider_mode, frozen_input_digest)
        SELECT :new, project_uid, version_uid, 'created', analysis_profile_id, prompt_bundle_id, provider_mode, frozen_input_digest
        FROM audit_run WHERE run_id = :old
    """), {"new": current, "old": current_scope.run_id})
    for state in ("queued", "running"):
        session.execute(text("UPDATE audit_run SET state = :s WHERE run_id = :r"), {"s": state, "r": current})
    return SimpleNamespace(old=old, case_id=case_id, observation=observation, current=current, actor=admin_uid)


def _import(session: Session) -> None:
    assert vectors.add_intents_for_new_cases(session) >= 1
    intents = vectors.pending_intent_texts(session)
    values = tuple(axis(0))
    digest = hashlib.sha256(struct.pack("!1024f", *values)).hexdigest()
    imported = vectors.import_vectors(session,
        vectors=[EncodedVector(input_digest, digest, values) for input_digest in sorted({entry.input_sha256 for entry in intents})],
        over_limit=(), rejected=(), missing=())
    assert imported.done == len(intents)


def _request(history: SimpleNamespace, *, copies: int = 1, **overrides):
    item = {"input_id": "xobs_current", "title": "Мощность ВРУ-2", "description": WORDS,
        "source_ids": ["text-1"], "norm_assessment": None, "structural_checks": {},
        "category": "dimensions", "finding_text": WORDS, "recommendation_text": RECOMMENDATION, **overrides}
    items = [item] if copies == 1 else [{**item, "input_id": f"xobs_current_{index}"} for index in range(copies)]
    return build_flow_review_request(model_id="claude-opus-5", run_id=history.current, section="AR", items=items,
        sources=[{"source_id": "text-1", "kind": "text", "quote": WORDS, "page_number": 1}],
        context={"complete": True, "sources": []}, image_ids=[])


def _data(request):
    return json.loads(request.body["messages"][0]["content"])["human_reference_data"]


def test_new_running_v2_request_contains_a_real_past_human_reason_and_comment(session: Session, history: SimpleNamespace) -> None:
    _import(session)
    original = _request(history)
    prepared = candidate_context_request(session, run_id=history.current, request=original)
    data = _data(prepared)
    assert data["status"] == "provided" and data["inputs"][0]["reason"] == "provided"
    assert data["cases"][0]["human_verdict"] == "rejected"
    assert data["cases"][0]["reason"] == HUMAN_REASON
    assert data["cases"][0]["comments"][0]["comment"] == HUMAN_COMMENT
    assert prepared.request_sha256 != original.request_sha256
    assert candidate_context_request(session, run_id=history.current, request=prepared).body == prepared.body
    receipt = candidate_context_receipt(prepared)
    assert receipt["case_bindings"][0]["case_id"] == history.case_id
    assert HUMAN_REASON not in json.dumps(receipt, ensure_ascii=False)
    assert HUMAN_COMMENT not in json.dumps(receipt, ensure_ascii=False)
    assert session.execute(text("SELECT state FROM audit_run WHERE run_id=:r"), {"r": history.current}).scalar_one() == "running"
    assert session.execute(text("SELECT count(*) FROM finding WHERE allocated_by_run_id=:r"), {"r": history.current}).scalar_one() == 0
    assert session.execute(text("SELECT count(*) FROM decision_memory_probe WHERE run_id=:r"), {"r": history.current}).scalar_one() == 0


@pytest.mark.parametrize("change", [None, "finding_text", "recommendation_text", "category"])
def test_cold_or_changed_full_view_never_falls_back_to_similar_words(session: Session, history: SimpleNamespace, change: str | None) -> None:
    overrides = {}
    if change is not None:
        _import(session)
        overrides[change] = {"finding_text": WORDS + " Требуется сверка.", "recommendation_text": "Обсудить с инженером.", "category": "layout"}[change]
    prepared = candidate_context_request(session, run_id=history.current, request=_request(history, **overrides))
    data = _data(prepared)
    assert data["cases"] == []
    assert data["inputs"][0]["reason"] == "query_vector_unavailable"
    assert HUMAN_REASON not in json.dumps(data, ensure_ascii=False)


@pytest.mark.parametrize("field,value", [("embedding_profile", "other-model-v1"), ("model_revision", "0" * 40),
    ("view_kind", "evidence_v1"), ("input_sha256", "f" * 64)])
def test_incompatible_warm_vectors_are_not_reused(session: Session, history: SimpleNamespace, field: str, value: str) -> None:
    vectors.add_intents_for_new_cases(session)
    intent = vectors.pending_intent_texts(session)[0]
    row = {"case_id": history.case_id, "view_kind": "finding_v1", "embedding_profile": EMBEDDING_PROFILE,
        "model_revision": MODEL_REVISION, "input_sha256": intent.input_sha256, "embedding_sha256": "e" * 64,
        "vector": "[" + ",".join(str(x) for x in axis(0)) + "]", field: value}
    session.execute(text("""
        INSERT INTO decision_memory_embedding (case_id, revision, view_kind, embedding_profile, model_revision, input_sha256, embedding_sha256, embedding)
        VALUES (:case_id, 1, :view_kind, :embedding_profile, :model_revision, :input_sha256, :embedding_sha256, CAST(:vector AS vector))
    """), row)
    assert _data(candidate_context_request(session, run_id=history.current, request=_request(history)))["inputs"][0]["reason"] == "query_vector_unavailable"


def test_machine_input_without_canonical_publication_fields_is_explicitly_unavailable(session: Session, history: SimpleNamespace) -> None:
    _import(session)
    data = _data(candidate_context_request(session, run_id=history.current, request=_request(history, category="")))
    assert data["cases"] == [] and data["inputs"][0]["reason"] == "canonical_query_unavailable"


@pytest.mark.parametrize("history", [{"section": "GP"}, {"data_class": "real"}], indirect=True)
def test_foreign_section_and_data_class_do_not_supply_a_query_vector_or_words(session: Session, history: SimpleNamespace) -> None:
    _import(session)
    data = _data(candidate_context_request(session, run_id=history.current, request=_request(history)))
    assert data["cases"] == [] and data["inputs"][0]["reason"] == "query_vector_unavailable"
    assert HUMAN_REASON not in json.dumps(data, ensure_ascii=False)


def test_a_case_of_this_run_does_not_supply_its_own_reference(session: Session, history: SimpleNamespace) -> None:
    _import(session)
    current = SimpleNamespace(current=history.old.run_id)
    data = _data(candidate_context_request(session, run_id=current.current, request=_request(current)))
    assert data["cases"] == [] and data["inputs"][0]["reason"] == "query_vector_unavailable"


@pytest.mark.parametrize("operation", ["withdraw", "forget"])
def test_repreparing_an_unsent_body_removes_a_withdrawn_or_forgotten_case(session: Session, history: SimpleNamespace, operation: str) -> None:
    _import(session)
    prepared = candidate_context_request(session, run_id=history.current, request=_request(history))
    assert _data(prepared)["cases"]
    if operation == "withdraw":
        withdraw_case(session, case_id=history.case_id, reason_code="wrong_decision", actor_user_uid=history.actor)
    else:
        # The forget fence is the tombstone: it must hide cached words even before
        # physical content deletion in the same transaction completes.
        session.execute(text("""
            INSERT INTO decision_memory_status_event (status_event_id, case_id, kind, reason_code, actor_user_uid,
                owner_permission_ref, forgotten_content_sha256)
            SELECT :id, case_id, 'forget', 'test_data', :actor, 'isolated context regression', content_sha256
            FROM decision_memory_case WHERE case_id=:case
        """), {"id": DecisionMemoryStatusEventId.new().value, "actor": history.actor, "case": history.case_id})
    fresh = candidate_context_request(session, run_id=history.current, request=prepared)
    assert _data(fresh)["cases"] == []
    assert HUMAN_REASON not in json.dumps(fresh.body, ensure_ascii=False)
    assert HUMAN_COMMENT not in json.dumps(fresh.body, ensure_ascii=False)
    assert fresh.request_sha256 != prepared.request_sha256


def test_latest_actual_vote_and_new_comment_change_the_reference_without_reencoding(session: Session, history: SimpleNamespace) -> None:
    _import(session)
    before = candidate_context_request(session, run_id=history.current, request=_request(history))
    record_decision(session, finding_uid=history.old.findings[0], finding_observation_id=history.observation,
        event_type="accept", comment="Проверены одинаковые режимы; замечание принято.", author_label="Инженер", author_user_uid=None)
    record_decision(session, finding_uid=history.old.findings[0], finding_observation_id=history.observation,
        event_type="comment", comment="Дополнительная сверка согласована.", author_label="Инженер", author_user_uid=None)
    after = candidate_context_request(session, run_id=history.current, request=before)
    assert _data(after)["cases"][0]["human_verdict"] == "accepted"
    assert _data(after)["cases"][0]["comments"][0]["comment"] == "Дополнительная сверка согласована."
    assert candidate_context_receipt(after)["context_sha256"] != candidate_context_receipt(before)["context_sha256"]
    assert after.request_sha256 != before.request_sha256


def test_new_repair_dispatch_refreshes_context_and_preserves_the_paid_origin_hash(session: Session, history: SimpleNamespace) -> None:
    _import(session)
    prepared = candidate_context_request(session, run_id=history.current, request=_request(history))
    repair = build_flow_repair_request(prepared, rejected=[{"reason": "review_input_missing", "input_id": "xobs_current"}],
        reply_sha256="a" * 64, procedure="finding_review", missing_input_ids=["xobs_current"],
        origin_request_sha256=prepared.request_sha256)
    withdraw_case(session, case_id=history.case_id, actor_user_uid=history.actor, reason_code="wrong_decision")
    fresh = candidate_context_request(session, run_id=history.current, request=repair)
    assert _data(fresh)["cases"] == []
    assert HUMAN_REASON not in json.dumps(fresh.body, ensure_ascii=False)
    feedback = json.loads(fresh.body["messages"][-1]["content"])
    assert feedback["semantic_repair"]["origin_request_sha256"] == prepared.request_sha256


def test_disabled_switch_and_legacy_request_do_not_disclose_examples(session: Session, history: SimpleNamespace, journalled_sessions: sessionmaker[Session]) -> None:
    _import(session)
    request = _request(history)
    legacy = replace(request, idempotency_scope=f"{history.current}:substantive-review:legacy")
    assert candidate_context_request(session, run_id=history.current, request=legacy) is legacy
    _setting(journalled_sessions, history.actor, False)
    prepared = candidate_context_request(session, run_id=history.current, request=request)
    assert _data(prepared)["inputs"][0]["reason"] == "critic_context_disabled"
    assert _data(prepared)["cases"] == []


def test_context_is_bounded_and_retains_the_status_and_human_comment_locks(session: Session, history: SimpleNamespace, engine) -> None:
    _import(session)
    prepared = candidate_context_request(session, run_id=history.current, request=_request(history))
    payload = json.loads(prepared.body["messages"][0]["content"])
    block = {key: payload[key] for key in ("human_reference_data", "human_reference_receipt")}
    assert len(json.dumps(block, ensure_ascii=False, separators=(",", ":"))) <= MAX_CHARACTERS
    with engine.begin() as other:
        for key in (COMMENT_LOCK_PREFIX + history.observation, STATUS_LOCK_PREFIX + history.case_id):
            assert other.execute(text("SELECT pg_try_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": key}).scalar_one() is False


def test_many_inputs_share_at_most_three_cases_each_within_one_global_budget(session: Session, history: SimpleNamespace) -> None:
    for _ in range(4):
        old = seed_run(session, [WORDS])
        observation = session.execute(text("SELECT canonical_observation_id FROM finding WHERE finding_uid=:f"), {"f": old.findings[0]}).scalar_one()
        record_decision(session, finding_uid=old.findings[0], finding_observation_id=observation,
            event_type="reject", comment="Основание: " + "проверено человеком; " * 150, author_label="Инженер", author_user_uid=None)
    _import(session)
    prepared = candidate_context_request(session, run_id=history.current, request=_request(history, copies=20))
    data = _data(prepared)
    assert any(item["cases"] for item in data["inputs"])
    assert all(len(item["cases"]) <= 3 for item in data["inputs"])
    assert any(case["truncated_fields"] for case in data["cases"])
    payload = json.loads(prepared.body["messages"][0]["content"])
    assert len(json.dumps({key: payload[key] for key in ("human_reference_data", "human_reference_receipt")}, ensure_ascii=False, separators=(",", ":"))) <= MAX_CHARACTERS


def test_a_grounded_canonical_member_does_not_hide_its_uncertain_group_member(session: Session, history: SimpleNamespace) -> None:
    uid, canonical, uncertain = FindingUid.new().value, FindingObservationId.new().value, FindingObservationId.new().value
    session.execute(text("""
        INSERT INTO finding (finding_uid,project_uid,version_uid,allocated_by_run_id,category,publication_policy)
        VALUES (:f,:p,:v,:r,'dimensions','reviewable-v1')
    """), {"f": uid, "p": history.old.project_uid, "v": history.old.version_uid, "r": history.old.run_id})
    for obs, grounded, words in ((canonical, True, WORDS), (uncertain, False, "Графическая часть требует дополнительной сверки.")):
        session.execute(text("""
            INSERT INTO finding_observation (finding_observation_id,run_id,finding_uid,stage_id,category,finding_text,recommendation_text,
                grounded,grounding_kind,ungrounded_reason,analysis_profile_id,prompt_bundle_id,provider_mode)
            SELECT :o,run_id,:f,'finding_merge','dimensions',:words,:recommendation,:grounded,:kind,:reason,
                analysis_profile_id,prompt_bundle_id,'recorded' FROM audit_run WHERE run_id=:r
        """), {"o": obs, "f": uid, "words": words, "recommendation": RECOMMENDATION, "grounded": grounded,
            "kind": "text_span" if grounded else "unverified", "reason": None if grounded else "source_binding_unverified", "r": history.old.run_id})
    session.execute(text("""
        INSERT INTO finding_evidence (finding_observation_id,evidence_ordinal,page_number,quote,char_start,char_end)
        VALUES (:o,0,1,'x',0,1)
    """), {"o": canonical})
    session.execute(text("UPDATE finding SET canonical_observation_id=:o WHERE finding_uid=:f"), {"o": canonical, "f": uid})
    record_decision(session, finding_uid=uid, finding_observation_id=canonical, event_type="reject", comment="Разбор всей группы.",
        author_label="Инженер", author_user_uid=None)
    case_id = session.execute(text("SELECT case_id FROM decision_memory_case WHERE origin_finding_uid=:f"), {"f": uid}).scalar_one()
    _import(session)
    data = _data(candidate_context_request(session, run_id=history.current, request=_request(history)))
    example = next(case for case in data["cases"] if case["case_id"] == case_id)
    assert example["unverified_reason"] is None
    assert example["has_unverified_sources"] is True
    assert example["source_observations"][0]["observation_id"] == uncertain
    assert example["source_observations"][0]["unverified_reason"] == "source_binding_unverified"
    assert len(example["source_observations"]) == 2


class _Dispatch:
    """Real effect/model-call rows; lease authorization and Blob transport are the two doubles.

    The job executor's lease machinery is tested separately. These tests target the
    real _call ordering, current memory reader, paid unit query and verified replay.
    """
    def __init__(self, session: Session, run_id: str):
        self.session, self.run_id = session, run_id
        self.job_id, self.attempt_id = JobId.new().value, AttemptId.new().value
        self.prepared, self.requests, self.commits = [], [], []
        self.prepare_commit_counts = []
        self.call_start_commits = 0
        self.expect_examples, self.fail_once = True, False
        self.blobs = {}
        session.execute(text("INSERT INTO job (job_id,run_id) VALUES (:j,:r)"), {"j": self.job_id, "r": run_id})
        session.execute(text("INSERT INTO attempt (attempt_id,job_id,execution_token) VALUES (:a,:j,:token)"),
            {"a": self.attempt_id, "j": self.job_id, "token": "local-context-" + self.attempt_id})
        event.listen(session, "after_commit", lambda _session: self.commits.append("commit"))
        self.adapter = SimpleNamespace(provider_mode=ProviderMode.RECORDED, complete=self.complete)
        self.binding = SimpleNamespace(adapter=self.adapter, call=None,
            config=ProviderConfig(ProviderMode.RECORDED, "claude-opus-5", 20.0, None, False))

    def require_current(self, *_):
        pass

    def prepare_provider_call(self, _session, _authority, **kwargs):
        assert len(self.commits) == self.call_start_commits + 1, "no commit between current-memory read and intent"
        self.prepare_commit_counts.append(len(self.commits))
        self.prepared.append(deepcopy(kwargs))
        call_id = ModelCallId.new().value
        self.session.execute(text("""
            INSERT INTO provider_call_effect (model_call_id,run_id,job_id,attempt_id,stage_id,provider,model_identity,provider_mode,parameters,request_sha256)
            VALUES (:id,:run,:job,:attempt,'text_analysis',:provider,:model,:mode,CAST(:params AS jsonb),:sha)
        """), {"id": call_id, "run": self.run_id, "job": self.job_id, "attempt": self.attempt_id,
            "provider": kwargs["provider"], "model": kwargs["model_identity"], "mode": kwargs["provider_mode"],
            "params": json.dumps(kwargs["parameters"]), "sha": kwargs["request_sha256"]})
        return call_id

    def complete(self, request):
        assert not self.session.in_transaction(), "the provider must run after intent commit"
        assert len(self.commits) == self.prepare_commit_counts[-1] + 1, "intent committed before provider I/O"
        if self.expect_examples:
            assert _data(request)["cases"][0]["reason"] == HUMAN_REASON
        else:
            assert _data(request)["cases"] == []
        assert self.prepared[-1]["request_sha256"] == request.request_sha256
        self.requests.append(request)
        if self.fail_once:
            self.fail_once = False
            raise DomainError(ErrorCode.ANALYSIS_FAILED, stage_id="text_analysis")
        return ModelResponse('{"reviews":[]}', "end_turn", 10, 5, 1)

    def response_received(self, call_id, response):
        self.session.execute(text("""
            UPDATE provider_call_effect SET state='response_received',response_sha256=:sha,input_tokens=:input,
                output_tokens=:output,latency_ms=:latency WHERE model_call_id=:id
        """), {"id": call_id, "sha": response.response_sha256, "input": response.input_tokens,
            "output": response.output_tokens, "latency": response.latency_ms})

    def complete_record(self, record):
        self.session.execute(text("""
            INSERT INTO model_call (model_call_id,run_id,stage_id,provider,model_identity,provider_mode,parameters,request_sha256,
                response_sha256,input_tokens,output_tokens,latency_ms,cost_micros,cost_basis,status)
            VALUES (:id,:run,'text_analysis',:provider,:model,:mode,CAST(:params AS jsonb),:request,:response,:input,:output,:latency,:cost,:basis,:status)
        """), {"id": str(record.model_call_id), "run": self.run_id, "provider": record.provider, "model": record.model_id,
            "mode": record.provider_mode.value, "params": json.dumps(dict(record.parameters)), "request": record.request_sha256,
            "response": record.response_sha256, "input": record.input_tokens, "output": record.output_tokens,
            "latency": record.latency_ms, "cost": round(record.cost_usd * 1_000_000), "basis": record.cost_basis, "status": record.status})
        self.session.execute(text("UPDATE provider_call_effect SET state='completed',final_model_call_id=model_call_id WHERE model_call_id=:id"),
            {"id": str(record.model_call_id)})
        self.session.commit()

    def not_processed(self, call_id, error, dispatch_class):
        prepared = self.prepared[-1]
        self.session.execute(text("""
            UPDATE provider_call_effect SET state='not_processed',error_code=:error,dispatch_class=:dispatch
            WHERE model_call_id=:id
        """), {"id": call_id, "error": error.code.value, "dispatch": dispatch_class})
        self.session.execute(text("""
            INSERT INTO model_call (model_call_id,run_id,stage_id,provider,model_identity,provider_mode,parameters,request_sha256,status,error_code,cost_micros,cost_basis)
            VALUES (:id,:run,'text_analysis',:provider,:model,:mode,CAST(:params AS jsonb),:sha,'failed',:error,0,'estimated')
        """), {"id": call_id, "run": self.run_id, "provider": prepared["provider"], "model": prepared["model_identity"],
            "mode": prepared["provider_mode"], "params": json.dumps(prepared["parameters"]),
            "sha": prepared["request_sha256"], "error": error.code.value})
        self.session.commit()

    def publish(self, _role, document):
        raw = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        sha = hashlib.sha256(raw).hexdigest()
        blob_id = str(derive_blob_id(sha256=sha, size=len(raw)))
        self.blobs[blob_id] = raw
        return SimpleNamespace(blob_id=blob_id, sha256=sha, size_bytes=len(raw))

    def call(self, request, receipt=None):
        self.call_start_commits = len(self.commits)
        return _call(self.session, run_id=self.run_id, authority=SimpleNamespace(), jobs=self,
            journal=SimpleNamespace(response_received=self.response_received, complete=self.complete_record, not_processed=self.not_processed), binding=self.binding,
            request=request, phase="finding_review:substantive:0", source_sha256="a" * 64, meter=CostMeter(20.0),
            store=SimpleNamespace(read=lambda blob_id, **_kwargs: self.blobs[str(blob_id)]), publish=self.publish,
            checkpoint=lambda _point: None, dispatch_receipt=receipt)


def test_actual_call_persists_context_hash_and_replays_paid_reply_before_reading_memory(session: Session, history: SimpleNamespace, monkeypatch) -> None:
    _import(session)
    request = _request(history)
    dispatch = _Dispatch(session, history.current)
    receipt = {}
    response, replayed = dispatch.call(request, receipt)
    assert not replayed and len(dispatch.requests) == 1
    assert receipt["request_sha256"] == dispatch.requests[0].request_sha256
    assert receipt["request_sha256"] != request.request_sha256
    assert dispatch.prepared[0]["parameters"]["flow_base_request_sha256"] == request.request_sha256
    assert dispatch.prepared[0]["parameters"]["human_reference_receipt"]["case_bindings"][0]["case_id"] == history.case_id
    withdraw_case(session, case_id=history.case_id, actor_user_uid=history.actor, reason_code="wrong_decision")
    from auditmanager.precedents import public
    def forbidden_read(*_args, **_kwargs):
        raise AssertionError("paid replay must happen before any current-memory read")
    monkeypatch.setattr(public, "candidate_context_request", forbidden_read)
    second_receipt = {}
    replay, reused = dispatch.call(request, second_receipt)
    assert reused and replay == response and len(dispatch.requests) == 1 and len(dispatch.prepared) == 1
    assert second_receipt["replayed"] is True
    assert second_receipt["request_sha256"] == receipt["request_sha256"]
    assert session.execute(text("SELECT count(*) FROM model_call WHERE run_id=:r"), {"r": history.current}).scalar_one() == 1


@pytest.mark.parametrize("state", ["prepared", "outcome_unknown"])
def test_actual_call_unknown_effect_fence_precedes_context_read_and_prevents_a_second_dispatch(session: Session, history: SimpleNamespace, monkeypatch, state: str) -> None:
    request = _request(history)
    dispatch = _Dispatch(session, history.current)
    session.commit()  # this test seeds the already-registered intent without invoking _call
    call_id = dispatch.prepare_provider_call(session, None, provider="anthropic", model_identity=request.model_id,
        provider_mode="recorded", request_sha256=request.request_sha256,
        parameters={"extended_phase": "finding_review:substantive:0", "extended_source_sha256": "a" * 64,
            "flow_base_request_sha256": request.request_sha256})
    if state == "outcome_unknown":
        session.execute(text("UPDATE provider_call_effect SET state='outcome_unknown',error_code='analysis_failed' WHERE model_call_id=:id"), {"id": call_id})
    from auditmanager.precedents import public
    def forbidden_read(*_args, **_kwargs):
        raise AssertionError("unknown effect must be reconciled before reading memory or dispatching")
    monkeypatch.setattr(public, "candidate_context_request", forbidden_read)
    with pytest.raises(DomainError) as error:
        dispatch.call(request)
    assert error.value.detail_fields.get("reason") == "extended_provider_outcome_unknown"
    assert len(dispatch.prepared) == 1 and dispatch.requests == []
    assert session.execute(text("SELECT count(*) FROM provider_call_effect WHERE run_id=:r"), {"r": history.current}).scalar_one() == 1


def test_actual_call_can_retry_a_proven_not_processed_failure_with_fresh_context(session: Session, history: SimpleNamespace) -> None:
    _import(session)
    request = _request(history)
    dispatch = _Dispatch(session, history.current)
    dispatch.fail_once = True
    with pytest.raises(DomainError):
        dispatch.call(request)
    assert len(dispatch.requests) == 1
    assert session.execute(text("SELECT state FROM provider_call_effect WHERE run_id=:r"), {"r": history.current}).scalar_one() == "not_processed"
    withdraw_case(session, case_id=history.case_id, actor_user_uid=history.actor, reason_code="wrong_decision")
    dispatch.expect_examples = False
    response, replayed = dispatch.call(request)
    assert not replayed and response.output_text == '{"reviews":[]}'
    assert len(dispatch.requests) == 2 and len(dispatch.prepared) == 2
    assert dispatch.requests[0].request_sha256 != dispatch.requests[1].request_sha256
    assert _data(dispatch.requests[1])["cases"] == []
    assert session.execute(text("SELECT state FROM provider_call_effect WHERE run_id=:r ORDER BY prepared_at"), {"r": history.current}).scalars().all() == ["not_processed", "completed"]
