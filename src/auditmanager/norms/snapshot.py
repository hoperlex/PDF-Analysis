"""The corpus-snapshot identifier — `R-17`'s consequence, settled as data.

`R-17` rules that provenance is a text footnote in an appendix, in the release version only,
naming the source and the date the corpus was drawn, with individual documents **not** pinned
to versions. The integrator recorded the consequence that follows: dropping per-document
versions makes the snapshot date the only anchor of provenance, so it has to be a field on
chunk rows, or the first corpus refresh makes every past verdict uninterpretable.

**Why the identifier is not a date.** Measured over all 674 documents, the `Дата сохранения`
field reads 23.07.2026 for 395, 24.07.2026 for 256, 20.08.2026 for 6, and is absent from 17.
So *"as at 20.08.2026"* is false for 668 documents and *"as at 23.07.2026"* is false for 279,
and no date at all is true for the 17. A single date is not a conservative approximation of
the window; it is a false statement about most of the corpus.

**What the identifier is instead.**

    <first-draw>..<last-draw>+<n-undated>d.<content-digest-12>
    2026-07-23..2026-08-20+17d.3f9a1c2b7d10

Three parts, each answering a question the others cannot:

- **the window** — the earliest and latest date the corpus states about itself, derived from
  the corpus rather than configured, so it cannot drift from the documents it describes;
- **the undated count** — how many documents the window does *not* cover. It is in the
  identifier and not only in a table because a reader who sees `+17d` asks what those are,
  and a reader who sees only a window does not know to;
- **the content digest** — SHA-256 over `(slug, source document id, sha256 of results.md)`
  for every document, sorted, truncated to 12 hex characters. The dates are what the corpus
  *says*; the digest is what it *is*. A re-draw that silently reissues a ГОСТ under the same
  save date changes the digest and therefore the snapshot, which is exactly the case the
  ruling's consequence was written about.

The digest is computed over a sorted list of content hashes, never over a directory listing or
a commit name: the corpus is invisible to git and a filesystem walk has no guaranteed order.

**The segmentation profile (`D-126`).** The key names the effective *text*; the paragraphs
stored under it are a projection of that text by one segmentation profile. Any profile other
than the literal ``markdown-v1`` therefore appends ``+seg-<profile>`` after the digest
(:func:`with_segmentation_profile`), so a raised profile is a new snapshot beside the old one
rather than a conflict on its key. ``markdown-v1`` adds nothing: every key minted so far, and
the bake-off's pinned key, stays byte-identical.

**The row digest.** :func:`row_digest` is the canonical digest over a stored snapshot's
declared canonical columns — the snapshot row, every document and every paragraph, with their
opaque ids, text and ``text_reliability``. It is what a bundle's manifest records and what the
importer and ``report`` recompute: equal digests mean equal rows with equal ids, in any
database.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, replace

#: Length of the truncated digest in the identifier. 12 hex characters is 48 bits; over a
#: population of snapshots measured in tens, a collision is not a risk worth a longer string.
#: The full digest is kept on the snapshot row, so nothing depends on the truncation.
DIGEST_CHARACTERS = 12

#: `D-126`: the one segmentation profile whose key carries no ``+seg-`` term. A literal, not
#: ``segmentation.SEGMENTATION_PROFILE_VERSION``: raising that constant must move the key.
BASE_SEGMENTATION_PROFILE = "markdown-v1"

#: The profile grammar TRANSPORT's bundle-name ERE accepts (`forced-command.sh`), and at most
#: ``norms_snapshot.segmentation_profile``'s 100 characters.
_SEGMENTATION_PROFILE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEGMENTATION_TERM = "+seg-"


@dataclass(frozen=True, slots=True)
class DocumentFingerprint:
    """One document's contribution to the snapshot digest."""

    slug: str
    source_document_id: str
    content_sha256: str
    drawn_on: str | None


@dataclass(frozen=True, slots=True)
class CorpusSnapshot:
    """A drawn corpus, identified."""

    snapshot_id: str
    drawn_from: str | None
    drawn_to: str | None
    undated_documents: int
    document_count: int
    content_digest: str

    @property
    def content_key(self) -> str:
        """Deterministic equality key, distinct from persisted ``norms_snapshot_id``."""
        return self.snapshot_id

    @property
    def footnote_window(self) -> str:
        """The appendix footnote's date phrase, in the form `R-17` accepts.

        `R-17` offers *"as at 20.08.2026"* or the window *"23.07–20.08.2026"* and says any
        single date is wrong for part of the corpus. This returns the window, and returns it
        as a window even when both ends are the same day, so the phrase does not quietly
        become a single date the next time a corpus happens to be drawn in one sitting.
        """
        if self.drawn_from is None or self.drawn_to is None:
            return "date not stated by the corpus"
        return f"{self.drawn_from}..{self.drawn_to}"


