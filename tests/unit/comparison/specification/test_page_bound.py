"""A comparison version may exceed 500 pages only under the relaxed intake, and then every comparison table accepts its pages (`REVIEW-FIX-CMP-SPEC-1102`).

Code review 2026-11-02, S2-blocks-4-9-02. Three parts: the reader's bound follows the one intake flag (measured in a child process per mode,
as ``tests/unit/ingest/test_intake_mode.py`` does); the refusal of a version over the bound is a typed validation refusal and not an
integrity error; and migration 0045 -- checked here against the text of the migrations it relaxes, with a recording stand-in for ``op``,
because no database is assigned to this lane (what PostgreSQL does with the same statements is for the gate).
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

import auditmanager
from auditmanager.comparison import service as comparison_service
from auditmanager.comparison.version_reader import VersionPairRefused

SOURCE = Path(auditmanager.__file__).resolve().parents[1]
ROOT = SOURCE.parent
VERSIONS = ROOT / "db" / "migrations" / "versions"
MIGRATION = VERSIONS / "20261102_0045_comparison_page_bounds.py"
RELAXES = ("20261027_0035_comparison_records.py", "20261028_0038_comparison_foundation.py",
           "20261028_0039_comparison_core.py", "20261029_0040_comparison_ai_reports.py")
INT = 2**31 - 1

_PROBE = """
import json
from auditmanager.comparison import version_reader as reader
def row(pages):
    return {"version_uid": "ver_01M2545JSD15ETSNNV904X991J", "version_document_uid": "doc_01M2545JSD15ETSNNV904X991D",
            "set_document_uid": "doc_01M2545JSD15ETSNNV904X991D", "project_uid": "prj_01M2545JSD15ETSNNV904X991F",
            "version_ordinal": 1, "state": "published", "sha256": "a" * 64, "byte_size": 1, "page_count": pages,
            "media_type": "application/pdf"}
def verdict(pages):
    try:
        reader._version_facts(row(pages), project_uid="prj_01M2545JSD15ETSNNV904X991F", document_uid="doc_01M2545JSD15ETSNNV904X991D")
        return "admitted"
    except reader.VersionPairRefused as refusal:
        return str(refusal)
