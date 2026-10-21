"""W57b saved reference text is exact, bounded and current-Attempt fenced."""

from __future__ import annotations

import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from auditmanager.analysis.public import ArtifactRef, canonical_bytes, sha256_hex
from auditmanager.jobs.public import AttemptAuthority
from auditmanager.norms.references.text_pages import reference_pages_from_text_layer
from auditmanager.runs.reference_text_input import load_saved_reference_text
from auditmanager.runs.repository import StageResultRow
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import VersionUid
from auditmanager.storage.public import BlobIntegrityError


RUN = "run_01M2545JSD15ETSNNV904X991J"
PROJECT = "prj_01M2545JSD15ETSNNV904X991J"
VERSION = "ver_01M2545JSD15ETSNNV904X991J"
AUTHORITY = AttemptAuthority(
    run_id=RUN,
    job_id="job_01M2545JSD15ETSNNV904X991J",
    attempt_id="att_01M2545JSD15ETSNNV904X991J",
    lease_id="lease_01M2545JSD15ETSNNV904X991J",
    execution_token="test-token",
)


def _document(*texts: str, version_uid: str = VERSION) -> dict:
    offset = 0
    pages = []
    for number, value in enumerate(texts, start=1):
        pages.append({
            "page_number": number,
            "char_start": offset,
            "char_end": offset + len(value),
            "text": value,
        })
        offset += len(value)
    return {
        "artifact_role": "prepared.text_layer",
        "artifact_version": "1.0.0",
        "version_uid": version_uid,
        "extractor": {
            "name": "fixture", "version": "1.0.0", "options_sha256": "a" * 64,
        },
        "normalization": {"id": "nfc_v1", "description": "NFC"},
        "total_char_count": offset,
        "pages": pages,
    }


def _ref(role: str, suffix: str, payload: bytes) -> ArtifactRef:
    return ArtifactRef(
        role=role,
        blob_id="blob_01M2545JSD15ETSNNV904X991" + suffix,
        sha256=sha256_hex(payload),
        size_bytes=len(payload),
        media_type="application/json",
    )


class FakeRuns:
    def __init__(self, stage: StageResultRow):
        self.run = SimpleNamespace(
            run_id=RUN, version_uid=VERSION, project_uid=PROJECT, state="running"
        )
        self.stage = stage
        self.get_calls = 0
        self.stage_calls = 0
        self.change_run = False
        self.change_stage = False
        self.change_ref = False
        self.duplicate_stage = False

    def get(self, session: object, run_id: str):
        assert run_id == RUN
        self.get_calls += 1
        return replace_namespace(self.run, state="cancelled") if self.change_run and self.get_calls == 2 else self.run

    def stage_results(self, session: object, run_id: str):
        assert run_id == RUN
        self.stage_calls += 1
        row = replace(self.stage, status="failed") if self.change_stage and self.stage_calls == 2 else self.stage
        if self.change_ref and self.stage_calls == 2:
            inventory, text = row.artifacts
            row = replace(row, artifacts=(inventory, {**text, "sha256": "b" * 64}))
        return (row, row) if self.duplicate_stage else (row,)


def replace_namespace(value: SimpleNamespace, **changes: object) -> SimpleNamespace:
    return SimpleNamespace(**{**vars(value), **changes})


class FakeDocuments:
    def __init__(self):
        self.version = SimpleNamespace(
            version_uid=VersionUid.parse(VERSION), project_uid=PROJECT, page_count=3
        )
        self.calls = 0
        self.change_version = False

    def get_version(self, session: object, version_uid: VersionUid):
        assert isinstance(version_uid, VersionUid)
        self.calls += 1
        if self.change_version and self.calls == 2:
            return replace_namespace(self.version, page_count=4)
        return self.version


class FakeJobs:
    def __init__(self):
        self.calls = 0
        self.stale = False

    def require_current(self, session: object, authority: AttemptAuthority):
        assert authority is AUTHORITY
        self.calls += 1
        if self.stale and self.calls == 2:
            raise DomainError(ErrorCode.STALE_ATTEMPT, aggregate_type="Attempt")


class FakeStore:
    def __init__(self, payload: bytes):
        self.payload = payload
        self.calls: list[tuple[str, str, int]] = []
        self.closed = False
        self.refuse = False
        self.overrun = False

    def open_stream(self, blob_id, *, expected_sha256: str, expected_size: int):
        self.calls.append((str(blob_id), expected_sha256, expected_size))
        if self.refuse:
            raise BlobIntegrityError()

        def chunks():
            try:
                yield self.payload[:13]
                yield self.payload[13:] + (b"!" if self.overrun else b"")
            finally:
                self.closed = True

        return chunks()


def _inputs(document: dict | None = None, payload: bytes | None = None):
    body = payload if payload is not None else canonical_bytes(document or _document("А😀", "", "БВ"))
    text_ref = _ref("prepared.text_layer", "J", body)
    inventory_ref = _ref("prepared.page_inventory", "K", b"{}")
    stage = StageResultRow(
        stage_id="source_preparation", stage_version="1.0.0",
        status="succeeded",
        artifacts=(inventory_ref.to_document(), text_ref.to_document()),
        metrics={}, error=None,
    )
    return FakeRuns(stage), FakeJobs(), FakeDocuments(), FakeStore(body), text_ref


