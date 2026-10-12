"""The stand side: ``import``, ``report`` and ``requeue`` of one verified bundle.

These run one-shot, in the api image, under the inbound key's import lock and never in a
serving process (`W54-PLAN.md` §3.5). The bundle is mounted read-only at
``/bundles/<KEY>`` and the copy record at ``/run/copy-record.json``.

**The import, in §3.5's order** (each step refuses before it writes; a re-run converges):

1. *Verify*: the bundle's name, ``SHA256SUMS`` and every file; the manifest against both; a
   complete build declared; the copy record by :func:`copy_record.accept_for_import` with the
   fingerprint recomputed now; the database at the code's migration head and at least the
   manifest's ``min_migration_head``; no manifest Blob ``rejected`` (`D-143`); no snapshot
   conflict (the key under another id, the id under another key, a child id elsewhere);
   on the first run, no manifest Blob already held by a row custody does not name (the
   import would move it out of the fingerprint).
2. *Admit and dispatch*: one admission per manifest slot in one transaction, then
   ``dispatch --until-idle``. Anything still ``pending`` or ``poisoned`` exits
   :data:`EXIT_INCOMPLETE` and keeps the bundle; a ``rejected`` admission is a refusal.
3. *One transaction*: every admission confirmed, the rows inserted with their ids
   (``import_snapshot``), ``publish_bindings('norm_source', snapshot)``, the bindings equal to
   the manifest's. Exact replay is a no-op; the same key with other ids, or the same id with
   another key, is refused.
4. *The build*, by the computed chunk key, in its own transaction ending with the completion
   row; its digest must be the manifest's.
5. *Reconcile and report*: the custody reconciler point-inspects (``HEAD``) the object of
   every confirmed admission (`W54-JUDGE-A` F2), then the same comparison ``report`` prints;
   exit 0 only on a full match **and** no custody incident. Deleting the objects is the
   inbound key's ``report`` verb, after a matched report and a successful import
   (`W54-BUNDLE-01` report §4); the container cannot write the read-only mount.

``report`` is read-only. With an object store (the command line always gives it one) it runs
the same reconciler first, so the shell's discard follows a report that has just seen every
confirmed object in the store, never a database-only one. ``requeue`` returns this bundle's
``poisoned`` admissions to ``pending``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO, Final

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.shared.db import read_state
from auditmanager.shared.db.session import session_scope
from auditmanager.shared.errors import DomainError
from auditmanager.shared.identity import NormsSnapshotId
from auditmanager.storage.public import BlobStore

from ..chunking import ChunkingRefused
from ..custody import (
    NORM_SOURCE,
    Admission,
    AdmissionState,
    CustodyDispatcher,
    CustodyReconciler,
    CustodyReconciliation,
    CustodyReport,
    admit,
    publish_bindings,
    report,
    requeue,
)
from ..embedding_repository import NormEmbeddingConflict, NormEmbeddingRepository
from ..loader import import_snapshot
from ..repository import (
    NormsProjectionConflict,
    NormsRepository,
    SnapshotImportConflict,
    SnapshotRowsInvalid,
)
from ..snapshot import SnapshotRow
from .contents import iter_build, read_rows
from .copy_record import (
    CopyRecord,
    StandFingerprint,
    accept_for_import,
    check_record_shape,
    compute_fingerprint,
    read_copy_record,
)
from .errors import EXIT_INCOMPLETE, EXIT_MISMATCH, EXIT_OK, BundleRefused
from .layout import MANIFEST_NAME, object_path, verify_bundle
from .manifest import Manifest, SnapshotFacts, parse_manifest

Say = Callable[[str], None]

STEPS: Final[tuple[str, ...]] = (
    "verified", "admitted", "dispatched", "rows_and_bindings", "build", "reported",
)

_BLOB_STATES = text(
    "SELECT blob_id, state FROM blob WHERE blob_id = ANY(CAST(:ids AS text[]))"
)
_HELD_OUTSIDE_CUSTODY = text(
    "SELECT count(*) FROM blob b WHERE b.blob_id = ANY(CAST(:ids AS text[])) "
    "AND NOT EXISTS (SELECT 1 FROM norm_custody_admission a WHERE a.blob_id = b.blob_id)"
)
_BLOB_TOTALS = text(
    "SELECT count(*), coalesce(sum(size_bytes), 0), "
    "count(*) FILTER (WHERE state = 'rejected'), count(*) FILTER (WHERE state = 'available') "
    "FROM blob WHERE (blob_id = ANY(CAST(:ids AS text[]))) = :manifest"
)
_UNRELIABLE = text(
    "SELECT count(*) FROM norm_paragraph WHERE norms_snapshot_id = :snapshot "
    "AND text_reliability = 'unreliable'"
)
_BUILD_ROW = text(
    "SELECT chunk_count, window_count, embedding_set_sha256 FROM norm_embedding_build "
    "WHERE norms_snapshot_id = :snapshot AND chunking_profile = :chunking_profile "
    "AND embedding_profile = :embedding_profile"
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class Stand:
    """The stand's database (and, for ``import``, its object store) as the commands see it."""

    session_factory: sessionmaker[Session]
    engine: Engine
    store: BlobStore | None = None
    clock: Callable[[], datetime] = field(default=_utcnow)


