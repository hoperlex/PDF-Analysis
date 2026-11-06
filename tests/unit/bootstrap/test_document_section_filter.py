"""`UI-PARITY-P0E` (contract 1.20.0, ruling `R-151l`): ``listDocuments`` keeps one section's documents.

The shipped ``DocumentAdapter`` is driven with a stand-in ingest service, so the predicate under test is
the adapter's own: the **confirmed classification of the current version** decides. The legacy
``section`` column never does, an unclassified version never matches, and the order is the
service's order with rows removed (the router pages it and never re-sorts).
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from auditmanager.bootstrap.adapters import DocumentAdapter

PROJECT = "prj_01M5B0000000000000000000P1"
USER = "usr_01M5B0000000000000000000X1"
WHEN = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)


def _record(n: int, *, classified: str | None, legacy: str | None = None) -> SimpleNamespace:
    version_uid = f"ver_01M5B0000000000000000000V{n}"
    classification = None
    if classified is not None:
        classification = SimpleNamespace(
            version_uid=version_uid, project_stage="P", section_code=classified,
            confirmed_by_user_uid=USER, confirmed_at=WHEN, revision=1,
        )
    return SimpleNamespace(
        version_uid=version_uid, document_uid=f"doc_01M5B0000000000000000000D{n}", project_uid=PROJECT,
        version_ordinal=1, byte_size=100, sha256="0" * 64, page_count=1, published_at=WHEN,
        media_type="application/pdf", display_title=f"Документ {n}", section=legacy,
        classification=classification, upload_kind="portal_bundle", manifest=(),
    )


class _Service:
    def __init__(self, records: list[Any]) -> None:
        self.records = records

    def list_documents(self, project_uid: Any) -> list[Any]:
        assert str(project_uid) == PROJECT
        return self.records


RECORDS = [
    _record(1, classified="AR"),
    _record(2, classified=None, legacy="AR"),
    _record(3, classified="KJ", legacy="AR"),
    _record(4, classified="AR"),
]


def _titles(views: Any) -> list[str]:
    return [view.display_title for view in views]


def test_without_a_section_every_document_is_listed_in_the_service_order() -> None:
    views = DocumentAdapter(_Service(RECORDS)).list_documents(project_uid=PROJECT)
    assert _titles(views) == ["Документ 1", "Документ 2", "Документ 3", "Документ 4"]


def test_a_section_keeps_the_confirmed_documents_in_order() -> None:
    views = DocumentAdapter(_Service(RECORDS)).list_documents(project_uid=PROJECT, section_code="AR")
    assert _titles(views) == ["Документ 1", "Документ 4"]


def test_the_legacy_section_and_an_unclassified_version_never_match() -> None:
    adapter = DocumentAdapter(_Service(RECORDS))
    assert "Документ 2" not in _titles(adapter.list_documents(project_uid=PROJECT, section_code="AR"))
    assert _titles(adapter.list_documents(project_uid=PROJECT, section_code="KJ")) == ["Документ 3"]


def test_a_section_with_no_document_is_an_empty_listing() -> None:
    views = DocumentAdapter(_Service(RECORDS)).list_documents(project_uid=PROJECT, section_code="OV")
    assert tuple(views) == ()
