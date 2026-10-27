"""PROD-11D-V3-GROUP-QUEUE-01: accepting an AR v3 group queues its six Runs, as accepting a Run does.

``AR-V3-BETA-ACCEPT-RECORDED-01`` found that ``RunAdapter.start_ar_v3_group`` created the group and six Runs
in ``created`` and nothing else, while ``RunAdapter.start_run`` also (1) advances the Run ``created ->
queued`` and (2) enqueues its Job in the accepting transaction, and (3) after the commit, and only when the
start was not a replay, hands the work to the carrier. In a served process the six Runs therefore stayed
``created`` for ever: no Job existed, so the ``DurableCarrier`` poller (``JobRepository.next_queued_run``: a
queued Job of a queued or running Run) never saw them.

This module measures the start on the stock recorded composition (``build_application``, a sealed synthetic
pack installed from a manifest file, a private migrated database), with the carrier seam observed by the
recorder of ``test_v3_recorded_group_over_http.py`` (``HeldCarrier``: it records what the adapter submits and,
here, never forwards it, so nothing executes and every reading is deterministic). It asserts, right after the
202: six ``queued`` Runs, six ``queued`` Jobs in the same committed transaction, the poller's own query finding
the first of them, one carrier submission per Run in scope order, each made after the commit; a replay of the
same key adds no Job and no submission; and a **second composition on the same database** (a restart of the
process that accepted the request, which died after the 202) finds all six Runs through the same query the
poller runs, one after another, and submits nothing by itself. The poller thread is not started.

The helpers are those of the HTTP acceptance module, loaded by explicit path (a test module is not importable
by name under ``--import-mode=importlib``) and never copied.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from auditmanager.jobs.public import JobRepository
from auditmanager.runs.public import seal_manifest
from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine


def _load(name: str, filename: str) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    path = Path(__file__).resolve().parent / filename
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # before execution: ``@dataclass(slots=True)`` resolves through sys.modules
    spec.loader.exec_module(module)
    return module


accept = _load("prod11d_accept_helpers", "test_v3_recorded_group_over_http.py")
probe = accept.probe
#: The probe's module-scoped fixture: a fresh database migrated to head and dropped afterwards (never the
#: lane's shared database).
probe_database = probe.probe_database

GROUPS = accept.GROUPS
SCOPES = accept.SCOPE_LABELS


@dataclass(slots=True)
class Stand:
    start: Any = None  # the 202 exchange
    again: Any = None  # the same key and body, again
    group_after_restart: Any = None
    run_ids: list[str] = field(default_factory=list)
    db: dict[str, Any] = field(default_factory=dict)


def _committed(factory: sessionmaker[Any], run_id: str | None) -> list[tuple[Any, ...]]:
    """What another connection sees of the Run and its Job: nothing unless the accepting transaction
    committed."""
    return accept._rows(factory, """
        SELECT r.state, j.state FROM audit_run r JOIN job j ON j.run_id = r.run_id WHERE r.run_id = :r
    """, r=run_id)


def _poller_walk(factory: sessionmaker[Any]) -> list[str]:
    """What the serving poller sees: its own repository query, asked until it answers ``None``, each answer
    handed back as ``submitted`` the way the carrier's pool holds a Run it has taken."""
    taken: list[str] = []
    with factory() as session:
        while (run_id := JobRepository().next_queued_run(session, submitted=taken)) is not None:
            taken.append(run_id)
            assert len(taken) <= 12, "the queue never ran dry"
    return taken


def _drive(probe_database_url: str, blob_store: Any, recordings: Path, manifest_dir: Path) -> Stand:
    out = Stand()
    engine = create_database_engine(DatabaseSettings(url=parse_database_url(probe_database_url)))
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    built: list[Any] = []
    try:
        with factory() as session, session.begin():
            probe._require_probe_database(session.execute(text("SELECT current_database()")).scalar_one())
            expert = accept._account(session, "queue-expert", ("expert",))
            served = probe._publish_source(session, blob_store, title="AR v3 group queue",
                                           register_blob=True, actor=str(expert.user_uid))
            pack = probe._seed_norms(session, blob_store, served, str(expert.user_uid))
        token = accept._token(expert)
        manifest = manifest_dir / "ar-v3-pack.json"
        manifest.write_bytes(seal_manifest(pack, accept.REVIEW))
        environ = accept._environment(probe_database_url, manifest)
        body = {"version_uid": served.version_uid}

        # The process that accepts the request. Its carrier seam is observed: what the adapter submits is
        # recorded with what another connection can see of that Run at the moment of the submit.
        first = accept._build(environ, recordings)
        built.append(first)
        first.held.observe = lambda run_id: _committed(factory, run_id)
        out.db["before"] = accept._counts(factory, served.version_uid)

        out.start = first.wire.call("POST", GROUPS, token=token, key="queue-start", body=body)
        group = out.start.data
        out.run_ids = [member["run_id"] for member in group["members"]]
        out.db["after_start"] = accept._counts(factory, served.version_uid)
        out.db["runs"] = accept._runs_of_group(factory, group["group_id"])
        out.db["jobs"] = accept._jobs_of_group(factory, group["group_id"])
        out.db["submitted"] = list(first.held.submitted)
        out.db["observed"] = list(first.held.observed)
        with factory() as session:
            out.db["next_queued_run"] = JobRepository().next_queued_run(session)

        out.again = first.wire.call("POST", GROUPS, token=token, key="queue-start", body=body)
        out.db["after_replay"] = accept._counts(factory, served.version_uid)
        out.db["jobs_after_replay"] = accept._jobs_of_group(factory, group["group_id"])
        out.db["runs_after_replay"] = accept._runs_of_group(factory, group["group_id"])
        out.db["submitted_after_replay"] = list(first.held.submitted)
        out.db["observed_after_replay"] = list(first.held.observed)

        # The process dies after the 202: its recorded submissions were never run. A new composition on
        # the same database is the restarted process; its carrier is a stock, unstarted ``DurableCarrier``.
        first.application.carrier.shutdown()
        first.application.session_factory.kw["bind"].dispose()
        second = accept._build(environ, recordings)
        built.append(second)
        with second.application.session_factory() as session:
            out.db["restart_first_pick"] = JobRepository().next_queued_run(session)
        out.db["restart_walk"] = _poller_walk(second.application.session_factory)
        out.db["restart_submitted"] = list(second.held.submitted)
        out.group_after_restart = second.wire.call("GET", f"{GROUPS}/{group['group_id']}", token=token)
    finally:
        for item in built:
            item.replay.release.set()
            item.application.carrier.shutdown()
            item.application.session_factory.kw["bind"].dispose()
        engine.dispose()
    return out


