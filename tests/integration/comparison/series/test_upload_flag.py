"""«После подготовки сравнить все соседние версии» (`CMP-SERIES-01`): the flag is stored with the batch and read back, and a
set whose preparation has completed gets its matrix prepared and then its series started -- through one work item attached to
the batch, which ``BatchLifecycle.advance`` queues once and a cancel of the batch reaches."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import pytest
from sqlalchemy import text

from auditmanager.comparison.series.followup import follow_up_dedupe_key
from auditmanager.ingest.comparison_batch.public import BatchLifecycle, ComparisonBatchService
from auditmanager.ingest.comparison_pdf.public import (
    ComparisonUploadRepository,
    ComparisonUploadService,
    DeclaredFileRequest,
)
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import new_ulid

from .support import EXPERT, ScriptedEngine, drain, key, make_due, runner_with, start


def declared() -> list[DeclaredFileRequest]:
    return [DeclaredFileRequest(display_name="v1.pdf", size_bytes=1000, sha256=hashlib.sha256(new_ulid().encode()).hexdigest(), page_count=2)]


@pytest.fixture
def uploads(sessions, blob_store):
    return ComparisonUploadService(blob_store, session_factory=sessions)


@pytest.fixture
def batches(sessions, uploads):
    return ComparisonBatchService(uploads, session_factory=sessions, lifecycle=BatchLifecycle(sweep_delay_seconds=0.0))


@pytest.fixture
def declare(uploads, batches, expert_uid):
    """``declare(project, flag)`` -> the batch's view; the batch is cancelled at the end (an account holds one active batch)."""
    made: list[str] = []

    def make(project: str, flag: bool | None = None, *, idempotency_key: str | None = None):
        extra = {} if flag is None else {"compare_after_preparation": flag}
        view = uploads.create_upload(project_uid=project, files=declared(), user_uid=expert_uid, actor_label="Эксперт Т.",
                                     idempotency_key=idempotency_key or key(), **extra)
        made.append(view.upload_id)
        return view

    yield make
    for upload_id in made:
        try:
            batches.cancel_upload(upload_id=upload_id, user_uid=expert_uid, actor_roles=EXPERT, idempotency_key=key())
        except DomainError:
            pass


def stored_flag(lab, upload_id: str) -> bool:
    return lab.rows("SELECT compare_after_preparation AS f FROM comparison_upload WHERE comparison_upload_id = :u", u=upload_id)[0]["f"]


def test_the_flag_is_stored_with_the_batch_and_read_back(lab, uploads, declare) -> None:
    doc = lab.clone(profiles=False)
    asked = declare(doc.project_uid, True)
    assert asked.compare_after_preparation is True and stored_flag(lab, asked.upload_id) is True
    assert uploads.get_upload(upload_id=asked.upload_id).compare_after_preparation is True


@pytest.mark.parametrize("flag", [None, False])
def test_a_batch_declared_without_the_flag_does_not_compare(lab, uploads, declare, flag: bool | None) -> None:
    doc = lab.clone(profiles=False)
    plain = declare(doc.project_uid, flag)
    assert plain.compare_after_preparation is False and stored_flag(lab, plain.upload_id) is False


def test_a_repeat_of_the_declaration_is_held_to_the_flag(lab, uploads, declare, expert_uid) -> None:
    doc = lab.clone(profiles=False)
    token = key()
    files = declared()
    first = uploads.create_upload(project_uid=doc.project_uid, files=files, user_uid=expert_uid, actor_label="Э",
                                  idempotency_key=token, compare_after_preparation=True)
    try:
        again = uploads.create_upload(project_uid=doc.project_uid, files=files, user_uid=expert_uid, actor_label="Э",
                                      idempotency_key=token, compare_after_preparation=True)
        assert again.upload_id == first.upload_id and again.compare_after_preparation is True
        with pytest.raises(DomainError) as other:
            uploads.create_upload(project_uid=doc.project_uid, files=files, user_uid=expert_uid, actor_label="Э",
                                  idempotency_key=token)
        assert other.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE
    finally:
        ComparisonBatchService(uploads, session_factory=uploads._factory).cancel_upload(  # type: ignore[attr-defined]
            upload_id=first.upload_id, user_uid=expert_uid, actor_roles=EXPERT, idempotency_key=key())