class BundleSource:
    """``CustodySource`` over the staged bundle: an admission's bytes by their digest."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def open(self, admission: Admission) -> BinaryIO:
        return (self._directory / object_path(admission.declared_sha256)).open("rb")


def _migration_number(revision: str | None) -> int:
    head = (revision or "").split("_", 1)[0]
    if not head.isdigit():
        raise BundleRefused("database_not_migrated", f"migration revision {revision!r} has no number")
    return int(head)


def _verified_manifest(directory: Path, *, only_manifest: bool) -> tuple[Manifest, bool]:
    bundle = verify_bundle(
        directory,
        only=[MANIFEST_NAME] if only_manifest else None,
        allow_discarded_objects=True,
    )
    if MANIFEST_NAME not in bundle.sums:
        raise BundleRefused("manifest_invalid", "SHA256SUMS does not list manifest.json")
    manifest = parse_manifest((directory / MANIFEST_NAME).read_bytes())
    manifest.check_against(bundle)
    return manifest, bundle.objects_discarded


def snapshot_facts(snapshot: SnapshotRow) -> SnapshotFacts:
    """The manifest's ``snapshot`` object as the rows state it (`W54-JUDGE-Y` F2)."""
    return SnapshotFacts(
        norms_snapshot_id=snapshot.norms_snapshot_id,
        base_content_key=snapshot.base_content_key,
        content_digest=snapshot.content_digest,
        segmentation_profile=snapshot.segmentation_profile,
        repair_count=snapshot.repair_count,
        unreliable_count=snapshot.unreliable_count,
    )


def _custody(session: Session, manifest: Manifest) -> CustodyReport:
    return report(session, role=NORM_SOURCE, targets=manifest.targets)


# --- import -------------------------------------------------------------------------------


