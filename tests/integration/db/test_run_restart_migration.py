"""`RUN-RESTART-01`: ``0071_run_restart`` -- the restart point of a run and the link of a tombstone to the run that replaced it, against real PostgreSQL.

A restart (``restartRun``) is a **new run** that replaces a ``partial``, ``failed`` or ``cancelled`` source; the source is tombstoned (``0066``) in the
transaction that publishes the new run. The revision adds one column, ``audit_run.restart_point``, and links the tombstone to the new run through the
**command** (``audit_run.command_id = audit_run_deletion.command_id``), with no second column on the frozen ``audit_run``. Each rule is shown by a row
that obeys beside a row that does not, with the triggers on, and a refusal is attributed to the constraint that made it, not only to its SQLSTATE:

* **the step changes no stored row**: every run keeps its columns, ``restart_point`` is ``NULL`` for all of them;
* **the point**: the eight stage chips of the run screen, and no other word;
* **the pair rule** ``ck_audit_run_started_from_pair`` (redefined, same name): a source is named exactly when there is a start stage or a restart
  point, never both, never with ``reaudit_of_run_id``; the rows of ``0060`` still obey it; a restart names its starter and its command;
* **one active restart per source**, released by any terminal state of the first (``ux_audit_run_active_restart``), and **one run per restart command**
  (``ux_audit_run_restart_command``);
* **frozen**: ``restart_point`` and the ``command_id`` of a restart cannot be rewritten (``AM003``); the command of an ordinary run, and any column
  that is not frozen, still can;
* **the link**: a tombstone that names a restart's command is refused (``AM001``) unless that run is ``published`` and names the tombstoned run as its
  source; the run that replaced a tombstoned source is the run whose ``command_id`` is the tombstone's; a plain ``deleteRun`` tombstone replaces nothing;
* **no constraint of the decision ledger compares versions**, so a carry between two findings of the same version (a restart's) is admitted as it stands;
* **the downgrade** refuses while a run holds a restart point, and with none restores the pair rule of ``0060`` and the frozen list of ``0064``.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import AnalysisProfileId, CommandId, PromptBundleId, RunId
from tests.integration.documents.seeding import Seeder
from tests.support.expected_facts import FACTS

THIS = "0071_run_restart"
PREVIOUS = "0070_document_group"

POINTS = ("preparation", "text", "blocks", "cross_check", "merge", "norms", "review", "correction")
PAIR = "ck_audit_run_started_from_pair"
POINT_CHECK = "ck_audit_run_restart_point"
STARTER_CHECK = "ck_audit_run_restart_has_starter_and_command"
ACTIVE = "ux_audit_run_active_restart"
COMMAND_KEY = "ux_audit_run_restart_command"


def _alembic(action: str, target: str) -> list[str]:
    return [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini", action, target]


def _refused(engine: Engine, write: Any, sqlstate: str, constraint: str | None = None) -> None:
    """The write is refused by the database with this SQLSTATE and, when named, by this constraint or index."""
    with pytest.raises(DBAPIError) as caught:
        with engine.begin() as connection:
            write(connection)
    assert str(getattr(caught.value.orig, "sqlstate", "") or "") == sqlstate, caught.value
    if constraint is not None:
        assert getattr(getattr(caught.value.orig, "diag", None), "constraint_name", None) == constraint, caught.value


def _accepted(engine: Engine, write: Any) -> None:
    """The write is accepted; the transaction is rolled back, so the next try starts from the same rows."""
    with engine.connect() as connection, connection.begin() as transaction:
        try:
            write(connection)
        finally:
            transaction.rollback()


class World:
    """One project, one version and one expert, committed; runs and commands are added on top."""

    def __init__(self, engine: Engine, *, at_head: bool = True) -> None:
        self.engine = engine
        self.at_head = at_head  # False: the schema of 0070, which has no ``restart_point`` column to write
        with Session(engine) as session:
            seed = Seeder(session)
            self.project = seed.project("Проект")
            self.version = seed.version(seed.document(self.project, "Документ"), classified=("R", "AR"))
            self.expert = seed.expert
            session.commit()

    def command(self, connection: Connection, command_type: str = "restart_run") -> str:
        command = str(CommandId.new())
        connection.execute(text(
            "INSERT INTO command_record (command_id, command_type, idempotency_key, payload_fingerprint) "
            "VALUES (:c, :t, :k, :f)"), {"c": command, "t": command_type, "k": f"rr01-{command[-12:]}", "f": "f" * 64})
        return command

    def run(
        self, connection: Connection, *, source: str | None = None, start_stage: str | None = None, point: str | None = None,
        command: str | None = None, starter: str | None = None, reaudit_of: str | None = None, state: str = "created",
    ) -> str:
        """Insert one run in the initial state, and walk it to ``state`` along the declared edges."""
        run = str(RunId.new())
        assert self.at_head or point is None
        connection.execute(text(
            "INSERT INTO audit_run (run_id, project_uid, version_uid, state, analysis_profile_id, prompt_bundle_id, provider_mode, "
            "frozen_input_digest, command_id, started_by_user_uid, started_from_run_id, start_stage_id, reaudit_of_run_id"
            + (", restart_point" if self.at_head else "") + ") "
            "VALUES (:r, :p, :v, 'created', :ap, :pb, 'recorded', :d, :c, :u, :s, :st, :ra" + (", :rp" if self.at_head else "") + ")"),
            {"r": run, "p": self.project, "v": self.version, "ap": str(AnalysisProfileId.new()), "pb": str(PromptBundleId.new()),
             "d": hashlib.sha256(run.encode()).hexdigest(), "c": command, "u": starter, "s": source, "st": start_stage, "ra": reaudit_of,
             **({"rp": point} if self.at_head else {})})
        self.walk(connection, run, state)
        return run

    @staticmethod
    def walk(connection: Connection, run: str, state: str) -> None:
        route = {
            "created": [], "queued": ["queued"], "running": ["queued", "running"], "validating": ["queued", "running", "validating"],
            "cancelled": ["cancelled"], "failed": ["queued", "failed"],
            "published": ["queued", "running", "validating", "published"],
            "partial": ["queued", "running", "validating", "partial"],
        }[state]
        for step in route:
            terminal = step in {"cancelled", "failed", "published", "partial"}
            degraded = ", degradation_set = '[\"text_analysis\"]'::jsonb" if step == "partial" else ""
            reason = ", terminal_reason = 'analysis_failed'" if step == "failed" else ""
            connection.execute(text(
                f"UPDATE audit_run SET state = :s{', terminal_at = now()' if terminal else ''}{degraded}{reason} WHERE run_id = :r"),
                {"s": step, "r": run})

    def ended_source(self, connection: Connection, state: str = "partial") -> str:
        return self.run(connection, state=state)

    def restart(self, connection: Connection, source: str, *, point: str = "review", state: str = "created") -> tuple[str, str]:
        """A restart run of ``source`` with its own command; returns (run, command)."""
        command = self.command(connection)
        return self.run(connection, source=source, point=point, command=command, starter=self.expert, state=state), command

    def tombstone(self, connection: Connection, run: str, command: str) -> None:
        connection.execute(text(
            "INSERT INTO audit_run_deletion (run_id, deleted_by_user_uid, command_id) VALUES (:r, :u, :c)"),
            {"r": run, "u": self.expert, "c": command})


def _count(engine: Engine, table: str) -> int:
    with engine.connect() as connection:
        return int(connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one())


def _replaced_by(connection: Connection, source: str) -> list[str]:
    """The run that replaced a tombstoned source, by the rule the contract states: the run whose command is the tombstone's."""
    return [row[0] for row in connection.execute(text(
        "SELECT r.run_id FROM audit_run_deletion d JOIN audit_run r ON r.command_id = d.command_id AND r.restart_point IS NOT NULL "
        "WHERE d.run_id = :s"), {"s": source})]


