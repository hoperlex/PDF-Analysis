"""Multipart staging against a real S3-compatible service (`CMP-STORAGE-PARTS-01`, ADR-0025 decision 10).

Every assertion about what the bucket holds is made through the independent boto3 client of
``conftest.raw_s3``, never through the adapter under test: the keys of the bucket and the in-progress
uploads of the bucket. A guard that only the adapter can see is not shown to fire.

The three mutation proofs the brief names are the tests marked in their docstrings:

* a completed object whose bytes do not match the declared SHA-256 is refused and leaves nothing
  (``test_a_wrong_digest_is_refused_and_leaves_no_object``);
* an aborted upload leaves no object (``test_an_aborted_upload_leaves_nothing_and_takes_no_more_parts``);
* parts out of order or missing are refused at completion
  (``TestPartsAreRefusedAtCompletion``).

The expected values are literals, not the module's own constants: both sides of a comparison built
from one constant move together under mutation.
"""

from __future__ import annotations

import hashlib
import io
from typing import Any, Iterator

import pytest

from auditmanager.storage import (
    ROLE_SOURCE_DOCUMENT,
    BlobIntegrityError,
    BlobMetadataInvalidError,
    BlobNotFoundError,
    ChecksumMismatchError,
    MultipartPartError,
    MultipartPartsError,
    MultipartStaging,
    S3BlobStore,
    SizeMismatchError,
    StorageUnavailableError,
    TemporaryBlobLostError,
    UploadedPart,
    abort_multipart_sweep,
    derive_blob_id,
    new_multipart_token,
    sha256_of,
)
from auditmanager.storage._object_layout import canonical_key, temporary_key

MIB = 1024 * 1024
FIRST = b"1" * (5 * MIB)
SECOND = b"2" * (5 * MIB)
LAST = b"%%EOF-tail\n" * 100
WHOLE = FIRST + SECOND + LAST
MEDIA = "application/pdf"


@pytest.fixture
def open_uploads(raw_s3: Any, settings: Any):
    """The in-progress multipart uploads of the bucket, as (key, upload id) pairs."""

    def _open() -> list[tuple[str, str]]:
        page = raw_s3.list_multipart_uploads(Bucket=settings.bucket)
        return sorted((u["Key"], u["UploadId"]) for u in page.get("Uploads", []))

    return _open


@pytest.fixture
def tokens(store: S3BlobStore) -> Iterator[list[str]]:
    """Tokens a test minted, aborted at teardown so no upload outlives its test."""
    minted: list[str] = []
    yield minted
    for token in minted:
        store.abort_multipart(token)


@pytest.fixture
def staged(store: S3BlobStore, tokens: list[str]):
    """Mint a token, begin the upload and send the given parts, numbered from 1."""

    def _stage(*payloads: bytes) -> tuple[str, list[UploadedPart]]:
        token = new_multipart_token()
        tokens.append(token)
        store.begin_multipart(token)
        receipts = [
            store.upload_part(token, number, payload)
            for number, payload in enumerate(payloads, start=1)
        ]
        return token, receipts

    return _stage


def _complete(store: S3BlobStore, token: str, parts: list[UploadedPart], **override: Any):
    arguments: dict[str, Any] = {
        "declared_sha256": sha256_of(WHOLE),
        "declared_size": len(WHOLE),
        "role": ROLE_SOURCE_DOCUMENT,
        "media_type": MEDIA,
    }
    arguments.update(override)
    return store.complete_multipart(token, parts, **arguments)


def test_the_adapter_satisfies_the_multipart_port(store: S3BlobStore) -> None:
    assert isinstance(store, MultipartStaging)


