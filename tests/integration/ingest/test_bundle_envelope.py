"""What the members of a portal bundle say: the PDF, the block list, the markdown, the counts.

`W55B-INGEST-01` (plan sections B3.2 and B3.5). The archive rules are in ``test_bundle_archive.py``;
this file judges the content half of the envelope
(:mod:`auditmanager.ingest.bundle_envelope`):

* the **PDF member keeps every refusal of a bare PDF, byte for byte**: the same field,
  constraint and message, because the same function judges both;
* ``_blocks.json`` against the **pinned schema** -- read from ``contracts/analysis/v1`` and
  compared with the constants in code, so a keyword the contract gains cannot be missed -- and
  against a generic checker over a seeded fuzz of the real block list (``jsonschema`` is not in
  the lock, so the schema is implemented by hand, and a hand-written copy is only as good as the
  comparison that backs it);
* ``_results.md`` and the block list agree **both ways**, for TEXT and IMAGE blocks of equal
  type, and a STAMP block has no header;
* every page has an embedded text layer **or** at least one portal block -- a block of any type;
* the **three counts** a version records, each compared with an independent reading.

The module needs no database, no object store and no container.
"""

from __future__ import annotations

import copy
import io
import json
import random
import re
from pathlib import Path
from typing import Any

import pytest

