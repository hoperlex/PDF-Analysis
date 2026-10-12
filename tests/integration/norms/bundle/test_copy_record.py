"""`W54-BUNDLE-01`: the importer's acceptance rule for the copy record, and the fingerprint.

Container-free. Three kinds of evidence:

* **one SQL text** -- :data:`FINGERPRINT_SCRIPT` is byte for byte ``copy-serve.sh``'s block,
  and the digest over its output is ``fc_fingerprint_json``'s;
* **the rule** -- every accepted shape and every refusal (`W54-FREEZE-01` amendment 2,
  `W54-STAND-COPY-01` §3.8) on records in the boundary's canonical layout;
* **parity with the writer** -- records the real ``copy-serve.sh`` writes (its own suite's
  stage, ``docker`` stubbed) are the records this rule accepts.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from auditmanager.norms.bundle.copy_record import (
    FINGERPRINT_SCRIPT,
    IMPORT_WINDOW,
    StandFingerprint,
    accept_for_import,
    check_record_shape,
    read_copy_record,
)
from auditmanager.norms.bundle.errors import BundleRefused
from tests.integration.norms.bundle.support import (
    COPY_SERVE,
    ROOT,
    bash_lib,
    fingerprint_document,
    record_fields,
    record_text,
)

LINES = [f"{table}|{rows}|{str(index) * 64}" for index, (table, rows) in enumerate(
    (("alembic_version", 1), ("app_user", 2), ("audit_event", 7), ("blob", 3), ("project", 1)), start=1
)]
FINGERPRINT = StandFingerprint.from_lines(LINES)
HEAD = "0019_execution_workers"


def _now() -> datetime:
    return datetime.now(UTC)


def test_the_fingerprint_script_is_copy_serves_block_byte_for_byte() -> None:
    serve = COPY_SERVE.read_text(encoding="utf-8")
    start = serve.index("-- >>> stand-fingerprint-v1\n")
    end = serve.index("-- <<< stand-fingerprint-v1\n") + len("-- <<< stand-fingerprint-v1\n")
    assert FINGERPRINT_SCRIPT == serve[start:end]


def test_the_fingerprint_digest_is_the_shells() -> None:
    ran = bash_lib('fc_fingerprint_json "$1"', "\n".join(LINES))
    assert ran.returncode == 0, ran.stderr
    shell = json.loads(ran.stdout)
    assert shell == fingerprint_document(FINGERPRINT)


def test_a_fingerprint_line_out_of_shape_or_order_is_refused() -> None:
    for lines in ([], [LINES[1], LINES[0]], ["App|1|" + "0" * 64], [LINES[0], LINES[0]]):
        with pytest.raises(BundleRefused, match="fingerprint_unreadable"):
            StandFingerprint.from_lines(lines)


def _record(tmp_path: Path, **overrides) -> Path:
    fingerprint = overrides.pop("fingerprint", fingerprint_document(FINGERPRINT))
    fields = record_fields(fingerprint=fingerprint, migration_head=HEAD, **overrides)
    path = tmp_path / "record.json"
    path.write_text(record_text(fields), encoding="utf-8")
    return path


def _accept(path: Path, *, fingerprint: StandFingerprint = FINGERPRINT, head: str = HEAD, now=None):
    return accept_for_import(
        read_copy_record(path), now=now or _now(), database_head=head, fingerprint=fingerprint
    )


def test_an_open_unexpired_waiver_with_the_same_fingerprint_is_accepted(tmp_path: Path) -> None:
    accepted = _accept(_record(tmp_path))
    assert accepted.kind == "test_data_waiver" and accepted.fingerprint_sha256 == FINGERPRINT.sha256


def test_an_attested_copy_inside_its_window_is_accepted(tmp_path: Path) -> None:
    accepted = _accept(_record(tmp_path, kind="copy", quiesced_offset=-3600))
    assert accepted.kind == "copy"
    assert accepted.valid_until - _now() < IMPORT_WINDOW - timedelta(minutes=59)


@pytest.mark.parametrize(
    "overrides, reason",
    [
        ({"state": "closed"}, "copy_record_closed"),
        ({"purpose": "publish"}, "copy_record_not_import"),
        ({"purpose": "none"}, "copy_record_not_import"),
        ({"kind": "copy", "attested": False}, "copy_record_unattested"),
        ({"kind": "test_data_waiver", "attested": False}, "copy_record_unattested"),
        ({"kind": "copy", "quiesced_offset": -43201}, "copy_record_expired"),
        ({"expires_offset": -1}, "copy_record_expired"),
        ({"real_data_marker": True}, "waiver_after_real_data"),
        ({"kind": "something"}, "copy_record_unreadable"),
        ({"fingerprint": {"algorithm": "other", "sha256": "f" * 64, "tables": {}}}, "copy_record_unreadable"),
    ],
)
def test_a_record_that_does_not_admit_this_import_is_refused(tmp_path: Path, overrides: dict, reason: str) -> None:
    with pytest.raises(BundleRefused) as refused:
        _accept(_record(tmp_path, **overrides))
    assert refused.value.reason == reason, refused.value


def test_a_copy_whose_attestation_names_another_dump_is_refused(tmp_path: Path) -> None:
    path = _record(tmp_path, kind="copy")
    fields = json.loads(path.read_text())
    fields["attestation"]["dump_sha256"] = "0" * 64
    path.write_text(record_text(fields))
    with pytest.raises(BundleRefused, match="copy_record_unattested"):
        _accept(path)


def test_a_waiver_carrying_a_dump_is_refused(tmp_path: Path) -> None:
    path = _record(tmp_path)
    fields = json.loads(path.read_text())
    fields["dump"] = {"file": "db.dump", "size_bytes": 1, "sha256": "d" * 64}
    path.write_text(record_text(fields))
    with pytest.raises(BundleRefused, match="copy_record_unreadable"):
        _accept(path)


def test_writers_not_recorded_stopped_are_refused(tmp_path: Path) -> None:
    path = _record(tmp_path)
    fields = json.loads(path.read_text())
    fields["writers_stopped"] = ["web"]
    path.write_text(record_text(fields))
    with pytest.raises(BundleRefused, match="copy_record_not_quiesced"):
        _accept(path)


def test_a_drifted_fingerprint_is_refused_and_names_the_table(tmp_path: Path) -> None:
    drifted = StandFingerprint.from_lines([line.replace("app_user|2|", "app_user|3|") for line in LINES])
    with pytest.raises(BundleRefused, match="fingerprint_drifted") as refused:
        _accept(_record(tmp_path), fingerprint=drifted)
    assert "app_user" in refused.value.message


def test_a_record_the_stand_migrated_past_is_stale(tmp_path: Path) -> None:
    with pytest.raises(BundleRefused, match="copy_record_stale"):
        _accept(_record(tmp_path), head="0020_something_later")


def test_no_record_an_empty_directory_or_garbage_is_refused(tmp_path: Path) -> None:
    with pytest.raises(BundleRefused, match="copy_record_absent"):
        read_copy_record(tmp_path / "absent.json")
    with pytest.raises(BundleRefused, match="copy_record_absent"):
        read_copy_record(None)
    (tmp_path / "dir.json").mkdir()  # D-37: a missing bind-mount source arrives as a directory
    with pytest.raises(BundleRefused, match="copy_record_absent"):
        read_copy_record(tmp_path / "dir.json")
    (tmp_path / "garbage.json").write_text("{not json")
    with pytest.raises(BundleRefused, match="copy_record_unreadable"):
        read_copy_record(tmp_path / "garbage.json")
    (tmp_path / "v2.json").write_text(json.dumps({"record_version": 2}))
    with pytest.raises(BundleRefused, match="copy_record_version"):
        read_copy_record(tmp_path / "v2.json")


def test_the_shape_rules_need_no_database(tmp_path: Path) -> None:
    until = check_record_shape(read_copy_record(_record(tmp_path, expires_offset=600)), now=_now())
    assert timedelta(minutes=9) < until - _now() <= timedelta(minutes=10)


# --- parity with the records copy-serve.sh writes ----------------------------------------


def _stand_copy_suite():
    path = ROOT / "tests/integration/composition/test_stand_copy_refusals.py"
    spec = importlib.util.spec_from_file_location("w54_stand_copy_suite", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _written_fingerprint(suite) -> StandFingerprint:
    return StandFingerprint.from_lines(suite.FINGERPRINT.splitlines())


def test_the_waiver_copy_serve_writes_is_accepted_and_refused_once_closed(tmp_path: Path) -> None:
    suite = _stand_copy_suite()
    stand = suite._stage(tmp_path)
    stamp = suite._waiver(stand)
    record = read_copy_record(stand.record)
    accepted = accept_for_import(
        record, now=_now(), database_head=record.get("migration_head"), fingerprint=_written_fingerprint(suite)
    )
    assert accepted.kind == "test_data_waiver" and accepted.stamp == stamp
    assert suite._copy_key(stand, f"resume {stamp}").code == 0
    with pytest.raises(BundleRefused, match="copy_record_closed"):
        accept_for_import(
            read_copy_record(stand.record), now=_now(), database_head=record.get("migration_head"),
            fingerprint=_written_fingerprint(suite),
        )


def test_the_attested_copy_copy_serve_writes_is_accepted_and_expires(tmp_path: Path) -> None:
    suite = _stand_copy_suite()
    stand = suite._stage(tmp_path)
    stamp = suite._attested(stand, "import")
    record = read_copy_record(stand.record)
    head = record.get("migration_head")
    accepted = accept_for_import(record, now=_now(), database_head=head, fingerprint=_written_fingerprint(suite))
    assert accepted.kind == "copy" and accepted.stamp == stamp
    with pytest.raises(BundleRefused, match="copy_record_expired"):
        accept_for_import(record, now=_now() + IMPORT_WINDOW, database_head=head,
                          fingerprint=_written_fingerprint(suite))
    with pytest.raises(BundleRefused, match="fingerprint_drifted"):
        accept_for_import(record, now=_now(), database_head=head,
                          fingerprint=StandFingerprint.from_lines(suite.OTHER_FINGERPRINT.splitlines()))


def test_an_unattested_copy_copy_serve_writes_is_refused(tmp_path: Path) -> None:
    suite = _stand_copy_suite()
    stand = suite._stage(tmp_path)
    suite._inventoried(stand)
    record = read_copy_record(stand.record)
    with pytest.raises(BundleRefused, match="copy_record_not_import|copy_record_unattested"):
        accept_for_import(record, now=_now(), database_head=record.get("migration_head"),
                          fingerprint=_written_fingerprint(suite))
