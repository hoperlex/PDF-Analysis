"""Multipart staging without a container (`CMP-STORAGE-PARTS-01`, ADR-0025 decision 10).

The real-service cases live in ``tests/integration/storage/test_multipart_staging.py``. A real store
refuses a disordered or incomplete part list *itself*, so a bucket can show that a list was refused but
not that the adapter refused it **before asking the store to assemble**. These cases drive the adapter
through a stand-in that records every call it receives, so "nothing was assembled" is an assertion about
calls, and the pagination and error-translation branches no single-digit-part upload reaches are
exercised.

The stand-in stores what the adapter sends and answers what S3 answers. It has no opinion of its own
beyond the three rules of S3 the adapter relies on: an unknown upload is ``NoSuchUpload``, a part list
is ascending, and a completion of an upload ends it.

Expected values are literals, not the module's own constants.
"""

from __future__ import annotations

import hashlib
import io
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from botocore.exceptions import ClientError

from auditmanager.storage import (
    ROLE_SOURCE_DOCUMENT,
    BlobMetadataInvalidError,
    BlobStore,
    ChecksumMismatchError,
    DurablePublicationStore,
    MultipartPartError,
    MultipartPartsError,
    MultipartStaging,
    S3BlobStore,
    S3StorageSettings,
    SizeMismatchError,
    StorageUnavailableError,
    TemporaryBlobLostError,
    UploadedPart,
    abort_multipart_sweep,
    new_multipart_token,
    sha256_of,
)
from auditmanager.storage.multipart import (
    MULTIPART_TOKEN_PATTERN,
    check_parts_for_completion,
    parse_multipart_token,
    validate_part_number,
    validate_part_size,
)

TOKEN = "mpu-" + "0123456789abcdef" * 2
MIB = 1024 * 1024
A = b"a" * 10
B = b"b" * 10
C = b"c" * 4
WHOLE = A + B + C


def _error(code: str, status: int = 400, operation: str = "Op") -> ClientError:
    return ClientError(
        {"Error": {"Code": code}, "ResponseMetadata": {"HTTPStatusCode": status}}, operation
    )


