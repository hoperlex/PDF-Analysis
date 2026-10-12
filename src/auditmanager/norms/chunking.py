"""Paragraphs joined into retrieval chunks.

`R-16` measured 58 021 chunks at ~1200 characters averaging 1072, over 319 730 substantive
paragraphs. The join is greedy and forward-only: accumulate consecutive paragraphs of one
document until the next would carry the chunk past the target, then emit.

Two rules that are decisions rather than mechanics:

- **A paragraph is never split.** A paragraph longer than the target becomes a chunk on its
  own. Splitting mid-sentence to hit a character count would hand an expert a quotation that
  does not end, and the anchoring `R-16` fixed is by page — there is no sub-paragraph anchor
  to split against.
- **A chunk may cross a page boundary.** Norm clauses run across page breaks constantly and
  the ConsultantPlus export cuts mid-sentence at one. A chunk carries `page_first` and
  `page_last`; the expert is shown one page crop per page in the span.

Two profiles exist (`W54-PLAN.md` §3.4, `F-4`):

- ``characters-v1`` joins **every** paragraph. It is the W33 profile and stays byte-identical,
  and it is **refused** over a snapshot that carries any unreliable block: a chunk set that
  silently includes text the repair ledger marked unreliable is exactly the defect `F-4`
  names.
- ``characters-v2`` is the reliability-aware profile. It joins the same way, but an
  unreliable paragraph is skipped and **ends** the chunk being built, so a chunk is always a
  consecutive span of reliable canonical paragraphs (the ``norm_chunk`` span CHECK needs that)
  and never stitches the text on both sides of a skipped paragraph into one quotation. Its
  invariant: every reliable paragraph is covered exactly once, and exactly the unreliable set
  is skipped (:func:`verify_coverage`). Over a document with no unreliable paragraph its chunks
  equal ``characters-v1``'s, field for field.
"""

from __future__ import annotations

from collections.abc import Sequence

from .model import Chunk, Paragraph

#: The character target `R-16` measured against.
DEFAULT_TARGET_CHARACTERS = 1200

#: How paragraphs are rejoined inside a chunk. A blank line, because that is what separated
#: them in the source and what makes the chunk readable when an expert is shown it.
JOIN = "\n\n"

#: Stored with every rebuildable chunk set. Changing the algorithm increments this value;
#: changing only the target remains visible after the colon.
CHUNKING_PROFILE_VERSION = "characters-v1"

#: The reliability-aware profile (`F-4`): unreliable paragraphs are skipped and break a chunk.
RELIABLE_CHUNKING_PROFILE_VERSION = "characters-v2"

#: The profile the loader builds unless told otherwise. A loaded snapshot must be loadable
#: whatever its ledger says, and only the reliability-aware profile is.
DEFAULT_CHUNKING_VERSION = RELIABLE_CHUNKING_PROFILE_VERSION

CHUNKING_VERSIONS = (CHUNKING_PROFILE_VERSION, RELIABLE_CHUNKING_PROFILE_VERSION)


class ChunkingRefused(ValueError):
    """A chunking profile cannot be built over this text (`F-4`)."""


def chunking_profile(
    target_characters: int, version: str = CHUNKING_PROFILE_VERSION
) -> str:
    """Stable profile key for one exact chunking policy."""
    if target_characters <= 0:
        raise ValueError("target_characters must be positive")
    if version not in CHUNKING_VERSIONS:
        raise ValueError(f"unknown chunking profile version {version!r}")
    return f"{version}:{target_characters}"


def parse_chunking_profile(profile: str) -> tuple[str, int]:
    """``"characters-v2:1200"`` → ``("characters-v2", 1200)``, refusing anything else."""
    version, separator, target = profile.partition(":")
    if not separator or not target.isdecimal() or target != str(int(target)):
        raise ValueError(f"malformed chunking profile {profile!r}")
    if chunking_profile(int(target), version) != profile:
        raise ValueError(f"malformed chunking profile {profile!r}")
    return version, int(target)


def join_into_chunks(
    paragraphs: Sequence[Paragraph],
    snapshot_id: str,
    target_characters: int = DEFAULT_TARGET_CHARACTERS,
) -> tuple[Chunk, ...]:
    """Join one document's substantive paragraphs into chunks (``characters-v1``'s join).

    Every paragraph is joined, whatever its reliability; :func:`chunk_paragraphs` is the
    build entry point that refuses this profile over unreliable text.
    """
    if target_characters <= 0:
        raise ValueError("target_characters must be positive")
    return _join_runs([tuple(paragraphs)], snapshot_id, target_characters)


