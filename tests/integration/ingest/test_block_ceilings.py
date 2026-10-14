"""The block list is bounded: per page, per bundle and in IMAGE blocks (`W55B-FIX`, X-4 and X-6).

`W55B-JUDGE-X` X-4: nothing bounded the number of portal blocks but the 16 MiB member, which
held about 120 000 IMAGE blocks, and every IMAGE block on a page that passes the box check is
cut, encoded and published as a crop of up to 4 000 000 pixels. X-6: ``_blocks.json`` cost
about 25 times its size in memory before a single block was judged.

* **The ceilings** (``blocks_count``): at most 100 blocks on a page, 3 000 in a bundle and
  1 000 IMAGE blocks in a bundle. Real maxima, measured on the 674 corpus bundles and the
  owner's export (counts only): 9 blocks on a page, 500 in a bundle, 47 IMAGE blocks in a
  bundle. Each ceiling is shown at its value (accepted) and one over it (refused), by the
  product and by the fixtures' reference checker, and the end-to-end page case through the
  archive reader and the whole envelope.
* **The member bound** of ``_blocks.json``: 4 MiB, fourteen times the largest real list
  (283 408 bytes); declared or counted, it answers ``bundle_member_size``, and the markdown,
  which is not parsed as JSON, keeps its own 16 MiB bound.

Every expected figure is a literal. The module needs no database.
"""

from __future__ import annotations

import io
import json
import zipfile
from typing import Any

import pytest

from auditmanager.ingest import bundle_archive as ba
from auditmanager.ingest import bundle_envelope as be
from auditmanager.ingest.bundle_archive import BundleLimits
from portal_bundle import archive_negatives as an  # tools/fixtures, on the path via conftest
from portal_bundle import portal_format as fmt
from portal_bundle import validate, zipwrite
from tests.integration.ingest.bundle_support import committed, judge

MiB = 1024 * 1024


@pytest.fixture(autouse=True)
def clean_tables() -> None:  # type: ignore[override]
    """Overrides ``conftest.clean_tables``: there is no database to empty."""


def _block(number: int, page: int, kind: str = "stamp") -> dict[str, Any]:
    return {
        "block_id": f"blk_{number:032x}", "page_index": page, "page_label": page + 1,
        "ordinal": None if kind == "stamp" else number, "block_type": kind,
        "status": "recognized", "coords_norm": [0.1, 0.1, 0.2, 0.2],
    }


def _blocks(count: int, *, per_page: int, kind: str = "stamp") -> list[dict[str, Any]]:
    return [_block(number, number // per_page, kind) for number in range(count)]


def _reference_says(blocks: list[dict[str, Any]]) -> list[str]:
    return [v.constraint for v in validate._check_block_ceilings({"blocks": blocks})]


CASES = [
    ("the page ceiling", _blocks(100, per_page=100), _blocks(101, per_page=101)),
    ("the bundle ceiling", _blocks(3_000, per_page=100), _blocks(3_001, per_page=100)),
    (
        "the IMAGE ceiling",
        _blocks(1_000, per_page=100, kind="image"),
        _blocks(1_001, per_page=100, kind="image"),
    ),
]


@pytest.mark.parametrize(("label", "at", "over"), CASES, ids=[c[0] for c in CASES])
def test_each_ceiling_admits_its_value_and_refuses_one_more(label: str, at: list, over: list) -> None:
    assert not be._over_a_ceiling(at), label
    assert _reference_says(at) == [], label
    assert be._over_a_ceiling(over), label
    assert _reference_says(over) == ["blocks_count"], label


def test_the_ceilings_are_the_measured_figures_and_the_fixtures_restate_them() -> None:
    assert (be.MAX_BLOCKS_PER_PAGE, be.MAX_BLOCKS, be.MAX_IMAGE_BLOCKS) == (100, 3_000, 1_000)
    assert (fmt.MAX_BLOCKS_PER_PAGE, fmt.MAX_BLOCKS, fmt.MAX_IMAGE_BLOCKS) == (100, 3_000, 1_000)
    # The real maxima (W55B-FIX §4) sit under each ceiling with the recorded margin.
    assert 9 * 11 <= be.MAX_BLOCKS_PER_PAGE
    assert 500 * 6 <= be.MAX_BLOCKS
    assert 47 * 21 <= be.MAX_IMAGE_BLOCKS


def test_a_page_over_its_ceiling_is_refused_through_the_whole_envelope_by_both() -> None:
    data = an.blocks_over_the_page_ceiling()
    assert judge(data)[:2] == ("file", "blocks_count")
    limits = validate.Limits(member_bytes=ba.MEMBER_BYTES, stamp_audit_bytes=ba.STAMP_AUDIT_BYTES)
    assert validate.validate(data, limits).constraints == ("blocks_count",)


def test_every_committed_bundle_is_inside_the_ceilings() -> None:
    for name in ("ar_baseline", "ar_baseline_minimal", "ar_baseline_ocr_defects",
                 "image_only_with_block", "pages_31"):
        assert judge(committed(f"{name}.zip"))[:2] == (None, None), name


# -- the member bound of _blocks.json (X-6) -------------------------------------------------


def test_the_block_list_bound_is_four_mebibytes_and_the_markdown_keeps_sixteen() -> None:
    assert ba.BLOCKS_MEMBER_BYTES == 4 * MiB
    assert ba.TEXT_MEMBER_BYTES == 16 * MiB
    assert ba.DEFAULT_LIMITS.blocks_member_bytes == 4 * MiB
    assert ba.BLOCKS_MEMBER_BYTES >= 14 * 283_408


LOW = BundleLimits(blocks_member_bytes=64 * 1024)


def _with_padded(suffix: bytes, size: int, *, declared: int | None) -> bytes:
    """The base bundle with one member grown to ``size`` bytes (trailing whitespace, so the JSON
    or markdown is still what it was), its header telling the truth or ``declared``."""
    items = an.members()
    target = next(i for i in items if i.name.endswith(suffix))
    target.payload = bytes(target.payload) + b" " * (size - len(target.payload))
    target.declared_size = declared
    return zipwrite.build_zip(items)


@pytest.mark.parametrize("declared", [None, 10], ids=["honest header", "header lies small"])
def test_a_block_list_over_its_own_bound_is_a_member_over_its_size(declared: int | None) -> None:
    data = _with_padded(b"_blocks.json", LOW.blocks_member_bytes + 1, declared=declared)
    assert judge(data, LOW)[:2] == ("file", "bundle_member_size")


def test_a_block_list_at_its_bound_and_a_markdown_over_it_are_not_refused_for_size() -> None:
    at = _with_padded(b"_blocks.json", LOW.blocks_member_bytes, declared=None)
    assert judge(at, LOW)[:2] == (None, None)
    markdown = _with_padded(b"_results.md", LOW.blocks_member_bytes + 1, declared=None)
    assert judge(markdown, LOW)[:2] == (None, None)


def test_the_real_block_lists_fit_the_bound_by_their_own_bytes() -> None:
    """The committed block lists, read out of their archives, against the production bound."""
    for name in ("ar_baseline", "pages_31"):
        with zipfile.ZipFile(io.BytesIO(committed(f"{name}.zip"))) as archive:
            raw = archive.read(next(n for n in archive.namelist() if n.endswith("_blocks.json")))
        assert len(raw) < ba.BLOCKS_MEMBER_BYTES and json.loads(raw)["blocks"], name