class MemoryMultipartS3:
    """The S3 calls the multipart methods make, over dicts, recording every call."""

    def __init__(self, *, page: int = 1000) -> None:
        self.objects: dict[str, bytes] = {}
        self.meta: dict[str, dict[str, str]] = {}
        self.uploads: dict[str, dict[str, Any]] = {}  # upload id -> {key, at, parts}
        self.calls: list[tuple[str, str]] = []
        self.page = page
        self.fail: dict[str, ClientError] = {}
        self._clock = datetime(2026, 10, 28, tzinfo=UTC)
        self._count = 0

    # --- helpers
    def _record(self, name: str, key: str = "") -> None:
        self.calls.append((name, key))
        if name in self.fail:
            raise self.fail[name]

    def open_upload(self, key: str, *, at: datetime | None = None) -> str:
        self._count += 1
        upload_id = f"upload-{self._count}"
        self.uploads[upload_id] = {
            "key": key,
            "at": at or self._clock + timedelta(seconds=self._count),
            "parts": {},
        }
        return upload_id

    def called(self, name: str) -> list[str]:
        return [key for call, key in self.calls if call == name]

    # --- the S3 surface
    def create_multipart_upload(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        self._record("create_multipart_upload", Key)
        return {"UploadId": self.open_upload(Key)}

    def list_multipart_uploads(self, *, Bucket: str, Prefix: str, **marker: Any) -> dict[str, Any]:
        self._record("list_multipart_uploads", Prefix)
        rows = sorted(
            ((u["key"], uid, u["at"]) for uid, u in self.uploads.items() if u["key"].startswith(Prefix)),
        )
        start = 0
        if marker.get("UploadIdMarker"):
            start = [uid for _, uid, _ in rows].index(marker["UploadIdMarker"]) + 1
        window = rows[start : start + self.page]
        truncated = start + self.page < len(rows)
        return {
            "Uploads": [{"Key": k, "UploadId": uid, "Initiated": at} for k, uid, at in window],
            "IsTruncated": truncated,
            "NextKeyMarker": window[-1][0] if window and truncated else "",
            "NextUploadIdMarker": window[-1][1] if window and truncated else "",
        }

    def upload_part(
        self, *, Bucket: str, Key: str, UploadId: str, PartNumber: int, Body: bytes
    ) -> dict[str, Any]:
        self._record("upload_part", Key)
        if UploadId not in self.uploads:
            raise _error("NoSuchUpload", 404)
        self.uploads[UploadId]["parts"][PartNumber] = bytes(Body)
        self.calls[-1] = ("upload_part", f"{UploadId}:{PartNumber}")
        return {"ETag": f'"{hashlib.md5(Body).hexdigest()}"'}

    def list_parts(
        self, *, Bucket: str, Key: str, UploadId: str, MaxParts: int, PartNumberMarker: int
    ) -> dict[str, Any]:
        self._record("list_parts", Key)
        if UploadId not in self.uploads:
            raise _error("NoSuchUpload", 404)
        numbers = sorted(n for n in self.uploads[UploadId]["parts"] if n > PartNumberMarker)
        window = numbers[: min(self.page, MaxParts)]
        truncated = len(numbers) > len(window)
        parts = self.uploads[UploadId]["parts"]
        return {
            "Parts": [
                {
                    "PartNumber": n,
                    "ETag": f'"{hashlib.md5(parts[n]).hexdigest()}"',
                    "Size": len(parts[n]),
                }
                for n in window
            ],
            "IsTruncated": truncated,
            "NextPartNumberMarker": window[-1] if window and truncated else 0,
        }

    def complete_multipart_upload(
        self, *, Bucket: str, Key: str, UploadId: str, MultipartUpload: dict[str, Any]
    ) -> dict[str, Any]:
        self._record("complete_multipart_upload", Key)
        if UploadId not in self.uploads:
            raise _error("NoSuchUpload", 404)
        numbers = [p["PartNumber"] for p in MultipartUpload["Parts"]]
        if numbers != sorted(numbers):
            raise _error("InvalidPartOrder")
        body = b""
        for part in MultipartUpload["Parts"]:
            held = self.uploads[UploadId]["parts"].get(part["PartNumber"])
            if held is None or f'"{hashlib.md5(held).hexdigest()}"' != part["ETag"]:
                raise _error("InvalidPart")
            body += held
        self.objects[Key] = body
        del self.uploads[UploadId]
        return {}

    def abort_multipart_upload(self, *, Bucket: str, Key: str, UploadId: str) -> None:
        self._record("abort_multipart_upload", Key)
        if UploadId not in self.uploads:
            raise _error("NoSuchUpload", 404)
        del self.uploads[UploadId]

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        if Key not in self.objects:
            raise _error("404", 404)
        return {
            "ContentLength": len(self.objects[Key]),
            "ContentType": "application/octet-stream",
            "Metadata": dict(self.meta.get(Key, {})),
            "LastModified": self._clock,
        }

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        if Key not in self.objects:
            raise _error("404", 404)
        return {"Body": io.BytesIO(self.objects[Key]), "Metadata": {}}

    def copy_object(
        self, *, Bucket: str, Key: str, CopySource: dict[str, str], MetadataDirective: str,
        ContentType: str, Metadata: dict[str, str],
    ) -> None:
        self.objects[Key] = self.objects[CopySource["Key"]]
        self.meta[Key] = dict(Metadata)

    def delete_object(self, *, Bucket: str, Key: str) -> None:
        self.objects.pop(Key, None)


def _store(client: MemoryMultipartS3 | None = None) -> tuple[S3BlobStore, MemoryMultipartS3]:
    client = client or MemoryMultipartS3()
    settings = S3StorageSettings(
        endpoint_url="http://127.0.0.1:1",
        region="us-east-1",
        access_key_id="k",
        secret_access_key="s",
        bucket="offline-bucket",
    )
    return S3BlobStore(settings, client=client), client


def _staged(store: S3BlobStore, *payloads: bytes) -> list[UploadedPart]:
    store.begin_multipart(TOKEN)
    return [store.upload_part(TOKEN, n, p) for n, p in enumerate(payloads, start=1)]


def _complete(store: S3BlobStore, parts: list[UploadedPart], **override: Any):
    arguments: dict[str, Any] = {
        "declared_sha256": sha256_of(WHOLE),
        "declared_size": len(WHOLE),
        "role": ROLE_SOURCE_DOCUMENT,
        "media_type": "application/pdf",
    }
    arguments.update(override)
    return store.complete_multipart(TOKEN, parts, **arguments)


class TestThePortShape:
    def test_the_multipart_port_is_four_operations(self) -> None:
        members = {name for name in dir(MultipartStaging) if not name.startswith("_")}
        assert members == {"abort_multipart", "begin_multipart", "complete_multipart", "upload_part"}

    def test_the_blob_store_port_did_not_grow(self) -> None:
        for name in ("begin_multipart", "upload_part", "complete_multipart", "abort_multipart"):
            assert not hasattr(BlobStore, name)
            assert not hasattr(DurablePublicationStore, name)

    def test_the_adapter_satisfies_both_ports(self) -> None:
        store, _ = _store()
        assert isinstance(store, MultipartStaging)
        assert isinstance(store, BlobStore)


class TestTheTokenAndTheBounds:
    def test_a_minted_token_matches_the_one_pattern(self) -> None:
        assert MULTIPART_TOKEN_PATTERN.pattern == r"^mpu-[0-9a-f]{32}$"
        token = new_multipart_token()
        assert parse_multipart_token(token) == token

    @pytest.mark.parametrize("bad", ["", "mpu-", "MPU-" + "a" * 32, "mpu-" + "a" * 32 + "\n", None, 3])
    def test_a_token_the_store_did_not_mint_is_refused(self, bad: Any) -> None:
        with pytest.raises(BlobMetadataInvalidError) as raised:
            parse_multipart_token(bad)
        assert raised.value.details == {"field": "upload_token", "constraint": MULTIPART_TOKEN_PATTERN.pattern}

    @pytest.mark.parametrize("number", [1, 2, 9999, 10000])
    def test_part_numbers_inside_the_bound(self, number: int) -> None:
        assert validate_part_number(number) == number

    @pytest.mark.parametrize("number", [0, -1, 10001, 2**31, True, False, 1.0, "1", None])
    def test_part_numbers_outside_the_bound(self, number: Any) -> None:
        with pytest.raises(MultipartPartError) as raised:
            validate_part_number(number)
        assert raised.value.details["field"] == "part_number"

    @pytest.mark.parametrize("size", [1, 2, 16 * MIB - 1, 16 * MIB])
    def test_part_sizes_inside_the_bound(self, size: int) -> None:
        assert validate_part_size(size) == size

    @pytest.mark.parametrize("size", [0, -1, 16 * MIB + 1])
    def test_part_sizes_outside_the_bound(self, size: int) -> None:
        with pytest.raises(MultipartPartError) as raised:
            validate_part_size(size)
        assert raised.value.details["field"] == "part_size"
        assert raised.value.code == "validation_failed"

    def test_the_new_errors_carry_no_location(self) -> None:
        with pytest.raises(TypeError):
            MultipartPartsError(bucket="b")
        with pytest.raises(TypeError):
            MultipartPartError(key="k")


def _part(number: int, size: int = 10, *, etag: str = "e" * 32, sha: str = "a" * 64) -> UploadedPart:
    return UploadedPart(number, size, sha, etag)


class TestThePartsOfACompletion:
    def test_a_whole_ordered_list_is_accepted_and_returned_as_a_tuple(self) -> None:
        parts = [_part(1), _part(2), _part(3, 4)]
        assert check_parts_for_completion(parts, declared_size=24) == tuple(parts)

    @pytest.mark.parametrize(
        "numbers",
        [[], [2, 1, 3], [1, 3], [2, 3], [1, 1, 2], [1, 2, 2], [0, 1, 2], [1, 2, 4], [3, 2, 1]],
    )
    def test_a_list_that_is_not_one_to_n_ascending_is_refused(self, numbers: list[int]) -> None:
        with pytest.raises(MultipartPartsError) as raised:
            check_parts_for_completion([_part(n) for n in numbers], declared_size=10 * len(numbers))
        assert raised.value.code == "validation_failed"
        assert raised.value.details["field"] == "parts"

    def test_sizes_that_do_not_add_up_are_an_integrity_refusal(self) -> None:
        with pytest.raises(SizeMismatchError) as raised:
            check_parts_for_completion([_part(1), _part(2)], declared_size=21)
        assert raised.value.code == "storage_integrity_error"
        assert raised.value.details == {"expected_size": 21, "actual_size": 20}

    @pytest.mark.parametrize(
        "broken",
        [
            _part(1, 0),
            _part(1, 16 * MIB + 1),
            _part(1, 10, etag=""),
            _part(1, 10, etag="e" * 257),
            _part(1, 10, sha="A" * 64),
            _part(1, 10, sha="a" * 63),
            UploadedPart(1, True, "a" * 64, "e"),  # type: ignore[arg-type]
        ],
    )
    def test_a_part_without_its_facts_is_refused(self, broken: UploadedPart) -> None:
        with pytest.raises(MultipartPartsError):
            check_parts_for_completion([broken], declared_size=broken.size_bytes)

    def test_something_that_is_not_a_part_is_refused(self) -> None:
        with pytest.raises(MultipartPartsError):
            check_parts_for_completion([(1, 10, "a" * 64, "e")], declared_size=10)  # type: ignore[list-item]


class TestNothingIsAssembledForAListTheAdapterRefuses:
    """Mutation proof: each refusal removed makes the stand-in see a ``complete_multipart_upload``."""

    @pytest.mark.parametrize(
        "pick",
        [
            lambda r: [r[1], r[0], r[2]],
            lambda r: [r[0], r[2]],
            lambda r: r[1:],
            lambda r: [r[0], r[0], r[1], r[2]],
            lambda r: [],
        ],
        ids=["disordered", "gap", "from-two", "repeat", "empty"],
    )
    def test_a_bad_list_is_refused_before_the_store_is_asked_to_assemble(self, pick: Any) -> None:
        store, client = _store()
        receipts = _staged(store, A, B, C)

        with pytest.raises(MultipartPartsError):
            _complete(store, pick(receipts))

        assert client.called("complete_multipart_upload") == []
        assert client.objects == {}
        assert len(client.uploads) == 1  # still open

    def test_sizes_that_do_not_add_up_are_refused_before_assembly(self) -> None:
        store, client = _store()
        receipts = _staged(store, A, B, C)

        with pytest.raises(SizeMismatchError):
            _complete(store, receipts, declared_size=len(WHOLE) + 1)

        assert client.called("complete_multipart_upload") == []
        assert len(client.uploads) == 1

    def test_a_part_the_store_does_not_hold_is_refused_before_assembly(self) -> None:
        store, client = _store()
        receipts = _staged(store, A, B)
        phantom = UploadedPart(3, len(C), sha256_of(C), hashlib.md5(C).hexdigest())

        with pytest.raises(MultipartPartsError):
            _complete(store, [*receipts, phantom])

        assert client.called("complete_multipart_upload") == []

    def test_a_receipt_with_another_size_than_the_store_holds_is_refused_before_assembly(self) -> None:
        store, client = _store()
        receipts = _staged(store, A, B, C)
        lying = [
            UploadedPart(1, len(A) - 1, receipts[0].sha256, receipts[0].etag),
            receipts[1],
            UploadedPart(3, len(C) + 1, receipts[2].sha256, receipts[2].etag),
        ]

        with pytest.raises(MultipartPartsError):
            _complete(store, lying)

        assert client.called("complete_multipart_upload") == []

    def test_a_receipt_with_another_etag_than_the_store_holds_is_refused_before_assembly(self) -> None:
        store, client = _store()
        receipts = _staged(store, A, B, C)
        forged = UploadedPart(2, len(B), receipts[1].sha256, "0" * 32)

        with pytest.raises(MultipartPartsError):
            _complete(store, [receipts[0], forged, receipts[2]])

        assert client.called("complete_multipart_upload") == []


class TestTheStoreSideOfACompletion:
    def test_the_whole_sequence_publishes_what_was_sent(self) -> None:
        store, client = _store()
        receipts = _staged(store, A, B, C)

        published = _complete(store, receipts)

        assert published.size == 24
        assert published.sha256 == sha256_of(WHOLE)
        assert client.uploads == {}
        # The temporary assembly is gone; only the canonical object is left.
        assert [k for k in client.objects if k.startswith("temporary/")] == []
        assert len(client.objects) == 1

    def test_a_wrong_digest_removes_the_assembly(self) -> None:
        store, client = _store()
        receipts = _staged(store, A, B, C)

        with pytest.raises(ChecksumMismatchError):
            _complete(store, receipts, declared_sha256=sha256_of(b"other"))

        assert client.objects == {}
        assert client.uploads == {}

    def test_the_store_refusing_the_parts_is_a_parts_error(self) -> None:
        store, client = _store()
        receipts = _staged(store, A, B, C)
        client.fail["complete_multipart_upload"] = _error("InvalidPart")

        with pytest.raises(MultipartPartsError):
            _complete(store, receipts)

    @pytest.mark.parametrize("code", ["InvalidPartOrder", "EntityTooSmall"])
    def test_the_other_refusals_of_a_part_list_are_parts_errors(self, code: str) -> None:
        store, client = _store()
        receipts = _staged(store, A, B, C)
        client.fail["complete_multipart_upload"] = _error(code)

        with pytest.raises(MultipartPartsError):
            _complete(store, receipts)

    def test_a_vanished_upload_is_a_lost_upload(self) -> None:
        store, client = _store()
        receipts = _staged(store, A, B, C)
        client.fail["complete_multipart_upload"] = _error("NoSuchUpload", 404)

        with pytest.raises(TemporaryBlobLostError):
            _complete(store, receipts)

    def test_a_server_fault_is_unavailable_and_the_assembly_is_not_thrown_away(self) -> None:
        store, client = _store()
        receipts = _staged(store, A, B, C)
        client.fail["complete_multipart_upload"] = _error("InternalError", 500)

        with pytest.raises(StorageUnavailableError):
            _complete(store, receipts)

        assert len(client.uploads) == 1

    def test_a_listing_that_runs_over_several_pages_still_finds_every_part(self) -> None:
        store, client = _store(MemoryMultipartS3(page=2))
        parts = [bytes([65 + n]) * 3 for n in range(7)]
        receipts = _staged(store, *parts)
        whole = b"".join(parts)

        published = _complete(
            store, receipts, declared_sha256=sha256_of(whole), declared_size=len(whole)
        )

        assert published.size == 21
        assert client.called("list_parts").__len__() == 4  # ceil(7 / 2) pages

    def test_an_exact_key_is_the_only_upload_the_token_names(self) -> None:
        store, client = _store()
        client.open_upload("temporary/" + TOKEN + "-sibling")
        client.open_upload("temporary/" + TOKEN[:-1])

        with pytest.raises(TemporaryBlobLostError):
            store.upload_part(TOKEN, 1, A)
        assert store.abort_multipart(TOKEN) is False
        assert len(client.uploads) == 2  # the siblings are untouched

    def test_the_earliest_of_two_open_uploads_takes_the_part_and_the_spare_is_aborted(self) -> None:
        store, client = _store()
        later = client.open_upload("temporary/" + TOKEN, at=datetime(2026, 10, 28, 1, tzinfo=UTC))
        earlier = client.open_upload("temporary/" + TOKEN, at=datetime(2026, 10, 28, 0, tzinfo=UTC))

        receipt = store.upload_part(TOKEN, 1, A)

        assert client.called("upload_part") == [f"{earlier}:1"]
        assert 1 in client.uploads[earlier]["parts"] and client.uploads[later]["parts"] == {}
        # An abort removes every upload the key has.
        assert store.abort_multipart(TOKEN) is True
        assert client.uploads == {}
        assert receipt.size_bytes == 10

    def test_an_upload_listing_over_two_pages_is_followed(self) -> None:
        store, client = _store(MemoryMultipartS3(page=1))
        client.open_upload("temporary/" + TOKEN, at=datetime(2026, 10, 28, 1, tzinfo=UTC))
        client.open_upload("temporary/" + TOKEN, at=datetime(2026, 10, 28, 2, tzinfo=UTC))

        assert store.abort_multipart(TOKEN) is True
        assert client.uploads == {}

    def test_begin_asks_the_store_once(self) -> None:
        store, client = _store()
        store.begin_multipart(TOKEN)
        store.begin_multipart(TOKEN)
        assert client.called("create_multipart_upload") == ["temporary/" + TOKEN]

    def test_an_oversized_stream_is_refused_after_reading_one_byte_past_the_bound(self) -> None:
        store, client = _store()
        store.begin_multipart(TOKEN)

        class Counting(io.BytesIO):
            asked: list[int] = []

            def read(self, size: int | None = -1) -> bytes:
                self.asked.append(size if size is not None else -1)
                return super().read(size)

        stream = Counting(b"x" * (16 * MIB + 5))
        with pytest.raises(MultipartPartError):
            store.upload_part(TOKEN, 1, stream)

        assert Counting.asked == [16 * MIB + 1]
        assert client.called("upload_part") == []


class _FakeStore:
    """What the sweep needs of a store: ``abort_multipart``, answering from a set."""

    def __init__(self, held: set[str], *, fail_on: str | None = None) -> None:
        self.held = set(held)
        self.asked: list[str] = []
        self.fail_on = fail_on

    def abort_multipart(self, token: str) -> bool:
        self.asked.append(token)
        if token == self.fail_on:
            raise StorageUnavailableError()
        present = token in self.held
        self.held.discard(token)
        return present


class TestTheAbortSweepLogic:
    T1, T2, T3 = ("mpu-" + c * 32 for c in "123")

    def test_the_report_names_each_token_once_in_order(self) -> None:
        store = _FakeStore({self.T1, self.T3})

        report = abort_multipart_sweep(
            store, [self.T1, self.T2, "bad", self.T1, self.T3, "bad"]  # type: ignore[arg-type]
        )

        assert report.aborted == (self.T1, self.T3)
        assert report.absent == (self.T2,)
        assert report.rejected == ("bad",)  # a repeated string is handled once, rejected or not
        assert store.asked == [self.T1, self.T2, self.T3]

    def test_a_malformed_token_never_reaches_the_store_and_does_not_stop_the_sweep(self) -> None:
        store = _FakeStore({self.T2})

        report = abort_multipart_sweep(store, ["../temporary/x", None, 7, self.T2])  # type: ignore[list-item]

        assert report.rejected == ("../temporary/x", "None", "7")
        assert report.aborted == (self.T2,)
        assert store.asked == [self.T2]

    def test_a_store_fault_is_raised_and_a_rerun_finishes_the_work(self) -> None:
        store = _FakeStore({self.T1, self.T2, self.T3}, fail_on=self.T2)

        with pytest.raises(StorageUnavailableError):
            abort_multipart_sweep(store, [self.T1, self.T2, self.T3])

        assert store.held == {self.T2, self.T3}
        store.fail_on = None
        report = abort_multipart_sweep(store, [self.T1, self.T2, self.T3])
        assert (report.aborted, report.absent) == ((self.T2, self.T3), (self.T1,))
        assert store.held == set()

    def test_no_tokens_is_an_empty_report(self) -> None:
        report = abort_multipart_sweep(_FakeStore(set()), [])
        assert (report.aborted, report.absent, report.rejected, report.handled) == ((), (), (), 0)
