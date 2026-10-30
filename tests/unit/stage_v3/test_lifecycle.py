"""One-call yields and fresh consent windows through the actual runtime branch."""
import copy
import sys
from types import SimpleNamespace
from datetime import datetime, timezone

from auditmanager.comparison.stage_v3 import bridge
from auditmanager.comparison.stage_v3.mode import ENGINE
from auditmanager.comparison.work.model import Failed
from tests.unit.comparison.stage_ai.test_runtime import uid, scene
from tests.unit.stage_v3.recorded_fixture import synthetic_response
from tests.unit.stage_v3.test_procedures import snapshot, run_fixture


def test_durable_runtime_four_calls_three_fresh_windows_and_saved_replay(monkeypatch):
    runtime, item, repo, jobs, _caller = scene()
    for index, row in enumerate(repo.source["all_profiles"]):
        row.update(side="left" if index == 0 else "right", page_number=1)
    for row in repo.source["fragments"]:
        row["created_at"] = datetime.now(timezone.utc)
    runtime.test_run["engine"] = ENGINE
    repo.run = lambda _session, _run: runtime.test_run
    jobs.record.consent_no = 1
    calls = []

    class Caller:
        def call(self, _item, _route, request, **_kwargs):
            response, payload = synthetic_response(request)
            calls.append(payload["_experimental_procedure"])
            identity = uid("cmc", len(calls))
            repo.priors[request.request_sha256] = {"state": "completed", "comparison_model_call_id": identity}
            return SimpleNamespace(response=response, call_id=identity, pause=None)

    runtime._caller = Caller()
    monkeypatch.setattr(bridge, "results", lambda _s, _r: {row["group_id"]: row["payload"]["v3_result"]
        for row in repo.units.values() if row["state"] == "completed" and "v3_result" in row["payload"]})
    original_failed = runtime._failed

    def fail(*args, **kwargs):
        error = sys.exception()
        if error is not None:
            raise error
        return original_failed(*args, **kwargs)

    runtime._failed = fail
    pauses = 0
    for phase in ("review", "classify", "synthesize"):
        for _ in range(30):
            before = len(calls)
            result = runtime.advance(item, run_id=uid("crn", 1), phase=phase)
            assert not isinstance(result, Failed), result
            assert len(calls) <= before + 1
            if jobs.state == "paused":
                assert len(calls) == before
                pauses += 1
                jobs.record.consent_no += 1
                jobs.state = "running"
            if isinstance(result, dict):
                break
        else:
            raise AssertionError((phase, "did not finish"))
    assert calls == ["mapper", "miner", "dedupe", "verify"]
    assert pauses == 3
    final = [row for row in repo.answers.values() if row["group_id"] == "v3:final:cards"]
    assert final[0]["cards"][0]["experimental"]["parameters"][0]["verification"]["verdict"] == "CONFIRMED"
    before = copy.deepcopy(repo.source["differences"])
    for phase in ("review", "classify", "synthesize"):
        assert isinstance(runtime.advance(item, run_id=uid("crn", 1), phase=phase), dict)
    assert len(calls) == 4 and repo.source["differences"] == before


def test_experimental_container_readers_validate_sealed_public_dtos():
    from auditmanager.api.schemas.models import StageAiReview, StageAiClassification, StageAiSynthesis
    from auditmanager.comparison.stage_v3 import procedures as p
    source = snapshot()
    for number, row in enumerate(source["fragments"], 1):
        row["stage_text_fragment_id"] = uid("stf", number)
    saved, _ = run_fixture(source)
    common = {"run_id": uid("crn", 1), "unit_id": uid("saunit", 1), "content_key": "a" * 64,
              "model_identity": {"model": "recorded"}, "created_at": datetime.now(timezone.utc)}
    for kind, schema, identity, field, value in (
        ("review", StageAiReview, "sarev", "decisions", [{"experimental_mapper": saved["v3:mapper:all"]}]),
        ("classify", StageAiClassification, "sacls", "cards", p.canonical_cards(source, saved)),
        ("synthesize", StageAiSynthesis, "sasyn", "result", {"experimental_procedure": "verify", "result": {}}),
    ):
        id_field = {"review": "review_id", "classify": "classification_id", "synthesize": "synthesis_id"}[kind]
        item = common | {id_field: uid(identity, 1), field: value}
        if kind != "synthesize":
            item.update(group_id="v3:test:all", source_sha256="b" * 64)
        projected = bridge.public_answer(kind, item, group_id="v3:test:all", source_sha256="b" * 64)
        schema.model_validate(projected)
        assert projected["model_identity"]["experimental"]["result"] == value