from auditmanager.ingest import bundle_envelope as be
from auditmanager.ingest.bundle_archive import extract_bundle
from auditmanager.ingest.envelope import (
    MAX_PAGES,
    PDFIUM_LOCK,
    TEXTLESS_PAGE_CHARACTERS,
    page_text_refusal,
    probe,
)
from auditmanager.shared.errors import DomainError
from portal_bundle import archive_negatives as an  # tools/fixtures, on the path via conftest
from portal_bundle import blocklist, generated, positives, schemacheck, validate, zipwrite
from portal_bundle import portal_format as fmt
from portal_bundle.blocklist import Block
from portal_bundle.bundle import build_bundle, make_files, pack, text_blocks
from portal_bundle.committed import PLAN_IMAGE
from portal_bundle.pdffacts import read_pages
from tests.integration.ingest.bundle_support import (
    bundle_around,
    committed,
    judge,
    refusal_of,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CORPUS = REPOSITORY_ROOT / "fixtures" / "synthetic" / "ar"
SCHEMA = REPOSITORY_ROOT / "contracts" / "analysis" / "v1" / "portal-blocks.schema.json"


@pytest.fixture(scope="session", autouse=True)
def lane_environment() -> None:  # type: ignore[override]
    """Overrides ``conftest.lane_environment``: this module reaches no service."""


@pytest.fixture(autouse=True)
def clean_tables() -> None:  # type: ignore[override]
    """Overrides ``conftest.clean_tables``: there is no database to empty."""


def admit(data: bytes) -> be.BundleAdmission:
    with extract_bundle(io.BytesIO(data)) as bundle:
        return be.admit_bundle(bundle)


def pdfium_characters(pdf: bytes) -> list[int]:
    """The characters pypdfium2 reads on each page, read here and not by the product."""
    import pypdfium2 as pdfium

    with PDFIUM_LOCK:
        document = pdfium.PdfDocument(pdf)
        try:
            counts = []
            for index in range(len(document)):
                page = document[index]
                text_page = page.get_textpage()
                try:
                    counts.append(len(text_page.get_text_range()))
                finally:
                    text_page.close()
                    page.close()
            return counts
        finally:
            document.close()


# ---------------------------------------------------------------------------------------
# The PDF member
# ---------------------------------------------------------------------------------------


def _bare_refusal(pdf: bytes) -> tuple[str, str, str]:
    with pytest.raises(DomainError) as raised:
        probe(pdf, source_filename="member.pdf")
    fields = dict(raised.value.detail_fields)
    return fields["field"], fields["constraint"], str(raised.value)


PDF_CASES = {
    "not a PDF": lambda: (CORPUS / "negative" / "not_a_pdf.txt").read_bytes(),
    "encrypted": lambda: (CORPUS / "negative" / "encrypted.pdf").read_bytes(),
    "501 pages": lambda: generated.pdf_with_n_pages(MAX_PAGES + 1),
    "truncated": lambda: (CORPUS / "ar_baseline.pdf").read_bytes()[:3000],
}


@pytest.mark.parametrize("case", sorted(PDF_CASES))
def test_a_pdf_member_is_refused_exactly_as_the_same_bytes_are_as_a_bare_pdf(case: str) -> None:
    """Same field, same constraint, same sentence: one function judges both."""
    pdf = PDF_CASES[case]()
    bare = _bare_refusal(pdf)
    with pytest.raises(DomainError) as raised:
        admit(bundle_around(pdf))
    fields = dict(raised.value.detail_fields)
    assert (fields["field"], fields["constraint"], str(raised.value)) == bare, case
    assert bare[0] in {"content", "page_count"}, "a PDF rule is not answered under field `file`"


def test_the_page_ceiling_is_five_hundred_pages_inclusive() -> None:
    """500 pages are accepted and 501 are not (both through the bundle, 500 in a second)."""
    five_hundred = generated.bundle_with_pages(500)
    admission = admit(five_hundred)
    assert admission.page_count == 500
    assert admission.text_character_count > 0 and admission.textless_pages == ()
    assert judge(generated.bundle_with_pages(501))[:2] == ("page_count", "1 <= page_count <= 500")


def test_a_pdf_defect_is_judged_before_the_block_list_is_read() -> None:
    """Cheapest and most attributable first: an encrypted PDF with a block list that is not
    JSON is refused as encrypted, never as a bad block list."""
    items = an.members()
    items[0] = zipwrite.Member(b"bundle.pdf", (CORPUS / "negative" / "encrypted.pdf").read_bytes(), method=0)
    items[1].payload = b"{ not json"
    assert judge(zipwrite.build_zip(items))[:2] == ("content", "not_encrypted")


def test_the_block_list_is_judged_before_the_markdown_and_the_markdown_before_the_pages() -> None:
    items = an.members()
    items[1].payload = b"{ not json"
    items[2].payload = b"# no headers at all\n"
    assert judge(zipwrite.build_zip(items))[:2] == ("file", "blocks_json_invalid")

    # A block list of the wrong page count AND a markdown that disagrees with it: the
    # markdown is judged first.
    files = an.base_files()
    document = json.loads(files.blocks_json)
    document["pages"].append(dict(document["pages"][0], page_index=2))
    items = an.members()
    items[1].payload = blocklist.dump(document)
    items[2].payload = b"# no headers at all\n"
    assert judge(zipwrite.build_zip(items))[:2] == ("file", "results_blocks_mismatch")


# ---------------------------------------------------------------------------------------
# The pinned schema, in code
# ---------------------------------------------------------------------------------------


def _schema() -> dict[str, Any]:
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


def test_the_constants_in_code_are_the_pinned_schemas() -> None:
    """Every fact of ``portal-blocks.schema.json`` that ``bundle_envelope`` implements, compared
    with the file. A keyword, a bound, a pattern or a rule the contract gains stops here."""
    schema = _schema()
    props = schema["properties"]
    page = props["pages"]["items"]
    block = props["blocks"]["items"]

    schemacheck.assert_supported(schema)          # nothing the hand-written check ignores
    assert tuple(schema["required"]) == be.SCHEMA_REQUIRED_TOP
    assert props["schema_version"] == {"const": be.SCHEMA_VERSION}
    assert props["coordinate_space"] == {"const": be.COORDINATE_SPACE}
    assert (props["pages"]["minItems"], props["pages"]["maxItems"]) == (be.PAGES_MIN, be.PAGES_MAX)
    assert tuple(page["required"]) == be.PAGE_REQUIRED
    assert tuple(page["properties"]["rotation"]["enum"]) == be.ROTATIONS
    assert page["properties"]["page_index"] == {"type": "integer", "minimum": 0}
    assert page["properties"]["width_px"] == {"type": "integer", "minimum": 1}
    assert page["properties"]["height_px"] == {"type": "integer", "minimum": 1}
    assert tuple(block["required"]) == be.BLOCK_REQUIRED
    assert tuple(block["properties"]["block_type"]["enum"]) == be.BLOCK_TYPES
    assert block["properties"]["block_id"]["pattern"] == be.BLOCK_ID_PATTERN.pattern
    assert block["properties"]["status"]["pattern"] == be.STATUS_PATTERN.pattern
    # Amendment 1 of the freeze: `shape_type` is optional and one of two words, `polygon_points`
    # is null or empty on a rectangle and 3..64 points otherwise, and a polygon must carry them.
    assert tuple(block["properties"]["shape_type"]["enum"]) == be.SHAPE_TYPES == ("rectangle", "polygon")
    assert "shape_type" not in block["required"]
    polygon = block["properties"]["polygon_points"]
    assert polygon["type"] == ["array", "null"]
    assert polygon["maxItems"] == be.POLYGON_MAX and "minItems" not in polygon
    assert polygon["if"] == {"type": "array", "minItems": 1}
    assert polygon["then"] == {"minItems": be.POLYGON_MIN}
    assert polygon["items"]["minItems"] == polygon["items"]["maxItems"] == 2
    assert block["if"] == {
        "required": ["shape_type"], "properties": {"shape_type": {"const": be.POLYGON_SHAPE}},
    }
    assert block["then"] == {
        "required": ["polygon_points"],
        "properties": {"polygon_points": {"type": "array", "minItems": 1}},
    }
    assert {"if", "then"} <= set(block) and not {"else", "oneOf", "anyOf", "allOf", "not"} & set(block)
    # `status` and `export_status` are the portal's tokens: a pattern, never a list of words.
    assert "enum" not in block["properties"]["status"]
    assert block["properties"]["export_status"] == {"type": "string"}
    coords = block["properties"]["coords_norm"]
    assert (coords["minItems"], coords["maxItems"]) == (4, 4)
    assert coords["items"] == {"type": "number", "minimum": 0, "maximum": 1}
    assert block["properties"]["ordinal"] == {"type": ["integer", "null"], "minimum": 0}
    assert block["properties"]["page_index"] == {"type": "integer", "minimum": 0}
    assert block["properties"]["page_label"] == {"type": "integer", "minimum": 1}
    assert len(schema["x-envelope-rules"]) == be.IMPLEMENTED_ENVELOPE_RULES
    # The portal's file: unknown properties are tolerated at every level.
    for node in (schema, page, block):
        assert "additionalProperties" not in node


def _reference_valid(document: Any) -> bool:
    """The reference: the fixtures' generic subset checker plus its envelope rules."""
    return not validate._check_blocks(json.dumps(document).encode("utf-8"))[0]


def _mutations(seed: int, count: int) -> list[tuple[str, Any]]:
    base = json.loads(committed_blocks_json())
    paths: list[tuple[Any, ...]] = []

    def walk(node: Any, path: tuple[Any, ...]) -> None:
        paths.append(path)
        if isinstance(node, dict):
            for key, value in node.items():
                walk(value, path + (key,))
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, path + (index,))

    walk(base, ())
    junk: list[Any] = [
        None, "", "x", "recognized", "blk_" + "0" * 32, "blk_" + "g" * 32, -1, 0, 1, 2, 90,
        45, 1.5, 1.0, 0.5, 1e9, True, False, [], {}, [0.1, 0.2, 0.3, 0.4], [0.5, 0.1, 0.4, 0.9],
        [0.1, 0.1], [[0.1, 0.1], [0.2, 0.2], [0.3, 0.1]], "text", "table", 501,
        "rectangle", "polygon", "Polygon", "circle", [[0.1, 0.1], [0.2, 0.2]],
    ]
    generator = random.Random(seed)
    found: list[tuple[str, Any]] = []
    for number in range(count):
        document = copy.deepcopy(base)
        path = generator.choice(paths[1:])
        parent: Any = document
        for step in path[:-1]:
            parent = parent[step]
        if generator.random() < 0.3 and isinstance(parent, dict):
            del parent[path[-1]]
            label = f"delete {path}"
        else:
            parent[path[-1]] = copy.deepcopy(generator.choice(junk))
            label = f"set {path}"
        found.append((f"{number}: {label}", document))
    return found