def import_bundle(
    directory: Path,
    *,
    copy_record: Path | None,
    stand: Stand,
    say: Say = print,
    observe: Callable[[str], None] | None = None,
) -> int:
    """Run §3.5's import. Returns the process exit status; raises :class:`BundleRefused`."""

    def reached(step: str) -> None:
        say(f"step: {step}")
        if observe is not None:
            observe(step)

    # 1. Verify -- everything that needs no database first.
    manifest, discarded = _verified_manifest(directory, only_manifest=False)
    if manifest.build is None:
        raise BundleRefused(
            "build_absent",
            "the manifest declares no complete embedding build; a bundle without one is "
            "refused (finish the build on the promotion database and export again)",
        )
    record = read_copy_record(copy_record)
    check_record_shape(record, now=stand.clock())
    rows = read_rows(directory)
    if rows.snapshot.norms_snapshot_id != manifest.snapshot.norms_snapshot_id or (
        rows.snapshot.content_key != manifest.content_key
    ):
        raise BundleRefused("bundle_rows_invalid", "the rows are not the manifest's snapshot")
    if rows.row_digest != manifest.row_digest:
        raise BundleRefused(
            "bundle_rows_invalid", f"the rows digest to {rows.row_digest}; the manifest says {manifest.row_digest}"
        )
    row_facts = snapshot_facts(rows.snapshot)
    if row_facts != manifest.snapshot:
        raise BundleRefused(
            "manifest_snapshot_differs",
            f"the manifest's snapshot facts {manifest.snapshot!r} are not the rows' {row_facts!r}",
        )
    say(f"bundle: {manifest.content_key} verified ({len(manifest.files)} files"
        f"{', objects already discarded' if discarded else ''})")

    state = read_state(stand.engine)
    if not state.is_at_head:
        raise BundleRefused("database_not_at_head", f"the database is {state.describe()}")
    if _migration_number(state.current) < _migration_number(manifest.min_migration_head):
        raise BundleRefused(
            "database_below_minimum",
            f"the database is at {state.current}; the bundle needs {manifest.min_migration_head}",
        )
    fingerprint = compute_fingerprint(stand.engine)
    accepted = accept_for_import(
        record, now=stand.clock(), database_head=state.current, fingerprint=fingerprint
    )
    say(f"copy record: {accepted.kind} {accepted.stamp} admits the import until "
        f"{accepted.valid_until:%Y-%m-%dT%H:%M:%SZ}; fingerprint {fingerprint.sha256} unchanged")

    snapshot_id = NormsSnapshotId.parse(manifest.snapshot.norms_snapshot_id)
    with session_scope(stand.session_factory) as session:
        blob_ids = list(manifest.blob_ids)
        rejected = sorted(
            str(blob_id)
            for blob_id, blob_state in session.execute(_BLOB_STATES, {"ids": blob_ids})
            if blob_state == "rejected"
        )
        if rejected:
            raise BundleRefused(
                "manifest_blob_rejected",
                f"{len(rejected)} manifest Blob(s) are rejected on the stand (D-143), first "
                f"{rejected[0]}; a rejected Blob has no way back, so this bundle cannot be admitted",
            )
        repository = NormsRepository(session)
        by_id = repository.snapshot_row(snapshot_id)
        by_key = repository.snapshot_row_by_key(manifest.content_key)
        if by_key is not None and by_key.norms_snapshot_id != manifest.snapshot.norms_snapshot_id:
            raise BundleRefused(
                "snapshot_conflict", f"the key {manifest.content_key} is held by {by_key.norms_snapshot_id}"
            )
        if by_id is not None and by_id.content_key != manifest.content_key:
            raise BundleRefused(
                "snapshot_conflict", f"{snapshot_id} names key {by_id.content_key!r} on the stand"
            )
        if by_id is not None and repository.stored_row_digest(snapshot_id) != manifest.row_digest:
            raise BundleRefused(
                "snapshot_conflict", f"{snapshot_id} is stored with other rows than the bundle's"
            )
        if by_id is None:
            clashes = repository.foreign_child_ids(rows)
            if clashes:
                raise BundleRefused(
                    "snapshot_conflict", f"{len(clashes)} document/paragraph id(s) belong to another snapshot, first {clashes[0]}"
                )
        custody = _custody(session, manifest)
        first_run = sum(custody.counts.values()) == 0
        if first_run:
            held = int(session.execute(_HELD_OUTSIDE_CUSTODY, {"ids": blob_ids}).scalar_one())
            if held:
                raise BundleRefused(
                    "manifest_blob_held_outside_custody",
                    f"{held} manifest Blob(s) already exist as client rows; admitting them would "
                    "move those rows out of the fingerprint. An owner decision (W54-BUNDLE-01 §4)",
                )
        if discarded and custody.count(AdmissionState.CONFIRMED) != manifest.counts.slots:
            raise BundleRefused(
                "objects_discarded",
                "the bundle's objects/ is gone but not every admission is confirmed; send the "
                "bundle again",
            )
        session.rollback()
    if stand.store is None:
        raise BundleRefused(
            "blob_store_unavailable",
            "the import has no object store: step 2 dispatches to it and step 5 reconciles "
            "custody against it",
        )
    store = stand.store
    reached("verified")

    # 2. Admit, then dispatch until idle.
    index = manifest.custody_manifest()
    admitted = replayed = 0
    with session_scope(stand.session_factory) as session:
        for request in manifest.admission_requests():
            outcome = admit(session, request, manifest=index)
            replayed += outcome.replayed
            admitted += not outcome.replayed
    say(f"admissions: {admitted} new, {replayed} already held")
    reached("admitted")
    if not discarded:
        dispatched = CustodyDispatcher(
            store, source=BundleSource(directory), session_factory=stand.session_factory
        ).dispatch(until_idle=True)
        say(f"dispatch: {len(dispatched.steps)} tries this pass")
    reached("dispatched")
    with session_scope(stand.session_factory) as session:
        custody = _custody(session, manifest)
    pending = custody.count(AdmissionState.PENDING)
    poisoned = custody.count(AdmissionState.POISONED)
    confirmed = custody.count(AdmissionState.CONFIRMED)
    say(f"admissions: confirmed {confirmed}, pending {pending}, poisoned {poisoned}, "
        f"rejected {custody.count(AdmissionState.REJECTED)}")
    if pending or poisoned:
        say("import: not finished -- the bundle is kept. Run import again later"
            + ("; poisoned admissions need requeue first" if poisoned else ""))
        return EXIT_INCOMPLETE
    if confirmed != manifest.counts.slots:
        failures = sorted({admission.last_failure or "?" for admission in custody.rejected_admissions})
        raise BundleRefused(
            "admission_rejected",
            f"{manifest.counts.slots - confirmed} slot(s) have no confirmed admission; rejected "
            f"for {failures!r}. Run import again to re-admit them, or send the bundle again",
        )

    # 3. One transaction: rows with their ids, then the bindings.
    try:
        with session_scope(stand.session_factory) as session:
            imported = import_snapshot(
                session,
                rows,
                chunking_profiles=[manifest.chunking_profile],
                expected_row_digest=manifest.row_digest,
            )
            publication = publish_bindings(session, NORM_SOURCE, manifest.targets)
            after = _custody(session, manifest)
            if (after.binding_count, after.binding_digest) != (manifest.binding_count, manifest.binding_digest):
                raise BundleRefused(
                    "bindings_differ",
                    f"the stand binds {after.binding_count} slots digesting to {after.binding_digest}; "
                    f"the manifest {manifest.binding_count} / {manifest.binding_digest}",
                )
    except SnapshotImportConflict as exc:
        raise BundleRefused("snapshot_conflict", str(exc)) from None
    except (SnapshotRowsInvalid, ChunkingRefused, NormsProjectionConflict) as exc:
        raise BundleRefused("bundle_rows_invalid", str(exc)) from None
    say(f"rows: {'inserted' if imported.created else 'already stored'} {imported.norms_snapshot_id}; "
        f"bindings: {len(publication.bound)} new, {publication.already_bound} already bound")
    reached("rows_and_bindings")

    # 4. The build, by the computed chunk key.
    try:
        with session_scope(stand.session_factory) as session:
            build = NormEmbeddingRepository(session).ensure_build(
                snapshot_id=snapshot_id,
                chunking_profile=manifest.chunking_profile,
                chunks=iter_build(directory, [entry.path for entry in manifest.files_of("build")]),
            )
            expected = manifest.build
            if (build.embedding_set_sha256, build.chunk_count, build.window_count) != (
                expected.embedding_set_sha256,
                expected.chunk_count,
                expected.window_count,
            ):
                raise BundleRefused(
                    "build_differs",
                    f"the stand's build is {build.embedding_set_sha256} ({build.chunk_count} chunks, "
                    f"{build.window_count} windows); the manifest's {expected!r}",
                )
    except NormEmbeddingConflict as exc:
        raise BundleRefused("build_conflict", str(exc)) from None
    say(f"build: {'loaded' if build.created else 'already stored'} {build.embedding_set_sha256}")
    reached("build")

    # 5. The reconciler, then the report, decide.
    status = report_bundle(directory, copy_record=copy_record, stand=stand, say=say)
    reached("reported")
    return status


