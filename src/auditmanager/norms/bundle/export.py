"""``export``: the promotion database and the drop become one verified bundle (plan §3.5).

Run on this host only (`W54-CORPUS-OPERATE-01` step 4), against the promotion database
(``DATABASE_URL``) and the drop, read-only. Nothing here reaches the stand.

1. **Read** the snapshot's canonical rows with their ids, the stored row digest, the chunk
   build of the named profile and, unless ``--without-build``, its complete embedding build
   with every window and vector, keyed by the computed chunk key (`D-127`). Each stored
   vector is re-packed and must hash to its stored ``embedding_sha256``.
2. **Objects.** For every document: its ``document.pdf`` (anchor ``pdf`` = the drop's opaque
   ``source_document_ref``) and every crop the drop's ``crops_index.json`` names for it
   (anchor ``crop`` = the block's opaque ``blk_…``). Each file is checked against the
   operator's ``SHA256SUMS`` over the drop, **hardlinked** into
   ``objects/<2 hex>/<sha256>.pdf`` (same filesystem; ``--copy-objects`` copies instead, and
   says so), re-hashed there, and made read-only. A file the sums do not name, or name with
   other bytes, stops the export.
3. **Identity** (`W54-JUDGE-Y` F1): the base snapshot is derived again from the rows'
   documents and the drop's ``results.md`` bytes (``snapshot.derive``) and must be the row's
   ``base_content_key`` and window; ``with_segmentation_profile(repaired_snapshot(base,
   ledger), profile)`` -- or the base itself without a ledger -- must be its ``content_key``
   and ``content_digest``; every ledger block's ``crop_sha256`` must be the bundled crop of
   that ``(slug, block_id)``; and the ledger file must name the ``SHA256SUMS`` given here
   (`F3`). So a bundle cannot pair one drop's text with another drop's PDFs or ledger.
4. **Rows, build, manifest, ``SHA256SUMS``**, then the directory is renamed
   ``<content_key>+<sha256(SHA256SUMS)>``. Until that rename the work is
   ``incomplete-*`` beside it, never a name the inbound key would accept.

The drop's layout (``<slug>/document.pdf``, ``<slug>/crops/<block_id>.pdf`` and the root
``crops_index.json``) is the drop's own ``MANIFEST.json`` statement; ``corpus_source`` reads
the document text and the crop paths, this module reads the PDFs.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import shutil
import stat
import tempfile
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.shared.identity import NormsSnapshotId

from ..corpus_source import DropSumsInvalid, crop_path, read_document
from ..corpus_source import read_drop_sums as _parse_drop_sums
from ..custody import binding_digest
from ..embedding import vectors
from ..embedding.digest import EMBEDDING_SET_DIGEST_VERSION, EmbeddingSetDigest
from ..embedding.model import ChunkEmbedding, EmbeddedWindow
from ..embedding.profile import EMBEDDING_PROFILE
from ..embedding_repository import NormEmbeddingRepository
from ..model import TextReliability
from ..repair import RepairLedger, repaired_snapshot
from ..repair_journal import read_ledger_file
from ..repository import NormsProjectionConflict, NormsRepository
from ..segmentation import drawn_on
from ..snapshot import (
    DocumentFingerprint,
    SnapshotRows,
    derive,
    fingerprint,
    with_segmentation_profile,
)
from .contents import BuildWriter, write_rows
from .errors import BundleRefused
from .layout import (
    MANIFEST_NAME,
    SUMS_NAME,
    bundle_name,
    object_path,
    render_sums,
    require_content_key,
    sha256_file,
    verify_bundle,
)
from .manifest import (
    MIN_MIGRATION_HEAD,
    PDF_MEDIA_TYPE,
    BuildFacts,
    Counts,
    LedgerFacts,
    Manifest,
    ManifestFile,
    ObjectSlot,
    SnapshotFacts,
    is_designatable_chunking,
    validate_manifest,
)

DOCUMENT_PDF: Final[str] = "document.pdf"
CROPS_INDEX: Final[str] = "crops_index.json"
DB_GROWTH_METHOD: Final[str] = (
    "proportional-relation-size-v1: per norm table, pg_total_relation_size x this snapshot's "
    "share of its rows; plus 1536 bytes per custody slot (estimated)"
)
CUSTODY_BYTES_PER_SLOT: Final[int] = 1536

_SELECT_WINDOWS = text(
    """
    SELECT d.source_document_ref, c.ordinal AS chunk_ordinal, e.window_ordinal, e.token_count,
           e.char_offset, e.char_length, e.paragraph_ordinal_first, e.paragraph_ordinal_last,
           e.input_sha256, e.embedding_sha256, e.embedding::text AS embedding
    FROM norm_embedding e
    JOIN norm_chunk c ON c.norm_chunk_pk = e.norm_chunk_pk
    JOIN norm_document d
      ON d.norms_snapshot_id = c.norms_snapshot_id AND d.norm_document_pk = c.norm_document_pk
    WHERE e.norms_snapshot_id = :snapshot
      AND e.chunking_profile = :chunking_profile
      AND e.embedding_profile = :embedding_profile
    ORDER BY d.source_document_ref COLLATE "C", c.ordinal, e.window_ordinal
    """
)
_SELECT_BUILD = text(
    """
    SELECT chunk_count, window_count, embedding_set_sha256 FROM norm_embedding_build
    WHERE norms_snapshot_id = :snapshot AND chunking_profile = :chunking_profile
      AND embedding_profile = :embedding_profile
    """
)
#: Per norm table: its total size, its row count, and this snapshot's rows.
_GROWTH = text(
    """
    SELECT
      pg_total_relation_size('norms_snapshot'), (SELECT count(*) FROM norms_snapshot), 1,
      pg_total_relation_size('norm_document'), (SELECT count(*) FROM norm_document),
        (SELECT count(*) FROM norm_document WHERE norms_snapshot_id = :snapshot),
      pg_total_relation_size('norm_paragraph'), (SELECT count(*) FROM norm_paragraph),
        (SELECT count(*) FROM norm_paragraph WHERE norms_snapshot_id = :snapshot),
      pg_total_relation_size('norm_chunk'), (SELECT count(*) FROM norm_chunk),
        (SELECT count(*) FROM norm_chunk
          WHERE norms_snapshot_id = :snapshot AND chunking_profile = :chunking_profile),
      pg_total_relation_size('norm_chunk_build'), (SELECT count(*) FROM norm_chunk_build), 1,
      pg_total_relation_size('norm_embedding'), (SELECT count(*) FROM norm_embedding),
        (SELECT count(*) FROM norm_embedding
          WHERE norms_snapshot_id = :snapshot AND chunking_profile = :chunking_profile),
      pg_total_relation_size('norm_embedding_build'), (SELECT count(*) FROM norm_embedding_build), 1
    """
)


# --- what the database gives ----------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ExportSource:
    """Everything the export takes from the promotion database."""

    rows: SnapshotRows
    row_digest: str
    chunking_profile: str
    chunk_count: int
    build: BuildFacts | None
    #: Re-iterable: each call streams the build's chunks in canonical order.
    chunks: Callable[[], Iterator[ChunkEmbedding]] | None
    norm_table_bytes: int


def _parse_vector(literal: str, expected_sha256: str, where: str) -> bytes:
    body = literal.strip()
    if not (body.startswith("[") and body.endswith("]")):
        raise BundleRefused("vector_unreadable", f"{where}: the stored vector is not a pgvector literal")
    try:
        packed = vectors.pack([float(value) for value in body[1:-1].split(",")])
    except (ValueError, vectors.VectorRefused) as exc:
        raise BundleRefused("vector_unreadable", f"{where}: {exc}") from None
    if hashlib.sha256(packed).hexdigest() != expected_sha256:
        raise BundleRefused(
            "vector_round_trip",
            f"{where}: the stored vector does not re-pack to its embedding_sha256",
        )
    return packed


def _stream_chunks(
    session: Session, snapshot_id: str, chunking_profile: str
) -> Iterator[ChunkEmbedding]:
    result = session.execute(
        _SELECT_WINDOWS,
        {"snapshot": snapshot_id, "chunking_profile": chunking_profile, "embedding_profile": EMBEDDING_PROFILE},
        execution_options={"stream_results": True, "yield_per": 1000},
    )
    current: tuple[str, int] | None = None
    windows: list[EmbeddedWindow] = []
    for row in result.mappings():
        key = (str(row["source_document_ref"]), int(row["chunk_ordinal"]))
        if current is not None and key != current:
            yield ChunkEmbedding(document_ref=current[0], chunk_ordinal=current[1], windows=tuple(windows))
            windows = []
        current = key
        windows.append(
            EmbeddedWindow(
                window_ordinal=int(row["window_ordinal"]),
                char_offset=int(row["char_offset"]),
                char_length=int(row["char_length"]),
                token_count=int(row["token_count"]),
                paragraph_ordinal_first=int(row["paragraph_ordinal_first"]),
                paragraph_ordinal_last=int(row["paragraph_ordinal_last"]),
                input_sha256=str(row["input_sha256"]),
                vector=_parse_vector(
                    str(row["embedding"]), str(row["embedding_sha256"]), f"chunk {key!r}"
                ),
            )
        )
    if current is not None:
        yield ChunkEmbedding(document_ref=current[0], chunk_ordinal=current[1], windows=tuple(windows))


def require_designatable_chunking(chunking_profile: str) -> None:
    """Refuse, before anything is read or written, a profile designation would refuse."""
    if not is_designatable_chunking(chunking_profile):
        raise BundleRefused(
            "chunking_profile_refused",
            f"{chunking_profile!r} is not characters-v2:<target>: a snapshot is designated "
            "only over the reliability-aware build, so a bundle over any other profile would "
            "import and then never become current (W55A-FIX, JUDGE-Y Y-5)",
        )


def read_export_source(
    session: Session,
    *,
    snapshot_id: str,
    chunking_profile: str,
    without_build: bool = False,
) -> ExportSource:
    """Read what a bundle carries from the promotion database. Writes nothing."""
    require_designatable_chunking(chunking_profile)
    try:
        identity = NormsSnapshotId.parse(snapshot_id)
    except ValueError as exc:
        raise BundleRefused("snapshot_absent", str(exc)) from None
    repository = NormsRepository(session)
    try:
        rows = repository.read_snapshot_rows(identity)
    except NormsProjectionConflict as exc:
        raise BundleRefused("snapshot_absent", str(exc)) from None
    digest = repository.stored_row_digest(identity)
    if digest != rows.row_digest:
        raise BundleRefused(
            "row_digest_unstable", f"the stored row digest {digest} is not the rows' {rows.row_digest}"
        )
    try:
        counts = repository.counts(identity, chunking_profile)
    except NormsProjectionConflict as exc:
        raise BundleRefused("chunk_build_absent", str(exc)) from None
    build: BuildFacts | None = None
    chunks: Callable[[], Iterator[ChunkEmbedding]] | None = None
    parameters = {
        "snapshot": snapshot_id,
        "chunking_profile": chunking_profile,
        "embedding_profile": EMBEDDING_PROFILE,
    }
    row = session.execute(_SELECT_BUILD, parameters).one_or_none()
    if row is None:
        if not without_build:
            raise BundleRefused(
                "build_absent",
                f"snapshot {snapshot_id} has no complete {EMBEDDING_PROFILE} build over "
                f"{chunking_profile}; finish it first (python -m auditmanager.norms.embedding) or "
                "pass --without-build, which the importer refuses",
            )
    else:
        recomputed = NormEmbeddingRepository(session).stored_build_digest(identity, chunking_profile)
        stored = (str(row.embedding_set_sha256), int(row.chunk_count), int(row.window_count))
        if recomputed != stored:
            raise BundleRefused(
                "build_digest_unstable",
                f"the stored windows digest to {recomputed!r}; the completion row says {stored!r}",
            )
        if int(row.chunk_count) != counts.chunks:
            raise BundleRefused(
                "build_incomplete",
                f"the build covers {int(row.chunk_count)} chunks; the chunk build holds {counts.chunks}",
            )
        build = BuildFacts(
            embedding_profile=EMBEDDING_PROFILE,
            digest_version=EMBEDDING_SET_DIGEST_VERSION,
            embedding_set_sha256=str(row.embedding_set_sha256),
            chunk_count=int(row.chunk_count),
            window_count=int(row.window_count),
        )

        def chunks() -> Iterator[ChunkEmbedding]:
            return _stream_chunks(session, snapshot_id, chunking_profile)

    growth = session.execute(_GROWTH, parameters).one()
    norm_bytes = 0
    values = [int(value) for value in growth]
    for index in range(0, len(values), 3):
        total, rows_all, mine = values[index : index + 3]
        if rows_all:
            norm_bytes += total * mine // rows_all
    return ExportSource(
        rows=rows,
        row_digest=digest,
        chunking_profile=chunking_profile,
        chunk_count=counts.chunks,
        build=build,
        chunks=chunks,
        norm_table_bytes=norm_bytes,
    )


# --- what the drop gives --------------------------------------------------------------


def read_drop_sums(path: Path) -> tuple[str, dict[str, str]]:
    """``(sha256 of the file, relative path -> sha256)`` of the operator's drop sums.

    The one parser the repair run also uses (``corpus_source.read_drop_sums``, `F3`).
    """
    try:
        parsed = _parse_drop_sums(path)
    except DropSumsInvalid as invalid:
        raise BundleRefused(invalid.reason, invalid.message) from None
    return parsed.sha256, dict(parsed.entries)


def read_crops_index(
    corpus: Path, *, sums: Mapping[str, str] | None = None
) -> dict[str, tuple[str, ...]]:
    """``slug -> block ids`` from the drop's root ``crops_index.json``.

    With source sums, bind the index's bytes and complete crop inventory to that listing
    before export creates a staging directory. The exporter later checks each object byte.
    """
    path = corpus / CROPS_INDEX
    try:
        data = path.read_bytes()
        entries = json.loads(data.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BundleRefused("drop_crops_index", f"{CROPS_INDEX} is unreadable: {exc}") from None
    if sums is not None:
        expected = sums.get(CROPS_INDEX)
        if expected is None:
            raise BundleRefused("drop_file_unsummed", f"the drop's SHA256SUMS does not name {CROPS_INDEX}")
        actual = hashlib.sha256(data).hexdigest()
        if actual != expected:
            raise BundleRefused(
                "drop_file_differs", f"{CROPS_INDEX} hashes to {actual}; the drop's SHA256SUMS says {expected}"
            )
    if not isinstance(entries, list):
        raise BundleRefused("drop_crops_index", f"{CROPS_INDEX} is not a list")
    by_slug: dict[str, set[str]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("slug"), str) or not isinstance(
            entry.get("block_id"), str
        ):
            raise BundleRefused("drop_crops_index", f"{CROPS_INDEX} holds an entry without slug and block_id")
        blocks = by_slug.setdefault(entry["slug"], set())
        if entry["block_id"] in blocks:
            raise BundleRefused("drop_crops_index", f"{CROPS_INDEX} names {entry['slug']}/{entry['block_id']} twice")
        blocks.add(entry["block_id"])
    if sums is not None:
        indexed = {f"{slug}/crops/{block_id}.pdf" for slug, blocks in by_slug.items() for block_id in blocks}
        listed = {relative for relative in sums if "/crops/" in relative and relative.endswith(".pdf")}
        if indexed != listed:
            omitted = sorted(listed - indexed)
            unsummed = sorted(indexed - listed)
            raise BundleRefused(
                "drop_crops_differ",
                f"{CROPS_INDEX} and SHA256SUMS disagree on crop PDFs "
                f"({len(omitted)} omitted, {len(unsummed)} unlisted; first omitted {omitted[:1]!r}, "
                f"first unlisted {unsummed[:1]!r})",
            )
    return {slug: tuple(sorted(blocks)) for slug, blocks in by_slug.items()}


@dataclass(frozen=True, slots=True)
class _Ledger:
    ledger: RepairLedger
    sha256: str


def _read_ledger(path: Path | None, rows: SnapshotRows, drop_sums_sha256: str) -> _Ledger | None:
    """The ``--ledger`` file, read and checked against the snapshot's counts and the sums."""
    snapshot = rows.snapshot
    if path is None:
        if snapshot.repair_count or snapshot.unreliable_count:
            raise BundleRefused(
                "ledger_required",
                f"{snapshot.content_key} carries {snapshot.repair_count} repairs and "
                f"{snapshot.unreliable_count} unreliable blocks; pass --ledger",
            )
        return None
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise BundleRefused("ledger_invalid", f"the repair ledger is unreadable: {exc.strerror or exc}") from None
    try:
        ledger, ledger_sums = read_ledger_file(data)
    except (KeyError, TypeError, ValueError) as exc:
        raise BundleRefused("ledger_invalid", f"the repair ledger is unreadable: {exc}") from None
    if ledger_sums is None:
        raise BundleRefused(
            "ledger_sums_unrecorded",
            "the repair ledger names no drop_sums_sha256, so it cannot show which SHA256SUMS "
            "its crops were checked against; write it again with `repair ledger`",
        )
    if ledger_sums != drop_sums_sha256:
        raise BundleRefused(
            "ledger_sums_differ",
            f"the repair checked its crops against SHA256SUMS {ledger_sums}; --drop-sums is "
            f"{drop_sums_sha256}",
        )
    if (len(ledger.applied), ledger.unreliable_count) != (snapshot.repair_count, snapshot.unreliable_count):
        raise BundleRefused(
            "ledger_mismatch",
            f"the ledger applies {len(ledger.applied)} and leaves {ledger.unreliable_count} "
            f"unreliable; the snapshot says {snapshot.repair_count} and {snapshot.unreliable_count}",
        )
    return _Ledger(ledger=ledger, sha256=hashlib.sha256(data).hexdigest())