@pytest.fixture
def at_head(migrated_database: Any) -> Iterator[Engine]:
    engine = create_database_engine(migrated_database)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def at_previous(empty_database: Any, foundation_command: Any) -> Iterator[tuple[Engine, str]]:
    url = empty_database.url.render_as_string(hide_password=False)
    done = foundation_command(_alembic("upgrade", PREVIOUS), url)
    assert done.returncode == 0, done.describe()
    engine = create_database_engine(empty_database)
    try:
        yield engine, url
    finally:
        engine.dispose()


# -- the step -------------------------------------------------------------------------------------


def test_the_head_of_the_tree_is_this_revision_or_a_later_one() -> None:
    assert FACTS.migration_head >= THIS


def test_the_revision_id_fits_the_version_column() -> None:
    assert len(THIS) <= 32


def test_the_step_changes_no_stored_row_and_every_run_has_no_restart_point(at_previous: tuple[Engine, str], foundation_command: Any) -> None:
    engine, url = at_previous
    world = World(engine, at_head=False)
    with engine.begin() as connection:
        source = world.run(connection, state="partial")
        # A row of ``0060`` (a start from a stage) and one of ``0066`` (a tombstone) must survive the redefined pair rule unchanged.
        started = world.run(connection, source=source, start_stage="text_analysis")
        world.tombstone(connection, source, world.command(connection, "delete_audit_run"))
    with engine.connect() as connection:
        before = [tuple(row) for row in connection.execute(text("SELECT run_id, state, started_from_run_id, start_stage_id FROM audit_run ORDER BY run_id"))]
        assert len(before) == 2
        assert connection.execute(text(
            "SELECT count(*) FROM information_schema.columns WHERE table_name = 'audit_run' AND column_name = 'restart_point'")).scalar_one() == 0
    done = foundation_command(_alembic("upgrade", THIS), url)
    assert done.returncode == 0, done.describe()
    with engine.connect() as connection:
        after = [tuple(row) for row in connection.execute(text("SELECT run_id, state, started_from_run_id, start_stage_id FROM audit_run ORDER BY run_id"))]
        assert after == before and len(after) == 2
        assert connection.execute(text("SELECT count(*) FROM audit_run WHERE restart_point IS NOT NULL")).scalar_one() == 0
        assert connection.execute(text("SELECT start_stage_id FROM audit_run WHERE run_id = :r"), {"r": started}).scalar_one() == "text_analysis"
    assert _count(engine, "audit_run_deletion") == 1


