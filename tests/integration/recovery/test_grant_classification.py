"""PROD-04-DB-ROLES-01: every object of the schema at head has a decision about the application role.

The application role (``api`` and ``worker``) gets exactly the rights ``scripts/recovery/
grant_classification.py`` says. That module is built on ``schema_coverage`` -- the recovery tooling's
closed declaration of the schema -- and adds the one thing it does not say: which rights each table
gets. This file is the guard that keeps the two, the catalogue and the code whole. Same discipline as
``test_schema_coverage.py`` and the same source of truth: a migration that adds a table, a view, a
sequence or a function is red here until it is classified, and the step that applies the rights
(``infra/deploy/apply-grants.sh``) refuses a relation it has no row for.

What is held, and what makes each hold fail (the mutation is in the test):

* the four classes partition ``schema_coverage.TABLES`` -- a table moved into two classes, or out of all,
  is refused by name;
* a table the schema declares immutable is never ``read-write`` -- ``audit_event`` moved there is refused;
* an ``append-only`` table without a trigger needs written evidence -- ``job`` moved there is refused;
* the live catalogue of a migrated database equals the declaration (tables, views, sequences and the
  tables that own them, trigger functions, plain functions) -- a table, view, sequence, trigger function
  and plain function created in a clone is each refused, named;
* the repository's own SQL (``observed_statements``) never needs more than the class grants -- a
  statement added to a module that updates an ``append-only`` table is refused, and so is a class that
  takes away what the code does;
* the SQL embedded in ``apply-grants.sh`` is the SQL this module generates from the classification -- a
  table moved to another class, or an edited script, is refused.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from scripts.recovery import grant_classification as grants
from scripts.recovery import schema_coverage as coverage

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "infra/deploy/apply-grants.sh"
SOURCE = ROOT / "src/auditmanager"


def _audit(engine: Engine) -> None:
    with Session(engine) as session:
        grants.audit_grant_classification(session)


def _run(engine: Engine, *statements: str) -> None:
    with engine.begin() as connection:
        for statement in statements:
            connection.exec_driver_sql(statement)


def _move(monkeypatch: pytest.MonkeyPatch, table: str, destination: str) -> None:
    """Move one table to another class, in the module's own sets (what an edit of the file would do)."""
    names = {"read-write": "READ_WRITE", "append-only": "APPEND_ONLY", "read-only": "READ_ONLY", "none": "NONE"}
    for attribute in names.values():
        monkeypatch.setattr(grants, attribute, getattr(grants, attribute) - {table})
    monkeypatch.setattr(grants, names[destination], getattr(grants, names[destination]) | {table})
    monkeypatch.setattr(grants, "_CLASSES", (
        ("read-write", grants.READ_WRITE), ("append-only", grants.APPEND_ONLY),
        ("read-only", grants.READ_ONLY), ("none", grants.NONE),
    ))


# --- the declaration is whole and consistent -----------------------------------------------------


def test_the_declaration_is_consistent() -> None:
    assert grants.classification_problems() == []


def test_the_four_classes_partition_the_tables_schema_coverage_declares() -> None:
    classified = grants.READ_WRITE | grants.APPEND_ONLY | grants.READ_ONLY | grants.NONE
    assert classified == coverage.TABLES
    assert sum(len(c) for c in (grants.READ_WRITE, grants.APPEND_ONLY, grants.READ_ONLY, grants.NONE)) == len(classified)
    # `0037_analysis_presets`: analysis_preset_revision (`0035_comparison_records`: comparison_sheet_link, comparison_summary)
    assert len(coverage.TABLES) == 67


def test_every_table_has_its_privileges_from_its_class() -> None:
    assert grants.table_privileges("job") == ("SELECT", "INSERT", "UPDATE", "DELETE")
    assert grants.table_privileges("audit_event") == ("SELECT", "INSERT")
    assert grants.table_privileges("alembic_version") == ("SELECT",)
    assert all("TRUNCATE" not in grants.table_privileges(t) for t in coverage.TABLES)
    assert all("DELETE" not in grants.table_privileges(t) for t in grants.APPEND_ONLY | grants.READ_ONLY)


