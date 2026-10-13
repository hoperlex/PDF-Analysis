"""``page_geometry_extraction`` over portal bundles, on the lane's real S3 (`W55B-GEOMETRY-01`).

* a bundle publishes ``geometry.portal_blocks`` (section 4.9), the crop manifest under
  ``crop_policy: portal_image_blocks`` (section 4.5, validated against its contract schema)
  and one ``geometry.crop_image`` PNG blob per distinct crop (section 4.10);
* every rotation cuts the right pixels; a page whose box disagrees is ``geometry_mismatch``,
  cuts no crop, and the stage still succeeds;
* equal crops are one blob; the same input gives the same JSON bytes and, in one
  environment, the same crops; ``crop_url`` reaches no artifact;
* a version without a bundle publishes exactly what it did before;
* the PDF is opened from a temporary file the stage removes, on success and on failure, and
  the source blob is never read whole; PDFium renders only under ``PDFIUM_LOCK``;
* refusals are typed, with their ``reason``.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import pytest

import auditmanager.ingest.envelope as ingest_envelope
from auditmanager.analysis.engine.serialization import canonical_bytes
from auditmanager.analysis.geometry import render as render_module
from auditmanager.analysis.geometry.crops import PNG_SIGNATURE
from auditmanager.analysis.geometry.maths import MAX_PIXELS, MIN_LONG_SIDE_PX
from auditmanager.analysis.geometry.source_file import TEMPORARY_PREFIX
from auditmanager.analysis.public import (
    ROLE_BLOCK_INDEX,
    ROLE_CROP_IMAGE,
    ROLE_PAGE_CROPS,
    ROLE_PORTAL_BLOCKS,
    StageStatus,
)
from auditmanager.analysis.ports.artifacts import envelope
from auditmanager.analysis.stages import page_geometry_extraction
from auditmanager.shared.errors import ErrorCode
from auditmanager.storage.public import parse_blob_id
from tests.integration.analysis.geometry.geometry_support import (
    BLUE,
    RED,
    BlockSpec,
    PageSpec,
    Rect,
    artifact_document,
    bundle_members,
    committed_bundle,
    decode_png,
    displayed_rect,
    grown,
    normalised,
    portal_blocks_violations,
    prepare,
    run_geometry,
    validate_crop_manifest,
)
from tests.integration.analysis.recognised import recognised_support as support
from tests.integration.analysis.recognised.recognised_support import VERSION_UID

store = support.store

OLD_METRICS = {"block_count", "page_count", "crop_policy", "crop_count", "duration_ms"}
NEW_METRICS = {
    "crop_blob_count",
    "crop_skipped_for_mismatch_count",
    "portal_block_count",
    "portal_image_block_count",
    "geometry_mismatch_page_count",
}
SQUARE = Rect(150.0, 400.0, 200.0, 120.0, RED)


def _square_page(rotate: int = 0) -> PageSpec:
    return PageSpec(595.0, 842.0, rotate, (SQUARE, Rect(60.0, 60.0, 80.0, 40.0, BLUE)))


def _over_square(page: PageSpec, margin: float = 0.01) -> list[float]:
    return grown(normalised(page, displayed_rect(page, SQUARE)), margin)


def _blob(store: Any, reference: Any) -> bytes:
    return store.read(parse_blob_id(reference.blob_id))


def _geometry_files() -> set[str]:
    return {name for name in os.listdir(tempfile.gettempdir()) if name.startswith(TEMPORARY_PREFIX)}


@pytest.fixture(scope="module")
def baseline(store) -> dict[str, Any]:
    prepared = prepare(store, committed_bundle("ar_baseline.zip"))
    result = run_geometry(store, prepared)
    assert result.status is StageStatus.SUCCEEDED, result.error
    return {"prepared": prepared, "result": result}


# -- the committed baseline bundle ---------------------------------------------------------


def test_a_bundle_publishes_portal_blocks_the_manifest_and_one_blob_per_crop(store, baseline) -> None:
    result = baseline["result"]
    roles = [ref.role for ref in result.artifacts]
    assert roles == [ROLE_BLOCK_INDEX, ROLE_PAGE_CROPS, ROLE_PORTAL_BLOCKS, ROLE_CROP_IMAGE, ROLE_CROP_IMAGE]
    assert len({ref.blob_id for ref in result.artifacts}) == len(roles)
    assert set(result.metrics) == OLD_METRICS | NEW_METRICS
    assert {key: result.metrics[key] for key in OLD_METRICS - {"duration_ms"} | NEW_METRICS} == {
        "block_count": result.metrics["block_count"],
        "page_count": 8,
        "crop_policy": "portal_image_blocks",
        "crop_count": 2,
        "crop_blob_count": 2,
        "crop_skipped_for_mismatch_count": 0,
        "portal_block_count": 12,
        "portal_image_block_count": 2,
        "geometry_mismatch_page_count": 0,
    }
    portal = artifact_document(store, result, ROLE_PORTAL_BLOCKS)
    assert portal_blocks_violations(portal) == []
    assert portal["version_uid"] == VERSION_UID
    assert portal["blocks_sha256"] == hashlib.sha256(committed_bundle("ar_baseline.zip").block_list).hexdigest()
    assert {page["geometry"] for page in portal["pages"]} == {"ok"}


def test_the_manifest_lists_each_image_block_and_matches_its_blob(store, baseline) -> None:
    result = baseline["result"]
    manifest = artifact_document(store, result, ROLE_PAGE_CROPS)
    assert validate_crop_manifest(manifest) == []
    assert manifest["crop_policy"] == "portal_image_blocks"
    portal = artifact_document(store, result, ROLE_PORTAL_BLOCKS)
    images = [b for b in portal["blocks"] if b["block_type"] == "image"]
    assert [c["portal_block_id"] for c in manifest["crops"]] == [b["portal_block_id"] for b in images]
    images_by_blob = {ref.blob_id: ref for ref in result.artifacts if ref.role == ROLE_CROP_IMAGE}
    for record, block in zip(manifest["crops"], images):
        assert record["page_number"] == block["page_number"]
        assert record["bbox_norm"] == block["bbox_norm"]
        reference = images_by_blob[record["blob_id"]]
        assert (reference.sha256, reference.size_bytes, reference.media_type) == (
            record["sha256"], record["size_bytes"], "image/png"
        )
        payload = _blob(store, reference)
        assert hashlib.sha256(payload).hexdigest() == record["sha256"]
        assert payload.startswith(PNG_SIGNATURE)
        image = decode_png(payload)
        assert image.size == (record["width_px"], record["height_px"])
        assert max(image.size) >= MIN_LONG_SIDE_PX
        assert image.size[0] * image.size[1] <= MAX_PIXELS
        assert record["render_profile"] == {
            "renderer": render_module.renderer_name(),
            "scale": record["render_profile"]["scale"],
            "min_long_side_px": 800,
            "max_pixels": 4_000_000,
            "format": "png",
        }
        # the portal raster's density (2480 px over 595.28 pt), to six decimals
        assert record["render_profile"]["scale"] == round(2480 / 595.28, 6)


def test_crop_url_and_every_url_reach_no_artifact(store, baseline) -> None:
    for reference in baseline["result"].artifacts:
        if reference.media_type != "application/json":
            continue
        payload = _blob(store, reference)
        for forbidden in (b"crop_url", b"portal.invalid", b"://", b"document_path"):
            assert forbidden not in payload, (reference.role, forbidden)


def test_the_same_input_gives_the_same_json_bytes_and_in_one_environment_the_same_crops(store, baseline) -> None:
    again = run_geometry(store, baseline["prepared"])
    assert again.status is StageStatus.SUCCEEDED
    assert [(r.role, r.blob_id, r.sha256) for r in again.artifacts] == [
        (r.role, r.blob_id, r.sha256) for r in baseline["result"].artifacts
    ]


def test_the_manifest_validator_refuses_damaged_manifests(store, baseline) -> None:
    good = artifact_document(store, baseline["result"], ROLE_PAGE_CROPS)
    damages = [
        lambda m: m.update(crop_policy="all"),
        lambda m: m.update(crop_policy="none"),
        lambda m: m["crops"][0].pop("blob_id"),
        lambda m: m["crops"][0].update(url="https://x"),
        lambda m: m["crops"][0]["render_profile"].update(min_long_side_px=799),
        lambda m: m["crops"][0]["render_profile"].update(scale=0),
        lambda m: m["crops"][0].update(sha256="ABC"),
        lambda m: m["crops"][0].update(bbox_norm=[0, 0, 1]),
        lambda m: m["crops"][0].update(width_px=0),
        lambda m: m.update(version_uid="ver_x"),
        lambda m: m["crops"][0]["render_profile"].update(renderer=""),
    ]
    for damage in damages:
        copy_ = json.loads(json.dumps(good))
        damage(copy_)
        assert validate_crop_manifest(copy_), damage


# -- a version without a bundle ------------------------------------------------------------


def test_a_version_without_a_bundle_publishes_exactly_what_it_did_before(store, baseline) -> None:
    bare = prepare(store, committed_bundle("ar_baseline.zip"), bundle=False)
    result = run_geometry(store, bare, with_companion=False)
    assert result.status is StageStatus.SUCCEEDED, result.error
    assert [ref.role for ref in result.artifacts] == [ROLE_BLOCK_INDEX, ROLE_PAGE_CROPS]
    assert set(result.metrics) == OLD_METRICS
    assert (result.metrics["crop_policy"], result.metrics["crop_count"]) == ("none", 0)
    manifest = _blob(store, result.artifact(ROLE_PAGE_CROPS))
    assert manifest == canonical_bytes(
        envelope(ROLE_PAGE_CROPS, VERSION_UID, crop_policy="none", crops=[])
    )
    assert validate_crop_manifest(json.loads(manifest)) == []
    # the block index is the bundle's, byte for byte: the bundle adds, never changes
    bundled = baseline["result"].artifact(ROLE_BLOCK_INDEX)
    assert result.artifact(ROLE_BLOCK_INDEX).sha256 == bundled.sha256
    assert result.metrics["block_count"] == baseline["result"].metrics["block_count"]


# -- rotations, end to end -----------------------------------------------------------------


def test_every_rotation_cuts_the_drawn_rectangle(store) -> None:
    pages = [_square_page(rotate) for rotate in (0, 90, 180, 270)]
    blocks = [BlockSpec("image", n, _over_square(page), ordinal=1) for n, page in enumerate(pages, start=1)]
    result = run_geometry(store, prepare(store, bundle_members(pages, blocks)))
    assert result.status is StageStatus.SUCCEEDED, result.error
    portal = artifact_document(store, result, ROLE_PORTAL_BLOCKS)
    assert [(p["rotation_deg"], p["geometry"]) for p in portal["pages"]] == [
        (0, "ok"), (90, "ok"), (180, "ok"), (270, "ok")
    ]
    manifest = artifact_document(store, result, ROLE_PAGE_CROPS)
    assert len(manifest["crops"]) == 4
    for record in manifest["crops"]:
        image = decode_png(store.read(parse_blob_id(record["blob_id"]))).convert("RGB")
        width, height = image.size
        assert image.getpixel((width // 2, height // 2)) == (255, 0, 0), record["page_number"]
        assert image.getpixel((1, 1)) == (255, 255, 255), record["page_number"]


# -- the page-box check --------------------------------------------------------------------


def test_a_page_whose_box_disagrees_cuts_no_crop_and_the_stage_still_succeeds(store) -> None:
    pages = [_square_page() for _ in range(4)]
    blocks = [BlockSpec("image", n, _over_square(pages[0]), ordinal=1) for n in range(1, 5)]
    blocks.append(BlockSpec("text", 2, [0.1, 0.05, 0.5, 0.1], ordinal=0))
    width_px, height_px = round(595 * 300 / 72), round(842 * 300 / 72)
    rasters = {
        2: (round(width_px * 1.01), height_px, 0),     # 1 % wider than the page: a mismatch
        3: (width_px, height_px, 90),                  # the portal says /Rotate 90; the PDF, 0
        4: (round(width_px * 1.004), height_px, 0),    # 0.4 %: within the tolerance
    }
    result = run_geometry(store, prepare(store, bundle_members(pages, blocks, rasters=rasters)))
    assert result.status is StageStatus.SUCCEEDED, result.error
    portal = artifact_document(store, result, ROLE_PORTAL_BLOCKS)
    assert portal_blocks_violations(portal) == []
    assert [p["geometry"] for p in portal["pages"]] == ["ok", "geometry_mismatch", "geometry_mismatch", "ok"]
    assert {(b["page_number"], b["geometry"]) for b in portal["blocks"]} == {
        (1, "ok"), (2, "geometry_mismatch"), (3, "geometry_mismatch"), (4, "ok")
    }
    manifest = artifact_document(store, result, ROLE_PAGE_CROPS)
    assert [c["page_number"] for c in manifest["crops"]] == [1, 4]
    assert result.metrics["geometry_mismatch_page_count"] == 2
    assert result.metrics["crop_skipped_for_mismatch_count"] == 2
    assert result.metrics["crop_count"] == 2
    assert result.metrics["portal_image_block_count"] == 4


# -- equal crops ---------------------------------------------------------------------------


def test_equal_crops_are_one_blob(store) -> None:
    pages = [_square_page(), _square_page()]
    box = _over_square(pages[0])
    blocks = [
        BlockSpec("image", 1, box, ordinal=1),
        BlockSpec("image", 1, box, ordinal=2),     # the same box on the same page
        BlockSpec("image", 2, box, ordinal=1),     # the same box on an identical page
    ]
    result = run_geometry(store, prepare(store, bundle_members(pages, blocks)))
    assert result.status is StageStatus.SUCCEEDED, result.error
    manifest = artifact_document(store, result, ROLE_PAGE_CROPS)
    assert len(manifest["crops"]) == 3
    assert len({c["blob_id"] for c in manifest["crops"]}) == 1
    assert [ref.role for ref in result.artifacts].count(ROLE_CROP_IMAGE) == 1
    assert (result.metrics["crop_count"], result.metrics["crop_blob_count"]) == (3, 1)


# -- the temporary file, the stream and the lock -------------------------------------------


class _Spy:
    """Wraps a callable; records what it was handed and whether that file existed then."""

    def __init__(self, inner: Any, *, fail: bool = False) -> None:
        self.inner = inner
        self.fail = fail
        self.calls: list[tuple[Any, bool, str | None]] = []

    def __call__(self, source: Any, *args: Any, **kwargs: Any) -> Any:
        path = Path(source) if isinstance(source, (str, os.PathLike)) else None
        exists = path is not None and path.is_file()
        digest = hashlib.sha256(path.read_bytes()).hexdigest() if exists else None
        self.calls.append((source, exists, digest))
        if self.fail:
            from auditmanager.shared.errors import DomainError

            raise DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, reason="spy_failure", stage_id="x")
        return self.inner(source, *args, **kwargs)


def test_the_pdf_is_opened_from_one_temporary_file_that_is_gone_afterwards(store, monkeypatch) -> None:
    bundle = committed_bundle("ar_baseline.zip")
    prepared = prepare(store, bundle)
    extract = _Spy(page_geometry_extraction.extract_document)
    monkeypatch.setattr(page_geometry_extraction, "extract_document", extract)
    import pypdfium2

    opened = _Spy(pypdfium2.PdfDocument)
    monkeypatch.setattr(pypdfium2, "PdfDocument", opened)
    before = _geometry_files()

    result = run_geometry(store, prepared)

    assert result.status is StageStatus.SUCCEEDED, result.error
    (source, existed, digest), = extract.calls
    assert isinstance(source, str), "the extractor was handed bytes, not a path"
    assert existed and digest == hashlib.sha256(bundle.pdf).hexdigest()
    assert Path(source).parent == Path(tempfile.gettempdir())
    assert Path(source).name.startswith(TEMPORARY_PREFIX)
    assert [call[0] for call in opened.calls] == [source], "PDFium opens the same file"
    assert not Path(source).exists()
    assert _geometry_files() == before


@pytest.mark.parametrize("where", ["extraction", "render"])
def test_the_temporary_file_is_removed_when_the_stage_fails(store, monkeypatch, where) -> None:
    prepared = prepare(store, committed_bundle("ar_baseline.zip"))
    extract = _Spy(page_geometry_extraction.extract_document, fail=where == "extraction")
    monkeypatch.setattr(page_geometry_extraction, "extract_document", extract)
    if where == "render":
        def broken(self, page_number, plan):
            raise RuntimeError("the renderer broke")

        monkeypatch.setattr(render_module.PdfiumDocument, "render", broken)
    before = _geometry_files()

    if where == "render":
        with pytest.raises(RuntimeError):
            run_geometry(store, prepared)
    else:
        result = run_geometry(store, prepared)
        assert result.status is StageStatus.FAILED and result.artifacts == ()
        assert result.error.details.get("reason") == "spy_failure"
    source, existed, _digest = extract.calls[0]
    assert existed and not Path(source).exists()
    assert _geometry_files() == before


class _GuardedStore:
    """The real store, except for one blob: a whole read of it, or any read, is refused."""

    def __init__(self, inner: Any, blob_id: Any, *, refuse_stream: bool = False) -> None:
        self._inner = inner
        self._blob_id = str(blob_id)
        self._refuse_stream = refuse_stream

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)

    def read(self, blob_id: Any, **kwargs: Any) -> bytes:
        if str(blob_id) == self._blob_id:
            raise AssertionError("this blob must not be read whole")
        return self._inner.read(blob_id, **kwargs)

    def open_stream(self, blob_id: Any, **kwargs: Any) -> Any:
        if self._refuse_stream and str(blob_id) == self._blob_id:
            raise OSError("the store broke")
        return self._inner.open_stream(blob_id, **kwargs)


def test_the_source_document_is_never_read_whole(store) -> None:
    prepared = prepare(store, committed_bundle("ar_baseline.zip"))
    from auditmanager.analysis.public import run_stage

    guarded = _GuardedStore(store, prepared.pdf_blob)
    result = run_stage(
        "page_geometry_extraction", version_uid=VERSION_UID,
        inputs=prepared.geometry_inputs(), blob_store=guarded,
    )
    assert result.status is StageStatus.SUCCEEDED, result.error


def test_every_pdfium_render_of_the_stage_holds_the_lock(store, monkeypatch) -> None:
    import pypdfium2.raw as pdfium_raw

    held: list[bool] = []
    original = pdfium_raw.FPDF_RenderPageBitmap

    def render(*args: Any) -> Any:
        held.append(ingest_envelope.PDFIUM_LOCK.locked())
        return original(*args)

    monkeypatch.setattr(pdfium_raw, "FPDF_RenderPageBitmap", render)
    result = run_geometry(store, prepare(store, committed_bundle("ar_baseline.zip")))
    assert result.status is StageStatus.SUCCEEDED, result.error
    assert held == [True, True]
    assert not ingest_envelope.PDFIUM_LOCK.locked()


# -- refusals ------------------------------------------------------------------------------


def _refusal(result: Any) -> str:
    assert result.status is StageStatus.FAILED and result.artifacts == ()
    assert result.error.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert result.error.details.get("stage_id") == "page_geometry_extraction"
    return str(result.error.details.get("reason"))


def test_a_block_list_the_store_cannot_hand_back_is_refused_never_treated_as_absent(store) -> None:
    from auditmanager.analysis.public import run_stage

    prepared = prepare(store, committed_bundle("ar_baseline.zip"))

    class Unreadable(_GuardedStore):
        def read(self, blob_id: Any, **kwargs: Any) -> bytes:
            if str(blob_id) == self._blob_id:
                raise OSError("gone")
            return self._inner.read(blob_id, **kwargs)

    result = run_stage(
        "page_geometry_extraction", version_uid=VERSION_UID,
        inputs=prepared.geometry_inputs(), blob_store=Unreadable(store, prepared.blocks_blob),
    )
    assert _refusal(result) == "portal_input_unreadable"


def test_a_source_stream_that_breaks_is_source_unreadable_and_leaves_no_file(store) -> None:
    from auditmanager.analysis.public import run_stage

    prepared = prepare(store, committed_bundle("ar_baseline.zip"))
    before = _geometry_files()
    result = run_stage(
        "page_geometry_extraction", version_uid=VERSION_UID, inputs=prepared.geometry_inputs(),
        blob_store=_GuardedStore(store, prepared.pdf_blob, refuse_stream=True),
    )
    assert _refusal(result) == "source_unreadable"
    assert _geometry_files() == before


def test_a_block_list_the_stage_cannot_use_is_portal_blocks_invalid(store) -> None:
    from auditmanager.analysis.public import run_stage
    from tests.integration.analysis.recognised.recognised_support import publish

    prepared = prepare(store, committed_bundle("ar_baseline.zip"))
    edited = json.loads(committed_bundle("ar_baseline.zip").block_list)
    edited["blocks"][0]["coords_norm"] = [0.5, 0.5, 0.4, 0.6]
    bad = publish(store, json.dumps(edited).encode(), role="source_structured_companion",
                  media_type="application/json")
    inputs = prepared.geometry_inputs() | {"source.structured_companion": bad}
    before = _geometry_files()
    result = run_stage("page_geometry_extraction", version_uid=VERSION_UID, inputs=inputs, blob_store=store)
    assert _refusal(result) == "portal_blocks_invalid"
    assert _geometry_files() == before


def test_a_degenerate_image_block_is_refused_and_leaves_no_file(store) -> None:
    page = _square_page()
    tiny = 1e-9
    members_ = bundle_members([page], [BlockSpec("image", 1, [0.5, 0.5, 0.5 + tiny, 0.5 + tiny], ordinal=1)])
    prepared = prepare(store, members_)
    before = _geometry_files()
    assert _refusal(run_geometry(store, prepared)) == "portal_block_degenerate"
    assert _geometry_files() == before
