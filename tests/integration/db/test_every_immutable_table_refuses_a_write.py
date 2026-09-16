"""Every immutable and append-only trigger, on every table, on both of its arms.

``tests/integration/db/test_schema_shape.py`` asserts that exactly the declared tables
carry ``am_immutable_row`` and ``am_append_only``. That is a *catalog* claim: it reads
``pg_trigger`` and checks which function is attached. It says nothing about what the
trigger fires on, and a trigger declared ``BEFORE DELETE`` instead of ``BEFORE UPDATE OR
DELETE`` satisfies it exactly.

``test_schema_invariants.py`` beside this file makes the *reachability* claim for most of
them — it performs the write and asserts the SQLSTATE. Three arms were missing, and
``W10-RUN`` proved it by mutating ``db/migrations/versions/20260910_0002_pc01_schema.py``
on a full copy of the tree (migrations applied by the literal ``alembic`` command inside
that copy, with ``auditmanager.__file__`` checked to resolve under it) and running the
whole battery, ``tests/contract`` and ``tests/checkpoint`` excluded:

* ``model_call`` re-declared ``BEFORE DELETE`` only — nothing failed. No test in the
  repository ever attempted an ``UPDATE`` or a ``DELETE`` on ``model_call`` at all; the
  table's entire immutability rested on the shape assertion.
* ``finding_evidence`` re-declared ``BEFORE UPDATE`` only — nothing failed.
  ``tests/integration/findings/test_grounding_gate.py`` nudges an anchor and is refused,
  which covers the UPDATE arm; nothing deletes an evidence row.
* ``audit_event`` re-declared ``BEFORE DELETE`` only — nothing failed.
  ``test_schema_invariants.py`` deletes an audit event and is refused; nothing updates one.

Each of those is a real consequence and not a technicality. A rewritable ``model_call``
row means the cost, the token counts and the recorded provider mode of a published run
can be edited after the fact, which is the whole of what that table is for. A deletable
``finding_evidence`` row means a published observation can be left pointing at evidence
that is simply gone. A rewritable ``audit_event`` is an audit trail that can be edited.

What is asserted
----------------
The SQLSTATE, always, and the one the *contract* assigns rather than "something raised":
``AM002`` for the append-only ledger and ``AM003`` for an immutable row. The two are
different rules with different messages and both map to ``state_transition_not_allowed``,
so asserting the catalog code alone would not tell them apart — and a table that lost its
own trigger but inherited a foreign-key cascade would still "raise".

Each statement is also checked to have matched a row before the refusal, so a guard
cannot appear to work because the ``WHERE`` clause found nothing.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from auditmanager.shared.db.schema import (
    SQLSTATE_APPEND_ONLY_VIOLATION,
    SQLSTATE_IMMUTABLE_ROW_VIOLATION,
)
from auditmanager.shared.db.session import create_session_factory, session_scope
from auditmanager.shared.identity import (
    AnalysisProfileId,
    AuditEventId,
    DocumentUid,
    FindingObservationId,
    FindingUid,
    ModelCallId,
    ProjectUid,
    PromptBundleId,
    RunId,
    VersionUid,
)

DIGEST = "a" * 64
OTHER_DIGEST = "b" * 64
QUOTE = "two fire-resistance classes"


def sqlstate_of(error: DBAPIError) -> str:
    """The five-character SQLSTATE the server reported."""
    return str(getattr(error.orig, "sqlstate", "") or "")


@pytest.fixture
def session(migrated_engine: Engine):
    factory = create_session_factory(migrated_engine)
    with session_scope(factory) as active:
        yield active


class Journey:
    """Enough of a published run to own one of every immutable row.

    Deliberately written with raw SQL rather than through the repositories: the guard's
    job is to refuse *every* caller, including one that never goes near a repository, and
    a fixture that could only produce rows the repositories produce could not tell the two
    apart.
    """

    def __init__(self, session: Session) -> None:
        self.session = session
        self.project_uid = str(ProjectUid.new())
        self.document_uid = str(DocumentUid.new())
        self.version_uid = str(VersionUid.new())
        self.run_id = str(RunId.new())
        self.model_call_id = str(ModelCallId.new())
        self.finding_uid = str(FindingUid.new())
        self.observation_id = str(FindingObservationId.new())
        self.audit_event_id = str(AuditEventId.new())

        session.execute(
            text("INSERT INTO project (project_uid, name) VALUES (:p, 'AR review')"),
            {"p": self.project_uid},
        )
        session.execute(
            text(
                "INSERT INTO document (document_uid, project_uid, display_title) "
                "VALUES (:d, :p, 'AR-1')"
            ),
            {"d": self.document_uid, "p": self.project_uid},
        )
        session.execute(
            text(
                "INSERT INTO document_version (version_uid, document_uid, "
                "version_ordinal, media_type, byte_size, sha256, page_count) "
                "VALUES (:v, :d, 1, 'application/pdf', 1024, :s, 12)"
            ),
            {"v": self.version_uid, "d": self.document_uid, "s": DIGEST},
        )
        session.execute(
            text(
                "INSERT INTO audit_run (run_id, project_uid, version_uid, "
                "analysis_profile_id, prompt_bundle_id, provider_mode, "
                "frozen_input_digest) "
                "VALUES (:r, :p, :v, :ap, :pb, 'recorded', :s)"
            ),
            {
                "r": self.run_id,
                "p": self.project_uid,
                "v": self.version_uid,
                "ap": str(AnalysisProfileId.new()),
                "pb": str(PromptBundleId.new()),
                "s": OTHER_DIGEST,
            },
        )
        session.execute(
            text(
                "INSERT INTO model_call (model_call_id, run_id, stage_id, provider, "
                "model_identity, provider_mode, request_sha256, response_sha256, "
                "input_tokens, output_tokens, latency_ms, cost_micros, status) "
                "VALUES (:m, :r, 'text_analysis', 'anthropic', 'a-model', 'recorded', "
                "        :req, :res, 4096, 512, 1200, 250000, 'succeeded')"
            ),
            {
                "m": self.model_call_id,
                "r": self.run_id,
                "req": DIGEST,
                "res": OTHER_DIGEST,
            },
        )
        session.execute(
            text(
                "INSERT INTO finding (finding_uid, project_uid, version_uid, "
                "allocated_by_run_id, category) "
                "VALUES (:f, :p, :v, :r, 'internal_contradiction')"
            ),
            {
                "f": self.finding_uid,
                "p": self.project_uid,
                "v": self.version_uid,
                "r": self.run_id,
            },
        )
        session.execute(
            text(
                "INSERT INTO finding_observation (finding_observation_id, run_id, "
                "finding_uid, stage_id, category, finding_text, recommendation_text, "
                "grounded, analysis_profile_id, prompt_bundle_id, provider_mode) "
                "VALUES (:o, :r, :f, 'text_analysis', 'internal_contradiction', "
                "        'Two fire-resistance classes', 'Reconcile the two statements', "
                "        true, :ap, :pb, 'recorded')"
            ),
            {
                "o": self.observation_id,
                "r": self.run_id,
                "f": self.finding_uid,
                "ap": str(AnalysisProfileId.new()),
                "pb": str(PromptBundleId.new()),
            },
        )
        session.execute(
            text(
                "INSERT INTO finding_evidence (finding_observation_id, "
                "evidence_ordinal, page_number, quote, char_start, char_end) "
                "VALUES (:o, 0, 4, :q, 100, :end)"
            ),
            {"o": self.observation_id, "q": QUOTE, "end": 100 + len(QUOTE)},
        )
        session.execute(
            text(
                "INSERT INTO audit_event (audit_event_id, event_type, aggregate_type, "
                "aggregate_id) VALUES (:e, 'run.published', 'AuditRun', :a)"
            ),
            {"e": self.audit_event_id, "a": self.run_id},
        )
        session.flush()

    def refuse(self, statement: str, parameters: dict) -> DBAPIError:
        """Run one statement inside its own SAVEPOINT and return the refusal.

        A SAVEPOINT per attempt, so a refusal aborts its own subtransaction and the next
        statement still runs against a live one.
        """
        with pytest.raises(DBAPIError) as raised:
            with self.session.begin_nested():
                proxy = self.session.execute(text(statement), parameters)
                assert proxy.rowcount == 1, (
                    "the statement matched no row, so no trigger could have refused it "
                    "and this assertion would be about nothing"
                )
                self.session.flush()
        return raised.value


@pytest.fixture
def journey(session: Session) -> Journey:
    return Journey(session)


# --- model_call: provenance nothing had ever tried to rewrite -------------------


@pytest.mark.parametrize(
    ("what", "statement"),
    [
        (
            "edit the cost of a recorded call",
            "UPDATE model_call SET cost_micros = 1 WHERE model_call_id = :m",
        ),
        (
            "edit the token counts",
            "UPDATE model_call SET input_tokens = 1, output_tokens = 1 "
            "WHERE model_call_id = :m",
        ),
        (
            "restate which provider mode answered",
            "UPDATE model_call SET provider_mode = 'live' WHERE model_call_id = :m",
        ),
        (
            "delete the evidence that a call happened",
            "DELETE FROM model_call WHERE model_call_id = :m",
        ),
    ],
)
def test_a_recorded_model_call_refuses_every_later_write(
    journey: Journey, what: str, statement: str
) -> None:
    """``model_call`` is the run's provenance, and provenance that can be edited is not.

    ``PROTOTYPE_PROFILE`` §8 criterion 4 requires a live outcome and a recorded one to
    stay distinguishable, and ``model_call.provider_mode`` is where that distinction is
    persisted. An UPDATE arm nobody had exercised is an UPDATE arm nobody would have
    missed: re-declaring the trigger ``BEFORE DELETE`` left the whole battery green, and
    the third case above is the one that matters most — a recorded run could then be
    relabelled as live, row by row, after it published.
    """
    exc = journey.refuse(statement, {"m": journey.model_call_id})

    assert sqlstate_of(exc) == SQLSTATE_IMMUTABLE_ROW_VIOLATION, what
    assert "immutable once written" in str(exc.orig)

    # The row survived, unchanged, and is still countable.
    row = journey.session.execute(
        text(
            "SELECT provider_mode, cost_micros, input_tokens FROM model_call "
            "WHERE model_call_id = :m"
        ),
        {"m": journey.model_call_id},
    ).one()
    assert tuple(row) == ("recorded", 250000, 4096)


# --- finding_evidence: the delete arm -------------------------------------------


def test_published_evidence_refuses_deletion_as_well_as_editing(
    journey: Journey,
) -> None:
    """An anchor cannot be nudged *or* removed after publication.

    The grounding-gate suite proves the nudge is refused. Deletion is the other way to
    break the same property, and it is worse: a published observation whose evidence rows
    are gone reads as grounded and can no longer be checked against the document. Only the
    UPDATE arm was exercised, so a ``BEFORE UPDATE``-only trigger left the battery green.
    """
    exc = journey.refuse(
        "DELETE FROM finding_evidence WHERE finding_observation_id = :o",
        {"o": journey.observation_id},
    )

    assert sqlstate_of(exc) == SQLSTATE_IMMUTABLE_ROW_VIOLATION
    assert "immutable once written" in str(exc.orig)

    quote = journey.session.execute(
        text(
            "SELECT quote FROM finding_evidence WHERE finding_observation_id = :o "
            "AND evidence_ordinal = 0"
        ),
        {"o": journey.observation_id},
    ).scalar_one()
    assert quote == QUOTE

    # The mirror image, so this file also carries the arm the other suite covers, and a
    # trigger that lost UPDATE instead reddens here too rather than only over there.
    update_exc = journey.refuse(
        "UPDATE finding_evidence SET char_start = char_start + 1 "
        "WHERE finding_observation_id = :o",
        {"o": journey.observation_id},
    )
    assert sqlstate_of(update_exc) == SQLSTATE_IMMUTABLE_ROW_VIOLATION


# --- audit_event: the update arm -------------------------------------------------


def test_the_audit_trail_refuses_an_update_as_well_as_a_delete(
    journey: Journey,
) -> None:
    """An audit event is appended, never corrected. Both arms, and the ledger's own code.

    ``test_schema_invariants.py`` deletes one and is refused. Nothing updated one, so a
    ``BEFORE DELETE``-only trigger left the battery green — and an audit trail whose rows
    can be rewritten in place is worth less than no audit trail, because it still looks
    like one.

    ``AM002`` and not ``AM003``: this is the append-only ledger's refusal, and the two
    carry different guidance — "append a new event" against "create a new entity with a
    new identifier". A test that accepted either would not notice the wrong function
    being attached.
    """
    for statement in (
        "UPDATE audit_event SET event_type = 'run.failed' WHERE audit_event_id = :e",
        "UPDATE audit_event SET payload = '{\"edited\": true}'::jsonb "
        "WHERE audit_event_id = :e",
        "DELETE FROM audit_event WHERE audit_event_id = :e",
    ):
        exc = journey.refuse(statement, {"e": journey.audit_event_id})
        assert sqlstate_of(exc) == SQLSTATE_APPEND_ONLY_VIOLATION, statement
        assert "append-only ledger" in str(exc.orig)

    event_type, payload = journey.session.execute(
        text("SELECT event_type, payload FROM audit_event WHERE audit_event_id = :e"),
        {"e": journey.audit_event_id},
    ).one()
    assert (event_type, payload) == ("run.published", {})


# --- the mirror image ------------------------------------------------------------


def test_the_rows_these_guards_protect_can_still_be_written_in_the_first_place(
    journey: Journey,
) -> None:
    """The control: the tables refuse *later* writes, not all writes.

    Without this the file above could pass against a schema that refused every insert,
    and the fixture's own success is the only thing standing between those two readings.
    A second audit event appends, which is what an append-only ledger is for.
    """
    second_event = str(AuditEventId.new())
    journey.session.execute(
        text(
            "INSERT INTO audit_event (audit_event_id, event_type, aggregate_type, "
            "aggregate_id) VALUES (:e, 'run.reconciled', 'AuditRun', :a)"
        ),
        {"e": second_event, "a": journey.run_id},
    )
    journey.session.flush()

    assert (
        journey.session.execute(
            text("SELECT count(*) FROM audit_event WHERE aggregate_id = :a"),
            {"a": journey.run_id},
        ).scalar_one()
        == 2
    )
    assert (
        journey.session.execute(
            text("SELECT count(*) FROM model_call WHERE run_id = :r"),
            {"r": journey.run_id},
        ).scalar_one()
        == 1
    )
    assert (
        journey.session.execute(
            text(
                "SELECT count(*) FROM finding_evidence "
                "WHERE finding_observation_id = :o"
            ),
            {"o": journey.observation_id},
        ).scalar_one()
        == 1
    )