def with_segmentation_profile(snapshot: CorpusSnapshot, profile: str) -> CorpusSnapshot:
    """The snapshot as stored under one segmentation profile (`D-126`).

    ``markdown-v1`` returns ``snapshot`` itself. Any other profile appends ``+seg-<profile>``
    after the digest; the window, counts and full digest are unchanged, because the profile
    says how the text is cut, not which text it is. A key that already names a profile is
    refused rather than qualified twice.
    """
    if len(profile) > 100 or _SEGMENTATION_PROFILE.match(profile) is None:
        raise ValueError(f"segmentation profile {profile!r} is not [a-z0-9]+(-[a-z0-9]+)*")
    if SEGMENTATION_TERM in snapshot.snapshot_id:
        raise ValueError(f"{snapshot.snapshot_id!r} already names a segmentation profile")
    if profile == BASE_SEGMENTATION_PROFILE:
        return snapshot
    return replace(snapshot, snapshot_id=f"{snapshot.snapshot_id}{SEGMENTATION_TERM}{profile}")


def fingerprint(slug: str, source_document_id: str, results_md: bytes, drawn_on: str | None) -> DocumentFingerprint:
    return DocumentFingerprint(
        slug=slug,
        source_document_id=source_document_id,
        content_sha256=hashlib.sha256(results_md).hexdigest(),
        drawn_on=drawn_on,
    )


def derive(fingerprints: Iterable[DocumentFingerprint]) -> CorpusSnapshot:
    """Derive the snapshot identifier from the documents themselves.

    Structure first, then compute, then write the value: the fingerprints are sorted into a
    canonical order before a byte is hashed, so two runs over the same corpus on two machines
    with two different directory orders agree.
    """
    ordered = sorted(fingerprints, key=lambda f: (f.slug, f.source_document_id, f.content_sha256))
    if not ordered:
        raise ValueError("a corpus snapshot needs at least one document")

    digest = hashlib.sha256()
    for item in ordered:
        digest.update(item.slug.encode("utf-8"))
        digest.update(b"\x00")
        digest.update(item.source_document_id.encode("utf-8"))
        digest.update(b"\x00")
        digest.update(item.content_sha256.encode("ascii"))
        digest.update(b"\n")
    content_digest = digest.hexdigest()

    dates = sorted(item.drawn_on for item in ordered if item.drawn_on is not None)
    undated = sum(1 for item in ordered if item.drawn_on is None)
    drawn_from = dates[0] if dates else None
    drawn_to = dates[-1] if dates else None

    window = f"{drawn_from}..{drawn_to}" if drawn_from is not None else "undated"
    snapshot_id = f"{window}+{undated}d.{content_digest[:DIGEST_CHARACTERS]}"

    return CorpusSnapshot(
        snapshot_id=snapshot_id,
        drawn_from=drawn_from,
        drawn_to=drawn_to,
        undated_documents=undated,
        document_count=len(ordered),
        content_digest=content_digest,
    )


# --- stored rows with their ids, and their canonical digest ---------------------------------

#: The row digest's own format. A change to what it covers or how it is serialised is a new
#: value, so a manifest written under one form can never be compared with another silently.
ROW_DIGEST_VERSION = "norm-snapshot-rows/1"


@dataclass(frozen=True, slots=True)
class SnapshotRow:
    """``norms_snapshot``'s declared columns (``created_at`` is the database's, not the row's)."""

    norms_snapshot_id: str
    content_key: str
    base_content_key: str
    content_digest: str
    drawn_from: str | None
    drawn_to: str | None
    undated_documents: int
    document_count: int
    repair_count: int
    unreliable_count: int
    segmentation_profile: str


@dataclass(frozen=True, slots=True)
class DocumentRow:
    """``norm_document``'s declared columns; the private ``norm_document_pk`` is never carried."""

    norm_document_id: str
    source_document_ref: str
    slug: str
    title: str
    doc_type: str
    drawn_on: str | None
    source_attribution: str
    pdf_page_count: int
    block_count: int
    page_heading_count: int
    recognised_characters: int
    paragraph_count: int


