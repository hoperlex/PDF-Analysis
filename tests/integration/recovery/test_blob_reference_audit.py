"""A restored database's declared Blob references are audited without writes."""

from __future__ import annotations

from copy import deepcopy

import pytest

from auditmanager.storage.public import derive_blob_id
from scripts.recovery.schema_coverage import HEAD
from scripts.recovery.blob_reference_audit import (
    BlobFact,
    BlobReferenceAuditRefused,
    audit_blob_references,
)

_CATALOG = [
    {"schema_name": "public", "table_name": table, "column_name": "blob_id"}
    for table in (
        "blob", "input_manifest_entry", "analysis_artifact_publication",
        "norm_custody_admission", "norm_custody_binding", "price_list_revision",
        "comparison_upload_file",  # `0038_comparison_foundation` (CMP-SEAL-C0)
    )
]
_CATALOG.extend([
    {"schema_name": "public", "table_name": "norm_retrieval_set", "column_name": column}
    for column in ("set_blob_id", "catalogue_blob_id")
])
_CATALOG.extend([
    {"schema_name": "public", "table_name": "comparison_page_profile", "column_name": column}
    for column in ("profile_blob_id", "preview_blob_id", "thumbnail_blob_id")
])


class _Rows:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows

    def mappings(self) -> list[dict[str, object]]:
        return self.rows


class _Session:
    def __init__(self, data: dict[str, list[dict[str, object]]]) -> None:
        self.data = data
        self.statements: list[str] = []

    def execute(self, statement: object) -> _Rows:
        sql = str(statement).strip()
        assert sql.upper().startswith("SELECT")
        self.statements.append(sql)
        if "public.alembic_version" in sql:
            key = "version"
        elif "pg_catalog.pg_attribute" in sql:
            key = "catalog"
        elif "FROM public.blob " in sql:
            key = "blob"
        elif "FROM public.input_manifest_entry" in sql:
            key = "manifest"
        elif "FROM public.analysis_artifact_publication" in sql:
            key = "artifacts"
        elif "FROM public.norm_custody_admission" in sql:
            key = "admissions"
        elif "FROM public.norm_custody_binding" in sql:
            key = "bindings"
        elif "FROM public.norm_retrieval_set" in sql:
            key = "retrieval_sets"
        elif "FROM public.price_list_revision" in sql:
            key = "price_lists"
        elif "FROM public.comparison_upload_file" in sql:
            key = "comparison_files"
        elif "FROM public.comparison_page_profile" in sql:
            key = "page_profiles"
        else:
            raise AssertionError(f"unexpected SQL: {sql}")
        return _Rows(self.data[key])


def _data() -> dict[str, list[dict[str, object]]]:
    sha = "a" * 64
    blob_id = str(derive_blob_id(sha256=sha, size=13))
    return {
        "version": [{"version_num": HEAD}],
        "catalog": deepcopy(_CATALOG),
        "blob": [{
            "blob_id": blob_id, "state": "available", "sha256": sha,
            "size_bytes": 13, "media_type": "application/pdf",
        }],
        "manifest": [{
            "owner_id": "ver_one", "role": "source_document", "blob_id": blob_id,
            "sha256": sha, "size_bytes": 13, "media_type": "application/pdf",
        }],
        "artifacts": [{
            "owner_id": "att_one", "stage_id": "extract_pdf", "blob_role": "source_document",
            "blob_id": blob_id, "state": "bound",
        }],
        "admissions": [{
            "owner_id": "nad_one", "blob_id": blob_id, "state": "confirmed",
            "declared_sha256": sha, "declared_size_bytes": 13,
            "media_type": "application/pdf",
        }],
        "bindings": [{"owner_id": "nbd_one", "admission_id": "nad_one", "blob_id": blob_id}],
        "retrieval_sets": [],
        "price_lists": [{
            "owner_id": "prl_one", "blob_id": blob_id, "sha256": sha,
            "size_bytes": 13, "media_type": "application/pdf",
        }],
        # `0038_comparison_foundation`: a verified upload file and a page profile, both holding the blob.
        "comparison_files": [{"owner_id": "cuf_one", "state": "verified", "blob_id": blob_id}],
        "page_profiles": [{
            "owner_id": "cpr_one", "profile_blob_id": blob_id, "preview_blob_id": blob_id,
            "thumbnail_blob_id": None,
        }],
    }


