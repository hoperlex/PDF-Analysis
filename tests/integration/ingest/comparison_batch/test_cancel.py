"""`CMP-INGEST-02`: «Отменить пакет» (ADR-0025 decision 10).

A cancel is the database's decision in one transaction (files, parts, sets, the batch, its queue items, the owed sweep) and
the store is cleaned afterwards by a work kind. It frees the account's one active slot, deletes nothing that was already
admitted, refuses what comes late, and is an expert's keyed act.
"""

from __future__ import annotations

import pytest

from auditmanager.ingest.comparison_pdf.public import ConfirmedFile, DeclaredFileRequest
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import parse_blob_id
from tests.integration.ingest.comparison_batch.support import (
    ADMIN,
    EXPERT,
    Harness,
    Queue,
    distinct_pdf,
    fresh_key,
)
from tests.integration.ingest.comparison_pdf.support import parts_of, sha256


def _reason(refusal: DomainError) -> str:
    return str(refusal.detail_fields["conflict_reason"])


def _mixed_batch(h: Harness) -> tuple[str, dict[str, str]]:
    """One batch still ``uploading``: a verified file, a file whose only part is staged (its multipart upload is open
    in the store) and a file that was declared and never sent."""
    names = ["Alpha (1).pdf", "Beta (1).pdf", "Gamma (1).pdf"]
    view = h.declare(names)
    ids = {item.display_name: item.file_id for item in view.files or ()}
    h.send(view.upload_id, ids["Alpha (1).pdf"], "Alpha (1).pdf")
    h.complete(view.upload_id, ids["Alpha (1).pdf"])
    h.send(view.upload_id, ids["Beta (1).pdf"], "Beta (1).pdf")
    assert h.state(view.upload_id) == "uploading"
    return view.upload_id, ids


class TestTheSlotIsFreed:
    def _declare_again(self, h: Harness):
        data = distinct_pdf()
        return h.comparison.create_upload(
            project_uid=h.project_uid, files=[DeclaredFileRequest("Other.pdf", len(data), sha256(data))],
            user_uid=h.user, actor_label="Эксперт Проверкин", idempotency_key=fresh_key("again"),
        )

    def test_an_account_with_an_active_batch_cannot_declare_another_until_it_cancels(self, h: Harness) -> None:
        first = h.declare(["Alpha (1).pdf"])
        with pytest.raises(DomainError) as refused:
            self._declare_again(h)
        assert refused.value.code is ErrorCode.CONFLICT and _reason(refused.value) == "comparison_upload_active"
        assert h.cancel(first.upload_id).state == "cancelled"
        assert self._declare_again(h).state == "uploading"

    @pytest.mark.parametrize("reach", ["uploading", "proposed", "processing", "paused"])
    def test_every_active_state_can_be_cancelled(self, h: Harness, reach: str) -> None:
        if reach == "uploading":
            upload_id = h.declare(["Alpha (1).pdf"]).upload_id
        else:
            upload_id = h.proposed({"Alpha": 1, "Beta": 1})
            if reach in ("processing", "paused"):
                h.confirm(upload_id, h.sets(upload_id)[0])
                assert h.state(upload_id) == "processing"
            if reach == "paused":
                h.pause(upload_id)
        assert h.state(upload_id) == reach
        assert h.cancel(upload_id).state == "cancelled"
        assert h.state(upload_id) == "cancelled"

    @pytest.mark.parametrize("reach", ["cancelled", "completed"])
    def test_a_finished_batch_is_a_conflict(self, h: Harness, reach: str) -> None:
        upload_id = h.proposed({"Alpha": 1})
        if reach == "cancelled":
            h.cancel(upload_id)
        else:
            h.confirm(upload_id, h.sets(upload_id)[0])
            assert h.state(upload_id) == "completed"
        with pytest.raises(DomainError) as refused:
            h.cancel(upload_id)
        assert refused.value.code is ErrorCode.CONFLICT and _reason(refused.value) == "comparison_upload_state"
        assert h.state(upload_id) == reach


