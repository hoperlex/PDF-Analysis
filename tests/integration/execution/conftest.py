"""Fixtures for this suite: the run-suite harness, loaded by explicit path.

The same harness ``tests/integration/runs/conftest.py`` binds (real PostgreSQL and MinIO,
never a skip), registered under the same module name so one copy serves every suite. Its
autouse ``_no_network`` is deliberately NOT bound here: the worker service opens its own
``LISTEN`` connection and its slot threads open their own database and object-store
connections, which that guard would refuse. Nothing here can spend: every adapter these
suites construct is the recorded one, and the root ``conftest`` has already removed every
provider-selecting variable from the process.

``sessions`` is a **committing** factory (the worker and a second process only see what is
committed), and ``quiet_queue`` keeps Jobs other suites left in the shared lane database
out of reach of a worker started here (D-152's lesson).
"""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

_HARNESS_NAME = "b5_run_harness"
_HARNESS_PATH = Path(__file__).resolve().parents[1] / "runs" / "harness.py"
if _HARNESS_NAME in sys.modules:
    harness: ModuleType = sys.modules[_HARNESS_NAME]
else:
    _spec = importlib.util.spec_from_file_location(_HARNESS_NAME, _HARNESS_PATH)
    assert _spec is not None and _spec.loader is not None
    harness = importlib.util.module_from_spec(_spec)
    sys.modules[_HARNESS_NAME] = harness
    _spec.loader.exec_module(harness)

engine = harness.engine
blob_store = harness.blob_store
session = harness.session
provider_config = harness.provider_config
recorded_adapter = harness.recorded_adapter


@pytest.fixture(scope="session")
def helpers() -> ModuleType:
    return harness


@pytest.fixture
def sessions(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


@pytest.fixture
def quiet_queue(sessions: sessionmaker[Session]) -> Iterator[None]:
    """Reclaim leftovers first, then park every foreign queued Job until the test ends."""
    from auditmanager.jobs.public import JobRepository

    with sessions() as setup:
        JobRepository().reclaim_expired(setup)
        setup.commit()
    with sessions() as setup:
        parked = setup.execute(text(
            "SELECT job_id, available_at FROM job WHERE state = 'queued' FOR UPDATE"
        )).all()
        setup.execute(text(
            "UPDATE job SET available_at = timestamptz '2099-01-01' WHERE state = 'queued'"
        ))
        paused = setup.execute(text(
            "SELECT paused FROM execution_control WHERE singleton"
        )).scalar_one_or_none()
        JobRepository().set_paused(setup, paused=False)
        setup.commit()
    try:
        yield
    finally:
        with sessions() as cleanup:
            for job_id, available_at in parked:
                cleanup.execute(text(
                    "UPDATE job SET available_at = :available_at WHERE job_id = :job_id "
                    "AND state = 'queued'"
                ), {"job_id": job_id, "available_at": available_at})
            JobRepository().set_paused(cleanup, paused=bool(paused))
            cleanup.commit()