class TestTheDeclarationRefusesWhatItCannotAllow:
    def test_a_table_in_two_classes_is_refused(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(grants, "READ_ONLY", grants.READ_ONLY | {"job"})
        monkeypatch.setattr(grants, "_CLASSES", (
            ("read-write", grants.READ_WRITE), ("append-only", grants.APPEND_ONLY),
            ("read-only", grants.READ_ONLY), ("none", grants.NONE),
        ))
        problems = grants.classification_problems()
        assert any("in both read-write and read-only" in p and "job" in p for p in problems), problems

    def test_a_table_in_no_class_is_refused_by_name(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(grants, "READ_WRITE", grants.READ_WRITE - {"job"})
        monkeypatch.setattr(grants, "_CLASSES", (
            ("read-write", grants.READ_WRITE), ("append-only", grants.APPEND_ONLY),
            ("read-only", grants.READ_ONLY), ("none", grants.NONE),
        ))
        problems = grants.classification_problems()
        assert any("unclassified=['job']" in p for p in problems), problems
        with pytest.raises(grants.GrantClassificationRefused, match="job"):
            grants.table_class("job")

    def test_an_immutable_table_is_never_read_write(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _move(monkeypatch, "audit_event", "read-write")
        problems = grants.classification_problems()
        assert any("audit_event carries an immutability trigger and is classified read-write" in p for p in problems), problems

    def test_an_append_only_table_without_a_trigger_needs_written_evidence(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _move(monkeypatch, "job", "append-only")
        problems = grants.classification_problems()
        assert any("unexplained=['job']" in p for p in problems), problems

    def test_a_lock_exception_on_a_table_that_is_not_append_only_is_refused(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(grants, "LOCK_ONLY_UPDATE", {**grants.LOCK_ONLY_UPDATE, "job": "no reason"})
        problems = grants.classification_problems()
        assert any("LOCK_ONLY_UPDATE names job" in p for p in problems), problems


# --- the code's own SQL never needs more than the class grants ------------------------------------


def test_the_repository_code_needs_nothing_the_classification_withholds() -> None:
    assert grants.evidence_problems(grants.observed_statements(SOURCE)) == []


def test_the_scan_finds_the_statements_the_classification_rests_on() -> None:
    seen = grants.observed_statements(SOURCE)
    assert "DELETE" in seen["app_user"].verbs and "DELETE" in seen["app_user_role"].verbs
    assert "LOCK" in seen["work_assignment"].verbs and "LOCK" in seen["document_version_classification"].verbs
    assert "UPDATE" in seen["stage_result"].verbs, "an INSERT ... ON CONFLICT DO UPDATE is an UPDATE"
    assert "UPDATE" in seen["execution_control"].verbs and "UPDATE" in seen["account_release_mark"].verbs
    # Nothing in the code updates or deletes from an append-only table or locks one but the two declared.
    for table in sorted(grants.APPEND_ONLY):
        extra = seen.get(table, grants.Observed(frozenset(), ())).verbs - {"INSERT"}
        if table in grants.LOCK_ONLY_UPDATE:
            assert extra == {"LOCK"}, table
        else:
            assert not extra, (table, extra)
    # And the tables the code never writes are exactly the read-only class.
    never_written = sorted(coverage.TABLES - set(seen))
    assert never_written == sorted(grants.READ_ONLY), never_written


class TestTheScanRefusesAStatementTheClassesDoNotAllow:
    @staticmethod
    def _tree(tmp_path: Path, sql: str) -> Path:
        root = tmp_path / "src"
        (root / "pkg").mkdir(parents=True)
        (root / "pkg/repo.py").write_text(f'from sqlalchemy import text\nSTATEMENT = text("{sql}")\n', encoding="utf-8")
        return root

    def test_an_update_of_an_append_only_table_is_refused(self, tmp_path: Path) -> None:
        root = self._tree(tmp_path, "UPDATE project SET name = :n WHERE project_uid = :p")
        problems = grants.evidence_problems(grants.observed_statements(root))
        assert any(p.startswith("project is append-only but the code needs ['UPDATE']") for p in problems), problems

    def test_a_delete_from_an_append_only_table_is_refused(self, tmp_path: Path) -> None:
        root = self._tree(tmp_path, "DELETE FROM audit_event WHERE true")
        problems = grants.evidence_problems(grants.observed_statements(root))
        assert any(p.startswith("audit_event is append-only but the code needs ['DELETE']") for p in problems), problems

    def test_an_upsert_is_an_update(self, tmp_path: Path) -> None:
        root = self._tree(tmp_path, "INSERT INTO project (project_uid) VALUES (:p) ON CONFLICT (project_uid) DO UPDATE SET name = :n")
        problems = grants.evidence_problems(grants.observed_statements(root))
        assert any(p.startswith("project is append-only but the code needs ['UPDATE']") for p in problems), problems

    def test_a_row_lock_on_an_append_only_table_is_refused_unless_declared(self, tmp_path: Path) -> None:
        root = self._tree(tmp_path, "SELECT model_call_id FROM model_call WHERE model_call_id = :i FOR UPDATE")
        problems = grants.evidence_problems(grants.observed_statements(root))
        assert any(p.startswith("model_call is append-only but the code needs ['LOCK']") for p in problems), problems

    def test_a_lock_through_an_alias_resolves_to_its_table(self, tmp_path: Path) -> None:
        root = self._tree(
            tmp_path, "SELECT 1 FROM job j JOIN model_call mc ON mc.run_id = j.run_id FOR UPDATE OF mc"
        )
        seen = grants.observed_statements(root)
        assert seen["model_call"].verbs == {"LOCK"} and "job" not in seen, seen

    def test_a_write_to_a_read_only_table_is_refused(self, tmp_path: Path) -> None:
        root = self._tree(tmp_path, "INSERT INTO alembic_version (version_num) VALUES (:v)")
        problems = grants.evidence_problems(grants.observed_statements(root))
        assert any(p.startswith("alembic_version is read-only but the code needs ['INSERT']") for p in problems), problems

    def test_a_class_that_takes_away_what_the_code_does_is_refused(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _move(monkeypatch, "app_user_role", "append-only")
        problems = grants.evidence_problems(grants.observed_statements(SOURCE))
        assert any(p.startswith("app_user_role is append-only but the code needs ['DELETE']") for p in problems), problems


# --- the catalogue of a migrated database is the declaration ---------------------------------------


def test_the_schema_at_head_is_classified_whole(migrated_engine: Engine) -> None:
    _audit(migrated_engine)


class TestTheCatalogueRefusesWhatTheDeclarationDoesNotName:
    """Each case adds ONE object to a fresh clone of the migrated schema and the audit must name it."""

    def test_a_new_table_is_refused_by_name(self, migrated_engine: Engine) -> None:
        _run(migrated_engine, "CREATE TABLE zz_new_table (id text PRIMARY KEY)")
        with pytest.raises(grants.GrantClassificationRefused, match=r"tables with no grant classification: \['zz_new_table'\]"):
            _audit(migrated_engine)

    def test_a_new_view_is_refused(self, migrated_engine: Engine) -> None:
        _run(migrated_engine, "CREATE VIEW zz_new_view AS SELECT 1 AS one")
        with pytest.raises(grants.GrantClassificationRefused, match=r"views differ from schema_coverage.VIEWS"):
            _audit(migrated_engine)

    def test_a_new_sequence_owned_by_no_table_is_refused(self, migrated_engine: Engine) -> None:
        _run(migrated_engine, "CREATE SEQUENCE zz_new_sequence")
        with pytest.raises(grants.GrantClassificationRefused, match=r"sequences owned by no table: \['zz_new_sequence'\]"):
            _audit(migrated_engine)

    def test_a_new_identity_column_is_refused(self, migrated_engine: Engine) -> None:
        _run(migrated_engine, "ALTER TABLE project ADD COLUMN zz_serial bigint GENERATED ALWAYS AS IDENTITY")
        with pytest.raises(grants.GrantClassificationRefused, match=r"sequence owners differ from schema_coverage.SEQUENCES"):
            _audit(migrated_engine)

    def test_a_new_trigger_function_is_refused(self, migrated_engine: Engine) -> None:
        _run(
            migrated_engine,
            "CREATE FUNCTION zz_new_trigger() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RETURN NEW; END $$",
        )
        with pytest.raises(grants.GrantClassificationRefused, match=r"trigger functions differ.*unknown=\['zz_new_trigger'\]"):
            _audit(migrated_engine)

    def test_a_new_plain_function_is_refused(self, migrated_engine: Engine) -> None:
        _run(migrated_engine, "CREATE FUNCTION zz_new_helper(a int) RETURNS int LANGUAGE sql IMMUTABLE AS 'SELECT a'")
        with pytest.raises(grants.GrantClassificationRefused, match=r"plain functions differ.*unknown=\['zz_new_helper'\]"):
            _audit(migrated_engine)

    def test_a_dropped_table_is_refused(self, migrated_engine: Engine) -> None:
        _run(migrated_engine, "DROP TABLE alembic_version")
        with pytest.raises(grants.GrantClassificationRefused, match=r"classified tables the catalogue does not hold: \['alembic_version'\]"):
            _audit(migrated_engine)

    def test_a_relation_in_another_schema_is_refused(self, migrated_engine: Engine) -> None:
        _run(migrated_engine, "CREATE SCHEMA zz_other", "CREATE TABLE zz_other.t (a int)")
        with pytest.raises(grants.GrantClassificationRefused, match=r"relations outside schema public: \['zz_other.t'\]"):
            _audit(migrated_engine)


# --- the script carries the SQL this classification generates -------------------------------------


def test_the_script_embeds_the_sql_generated_from_the_classification() -> None:
    assert grants.script_drift(SCRIPT.read_text(encoding="utf-8")) == []


class TestTheScriptGoesStaleLoudly:
    def test_a_table_moved_to_another_class_makes_the_script_stale(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _move(monkeypatch, "project", "read-write")
        drift = grants.script_drift(SCRIPT.read_text(encoding="utf-8"))
        assert [d.split(":")[0] for d in drift] == ["apply", "check"], drift

    def test_a_hand_edited_apply_block_is_stale(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        edited = text.replace("GRANT USAGE ON SCHEMA public", "GRANT ALL ON SCHEMA public", 1)
        assert edited != text
        assert grants.script_drift(edited) == ["apply: the embedded SQL differs from the classification"]

    def test_a_script_without_the_block_is_stale(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        removed = re.sub(r"^# >>> generated: check-sql\n.*?^# <<< generated: check-sql\n", "", text, flags=re.DOTALL | re.MULTILINE)
        assert removed != text
        drift = grants.script_drift(removed)
        assert len(drift) == 1 and drift[0].startswith("check: the script does not hold exactly one"), drift

    def test_write_script_makes_a_stale_script_current_and_changes_nothing_else(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        stale = text.replace("GRANT USAGE ON SCHEMA public", "GRANT ALL ON SCHEMA public", 1)
        assert grants.write_blocks(stale) == text


def test_the_generated_apply_sql_grants_no_truncate_no_references_and_no_default_privileges() -> None:
    sql = grants.render_sql("apply")
    assert not re.search(r"GRANT[^;]*\b(TRUNCATE|REFERENCES|TRIGGER|MAINTAIN)\b", sql), "a grant of a forbidden privilege"
    assert "ALTER DEFAULT PRIVILEGES" not in sql
    assert not re.search(r"\bGRANT\s+ALL\b", sql)
    assert "REVOKE CREATE ON SCHEMA public FROM PUBLIC" in sql and "REVOKE CREATE ON SCHEMA public FROM :\"app_role\"" in sql


def test_the_generated_check_sql_asks_about_every_privilege_postgresql_knows() -> None:
    sql = grants.render_sql("check")
    for privilege in grants.ALL_TABLE_PRIVILEGES:
        assert f"('{privilege}')" in sql, privilege
    assert not re.search(r"\b(GRANT|REVOKE|CREATE ROLE|ALTER ROLE|DROP)\b", sql), "the verification changes nothing"
