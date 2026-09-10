"""Fixtures for the stage-result contract suite.

This suite runs under the **runtime** interpreter (`.venv/bin/pytest`), which carries
no JSON Schema validator, and reaches a real Draft 2020-12 implementation by driving
`stage_result_schema_check.py` through the **governance** interpreter
(`.venv/bootstrap/bin/python`), the only one holding `jsonschema`.

It fails closed. A missing governance interpreter is an error, never a skip: a suite
that silently stops checking where the dependency is absent is exactly where a defect
of this class survives.

Nothing here reaches a database or an object store. Every payload is produced by
constructing `StageResult` values in memory, because what is under test is the shape
this package emits, not the services it emits it into.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Callable

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SCHEMA = (
    REPOSITORY_ROOT / "contracts" / "analysis" / "v1" / "stage-result.schema.json"
)
EXAMPLES = REPOSITORY_ROOT / "contracts" / "analysis" / "v1" / "examples"
CHECKER = Path(__file__).resolve().parent / "stage_result_schema_check.py"
GOVERNANCE_PYTHON = REPOSITORY_ROOT / ".venv" / "bootstrap" / "bin" / "python"


@pytest.fixture(scope="session")
def stage_result_schema() -> dict[str, Any]:
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def contract_examples() -> dict[str, Any]:
    """The contract's own example payloads, valid and deliberately invalid."""
    return {
        path.name: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(EXAMPLES.glob("stage-result*.json"))
    }


@pytest.fixture(scope="session")
def validate() -> Callable[[dict[str, Any], list[dict[str, Any]]], dict[str, Any]]:
    """Evaluate cases against a schema with a real Draft 2020-12 validator."""
    if not GOVERNANCE_PYTHON.exists():
        raise AssertionError(
            f"the governance interpreter is missing at {GOVERNANCE_PYTHON}. "
            "This suite validates against JSON Schema 2020-12 and will not pass "
            "without one. Run: make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12"
        )

    def run(
        schema: dict[str, Any], cases: list[dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        job = json.dumps({"schema": schema, "cases": cases})
        completed = subprocess.run(
            [str(GOVERNANCE_PYTHON), str(CHECKER)],
            input=job,
            capture_output=True,
            text=True,
            cwd=REPOSITORY_ROOT,
        )
        if completed.returncode != 0:
            raise AssertionError(
                "the stage-result schema validation could not be performed "
                f"(exit {completed.returncode}):\n{completed.stderr}"
            )
        results = json.loads(completed.stdout)["results"]
        return {result["name"]: result for result in results}

    return run