class TestWhatTheDatabaseDecides:
    def test_files_parts_and_sets_are_settled_together_and_a_verified_file_is_left_alone(self, h: Harness) -> None:
        upload_id, ids = _mixed_batch(h)
        h.cancel(upload_id)
        files = {r[0]: (r[1], r[2]) for r in h.rows(
            "SELECT display_name, state, failure_reason FROM comparison_upload_file WHERE comparison_upload_id = :i", i=upload_id)}
        assert files["Alpha (1).pdf"] == ("verified", None), "a verified file's bytes are published and stay"
        assert files["Beta (1).pdf"] == ("failed", "batch_cancelled")
        assert files["Gamma (1).pdf"] == ("failed", "batch_cancelled")
        parts = {r[0]: r[1] for r in h.rows(
            "SELECT comparison_upload_file_id, state FROM comparison_upload_part WHERE comparison_upload_file_id = ANY(:f)",
            f=list(ids.values()))}
        assert parts[ids["Alpha (1).pdf"]] == "completed" and parts[ids["Beta (1).pdf"]] == "aborted"
        sets = h.rows("SELECT state, failure_reason FROM comparison_upload_set WHERE comparison_upload_id = :i", i=upload_id)
        assert sets and all(row == ("excluded", None) for row in sets), "no set that made no versions survives"

    def test_the_store_is_untouched_until_the_sweep_runs_and_clean_after_it(
        self, h: Harness, queue: Queue, open_uploads
    ) -> None:
        upload_id, _ids = _mixed_batch(h)
        assert len(open_uploads()) == 1
        h.cancel(upload_id)
        assert len(open_uploads()) == 1, "the cancel is the database's decision; the store is the sweep's"
        [sweep] = h.work(upload_id, kind="upload_abort_sweep")
        assert sweep["state"] == "queued" and sweep["payload"] == {"upload_id": upload_id, "reason": "cancelled"}
        assert [kind for kind, _state in queue.run_all()] == ["upload_abort_sweep"]
        assert open_uploads() == []
        assert h.work(upload_id, kind="upload_abort_sweep")[0]["state"] == "succeeded"

    def test_every_waiting_item_of_the_batch_is_cancelled_with_it(self, h: Harness) -> None:
        upload_id = h.proposed({"Alpha": 2, "Beta": 1})
        h.confirm(upload_id, h.sets(upload_id)[0])  # a batch being processed: two profile items of the batch wait
        assert [(w["kind"], w["state"]) for w in h.work(upload_id)] == [("page_profile", "queued")] * 2
        h.cancel(upload_id)
        assert [(w["kind"], w["state"]) for w in h.work(upload_id)] == [("page_profile", "cancelled")] * 2

    def test_a_batch_that_never_started_an_upload_owes_no_sweep(self, h: Harness) -> None:
        upload_id = h.declare(["Alpha (1).pdf"]).upload_id
        h.cancel(upload_id)
        assert h.work(upload_id, kind="upload_abort_sweep") == []

    def test_a_cancel_asks_an_item_in_flight_to_stop_and_cancels_the_rest(self, h: Harness, queue: Queue) -> None:
        upload_id = h.proposed({"Alpha": 2, "Beta": 1})
        h.confirm(upload_id, h.sets(upload_id)[0])
        in_flight = queue.claim()
        assert in_flight is not None and in_flight.kind == "page_profile"
        h.cancel(upload_id)
        items = {w["id"]: w for w in h.work(upload_id, kind="page_profile")}
        assert items[in_flight.work_id]["cancel_requested"] is True
        assert items[in_flight.work_id]["state"] in ("leased", "running"), "the holder ends it at its next checkpoint"
        assert sorted(w["state"] for k, w in items.items() if k != in_flight.work_id) == ["cancelled"]

    def test_sweep_survives_the_cancel_of_the_batch_it_belongs_to(self, h: Harness, queue: Queue, open_uploads) -> None:
        """The ordering guard: the items of the batch are stopped first and the sweep is enqueued after, so the sweep
        (which carries the batch's identity too) is never one of the items the cancel stopped."""
        upload_id, _ids = _mixed_batch(h)
        h.cancel(upload_id)
        assert [(w["kind"], w["state"]) for w in h.work(upload_id)] == [("upload_abort_sweep", "queued")]
        queue.run_all()
        assert open_uploads() == []