@dataclass(frozen=True, slots=True)
class ParagraphRow:
    """``norm_paragraph``'s declared columns, its document named by its opaque id."""

    norm_paragraph_id: str
    norm_document_id: str
    ordinal: int
    page_label: int
    block_ref: str
    char_offset: int
    char_length: int
    kind: str
    clause_number: str | None
    text: str
    text_reliability: str


_SNAPSHOT_FIELDS = (
    "norms_snapshot_id", "content_key", "base_content_key", "content_digest", "drawn_from",
    "drawn_to", "undated_documents", "document_count", "repair_count", "unreliable_count",
    "segmentation_profile",
)
_DOCUMENT_FIELDS = (
    "norm_document_id", "source_document_ref", "slug", "title", "doc_type", "drawn_on",
    "source_attribution", "pdf_page_count", "block_count", "page_heading_count",
    "recognised_characters", "paragraph_count",
)
_PARAGRAPH_FIELDS = (
    "norm_paragraph_id", "norm_document_id", "ordinal", "page_label", "block_ref",
    "char_offset", "char_length", "kind", "clause_number", "text", "text_reliability",
)


@dataclass(frozen=True, slots=True)
class SnapshotRows:
    """One snapshot's canonical rows with their ids: what is exported and imported as given."""

    snapshot: SnapshotRow
    documents: tuple[DocumentRow, ...]
    paragraphs: tuple[ParagraphRow, ...]

    @property
    def row_digest(self) -> str:
        return row_digest(self)


def _line(tag: str, row: object, names: tuple[str, ...]) -> bytes:
    values = [getattr(row, name) for name in names]
    return (
        tag
        + json.dumps(values, ensure_ascii=False, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


class RowDigest:
    """The row digest, fed one row at a time in canonical order — and refusing any other.

    One snapshot row first; then documents in ascending ``norm_document_id``; then paragraphs
    in ascending ``(norm_document_id, ordinal)``. Ids are compared as Python strings, which is
    code-point order, the order PostgreSQL gives under ``COLLATE "C"``. A row out of order
    raises instead of hashing, so a reader that forgot its ``ORDER BY`` cannot produce a
    plausible wrong digest.
    """

    __slots__ = ("_digest", "_last", "_stage")

    def __init__(self) -> None:
        self._digest = hashlib.sha256()
        self._digest.update(f"{ROW_DIGEST_VERSION}\n".encode("ascii"))
        self._stage = 0
        self._last: tuple[str, int] | str | None = None

    def snapshot(self, row: SnapshotRow) -> None:
        if self._stage != 0:
            raise ValueError("the row digest takes exactly one snapshot row, first")
        self._digest.update(_line("S", row, _SNAPSHOT_FIELDS))
        self._stage = 1

    def document(self, row: DocumentRow) -> None:
        if self._stage != 1:
            raise ValueError("documents follow the snapshot row and precede every paragraph")
        if self._last is not None and not row.norm_document_id > self._last:  # type: ignore[operator]
            raise ValueError(f"document {row.norm_document_id} is out of canonical order")
        self._digest.update(_line("D", row, _DOCUMENT_FIELDS))
        self._last = row.norm_document_id

    def paragraph(self, row: ParagraphRow) -> None:
        if self._stage == 1:
            self._stage, self._last = 2, None
        if self._stage != 2:
            raise ValueError("paragraphs follow the snapshot row and every document")
        key = (row.norm_document_id, row.ordinal)
        if self._last is not None and not key > self._last:  # type: ignore[operator]
            raise ValueError(f"paragraph {row.norm_paragraph_id} is out of canonical order")
        self._digest.update(_line("P", row, _PARAGRAPH_FIELDS))
        self._last = key

    def hexdigest(self) -> str:
        if self._stage == 0:
            raise ValueError("the row digest needs the snapshot row")
        return self._digest.hexdigest()


def row_digest(rows: SnapshotRows) -> str:
    """SHA-256 over the snapshot's canonical rows, independent of database and insertion order.

    Structure, then compute: documents are sorted by ``norm_document_id`` and paragraphs by
    ``(norm_document_id, ordinal)`` before a byte is hashed. Each row is one line — a tag, then
    a compact JSON array of its declared columns in a fixed order — under a version header.
    Private keys, timestamps, generated columns and the rebuildable chunks are not covered.
    """
    digest = RowDigest()
    digest.snapshot(rows.snapshot)
    for document in sorted(rows.documents, key=lambda row: row.norm_document_id):
        digest.document(document)
    for paragraph in sorted(
        rows.paragraphs, key=lambda row: (row.norm_document_id, row.ordinal)
    ):
        digest.paragraph(paragraph)
    return digest.hexdigest()
