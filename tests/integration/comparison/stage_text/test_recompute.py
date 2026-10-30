"""A keyed Stage Text request, one work item and a lease-fenced worker result."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.comparison.profile.models import PageProfileData, PageProfileRow, Word
from auditmanager.comparison.stage_text.handler import StageTextRecomputeHandler
from auditmanager.comparison.stage_text.read import StageTextReadService
from auditmanager.comparison.stage_text.recompute import StageTextRecomputeService, WORK_KIND
from auditmanager.comparison.work.model import Completed, Failed, WorkDependencies
from auditmanager.comparison.work.repository import ComparisonWorkRepository
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import new_ulid
from auditmanager.workers.public import WorkerRegistry
from tests.integration.comparison.stage_text.test_store import _command, _seed


class _Profiles:
    def __init__(self, profiles: dict[str, PageProfileData]) -> None:
        self.profiles = profiles

    def read_page_profile(self, profile_id: str) -> PageProfileData:
        return self.profiles[profile_id]


def _profiles(session: Session, left: str, right: str, *, empty: bool) -> _Profiles:
    rows = session.execute(text(
        "SELECT comparison_page_profile_id, version_uid FROM comparison_page_profile "
        "WHERE comparison_page_profile_id = ANY(CAST(:ids AS text[]))"
    ), {"ids": [left, right]}).all()
    result = {}
    for profile_id, version_uid in rows:
        value = "Нагрузка 10 кВт" if profile_id == left else "Нагрузка 20 кВт"
        words = () if empty else (Word(10, 10, 70, 18, value),)
        profile = PageProfileData(
            row=PageProfileRow(str(profile_id), str(version_uid), 1, "1" * 64,
                               "test", "ready", None, {}, "blob_profile", None, None,
                               datetime.now(timezone.utc)),
            width_pt=100, height_pt=100, rotation=0,
            has_text_layer=not empty, scan=empty, content_merkle=None,
            words=words,
        )
        result[str(profile_id)] = profile
    return _Profiles(result)


def _claim_and_run(store, profiles: _Profiles):
    work = ComparisonWorkRepository()
    with session_scope(store._sessions) as session:
        worker_id = WorkerRegistry().register(session, version="cmp-stage-text-test", slots=1)
        item = work.claim(session, worker_id=worker_id,
                          modules={"stages"}, kinds={WORK_KIND})
    assert item is not None
    handler = StageTextRecomputeHandler(
        WorkDependencies(None, store._sessions, None, work),  # type: ignore[arg-type]
        profile_reader=profiles,
    )
    outcome = handler.run(item)
    if isinstance(outcome, (Completed, Failed)):
        with session_scope(store._sessions) as session:
            assert work.finish(session, item.authority, outcome) == (
                "succeeded" if isinstance(outcome, Completed) else "failed"
            )
    return outcome


def test_keyed_request_and_worker_materialize_raw_evidence(comparison_session: Session) -> None:
    store, pair, revision, actor, left, right = _seed(comparison_session)
    service = StageTextRecomputeService(store._sessions)
    key = f"stage-text-{new_ulid()}"
    request = dict(revision_id=revision, user_uid=actor,
                   actor_roles=frozenset({"expert"}), idempotency_key=key)
    first = service.start(**request)
    assert first.state == "queued" and [s.step_no for s in first.steps] == [2, 3]
    assert service.start(**request).run_id == first.run_id
    other = service.start(**(request | {"idempotency_key": f"stage-text-{new_ulid()}"}))
    assert other.run_id == first.run_id
    assert comparison_session.execute(text(
        "SELECT count(*) FROM comparison_work WHERE kind = :kind AND project_uid = "
        "(SELECT project_uid FROM stage_pair WHERE stage_pair_id = :pair)"
    ), {"kind": WORK_KIND, "pair": pair}).scalar_one() == 1
    with pytest.raises(DomainError) as reused:
        service.start(**(request | {"revision_id": f"slk_{new_ulid()}"}))
    assert reused.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE

    assert isinstance(_claim_and_run(store, _profiles(comparison_session, left, right, empty=False)), Completed)
    finished = service.get(first.run_id)
    assert finished.state == "completed" and not finished.stale
    assert finished.steps[0].counts == {"fragments": 2, "exclusions": 0}
    assert finished.steps[1].counts == {"differences": 1, "hints": 0}
    reader = StageTextReadService(store._sessions)
    differences, _ = reader.revision_rows(kind="differences", revision_id=revision,
                                          after=None, limit=10)
    assert len(differences) == 1 and differences[0]["status"] == "changed"


def test_completed_empty_run_seals_a_true_empty_result(comparison_session: Session) -> None:
    store, pair, revision, actor, left, right = _seed(comparison_session)
    service = StageTextRecomputeService(store._sessions)
    run = service.start(revision_id=revision, user_uid=actor,
                        actor_roles=frozenset({"expert"}),
                        idempotency_key=f"stage-text-{new_ulid()}")
    assert isinstance(_claim_and_run(store, _profiles(comparison_session, left, right, empty=True)), Completed)
    assert service.get(run.run_id).state == "completed"
    reader = StageTextReadService(store._sessions)
    fragments, _ = reader.fragments(pair_id=pair, after=None, limit=10)
    differences, _ = reader.revision_rows(kind="differences", revision_id=revision,
                                          after=None, limit=10)
    assert fragments == differences == ()


def test_new_map_revision_fences_worker_before_evidence(comparison_session: Session) -> None:
    store, pair, revision, actor, left, right = _seed(comparison_session)
    service = StageTextRecomputeService(store._sessions)
    run = service.start(revision_id=revision, user_uid=actor,
                        actor_roles=frozenset({"expert"}),
                        idempotency_key=f"stage-text-{new_ulid()}")
    comparison_session.execute(text(
        "INSERT INTO stage_link_revision (stage_link_revision_id, stage_pair_id, revision_no, "
        "base_revision_id, source, input_sha256, actor_user_uid, command_id) "
        "VALUES (:revision, :pair, 2, :base, 'expert', :sha, :actor, :command)"
    ), {"revision": f"slk_{new_ulid()}", "pair": pair, "base": revision,
        "sha": "e" * 64, "actor": actor,
        "command": _command(comparison_session, "apply_stage_sheet_map")})
    outcome = _claim_and_run(store, _profiles(comparison_session, left, right, empty=False))
    assert isinstance(outcome, Failed) and outcome.reason == "stage_text_run_stale"
    assert service.get(run.run_id).state == "failed"
    assert comparison_session.execute(text(
        "SELECT count(*) FROM stage_text_fragment WHERE stage_pair_id = :pair"
    ), {"pair": pair}).scalar_one() == 0


def test_missing_profile_archive_fails_without_an_empty_seal(comparison_session: Session) -> None:
    store, pair, revision, actor, left, right = _seed(comparison_session)
    service = StageTextRecomputeService(store._sessions)
    run = service.start(revision_id=revision, user_uid=actor,
                        actor_roles=frozenset({"expert"}),
                        idempotency_key=f"stage-text-{new_ulid()}")
    profiles = _profiles(comparison_session, left, right, empty=False)
    original = profiles.profiles[left]
    profiles.profiles[left] = replace(
        original, row=replace(original.row, profile_blob_id=None),
    )
    outcome = _claim_and_run(store, profiles)
    assert isinstance(outcome, Failed) and outcome.reason == "stage_text_evidence_invalid"
    assert service.get(run.run_id).state == "failed"
    with pytest.raises(DomainError) as unreadable:
        StageTextReadService(store._sessions).fragments(pair_id=pair, after=None, limit=10)
    assert unreadable.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE


def test_next_run_gets_its_own_work_before_prior_work_finishes(comparison_session: Session) -> None:
    store, _pair, revision, actor, _left, _right = _seed(comparison_session)
    service = StageTextRecomputeService(store._sessions)
    request = dict(revision_id=revision, user_uid=actor, actor_roles=frozenset({"expert"}))
    first = service.start(**request, idempotency_key=f"stage-text-{new_ulid()}")
    comparison_session.execute(text(
        "UPDATE stage_chain_run SET state = 'completed' WHERE stage_chain_run_id = :run"
    ), {"run": first.run_id})
    second = service.start(**request, idempotency_key=f"stage-text-{new_ulid()}")
    assert second.run_id != first.run_id
    payloads = comparison_session.execute(text(
        "SELECT payload FROM comparison_work WHERE kind = :kind "
        "AND payload->>'run_id' IN (:first, :second)"
    ), {"kind": WORK_KIND, "first": first.run_id, "second": second.run_id}).scalars().all()
    assert {row["run_id"] for row in payloads} == {first.run_id, second.run_id}
