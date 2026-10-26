"""`OPT-PROJECT-ALL-SECTIONS-01`: what migration ``0034`` restates, held equal to ``0028``.

No database. A migration restates its SQL instead of importing it (it is history and must not
move when another migration does), so the equalities are a test's job:

* the function ``0034``'s downgrade restores is ``0028``'s installed function **exactly** (the
  string ``0028`` itself generates for ``version_classification_current``), so the round trip is
  byte for byte and ``pg_get_functiondef`` reads the same before and after;
* the function ``0034`` installs differs from it in exactly the lines the rule changed -- the
  version's ``AR`` condition is gone, the vendor list's section equals the version's, and the
  exception text stops saying «AR» -- and in no other: every other condition stays;
* the revision id fits ``alembic_version.version_num`` (``varchar(32)``).
"""

from __future__ import annotations

import difflib
import importlib.util
import re
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[3]
VERSIONS = ROOT / "db/migrations/versions"
THIS = VERSIONS / "20261027_0034_pass_scope_all_sections.py"
MIGRATION_0028 = VERSIONS / "20261020_0028_classification_corrections.py"
MIGRATION_0027 = VERSIONS / "20261020_0027_optimisation_proposals.py"


def _module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _lines(sql: str) -> list[str]:
    return [line.strip() for line in sql.strip().splitlines()]


def _changes(old: str, new: str) -> tuple[list[str], list[str]]:
    removed: list[str] = []
    added: list[str] = []
    for line in difflib.unified_diff(_lines(old), _lines(new), lineterm="", n=0):
        if line.startswith(("---", "+++", "@@")):
            continue
        (removed if line.startswith("-") else added).append(line[1:])
    return removed, added


def test_the_chain_and_the_revision_id() -> None:
    migration = _module(THIS, "migration_0034")
    assert migration.revision == "0034_pass_scope_all_sections"
    assert migration.down_revision == "0033_ar_v3_cite_stage_id"
    # alembic_version.version_num is varchar(32): a longer id cannot be stored
    assert len(migration.revision) <= 32


def test_the_downgrade_restores_0028s_installed_function_exactly() -> None:
    migration = _module(THIS, "migration_0034_restore")
    original = _module(MIGRATION_0028, "migration_0028_for_0034")
    assert migration._FUNCTION_0028 == original._pass_scope_function("version_classification_current")


def test_0028s_function_is_0027s_apart_from_the_relation_it_reads() -> None:
    """The chain of restatements holds: 0027 -> 0028 (the relation) -> 0034 (the section rule)."""
    migration = _module(THIS, "migration_0034_chain")
    first = re.search(
        r"CREATE FUNCTION am_check_optimisation_pass_scope\(\).*?\$fn\$;",
        MIGRATION_0027.read_text(encoding="utf-8"),
        re.DOTALL,
    )
    assert first is not None
    squash = lambda sql: re.sub(r"\s+", " ", sql).strip()  # noqa: E731
    restored = squash(migration._FUNCTION_0028).replace("CREATE OR REPLACE FUNCTION", "CREATE FUNCTION", 1)
    assert restored.replace("version_classification_current", "document_version_classification") == squash(
        first.group(0)
    )


def test_the_installed_function_differs_from_0028s_in_exactly_the_section_rule() -> None:
    migration = _module(THIS, "migration_0034_install")
    removed, added = _changes(migration._FUNCTION_0028, migration._FUNCTION_0034)
    assert removed == [
        "AND c.section_code = 'AR'",
        "AND l.section_code = 'AR'",
        "'state_transition_not_allowed: optimisation pass % does not pin one AR '",
        "'project and an AR vendor list in force for it', NEW.optimisation_pass_id",
    ]
    assert added == [
        "AND l.section_code = c.section_code",
        "'state_transition_not_allowed: optimisation pass % does not pin one classified '",
        "'project and a vendor list of that version''s section in force for it',",
        "NEW.optimisation_pass_id",
    ]
    installed = migration._FUNCTION_0034
    for kept in (
        "JOIN version_classification_current c ON c.version_uid = v.version_uid",
        "AND d.project_uid = NEW.project_uid",
        "AND v.version_uid = NEW.version_uid",
        "AND r.run_id = NEW.run_id",
        "AND r.project_uid = NEW.project_uid",
        "AND p.price_list_id = NEW.price_list_id",
        "AND l.mode = 'list'",
        "AND l.scope = NEW.vendor_list_source",
        "AND (l.scope = 'global' OR l.project_uid = NEW.project_uid)",
        "USING ERRCODE = 'AM001'",
    ):
        assert kept in installed, kept
    assert "'AR'" not in installed  # no section is named: the rule is an equality


def test_the_upgrade_installs_it_and_the_downgrade_refuses_before_restoring() -> None:
    source = THIS.read_text(encoding="utf-8")
    upgrade = source[source.index("def upgrade()") : source.index("def downgrade()")]
    downgrade = source[source.index("def downgrade()") :]
    assert "op.execute(_FUNCTION_0034)" in upgrade and "_FUNCTION_0028" not in upgrade
    assert "0034 downgrade refused" in downgrade
    assert downgrade.index("raise RuntimeError") < downgrade.index("op.execute(_FUNCTION_0028)")
