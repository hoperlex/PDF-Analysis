"""`COMPARE-PERSISTED-SUMMARY-01`: what migration ``0035`` restates, held equal to the code.

No database. A migration restates its vocabulary instead of importing it (it is history and must
not move when the application does), so the equalities are a test's job.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from auditmanager.comparison import audit, approved_evidence, raw_text, service, sheet_links
from auditmanager.comparison import version_reader

ROOT = Path(__file__).resolve().parents[3]
THIS = ROOT / "db/migrations/versions/20261027_0035_comparison_records.py"


def _module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("migration_0035", THIS)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_chain_and_the_revision_id() -> None:
    migration = _module()
    assert migration.revision == "0035_comparison_records"
    assert migration.down_revision == "0034_pass_scope_all_sections"
    # alembic_version.version_num is varchar(32): a longer id cannot be stored
    assert len(migration.revision) <= 32


def test_the_restated_bounds_equal_the_code() -> None:
    migration = _module()
    assert migration.MAX_ACTIVE_LINKS == raw_text.MAX_PAIRS == sheet_links.MAX_ACTIVE_LINKS
    assert migration.MAX_PAGE_NUMBER == version_reader.MAX_VERSION_PAGES
    assert tuple(migration.EVENT_KINDS) == sheet_links.EVENT_KINDS
    # The served response budget of the approved differences is the proposal diffs' budget.
    assert approved_evidence.MAX_APPROVED_CHANGED_CHARACTERS == service.MAX_DIFF_PAGE_CHARACTERS


def test_the_chain_function_states_the_limit_it_enforces() -> None:
    migration = _module()
    assert f"active_links >= {raw_text.MAX_PAIRS}" in migration._CHAIN_FUNCTION
    # The trigger serialises writers with the advisory lock whose key the repository builds.
    key = sheet_links.lock_key("ver_a", "ver_b")
    assert key == "comparison_sheet_link:ver_a:ver_b"
    assert "'comparison_sheet_link:' || NEW.source_version_uid || ':' || NEW.target_version_uid" in (
        " ".join(migration._CHAIN_FUNCTION.split())
    )


def test_the_journal_event_types_are_the_ones_the_migration_comment_and_purge_expect() -> None:
    assert audit.COMPARISON_EVENT_TYPES == (
        "comparison.sheet_link_approved", "comparison.sheet_link_withdrawn",
    )
    assert all(name.startswith("comparison.") for name in audit.COMPARISON_EVENT_TYPES)
