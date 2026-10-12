"""`W54-BUNDLE-01` heavy cases: export from a promotion-like database, import into a
disposable stand, report, replay, conflicts and refusals -- on a real PostgreSQL and S3.

A heavy step (`W54-FREEZE-01`): run only inside the owner's window, on the lane stack
(PostgreSQL ``57170``, S3 ``60770/60771``). The module name carries ``postgres``, so the
container-free runs deselect it with ``-k "not postgres"``.

What each required item is proved by:

* §3.5's order on a disposable stand -- ``test_postgres_the_import_runs_in_order…``: the
  steps in order, every admission confirmed before the snapshot row, the snapshot row before
  every binding, the ids the promotion database minted, and the report a full match;
* **an import alone leaves the fingerprint unchanged** -- the same test, and every refusal;
* replay a no-op -- ``…_an_exact_replay…`` and ``…_after_the_objects_were_discarded…``;
* conflicts refused -- ``…_conflicts_are_refused…``;
* an unconfirmed admission keeps the bundle -- ``…_an_unconfirmed_admission…`` and
  ``…_poisoned_admissions…``;
* ``report`` matches and a tampered row fails it -- ``…_report_fails…``;
* refusals without a record, with a stale, unattested or expired one, a drifted fingerprint,
  an absent build or a ``rejected`` manifest Blob -- ``…_refusals_write_nothing``.
"""

from __future__ import annotations

import dataclasses
import shutil
from pathlib import Path

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from auditmanager.norms.bundle.copy_record import compute_fingerprint
from auditmanager.norms.bundle.errors import (
    EXIT_INCOMPLETE,
    EXIT_MISMATCH,
    EXIT_OK,
    BundleRefused,
)
from auditmanager.norms.bundle.export import read_export_source, write_bundle
from auditmanager.norms.bundle.layout import MANIFEST_NAME, verify_bundle
from auditmanager.norms.bundle.manifest import parse_manifest
from auditmanager.norms.bundle.stand import (
    STEPS,
    Stand,
    import_bundle,
    report_bundle,
    requeue_bundle,
)
from auditmanager.norms.custody import blob_id_for
from auditmanager.norms.embedding_repository import NormEmbeddingRepository
from auditmanager.norms.repository import NormsRepository
from auditmanager.shared.identity import NormsSnapshotId
from auditmanager.storage import S3BlobStore, StorageUnavailableError
from auditmanager.storage.public import (
    BlobMetadataRepository,
    declare_blob,
    parse_blob_id,
    parse_blob_role,
)
from tests.integration.norms.bundle.conftest import (
    STAND_TABLES,
    Promoted,
    open_waiver,
    write_client_rows,
)
from tests.integration.norms.bundle.support import CHUNKING_PROFILE


def _manifest(bundle: Path):
    return parse_manifest((bundle / MANIFEST_NAME).read_bytes())


def _counts(engine: Engine) -> dict[str, int]:
    with engine.connect() as connection:
        return {table: int(connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one())
                for table in STAND_TABLES}


def _import(bundle: Path, record: Path | None, stand: Stand, steps: list[str] | None = None) -> tuple[int, list[str]]:
    lines: list[str] = []
    status = import_bundle(bundle, copy_record=record, stand=stand, say=lines.append,
                           observe=None if steps is None else steps.append)
    return status, lines


def _report(bundle: Path, record: Path, stand: Stand) -> tuple[int, list[str]]:
    lines: list[str] = []
    return report_bundle(bundle, copy_record=record, stand=stand, say=lines.append), lines


def _ids(engine: Engine, snapshot_id: str) -> tuple[set[str], set[str]]:
    with engine.connect() as connection:
        documents = {str(v) for (v,) in connection.execute(
            text("SELECT norm_document_id FROM norm_document WHERE norms_snapshot_id = :s"), {"s": snapshot_id})}
        paragraphs = {str(v) for (v,) in connection.execute(
            text("SELECT norm_paragraph_id FROM norm_paragraph WHERE norms_snapshot_id = :s"), {"s": snapshot_id})}
    return documents, paragraphs


