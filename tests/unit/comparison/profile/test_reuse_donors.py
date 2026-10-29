"""Which versions may hand their stored page profiles to another (`CMP-C1-FIX-C` item 3). Container-free.

The database side (the rows copied, the children not started) is `tests/integration/comparison/profile_queue/
test_identical_versions_reuse_profiles.py`; this holds the rule that picks the donors, which is what keeps a profile of
another project, or of other bytes, from ever being taken.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.comparison.profile import reuse
from auditmanager.comparison.profile.source import SourceVersion
from auditmanager.documents.public import MANIFEST_ROLE_COMPARISON_PDF, MANIFEST_ROLE_SOURCE_DOCUMENT

PROJECT = "prj_01ARZ3NDEKTSV4RRFFQ69G5FAV"
ME = "ver_01ARZ3NDEKTSV4RRFFQ69G5FA0"
SHA = "a" * 64
SOURCE = SourceVersion(version_uid=ME, project_uid=PROJECT, page_count=6, sha256=SHA, size_bytes=1000, blob_id="blob_x")


def version(uid: str, *, project: str = PROJECT, pages: int = 6, entries: tuple[tuple[str, str, int], ...] | None = None) -> Any:
    entries = entries if entries is not None else ((MANIFEST_ROLE_COMPARISON_PDF, SHA, 1000),)
    manifest = tuple(
        SimpleNamespace(role=role, sha256=sha, size_bytes=size, blob_id="blob_x", media_type="application/pdf")
        for role, sha, size in entries
    )
    return SimpleNamespace(version_uid=uid, project_uid=project, page_count=pages, manifest=manifest)


@pytest.fixture
def donors(monkeypatch: pytest.MonkeyPatch):
    def pick(referencing: list[tuple[str, str]], records: dict[str, Any]) -> list[str]:
        class Repository:
            def versions_referencing(self, session: Any, blob_id: Any) -> Any:
                return tuple(referencing)

            def get_version(self, session: Any, uid: Any) -> Any:
                return records[str(uid)]

        monkeypatch.setattr("auditmanager.documents.public.DocumentRepository", Repository)
        monkeypatch.setattr("auditmanager.storage.public.parse_blob_id", lambda value: value)
        return list(reuse._donors(object(), SOURCE))  # type: ignore[arg-type]

    return pick


def uid(n: int) -> str:
    return f"ver_01ARZ3NDEKTSV4RRFFQ69G5F{n:02d}"


def test_a_version_of_the_same_project_bytes_and_pages_is_a_donor_in_a_fixed_order(donors) -> None:
    a, b = uid(11), uid(12)
    found = donors(
        [(b, MANIFEST_ROLE_COMPARISON_PDF), (a, MANIFEST_ROLE_SOURCE_DOCUMENT)],
        {a: version(a, entries=((MANIFEST_ROLE_SOURCE_DOCUMENT, SHA, 1000),)), b: version(b)},
    )
    assert found == [a, b], "either role counts, and the order does not depend on the order the database answered"


@pytest.mark.parametrize(
    "case, record",
    [
        ("another project", version(uid(21), project="prj_01ARZ3NDEKTSV4RRFFQ69G5FA1")),
        ("another page count", version(uid(21), pages=7)),
        ("another digest", version(uid(21), entries=((MANIFEST_ROLE_COMPARISON_PDF, "b" * 64, 1000),))),
        ("another size", version(uid(21), entries=((MANIFEST_ROLE_COMPARISON_PDF, SHA, 999),))),
        (
            "a manifest with two sources",
            version(uid(21), entries=((MANIFEST_ROLE_COMPARISON_PDF, SHA, 1000), (MANIFEST_ROLE_SOURCE_DOCUMENT, SHA, 1000))),
        ),
    ],
)
def test_a_version_that_differs_in_any_of_these_is_never_a_donor(donors, case: str, record: Any) -> None:
    assert donors([(uid(21), MANIFEST_ROLE_COMPARISON_PDF)], {uid(21): record}) == [], case


def test_neither_the_version_itself_nor_a_version_that_merely_holds_the_blob_under_another_role_is_a_donor(donors) -> None:
    other = uid(31)
    assert donors(
        [(ME, MANIFEST_ROLE_COMPARISON_PDF), (other, "source.markdown")],
        {ME: version(ME), other: version(other)},
    ) == []