@pytest.fixture(scope="module")
def stand(probe_database: str, blob_store: Any, tmp_path_factory: pytest.TempPathFactory) -> Stand:
    return _drive(probe_database, blob_store, tmp_path_factory.mktemp("queue-recordings"),
                  tmp_path_factory.mktemp("queue-pack"))


def test_the_start_is_accepted_with_six_queued_runs(stand: Stand) -> None:
    """The 202 says what was accepted: a group of six, every Run ``queued`` (not ``created``), and the
    database says the same."""
    assert stand.start.status == 202
    assert stand.db["before"] == {"groups": 0, "runs": 0, "jobs": 0}
    assert [member["scope_id"] for member in stand.start.data["members"]] == list(SCOPES)
    assert [member["state"] for member in stand.start.data["members"]] == ["queued"] * 6
    assert stand.db["runs"] == [(scope, "queued") for scope in SCOPES]


def test_the_start_enqueues_one_queued_job_per_run_in_the_same_transaction(stand: Stand) -> None:
    """Six Jobs, one per Run, all ``queued``; a connection other than the request's sees every Run
    ``queued`` with its Job ``queued`` at the moment of the submit, so Run, Job and group were committed
    together."""
    assert stand.db["after_start"] == {"groups": 1, "runs": 6, "jobs": 6}
    assert stand.db["jobs"] == [(scope, "queued") for scope in SCOPES]


def test_the_pollers_query_finds_the_first_run_right_after_the_start(stand: Stand) -> None:
    """``JobRepository.next_queued_run`` is the query the ``DurableCarrier`` poller runs: before this task it
    answered ``None`` here."""
    assert stand.db["next_queued_run"] == stand.run_ids[0]


def test_the_carrier_received_one_submission_per_run_in_scope_order(stand: Stand) -> None:
    """The unit of work is ``RunAdapter._job(run_id)`` (the recorder reads the Run id from the job the
    adapter built), submitted once for each of the six Runs, in the group's order."""
    assert stand.run_ids == [member["run_id"] for member in stand.start.data["members"]]
    assert len(set(stand.run_ids)) == 6
    assert stand.db["submitted"] == stand.run_ids


def test_every_submission_was_made_after_the_commit(stand: Stand) -> None:
    """At the moment of each ``submit`` a separate connection already sees that Run ``queued`` with a
    ``queued`` Job: the carrier is never handed work that a crash would erase."""
    assert stand.db["observed"] == [[("queued", "queued")]] * 6


def test_a_replay_of_the_same_key_adds_no_job_and_no_submission(stand: Stand) -> None:
    again = stand.again
    assert again.status == 202
    assert again.data["group_id"] == stand.start.data["group_id"]
    assert [member["run_id"] for member in again.data["members"]] == stand.run_ids
    assert stand.db["after_replay"] == {"groups": 1, "runs": 6, "jobs": 6}
    assert stand.db["jobs_after_replay"] == stand.db["jobs"]
    assert stand.db["runs_after_replay"] == stand.db["runs"]
    assert stand.db["submitted_after_replay"] == stand.db["submitted"] == stand.run_ids
    assert stand.db["observed_after_replay"] == stand.db["observed"]


def test_after_a_restart_the_pollers_query_finds_all_six_runs_one_after_another(stand: Stand) -> None:
    """The process that accepted the request died after the 202 (nothing it submitted ran). A new
    composition on the same database finds the Runs from the database alone: the first Run first, then each
    next one as the previous is taken, in scope order, and then nothing."""
    assert stand.db["restart_first_pick"] == stand.run_ids[0]
    assert stand.db["restart_walk"] == stand.run_ids


def test_a_restarted_process_submits_nothing_by_itself_and_still_reads_queued(stand: Stand) -> None:
    """Discovery is the poller's job: a restarted ``RunAdapter`` hands nothing to the carrier."""
    assert stand.db["restart_submitted"] == []
    assert stand.group_after_restart.status == 200
    assert [member["state"] for member in stand.group_after_restart.data["members"]] == ["queued"] * 6
