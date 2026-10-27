"""`CMP-INGEST-01`: completing a file -- verified whole against its declaration, read, placed -- on the real services.

The two integrity refusals leave **nothing published**: the bucket is read through a plain ``boto3`` client (no canonical
object, no temporary object, no multipart upload still open), the Blob row of the content is not ``available``, and the file
is ``failed`` with its reason and no part rows, so the client sends it again. A document outside the comparison envelope is
the other kind of failure: the same bytes would be refused again, so the file is not retried and the rest of the batch goes
on. Crashes between the steps leave state the next call resumes from.
"""

from __future__ import annotations

import pytest

from auditmanager.ingest.comparison_pdf.public import PART_BYTES, ComparisonUploadService
from auditmanager.ingest.comparison_pdf.reading import PdfReading
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import UploadedPart, abort_multipart_sweep, declare_blob, parse_blob_role
from tests.integration.ingest.comparison_pdf.support import (
    CORPUS,
    complete,
    create,
    declare,
    padded_pdf,
    parts_of,
    send,
    sha256,
    table,
    upload_batch,
    vs1,
)

BIG = padded_pdf(PART_BYTES + 12_345)


def _refused(call) -> DomainError:
    with pytest.raises(DomainError) as caught:
        call()
    return caught.value


def _file(service, view, name):
    return next(f for f in service.get_upload(upload_id=view.upload_id).files or () if f.display_name == name)


class TestAMultiPartFile:
    def test_two_parts_are_assembled_verified_published_and_read(
        self, comparison, project, user, session_factory, bucket_keys, open_uploads
    ) -> None:
        view = create(comparison, str(project.project_uid), {"big.pdf": BIG}, user=user)
        file_id = view.files[0].file_id
        send(comparison, view.upload_id, file_id, BIG, key="k", user=user)
        assert [f.parts_staged for f in comparison.get_upload(upload_id=view.upload_id).files or ()] == [2]
        done = complete(comparison, view.upload_id, file_id, key="done", user=user)
        assert (done.state, done.parts_staged, done.failure_reason) == ("verified", 2, None)
        keys = bucket_keys()
        assert len(keys) == 1 and keys[0].startswith("blobs/"), keys  # the canonical object only: no temporary, no part
        assert open_uploads() == []
        with session_factory() as session:
            assert table(session, "SELECT state, size_bytes, sha256 FROM blob") == [("available", len(BIG), sha256(BIG))]
            assert table(session, "SELECT state, blob_id IS NOT NULL FROM comparison_upload_file") == [("verified", True)]
            assert table(session, "SELECT part_number, state FROM comparison_upload_part ORDER BY part_number") == [
                (1, "completed"), (2, "completed")]

    def test_a_file_with_a_text_layer_and_no_designation_is_grouped_by_its_name_and_says_so(
        self, comparison, project, user
    ) -> None:
        view = create(comparison, str(project.project_uid), {"Раздел ЭМ (1).pdf": BIG}, user=user)
        send(comparison, view.upload_id, view.files[0].file_id, BIG, key="k", user=user)
        complete(comparison, view.upload_id, view.files[0].file_id, key="done", user=user)
        only = comparison.get_proposal(upload_id=view.upload_id).sets[0]
        assert (only.designation, only.warnings) == (None, ("no_stamp_found",))


