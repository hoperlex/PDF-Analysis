"""D-128 F-10: reconciliation must not offer categories it cannot populate."""

from dataclasses import fields

from auditmanager.ingest import ReconciliationReport, UnattributedBlob
from auditmanager.storage import derive_blob_id, sha256_of


def test_report_has_only_observable_blob_categories() -> None:
    names = {field.name for field in fields(ReconciliationReport)}
    assert "unattributed_blobs" in names
    assert "orphan_objects" not in names
    assert "unpublished_records" not in names
    assert "legacy_unattributed_blobs" not in names

    content = b"%PDF-1.7\n%%EOF\n"
    blob = UnattributedBlob(
        blob_id=derive_blob_id(sha256=sha256_of(content), size=len(content)),
        recorded_state="verifying",
        sha256=sha256_of(content),
        size_bytes=len(content),
        object_present=True,
    )
    report = ReconciliationReport(unattributed_blobs=(blob,))
    assert not report.is_clean
    assert report.describe().startswith("unattributed_blobs=1 missing_objects=0 ")
    assert ReconciliationReport().is_clean
