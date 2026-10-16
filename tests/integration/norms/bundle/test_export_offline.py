"""`W54-BUNDLE-01`: the export writes a bundle the inbound key accepts, from the drop's bytes.

Container-free: the database half (``read_export_source``) is replaced by an
:class:`ExportSource` built here; ``test_bundle_postgres.py`` runs the whole export against a
real promotion-like database in the window.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import stat
from pathlib import Path

import pytest

from auditmanager.norms.bundle.contents import iter_build, read_rows
from auditmanager.norms.bundle.errors import BundleRefused
from auditmanager.norms.bundle.export import ExportSource, write_bundle
from auditmanager.norms.bundle.layout import MANIFEST_NAME, object_path, verify_bundle
from auditmanager.norms.bundle.manifest import BuildFacts, parse_manifest
from auditmanager.norms.custody import NORM_SOURCE, CustodySlot, binding_digest
from auditmanager.norms.embedding.digest import EMBEDDING_SET_DIGEST_VERSION
from auditmanager.norms.embedding.profile import EMBEDDING_PROFILE
from tests.integration.norms.bundle.support import (
    CHUNKING_PROFILE,
    bash_lib,
    chunks_digest,
    default_documents,
    synthetic_chunks,
    synthetic_rows,
    write_drop,
)


def _source(rows, *, with_build: bool = True) -> ExportSource:
    chunks = synthetic_chunks([document.source_document_ref for document in rows.documents])
    build = BuildFacts(
        embedding_profile=EMBEDDING_PROFILE,
        digest_version=EMBEDDING_SET_DIGEST_VERSION,
        embedding_set_sha256=chunks_digest(rows.snapshot.content_key, chunks),
        chunk_count=len(chunks),
        window_count=sum(len(chunk.windows) for chunk in chunks),
    )
    return ExportSource(
        rows=rows,
        row_digest=rows.row_digest,
        chunking_profile=CHUNKING_PROFILE,
        chunk_count=len(chunks),
        build=build if with_build else None,
        chunks=(lambda: iter(chunks)) if with_build else None,
        norm_table_bytes=4096,
    )


@pytest.fixture
def drop(tmp_path: Path) -> tuple[Path, Path]:
    return write_drop(tmp_path / "drop")


def test_the_export_is_a_bundle_both_ends_accept_with_every_slot(tmp_path: Path, drop) -> None:
    corpus, sums = drop
    rows = synthetic_rows()
    result = write_bundle(_source(rows), corpus=corpus, drop_sums=sums, ledger=None, out=tmp_path / "out")
    directory = result.directory
    assert result.created and directory.parent == tmp_path / "out"
    assert [path.name for path in (tmp_path / "out").iterdir()] == [directory.name], "work left behind"

    # Both ends' tree rule: this module's, and the shell's fc_check_bundle_tree.
    verified = verify_bundle(directory)
    ran = bash_lib('fc_check_bundle_tree "$1" "$2" && echo ok', str(directory), directory.name)
    assert ran.stdout.strip() == "ok", ran.stderr

    manifest = parse_manifest((directory / MANIFEST_NAME).read_bytes())
    manifest.check_against(verified)
    assert manifest == result.manifest
    assert manifest.content_key == rows.snapshot.content_key
    assert manifest.row_digest == rows.row_digest == read_rows(directory).row_digest
    # Two PDFs and three crops, one crop byte-identical to the second PDF: four objects,
    # five slots, one object serving two documents' anchors.
    assert (manifest.counts.objects, manifest.counts.slots) == (4, 5)
    by_document = {row.source_document_ref: row.norm_document_id for row in rows.documents}
    shared = manifest.object_for(hashlib.sha256(b"%PDF-1.7 shared bytes\n").hexdigest())
    assert shared is not None and {(slot.target_id, slot.anchor_kind) for slot in shared.slots} == {
        (by_document["doc_" + "1" * 32], "crop"),
        (by_document["doc_" + "2" * 32], "pdf"),
    }
    slots = dict(manifest.custody_manifest().entries)
    pdf = CustodySlot(NORM_SOURCE, "norm_document", by_document["doc_" + "1" * 32], "pdf", "doc_" + "1" * 32)
    assert slots[pdf].sha256 == hashlib.sha256(b"%PDF-1.7 document one\n").hexdigest()
    assert manifest.binding_digest == binding_digest(manifest.binding_entries())
    assert manifest.object_bytes == sum(entry.size for entry in manifest.files_of("object"))
    assert manifest.drop_sums_sha256 == hashlib.sha256(sums.read_bytes()).hexdigest()
    assert set(manifest.results_md_sha256) == set(by_document.values())
    assert manifest.db_growth_bytes == 4096 + 5 * 1536

    # The build reads back chunk for chunk, vectors and all.
    chunks = list(iter_build(directory, [entry.path for entry in manifest.files_of("build")]))
    assert chunks == synthetic_chunks(list(by_document))
    assert manifest.build is not None and manifest.build.embedding_set_sha256 == chunks_digest(manifest.content_key, chunks)


def test_objects_are_hardlinks_of_the_drop_made_read_only(tmp_path: Path, drop) -> None:
    corpus, sums = drop
    rows = synthetic_rows()
    result = write_bundle(_source(rows), corpus=corpus, drop_sums=sums, ledger=None, out=tmp_path / "out")
    document = default_documents()[0]
    source = corpus / document.slug / "document.pdf"
    linked = result.directory / object_path(hashlib.sha256(document.pdf).hexdigest())
    assert os.stat(source).st_ino == os.stat(linked).st_ino
    assert not os.stat(linked).st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)


def test_copy_objects_copies_instead(tmp_path: Path, drop) -> None:
    corpus, sums = drop
    result = write_bundle(
        _source(synthetic_rows()), corpus=corpus, drop_sums=sums, ledger=None, out=tmp_path / "out",
        copy_objects=True,
    )
    document = default_documents()[0]
    linked = result.directory / object_path(hashlib.sha256(document.pdf).hexdigest())
    assert os.stat(corpus / document.slug / "document.pdf").st_ino != os.stat(linked).st_ino


def test_an_equal_export_is_the_same_bundle(tmp_path: Path, drop) -> None:
    corpus, sums = drop
    source = _source(synthetic_rows())
    first = write_bundle(source, corpus=corpus, drop_sums=sums, ledger=None, out=tmp_path / "out")
    second = write_bundle(source, corpus=corpus, drop_sums=sums, ledger=None, out=tmp_path / "out")
    assert second.directory == first.directory and not second.created
    assert [path.name for path in (tmp_path / "out").iterdir()] == [first.directory.name]


def test_an_export_without_a_build_says_so_in_the_manifest(tmp_path: Path, drop) -> None:
    corpus, sums = drop
    result = write_bundle(
        _source(synthetic_rows(), with_build=False), corpus=corpus, drop_sums=sums, ledger=None,
        out=tmp_path / "out",
    )
    assert result.manifest.build is None and not result.manifest.files_of("build")
    assert parse_manifest((result.directory / MANIFEST_NAME).read_bytes()).build is None


def _rewrite_sums(sums: Path, relative: str, sha: str | None) -> None:
    lines = [line for line in sums.read_text(encoding="utf-8").splitlines() if not line.endswith(f"./{relative}")]
    if sha is not None:
        lines.append(f"{sha}  ./{relative}")
    sums.write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.mark.parametrize(
    "damage, reason",
    [
        ("pdf-differs-from-sums", "drop_file_differs"),
        ("pdf-unsummed", "drop_file_unsummed"),
        ("results-differs", "drop_file_differs"),
        ("crop-not-indexed", "drop_crops_differ"),
        ("document-absent", "drop_document_absent"),
        ("source-ref-differs", "drop_document_differs"),
    ],
)
def test_a_drop_that_is_not_its_sums_stops_the_export_and_leaves_nothing(
    tmp_path: Path, drop, damage: str, reason: str
) -> None:
    corpus, sums = drop
    document = default_documents()[0]
    rows = synthetic_rows()
    if damage == "pdf-differs-from-sums":
        (corpus / document.slug / "document.pdf").write_bytes(b"%PDF other bytes\n")
    elif damage == "pdf-unsummed":
        _rewrite_sums(sums, f"{document.slug}/document.pdf", None)
    elif damage == "results-differs":
        _rewrite_sums(sums, f"{document.slug}/results.md", "0" * 64)
    elif damage == "crop-not-indexed":
        (corpus / document.slug / "crops" / ("blk_" + "f" * 32 + ".pdf")).write_bytes(b"x")
    elif damage == "document-absent":
        rows = dataclasses.replace(
            rows, documents=tuple(dataclasses.replace(row, slug="absent") if row.slug == document.slug else row
                                  for row in rows.documents)
        )
    elif damage == "source-ref-differs":
        (corpus / document.slug / "blocks.json").write_text(json.dumps({"document_id": "doc_" + "9" * 32}))
    with pytest.raises(BundleRefused, match=reason):
        write_bundle(_source(rows), corpus=corpus, drop_sums=sums, ledger=None, out=tmp_path / "out")
    assert list((tmp_path / "out").iterdir()) == [], "a refused export left a directory"


@pytest.mark.parametrize("index_digest_updated", [False, True])
def test_export_refuses_a_crop_removed_from_index_and_drop_but_still_in_sums(
    tmp_path: Path, drop, index_digest_updated: bool
) -> None:
    corpus, sums = drop
    index_path = corpus / "crops_index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    omitted = index.pop()
    index_path.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    (corpus / omitted["slug"] / "crops" / f"{omitted['block_id']}.pdf").unlink()
    if index_digest_updated:
        _rewrite_sums(sums, "crops_index.json", hashlib.sha256(index_path.read_bytes()).hexdigest())
    assert omitted["block_id"] in sums.read_text(encoding="utf-8")

    with pytest.raises(BundleRefused) as refused:
        write_bundle(_source(synthetic_rows()), corpus=corpus, drop_sums=sums,
                     ledger=None, out=tmp_path / "out")
    assert refused.value.reason == ("drop_crops_differ" if index_digest_updated else "drop_file_differs")
    assert not (tmp_path / "out").exists(), "a rejected index created export staging"


@pytest.mark.parametrize("damage", ["modified", "unsummed"])
def test_export_refuses_unbound_index_even_when_crop_paths_still_match(
    tmp_path: Path, drop, damage: str
) -> None:
    corpus, sums = drop
    index_path = corpus / "crops_index.json"
    if damage == "modified":
        index = json.loads(index_path.read_text(encoding="utf-8"))
        index[0]["page_index"] = 99
        index_path.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    else:
        _rewrite_sums(sums, "crops_index.json", None)

    with pytest.raises(BundleRefused) as refused:
        write_bundle(_source(synthetic_rows()), corpus=corpus, drop_sums=sums,
                     ledger=None, out=tmp_path / "out")
    assert refused.value.reason == ("drop_file_differs" if damage == "modified" else "drop_file_unsummed")
    assert not (tmp_path / "out").exists(), "a rejected index created export staging"


def test_a_repaired_snapshot_without_its_ledger_is_refused(tmp_path: Path, drop) -> None:
    corpus, sums = drop
    rows = synthetic_rows()
    rows = dataclasses.replace(rows, snapshot=dataclasses.replace(rows.snapshot, repair_count=1))
    with pytest.raises(BundleRefused, match="ledger_required"):
        write_bundle(_source(rows), corpus=corpus, drop_sums=sums, ledger=None, out=tmp_path / "out")


def test_a_build_that_does_not_digest_as_recorded_is_refused(tmp_path: Path, drop) -> None:
    corpus, sums = drop
    source = _source(synthetic_rows())
    assert source.build is not None
    source = dataclasses.replace(
        source, build=dataclasses.replace(source.build, embedding_set_sha256="0" * 64)
    )
    with pytest.raises(BundleRefused, match="build_digest_unstable"):
        write_bundle(source, corpus=corpus, drop_sums=sums, ledger=None, out=tmp_path / "out")
    assert list((tmp_path / "out").iterdir()) == []
