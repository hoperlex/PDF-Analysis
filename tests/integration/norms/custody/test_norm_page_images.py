"""`M7-NORM-PNG` against a real PostgreSQL and a real S3-compatible store: a norm page is rendered once, kept, and chosen only from the request.

The pages are one-page PDFs held by custody (role ``norm_source``, anchor kind ``crop``, the anchor the paragraph's ``block_ref``), as the corpus holds
them. The renderer is the product's (PDFium under ``PDFIUM_LOCK``); a PNG is checked by its header bytes and its size, never opened. Each case
observes the database through its own connection, never through the code under test.
"""

from __future__ import annotations

import hashlib
import io
import json
import struct
from dataclasses import dataclass
from types import SimpleNamespace as NS
from typing import Any

import pytest
from PIL import Image, ImageDraw
from sqlalchemy import text

from auditmanager.analysis.public import build_critic_request
from auditmanager.executors.image_input import checked_pngs
from auditmanager.executors.pull import _task_payload
from auditmanager.norms.public import (
    NORM_SOURCE,
    CustodyDispatcher,
    NormPageImages,
    admit,
    publish_bindings,
)
from auditmanager.norms.page_images import MAX_IMAGES_PER_TASK, RENDER_PROFILE, render_pdf_page
from auditmanager.runs import extended_review as runtime
from auditmanager.shared.db import session_scope
from auditmanager.shared.identity import NormParagraphId
from auditmanager.storage.public import parse_blob_id

from .conftest import CustodyKit, insert_target, new_document_id

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _pdf(number: int, *, pages: int = 1) -> bytes:
    """A one-page PDF (several on request), different for every ``number`` so that the pages are different Blobs."""
    images = []
    for page in range(pages):
        image = Image.new("RGB", (420, 594), "white")
        ImageDraw.Draw(image).rectangle((20 + 7 * number, 30 + page, 200 + 11 * number, 120 + 5 * number), fill="black")
        images.append(image)
    buffer = io.BytesIO()
    images[0].save(buffer, format="PDF", save_all=pages > 1, append_images=images[1:], resolution=72.0)
    return buffer.getvalue()


def _png_size(data: bytes) -> tuple[int, int]:
    """The pixel size from the IHDR chunk; the picture itself is never decoded."""
    assert data.startswith(PNG_SIGNATURE) and data[12:16] == b"IHDR"
    return struct.unpack(">II", data[16:24])


@dataclass
class Corpus:
    kit: CustodyKit
    document_id: str
    snapshot_id: str
    paragraphs: list[str]

    def row(self, number: int) -> dict[str, str]:
        """What a ``norm_context`` row of a critic request names its paragraph by."""
        return {"snapshot_id": self.snapshot_id, "document_id": self.document_id, "paragraph_id": self.paragraphs[number],
            "designation": "СП 1.2.3", "clause_number": f"{number + 1}.1", "quote": f"Текст нормы {number}",
            "page_label": number + 1, "status": "candidate_not_verified"}

    def binding_of(self, block: str) -> str | None:
        return self.kit.scalar(
            "SELECT norm_custody_binding_id FROM norm_custody_binding WHERE anchor_kind = 'crop' AND anchor = :block", block=block)

    def renders(self) -> list[Any]:
        with self.kit.engine.connect() as connection:
            return list(connection.execute(text(
                "SELECT norm_custody_binding_id, render_profile, blob_id, sha256, size_bytes, media_type, width_px, height_px "
                "FROM norm_crop_render ORDER BY rendered_at, norm_custody_binding_id")).mappings())