# -- the point and the pair rule --------------------------------------------------------------------


def test_the_point_is_one_of_the_eight_chips_and_no_other_word(at_head: Engine) -> None:
    world = World(at_head)
    with at_head.begin() as connection:
        source = world.ended_source(connection)
    for point in POINTS:
        _accepted(at_head, lambda c, point=point: world.restart(c, source, point=point))
    for bad in ("Review", "critic", "comprehensive_analysis", "text_analysis", "", "all"):
        _refused(at_head, lambda c, bad=bad: world.restart(c, source, point=bad), "23514", POINT_CHECK)


def test_the_pair_rule_names_a_source_exactly_when_there_is_a_start_stage_or_a_restart_point(at_head: Engine) -> None:
    world = World(at_head)
    with at_head.begin() as connection:
        source = world.ended_source(connection)
        other = world.ended_source(connection, "failed")
    command = lambda c: world.command(c)  # noqa: E731
    # Obeying rows: the three runs a source can have.
    _accepted(at_head, lambda c: world.run(c, source=source, start_stage="document_context_build"))      # 0060, unchanged
    _accepted(at_head, lambda c: world.restart(c, source))                                              # 0071
    _accepted(at_head, lambda c: world.run(c))                                                          # neither
    # A source with neither a start stage nor a restart point, and a mode with no source.
    _refused(at_head, lambda c: world.run(c, source=source), "23514", PAIR)
    _refused(at_head, lambda c: world.run(c, start_stage="text_analysis"), "23514", PAIR)
    _refused(at_head, lambda c: world.run(c, point="review", command=command(c), starter=world.expert), "23514", PAIR)
    # Both modes at once.
    _refused(at_head, lambda c: world.run(c, source=source, start_stage="text_analysis", point="review", command=command(c),
                                          starter=world.expert), "23514", PAIR)
    # A re-audit is not a restart, and a restart is not a re-audit (the rule of 0060, kept).
    _refused(at_head, lambda c: world.run(c, source=source, point="review", command=command(c), starter=world.expert, reaudit_of=other),
             "23514", PAIR)
    _refused(at_head, lambda c: world.run(c, source=source, start_stage="text_analysis", reaudit_of=other), "23514", PAIR)


