"""GATE-FIX-DB-01: the downgrade chain restores every step, and the upgrades stay untouched.

``0022_findings_v2`` could not be downgraded at all: its downgrade rebuilt
``finding_current_verdict`` with ``CREATE OR REPLACE VIEW`` and one column fewer, which
PostgreSQL refuses (``cannot drop columns from view``). Every test that walks a database back
through ``0022`` -- the accounts, durable-effects, norm-embedding, release-notes and
terminal-detail downgrades -- failed there, and nothing exercised the 0022 downgrade on its own
because the only 0022 downgrade test is the *refusal* with retained data.

This module proves the repaired chain with three claims, each against a real PostgreSQL server:

* **the upgrade text is untouched.** The ``0022``..``0027`` upgrade surfaces (every top-level
  statement except the docstring, ``downgrade()`` and the ``_downgrade_*`` helpers) are pinned
  by a digest taken from ``origin/dev``'s bytes. A downgrade may be repaired; an upgrade may not.
* **every step down restores the schema exactly.** One database is walked up through every
  revision from ``0021`` with a catalog inventory taken at each, then walked down one revision
  at a time; after each downgrade the inventory equals the one taken on the way up.
* **the round trip loses nothing a downgrade promised to keep.** Rows written at ``0021`` survive
  head -> ``0021`` -> head, rows in the tables a downgrade drops are dropped (with the warning the
  migration owns), and a database upgraded straight to head has the same inventory as the one
  that went down and up.

The inventory is the same catalog families as ``test_schema_invariant_inventory.py`` plus
comments and ACLs, compared row by row instead of by digest so a failure names the object, and
with one deliberate difference: a column's *position* is its rank among the table's live
columns, not ``attnum``. Dropping and re-adding a column keeps the table identical for every
reader but moves the dropped column's ``attnum`` forever, so ``ordinal_position`` can never be
equal after a round trip and comparing it would assert something no downgrade can satisfy.
"""

from __future__ import annotations

import ast
import hashlib
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, text

from auditmanager.access.public import UserUid
from auditmanager.shared.db.config import DatabaseSettings
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.db.migrations import head_revision, revision_walk
from auditmanager.shared.identity import (
    AnalysisProfileId,
    AuditEventId,
    CommandId,
    DocumentUid,
    FindingObservationId,
    FindingUid,
    ProjectUid,
    PromptBundleId,
    RunId,
    VersionUid,
)

VERSIONS = Path(__file__).resolve().parents[3] / "db" / "migrations" / "versions"
FIRST_TOUCHED = "0021_portal_bundles"  # the released revision the chain walks back to

#: sha256 of each ``upgrade surface`` as ``origin/dev`` (``7bdb254e``) carried it. See
#: ``_upgrade_surface``. A mismatch means an upgrade statement, a constant or a helper it uses
#: changed; a downgrade-only change does not move these.
UPGRADE_SURFACE_DIGESTS = {
    "20261015_0022_findings_v2.py": "cf8b4f7c66c5663ddd0ccb54cea24fa6a3dc4d00cc03a4a5ab72739e969de493",
    "20261016_0023_norm_citations.py": "00a125b1e2f235aec9a42dc85a16e7d1d9da4f80bb8844c25a55369a20b7c3c6",
    "20261020_0024_version_classification.py": "2887367bcaa5546cb0e7cd92d46a5f419f37b9c333a6cf98d256c25955286c3a",
    "20261020_0025_work_assignments.py": "7061fccf5c5dafa35d911ab9b913c39050bfaa8d0505833541c2724ce919d0e3",
    "20261020_0026_price_lists.py": "6b21a92cb743436230093aee86bd826699207cabaa331deae4102f312a6fae6d",
    "20261020_0027_optimisation_proposals.py": "5cbe94b32de47e8d62c3639680096027ff049adac5fd31618d6b5a644042e93f",
}


def _alembic(action: str, target: str) -> list[str]:
    return [".venv/bin/python", "-m", "alembic", "--config", "db/migrations/alembic.ini", action, target]


# --------------------------------------------------------------------------------------
# claim 1: the upgrade text is untouched
# --------------------------------------------------------------------------------------


def _is_docstring(node: ast.stmt) -> bool:
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def _upgrade_surface(source: str) -> str:
    """The exact source text of everything a downgrade repair must not touch.

    Every top-level statement in file order, as the bytes of its own lines, except the module
    docstring (prose), ``downgrade()`` and the helpers named ``_downgrade_*``. The constants,
    the imports and the helpers ``upgrade()`` calls are therefore inside the surface; a
    downgrade-only helper must be named ``_downgrade_*`` to stay outside it.
    """
    lines = source.splitlines(keepends=True)
    kept: list[str] = []
    for node in ast.parse(source).body:
        if _is_docstring(node):
            continue
        if isinstance(node, ast.FunctionDef) and (
            node.name == "downgrade" or node.name.startswith("_downgrade_")
        ):
            continue
        kept.append("".join(lines[node.lineno - 1 : node.end_lineno]))
    return "\n".join(kept)