# --- report -------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Comparison:
    name: str
    stand: object
    expected: object
    #: ``False`` for a figure ``report`` prints but does not compare (client data).
    compared: bool = True

    @property
    def matches(self) -> bool:
        return not self.compared or self.stand == self.expected

    def render(self) -> str:
        if not self.compared:
            return f"{self.name}: {self.stand}"
        if self.matches:
            return f"{self.name}: {self.stand} match"
        return f"{self.name}: stand {self.stand} expected {self.expected} MISMATCH"


def compare_stand(
    session: Session, manifest: Manifest, record: CopyRecord, fingerprint: StandFingerprint
) -> list[Comparison]:
    """Every figure ``report`` prints, with what the manifest and the record expect."""
    snapshot_id = NormsSnapshotId.parse(manifest.snapshot.norms_snapshot_id)
    repository = NormsRepository(session)
    stored = repository.snapshot_row(snapshot_id)
    out: list[Comparison] = [
        Comparison("content_key", None if stored is None else stored.content_key, manifest.content_key)
    ]
    absent = "absent"
    if stored is None:
        out += [
            Comparison(name, absent, value)
            for name, value in (
                ("row_digest", manifest.row_digest),
                ("documents", manifest.counts.documents),
                ("paragraphs", manifest.counts.paragraphs),
                ("unreliable_paragraphs", manifest.counts.unreliable_paragraphs),
                ("chunks", manifest.counts.chunks),
            )
        ]
    else:
        out.append(Comparison("row_digest", repository.stored_row_digest(snapshot_id), manifest.row_digest))
        try:
            counts = repository.counts(snapshot_id, manifest.chunking_profile)
            documents, paragraphs, chunks = counts.documents, counts.paragraphs, counts.chunks
        except NormsProjectionConflict:
            documents = paragraphs = chunks = absent  # type: ignore[assignment]
        out += [
            Comparison("documents", documents, manifest.counts.documents),
            Comparison("paragraphs", paragraphs, manifest.counts.paragraphs),
            Comparison(
                "unreliable_paragraphs",
                int(session.execute(_UNRELIABLE, {"snapshot": str(snapshot_id)}).scalar_one()),
                manifest.counts.unreliable_paragraphs,
            ),
            Comparison("chunks", chunks, manifest.counts.chunks),
        ]
    expected_build = manifest.build
    build_row = session.execute(
        _BUILD_ROW,
        {
            "snapshot": str(snapshot_id),
            "chunking_profile": manifest.chunking_profile,
            "embedding_profile": expected_build.embedding_profile if expected_build else "",
        },
    ).one_or_none()
    if stored is None or build_row is None or expected_build is None:
        out += [
            Comparison("windows", absent, manifest.counts.windows),
            Comparison("build_digest", absent, None if expected_build is None else expected_build.embedding_set_sha256),
        ]
    else:
        digest, _chunks, windows = NormEmbeddingRepository(session).stored_build_digest(
            snapshot_id, manifest.chunking_profile, expected_build.embedding_profile
        )
        recorded = str(build_row.embedding_set_sha256)
        out += [
            Comparison("windows", windows, manifest.counts.windows),
            Comparison("build_digest", digest if digest == recorded else f"{digest} (row {recorded})",
                       expected_build.embedding_set_sha256),
        ]
    custody = _custody(session, manifest)
    out += [
        Comparison("admissions_confirmed", custody.count(AdmissionState.CONFIRMED), manifest.counts.slots),
        Comparison("admissions_pending", custody.count(AdmissionState.PENDING), 0),
        Comparison("admissions_poisoned", custody.count(AdmissionState.POISONED), 0),
        Comparison("bindings", custody.binding_count, manifest.binding_count),
        Comparison("binding_digest", custody.binding_digest, manifest.binding_digest),
    ]
    ids = list(manifest.blob_ids)
    count, size, rejected, available = session.execute(_BLOB_TOTALS, {"ids": ids, "manifest": True}).one()
    out += [
        Comparison("manifest_blobs", int(count), manifest.counts.objects),
        Comparison("manifest_blob_bytes", int(size), manifest.object_bytes),
        Comparison("manifest_blobs_available", int(available), manifest.counts.objects),
        Comparison("manifest_blobs_rejected", int(rejected), 0),
    ]
    count, size, rejected, _available = session.execute(_BLOB_TOTALS, {"ids": ids, "manifest": False}).one()
    out.append(Comparison("other_blobs_rejected", int(rejected), record.get("rejected_blob_count")))
    out.append(Comparison("copy_record_open", record.get("state") == "open", True))
    recorded_tables = record.fingerprint_tables()
    for name in sorted(set(fingerprint.tables) | set(recorded_tables)):
        here = fingerprint.tables.get(name)
        there = recorded_tables.get(name)
        out.append(
            Comparison(
                f"client_rows[{name}]",
                None if here is None else (here.rows, here.sha256[:12]),
                None if there is None else (there.rows, str(there.sha256)[:12]),
            )
        )
    out.append(Comparison("client_fingerprint", fingerprint.sha256, record.fingerprint_sha256))
    # Printed, not compared: the stand's other Blobs are client data.
    out.append(Comparison("other_blobs", f"{int(count)} rows, {int(size)} bytes", None, compared=False))
    return out


