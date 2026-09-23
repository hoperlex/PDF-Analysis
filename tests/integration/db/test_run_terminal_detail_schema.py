"""`D-46` / ``0010_run_terminal_detail``: the column, its two CHECKs, and its rollback.

**This file exists because a mutation came back green, and that was the finding.**

``tests/integration/runs/test_terminal_detail_says_which_dependency.py`` already drives the
two CHECKs -- it writes an illegal detail through the session and requires a ``DBAPIError``
-- and those cases are real: they assert what the lane's live schema does. But the runs
suite connects to the **already-migrated lane database**, so weakening the constraint in
``0010``'s source changes nothing it can see. Measured: mutating
``ck_audit_run_terminal_detail_needs_a_reason`` to ``CHECK (true)`` in a whole-worktree copy
left that suite at **14 passed**.

``OPERATING_CONSTRAINTS.md`` §10.1 names the mechanism -- *"it does not make a migration
mutable, and neither does any other copy"* -- and names the escape, a whole-worktree copy.
What it does not say, and what this cost, is that a whole-worktree copy is **still** not
enough unless the suite re-migrates: the escape is the ``migrated_engine`` fixture, which
creates a throwaway database and applies the head to it through the literal command. So the
migration-sensitive assertions belong here, and the behavioural ones stay where they are.

Two claims that are worth keeping apart
----------------------------------------
The CHECK that a detail needs a reason is **structural and is meant to be in the table**: a
detail with no code beside it is unscreenable by anything, at any later time, because the
allowlist that bounds it is a property of the reported code.

The **key allowlist itself is deliberately not here**, and its absence is a decision rather
than an omission. Encoding the frozen catalog's twenty-two per-code key lists into a
migration is how they drift from ``contracts/domain/v1/error-codes.json``, and correcting
them would need another revision. It is applied by
:func:`auditmanager.shared.errors.screen_details` -- the same function the error envelope
uses -- at three points in three different eras.
"""

from __future__ import annotations

import json

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from auditmanager.shared.identity import (
    AnalysisProfileId,
    DocumentUid,
    ProjectUid,
    PromptBundleId,
    RunId,
    VersionUid,
)
from tests.integration.db.conftest import (  # type: ignore[import-not-found]
    MIGRATE_ARGV,
    run_foundation_command,
)

DOWNGRADE_ARGV = [
    ".venv/bin/python",
    "-m",
    "alembic",
    "--config",
    "db/migrations/alembic.ini",
    "downgrade",
    "0009_reviewer_display_name",
]


def _constraint(session: Session, name: str) -> str | None:
    return session.execute(
        text("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = :n"),
        {"n": name},
    ).scalar()


def _column_type(session: Session, table: str, column: str) -> str | None:
    return session.execute(
        text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    ).scalar()


def _seed_run(session: Session, *, state: str, reason: str | None) -> str:
    """One ``audit_run`` row in a terminal state, written with raw SQL.

    Raw SQL and not the repository, deliberately: what is under test is the **table's** own
    refusal, and going through the code that also screens would test the screen twice and
    the table not at all.

    The parents are the minimum ``audit_run``'s foreign keys require. Written out rather
    than shared with ``test_schema_invariants.py``'s ``Fixture``, which seeds a whole
    journey this file has no use for.
    """
    project_uid = str(ProjectUid.new())
    document_uid = str(DocumentUid.new())
    version_uid = str(VersionUid.new())
    run_id = str(RunId.new())
    session.execute(
        text("INSERT INTO project (project_uid, name) VALUES (:uid, 'w42 detail')"),
        {"uid": project_uid},
    )
    session.execute(
        text(
            "INSERT INTO document (document_uid, project_uid, display_title) "
            "VALUES (:doc, :prj, 'w42')"
        ),
        {"doc": document_uid, "prj": project_uid},
    )
    session.execute(
        text(
            "INSERT INTO document_version (version_uid, document_uid, version_ordinal, "
            "media_type, byte_size, sha256, page_count) "
            "VALUES (:ver, :doc, 1, 'application/pdf', 1024, :d, 12)"
        ),
        {"ver": version_uid, "doc": document_uid, "d": "a" * 64},
    )
    # Inserted in the declared initial state and walked to the terminal, because
    # `am_guard_state_transition` refuses a row created in any other state -- the same
    # trigger `test_schema_invariants.py` exists to prove. A row that bypassed the machine
    # would also be a row the CHECKs under test had never been applied to in the way the
    # application applies them.
    session.execute(
        text(
            "INSERT INTO audit_run (run_id, project_uid, version_uid, "
            "analysis_profile_id, prompt_bundle_id, provider_mode, frozen_input_digest) "
            "VALUES (:run, :prj, :ver, :ap, :pb, 'recorded', :d)"
        ),
        {
            "run": run_id,
            "prj": project_uid,
            "ver": version_uid,
            "ap": str(AnalysisProfileId.new()),
            "pb": str(PromptBundleId.new()),
            "d": "b" * 64,
        },
    )
    for next_state in ("queued", "running", "validating"):
        session.execute(
            text("UPDATE audit_run SET state = :s WHERE run_id = :r"),
            {"s": next_state, "r": run_id},
        )
    session.execute(
        text(
            "UPDATE audit_run SET state = :s, terminal_reason = :reason, "
            "terminal_at = now() WHERE run_id = :r"
        ),
        {"s": state, "reason": reason, "r": run_id},
    )
    return run_id


