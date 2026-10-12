"""`W54-BUNDLE-01`: the importer's step 5 -- the objects go after a matched report, only then.

`W54-PLAN.md` §3.5: "after `report` matches, delete the objects, keep manifest and report".
The importer's container reads the bundle through a read-only mount, so the deletion is the
inbound key's ``report`` verb, inside staging and under the import lock (report §4). It
happens exactly when that report exits 0 **and** the last import of the same bundle exited
0; it removes ``objects/`` and nothing else, and keeps the report's output.

Container-free, on `test_bundle_transport_refusals.py`'s own stage: the staged
``receive-bundle.sh`` with ``docker`` stubbed on ``PATH`` (``STUB_EXIT`` is the module's exit
status, ``STUB_STDOUT`` its output).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from tests.integration.norms.bundle.support import ROOT


def _transport_suite():
    path = ROOT / "tests/integration/composition/test_bundle_transport_refusals.py"
    spec = importlib.util.spec_from_file_location("w54_transport_suite", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


SUITE = _transport_suite()


def _staged(tmp_path: Path, *, import_exit: str | None):
    stand = SUITE._stage(tmp_path)
    key = SUITE._place(stand, SUITE._bundle(tmp_path / "made"))
    logs = stand.staging / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    if import_exit is not None:
        (logs / f"{key}.import.exit").write_text(f"{import_exit}\n")
    return stand, key, stand.staging / "bundles" / key, logs


def test_a_matched_report_after_a_successful_import_discards_only_the_objects(tmp_path: Path) -> None:
    stand, key, bundle, logs = _staged(tmp_path, import_exit="0")
    kept_before = sorted(p.relative_to(bundle).as_posix() for p in bundle.rglob("*") if p.is_file()
                         and not p.relative_to(bundle).as_posix().startswith("objects/"))
    ran = SUITE._inbound(stand, f"report {key}", env={"STUB_EXIT": "0", "STUB_STDOUT": "report: full match"})
    assert ran.code == 0, ran.err
    assert "report: full match" in ran.out
    assert not (bundle / "objects").exists()
    kept = sorted(p.relative_to(bundle).as_posix() for p in bundle.rglob("*") if p.is_file())
    assert kept == kept_before and "manifest.json" in kept and "SHA256SUMS" in kept
    assert (logs / f"{key}.report").read_text() == "report: full match\n"
    discarded = (logs / f"{key}.discarded").read_text()
    assert discarded.startswith("discarded_at=") and "report_sha256=" in discarded
    assert "removed" in ran.err
    assert stand.docker_calls() == [SUITE._fixed(stand, "report", key)]

    # A second report finds nothing left to discard and is otherwise the same report.
    again = SUITE._inbound(stand, f"report {key}", env={"STUB_EXIT": "0", "STUB_STDOUT": "report: full match"})
    assert again.code == 0 and "removed" not in again.err


@pytest.mark.parametrize(
    "import_exit, report_exit",
    [(None, "0"), ("75", "0"), ("2", "0"), ("0", "1"), ("0", "5")],
)
def test_no_matched_report_after_a_successful_import_no_discard(
    tmp_path: Path, import_exit: str | None, report_exit: str
) -> None:
    stand, key, bundle, logs = _staged(tmp_path, import_exit=import_exit)
    objects = sorted(p.read_bytes() for p in (bundle / "objects").rglob("*") if p.is_file())
    ran = SUITE._inbound(stand, f"report {key}", env={"STUB_EXIT": report_exit, "STUB_STDOUT": "a report"})
    assert ran.code == int(report_exit), "the module's exit status is not passed on"
    assert sorted(p.read_bytes() for p in (bundle / "objects").rglob("*") if p.is_file()) == objects
    assert not (logs / f"{key}.discarded").exists()
    assert (logs / f"{key}.report").read_text() == "a report\n", "the report's output is kept either way"


def test_a_report_under_a_held_import_lock_discards_nothing(tmp_path: Path) -> None:
    stand, key, bundle, _logs = _staged(tmp_path, import_exit="0")
    with SUITE._holding(stand.staging / "import.lock"):
        ran = SUITE._inbound(stand, f"report {key}", env={"STUB_EXIT": "0"})
    assert ran.refused("import-lock-free"), ran.err
    assert (bundle / "objects").is_dir()
    assert stand.docker_calls() == []
