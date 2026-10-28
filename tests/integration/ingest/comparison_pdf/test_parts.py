"""`CMP-INGEST-01`: sending a file in parts (ADR-0025 decision 10), on the real PostgreSQL and the real MinIO.

The order is the design: **the token is persisted and the part has a database owner before the first byte moves**; a part
is refused before the store is asked (a number the declared size does not need, a size that is not the part size, a batch or
a file that cannot take a part); the same part sent again replays its receipt without a second upload. Assertions about the
store are made through a plain ``boto3`` client and through a spy that records the calls the service made, never through the
adapter's own view.
"""

from __future__ import annotations

import pytest

from auditmanager.ingest.comparison_pdf.public import PART_BYTES
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.errors import StorageUnavailableError
from tests.integration.ingest.comparison_pdf.support import create, padded_pdf, sha256, table, vs1

BIG = padded_pdf(PART_BYTES + 12_345)  # two parts: one 16 MiB, one small (S3 accepts a small last part)


def _first_file(view):
    return (view.files or ())[0].file_id


def _refused(call) -> DomainError:
    with pytest.raises(DomainError) as caught:
        call()
    return caught.value


@pytest.fixture
def one(watched, project, user):
    """A batch of one small file, and one of the two-part file."""
    small = vs1()["v1.pdf"]
    view = create(watched, str(project.project_uid), {"small.pdf": small, "big.pdf": BIG}, user=user)
    ids = {f.display_name: f.file_id for f in view.files or ()}
    return view, ids, small


class TestTheOwnerComesFirst:
    def test_the_token_is_persisted_and_the_part_row_exists_before_the_store_is_asked(
        self, one, watched, spy, session_factory, bucket_keys, user
    ) -> None:
        view, ids, small = one
        spy.fail["begin_multipart"] = StorageUnavailableError(dependency="blob_storage")
        refused = _refused(lambda: watched.put_part(upload_id=view.upload_id, file_id=ids["small.pdf"], part_number=1,
                                                     content=small, user_uid=user, idempotency_key="p1"))
        assert refused.code is ErrorCode.DEPENDENCY_UNAVAILABLE
        with session_factory() as session:
            (token, state), = table(session, "SELECT multipart_token, state FROM comparison_upload_file WHERE comparison_upload_file_id = :f", f=ids["small.pdf"])
            parts = table(session, "SELECT part_number, state, size_bytes FROM comparison_upload_part")
            blob = table(session, "SELECT state, size_bytes FROM blob")
        assert token is not None and token.startswith("mpu-") and state == "uploading"
        assert parts == [(1, "declared", None)]  # owned, not yet staged
        assert blob == [("temporary", len(small))]  # the declared Blob: the database owner of the bytes
        assert bucket_keys() == [] and spy.count("upload_part") == 0

    def test_the_part_is_sent_when_the_store_is_back_with_the_token_the_first_attempt_persisted(
        self, one, watched, spy, session_factory, user
    ) -> None:
        view, ids, small = one
        spy.fail["begin_multipart"] = StorageUnavailableError(dependency="blob_storage")
        _refused(lambda: watched.put_part(upload_id=view.upload_id, file_id=ids["small.pdf"], part_number=1, content=small,
                                           user_uid=user, idempotency_key="p1"))
        with session_factory() as session:
            token = table(session, "SELECT multipart_token FROM comparison_upload_file WHERE multipart_token IS NOT NULL")[0][0]
        receipt = watched.put_part(upload_id=view.upload_id, file_id=ids["small.pdf"], part_number=1, content=small,
                                   user_uid=user, idempotency_key="p1")
        assert (receipt.part_number, receipt.size_bytes, receipt.sha256) == (1, len(small), sha256(small))
        with session_factory() as session:
            assert table(session, "SELECT multipart_token FROM comparison_upload_file WHERE multipart_token IS NOT NULL")[0][0] == token
            assert table(session, "SELECT part_number, state, size_bytes, sha256 FROM comparison_upload_part") == [
                (1, "staged", len(small), sha256(small))]

    def test_the_file_moves_to_uploading_with_its_first_part_and_the_batch_reads_the_staged_count(
        self, one, watched, user
    ) -> None:
        view, ids, small = one
        watched.put_part(upload_id=view.upload_id, file_id=ids["small.pdf"], part_number=1, content=small, user_uid=user,
                         idempotency_key="p1")
        read = {f.display_name: f for f in watched.get_upload(upload_id=view.upload_id).files or ()}
        assert (read["small.pdf"].state, read["small.pdf"].parts_staged) == ("uploading", 1)
        assert (read["big.pdf"].state, read["big.pdf"].parts_staged) == ("declared", 0)


