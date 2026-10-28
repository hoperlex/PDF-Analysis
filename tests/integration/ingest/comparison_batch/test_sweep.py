"""`CMP-INGEST-02`: the work kind ``upload_abort_sweep`` -- the store's open multipart uploads of a cancelled or abandoned
batch are aborted from the database's decision, and only from it.

The store is the real one (the bucket is read back through a plain ``boto3`` client), wrapped to record which tokens were
offered to its ``abort``.
"""

from __future__ import annotations

import pytest

from auditmanager.comparison.public import ComparisonWorkRepository
from auditmanager.ingest.comparison_batch.public import BatchLifecycle, ComparisonBatchService
from auditmanager.shared.db import session_scope
from auditmanager.storage.errors import StorageUnavailableError
from tests.integration.ingest.comparison_batch.conftest import SpyStore
from tests.integration.ingest.comparison_batch.support import EXPERT, Harness, Queue, fresh_key


def _mixed_batch(h: Harness) -> tuple[str, dict[str, str]]:
    names = ["Alpha (1).pdf", "Beta (1).pdf", "Gamma (1).pdf"]
    view = h.declare(names)
    ids = {item.display_name: item.file_id for item in view.files or ()}
    h.send(view.upload_id, ids["Alpha (1).pdf"], "Alpha (1).pdf")
    h.complete(view.upload_id, ids["Alpha (1).pdf"])
    h.send(view.upload_id, ids["Beta (1).pdf"], "Beta (1).pdf")
    h.send(view.upload_id, ids["Gamma (1).pdf"], "Gamma (1).pdf")
    return view.upload_id, ids


def _token_of(h: Harness, file_id: str) -> str:
    return str(h.rows("SELECT multipart_token FROM comparison_upload_file WHERE comparison_upload_file_id = :f", f=file_id)[0][0])


def _queue(session_factory, engine, spy: SpyStore, lifecycle) -> Queue:
    return Queue(session_factory, engine, spy, lifecycle=lifecycle)


def _enqueue_sweep(h: Harness, upload_id: str, *, payload: dict | None = None, key: str = "manual") -> None:
    with session_scope(h.sessions) as session:
        ComparisonWorkRepository().enqueue(
            session, project_uid=h.project_uid, module="versions", kind="upload_abort_sweep",
            payload={"upload_id": upload_id, "reason": "cancelled"} if payload is None else payload, dedupe_key=key,
            comparison_upload_id=upload_id,
        )


class TestWhatTheSweepAborts:
    def test_only_the_uploads_of_files_that_never_completed_are_offered_to_the_store(
        self, h: Harness, spy: SpyStore, session_factory, engine, lifecycle, open_uploads
    ) -> None:
        upload_id, ids = _mixed_batch(h)
        verified = _token_of(h, ids["Alpha (1).pdf"])
        unfinished = sorted(_token_of(h, ids[name]) for name in ("Beta (1).pdf", "Gamma (1).pdf"))
        assert len(open_uploads()) == 2
        h.cancel(upload_id)
        assert _queue(session_factory, engine, spy, lifecycle).run_all() == [("upload_abort_sweep", "succeeded")]
        assert sorted(spy.aborted_tokens()) == unfinished and verified not in spy.aborted_tokens()
        assert open_uploads() == []

    def test_it_is_safe_to_run_again(self, h: Harness, spy: SpyStore, session_factory, engine, lifecycle, open_uploads) -> None:
        upload_id, _ids = _mixed_batch(h)
        h.cancel(upload_id)
        queue = _queue(session_factory, engine, spy, lifecycle)
        queue.run_all()
        _enqueue_sweep(h, upload_id, key="again")
        assert queue.run_all() == [("upload_abort_sweep", "succeeded")], "tokens already aborted are simply absent"
        assert open_uploads() == []

    def test_a_published_blob_is_never_touched(self, h: Harness, spy: SpyStore, session_factory, engine, lifecycle, raw_s3, s3_settings) -> None:
        upload_id, ids = _mixed_batch(h)
        before = sorted(i["Key"] for i in raw_s3.list_objects_v2(Bucket=s3_settings.bucket).get("Contents", []))
        assert before, "Alpha's bytes are published"
        h.cancel(upload_id)
        _queue(session_factory, engine, spy, lifecycle).run_all()
        after = sorted(i["Key"] for i in raw_s3.list_objects_v2(Bucket=s3_settings.bucket).get("Contents", []))
        assert after == before