class TestACompletedFileIsPublishedWhole:
    def test_three_parts_become_one_canonical_blob(
        self, store: S3BlobStore, staged: Any, bucket_keys: Any, open_uploads: Any, blobs: list
    ) -> None:
        token, receipts = staged(FIRST, SECOND, LAST)

        published = _complete(store, token, receipts)
        blobs.append(published.blob_id)

        assert published.sha256 == hashlib.sha256(WHOLE).hexdigest()
        assert published.size == len(WHOLE) == 10 * MIB + len(LAST)
        assert published.blob_id == derive_blob_id(sha256=sha256_of(WHOLE), size=len(WHOLE))
        assert store.read(published.blob_id) == WHOLE
        # The bucket holds the canonical object and nothing else: no temporary, no open upload.
        assert bucket_keys() == [canonical_key(published.blob_id)]
        assert open_uploads() == []

    def test_a_receipt_carries_the_facts_the_caller_records(
        self, staged: Any
    ) -> None:
        _, receipts = staged(FIRST, LAST)

        assert [(r.part_number, r.size_bytes, r.sha256) for r in receipts] == [
            (1, 5242880, hashlib.sha256(FIRST).hexdigest()),
            (2, len(LAST), hashlib.sha256(LAST).hexdigest()),
        ]
        # The store's own receipt for a part is the MD5 of its bytes, unquoted; the table holds it bare.
        assert [r.etag for r in receipts] == [
            hashlib.md5(FIRST).hexdigest(),
            hashlib.md5(LAST).hexdigest(),
        ]

    def test_sending_a_part_again_replays_the_receipt_and_a_new_body_replaces_it(
        self, store: S3BlobStore, staged: Any, blobs: list
    ) -> None:
        token, receipts = staged(FIRST, LAST)
        assert store.upload_part(token, 1, FIRST) == receipts[0]

        replaced = store.upload_part(token, 2, b"another tail")
        assert replaced.etag != receipts[1].etag

        whole = FIRST + b"another tail"
        published = store.complete_multipart(
            token,
            [receipts[0], replaced],
            declared_sha256=sha256_of(whole),
            declared_size=len(whole),
            role=ROLE_SOURCE_DOCUMENT,
            media_type=MEDIA,
        )
        blobs.append(published.blob_id)
        assert store.read(published.blob_id) == whole

    def test_a_stream_is_accepted_as_a_part(self, store: S3BlobStore, staged: Any) -> None:
        token, _ = staged()
        receipt = store.upload_part(token, 1, io.BytesIO(LAST))
        assert receipt.size_bytes == len(LAST)
        assert receipt.sha256 == sha256_of(LAST)

    def test_bytes_already_published_are_reused_and_leave_no_temporary(
        self, store: S3BlobStore, staged: Any, publish: Any, bucket_keys: Any
    ) -> None:
        already = publish(WHOLE)
        token, receipts = staged(FIRST, SECOND, LAST)

        again = _complete(store, token, receipts)

        assert again.blob_id == already.blob_id
        assert bucket_keys() == [canonical_key(already.blob_id)]

    def test_begin_is_idempotent(
        self, store: S3BlobStore, tokens: list[str], open_uploads: Any
    ) -> None:
        token = new_multipart_token()
        tokens.append(token)
        store.begin_multipart(token)
        store.begin_multipart(token)
        assert [key for key, _ in open_uploads()] == [temporary_key(token)]

    def test_two_uploads_opened_by_a_race_are_resolved_and_the_spare_is_aborted(
        self,
        store: S3BlobStore,
        staged: Any,
        raw_s3: Any,
        settings: Any,
        open_uploads: Any,
        blobs: list,
    ) -> None:
        token, receipts = staged(FIRST, SECOND, LAST)
        # A second `begin` that lost the race created its own upload for the same key.
        raw_s3.create_multipart_upload(Bucket=settings.bucket, Key=temporary_key(token))
        assert len(open_uploads()) == 2

        published = _complete(store, token, receipts)
        blobs.append(published.blob_id)

        assert store.read(published.blob_id) == WHOLE
        assert open_uploads() == []


