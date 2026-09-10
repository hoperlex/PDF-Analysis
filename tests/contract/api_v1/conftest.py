"""Fixtures for the `contracts/api/v1` schema-composition suite.

This suite runs under the **runtime** interpreter (`.venv/bin/pytest`), which carries
no JSON Schema validator, and reaches a real Draft 2020-12 implementation by driving
`schema_validation_check.py` through the **governance** interpreter
(`.venv/bootstrap/bin/python`), the only one holding `jsonschema`.

It fails closed. A missing governance interpreter is an error, never a skip: a suite
that silently stops checking where the dependency is absent is exactly where a defect
of this class survives.
"""

from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path
from typing import Any, Callable

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
OPENAPI = REPOSITORY_ROOT / "contracts" / "api" / "v1" / "openapi.json"
PAYLOAD = Path(__file__).resolve().parent / "finding_detail.example.json"
CHECKER = Path(__file__).resolve().parent / "schema_validation_check.py"
GOVERNANCE_PYTHON = REPOSITORY_ROOT / ".venv" / "bootstrap" / "bin" / "python"

#: The two properties `FindingDetail` exists to add to `Finding`, per the
#: `finding_current_verdict` projection in docs/program/P02_SEAMS.md section 5.4.
DETAIL_ONLY_PROPERTIES = frozenset({"latest_comment", "decision_event_count"})

#: A property no schema in the document declares, used to prove closure is still real.
UNKNOWN_PROPERTY = "smuggled_field"


# Both constants are also fixtures. Under `--import-mode=importlib`, set repository-wide
# in pyproject.toml, a test module cannot `import conftest`, and pyproject is explicit
# that a lane must not reach for a sys.path hack to get around it.


@pytest.fixture(scope="session")
def detail_only_properties() -> frozenset[str]:
    return DETAIL_ONLY_PROPERTIES


@pytest.fixture(scope="session")
def unknown_property() -> str:
    return UNKNOWN_PROPERTY


@pytest.fixture(scope="session")
def openapi_document() -> dict[str, Any]:
    return json.loads(OPENAPI.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def finding_detail_payload() -> dict[str, Any]:
    """A realistic `GET /findings/{finding_uid}` 200 body, carrying both added fields."""
    return json.loads(PAYLOAD.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def finding_payload(finding_detail_payload: dict[str, Any]) -> dict[str, Any]:
    """The same body reduced to the `Finding` field set."""
    return {
        key: value
        for key, value in finding_detail_payload.items()
        if key not in DETAIL_ONLY_PROPERTIES
    }


@pytest.fixture(scope="session")
def validate() -> Callable[[dict[str, Any], list[dict[str, Any]]], dict[str, Any]]:
    """Evaluate cases against a document with a real Draft 2020-12 validator.

    The document is a parameter rather than the file on disk, so a case can be run
    against a deliberately mutated copy and the defect shape stays under test.
    """
    if not GOVERNANCE_PYTHON.exists():
        raise AssertionError(
            f"the governance interpreter is missing at {GOVERNANCE_PYTHON}. "
            "This suite validates against JSON Schema 2020-12 and will not pass "
            "without one. Run: make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12"
        )

    def run(
        document: dict[str, Any], cases: list[dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        job = json.dumps({"document": document, "cases": cases})
        completed = subprocess.run(
            [str(GOVERNANCE_PYTHON), str(CHECKER)],
            input=job,
            capture_output=True,
            text=True,
            cwd=REPOSITORY_ROOT,
        )
        if completed.returncode != 0:
            raise AssertionError(
                "the schema validation check could not be performed "
                f"(exit {completed.returncode}):\n{completed.stderr}"
            )
        results = json.loads(completed.stdout)["results"]
        return {result["name"]: result for result in results}

    return run


@pytest.fixture(scope="session")
def document_with_the_pre_fix_shape(
    openapi_document: dict[str, Any],
) -> dict[str, Any]:
    """The document as it stood before this repair, rebuilt in memory.

    `FindingDetail` composed a `$ref` to the closed `Finding` with an `allOf` branch
    carrying the two added properties. Keeping it here, evaluated by the same
    validator, is what proves the guard below can fail - the defect is reproduced on
    every run rather than recorded in prose.
    """
    document = copy.deepcopy(openapi_document)
    detail = document["components"]["schemas"]["FindingDetail"]

    # Shape-tolerant on purpose: it reconstructs the defect from whichever shape the
    # document currently holds, so this fixture is usable to show the suite red
    # against the unrepaired document as well as green against the repaired one.
    declared: dict[str, Any] = dict(detail.get("properties", {}))
    for branch in detail.get("allOf", []):
        declared.update(branch.get("properties", {}))
    missing = DETAIL_ONLY_PROPERTIES - declared.keys()
    assert not missing, f"FindingDetail declares no {sorted(missing)}"
    added = {name: declared[name] for name in sorted(DETAIL_ONLY_PROPERTIES)}

    document["components"]["schemas"]["FindingDetail"] = {
        "allOf": [
            {"$ref": "#/components/schemas/Finding"},
            {"type": "object", "properties": added},
        ]
    }
    return document
