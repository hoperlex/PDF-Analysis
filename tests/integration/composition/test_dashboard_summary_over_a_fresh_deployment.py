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
    DecisionId,
    DocumentUid,
    FindingObservationId,
    FindingUid,
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
        ),
        is_default_credential=False,
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


# ---------------------------------------------------------------------------
# `G2` / `X-2`: known data, exact counts -- absent-is-not-empty proves nothing about
# present-is-counted. `X` mutated `_filled` to return `(member, 0)` for every member
# (never reading the database) and `cost_basis` to `"measured"` unconditionally; both
# passed this file's three tests above and the whole 612-scope around it, because every
# state here is all zeros except `spend`, and `spend`'s one call is genuinely
# `measured`. What follows seeds every count in advance and asserts the exact number.
# ---------------------------------------------------------------------------


def _seed_published_document(
    engine: Engine, project_uid: str, tag: str, section: str | None
) -> None:
    """A document with a published current version, classified under ``section`` (or
    unclassified when ``None``) -- the shape ``documents_by_project`` and
    ``section_breakdown`` both count, via ``DocumentRepository._LIST_PROJECTS``'s join
    (``dashboard/repository.py``'s own docstring: "the same join `_LIST_PROJECTS`
    counts through"). Unlike ``_seed_one_model_call``'s document, this one sets
    ``current_version_uid`` -- the one column that makes a document counted at all.
    """
    document_uid = str(DocumentUid.new())
    version_uid = str(VersionUid.new())
    digest = _sha256_hex(f"{tag}-version")
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO document (document_uid, project_uid, display_title, section) "
                "VALUES (:d, :p, :t, :sec)"
            ),
            {"d": document_uid, "p": project_uid, "t": f"W46-GUARD {tag}", "sec": section},
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
            text("UPDATE document SET current_version_uid = :v WHERE document_uid = :d"),
            {"v": version_uid, "d": document_uid},
        )


def _walk_run_to(engine: Engine, run_id: str, target: str) -> None:
    """Move a run along declared edges only, from ``created`` to any of the eight
    frozen states.

    Extends ``tests/integration/api/conftest.py``'s ``PublishedRun._walk_to`` (not
    imported from it -- out of reach from this directory under
    ``--import-mode=importlib``, same reasoning ``fresh_database_url`` above already
    gives for not sharing ``tests/integration/db/conftest.py``'s fixtures) with the two
    states it has no caller that needs: ``cancelled`` (declared directly from
    ``created``, the shortest edge, per ``db/migrations/versions/20260910_0002_
    pc01_schema.py``'s ``contract_state_transition`` seed) and ``partial`` (declared
    only from ``validating``, and only with a non-empty ``degradation_set`` --
    ``ck_audit_run_partial_records_degradation``).
    """
    path = {
        "created": (),
        "queued": ("queued",),
        "running": ("queued", "running"),
        "validating": ("queued", "running", "validating"),
        "published": ("queued", "running", "validating", "published"),
        "partial": ("queued", "running", "validating", "partial"),
        "failed": ("queued", "running", "validating", "failed"),
        "cancelled": ("cancelled",),
    }[target]
    with engine.begin() as connection:
        for step in path:
            terminal = step in {"published", "partial", "failed", "cancelled"}
            connection.execute(
                text(
                    "UPDATE audit_run SET state = :s, "
                    "terminal_at = CASE WHEN :t THEN now() ELSE NULL END, "
                    "terminal_reason = CASE WHEN :s = 'failed' THEN 'analysis_failed' "
                    "ELSE NULL END, "
                    "degradation_set = CASE WHEN :s = 'partial' "
                    "THEN '[\"block_analysis\"]'::jsonb "
                    "WHEN :s = 'published' THEN '[]'::jsonb "
                    "ELSE degradation_set END "
                    "WHERE run_id = :r"
                ),
                {"s": step, "t": terminal, "r": run_id},
            )


def _seed_run(engine: Engine, project_uid: str, tag: str, target_state: str) -> tuple[str, str]:
    """One run, with its own throwaway document and version, walked from ``created`` to
    ``target_state``. Returns ``(run_id, version_uid)``.

    The document is deliberately never published (``current_version_uid`` stays
    ``NULL``) so it does not count toward ``documents_by_project`` or
    ``section_breakdown`` -- run-state seeding and document/section seeding stay
    orthogonal, the same way ``_seed_one_model_call``'s document already does not
    count.
    """
    document_uid = str(DocumentUid.new())
    version_uid = str(VersionUid.new())
    run_id = str(RunId.new())
    analysis_profile_id = str(AnalysisProfileId.new())
    prompt_bundle_id = str(PromptBundleId.new())
    digest = _sha256_hex(f"{tag}-version")
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO document (document_uid, project_uid, display_title) "
                "VALUES (:d, :p, :t)"
            ),
            {"d": document_uid, "p": project_uid, "t": f"W46-GUARD {tag}"},
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
    _walk_run_to(engine, run_id, target_state)
    return run_id, version_uid