def done_set(lab, upload_id: str, document_uid: str, user: str, *, released: bool = True) -> str:
    """A confirmed set of the batch whose versions exist (the document's), released or not."""
    set_id = f"cus_{new_ulid()}"
    proposal: dict[str, Any] = {"confirmed": {"files": [{"position": 1, "version_uid": "ver_" + new_ulid()}]}}
    if released:
        proposal["processing"] = {"work": {}}
    with lab.sessions() as session:
        for state in ("proposed", "processing"):  # the batch is being processed once a set is confirmed
            session.execute(text("UPDATE comparison_upload SET state = :s WHERE comparison_upload_id = :u AND state <> :s "
                                 "AND state <> 'processing'"), {"s": state, "u": upload_id})
        session.execute(text(
            "INSERT INTO comparison_upload_set (comparison_upload_set_id, comparison_upload_id, state, document_uid, "
            "proposal, confirmed_by_user_uid, confirmed_at, terminal_at) VALUES (:s, :u, 'done', :d, CAST(:p AS jsonb), "
            ":by, clock_timestamp(), clock_timestamp())"),
            {"s": set_id, "u": upload_id, "d": document_uid, "p": json.dumps(proposal), "by": user})
        session.commit()
    return set_id


def advance(sessions, upload_id: str) -> str:
    with session_scope(sessions) as session:
        upload = ComparisonUploadRepository().get_upload(session, upload_id, for_update=True)
        assert upload is not None
        return BatchLifecycle().advance(session, upload).outcome


def follow_ups(lab, upload_id: str) -> list[dict[str, Any]]:
    return lab.rows("SELECT comparison_work_id AS id, state, dedupe_key, created_by_user_uid AS by, payload, comparison_upload_id AS u "
                    "FROM comparison_work WHERE comparison_upload_id = :u AND kind = 'series_after_preparation' ORDER BY created_at", u=upload_id)


def test_advance_queues_the_follow_up_of_a_prepared_set_once_and_only_for_a_flagged_batch(lab, sessions, declare, expert_uid) -> None:
    doc = lab.clone()
    plain = declare(doc.project_uid, False)
    done_set(lab, plain.upload_id, doc.document_uid, expert_uid)
    assert advance(sessions, plain.upload_id) in ("waiting", "completed") and follow_ups(lab, plain.upload_id) == []

    # the second batch of the installation: a second account
    other = lab.clone()
    from tests.support.accounts import complete_expert_account

    with sessions() as session:
        second = str(complete_expert_account(session, "series-flag-other").user_uid)
        session.commit()
    from auditmanager.ingest.comparison_pdf.public import ComparisonUploadService as Service

    flagged = Service(None, session_factory=sessions).create_upload(
        project_uid=other.project_uid, files=declared(), user_uid=second, actor_label="Другой Э.", idempotency_key=key(),
        compare_after_preparation=True)
    try:
        set_id = done_set(lab, flagged.upload_id, other.document_uid, second)
        assert advance(sessions, flagged.upload_id) == "waiting"  # the follow-up is an item of the batch: it is in flight
        queued = follow_ups(lab, flagged.upload_id)
        assert len(queued) == 1 and queued[0]["state"] == "queued" and queued[0]["u"] == flagged.upload_id
        assert queued[0]["dedupe_key"] == follow_up_dedupe_key(set_id) and queued[0]["by"] == second
        assert queued[0]["payload"] == {"document_uid": other.document_uid, "set_id": set_id, "actor_label": "Другой Э."}
        assert lab.rows("SELECT proposal->'comparison'->>'work' AS w FROM comparison_upload_set WHERE comparison_upload_set_id = :s",
                        s=set_id)[0]["w"] == queued[0]["id"]
        assert advance(sessions, flagged.upload_id) == "waiting" and len(follow_ups(lab, flagged.upload_id)) == 1  # once
    finally:
        ComparisonBatchService(Service(None, session_factory=sessions), session_factory=sessions).cancel_upload(
            upload_id=flagged.upload_id, user_uid=second, actor_roles=EXPERT, idempotency_key=key())