class TestARefusedPartNeverReachesTheStore:
    def _expect(self, watched, spy, session_factory, view, file_id, number, content, user, constraint, key="p"):
        before = list(spy.calls)
        refused = _refused(lambda: watched.put_part(upload_id=view.upload_id, file_id=file_id, part_number=number,
                                                     content=content, user_uid=user, idempotency_key=key))
        assert refused.code is ErrorCode.VALIDATION_FAILED
        assert (refused.detail_fields["field"], refused.detail_fields["constraint"]) == ("content", constraint)
        assert spy.calls == before, "the store was asked about a part that was refused"
        with session_factory() as session:
            assert table(session, "SELECT count(*) FROM comparison_upload_part") == [(0,)]
            assert table(session, "SELECT multipart_token FROM comparison_upload_file") == [(None,), (None,)]

    @pytest.mark.parametrize("number", [0, 2, 17])
    def test_a_part_number_the_declared_size_does_not_need(self, one, watched, spy, session_factory, user, number) -> None:
        view, ids, small = one
        self._expect(watched, spy, session_factory, view, ids["small.pdf"], number, small, user, "comparison_part_number")

    def test_an_empty_body(self, one, watched, spy, session_factory, user) -> None:
        view, ids, _small = one
        self._expect(watched, spy, session_factory, view, ids["small.pdf"], 1, b"", user, "comparison_part_size")

    def test_a_body_over_sixteen_mebibytes(self, one, watched, spy, session_factory, user) -> None:
        view, ids, _small = one
        self._expect(watched, spy, session_factory, view, ids["big.pdf"], 1, b"x" * (PART_BYTES + 1), user, "comparison_part_size")

    def test_a_part_in_the_middle_of_a_file_that_is_not_one_part_long(self, one, watched, spy, session_factory, user) -> None:
        view, ids, _small = one
        self._expect(watched, spy, session_factory, view, ids["big.pdf"], 1, BIG[: PART_BYTES - 1], user, "comparison_part_size")

    def test_the_last_part_may_be_short_but_not_longer_than_a_part(self, one, watched, spy, session_factory, user) -> None:
        view, ids, small = one
        self._expect(watched, spy, session_factory, view, ids["small.pdf"], 1, b"x" * (PART_BYTES + 1), user, "comparison_part_size")

    def test_a_file_or_batch_that_is_unknown_or_not_this_ones_is_not_found(self, one, watched, project, user) -> None:
        view, ids, small = one
        other = create(watched, str(project.project_uid), {"x.pdf": b"%PDF-1.7 x"}, user=f"usr_{'0' * 26}", key="other")
        for upload_id, file_id, aggregate in (
            ("cbt_" + "0" * 26, ids["small.pdf"], "ComparisonUpload"),
            (view.upload_id, "cuf_" + "0" * 26, "ComparisonUploadFile"),
            (view.upload_id, (other.files or ())[0].file_id, "ComparisonUploadFile"),
        ):
            refused = _refused(lambda: watched.put_part(upload_id=upload_id, file_id=file_id, part_number=1, content=small,
                                                         user_uid=user, idempotency_key="nf"))
            assert refused.code is ErrorCode.NOT_FOUND and refused.detail_fields == {"aggregate_type": aggregate}


