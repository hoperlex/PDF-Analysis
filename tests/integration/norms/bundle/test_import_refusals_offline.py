"""`W54-BUNDLE-01`: the importer refuses, before it touches the database, every bundle and
copy record that cannot admit an import.

Container-free: the stand's database is an object that fails the test if anything reaches
it, so each refusal below is shown to come before the first statement. The refusals that
need the database (a drifted fingerprint, a ``rejected`` manifest Blob, a conflicting
snapshot) are in ``test_bundle_postgres.py``.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path

import pytest

from auditmanager.norms.bundle.cli import main
from auditmanager.norms.bundle.contents import DOCUMENTS_FILE, PARAGRAPHS_FILE, read_rows
from auditmanager.norms.bundle.errors import EXIT_REFUSED, BundleRefused
from auditmanager.norms.bundle.export import write_bundle
from auditmanager.norms.bundle.layout import (
    MANIFEST_NAME,
    SUMS_NAME,
    bundle_name,
    parse_sums,
    render_sums,
)
from auditmanager.norms.bundle.manifest import parse_manifest, validate_manifest
from auditmanager.norms.bundle.stand import (
    Stand,
    import_bundle,
    report_bundle,
    requeue_bundle,
)
from auditmanager.norms.custody import binding_digest
from auditmanager.norms.repository import validate_snapshot_rows
from tests.integration.norms.bundle.support import (
    record_fields,
    record_text,
    synthetic_rows,
    write_drop,
)
from tests.integration.norms.bundle.test_export_offline import _source


class Untouchable:
    """Stands in for the engine and the session factory; any use fails the test."""

    def __getattr__(self, name: str):
        raise AssertionError(f"the database was reached ({name}) before the refusal")

    def __call__(self, *args, **kwargs):
        raise AssertionError("the database was reached before the refusal")


STAND = Stand(session_factory=Untouchable(), engine=Untouchable())  # type: ignore[arg-type]


@pytest.fixture
def bundle(tmp_path: Path) -> Path:
    corpus, sums = write_drop(tmp_path / "drop")
    return write_bundle(
        _source(synthetic_rows()), corpus=corpus, drop_sums=sums, ledger=None, out=tmp_path / "out"
    ).directory


@pytest.fixture
def unbuilt(tmp_path: Path) -> Path:
    corpus, sums = write_drop(tmp_path / "drop-unbuilt")
    return write_bundle(
        _source(synthetic_rows(), with_build=False), corpus=corpus, drop_sums=sums, ledger=None,
        out=tmp_path / "out-unbuilt",
    ).directory


def _record(tmp_path: Path, **overrides) -> Path:
    path = tmp_path / "record.json"
    path.write_text(record_text(record_fields(**overrides)), encoding="utf-8")
    return path


def _refused(directory: Path, record: Path | None) -> BundleRefused:
    with pytest.raises(BundleRefused) as refused:
        import_bundle(directory, copy_record=record, stand=STAND, say=lambda _line: None)
    return refused.value


def test_a_bundle_without_a_complete_build_is_refused(tmp_path: Path, unbuilt: Path) -> None:
    assert _refused(unbuilt, _record(tmp_path)).reason == "build_absent"


@pytest.mark.parametrize(
    "overrides, reason",
    [
        (None, "copy_record_absent"),
        ({"state": "closed"}, "copy_record_closed"),
        ({"kind": "copy", "attested": False}, "copy_record_unattested"),
        ({"expires_offset": -60}, "copy_record_expired"),
        ({"kind": "copy", "quiesced_offset": -50000}, "copy_record_expired"),
        ({"real_data_marker": True}, "waiver_after_real_data"),
        ({"purpose": "publish"}, "copy_record_not_import"),
    ],
)
def test_a_record_that_cannot_admit_an_import_is_refused_before_the_database(
    tmp_path: Path, bundle: Path, overrides: dict | None, reason: str
) -> None:
    record = None if overrides is None else _record(tmp_path, **overrides)
    assert _refused(bundle, record).reason == reason


def test_a_tampered_bundle_is_refused_before_the_record_is_read(tmp_path: Path, bundle: Path) -> None:
    (bundle / PARAGRAPHS_FILE).write_bytes((bundle / PARAGRAPHS_FILE).read_bytes().replace("пункт".encode(), "ПУНКТ".encode()))
    assert _refused(bundle, None).reason == "bundle_bytes"


def _resign(directory: Path, relative: str, data: bytes, *, update_row_digest: bool = False) -> Path:
    """Rewrite one file *and* every digest naming it: a self-consistent forgery."""
    (directory / relative).write_bytes(data)
    sha = hashlib.sha256(data).hexdigest()
    manifest = json.loads((directory / MANIFEST_NAME).read_text())
    if update_row_digest:
        manifest["row_digest"]["sha256"] = read_rows(directory).row_digest
    for entry in manifest["files"]:
        if entry["path"] == relative:
            entry["sha256"], entry["size"] = sha, len(data)
    (directory / MANIFEST_NAME).write_text(json.dumps(manifest, sort_keys=True, indent=1) + "\n")
    sums = parse_sums((directory / SUMS_NAME).read_bytes())
    sums[relative] = sha
    sums[MANIFEST_NAME] = hashlib.sha256((directory / MANIFEST_NAME).read_bytes()).hexdigest()
    rendered = render_sums(sums)
    (directory / SUMS_NAME).write_bytes(rendered)
    return directory.rename(directory.with_name(bundle_name(directory.name.rsplit("+", 1)[0], rendered)))


def test_rows_re_signed_after_the_export_do_not_digest_as_the_manifest_says(tmp_path: Path, bundle: Path) -> None:
    data = (bundle / PARAGRAPHS_FILE).read_bytes().replace("пункт".encode(), "ПУНКТ".encode())
    forged = _resign(bundle, PARAGRAPHS_FILE, data)
    refused = _refused(forged, _record(tmp_path))
    assert refused.reason == "bundle_rows_invalid" and "digest" in refused.message


def test_checksum_consistent_invalid_rows_refuse_before_database_or_custody(
    tmp_path: Path, bundle: Path
) -> None:
    documents = [json.loads(line) for line in (bundle / DOCUMENTS_FILE).read_text().splitlines()]
    documents[0]["paragraph_count"] += 1
    data = b"".join(
        (json.dumps(document, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n")
        .encode("utf-8") for document in documents
    )
    forged = _resign(bundle, DOCUMENTS_FILE, data, update_row_digest=True)
    manifest = parse_manifest((forged / MANIFEST_NAME).read_bytes())
    assert read_rows(forged).row_digest == manifest.row_digest
    refused = _refused(forged, _record(tmp_path))
    assert refused.reason == "bundle_rows_invalid"
    assert "paragraph ordinals" in refused.message


def test_synthetic_fixture_rows_are_semantically_valid() -> None:
    validate_snapshot_rows(synthetic_rows())


def _resign_pdf_slot_damage(directory: Path, damage: str) -> Path:
    manifest = parse_manifest((directory / MANIFEST_NAME).read_bytes())
    pdf = next(
        entry for entry in manifest.files_of("object")
        if len(entry.slots) == 1 and entry.slots[0].anchor_kind == "pdf"
    )
    if damage == "missing":
        files = tuple(entry for entry in manifest.files if entry != pdf)
        counts = dataclasses.replace(manifest.counts, objects=manifest.counts.objects - 1,
                                     slots=manifest.counts.slots - 1)
        changed = dataclasses.replace(manifest, files=files, counts=counts,
                                      object_bytes=manifest.object_bytes - pdf.size,
                                      binding_count=manifest.binding_count - 1)
        (directory / pdf.path).unlink()
    else:
        bad_slot = dataclasses.replace(pdf.slots[0], anchor="doc_" + "f" * 32)
        slots = (bad_slot,) if damage == "wrong_anchor" else (*pdf.slots, bad_slot)
        changed_file = dataclasses.replace(pdf, slots=slots)
        files = tuple(changed_file if entry == pdf else entry for entry in manifest.files)
        extra = int(damage == "extra")
        counts = dataclasses.replace(manifest.counts, slots=manifest.counts.slots + extra)
        changed = dataclasses.replace(manifest, files=files, counts=counts,
                                      binding_count=manifest.binding_count + extra)
    changed = dataclasses.replace(changed, binding_digest=binding_digest(changed.binding_entries()))
    validate_manifest(changed)  # the existing internal checks accept this self-consistent forgery
    (directory / MANIFEST_NAME).write_bytes(changed.render())
    sums = parse_sums((directory / SUMS_NAME).read_bytes())
    if damage == "missing":
        del sums[pdf.path]
    sums[MANIFEST_NAME] = hashlib.sha256((directory / MANIFEST_NAME).read_bytes()).hexdigest()
    rendered = render_sums(sums)
    (directory / SUMS_NAME).write_bytes(rendered)
    return directory.rename(directory.with_name(bundle_name(changed.content_key, rendered)))


@pytest.mark.parametrize("damage", ["missing", "wrong_anchor", "extra"])
def test_import_refuses_pdf_slots_that_do_not_match_document_rows_before_database(
    tmp_path: Path, bundle: Path, damage: str
) -> None:
    forged = _resign_pdf_slot_damage(bundle, damage)
    assert _refused(forged, _record(tmp_path)).reason == "bundle_source_slots_invalid"


def test_the_cli_prints_the_refusal_and_exits_2(tmp_path: Path, bundle: Path, capsys) -> None:
    status = main(["import", str(bundle), "--copy-record", str(tmp_path / "none.json")],
                  stand_factory=lambda _store: STAND)
    assert status == EXIT_REFUSED
    assert "bundle: REFUSED [copy_record_absent]" in capsys.readouterr().err


def test_report_and_requeue_refuse_a_bundle_whose_manifest_was_altered(tmp_path: Path, bundle: Path) -> None:
    manifest = bundle / MANIFEST_NAME
    manifest.write_bytes(manifest.read_bytes().replace(b'"manifest_version": 1', b'"manifest_version": 2'))
    with pytest.raises(BundleRefused, match="bundle_bytes"):
        report_bundle(bundle, copy_record=_record(tmp_path), stand=STAND, say=lambda _line: None)
    with pytest.raises(BundleRefused, match="bundle_bytes"):
        requeue_bundle(bundle, stand=STAND, say=lambda _line: None)


def test_verify_re_hashes_every_byte(tmp_path: Path, bundle: Path, capsys) -> None:
    assert main(["verify", str(bundle)]) == 0
    assert "every byte re-hashed" in capsys.readouterr().out
    obj = next(path for path in (bundle / "objects").rglob("*.pdf"))
    obj.chmod(0o644)
    obj.write_bytes(b"other")
    assert main(["verify", str(bundle)]) == EXIT_REFUSED
    assert "REFUSED [bundle_bytes]" in capsys.readouterr().err


def test_import_refuses_loudly_while_the_storage_surface_lacks_the_adapter(monkeypatch) -> None:
    """ALR-05: the store comes through ``storage.public`` or not at all -- never a deep import."""
    import auditmanager.storage.public as storage_public
    from auditmanager.norms.bundle.cli import blob_store_from_environment

    monkeypatch.delattr(storage_public, "S3BlobStore", raising=False)
    with pytest.raises(BundleRefused, match="blob_store_unavailable"):
        blob_store_from_environment()