class TestTheColumn:
    def test_it_exists_and_is_jsonb(self, migrated_engine: Engine) -> None:
        with Session(migrated_engine) as session:
            assert _column_type(session, "audit_run", "terminal_detail") == "jsonb"

    def test_both_constraints_exist(self, migrated_engine: Engine) -> None:
        with Session(migrated_engine) as session:
            shape = _constraint(session, "ck_audit_run_terminal_detail_is_object")
            coupling = _constraint(
                session, "ck_audit_run_terminal_detail_needs_a_reason"
            )
        assert shape is not None, "nothing bounds terminal_detail's shape"
        assert "jsonb_typeof" in shape, shape
        assert coupling is not None, (
            "a terminal_detail with no terminal_reason beside it is unscreenable -- the "
            "allowlist that bounds its keys is a property of the reported code -- and "
            "nothing in this table refuses one"
        )
        assert "terminal_reason IS NOT NULL" in coupling, coupling

    def test_the_coupling_constraint_is_not_a_tautology(
        self, migrated_engine: Engine
    ) -> None:
        """The specific way a CHECK stops being one: ``CHECK (true)``.

        Named because that is exactly the mutation this file was written for, and because
        a constraint that exists and admits everything reads, in ``pg_constraint``, like a
        constraint.
        """
        with Session(migrated_engine) as session:
            coupling = _constraint(
                session, "ck_audit_run_terminal_detail_needs_a_reason"
            )
        assert coupling is not None
        assert coupling.strip().lower() not in {"check (true)", "check ((true))"}, coupling