def _digest(text_: str) -> str:
    return hashlib.sha256(text_.encode("utf-8")).hexdigest()


@pytest.mark.parametrize("filename", sorted(UPGRADE_SURFACE_DIGESTS))
def test_the_upgrade_surface_of_every_touched_migration_is_the_one_on_origin_dev(
    filename: str,
) -> None:
    observed = _digest(_upgrade_surface((VERSIONS / filename).read_text(encoding="utf-8")))
    assert observed == UPGRADE_SURFACE_DIGESTS[filename], (
        f"{filename}: the upgrade surface changed. GATE-FIX-DB-01 may repair a downgrade only; "
        "an upgrade is released SQL. If this is a deliberate successor, it is a new migration."
    )


_SYNTHETIC = '''"""docstring."""
from alembic import op

LIST = ("a", "b")


def _helper() -> None:
    op.execute("SELECT 1")


def _downgrade_helper() -> None:
    op.execute("SELECT 2")


def upgrade() -> None:
    _helper()


def downgrade() -> None:
    _downgrade_helper()
'''


def test_the_upgrade_surface_digest_can_fail() -> None:
    """The guard's proof that it moves: it ignores a downgrade, it does not ignore an upgrade."""
    base = _digest(_upgrade_surface(_SYNTHETIC))
    downgrade_only = _SYNTHETIC.replace("SELECT 2", "SELECT 22").replace(
        "_downgrade_helper()\n", "_downgrade_helper()\n    pass\n", 1
    )
    assert _digest(_upgrade_surface(downgrade_only)) == base
    for mutated in (
        _SYNTHETIC.replace("SELECT 1", "SELECT 11"),  # a helper the upgrade calls
        _SYNTHETIC.replace('("a", "b")', '("a", "c")'),  # a constant
        _SYNTHETIC.replace("    _helper()\n\n\ndef downgrade", "    _helper()\n    _helper()\n\n\ndef downgrade"),
        _SYNTHETIC.replace("from alembic import op", "from alembic import op as o"),  # an import
    ):
        assert mutated != _SYNTHETIC
        assert _digest(_upgrade_surface(mutated)) != base


# --------------------------------------------------------------------------------------
# claim 2 and 3: the catalog inventory, step by step
# --------------------------------------------------------------------------------------

_Inventory = dict[str, list[tuple[str, ...]]]

_QUERIES: dict[str, str] = {
    # a column's position is its rank among the live columns (see the module docstring)
    "columns": """
        SELECT table_name, column_name,
               row_number() OVER (PARTITION BY table_name ORDER BY ordinal_position),
               data_type, udt_schema, udt_name, is_nullable, column_default, is_identity,
               identity_generation, is_generated, generation_expression,
               character_maximum_length, numeric_precision, numeric_scale,
               datetime_precision, collation_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
    """,
    "relations": """
        SELECT c.relname, c.relkind, c.relpersistence, c.relrowsecurity,
               c.relforcerowsecurity, c.relacl::text, pg_get_userbyid(c.relowner)
        FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p', 'v', 'm', 'S')
    """,
    "constraints": """
        SELECT t.relname, c.conname, c.contype, pg_get_constraintdef(c.oid, true),
               c.convalidated
        FROM pg_constraint c JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE n.nspname = 'public'
    """,
    "indexes": """
        SELECT tablename, indexname, indexdef FROM pg_indexes WHERE schemaname = 'public'
    """,
    "triggers": """
        SELECT c.relname, t.tgname, t.tgenabled, pg_get_triggerdef(t.oid, true)
        FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND NOT t.tgisinternal
    """,
    "functions": """
        SELECT p.proname, pg_get_function_identity_arguments(p.oid), pg_get_functiondef(p.oid)
        FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid = 'pg_proc'::regclass
                          AND d.objid = p.oid AND d.deptype = 'e')
    """,
    "views": """
        SELECT c.relname, pg_get_viewdef(c.oid, true)
        FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind = 'v'
    """,
    "types": """
        SELECT t.typname, t.typtype::text
        FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE n.nspname = 'public' AND t.typtype IN ('e', 'd', 'r', 'm')
    """,
    "sequences": """
        SELECT c.relname, s.seqtypid::regtype::text, s.seqstart, s.seqincrement, s.seqmax,
               s.seqmin, s.seqcache, s.seqcycle
        FROM pg_sequence s JOIN pg_class c ON c.oid = s.seqrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public'
    """,
    "comments": """
        SELECT 'relation', c.relname, COALESCE(a.attname, ''), d.description
        FROM pg_description d
        JOIN pg_class c ON d.classoid = 'pg_class'::regclass AND d.objoid = c.oid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        LEFT JOIN pg_attribute a ON a.attrelid = c.oid AND d.objsubid > 0 AND a.attnum = d.objsubid
        WHERE n.nspname = 'public'
        UNION ALL
        SELECT 'function', p.proname, pg_get_function_identity_arguments(p.oid), d.description
        FROM pg_description d
        JOIN pg_proc p ON d.classoid = 'pg_proc'::regclass AND d.objoid = p.oid
        JOIN pg_namespace n ON n.oid = p.pronamespace WHERE n.nspname = 'public'
        UNION ALL
        SELECT 'constraint', t.relname, c.conname, d.description
        FROM pg_description d
        JOIN pg_constraint c ON d.classoid = 'pg_constraint'::regclass AND d.objoid = c.oid
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace WHERE n.nspname = 'public'
    """,
    "extensions": "SELECT extname, extversion FROM pg_extension WHERE extname <> 'plpgsql'",
    "state_topology": "SELECT machine, from_state, to_state FROM contract_state_transition",
    "alembic": "SELECT version_num FROM alembic_version",
}


