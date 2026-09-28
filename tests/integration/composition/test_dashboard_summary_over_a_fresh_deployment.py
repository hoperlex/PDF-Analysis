"""`getDashboardSummary`, observed on a row. `F-5a`.

``docs/program/reviews/W46-JUDGE-A.md`` section 3, "What is not guarded": the only two
guards that show absent-is-not-empty failing over this operation check the section
**vocabulary** (three spellings agree) and the **page-shape** exemption (no ``items``,
no ``page``) -- neither observes a response row. The judge mutated ``_filled`` to drop
zero-count members and to append the unclassified bucket only when it is non-zero, and
609 tests stayed green: **the property the operation was built for has no guard that can
fail.**

This file is that guard. It drives the real, shipped ``getDashboardSummary`` -- the
composition root's own ``DashboardAdapter``, wired through a real ASGI app -- over a
database this test creates and migrates itself and drops when it ends, because
``getDashboardSummary`` sums over the **whole deployment** with no filter: the lane's own
gate database carries whatever every other suite in this run has committed to it (see
``tests/integration/composition/test_version_blocks_wire_shape.py`` and its module-scoped
``app`` fixture, which never claims an empty count for exactly this reason), and "absent"
cannot be observed against a table nobody can prove is empty.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from auditmanager.access.repository import UserRepository
from auditmanager.api.routers.idempotency import IDEMPOTENCY_HEADER
from auditmanager.api.security import API_TOKEN_VARIABLE, Subject, build_signer
from auditmanager.dashboard.repository import PROJECT_SECTIONS, RUN_STATES, VERDICTS
from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import (
    AnalysisProfileId,
    DocumentUid,
    ModelCallId,
    PromptBundleId,
    RunId,
    VersionUid,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEPLOYMENT_SECRET = "dashboard-spend-fresh-deployment-token"
SUITE_LOGIN = "w46-spend-dashboard-fresh"
SUITE_PASSWORD = "w46-spend-suite-account-password"

#: The literal command this suite runs to bring its own throwaway database to head, the
#: same invocation ``tests/integration/db/conftest.py`` runs and
#: ``docs/program/FOUNDATION_LOCK.json`` records -- so "migrations apply" and "this test
#: can run" cannot diverge.
MIGRATE_ARGV = [
    ".venv/bin/python",
    "-m",
    "alembic",
    "--config",
    "db/migrations/alembic.ini",
    "upgrade",
    "head",
]


def _sha256_hex(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


@pytest.fixture
def fresh_database_url() -> Iterator[str]:
    """A freshly created, migrated, otherwise-untouched database, dropped afterwards.

    ``getDashboardSummary`` has no ``WHERE`` clause anywhere in it (`DashboardRepository`
    -- deliberately, see its own docstring), so the only way to know a count is really
    zero is to own every row in the database it reads. Modelled on
    ``tests/integration/db/conftest.py``'s ``empty_database``/``migrated_database``, and
    not imported from it: that conftest is out of reach from this directory under
    ``--import-mode=importlib`` with no shared parent conftest, and this fixture is
    six lines shorter than the machinery it would take to share it.
    """
    configured = os.environ.get("DATABASE_URL")
    assert configured, "this suite needs the lane's .env loaded"
    settings = DatabaseSettings(url=parse_database_url(configured))
    maintenance_engine = create_database_engine(
        DatabaseSettings(url=settings.url.set(database="postgres"))
    ).execution_options(isolation_level="AUTOCOMMIT")
    name = f"w46_spend_fresh_{secrets.token_hex(6)}"
    try:
        with maintenance_engine.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{name}"'))
        url = settings.url.set(database=name).render_as_string(hide_password=False)
        environment = dict(os.environ) | {"PYTHONPATH": "src", "DATABASE_URL": url}
        completed = subprocess.run(
            MIGRATE_ARGV,
            cwd=REPOSITORY_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=180,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
        yield url
    finally:
        with maintenance_engine.connect() as connection:
            connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :name AND pid <> pg_backend_pid()"
                ),
                {"name": name},
            )
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
        maintenance_engine.dispose()


@pytest.fixture
def engine(fresh_database_url: str) -> Iterator[Engine]:
    eng = create_database_engine(DatabaseSettings(url=parse_database_url(fresh_database_url)))
    try:
        yield eng
    finally:
        eng.dispose()


@pytest.fixture
def app(fresh_database_url: str) -> TestClient:
    """The real, shipped application -- composition root and all -- over the fresh
    database. Not a fixture adapter: `DashboardAdapter` has no fixture-only stand-in to
    fall back on (see `tests/integration/api/conftest.py`'s `shipped_router`), so the
    real app is the only way to drive this operation over a database this test controls.
    """
    from auditmanager.api.app import create_asgi_app

    environ = dict(os.environ) | {
        "DATABASE_URL": fresh_database_url,
        "AUDITMANAGER_PROVIDER_MODE": "recorded",
        API_TOKEN_VARIABLE: DEPLOYMENT_SECRET,
    }
    asgi_app = create_asgi_app(environ=environ)
    return TestClient(asgi_app, raise_server_exceptions=False)


@pytest.fixture
def token(engine: Engine) -> str:
    """A credential this fresh deployment's own seam will accept.

    Minted the way `tests/support/accounts.py`'s `provisioned_credential` does --
    write the row, read the epoch back, mint from what the database says -- but against
    *this* fresh database rather than the lane's shared one, which that shared helper has
    no parameter for.
    """
    with Session(engine) as session:
        users = UserRepository()
        record = users.find_by_login(session, SUITE_LOGIN)
        if record is None:
            record = users.create_user(session, SUITE_LOGIN, SUITE_PASSWORD)
            session.commit()
    signer = build_signer({API_TOKEN_VARIABLE: DEPLOYMENT_SECRET})
    assert signer is not None
    return signer.issue(
        Subject(
            user_uid=str(record.user_uid),
            login=record.login,
            token_epoch=record.token_epoch,
            display_label=record.display_label,
        )
    ).token


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _dashboard(app: TestClient, token: str) -> dict[str, Any]:
    answer = app.get("/dashboard", headers=_auth(token))
    assert answer.status_code == 200, answer.content
    return answer.json()


def _create_project(app: TestClient, token: str, tag: str) -> str:
    payload = json.dumps({"name": f"W46-SPEND fresh deployment {tag}"}).encode("utf-8")
    answer = app.post(
        "/projects",
        headers=_auth(token)
        | {IDEMPOTENCY_HEADER: f"{tag}-prj", "Content-Type": "application/json"},
        content=payload,
    )
    assert answer.status_code == 201, answer.content
    return answer.json()["project_uid"]


def _seed_one_model_call(engine: Engine, project_uid: str, tag: str) -> None:
    """One provider call, real enough to satisfy every constraint `model_call` carries.

    Written directly, the way `tests/integration/api/conftest.py`'s own `PublishedRun`
    seeds `project`/`document`/`document_version`/`audit_run` -- a fixture is allowed to
    know the schema its own suite exists to protect. The run is left at `created`; the
    aggregate's `_SPEND` query has no `WHERE state = ...` and does not care.
    """
    document_uid = str(DocumentUid.new())
    version_uid = str(VersionUid.new())
    run_id = str(RunId.new())
    analysis_profile_id = str(AnalysisProfileId.new())
    prompt_bundle_id = str(PromptBundleId.new())
    model_call_id = str(ModelCallId.new())
    digest = _sha256_hex(f"{tag}-version")
    request_sha = _sha256_hex(f"{tag}-request")
    response_sha = _sha256_hex(f"{tag}-response")
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO document (document_uid, project_uid, display_title) "
                "VALUES (:d, :p, 'Fresh deployment document')"
            ),
            {"d": document_uid, "p": project_uid},
        )
        connection.execute(
            text(
                "INSERT INTO document_version (version_uid, document_uid, version_ordinal, "
                "media_type, byte_size, sha256, page_count) "
                "VALUES (:v, :d, 1, 'application/pdf', 1024, :s, 1)"
            ),
            {"v": version_uid, "d": document_uid, "s": digest},
        )
        connection.execute(
            text(
                "INSERT INTO audit_run (run_id, project_uid, version_uid, state, "
                "analysis_profile_id, prompt_bundle_id, provider_mode, frozen_input_digest) "
                "VALUES (:r, :p, :v, 'created', :ap, :pb, 'recorded', :s)"
            ),
            {
                "r": run_id,
                "p": project_uid,
                "v": version_uid,
                "ap": analysis_profile_id,
                "pb": prompt_bundle_id,
                "s": digest,
            },
        )
        connection.execute(
            text(
                "INSERT INTO model_call (model_call_id, run_id, stage_id, provider, "
                "model_identity, provider_mode, request_sha256, response_sha256, "
                "cost_micros, cost_basis, status) "
                "VALUES (:mc, :r, 'text_analysis', 'anthropic', 'claude-w46-spend-suite', "
                "'recorded', :req, :resp, :cost, 'measured', 'succeeded')"
            ),
            {
                "mc": model_call_id,
                "r": run_id,
                "req": request_sha,
                "resp": response_sha,
                "cost": 34_400,
            },
        )


# ---------------------------------------------------------------------------
# The guard
# ---------------------------------------------------------------------------


def test_a_deployment_with_nothing_in_it_reports_every_bucket_present_at_zero(
    app: TestClient, token: str
) -> None:
    """`F-5a`. Every member of every frozen vocabulary is present at `0` -- absent is not
    empty -- and `spend` itself is absent, because no `model_call` row exists anywhere
    (`F-1`). This is the exact shape the judge's mutation (report, section 3) destroys:
    dropping zero-count members from `_filled` and folding the unclassified bucket away
    when it is zero.
    """
    body = _dashboard(app, token)

    assert body["documents_by_project"] == []

    sections = body["section_breakdown"]
    assert len(sections) == len(PROJECT_SECTIONS) + 1, sections
    by_section = {row.get("section"): row["document_count"] for row in sections}
    for code in PROJECT_SECTIONS:
        assert by_section[code] == 0, (code, sections)
    assert by_section[None] == 0, "the unclassified bucket is missing or non-zero"
    assert sum(1 for row in sections if "section" not in row) == 1

    verdicts = {row["verdict"]: row["count"] for row in body["findings_by_verdict"]}
    assert set(verdicts) == set(VERDICTS), verdicts
    assert all(count == 0 for count in verdicts.values()), verdicts

    by_state = {row["state"]: row["count"] for row in body["run_activity"]["by_state"]}
    assert set(by_state) == set(RUN_STATES), by_state
    assert all(count == 0 for count in by_state.values()), by_state

    assert "spend" not in body["run_activity"], (
        "no model_call row exists anywhere in this deployment; spend must be absent, "
        "not a zero labelled measured (F-1)"
    )


def test_a_project_with_no_documents_is_a_row_present_at_zero(
    app: TestClient, token: str
) -> None:
    """Absent is not empty one level up: a real project with nothing in it is a row, not
    a gap. Creating it must not manufacture a call either -- `spend` stays absent."""
    project_uid = _create_project(app, token, "no-docs")

    body = _dashboard(app, token)
    assert body["documents_by_project"] == [
        {
            "project_uid": project_uid,
            "name": "W46-SPEND fresh deployment no-docs",
            "document_count": 0,
        }
    ]
    assert "spend" not in body["run_activity"]


def test_spend_appears_once_one_model_call_exists(
    app: TestClient, token: str, engine: Engine
) -> None:
    """The other half of `F-1`: once a real provider call has happened, `spend` is
    present with all three fields -- never omitted just because this suite proved the
    absent case above."""
    project_uid = _create_project(app, token, "one-call")
    _seed_one_model_call(engine, project_uid, "one-call")

    body = _dashboard(app, token)
    assert body["run_activity"]["spend"] == {
        "model_call_count": 1,
        "cost_micros": 34_400,
        "cost_basis": "measured",
    }