class TestTheTableRefusesWhatCannotBeScreened:
    def test_a_detail_with_no_reason_is_refused(self, migrated_engine: Engine) -> None:
        with Session(migrated_engine) as session:
            run_id = _seed_run(session, state="published", reason=None)
            with pytest.raises(DBAPIError):
                session.execute(
                    text(
                        "UPDATE audit_run SET terminal_detail = CAST(:d AS jsonb) "
                        "WHERE run_id = :r"
                    ),
                    {"d": json.dumps({"dependency": "model_provider"}), "r": run_id},
                )
            session.rollback()

    def test_a_detail_that_is_not_an_object_is_refused(
        self, migrated_engine: Engine
    ) -> None:
        with Session(migrated_engine) as session:
            run_id = _seed_run(session, state="failed", reason="dependency_unavailable")
            for illegal in ('["a"]', '"a string"', "42"):
                with pytest.raises(DBAPIError), session.begin_nested():
                    session.execute(
                        text(
                            "UPDATE audit_run SET terminal_detail = CAST(:d AS jsonb) "
                            "WHERE run_id = :r"
                        ),
                        {"d": illegal, "r": run_id},
                    )
            session.rollback()

    def test_a_flat_object_beside_a_reason_is_accepted(
        self, migrated_engine: Engine
    ) -> None:
        """The other half. A table that refused everything would pass both cases above."""
        with Session(migrated_engine) as session:
            run_id = _seed_run(session, state="failed", reason="analysis_input_invalid")
            session.execute(
                text(
                    "UPDATE audit_run SET terminal_detail = CAST(:d AS jsonb) "
                    "WHERE run_id = :r"
                ),
                {
                    "d": json.dumps(
                        {"stage_id": "text_analysis", "reason": "recording_missing"}
                    ),
                    "r": run_id,
                },
            )
            stored = session.execute(
                text("SELECT terminal_detail FROM audit_run WHERE run_id = :r"),
                {"r": run_id},
            ).scalar()
            assert stored == {
                "stage_id": "text_analysis",
                "reason": "recording_missing",
            }
            session.rollback()

    def test_the_key_allowlist_is_deliberately_not_in_the_table(
        self, migrated_engine: Engine
    ) -> None:
        """An unsafe key reaches the column, and that is the design rather than a hole.

        The catalog's twenty-two per-code key lists belong to
        ``contracts/domain/v1/error-codes.json``; encoding them in a migration is how they
        drift, and correcting them would need another revision. The screen is
        ``screen_details``, applied at three points in the code -- and the third of those,
        at the edge, is what covers a row like the one written here.

        This case is a **statement of where the boundary is**, not an endorsement. If
        somebody later adds the allowlist to the table, this is the case that tells them
        the decision was made rather than forgotten.
        """
        with Session(migrated_engine) as session:
            run_id = _seed_run(session, state="failed", reason="dependency_unavailable")
            session.execute(
                text(
                    "UPDATE audit_run SET terminal_detail = CAST(:d AS jsonb) "
                    "WHERE run_id = :r"
                ),
                {"d": json.dumps({"prompt": "not a safe key for this code"}), "r": run_id},
            )
            # And the edge refuses to publish it, which is the screen that actually covers
            # a row like this one.
            from auditmanager.api.schemas.runs import RunStatusView, run_status_body
            from auditmanager.shared.errors import UnsafeDetailKey

            import datetime

            project_uid, version_uid = session.execute(
                text(
                    "SELECT project_uid, version_uid FROM audit_run WHERE run_id = :r"
                ),
                {"r": run_id},
            ).one()
            view = RunStatusView(
                run_id=run_id,
                project_uid=project_uid,
                version_uid=version_uid,
                state="failed",
                provider_mode="recorded",
                created_at=datetime.datetime(2026, 9, 23, tzinfo=datetime.timezone.utc),
                terminal_reason="dependency_unavailable",
                terminal_detail={"prompt": "not a safe key for this code"},
            )
            with pytest.raises(UnsafeDetailKey):
                run_status_body(view)
            session.rollback()


class TestTheRollback:
    """`R-11` reverted a whole wave over a reseal. This column is part of one."""

    def test_it_downgrades_and_upgrades_again(self, migrated_database) -> None:
        url = migrated_database.url.render_as_string(hide_password=False)
        from auditmanager.shared.db.engine import create_database_engine

        down = run_foundation_command(DOWNGRADE_ARGV, url)
        assert down.returncode == 0, down.describe()

        engine = create_database_engine(migrated_database)
        try:
            with Session(engine) as session:
                assert _column_type(session, "audit_run", "terminal_detail") is None
                assert (
                    _constraint(session, "ck_audit_run_terminal_detail_needs_a_reason")
                    is None
                )
                assert (
                    _constraint(session, "ck_audit_run_terminal_detail_is_object") is None
                )
                # `0009` is a separate revision and must still be there: reverting the
                # reseal does not un-name every reviewer, which is the whole reason this
                # wave wrote two migrations instead of the one it was allocated.
                assert _column_type(session, "app_user", "display_name") == "text"

            up = run_foundation_command(MIGRATE_ARGV, url)
            assert up.returncode == 0, up.describe()
            with Session(engine) as session:
                assert _column_type(session, "audit_run", "terminal_detail") == "jsonb"
        finally:
            engine.dispose()