class TestReplayAndReplacement:
    def test_the_same_part_again_replays_the_receipt_without_a_second_upload(self, one, watched, spy, user) -> None:
        view, ids, small = one
        first = watched.put_part(upload_id=view.upload_id, file_id=ids["small.pdf"], part_number=1, content=small,
                                 user_uid=user, idempotency_key="p1")
        sent = spy.count("upload_part")
        again_new_key = watched.put_part(upload_id=view.upload_id, file_id=ids["small.pdf"], part_number=1, content=small,
                                         user_uid=user, idempotency_key="p2")
        again_same_key = watched.put_part(upload_id=view.upload_id, file_id=ids["small.pdf"], part_number=1, content=small,
                                          user_uid=user, idempotency_key="p1")
        assert first == again_new_key == again_same_key and spy.count("upload_part") == sent == 1

    def test_the_same_key_with_other_bytes_is_refused(self, one, watched, user) -> None:
        view, ids, small = one
        watched.put_part(upload_id=view.upload_id, file_id=ids["small.pdf"], part_number=1, content=small, user_uid=user,
                         idempotency_key="p1")
        refused = _refused(lambda: watched.put_part(upload_id=view.upload_id, file_id=ids["small.pdf"], part_number=1,
                                                     content=small[:-1], user_uid=user, idempotency_key="p1"))
        assert refused.code is ErrorCode.IDEMPOTENCY_KEY_REUSE

    def test_other_bytes_under_a_new_key_replace_the_part(self, one, watched, spy, session_factory, user) -> None:
        view, ids, small = one
        watched.put_part(upload_id=view.upload_id, file_id=ids["small.pdf"], part_number=1, content=small, user_uid=user,
                         idempotency_key="p1")
        replaced = watched.put_part(upload_id=view.upload_id, file_id=ids["small.pdf"], part_number=1, content=small[:-1],
                                    user_uid=user, idempotency_key="p2")
        assert replaced.size_bytes == len(small) - 1 and spy.count("upload_part") == 2
        with session_factory() as session:
            assert table(session, "SELECT size_bytes, sha256 FROM comparison_upload_part") == [(len(small) - 1, sha256(small[:-1]))]


class TestAPartThatCannotBeTaken:
    def test_a_part_after_the_file_was_completed(self, one, watched, user) -> None:
        view, ids, small = one
        watched.put_part(upload_id=view.upload_id, file_id=ids["small.pdf"], part_number=1, content=small, user_uid=user, idempotency_key="p1")
        watched.complete_file(upload_id=view.upload_id, file_id=ids["small.pdf"], user_uid=user, idempotency_key="c1")
        refused = _refused(lambda: watched.put_part(upload_id=view.upload_id, file_id=ids["small.pdf"], part_number=1, content=small,
                                                     user_uid=user, idempotency_key="late"))
        assert refused.code is ErrorCode.CONFLICT and refused.detail_fields["conflict_reason"] == "comparison_upload_state"

    def test_a_part_of_a_batch_that_is_no_longer_uploading(self, comparison, project, user, session_factory) -> None:
        from sqlalchemy import text

        small = vs1()["v1.pdf"]
        view = create(comparison, str(project.project_uid), {"a.pdf": small}, user=user)
        with session_factory() as session:
            session.execute(text("UPDATE comparison_upload SET state = 'proposed' WHERE comparison_upload_id = :i"), {"i": view.upload_id})
            session.commit()
        refused = _refused(lambda: comparison.put_part(upload_id=view.upload_id, file_id=_first_file(view), part_number=1,
                                                       content=small, user_uid=user, idempotency_key="p1"))
        assert refused.code is ErrorCode.CONFLICT and refused.detail_fields["conflict_reason"] == "comparison_upload_state"