def test_postgres_the_export_carries_the_promotion_databases_digests(promoted: Promoted, promotion_engine: Engine) -> None:
    manifest = _manifest(promoted.bundle)
    verify_bundle(promoted.bundle)
    snapshot_id = NormsSnapshotId.parse(promoted.snapshot_id)
    with Session(promotion_engine) as session:
        assert manifest.row_digest == NormsRepository(session).stored_row_digest(snapshot_id)
        digest, chunks, windows = NormEmbeddingRepository(session).stored_build_digest(snapshot_id, CHUNKING_PROFILE)
    assert manifest.build is not None
    assert (manifest.build.embedding_set_sha256, manifest.counts.chunks, manifest.counts.windows) == (digest, chunks, windows)
    assert manifest.content_key == promoted.content_key and manifest.db_growth_bytes > 0


def test_postgres_the_import_runs_in_order_with_its_ids_and_leaves_the_fingerprint(
    promoted: Promoted, promotion_engine: Engine, stand: Stand, tmp_path: Path
) -> None:
    record = open_waiver(stand, tmp_path)
    before = compute_fingerprint(stand.engine)
    steps: list[str] = []
    status, lines = _import(promoted.bundle, record, stand, steps)
    assert status == EXIT_OK, lines
    assert steps == list(STEPS)
    assert "report: full match" in lines

    with stand.engine.connect() as connection:
        confirmed = connection.execute(text("SELECT max(confirmed_at), count(*) FROM norm_custody_admission "
                                            "WHERE state = 'confirmed'")).one()
        created = connection.execute(text("SELECT created_at FROM norms_snapshot WHERE norms_snapshot_id = :s"),
                                     {"s": promoted.snapshot_id}).scalar_one()
        bound = connection.execute(text("SELECT min(bound_at), count(*) FROM norm_custody_binding")).one()
    manifest = _manifest(promoted.bundle)
    assert confirmed[1] == bound[1] == manifest.counts.slots
    assert confirmed[0] <= created <= bound[0], "admissions confirmed, then rows, then bindings"
    assert _ids(stand.engine, promoted.snapshot_id) == _ids(promotion_engine, promoted.snapshot_id)

    assert compute_fingerprint(stand.engine) == before, "the import moved the client fingerprint"
    assert stand.store is not None
    for entry in manifest.files_of("object"):
        assert stand.store.inspect(parse_blob_id(blob_id_for(entry.sha256, entry.size))).sha256 == entry.sha256
    status, lines = _report(promoted.bundle, record, stand)
    assert status == EXIT_OK and lines[-1] == "report: full match", lines


def test_postgres_an_exact_replay_is_a_no_op(promoted: Promoted, stand: Stand, tmp_path: Path) -> None:
    record = open_waiver(stand, tmp_path)
    assert _import(promoted.bundle, record, stand)[0] == EXIT_OK
    counts = _counts(stand.engine)
    status, lines = _import(promoted.bundle, record, stand)
    assert status == EXIT_OK, lines
    assert _counts(stand.engine) == counts, "a replay wrote rows"
    assert any("rows: already stored" in line for line in lines)
    assert any("build: already stored" in line for line in lines)
    assert any(line.startswith("admissions: 0 new") for line in lines)


def test_postgres_a_replay_after_the_objects_were_discarded_is_a_no_op(
    promoted: Promoted, stand: Stand, tmp_path: Path
) -> None:
    record = open_waiver(stand, tmp_path)
    assert _import(promoted.bundle, record, stand)[0] == EXIT_OK
    staged = tmp_path / "staged" / promoted.bundle.name
    shutil.copytree(promoted.bundle, staged)
    shutil.rmtree(staged / "objects")
    counts = _counts(stand.engine)
    status, lines = _import(staged, record, stand)
    assert status == EXIT_OK, lines
    assert _counts(stand.engine) == counts
    assert _report(staged, record, stand)[0] == EXIT_OK


def test_postgres_discarded_objects_before_a_finished_import_are_refused(
    promoted: Promoted, stand: Stand, tmp_path: Path
) -> None:
    staged = tmp_path / "staged" / promoted.bundle.name
    shutil.copytree(promoted.bundle, staged)
    shutil.rmtree(staged / "objects")
    with pytest.raises(BundleRefused, match="objects_discarded"):
        _import(staged, open_waiver(stand, tmp_path), stand)


