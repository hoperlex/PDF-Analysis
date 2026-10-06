"""The identifier catalog and its schema agree on the identifier names.

``contracts/domain/v1/identifiers.json`` declares the identifier names in ``identifiers``.
``contracts/domain/v1/identifiers.schema.json`` restricts two other places to those names with a
string ``enum``: the value of every ``entities`` entry, and every member of a
``distinct_identities`` entry's ``identifiers``. When the catalog gains a name and the enums do
not, the catalog no longer validates against its own schema -- which is how candidate
revision 9 reached a merged candidate (``W49-JUDGE-Y`` F-1): the only validation of the pair is
``tests/contract/test_cp00_candidate.py``, which the gate does not run, and it needs
``jsonschema``, which the gate's environment does not install.

So this test runs inside ``make gate`` and imports nothing but the standard library. It walks
the schema the way the finding was measured (``W49-FIX`` P-01) and asserts the totality both
ways: every catalog name is admitted by each identifier-name enum, and each such enum admits
nothing the catalog does not declare. An identifier-name enum is found by content, not by
path -- any string ``enum`` that shares a member with the catalog's names -- so a third such
enum added later is held to the same rule, and the expected two locations are asserted so an
enum that silently stops being found is a failure too.

It also asserts that the schema pins the catalog's ``candidate_revision``: the pin is what keeps
the candidate from changing meaning without a deliberate edit of both files.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DOMAIN = REPOSITORY_ROOT / "contracts" / "domain" / "v1"
CATALOG_PATH = DOMAIN / "identifiers.json"
SCHEMA_PATH = DOMAIN / "identifiers.schema.json"

#: Where the identifier-name enums sit at candidate revision 9, as JSON pointers. Found by
#: walking the schema (P-01) and named here so that the walk losing one is a failure.
EXPECTED_IDENTIFIER_NAME_ENUMS = frozenset(
    {
        "/properties/entities/additionalProperties",
        "/properties/distinct_identities/items/properties/identifiers/items",
    }
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _string_enums(node: object, pointer: str = "") -> Iterator[tuple[str, list[str]]]:
    """Yield ``(json_pointer, enum)`` for every ``enum`` whose members are all strings."""
    if isinstance(node, dict):
        enum = node.get("enum")
        if isinstance(enum, list) and enum and all(isinstance(v, str) for v in enum):
            yield pointer, enum
        for key, child in node.items():
            escaped = str(key).replace("~", "~0").replace("/", "~1")
            yield from _string_enums(child, f"{pointer}/{escaped}")
    elif isinstance(node, list):
        for index, child in enumerate(node):
            yield from _string_enums(child, f"{pointer}/{index}")


def _catalog_names() -> list[str]:
    identifiers = _load(CATALOG_PATH)["identifiers"]
    assert isinstance(identifiers, dict) and identifiers, (
        "identifiers.json `identifiers` must be a non-empty map of name to prefix"
    )
    return list(identifiers)


def _identifier_name_enums() -> dict[str, list[str]]:
    names = set(_catalog_names())
    return {
        pointer: enum
        for pointer, enum in _string_enums(_load(SCHEMA_PATH))
        if names.intersection(enum)
    }


def test_the_walk_finds_exactly_the_identifier_name_enums() -> None:
    found = set(_identifier_name_enums())
    assert found == EXPECTED_IDENTIFIER_NAME_ENUMS, (
        f"identifier-name enums found by the walk: {sorted(found)}; "
        f"expected: {sorted(EXPECTED_IDENTIFIER_NAME_ENUMS)}"
    )


def test_each_identifier_name_enum_admits_every_catalog_name() -> None:
    names = _catalog_names()
    missing = {
        pointer: [name for name in names if name not in enum]
        for pointer, enum in _identifier_name_enums().items()
    }
    missing = {pointer: lacked for pointer, lacked in missing.items() if lacked}
    assert not missing, (
        f"identifiers.schema.json enums lack names identifiers.json declares: {missing}"
    )


def test_each_identifier_name_enum_admits_nothing_the_catalog_does_not_declare() -> None:
    names = set(_catalog_names())
    extra = {
        pointer: [value for value in enum if value not in names]
        for pointer, enum in _identifier_name_enums().items()
    }
    extra = {pointer: values for pointer, values in extra.items() if values}
    assert not extra, (
        f"identifiers.schema.json enums admit names identifiers.json does not declare: {extra}"
    )


def test_each_identifier_name_enum_lists_each_name_once() -> None:
    repeated = {
        pointer: sorted({value for value in enum if enum.count(value) > 1})
        for pointer, enum in _identifier_name_enums().items()
    }
    repeated = {pointer: values for pointer, values in repeated.items() if values}
    assert not repeated, f"identifier-name enums repeat a name: {repeated}"


def test_the_schema_pins_the_catalogs_candidate_revision() -> None:
    catalog_revision = _load(CATALOG_PATH)["candidate_revision"]
    pin = _load(SCHEMA_PATH)["properties"]["candidate_revision"]
    assert "const" in pin, f"identifiers.schema.json does not pin candidate_revision: {pin}"
    assert pin["const"] == catalog_revision, (
        f"identifiers.schema.json pins candidate_revision {pin['const']!r}; "
        f"identifiers.json declares {catalog_revision!r}"
    )