def committed_blocks_json() -> bytes:
    with extract_bundle(io.BytesIO(committed("ar_baseline.zip"))) as bundle:
        return bundle.read_bytes("blocks")


def test_the_hand_written_check_agrees_with_the_generic_one_over_a_seeded_fuzz() -> None:
    mutations = _mutations(seed=20261013, count=600)
    verdicts = {be._blocks_problem(document) is None for _label, document in mutations}
    assert verdicts == {True, False}, "the fuzz must contain both accepted and refused documents"
    for label, document in mutations:
        assert (be._blocks_problem(document) is None) == _reference_valid(document), label


_ABSENT = object()


def _ring(count: int) -> list[list[float]]:
    """``count`` vertices, every coordinate inside [0, 1]."""
    step = max(count - 1, 1)
    return [[round(0.1 + 0.8 * i / step, 3), round(0.9 - 0.8 * i / step, 3)] for i in range(count)]


SHAPE_CASES: dict[str, Any] = {
    "absent": _ABSENT, "rectangle": "rectangle", "polygon": "polygon",
    "Polygon": "Polygon", "RECTANGLE": "RECTANGLE", "circle": "circle", "empty string": "",
    "null": None, "number": 1, "true": True, "list": ["polygon"],
}
POINTS_CASES: dict[str, Any] = {
    "absent": _ABSENT, "null": None, "empty list": [], "one point": _ring(1), "two points": _ring(2),
    "three points": _ring(3), "eleven points": _ring(11), "sixty-four points": _ring(64),
    "sixty-five points": _ring(65), "x above one": [[1.2, 0.1], [0.2, 0.2], [0.3, 0.1]],
    "y below zero": [[0.1, -0.1], [0.2, 0.2], [0.3, 0.1]],
    "a point of three": [[0.1, 0.1, 0.1], [0.2, 0.2, 0.2], [0.3, 0.1, 0.1]],
    "a point of one": [[0.1], [0.2], [0.3]], "a point that is a string": [[0.1, 0.1], [0.2, 0.2], "x"],
    "a boolean coordinate": [[True, 0.1], [0.2, 0.2], [0.3, 0.1]],
    "a string": "x", "an object": {}, "zero": 0, "false": False,
}