class TestAnIntegrityFailureLeavesNothingPublished:
    def _declared_wrong(self, comparison, project, user, *, data: bytes, declared_sha: str | None = None, declared_size: int | None = None):
        from auditmanager.ingest.comparison_pdf.public import DeclaredFileRequest

        view = comparison.create_upload(
            project_uid=str(project.project_uid),
            files=[DeclaredFileRequest("a.pdf", declared_size or len(data), declared_sha or sha256(data))],
            user_uid=user, actor_label="Эксперт", idempotency_key="decl",
        )
        return view, view.files[0].file_id

    def _nothing_published(self, bucket_keys, open_uploads, session_factory, *digests: str) -> None:
        assert bucket_keys() == [], "an object is left in the bucket"
        assert open_uploads() == [], "a multipart upload is left open"
        with session_factory() as session:
            states = table(session, "SELECT sha256, state FROM blob")
        assert all(state != "available" for _sha, state in states), states

    def test_a_digest_that_differs_is_storage_integrity_error_and_the_file_is_failed(
        self, comparison, project, user, session_factory, bucket_keys, open_uploads
    ) -> None:
        real = vs1()["v1.pdf"]
        wrong = vs1()["v2.pdf"][: len(real)].ljust(len(real), b" ")
        view, file_id = self._declared_wrong(comparison, project, user, data=wrong, declared_sha=sha256(real), declared_size=len(real))
        send(comparison, view.upload_id, file_id, wrong, key="k", user=user)
        refused = _refused(lambda: complete(comparison, view.upload_id, file_id, key="done", user=user))
        assert refused.code is ErrorCode.STORAGE_INTEGRITY_ERROR
        assert refused.detail_fields == {"expected_sha256": sha256(real), "actual_sha256": sha256(wrong)}
        failed = _file(comparison, view, "a.pdf")
        assert (failed.state, failed.failure_reason, failed.parts_staged) == ("failed", "comparison_file_sha256", 0)
        self._nothing_published(bucket_keys, open_uploads, session_factory)
        with session_factory() as session:
            assert table(session, "SELECT count(*) FROM comparison_upload_part") == [(0,)]
            assert table(session, "SELECT blob_id FROM comparison_upload_file") == [(None,)]

    def test_a_size_that_differs_is_the_files_size_reason_and_carries_no_digest(
        self, comparison, project, user, session_factory, bucket_keys, open_uploads
    ) -> None:
        data = vs1()["v1.pdf"]
        view, file_id = self._declared_wrong(comparison, project, user, data=data, declared_size=len(data) + 5)
        send(comparison, view.upload_id, file_id, data, key="k", user=user)
        refused = _refused(lambda: complete(comparison, view.upload_id, file_id, key="done", user=user))
        assert refused.code is ErrorCode.STORAGE_INTEGRITY_ERROR
        assert refused.detail_fields == {"role": "comparison_file_size"}
        assert _file(comparison, view, "a.pdf").failure_reason == "comparison_file_size"
        with session_factory() as session:
            assert table(session, "SELECT count(*) FROM comparison_upload_part") == [(0,)]
            assert all(state != "available" for _s, state in table(session, "SELECT sha256, state FROM blob"))

    def test_the_client_sends_it_again_and_it_is_verified(
        self, comparison, project, user, session_factory, bucket_keys
    ) -> None:
        real = vs1()["v1.pdf"]
        wrong = real[:-1] + b"X"
        view, file_id = self._declared_wrong(comparison, project, user, data=wrong, declared_sha=sha256(real), declared_size=len(real))
        send(comparison, view.upload_id, file_id, wrong, key="k1", user=user)
        _refused(lambda: complete(comparison, view.upload_id, file_id, key="done1", user=user))
        send(comparison, view.upload_id, file_id, real, key="k2", user=user)  # the right bytes this time
        done = complete(comparison, view.upload_id, file_id, key="done2", user=user)
        assert (done.state, done.failure_reason) == ("verified", None)
        assert len(bucket_keys()) == 1

    def test_a_completion_with_a_part_missing_is_refused_and_leaves_the_upload_as_it_was(
        self, comparison, project, user, open_uploads
    ) -> None:
        view = create(comparison, str(project.project_uid), {"big.pdf": BIG}, user=user)
        file_id = view.files[0].file_id
        send(comparison, view.upload_id, file_id, BIG, key="k", user=user, only=[1])
        refused = _refused(lambda: complete(comparison, view.upload_id, file_id, key="done", user=user))
        assert refused.code is ErrorCode.VALIDATION_FAILED and refused.detail_fields["field"] == "parts"
        send(comparison, view.upload_id, file_id, BIG, key="k", user=user, only=[2])  # the missing part arrives
        assert complete(comparison, view.upload_id, file_id, key="done2", user=user).state == "verified"

    def test_a_completion_with_no_part_at_all(self, comparison, project, user) -> None:
        view = create(comparison, str(project.project_uid), {"a.pdf": vs1()["v1.pdf"]}, user=user)
        refused = _refused(lambda: complete(comparison, view.upload_id, view.files[0].file_id, key="done", user=user))
        assert refused.code is ErrorCode.VALIDATION_FAILED and refused.detail_fields["field"] == "parts"

    def test_a_late_part_of_a_file_whose_parts_were_swept_is_a_staged_upload_lost(
        self, comparison, store, project, user, session_factory, open_uploads
    ) -> None:
        """The abort sweep (a work handler's) marks the database first and then aborts at the store; if the
        store's upload is gone the completion says so, the file is failed (retryable) and the parts are re-sent."""
        data = vs1()["v1.pdf"]
        view = create(comparison, str(project.project_uid), {"a.pdf": data}, user=user)
        file_id = view.files[0].file_id
        send(comparison, view.upload_id, file_id, data, key="k", user=user)
        with session_factory() as session:
            token = table(session, "SELECT multipart_token FROM comparison_upload_file")[0][0]
        assert abort_multipart_sweep(store, [token]).aborted == (token,)
        refused = _refused(lambda: complete(comparison, view.upload_id, file_id, key="done", user=user))
        assert refused.code.value == "staged_upload_lost"
        assert _file(comparison, view, "a.pdf").failure_reason == "staged_upload_lost"
        send(comparison, view.upload_id, file_id, data, key="k2", user=user)
        assert complete(comparison, view.upload_id, file_id, key="done2", user=user).state == "verified"


