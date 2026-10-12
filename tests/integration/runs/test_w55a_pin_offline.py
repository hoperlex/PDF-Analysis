"""`W55A-PIN-01`, container-free: new runs and re-audits pin the current norms snapshot.

Plan `W55-PLAN.md` section A3.3 (R-82, R-113, CD-6). What is proved here without a
database:

* the input basis is byte-for-byte the digest every run stored before W55 (a literal
  captured from the base ``08259ba``), and a NULL run's stored digest equals it;
* a pinned run's stored digest is the basis document plus ``norms_snapshot_id`` and
  differs from its basis;
* ``start_run_fingerprint`` over the basis is the fingerprint a pre-W55 ``command_record``
  holds (a literal captured from the base), so such a key replays;
* ``start_audit_run`` and ``reaudit_run`` pin what the reader answers, read it only after
  the ledger accepted the key, and hand the ledger a fingerprint the snapshot cannot move;
* the re-audit no longer carries the source's snapshot over;
* ``_run_status_view`` carries the pin into ``RunStatus``.

The repositories are fakes recording what they were handed. What PostgreSQL does with the
rows -- the reader's SQL, the foreign key, a replay across committed designations -- is in
``test_w55a_pin_window.py``.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.ingest.public import CommandReplay, CommandStarted, payload_fingerprint
from auditmanager.runs import commands as commands_module
from auditmanager.runs.commands import (
    current_norms_snapshot,
    frozen_input_digest,
    input_basis_digest,
    reaudit_run,
    start_audit_run,
    start_run_fingerprint,
)
from auditmanager.runs.scope import UNEVALUATED_GUARDS
from auditmanager.shared.identity import CommandId

VERSION = "ver_01M2545JSD15ETSNNV904X991J"
PROFILE = "ap_01M2545JSD15ETSNNV904X991A"
BUNDLE = "pb_01M2545JSD15ETSNNV904X991P"
BLOB = "blob_sha256_" + "ab" * 32
SNAPSHOT = "ns_01M2545JSD15ETSNNV904X991N"
OTHER_SNAPSHOT = "ns_01M2545JSD15ETSNNV904X992N"
SOURCE_RUN = "run_01M2545JSD15ETSNNV904X991K"
PROJECT = "prj_01M2545JSD15ETSNNV904X991F"
COMMAND = "cmd_01M2545JSD15ETSNNV904X991C"

BASIS_INPUTS: dict[str, Any] = {
    "version_uid": VERSION,
    "blob_ids": {"source.document": BLOB},
    "analysis_profile_id": PROFILE,
    "prompt_bundle_id": BUNDLE,
}

#: ``frozen_input_digest(**BASIS_INPUTS)`` on the base ``08259ba``, before this lane: the
#: value every pre-W55 run with these inputs stored. Captured, not derived.
PRE_W55_DIGEST = "edb5162bab84b32ec352ffa4785cc7ab02625c7b92a88c78bec5ccdca2a8c031"
#: ``start_run_fingerprint(..., provider_mode="recorded", frozen_input_digest_value=
#: PRE_W55_DIGEST)`` on the base: what a pre-W55 ``command_record`` holds for this request.
PRE_W55_FINGERPRINT = "62bde5d8d311ce2d73c60ed4c870c7ff03602ff6b540c2bf2ec2e5074fb7f061"
#: The stored digest of the same inputs pinned to ``SNAPSHOT``.
PINNED_DIGEST = "a4c42d6d2e1b74bdf5fb437e6167f09cd5cce4722fb0c30d8d6f497b2fafd77d"


def _independent_digest(document: dict[str, Any]) -> str:
    """The canonical serialization restated here, so the literal is not self-confirming."""
    payload = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# --- the two digests and the fingerprint ---------------------------------------------------


def test_the_basis_is_the_pre_w55_digest_byte_for_byte() -> None:
    assert input_basis_digest(**BASIS_INPUTS) == PRE_W55_DIGEST


def test_a_null_run_stores_its_basis() -> None:
    stored = frozen_input_digest(**BASIS_INPUTS, norms_snapshot_id=None)
    assert stored == input_basis_digest(**BASIS_INPUTS) == PRE_W55_DIGEST


def test_a_pinned_run_stores_the_basis_plus_its_snapshot() -> None:
    stored = frozen_input_digest(**BASIS_INPUTS, norms_snapshot_id=SNAPSHOT)
    assert stored != input_basis_digest(**BASIS_INPUTS)
    assert stored == PINNED_DIGEST == _independent_digest(
        {
            "analysis_profile_id": PROFILE,
            "blob_ids": {"source.document": BLOB},
            "norms_snapshot_id": SNAPSHOT,
            "prompt_bundle_id": BUNDLE,
            "version_uid": VERSION,
        }
    )
    assert stored != frozen_input_digest(**BASIS_INPUTS, norms_snapshot_id=OTHER_SNAPSHOT)


def test_the_stored_digest_has_no_default_snapshot() -> None:
    """A caller that forgot the pin must not silently store a digest claiming none."""
    with pytest.raises(TypeError):
        frozen_input_digest(**BASIS_INPUTS)  # type: ignore[call-arg]


def test_the_fingerprint_over_the_basis_is_the_pre_w55_fingerprint() -> None:
    fingerprint = start_run_fingerprint(
        version_uid=VERSION, analysis_profile_id=PROFILE, prompt_bundle_id=BUNDLE,
        provider_mode="recorded", input_basis_digest_value=input_basis_digest(**BASIS_INPUTS),
    )
    assert str(fingerprint) == PRE_W55_FINGERPRINT
    assert str(fingerprint) == str(payload_fingerprint({
        "analysis_profile_id": PROFILE,
        "frozen_input_digest": PRE_W55_DIGEST,
        "prompt_bundle_id": BUNDLE,
        "provider_mode": "recorded",
        "version_uid": VERSION,
    }))


# --- fakes ------------------------------------------------------------------------------


class _Ledger:
    """``CommandRepository``: records each fingerprint; replays a key it has seen."""

    def __init__(self, replay_run: str | None = None) -> None:
        self.fingerprints: list[str] = []
        self.succeeded: list[dict[str, Any]] = []
        self._replay_run = replay_run

    def begin(self, session: Any, *, command_type: str, idempotency_key: Any,
              fingerprint: Any) -> Any:
        self.fingerprints.append(str(fingerprint))
        if self._replay_run is not None:
            return CommandReplay(CommandId(COMMAND), {"run_id": self._replay_run})
        return CommandStarted(CommandId(COMMAND))

    def succeed(self, session: Any, command_id: Any, outcome: dict[str, Any]) -> None:
        self.succeeded.append(dict(outcome))


class _Runs:
    """``RunRepository``: records ``create``; ``get`` answers the source run."""

    def __init__(self, source: Any = None) -> None:
        self.created: list[dict[str, Any]] = []
        self._source = source

    def create(self, session: Any, **row: Any) -> None:
        self.created.append(row)

    def get(self, session: Any, run_id: str) -> Any:
        assert self._source is not None and run_id == self._source.run_id
        return self._source

    def advance(self, session: Any, **_: Any) -> None:
        return None


class _Documents:
    def get_version(self, session: Any, version_uid: Any) -> Any:
        assert str(version_uid) == VERSION
        return SimpleNamespace(
            project_uid=PROJECT,
            manifest=(SimpleNamespace(role="source.document", blob_id=BLOB),),
        )


class _Jobs:
    def enqueue(self, session: Any, *, run_id: str) -> None:
        return None


class _Session:
    """Answers the re-audit's two raw statements: the row lock and the busy check."""

    def execute(self, statement: Any, parameters: Any = None) -> Any:
        return SimpleNamespace(scalar_one_or_none=lambda: None)