class TestTheSeamBeforePublication:
    """``before_publish`` is where the caller commits ``verifying`` for the declared ``blob_id``."""

    def test_it_sees_the_verified_blob_before_anything_is_canonical(
        self, store: S3BlobStore, staged: Any, bucket_keys: Any, blobs: list
    ) -> None:
        """Mutation proof: the seam is never called."""
        token, receipts = staged(FIRST, SECOND, LAST)
        seen: list[tuple[Any, list[str]]] = []

        published = _complete(
            store, token, receipts, before_publish=lambda v: seen.append((v, bucket_keys()))
        )
        blobs.append(published.blob_id)

        ((verified, keys),) = seen
        assert verified.blob_id == published.blob_id
        assert (verified.sha256, verified.size) == (sha256_of(WHOLE), len(WHOLE))
        assert verified.upload_token == token
        # At that moment the bytes are assembled and verified but not yet canonical.
        assert keys == [temporary_key(token)]
        assert bucket_keys() == [canonical_key(published.blob_id)]

    def test_it_is_not_called_for_bytes_that_failed_the_verification(
        self, store: S3BlobStore, staged: Any
    ) -> None:
        token, receipts = staged(FIRST, SECOND, LAST)
        seen: list[Any] = []

        with pytest.raises(ChecksumMismatchError):
            _complete(
                store, token, receipts,
                declared_sha256=sha256_of(b"other"), before_publish=seen.append,
            )

        assert seen == []

    def test_a_failure_in_it_publishes_nothing_and_keeps_the_assembly_for_a_retry(
        self, store: S3BlobStore, staged: Any, bucket_keys: Any, blobs: list
    ) -> None:
        token, receipts = staged(FIRST, SECOND, LAST)

        def refuse(_: Any) -> None:
            raise RuntimeError("the database refused the checkpoint")

        with pytest.raises(RuntimeError):
            _complete(store, token, receipts, before_publish=refuse)

        assert bucket_keys() == [temporary_key(token)]
        published = _complete(store, token, receipts)
        blobs.append(published.blob_id)
        assert bucket_keys() == [canonical_key(published.blob_id)]


class TestAWrongObjectIsRefused:
    def test_a_wrong_digest_is_refused_and_leaves_no_object(
        self, store: S3BlobStore, staged: Any, bucket_keys: Any, open_uploads: Any
    ) -> None:
        """Mutation proof: ``complete_multipart`` publishes without ``verify_temporary``."""
        token, receipts = staged(FIRST, SECOND, LAST)
        before = bucket_keys()
        wrong = sha256_of(b"the digest the caller wrongly declared")

        with pytest.raises(ChecksumMismatchError) as raised:
            _complete(store, token, receipts, declared_sha256=wrong)

        assert raised.value.code == "storage_integrity_error"
        assert raised.value.details["expected_sha256"] == wrong
        assert raised.value.details["actual_sha256"] == sha256_of(WHOLE)
        # Nothing canonical, nothing temporary, no upload left: the bucket is as it was before.
        assert bucket_keys() == before == []
        assert open_uploads() == []
        # Not under the declared identity, and not under the honest one either.
        with pytest.raises(BlobNotFoundError):
            store.inspect(derive_blob_id(sha256=wrong, size=len(WHOLE)))
        with pytest.raises(BlobNotFoundError):
            store.inspect(derive_blob_id(sha256=sha256_of(WHOLE), size=len(WHOLE)))

    def test_a_flipped_byte_in_one_part_is_a_digest_mismatch(
        self, store: S3BlobStore, staged: Any, bucket_keys: Any
    ) -> None:
        """The caller declared the digest of the file it meant to send; one part carried another byte."""
        token, receipts = staged(FIRST, SECOND, LAST[:-1] + b"X")

        with pytest.raises(ChecksumMismatchError):
            _complete(store, token, receipts)

        assert bucket_keys() == []

    def test_a_declared_size_the_parts_do_not_add_up_to_is_refused_before_assembly(
        self, store: S3BlobStore, staged: Any, bucket_keys: Any, open_uploads: Any, blobs: list
    ) -> None:
        """Mutation proof: the sum-of-sizes check removed (the upload would be assembled, then deleted)."""
        token, receipts = staged(FIRST, SECOND, LAST)

        with pytest.raises(SizeMismatchError) as raised:
            _complete(store, token, receipts, declared_size=len(WHOLE) + 1)

        assert raised.value.details["expected_size"] == len(WHOLE) + 1
        assert raised.value.details["actual_size"] == len(WHOLE)
        assert bucket_keys() == []
        # Refused before anything was assembled: the upload is exactly as it was, so the right
        # declaration still completes it.
        assert [key for key, _ in open_uploads()] == [temporary_key(token)]
        blobs.append(_complete(store, token, receipts).blob_id)

    def test_a_receipt_whose_size_differs_from_what_the_store_holds_is_refused(
        self, store: S3BlobStore, staged: Any, bucket_keys: Any
    ) -> None:
        """Sizes that add up to the declaration cannot hide a part the store holds differently."""
        token, receipts = staged(FIRST, SECOND, LAST)
        lying = [
            UploadedPart(1, 5 * MIB - 1, receipts[0].sha256, receipts[0].etag),
            receipts[1],
            UploadedPart(3, len(LAST) + 1, receipts[2].sha256, receipts[2].etag),
        ]
        assert sum(part.size_bytes for part in lying) == len(WHOLE)

        with pytest.raises(MultipartPartsError):
            _complete(store, token, lying)

        assert bucket_keys() == []