class TestADocumentOutsideTheEnvelopeIsRefusedForGood:
    def _refused_file(self, comparison, project, user, name, data):
        view = create(comparison, str(project.project_uid), {name: data}, user=user)
        send(comparison, view.upload_id, view.files[0].file_id, data, key="k", user=user)
        return view, _refused(lambda: complete(comparison, view.upload_id, view.files[0].file_id, key="done", user=user))

    def test_an_encrypted_pdf_is_validation_failed_with_the_envelopes_own_reason(self, comparison, project, user, session_factory) -> None:
        data = (CORPUS.parent / "synthetic" / "ar" / "negative" / "encrypted.pdf").read_bytes()
        view, refused = self._refused_file(comparison, project, user, "enc.pdf", data)
        assert refused.code is ErrorCode.VALIDATION_FAILED
        assert (refused.detail_fields["field"], refused.detail_fields["constraint"]) == ("content", "not_encrypted")
        failed = _file(comparison, view, "enc.pdf")
        assert (failed.state, failed.failure_reason, failed.set_id) == ("failed", "content_not_encrypted", None)
        with session_factory() as session:
            # The bytes were verified before they were read, so the Blob is published and the failed file names it
            # (the store has no delete); it never became a version.
            assert table(session, "SELECT state FROM blob") == [("available",)]
            assert table(session, "SELECT blob_id IS NOT NULL FROM comparison_upload_file") == [(True,)]
            assert table(session, "SELECT count(*) FROM document_version") == [(0,)]

    def test_the_refusal_is_recorded_under_its_key_and_a_repeat_answers_it(self, comparison, project, user) -> None:
        data = (CORPUS.parent / "synthetic" / "ar" / "negative" / "encrypted.pdf").read_bytes()
        view, first = self._refused_file(comparison, project, user, "enc.pdf", data)
        again = _refused(lambda: complete(comparison, view.upload_id, view.files[0].file_id, key="done", user=user))
        assert again.code is first.code

    def test_the_same_bytes_are_not_taken_again(self, comparison, project, user) -> None:
        data = (CORPUS.parent / "synthetic" / "ar" / "negative" / "encrypted.pdf").read_bytes()
        view, _refused_once = self._refused_file(comparison, project, user, "enc.pdf", data)
        late = _refused(lambda: comparison.put_part(upload_id=view.upload_id, file_id=view.files[0].file_id, part_number=1,
                                                    content=data, user_uid=user, idempotency_key="again"))
        assert late.code is ErrorCode.CONFLICT and late.detail_fields["conflict_reason"] == "comparison_upload_state"

    def test_a_declared_page_count_that_the_document_does_not_have_is_refused(self, comparison, project, user) -> None:
        data = vs1()["v1.pdf"]  # six pages
        view = comparison.create_upload(project_uid=str(project.project_uid), files=[declare("a.pdf", data, page_count=7)],
                                        user_uid=user, actor_label="Эксперт", idempotency_key="decl")
        send(comparison, view.upload_id, view.files[0].file_id, data, key="k", user=user)
        refused = _refused(lambda: complete(comparison, view.upload_id, view.files[0].file_id, key="done", user=user))
        assert (refused.detail_fields["field"], refused.detail_fields["constraint"]) == ("page_count", "declared_page_count")
        assert _file(comparison, view, "a.pdf").failure_reason == "content_declared_page_count"

    def test_the_declared_page_count_that_matches_is_accepted(self, comparison, project, user) -> None:
        data = vs1()["v1.pdf"]
        view = comparison.create_upload(project_uid=str(project.project_uid), files=[declare("a.pdf", data, page_count=6)],
                                        user_uid=user, actor_label="Эксперт", idempotency_key="decl")
        send(comparison, view.upload_id, view.files[0].file_id, data, key="k", user=user)
        assert complete(comparison, view.upload_id, view.files[0].file_id, key="done", user=user).state == "verified"

    def test_the_rest_of_the_batch_goes_on_without_the_refused_file(self, comparison, project, user) -> None:
        good = vs1()
        enc = (CORPUS.parent / "synthetic" / "ar" / "negative" / "encrypted.pdf").read_bytes()
        view = create(comparison, str(project.project_uid), {"enc.pdf": enc, **good}, user=user)
        ids = {f.display_name: f.file_id for f in view.files or ()}
        for index, (name, data) in enumerate({"enc.pdf": enc, **good}.items()):
            send(comparison, view.upload_id, ids[name], data, key=f"k{index}", user=user)
            try:
                complete(comparison, view.upload_id, ids[name], key=f"d{index}", user=user)
            except DomainError:
                assert name == "enc.pdf"
        assert comparison.get_upload(upload_id=view.upload_id).state == "proposed"
        proposal = comparison.get_proposal(upload_id=view.upload_id)
        assert len(proposal.sets) == 1 and len(proposal.sets[0].files) == 5

    def test_a_batch_in_which_every_file_was_refused_has_nothing_to_confirm_and_is_completed(self, comparison, project, user) -> None:
        enc = (CORPUS.parent / "synthetic" / "ar" / "negative" / "encrypted.pdf").read_bytes()
        view, _refused_once = self._refused_file(comparison, project, user, "enc.pdf", enc)
        after = comparison.get_upload(upload_id=view.upload_id)
        assert after.state == "completed" and comparison.get_proposal(upload_id=view.upload_id).sets == ()


