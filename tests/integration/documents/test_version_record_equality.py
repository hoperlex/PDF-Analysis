"""`CLASSIFICATION-CORRECTION-01` phase A: a classification is not part of a version's identity.

No database. The run input readers (``runs/*_input.py``) read a version, read its bytes from
the store, then read the version again and refuse ``version_changed_during_*_read`` when
``second != first``. Every field of ``DocumentVersionRecord`` is immutable except the
classification an expert may now correct, so the comparison must not see it: a correction
committed inside that window would otherwise fail a run that is pinned to the profile it
started with. Every other field still counts.
"""

from __future__ import annotations

from dataclasses import fields, replace
from datetime import datetime, timezone

from auditmanager.documents.models import DocumentVersionRecord, VersionClassificationRecord
from auditmanager.shared.identity import DocumentUid, ProjectUid, VersionUid

PUBLISHED = datetime(2026, 10, 20, 9, 0, tzinfo=timezone.utc)
EXPERT = "usr_01M25P3TH08VVTTGJRXYBZZ7RP"


def _version() -> DocumentVersionRecord:
    return DocumentVersionRecord(
        version_uid=VersionUid.new(),
        document_uid=DocumentUid.new(),
        project_uid=ProjectUid.new(),
        version_ordinal=1,
        display_title="План",
        section=None,
        media_type="application/pdf",
        byte_size=10,
        sha256="0" * 64,
        page_count=1,
        published_at=PUBLISHED,
        manifest=(),
    )


def _classified(version: DocumentVersionRecord, stage: str, section: str) -> DocumentVersionRecord:
    return replace(
        version,
        classification=VersionClassificationRecord(
            version_uid=version.version_uid,
            project_stage=stage,
            section_code=section,
            confirmed_by_user_uid=EXPERT,
            confirmed_at=PUBLISHED,
        ),
    )


def test_a_corrected_classification_does_not_make_the_version_a_different_one() -> None:
    bare = _version()
    first = _classified(bare, "P", "AR")
    corrected = _classified(bare, "R", "KJ")
    assert first == corrected == bare
    assert hash(first) == hash(corrected) == hash(bare)


def test_the_classification_is_still_carried_and_readable() -> None:
    corrected = _classified(_version(), "R", "KJ")
    assert corrected.classification is not None
    assert (corrected.classification.project_stage, corrected.classification.section_code) == ("R", "KJ")


def test_every_other_field_still_counts_toward_equality() -> None:
    base = _version()
    changed = {
        "version_ordinal": 2,
        "display_title": "Другое",
        "section": "AR",
        "media_type": "application/zip",
        "byte_size": 11,
        "sha256": "1" * 64,
        "page_count": 2,
        "published_at": datetime(2026, 10, 21, tzinfo=timezone.utc),
        "version_uid": VersionUid.new(),
        "document_uid": DocumentUid.new(),
        "project_uid": ProjectUid.new(),
        "text_character_count": 5,
        "textless_pages": (1,),
        "recognised_character_count": 3,
        "upload_kind": "comparison_pdf",
    }
    compared = {item.name for item in fields(DocumentVersionRecord) if item.compare}
    assert compared == set(changed) | {"manifest"}, "a new field must be judged here"
    for name, value in changed.items():
        assert replace(base, **{name: value}) != base, name
