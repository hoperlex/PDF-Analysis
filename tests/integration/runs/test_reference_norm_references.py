"""`NORM-REFS-RUN-01`: a stored Run's cited norms, per request, without a container.

``read_run_norm_references`` composes the Run row, its Version, the Run's saved page text
(a port the composition root implements) and the pinned snapshot's catalogue into the
unchanged W57b chain. The fakes below answer the exact SQL statements of
``read_snapshot_catalogue`` from a Python list and record every statement, so what these
prove is the composition: the explicit states, the order of the preconditions (a Run with no
pinned snapshot never reads text), refusals as ``internal_error`` (never an empty answer),
a storage error passing through untouched, and a read that writes nothing. The SQL itself is
proved on PostgreSQL by ``tests/integration/norms/references/test_snapshot_catalogue_db.py``.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.norms.references import read_model
from auditmanager.norms.references import snapshot_catalogue as catalogue_module
from auditmanager.norms.references.tokens import sql_designation_tokens
from auditmanager.runs import reference_pipeline as chain
from auditmanager.runs.reference_pipeline import (
    STATE_READY,
    STATE_SNAPSHOT_NOT_PINNED,
    STATE_TEXT_UNAVAILABLE,
    STATE_TOO_MANY_CITATIONS,
    STATES,
    RunNormReferences,
    SavedRunPageText,
    read_run_norm_references,
)
from auditmanager.shared.errors import DomainError, ErrorCode

RUN = "run_01M2545JSD15ETSNNV904X991J"
VERSION = "ver_01M2545JSD15ETSNNV904X991J"
PROJECT = "prj_01M2545JSD15ETSNNV904X991J"
SNAPSHOT = "ns_01M2545JSD15ETSNNV904X991J"
SHA = "a" * 64

SP_2022 = "СП_54_13330_2022__Свод_правил__Здания_жилые"
SP_2024 = "СП_54_13330_2024__Свод_правил__Здания_жилые"
MDS = "МДС_12-24_2006__Устройство_обычных"
PAGES = {1: "Здания по СП 54.13330.2022 и ГОСТ 21.101-2020.", 2: "", 3: "Снова СП 54.13330.2022."}


class _Runs:
    def __init__(self, *, snapshot: str | None = SNAPSHOT, run_id: str = RUN) -> None:
        self.row = SimpleNamespace(
            run_id=run_id, project_uid=PROJECT, version_uid=VERSION,
            norms_snapshot_id=snapshot, state="published",
        )
        self.missing = False

    def get(self, session: Any, run_id: str) -> Any:
        if self.missing:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="AuditRun")
        assert run_id == RUN
        return self.row


class _Documents:
    def __init__(self, **changes: Any) -> None:
        self.row = SimpleNamespace(version_uid=VERSION, project_uid=PROJECT, page_count=3)
        self.row.__dict__.update(changes)

    def get_version(self, session: Any, version_uid: Any) -> Any:
        assert str(version_uid) == VERSION
        return self.row


class _Reader:
    def __init__(self, answer: Any = "default") -> None:
        self.answer = (
            SavedRunPageText(RUN, SHA, dict(PAGES)) if isinstance(answer, str) else answer
        )
        self.calls: list[dict[str, Any]] = []

    def saved_page_text(self, session: Any, **keywords: Any) -> Any:
        self.calls.append(keywords)
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


class _Result:
    def __init__(self, rows: list[dict[str, Any]], scalar: Any = None) -> None:
        self._rows, self._scalar = rows, scalar

    def mappings(self) -> "_Result":
        return self

    def all(self) -> list[dict[str, Any]]:
        return list(self._rows)

    def scalar_one_or_none(self) -> Any:
        return self._scalar


class _Session:
    """The pinned snapshot's documents, answering the two catalogue statements."""

    def __init__(self, slugs: tuple[str, ...] = (SP_2022, SP_2024, MDS), *,
                 declared: int | None | str = "all", tokens: dict[str, list[str]] | None = None):
        self.rows = [
            {
                "norm_document_id": f"ndoc_{number:026d}",
                "slug": slug,
                "designation_tokens": (tokens or {}).get(slug, list(sql_designation_tokens(slug))),
            }
            for number, slug in enumerate(slugs, 1)
        ]
        self.declared = len(self.rows) if declared == "all" else declared
        self.statements: list[str] = []

    def execute(self, statement: Any, parameters: dict[str, Any]) -> _Result:
        self.statements.append(" ".join(str(statement).split()))
        assert parameters["snapshot_id"] == SNAPSHOT
        if statement is catalogue_module._DECLARED_COUNT:
            return _Result([], self.declared)
        assert statement is catalogue_module._DOCUMENT_PAGE
        page = [r for r in self.rows if r["norm_document_id"] > parameters["after"]]
        return _Result(page[: parameters["page_size"]])