def test_a_restart_names_its_starter_and_its_command(at_head: Engine) -> None:
    world = World(at_head)
    with at_head.begin() as connection:
        source = world.ended_source(connection)
    _refused(at_head, lambda c: world.run(c, source=source, point="text", command=world.command(c)), "23514", STARTER_CHECK)
    _refused(at_head, lambda c: world.run(c, source=source, point="text", starter=world.expert), "23514", STARTER_CHECK)
    _accepted(at_head, lambda c: world.run(c, source=source, point="text", command=world.command(c), starter=world.expert))


# -- the two unique indexes -------------------------------------------------------------------------


def test_one_restart_of_a_source_is_active_at_a_time_and_any_terminal_state_releases_it(at_head: Engine) -> None:
    world = World(at_head)
    with at_head.begin() as connection:
        source = world.ended_source(connection)
        other_source = world.ended_source(connection, "cancelled")
        first, _ = world.restart(connection, source)
    # Created, queued, running and validating are all active.
    for step in (None, "queued", "running", "validating"):
        if step is not None:
            with at_head.begin() as connection:
                connection.execute(text("UPDATE audit_run SET state = :s WHERE run_id = :r"), {"s": step, "r": first})
        _refused(at_head, lambda c: world.restart(c, source, point="norms"), "23505", ACTIVE)
    # The controls: another source, and a start from a stage of the same source, are not held by it.
    _accepted(at_head, lambda c: world.restart(c, other_source))
    _accepted(at_head, lambda c: world.run(c, source=source, start_stage="text_analysis"))
    # A terminal state of the first releases the source: each of the three that can end a restart, on a source of its own.
    for terminal in ("cancelled", "failed", "partial"):
        with at_head.begin() as connection:
            fresh = world.ended_source(connection)
            running, _ = world.restart(connection, fresh, state="running")
        _refused(at_head, lambda c: world.restart(c, fresh, point="norms"), "23505", ACTIVE)
        with at_head.begin() as connection:
            if terminal == "partial":
                connection.execute(text("UPDATE audit_run SET state = 'validating' WHERE run_id = :r"), {"r": running})
            connection.execute(text(
                "UPDATE audit_run SET state = :s, terminal_at = now()"
                + (", terminal_reason = 'analysis_failed'" if terminal == "failed" else "")
                + (", degradation_set = '[\"text_analysis\"]'::jsonb" if terminal == "partial" else "")
                + " WHERE run_id = :r"), {"s": terminal, "r": running})
        _accepted(at_head, lambda c: world.restart(c, fresh, point="norms"))


def test_a_restart_command_makes_one_run(at_head: Engine) -> None:
    world = World(at_head)
    with at_head.begin() as connection:
        source = world.ended_source(connection)
        other = world.ended_source(connection, "failed")
        run, command = world.restart(connection, source, state="cancelled")
    _refused(at_head, lambda c: world.run(c, source=other, point="text", command=command, starter=world.expert), "23505", COMMAND_KEY)
    _accepted(at_head, lambda c: world.run(c, source=other, point="text", command=world.command(c), starter=world.expert))
    assert run


# -- frozen -----------------------------------------------------------------------------------------