class TestNothingAdmittedIsDeleted:
    def test_a_confirmed_sets_versions_their_blobs_and_bytes_survive_a_cancel_and_its_sweep(
        self, h: Harness, queue: Queue, store, raw_s3, s3_settings
    ) -> None:
        upload_id = h.proposed({"Alpha": 2, "Beta": 1})
        alpha, beta = h.sets(upload_id)
        h.confirm(upload_id, alpha)
        versions = h.rows(
            "SELECT version_uid, document_uid, sha256, byte_size, upload_kind FROM document_version ORDER BY version_ordinal, version_uid")
        documents = h.rows("SELECT document_uid, current_version_uid FROM document")
        blobs = h.rows("SELECT blob_id, state, sha256, size_bytes FROM blob ORDER BY blob_id")
        keys_before = sorted(
            item["Key"] for item in raw_s3.list_objects_v2(Bucket=s3_settings.bucket).get("Contents", []))
        assert len(versions) == 2 and all(v[4] == "comparison_pdf" for v in versions)

        h.cancel(upload_id)
        queue.run_all()

        assert h.rows(
            "SELECT version_uid, document_uid, sha256, byte_size, upload_kind FROM document_version ORDER BY version_ordinal, version_uid"
        ) == versions
        assert h.rows("SELECT document_uid, current_version_uid FROM document") == documents
        assert h.rows("SELECT blob_id, state, sha256, size_bytes FROM blob ORDER BY blob_id") == blobs
        assert all(b[1] == "available" for b in blobs if b[0] in {f for (f,) in h.rows(
            "SELECT blob_id FROM comparison_upload_file WHERE state = 'verified'")})
        keys_after = sorted(item["Key"] for item in raw_s3.list_objects_v2(Bucket=s3_settings.bucket).get("Contents", []))
        assert keys_after == keys_before, "no object left the bucket"
        # The bytes of every verified file read back, whole, through the store.
        for blob_id, file_sha, size in h.rows(
            "SELECT blob_id, declared_sha256, declared_size_bytes FROM comparison_upload_file WHERE state = 'verified'"
        ):
            stream = store.open_stream(parse_blob_id(blob_id), expected_sha256=file_sha, expected_size=size)
            assert sha256(b"".join(stream)) == file_sha

    def test_the_done_set_stays_done_and_only_the_undecided_set_is_left_out(self, h: Harness) -> None:
        upload_id = h.proposed({"Alpha": 1, "Beta": 1})
        alpha, beta = h.sets(upload_id)
        h.confirm(upload_id, alpha)
        h.cancel(upload_id)
        assert h.set_states(upload_id) == {alpha.set_id: "done", beta.set_id: "excluded"}
        assert h.rows("SELECT document_uid FROM comparison_upload_set WHERE comparison_upload_set_id = :s", s=alpha.set_id)[0][0]


class TestWhatComesLateIsRefused:
    def test_a_part_after_the_cancel_is_a_conflict_and_nothing_is_staged(self, h: Harness, open_uploads) -> None:
        upload_id, ids = _mixed_batch(h)
        h.cancel(upload_id)
        data = h.contents["Gamma (1).pdf"]
        with pytest.raises(DomainError) as refused:
            h.comparison.put_part(
                upload_id=upload_id, file_id=ids["Gamma (1).pdf"], part_number=1, content=parts_of(data)[0],
                user_uid=h.user, idempotency_key=fresh_key("late"),
            )
        assert refused.value.code is ErrorCode.CONFLICT and _reason(refused.value) == "comparison_upload_state"
        assert len(open_uploads()) == 1, "only the upload that was open before the cancel; the refused part opened none"

    def test_a_confirmation_after_the_cancel_is_a_conflict_and_makes_no_version(self, h: Harness) -> None:
        upload_id = h.proposed({"Alpha": 1})
        only = h.sets(upload_id)[0]
        h.cancel(upload_id)
        with pytest.raises(DomainError) as refused:
            h.confirm(upload_id, only)
        assert refused.value.code is ErrorCode.CONFLICT and _reason(refused.value) == "comparison_set_state"
        assert h.rows("SELECT count(*) FROM document_version") == [(0,)]