class TestTheBatchIsProposedWhenEveryFileIsSettled:
    def test_one_file_short_keeps_the_batch_uploading_and_the_last_one_proposes_it(self, comparison, project, user) -> None:
        files = vs1()
        view = create(comparison, str(project.project_uid), files, user=user)
        ids = {f.display_name: f.file_id for f in view.files or ()}
        names = list(files)
        for name in names[:-1]:
            send(comparison, view.upload_id, ids[name], files[name], key=name.replace(".", ""), user=user)
            complete(comparison, view.upload_id, ids[name], key=name.replace(".", "") + "d", user=user)
        middle = comparison.get_upload(upload_id=view.upload_id)
        assert middle.state == "uploading"
        sets = comparison.get_proposal(upload_id=view.upload_id).sets
        assert [s.state for s in sets] == ["uploading"] and len(sets[0].files) == 4
        last = names[-1]
        send(comparison, view.upload_id, ids[last], files[last], key="last", user=user)
        complete(comparison, view.upload_id, ids[last], key="lastd", user=user)
        assert comparison.get_upload(upload_id=view.upload_id).state == "proposed"
        assert [s.state for s in comparison.get_proposal(upload_id=view.upload_id).sets] == ["needs_confirmation"]

    def test_a_file_that_failed_its_integrity_keeps_the_batch_uploading_until_it_is_sent_again(self, comparison, project, user) -> None:
        good = vs1()
        view = create(comparison, str(project.project_uid), {"a.pdf": good["v1.pdf"], "b.pdf": good["v2.pdf"]}, user=user)
        ids = {f.display_name: f.file_id for f in view.files or ()}
        send(comparison, view.upload_id, ids["a.pdf"], good["v1.pdf"], key="a", user=user)
        complete(comparison, view.upload_id, ids["a.pdf"], key="ad", user=user)
        send(comparison, view.upload_id, ids["b.pdf"], good["v2.pdf"][:-1] + b"X", key="b", user=user)
        _refused(lambda: complete(comparison, view.upload_id, ids["b.pdf"], key="bd", user=user))
        assert comparison.get_upload(upload_id=view.upload_id).state == "uploading"
        send(comparison, view.upload_id, ids["b.pdf"], good["v2.pdf"], key="b2", user=user)
        complete(comparison, view.upload_id, ids["b.pdf"], key="bd2", user=user)
        assert comparison.get_upload(upload_id=view.upload_id).state == "proposed"

    def test_two_files_completed_at_once_are_both_placed(self, comparison, project, user) -> None:
        from concurrent.futures import ThreadPoolExecutor

        files = vs1()
        view = create(comparison, str(project.project_uid), files, user=user)
        ids = {f.display_name: f.file_id for f in view.files or ()}
        for name, data in files.items():
            send(comparison, view.upload_id, ids[name], data, key=name.replace(".", ""), user=user)

        def finish(name: str):
            return complete(comparison, view.upload_id, ids[name], key=name.replace(".", "") + "d", user=user)

        with ThreadPoolExecutor(max_workers=5) as pool:
            results = list(pool.map(finish, files))
        assert [r.state for r in results] == ["verified"] * 5
        proposal = comparison.get_proposal(upload_id=view.upload_id)
        assert comparison.get_upload(upload_id=view.upload_id).state == "proposed"
        assert len(proposal.sets) == 1 and len(proposal.sets[0].files) == 5


