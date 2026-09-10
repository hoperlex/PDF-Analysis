"""Validate every schema object in the OpenAPI document against JSON Schema 2020-12.

Not named ``test_*`` on purpose: it runs in the **governance** environment, which is
the only one carrying ``jsonschema``. The runtime lock does not, and adding a
dependency to the root lock is a single-owner task, not a lane decision. So::

    .venv/bootstrap/bin/python tests/contract/domain_p02/openapi_metaschema_check.py

Why this is worth a separate command: OpenAPI 3.1 aligned its Schema Object with
JSON Schema 2020-12, so every entry under ``components.schemas`` is a real JSON
Schema and a metaschema validator is a real check of it - it catches a mistyped
keyword, a malformed ``pattern`` and a non-schema where a schema belongs.

The structural rules of the OpenAPI document *itself* - operations, parameters,
responses, reference resolution - are checked by ``test_openapi_document.py``,
which runs in the runtime environment with the standard library alone and never
skips.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DOCUMENT = REPOSITORY_ROOT / "contracts" / "api" / "v1" / "openapi.json"


def main() -> int:
    try:
        from jsonschema import Draft202012Validator
    except ModuleNotFoundError:
        print(
            "jsonschema is not importable. Run this with the governance interpreter:\n"
            "    .venv/bootstrap/bin/python "
            "tests/contract/domain_p02/openapi_metaschema_check.py",
            file=sys.stderr,
        )
        return 2

    document = json.loads(DOCUMENT.read_text(encoding="utf-8"))
    schemas = document["components"]["schemas"]

    failures: list[str] = []
    for name, schema in sorted(schemas.items()):
        try:
            Draft202012Validator.check_schema(schema)
        except Exception as exc:  # noqa: BLE001 - reported, not raised
            failures.append(f"components.schemas.{name}: {exc}")

    # Every `pattern` must compile, in Python and as a plain ECMA-ish regex. A
    # generator that cannot compile it produces a client that rejects valid input.
    for name, schema in sorted(schemas.items()):
        for path, pattern in _walk_patterns(schema, f"components.schemas.{name}"):
            try:
                re.compile(pattern)
            except re.error as exc:
                failures.append(f"{path}: pattern does not compile: {exc}")

    if failures:
        print(f"OPENAPI-METASCHEMA FAIL: {len(failures)} problem(s)", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1

    print(f"checked {len(schemas)} schema objects in {DOCUMENT.relative_to(REPOSITORY_ROOT)}")
    print("OPENAPI-METASCHEMA OK")
    return 0


def _walk_patterns(node: object, path: str):
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "pattern" and isinstance(value, str):
                yield f"{path}.pattern", value
            else:
                yield from _walk_patterns(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _walk_patterns(value, f"{path}[{index}]")


if __name__ == "__main__":
    raise SystemExit(main())
