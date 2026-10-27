"""The value types ingest returns. Opaque identity plus recorded facts, nothing else.

``docs/program/P02_SEAMS.md`` section 2.2 lists what is never an identity, and the
``P2-META-01`` integration contract fixes what a consumer receives: "the version
identity plus a manifest of role, blob identity, checksum, size and media type. Bucket
and object key never appear in a return value, log or error."

That is enforced here by omission rather than by redaction. These dataclasses have no
field for a bucket, an object key, a URL, a filesystem path, an uploaded file name or a
display ordinal, so there is nothing for a caller to read and nothing for a formatter to
leak. The columns that hold those values -- ``document_version.source_filename`` and
``document_version.version_ordinal`` -- are written by the repository and are simply not
projected onto any of these types.

``sha256`` *is* present, and deliberately: the contract names a checksum among the facts
a consumer receives. A checksum is a verification value, never an identity, and nothing
in the schema references one with a foreign key.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Final

import json
from pathlib import Path

from auditmanager.shared.identity import DocumentUid, ProjectUid, VersionUid
from auditmanager.storage.public import BlobId

__all__ = [
    "MANIFEST_ROLE_COMPARISON_PDF",
    "MANIFEST_ROLE_MARKDOWN",
    "MANIFEST_ROLE_SOURCE_DOCUMENT",
    "MANIFEST_ROLE_STAMP_AUDIT",
    "MANIFEST_ROLE_STRUCTURED_COMPANION",
    "ROLE_COMPARISON_PDF",
    "ROLE_SOURCE_DOCUMENT",
    "ROLE_SOURCE_MARKDOWN",
    "ROLE_SOURCE_STAMP_AUDIT",
    "ROLE_SOURCE_STRUCTURED_COMPANION",
    "CurrentVersionPlacementRecord",
    "DocumentVersionRecord",
    "ManifestEntry",
    "ProjectListingRecord",
    "ProjectRecord",
    "UPLOAD_KIND_COMPARISON_PDF",
    "UPLOAD_KIND_PORTAL_BUNDLE",
    "UploadOutcome",
    "VersionClassificationRecord",
]

#: The blob role, in ``auditmanager.storage``'s namespace. Validated by
#: ``parse_blob_role`` and written on the object, not on the manifest entry.
ROLE_SOURCE_DOCUMENT: Final[str] = "source_document"
#: The blob roles of the other stored members of a portal bundle (`W55B-INGEST-01`). Each is a
#: first publisher's historical metadata on the object (``R-76``); the manifest entry below is
#: what binds the bytes to a version, under the registry's own role name.
ROLE_SOURCE_STRUCTURED_COMPANION: Final[str] = "source_structured_companion"
ROLE_SOURCE_MARKDOWN: Final[str] = "source_markdown"
ROLE_SOURCE_STAMP_AUDIT: Final[str] = "source_stamp_audit"


#: `CMP-INGEST-01` (ADR-0025 decision 11). How a version reached the product: ``document_version.upload_kind``
#: (migration ``0038``). Every version before it is a portal bundle; a plain PDF admitted for comparison is
#: ``comparison_pdf``.
UPLOAD_KIND_PORTAL_BUNDLE: Final[str] = "portal_bundle"
UPLOAD_KIND_COMPARISON_PDF: Final[str] = "comparison_pdf"
#: The blob role of a plain PDF admitted for comparison, and the manifest-entry role that binds it to its
#: version. **Deliberately not** ``source.document``: the existing start-run check requires that entry, so a
#: comparison-only version is refused by the very rule that refuses a version with no source (ADR-0025
#: decision 11), and no section analysis can read it by accident. The pattern is the manifest role's own
#: (``ck_input_manifest_entry_role``).
ROLE_COMPARISON_PDF: Final[str] = "comparison_pdf"
MANIFEST_ROLE_COMPARISON_PDF: Final[str] = "comparison.source_pdf"


def _required_source_role() -> str:
    """The manifest-entry role ``source_preparation`` requires, read from the contract.

    **These are two different namespaces and they were conflated.** The blob role above is
    ``source_document``; the manifest-entry role the analysis stage registry requires is
    ``source.document``. Writing the blob spelling into the manifest made every version
    produced by the real upload path unable to start a run - ``start_audit_run`` refused
    with ``analysis_input_invalid`` before any stage - while
    ``ck_input_manifest_entry_role`` accepted both, because it is a shape pattern rather
    than a vocabulary.

    It survived eight test suites because the run harness defined its own manifest role
    constant with the contract's spelling and seeded fixtures with that, so the executor
    was only ever shown the role its own code expected.

    Reading it from the frozen registry rather than restating it means a rename in the
    contract cannot silently diverge again: this raises at import instead.
    """
    registry = json.loads(_STAGE_REGISTRY.read_text(encoding="utf-8"))
    stages = registry.get("stages") or registry.get("registry") or []
    for stage in stages:
        if stage.get("stage_id") != "source_preparation":
            continue
        for declared in stage.get("required_inputs") or stage.get("inputs") or []:
            if declared.get("required") and declared.get("media_type") == "application/pdf":
                return str(declared["role"])
    raise RuntimeError(
        "contracts/analysis/v1/stage-registry.json declares no required PDF input for "
        "source_preparation; the manifest role cannot be derived"
    )


def _declared_source_role(role: str, media_type: str) -> str:
    """A bundle member's manifest role, confirmed against ``source_preparation``'s inputs.

    The same derivation as :func:`_required_source_role`, for the optional inputs a portal
    bundle adds: the role is not restated here, it is looked up in the registry by name and
    media type, and a registry that no longer declares it stops the import.
    """
    registry = json.loads(_STAGE_REGISTRY.read_text(encoding="utf-8"))
    for stage in registry.get("stages") or registry.get("registry") or []:
        if stage.get("stage_id") != "source_preparation":
            continue
        for declared in stage.get("required_inputs") or stage.get("inputs") or []:
            if declared.get("role") == role and declared.get("media_type") == media_type:
                return str(declared["role"])
    raise RuntimeError(
        f"contracts/analysis/v1/stage-registry.json declares no {role} input of type "
        f"{media_type} for source_preparation; the manifest role cannot be derived"
    )


_STAGE_REGISTRY = (
    Path(__file__).resolve().parents[3] / "contracts" / "analysis" / "v1" / "stage-registry.json"
)

#: The manifest-entry role PC-01 publishes, derived from the stage registry.
MANIFEST_ROLE_SOURCE_DOCUMENT: Final[str] = _required_source_role()
#: The roles a portal bundle adds (`W55B-INGEST-01`, plan section B3.4).
MANIFEST_ROLE_STRUCTURED_COMPANION: Final[str] = _declared_source_role(
    "source.structured_companion", "application/json"
)
MANIFEST_ROLE_MARKDOWN: Final[str] = _declared_source_role("source.markdown", "text/markdown")
MANIFEST_ROLE_STAMP_AUDIT: Final[str] = _declared_source_role(
    "source.stamp_audit", "application/json"
)


@dataclass(frozen=True, slots=True)
class ProjectRecord:
    """A project as a consumer sees it.

    ``name`` is a display label the expert chose. The schema's own comment calls it
    "not unique, not an identity and never a foreign key", so returning it reveals no
    address and creates no coupling.
    """

    project_uid: ProjectUid
    name: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ProjectListingRecord:
    """One row of ``listProjects``: a project, and how many documents it would list.

    A separate type from :class:`ProjectRecord` rather than an optional fourth field on
    it, because the count is a different kind of fact. ``create_project`` and
    ``get_project`` read one ``project`` row and know nothing about documents; making
    them carry a ``document_count`` would mean carrying ``None``, and a record that can
    answer "I do not know" is a record the serialiser has to interpret. Here the answer
    is always a number.

    ``document_count`` is an ``int`` and is **never** ``None``. A project with no
    documents reports ``0``, which is a measurement; omitting the field would be the
    different and weaker claim that nobody counted. `D-3` is this programme's record of
    what a flattering default costs.

    **It counts exactly what ``listDocuments`` would return for the same project** --
    documents whose ``current_version_uid`` points at a published version -- so a screen
    cannot render "3 documents" above a list of two. See ``_LIST_PROJECTS`` in
    ``repository.py``, which reuses ``_LIST_DOCUMENTS``' own join to say it.
    """

    project_uid: ProjectUid
    name: str
    created_at: datetime
    document_count: int


@dataclass(frozen=True, slots=True)
class ManifestEntry:
    """One row of a published version's immutable input manifest.

    ``blob_id`` is the only handle to the bytes. It is derived by
    ``auditmanager.storage`` from ``(sha256, size)``, so it addresses content rather
    than a location, and there is no accessor anywhere that turns it into a key.
    """

    role: str
    blob_id: BlobId
    sha256: str
    size_bytes: int
    media_type: str


@dataclass(frozen=True, slots=True)
class VersionClassificationRecord:
    """One version's **current** expert-confirmed project stage and section.

    `W59-SECTION-SEAL-01` stored the original confirmation in
    ``document_version_classification`` (``0024``), outside the immutable ``document_version``
    row and with the same no-UPDATE/no-DELETE guarantee. `CLASSIFICATION-CORRECTION-01`
    (``0028``) lets an expert correct it by appending revisions; this record is what the view
    ``version_classification_current`` derives: the latest revision, ``revision`` 1 while the
    version has no correction. ``confirmed_by_user_uid`` and ``confirmed_at`` are those of
    **that revision** -- who stands behind these values. It is a fact about exactly one
    ``version_uid``: never inherited by a newer version, never derived from ``document.section``,
    a file name or a suggestion.
    """

    version_uid: VersionUid
    project_stage: str
    section_code: str
    confirmed_by_user_uid: str
    confirmed_at: datetime
    revision: int = 1


@dataclass(frozen=True, slots=True)
class ClassificationRevisionRecord:
    """`CLASSIFICATION-CORRECTION-01`. One numbered entry of a version's classification history.

    Revision 1 is the original confirmation (``reason`` ``None``); revisions 2.. are the
    append-only corrections, each with the expert who made it and why.
    """

    version_uid: VersionUid
    revision: int
    project_stage: str
    section_code: str
    actor_user_uid: str
    reason: str | None
    decided_at: datetime


@dataclass(frozen=True, slots=True)
class CurrentVersionPlacementRecord:
    """`SECTION-READ-MODEL-01`. A document set's **current** version and where it is placed.

    The narrow row the section views read -- «Оптимизация разделов» finds its member sets and
    its unclassified ones through it -- so a caller asks «which sets' current versions are
    confirmed in section X» without walking every project's ``listDocuments``. It carries the
    set's address (project, document, version), the three display facts the view prints
    (title, ordinal, page count) and the placement itself; it carries no manifest and no
    blob handle.

    ``project_stage`` and ``section_code`` are the **current version's** current classification
    (``version_classification_current``, the latest revision since `CLASSIFICATION-CORRECTION-01`):
    both set, or both ``None`` while no expert has classified that version. They are never read
    from the legacy ``document.section``, from an older version of the set or from a file name,
    and ``version_ordinal`` is a display value, never a key (foundation invariant 3).
    """

    project_uid: ProjectUid
    project_name: str
    document_uid: DocumentUid
    display_title: str
    version_uid: VersionUid
    version_ordinal: int
    page_count: int
    project_stage: str | None
    section_code: str | None


@dataclass(frozen=True, slots=True)
class DocumentVersionRecord:
    """One published, immutable version and its complete input manifest.

    Immutable in the database as well as here: ``trg_document_version_immutable`` and
    ``trg_input_manifest_entry_immutable`` refuse UPDATE and DELETE with SQLSTATE
    ``AM003``. A corrected source file is a new ``version_uid``, never an edit.
    """

    version_uid: VersionUid
    document_uid: DocumentUid
    project_uid: ProjectUid
    #: The display ordinal of this version within its document, 1-based. Foundation
    #: invariant 3 says a display ordinal is **not an identifier** - it is never a key,
    #: never resolved against, and never used to address a version. It is carried
    #: because ``DocumentVersion`` in the frozen API contract requires it, so a reviewer
    #: can be told they are looking at version 2 rather than version 1.
    version_ordinal: int
    #: The display label the uploader supplied, carried because the frozen
    #: ``DocumentVersion`` schema declares it and `B7`'s upload panel has no other way to
    #: show a reviewer the title they typed. It is a label, never an identity: nothing
    #: resolves a version by it, and `source_filename` stays withheld because a filename is
    #: named in foundation invariant 3 and a display title is not.
    display_title: str
    #: `R-40`. One of the fifteen project sections (legacy's fourteen, `D-56`, and ``PS``),
    #: or ``None`` when the document has not been classified. Lives on the document, like ``display_title`` --
    #: it is a fact about what the document *is*, not about which published revision of
    #: its bytes this record describes -- and is set once, at upload, never rewritten.
    #: ``None`` is a real answer and is never defaulted to one of the codes. It is not the
    #: version's classification below and never routes a run.
    section: str | None
    media_type: str
    byte_size: int
    sha256: str
    page_count: int
    published_at: datetime
    manifest: tuple[ManifestEntry, ...]
    #: The three counts of a portal bundle (`W55B-INGEST-01`, migration ``0021``): all
    #: ``None`` for a version published without a bundle, all set for one published with
    #: it -- the database refuses a half-set row. They are facts about the PDF as
    #: pypdfium2 reads it and are **not** on the API wire.
    #:
    #: ``text_character_count`` -- pypdfium2's character count over the whole document,
    #: line breaks included (the analysis input budget's measure, G-11);
    #: ``textless_pages`` -- the ascending, 1-based pages with fewer than fifty such
    #: characters, empty when none; ``recognised_character_count`` -- the characters of
    #: recognised text the portal's markdown holds for those pages.
    text_character_count: int | None = None
    textless_pages: tuple[int, ...] | None = None
    recognised_character_count: int | None = None
    #: `W59-SECTION-SEAL-01`. The version's persisted classification, or ``None`` while no
    #: expert has classified it. Run start routes the analysis profile from this field only.
    #:
    #: `CLASSIFICATION-CORRECTION-01`: the **current** classification, which an expert may
    #: correct at any time -- unlike every other field here, which is immutable. So it is not
    #: part of the record's equality: the run input readers re-read a version after reading
    #: its bytes and refuse ``version_changed_during_*_read`` when the two records differ, and
    #: a correction that commits in that window must not fail a run that is pinned to the
    #: profile it started with.
    classification: VersionClassificationRecord | None = field(default=None, compare=False)
    #: `CMP-SEAL-C0` (migration ``0038``, ADR-0025 decision 11). How the version reached the
    #: product: ``portal_bundle`` (every version before ``0038``) or ``comparison_pdf`` (a plain
    #: PDF admitted for comparison only: no section analysis starts on it, and it never becomes the
    #: current version of a document that has a portal version). `CMP-INGEST-01` reads it from
    #: ``document_version.upload_kind`` in every SELECT of the repository; the default is the value of every
    #: version that existed before ``0038`` and of a record built without a row.
    upload_kind: str = UPLOAD_KIND_PORTAL_BUNDLE

    def entry(self, role: str) -> ManifestEntry:
        """The manifest entry for one role.

        Raises :class:`KeyError` rather than returning ``None``: a missing required
        role is a broken manifest, and the caller that asked for it cannot continue.
        """
        for item in self.manifest:
            if item.role == role:
                return item
        raise KeyError(role)

    @property
    def source(self) -> ManifestEntry:
        """The PDF this version *is*: the ``source_document`` entry every PC-01 version carries or,
        for a plain PDF admitted for comparison (`CMP-INGEST-01`), its ``comparison.source_pdf``
        entry. A version holds exactly one of the two, so the answer is never ambiguous; a manifest
        with neither is still a broken manifest (:class:`KeyError`).

        This is the *bytes* accessor (the content stream, the page reads). It is **not** how a run is
        admitted: :meth:`entry` with ``MANIFEST_ROLE_SOURCE_DOCUMENT`` stays strict, which is what the
        run start tests, so a comparison-only version is refused there (``comparison_only_version``).
        """
        for role in (MANIFEST_ROLE_SOURCE_DOCUMENT, MANIFEST_ROLE_COMPARISON_PDF):
            for item in self.manifest:
                if item.role == role:
                    return item
        raise KeyError(MANIFEST_ROLE_SOURCE_DOCUMENT)


@dataclass(frozen=True, slots=True)
class UploadOutcome:
    """What one upload command produced.

    ``replayed`` is ``True`` when the command key had already succeeded with this exact
    payload and the stored result was returned without creating anything. A caller can
    therefore distinguish "created" from "already done" without comparing timestamps.
    """

    version: DocumentVersionRecord
    replayed: bool = False