class TestTheActIsKeyedAndAnExperts:
    def test_a_repeat_under_the_same_key_answers_the_first_outcome_and_does_nothing_more(self, h: Harness) -> None:
        upload_id, _ids = _mixed_batch(h)
        first = h.cancel(upload_id, key="cancel-1")
        work_before = h.work(upload_id)
        again = h.cancel(upload_id, key="cancel-1")
        assert (first.state, again.state) == ("cancelled", "cancelled")
        assert h.work(upload_id) == work_before, "no second sweep, nothing re-run"

    def test_the_same_key_for_another_batch_is_a_key_reuse(self, h: Harness) -> None:
        upload_id, _ids = _mixed_batch(h)
        h.cancel(upload_id, key="shared-key")
        other = h.proposed({"Beta": 1})
        with pytest.raises(DomainError) as refused:
            h.cancel(other, key="shared-key")
        assert refused.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE
        assert h.state(other) == "proposed"

    def test_a_refused_cancel_leaves_no_record_so_the_key_can_be_used_again(self, h: Harness) -> None:
        upload_id = h.proposed({"Alpha": 1})
        h.cancel(upload_id)
        with pytest.raises(DomainError):
            h.cancel(upload_id, key="retry-me")
        assert h.rows("SELECT count(*) FROM command_record WHERE command_type = 'cancel_comparison_upload' "
                      "AND idempotency_key = 'retry-me'") == [(0,)]

    def test_an_administrator_without_the_expert_role_is_refused_and_nothing_changes(self, h: Harness) -> None:
        upload_id, _ids = _mixed_batch(h)
        with pytest.raises(DomainError) as refused:
            h.cancel(upload_id, roles=ADMIN, key="admin-cancel")
        assert refused.value.code is ErrorCode.PERMISSION_DENIED
        assert h.state(upload_id) == "uploading"
        assert h.rows("SELECT count(*) FROM command_record WHERE idempotency_key = 'admin-cancel'") == [(0,)]
        assert h.work(upload_id, kind="upload_abort_sweep") == []

    def test_an_unknown_batch_is_not_found(self, h: Harness) -> None:
        with pytest.raises(DomainError) as refused:
            h.cancel("cbt_01ARZ3NDEKTSV4RRFFQ69G5FAV")
        assert refused.value.code is ErrorCode.NOT_FOUND


class TestAnAbandonedUploadIsCancelledByTheDrive:
    def test_a_batch_untouched_for_a_day_is_cancelled_its_slot_freed_and_its_upload_swept(
        self, h: Harness, queue: Queue, open_uploads
    ) -> None:
        upload_id, _ids = _mixed_batch(h)
        h.make_idle(upload_id, seconds=24 * 3600 + 60)
        h.make_due("comparison_batch_drive")
        steps = queue.run_all()
        assert ("comparison_batch_drive", "succeeded") in steps and ("upload_abort_sweep", "succeeded") in steps
        assert h.state(upload_id) == "cancelled"
        assert open_uploads() == []
        [sweep] = h.work(upload_id, kind="upload_abort_sweep")
        assert sweep["payload"]["reason"] == "abandoned"

    def test_a_batch_that_is_still_in_use_is_not_abandoned(self, h: Harness, queue: Queue, open_uploads) -> None:
        upload_id, _ids = _mixed_batch(h)
        h.make_idle(upload_id, seconds=23 * 3600)
        h.make_due("comparison_batch_drive")
        assert queue.run_all() == [("comparison_batch_drive", "queued")], "it yielded and will look again"
        assert h.state(upload_id) == "uploading" and len(open_uploads()) == 1

    def test_a_proposed_batch_waiting_for_its_person_is_not_abandoned(self, h: Harness, queue: Queue) -> None:
        upload_id = h.proposed({"Alpha": 1})
        h.make_idle(upload_id, seconds=3 * 24 * 3600)
        h.make_due("comparison_batch_drive")
        queue.run_all()
        assert h.state(upload_id) == "proposed"
