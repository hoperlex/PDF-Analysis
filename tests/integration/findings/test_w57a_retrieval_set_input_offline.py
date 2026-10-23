"""Offline refusals at the saved W57a retrieval-set Blob boundary."""

from __future__ import annotations

import hashlib

import pytest

from auditmanager.findings.retrieval_set_input import (
    RetrievalSetInputRefused,
    load_verified_retrieval_set,
)
from auditmanager.jobs.public import AttemptAuthority
from auditmanager.storage.public import BlobNotFoundError


_DATA = b'{"verified":"set"}'
_SHA = hashlib.sha256(_DATA).hexdigest()
_BLOB = "blob_00000000000000000000000000"
_AUTH = AttemptAuthority("run_test", "job_test", "att_test", "lease_test", "secret")


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
        assert "norm_custody_binding" in sql
        assert "norm_custody_admission" in sql
        assert "norm_catalogue" in sql
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
            raise RetrievalSetInputRefused("stale_attempt")


class _Store:
    def __init__(self, data=_DATA, fail=False):
        self.data = data
        self.fail = fail
        self.calls = 0
        self.closed = False

    def open_stream(self, blob_id, *, expected_sha256, expected_size):
        self.calls += 1
        assert str(blob_id) == _BLOB
        assert expected_sha256 == _SHA
        assert expected_size == len(_DATA)
        if self.fail:
            raise BlobNotFoundError(blob_id=str(blob_id))
        try:
            yield self.data
        finally:
            self.closed = True


def _row(**changes):
    return {
        "run_state": "validating", "norms_snapshot_id": "ns_test",
        "norm_retrieval_set_id": "nrs_test", "set_blob_id": _BLOB,
        "set_sha256": _SHA, "set_size_bytes": len(_DATA),
        "map_sha256": "a" * 64, "reviewed_content_key": "reviewed",
        **changes,
    }


def _read(before=None, *, after=None, store=None, jobs=None, cap=10_000_000):
    session = _Session([_row()] if before is None else before, after)
    object_store = store or _Store()
    authority = jobs or _Jobs()
    return load_verified_retrieval_set(
        session, authority=_AUTH, blob_store=object_store,
        max_set_bytes=cap, jobs=authority,
    ), session, object_store, authority


def test_verified_set_returns_exact_bytes_after_two_authority_checks():
    saved, session, store, jobs = _read()
    assert saved.data == _DATA
    assert (saved.run_id, saved.norm_retrieval_set_id, saved.set_sha256) == (
        _AUTH.run_id, "nrs_test", _SHA,
    )
    assert saved.map_sha256 == "a" * 64
    assert (session.calls, jobs.calls, store.calls, store.closed) == (2, 2, 1, True)


@pytest.mark.parametrize("before", [[], [_row(), _row()], [_row(run_state="published")]])
def test_missing_duplicate_or_terminal_pin_refuses_before_blob_read(before):
    store = _Store()
    with pytest.raises(RetrievalSetInputRefused):
        _read(before, store=store)
    assert store.calls == 0


def test_byte_ceiling_refuses_before_blob_read():
    store = _Store()
    with pytest.raises(RetrievalSetInputRefused, match="verified_set_pin_invalid"):
        _read(store=store, cap=len(_DATA) - 1)
    assert store.calls == 0


def test_invalid_map_identity_refuses_before_blob_read():
    store = _Store()
    with pytest.raises(RetrievalSetInputRefused, match="verified_set_pin_invalid"):
        _read(before=[_row(map_sha256="A" * 64)], store=store)
    assert store.calls == 0


@pytest.mark.parametrize("payload", [_DATA[:-1], _DATA + b"x", b"x" * len(_DATA)])
def test_short_long_or_corrupt_saved_object_refuses_and_closes(payload):
    store = _Store(data=payload)
    with pytest.raises(RetrievalSetInputRefused):
        _read(store=store)
    assert store.closed


def test_custody_or_attempt_drift_after_object_read_refuses():
    store = _Store()
    with pytest.raises(RetrievalSetInputRefused, match="changed_during_read"):
        _read(after=[_row(reviewed_content_key="other")], store=store)
    assert store.closed
    with pytest.raises(RetrievalSetInputRefused, match="stale_attempt"):
        _read(jobs=_Jobs(fail_second=True))


def test_missing_object_refuses_without_fallback():
    with pytest.raises(RetrievalSetInputRefused, match="set_blob_unreadable"):
        _read(store=_Store(fail=True))