def _insert_snapshot(engine: Engine, promoted: Promoted, *, snapshot_id: str, content_key: str) -> None:
    rows = read_export_source_rows(promoted)
    snapshot = dataclasses.replace(rows.snapshot, norms_snapshot_id=snapshot_id, content_key=content_key,
                                   base_content_key=content_key)
    with Session(engine) as session, session.begin():
        NormsRepository(session).insert_snapshot_rows(dataclasses.replace(rows, snapshot=snapshot, documents=(),
                                                                          paragraphs=()))


def read_export_source_rows(promoted: Promoted):
    from auditmanager.norms.bundle.contents import read_rows
    return read_rows(promoted.bundle)


@pytest.mark.parametrize("conflict", ["key-under-another-id", "id-under-another-key"])
def test_postgres_conflicts_are_refused_and_write_nothing(
    promoted: Promoted, stand: Stand, tmp_path: Path, conflict: str
) -> None:
    if conflict == "key-under-another-id":
        _insert_snapshot(stand.engine, promoted, snapshot_id=str(NormsSnapshotId.new()), content_key=promoted.content_key)
    else:
        _insert_snapshot(stand.engine, promoted, snapshot_id=promoted.snapshot_id, content_key="undated+0d.ffffffffffff")
    record = open_waiver(stand, tmp_path)
    before = _counts(stand.engine)
    with pytest.raises(BundleRefused, match="snapshot_conflict"):
        _import(promoted.bundle, record, stand)
    assert _counts(stand.engine) == before
    assert before["norm_custody_admission"] == 0


class OutageStore:
    """The real store, except that staging fails as an unreachable store does."""

    def __init__(self, store: S3BlobStore) -> None:
        self._store = store

    def stage_temporary(self, *args, **kwargs):
        raise StorageUnavailableError()

    def __getattr__(self, name: str):
        return getattr(self._store, name)


def _make_due(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("UPDATE norm_custody_admission SET available_at = clock_timestamp() "
                                "WHERE state = 'pending'"))


def test_postgres_an_unconfirmed_admission_keeps_the_bundle_and_a_rerun_finishes(
    promoted: Promoted, stand: Stand, tmp_path: Path
) -> None:
    record = open_waiver(stand, tmp_path)
    failing = dataclasses.replace(stand, store=OutageStore(stand.store))  # type: ignore[arg-type]
    status, lines = _import(promoted.bundle, record, failing)
    assert status == EXIT_INCOMPLETE, lines
    assert any("the bundle is kept" in line for line in lines)
    counts = _counts(stand.engine)
    assert counts["norms_snapshot"] == 0 and counts["norm_custody_binding"] == 0
    assert counts["norm_custody_admission"] == _manifest(promoted.bundle).counts.slots
    verify_bundle(promoted.bundle)  # every byte still there

    _make_due(stand.engine)
    status, lines = _import(promoted.bundle, record, stand)
    assert status == EXIT_OK, lines


def test_postgres_poisoned_admissions_take_requeue_then_import(
    promoted: Promoted, stand: Stand, tmp_path: Path
) -> None:
    record = open_waiver(stand, tmp_path)
    failing = dataclasses.replace(stand, store=OutageStore(stand.store))  # type: ignore[arg-type]
    for _ in range(5):
        _make_due(stand.engine)
        assert _import(promoted.bundle, record, failing)[0] == EXIT_INCOMPLETE
    status, lines = _import(promoted.bundle, record, stand)
    assert status == EXIT_INCOMPLETE and any("requeue" in line for line in lines), lines
    said: list[str] = []
    assert requeue_bundle(promoted.bundle, stand=stand, say=said.append) == EXIT_OK
    assert f"requeue: {_manifest(promoted.bundle).counts.slots} poisoned" in said[0]
    status, lines = _import(promoted.bundle, record, stand)
    assert status == EXIT_OK, lines