def _corpus(kit: CustodyKit, pages: list[bytes | None], *, blocks: list[int] | None = None) -> Corpus:
    """One norm document with one paragraph per entry of ``blocks`` (default: one per page). ``pages[i]`` is the one-page PDF custody holds for
    the block ``blk_i``; ``None`` is a page custody does not hold. ``blocks[j]`` names the block paragraph ``j`` sits on."""
    blocks = list(range(len(pages))) if blocks is None else blocks
    document = new_document_id()
    with session_scope(kit.session_factory) as session:
        insert_target(session, document)
        snapshot, document_pk = session.execute(text(
            "SELECT norms_snapshot_id, norm_document_pk FROM norm_document WHERE norm_document_id = :d"), {"d": document}).one()
        paragraphs, offset = [], 0
        for ordinal, block in enumerate(blocks):
            body = f"Пункт {ordinal}: требования к конструкции."
            paragraph = str(NormParagraphId.new())
            paragraphs.append(paragraph)
            session.execute(text(
                "INSERT INTO norm_paragraph (norm_paragraph_id, norms_snapshot_id, norm_document_pk, ordinal, page_label, block_ref, "
                "char_offset, char_length, kind, text) VALUES (:p, :s, :pk, :o, :page, :block, :offset, :length, 'body', :body)"
            ), {"p": paragraph, "s": snapshot, "pk": document_pk, "o": ordinal, "page": block + 1, "block": f"blk_{block}",
                "offset": offset, "length": len(body), "body": body})
            offset += len(body) + 1
    held = [(number, pdf) for number, pdf in enumerate(pages) if pdf is not None]
    for number, pdf in held:
        request = kit.request(document, f"blk_{number}", pdf, anchor_kind="crop")
        with session_scope(kit.session_factory) as session:
            admit(session, request, manifest=kit.manifest)
    CustodyDispatcher(kit.store, source=kit.source, session_factory=kit.session_factory).dispatch()
    with session_scope(kit.session_factory) as session:
        publish_bindings(session, NORM_SOURCE, [document])
    return Corpus(kit=kit, document_id=document, snapshot_id=snapshot, paragraphs=paragraphs)


class CountingRenderer:
    """The product's renderer, counted: how many times a page was really drawn."""

    def __init__(self) -> None:
        self.pdfs: list[bytes] = []

    def __call__(self, pdf: bytes):
        self.pdfs.append(pdf)
        return render_pdf_page(pdf)


def _service(kit: CustodyKit, renderer: CountingRenderer) -> NormPageImages:
    return NormPageImages(store=kit.store, session_factory=kit.session_factory, renderer=renderer)


# -- rendered once, kept, reused ---------------------------------------------------------------------------------------------------------


def test_a_page_is_rendered_once_kept_in_norm_crop_render_and_reused(custody: CustodyKit) -> None:
    corpus = _corpus(custody, [_pdf(1)])
    renderer = CountingRenderer()
    first = _service(custody, renderer).select([corpus.row(0)])
    image, = first.images
    row, = corpus.renders()
    binding = corpus.binding_of("blk_0")
    assert binding is not None and image.crop_id == "norm." + binding and row["norm_custody_binding_id"] == binding
    assert (row["render_profile"], row["media_type"]) == (RENDER_PROFILE, "image/png")
    # the row describes the bytes: digest, size and pixel size from the PNG's own header
    assert image.data.startswith(PNG_SIGNATURE) and len(image.data) == row["size_bytes"] > 100
    assert hashlib.sha256(image.data).hexdigest() == row["sha256"] == image.render.sha256
    assert _png_size(image.data) == (row["width_px"], row["height_px"])
    assert row["width_px"] > 400, "150 dpi: a 420 x 594 pt page is about 875 x 1237 px"
    # the Blob is published and available, and its object is in the bucket under the content-derived key
    assert custody.scalar("SELECT state FROM blob WHERE blob_id = :b", b=row["blob_id"]) == "available"
    assert custody.store.read(parse_blob_id(row["blob_id"])) == image.data
    # the second delivery -- the same service, then another one as another process would be -- draws nothing and adds no row
    again = _service(custody, renderer).select([corpus.row(0)])
    assert len(renderer.pdfs) == 1, "a render is made once"
    assert again.images[0].data == image.data and again.images[0].render == first.images[0].render
    _service(custody, renderer).select([corpus.row(0)])
    assert len(renderer.pdfs) == 1 and len(corpus.renders()) == 1


def test_the_second_page_of_a_pair_is_the_only_new_render(custody: CustodyKit) -> None:
    corpus = _corpus(custody, [_pdf(1), _pdf(2)])
    renderer = CountingRenderer()
    service = _service(custody, renderer)
    service.select([corpus.row(0)])
    service.select([corpus.row(0), corpus.row(1)])
    assert len(renderer.pdfs) == 2 and len(corpus.renders()) == 2


# -- at most two pages ------------------------------------------------------------------------------------------------------------------


