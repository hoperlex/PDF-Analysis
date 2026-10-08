"""Independent, hand-maintained expectations for the frozen contract test suites.

This module parses only the JSON beside it. It never derives an expectation from an
OpenAPI document, error catalog, migration graph or generated frontend artifact.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

FACTS_PATH = Path(__file__).with_suffix(".json")
METHODS = frozenset({"GET", "POST", "PATCH", "PUT", "DELETE", "HEAD", "OPTIONS"})


@dataclass(frozen=True)
class ExpectedFacts:
    path_count: int
    operations: tuple[tuple[str, str, str], ...]
    schema_names: frozenset[str]
    api_error_codes: int
    stored_error_codes: int
    migration_head: str
    contract_version: str

    @property
    def operation_count(self) -> int:
        return len(self.operations)

    @property
    def schema_count(self) -> int:
        return len(self.schema_names)


def load_expected_facts(path: Path = FACTS_PATH) -> ExpectedFacts:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("facts_version") != 1:
        raise ValueError("expected facts schema version must be 1")
    surface = raw["surface"]
    errors = raw["error_catalog"]
    if not isinstance(surface, dict) or not isinstance(errors, dict):
        raise ValueError("expected surface and error catalog objects")
    path_count = surface["path_count"]
    operations = surface["operations"]
    schema_names = surface["schema_names"]
    api_codes = errors["api_codes"]
    stored_codes = errors["stored_vocabulary"]
    if any(type(count) is not int or count < 0 for count in (path_count, api_codes, stored_codes)):
        raise ValueError("expected counts must be nonnegative integers")
    if not isinstance(operations, list) or not operations or any(
        not isinstance(item, list)
        or len(item) != 3
        or not all(isinstance(part, str) and part for part in item)
        or item[0] not in METHODS
        or not item[1].startswith("/")
        for item in operations
    ):
        raise ValueError("expected operations must be explicit method/path/id triples")
    triples = tuple(tuple(item) for item in operations)
    if (
        len(triples) != len(set(triples))
        or len({(method, path) for method, path, _ in triples}) != len(triples)
        or len({operation_id for _, _, operation_id in triples}) != len(triples)
    ):
        raise ValueError("duplicate expected operation")
    if not isinstance(schema_names, list) or not schema_names or any(
        not isinstance(name, str) or not name for name in schema_names
    ) or len(schema_names) != len(set(schema_names)):
        raise ValueError("expected schema names must be a unique explicit list")
    head = raw["migration_head"]
    version = raw["contract_version"]
    if not isinstance(head, str) or not re.fullmatch(r"\d{4}_[a-z0-9_]+", head):
        raise ValueError("invalid expected migration head")
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", version):
        raise ValueError("invalid expected contract version")
    return ExpectedFacts(
        path_count=path_count,
        operations=triples,
        schema_names=frozenset(schema_names),
        api_error_codes=api_codes,
        stored_error_codes=stored_codes,
        migration_head=head,
        contract_version=version,
    )


FACTS = load_expected_facts()
