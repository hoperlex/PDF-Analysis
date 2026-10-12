"""`W54-SNAPSHOT-01`: a snapshot's rows with their ids, their canonical digest, and the
refusals `import_snapshot` makes before it touches a database.

Container-free. Replay, conflict and the round trip through two databases are in
`tests/integration/db/test_norms_corpus_migration.py` (a heavy step for the window).
"""

from __future__ import annotations

import dataclasses
import hashlib
import random

import pytest

from auditmanager.norms import (
    ROW_DIGEST_VERSION,
    DocumentRow,
    ParagraphRow,
    RowDigest,
    SnapshotRow,
    SnapshotRows,
    row_digest,
)
from auditmanager.norms.chunking import ChunkingRefused
from auditmanager.norms.loader import import_snapshot
from auditmanager.norms.repository import SnapshotRowsInvalid, validate_snapshot_rows

SNAPSHOT_ID = "ns_" + "0" * 26
DOCUMENT_A = "ndoc_" + "1" * 26
DOCUMENT_B = "ndoc_" + "2" * 26
KEY = "2026-07-23..2026-07-23+0d+0r+1u." + "a" * 12
BASE_KEY = "2026-07-23..2026-07-23+0d." + "b" * 12


def _paragraph_id(index: int) -> str:
    return "npar_" + f"{index:026d}"


def _rows(**snapshot_changes: object) -> SnapshotRows:
    snapshot = SnapshotRow(
        norms_snapshot_id=SNAPSHOT_ID,
        content_key=KEY,
        base_content_key=BASE_KEY,
        content_digest="c" * 64,
        drawn_from="2026-07-23",
        drawn_to="2026-07-23",
        undated_documents=0,
        document_count=2,
        repair_count=0,
        unreliable_count=1,
        segmentation_profile="markdown-v1",
    )
    documents = tuple(
        DocumentRow(
            norm_document_id=identity,
            source_document_ref=f"doc_source_{index}",
            slug=f"СП_{index}",
            title=f"СП {index}.pdf",
            doc_type="СП",
            drawn_on="2026-07-23",
            source_attribution="consultant_plus",
            pdf_page_count=2,
            block_count=2,
            page_heading_count=2,
            recognised_characters=100,
            paragraph_count=2,
        )
        for index, identity in enumerate((DOCUMENT_A, DOCUMENT_B))
    )
    paragraphs = tuple(
        ParagraphRow(
            norm_paragraph_id=_paragraph_id(2 * d + o),
            norm_document_id=document,
            ordinal=o,
            page_label=o + 1,
            block_ref=f"blk_{d}{o}",
            char_offset=50 * o,
            char_length=len(text),
            kind="body",
            clause_number=f"{o + 1}.1" if o == 0 else None,
            text=text,
            text_reliability="unreliable" if (d, o) == (1, 1) else "reliable",
        )
        for d, document in enumerate((DOCUMENT_A, DOCUMENT_B))
        for o, text in enumerate(("1.1. Пункт «первый».", "Второй абзац"))
    )
    return SnapshotRows(
        snapshot=dataclasses.replace(snapshot, **snapshot_changes),
        documents=documents,
        paragraphs=paragraphs,
    )


# --- the digest ------------------------------------------------------------------------------


def test_the_row_digest_is_the_documented_canonical_serialisation() -> None:
    """Written out by hand, so a change to the form is a deliberate change to this test."""
    lines = [
        f"{ROW_DIGEST_VERSION}\n",
        'S["ns_00000000000000000000000000","2026-07-23..2026-07-23+0d+0r+1u.aaaaaaaaaaaa",'
        '"2026-07-23..2026-07-23+0d.bbbbbbbbbbbb","' + "c" * 64 + '","2026-07-23","2026-07-23",'
        '0,2,0,1,"markdown-v1"]\n',
    ]
    for index, identity in enumerate((DOCUMENT_A, DOCUMENT_B)):
        lines.append(
            f'D["{identity}","doc_source_{index}","СП_{index}","СП {index}.pdf","СП",'
            '"2026-07-23","consultant_plus",2,2,2,100,2]\n'
        )
    for d, identity in enumerate((DOCUMENT_A, DOCUMENT_B)):
        lines.append(
            f'P["{_paragraph_id(2 * d)}","{identity}",0,1,"blk_{d}0",0,20,"body","1.1",'
            '"1.1. Пункт «первый».","reliable"]\n'
        )
        reliability = "unreliable" if d == 1 else "reliable"
        lines.append(
            f'P["{_paragraph_id(2 * d + 1)}","{identity}",1,2,"blk_{d}1",50,12,"body",null,'
            f'"Второй абзац","{reliability}"]\n'
        )
    expected = hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()
    assert row_digest(_rows()) == expected
    assert _rows().row_digest == expected