def _data_with_verified_set() -> dict[str, list[dict[str, object]]]:
    data = _data()
    set_sha, catalogue_sha = "b" * 64, "c" * 64
    set_id = str(derive_blob_id(sha256=set_sha, size=7))
    catalogue_id = str(derive_blob_id(sha256=catalogue_sha, size=9))
    data["blob"].extend([
        {"blob_id": set_id, "state": "available", "sha256": set_sha,
         "size_bytes": 7, "media_type": "application/json"},
        {"blob_id": catalogue_id, "state": "available", "sha256": catalogue_sha,
         "size_bytes": 9, "media_type": "application/json"},
    ])
    data["retrieval_sets"] = [{
        "owner_id": "nrs_one", "state": "verified",
        "set_blob_id": set_id, "set_size_bytes": 7,
        "observed_set_sha256": set_sha,
        "catalogue_blob_id": catalogue_id, "catalogue_size_bytes": 9,
        "observed_catalogue_sha256": catalogue_sha,
    }]
    return data


def test_healthy_database_returns_all_available_blob_facts_and_reads_only() -> None:
    data = _data()
    session = _Session(data)
    result = audit_blob_references(session)  # type: ignore[arg-type]
    assert result.available_blobs == (
        BlobFact(data["blob"][0]["blob_id"], "a" * 64, 13, "application/pdf"),
    )
    assert result.source_counts == (
        ("input_manifest_entry", 1), ("analysis_artifact_publication", 1),
        ("norm_custody_admission", 1), ("norm_custody_binding", 1),
        ("norm_retrieval_set", 0), ("price_list_revision", 1),
        ("comparison_upload_file", 1), ("comparison_page_profile", 1),
    )
    assert audit_blob_references(session) == result  # type: ignore[arg-type]
    assert data == session.data
    assert len(session.statements) == 22  # two audits x eleven SELECTs


def test_verified_retrieval_set_reads_both_0023_blob_columns() -> None:
    data = _data_with_verified_set()
    result = audit_blob_references(_Session(data))  # type: ignore[arg-type]
    assert result.source_counts[-4] == ("norm_retrieval_set", 1)
    assert {fact.blob_id for fact in result.available_blobs} == {
        row["blob_id"] for row in data["blob"]
    }


@pytest.mark.parametrize("role,change,reason", (
    ("set", "missing", "names an unavailable"),
    ("catalogue", "missing", "names an unavailable"),
    ("set", "unavailable", "names an unavailable"),
    ("catalogue", "unavailable", "names an unavailable"),
    ("set", "wrong_digest", "set Blob facts differ"),
    ("catalogue", "wrong_digest", "catalogue Blob facts differ"),
    ("set", "wrong_size", "set Blob facts differ"),
    ("catalogue", "wrong_size", "catalogue Blob facts differ"),
))
def test_verified_retrieval_set_requires_both_exact_available_blobs(
    role: str, change: str, reason: str,
) -> None:
    data = _data_with_verified_set()
    row = data["retrieval_sets"][0]
    if change == "missing":
        row[f"{role}_blob_id"] = "blob_" + "0" * 26
    elif change == "unavailable":
        next(blob for blob in data["blob"] if blob["blob_id"] == row[f"{role}_blob_id"])["state"] = "verifying"
    elif change == "wrong_digest":
        row[f"observed_{role}_sha256"] = "0" * 64
    else:
        row[f"{role}_size_bytes"] = 99
    with pytest.raises(BlobReferenceAuditRefused, match=reason):
        audit_blob_references(_Session(data))  # type: ignore[arg-type]


def test_rejected_set_has_no_blob_references() -> None:
    data = _data_with_verified_set()
    row = data["retrieval_sets"][0]
    row.update(state="rejected", set_blob_id=None, set_size_bytes=None,
               catalogue_blob_id=None, catalogue_size_bytes=None)
    assert audit_blob_references(_Session(data)).source_counts[-4] == (  # type: ignore[arg-type]
        "norm_retrieval_set", 1,
    )
    row["catalogue_blob_id"] = data["blob"][2]["blob_id"]
    with pytest.raises(BlobReferenceAuditRefused, match="rejected retrieval set"):
        audit_blob_references(_Session(data))  # type: ignore[arg-type]