def test_postgres_report_fails_on_a_tampered_row_and_on_a_client_write(
    promoted: Promoted, stand: Stand, tmp_path: Path
) -> None:
    record = open_waiver(stand, tmp_path)
    assert _import(promoted.bundle, record, stand)[0] == EXIT_OK
    with stand.engine.begin() as connection:
        connection.execute(text("ALTER TABLE norm_paragraph DISABLE TRIGGER USER"))
        connection.execute(text("UPDATE norm_paragraph SET text = text || ' (tampered)' WHERE ordinal = 0 "
                                "AND norms_snapshot_id = :s"), {"s": promoted.snapshot_id})
        connection.execute(text("ALTER TABLE norm_paragraph ENABLE TRIGGER USER"))
    status, lines = _report(promoted.bundle, record, stand)
    assert status == EXIT_MISMATCH
    assert any(line.startswith("row_digest: stand") and line.endswith("MISMATCH") for line in lines), lines

    write_client_rows(stand.engine)
    status, lines = _report(promoted.bundle, record, stand)
    assert status == EXIT_MISMATCH
    assert any(line.startswith("client_fingerprint: stand") for line in lines), lines


def _unbuilt_bundle(promoted: Promoted, promotion_engine: Engine, out: Path) -> Path:
    with Session(promotion_engine) as session:
        source = read_export_source(session, snapshot_id=promoted.snapshot_id, chunking_profile=CHUNKING_PROFILE)
        session.rollback()
    source = dataclasses.replace(source, build=None, chunks=None)
    return write_bundle(source, corpus=promoted.corpus, drop_sums=promoted.sums, ledger=None, out=out,
                        copy_objects=True).directory


def _reject_one_manifest_blob(stand: Stand, promoted: Promoted) -> None:
    entry = _manifest(promoted.bundle).files_of("object")[0]
    declaration = declare_blob(sha256=entry.sha256, size=entry.size, role=parse_blob_role("source_document"),
                               media_type="application/pdf")
    with Session(stand.engine) as session, session.begin():
        repository = BlobMetadataRepository()
        repository.record_declared(session, declaration)
        repository.mark_rejected(session, declaration.blob_id)


def _hold_one_manifest_blob(stand: Stand, promoted: Promoted) -> None:
    entry = _manifest(promoted.bundle).files_of("object")[0]
    with Session(stand.engine) as session, session.begin():
        BlobMetadataRepository().record_declared(
            session, declare_blob(sha256=entry.sha256, size=entry.size, role=parse_blob_role("source_document"),
                                  media_type="application/pdf"))


@pytest.mark.parametrize(
    "case, reason",
    [
        ("no-record", "copy_record_absent"),
        ("stale-record", "copy_record_closed"),
        ("unattested-copy", "copy_record_unattested"),
        ("expired-waiver", "copy_record_expired"),
        ("migrated-since", "copy_record_stale"),
        ("drifted-fingerprint", "fingerprint_drifted"),
        ("absent-build", "build_absent"),
        ("rejected-manifest-blob", "manifest_blob_rejected"),
        ("manifest-blob-held-by-a-client-row", "manifest_blob_held_outside_custody"),
    ],
)
def test_postgres_refusals_write_nothing(
    promoted: Promoted, promotion_engine: Engine, stand: Stand, tmp_path: Path, case: str, reason: str
) -> None:
    bundle = promoted.bundle
    if case == "rejected-manifest-blob":
        _reject_one_manifest_blob(stand, promoted)
    if case == "manifest-blob-held-by-a-client-row":
        _hold_one_manifest_blob(stand, promoted)
    overrides = {
        "stale-record": {"state": "closed"},
        "unattested-copy": {"kind": "copy", "attested": False},
        "expired-waiver": {"expires_offset": -1},
        "migrated-since": {"migration_head": "0018_norm_custody"},
    }.get(case, {})
    record = None if case == "no-record" else open_waiver(stand, tmp_path, **overrides)
    if case == "drifted-fingerprint":
        write_client_rows(stand.engine)
    if case == "absent-build":
        bundle = _unbuilt_bundle(promoted, promotion_engine, tmp_path / "unbuilt")
    before_counts = _counts(stand.engine)
    before_fingerprint = compute_fingerprint(stand.engine)
    with pytest.raises(BundleRefused) as refused:
        _import(bundle, record, stand)
    assert refused.value.reason == reason, refused.value
    assert _counts(stand.engine) == before_counts, "a refused import wrote rows"
    assert compute_fingerprint(stand.engine) == before_fingerprint