def _normalise(value: object) -> str:
    return "<NULL>" if value is None else re.sub(r"\s+", " ", str(value)).strip()


def _inventory(engine: Engine) -> _Inventory:
    with engine.connect() as connection:
        return {
            family: sorted(
                tuple(_normalise(value) for value in row)
                for row in connection.execute(text(query)).all()
            )
            for family, query in _QUERIES.items()
        }


def _difference(expected: _Inventory, observed: _Inventory) -> list[str]:
    lines: list[str] = []
    for family in _QUERIES:
        wanted, found = set(expected[family]), set(observed[family])
        lines += [f"missing  {family}: {row!r}" for row in sorted(wanted - found)]
        lines += [f"surplus  {family}: {row!r}" for row in sorted(found - wanted)]
    return lines


def _assert_same(expected: _Inventory, observed: _Inventory, where: str) -> None:
    difference = _difference(expected, observed)
    assert not difference, where + ":\n" + "\n".join(difference[:40])


def test_the_inventory_can_fail(migrated_engine: Engine) -> None:
    """The comparison is not vacuous: a missing column, a changed view and a comment all show."""
    baseline = _inventory(migrated_engine)
    assert all(baseline[family] for family in ("columns", "constraints", "views", "comments"))
    with migrated_engine.begin() as connection:
        connection.execute(text("ALTER TABLE finding_observation DROP COLUMN proposed_severity"))
    assert _difference(baseline, _inventory(migrated_engine))
    with migrated_engine.begin() as connection:
        connection.execute(
            text("COMMENT ON VIEW finding_current_verdict IS 'a different comment'")
        )
    assert any(
        "comments" in line for line in _difference(baseline, _inventory(migrated_engine))
    )


# --------------------------------------------------------------------------------------
# sample rows
# --------------------------------------------------------------------------------------


def _user(connection: Any) -> str:
    user = str(UserUid.new())
    connection.execute(
        text(
            "INSERT INTO app_user (user_uid, login, password_algorithm, password_iterations, "
            "password_salt, password_hash) "
            "VALUES (:u, :login, 'pbkdf2_sha256', 100000, :salt, :hash)"
        ),
        {"u": user, "login": user.lower(), "salt": "0" * 32, "hash": "0" * 64},
    )
    return user