def test_the_next_set_waits_for_the_follow_up_and_a_cancel_of_the_batch_reaches_it(lab, sessions, batches, declare, expert_uid) -> None:
    doc = lab.clone()
    flagged = declare(doc.project_uid, True)
    done_set(lab, flagged.upload_id, doc.document_uid, expert_uid)
    waiting = done_set(lab, flagged.upload_id, doc.document_uid, expert_uid, released=False)
    assert advance(sessions, flagged.upload_id) == "waiting"  # not "released": the follow-up of the first set is in flight
    assert lab.rows("SELECT proposal ? 'processing' AS released FROM comparison_upload_set WHERE comparison_upload_set_id = :s", s=waiting)[0]["released"] is False
    batches.cancel_upload(upload_id=flagged.upload_id, user_uid=expert_uid, actor_roles=EXPERT, idempotency_key=key())
    assert [f["state"] for f in follow_ups(lab, flagged.upload_id)] == ["cancelled"]


def test_the_follow_up_prepares_the_matrix_and_then_starts_the_series_for_the_person_who_declared_the_batch(
    lab, sessions, engine, blob_store, worker_id, service, declare, expert_uid,
) -> None:
    doc = lab.clone()  # profiles exist, no matrix yet
    flagged = declare(doc.project_uid, True)
    set_id = done_set(lab, flagged.upload_id, doc.document_uid, expert_uid)
    advance(sessions, flagged.upload_id)
    fake = ScriptedEngine(sessions)
    runner = runner_with(sessions, engine, blob_store, compare=fake)
    ran = drain(runner, worker_id, engine, sessions, doc.project_uid)

    kinds = [kind for kind, _state in ran]
    assert kinds.count("matrix_build") == 1 and kinds.count("series_pair") == 24
    assert kinds.index("matrix_build") < kinds.index("series_pair")
    page = service.list_series(project_uid=doc.project_uid, document_uid=doc.document_uid, after=None, limit=10)
    assert len(page.items) == 1 and page.items[0]["state"] == "completed"
    row = lab.rows("SELECT actor_user_uid AS u, actor_label AS l FROM comparison_series WHERE document_uid = :d", d=doc.document_uid)[0]
    assert row == {"u": expert_uid, "l": "Эксперт Т."}
    assert [f["state"] for f in follow_ups(lab, flagged.upload_id)] == ["succeeded"]
    command = lab.rows("SELECT count(*) AS n FROM command_record WHERE command_type = 'start_comparison_series' "
                       "AND idempotency_key = :k", k=f"auto-{set_id}")[0]["n"]
    assert command == 1
    # the batch can now complete: nothing of it is in flight
    assert advance(sessions, flagged.upload_id) in ("waiting", "completed", "released")


def test_the_follow_up_fails_visibly_when_a_series_is_already_live(lab, sessions, engine, blob_store, worker_id, matrix_service,
                                                                   service, declare, expert_uid) -> None:
    from .support import build

    doc = lab.clone()
    build(matrix_service, doc)
    start(service, doc, expert_uid)  # a person started one meanwhile
    flagged = declare(doc.project_uid, True)
    done_set(lab, flagged.upload_id, doc.document_uid, expert_uid)
    advance(sessions, flagged.upload_id)
    runner = runner_with(sessions, engine, blob_store, compare=ScriptedEngine(sessions))
    ran = drain(runner, worker_id, engine, sessions, doc.project_uid, rounds=3, limit=3, hold=("series_pair", "series_drive"))
    assert ("series_after_preparation", "failed") in ran
    failed = lab.rows("SELECT failure_reason AS r FROM comparison_work WHERE comparison_upload_id = :u AND kind = 'series_after_preparation'",
                      u=flagged.upload_id)[0]
    assert failed["r"] == "comparison_series_active"
    assert len(service.list_series(project_uid=doc.project_uid, document_uid=doc.document_uid, after=None, limit=10).items) == 1
    make_due(sessions, doc.project_uid)