def _amendment_accepts(shape: Any, points: Any) -> bool:
    """Amendment 1 of the freeze, read on its own (not from the schema or from the product).

    ``shape_type``: absent, or exactly ``rectangle`` or ``polygon``. ``polygon_points``: absent,
    ``null`` or empty, or 3..64 ``[x, y]`` pairs inside [0, 1]. A ``polygon`` block carries a
    non-empty list.
    """
    shape_ok = shape is _ABSENT or (isinstance(shape, str) and shape in ("rectangle", "polygon"))
    if points is _ABSENT or points is None:
        return shape_ok and shape != "polygon"
    if not isinstance(points, list):
        return False
    if points and not 3 <= len(points) <= 64:
        return False
    for point in points:
        if not (isinstance(point, list) and len(point) == 2):
            return False
        if not all(type(c) in (int, float) and 0 <= c <= 1 for c in point):
            return False
    return shape_ok and not (shape == "polygon" and not points)


def test_shape_type_and_polygon_points_are_judged_alike_by_the_product_the_reference_and_the_amendment(
) -> None:
    """Every ``shape_type`` against every ``polygon_points`` on a block of the real block list:
    the hand-written check, the generic one reading the contract file, and a third reading of
    the amendment that shares code with neither. A drift in any of the three, in either
    direction, is a disagreement here."""
    base = json.loads(committed_blocks_json())
    verdicts: set[bool] = set()
    for shape_label, shape in SHAPE_CASES.items():
        for points_label, points in POINTS_CASES.items():
            document = copy.deepcopy(base)
            block = document["blocks"][0]
            for key, value in (("shape_type", shape), ("polygon_points", points)):
                if value is _ABSENT:
                    block.pop(key, None)
                else:
                    block[key] = value
            label = f"shape_type {shape_label} / polygon_points {points_label}"
            wanted = _amendment_accepts(shape, points)
            verdicts.add(wanted)
            assert (be._blocks_problem(document) is None) == wanted, f"product: {label}"
            assert _reference_valid(document) == wanted, f"reference: {label}"
    assert verdicts == {True, False}


@pytest.mark.parametrize("kind", sorted(an.BLOCKS_INVALID))
def test_each_block_list_defect_is_refused_as_an_invalid_block_list(kind: str) -> None:
    """Every way the fixtures break a block list, each refused for that and for nothing the
    markdown or the page count could be blamed for."""
    assert judge(an.blocks_json_invalid(kind))[:2] == ("file", "blocks_json_invalid"), kind


