"""A chain that halts at its first stage, and the two rules that get it to a terminal.

Every existing test in this suite drives a run whose three deterministic stages succeed.
That leaves two branches in ``executor.execute_run`` that nothing reaches, and ``W10-RUN``
proved it by mutating each away on a copy of ``src/`` and running the whole battery
(``tests/contract`` and ``tests/checkpoint`` excluded, 498 passed + the 154 in ``runs`` and
``ingest``). Nothing failed either time:

* ``if result.status is not StageStatus.SUCCEEDED: halted = True; break`` → ``if False:``.
  A failed preparation stage no longer stops the chain, so ``page_geometry_extraction``
  and ``document_context_build`` are run against inputs that do not exist and the model
  stage is asked for an analysis of a document nothing could read. The executor's own
  comment says why it must not: "continuing would produce a cascade of identical
  ``missing_required_input`` failures that say nothing extra" — and, worse, it spends a
  provider call on a document the chain already knows it could not prepare.
* ``missing = [stage for stage in PC01_STAGES if stage not in statuses]`` → ``missing =
  []``. A stage that never ran has no status, and ``select_terminal`` requires one for
  every required stage. Without this branch the run reaches ``select_terminal`` with an
  incomplete map, and the executor's contract — "the run must reach a terminal" — rests on
  whatever that function happens to do with a hole in its input.

How the halt is produced
------------------------
Through the real chain, by making the source bytes unreadable *at the port*. The store is
wrapped so that a ``read`` of the one seeded source blob returns bytes that are not a PDF;
every other call delegates to the real adapter. Nothing about ``source_preparation`` is
special-cased and no stage is stubbed: the stage really runs, really reads, and really
fails on what it got.

That is deliberately not done by corrupting the published object. The version's manifest is
immutable and the object is content-addressed, so a corrupted object would be a different
fault — it is the one ``tests/integration/ingest`` now guards — and it would leave residue
in a shared bucket. Here the bucket is untouched.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.runs import RunRepository, execute_run, start_audit_run

#: The four stages ``PC01_STAGES`` declares, written out rather than imported. A run that
#: silently stopped requiring one of them would still satisfy an assertion built from the
#: constant itself.
PINNED_PC01_STAGES = (
    "source_preparation",
    "page_geometry_extraction",
    "document_context_build",
    "text_analysis",
)


class UnreadableSource:
    """The real adapter, except that one blob reads back as something that is not a PDF.

    A transport-level substitution, not a stage stub: ``source_preparation`` performs its
    own read through the port and then fails on the bytes it was handed, exactly as it
    would for a genuinely unreadable object.
    """

    def __init__(self, inner, blob_id: str) -> None:
        self._inner = inner
        self._blob_id = blob_id
        self.reads_of_the_source = 0

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def read(self, blob_id, **kwargs):
        if str(blob_id) == self._blob_id:
            self.reads_of_the_source += 1
            return b"this is not a PDF and no page parser will accept it\n"
        return self._inner.read(blob_id, **kwargs)


class ProviderThatMustNotBeAsked:
    """An adapter that fails the test if the executor reaches it.

    The point of halting is that the provider is never asked about a document the chain
    could not prepare. Asserting that with a counter would let the call happen and then
    complain; this makes the call itself the failure, so the reason is unambiguous.
    """

    def __init__(self, provider_mode) -> None:
        self._mode = provider_mode
        self.calls = 0

    @property
    def provider_mode(self):
        return self._mode

    def complete(self, request):  # pragma: no cover - reaching this is the failure
        self.calls += 1
        raise AssertionError(
            "the model provider was asked about a document whose preparation failed; "
            "the chain must halt before the AI stage"
        )


def _start(session: Session, seeded, new_key, label: str) -> str:
    started = start_audit_run(
        session,
        version_uid=seeded.version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded",
        idempotency_key=new_key(label),
    )
    assert started.replayed is False
    return str(started.run_id)


@pytest.fixture
def halted_run(session: Session, seeded, blob_store, recorded_adapter, provider_config,
               new_key):
    """One execution whose first stage fails, driven through the real chain."""
    store = UnreadableSource(blob_store, seeded.source_blob_id)
    adapter = ProviderThatMustNotBeAsked(recorded_adapter.provider_mode)
    run_id = _start(session, seeded, new_key, "halted-chain")

    result = execute_run(
        session,
        run_id,
        blob_store=store,
        adapter=adapter,
        provider_config=provider_config,
        sleep=lambda _seconds: None,
    )
    assert store.reads_of_the_source >= 1, (
        "the substitution never took effect, so nothing below is about a halted chain"
    )
    return run_id, result, adapter


def test_a_failed_preparation_stage_stops_the_chain_before_the_provider(
    session: Session, halted_run
) -> None:
    """The stages after the failure do not run, and the provider is never asked.

    Asserted on what was **persisted**, not on an in-process tally: a stage that ran wrote
    a row, and a stage that did not has none. That is the difference the ``halted`` flag
    makes, and it is invisible to every assertion that only looks at the terminal.
    """
    run_id, result, adapter = halted_run

    assert adapter.calls == 0

    persisted = {
        row[0]
        for row in session.execute(
            text("SELECT stage_id FROM stage_result WHERE run_id = :r"), {"r": run_id}
        )
    }
    assert persisted == {"source_preparation"}, (
        "exactly one stage ran; the chain must not continue into stages whose inputs the "
        "failed stage never produced"
    )
    assert result.stage_statuses == {"source_preparation": "failed"}

    status, error = session.execute(
        text(
            "SELECT status, error FROM stage_result "
            "WHERE run_id = :r AND stage_id = 'source_preparation'"
        ),
        {"r": run_id},
    ).one()
    assert status == "failed"
    assert error is not None
    # No model_call row either: nothing was spent on a document that could not be read.
    assert (
        session.execute(
            text("SELECT count(*) FROM model_call WHERE run_id = :r"), {"r": run_id}
        ).scalar_one()
        == 0
    )


def test_the_stages_that_never_ran_are_named_in_the_degradation_set(
    session: Session, halted_run
) -> None:
    """A run that halted still reaches a terminal, and it says which stages are missing.

    ``select_terminal`` requires a status for every required stage, and a halted chain has
    three that never produced one. The executor records those as failed-by-absence rather
    than letting selection see a hole — so the run ends, and the row names what did not
    happen instead of merely saying the run failed.

    The three names are written out. An assertion built from ``PC01_STAGES`` would agree
    with the module however the list changed.
    """
    run_id, result, _ = halted_run

    assert result.terminal_state == "failed"
    assert set(result.degradation_set) == {
        "page_geometry_extraction",
        "document_context_build",
        "text_analysis",
    }
    assert "source_preparation" not in result.degradation_set, (
        "source_preparation did run; it is failed, not absent, and the degradation set "
        "is the set of stages with no status at all"
    )
    assert result.terminal_reason == "analysis_failed"
    assert result.gate_ran is False
    assert result.published_finding_count == 0
    assert result.attempts == 0, (
        "the chain never reached the provider, so it has no attempts rather than one "
        "failed attempt"
    )

    # And the same facts out of the database, which is what an operator reads.
    state, degradation_set, terminal_reason, terminal_at = session.execute(
        text(
            "SELECT state, degradation_set, terminal_reason, terminal_at "
            "FROM audit_run WHERE run_id = :r"
        ),
        {"r": run_id},
    ).one()
    assert state == "failed"
    assert terminal_at is not None
    assert terminal_reason == "analysis_failed"
    assert set(degradation_set) == {
        "page_geometry_extraction",
        "document_context_build",
        "text_analysis",
    }

    # The four required stages, spelled out, so "the three that are missing" is a claim
    # about a known set rather than about whatever the module currently declares.
    assert set(PINNED_PC01_STAGES) - {"source_preparation"} == set(degradation_set)


def test_the_run_is_not_left_running(session: Session, halted_run) -> None:
    """``OD-10``'s companion property: a halted chain reaches a terminal by itself.

    Reconciliation exists for runs whose *process* died. A run whose chain failed must not
    need it — if this row were left ``running``, the failure would look like an outage.
    """
    run_id, _, _ = halted_run

    state = session.execute(
        text("SELECT state FROM audit_run WHERE run_id = :r"), {"r": run_id}
    ).scalar_one()
    assert state in {"published", "partial", "failed", "cancelled"}
    assert state == "failed"
