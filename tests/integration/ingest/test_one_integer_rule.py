"""One integer rule for the block list, at ingest and in both run stages (`W55B-FIX`, X-7).

`W55B-JUDGE-X` X-7 and `W55B-JUDGE-Y` Y-1(a): ingest admitted an integer-valued float --
``"page_index": 0.0``, ``"rotation": 0.0``, ``"width_px": 1000.0``, ``"page_label": 1.0``,
``"ordinal": 0.0`` -- because JSON Schema's ``integer`` admits one, while
``source_preparation`` and ``page_geometry_extraction`` read each of them as a Python ``int``
and refused the float as ``portal_blocks_invalid``. A version is immutable, so it failed
every run. Now every integer field is a JSON integer as written, on every side:

* ingest refuses the float with ``blocks_json_invalid`` (the bundle's own constraint);
* the fixtures' reference checker refuses it too, so the generator cannot write one;
* each stage that reads the field refuses it, which is what it always did.

And the integer itself -- the committed baseline, unchanged -- is accepted by all of them.
The module needs no database.
"""

from __future__ import annotations

import io
import json
import zipfile
from typing import Any

import pytest

from auditmanager.analysis.geometry.portal import read_layout
from auditmanager.analysis.recognised.portal import read_block_list
from auditmanager.shared.errors import DomainError
from portal_bundle import validate  # tools/fixtures, on the path via conftest
from tests.integration.ingest.bundle_support import committed, judge

BASELINE = "ar_baseline.zip"


@pytest.fixture(autouse=True)
def clean_tables() -> None:  # type: ignore[override]
    """Overrides ``conftest.clean_tables``: there is no database to empty."""


def _members() -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(committed(BASELINE))) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def _blocks_name(members: dict[str, bytes]) -> str:
    return next(name for name in members if name.endswith("_blocks.json"))


def _rezip(members: dict[str, bytes], blocks: bytes) -> bytes:
    name = _blocks_name(members)
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for member, data in members.items():
            archive.writestr(member, blocks if member == name else data)
    return out.getvalue()


def _edited(where: str, field: str) -> tuple[bytes, int]:
    """The baseline's block list with one integer written as a float, and its page count."""
    members = _members()
    document = json.loads(members[_blocks_name(members)])
    if where == "document":
        document[field] = float(document[field])
    elif where == "page":
        document["pages"][0][field] = float(document["pages"][0][field])
    else:
        block = next(b for b in document["blocks"] if b.get(field) is not None)
        block[field] = float(block[field])
    raw = json.dumps(document).encode("utf-8")
    return raw, len(document["pages"])


#: (where, field, the stages that read it as an integer).
CASES: list[tuple[str, str, tuple[str, ...]]] = [
    ("page", "page_index", ("geometry",)),
    ("page", "width_px", ("geometry",)),
    ("page", "height_px", ("geometry",)),
    ("page", "rotation", ("geometry",)),
    ("block", "page_index", ("geometry", "recognised")),
    ("block", "page_label", ("geometry",)),
    ("block", "ordinal", ("geometry",)),
    ("document", "schema_version", ()),
]


def _stage_refuses(stage: str, raw: bytes, page_count: int) -> str | None:
    reader: Any = read_layout if stage == "geometry" else read_block_list
    try:
        reader(raw, page_count=page_count, stage_id="probe")
    except DomainError as refused:
        return str(dict(refused.detail_fields).get("reason"))
    return None


@pytest.mark.parametrize(("where", "field", "stages"), CASES, ids=[f"{w}.{f}" for w, f, _ in CASES])
def test_an_integer_written_as_a_float_is_refused_by_ingest_by_the_reference_and_by_every_stage(
    where: str, field: str, stages: tuple[str, ...]
) -> None:
    raw, page_count = _edited(where, field)
    assert b".0" in raw

    assert judge(_rezip(_members(), raw))[:2] == ("file", "blocks_json_invalid")
    violations, _document = validate._check_blocks(raw)
    assert [v.constraint for v in violations] == ["blocks_json_invalid"], violations
    for stage in stages:
        assert _stage_refuses(stage, raw, page_count) == "portal_blocks_invalid", stage


def test_the_integers_as_the_portal_writes_them_are_accepted_by_all_of_them() -> None:
    members = _members()
    raw = members[_blocks_name(members)]
    field, constraint, admission = judge(committed(BASELINE))
    assert (field, constraint) == (None, None) and admission is not None
    assert validate._check_blocks(raw)[0] == []
    for stage in ("geometry", "recognised"):
        assert _stage_refuses(stage, raw, admission.page_count) is None, stage
