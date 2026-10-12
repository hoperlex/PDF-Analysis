"""The bundle manifest, ``manifest.json``, format ``auditmanager-norm-bundle/1``.

The plan's field list (§3.5) made concrete. One JSON object, rendered canonically (sorted
keys, one-space indent, ASCII with ``\\u`` escapes, a final newline), so the same bundle is
the same bytes on every export::

    manifest_version     1
    format               "auditmanager-norm-bundle/1"
    content_key          the snapshot's key, also the bundle name's first part
    min_migration_head   the oldest migration whose schema holds every row the import writes
    snapshot             the snapshot row's identity facts (id, base key, content digest,
                         segmentation profile, repair and unreliable counts)
    row_digest           {"version": "norm-snapshot-rows/1", "sha256": ...} over ids, text
                         and text_reliability (``snapshot.row_digest``)
    chunking_profile     the chunk profile the import derives and the build is over
    build                {"embedding_profile", "digest_version", "embedding_set_sha256",
                          "chunk_count", "window_count"} -- or null: a bundle without a
                         complete build, which the importer refuses
    counts               documents, paragraphs, unreliable_paragraphs, chunks, windows,
                         objects (distinct files) and slots (custody admissions)
    object_bytes         the bytes of the distinct objects
    db_growth_bytes      measured on the promotion database (``db_growth_method``)
    drop                 {"sums_sha256": the operator's drop SHA256SUMS, "results_md_sha256":
                          {norm_document_id: SHA-256 of that document's results.md}}
    ledger               null, or the repair ledger's SHA-256, version, base snapshot and its
                         applied and unreliable entries
    custody              {"role", "binding_count", "binding_digest"} as ``report`` computes
                         them from the stand's bindings
    files                every file but manifest.json and SHA256SUMS: path, kind
                         (rows | build | object), sha256, size, and for an object its media
                         type and the custody slots (target, anchor kind, anchor) it serves

An object is named by its bytes (``objects/<2 hex>/<sha256>.pdf``); equal bytes at two
anchors are one file with two slots and become one Blob with two bindings (`R-76`).
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

from ..custody import (
    NORM_SOURCE,
    ROLE_SHAPES,
    AdmissionRequest,
    BindingDigestEntry,
    CustodySlot,
    DeclaredContent,
    ManifestIndex,
    binding_digest,
    blob_id_for,
)
from ..embedding.digest import EMBEDDING_SET_DIGEST_VERSION
from ..embedding.profile import EMBEDDING_PROFILE
from ..snapshot import ROW_DIGEST_VERSION
from .errors import BundleRefused
from .layout import (
    MANIFEST_NAME,
    OBJECTS_DIR,
    SUMS_NAME,
    VerifiedBundle,
    object_path,
    require_bundle_path,
    require_content_key,
)

MANIFEST_FORMAT: Final[str] = "auditmanager-norm-bundle/1"
MANIFEST_VERSION: Final[int] = 1
#: `0018_norm_custody` adds the custody tables, ``text_reliability`` and
#: ``unreliable_count``; every older table the import writes is older than it.
MIN_MIGRATION_HEAD: Final[str] = "0018_norm_custody"
PDF_MEDIA_TYPE: Final[str] = "application/pdf"
FILE_KINDS: Final[frozenset[str]] = frozenset({"rows", "build", "object"})
ANCHOR_KINDS: Final[frozenset[str]] = ROLE_SHAPES[NORM_SOURCE].anchor_kinds


def _refuse(message: str) -> BundleRefused:
    return BundleRefused("manifest_invalid", message)


@dataclass(frozen=True, slots=True, order=True)
class ObjectSlot:
    """One custody slot an object serves: a norm document and an opaque anchor."""

    target_id: str
    anchor_kind: str
    anchor: str


@dataclass(frozen=True, slots=True)
class ManifestFile:
    path: str
    kind: str
    sha256: str
    size: int
    media_type: str | None = None
    slots: tuple[ObjectSlot, ...] = ()


@dataclass(frozen=True, slots=True)
class BuildFacts:
    embedding_profile: str
    digest_version: str
    embedding_set_sha256: str
    chunk_count: int
    window_count: int


@dataclass(frozen=True, slots=True)
class Counts:
    documents: int
    paragraphs: int
    unreliable_paragraphs: int
    chunks: int
    windows: int
    objects: int
    slots: int


@dataclass(frozen=True, slots=True)
class LedgerFacts:
    sha256: str
    version: str
    base_snapshot_id: str
    #: ``[document_slug, block_id]`` of every applied repair, sorted.
    applied: tuple[tuple[str, str], ...]
    #: ``[document_slug, block_id, outcome]`` of every block that did not end ``REPAIRED``.
    unreliable: tuple[tuple[str, str, str], ...]


@dataclass(frozen=True, slots=True)
class SnapshotFacts:
    norms_snapshot_id: str
    base_content_key: str
    content_digest: str
    segmentation_profile: str
    repair_count: int
    unreliable_count: int


@dataclass(frozen=True, slots=True)
class Manifest:
    content_key: str
    min_migration_head: str
    snapshot: SnapshotFacts
    row_digest: str
    chunking_profile: str
    build: BuildFacts | None
    counts: Counts
    object_bytes: int
    db_growth_bytes: int
    db_growth_method: str
    drop_sums_sha256: str
    results_md_sha256: Mapping[str, str]
    ledger: LedgerFacts | None
    binding_count: int
    binding_digest: str
    files: tuple[ManifestFile, ...]

    # --- derived views --------------------------------------------------------------

    def files_of(self, kind: str) -> tuple[ManifestFile, ...]:
        return tuple(entry for entry in self.files if entry.kind == kind)

    @property
    def targets(self) -> tuple[str, ...]:
        """Every norm document the bundle's custody slots bind to, sorted."""
        return tuple(sorted({slot.target_id for entry in self.files_of("object") for slot in entry.slots}))

    def slots(self) -> Iterator[tuple[CustodySlot, DeclaredContent]]:
        shape = ROLE_SHAPES[NORM_SOURCE]
        for entry in self.files_of("object"):
            content = DeclaredContent(
                sha256=entry.sha256, size=entry.size, media_type=entry.media_type or ""
            )
            for slot in entry.slots:
                yield (
                    CustodySlot(
                        role=NORM_SOURCE,
                        target_kind=shape.target_kind,
                        target_id=slot.target_id,
                        anchor_kind=slot.anchor_kind,
                        anchor=slot.anchor,
                    ),
                    content,
                )

    def custody_manifest(self) -> ManifestIndex:
        """The verified manifest as custody reads it (``CustodyManifest``)."""
        return ManifestIndex(entries=dict(self.slots()))

    def admission_requests(self) -> tuple[AdmissionRequest, ...]:
        return tuple(
            AdmissionRequest(
                role=slot.role,
                target_id=slot.target_id,
                anchor_kind=slot.anchor_kind,
                anchor=slot.anchor,
                sha256=content.sha256,
                size=content.size,
                media_type=content.media_type,
            )
            for slot, content in sorted(
                self.slots(), key=lambda item: (item[0].target_id, item[0].anchor_kind, item[0].anchor)
            )
        )

    def binding_entries(self) -> tuple[BindingDigestEntry, ...]:
        return tuple(
            BindingDigestEntry(
                role=slot.role,
                target_kind=slot.target_kind,
                target_id=slot.target_id,
                blob_id=blob_id_for(content.sha256, content.size),
                anchor_kind=slot.anchor_kind,
                anchor=slot.anchor,
            )
            for slot, content in self.slots()
        )

    @property
    def blob_ids(self) -> tuple[str, ...]:
        return tuple(sorted({blob_id_for(entry.sha256, entry.size) for entry in self.files_of("object")}))

    def object_for(self, sha256: str) -> ManifestFile | None:
        for entry in self.files_of("object"):
            if entry.sha256 == sha256:
                return entry
        return None

    # --- the files against the verified tree -------------------------------------------

    def check_against(self, bundle: VerifiedBundle) -> None:
        """The manifest names exactly the files ``SHA256SUMS`` lists, with their digests."""
        if bundle.content_key != self.content_key:
            raise _refuse(
                f"the manifest's content key {self.content_key!r} is not the bundle name's "
                f"{bundle.content_key!r}"
            )
        listed = dict(bundle.sums)
        listed.pop(MANIFEST_NAME, None)
        named = {entry.path: entry for entry in self.files}
        if set(listed) != set(named):
            missing = sorted(set(named) - set(listed))
            extra = sorted(set(listed) - set(named))
            raise _refuse(f"SHA256SUMS and the manifest disagree (missing {missing[:3]!r}, extra {extra[:3]!r})")
        for path, entry in named.items():
            if listed[path] != entry.sha256:
                raise _refuse(f"{path}: the manifest says {entry.sha256}, SHA256SUMS {listed[path]}")
            size = bundle.sizes.get(path)
            if size is not None and size != entry.size:
                raise _refuse(f"{path}: the manifest says {entry.size} bytes, the file has {size}")

    # --- rendering --------------------------------------------------------------------

    def as_document(self) -> dict[str, Any]:
        return {
            "manifest_version": MANIFEST_VERSION,
            "format": MANIFEST_FORMAT,
            "content_key": self.content_key,
            "min_migration_head": self.min_migration_head,
            "snapshot": {
                "norms_snapshot_id": self.snapshot.norms_snapshot_id,
                "base_content_key": self.snapshot.base_content_key,
                "content_digest": self.snapshot.content_digest,
                "segmentation_profile": self.snapshot.segmentation_profile,
                "repair_count": self.snapshot.repair_count,
                "unreliable_count": self.snapshot.unreliable_count,
            },
            "row_digest": {"version": ROW_DIGEST_VERSION, "sha256": self.row_digest},
            "chunking_profile": self.chunking_profile,
            "build": None
            if self.build is None
            else {
                "embedding_profile": self.build.embedding_profile,
                "digest_version": self.build.digest_version,
                "embedding_set_sha256": self.build.embedding_set_sha256,
                "chunk_count": self.build.chunk_count,
                "window_count": self.build.window_count,
            },
            "counts": {
                "documents": self.counts.documents,
                "paragraphs": self.counts.paragraphs,
                "unreliable_paragraphs": self.counts.unreliable_paragraphs,
                "chunks": self.counts.chunks,
                "windows": self.counts.windows,
                "objects": self.counts.objects,
                "slots": self.counts.slots,
            },
            "object_bytes": self.object_bytes,
            "db_growth_bytes": self.db_growth_bytes,
            "db_growth_method": self.db_growth_method,
            "drop": {
                "sums_sha256": self.drop_sums_sha256,
                "results_md_sha256": dict(sorted(self.results_md_sha256.items())),
            },
            "ledger": None
            if self.ledger is None
            else {
                "sha256": self.ledger.sha256,
                "version": self.ledger.version,
                "base_snapshot_id": self.ledger.base_snapshot_id,
                "applied": [list(item) for item in self.ledger.applied],
                "unreliable": [list(item) for item in self.ledger.unreliable],
            },
            "custody": {
                "role": NORM_SOURCE,
                "binding_count": self.binding_count,
                "binding_digest": self.binding_digest,
            },
            "files": [_file_document(entry) for entry in sorted(self.files, key=lambda e: e.path)],
        }

    def render(self) -> bytes:
        return (
            json.dumps(self.as_document(), sort_keys=True, indent=1, ensure_ascii=True) + "\n"
        ).encode("ascii")