@pytest.mark.parametrize(
    "edit",
    [
        pytest.param(lambda d: d.update(document_id="doc_whatever"), id="document_id is ignored"),
        pytest.param(lambda d: d.pop("document_id", None), id="document_id may be absent"),
        pytest.param(lambda d: d.update(invented="by the portal"), id="unknown top-level property"),
        pytest.param(lambda d: d["blocks"][0].update(invented=[1]), id="unknown block property"),
        pytest.param(lambda d: d["blocks"][0].update(status="failed"), id="a failed block is tolerated"),
        pytest.param(lambda d: d["pages"][0].update(rotation=90), id="rotation 90"),
        pytest.param(lambda d: d["pages"][1].update(rotation=180), id="rotation 180"),
        pytest.param(lambda d: d["pages"][2].update(rotation=270), id="rotation 270"),
        pytest.param(lambda d: d["blocks"][0].update(ordinal=None), id="a null ordinal"),
        pytest.param(lambda d: d["blocks"][1].update(ordinal=d["blocks"][0]["ordinal"]),
                     id="ordinals need not be unique"),
        pytest.param(lambda d: d["blocks"][0].update(crop_url=None), id="a null crop_url"),
        # Amendment 1, `shape_type` and `polygon_points`.
        pytest.param(lambda d: d["blocks"][0].update(polygon_points=None),
                     id="a rectangle with a null polygon_points"),
        pytest.param(lambda d: d["blocks"][0].update(polygon_points=[]),
                     id="a rectangle with an empty polygon_points"),
        pytest.param(lambda d: d["blocks"][0].pop("polygon_points"),
                     id="a rectangle without polygon_points"),
        pytest.param(lambda d: d["blocks"][0].pop("shape_type"), id="a block without shape_type"),
        pytest.param(lambda d: d["blocks"][0].update(shape_type="rectangle"),
                     id="shape_type rectangle"),
        pytest.param(lambda d: d["blocks"][0].update(shape_type="polygon", polygon_points=_ring(3)),
                     id="a polygon with three vertices"),
        pytest.param(lambda d: d["blocks"][0].update(shape_type="polygon", polygon_points=_ring(11)),
                     id="a polygon with eleven vertices"),
        pytest.param(lambda d: d["blocks"][0].update(shape_type="polygon", polygon_points=_ring(64)),
                     id="a polygon with sixty-four vertices"),
        pytest.param(lambda d: d["blocks"][0].update(polygon_points=_ring(6)),
                     id="vertices on a rectangle are not refused"),
        # `status` and `export_status`: the portal's tokens, a pattern and not a list of words.
        pytest.param(lambda d: d["blocks"][0].update(status="queued", export_status="queued"),
                     id="another lower-case status token"),
        pytest.param(lambda d: d["blocks"][0].update(status="a" * 40), id="a forty-character status"),
        pytest.param(lambda d: d["blocks"][0].update(export_status="Anything At All"),
                     id="export_status is any string"),
    ],
)
def test_what_the_portal_may_say_is_accepted(edit: Any) -> None:
    assert _judged_after(edit) == (None, None)


def _judged_after(edit: Any) -> tuple[str | None, str | None]:
    """(field, constraint) of a three-page bundle whose block list ``edit`` has changed."""
    pdf = generated.pdf_with_n_pages(3)           # three pages, a TEXT block on each
    files = make_files(pdf, an.STEM)
    document = json.loads(files.blocks_json)
    edit(document)
    items = pack(files)
    items[1].payload = blocklist.dump(document)
    return judge(zipwrite.build_zip(items))[:2]