class TestPartsAreRefusedAtCompletion:
    """Mutation proof: ``check_parts_for_completion`` and ``_require_staged`` removed in turn."""

    def test_parts_out_of_order_are_refused(
        self, store: S3BlobStore, staged: Any, bucket_keys: Any, open_uploads: Any
    ) -> None:
        token, receipts = staged(FIRST, SECOND, LAST)

        with pytest.raises(MultipartPartsError) as raised:
            _complete(store, token, [receipts[1], receipts[0], receipts[2]])

        assert raised.value.code == "validation_failed"
        assert raised.value.details["field"] == "parts"
        assert bucket_keys() == []
        assert [key for key, _ in open_uploads()] == [temporary_key(token)]

    # The three lists below are ones the store itself accepts (measured on MinIO: `[1, 3]`, `[2, 3]` and
    # `[1, 1, 2, 3]` all assemble). The declaration is made to match what the list would assemble, so the
    # sizes add up and the digest is the right one: only the numbering check stands between the list and a
    # successful publication of a file nobody meant to send.

    def test_a_gap_in_the_numbers_is_refused(
        self, store: S3BlobStore, staged: Any, bucket_keys: Any
    ) -> None:
        token, receipts = staged(FIRST, SECOND, LAST)
        meant = FIRST + LAST
        with pytest.raises(MultipartPartsError):
            _complete(
                store, token, [receipts[0], receipts[2]],
                declared_sha256=sha256_of(meant), declared_size=len(meant),
            )
        assert bucket_keys() == []

    def test_a_list_that_does_not_start_at_one_is_refused(
        self, store: S3BlobStore, staged: Any, bucket_keys: Any
    ) -> None:
        token, receipts = staged(FIRST, SECOND, LAST)
        meant = SECOND + LAST
        with pytest.raises(MultipartPartsError):
            _complete(
                store, token, receipts[1:],
                declared_sha256=sha256_of(meant), declared_size=len(meant),
            )
        assert bucket_keys() == []

    def test_a_repeated_part_is_refused(
        self, store: S3BlobStore, staged: Any, bucket_keys: Any
    ) -> None:
        token, receipts = staged(FIRST, SECOND, LAST)
        meant = FIRST + FIRST + SECOND + LAST
        with pytest.raises(MultipartPartsError):
            _complete(
                store, token, [receipts[0], receipts[0], receipts[1], receipts[2]],
                declared_sha256=sha256_of(meant), declared_size=len(meant),
            )
        assert bucket_keys() == []

    def test_no_parts_are_refused(self, store: S3BlobStore, staged: Any) -> None:
        token, _ = staged(FIRST)
        with pytest.raises(MultipartPartsError):
            _complete(store, token, [])

    def test_a_listed_part_the_store_never_received_is_refused(
        self, store: S3BlobStore, staged: Any, bucket_keys: Any, open_uploads: Any
    ) -> None:
        token, receipts = staged(FIRST, SECOND)
        phantom = UploadedPart(3, len(LAST), sha256_of(LAST), hashlib.md5(LAST).hexdigest())

        with pytest.raises(MultipartPartsError):
            _complete(store, token, [*receipts, phantom])

        assert bucket_keys() == []
        assert [key for key, _ in open_uploads()] == [temporary_key(token)]

    def test_a_part_with_another_receipt_than_the_store_holds_is_refused(
        self, store: S3BlobStore, staged: Any
    ) -> None:
        token, receipts = staged(FIRST, SECOND, LAST)
        forged = UploadedPart(2, receipts[1].size_bytes, receipts[1].sha256, "0" * 32)
        with pytest.raises(MultipartPartsError):
            _complete(store, token, [receipts[0], forged, receipts[2]])

    def test_a_small_part_in_the_middle_is_refused_by_the_store_as_a_parts_error(
        self, store: S3BlobStore, staged: Any, bucket_keys: Any
    ) -> None:
        small = b"ten bytes!"
        token, receipts = staged(small, small, small)
        whole = small * 3

        with pytest.raises(MultipartPartsError) as raised:
            _complete(
                store,
                token,
                receipts,
                declared_sha256=sha256_of(whole),
                declared_size=len(whole),
            )

        assert raised.value.code == "validation_failed"
        assert bucket_keys() == []

    def test_a_listed_part_is_enough_and_an_unlisted_one_is_dropped(
        self, store: S3BlobStore, staged: Any, blobs: list
    ) -> None:
        """The store holds a fourth part the caller never recorded: it is not part of the object."""
        token, receipts = staged(FIRST, SECOND, LAST, b"never recorded")

        published = _complete(store, token, receipts[:3])
        blobs.append(published.blob_id)

        assert store.read(published.blob_id) == WHOLE