class _Reader:
    def __init__(self, answer: str | None) -> None:
        self.answer = answer
        self.calls = 0

    def __call__(self, session: Any) -> str | None:
        self.calls += 1
        return self.answer


def _start(reader: _Reader, ledger: _Ledger, runs: _Runs) -> Any:
    return start_audit_run(
        _Session(), version_uid=VERSION, analysis_profile_id=PROFILE,
        prompt_bundle_id=BUNDLE, provider_mode="recorded", idempotency_key="pin-offline-1",
        commands=ledger, runs=runs, documents=_Documents(), norms_snapshot=reader,
    )


# --- startRun --------------------------------------------------------------------------------


def test_a_new_run_pins_the_current_snapshot() -> None:
    runs = _Runs()
    _start(_Reader(SNAPSHOT), _Ledger(), runs)
    (row,) = runs.created
    assert row["norms_snapshot_id"] == SNAPSHOT
    assert row["frozen_input_digest"] == PINNED_DIGEST


def test_a_new_run_pins_null_while_none_is_current_and_stores_its_basis() -> None:
    runs = _Runs()
    _start(_Reader(None), _Ledger(), runs)
    (row,) = runs.created
    assert row["norms_snapshot_id"] is None
    assert row["frozen_input_digest"] == PRE_W55_DIGEST


