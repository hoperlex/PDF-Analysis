"""`D-577`, `D-621`: the seed of ``tools/measure/perf`` still builds its volume against the migrated schema, with every trigger on.

The seed is plain SQL against a long list of tables, so the way it rots is a migration: a column renamed, a constraint added, a trigger that
now refuses a row. ``tests/unit/measure/test_perf_harness.py`` shows without a database that the harness imports and that the product names it
reaches for exist; this builds the SMOKE volume (the one ``perf_stand.sh --smoke`` builds) on a fresh clone of the migrated template and
reads it back through the product's own read models:

* ``seed_d463``: 12 + 8 documents, runs of every kind, findings and expert events, price lists, passes with proposals and decisions;
  ``DocumentAuditReadModel.audits`` then answers for the page project's versions with non-zero finding and optimisation counts;
* ``seed_memory``: the decision memory grown to 150 cases and then to 200 (a second call adds the difference, a call that asks for no more
  adds nothing); ``MemoryReader.list_cases`` and ``counts`` answer over it, and the status events (withdrawn, forgotten) are in it.

Nothing is disabled to make it pass: a trigger that refuses a row fails the seed, which is the point.
"""

from __future__ import annotations

import importlib.util
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from auditmanager.dashboard import DocumentAuditReadModel
from auditmanager.decision_memory.reads import MemoryReader
from tests.integration.db.conftest import (  # type: ignore[import-not-found]  # noqa: F401
    configured_settings,
    maintenance_engine,
    migrated_database,
    migrated_database_factory,
    migrated_engine,
    migrated_template,
)

SEED = Path(__file__).resolve().parents[3] / "tools" / "measure" / "perf" / "perf_seed.py"
SMOKE = {
    "PERF_P1_DOCS": "12", "PERF_P2_DOCS": "8", "PERF_PASS_SIZES": "20,30,40", "PERF_OLD_PASS_SIZE": "25", "PERF_P2_PASS_SIZE": "10",
}


@pytest.fixture
def perf_seed(monkeypatch: pytest.MonkeyPatch) -> Iterator[ModuleType]:
    """The seed module, loaded afresh at the smoke scale (it reads its scale from the environment at import)."""
    for name, value in SMOKE.items():
        monkeypatch.setenv(name, value)
    spec = importlib.util.spec_from_file_location("perf_seed_under_test", SEED)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    yield module


def scalar(engine: Engine, sql: str) -> int:
    with engine.connect() as conn:
        return int(conn.execute(text(sql)).scalar_one())


def test_the_smoke_volume_builds_and_the_read_model_answers_over_it(migrated_engine: Engine, perf_seed: ModuleType) -> None:
    assert perf_seed.scale() == {
        "p1_documents": 12, "p2_documents": 8, "pass_sizes": [20, 30, 40], "old_pass_size": 25, "p2_pass_size": 10,
    }
    ids = perf_seed.prepare(migrated_engine)
    perf_seed.seed_d463(migrated_engine, ids)

    assert scalar(migrated_engine, "SELECT count(*) FROM document") == 20
    assert scalar(migrated_engine, "SELECT count(*) FROM project") == 2
    assert scalar(migrated_engine, "SELECT count(*) FROM audit_run WHERE state = 'published'") > 0
    assert scalar(migrated_engine, "SELECT count(*) FROM audit_run WHERE state = 'failed'") > 0, "the failed newer run is part of the volume"
    assert scalar(migrated_engine, "SELECT count(*) FROM finding") > 100
    assert scalar(migrated_engine, "SELECT count(*) FROM expert_decision_event") > 0
    assert scalar(migrated_engine, "SELECT count(*) FROM optimisation_pass") > 0
    proposals = scalar(migrated_engine, "SELECT count(*) FROM optimisation_proposal")
    assert proposals >= 12 * 20, "every page-project document has a latest pass of at least 20 proposals"
    assert scalar(migrated_engine, "SELECT count(*) FROM optimisation_proposal_decision") > 0
    # the scaffolding the measurement must not see is gone
    for table in ("perf_dec_rows", "perf_dec", "perf_find", "perf_pass_plan"):
        assert scalar(migrated_engine, f"SELECT count(*) FROM pg_tables WHERE tablename = '{table}'") == 0, table

    # read back through the product: the audits of the page project's current versions carry findings and optimisation counts
    with Session(migrated_engine) as session:
        versions = [
            row[0]
            for row in session.execute(
                text(
                    "SELECT d.current_version_uid FROM document d WHERE d.project_uid = :p ORDER BY 1"
                ),
                {"p": ids["prj:1"]},
            )
        ]
        assert len(versions) == 12
        audits = DocumentAuditReadModel().audits(session, version_uids=versions)
    assert set(audits) == set(versions)
    assert all(audit.finding_count > 0 for audit in audits.values()), "every page-project document has a published run with findings"
    assert all((audit.optimisation_proposal_count or 0) >= 20 for audit in audits.values())
    assert sum(audit.optimisation_undecided_count or 0 for audit in audits.values()) > 0


def test_the_memory_grows_to_the_asked_size_and_only_by_the_difference(migrated_engine: Engine, perf_seed: ModuleType) -> None:
    ids = perf_seed.prepare(migrated_engine)
    perf_seed.seed_memory(migrated_engine, ids, 150)
    assert scalar(migrated_engine, "SELECT count(*) FROM decision_memory_case") == 150
    assert scalar(migrated_engine, "SELECT count(*) FROM decision_memory_decision") >= 150
    assert scalar(migrated_engine, "SELECT count(*) FROM decision_memory_status_event WHERE kind = 'withdraw'") > 0
    assert scalar(migrated_engine, "SELECT count(*) FROM decision_memory_status_event WHERE kind = 'forget'") > 0

    perf_seed.seed_memory(migrated_engine, ids, 150)
    assert scalar(migrated_engine, "SELECT count(*) FROM decision_memory_case") == 150, "asking for what is there adds nothing"
    perf_seed.seed_memory(migrated_engine, ids, 200)
    assert scalar(migrated_engine, "SELECT count(*) FROM decision_memory_case") == 200

    reader = MemoryReader()
    with Session(migrated_engine) as session:
        page = reader.list_cases(session, limit=50)
        assert len(page.items) == 50
        assert page.next_after is not None
        counts = reader.counts(session)
    assert counts.cases == 200
    assert counts.decisions >= 200
    assert {status for status, _, _ in counts.by_status_and_class} >= {"active", "withdrawn", "forgotten"}
