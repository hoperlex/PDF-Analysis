"""`NORM-REFS-RUN-01` against real PostgreSQL: a stored Run's cited norms, with the real rows.

HEAVY by the repository's classification: it needs the lane's PostgreSQL and MinIO (the
harness's ``seeded`` version puts its PDF in the bucket). Everything runs in the harness's
rolled-back transaction, and the rows below are written by plain SQL or the owning
repositories, never by the code under test.

What the container-free suite (``test_reference_norm_references.py``) cannot prove and this
does: the Run row and its Version are the real ones (the page count comes from the stored
version, the pin from ``audit_run.norms_snapshot_id``), the snapshot is read from the real
``norm_document`` rows with their database-generated designation tokens, and the whole read
writes nothing. The saved text is a stand-in reader here; the production reader
(``_AnalysisReader``) is the comparison's own and is exercised by that suite.
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import text

from auditmanager.documents.public import DocumentRepository
from auditmanager.runs.public import (
    NORM_REFERENCES_READY,
    NORM_REFERENCES_SNAPSHOT_NOT_PINNED,
    NORM_REFERENCES_TEXT_UNAVAILABLE,
    SavedRunPageText,
    read_run_norm_references,
)
from auditmanager.runs.repository import RunRepository
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import NormDocumentId, NormsSnapshotId, RunId, VersionUid

SP_2022 = "СП_54_13330_2022__Свод_правил__Здания_жилые_многоквартирные"
SP_2024 = "СП_54_13330_2024__Свод_правил__Здания_жилые_многоквартирные"
GOST = "ГОСТ_21_101-2020__Система_проектной_документации"
MDS = "МДС_12-24_2006__Устройство_обычных"
SHA = "d" * 64


class _Text:
    """Answers the Run's saved text from a dict; records what it was asked."""

    def __init__(self, answer: dict[int, str] | None) -> None:
        self.answer = answer
        self.asked: list[dict[str, Any]] = []

    def saved_page_text(self, session: Any, *, run_id: str, version_uid: str, page_count: int):
        self.asked.append({"run_id": run_id, "version_uid": version_uid, "page_count": page_count})
        if self.answer is None:
            return None
        pages = {number: self.answer.get(number, "") for number in range(1, page_count + 1)}
        return SavedRunPageText(run_id, SHA, pages)


def _snapshot(session: Any, slugs: tuple[str, ...], *, declared: int | None = None) -> tuple[str, dict[str, str]]:
    snapshot = str(NormsSnapshotId.new())
    tail = snapshot[-12:].lower()
    count = len(slugs) if declared is None else declared
    session.execute(text(
        "INSERT INTO norms_snapshot (norms_snapshot_id, content_key, base_content_key, "
        "content_digest, undated_documents, document_count, repair_count, unreliable_count, "
        "segmentation_profile) VALUES (:s, :k, :k, :d, 0, :n, 0, 0, 'markdown-v1')"
    ), {"s": snapshot, "k": f"norm-refs-{tail}", "d": "e" * 64, "n": count})
    ids: dict[str, str] = {}
    for slug in slugs:
        ids[slug] = str(NormDocumentId.new())
        session.execute(text(
            "INSERT INTO norm_document (norm_document_id, norms_snapshot_id, source_document_ref, "
            "slug, title, doc_type, source_attribution, pdf_page_count, block_count, "
            "page_heading_count, recognised_characters, paragraph_count) "
            "VALUES (:d, :s, :ref, :slug, :title, :doc_type, 'consultant_plus', 50, 1, 0, 10, 0)"
        ), {
            "d": ids[slug], "s": snapshot, "ref": f"ref-{ids[slug][-8:]}", "slug": slug,
            "title": slug.split("__", 1)[-1].replace("_", " ") or slug, "doc_type": slug.split("_", 1)[0],
        })
    return snapshot, ids


def _run(session: Any, seeded: Any, *, snapshot: str | None) -> str:
    run_id = str(RunId.new())
    RunRepository().create(
        session, run_id=run_id, project_uid=seeded.project_uid, version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id, prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded", frozen_input_digest="a" * 64, command_id=None,
        norms_snapshot_id=snapshot,
    )
    return run_id


def _count(session: Any, table: str) -> int:
    return session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()


