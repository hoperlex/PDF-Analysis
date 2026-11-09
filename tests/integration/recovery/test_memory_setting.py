"""`DECISION-MEMORY-01` phase M2: the operator tool ``scripts/recovery/memory_setting.py`` shows and journals the installation settings.

On a clone of the migrated schema, as the owner. Shown: nothing journalled reads as the defaults (``test``, ``off``); a change journals one
row with the next revision, the admin's ``usr_`` identity (never the login) and the owner's permission when given; the same value again records
nothing; ``training_use = on`` is refused without the owner's permission before the database is touched (and the table's CHECK would refuse it
too); an expert's login, an unknown name or value and a mistyped database are refused; and every guard is shown able to fail on a copy of the
source with the block deleted. The capture reading the journal is ``test_decision_memory_status``.

`D-496`: a change of ``data_class`` is refused while the ledger holds accept/reject decisions the memory has not captured, and "not captured" is
what the worker's sweep says it is -- the tool's count and the sweep's backlog are held to one number on the same committed ledger, and the
real sweep is run to take the backlog to zero. A decision that is being written while the flip runs is not missed (the ledger table is locked
for the count and the journal write; shown with a real second transaction and a real second process, and shown able to fail).
"""

from __future__ import annotations

import contextlib
import io
import os
import re
import subprocess
import sys
import time
import types
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.bootstrap.adapters import _UNCAPTURED_EVENTS, MemoryCaptureAssembler, MemoryCaptureSweep, MemorySweepReport
from auditmanager.decisions import record_decision
from auditmanager.decisions.public import register_decision_recorded, registered_decision_recorded
from auditmanager.findings import TextLayer
from auditmanager.shared.db.engine import create_database_engine
from scripts.recovery import memory_setting as tool
from tests.integration.decisions.conftest import PublishedRun, _text_layer_artifact  # type: ignore[import-not-found]

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "scripts/recovery/memory_setting.py"
REF = "owner message 2026-11-09, settings test"