@pytest.mark.parametrize(
    "edit",
    [
        # `shape_type` is one of two words, case-sensitive; null and the empty string are not words.
        pytest.param(lambda d: d["blocks"][0].update(shape_type="circle"), id="an unknown shape_type"),
        pytest.param(lambda d: d["blocks"][0].update(shape_type="Polygon", polygon_points=_ring(6)),
                     id="shape_type Polygon"),
        pytest.param(lambda d: d["blocks"][0].update(shape_type="RECTANGLE"), id="shape_type RECTANGLE"),
        pytest.param(lambda d: d["blocks"][0].update(shape_type=""), id="an empty shape_type"),
        pytest.param(lambda d: d["blocks"][0].update(shape_type=None), id="a null shape_type"),
        pytest.param(lambda d: d["blocks"][0].update(shape_type=["polygon"]), id="a list shape_type"),
        # A polygon carries its vertices: not null, not absent, not empty.
        pytest.param(lambda d: d["blocks"][0].update(shape_type="polygon", polygon_points=None),
                     id="a polygon with null polygon_points"),
        pytest.param(lambda d: d["blocks"][0].update(shape_type="polygon"),
                     id="a polygon without polygon_points"),
        pytest.param(lambda d: d["blocks"][0].update(shape_type="polygon", polygon_points=[]),
                     id="a polygon with an empty polygon_points"),
        # A non-empty list holds 3..64 pairs inside the unit square.
        pytest.param(lambda d: d["blocks"][0].update(shape_type="polygon", polygon_points=_ring(1)),
                     id="a polygon with one vertex"),
        pytest.param(lambda d: d["blocks"][0].update(shape_type="polygon", polygon_points=_ring(2)),
                     id="a polygon with two vertices"),
        pytest.param(lambda d: d["blocks"][0].update(polygon_points=_ring(2)),
                     id="two vertices on a rectangle"),
        pytest.param(lambda d: d["blocks"][0].update(polygon_points=_ring(1)),
                     id="one vertex on a rectangle"),
        pytest.param(lambda d: d["blocks"][0].update(shape_type="polygon", polygon_points=_ring(65)),
                     id="a polygon with sixty-five vertices"),
        pytest.param(lambda d: d["blocks"][0].update(shape_type="polygon",
                                                     polygon_points=[[1.2, 0.1], [0.2, 0.2], [0.3, 0.1]]),
                     id="a vertex outside the unit square"),
        pytest.param(lambda d: d["blocks"][0].update(polygon_points="x"), id="polygon_points a string"),
        # `status` stays a lower-case token.
        pytest.param(lambda d: d["blocks"][0].update(status="Recognized"), id="status in capitals"),
        pytest.param(lambda d: d["blocks"][0].update(status="a" * 41), id="a forty-one-character status"),
        pytest.param(lambda d: d["blocks"][0].update(status=""), id="an empty status"),
        pytest.param(lambda d: d["blocks"][0].update(export_status=None), id="a null export_status"),
        # The rest of Amendment 1 that already held.
        pytest.param(lambda d: d.update(schema_version=2), id="schema_version 2"),
        pytest.param(lambda d: d.update(coordinate_space="normalized_page_bottom_left"),
                     id="another coordinate space"),
        pytest.param(lambda d: d["blocks"][0].update(block_type="TEXT"), id="block_type in capitals"),
        pytest.param(lambda d: d["blocks"][0].update(block_type="table"), id="a fourth block_type"),
    ],
)
def test_what_the_amendment_does_not_allow_is_refused_as_an_invalid_block_list(edit: Any) -> None:
    assert _judged_after(edit) == ("file", "blocks_json_invalid")


def test_the_new_negatives_and_positives_are_in_the_fixture_registries() -> None:
    """The fixtures' own cases for the three rules, so `test_each_block_list_defect...` above and
    the ``every valid but unusual positive`` test of the fixtures run them."""
    assert {"polygon_with_two_points", "polygon_without_points", "unknown_shape_type"} <= set(
        an.BLOCKS_INVALID)
    for name in ("rectangle_with_empty_polygon_points", "rectangle_with_null_polygon_points",
                 "block_without_shape_type"):
        assert judge(positives.POSITIVES[name]())[:2] == (None, None), name


def test_every_block_type_and_a_stamp_without_an_ordinal_or_a_crop_are_accepted() -> None:
    """The real export's stamps have a null ordinal and a null crop_url; the committed
    baseline's two STAMP blocks have the same, and all three types are in it."""
    document = json.loads(committed_blocks_json())
    stamps = [b for b in document["blocks"] if b["block_type"] == "stamp"]
    assert stamps and all(b["ordinal"] is None and b["crop_url"] is None for b in stamps)
    assert {b["block_type"] for b in document["blocks"]} == set(be.BLOCK_TYPES)
    assert be._blocks_problem(document) is None


def test_a_block_id_with_a_trailing_newline_is_refused() -> None:
    """The one place the product is stricter than the reference on purpose: JSON Schema's
    ``$`` does not match before a final newline, Python's ``re.search`` does."""
    document = json.loads(an.base_files().blocks_json)
    document["blocks"][0]["block_id"] += "\n"
    assert be._blocks_problem(document) is not None
    assert _reference_valid(document), "the reference no longer accepts it: drop this test"