def reconcile_custody(stand: Stand, say: Say = print) -> list[Comparison]:
    """`W54-JUDGE-A` F2: the custody reconciler over every confirmed admission. Read-only.

    Every incident is printed and makes the report a mismatch, so the shell's discard of
    ``objects/`` (which needs exit 0) stays closed while any confirmed object is missing or
    differs. The scope is all of custody, not this bundle: an integrity incident anywhere
    is a reason not to throw away the bytes that could repair it.
    """
    if stand.store is None:
        raise BundleRefused("blob_store_unavailable", "custody cannot be reconciled without the object store")
    result: CustodyReconciliation = CustodyReconciler(
        stand.store, session_factory=stand.session_factory
    ).reconcile()
    for incident in result.incidents:
        say(f"custody incident: {incident.kind.value} admission {incident.admission_id} "
            f"blob {incident.blob_id}")
    return [
        Comparison("custody_objects_checked", result.checked_blobs, None, compared=False),
        Comparison("custody_incidents", len(result.incidents), 0),
        Comparison("custody_redrive_due", len(result.redrive_due), None, compared=False),
    ]


def report_bundle(directory: Path, *, copy_record: Path | None, stand: Stand, say: Say = print) -> int:
    """``report``: read-only. Exit 0 only when every figure matches and, with a store, no
    custody incident is found."""
    manifest, discarded = _verified_manifest(directory, only_manifest=True)
    record = read_copy_record(copy_record)
    fingerprint = compute_fingerprint(stand.engine)
    custody = [] if stand.store is None else reconcile_custody(stand, say)
    session = stand.session_factory()
    try:
        comparisons = compare_stand(session, manifest, record, fingerprint) + custody
    finally:
        session.rollback()
        session.close()
    say(f"report: {manifest.content_key} ({'objects discarded' if discarded else 'objects staged'}"
        f"{'' if stand.store is not None else '; custody not reconciled: no object store'})")
    for comparison in comparisons:
        say(comparison.render())
    mismatched = [comparison.name for comparison in comparisons if not comparison.matches]
    if mismatched:
        say(f"report: {len(mismatched)} MISMATCH ({', '.join(mismatched[:8])})")
        return EXIT_MISMATCH
    say("report: full match")
    return EXIT_OK


# --- requeue ------------------------------------------------------------------------------


def requeue_bundle(directory: Path, *, stand: Stand, say: Say = print) -> int:
    """Custody ``requeue`` of this bundle's ``poisoned`` admissions."""
    manifest, _discarded = _verified_manifest(directory, only_manifest=True)
    try:
        with session_scope(stand.session_factory) as session:
            poisoned = [admission.admission_id for admission in _custody(session, manifest).poisoned]
            requeued = requeue(session, poisoned) if poisoned else ()
    except DomainError as exc:
        raise BundleRefused("requeue_refused", str(exc)) from None
    say(f"requeue: {len(requeued)} poisoned admission(s) of {manifest.content_key} returned to pending")
    return EXIT_OK


__all__ = [
    "STEPS",
    "BundleSource",
    "Comparison",
    "Stand",
    "compare_stand",
    "import_bundle",
    "reconcile_custody",
    "snapshot_facts",
    "report_bundle",
    "requeue_bundle",
]
