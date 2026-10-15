"""Exact stored set/version preflight for later approved comparison links."""

from __future__ import annotations

from copy import deepcopy

import pytest

from auditmanager.comparison.version_reader import (
    VersionPairRefused,
    read_ordered_version_pair,
)


PROJECT = "prj_01M2545JSD15ETSNNV904X991J"
OTHER_PROJECT = "prj_01M2545JSD15ETSNNV904X991K"
DOCUMENT = "doc_01M2545JSD15ETSNNV904X991J"
OTHER_DOCUMENT = "doc_01M2545JSD15ETSNNV904X991K"
SOURCE = "ver_01M2545JSD15ETSNNV904X991J"
TARGET = "ver_01M2545JSD15ETSNNV904X991K"
OTHER_VERSION = "ver_01M2545JSD15ETSNNV904X991M"


def _rows():
    base = {
        "version_document_uid": DOCUMENT,
        "set_document_uid": DOCUMENT,
        "project_uid": PROJECT,
        "state": "published",
        "byte_size": 100,
        "page_count": 2,
        "media_type": "application/pdf",
    }
    return [
        base | {"version_uid": SOURCE, "version_ordinal": 1, "sha256": "a" * 64},
        base | {"version_uid": TARGET, "version_ordinal": 3, "sha256": "b" * 64},
    ]


class _Result:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def all(self):
        return self.rows


class _Session:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def execute(self, statement, parameters):
        self.calls.append((str(statement), parameters))
        return _Result(self.rows)


def _read(session, **changes):
    arguments = {
        "session": session,
        "project_uid": PROJECT,
        "document_uid": DOCUMENT,
        "source_version_uid": SOURCE,
        "target_version_uid": TARGET,
    }
    arguments.update(changes)
    return read_ordered_version_pair(**arguments)


def test_exact_membership_and_order_from_one_select() -> None:
    session = _Session(list(reversed(_rows())))
    pair = _read(session)
    assert pair.project_uid == PROJECT
    assert pair.document_uid == DOCUMENT
    assert pair.source.version_uid == SOURCE
    assert pair.target.version_uid == TARGET
    assert pair.source.version_ordinal == 1
    assert pair.target.version_ordinal == 3
    assert pair.source.sha256 == "a" * 64
    assert pair.target.sha256 == "b" * 64
    assert len(session.calls) == 1
    sql, parameters = session.calls[0]
    assert sql.strip().startswith("SELECT")
    assert "JOIN document d ON d.document_uid = v.document_uid" in sql
    assert "source_filename" not in sql and "display_title" not in sql
    assert parameters == {"source_version_uid": SOURCE, "target_version_uid": TARGET}


@pytest.mark.parametrize("rows,reason", [
    ([], "version_pair_incomplete"),
    (_rows()[:1], "version_pair_incomplete"),
    (_rows() + [_rows()[0]], "version_pair_incomplete"),
    ([_rows()[0], _rows()[0]], "version_pair_identity_mismatch"),
    ([_rows()[0], _rows()[1] | {"version_uid": OTHER_VERSION}],
     "version_pair_identity_mismatch"),
])
def test_missing_duplicate_or_foreign_version_row_is_refused(rows, reason: str) -> None:
    with pytest.raises(VersionPairRefused, match=reason):
        _read(_Session(rows))


@pytest.mark.parametrize("column,value,reason", [
    ("version_document_uid", OTHER_DOCUMENT, "version_set_mismatch"),
    ("set_document_uid", OTHER_DOCUMENT, "version_set_mismatch"),
    ("project_uid", OTHER_PROJECT, "version_project_mismatch"),
    ("state", "draft", "version_not_published"),
    ("version_ordinal", 0, "version_ordinal_invalid"),
    ("sha256", "f" * 63, "version_digest_invalid"),
    ("byte_size", -1, "version_byte_size_invalid"),
    ("page_count", 0, "version_page_count_invalid"),
    ("media_type", "text/plain", "version_media_type_invalid"),
])
def test_stored_fact_mismatch_refused(column: str, value, reason: str) -> None:
    rows = deepcopy(_rows())
    rows[1][column] = value
    with pytest.raises(VersionPairRefused, match=reason):
        _read(_Session(rows))


def test_wrong_caller_project_and_set_refused() -> None:
    with pytest.raises(VersionPairRefused, match="version_project_mismatch"):
        _read(_Session(_rows()), project_uid=OTHER_PROJECT)
    with pytest.raises(VersionPairRefused, match="version_set_mismatch"):
        _read(_Session(_rows()), document_uid=OTHER_DOCUMENT)


def test_source_must_precede_target_by_ordinal_not_uid_or_timestamp() -> None:
    rows = deepcopy(_rows())
    rows[0]["version_ordinal"] = 4
    with pytest.raises(VersionPairRefused, match="version_order_invalid"):
        _read(_Session(rows))
    rows[0]["version_ordinal"] = rows[1]["version_ordinal"]
    with pytest.raises(VersionPairRefused, match="version_order_invalid"):
        _read(_Session(rows))


@pytest.mark.parametrize("changes,reason", [
    ({"project_uid": "doc_01M2545JSD15ETSNNV904X991J"}, "project_uid_invalid"),
    ({"document_uid": "prj_01M2545JSD15ETSNNV904X991J"}, "document_uid_invalid"),
    ({"source_version_uid": "source.pdf"}, "source_version_uid_invalid"),
    ({"target_version_uid": SOURCE}, "same_version"),
])
def test_invalid_caller_identity_fails_before_sql(changes, reason: str) -> None:
    session = _Session(_rows())
    with pytest.raises(VersionPairRefused, match=reason):
        _read(session, **changes)
    assert session.calls == []