def test_at_most_two_pages_of_three_paragraphs_and_the_third_page_is_never_rendered(custody: CustodyKit) -> None:
    corpus = _corpus(custody, [_pdf(1), _pdf(2), _pdf(3)])
    renderer = CountingRenderer()
    selection = _service(custody, renderer).select([corpus.row(number) for number in range(3)])
    assert MAX_IMAGES_PER_TASK == 2 and len(selection.images) == 2
    assert [image.paragraph_ids for image in selection.images] == [(corpus.paragraphs[0],), (corpus.paragraphs[1],)], "in the order of the request"
    assert len(renderer.pdfs) == 2 and len(corpus.renders()) == 2 and corpus.binding_of("blk_2") not in {r["norm_custody_binding_id"] for r in corpus.renders()}
    assert selection.unavailable == ()


def test_a_limit_above_two_is_refused(custody: CustodyKit) -> None:
    service = _service(custody, CountingRenderer())
    with pytest.raises(ValueError, match="norm_page_image_limit_invalid"):
        service.select([], limit=3)
    assert service.select([], limit=0).images == ()


def test_two_paragraphs_of_one_page_are_one_image_and_both_are_named_on_it(custody: CustodyKit) -> None:
    corpus = _corpus(custody, [_pdf(1), _pdf(2)], blocks=[0, 0, 1])
    selection = _service(custody, CountingRenderer()).select([corpus.row(0), corpus.row(1), corpus.row(2)])
    assert [image.paragraph_ids for image in selection.images] == [(corpus.paragraphs[0], corpus.paragraphs[1]), (corpus.paragraphs[2],)]


# -- only the pages of the request's own paragraphs ---------------------------------------------------------------------------------------


def test_only_the_pages_of_the_paragraphs_of_the_request_are_shown(custody: CustodyKit) -> None:
    corpus = _corpus(custody, [_pdf(1), _pdf(2), _pdf(3)])
    renderer = CountingRenderer()
    selection = _service(custody, renderer).select([corpus.row(2)])
    image, = selection.images
    assert image.paragraph_ids == (corpus.paragraphs[2],) and image.crop_id == "norm." + (corpus.binding_of("blk_2") or "")
    assert [row["norm_custody_binding_id"] for row in corpus.renders()] == [corpus.binding_of("blk_2")], "the other two pages stay unrendered"
    assert len(renderer.pdfs) == 1


def test_a_row_that_does_not_name_a_paragraph_of_this_snapshot_and_document_shows_no_page(custody: CustodyKit) -> None:
    corpus = _corpus(custody, [_pdf(1)])
    other_snapshot = {**corpus.row(0), "snapshot_id": "ns_" + "0" * 26}
    other_document = {**corpus.row(0), "document_id": "ndoc_" + "0" * 26}
    unknown = {**corpus.row(0), "paragraph_id": str(NormParagraphId.new())}
    renderer = CountingRenderer()
    selection = _service(custody, renderer).select([other_snapshot, other_document, unknown, {"paragraph_id": "x"}, "not a row", None])
    assert selection.images == () and renderer.pdfs == [] and corpus.renders() == []
    assert {reason for _, reason in selection.unavailable} == {"page_not_in_custody"}


# -- a page that cannot be produced -------------------------------------------------------------------------------------------------------


def test_a_page_custody_does_not_hold_is_listed_and_the_next_page_takes_its_place(custody: CustodyKit) -> None:
    corpus = _corpus(custody, [None, _pdf(2)])
    selection = _service(custody, CountingRenderer()).select([corpus.row(0), corpus.row(1)])
    assert [image.paragraph_ids for image in selection.images] == [(corpus.paragraphs[1],)]
    assert selection.unavailable == ((corpus.paragraphs[0], "page_not_in_custody"),)


def test_a_source_that_is_not_a_pdf_is_listed_leaves_no_row_and_is_tried_again_next_time(custody: CustodyKit) -> None:
    corpus = _corpus(custody, [b"%PDF-1.7\nthis is not a document of any kind\n"])
    renderer = CountingRenderer()
    service = _service(custody, renderer)
    first = service.select([corpus.row(0)])
    assert first.images == () and first.unavailable == ((corpus.paragraphs[0], "source_unreadable"),)
    assert corpus.renders() == []
    service.select([corpus.row(0)])
    assert len(renderer.pdfs) == 2, "nothing was recorded, so the next delivery tries again"


