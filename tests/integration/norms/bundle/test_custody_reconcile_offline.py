"""`W54-FIX-PY`: ``report`` reconciles custody before the discard; storage failures refuse.

`W54-JUDGE-A` F2: the custody reconciler had no caller, and the inbound key discards
``objects/`` after a report that exits 0 -- a database-only comparison. Now ``report`` (and
so the import's step 5) runs the reconciler whenever it has the object store, which the
command line always gives it, and any incident makes the report a mismatch.

`W54-JUDGE-A` F5: a ``StorageError`` (an unreadable configuration, a missing bucket, an
outage) left the command line as a traceback and exit 1 -- the report-mismatch status. It is
now ``EXIT_REFUSED`` with the reason ``blob_store_unavailable``.

Container-free: the database figures of ``compare_stand`` and the fingerprint are replaced
here; ``test_bundle_postgres.py`` runs the reconciler against PostgreSQL and S3.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import auditmanager.norms.bundle.stand as stand_module
from auditmanager.norms.bundle.cli import main
from auditmanager.norms.bundle.copy_record import StandFingerprint
from auditmanager.norms.bundle.errors import EXIT_MISMATCH, EXIT_OK, EXIT_REFUSED
from auditmanager.norms.bundle.export import write_bundle
from auditmanager.norms.bundle.stand import Stand, report_bundle
from auditmanager.norms.custody import CustodyIncident, CustodyReconciliation, IncidentKind
from auditmanager.storage import StorageConfigurationError, StorageUnavailableError
from auditmanager.storage.public import StorageError
from tests.integration.norms.bundle.support import record_fields, record_text, synthetic_rows, write_drop
from tests.integration.norms.bundle.test_export_offline import _source


class _Session:
    def rollback(self) -> None:
        return None

    def close(self) -> None:
        return None


class _Store:
    """Never reached: the reconciler is replaced, so a store call would be a bug here."""

    def __getattr__(self, name: str):
        raise AssertionError(f"the store was reached ({name})")


@pytest.fixture
def bundle(tmp_path: Path) -> Path:
    corpus, sums = write_drop(tmp_path / "drop")
    return write_bundle(
        _source(synthetic_rows()), corpus=corpus, drop_sums=sums, ledger=None, out=tmp_path / "out"
    ).directory


@pytest.fixture
def record(tmp_path: Path) -> Path:
    path = tmp_path / "record.json"
    path.write_text(record_text(record_fields()), encoding="utf-8")
    return path


@pytest.fixture
def offline(monkeypatch: pytest.MonkeyPatch) -> list[CustodyReconciliation]:
    """The stand's database figures all match; the reconciler returns what the test queues."""
    results: list[CustodyReconciliation] = []
    calls: list[object] = []

    class Reconciler:
        def __init__(self, store, *, session_factory=None) -> None:
            calls.append(store)

        def reconcile(self) -> CustodyReconciliation:
            return results.pop(0)

    monkeypatch.setattr(stand_module, "CustodyReconciler", Reconciler)
    monkeypatch.setattr(stand_module, "compute_fingerprint",
                        lambda _engine: StandFingerprint(sha256="f" * 64, tables={}))
    monkeypatch.setattr(stand_module, "compare_stand", lambda *_args: [])
    return results


def _stand(store: object | None) -> Stand:
    return Stand(session_factory=_Session, engine=object(), store=store)  # type: ignore[arg-type]


def test_report_with_a_store_fails_on_a_custody_incident(bundle: Path, record: Path, offline) -> None:
    incident = CustodyIncident(IncidentKind.OBJECT_MISSING, "nad_1", "nbd_1", "blob_1")
    offline.append(CustodyReconciliation(incidents=(incident,), redrive_due=(), checked_blobs=4))
    lines: list[str] = []
    assert report_bundle(bundle, copy_record=record, stand=_stand(_Store()), say=lines.append) == EXIT_MISMATCH
    assert "custody incident: object_missing admission nad_1 blob blob_1" in lines
    assert "custody_incidents: stand 1 expected 0 MISMATCH" in lines
    assert lines[-1].startswith("report: 1 MISMATCH (custody_incidents")


def test_report_with_a_store_and_no_incident_is_a_full_match(bundle: Path, record: Path, offline) -> None:
    offline.append(CustodyReconciliation(incidents=(), redrive_due=(), checked_blobs=4))
    lines: list[str] = []
    assert report_bundle(bundle, copy_record=record, stand=_stand(_Store()), say=lines.append) == EXIT_OK
    assert "custody_incidents: 0 match" in lines and lines[-1] == "report: full match"
    assert offline == [], "the reconciler did not run"


def test_report_without_a_store_says_custody_was_not_reconciled(bundle: Path, record: Path, offline) -> None:
    lines: list[str] = []
    assert report_bundle(bundle, copy_record=record, stand=_stand(None), say=lines.append) == EXIT_OK
    assert any("custody not reconciled: no object store" in line for line in lines)


def test_the_report_command_opens_the_object_store(bundle: Path, record: Path, offline) -> None:
    """The shell discards ``objects/`` after this command exits 0, so it must reconcile."""
    offline.append(CustodyReconciliation(incidents=(), redrive_due=(), checked_blobs=4))
    asked: list[bool] = []

    def factory(with_store: bool) -> Stand:
        asked.append(with_store)
        return _stand(_Store() if with_store else None)

    assert main(["report", str(bundle), "--copy-record", str(record)], stand_factory=factory) == EXIT_OK
    assert asked == [True]


@pytest.mark.parametrize(
    "error",
    [StorageConfigurationError(field="S3_BUCKET", constraint="required"), StorageUnavailableError()],
    ids=["settings", "outage"],
)
@pytest.mark.parametrize("command", ["import", "report"])
def test_a_storage_failure_is_a_named_refusal_not_a_mismatch(
    bundle: Path, record: Path, capsys, error: StorageError, command: str
) -> None:
    def factory(_with_store: bool) -> Stand:
        raise error

    status = main([command, str(bundle), "--copy-record", str(record)], stand_factory=factory)
    assert status == EXIT_REFUSED != EXIT_MISMATCH
    err = capsys.readouterr().err
    assert err.startswith("bundle: REFUSED [blob_store_unavailable]: ") and "Traceback" not in err


def test_a_storage_failure_inside_the_reconciler_is_a_refusal(
    bundle: Path, record: Path, offline, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    def failing(_stand, _say):
        raise StorageUnavailableError()

    monkeypatch.setattr(stand_module, "reconcile_custody", failing)
    status = main(["report", str(bundle), "--copy-record", str(record)],
                  stand_factory=lambda with_store: _stand(_Store() if with_store else None))
    assert status == EXIT_REFUSED
    assert "REFUSED [blob_store_unavailable]" in capsys.readouterr().err

