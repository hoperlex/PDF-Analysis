"""The norm PDF through its confirmed binding, against PostgreSQL and S3 (`W55A-SEARCH-01`).

Window: PostgreSQL ``57230``, S3 ``60830/60831``. The shipped ``NormContentAdapter`` over
the real ``S3BlobStore`` (``W55A-CONTENT-01``'s ``open_stream``): the object is written by
the store's own ``put_blob``, the binding by plain SQL (``conftest.Corpus``). A document
without a confirmed binding of its PDF serves nothing, even when the bytes are in the store.
"""

from __future__ import annotations

import hashlib

import pytest

from auditmanager.api.schemas.content import ByteRange
from auditmanager.bootstrap.adapters import NormContentAdapter, NormsSearchAdapter
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage import S3BlobStore
from auditmanager.storage.public import parse_blob_role
from tests.integration.norms.search.conftest import Corpus

SP54 = "СП_54_13330_2022__Свод_правил__Здания_жилые"
DATA = b"%PDF-1.7\n" + bytes(range(256)) * 1500


def _put(store: S3BlobStore, data: bytes) -> None:
    store.put_blob(
        data,
        declared_sha256=hashlib.sha256(data).hexdigest(),
        declared_size=len(data),
        role=parse_blob_role("norm_source"),
        media_type="application/pdf",
    )


def _refusal(call) -> DomainError:
    with pytest.raises(DomainError) as caught:
        call()
    return caught.value


def test_the_pdf_is_served_only_through_a_confirmed_binding(
    corpus: Corpus, pdf_store: S3BlobStore
) -> None:
    snapshot = corpus.snapshot(documents=2)
    bound = corpus.document(snapshot, SP54, ref="sp54")
    unbound = corpus.document(snapshot, "ГОСТ_10140-2003__Плиты", ref="gost")
    _put(pdf_store, DATA)
    corpus.bind_pdf(bound, DATA)
    other = DATA + b"unbound"
    _put(pdf_store, other)
    corpus.blob(other)  # the bytes exist and are available, but nothing binds them

    content = NormContentAdapter(corpus.session_factory, blob_store=pdf_store)
    whole = content.stream_content(norm_document_id=bound, byte_range=None)
    assert (whole.total_size, whole.window) == (len(DATA), None)
    assert b"".join(whole.chunks) == DATA

    window = content.stream_content(norm_document_id=bound, byte_range=ByteRange(100, 163))
    assert window.window == (100, 163)
    assert b"".join(window.chunks) == DATA[100:164]

    error = _refusal(lambda: content.stream_content(norm_document_id=unbound, byte_range=None))
    assert (error.code, dict(error.detail_fields)) == (
        ErrorCode.REQUIRED_NORM_UNAVAILABLE, {"reference_kind": "norm_source"}
    )
    error = _refusal(lambda: content.stream_content(
        norm_document_id="ndoc_01ARZ3NDEKTSV4RRFFQ69G5FAV", byte_range=None
    ))
    assert error.code is ErrorCode.NOT_FOUND

    reads = NormsSearchAdapter(corpus.session_factory, timeout_ms=3000)
    assert reads.get_document(norm_document_id=bound).content_available is True
    assert reads.get_document(norm_document_id=unbound).content_available is False


def test_a_binding_whose_object_is_gone_is_a_typed_failure(
    corpus: Corpus, pdf_store: S3BlobStore
) -> None:
    snapshot = corpus.snapshot()
    document = corpus.document(snapshot, SP54, ref="sp54")
    corpus.bind_pdf(document, DATA)  # bound, but never put in this bucket
    content = NormContentAdapter(corpus.session_factory, blob_store=pdf_store)
    error = _refusal(lambda: content.stream_content(norm_document_id=document, byte_range=None))
    assert error.code is ErrorCode.STORAGE_INTEGRITY_ERROR
    assert dict(error.detail_fields)["role"] == "norm_source"