def _read(session: Any = None, *, runs: Any = None, documents: Any = None, reader: Any = None,
          run_id: str = RUN) -> RunNormReferences:
    return read_run_norm_references(
        session if session is not None else _Session(),
        run_id=run_id,
        reader=reader if reader is not None else _Reader(),
        runs=runs or _Runs(),
        documents=documents or _Documents(),
    )


def _refused(code: ErrorCode, **keywords: Any) -> DomainError:
    with pytest.raises(DomainError) as refused:
        _read(**keywords)
    assert refused.value.code is code
    return refused.value


# --- ready ---------------------------------------------------------------------------------


def test_a_stored_run_lists_its_cited_norms_against_its_pinned_snapshot() -> None:
    session, reader = _Session(), _Reader()

    answer = _read(session, reader=reader)

    assert (answer.state, answer.run_id, answer.version_uid) == (STATE_READY, RUN, VERSION)
    assert (answer.page_count, answer.norms_snapshot_id, answer.text_layer_sha256) == (3, SNAPSHOT, SHA)
    model = answer.references
    assert model is not None
    assert (model.norms_snapshot_id, model.snapshot_document_count, model.unread_pages) == (SNAPSHOT, 3, (2,))
    assert [(i.cited, i.outcome, i.matched_designation) for i in model.items] == [
        ("СП 54.13330.2022", "newer_edition", "СП 54.13330.2024"),
        ("ГОСТ 21.101-2020", "not_in_corpus", None),
    ]
    assert [a.page_number for a in model.items[0].anchors] == [1, 3]
    assert [u.slug for u in model.unrecognised] == [MDS]
    assert reader.calls == [{"run_id": RUN, "version_uid": VERSION, "page_count": 3}]


def test_the_read_sends_select_statements_only() -> None:
    session = _Session()

    _read(session)

    assert session.statements and all(s.upper().startswith("SELECT") for s in session.statements)


def test_the_same_stored_run_gives_the_same_answer() -> None:
    assert _read() == _read()


# --- explicit states, in the order the preconditions are checked ---------------------------


def test_a_run_that_pinned_no_snapshot_says_so_and_reads_neither_text_nor_snapshot() -> None:
    session, reader = _Session(), _Reader()

    answer = _read(session, runs=_Runs(snapshot=None), reader=reader)

    assert (answer.state, answer.norms_snapshot_id, answer.references) == (
        STATE_SNAPSHOT_NOT_PINNED, None, None,
    )
    assert (reader.calls, session.statements) == ([], [])


def test_a_run_without_a_saved_text_layer_says_so_and_reads_no_snapshot() -> None:
    session = _Session()

    answer = _read(session, reader=_Reader(None))

    assert (answer.state, answer.text_layer_sha256, answer.references) == (
        STATE_TEXT_UNAVAILABLE, None, None,
    )
    assert answer.norms_snapshot_id == SNAPSHOT
    assert session.statements == []


def test_too_many_distinct_citations_is_an_explicit_state_not_a_cut_list(monkeypatch) -> None:
    monkeypatch.setattr(read_model, "MAX_CITED_NORMS", 1)

    answer = _read()

    assert (answer.state, answer.references) == (STATE_TOO_MANY_CITATIONS, None)
    assert answer.text_layer_sha256 == SHA