class TestWhatTheSweepRefuses:
    def test_a_batch_that_is_not_cancelled_is_never_swept(
        self, h: Harness, spy: SpyStore, session_factory, engine, lifecycle, open_uploads
    ) -> None:
        upload_id, _ids = _mixed_batch(h)
        _enqueue_sweep(h, upload_id)
        assert _queue(session_factory, engine, spy, lifecycle).run_all() == [("upload_abort_sweep", "failed")]
        assert [w["failure_reason"] for w in h.work(upload_id, kind="upload_abort_sweep")] == ["sweep_upload_not_cancelled"]
        assert spy.aborted_tokens() == [] and len(open_uploads()) == 2
        assert h.state(upload_id) == "uploading"

    @pytest.mark.parametrize("payload", [
        {}, {"upload_id": "nope", "reason": "cancelled"}, {"upload_id": "cbt_01ARZ3NDEKTSV4RRFFQ69G5FAV"},
        {"upload_id": "cbt_01ARZ3NDEKTSV4RRFFQ69G5FAV", "reason": "because"},
        {"upload_id": "cbt_01ARZ3NDEKTSV4RRFFQ69G5FAV", "reason": "cancelled", "extra": 1},
    ])
    def test_a_payload_that_is_not_a_cancelled_batch_is_refused_before_anything_is_read(
        self, h: Harness, spy: SpyStore, session_factory, engine, lifecycle, payload: dict
    ) -> None:
        upload_id = h.declare(["Alpha (1).pdf"]).upload_id
        _enqueue_sweep(h, upload_id, payload=payload)
        assert _queue(session_factory, engine, spy, lifecycle).run_all() == [("upload_abort_sweep", "failed")]
        assert [w["failure_reason"] for w in h.work(upload_id, kind="upload_abort_sweep")] == ["batch_payload_invalid"]
        assert spy.aborted_tokens() == []

    def test_an_unknown_batch_is_never_swept(self, h: Harness, spy: SpyStore, session_factory, engine, lifecycle) -> None:
        anchor = h.declare(["Alpha (1).pdf"]).upload_id  # the item is attached to a real batch; its payload names another
        _enqueue_sweep(h, anchor, payload={"upload_id": "cbt_01ARZ3NDEKTSV4RRFFQ69G5FAV", "reason": "cancelled"})
        assert _queue(session_factory, engine, spy, lifecycle).run_all() == [("upload_abort_sweep", "failed")]
        assert spy.aborted_tokens() == []

    def test_one_token_the_store_rejects_does_not_stop_the_others_and_is_reported(
        self, h: Harness, spy: SpyStore, session_factory, engine, lifecycle, open_uploads
    ) -> None:
        names = ["Alpha (1).pdf", "Beta (1).pdf"]
        view = h.declare(names)
        ids = {i.display_name: i.file_id for i in view.files or ()}
        h.send(view.upload_id, ids["Beta (1).pdf"], "Beta (1).pdf")
        with session_scope(h.sessions) as session:  # a token nobody minted (the column is write-once, and was empty)
            from sqlalchemy import text

            session.execute(text(
                "UPDATE comparison_upload_file SET multipart_token = '../escape' WHERE comparison_upload_file_id = :f"
            ), {"f": ids["Alpha (1).pdf"]})
        h.cancel(view.upload_id)
        assert _queue(session_factory, engine, spy, lifecycle).run_all() == [("upload_abort_sweep", "failed")]
        assert [w["failure_reason"] for w in h.work(view.upload_id, kind="upload_abort_sweep")] == ["sweep_token_rejected"]
        assert open_uploads() == [], "the valid token was aborted all the same"


class TestAStoreFault:
    def test_is_a_failed_attempt_that_retries_and_finishes_when_the_store_is_back(
        self, h: Harness, spy: SpyStore, session_factory, engine, lifecycle, open_uploads
    ) -> None:
        upload_id, _ids = _mixed_batch(h)
        h.cancel(upload_id)
        spy.fail["abort_multipart"] = StorageUnavailableError(dependency="blob_storage")
        queue = _queue(session_factory, engine, spy, lifecycle)
        [(kind, state)] = queue.run_all()
        assert kind == "upload_abort_sweep" and state not in ("succeeded", "failed"), "back on the queue, not lost"
        assert len(open_uploads()) == 2
        h.make_due("upload_abort_sweep")
        # the retry waits out its backoff: bring it forward
        with session_scope(h.sessions) as session:
            from sqlalchemy import text

            session.execute(text("UPDATE comparison_work SET not_before = clock_timestamp() - interval '1 second' "
                                 "WHERE kind = 'upload_abort_sweep' AND state = 'queued'"))
        assert queue.run_all() == [("upload_abort_sweep", "succeeded")]
        assert open_uploads() == []


class TestTheGraceBeforeTheSweep:
    def test_the_product_waits_for_a_part_still_on_its_way_and_the_tests_do_not(self, h: Harness, session_factory) -> None:
        upload_id, _ids = _mixed_batch(h)
        product = ComparisonBatchService(h.comparison, session_factory=session_factory, lifecycle=BatchLifecycle())
        product.cancel_upload(upload_id=upload_id, user_uid=h.user, actor_roles=EXPERT, idempotency_key=fresh_key("c"))
        [sweep] = h.work(upload_id, kind="upload_abort_sweep")
        with session_factory() as session:
            from sqlalchemy import text

            seconds = session.execute(text(
                "SELECT extract(epoch FROM not_before - clock_timestamp()) FROM comparison_work "
                "WHERE comparison_work_id = :w"), {"w": sweep["id"]}).scalar_one()
        assert 290 <= float(seconds) <= 300, "five minutes: longer than the edge's longest request"