def _seed_released_rows(engine: Engine) -> dict[str, str]:
    """Rows in tables no downgrade may touch: a project, its document and version, a run, a command."""
    ids = {
        "project": str(ProjectUid.new()),
        "document": str(DocumentUid.new()),
        "version": str(VersionUid.new()),
        "run": str(RunId.new()),
        "command": str(CommandId.new()),
    }
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO project (project_uid, name) VALUES (:project, 'Школа')"), ids
        )
        connection.execute(
            text(
                "INSERT INTO document (document_uid, project_uid, display_title, section) "
                "VALUES (:document, :project, 'КЖ-1', 'KJ')"
            ),
            ids,
        )
        connection.execute(
            text(
                "INSERT INTO document_version (version_uid, document_uid, version_ordinal, "
                "source_filename, media_type, byte_size, sha256, page_count) "
                "VALUES (:version, :document, 1, 'КЖ-1.pdf', 'application/pdf', 1024, :sha, 1)"
            ),
            {**ids, "sha": "c" * 64},
        )
        connection.execute(
            text(
                "INSERT INTO audit_run (run_id, project_uid, version_uid, analysis_profile_id, "
                "prompt_bundle_id, provider_mode, frozen_input_digest) "
                "VALUES (:run, :project, :version, :ap, :pb, 'recorded', :digest)"
            ),
            {
                **ids,
                "ap": str(AnalysisProfileId.new()),
                "pb": str(PromptBundleId.new()),
                "digest": "b" * 64,
            },
        )
        connection.execute(
            text(
                "INSERT INTO command_record (command_id, command_type, idempotency_key, "
                "payload_fingerprint) VALUES (:command, 'start_run', :key, :fp)"
            ),
            {**ids, "key": ids["command"].lower(), "fp": "f" * 64},
        )
    return ids


_RELEASED_TABLES = ("project", "document", "document_version", "audit_run", "command_record")


def _row_counts(engine: Engine) -> dict[str, int]:
    with engine.connect() as connection:
        return {
            table: int(connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one())
            for table in _RELEASED_TABLES
        }


def _seed_rows_the_chain_drops(engine: Engine, ids: dict[str, str]) -> None:
    """A classification (0024) and an assignment with its history (0025): dropped, by design."""
    with engine.begin() as connection:
        expert, admin = _user(connection), _user(connection)
        connection.execute(
            text(
                "INSERT INTO document_version_classification "
                "(version_uid, project_stage, section_code, confirmed_by_user_uid) "
                "VALUES (:version, 'R', 'KJ', :expert)"
            ),
            {**ids, "expert": expert},
        )
        assignment = "asg_01ARZ3NDEKTSV4RRFFQ69G5FAV"
        connection.execute(
            text(
                "INSERT INTO work_assignment (assignment_uid, project_uid, document_uid, "
                "assignee_user_uid, created_by_user_uid, note) "
                "VALUES (:a, :project, :document, :expert, :admin, 'проверить армирование')"
            ),
            {**ids, "a": assignment, "expert": expert, "admin": admin},
        )
        connection.execute(
            text(
                "INSERT INTO work_assignment_event (event_id, assignment_uid, seq, kind, "
                "actor_user_uid) VALUES (:e, :a, 1, 'assigned', :admin)"
            ),
            {"e": str(AuditEventId.new()), "a": assignment, "admin": admin},
        )


def _chain() -> list[str]:
    walk = revision_walk()
    assert FIRST_TOUCHED in walk, f"{FIRST_TOUCHED} is not in the revision walk {walk}"
    chain = walk[walk.index(FIRST_TOUCHED) :]
    assert chain[-1] == head_revision()
    assert len(chain) >= 7, f"the chain 0021..0027 shrank to {chain}"
    return chain


# --------------------------------------------------------------------------------------
# the walk
# --------------------------------------------------------------------------------------


def test_every_step_down_restores_the_schema_and_head_upgrades_again(
    empty_database: DatabaseSettings,
    foundation_command: Callable[[list[str], str], Any],
    migrated_database: DatabaseSettings,
) -> None:
    url = empty_database.url.render_as_string(hide_password=False)
    chain = _chain()

    def run(action: str, revision: str) -> str:
        result = foundation_command(_alembic(action, revision), url)
        assert result.returncode == 0, result.describe()
        return result.stdout + result.stderr

    engine = create_database_engine(empty_database)
    straight = create_database_engine(migrated_database)
    try:
        # up, one revision at a time, with an inventory taken at each
        run("upgrade", chain[0])
        ids = _seed_released_rows(engine)
        released = _row_counts(engine)
        assert all(released.values()), released
        on_the_way_up: dict[str, _Inventory] = {chain[0]: _inventory(engine)}
        for revision in chain[1:]:
            run("upgrade", revision)
            on_the_way_up[revision] = _inventory(engine)
            assert _row_counts(engine) == released, f"{revision} changed a released row"
        head = chain[-1]
        _assert_same(_inventory(straight), on_the_way_up[head], "step-by-step vs straight upgrade")
        _seed_rows_the_chain_drops(engine, ids)

        # down, one revision at a time: each step must restore the inventory it left
        for revision, previous in zip(reversed(chain[1:]), reversed(chain[:-1])):
            output = run("downgrade", previous)
            _assert_same(
                on_the_way_up[previous], _inventory(engine), f"after downgrade {revision} -> {previous}"
            )
            assert _row_counts(engine) == released, f"downgrading {revision} touched a released row"
            if revision == "0025_work_assignments":
                assert "exist nowhere else and are dropped" in output, output

        # and up again: the round trip equals a straight upgrade
        run("upgrade", head)
        _assert_same(_inventory(straight), _inventory(engine), "round trip vs straight upgrade")
        assert _row_counts(engine) == released
        with engine.connect() as connection:
            for table in ("document_version_classification", "work_assignment", "work_assignment_event"):
                assert connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 0
    finally:
        engine.dispose()
        straight.dispose()


