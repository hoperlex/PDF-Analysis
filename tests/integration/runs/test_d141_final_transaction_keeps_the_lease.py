"""`W54-JUDGE-Y` F5: the evidence gate's S3 reads happen before the run row is locked.

``running -> validating`` locks the ``audit_run`` row until the caller's final commit. The
gate used to read its three artifacts from the store *after* that advance, so the row lock
was held for as long as the store took. The reads now run first (``_read_gate_inputs``);
the gate receives what was read and has no store to read from. `D-141`'s commit -- the text
stage made durable and the Lease released before the gate -- still precedes both.

Two halves:

* ``test_static_…`` -- container-free: the executor's source order and the gate's
  signature. Revert the fix and both assertions fail.
* ``test_a_run_reads_…`` -- HEAVY (real PostgreSQL and MinIO, the runs harness; it fails,
  never skips, without them): a real run, with every ``read_artifact`` call and every run
  transition recorded in order. No artifact read may follow the ``validating`` advance.

The lease half of `D-141` is ``tests/integration/jobs/test_d141_final_transaction_keeps_the_lease.py``.
"""

from __future__ import annotations

import ast
import inspect
from typing import Any

from sqlalchemy.orm import Session

import auditmanager.runs.executor as executor_module
from auditmanager.runs import RunRepository, execute_run, start_audit_run


def _calls_in_order(function: Any) -> list[tuple[int, str, dict[str, str]]]:
    """``(line, callee, {keyword: literal})`` for every call in ``function``'s body."""
    tree = ast.parse(inspect.getsource(function))
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            callee = ast.unparse(node.func)
            keywords = {
                keyword.arg: keyword.value.value
                for keyword in node.keywords
                if keyword.arg is not None and isinstance(keyword.value, ast.Constant)
            }
            calls.append((node.lineno, callee, keywords))
    return sorted(calls)


def test_static_the_gate_inputs_are_read_before_the_validating_advance() -> None:
    calls = _calls_in_order(executor_module._execute_run_body)
    reads = [line for line, callee, _ in calls if callee == "_read_gate_inputs"]
    advances = [line for line, callee, keywords in calls
                if callee == "run_repo.advance" and keywords.get("to_state") == "validating"]
    gates = [line for line, callee, _ in calls if callee == "_run_evidence_gate"]
    commits = [line for line, callee, _ in calls if callee == "session.commit"]
    assert len(reads) == len(advances) == len(gates) == 1, (reads, advances, gates)
    # D-141's commit after the text stage, then the reads, then the lock, then the gate.
    assert any(line < reads[0] for line in commits)
    assert reads[0] < advances[0] < gates[0]
    # The gate is handed what was read; it has no store to read from under the lock.
    parameters = inspect.signature(executor_module._run_evidence_gate).parameters
    assert "blob_store" not in parameters and "inputs" in parameters


def test_a_run_reads_no_artifact_after_the_validating_advance(
    session: Session, seeded, blob_store, recorded_adapter, provider_config, new_key, monkeypatch
) -> None:
    events: list[str] = []
    real_read = executor_module.read_artifact
    real_advance = RunRepository.advance

    def read_artifact(*args: Any, **kwargs: Any):
        events.append(f"read:{kwargs.get('expected_role')}")
        return real_read(*args, **kwargs)

    def advance(self, session, *, run_id, from_state, to_state):  # noqa: ANN001
        events.append(f"advance:{to_state}")
        return real_advance(self, session, run_id=run_id, from_state=from_state, to_state=to_state)

    monkeypatch.setattr(executor_module, "read_artifact", read_artifact)
    monkeypatch.setattr(RunRepository, "advance", advance)

    started = start_audit_run(
        session,
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded",
        idempotency_key=new_key("y-f5-gate-reads"),
    )
    result = execute_run(
        session, started.run_id, blob_store=blob_store, adapter=recorded_adapter,
        provider_config=provider_config,
    )
    assert result.terminal_state == "published" and result.gate_ran, result
    assert "advance:validating" in events, events
    validating = events.index("advance:validating")
    gate_reads = [event for event in events[:validating] if event.startswith("read:")]
    assert gate_reads, "the gate read nothing, so nothing was measured"
    assert not [event for event in events[validating:] if event.startswith("read:")], events
