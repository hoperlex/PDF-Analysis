"""`D-129` Y F-7: the API edge recognises a driver refusal without importing the driver library.

``AGENTS.md`` section 4 forbids direct SQL from a router. ``api/routers/errors.py`` classifies
database failures into the error envelope and used to do so with ``from sqlalchemy.exc import
DBAPIError``. The name now comes from ``auditmanager.shared.db.public``, which re-exports the
same class, so nothing about classification may have moved. No database: the refusals below
are built by hand, which proves the classifier reads the SQLSTATE and the names line up -- that
a *real* trigger's refusal reaches the typed code stays with
``tests/integration/api/test_database_refusals.py``.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
import sqlalchemy.exc

from auditmanager.api.routers import errors
from auditmanager.shared.db import public as db_public
from auditmanager.shared.errors import DomainError, ErrorCode

API_ROOT = Path(__file__).resolve().parents[3] / "src" / "auditmanager" / "api"


def sqlalchemy_imports(source: str) -> list[str]:
    """Every ``sqlalchemy`` import in ``source``, as ``line: module``."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            names = [node.module or ""]
        else:
            continue
        found.extend(
            f"{node.lineno}: {name}"
            for name in names
            if name == "sqlalchemy" or name.startswith("sqlalchemy.")
        )
    return found


class _Driver(Exception):
    """A driver's own exception: only the structured SQLSTATE field matters to the edge."""

    def __init__(self, sqlstate: str | None) -> None:
        super().__init__("driver prose that must never reach an envelope")
        self.sqlstate = sqlstate


def _refusal(sqlstate: str | None) -> sqlalchemy.exc.DBAPIError:
    return sqlalchemy.exc.DBAPIError("UPDATE t SET x = 1", {}, _Driver(sqlstate))


# --- the guard, and proof the detector can see ---------------------------------------


@pytest.mark.parametrize(
    "source",
    [
        "from sqlalchemy.exc import DBAPIError\n",
        "import sqlalchemy.orm\n",
        "import sqlalchemy as sa\n",
        "from sqlalchemy import text\n",
    ],
)
def test_the_detector_sees_every_spelling_of_a_sqlalchemy_import(source: str) -> None:
    assert sqlalchemy_imports(source) != []


def test_the_detector_passes_the_boundary_name() -> None:
    assert sqlalchemy_imports("from auditmanager.shared.db.public import DBAPIError\n") == []


def test_no_module_of_the_api_package_imports_sqlalchemy() -> None:
    sources = sorted(API_ROOT.rglob("*.py"))
    assert len(sources) > 10, f"the API package was not found under {API_ROOT}"
    offenders = {
        path.relative_to(API_ROOT).as_posix(): found
        for path in sources
        if (found := sqlalchemy_imports(path.read_text(encoding="utf-8")))
    }
    assert offenders == {}


# --- no behaviour change -------------------------------------------------------------


def test_the_edge_name_is_the_driver_class_itself() -> None:
    """Same object: an ``isinstance`` or ``except`` against it matches what it always matched."""
    assert db_public.DBAPIError is sqlalchemy.exc.DBAPIError
    assert errors.DBAPIError is sqlalchemy.exc.DBAPIError


@pytest.mark.parametrize("sqlstate", ["AM001", "AM002", "AM003"])
def test_the_three_custom_sqlstates_report_the_transition_code(sqlstate: str) -> None:
    refusal = _refusal(sqlstate)

    assert errors.error_code_for(refusal) is ErrorCode.STATE_TRANSITION_NOT_ALLOWED
    assert errors.to_domain_error(refusal).code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED


@pytest.mark.parametrize("sqlstate", ["23505", "40001", None])
def test_any_other_driver_refusal_is_an_internal_error_carrying_nothing(
    sqlstate: str | None,
) -> None:
    refusal = _refusal(sqlstate)

    assert errors.error_code_for(refusal) is None
    mapped = errors.to_domain_error(refusal)
    assert mapped.code is ErrorCode.INTERNAL_ERROR
    assert "driver prose" not in repr(mapped.envelope("cid").as_dict())


def test_a_domain_error_passes_through_unchanged() -> None:
    typed = DomainError(ErrorCode.NOT_FOUND)

    assert errors.to_domain_error(typed) is typed


def test_guarded_adds_the_callers_details_to_a_mapped_refusal() -> None:
    def handler() -> None:
        raise _refusal("AM001")

    with pytest.raises(DomainError) as raised:
        errors.guarded(handler, machine="audit_run")()

    assert raised.value.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED
    assert raised.value.envelope("cid").as_dict()["details"] == {"machine": "audit_run"}


def test_guarded_lets_an_unmapped_refusal_through_untouched() -> None:
    refusal = _refusal("23505")

    def handler() -> None:
        raise refusal

    with pytest.raises(sqlalchemy.exc.DBAPIError) as raised:
        errors.guarded(handler)()

    assert raised.value is refusal