def test_the_row_digest_does_not_depend_on_row_order() -> None:
    rows = _rows()
    shuffled = list(rows.paragraphs)
    random.Random(7).shuffle(shuffled)
    reordered = SnapshotRows(rows.snapshot, tuple(reversed(rows.documents)), tuple(shuffled))
    assert row_digest(reordered) == row_digest(rows)


@pytest.mark.parametrize(
    "change",
    [
        lambda rows: dataclasses.replace(rows, snapshot=dataclasses.replace(rows.snapshot, unreliable_count=2)),
        lambda rows: dataclasses.replace(
            rows, documents=(dataclasses.replace(rows.documents[0], title="другое"),) + rows.documents[1:]
        ),
        lambda rows: dataclasses.replace(
            rows, paragraphs=(dataclasses.replace(rows.paragraphs[0], text="1.1. Пункт «второй»."),) + rows.paragraphs[1:]
        ),
        lambda rows: dataclasses.replace(
            rows, paragraphs=(dataclasses.replace(rows.paragraphs[0], text_reliability="unreliable"),) + rows.paragraphs[1:]
        ),
        lambda rows: dataclasses.replace(
            rows, paragraphs=(dataclasses.replace(rows.paragraphs[0], norm_paragraph_id=_paragraph_id(99)),) + rows.paragraphs[1:]
        ),
        lambda rows: dataclasses.replace(rows, snapshot=dataclasses.replace(rows.snapshot, norms_snapshot_id="ns_" + "1" * 26)),
    ],
    ids=["count", "document", "text", "reliability", "paragraph-id", "snapshot-id"],
)
def test_every_id_text_and_reliability_moves_the_digest(change) -> None:
    rows = _rows()
    assert row_digest(change(rows)) != row_digest(rows)


def test_the_incremental_digest_refuses_rows_out_of_canonical_order() -> None:
    rows = _rows()
    digest = RowDigest()
    with pytest.raises(ValueError, match="needs the snapshot row"):
        digest.hexdigest()
    with pytest.raises(ValueError, match="follow the snapshot row"):
        digest.document(rows.documents[0])
    digest.snapshot(rows.snapshot)
    with pytest.raises(ValueError, match="exactly one snapshot row"):
        digest.snapshot(rows.snapshot)
    digest.document(rows.documents[1])
    with pytest.raises(ValueError, match="out of canonical order"):
        digest.document(rows.documents[0])
    with pytest.raises(ValueError, match="out of canonical order"):
        digest.document(rows.documents[1])  # a duplicate is out of order too
    digest.paragraph(rows.paragraphs[1])
    with pytest.raises(ValueError, match="out of canonical order"):
        digest.paragraph(rows.paragraphs[0])
    with pytest.raises(ValueError, match="precede every paragraph"):
        digest.document(rows.documents[0])


# --- validation ------------------------------------------------------------------------------


def test_well_formed_rows_validate() -> None:
    validate_snapshot_rows(_rows())


