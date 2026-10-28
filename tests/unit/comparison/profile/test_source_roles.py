"""Which manifest entry is the bytes of a version (`CMP-C1-FIX-C` item 1). Container-free.

``load_source_version`` is what the page-profile builder, the engine and the tile reader read a version through. A portal
version binds its PDF as ``source.document``; a plain PDF admitted for comparison (`CMP-INGEST-01`) binds it as
``comparison.source_pdf``, deliberately another role so that a run refuses it. Until this lane the reader took only the first,
so a version admitted by the product's own upload could not be profiled (`MEASURE-ENGINE-01.md` section 2). The roles are the
``documents.public`` names; the spelling is held here too, because a renamed role would silently turn this back into the
defect.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.comparison.profile.source import REASON_AMBIGUOUS, REASON_UNREADABLE, load_source_version
from auditmanager.documents.public import MANIFEST_ROLE_COMPARISON_PDF, MANIFEST_ROLE_SOURCE_DOCUMENT
from auditmanager.shared.errors import DomainError, ErrorCode

VERSION = "ver_01ARZ3NDEKTSV4RRFFQ69G5FAV"
PROJECT = "prj_01ARZ3NDEKTSV4RRFFQ69G5FAV"


def entry(role: str, *, blob: str, media_type: str = "application/pdf", size: int = 100) -> Any:
    return SimpleNamespace(role=role, blob_id=blob, sha256=blob[-1] * 64, size_bytes=size, media_type=media_type)


@pytest.fixture
def manifest(monkeypatch: pytest.MonkeyPatch):
    """Serve the manifest a test names as the version's, through the one repository the reader calls."""

    def serve(*entries: Any) -> None:
        record = SimpleNamespace(version_uid=VERSION, project_uid=PROJECT, page_count=7, manifest=tuple(entries))

        class Repository:
            def get_version(self, session: Any, version_uid: Any) -> Any:
                assert str(version_uid) == VERSION
                return record

        monkeypatch.setattr("auditmanager.documents.public.DocumentRepository", Repository)

    return serve


def test_the_two_roles_are_the_documents_public_names_with_their_published_spelling() -> None:
    assert MANIFEST_ROLE_SOURCE_DOCUMENT == "source.document"
    assert MANIFEST_ROLE_COMPARISON_PDF == "comparison.source_pdf"


def test_a_portal_version_is_read_through_its_source_document(manifest) -> None:
    manifest(entry(MANIFEST_ROLE_SOURCE_DOCUMENT, blob="blob_a"), entry("source.markdown", blob="blob_b", media_type="text/markdown"))
    found = load_source_version(object(), VERSION)  # type: ignore[arg-type]
    assert (found.blob_id, found.page_count, found.project_uid, found.size_bytes) == ("blob_a", 7, PROJECT, 100)
    assert found.sha256 == "a" * 64


def test_a_comparison_version_is_read_through_its_comparison_pdf(manifest) -> None:
    manifest(entry(MANIFEST_ROLE_COMPARISON_PDF, blob="blob_c", size=4096))
    found = load_source_version(object(), VERSION)  # type: ignore[arg-type]
    assert (found.blob_id, found.size_bytes, found.version_uid) == ("blob_c", 4096, VERSION)
    assert found.sha256 == "c" * 64


@pytest.mark.parametrize(
    "entries",
    [
        (),
        (SimpleNamespace(role="source.markdown", blob_id="blob_m", sha256="m" * 64, size_bytes=1, media_type="text/markdown"),),
        # a PDF under a role that is not one of the two is not the version's bytes
        (SimpleNamespace(role="source.structured_companion", blob_id="blob_s", sha256="s" * 64, size_bytes=1, media_type="application/pdf"),),
        # the right role under another media type is not a PDF the children can open
        (SimpleNamespace(role=MANIFEST_ROLE_COMPARISON_PDF, blob_id="blob_t", sha256="t" * 64, size_bytes=1, media_type="text/plain"),),
        (SimpleNamespace(role=MANIFEST_ROLE_SOURCE_DOCUMENT, blob_id="blob_t", sha256="t" * 64, size_bytes=1, media_type="image/png"),),
    ],
)
def test_a_manifest_without_a_readable_source_is_refused_as_unreadable(manifest, entries) -> None:
    manifest(*entries)
    with pytest.raises(DomainError) as refusal:
        load_source_version(object(), VERSION)  # type: ignore[arg-type]
    assert refusal.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert refusal.value.detail_fields["reason"] == REASON_UNREADABLE == "source_unreadable"


def test_a_manifest_that_holds_both_roles_is_refused_as_ambiguous_whichever_comes_first(manifest) -> None:
    both = (entry(MANIFEST_ROLE_SOURCE_DOCUMENT, blob="blob_a"), entry(MANIFEST_ROLE_COMPARISON_PDF, blob="blob_c"))
    for order in (both, tuple(reversed(both))):
        manifest(*order)
        with pytest.raises(DomainError) as refusal:
            load_source_version(object(), VERSION)  # type: ignore[arg-type]
        assert refusal.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
        assert refusal.value.detail_fields["reason"] == REASON_AMBIGUOUS == "source_manifest_ambiguous"