def test_price_list_revision_is_a_declared_blob_reference_source() -> None:
    """`0026_price_lists` added a Blob reference; the catalog check must know it by name."""
    data = _data()
    data["catalog"] = [row for row in data["catalog"] if row["table_name"] != "price_list_revision"]
    with pytest.raises(BlobReferenceAuditRefused, match="price_list_revision"):
        audit_blob_references(_Session(data))  # type: ignore[arg-type]


@pytest.mark.parametrize("table", ("comparison_upload_file", "comparison_page_profile"))
def test_the_comparison_tables_are_declared_blob_reference_sources(table: str) -> None:
    """`0038_comparison_foundation` added four Blob references; the catalog check knows them by name."""
    data = _data()
    data["catalog"] = [row for row in data["catalog"] if row["table_name"] != table]
    with pytest.raises(BlobReferenceAuditRefused, match="catalog differs"):
        audit_blob_references(_Session(data))  # type: ignore[arg-type]


@pytest.mark.parametrize("change,reason", (
    ("file_blob_unknown", "comparison_upload_file names an unavailable"),
    ("file_not_verified", "holds a Blob before it is verified"),
    ("profile_preview_unknown", "comparison_page_profile names an unavailable"),
    ("profile_blob_unavailable", "comparison_page_profile names an unavailable"),
))
def test_a_comparison_blob_reference_must_name_an_available_blob(change: str, reason: str) -> None:
    data = _data()
    if change == "file_blob_unknown":
        data["comparison_files"][0]["blob_id"] = "blob_" + "0" * 26
    elif change == "file_not_verified":
        data["comparison_files"][0]["state"] = "uploading"
    elif change == "profile_preview_unknown":
        data["page_profiles"][0]["preview_blob_id"] = "blob_" + "0" * 26
    else:
        data["blob"][0]["state"] = "verifying"
        data["blob"][0].update(sha256=None, size_bytes=None, media_type=None)
        data["manifest"] = []
        data["artifacts"] = []
        data["admissions"] = []
        data["bindings"] = []
        data["price_lists"] = []
        data["comparison_files"] = []
    with pytest.raises(BlobReferenceAuditRefused, match=reason):
        audit_blob_references(_Session(data))  # type: ignore[arg-type]


@pytest.mark.parametrize("catalog_change", ("new_column", "new_fk", "missing_source"))
def test_schema_catalog_is_an_exact_closed_set(catalog_change: str) -> None:
    data = _data()
    if catalog_change == "missing_source":
        data["catalog"].pop()
    else:
        data["catalog"].append({
            "schema_name": "public", "table_name": "export_archive",
            "column_name": "archive_blob_id" if catalog_change == "new_column" else "payload",
        })
    session = _Session(data)
    with pytest.raises(BlobReferenceAuditRefused, match="catalog differs"):
        audit_blob_references(session)  # type: ignore[arg-type]
    assert len(session.statements) == 2


def test_the_0023_head_is_no_longer_accepted() -> None:
    data = _data()
    data["version"] = [{"version_num": "0023_norm_citations"}]
    with pytest.raises(BlobReferenceAuditRefused, match="migration head"):
        audit_blob_references(_Session(data))  # type: ignore[arg-type]


def test_wrong_migration_head_refuses_before_reading_sources() -> None:
    data = _data()
    data["version"] = [{"version_num": "0029_future"}]
    session = _Session(data)
    with pytest.raises(BlobReferenceAuditRefused, match="migration head"):
        audit_blob_references(session)  # type: ignore[arg-type]
    assert len(session.statements) == 1