# ---------------------------------------------------------------------------------------
# The markdown, both ways
# ---------------------------------------------------------------------------------------


def test_the_markdown_may_use_windows_line_endings() -> None:
    items = an.members()
    items[2].payload = items[2].payload.replace(b"\n", b"\r\n")
    assert judge(zipwrite.build_zip(items))[:2] == (None, None)


@pytest.mark.parametrize("kind", sorted(an.MARKDOWN_MISMATCH))
def test_each_way_the_markdown_and_the_block_list_can_disagree_is_a_mismatch(kind: str) -> None:
    assert judge(an.MARKDOWN_MISMATCH[kind]())[:2] == ("file", "results_blocks_mismatch"), kind


def test_a_stamp_block_has_no_header_and_may_not_have_one() -> None:
    """Both halves of the rule: the complete bundle (two STAMP blocks, no headers) is
    accepted, and a header for a stamp is refused (``header_for_a_stamp`` above)."""
    assert judge(committed("ar_baseline.zip"))[:2] == (None, None)
    assert admit(committed("ar_baseline.zip")).block_count == 12


# ---------------------------------------------------------------------------------------
# Every page: a text layer or a portal block
# ---------------------------------------------------------------------------------------


def test_a_page_with_neither_a_layer_nor_a_block_is_refused_with_the_bare_pdfs_sentence() -> None:
    field, constraint, admission = judge(committed("image_only.zip"))
    assert (field, constraint, admission) == ("page_text", "every_page_has_extractable_text", None)
    with pytest.raises(DomainError) as raised:
        admit(committed("image_only.zip"))
    assert str(raised.value) == str(page_text_refusal()), (
        "the sentence is the bare PDF's, so characterization record 21 keeps its bytes"
    )


def test_a_block_of_any_type_satisfies_the_rule_for_its_page() -> None:
    accepted = admit(committed("image_only_with_block.zip"))
    assert accepted.textless_pages == (1, 2)

    pdf = generated.pdf_page_without_text_layer(3, 2)
    # A STAMP block alone on the page without a layer, and an IMAGE block alone.
    for kind, extra in (
        ("stamp", Block(fmt.KIND_STAMP, 1, (0.5, 0.86, 0.9, 0.95), fields=(("code", "X"),))),
        ("image", Block(fmt.KIND_IMAGE, 1, (0.1, 0.1, 0.9, 0.5), image=PLAN_IMAGE)),
    ):
        files = make_files(pdf, f"only_{kind}", extra_blocks=[extra])
        data = build_bundle(files).data
        result = admit(data)
        assert result.textless_pages == (2,), kind
        assert result.recognised_character_count == 0, (
            f"a {kind} block holds no recognised text, but {result.recognised_character_count} "
            "characters were counted"
        )


def test_a_block_on_another_page_does_not_satisfy_the_rule() -> None:
    pdf = generated.pdf_page_without_text_layer(3, 2)
    files = make_files(pdf, "elsewhere")              # TEXT blocks on pages 1 and 3 only
    assert judge(build_bundle(files, expect="every_page_has_extractable_text").data)[:2] == (
        "page_text", "every_page_has_extractable_text",
    )


# ---------------------------------------------------------------------------------------
# The counts
# ---------------------------------------------------------------------------------------


def test_the_character_count_is_the_sum_of_what_pypdfium2_reads_on_each_page() -> None:
    pdf = (CORPUS / "ar_baseline.pdf").read_bytes()
    per_page = pdfium_characters(pdf)
    admission = admit(committed("ar_baseline.zip"))
    assert admission.text_character_count == sum(per_page) > 0
    assert admission.textless_pages == ()
    assert admission.recognised_character_count == 0
    assert admission.page_count == len(per_page) == 8


