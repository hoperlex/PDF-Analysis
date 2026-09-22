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
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass

#: Length of the truncated digest in the identifier. 12 hex characters is 48 bits; over a
#: population of snapshots measured in tens, a collision is not a risk worth a longer string.
#: The full digest is kept on the snapshot row, so nothing depends on the truncation.
DIGEST_CHARACTERS = 12


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
