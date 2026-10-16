"""The unserved Run reference chain binds both saved inputs to one pin."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from auditmanager.analysis.public import TextLayer
from auditmanager.jobs.public import AttemptAuthority
from auditmanager.norms.public import (
    ReferencePipelineResult,
    VerifiedCatalogueInput,
)
from auditmanager.norms.references.catalogue_query import CatalogueExpectation
from auditmanager.norms.references.resolution import NEWER
from auditmanager.norms.references.tokens import sql_designation_tokens
from auditmanager.runs import reference_pipeline as chain
from auditmanager.runs.public import ReferenceRunPins, read_run_references
from auditmanager.runs.reference_text_input import SavedReferenceTextInput
from auditmanager.shared.errors import DomainError, ErrorCode


RUN = "run_01M2545JSD15ETSNNV904X991J"
VERSION = "ver_01M2545JSD15ETSNNV904X991J"
SET = "nrs_01M2545JSD15ETSNNV904X991J"
SNAPSHOT = "ns_01M2545JSD15ETSNNV904X991J"
AUTHORITY = AttemptAuthority(
    RUN, "job_01M2545JSD15ETSNNV904X991J",
    "att_01M2545JSD15ETSNNV904X991J",
    "lease_01M2545JSD15ETSNNV904X991J", "test-token",
)
PINS = ReferenceRunPins(RUN, VERSION, SET, SNAPSHOT)


def _catalogue() -> VerifiedCatalogueInput:
    documents = [
        {
            "norm_document_id": f"ndoc_{index:026d}",
            "slug": slug,
            "designation_tokens": sql_designation_tokens(slug),
            "title": slug,
            "doc_type": "СП",
        }
        for index, slug in enumerate(("СП_54.13330.2022", "СП_54.13330.2024"), 1)
    ]
    payload = {
        "catalogue_version": "norm-catalogue-prep-v1",
        "norms_snapshot_id": SNAPSHOT,
        "content_key": "reviewed-key",
        "snapshot_content_digest": "a" * 64,
        "document_count": len(documents),
        "documents": documents,
    }
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    expectation = CatalogueExpectation(
        SNAPSHOT, "reviewed-key", "a" * 64, 2, hashlib.sha256(blob).hexdigest(),
    )
    return VerifiedCatalogueInput(RUN, SET, "blob_01M2545JSD15ETSNNV904X991J", blob, expectation)


def _saved() -> SavedReferenceTextInput:
    text = "См. СП 54.13330.2022."
    layer = TextLayer(
        version_uid=VERSION,
        normalization_id="nfc_v1",
        pages=(
            SimpleNamespace(page_number=1, char_start=0, char_end=len(text), text=text),
            SimpleNamespace(page_number=2, char_start=len(text), char_end=len(text), text=""),
        ),
        document_text=text,
    )
    return SavedReferenceTextInput(layer, VERSION, 2)


class _Rows:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def all(self):
        return self.rows


class _Session:
    def __init__(self):
        self.row = {
            "run_id": RUN,
            "version_uid": VERSION,
            "norm_retrieval_set_id": SET,
            "norms_snapshot_id": SNAPSHOT,
            "state": "running",
        }
        self.final_row = None
        self.calls = 0

    def execute(self, statement, params):
        assert "FROM audit_run WHERE run_id = :run_id" in str(statement)
        assert params == {"run_id": RUN}
        self.calls += 1
        row = self.final_row if self.calls == 2 and self.final_row is not None else self.row
        return _Rows([row])


class _Jobs:
    def __init__(self):
        self.calls = 0
        self.stale_on_final = False

    def require_current(self, session, authority):
        assert authority is AUTHORITY
        self.calls += 1
        if self.stale_on_final and self.calls == 2:
            raise DomainError(ErrorCode.STALE_ATTEMPT, aggregate_type="Attempt")


def _install_readers(monkeypatch, *, saved=None, catalogue=None):
    saved = saved or _saved()
    catalogue = catalogue or _catalogue()
    calls = []

    def read_saved(session, *, authority, blob_store, max_input_bytes, runs, jobs, documents):
        assert authority is AUTHORITY
        assert max_input_bytes == 50_000
        calls.append("saved")
        return saved

    def read_catalogue(session, *, authority, blob_store, max_catalogue_bytes, jobs):
        assert authority is AUTHORITY
        assert max_catalogue_bytes == 20_000
        calls.append("catalogue")
        return catalogue

    monkeypatch.setattr(chain, "load_saved_reference_text", read_saved)
    monkeypatch.setattr(chain, "load_verified_catalogue", read_catalogue)
    return calls


def _read(session, jobs, *, pins=PINS, listed=(), max_catalogue_bytes=20_000):
    return read_run_references(
        session, authority=AUTHORITY, blob_store=object(), pins=pins,
        listed_unparsed_slugs=listed, max_text_bytes=50_000,
        max_catalogue_bytes=max_catalogue_bytes, jobs=jobs,
    )


def test_current_run_produces_grounded_newer_candidate_and_unread_pdf_page(monkeypatch):
    calls = _install_readers(monkeypatch)
    session, jobs = _Session(), _Jobs()

    report = _read(session, jobs)

    assert calls == ["saved", "catalogue"]
    assert (session.calls, jobs.calls) == (2, 2)
    assert report.pins == PINS
    assert report.catalogue_sha256 == _catalogue().expectation.catalogue_sha256
    assert isinstance(report.result, ReferencePipelineResult)
    assert report.result.report.unread_pages == ("2",)
    assert report.result.report.references[0].outcome == NEWER
    candidate, = report.result.newer_candidates
    assert candidate.evidence[0].quote == "СП 54.13330.2022"
    assert candidate.evidence[0].page_number == 1
    assert _read(_Session(), _Jobs()) == report


@pytest.mark.parametrize("field", [
    "run_id", "version_uid", "norm_retrieval_set_id", "norms_snapshot_id",
])
def test_wrong_explicit_pin_refuses_before_source_read(monkeypatch, field):
    calls = _install_readers(monkeypatch)
    wrong = replace(PINS, **{field: "wrong"})
    with pytest.raises(DomainError) as caught:
        _read(_Session(), _Jobs(), pins=wrong)
    assert caught.value.code == ErrorCode.ANALYSIS_INPUT_INVALID
    assert calls == []


@pytest.mark.parametrize("change", ["version", "run", "set", "snapshot"])
def test_reader_must_return_the_same_run_sources(monkeypatch, change):
    saved = _saved()
    catalogue = _catalogue()
    if change == "version":
        saved = replace(saved, version_uid="wrong")
    elif change == "run":
        catalogue = replace(catalogue, run_id="wrong")
    elif change == "set":
        catalogue = replace(catalogue, norm_retrieval_set_id="wrong")
    else:
        catalogue = replace(
            catalogue, expectation=replace(catalogue.expectation, snapshot_id="wrong"),
        )
    _install_readers(monkeypatch, saved=saved, catalogue=catalogue)
    with pytest.raises(DomainError, match="cannot be bound"):
        _read(_Session(), _Jobs())


def test_changed_pin_or_stale_attempt_after_pipeline_refuses(monkeypatch):
    _install_readers(monkeypatch)
    session = _Session()
    session.final_row = {**session.row, "norms_snapshot_id": "ns_changed"}
    with pytest.raises(DomainError, match="cannot be bound"):
        _read(session, _Jobs())

    jobs = _Jobs()
    jobs.stale_on_final = True
    with pytest.raises(DomainError) as caught:
        _read(_Session(), jobs)
    assert caught.value.code == ErrorCode.STALE_ATTEMPT


def test_explicit_unparsed_slug_tuple_is_required(monkeypatch):
    calls = _install_readers(monkeypatch)
    with pytest.raises(DomainError):
        _read(_Session(), _Jobs(), listed=None)
    assert calls == []


@pytest.mark.parametrize("listing", [
    ("",),
    ("e\u0301",),
    ("same", "same"),
    ("\ud800",),
    ("x" * 20_001,),
    ("а" * 6_000, "б" * 5_000),
])
def test_invalid_or_oversized_listing_refuses_before_blob_reads(monkeypatch, listing):
    calls = _install_readers(monkeypatch)
    session, jobs = _Session(), _Jobs()

    with pytest.raises(DomainError) as caught:
        _read(session, jobs, listed=listing)

    assert caught.value.code == ErrorCode.ANALYSIS_INPUT_INVALID
    assert calls == []
    assert (session.calls, jobs.calls) == (0, 0)


@pytest.mark.parametrize("ceiling", [True, 0, 10_000_001])
def test_invalid_catalogue_ceiling_refuses_before_blob_reads(monkeypatch, ceiling):
    calls = _install_readers(monkeypatch)
    with pytest.raises(DomainError) as caught:
        _read(_Session(), _Jobs(), max_catalogue_bytes=ceiling)
    assert caught.value.code == ErrorCode.ANALYSIS_INPUT_INVALID
    assert calls == []


def test_listing_longer_than_verified_snapshot_refuses_before_extraction(monkeypatch):
    calls = _install_readers(monkeypatch)

    def unexpected_extraction(**kwargs):
        pytest.fail("reference extraction must not start for an impossible listing")

    monkeypatch.setattr(chain, "reference_pages_from_text_layer", unexpected_extraction)
    with pytest.raises(DomainError) as caught:
        _read(_Session(), _Jobs(), listed=("a", "b", "c"))

    assert caught.value.code == ErrorCode.ANALYSIS_INPUT_INVALID
    assert calls == ["saved", "catalogue"]
