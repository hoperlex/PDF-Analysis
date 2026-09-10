"""Validate payloads against schemas of the OpenAPI document, under Draft 2020-12.

Not named ``test_*`` on purpose, and it takes its whole job on stdin. ``jsonschema``
lives only in the **governance** environment (``requirements/validation.lock``); the
runtime lock does not carry it, and adding a root dependency is a single-owner task
rather than a lane decision. So the pytest suite beside this file runs under the
runtime interpreter and drives this script through the governance one::

    .venv/bootstrap/bin/python tests/contract/api_v1/schema_validation_check.py

Why a real validator and not a hand-rolled check: the defect this suite exists to pin
is a *JSON Schema 2020-12 evaluation-scope* rule - ``additionalProperties`` sees only
its own schema object's property annotations, and sibling ``allOf`` branches
contribute nothing to it. Re-implementing that rule in the test would be asserting the
belief under test. The pinned ``jsonschema`` implements the specification instead.

Protocol. stdin is one JSON object::

    {"document": <the OpenAPI document>,
     "cases": [{"name": str, "schema": str, "payload": <any>}, ...]}

stdout is one JSON object::

    {"results": [{"name": str, "valid": bool, "messages": [str, ...]}, ...]}

The caller supplies the document, so a case may be run against a deliberately mutated
copy - which is how the pre-fix shape is kept under test rather than described in prose.
Exit 0 means every case was evaluated, whatever each verdict was; a non-zero exit means
the evaluation itself could not be performed, which is never a passing condition.
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
            "tests/contract/api_v1/schema_validation_check.py",
            file=sys.stderr,
        )
        return 2

    try:
        job = json.load(sys.stdin)
        document = job["document"]
        cases = job["cases"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"malformed job on stdin: {exc}", file=sys.stderr)
        return 2

    components = document["components"]

    results = []
    for case in cases:
        name = case["name"]
        schema_name = case["schema"]
        if schema_name not in components["schemas"]:
            print(f"{name}: no schema named {schema_name!r}", file=sys.stderr)
            return 2

        # The root schema resource carries `components`, so `#/components/schemas/X`
        # resolves inside it without a registry and without rewriting any `$ref`.
        schema = {
            "$ref": f"#/components/schemas/{schema_name}",
            "components": components,
        }
        try:
            Draft202012Validator.check_schema(schema)
            validator = Draft202012Validator(schema)
            errors = sorted(
                validator.iter_errors(case["payload"]),
                key=lambda error: (list(error.absolute_path), error.message),
            )
        except Exception as exc:  # noqa: BLE001 - an unevaluable case is a hard failure
            print(f"{name}: could not evaluate: {exc!r}", file=sys.stderr)
            return 2

        results.append(
            {
                "name": name,
                "valid": not errors,
                "messages": [error.message for error in errors],
            }
        )

    json.dump({"results": results}, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
