"""`AR-V3-OPT-IN` (design 4.2 and 4.8): the one place that decides whether a deployment lets AR v3 be started is pinned.

"A pack that is installed does not by itself allow a start" is carried by a single keyword of the composition root:
``RunAdapter(..., ar_v3_start_allowed=_ar_v3_start_allowed(env, ...))`` in ``build_application``. This module reads the
source as syntax (container-free, as ``test_composition_pins_the_cost_consent_gate.py`` does): the keyword is passed
once, by the ``api`` build only, and its value is the strict reader and not a constant. Controls plant the mutations a
careless edit would make and show the reader goes red on each. The reader itself is exercised on its values.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from auditmanager.bootstrap import composition
from auditmanager.bootstrap.settings import ConfigurationError
from auditmanager.runs.public import START_ALLOWED_ENV

COMPOSITION = Path(composition.__file__).resolve()


def _calls(source: str, name: str) -> list[tuple[str, ast.Call]]:
    """``(enclosing function, call)`` of every call to ``name`` however it is spelled."""
    found: list[tuple[str, ast.Call]] = []
    for function in ast.walk(ast.parse(source)):
        if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for node in ast.walk(function):
            if isinstance(node, ast.Call) and ast.unparse(node.func).rsplit(".", 1)[-1] == name:
                found.append((function.name, node))
    return found


def _allowance_keywords(source: str) -> list[tuple[str, ast.expr]]:
    found: list[tuple[str, ast.expr]] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call):
            for keyword in node.keywords:
                if keyword.arg == "ar_v3_start_allowed":
                    found.append((ast.unparse(node.func).rsplit(".", 1)[-1], keyword.value))
    return found


def _allowance_is_pinned(source: str) -> bool:
    """Exactly one call passes the keyword; it is the run adapter; the value calls the strict reader, in the api build only."""
    found = _allowance_keywords(source)
    if len(found) != 1:
        return False
    callee, value = found[0]
    if callee != "RunAdapter" or not (isinstance(value, ast.Call) and ast.unparse(value.func) == "_ar_v3_start_allowed"):
        return False
    readers = _calls(source, "_ar_v3_start_allowed")
    return [name for name, _ in readers if name != "_ar_v3_start_allowed"] == ["build_application"]


def test_the_composition_root_passes_the_strict_reader_to_the_run_adapter_once_and_only_from_the_api_build() -> None:
    source = COMPOSITION.read_text(encoding="utf-8")
    assert _allowance_is_pinned(source), _allowance_keywords(source)
    # The worker executes what was accepted: it never reads the variable.
    assert "build_worker_runtime" not in {name for name, _ in _calls(source, "_ar_v3_start_allowed")}
    assert START_ALLOWED_ENV not in source.split("def build_worker_runtime", 1)[1].split("def build_application", 1)[0]


def test_the_reader_goes_red_when_the_keyword_is_removed_made_constant_duplicated_or_moved_to_the_worker() -> None:
    source = COMPOSITION.read_text(encoding="utf-8")
    assert _allowance_is_pinned(source)
    call = "ar_v3_start_allowed=_ar_v3_start_allowed(env, ar_v3_installed_pack),"
    assert source.count(call) == 1
    assert not _allowance_is_pinned(source.replace(call, "ar_v3_start_allowed=True,"))
    assert not _allowance_is_pinned(source.replace(call, "ar_v3_start_allowed=bool(env.get('X')),"))
    removed = source.replace("        " + call + "\n", "")
    assert removed != source and not _allowance_is_pinned(removed)
    assert not _allowance_is_pinned(source + "\n_second = RunAdapter(ar_v3_start_allowed=_ar_v3_start_allowed(env, None))\n")
    moved = source.replace(
        "    ar_v3_pack_registry = _ar_v3_pack_registry(env)\n",
        "    ar_v3_pack_registry = _ar_v3_pack_registry(env)\n    _ar_v3_start_allowed(env, None)\n", 1,
    )
    assert moved != source and not _allowance_is_pinned(moved)


@pytest.mark.parametrize(("env", "expected"), [
    ({}, False), ({START_ALLOWED_ENV: ""}, False), ({START_ALLOWED_ENV: "  "}, False), ({START_ALLOWED_ENV: "0"}, False),
    ({START_ALLOWED_ENV: "1"}, True), ({START_ALLOWED_ENV: " 1 "}, True),
])
def test_the_reader_is_off_unless_the_environment_says_one(env: dict[str, str], expected: bool) -> None:
    assert composition._ar_v3_start_allowed(env, None) is expected


@pytest.mark.parametrize("value", ["true", "yes", "2", "1x", " 1x", "on"])
def test_a_value_that_is_not_plainly_zero_or_one_refuses_the_start_naming_the_variable(value: str) -> None:
    with pytest.raises(ConfigurationError) as refused:
        composition._ar_v3_start_allowed({START_ALLOWED_ENV: value}, None)
    assert START_ALLOWED_ENV in str(refused.value)


def test_the_value_is_logged_once_with_the_pack_state(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("INFO", logger=composition.__name__):
        composition._ar_v3_start_allowed({START_ALLOWED_ENV: "1"}, None)
    messages = [record.getMessage() for record in caplog.records if "AR v3 beta" in record.getMessage()]
    assert messages == [f"AR v3 beta: pack not installed, starts allowed ({START_ALLOWED_ENV})"]