def test_the_restart_point_and_the_command_of_a_restart_cannot_be_rewritten_and_nothing_else_about_an_ordinary_run_changes(at_head: Engine) -> None:
    world = World(at_head)
    with at_head.begin() as connection:
        source = world.ended_source(connection)
        run, _ = world.restart(connection, source, point="review")
        plain = world.run(connection, command=world.command(connection, "start_audit_run"))
    _refused(at_head, lambda c: c.execute(text("UPDATE audit_run SET restart_point = 'text' WHERE run_id = :r"), {"r": run}), "AM003")
    _refused(at_head, lambda c: c.execute(text("UPDATE audit_run SET restart_point = NULL WHERE run_id = :r"), {"r": run}), "AM003")
    _refused(at_head, lambda c: c.execute(text("UPDATE audit_run SET command_id = :c WHERE run_id = :r"), {"r": run, "c": world.command(c)}), "AM003")
    _refused(at_head, lambda c: c.execute(text("UPDATE audit_run SET command_id = NULL WHERE run_id = :r"), {"r": run}), "AM003")
    # The controls: the command of a run that is no restart is as it was (the recovery drills rewrite receipts), and so is any column the guard does
    # not freeze.
    _accepted(at_head, lambda c: c.execute(text("UPDATE audit_run SET command_id = :c WHERE run_id = :r"), {"r": plain, "c": world.command(c)}))
    _accepted(at_head, lambda c: c.execute(text("UPDATE audit_run SET command_id = NULL WHERE run_id = :r"), {"r": plain}))
    _accepted(at_head, lambda c: c.execute(text("UPDATE audit_run SET updated_at = now() WHERE run_id = :r"), {"r": run}))
    with at_head.connect() as connection:
        assert connection.execute(text("SELECT restart_point FROM audit_run WHERE run_id = :r"), {"r": run}).scalar_one() == "review"


# -- the link of the source to the run that replaced it ---------------------------------------------


def test_the_run_that_replaced_a_tombstoned_source_is_the_run_of_the_tombstones_command(at_head: Engine) -> None:
    world = World(at_head)
    with at_head.begin() as connection:
        source = world.ended_source(connection)
        # An earlier restart of the same source that was cancelled stays a run of its own and is not the replacement.
        earlier, _ = world.restart(connection, source, point="text", state="cancelled")
        replacing, command = world.restart(connection, source, state="validating")
        # Before the new run publishes the source has no tombstone and nothing points forward from it: the new run points back.
        assert _replaced_by(connection, source) == []
        assert connection.execute(text("SELECT started_from_run_id FROM audit_run WHERE run_id = :r"), {"r": replacing}).scalar_one() == source
        # The new run publishes; the source is tombstoned in the same transaction with the new run's command.
        connection.execute(text("UPDATE audit_run SET state = 'published', terminal_at = now() WHERE run_id = :r"), {"r": replacing})
        world.tombstone(connection, source, command)
    with at_head.connect() as connection:
        assert _replaced_by(connection, source) == [replacing] and replacing != earlier
        assert connection.execute(text("SELECT count(*) FROM audit_run WHERE started_from_run_id = :s"), {"s": source}).scalar_one() == 2


def test_a_tombstone_by_a_restart_is_refused_until_the_new_run_has_published_and_for_any_run_but_its_source(at_head: Engine) -> None:
    world = World(at_head)
    with at_head.begin() as connection:
        source = world.ended_source(connection)
        stranger = world.ended_source(connection, "failed")
        run, command = world.restart(connection, source, state="running")
        failed, failed_command = world.restart(connection, world.ended_source(connection), state="failed")
    # Not yet published: the source stays listed (R-155g).
    _refused(at_head, lambda c: world.tombstone(c, source, command), "AM001")
    # A restart that failed deletes nothing, ever.
    failed_source = _source_of(at_head, failed)
    _refused(at_head, lambda c: world.tombstone(c, failed_source, failed_command), "AM001")
    with at_head.begin() as connection:
        connection.execute(text("UPDATE audit_run SET state = 'validating' WHERE run_id = :r"), {"r": run})
        connection.execute(text("UPDATE audit_run SET state = 'published', terminal_at = now() WHERE run_id = :r"), {"r": run})
    # Published, but another run is not the restart's source.
    _refused(at_head, lambda c: world.tombstone(c, stranger, command), "AM001")
    # The control: the source, the same row that was refused a moment ago.
    with at_head.begin() as connection:
        world.tombstone(connection, source, command)
    assert _count(at_head, "audit_run_deletion") == 1