def _load(runs, jobs, documents, store, *, byte_limit=50_000):
    return load_saved_reference_text(
        object(), authority=AUTHORITY, blob_store=store,
        max_input_bytes=byte_limit, runs=runs, jobs=jobs, documents=documents,
    )


def test_exact_text_layer_preserves_cyrillic_offsets_and_empty_page() -> None:
    runs, jobs, documents, store, ref = _inputs()

    result = _load(runs, jobs, documents, store)

    assert (jobs.calls, runs.get_calls, runs.stage_calls, documents.calls) == (2, 2, 2, 2)
    assert store.calls == [(ref.blob_id, ref.sha256, ref.size_bytes)]
    assert store.closed
    assert result.text_layer.document_text == "А😀БВ"
    assert (result.version_uid, result.page_count) == (VERSION, 3)
    pages = reference_pages_from_text_layer(
        text_layer=result.text_layer,
        version_uid=result.version_uid,
        page_count=result.page_count,
    )
    assert [(page.page_number, page.char_start, page.text) for page in pages] == [
        (1, 0, "А😀"), (2, 2, None), (3, 2, "БВ"),
    ]


@pytest.mark.parametrize("change", ["run", "stage", "stage_ref", "version", "attempt"])
def test_second_fence_refuses_changed_authority_or_source(change: str) -> None:
    runs, jobs, documents, store, _ = _inputs()
    if change == "run":
        runs.change_run = True
    elif change == "stage":
        runs.change_stage = True
    elif change == "stage_ref":
        runs.change_ref = True
    elif change == "version":
        documents.change_version = True
    else:
        jobs.stale = True
    with pytest.raises(DomainError) as caught:
        _load(runs, jobs, documents, store)
    assert caught.value.code == (ErrorCode.STALE_ATTEMPT if change == "attempt" else ErrorCode.ANALYSIS_INPUT_INVALID)
    assert store.closed


@pytest.mark.parametrize("change", ["duplicate", "status", "stage_version", "run_version", "version_project"])
def test_bad_saved_identity_refuses_before_blob_open(change: str) -> None:
    runs, jobs, documents, store, _ = _inputs()
    if change == "duplicate":
        runs.duplicate_stage = True
    elif change == "status":
        runs.stage = replace(runs.stage, status="failed")
    elif change == "stage_version":
        runs.stage = replace(runs.stage, stage_version="9.9.9")
    elif change == "run_version":
        runs.run = replace_namespace(runs.run, version_uid="ver_01M2545JSD15ETSNNV904X991K")
    else:
        documents.version = replace_namespace(documents.version, project_uid="prj_01M2545JSD15ETSNNV904X991K")
    with pytest.raises(DomainError):
        _load(runs, jobs, documents, store)
    assert store.calls == []


@pytest.mark.parametrize("limit", [0, True, 20])
def test_invalid_or_small_byte_cap_refuses_before_blob_open(limit: object) -> None:
    runs, jobs, documents, store, _ = _inputs()
    with pytest.raises(DomainError) as caught:
        _load(runs, jobs, documents, store, byte_limit=limit)
    assert caught.value.code == ErrorCode.ANALYSIS_INPUT_INVALID
    assert store.calls == []


@pytest.mark.parametrize("change", ["digest", "size", "overrun", "store_refusal"])
def test_blob_digest_size_and_stream_refusals_close_the_read(change: str) -> None:
    runs, jobs, documents, store, _ = _inputs()
    if change in {"digest", "size"}:
        inventory, text = runs.stage.artifacts
        value = "b" * 64 if change == "digest" else text["size_bytes"] + 1
        key = "sha256" if change == "digest" else "size_bytes"
        runs.stage = replace(runs.stage, artifacts=(inventory, {**text, key: value}))
    elif change == "overrun":
        store.overrun = True
    else:
        store.refuse = True
    with pytest.raises(DomainError):
        _load(runs, jobs, documents, store)
    assert store.closed if change != "store_refusal" else not store.closed


@pytest.mark.parametrize("change", [
    "noncanonical", "wrong_layer_version", "wrong_page_count", "wrong_page_numbers", "bool_offset",
])
def test_self_consistent_blob_with_bad_text_layer_refuses(change: str) -> None:
    document = _document("А😀", "", "БВ")
    if change == "noncanonical":
        payload = json.dumps(document, ensure_ascii=False, indent=2).encode("utf-8")
    else:
        if change == "wrong_layer_version":
            document["version_uid"] = "ver_01M2545JSD15ETSNNV904X991K"
        elif change == "wrong_page_count":
            document["pages"].pop()
            document["total_char_count"] = 2
        elif change == "wrong_page_numbers":
            for page in document["pages"]:
                page["page_number"] += 1
        else:
            document["pages"][0]["char_start"] = False
        payload = canonical_bytes(document)
    runs, jobs, documents, store, _ = _inputs(payload=payload)
    with pytest.raises(DomainError) as caught:
        _load(runs, jobs, documents, store)
    assert caught.value.code == ErrorCode.ANALYSIS_INPUT_INVALID
    assert jobs.calls == 1
    assert store.closed