def chunk_paragraphs(
    paragraphs: Sequence[Paragraph],
    snapshot_id: str,
    target_characters: int = DEFAULT_TARGET_CHARACTERS,
    *,
    version: str = DEFAULT_CHUNKING_VERSION,
) -> tuple[Chunk, ...]:
    """Build one document's chunks under a named profile version.

    ``characters-v1`` refuses a document carrying an unreliable paragraph; ``characters-v2``
    skips each unreliable paragraph and starts a new chunk after it. The result is checked
    against :func:`verify_coverage` before it is returned.
    """
    if target_characters <= 0:
        raise ValueError("target_characters must be positive")
    if version == CHUNKING_PROFILE_VERSION:
        unreliable = [paragraph.ordinal for paragraph in paragraphs if not paragraph.is_reliable]
        if unreliable:
            raise ChunkingRefused(
                f"{CHUNKING_PROFILE_VERSION} joins every paragraph and this document carries "
                f"{len(unreliable)} unreliable one(s) (first ordinal {unreliable[0]}); "
                f"build {RELIABLE_CHUNKING_PROFILE_VERSION} instead"
            )
        chunks = _join_runs([tuple(paragraphs)], snapshot_id, target_characters)
    elif version == RELIABLE_CHUNKING_PROFILE_VERSION:
        runs: list[tuple[Paragraph, ...]] = []
        run: list[Paragraph] = []
        for paragraph in paragraphs:
            if paragraph.is_reliable:
                run.append(paragraph)
                continue
            if run:
                runs.append(tuple(run))
                run = []
        if run:
            runs.append(tuple(run))
        chunks = _join_runs(runs, snapshot_id, target_characters)
    else:
        raise ValueError(f"unknown chunking profile version {version!r}")
    verify_coverage(paragraphs, chunks, version=version)
    return chunks


def verify_coverage(
    paragraphs: Sequence[Paragraph], chunks: Sequence[Chunk], *, version: str
) -> None:
    """The profile's invariant, or :class:`ChunkingRefused`.

    Chunks are in ordinal order ``0..n-1``; each spans consecutive canonical paragraphs whose
    ``paragraph_count`` equals the span; spans are disjoint and ascending; every paragraph a
    span names is reliable under ``characters-v2``; and the union of the spans is exactly the
    reliable set (``characters-v2``) or every paragraph (``characters-v1``).
    """
    by_ordinal = {paragraph.ordinal: paragraph for paragraph in paragraphs}
    if len(by_ordinal) != len(paragraphs):
        raise ChunkingRefused("two paragraphs share one ordinal")
    covered: list[int] = []
    previous_last = -1
    for index, chunk in enumerate(chunks):
        first, last = chunk.paragraph_ordinal_first, chunk.paragraph_ordinal_last
        if chunk.ordinal != index:
            raise ChunkingRefused(f"chunk ordinal {chunk.ordinal} is not {index}")
        if first <= previous_last or last < first:
            raise ChunkingRefused(f"chunk {index} span {first}..{last} overlaps or inverts")
        if chunk.paragraph_count != last - first + 1:
            raise ChunkingRefused(
                f"chunk {index} counts {chunk.paragraph_count} paragraphs over {first}..{last}"
            )
        for ordinal in range(first, last + 1):
            paragraph = by_ordinal.get(ordinal)
            if paragraph is None:
                raise ChunkingRefused(f"chunk {index} names absent paragraph {ordinal}")
            if version == RELIABLE_CHUNKING_PROFILE_VERSION and not paragraph.is_reliable:
                raise ChunkingRefused(f"chunk {index} includes unreliable paragraph {ordinal}")
            covered.append(ordinal)
        previous_last = last
    if version == RELIABLE_CHUNKING_PROFILE_VERSION:
        expected = [p.ordinal for p in sorted(paragraphs, key=lambda p: p.ordinal) if p.is_reliable]
    else:
        expected = sorted(by_ordinal)
    if covered != expected:
        missing = sorted(set(expected) - set(covered))
        raise ChunkingRefused(
            f"{version} chunks cover {len(covered)} paragraphs, expected {len(expected)}"
            + (f"; first uncovered ordinal {missing[0]}" if missing else "")
        )


def _join_runs(
    runs: Sequence[Sequence[Paragraph]], snapshot_id: str, target_characters: int
) -> tuple[Chunk, ...]:
    chunks: list[Chunk] = []
    batch: list[Paragraph] = []

    def flush() -> None:
        if not batch:
            return
        text = JOIN.join(paragraph.text for paragraph in batch)
        chunks.append(
            Chunk(
                snapshot_id=snapshot_id,
                document_slug=batch[0].document_slug,
                ordinal=len(chunks),
                page_first=min(paragraph.page_label for paragraph in batch),
                page_last=max(paragraph.page_label for paragraph in batch),
                char_offset=batch[0].char_offset,
                char_length=batch[-1].char_offset + batch[-1].char_length - batch[0].char_offset,
                paragraph_count=len(batch),
                clause_numbers=tuple(
                    paragraph.clause_number
                    for paragraph in batch
                    if paragraph.clause_number is not None
                ),
                text=text,
                paragraph_ordinal_first=batch[0].ordinal,
                paragraph_ordinal_last=batch[-1].ordinal,
            )
        )
        batch.clear()

    for run in runs:
        running = 0
        for paragraph in run:
            addition = len(paragraph.text) + (len(JOIN) if batch else 0)
            if batch and running + addition > target_characters:
                flush()
                running = 0
                addition = len(paragraph.text)
            batch.append(paragraph)
            running += addition
        flush()
    return tuple(chunks)