def _seed_finding(
    engine: Engine,
    project_uid: str,
    version_uid: str,
    run_id: str,
    tag: str,
    verdict: str,
) -> None:
    """One finding at a known verdict: ``pending``, ``accepted`` or ``rejected``.

    ``pending`` needs only the ``finding`` row -- the projection's own default,
    ``COALESCE(v.verdict, 'pending')`` (``20260910_0002_pc01_schema.py``'s
    ``finding_current_verdict`` view). ``accepted``/``rejected`` need one
    ``expert_decision_event`` too, which itself needs a ``finding_observation`` row
    first: ``expert_decision_event.finding_observation_id`` is ``NOT NULL``.

    ``needs_manual_review`` is not offered here, on purpose. The migration that
    declares the verdict enum says so in its own comment: *"`needs_manual_review` is
    declared with no PC-01 producer."* ``ck_expert_decision_event_type_verdict_agree``
    enforces it structurally -- of the four declared event types (``accept``,
    ``reject``, ``comment``, ``revoke``), none may carry that verdict, so no ``INSERT``
    into this table can ever produce it, not even a test's own. The exact-count test
    below asserts that count is ``0`` for this reason, not because nothing tried.
    """
    assert verdict in ("pending", "accepted", "rejected"), verdict
    finding_uid = str(FindingUid.new())
    finding_observation_id = str(FindingObservationId.new())
    analysis_profile_id = str(AnalysisProfileId.new())
    prompt_bundle_id = str(PromptBundleId.new())
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO finding (finding_uid, project_uid, version_uid, "
                "allocated_by_run_id, category) "
                "VALUES (:f, :p, :v, :r, 'internal_contradiction')"
            ),
            {"f": finding_uid, "p": project_uid, "v": version_uid, "r": run_id},
        )
        if verdict == "pending":
            return
        connection.execute(
            text(
                "INSERT INTO finding_observation (finding_observation_id, run_id, "
                "finding_uid, stage_id, category, finding_text, recommendation_text, "
                "grounded, analysis_profile_id, prompt_bundle_id, provider_mode) "
                "VALUES (:o, :r, :f, 'text_analysis', 'internal_contradiction', "
                "'W46-GUARD seeded finding text.', "
                "'W46-GUARD seeded recommendation text.', "
                "true, :ap, :pb, 'recorded')"
            ),
            {
                "o": finding_observation_id,
                "r": run_id,
                "f": finding_uid,
                "ap": analysis_profile_id,
                "pb": prompt_bundle_id,
            },
        )
        event_type = {"accepted": "accept", "rejected": "reject"}[verdict]
        connection.execute(
            text(
                "INSERT INTO expert_decision_event (decision_id, finding_uid, "
                "finding_observation_id, event_type, verdict, author_label) "
                "VALUES (:dec, :f, :o, :et, :verd, :author)"
            ),
            {
                "dec": str(DecisionId.new()),
                "f": finding_uid,
                "o": finding_observation_id,
                "et": event_type,
                "verd": verdict,
                "author": "W46-GUARD suite",
            },
        )


def _seed_model_call(
    engine: Engine, run_id: str, tag: str, cost_micros: int, cost_basis: str
) -> None:
    """One provider call at a known cost and a known basis, attached to ``run_id``.

    Unlike ``_seed_one_model_call`` (which always creates its own project, document,
    version and run), this attaches to a run the caller already has -- two calls on
    the same run is exactly the shape that makes ``cost_basis`` a real aggregate
    decision rather than a copy of the one row that exists.
    """
    model_call_id = str(ModelCallId.new())
    request_sha = _sha256_hex(f"{tag}-request")
    response_sha = _sha256_hex(f"{tag}-response")
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO model_call (model_call_id, run_id, stage_id, provider, "
                "model_identity, provider_mode, request_sha256, response_sha256, "
                "cost_micros, cost_basis, status) "
                "VALUES (:mc, :r, 'text_analysis', 'anthropic', "
                "'claude-w46-guard-suite', 'recorded', :req, :resp, :cost, :basis, "
                "'succeeded')"
            ),
            {
                "mc": model_call_id,
                "r": run_id,
                "req": request_sha,
                "resp": response_sha,
                "cost": cost_micros,
                "basis": cost_basis,
            },
        )