@pytest.fixture
def clone(migrated_database_factory: Any, monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    settings = migrated_database_factory()
    monkeypatch.setenv("DATABASE_URL", settings.url.render_as_string(hide_password=False))
    engine = create_database_engine(settings)
    try:
        yield types.SimpleNamespace(engine=engine, database=str(settings.url.database))
    finally:
        engine.dispose()


def run(module: types.ModuleType, clone: Any, *argv: str, database: str | None = None) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stderr(err):
        code = module.run(["--database", database or clone.database, *argv], out=out)
    return code, out.getvalue(), err.getvalue()


def journal(clone: Any) -> list[tuple[Any, ...]]:
    with clone.engine.connect() as connection:
        return [tuple(row) for row in connection.execute(text(
            "SELECT setting_name, revision, value, actor_user_uid, owner_permission_ref FROM decision_memory_setting_event "
            "ORDER BY setting_name, revision"))]


_BLOCK = r"^[ \t]*# >>> guard: {name}\n.*?^[ \t]*# <<< guard: {name}\n"
_MUTANTS = iter(range(10**6))


def mutant(*guards: str) -> types.ModuleType:
    source = SOURCE.read_text(encoding="utf-8")
    for name in guards:
        source, matched = re.subn(_BLOCK.format(name=re.escape(name)), "", source, flags=re.DOTALL | re.MULTILINE)
        assert matched == 1, f"the guard markers for {name!r} are not a single block"
    module = types.ModuleType(f"scripts.recovery.memory_setting_mutant_{next(_MUTANTS)}")
    module.__file__ = str(SOURCE)
    sys.modules[module.__name__] = module
    exec(compile(source, f"<memory_setting without {guards}>", "exec"), module.__dict__)  # noqa: S102
    return module


def test_nothing_journalled_reads_as_the_safe_defaults(clone: Any) -> None:
    code, out, err = run(tool, clone, "show")
    assert code == 0 and err == "", (out, err)
    assert "data_class: test (default; default test)" in out and "training_use: off (default; default off)" in out
    assert journal(clone) == []


def test_a_change_is_journalled_once_with_the_admins_identity_and_the_same_value_again_records_nothing(clone: Any) -> None:
    admin = str(clone.engine.connect().execute(text("SELECT user_uid FROM app_user WHERE login = 'admin'")).scalar_one())
    code, out, err = run(tool, clone, "set", "data_class", "real", "--actor", "admin")
    assert code == 0, (out, err)
    assert "test -> real (revision 1)" in out and "keep the class they were captured with" in out
    assert journal(clone) == [("data_class", 1, "real", admin, None)]          # the identity, never the login

    code, out, _ = run(tool, clone, "set", "data_class", "real", "--actor", "admin")
    assert code == 0 and "already real; nothing to do" in out and len(journal(clone)) == 1

    assert run(tool, clone, "set", "data_class", "test", "--actor", "admin")[0] == 0
    code, out, _ = run(tool, clone, "set", "training_use", "on", "--actor", "admin", "--owner-permission-ref", REF)
    assert code == 0 and "off -> on (revision 1)" in out, out
    assert journal(clone) == [("data_class", 1, "real", admin, None), ("data_class", 2, "test", admin, None),
                              ("training_use", 1, "on", admin, REF)]
    shown = run(tool, clone, "show")[1]
    assert "data_class: test (revision 2; default test)" in shown and "training_use: on (revision 1; default off)" in shown


def test_the_refusals_change_nothing(clone: Any) -> None:
    for argv, says in [
        (["set", "training_use", "on", "--actor", "admin"], "--owner-permission-ref"),            # an on releases content off the host
        (["set", "data_class", "production", "--actor", "admin"], "admits ['test', 'real']"),
        (["set", "retention", "forever", "--actor", "admin"], "admits []"),
        (["set", "training_use", "real", "--actor", "admin"], "admits ['off', 'on']"),
        (["set", "data_class", "real", "--actor", "nobody"], "--actor must be the login of an active"),
        (["set", "data_class", "real", "--actor", "admin", "--owner-permission-ref", "x" * 201], "one line of at most 200"),
        (["set", "data_class", "real", "--actor", "admin", "--owner-permission-ref", "two\nlines"], "one line of at most 200"),
    ]:
        code, out, err = run(tool, clone, *argv)
        assert code == tool.EXIT_REFUSED and says in err, (argv, code, out, err)
    code, out, err = run(tool, clone, "show", database="some_other_database")
    assert code == tool.EXIT_REFUSED and "not the connected database" in err
    assert journal(clone) == []


def test_the_guards_are_shown_able_to_fail(clone: Any) -> None:
    on_without_permission = ["set", "training_use", "on", "--actor", "admin"]
    assert run(tool, clone, *on_without_permission)[0] == tool.EXIT_REFUSED
    code, out, err = run(mutant("training-needs-permission"), clone, *on_without_permission)
    assert code == tool.EXIT_FAILED and "ck_decision_memory_setting_event_on_needs_permission" in err   # only the table's CHECK is left
    assert journal(clone) == []

    code, out, err = run(mutant("value-in-list"), clone, "set", "data_class", "production", "--actor", "admin")
    assert code == tool.EXIT_FAILED and "ck_decision_memory_setting_event_value" in err                  # likewise
    code, out, err = run(mutant("names-match"), clone, "show", database="some_other_database")
    assert code == 0, (out, err)                                                                         # without the guard it reads another name's data
    code, out, err = run(mutant("reference-shape"), clone, "set", "data_class", "real", "--actor", "admin",
                         "--owner-permission-ref", "two\nlines")
    assert code == 0 or "one line of at most 200" not in err, err


def test_a_database_at_another_migration_is_refused(clone: Any) -> None:
    with clone.engine.begin() as connection:
        connection.execute(text("UPDATE public.alembic_version SET version_num = '0099_a_future_head'"))
    code, out, err = run(tool, clone, "show")
    assert code == tool.EXIT_REFUSED and "the tool was written for" in err and "0099_a_future_head" in err, (code, out, err)
    code, out, err = run(mutant("head-is-declared"), clone, "show")           # without the guard it reads a schema it was not written for
    assert code == 0 and "data_class: test" in out, (code, out, err)


def test_a_libpq_variable_that_could_redirect_the_connection_is_refused(clone: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """``PGCONNECT_TIMEOUT`` is a libpq variable that redirects nothing, so the copy without the guard can be run without harm."""
    monkeypatch.setenv("PGCONNECT_TIMEOUT", "5")
    code, out, err = run(tool, clone, "show")
    assert code == tool.EXIT_REFUSED and "PGCONNECT_TIMEOUT" in err and "can redirect the connection" in err, (code, out, err)
    code, out, err = run(mutant("no-ambient-libpq"), clone, "show")
    assert code == 0 and "data_class: test" in out, (code, out, err)          # without the guard any PG* variable is honoured silently


# --- D-496: the backlog of the capture, and the flip ---------------------------------------------------------------------


class _Geometry:
    """The object store of the capture, empty: these findings name no block and the portal has no crops."""

    def evidence_boxes_in(self, session: Session, run_id: str) -> dict[str, Any]:
        return {}

    def portal_crops_in(self, session: Session, run_id: str) -> tuple[Any, ...]:
        return ()


class Ledger:
    """A really published run on the clone, committed, and the ways to put decisions in its ledger -- captured or not -- and to sweep."""

    def __init__(self, engine: Any) -> None:
        self.engine = engine
        self.sessions = sessionmaker(bind=engine, expire_on_commit=False, future=True)
        with self.sessions() as session:
            self.run = PublishedRun(session, TextLayer.from_artifact(_text_layer_artifact()))
            session.commit()
        self.assembler = MemoryCaptureAssembler(geometry=_Geometry())

    def decide(self, event_type: str, finding: int = 1, *, capture: bool = False, session: Session | None = None) -> Any:
        """One ledger event. ``capture`` registers the memory as the ledger's port (as the product does); without it the event is
        the kind the sweep exists for. Committed unless the caller passes the ``session`` whose transaction it wants to keep open."""
        before = registered_decision_recorded()
        register_decision_recorded(self.assembler if capture else None)
        own = session is None
        active = self.sessions() if own else session
        try:
            event = record_decision(
                active,
                finding_uid=self.run.finding_uid if finding == 1 else self.run.second_finding_uid,
                finding_observation_id=self.run.finding_observation_id if finding == 1 else self.run.second_finding_observation_id,
                event_type=event_type, comment="проверено по странице", author_label="Петрова А.", author_user_uid=None)
            if own:
                active.commit()
            return event
        finally:
            if own:
                active.close()
            register_decision_recorded(before)

    def sweep(self) -> MemorySweepReport:
        return MemoryCaptureSweep(self.sessions, self.assembler, batch=500).run_once()

    def sweeps_backlog(self) -> int:
        """What the worker's sweep would pick up, by ITS query: every row, from the start, in one batch."""
        with self.sessions() as session:
            return len(session.execute(_UNCAPTURED_EVENTS, {"after": 0, "batch": 10_000}).mappings().all())

    def classes(self) -> dict[str, int]:
        with self.sessions() as session:
            return {str(k): int(n) for k, n in session.execute(text(
                "SELECT data_class, count(*) FROM decision_memory_case GROUP BY data_class"))}


@pytest.fixture
def ledger(clone: Any) -> Iterator[Ledger]:
    before = registered_decision_recorded()
    try:
        yield Ledger(clone.engine)
    finally:
        register_decision_recorded(before)


def tools_backlog(clone: Any) -> int:
    with clone.engine.connect() as connection:
        return tool.uncaptured_decisions(connection)


FLIP = ("set", "data_class", "real", "--actor", "admin")
SAYS_BACKLOG = "accept/reject decision(s) of the ledger are not captured by the decision memory yet"


def test_the_flip_is_refused_with_the_sweeps_own_count_and_allowed_when_the_real_sweep_has_emptied_it(clone: Any, ledger: Ledger) -> None:
    ledger.decide("accept", 1, capture=True)       # captured in its own transaction, as the product does
    ledger.decide("comment", 1)                    # a comment is never captured: not backlog
    ledger.decide("accept", 2)                     # decided where no memory was registered: backlog
    ledger.decide("reject", 2)
    assert tools_backlog(clone) == ledger.sweeps_backlog() == 2

    code, out, err = run(tool, clone, *FLIP)
    assert code == tool.EXIT_REFUSED and err.startswith("memory_setting: REFUSED: 2 " + SAYS_BACKLOG), (code, out, err)
    assert "Let the worker's sweep finish" in err and "There is no override" in err and "Nothing was changed" in err
    assert journal(clone) == []
    assert "uncaptured-decisions: 2" in run(tool, clone, "show")[1]

    report = ledger.sweep()                         # the real sweep, the real assembler
    assert (report.captured, report.failed) == (2, 0)      # the number the tool refused with is the number the sweep captured
    assert tools_backlog(clone) == ledger.sweeps_backlog() == 0
    code, out, err = run(tool, clone, *FLIP)
    assert code == 0 and "test -> real (revision 1)" in out, (out, err)
    assert [row[:3] for row in journal(clone)] == [("data_class", 1, "real")]
    assert ledger.classes() == {"test": 2}          # what was decided before the flip stayed what it was: two cases, both test
    assert "uncaptured-decisions: 0" in run(tool, clone, "show")[1]


def test_every_change_of_data_class_waits_for_the_sweep_and_nothing_else_does(clone: Any, ledger: Ledger) -> None:
    assert run(tool, clone, *FLIP)[0] == 0
    ledger.decide("reject", 1)                      # a new uncaptured decision, after the flip
    assert tools_backlog(clone) == ledger.sweeps_backlog() == 1

    code, out, err = run(tool, clone, "set", "data_class", "test", "--actor", "admin")       # back, too: the other direction is the same race
    assert code == tool.EXIT_REFUSED and "1 " + SAYS_BACKLOG in err, (code, out, err)
    code, out, err = run(tool, clone, *FLIP)                                                    # the value in force: nothing to do, not a refusal
    assert code == 0 and "already real; nothing to do" in out, (code, out, err)
    code, out, err = run(tool, clone, "set", "training_use", "on", "--actor", "admin", "--owner-permission-ref", REF)   # another setting
    assert code == 0 and "off -> on" in out, (code, out, err)
    assert [row[:3] for row in journal(clone)] == [("data_class", 1, "real"), ("training_use", 1, "on")]

    assert ledger.sweep().captured == 1
    assert run(tool, clone, "set", "data_class", "test", "--actor", "admin")[0] == 0


def _decision_in_flight(clone: Any, ledger: Ledger) -> Session:
    """A decision whose transaction has inserted its ledger event and not committed: it holds the ledger table's row lock."""
    session = Session(clone.engine, expire_on_commit=False)
    ledger.decide("accept", 2, session=session)
    return session


def test_a_decision_written_during_the_flip_is_counted_by_the_flip_that_waited_for_it(clone: Any, ledger: Ledger) -> None:
    """A second transaction has a decision in flight; a second PROCESS runs the flip; the flip waits, the decision commits, the flip refuses."""
    inflight = _decision_in_flight(clone, ledger)
    environment = {**os.environ, "MEMORY_SETTING_LOCK_TIMEOUT": "60s", "PYTHONPATH": f"{ROOT / 'src'}{os.pathsep}{ROOT}"}
    process = subprocess.Popen(
        [sys.executable, "-m", "scripts.recovery.memory_setting", "--database", clone.database, *FLIP],
        cwd=ROOT, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        deadline = time.monotonic() + 60
        waiting = 0
        while time.monotonic() < deadline and not waiting:
            with clone.engine.connect() as connection:
                waiting = int(connection.execute(text(
                    "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND wait_event_type = 'Lock' "
                    "AND query LIKE 'LOCK TABLE public.expert_decision_event%'")).scalar_one())
            if not waiting:
                assert process.poll() is None, "the flip ended without waiting for the decision in flight"
                time.sleep(0.2)
        assert waiting, "the flip never queued behind the decision in flight"
        assert journal(clone) == []                 # it has not flipped, and it cannot until the decision has committed
        inflight.commit()
        out, err = process.communicate(timeout=60)
    finally:
        inflight.close()
        if process.poll() is None:
            process.kill()                          # the process this test started, by its own handle
            process.communicate()
    assert process.returncode == tool.EXIT_REFUSED and "1 " + SAYS_BACKLOG in err, (process.returncode, out, err)
    assert journal(clone) == [] and tools_backlog(clone) == ledger.sweeps_backlog() == 1


def test_the_flip_waits_no_longer_than_its_timeout_and_changes_nothing(clone: Any, ledger: Ledger, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEMORY_SETTING_LOCK_TIMEOUT", "1s")
    inflight = _decision_in_flight(clone, ledger)
    try:
        started = time.monotonic()
        code, out, err = run(tool, clone, *FLIP)
        assert code == tool.EXIT_REFUSED and "could not lock within 1s" in err and "Nothing was changed" in err, (code, out, err)
        assert time.monotonic() - started < 30 and journal(clone) == []
    finally:
        inflight.rollback()
        inflight.close()


def test_the_backlog_guard_is_shown_able_to_fail(clone: Any, ledger: Ledger) -> None:
    ledger.decide("accept", 1)
    ledger.decide("reject", 2)
    # no-uncaptured-decisions: without it the flip goes through and the sweep then gives the test-era backlog the NEW class for good
    code, out, err = run(mutant("no-uncaptured-decisions"), clone, *FLIP)
    assert code == 0 and journal(clone) != [], (out, err)
    assert ledger.sweep().captured == 2
    assert ledger.classes() == {"real": 2}          # the reclassification of the backlog that the guard exists to stop


def test_the_lock_guards_are_shown_able_to_fail(clone: Any, ledger: Ledger, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEMORY_SETTING_LOCK_TIMEOUT", "1s")
    # decisions-quiesced: without the lock the count cannot see a decision that has not committed, the flip goes through, and the
    # decision then commits into a ledger whose data_class already says real -- a backlog the flip never counted
    inflight = _decision_in_flight(clone, ledger)
    try:
        code, out, err = run(mutant("decisions-quiesced"), clone, *FLIP)
        assert code == 0 and [row[:3] for row in journal(clone)] == [("data_class", 1, "real")], (out, err)
        inflight.commit()
    finally:
        inflight.close()
    assert tools_backlog(clone) == ledger.sweeps_backlog() == 1
    assert ledger.sweep().captured == 1 and ledger.classes() == {"real": 1}    # the slip: decided around the flip, captured as real

    # lock-available: the timeout is a refusal with words; without the guard it is the database's raw error
    blocked = _decision_in_flight(clone, ledger)
    try:
        code, out, err = run(mutant("lock-available"), clone, "set", "data_class", "test", "--actor", "admin")
        assert code == tool.EXIT_FAILED and "could not lock within" not in err and "lock timeout" in err, (code, out, err)
    finally:
        blocked.rollback()
        blocked.close()


GUARDS_WITH_A_SCENARIO = (
    "value-in-list", "reference-shape", "training-needs-permission", "names-match", "head-is-declared", "no-ambient-libpq",
    "no-uncaptured-decisions", "decisions-quiesced", "lock-available",
)


def test_every_guard_of_the_tool_has_a_scenario_above() -> None:
    """A guard added to the tool without a test that deletes it fails here, which is the reminder to write one (`D-492`)."""
    source = SOURCE.read_text(encoding="utf-8")
    opened = re.findall(r"^[ \t]*# >>> guard: ([a-z0-9-]+)$", source, flags=re.MULTILINE)
    closed = re.findall(r"^[ \t]*# <<< guard: ([a-z0-9-]+)$", source, flags=re.MULTILINE)
    assert opened == closed and sorted(opened) == sorted(GUARDS_WITH_A_SCENARIO)
    for name in opened:                                                       # each deletes to a module that still compiles
        mutant(name)