def test_the_verdict_view_works_after_the_round_trip(
    empty_database: DatabaseSettings, foundation_command: Callable[[list[str], str], Any]
) -> None:
    """The rebuilt view is not only shaped right: it answers, for a finding written after it."""
    url = empty_database.url.render_as_string(hide_password=False)
    steps = ((("upgrade", "head")), (("downgrade", FIRST_TOUCHED)), (("upgrade", "head")))
    for action, revision in steps:
        result = foundation_command(_alembic(action, revision), url)
        assert result.returncode == 0, result.describe()
    engine = create_database_engine(empty_database)
    try:
        ids = _seed_released_rows(engine)
        finding, observation = str(FindingUid.new()), str(FindingObservationId.new())
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO finding (finding_uid, project_uid, version_uid, "
                    "allocated_by_run_id, category) "
                    "VALUES (:f, :project, :version, :run, 'internal_contradiction')"
                ),
                {**ids, "f": finding},
            )
            connection.execute(
                text(
                    "INSERT INTO finding_observation (finding_observation_id, run_id, "
                    "finding_uid, stage_id, category, finding_text, recommendation_text, "
                    "grounded, analysis_profile_id, prompt_bundle_id, provider_mode) "
                    "VALUES (:o, :run, :f, 'text_analysis', 'internal_contradiction', "
                    "'A conflict', 'Resolve it', true, :ap, :pb, 'recorded')"
                ),
                {
                    **ids, "o": observation, "f": finding,
                    "ap": str(AnalysisProfileId.new()), "pb": str(PromptBundleId.new()),
                },
            )
        with engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT current_verdict, decision_event_count, decided_severity "
                    "FROM finding_current_verdict WHERE finding_uid = :f"
                ),
                {"f": finding},
            ).one()
        assert tuple(row) == ("pending", 0, None)
    finally:
        engine.dispose()


_AT_0021_VIEW_COLUMNS = [
    "finding_uid",
    "current_verdict",
    "latest_verdict_decision_id",
    "latest_verdict_recorded_at",
    "latest_comment",
    "latest_comment_decision_id",
    "latest_decision_id",
    "decision_recorded_at",
    "decision_event_count",
]


def test_the_0022_downgrade_returns_the_nine_columns_and_keeps_the_views_comment(
    empty_database: DatabaseSettings, foundation_command: Callable[[list[str], str], Any]
) -> None:
    """Whatever comment the view carries survives, quotes, colons and percent signs included.

    The comment is read from the catalog and set again after the view is dropped; a colon or a
    ``%`` in it must reach PostgreSQL as text, not as a bind parameter or a format directive.
    """
    url = empty_database.url.render_as_string(hide_password=False)
    tricky = "it's a view: see :this and 100% of %s; \"quoted\" \\ done"
    upgraded = foundation_command(_alembic("upgrade", "0022_findings_v2"), url)
    assert upgraded.returncode == 0, upgraded.describe()
    engine = create_database_engine(empty_database)
    try:
        with engine.begin() as connection:
            literal = "'" + tricky.replace("'", "''") + "'"
            connection.execute(
                text("COMMENT ON VIEW finding_current_verdict IS " + literal.replace(":", "\\:"))
            )
            columns = connection.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'finding_current_verdict' ORDER BY ordinal_position"
                )
            ).scalars().all()
        assert columns == [*_AT_0021_VIEW_COLUMNS, "decided_severity"]

        downgraded = foundation_command(_alembic("downgrade", FIRST_TOUCHED), url)
        assert downgraded.returncode == 0, downgraded.describe()
        with engine.connect() as connection:
            columns = connection.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'finding_current_verdict' ORDER BY ordinal_position"
                )
            ).scalars().all()
            comment = connection.execute(
                text("SELECT obj_description('finding_current_verdict'::regclass, 'pg_class')")
            ).scalar_one()
            version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert columns == _AT_0021_VIEW_COLUMNS
        assert comment == tricky
        assert version == FIRST_TOUCHED
    finally:
        engine.dispose()