def test_the_states_are_these_four_in_this_order() -> None:
    assert STATES == (
        "ready", "snapshot_not_pinned", "text_unavailable", "too_many_citations",
    )


# --- refusals: never an empty answer ---------------------------------------------------------


def test_an_unknown_run_is_not_found() -> None:
    runs = _Runs()
    runs.missing = True
    refused = _refused(ErrorCode.NOT_FOUND, runs=runs)
    assert refused.detail_fields == {"aggregate_type": "AuditRun"}


@pytest.mark.parametrize("run_id", ["", "run_x", "ver_01M2545JSD15ETSNNV904X991J", None, 7])
def test_a_malformed_run_id_is_a_validation_failure_before_any_read(run_id) -> None:
    reader = _Reader()
    refused = _refused(ErrorCode.VALIDATION_FAILED, run_id=run_id, reader=reader)
    assert refused.detail_fields == {"field": "run_id", "constraint": "pattern"}
    assert reader.calls == []


@pytest.mark.parametrize(
    "changes",
    [
        {"version_uid": "ver_01M2545JSD15ETSNNV904X9910"},
        {"project_uid": "prj_01M2545JSD15ETSNNV904X9910"},
        {"page_count": 0},
        {"page_count": True},
        {"page_count": None},
    ],
)
def test_a_version_that_is_not_the_runs_is_an_internal_error(changes) -> None:
    reader = _Reader()
    _refused(ErrorCode.INTERNAL_ERROR, documents=_Documents(**changes), reader=reader)
    assert reader.calls == []


def test_a_run_whose_version_identity_is_invalid_is_an_internal_error() -> None:
    runs = _Runs()
    runs.row.version_uid = "not-a-version"
    _refused(ErrorCode.INTERNAL_ERROR, runs=runs)


@pytest.mark.parametrize(
    "answer",
    [
        SavedRunPageText("run_01M2545JSD15ETSNNV904X9910", SHA, dict(PAGES)),
        SavedRunPageText(RUN, "A" * 64, dict(PAGES)),
        SavedRunPageText(RUN, "a" * 63, dict(PAGES)),
        SavedRunPageText(RUN, SHA, {1: "x", 2: "y"}),
        SavedRunPageText(RUN, SHA, {1: "x", 2: "y", 3: "z", 4: "w"}),
        SavedRunPageText(RUN, SHA, {1: "x", 2: "y", 4: "w"}),
        SavedRunPageText(RUN, SHA, {1: "x", 2: None, 3: "z"}),
        SavedRunPageText(RUN, SHA, [("1", "x")]),
        SimpleNamespace(run_id=RUN, text_layer_sha256=SHA, pages=dict(PAGES)),
    ],
)
def test_a_saved_text_that_does_not_match_the_run_is_an_internal_error(answer) -> None:
    _refused(ErrorCode.INTERNAL_ERROR, reader=_Reader(answer))


def test_a_storage_integrity_error_from_the_reader_passes_through_unchanged() -> None:
    """A layer that exists but fails its digest raises; it is never reported as unavailable."""
    failure = DomainError(ErrorCode.STORAGE_INTEGRITY_ERROR, blob_id="b", role="r", expected_sha256="s")

    with pytest.raises(DomainError) as raised:
        _read(reader=_Reader(failure))

    assert raised.value is failure


@pytest.mark.parametrize(
    "session",
    [
        _Session(declared=None),
        _Session(declared=2),
        _Session(declared=4),
        _Session(tokens={SP_2022: ["сп", "54"]}),
    ],
    ids=["snapshot-absent", "stores-more", "stores-fewer", "tokens-differ-from-twin"],
)
def test_a_pinned_snapshot_that_cannot_be_read_whole_is_an_internal_error(session) -> None:
    refused = _refused(ErrorCode.INTERNAL_ERROR, session=session)
    assert "pinned snapshot" in str(refused)
