"""Validate stage-result payloads against the frozen schema, under Draft 2020-12.

Not named ``test_*`` on purpose, and it takes its whole job on stdin. ``jsonschema``
lives only in the **governance** environment (``requirements/validation.lock``); the
runtime lock does not carry it, and adding a root dependency is a single-owner task
rather than a lane decision. So the pytest suite beside this file runs under the
runtime interpreter and drives this script through the governance one::

    .venv/bootstrap/bin/python tests/contract/analysis_packages/stage_result_schema_check.py

Why a real validator and not a hand-rolled check: the rules this suite exists to pin
are JSON Schema ``if``/``then`` conditionals - ``succeeded`` forbids ``error`` via
``not: {required: [...]}``, and the three other statuses require it. Re-implementing
that evaluation in the test would be asserting the belief under test.

Protocol. stdin is one JSON object::

    {"schema": <the stage-result schema>,
     "cases": [{"name": str, "payload": <any>}, ...]}

stdout is one JSON object::

    {"results": [{"name": str, "valid": bool, "messages": [str, ...]}, ...]}

Exit 0 means every case was evaluated, whatever each verdict was. A non-zero exit
means the evaluation itself could not be performed, which is never a passing
condition.
"""

from __future__ import annotations

import json
import sys


def main() -> int:
    try:
        from jsonschema import Draft202012Validator
    except ModuleNotFoundError:
        print(
            "jsonschema is not importable. Run this with the governance interpreter:\n"
            "    .venv/bootstrap/bin/python "
            "tests/contract/analysis_packages/stage_result_schema_check.py",
            file=sys.stderr,
        )
        return 2

    try:
        job = json.load(sys.stdin)
        schema = job["schema"]
        cases = job["cases"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"malformed job on stdin: {exc}", file=sys.stderr)
        return 2

    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:  # noqa: BLE001 - the schema itself is the subject here
        print(f"the stage-result schema is not a valid Draft 2020-12 schema: {exc}",
              file=sys.stderr)
        return 2

    validator = Draft202012Validator(schema)
    results = []
    for case in cases:
        errors = sorted(validator.iter_errors(case["payload"]), key=lambda e: e.path)
        results.append(
            {
                "name": case["name"],
                "valid": not errors,
                "messages": [
                    f"{'/'.join(str(part) for part in error.path) or '<root>'}: "
                    f"{error.message}"
                    for error in errors
                ],
            }
        )

    json.dump({"results": results}, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