def _without(rows: SnapshotRows, index: int) -> SnapshotRows:
    return dataclasses.replace(rows, paragraphs=rows.paragraphs[:index] + rows.paragraphs[index + 1 :])


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda r: dataclasses.replace(r, snapshot=dataclasses.replace(r.snapshot, norms_snapshot_id=KEY)), "contract pattern"),
        (lambda r: dataclasses.replace(r, documents=(dataclasses.replace(r.documents[0], norm_document_id="СП_0"),) + r.documents[1:]), "contract pattern"),
        (lambda r: dataclasses.replace(r, paragraphs=(dataclasses.replace(r.paragraphs[0], norm_paragraph_id="blk_00"),) + r.paragraphs[1:]), "contract pattern"),
        (lambda r: dataclasses.replace(r, snapshot=dataclasses.replace(r.snapshot, document_count=3)), "claims 3 documents"),
        (lambda r: dataclasses.replace(r, documents=(r.documents[0], dataclasses.replace(r.documents[1], slug="СП_0"))), "share one slug"),
        (lambda r: dataclasses.replace(r, documents=(r.documents[0], dataclasses.replace(r.documents[1], norm_document_id=DOCUMENT_A))), "share one norm_document_id"),
        (lambda r: dataclasses.replace(r, paragraphs=(dataclasses.replace(r.paragraphs[0], norm_paragraph_id=_paragraph_id(1)),) + r.paragraphs[1:]), "share one norm_paragraph_id"),
        (lambda r: _without(r, 0), "ordinals are not 0..1"),
        (lambda r: dataclasses.replace(r, paragraphs=(dataclasses.replace(r.paragraphs[0], norm_document_id="ndoc_" + "3" * 26),) + r.paragraphs[1:]), "absent document"),
        (lambda r: dataclasses.replace(r, paragraphs=(dataclasses.replace(r.paragraphs[0], text_reliability="maybe"),) + r.paragraphs[1:]), "text_reliability"),
        (lambda r: dataclasses.replace(r, paragraphs=(dataclasses.replace(r.paragraphs[0], kind="list"),) + r.paragraphs[1:]), "kind"),
        (lambda r: dataclasses.replace(r, snapshot=dataclasses.replace(r.snapshot, unreliable_count=0)), "unreliable_count = 0"),
        (lambda r: dataclasses.replace(r, snapshot=dataclasses.replace(r.snapshot, segmentation_profile="markdown-v2")), "D-126"),
        (lambda r: dataclasses.replace(r, snapshot=dataclasses.replace(r.snapshot, content_key=KEY + "+seg-markdown-v2")), "names a profile"),
    ],
)
def test_malformed_rows_are_refused_before_anything_is_written(change, message: str) -> None:
    with pytest.raises(SnapshotRowsInvalid, match=message):
        validate_snapshot_rows(change(_rows()))


def test_a_qualified_snapshot_validates_when_both_keys_carry_its_profile() -> None:
    validate_snapshot_rows(
        _rows(
            segmentation_profile="markdown-v2",
            content_key=KEY + "+seg-markdown-v2",
            base_content_key=BASE_KEY + "+seg-markdown-v2",
        )
    )
    with pytest.raises(SnapshotRowsInvalid, match="base_content_key"):
        validate_snapshot_rows(
            _rows(segmentation_profile="markdown-v2", content_key=KEY + "+seg-markdown-v2")
        )


# --- import refusals that precede the database -----------------------------------------------


class _NoDatabase:
    """A session that fails the test if `import_snapshot` reaches it."""

    def __getattr__(self, name: str):
        raise AssertionError(f"import_snapshot touched the session ({name}) before refusing")


def test_import_refuses_a_digest_other_than_the_manifests_before_touching_the_session() -> None:
    with pytest.raises(SnapshotRowsInvalid, match="does not equal the expected"):
        import_snapshot(
            _NoDatabase(), _rows(), chunking_profiles=["characters-v2:1200"],
            expected_row_digest="0" * 64,
        )


def test_import_refuses_characters_v1_over_unreliable_rows_before_touching_the_session() -> None:
    with pytest.raises(ChunkingRefused, match="1 unreliable block"):
        import_snapshot(_NoDatabase(), _rows(), chunking_profiles=["characters-v1:1200"])


@pytest.mark.parametrize(
    "profiles",
    [[], ["characters-v2:1200", "characters-v2:1200"], ["characters-v3:1200"], ["characters-v2"]],
)
def test_import_refuses_a_malformed_profile_list_before_touching_the_session(profiles) -> None:
    with pytest.raises(SnapshotRowsInvalid):
        import_snapshot(_NoDatabase(), _rows(), chunking_profiles=profiles)


def test_import_validates_the_rows_before_touching_the_session() -> None:
    with pytest.raises(SnapshotRowsInvalid, match="unreliable_count = 0"):
        import_snapshot(
            _NoDatabase(), _rows(unreliable_count=0), chunking_profiles=["characters-v2:1200"]
        )