def test_the_start_fingerprint_does_not_move_with_the_snapshot() -> None:
    """The same request before and after a designation is one payload, so it replays."""
    ledger = _Ledger()
    for answer in (None, SNAPSHOT, OTHER_SNAPSHOT):
        _start(_Reader(answer), ledger, _Runs())
    assert ledger.fingerprints == [PRE_W55_FINGERPRINT] * 3


def test_a_replayed_start_reads_no_snapshot_and_creates_nothing() -> None:
    reader, runs = _Reader(SNAPSHOT), _Runs()
    started = _start(reader, _Ledger(replay_run=SOURCE_RUN), runs)
    assert started.replayed is True and started.run_id == SOURCE_RUN
    assert reader.calls == 0 and runs.created == []


# --- reauditRun ------------------------------------------------------------------------------


def _source(snapshot: str | None) -> Any:
    return SimpleNamespace(
        run_id=SOURCE_RUN, project_uid=PROJECT, version_uid=VERSION, state="failed",
        frozen_input_digest="c" * 64, norms_snapshot_id=snapshot,
    )


def _reaudit(reader: _Reader, ledger: _Ledger, runs: _Runs) -> Any:
    return reaudit_run(
        _Session(), source_run_id=SOURCE_RUN, roles=frozenset({"expert"}),
        idempotency_key="pin-offline-reaudit", analysis_profile_id=PROFILE,
        prompt_bundle_id=BUNDLE, provider_mode="recorded", runs=runs, jobs=_Jobs(),
        commands=ledger, documents=_Documents(), norms_snapshot=reader,
    )


@pytest.mark.parametrize("source_snapshot", [None, OTHER_SNAPSHOT])
def test_a_reaudit_pins_the_current_snapshot_not_the_sources(source_snapshot) -> None:
    runs = _Runs(_source(source_snapshot))
    _reaudit(_Reader(SNAPSHOT), _Ledger(), runs)
    (row,) = runs.created
    assert row["norms_snapshot_id"] == SNAPSHOT
    assert row["frozen_input_digest"] == PINNED_DIGEST


def test_a_reaudit_pins_null_while_none_is_current_whatever_the_source_pinned() -> None:
    runs = _Runs(_source(OTHER_SNAPSHOT))
    _reaudit(_Reader(None), _Ledger(), runs)
    (row,) = runs.created
    assert row["norms_snapshot_id"] is None
    assert row["frozen_input_digest"] == PRE_W55_DIGEST