def _source_of(engine: Engine, run: str) -> str:
    with engine.connect() as connection:
        return str(connection.execute(text("SELECT started_from_run_id FROM audit_run WHERE run_id = :r"), {"r": run}).scalar_one())


def test_a_plain_delete_replaces_nothing_and_is_not_held_by_the_restart_guard(at_head: Engine) -> None:
    world = World(at_head)
    with at_head.begin() as connection:
        source = world.ended_source(connection)
        restart, _ = world.restart(connection, source, state="running")
        deleted = world.ended_source(connection, "cancelled")
        world.tombstone(connection, deleted, world.command(connection, "delete_audit_run"))
    with at_head.connect() as connection:
        assert _replaced_by(connection, deleted) == []
        assert _replaced_by(connection, source) == []
    assert restart


# -- the decision ledger ----------------------------------------------------------------------------


def test_no_constraint_of_the_decision_ledger_compares_versions_so_a_carry_inside_one_version_is_admitted(at_head: Engine) -> None:
    """``carried_from_decision_id`` is held by its shape, not-self, the verdict arm and a foreign key; none looks at a version (a command does).
    A restart carries between two findings of one version, made by two runs; a comment is carried as a comment event with no link."""
    with at_head.connect() as connection:
        defined = " ".join(row[0] for row in connection.execute(text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid = 'expert_decision_event'::regclass "
            "AND conname LIKE 'ck_expert_decision_event_carried_from%'")))
        assert "version" not in defined and defined.count("carried_from_decision_id") >= 4
        triggers = [row[0] for row in connection.execute(text(
            "SELECT pg_get_triggerdef(oid) FROM pg_trigger WHERE tgrelid = 'expert_decision_event'::regclass AND NOT tgisinternal"))]
        assert triggers and all("version" not in definition for definition in triggers)

    version, project = "ver_01ARZ3NDEKTSV4RRFFQ69G5FAV", "prj_01ARZ3NDEKTSV4RRFFQ69G5FAV"
    source_finding, target_finding = "fnd_01ARZ3NDEKTSV4RRFFQ69G5FAV", "fnd_01ARZ3NDEKTSV4RRFFQ69G5FAW"
    source_run, target_run = str(RunId.new()), str(RunId.new())
    source_decision, carried_decision = "dec_01ARZ3NDEKTSV4RRFFQ69G5FAV", "dec_01ARZ3NDEKTSV4RRFFQ69G5FAW"
    insert = text(
        "INSERT INTO expert_decision_event (decision_id, finding_uid, finding_observation_id, event_type, verdict, comment, author_label, "
        "carried_from_decision_id) VALUES (:id, :f, 'fobs_01ARZ3NDEKTSV4RRFFQ69G5FAV', :t, :v, :c, 'Эксперт', :from)")

    def plant(connection: Connection) -> None:
        # The superuser of the lane's database switches off the foreign keys and the append-only trigger for these rows only (as the 0058 test
        # does); the CHECKs, which are what is under test, stay in force.
        connection.execute(text("SET LOCAL session_replication_role = replica"))
        for finding, run in ((source_finding, source_run), (target_finding, target_run)):
            connection.execute(text(
                "INSERT INTO finding (finding_uid, project_uid, version_uid, allocated_by_run_id, category) "
                "VALUES (:f, :p, :v, :r, 'dimensions')"), {"f": finding, "p": project, "v": version, "r": run})
        connection.execute(insert, {"id": source_decision, "f": source_finding, "t": "accept", "v": "accepted", "c": None, "from": None})
        # The verdict of the source, carried to the finding of the new run of the same version, with its link.
        connection.execute(insert, {"id": carried_decision, "f": target_finding, "t": "accept", "v": "accepted", "c": None, "from": source_decision})
        # The comment of the source, carried as a comment event with provenance text and no link.
        connection.execute(insert, {"id": "dec_01ARZ3NDEKTSV4RRFFQ69G5FAX", "f": target_finding, "t": "comment", "v": None,
                                    "c": "Перенесено из прогона " + source_run, "from": None})
        assert {row[0] for row in connection.execute(text(
            "SELECT version_uid FROM finding WHERE finding_uid IN (:a, :b)"), {"a": source_finding, "b": target_finding})} == {version}
        assert connection.execute(text(
            "SELECT carried_from_decision_id FROM expert_decision_event WHERE decision_id = :d"), {"d": carried_decision}).scalar_one() == source_decision

    _accepted(at_head, plant)

    def plant_comment_with_a_link(connection: Connection) -> None:
        plant(connection)
        with connection.begin_nested():
            connection.execute(insert, {"id": "dec_01ARZ3NDEKTSV4RRFFQ69G5FAY", "f": target_finding, "t": "comment", "v": None, "c": "x",
                                        "from": source_decision})

    # The control: the verdict arm of 0058 still refuses a comment that carries a link, for a restart as for a new version.
    with pytest.raises(DBAPIError) as caught:
        _accepted(at_head, plant_comment_with_a_link)
    assert "ck_expert_decision_event_carried_from_verdict" in str(caught.value.orig)