class TestAnAbortedUploadLeavesNothing:
    def test_an_aborted_upload_leaves_nothing_and_takes_no_more_parts(
        self, store: S3BlobStore, staged: Any, bucket_keys: Any, open_uploads: Any
    ) -> None:
        """Mutation proof: ``abort_multipart`` does not abort the upload."""
        token, receipts = staged(FIRST, SECOND)
        assert [key for key, _ in open_uploads()] == [temporary_key(token)]

        assert store.abort_multipart(token) is True

        assert open_uploads() == []
        assert bucket_keys() == []
        # A straggler part, and a completion, are refused as a lost upload (`staged_upload_lost`).
        with pytest.raises(TemporaryBlobLostError) as lost:
            store.upload_part(token, 3, LAST)
        assert lost.value.code == "staged_upload_lost"
        with pytest.raises(TemporaryBlobLostError):
            _complete(store, token, [*receipts, UploadedPart(3, len(LAST), sha256_of(LAST), "0" * 32)])
        assert open_uploads() == []
        assert bucket_keys() == []

    def test_an_abort_touches_only_its_own_token(
        self, store: S3BlobStore, staged: Any, bucket_keys: Any, open_uploads: Any
    ) -> None:
        """The store narrows the upload listing by prefix already; the exact-key filter behind it
        (tokens are fixed-length, so no sibling key exists on a real store) is proved by the
        offline stand-in, ``test_an_exact_key_is_the_only_upload_the_token_names``."""
        mine, _ = staged(FIRST)
        other, _ = staged(SECOND)
        plain = store.stage_temporary(
            b"plainly staged bytes",
            declared_sha256=sha256_of(b"plainly staged bytes"),
            declared_size=len(b"plainly staged bytes"),
            role=ROLE_SOURCE_DOCUMENT,
            media_type=MEDIA,
        )

        assert store.abort_multipart(mine) is True

        assert [key for key, _ in open_uploads()] == [temporary_key(other)]
        assert bucket_keys() == [temporary_key(plain.upload_token)]
        store.discard_temporary(plain)

    def test_aborting_again_is_a_no_op(self, store: S3BlobStore, staged: Any) -> None:
        token, _ = staged(FIRST)
        assert store.abort_multipart(token) is True
        assert store.abort_multipart(token) is False
        assert store.abort_multipart(new_multipart_token()) is False

    def test_an_unverified_assembly_is_deleted_by_the_abort(
        self,
        store: S3BlobStore,
        staged: Any,
        raw_s3: Any,
        settings: Any,
        bucket_keys: Any,
        open_uploads: Any,
    ) -> None:
        """A process killed after the store assembled the object and before it was verified."""
        token, receipts = staged(FIRST, SECOND, LAST)
        _, upload_id = open_uploads()[0]
        raw_s3.complete_multipart_upload(
            Bucket=settings.bucket,
            Key=temporary_key(token),
            UploadId=upload_id,
            MultipartUpload={
                "Parts": [{"PartNumber": r.part_number, "ETag": f'"{r.etag}"'} for r in receipts]
            },
        )
        assert bucket_keys() == [temporary_key(token)]

        assert store.abort_multipart(token) is True

        assert bucket_keys() == []

    def test_the_abort_never_removes_a_published_blob(
        self, store: S3BlobStore, staged: Any, bucket_keys: Any, blobs: list
    ) -> None:
        token, receipts = staged(FIRST, SECOND, LAST)
        published = _complete(store, token, receipts)
        blobs.append(published.blob_id)

        assert store.abort_multipart(token) is False

        assert bucket_keys() == [canonical_key(published.blob_id)]
        assert store.read(published.blob_id) == WHOLE