class TestRecovery:
    def test_a_completion_is_idempotent_by_state(self, watched, spy, project, user) -> None:
        data = vs1()["v1.pdf"]
        view = create(watched, str(project.project_uid), {"a.pdf": data}, user=user)
        send(watched, view.upload_id, view.files[0].file_id, data, key="k", user=user)
        first = complete(watched, view.upload_id, view.files[0].file_id, key="d1", user=user)
        calls = spy.count("complete_multipart")
        again = complete(watched, view.upload_id, view.files[0].file_id, key="d2", user=user)
        assert first.state == again.state == "verified" and spy.count("complete_multipart") == calls == 1

    def test_the_same_key_for_another_file_is_refused(self, comparison, project, user) -> None:
        files = vs1()
        view = create(comparison, str(project.project_uid), {"a.pdf": files["v1.pdf"], "b.pdf": files["v2.pdf"]}, user=user)
        ids = {f.display_name: f.file_id for f in view.files or ()}
        for name, key in (("a.pdf", "ka"), ("b.pdf", "kb")):
            send(comparison, view.upload_id, ids[name], files["v1.pdf" if name == "a.pdf" else "v2.pdf"], key=key, user=user)
        complete(comparison, view.upload_id, ids["a.pdf"], key="same", user=user)
        refused = _refused(lambda: complete(comparison, view.upload_id, ids["b.pdf"], key="same", user=user))
        assert refused.code is ErrorCode.IDEMPOTENCY_KEY_REUSE

    def test_a_reader_that_fails_after_the_publication_leaves_a_file_the_next_call_resumes_at_the_reading(
        self, store, session_factory, project, user
    ) -> None:
        calls: list[int] = []

        def flaky(handle, **kwargs):
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError("the PDF reader process did not start")
            from auditmanager.ingest.comparison_pdf.reading import read_pdf

            return read_pdf(handle, **kwargs)

        from auditmanager.ingest.comparison_pdf.public import ComparisonUploadService

        service = ComparisonUploadService(store, session_factory=session_factory, read=flaky)
        data = vs1()["v1.pdf"]
        view = create(service, str(project.project_uid), {"a.pdf": data}, user=user)
        file_id = view.files[0].file_id
        send(service, view.upload_id, file_id, data, key="k", user=user)
        with pytest.raises(RuntimeError):
            complete(service, view.upload_id, file_id, key="d1", user=user)
        with session_factory() as session:
            assert table(session, "SELECT state, blob_id IS NOT NULL FROM comparison_upload_file") == [("uploading", True)]
            assert table(session, "SELECT state FROM blob") == [("available",)]
        done = complete(service, view.upload_id, file_id, key="d2", user=user)
        assert done.state == "verified" and len(calls) == 2

    def test_a_process_killed_after_the_publication_and_before_the_blob_was_marked_is_recognised(
        self, comparison, store, session_factory, project, user
    ) -> None:
        """The store published the object (its temporary upload is gone) but nothing was committed after it: the
        Blob is ``verifying``, the file has no blob. The completion finds the published Blob by its identity."""
        from auditmanager.storage.public import BlobMetadataRepository

        data = vs1()["v1.pdf"]
        view = create(comparison, str(project.project_uid), {"a.pdf": data}, user=user)
        file_id = view.files[0].file_id
        send(comparison, view.upload_id, file_id, data, key="k", user=user)
        with session_factory() as session:
            token = table(session, "SELECT multipart_token FROM comparison_upload_file")[0][0]
            parts = table(session, "SELECT part_number, size_bytes, sha256, etag FROM comparison_upload_part ORDER BY part_number")

        def checkpoint(verified) -> None:
            with session_factory() as session:
                BlobMetadataRepository().record_verified(session, verified)
                session.commit()

        store.complete_multipart(
            token, [UploadedPart(*row) for row in parts], declared_sha256=sha256(data), declared_size=len(data),
            role=parse_blob_role("comparison_pdf"), media_type="application/pdf", before_publish=checkpoint,
        )
        with session_factory() as session:
            assert table(session, "SELECT state FROM blob") == [("verifying",)]
            assert table(session, "SELECT blob_id FROM comparison_upload_file") == [(None,)]
        done = complete(comparison, view.upload_id, file_id, key="d", user=user)
        assert done.state == "verified"
        with session_factory() as session:
            assert table(session, "SELECT state FROM blob") == [("available",)]