print(json.dumps({"max": reader.MAX_VERSION_PAGES, "500": verdict(500), "501": verdict(501), "int": verdict(2**31 - 1), "zero": verdict(0)}))
"""


def measure(relaxed: str | None) -> dict[str, Any]:
    environment = {key: value for key, value in os.environ.items() if key != "AUDITMANAGER_INTAKE_RELAXED"}
    environment["PYTHONPATH"] = str(SOURCE)
    if relaxed is not None:
        environment["AUDITMANAGER_INTAKE_RELAXED"] = relaxed
    finished = subprocess.run([sys.executable, "-c", _PROBE], env=environment, capture_output=True, text=True, check=False, timeout=120)
    assert finished.returncode == 0, finished.stderr[-2000:]
    return json.loads(finished.stdout)


def test_by_default_a_version_over_500_pages_is_refused_up_front() -> None:
    for flag in (None, "0"):
        assert measure(flag) == {"max": 500, "500": "admitted", "501": "version_page_count_invalid",
                                 "int": "version_page_count_invalid", "zero": "version_page_count_invalid"}


def test_under_the_relaxed_intake_the_bound_is_the_database_integer() -> None:
    assert measure("1") == {"max": INT, "500": "admitted", "501": "admitted", "int": "admitted", "zero": "version_page_count_invalid"}


# -- the refusal is a typed validation refusal -------------------------------------------------------------------------


def _refused_with(monkeypatch: pytest.MonkeyPatch, reason: str) -> None:
    def refuse(*_: Any, **__: Any) -> Any:
        raise VersionPairRefused(reason)

    monkeypatch.setattr(comparison_service, "read_ordered_version_pair", refuse)
    request = SimpleNamespace(project_uid="prj_x", document_uid="doc_x", source_version_uid="ver_a", target_version_uid="ver_b")
    comparison_service.VersionComparisonService._version_pair(None, request)  # type: ignore[arg-type]  # noqa: SLF001


def test_a_version_over_the_bound_is_a_request_refusal_not_an_integrity_error(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(comparison_service.ComparisonRequestInvalid, match="version_page_count_invalid"):
        _refused_with(monkeypatch, "version_page_count_invalid")


def test_a_contradiction_in_the_stored_row_is_still_an_integrity_error(monkeypatch: pytest.MonkeyPatch) -> None:
    for reason in ("version_row_invalid", "version_digest_invalid", "version_byte_size_invalid", "version_media_type_invalid"):
        with pytest.raises(comparison_service.ComparisonIntegrityError):
            _refused_with(monkeypatch, reason)


# -- migration 0045 ---------------------------------------------------------------------------------------------------


def migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("migration_0045", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def squeeze(text: str) -> str:
    return re.sub(r"\s+", " ", text).replace("( ", "(").replace(" )", ")").strip()


def check_text(file: str, table: str, name: str) -> str:
    """The text of ``CHECK (...)`` of constraint ``name`` inside ``CREATE TABLE table`` of the file, ``{MAX_PAGE_NUMBER}`` as 500."""
    source = (VERSIONS / file).read_text(encoding="utf-8").replace("{MAX_PAGE_NUMBER}", "500")
    start = source.index(f"CREATE TABLE {table} (")
    following = re.search(r"CREATE TABLE \w+ \(", source[start + 10:])
    body = source[start: start + 10 + following.start()] if following else source[start:]
    declared = re.search(rf"CONSTRAINT {name}\s+CHECK \(", body)
    assert declared is not None, f"{name} is not a CHECK of {table} in {file}"
    depth, index = 1, declared.end()
    while depth:
        depth += {"(": 1, ")": -1}.get(body[index], 0)
        index += 1
    return squeeze(body[declared.end(): index - 1])


def test_the_revision_follows_the_head_it_replaces() -> None:
    module = migration()
    assert module.revision == "0045_comparison_page_bounds" and module.down_revision == "0044_section_stats_uncapped"
    assert len(module.revision) <= 32  # alembic_version.version_num is varchar(32)
    assert len(module.PAGE_CHECKS) == 7


def test_every_former_condition_is_the_text_of_the_check_it_relaxes() -> None:
    """The downgrade must restore exactly what 0035/0038/0039/0040 created: compared with their text, not retyped from memory."""
    for table, name, relaxed, former, _columns in migration().PAGE_CHECKS:
        found = [check_text(file, table, name) for file in RELAXES if f"CONSTRAINT {name}" in (VERSIONS / file).read_text(encoding="utf-8")]
        assert len(found) == 1, f"{name} is created in {len(found)} of the four migrations"
        assert squeeze(former) == found[0], (name, former, found[0])
        assert "500" not in relaxed and "BETWEEN" not in relaxed
        assert re.search(r">= 1", relaxed), name


def test_no_other_page_bound_remains_in_the_four_migrations() -> None:
    """The enumerator: every CHECK that bounds a page number in the four migrations is relaxed here, but the count of versions of an order."""
    relaxed = {name for _t, name, _r, _f, _c in migration().PAGE_CHECKS}
    found: set[str] = set()
    for file in RELAXES:
        source = (VERSIONS / file).read_text(encoding="utf-8")
        for match in re.finditer(r"CONSTRAINT (\w+)\s+CHECK \(", source):
            tail = source[match.end(): match.end() + 600].split("CONSTRAINT ", 1)[0]
            if "{MAX_PAGE_NUMBER}" in tail:
                found.add(match.group(1))
    assert found - relaxed == {"ck_comparison_version_order_versions_is_array"}, found - relaxed
    assert relaxed <= found


class Recorder:
    """A stand-in for ``alembic.op`` that records, and a connection whose guard queries answer from ``large``."""

    def __init__(self, large: set[str]) -> None:
        self.large, self.calls, self.queries = large, [], []

    def get_bind(self) -> Any:
        recorder = self

        class Connection:
            def execute(self, statement: Any, params: dict[str, Any]) -> Any:
                sql = str(statement)
                recorder.queries.append((sql, dict(params)))
                table = re.search(r"FROM (\w+) WHERE", sql).group(1)  # type: ignore[union-attr]
                return SimpleNamespace(scalar_one=lambda: table in recorder.large)

        return Connection()

    def drop_constraint(self, name: str, table: str, type_: str) -> None:
        self.calls.append(("drop", table, name))

    def create_check_constraint(self, name: str, table: str, condition: str) -> None:
        self.calls.append(("create", table, name, condition))


def run(monkeypatch: pytest.MonkeyPatch, step: str, large: set[str] = frozenset()) -> Recorder:  # type: ignore[assignment]
    module = migration()
    recorder = Recorder(set(large))
    monkeypatch.setattr(module, "op", recorder)
    getattr(module, step)()
    return recorder


def test_upgrade_swaps_seven_checks_for_their_lower_bounds(monkeypatch: pytest.MonkeyPatch) -> None:
    recorder = run(monkeypatch, "upgrade")
    checks = migration().PAGE_CHECKS
    assert recorder.queries == []
    assert recorder.calls == [step for table, name, relaxed, _f, _c in checks
                              for step in (("drop", table, name), ("create", table, name, relaxed))]


def test_the_downgrade_refuses_while_a_page_above_500_exists_and_touches_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    tables = [table for table, *_ in migration().PAGE_CHECKS]
    for table in sorted(set(tables)):
        recorder = Recorder({table})
        module = migration()
        monkeypatch.setattr(module, "op", recorder)
        with pytest.raises(RuntimeError, match="comparison_page_bounds_large_pages_exist"):
            module.downgrade()
        assert recorder.calls == [], f"a row of {table} above 500 must stop the downgrade before any constraint changes"
        assert all(params == {"maximum": 500} for _sql, params in recorder.queries)


def test_the_guard_looks_at_every_bounded_column(monkeypatch: pytest.MonkeyPatch) -> None:
    recorder = run(monkeypatch, "downgrade")
    asked = [(re.search(r"FROM (\w+) WHERE", sql).group(1), sorted(re.findall(r"(\w+) > :maximum", sql)))  # type: ignore[union-attr]
             for sql, _params in recorder.queries]
    assert asked == [(table, sorted(columns)) for table, _n, _r, _f, columns in migration().PAGE_CHECKS]


def test_the_downgrade_restores_the_former_checks_when_no_page_is_above_500(monkeypatch: pytest.MonkeyPatch) -> None:
    recorder = run(monkeypatch, "downgrade")
    checks = migration().PAGE_CHECKS
    assert recorder.calls == [step for table, name, _r, former, _c in checks
                              for step in (("drop", table, name), ("create", table, name, former))]