def test_a_source_of_two_pages_is_refused_not_cut(custody: CustodyKit) -> None:
    corpus = _corpus(custody, [_pdf(1, pages=2)])
    selection = _service(custody, CountingRenderer()).select([corpus.row(0)])
    assert selection.images == () and selection.unavailable == ((corpus.paragraphs[0], "source_not_one_page"),)
    assert corpus.renders() == []


def test_a_page_that_would_need_too_many_pixels_is_refused_not_rendered_smaller(custody: CustodyKit) -> None:
    corpus = _corpus(custody, [_pdf(1)])
    selection = _service(custody, lambda pdf: render_pdf_page(pdf, max_pixels=1000)).select([corpus.row(0)])
    assert selection.images == () and selection.unavailable == ((corpus.paragraphs[0], "page_too_large"),)
    assert corpus.renders() == []


def test_a_render_whose_blob_no_longer_matches_its_row_is_reported_and_never_delivered(custody: CustodyKit) -> None:
    corpus = _corpus(custody, [_pdf(1)])
    renderer = CountingRenderer()
    _service(custody, renderer).select([corpus.row(0)])
    row, = corpus.renders()
    # the row is the record of the bytes: a service whose store returns other bytes under that id finds out and says so
    class Corrupt:
        def __init__(self, store: Any) -> None:
            self._store = store

        def __getattr__(self, name: str) -> Any:
            return getattr(self._store, name)

        def read(self, blob_id: Any, *, verify: bool = True) -> bytes:
            return PNG_SIGNATURE + b"not the bytes of the render"

    selection = NormPageImages(store=Corrupt(custody.store), session_factory=custody.session_factory, renderer=renderer).select([corpus.row(0)])
    assert selection.images == () and selection.unavailable == ((corpus.paragraphs[0], "render_unreadable"),)
    assert len(renderer.pdfs) == 1 and len(corpus.renders()) == 1 and corpus.renders()[0]["sha256"] == row["sha256"]


# -- the task the critic is given ------------------------------------------------------------------------------------------------------------


def test_the_critic_request_declares_the_pages_and_the_task_the_pull_adapter_writes_carries_them(custody: CustodyKit, monkeypatch) -> None:
    """From the corpus to the descriptors: the request is built for these paragraphs, the helper adds their pages, the descriptors pass the executor's
    own checks, the bytes behind them are the rendered PNGs, and the task payload is what the runner is served."""
    corpus = _corpus(custody, [_pdf(1), _pdf(2), _pdf(3)])
    candidates = [corpus.row(number) for number in range(3)]
    observation = {"title": "Наблюдение", "description": "Описание", "source_ids": ["s1"], "norm_candidates": candidates}
    source = {"source_id": "s1", "kind": "text", "source_type": "native_text", "page_number": 1, "quote": "Размер проёма 1200 мм принят по проекту"}
    request = build_critic_request(model_id="m", run_id="run", section="AR", observations={"i1": observation}, sources=[source], window_id="w1",
        reference_section=True)
    assert "images" not in request.body
    helper = runtime._CriticNormImages(NS(get_bind=lambda: custody.engine), NS(run_id="run"), custody.store)
    monkeypatch.setattr(helper, "withheld", lambda: None)  # the member's facts are the unit test's; here the pages are
    state: dict[str, Any] = {}
    imaged_request, imaged = helper.attach(request, state=state, identity="finding_review:b000")
    descriptors = imaged_request.body["images"]
    assert len(descriptors) == 2 and imaged == {corpus.paragraphs[0], corpus.paragraphs[1]}
    assert [item["crop_id"] for item in descriptors] == ["norm." + (corpus.binding_of("blk_0") or ""), "norm." + (corpus.binding_of("blk_1") or "")]
    raws = checked_pngs(imaged_request)  # every limit of the executor's rules, and the digest of every byte string
    assert [hashlib.sha256(raw).hexdigest() for raw in raws] == [item["sha256"] for item in descriptors]
    assert all(_png_size(raw)[0] > 400 for raw in raws)
    assert _task_payload(imaged_request)["images"] == descriptors
    receipt, = state["norm_page_images"]
    assert receipt["status"] == "declared" and len(receipt["images"]) == 2 and receipt["unavailable"] == []
    # the text of the request is untouched by the pages
    assert json.loads(imaged_request.body["messages"][0]["content"]) == json.loads(request.body["messages"][0]["content"])
    # a second request of the same run reuses the renders
    assert len(corpus.renders()) == 2
