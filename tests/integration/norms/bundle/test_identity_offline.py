"""`W54-FIX-PY`: a bundle proves its rows came from the drop and the ledger it names.

`W54-JUDGE-Y` F1: nothing checked that the promoted rows were the drop's text and the
ledger's repairs, so a bundle could pair drop A's text with drop B's PDFs and ledger L2 and
still report a full match. F2: the manifest's snapshot facts were never compared with the
imported rows. F3: the ledger did not say which ``SHA256SUMS`` its crops were checked
against. Each case below fails on the code before the fix (the export or the import went
through).

Container-free: the export's database half is :func:`test_export_offline._source`; the
importer's database is an object that fails the test if it is reached.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path

import pytest

from auditmanager.norms.bundle.errors import BundleRefused
from auditmanager.norms.bundle.export import write_bundle
from auditmanager.norms.bundle.layout import MANIFEST_NAME, SUMS_NAME, bundle_name, parse_sums, render_sums
from auditmanager.norms.bundle.manifest import parse_manifest
from auditmanager.norms.bundle.stand import import_bundle
from auditmanager.norms.repair import PageRepair, RepairLedger, RepairOutcome, ledger_of
from auditmanager.norms.repair_journal import ledger_document
from tests.integration.norms.bundle.support import (
    base_snapshot,
    default_documents,
    record_fields,
    record_text,
    synthetic_rows,
    write_drop,
)
from tests.integration.norms.bundle.test_export_offline import _source
from tests.integration.norms.bundle.test_import_refusals_offline import STAND

FIRST = default_documents()[0]
BLOCK_A = "blk_" + "a" * 32
BLOCK_B = "blk_" + "b" * 32


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _repair(block_id: str, outcome: RepairOutcome, *, replacement: str | None = None,
            crop: bytes | None = None, slug: str = FIRST.slug) -> PageRepair:
    text = next(text for block, _page, text in FIRST.blocks if block == block_id) if slug == FIRST.slug else ""
    return PageRepair(
        document_slug=slug,
        block_id=block_id,
        page_label=1,
        original_sha256=_sha(text.encode("utf-8")),
        original_characters=len(text),
        crop_sha256=_sha(FIRST.crops[block_id] if crop is None else crop),
        outcome=outcome,
        replacement=replacement,
        attempts=(),
    )


def _ledger(*repairs: PageRepair) -> RepairLedger:
    return ledger_of(base_snapshot().snapshot_id, "2026-10-12T00:00:00+00:00", repairs)


def _write_ledger(where: Path, ledger: RepairLedger, sums: Path | None, *, field: bool = True) -> Path:
    path = where / "ledger.json"
    if field:
        assert sums is not None
        document = ledger_document(ledger, drop_sums_sha256=_sha(sums.read_bytes()))
    else:
        document = ledger.as_document()
    path.write_text(json.dumps(document, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return path


REPAIRED = _ledger(
    _repair(BLOCK_A, RepairOutcome.REPAIRED, replacement="1.1. Восстановленный текст первого пункта."),
    _repair(BLOCK_B, RepairOutcome.STILL_DEGENERATE),
)


@pytest.fixture
def drop(tmp_path: Path) -> tuple[Path, Path]:
    return write_drop(tmp_path / "drop")


def _export(tmp_path: Path, drop, rows, ledger: Path | None = None):
    corpus, sums = drop
    return write_bundle(_source(rows), corpus=corpus, drop_sums=sums, ledger=ledger, out=tmp_path / "out")


def _refused(tmp_path: Path, drop, rows, ledger: Path | None = None) -> BundleRefused:
    with pytest.raises(BundleRefused) as refused:
        _export(tmp_path, drop, rows, ledger)
    out = tmp_path / "out"
    assert not out.exists() or list(out.iterdir()) == [], "a refused export left a directory"
    return refused.value


# --- F1: the rows are the drop's text --------------------------------------------------


def test_a_repaired_export_whose_keys_the_drop_and_ledger_derive_is_written(tmp_path: Path, drop) -> None:
    rows = synthetic_rows(ledger=REPAIRED)
    assert "+1r+1u." in rows.snapshot.content_key
    result = _export(tmp_path, drop, rows, _write_ledger(tmp_path, REPAIRED, drop[1]))
    assert result.manifest.content_key == rows.snapshot.content_key
    assert result.manifest.ledger is not None and result.manifest.ledger.applied == ((FIRST.slug, BLOCK_A),)


def test_rows_of_another_drops_text_are_refused(tmp_path: Path, drop) -> None:
    """The judge's case: the rows name drop A, the bundle is built from drop B's bytes."""
    rows = synthetic_rows()
    other = [dataclasses.replace(document, blocks=[(block, page, text + " Изменено.") for block, page, text in document.blocks])
             if document.slug == FIRST.slug else document for document in default_documents()]
    other_drop = write_drop(tmp_path / "other", other)
    assert _refused(tmp_path, other_drop, rows).reason == "base_key_differs"


def test_a_base_key_the_rows_do_not_derive_is_refused(tmp_path: Path, drop) -> None:
    rows = synthetic_rows()
    forged = "undated+0d.0123456789ab"
    rows = dataclasses.replace(rows, snapshot=dataclasses.replace(rows.snapshot, base_content_key=forged,
                                                                   content_key=forged))
    assert _refused(tmp_path, drop, rows).reason == "base_key_differs"


def test_an_unrepaired_content_digest_other_than_the_drops_is_refused(tmp_path: Path, drop) -> None:
    rows = synthetic_rows()
    rows = dataclasses.replace(rows, snapshot=dataclasses.replace(rows.snapshot, content_digest="0" * 64))
    assert _refused(tmp_path, drop, rows).reason == "content_key_differs"


def test_a_row_save_date_other_than_the_drops_is_refused(tmp_path: Path, drop) -> None:
    rows = synthetic_rows()
    rows = dataclasses.replace(rows, documents=tuple(
        dataclasses.replace(row, drawn_on="2026-07-24") if row.slug == FIRST.slug else row for row in rows.documents
    ))
    assert _refused(tmp_path, drop, rows).reason == "drop_document_differs"


def test_rows_repaired_by_another_ledger_are_refused(tmp_path: Path, drop) -> None:
    """Same counts, other replacement text: ledger L2 cannot ride under L1's rows."""
    other = _ledger(
        _repair(BLOCK_A, RepairOutcome.REPAIRED, replacement="1.1. Другой текст первого пункта."),
        _repair(BLOCK_B, RepairOutcome.STILL_DEGENERATE),
    )
    rows = synthetic_rows(ledger=REPAIRED)
    assert _refused(tmp_path, drop, rows, _write_ledger(tmp_path, other, drop[1])).reason == "content_key_differs"