@pytest.mark.parametrize("change,reason", (
    ("manifest_missing", "input_manifest_entry names an unavailable"),
    ("manifest_facts", "input_manifest_entry facts differ"),
    ("artifact_unavailable", "analysis_artifact_publication names an unavailable"),
    ("artifact_intent_missing", "analysis artifact intent lacks Blob row"),
    ("admission_missing", "norm_custody_admission names an unavailable"),
    ("admission_facts", "confirmed custody facts differ"),
    ("binding_wrong", "custody binding lacks matching confirmed admission"),
    ("price_list_missing", "price_list_revision names an unavailable"),
    ("price_list_unavailable", "price_list_revision names an unavailable"),
    ("price_list_digest", "disagrees with content identity"),
    ("price_list_size", "disagrees with content identity"),
    ("price_list_media", "price_list_revision facts differ"),
))
def test_broken_references_refuse(change: str, reason: str) -> None:
    data = _data()
    blob_id = data["blob"][0]["blob_id"]
    if change == "manifest_missing":
        data["manifest"][0]["blob_id"] = "blob_" + "0" * 26
    elif change == "manifest_facts":
        data["manifest"][0]["media_type"] = "text/plain"
    elif change == "artifact_unavailable":
        data["blob"][0]["state"] = "verifying"
        data["manifest"].clear()
    elif change == "artifact_intent_missing":
        data["artifacts"][0]["state"] = "prepared"
        data["artifacts"][0]["blob_id"] = "blob_" + "0" * 26
    elif change == "admission_missing":
        data["blob"][0]["state"] = "verifying"
        data["manifest"].clear()
        data["artifacts"].clear()
    elif change == "admission_facts":
        data["admissions"][0]["media_type"] = "text/plain"
    elif change == "price_list_missing":
        data["price_lists"][0]["blob_id"] = "blob_" + "0" * 26
    elif change == "price_list_unavailable":
        data["blob"][0]["state"] = "verifying"
        for name in ("manifest", "artifacts", "admissions", "bindings"):
            data[name].clear()
    elif change == "price_list_digest":
        data["price_lists"][0]["sha256"] = "b" * 64
    elif change == "price_list_size":
        data["price_lists"][0]["size_bytes"] = 14
    elif change == "price_list_media":
        data["price_lists"][0]["media_type"] = "text/csv"
    else:
        data["bindings"][0]["admission_id"] = "nad_missing"
    assert blob_id is not None
    with pytest.raises(BlobReferenceAuditRefused, match=reason):
        audit_blob_references(_Session(data))  # type: ignore[arg-type]


def test_pending_and_rejected_admissions_need_no_published_object() -> None:
    data = _data()
    data["manifest"].clear()
    data["artifacts"].clear()
    data["bindings"].clear()
    data["admissions"][0]["state"] = "pending"
    data["price_lists"].clear()
    data["comparison_files"].clear()
    data["page_profiles"].clear()
    data["blob"].clear()
    result = audit_blob_references(_Session(data))  # type: ignore[arg-type]
    assert result.available_blobs == ()
    data["admissions"][0]["state"] = "rejected"
    assert audit_blob_references(_Session(data)).source_counts[2] == (  # type: ignore[arg-type]
        "norm_custody_admission", 1,
    )


def test_unsettled_artifact_can_hold_incomplete_temporary_blob() -> None:
    data = _data()
    data["manifest"].clear()
    data["bindings"].clear()
    data["admissions"].clear()
    data["price_lists"].clear()
    data["comparison_files"].clear()
    data["page_profiles"].clear()
    data["artifacts"][0]["state"] = "abandoned"
    data["blob"][0].update(state="temporary", sha256=None, size_bytes=None, media_type=None)
    assert audit_blob_references(_Session(data)).available_blobs == ()  # type: ignore[arg-type]


def test_content_identity_and_blob_state_are_verified() -> None:
    data = _data()
    data["blob"][0]["sha256"] = "b" * 64
    with pytest.raises(BlobReferenceAuditRefused, match="content identity"):
        audit_blob_references(_Session(data))  # type: ignore[arg-type]
    data["blob"][0]["sha256"] = "a" * 64
    data["blob"][0]["state"] = "future_state"
    with pytest.raises(BlobReferenceAuditRefused, match="unknown state"):
        audit_blob_references(_Session(data))  # type: ignore[arg-type]


def test_unknown_artifact_state_refuses() -> None:
    data = _data()
    data["artifacts"][0]["state"] = "future_state"
    with pytest.raises(BlobReferenceAuditRefused, match="analysis artifact state is unknown"):
        audit_blob_references(_Session(data))  # type: ignore[arg-type]