class TestACompletionIsRetryable:
    def test_a_completion_killed_before_it_verified_resumes_at_the_verification(
        self,
        store: S3BlobStore,
        staged: Any,
        raw_s3: Any,
        settings: Any,
        bucket_keys: Any,
        open_uploads: Any,
        blobs: list,
    ) -> None:
        """Mutation proof: with no open upload the completion gives up instead of verifying."""
        token, receipts = staged(FIRST, SECOND, LAST)
        _, upload_id = open_uploads()[0]
        raw_s3.complete_multipart_upload(
            Bucket=settings.bucket,
            Key=temporary_key(token),
            UploadId=upload_id,
            MultipartUpload={
                "Parts": [{"PartNumber": r.part_number, "ETag": f'"{r.etag}"'} for r in receipts]
            },
        )
        assert open_uploads() == []

        published = _complete(store, token, receipts)
        blobs.append(published.blob_id)

        assert store.read(published.blob_id) == WHOLE
        assert bucket_keys() == [canonical_key(published.blob_id)]

    def test_a_completion_with_no_upload_and_no_object_is_a_lost_upload(
        self, store: S3BlobStore, tokens: list[str]
    ) -> None:
        token = new_multipart_token()
        tokens.append(token)
        parts = [UploadedPart(1, len(WHOLE), sha256_of(WHOLE), "0" * 32)]
        with pytest.raises(TemporaryBlobLostError):
            _complete(store, token, parts)

    def test_a_second_completion_after_the_publication_finds_nothing_to_resume(
        self, store: S3BlobStore, staged: Any, blobs: list
    ) -> None:
        token, receipts = staged(FIRST, SECOND, LAST)
        blobs.append(_complete(store, token, receipts).blob_id)
        with pytest.raises(TemporaryBlobLostError):
            _complete(store, token, receipts)


class TestTheBoundsAreRefusedBeforeAnythingIsSent:
    @pytest.mark.parametrize("number", [0, -1, 10001, True, 1.5, "1", None])
    def test_a_part_number_outside_one_to_ten_thousand(
        self, store: S3BlobStore, tokens: list[str], number: Any
    ) -> None:
        token = new_multipart_token()
        tokens.append(token)
        store.begin_multipart(token)
        with pytest.raises(MultipartPartError) as raised:
            store.upload_part(token, number, b"x")
        assert raised.value.code == "validation_failed"
        assert raised.value.details["field"] == "part_number"

    def test_an_empty_part_and_a_part_over_sixteen_mib(
        self, store: S3BlobStore, tokens: list[str], raw_s3: Any, settings: Any, open_uploads: Any
    ) -> None:
        token = new_multipart_token()
        tokens.append(token)
        store.begin_multipart(token)
        with pytest.raises(MultipartPartError) as empty:
            store.upload_part(token, 1, b"")
        assert empty.value.details["field"] == "part_size"
        with pytest.raises(MultipartPartError):
            store.upload_part(token, 1, b"x" * (16 * MIB + 1))
        with pytest.raises(MultipartPartError):
            store.upload_part(token, 1, io.BytesIO(b"x" * (16 * MIB + 1)))
        # Nothing reached the upload.
        _, upload_id = open_uploads()[0]
        held = raw_s3.list_parts(Bucket=settings.bucket, Key=temporary_key(token), UploadId=upload_id)
        assert held.get("Parts", []) == []

    def test_a_part_of_exactly_sixteen_mib_is_accepted(
        self, store: S3BlobStore, staged: Any
    ) -> None:
        _, receipts = staged(b"z" * (16 * MIB))
        assert receipts[0].size_bytes == 16777216

    def test_a_part_for_an_upload_never_begun_is_a_lost_upload(
        self, store: S3BlobStore
    ) -> None:
        with pytest.raises(TemporaryBlobLostError):
            store.upload_part(new_multipart_token(), 1, b"x")