def test_the_reaudit_fingerprint_is_the_source_and_never_the_snapshot() -> None:
    ledger = _Ledger()
    for answer in (None, SNAPSHOT, OTHER_SNAPSHOT):
        _reaudit(_Reader(answer), ledger, _Runs(_source(None)))
    expected = str(payload_fingerprint({
        "reaudit_of_run_id": SOURCE_RUN, "frozen_input_digest": "c" * 64,
    }))
    assert ledger.fingerprints == [expected] * 3


def test_a_replayed_reaudit_reads_no_snapshot() -> None:
    reader, runs = _Reader(SNAPSHOT), _Runs(_source(None))
    started = _reaudit(reader, _Ledger(replay_run="run_01M2545JSD15ETSNNV904X993K"), runs)
    assert started.replayed is True
    assert reader.calls == 0 and runs.created == []


# --- the default reader ----------------------------------------------------------------------


def test_the_default_reader_is_norms_public_current_snapshot(monkeypatch) -> None:
    import inspect

    for command in (start_audit_run, reaudit_run):
        default = inspect.signature(command).parameters["norms_snapshot"].default
        assert default is current_norms_snapshot, command.__name__

    seen: list[Any] = []

    def none_current(session: Any) -> None:
        seen.append(session)
        return None

    monkeypatch.setattr(commands_module, "current_snapshot", none_current)
    marker = object()
    assert current_norms_snapshot(marker) is None  # type: ignore[arg-type]
    monkeypatch.setattr(
        commands_module, "current_snapshot",
        lambda session: SimpleNamespace(norms_snapshot_id=SNAPSHOT),
    )
    assert current_norms_snapshot(marker) == SNAPSHOT  # type: ignore[arg-type]
    assert seen == [marker]

    # Unpatched, the name is the norms context's public reader, not a copy of it.
    from auditmanager.norms import public as norms_public

    monkeypatch.undo()
    assert commands_module.current_snapshot is norms_public.current_snapshot


# --- RunStatus -------------------------------------------------------------------------------


@pytest.mark.parametrize("pinned", [None, SNAPSHOT])
def test_the_run_status_view_carries_the_pin(monkeypatch, pinned) -> None:
    import auditmanager.findings as findings
    import auditmanager.runs as runs_package
    from auditmanager.api.schemas.runs import run_status_body
    from auditmanager.bootstrap.adapters import _run_status_view

    row = SimpleNamespace(
        run_id="run_01M2545JSD15ETSNNV904X993K", project_uid=PROJECT, version_uid=VERSION,
        state="queued", provider_mode="recorded",
        created_at=datetime(2026, 10, 12, tzinfo=timezone.utc),
        analysis_profile_id=PROFILE, prompt_bundle_id=BUNDLE, degradation_set=(),
        terminal_reason=None, terminal_detail=None, interrupted_reason=None,
        terminal_at=None, reaudit_of_run_id=None, norms_snapshot_id=pinned,
    )

    class _Repository:
        def get(self, session: Any, run_id: str) -> Any:
            return row

        def stage_results(self, session: Any, run_id: str) -> tuple[()]:
            return ()

        def cost(self, session: Any, run_id: str) -> None:
            return None

    monkeypatch.setattr(runs_package, "RunRepository", _Repository)
    monkeypatch.setattr(findings, "published_finding_count", lambda session, run_id: 0)
    monkeypatch.setattr(findings, "diagnostics", lambda session, run_id: ())

    view = _run_status_view(None, row.run_id)  # type: ignore[arg-type]
    assert view.norms_snapshot_id == pinned
    body = run_status_body(view)
    if pinned is None:
        assert "norms_snapshot_id" not in body
    else:
        assert body["norms_snapshot_id"] == pinned


# --- the scope note --------------------------------------------------------------------------


def test_the_scope_note_no_longer_says_no_snapshot_is_pinned() -> None:
    (clause,) = [g for g in UNEVALUATED_GUARDS if "NormsSnapshot" in g.clause]
    assert "pins no norms snapshot" not in clause.reason
    assert "NULL pin" in clause.reason and "W57" in clause.reason
