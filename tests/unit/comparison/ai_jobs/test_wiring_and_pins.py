"""`CMP-AI-JOBS-01`: what ties the core to the rest of the tree, container-free -- the names a lane imports, the vocabulary pinned to
the migration, the registered reasons, the reasons of the spend wrapper that pause a job, and the rule that no lane writes
``comparison_ai_job`` or the journal itself."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

from auditmanager.analysis.public import ModelRequest, ProviderMode
from auditmanager.comparison import public
from auditmanager.comparison.ai_jobs import model, service
from auditmanager.comparison.public import AiMethod, RecordedAnswers
from auditmanager.shared.errors import DomainError, ErrorCode

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "src/auditmanager"
PACKAGE = SRC / "comparison/ai_jobs"


def _migration():
    path = next((ROOT / "db/migrations/versions").glob("*_0040_comparison_ai_reports.py"))
    spec = importlib.util.spec_from_file_location("migration_0040_for_ai_jobs_pins", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# -- the names a lane imports ----------------------------------------------------------------------------------------


@pytest.mark.parametrize("name", [
    "AI_METHODS", "AiCallGroup", "AiConsentInput", "AiCounts", "AiEstimate", "AiEstimateRequest", "AiJobCommand", "AiJobRecord",
    "AiJobSpend", "AiJobView", "AiMethod", "AiMode", "AiProgress", "AiRoute", "AiScope", "AiTotals", "AiWaitingJobs",
    "AiWorkItemSpec", "ComparisonAiJobService", "RecordedAnswers", "ai_digest_of", "ai_pause_reason_of", "ai_route_missing",
    "ai_work_kind_of", "build_ai_estimate", "read_ai_route",
])
def test_the_core_is_exported_from_the_comparison_public_surface(name: str) -> None:
    assert name in public.__all__ and getattr(public, name) is not None


def test_a_method_is_a_runtime_checkable_protocol() -> None:
    class Complete:
        method = "spec"
        prompt_version = "v1"

        def counts(self, session: object, request: object) -> object: ...

        def work_items(self, session: object, job: object, mode: object) -> list[object]: ...

    class Incomplete:
        method = "spec"

    assert isinstance(Complete(), AiMethod) and not isinstance(Incomplete(), AiMethod)


# -- the vocabulary is the migration's -------------------------------------------------------------------------------


def test_the_methods_states_and_pause_reasons_are_the_migrations() -> None:
    migration = _migration()
    assert model.METHODS == migration.METHODS
    assert model.JOB_STATES == migration.JOB_STATES
    assert model.JOB_LIVE_STATES == migration.JOB_LIVE
    assert model.PAUSE_REASONS == migration.PAUSE_REASONS
    assert set(model.JOB_LIVE_STATES) | set(model.JOB_TERMINAL_STATES) == set(model.JOB_STATES)
    assert model.CONSENT_PAUSES <= set(model.PAUSE_REASONS)
    assert {model.work_kind_of(method) for method in model.METHODS} <= set(migration.WORK_KINDS_AFTER)


def test_the_registered_refusals_are_the_ones_the_seal_registered() -> None:
    registered = (ROOT / "contracts/domain/v1/error-codes.json").read_text(encoding="utf-8")
    for reason in (
        model.CONFLICT_ESTIMATE_STALE, model.CONFLICT_CEILING_JOB, model.CONFLICT_CEILING_DAY, model.CONFLICT_AI_JOB_ACTIVE,
        model.CONFLICT_AI_JOB_STATE, model.CONFLICT_NOTHING_TO_DO, model.CONSTRAINT_CONSENT_REQUIRED,
    ):
        assert reason in registered, reason


def test_the_state_commands_use_only_declared_states_and_the_dequeue_is_a_subset_of_the_cancel() -> None:
    for states in service.COMMAND_EDGES.values():
        assert set(states) <= set(model.JOB_STATES)
    assert set(service.COMMAND_EDGES["dequeue"]) <= set(service.COMMAND_EDGES["cancel"])
    assert set(service.COMMAND_EDGES["retry"]) == set(model.JOB_TERMINAL_STATES)
    assert set(service.COMMAND_EDGES["pause"]) | set(service.COMMAND_EDGES["resume"]) == set(model.JOB_LIVE_STATES)


# -- the reasons of the spend wrapper --------------------------------------------------------------------------------


def _spend_pause_reasons() -> set[str]:
    """Every reason the spend package says should pause a job: ``CallRefused(REASON, pauses_job=True)`` and ``SpendPause(REASON)``."""
    from auditmanager.comparison.spend import errors

    reasons: set[str] = set()
    for path in (ROOT / "src/auditmanager/comparison/spend").glob("*.py"):
        source = path.read_text(encoding="utf-8")
        names = re.findall(r"CallRefused\(\s*(REASON_\w+),\s*pauses_job=True\s*\)", source)
        names += re.findall(r"SpendPause\(\s*(REASON_\w+)\s*\)", source)
        reasons |= {getattr(errors, name) for name in names}
    return reasons


def test_every_reason_that_pauses_a_job_in_the_spend_wrapper_has_a_pause_reason_of_the_job() -> None:
    pausing = _spend_pause_reasons()
    assert pausing >= {"overrun", "job_ceiling", "day_ceiling", "consent_stale", "consent_required"}
    assert pausing == set(service.PAUSE_OF_SPEND_REASON), "the spend wrapper pauses for a reason the job layer does not map"
    assert set(service.PAUSE_OF_SPEND_REASON.values()) <= set(model.PAUSE_REASONS)
    assert service.pause_reason_of("connection_busy") is None and service.pause_reason_of("overrun") == "overrun"


# -- who writes what -------------------------------------------------------------------------------------------------

_WRITE = r"(?:INSERT\s+INTO|UPDATE|DELETE\s+FROM)\s+{table}\b"


def _sources(root: Path) -> dict[Path, str]:
    return {path: path.read_text(encoding="utf-8") for path in root.rglob("*.py")}


def test_only_the_cores_repository_writes_the_job_table_and_no_lane_does() -> None:
    writers = {path.relative_to(SRC).as_posix() for path, source in _sources(SRC).items()
               if re.search(_WRITE.format(table="comparison_ai_job"), source, flags=re.IGNORECASE)}
    assert writers == {"comparison/ai_jobs/repository.py"}


def test_the_core_writes_no_journal_row_and_no_attempt_and_one_kind_of_work_item_row() -> None:
    sources = _sources(PACKAGE)
    for path, source in sources.items():
        for table in ("comparison_model_call", "comparison_work_attempt", "executor_task"):
            assert not re.search(_WRITE.format(table=table), source, flags=re.IGNORECASE), (path.name, table)
        assert not re.search(r"UPDATE\s+comparison_work\b", source, flags=re.IGNORECASE), path.name
    inserts = [path.name for path, source in sources.items() if re.search(_WRITE.format(table="comparison_work"), source, flags=re.IGNORECASE)]
    assert inserts == ["repository.py"]


def test_the_core_never_calls_an_adapter() -> None:
    for path, source in _sources(PACKAGE).items():
        assert ".complete(" not in source, path.name


# -- recorded mode ---------------------------------------------------------------------------------------------------


def _request(label: str) -> ModelRequest:
    return ModelRequest(model_id="claude-opus-5", body={"model": "claude-opus-5", "messages": [{"role": "user", "content": label}]})


def test_a_recorded_answer_is_served_by_the_digest_of_the_request_and_nothing_else() -> None:
    answers = RecordedAnswers()
    question = _request("is this a pair?")
    key = answers.record(question, '{"pair": true}', input_tokens=11, output_tokens=7)
    assert key == question.request_sha256 and answers.has_answer(question)
    reply = answers.complete(question)
    assert (reply.output_text, reply.input_tokens, reply.output_tokens) == ('{"pair": true}', 11, 7)
    assert answers.calls == 1 and answers.digests == [key]
    other = _request("is this a pair? (edited)")
    assert other.request_sha256 != key and not answers.has_answer(other)


def test_a_question_with_no_recording_is_never_answered_and_never_a_call() -> None:
    answers = RecordedAnswers()
    with pytest.raises(DomainError) as missing:
        answers.complete(_request("unknown"))
    assert missing.value.code is ErrorCode.ANALYSIS_INPUT_INVALID and missing.value.detail_fields["reason"] == "recording_missing"
    assert answers.calls == 1  # the request was seen and refused


def test_a_recorded_reply_cannot_present_itself_as_live() -> None:
    answers = RecordedAnswers()
    assert answers.provider_mode is ProviderMode.RECORDED
    with pytest.raises(AttributeError):
        answers.provider_mode = ProviderMode.LIVE  # type: ignore[misc]
    with pytest.raises(AttributeError):
        RecordedAnswers._PROVIDER_MODE.value = "live"  # type: ignore[misc]


def test_the_service_refuses_a_module_set_that_is_not_one_and_a_provider_mode_that_is_not_one() -> None:
    from sqlalchemy.orm import sessionmaker

    with pytest.raises(ValueError):
        service.ComparisonAiJobService(sessionmaker(), methods=[], comparison_modules="stages")
    with pytest.raises(ValueError):
        service.ComparisonAiJobService(sessionmaker(), methods=[], provider_mode="proxy")