def test_a_ledger_over_another_base_is_refused(tmp_path: Path, drop) -> None:
    rows = synthetic_rows(ledger=REPAIRED)
    foreign = dataclasses.replace(REPAIRED, base_snapshot_id="undated+0d.0123456789ab")
    assert _refused(tmp_path, drop, rows, _write_ledger(tmp_path, foreign, drop[1])).reason == "ledger_mismatch"


def test_a_ledger_recognised_from_another_crop_is_refused(tmp_path: Path, drop) -> None:
    ledger = _ledger(
        _repair(BLOCK_A, RepairOutcome.REPAIRED, replacement="1.1. Восстановленный текст.", crop=b"%PDF other crop\n"),
    )
    rows = synthetic_rows(ledger=ledger)
    assert _refused(tmp_path, drop, rows, _write_ledger(tmp_path, ledger, drop[1])).reason == "ledger_crop_differs"


def test_a_ledger_block_whose_crop_the_bundle_lacks_is_refused(tmp_path: Path, drop) -> None:
    documents = default_documents()
    documents[0] = dataclasses.replace(documents[0], crops={BLOCK_B: documents[0].crops[BLOCK_B]})
    drop = write_drop(tmp_path / "no-crop", documents)
    ledger = _ledger(_repair(BLOCK_A, RepairOutcome.UNUSABLE))
    rows = synthetic_rows(documents, ledger=ledger)
    assert _refused(tmp_path, drop, rows, _write_ledger(tmp_path, ledger, drop[1])).reason == "ledger_crop_absent"


# --- F3: the ledger names the sums it was checked against --------------------------------


def test_a_ledger_without_its_sums_digest_is_refused(tmp_path: Path, drop) -> None:
    rows = synthetic_rows(ledger=REPAIRED)
    path = _write_ledger(tmp_path, REPAIRED, None, field=False)
    assert _refused(tmp_path, drop, rows, path).reason == "ledger_sums_unrecorded"


def test_a_ledger_taken_over_other_sums_is_refused(tmp_path: Path, drop) -> None:
    rows = synthetic_rows(ledger=REPAIRED)
    other = tmp_path / "other-sums"
    other.write_bytes(drop[1].read_bytes() + b"\n")
    path = _write_ledger(tmp_path, REPAIRED, other)
    assert _refused(tmp_path, drop, rows, path).reason == "ledger_sums_differ"


@pytest.mark.parametrize(
    "damage",
    ["uppercase", "duplicate", "duplicate-after-dot-slash"],
)
def test_the_export_reads_sums_with_the_one_canonical_parser(tmp_path: Path, drop, damage: str) -> None:
    corpus, sums = drop
    lines = sums.read_text(encoding="utf-8").splitlines()
    if damage == "uppercase":
        lines[0] = lines[0][:64].upper() + lines[0][64:]
    elif damage == "duplicate":
        lines.append(lines[0])
    else:
        lines.append(lines[0].replace("  ./", "  ", 1))
    sums.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert _refused(tmp_path, (corpus, sums), synthetic_rows()).reason == "drop_sums_malformed"


# --- F2: the manifest's snapshot facts are the rows' -------------------------------------


def _forge_manifest(directory: Path, **snapshot_changes: object) -> Path:
    """Rewrite the manifest's snapshot facts and re-sign it: a self-consistent forgery."""
    manifest = parse_manifest((directory / MANIFEST_NAME).read_bytes())
    forged = dataclasses.replace(manifest, snapshot=dataclasses.replace(manifest.snapshot, **snapshot_changes))
    (directory / MANIFEST_NAME).write_bytes(forged.render())
    sums = parse_sums((directory / SUMS_NAME).read_bytes())
    sums[MANIFEST_NAME] = _sha((directory / MANIFEST_NAME).read_bytes())
    rendered = render_sums(sums)
    (directory / SUMS_NAME).write_bytes(rendered)
    return directory.rename(directory.with_name(bundle_name(directory.name.rsplit("+", 1)[0], rendered)))


@pytest.mark.parametrize(
    "changes",
    [{"content_digest": "0" * 64}, {"base_content_key": "undated+0d.0123456789ab"}],
)
def test_the_importer_refuses_manifest_snapshot_facts_the_rows_do_not_state(
    tmp_path: Path, drop, changes: dict
) -> None:
    bundle = _forge_manifest(_export(tmp_path, drop, synthetic_rows()).directory, **changes)
    record = tmp_path / "record.json"
    record.write_text(record_text(record_fields()), encoding="utf-8")
    with pytest.raises(BundleRefused) as refused:
        import_bundle(bundle, copy_record=record, stand=STAND, say=lambda _line: None)
    assert refused.value.reason == "manifest_snapshot_differs"