def test_a_deployment_with_known_data_reports_the_exact_counts(
    app: TestClient, token: str, engine: Engine
) -> None:
    """`X-2` (`docs/program/reviews/W46-JUDGE-X.md`): the fresh-deployment guard above
    proves absent-is-not-empty and nothing about present-is-counted. Two of X's
    mutations of `_filled` -- every count forced to `(member, 0)`, never reading the
    database, and `cost_basis` forced to `"measured"` unconditionally -- both pass the
    three tests above and the whole 612-test scope around them, because every state
    those tests drive is all zeros except one `spend` call that genuinely is
    `measured`.

    Every count below is known before the read and pairwise distinct inside its breakdown:
    all fourteen sections plus unclassified carry 1..15 documents; the eight run states
    carry distinct positive counts; six findings span the three reachable verdicts (see
    `_seed_finding` for why `needs_manual_review` is asserted at exactly `0` rather
    than seeded); and two provider calls, one measured and one estimated, so the
    aggregate basis is a real decision (`estimated`, `F-1`'s own rule) rather than a
    copy of a single row. `_filled`-returns-zero and `cost_basis`-always-`"measured"`
    both fail every assertion below.
    """
    project_a = _create_project(app, token, "counts-a")
    project_b = _create_project(app, token, "counts-b")
    expected_by_section = {code: index + 1 for index, code in enumerate(PROJECT_SECTIONS)}
    expected_by_section[None] = len(PROJECT_SECTIONS) + 1
    for section, count in expected_by_section.items():
        project_uid = project_b if section is None else project_a
        for ordinal in range(count):
            _seed_published_document(
                engine,
                project_uid,
                f"section-{section or 'unclassified'}-{ordinal}",
                section,
            )

    expected_by_state = {state: index + 1 for index, state in enumerate(RUN_STATES)}
    # The finding allocation below contributes one additional published run.
    for state, count in expected_by_state.items():
        seed_count = count - 1 if state == "published" else count
        for ordinal in range(seed_count):
            _seed_run(engine, project_a, f"state-{state}-{ordinal}", state)

    finding_project = _create_project(app, token, "counts-findings")
    finding_run_id, finding_version_uid = _seed_run(
        engine, finding_project, "findings-run", "published"
    )
    _seed_finding(engine, finding_project, finding_version_uid, finding_run_id, "f1", "pending")
    _seed_finding(engine, finding_project, finding_version_uid, finding_run_id, "f2", "accepted")
    _seed_finding(engine, finding_project, finding_version_uid, finding_run_id, "f3", "accepted")
    _seed_finding(engine, finding_project, finding_version_uid, finding_run_id, "f4", "rejected")
    _seed_finding(engine, finding_project, finding_version_uid, finding_run_id, "f5", "rejected")
    _seed_finding(engine, finding_project, finding_version_uid, finding_run_id, "f6", "rejected")

    _seed_model_call(engine, finding_run_id, "spend-measured", 12_000, "measured")
    _seed_model_call(engine, finding_run_id, "spend-estimated", 30_000, "estimated")

    body = _dashboard(app, token)

    projects_by_uid = {row["project_uid"]: row for row in body["documents_by_project"]}
    assert projects_by_uid[project_a]["document_count"] == sum(
        expected_by_section[code] for code in PROJECT_SECTIONS
    ), projects_by_uid
    assert projects_by_uid[project_b]["document_count"] == expected_by_section[None], projects_by_uid

    sections = body["section_breakdown"]
    assert len(sections) == len(PROJECT_SECTIONS) + 1, sections
    by_section = {row.get("section"): row["document_count"] for row in sections}
    assert by_section == expected_by_section, by_section
    assert len(set(by_section.values())) == len(by_section), by_section

    by_verdict = {row["verdict"]: row["count"] for row in body["findings_by_verdict"]}
    assert by_verdict == {
        "pending": 1,
        "accepted": 2,
        "rejected": 3,
        "needs_manual_review": 0,
    }, by_verdict
    assert len(set(by_verdict.values())) == len(by_verdict), by_verdict

    by_state = {row["state"]: row["count"] for row in body["run_activity"]["by_state"]}
    assert by_state == expected_by_state, by_state
    assert len(set(by_state.values())) == len(by_state), by_state

    assert body["run_activity"]["spend"] == {
        "model_call_count": 2,
        "cost_micros": 42_000,
        "cost_basis": "estimated",
    }