def _ledger_facts(read: _Ledger | None) -> LedgerFacts | None:
    if read is None:
        return None
    ledger = read.ledger
    return LedgerFacts(
        sha256=read.sha256,
        version=ledger.version,
        base_snapshot_id=ledger.base_snapshot_id,
        applied=tuple(sorted(repair.key for repair in ledger.applied)),
        unreliable=tuple(
            sorted((repair.document_slug, repair.block_id, repair.outcome.value) for repair in ledger.unreliable)
        ),
    )


def _require_identity(
    rows: SnapshotRows,
    fingerprints: list[DocumentFingerprint],
    ledger: RepairLedger | None,
    crops: Mapping[tuple[str, str], str],
) -> None:
    """`F1`: the rows' keys are the keys the drop's text and the ledger derive, nothing else.

    ``fingerprints`` are the rows' documents with the drop's ``results.md`` bytes and save
    dates; ``crops`` maps ``(slug, block_id)`` to the SHA-256 of the crop placed in the bundle.
    """
    snapshot = rows.snapshot
    base = derive(fingerprints)
    try:
        qualified_base = with_segmentation_profile(base, snapshot.segmentation_profile)
    except ValueError as exc:
        raise BundleRefused("base_key_differs", str(exc)) from None
    derived = (qualified_base.content_key, base.drawn_from, base.drawn_to, base.undated_documents,
               base.document_count)
    stored = (snapshot.base_content_key, snapshot.drawn_from, snapshot.drawn_to,
              snapshot.undated_documents, snapshot.document_count)
    if derived != stored:
        raise BundleRefused(
            "base_key_differs",
            f"the rows' documents and the drop's results.md derive {derived!r}; the snapshot row "
            f"says {stored!r}",
        )
    effective = base
    if ledger is not None:
        try:
            effective = repaired_snapshot(base, ledger)
        except ValueError as exc:
            raise BundleRefused("ledger_mismatch", str(exc)) from None
        for repair in sorted(ledger.repairs, key=lambda item: item.key):
            bundled = crops.get(repair.key)
            if bundled is None:
                raise BundleRefused(
                    "ledger_crop_absent",
                    f"{repair.document_slug}/{repair.block_id}: the ledger names a block whose "
                    "crop this bundle does not carry",
                )
            if bundled != repair.crop_sha256:
                raise BundleRefused(
                    "ledger_crop_differs",
                    f"{repair.document_slug}/{repair.block_id}: the ledger was recognised from crop "
                    f"{repair.crop_sha256}; the bundle carries {bundled}",
                )
    qualified = with_segmentation_profile(effective, snapshot.segmentation_profile)
    if (qualified.content_key, qualified.content_digest) != (snapshot.content_key, snapshot.content_digest):
        raise BundleRefused(
            "content_key_differs",
            f"the drop and the {'ledger' if ledger is not None else 'absent ledger'} derive "
            f"{qualified.content_key} / {qualified.content_digest}; the snapshot row says "
            f"{snapshot.content_key} / {snapshot.content_digest}",
        )