def _file_document(entry: ManifestFile) -> dict[str, Any]:
    document: dict[str, Any] = {
        "path": entry.path,
        "kind": entry.kind,
        "sha256": entry.sha256,
        "size": entry.size,
    }
    if entry.kind == "object":
        document["media_type"] = entry.media_type
        document["slots"] = [
            {"target_id": slot.target_id, "anchor_kind": slot.anchor_kind, "anchor": slot.anchor}
            for slot in sorted(entry.slots)
        ]
    return document


# --- parsing --------------------------------------------------------------------------


def _object(value: Any, keys: Sequence[str], where: str, *, optional: Sequence[str] = ()) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _refuse(f"{where} is not an object")
    present = set(value)
    required = set(keys) - set(optional)
    if not required <= present or not present <= set(keys):
        raise _refuse(
            f"{where} has keys {sorted(present)!r}; expected {sorted(keys)!r}"
        )
    return value


def _str(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value:
        raise _refuse(f"{where} is not non-empty text")
    return value


def _int(value: Any, where: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise _refuse(f"{where} is not a non-negative integer")
    return value


def _sha(value: Any, where: str) -> str:
    text = _str(value, where)
    if len(text) != 64 or any(c not in "0123456789abcdef" for c in text):
        raise _refuse(f"{where} is not a SHA-256")
    return text


_TOP = (
    "manifest_version", "format", "content_key", "min_migration_head", "snapshot", "row_digest",
    "chunking_profile", "build", "counts", "object_bytes", "db_growth_bytes", "db_growth_method",
    "drop", "ledger", "custody", "files",
)


def parse_manifest(data: bytes) -> Manifest:
    """Parse and validate ``manifest.json``; every inconsistency is a refusal."""
    try:
        document = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _refuse(f"manifest.json is not JSON: {exc}") from None
    top = _object(document, _TOP, "the manifest")
    if top["manifest_version"] != MANIFEST_VERSION or top["format"] != MANIFEST_FORMAT:
        raise _refuse(
            f"manifest version {top['manifest_version']!r} / format {top['format']!r} is not "
            f"{MANIFEST_VERSION} / {MANIFEST_FORMAT}"
        )
    content_key = require_content_key(_str(top["content_key"], "content_key"))
    snapshot = _object(
        top["snapshot"],
        ("norms_snapshot_id", "base_content_key", "content_digest", "segmentation_profile",
         "repair_count", "unreliable_count"),
        "snapshot",
    )
    row = _object(top["row_digest"], ("version", "sha256"), "row_digest")
    if row["version"] != ROW_DIGEST_VERSION:
        raise _refuse(f"row digest version {row['version']!r} is not {ROW_DIGEST_VERSION}")
    build: BuildFacts | None = None
    if top["build"] is not None:
        raw = _object(
            top["build"],
            ("embedding_profile", "digest_version", "embedding_set_sha256", "chunk_count", "window_count"),
            "build",
        )
        if raw["embedding_profile"] != EMBEDDING_PROFILE or raw["digest_version"] != EMBEDDING_SET_DIGEST_VERSION:
            raise _refuse(
                f"build {raw['embedding_profile']!r} / {raw['digest_version']!r} is not "
                f"{EMBEDDING_PROFILE} / {EMBEDDING_SET_DIGEST_VERSION}"
            )
        build = BuildFacts(
            embedding_profile=raw["embedding_profile"],
            digest_version=raw["digest_version"],
            embedding_set_sha256=_sha(raw["embedding_set_sha256"], "build.embedding_set_sha256"),
            chunk_count=_int(raw["chunk_count"], "build.chunk_count"),
            window_count=_int(raw["window_count"], "build.window_count"),
        )
    counts_raw = _object(
        top["counts"],
        ("documents", "paragraphs", "unreliable_paragraphs", "chunks", "windows", "objects", "slots"),
        "counts",
    )
    counts = Counts(**{name: _int(value, f"counts.{name}") for name, value in counts_raw.items()})
    drop = _object(top["drop"], ("sums_sha256", "results_md_sha256"), "drop")
    results = drop["results_md_sha256"]
    if not isinstance(results, dict):
        raise _refuse("drop.results_md_sha256 is not an object")
    ledger: LedgerFacts | None = None
    if top["ledger"] is not None:
        raw_ledger = _object(
            top["ledger"], ("sha256", "version", "base_snapshot_id", "applied", "unreliable"), "ledger"
        )
        applied = raw_ledger["applied"]
        unreliable = raw_ledger["unreliable"]
        if not isinstance(applied, list) or not all(
            isinstance(item, list) and len(item) == 2 and all(isinstance(v, str) for v in item)
            for item in applied
        ):
            raise _refuse("ledger.applied is not a list of [document_slug, block_id]")
        if not isinstance(unreliable, list) or not all(
            isinstance(item, list) and len(item) == 3 and all(isinstance(v, str) for v in item)
            for item in unreliable
        ):
            raise _refuse("ledger.unreliable is not a list of [document_slug, block_id, outcome]")
        ledger = LedgerFacts(
            sha256=_sha(raw_ledger["sha256"], "ledger.sha256"),
            version=_str(raw_ledger["version"], "ledger.version"),
            base_snapshot_id=_str(raw_ledger["base_snapshot_id"], "ledger.base_snapshot_id"),
            applied=tuple((a, b) for a, b in applied),
            unreliable=tuple((a, b, c) for a, b, c in unreliable),
        )
    custody = _object(top["custody"], ("role", "binding_count", "binding_digest"), "custody")
    if custody["role"] != NORM_SOURCE:
        raise _refuse(f"custody role {custody['role']!r} is not {NORM_SOURCE}")
    if not isinstance(top["files"], list):
        raise _refuse("files is not a list")
    files = tuple(_parse_file(item, index) for index, item in enumerate(top["files"]))
    manifest = Manifest(
        content_key=content_key,
        min_migration_head=_str(top["min_migration_head"], "min_migration_head"),
        snapshot=SnapshotFacts(
            norms_snapshot_id=_str(snapshot["norms_snapshot_id"], "snapshot.norms_snapshot_id"),
            base_content_key=_str(snapshot["base_content_key"], "snapshot.base_content_key"),
            content_digest=_str(snapshot["content_digest"], "snapshot.content_digest"),
            segmentation_profile=_str(snapshot["segmentation_profile"], "snapshot.segmentation_profile"),
            repair_count=_int(snapshot["repair_count"], "snapshot.repair_count"),
            unreliable_count=_int(snapshot["unreliable_count"], "snapshot.unreliable_count"),
        ),
        row_digest=_sha(row["sha256"], "row_digest.sha256"),
        chunking_profile=_str(top["chunking_profile"], "chunking_profile"),
        build=build,
        counts=counts,
        object_bytes=_int(top["object_bytes"], "object_bytes"),
        db_growth_bytes=_int(top["db_growth_bytes"], "db_growth_bytes"),
        db_growth_method=_str(top["db_growth_method"], "db_growth_method"),
        drop_sums_sha256=_sha(drop["sums_sha256"], "drop.sums_sha256"),
        results_md_sha256={
            _str(key, "drop.results_md_sha256 key"): _sha(value, f"drop.results_md_sha256[{key}]")
            for key, value in results.items()
        },
        ledger=ledger,
        binding_count=_int(custody["binding_count"], "custody.binding_count"),
        binding_digest=_sha(custody["binding_digest"], "custody.binding_digest"),
        files=files,
    )
    validate_manifest(manifest)
    return manifest


def _parse_file(item: Any, index: int) -> ManifestFile:
    where = f"files[{index}]"
    if not isinstance(item, dict):
        raise _refuse(f"{where} is not an object")
    kind = item.get("kind")
    if kind == "object":
        raw = _object(item, ("path", "kind", "sha256", "size", "media_type", "slots"), where)
        if not isinstance(raw["slots"], list) or not raw["slots"]:
            raise _refuse(f"{where}.slots is not a non-empty list")
        slots = tuple(
            ObjectSlot(
                target_id=_str(slot["target_id"], f"{where}.slots.target_id"),
                anchor_kind=_str(slot["anchor_kind"], f"{where}.slots.anchor_kind"),
                anchor=_str(slot["anchor"], f"{where}.slots.anchor"),
            )
            for slot in (
                _object(value, ("target_id", "anchor_kind", "anchor"), f"{where}.slots")
                for value in raw["slots"]
            )
        )
        return ManifestFile(
            path=_str(raw["path"], f"{where}.path"),
            kind=kind,
            sha256=_sha(raw["sha256"], f"{where}.sha256"),
            size=_int(raw["size"], f"{where}.size"),
            media_type=_str(raw["media_type"], f"{where}.media_type"),
            slots=slots,
        )
    raw = _object(item, ("path", "kind", "sha256", "size"), where)
    if kind not in FILE_KINDS:
        raise _refuse(f"{where}.kind {kind!r} is not one of {sorted(FILE_KINDS)}")
    return ManifestFile(
        path=_str(raw["path"], f"{where}.path"),
        kind=kind,
        sha256=_sha(raw["sha256"], f"{where}.sha256"),
        size=_int(raw["size"], f"{where}.size"),
    )


def validate_manifest(manifest: Manifest) -> None:
    """The manifest's internal arithmetic: what it says about itself must add up."""
    require_content_key(manifest.content_key)
    paths = [entry.path for entry in manifest.files]
    if len(set(paths)) != len(paths):
        raise _refuse("files names one path twice")
    for entry in manifest.files:
        require_bundle_path(entry.path)
        if entry.path in (MANIFEST_NAME, SUMS_NAME):
            raise _refuse(f"files names {entry.path}")
        if entry.kind == "object":
            if entry.path != object_path(entry.sha256):
                raise _refuse(f"{entry.path} is not the content-addressed path of its bytes")
            if entry.media_type != PDF_MEDIA_TYPE:
                raise _refuse(f"{entry.path}: media type {entry.media_type!r} is not {PDF_MEDIA_TYPE}")
        elif entry.path.startswith(f"{OBJECTS_DIR}/"):
            raise _refuse(f"{entry.path} is under objects/ but is not an object")
    shape = ROLE_SHAPES[NORM_SOURCE]
    pattern = shape.target_pattern()
    seen: set[ObjectSlot] = set()
    for entry in manifest.files_of("object"):
        for slot in entry.slots:
            if not pattern.fullmatch(slot.target_id):
                raise _refuse(f"slot target {slot.target_id!r} is not a norm document id")
            if slot.anchor_kind not in ANCHOR_KINDS or not 1 <= len(slot.anchor) <= 500:
                raise _refuse(f"slot anchor {slot.anchor_kind}/{slot.anchor!r} is not a custody anchor")
            if slot in seen:
                raise _refuse(f"slot {slot!r} is served by two objects")
            seen.add(slot)
    objects = manifest.files_of("object")
    if manifest.counts.objects != len(objects):
        raise _refuse(f"counts.objects is {manifest.counts.objects}; files holds {len(objects)} objects")
    if manifest.counts.slots != len(seen) or manifest.binding_count != len(seen):
        raise _refuse(
            f"counts.slots {manifest.counts.slots} and custody.binding_count "
            f"{manifest.binding_count} must both equal the {len(seen)} slots"
        )
    if manifest.object_bytes != sum(entry.size for entry in objects):
        raise _refuse("object_bytes is not the sum of the objects' sizes")
    if binding_digest(manifest.binding_entries()) != manifest.binding_digest:
        raise _refuse("custody.binding_digest is not the digest of the manifest's slots")
    targets = set(manifest.targets)
    if targets and len(targets) != manifest.counts.documents:
        raise _refuse(
            f"the slots bind {len(targets)} documents; counts.documents is {manifest.counts.documents}"
        )
    if set(manifest.results_md_sha256) != targets:
        raise _refuse("drop.results_md_sha256 does not name exactly the bound documents")
    build_files = manifest.files_of("build")
    if manifest.build is None:
        if build_files:
            raise _refuse("build is null but build files are listed")
    else:
        if not build_files:
            raise _refuse("build is declared but no build file is listed")
        if (manifest.build.chunk_count, manifest.build.window_count) != (
            manifest.counts.chunks,
            manifest.counts.windows,
        ):
            raise _refuse("the build's chunk and window counts are not counts.chunks/windows")
    if not manifest.files_of("rows"):
        raise _refuse("no rows file is listed")
    if manifest.ledger is not None:
        if len(manifest.ledger.applied) != manifest.snapshot.repair_count:
            raise _refuse("the ledger's applied entries are not the snapshot's repair_count")
        if len(manifest.ledger.unreliable) != manifest.snapshot.unreliable_count:
            raise _refuse("the ledger's unreliable entries are not the snapshot's unreliable_count")
    elif manifest.snapshot.repair_count or manifest.snapshot.unreliable_count:
        raise _refuse("a repaired or unreliable snapshot carries its ledger")


__all__ = [
    "ANCHOR_KINDS",
    "MANIFEST_FORMAT",
    "MANIFEST_VERSION",
    "MIN_MIGRATION_HEAD",
    "PDF_MEDIA_TYPE",
    "BuildFacts",
    "Counts",
    "LedgerFacts",
    "Manifest",
    "ManifestFile",
    "ObjectSlot",
    "SnapshotFacts",
    "parse_manifest",
    "validate_manifest",
]