def test_a_page_is_textless_below_fifty_characters_and_not_at_fifty() -> None:
    from ar_corpus import document

    assert TEXTLESS_PAGE_CHARACTERS == 50
    lines = lambda text: generated._page_lines([text])  # noqa: E731
    texts = ["x" * 49, "y" * 50, "z" * 51, "w" * 10]
    pdf = document.simple_text_pdf(generated._font(), [lines(t) for t in texts])
    per_page = pdfium_characters(pdf)
    assert per_page == [49, 50, 51, 10], f"pypdfium2 reads {per_page}; the pages are mis-sized"

    admission = admit(build_bundle(make_files(pdf, "threshold")).data)
    assert admission.textless_pages == (1, 4)
    assert admission.text_character_count == 160
    # Their text layers are real, so the text-layer rule is satisfied by the layer alone.
    assert admission.recognised_character_count > 0, (
        "the portal's TEXT blocks on those two pages hold recognised text"
    )


def test_the_textless_pages_are_ascending_one_based_and_empty_when_there_are_none() -> None:
    assert admit(committed("ar_baseline.zip")).textless_pages == ()
    pdf = generated.pdf_page_without_text_layer(page_count=5, textless_page=4)
    pages = read_pages(pdf)
    blocks = text_blocks(
        pages, only=range(len(pages)),
        bodies={3: "Распознанный текст четвёртой страницы без слоя."},
    )
    admission = admit(build_bundle(make_files(pdf, "fifth", pages=pages, blocks=blocks)).data)
    assert admission.textless_pages == (4,)
    assert admission.page_count == 5


def _markdown_bodies(markdown: str) -> dict[str, str]:
    """block id -> body, read by a second, independent pattern (the product's is line-based)."""
    section = re.compile(
        r"^### BLOCK #\d+ \[(TEXT|IMAGE)\]: (blk_[0-9a-f]{32})\n\n((?:> [^\n]*\n)+)\n"
        r"(.*?)(?=^### BLOCK #|^## Page |\Z)", re.MULTILINE | re.DOTALL)
    return {m.group(2): m.group(4).strip("\n") for m in section.finditer(markdown)
            if m.group(1) == "TEXT"}


def test_the_recognised_characters_are_those_of_the_text_blocks_on_the_textless_pages() -> None:
    data = committed("image_only_with_block.zip")
    with extract_bundle(io.BytesIO(data)) as bundle:
        document = json.loads(bundle.read_bytes("blocks"))
        bodies = _markdown_bodies(bundle.read_bytes("results_md").decode("utf-8"))
    per_page_text = {
        b["page_index"] + 1: len(bodies[b["block_id"]])
        for b in document["blocks"] if b["block_type"] == "text"
    }
    assert sorted(per_page_text) == [1, 2]
    admission = admit(data)
    assert admission.recognised_character_count == sum(per_page_text.values()) > 0

    # Not the characters of pages that have a layer: the baseline's TEXT blocks hold the
    # whole text layer and none of it counts, because no page is textless.
    assert admit(committed("ar_baseline.zip")).recognised_character_count == 0


def test_recognised_text_is_never_merged_into_the_text_layer_count() -> None:
    """The count of what pypdfium2 reads is the PDF's alone: the scanned bundle's recognised
    text (hundreds of characters) does not raise it above zero."""
    admission = admit(committed("image_only_with_block.zip"))
    assert admission.text_character_count == 0
    assert admission.recognised_character_count > 0


def test_a_crop_url_is_never_fetched_stored_for_display_or_rendered() -> None:
    """The portal's capability URLs: every ``crop_url`` and every ``> **Crop:**`` link of a bundle
    points at a port this test is listening on, the bundle is admitted, and nothing connects.

    "Stored for display" is the other half: no count, no field and no part of the admission
    carries a URL (it is a handful of integers), and the block list is stored byte for byte as
    the portal wrote it, so a later reader can see the link was never used."""
    import socket

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(8)
    listener.settimeout(0.5)
    try:
        port = listener.getsockname()[1]
        files = an.base_files()
        url = f"http://127.0.0.1:{port}/api/crops/"
        document = json.loads(files.blocks_json)
        for block in document["blocks"]:
            block["crop_url"] = url + block["block_id"]
        markdown = re.sub(r"https://portal\.invalid/api/crops/\S+?\)", url + "x)",
                          files.results_md.decode("utf-8"))
        assert str(port) in markdown
        items = pack(files)
        items[1].payload = blocklist.dump(document)
        items[2].payload = markdown.encode("utf-8")
        admission = admit(zipwrite.build_zip(items))
        with pytest.raises(socket.timeout):
            listener.accept()
        assert "http" not in repr(admission)
    finally:
        listener.close()
