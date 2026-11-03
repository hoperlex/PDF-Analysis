"""`REVIEW-FIX-SEAMS-1102` -- the recovery tooling is declared at the newest migration, always.

`scripts/recovery/schema_coverage.py` names the schema the restore audit, the project erase and the
product purge were written for (`HEAD`), and each of them refuses a database at any other head. A
migration that moves the head without moving that literal therefore turns the three tools into
refusals on exactly the databases they exist for (code review 2026-11-02, S8-02, S5-02: the literal
stayed at `0041_comparison_stage_core` while migrations ran to `0044_section_stats_uncapped`).
`tests/integration/recovery/test_schema_coverage.py` says the same against a live database; this one
needs none, so it is red in the cheap battery the moment a migration file is added.

The head is read two ways and both must equal `HEAD`: the revision of the file whose name sorts
last (the numbered file names are the convention), and the one revision no other file names as its
`down_revision` (what Alembic would call the head). Every guard here has a test that feeds it a tree
it must refuse.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERSIONS = ROOT / "db" / "migrations" / "versions"
COVERAGE = ROOT / "scripts" / "recovery" / "schema_coverage.py"

REVISION = re.compile(r"""^revision\s*(?::[^=\n]+)?=\s*['"]([^'"]+)['"]""", re.MULTILINE)
DOWN_REVISION = re.compile(r"""^down_revision\s*(?::[^=\n]+)?=\s*(?:None|['"]([^'"]+)['"])""", re.MULTILINE)


def declared_head() -> str:
    name = "recovery_schema_coverage_head_guard"
    spec = importlib.util.spec_from_file_location(name, COVERAGE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return str(module.HEAD)


def migration_files() -> dict[str, str]:
    return {path.name: path.read_text(encoding="utf-8") for path in sorted(VERSIONS.glob("*.py"))}


def head_problems(files: dict[str, str], declared: str) -> list[str]:
    """Every way the migration tree and the declared head disagree; empty when they agree."""
    revisions: dict[str, str] = {}
    parents: set[str] = set()
    for name, source in files.items():
        revision, down = REVISION.search(source), DOWN_REVISION.search(source)
        if revision is None or down is None:
            return [f"{name} does not state its revision and down_revision"]
        revisions[name] = revision.group(1)
        if down.group(1) is not None:
            parents.add(down.group(1))
    if not revisions:
        return ["no migration file found"]
    heads = sorted(revision for revision in revisions.values() if revision not in parents)
    newest = revisions[sorted(revisions)[-1]]
    problems: list[str] = []
    if len(heads) != 1:
        problems.append(f"the migration tree has {len(heads)} heads: {heads}")
    elif heads[0] != declared:
        problems.append(f"schema_coverage.HEAD is {declared!r}, the migration chain ends at {heads[0]!r}")
    if newest != declared:
        problems.append(f"schema_coverage.HEAD is {declared!r}, the newest migration file is {newest!r}")
    return problems


def test_the_recovery_tooling_is_declared_at_the_newest_migration() -> None:
    files = migration_files()
    assert len(files) > 40, "the migration tree was not found"
    assert head_problems(files, declared_head()) == []


def test_the_head_is_a_real_migration_revision() -> None:
    assert declared_head() in {match.group(1) for source in migration_files().values()
                               for match in [REVISION.search(source)] if match}


# -- the guard can fail ---------------------------------------------------------------------


def _next_migration(source_revision: str, number: str = "0099", name: str = "later_change") -> tuple[str, str]:
    revision = f"{number}_{name}"
    return f"20261231_{number}_{name}.py", (
        f'revision: str = "{revision}"\ndown_revision: str | None = "{source_revision}"\n')


def test_a_newer_migration_file_is_refused_until_the_head_moves() -> None:
    files, declared = migration_files(), declared_head()
    name, source = _next_migration(declared)
    files[name] = source
    assert head_problems(files, declared) == [
        f"schema_coverage.HEAD is {declared!r}, the migration chain ends at '0099_later_change'",
        f"schema_coverage.HEAD is {declared!r}, the newest migration file is '0099_later_change'",
    ]


def test_a_head_that_has_run_ahead_of_the_migrations_is_refused() -> None:
    files = migration_files()
    problems = head_problems(files, "0099_later_change")
    assert len(problems) == 2 and all("'0099_later_change'" in problem for problem in problems)


def test_a_head_that_lags_by_one_migration_is_refused() -> None:
    files = migration_files()
    newest = files[sorted(files)[-1]]
    previous = DOWN_REVISION.search(newest)
    assert previous is not None and previous.group(1) is not None
    problems = head_problems(files, previous.group(1))
    assert len(problems) == 2 and all(f"{previous.group(1)!r}" in problem for problem in problems)


def test_a_branch_in_the_migration_tree_is_refused() -> None:
    files, declared = migration_files(), declared_head()
    # a second child of the migration before the newest one: two chains end in different places
    newest = files[sorted(files)[-1]]
    previous = DOWN_REVISION.search(newest)
    assert previous is not None and previous.group(1) is not None
    name, source = _next_migration(previous.group(1), number="0098", name="side_branch")
    files[name] = source
    problems = head_problems(files, declared)
    assert any("2 heads" in problem for problem in problems), problems


def test_a_migration_file_without_a_revision_is_refused() -> None:
    files = migration_files()
    files["20261231_0099_broken.py"] = "print('no revision here')\n"
    assert head_problems(files, declared_head()) == ["20261231_0099_broken.py does not state its revision and down_revision"]


def test_an_empty_tree_is_refused() -> None:
    assert head_problems({}, declared_head()) == ["no migration file found"]
