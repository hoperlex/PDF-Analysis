"""`CLASSIFICATION-CORRECTION-01`: what migration ``0028`` restates, held equal to the code.

No database. A migration restates its vocabulary instead of importing it (it is history and
must not move when the application does), so the equality is a test's job: the stages, the
fifteen section codes and the reason bound are the correction rules'; the restored
``am_check_optimisation_pass_scope`` is ``0027``'s body character for character (whitespace
aside); the installed one differs from it in exactly the relation the version's classification
is read from.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from types import ModuleType

from auditmanager.sections import correction
from auditmanager.sections.suggestion import _catalogue

ROOT = Path(__file__).resolve().parents[3]
VERSIONS = ROOT / "db/migrations/versions"
MIGRATION = VERSIONS / "20261020_0028_classification_corrections.py"
PREVIOUS = VERSIONS / "20261020_0027_optimisation_proposals.py"
CLASSIFICATION = VERSIONS / "20261020_0024_version_classification.py"


def _module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _squash(sql: str) -> str:
    return re.sub(r"\s+", " ", sql).strip()


def _function_body_of_0027() -> str:
    source = PREVIOUS.read_text(encoding="utf-8")
    match = re.search(
        r"CREATE FUNCTION am_check_optimisation_pass_scope\(\).*?\$fn\$;", source, re.DOTALL
    )
    assert match is not None
    return _squash(match.group(0))


def test_the_revision_chain_and_the_restated_vocabulary_are_the_rules() -> None:
    migration = _module(MIGRATION, "migration_0028")
    assert migration.revision == "0028_classification_corrections"
    assert migration.down_revision == "0027_optimisation_proposals"
    assert migration.MAX_REASON_LENGTH == correction.MAX_REASON_LENGTH
    assert tuple(migration.PROJECT_STAGES) == correction.PROJECT_STAGES
    assert set(migration.PROJECT_SECTIONS) == {entry.code for entry in _catalogue()}
    assert len(migration.PROJECT_SECTIONS) == 15
    # and the vocabulary the original table's migration restated, kept in step
    original = _module(CLASSIFICATION, "migration_0024")
    assert tuple(migration.PROJECT_SECTIONS) == tuple(original.PROJECT_SECTIONS)
    assert tuple(migration.PROJECT_STAGES) == tuple(original.PROJECT_STAGES)


def test_the_downgrade_restores_the_0027_function_body_exactly() -> None:
    migration = _module(MIGRATION, "migration_0028_restore")
    restored = _squash(migration._pass_scope_function("document_version_classification"))
    assert restored.replace("CREATE OR REPLACE FUNCTION", "CREATE FUNCTION", 1) == _function_body_of_0027()


def test_the_installed_function_differs_only_in_the_relation_it_reads() -> None:
    migration = _module(MIGRATION, "migration_0028_install")
    installed = _squash(migration._pass_scope_function("version_classification_current"))
    restored = _squash(migration._pass_scope_function("document_version_classification"))
    assert installed != restored
    assert installed.replace("version_classification_current", "document_version_classification") == restored
    assert "JOIN version_classification_current c ON c.version_uid = v.version_uid" in installed
    assert "c.section_code = 'AR'" in installed


def test_the_upgrade_creates_the_objects_the_repository_reads_and_nothing_else_is_dropped() -> None:
    source = MIGRATION.read_text(encoding="utf-8")
    upgrade = source[source.index("def upgrade()") : source.index("def downgrade()")]
    for name in (
        "document_version_classification_correction",
        "am_check_classification_correction_chain",
        "version_classification_revision",
        "version_classification_current",
        "trg_document_version_classification_correction_immutable",
        "trg_document_version_classification_correction_chain",
    ):
        assert name in upgrade, name
    downgrade = source[source.index("def downgrade()") :]
    # only this revision's own objects are dropped; the original table is never touched
    assert "DROP TABLE document_version_classification_correction;" in downgrade
    assert "DROP TABLE document_version_classification;" not in downgrade
    assert "DROP VIEW version_classification_current;" in downgrade
    assert "DROP VIEW version_classification_revision;" in downgrade
    assert downgrade.index("_pass_scope_function(\"document_version_classification\")") < downgrade.index(
        "DROP VIEW version_classification_current;"
    ), "the function must stop reading the view before the view is dropped"