class TestOnlyAMintedTokenIsAKeyStem:
    @pytest.mark.parametrize(
        "token",
        [
            "",
            "mpu-",
            "mpu-" + "g" * 32,
            "mpu-" + "A" * 32,
            "mpu-" + "a" * 31,
            "mpu-" + "a" * 33,
            "mpu-" + "a" * 32 + "\n",
            "../blobs/xx",
            "temporary/mpu-" + "a" * 32,
            "a" * 32,
            None,
            7,
        ],
    )
    def test_a_string_the_store_did_not_mint_is_refused_by_every_call(
        self, store: S3BlobStore, token: Any
    ) -> None:
        part = UploadedPart(1, 1, sha256_of(b"x"), "0" * 32)
        calls = (
            lambda: store.begin_multipart(token),
            lambda: store.upload_part(token, 1, b"x"),
            lambda: store.abort_multipart(token),
            lambda: store.complete_multipart(
                token,
                [part],
                declared_sha256=sha256_of(b"x"),
                declared_size=1,
                role=ROLE_SOURCE_DOCUMENT,
                media_type=MEDIA,
            ),
        )
        for call in calls:
            with pytest.raises(BlobMetadataInvalidError) as raised:
                call()
            assert raised.value.details["field"] == "upload_token"

    def test_a_minted_token_is_opaque_and_unique(self) -> None:
        minted = {new_multipart_token() for _ in range(50)}
        assert len(minted) == 50
        assert all(len(t) == 36 and t.startswith("mpu-") for t in minted)


class TestTheAbortSweep:
    def test_the_sweep_aborts_what_is_open_and_reports_the_rest(
        self,
        store: S3BlobStore,
        staged: Any,
        bucket_keys: Any,
        open_uploads: Any,
        blobs: list,
    ) -> None:
        open_one, _ = staged(FIRST)
        open_two, _ = staged(SECOND)
        done, receipts = staged(FIRST, SECOND, LAST)
        published = _complete(store, done, receipts)
        blobs.append(published.blob_id)
        never_begun = new_multipart_token()

        report = abort_multipart_sweep(
            store, [open_one, never_begun, "not-a-token", open_two, open_one, done]
        )

        assert report.aborted == (open_one, open_two)
        assert report.absent == (never_begun, done)
        assert report.rejected == ("not-a-token",)
        assert report.handled == 5
        assert open_uploads() == []
        # The completed file's published blob is untouched by the sweep.
        assert bucket_keys() == [canonical_key(published.blob_id)]

    def test_a_second_sweep_finds_nothing(self, store: S3BlobStore, staged: Any) -> None:
        token, _ = staged(FIRST)
        assert abort_multipart_sweep(store, [token]).aborted == (token,)
        again = abort_multipart_sweep(store, [token])
        assert (again.aborted, again.absent, again.rejected) == ((), (token,), ())

    def test_an_unreachable_store_raises_instead_of_reporting(
        self, unreachable_store: S3BlobStore
    ) -> None:
        with pytest.raises(StorageUnavailableError):
            abort_multipart_sweep(unreachable_store, [new_multipart_token()])


class TestAnUnavailableStoreIsAnExplicitFailure:
    def test_every_call_raises_a_typed_error_and_nothing_is_staged_elsewhere(
        self, unreachable_store: S3BlobStore
    ) -> None:
        token = new_multipart_token()
        with pytest.raises(StorageUnavailableError):
            unreachable_store.begin_multipart(token)
        with pytest.raises(StorageUnavailableError):
            unreachable_store.upload_part(token, 1, b"x")
        with pytest.raises(StorageUnavailableError):
            unreachable_store.abort_multipart(token)


def test_a_refusal_is_a_blob_integrity_error_where_the_bytes_are_wrong(
    store: S3BlobStore, staged: Any
) -> None:
    """Both mismatches are one catchable family (`storage_integrity_error`) for the caller."""
    token, receipts = staged(FIRST, SECOND, LAST)
    with pytest.raises(BlobIntegrityError):
        _complete(store, token, receipts, declared_size=len(WHOLE) + 1)
    with pytest.raises(BlobIntegrityError):
        _complete(store, token, receipts, declared_sha256=sha256_of(b"other"))
