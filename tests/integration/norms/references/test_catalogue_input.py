"""Offline custody and Attempt refusals for the unserved W57b catalogue read."""

from __future__ import annotations

from dataclasses import replace

import pytest

from auditmanager.jobs.public import AttemptAuthority
from auditmanager.norms.references.catalogue_input import (
    CatalogueInputRefused,
    load_verified_catalogue,
)
from auditmanager.norms.references.catalogue_query import load_pinned_catalogue
from auditmanager.norms.references.tokens import sql_designation_tokens
from auditmanager.norms.retrieval.artifact import SnapshotBinding
from auditmanager.norms.retrieval.catalogue import CatalogueDocument, build_catalogue
from auditmanager.storage.public import BlobNotFoundError


_SNAPSHOT = "ns_" + "0" * 26
_SET = "nrs_" + "0" * 26
_BLOB = "blob_" + "0" * 26
_AUTH = AttemptAuthority("run_test", "job_test", "att_test", "lease_test", "secret")
_CANONICAL = build_catalogue(
    snapshot=SnapshotBinding(_SNAPSHOT, "reviewed-key", "a" * 64, "bge-build", 1),
    documents=(CatalogueDocument(
        "ndoc_" + "0" * 26, "СП_54.13330.2022",
        sql_designation_tokens("СП_54.13330.2022"), "Residential buildings", "СП",
    ),),
)


class _Rows:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def all(self):
        return self.rows


class _Session:
    def __init__(self, before, after=None):
        self.before = before
        self.after = before if after is None else after
        self.calls = 0

    def execute(self, statement, params):
        sql = str(statement)
        assert "norm_custody_binding set_binding" in sql
        assert "norm_custody_binding cat_binding" in sql
        assert "norm_custody_admission cat_admission" in sql
        assert "cat_blob.state = 'available'" in sql
        assert "count(*) FROM norm_document" in sql
        assert params == {"run_id": _AUTH.run_id}
        self.calls += 1
        return _Rows(self.before if self.calls == 1 else self.after)


class _Jobs:
    def __init__(self, fail_second=False):
        self.calls = 0
        self.fail_second = fail_second

    def require_current(self, session, authority):
        assert authority == _AUTH
        self.calls += 1
        if self.fail_second and self.calls == 2:
            raise CatalogueInputRefused("stale_attempt")


class _Store:
    def __init__(self, data=_CANONICAL.data, fail=False):
        self.data = data
        self.fail = fail
        self.calls = 0
        self.closed = False

    def open_stream(self, blob_id, *, expected_sha256, expected_size):
        self.calls += 1
        assert str(blob_id) == _BLOB
        assert expected_sha256 == _CANONICAL.sha256
        assert expected_size == len(_CANONICAL.data)
        if self.fail:
            raise BlobNotFoundError(blob_id=str(blob_id))
        try:
            yield self.data
        finally:
            self.closed = True


def _row(**changes):
    return {
        "run_state": "validating", "norms_snapshot_id": _SNAPSHOT,
        "norm_retrieval_set_id": _SET, "map_sha256": "b" * 64,
        "reviewed_content_key": "reviewed-key",
        "set_blob_id": "blob_" + "1" * 26,
        "set_sha256": "c" * 64, "set_size_bytes": 42,
        "catalogue_blob_id": _BLOB,
        "catalogue_sha256": _CANONICAL.sha256,
        "catalogue_size_bytes": len(_CANONICAL.data),
        "content_key": "reviewed-key", "content_digest": "a" * 64,
        "document_count": 1, "stored_document_count": 1,
        "binding_count": 2,
        **changes,
    }


def _read(before=None, *, after=None, store=None, jobs=None, cap=10_000_000):
    session = _Session([_row()] if before is None else before, after)
    object_store = store or _Store()
    authority = jobs or _Jobs()
    saved = load_verified_catalogue(
        session, authority=_AUTH, blob_store=object_store,
        max_catalogue_bytes=cap, jobs=authority,
    )
    return saved, session, object_store, authority


def test_exact_pinned_bytes_pass_pure_catalogue_validator():
    saved, session, store, jobs = _read()
    assert saved.run_id == _AUTH.run_id
    assert saved.norm_retrieval_set_id == _SET
    assert saved.catalogue_blob_id == _BLOB
    assert saved.data == _CANONICAL.data
    catalogue = load_pinned_catalogue(
        blob=saved.data, expected=saved.expectation, listed_unparsed_slugs=(),
    )
    assert catalogue.snapshot_id == _SNAPSHOT
    assert len(catalogue.documents) == 1
    assert (session.calls, jobs.calls, store.calls, store.closed) == (2, 2, 1, True)


@pytest.mark.parametrize("before", [[], [_row(), _row()], [_row(run_state="published")]])
def test_missing_duplicate_or_terminal_pin_refuses_before_object_read(before):
    store = _Store()
    with pytest.raises(CatalogueInputRefused):
        _read(before, store=store)
    assert store.calls == 0


@pytest.mark.parametrize("changes", [
    {"binding_count": 1}, {"binding_count": 3},
    {"document_count": 2}, {"stored_document_count": 2},
    {"content_digest": "A" * 64}, {"catalogue_sha256": "invalid"},
])
def test_incomplete_custody_or_snapshot_facts_refuse_before_object_read(changes):
    store = _Store()
    with pytest.raises(CatalogueInputRefused, match="pin_invalid"):
        _read([_row(**changes)], store=store)
    assert store.calls == 0


@pytest.mark.parametrize("cap", [0, True, 10_000_001, len(_CANONICAL.data) - 1])
def test_invalid_or_too_small_ceiling_refuses_before_object_read(cap):
    store = _Store()
    with pytest.raises(CatalogueInputRefused):
        _read(store=store, cap=cap)
    assert store.calls == 0


@pytest.mark.parametrize("payload", [
    _CANONICAL.data[:-1], _CANONICAL.data + b"x",
    b"x" * len(_CANONICAL.data),
])
def test_short_long_or_corrupt_object_refuses_and_closes(payload):
    store = _Store(data=payload)
    with pytest.raises(CatalogueInputRefused):
        _read(store=store)
    assert store.closed


def test_missing_object_refuses_without_fallback():
    with pytest.raises(CatalogueInputRefused, match="catalogue_blob_unreadable"):
        _read(store=_Store(fail=True))


def test_changed_pin_or_stale_attempt_after_read_refuses():
    store = _Store()
    with pytest.raises(CatalogueInputRefused, match="changed_during_read"):
        _read(after=[_row(content_digest="b" * 64)], store=store)
    assert store.closed
    with pytest.raises(CatalogueInputRefused, match="stale_attempt"):
        _read(jobs=_Jobs(fail_second=True))


def test_pure_validator_still_refuses_wrong_content_facts():
    saved, *_ = _read()
    wrong = replace(saved.expectation, content_key="foreign-key")
    with pytest.raises(ValueError, match="content key differs"):
        load_pinned_catalogue(
            blob=saved.data, expected=wrong, listed_unparsed_slugs=(),
        )