def test_a_stored_run_lists_the_norms_its_text_cites_against_its_own_snapshot(session, seeded) -> None:
    snapshot, ids = _snapshot(session, (SP_2022, SP_2024, GOST, MDS))
    run_id = _run(session, seeded, snapshot=snapshot)
    reader = _Text({1: "По СП 54.13330.2022 и ГОСТ 21.101-2021; ГОСТ Р 99999-2020; СП 54.13330."})
    page_count = DocumentRepository().get_version(session, VersionUid.parse(seeded.version_uid)).page_count
    before = (_count(session, "audit_run"), _count(session, "norm_document"), _count(session, "norms_snapshot"))

    answer = read_run_norm_references(session, run_id=run_id, reader=reader)

    assert (answer.state, answer.run_id, answer.version_uid) == (NORM_REFERENCES_READY, run_id, seeded.version_uid)
    assert (answer.page_count, answer.norms_snapshot_id, answer.text_layer_sha256) == (page_count, snapshot, SHA)
    assert reader.asked == [{"run_id": run_id, "version_uid": seeded.version_uid, "page_count": page_count}]
    model = answer.references
    assert model is not None
    assert [(i.cited, i.outcome) for i in model.items] == [
        ("СП 54.13330.2022", "newer_edition"),
        ("ГОСТ 21.101-2021", "older_edition_only"),
        ("ГОСТ Р 99999-2020", "not_in_corpus"),
        ("СП 54.13330", "not_recognised"),
    ]
    assert model.items[0].matched_document_id == ids[SP_2024]
    assert model.items[0].matched_designation == "СП 54.13330.2024"
    assert model.items[1].matched_document_id == ids[GOST]
    assert model.snapshot_document_count == 4
    assert [u.document_id for u in model.unrecognised] == [ids[MDS]]
    assert (model.page_count, model.unread_pages == tuple(range(2, page_count + 1))) == (page_count, True)
    assert before == (_count(session, "audit_run"), _count(session, "norm_document"), _count(session, "norms_snapshot"))


def test_the_runs_own_snapshot_decides_not_another_that_holds_the_cited_edition(session, seeded) -> None:
    """Two snapshots hold different editions; each run is answered from its own."""
    older, _ = _snapshot(session, (SP_2022,))
    newer, _ = _snapshot(session, (SP_2022, SP_2024))
    cites = _Text({1: "СП 54.13330.2022"})

    on_older = read_run_norm_references(session, run_id=_run(session, seeded, snapshot=older), reader=cites)
    on_newer = read_run_norm_references(session, run_id=_run(session, seeded, snapshot=newer), reader=cites)

    assert [i.outcome for i in on_older.references.items] == ["in_corpus"]
    assert [i.outcome for i in on_newer.references.items] == ["newer_edition"]


def test_a_run_that_pinned_no_snapshot_says_so_without_reading_its_text(session, seeded) -> None:
    reader = _Text({1: "СП 54.13330.2022"})

    answer = read_run_norm_references(session, run_id=_run(session, seeded, snapshot=None), reader=reader)

    assert (answer.state, answer.norms_snapshot_id, answer.references) == (
        NORM_REFERENCES_SNAPSHOT_NOT_PINNED, None, None,
    )
    assert reader.asked == []


def test_a_run_with_no_saved_text_says_so(session, seeded) -> None:
    snapshot, _ = _snapshot(session, (SP_2022,))

    answer = read_run_norm_references(session, run_id=_run(session, seeded, snapshot=snapshot), reader=_Text(None))

    assert (answer.state, answer.norms_snapshot_id, answer.references) == (
        NORM_REFERENCES_TEXT_UNAVAILABLE, snapshot, None,
    )


def test_an_unknown_run_is_not_found(session) -> None:
    with pytest.raises(DomainError) as refused:
        read_run_norm_references(session, run_id=str(RunId.new()), reader=_Text({1: "x"}))
    assert refused.value.code is ErrorCode.NOT_FOUND
    assert refused.value.detail_fields == {"aggregate_type": "AuditRun"}


@pytest.mark.parametrize("declared", [1, 3])
def test_a_snapshot_whose_rows_differ_from_its_declared_count_is_an_internal_error(session, seeded, declared) -> None:
    snapshot, _ = _snapshot(session, (SP_2022, SP_2024), declared=declared)

    with pytest.raises(DomainError) as refused:
        read_run_norm_references(
            session, run_id=_run(session, seeded, snapshot=snapshot), reader=_Text({1: "СП 54.13330.2022"}),
        )

    assert refused.value.code is ErrorCode.INTERNAL_ERROR