# -- the downgrade ----------------------------------------------------------------------------------


def test_the_downgrade_refuses_while_a_run_holds_a_restart_point_and_restores_0070_with_none(
    at_previous: tuple[Engine, str], foundation_command: Any,
) -> None:
    engine, url = at_previous
    done = foundation_command(_alembic("upgrade", THIS), url)
    assert done.returncode == 0, done.describe()
    world = World(engine)
    with engine.begin() as connection:
        source = world.ended_source(connection)
        restart, _ = world.restart(connection, source, point="correction", state="cancelled")

    refused = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert refused.returncode != 0, refused.describe()
    assert "restart_point" in refused.describe()
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == THIS
        assert connection.execute(text("SELECT restart_point FROM audit_run WHERE run_id = :r"), {"r": restart}).scalar_one() == "correction"

    # The control: with no restart run the same downgrade goes through (the run is planted away under the superuser, as the 0058 test does).
    with engine.begin() as connection:
        connection.execute(text("SET LOCAL session_replication_role = replica"))
        connection.execute(text("DELETE FROM audit_run WHERE run_id = :r"), {"r": restart})
    downgraded = foundation_command(_alembic("downgrade", PREVIOUS), url)
    assert downgraded.returncode == 0, downgraded.describe()
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == PREVIOUS
        assert connection.execute(text(
            "SELECT count(*) FROM information_schema.columns WHERE table_name = 'audit_run' AND column_name = 'restart_point'")).scalar_one() == 0
        assert connection.execute(text("SELECT to_regclass('ux_audit_run_active_restart')")).scalar_one() is None
        assert connection.execute(text("SELECT to_regproc('am_guard_run_deletion_by_restart')")).scalar_one() is None
        # 0060's rule is back: a source with a start stage is the only shape, and 0064's frozen list no longer holds command_id.
        pair = connection.execute(text("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = :n"), {"n": PAIR}).scalar_one()
        assert "restart_point" not in pair
        guard = connection.execute(text(
            "SELECT pg_get_triggerdef(oid) FROM pg_trigger WHERE tgname = 'trg_audit_run_frozen_guard'")).scalar_one()
        assert "'publication_mode'" in guard and "restart_point" not in guard
        assert connection.execute(text("SELECT count(*) FROM pg_trigger WHERE tgname = 'trg_audit_run_restart_command_frozen'")).scalar_one() == 0

    upgraded = foundation_command(_alembic("upgrade", THIS), url)
    assert upgraded.returncode == 0, upgraded.describe()
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == THIS
        guard = connection.execute(text(
            "SELECT pg_get_triggerdef(oid) FROM pg_trigger WHERE tgname = 'trg_audit_run_frozen_guard'")).scalar_one()
        assert "'restart_point'" in guard
        assert connection.execute(text("SELECT count(*) FROM pg_trigger WHERE tgname = 'trg_audit_run_restart_command_frozen'")).scalar_one() == 1