class _ObjectPlacer:
    """Puts drop files into ``objects/``, once per distinct content, checked three ways."""

    def __init__(self, staging: Path, corpus: Path, sums: Mapping[str, str], *, copy: bool) -> None:
        self._staging = staging
        self._corpus = corpus
        self._sums = sums
        self._copy = copy
        self.objects: dict[str, tuple[int, list[ObjectSlot]]] = {}

    def place(self, source: Path, slot: ObjectSlot) -> str:
        """Place ``source`` for ``slot``; return the SHA-256 of the object now in the bundle."""
        relative = source.relative_to(self._corpus).as_posix()
        expected = self._sums.get(relative)
        if expected is None:
            raise BundleRefused("drop_file_unsummed", f"the drop's SHA256SUMS does not name {relative}")
        if expected in self.objects:
            self.objects[expected][1].append(slot)
            return expected
        target = self._staging / object_path(expected)
        target.parent.mkdir(parents=True, exist_ok=True)
        if self._copy:
            shutil.copyfile(source, target)
        else:
            try:
                os.link(source, target)
            except OSError as exc:
                raise BundleRefused(
                    "object_link",
                    f"{relative} cannot be hardlinked into the bundle ({exc.strerror}); the bundle "
                    "must be on the drop's filesystem, or pass --copy-objects",
                ) from None
        sha, size = sha256_file(target)
        if sha != expected:
            raise BundleRefused(
                "drop_file_differs", f"{relative} hashes to {sha}; the drop's SHA256SUMS says {expected}"
            )
        mode = target.stat().st_mode
        if mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
            os.chmod(target, mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
        self.objects[expected] = (size, [slot])
        return expected


@dataclass(frozen=True, slots=True)
class ExportResult:
    directory: Path
    manifest: Manifest
    created: bool


def write_bundle(
    source: ExportSource,
    *,
    corpus: Path,
    drop_sums: Path,
    ledger: Path | None,
    out: Path,
    copy_objects: bool = False,
) -> ExportResult:
    """Write ``<out>/<content_key>+<digest>/`` from ``source`` and the drop."""
    require_designatable_chunking(source.chunking_profile)
    rows = source.rows
    snapshot = rows.snapshot
    require_content_key(snapshot.content_key)
    sums_sha256, sums = read_drop_sums(drop_sums)
    read_ledger = _read_ledger(ledger, rows, sums_sha256)
    ledger_facts = _ledger_facts(read_ledger)
    crops = read_crops_index(corpus, sums=sums)
    out.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="incomplete-", dir=out))
    try:
        placer = _ObjectPlacer(staging, corpus, sums, copy=copy_objects)
        results: dict[str, str] = {}
        fingerprints: list[DocumentFingerprint] = []
        bundled_crops: dict[tuple[str, str], str] = {}
        for document in sorted(rows.documents, key=lambda row: row.norm_document_id):
            directory = corpus / document.slug
            if not directory.is_dir():
                raise BundleRefused("drop_document_absent", f"the drop has no directory for {document.slug}")
            text_source = read_document(directory)
            if text_source.source_document_id != document.source_document_ref:
                raise BundleRefused(
                    "drop_document_differs",
                    f"{document.slug}: blocks.json names {text_source.source_document_id!r}, the row "
                    f"{document.source_document_ref!r}",
                )
            results_relative = f"{document.slug}/results.md"
            results_sha = hashlib.sha256(text_source.results_bytes).hexdigest()
            if sums.get(results_relative) != results_sha:
                raise BundleRefused(
                    "drop_file_differs", f"{results_relative} is not the bytes the drop's SHA256SUMS names"
                )
            results[document.norm_document_id] = results_sha
            saved_on = drawn_on(text_source.markdown)
            if saved_on != document.drawn_on:
                raise BundleRefused(
                    "drop_document_differs",
                    f"{document.slug}: results.md states save date {saved_on!r}, the row "
                    f"{document.drawn_on!r}",
                )
            fingerprints.append(
                fingerprint(
                    slug=document.slug,
                    source_document_id=document.source_document_ref,
                    results_md=text_source.results_bytes,
                    drawn_on=saved_on,
                )
            )
            placer.place(
                directory / DOCUMENT_PDF,
                ObjectSlot(document.norm_document_id, "pdf", document.source_document_ref),
            )
            listed = crops.get(document.slug, ())
            present = (
                {path.stem for path in (directory / "crops").glob("*.pdf")}
                if (directory / "crops").is_dir()
                else set()
            )
            if present != set(listed):
                raise BundleRefused(
                    "drop_crops_differ",
                    f"{document.slug}: crops/ holds {len(present)} crops, {CROPS_INDEX} names "
                    f"{len(listed)}",
                )
            for block_id in listed:
                bundled_crops[(document.slug, block_id)] = placer.place(
                    crop_path(corpus, document.slug, block_id),
                    ObjectSlot(document.norm_document_id, "crop", block_id),
                )
        _require_identity(
            rows, fingerprints, None if read_ledger is None else read_ledger.ledger, bundled_crops
        )

        files: list[ManifestFile] = []
        for path in write_rows(staging, rows):
            sha, size = sha256_file(staging / path)
            files.append(ManifestFile(path=path, kind="rows", sha256=sha, size=size))

        windows = 0
        if source.build is not None and source.chunks is not None:
            digest = EmbeddingSetDigest(
                content_key=snapshot.content_key,
                chunking_profile=source.chunking_profile,
                embedding_profile=EMBEDDING_PROFILE,
            )

            def digested() -> Iterator[ChunkEmbedding]:
                for chunk in source.chunks():  # type: ignore[misc]
                    for window in chunk.windows:
                        digest.add(chunk.document_ref, chunk.chunk_ordinal, window)
                    yield chunk

            writer = BuildWriter(staging)
            for path in writer.write_all(digested()):
                sha, size = sha256_file(staging / path)
                files.append(ManifestFile(path=path, kind="build", sha256=sha, size=size))
            if (writer.chunks, writer.windows, digest.hexdigest()) != (
                source.build.chunk_count,
                source.build.window_count,
                source.build.embedding_set_sha256,
            ):
                raise BundleRefused(
                    "build_digest_unstable",
                    f"the written build is {writer.chunks} chunks / {writer.windows} windows / "
                    f"{digest.hexdigest()}; the database's is {source.build!r}",
                )
            windows = writer.windows

        for sha, (size, slots) in sorted(placer.objects.items()):
            files.append(
                ManifestFile(
                    path=object_path(sha),
                    kind="object",
                    sha256=sha,
                    size=size,
                    media_type=PDF_MEDIA_TYPE,
                    slots=tuple(sorted(slots)),
                )
            )
        slot_count = sum(len(slots) for _size, slots in placer.objects.values())
        unreliable = sum(
            1 for row in rows.paragraphs if row.text_reliability == TextReliability.UNRELIABLE.value
        )
        draft = Manifest(
            content_key=snapshot.content_key,
            min_migration_head=MIN_MIGRATION_HEAD,
            snapshot=SnapshotFacts(
                norms_snapshot_id=snapshot.norms_snapshot_id,
                base_content_key=snapshot.base_content_key,
                content_digest=snapshot.content_digest,
                segmentation_profile=snapshot.segmentation_profile,
                repair_count=snapshot.repair_count,
                unreliable_count=snapshot.unreliable_count,
            ),
            row_digest=source.row_digest,
            chunking_profile=source.chunking_profile,
            build=source.build,
            counts=Counts(
                documents=len(rows.documents),
                paragraphs=len(rows.paragraphs),
                unreliable_paragraphs=unreliable,
                chunks=source.chunk_count,
                windows=windows,
                objects=len(placer.objects),
                slots=slot_count,
            ),
            object_bytes=sum(size for size, _slots in placer.objects.values()),
            db_growth_bytes=source.norm_table_bytes + slot_count * CUSTODY_BYTES_PER_SLOT,
            db_growth_method=DB_GROWTH_METHOD,
            drop_sums_sha256=sums_sha256,
            results_md_sha256=results,
            ledger=ledger_facts,
            binding_count=slot_count,
            binding_digest="0" * 64,
            files=tuple(sorted(files, key=lambda entry: entry.path)),
        )
        manifest = dataclasses.replace(draft, binding_digest=binding_digest(draft.binding_entries()))
        validate_manifest(manifest)
        (staging / MANIFEST_NAME).write_bytes(manifest.render())
        listed = {entry.path: entry.sha256 for entry in manifest.files}
        listed[MANIFEST_NAME] = sha256_file(staging / MANIFEST_NAME)[0]
        sums_bytes = render_sums(listed)
        (staging / SUMS_NAME).write_bytes(sums_bytes)

        name = bundle_name(snapshot.content_key, sums_bytes)
        final = out / name
        if final.exists():
            if (final / SUMS_NAME).read_bytes() != sums_bytes:  # pragma: no cover - same name, same sums
                raise BundleRefused("bundle_exists", f"{final} exists with other contents")
            shutil.rmtree(staging)
            created = False
        else:
            os.rename(staging, final)
            created = True
        verify_bundle(
            final,
            only=[entry.path for entry in manifest.files if entry.kind != "object"] + [MANIFEST_NAME],
        )
        return ExportResult(directory=final, manifest=manifest, created=created)
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        raise


def export_bundle(
    session: Session,
    *,
    snapshot_id: str,
    chunking_profile: str,
    corpus: Path,
    drop_sums: Path,
    ledger: Path | None,
    out: Path,
    copy_objects: bool = False,
    without_build: bool = False,
) -> ExportResult:
    source = read_export_source(
        session, snapshot_id=snapshot_id, chunking_profile=chunking_profile, without_build=without_build
    )
    return write_bundle(
        source, corpus=corpus, drop_sums=drop_sums, ledger=ledger, out=out, copy_objects=copy_objects
    )


__all__ = [
    "CROPS_INDEX",
    "DOCUMENT_PDF",
    "ExportResult",
    "ExportSource",
    "export_bundle",
    "read_crops_index",
    "read_drop_sums",
    "read_export_source",
    "require_designatable_chunking",
    "write_bundle",
]
