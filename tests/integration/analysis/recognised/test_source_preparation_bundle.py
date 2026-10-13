"""``source_preparation`` over portal bundles, on the lane's real S3 (`W55B-RECOGNISED-01`).

* ``prepared.recognised_text`` is published for a bundle and absent without one;
* the text-layer-or-block rule (``R-116``, ``P02_SEAMS`` section 4.2): a page with no text
  layer is admitted when a portal block sits on it and refused when none does, and a version
  without a bundle keeps today's refusal;
* the recognised text never reaches ``prepared.text_layer`` (section 4.1, ``R-117``);
* the PDF is opened from a temporary file the stage removes, on success and on failure, and
  the source blob is never read whole into memory;
* refusals are typed, with their ``reason``; the stage is deterministic.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import pytest

from auditmanager.analysis.public import (
    ROLE_PAGE_INVENTORY,
    ROLE_RECOGNISED_TEXT,
    ROLE_SOURCE_DOCUMENT,
    ROLE_TEXT_LAYER,
    StageStatus,
    run_stage,
)
from auditmanager.analysis.stages import source_preparation
from auditmanager.analysis.text import load_text_layer
from auditmanager.shared.errors import DomainError, ErrorCode
from tests.integration.analysis.recognised import recognised_support as support
from tests.integration.analysis.recognised.recognised_support import (
    CORPUS,
    VERSION_UID,
    assert_recognised_text_shape,
    bundle_inputs,
    members,
    stage_inputs,
)

store = support.store

NEW_METRICS = {"recognised_entry_count", "recognised_flagged_entry_count", "pages_without_text_layer"}


def _run(store: Any, inputs: dict[str, Any], **kwargs: Any) -> Any:
    return run_stage(
        "source_preparation", version_uid=VERSION_UID, inputs=inputs, blob_store=store, **kwargs
    )


def _document(store: Any, result: Any, role: str) -> dict[str, Any]:
    return json.loads(store.read(result.artifact(role).blob_id))


# --- the artifact -------------------------------------------------------------------------


def test_a_bundle_publishes_the_recognised_text_beside_the_two_prepared_artifacts(store) -> None:
    bundle = members("ar_baseline_ocr_defects.zip")
    result = _run(store, bundle_inputs(store, bundle))

    assert result.status is StageStatus.SUCCEEDED, result.error
    assert {ref.role for ref in result.artifacts} == {
        ROLE_PAGE_INVENTORY,
        ROLE_TEXT_LAYER,
        ROLE_RECOGNISED_TEXT,
    }
    document = _document(store, result, ROLE_RECOGNISED_TEXT)
    assert_recognised_text_shape(document, version_uid=VERSION_UID, markdown=bundle.markdown, page_count=8)
    assert result.metrics["recognised_entry_count"] == 8
    assert result.metrics["recognised_flagged_entry_count"] == 4
    assert result.metrics["pages_without_text_layer"] == 0


def test_the_baseline_bundle_carries_descriptions_and_no_stamp(store) -> None:
    bundle = members("ar_baseline.zip")
    result = _run(store, bundle_inputs(store, bundle))
    document = _document(store, result, ROLE_RECOGNISED_TEXT)

    kinds = [entry["kind"] for entry in document["entries"]]
    assert kinds.count("recognised_text") == 8 and kinds.count("portal_description") == 2
    stamps = {b["block_id"] for b in bundle.blocks if b["block_type"] == "stamp"}
    assert not stamps & {entry["portal_block_id"] for entry in document["entries"]}


def test_a_version_without_a_bundle_publishes_no_recognised_text_and_no_new_metric(store) -> None:
    pdf = (CORPUS / "ar_baseline.pdf").read_bytes()
    result = _run(store, stage_inputs(store, pdf))

    assert result.status is StageStatus.SUCCEEDED, result.error
    assert {ref.role for ref in result.artifacts} == {ROLE_PAGE_INVENTORY, ROLE_TEXT_LAYER}
    assert not NEW_METRICS & set(result.metrics)
    inventory = _document(store, result, ROLE_PAGE_INVENTORY)
    assert all(page["has_text_layer"] is True for page in inventory["pages"])


# --- never in the text layer --------------------------------------------------------------


def test_the_text_layer_of_a_bundle_is_byte_for_byte_the_text_layer_of_its_bare_pdf(store) -> None:
    bundle = members("ar_baseline_ocr_defects.zip")
    with_bundle = _run(store, bundle_inputs(store, bundle))
    without = _run(store, stage_inputs(store, bundle.pdf))

    bundled_layer = with_bundle.artifact(ROLE_TEXT_LAYER)
    bare_layer = without.artifact(ROLE_TEXT_LAYER)
    assert bundled_layer.sha256 == bare_layer.sha256
    assert store.read(bundled_layer.blob_id) == store.read(bare_layer.blob_id)
    assert with_bundle.artifact(ROLE_PAGE_INVENTORY).sha256 == without.artifact(ROLE_PAGE_INVENTORY).sha256


def test_no_recognised_word_reaches_the_text_layer(store) -> None:
    """The seeded flaws exist only in the recognised text: the layer holds none of them."""
    bundle = members("ar_baseline_ocr_defects.zip")
    result = _run(store, bundle_inputs(store, bundle))
    layer = _document(store, result, ROLE_TEXT_LAYER)
    whole = "".join(page["text"] for page in layer["pages"])
    recognised = _document(store, result, ROLE_RECOGNISED_TEXT)

    seeded = support.manifest_entry("ar_baseline_ocr_defects.zip")["seeded_text_defects"]
    flawed = [d["recognised"] for d in seeded if d["flaggable"]]
    assert all(any(word in e["text"] for e in recognised["entries"]) for word in flawed)
    assert not [word for word in flawed if word in whole]


# --- the text-layer-or-block rule -----------------------------------------------------------


def test_a_textless_page_that_holds_a_portal_block_is_admitted_and_marked(store) -> None:
    bundle = members("image_only_with_block.zip")
    result = _run(store, bundle_inputs(store, bundle))

    assert result.status is StageStatus.SUCCEEDED, result.error
    inventory = _document(store, result, ROLE_PAGE_INVENTORY)
    assert [(p["page_number"], p["has_text_layer"], p["char_count"]) for p in inventory["pages"]] == [
        (1, False, 0),
        (2, False, 0),
    ]
    layer = _document(store, result, ROLE_TEXT_LAYER)
    assert [(p["char_start"], p["char_end"], p["text"]) for p in layer["pages"]] == [
        (0, 0, ""),
        (0, 0, ""),
    ]
    assert layer["total_char_count"] == 0
    loaded = load_text_layer(layer)  # the text-analysis reader still accepts it (section 4.1)
    assert loaded.total_char_count == 0
    recognised = _document(store, result, ROLE_RECOGNISED_TEXT)
    assert [e["page_number"] for e in recognised["entries"]] == [1, 2]
    assert all(e["text"] and e["quote_source"] == "recognised" for e in recognised["entries"])
    assert result.metrics["pages_without_text_layer"] == 2


def _assert_text_layer_refusal(result: Any) -> None:
    assert result.status is StageStatus.FAILED
    assert result.artifacts == ()
    assert result.error is not None
    assert result.error.code is ErrorCode.VALIDATION_FAILED
    assert result.error.details.get("field") == "page_number"
    assert result.error.details.get("constraint") == "every page must carry extractable embedded text"


def test_a_textless_page_with_no_portal_block_is_refused(store) -> None:
    bundle = members("image_only.zip")
    assert bundle.blocks == []
    _assert_text_layer_refusal(_run(store, bundle_inputs(store, bundle)))


def test_a_block_on_another_page_does_not_admit_a_textless_one(store) -> None:
    """Page 2 is textless; a block list holding a block on page 1 only does not admit it."""
    bundle = members("image_only_with_block.zip")
    document = json.loads(bundle.block_list)
    keep = [b for b in document["blocks"] if b["page_index"] == 0]
    assert len(keep) == 1 and len(document["blocks"]) == 2
    document["blocks"] = keep
    dropped = next(
        b["block_id"] for b in json.loads(bundle.block_list)["blocks"] if b["page_index"] == 1
    )
    text = bundle.markdown.decode("utf-8")
    start = text.index("### BLOCK", text.index("## Page 2"))
    assert dropped in text[start:]
    markdown = text[:start].encode("utf-8")

    inputs = stage_inputs(
        store, bundle.pdf, markdown=markdown, block_list=json.dumps(document).encode("utf-8")
    )
    _assert_text_layer_refusal(_run(store, inputs))


def test_a_version_without_a_bundle_keeps_the_refusal(store) -> None:
    pdf = members("image_only_with_block.zip").pdf
    _assert_text_layer_refusal(_run(store, stage_inputs(store, pdf)))
    _assert_text_layer_refusal(
        _run(store, stage_inputs(store, (CORPUS / "negative" / "image_only.pdf").read_bytes()))
    )


# --- refusals of the members ------------------------------------------------------------------


@pytest.mark.parametrize("present", ["markdown", "block_list"])
def test_one_member_without_the_other_is_refused(store, present: str) -> None:
    bundle = members("ar_baseline.zip")
    inputs = stage_inputs(
        store,
        bundle.pdf,
        markdown=bundle.markdown if present == "markdown" else None,
        block_list=bundle.block_list if present == "block_list" else None,
    )
    result = _run(store, inputs)

    assert result.status is StageStatus.FAILED and result.artifacts == ()
    assert result.error.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert result.error.details.get("reason") == "portal_inputs_incomplete"


def test_a_stored_pair_that_disagrees_is_refused_with_its_reason(store) -> None:
    bundle = members("ar_baseline.zip")
    identifier = next(b["block_id"] for b in bundle.blocks if b["block_type"] == "text")
    markdown = bundle.markdown.replace(identifier.encode(), b"blk_" + b"0" * 32)
    result = _run(store, stage_inputs(store, bundle.pdf, markdown=markdown, block_list=bundle.block_list))

    assert result.status is StageStatus.FAILED and result.artifacts == ()
    assert result.error.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert result.error.details.get("reason") == "recognised_markdown_mismatch"


def test_a_crlf_markdown_publishes_the_same_entries_as_its_lf_original(store) -> None:
    bundle = members("ar_baseline.zip")
    crlf = bundle.markdown.replace(b"\n", b"\r\n")
    lf_result = _run(store, bundle_inputs(store, bundle))
    crlf_result = _run(
        store, stage_inputs(store, bundle.pdf, markdown=crlf, block_list=bundle.block_list)
    )
    lf = _document(store, lf_result, ROLE_RECOGNISED_TEXT)
    crlf_document = _document(store, crlf_result, ROLE_RECOGNISED_TEXT)

    assert crlf_document["entries"] == lf["entries"]
    assert crlf_document["results_sha256"] == hashlib.sha256(crlf).hexdigest()


# --- determinism ----------------------------------------------------------------------------


def test_two_runs_publish_the_same_three_blobs(store) -> None:
    bundle = members("ar_baseline_ocr_defects.zip")
    first = _run(store, bundle_inputs(store, bundle))
    second = _run(store, bundle_inputs(store, bundle))
    assert [(r.role, r.blob_id, r.sha256) for r in first.artifacts] == [
        (r.role, r.blob_id, r.sha256) for r in second.artifacts
    ]
    assert {k: v for k, v in first.metrics.items() if k != "duration_ms"} == {
        k: v for k, v in second.metrics.items() if k != "duration_ms"
    }


# --- the temporary file ---------------------------------------------------------------------


def _source_files() -> set[str]:
    return {name for name in os.listdir(tempfile.gettempdir()) if name.startswith("am-source-")}


class _Spy:
    """Wraps ``extract_document``: records what it was given and what that was on disk."""

    def __init__(self, real: Any, *, fail: bool = False) -> None:
        self.real = real
        self.fail = fail
        self.calls: list[tuple[Any, bool, str]] = []

    def __call__(self, source: Any) -> Any:
        path = Path(source) if isinstance(source, (str, os.PathLike)) else None
        exists = path is not None and path.is_file()
        digest = hashlib.sha256(path.read_bytes()).hexdigest() if exists else ""
        self.calls.append((source, exists, digest))
        if self.fail:
            raise DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, reason="spy_failure")
        return self.real(source)


def test_the_pdf_is_opened_from_a_temporary_file_that_is_gone_afterwards(store, monkeypatch) -> None:
    bundle = members("ar_baseline.zip")
    spy = _Spy(source_preparation.extract_document)
    monkeypatch.setattr(source_preparation, "extract_document", spy)
    before = _source_files()

    result = _run(store, bundle_inputs(store, bundle))

    assert result.status is StageStatus.SUCCEEDED, result.error
    assert len(spy.calls) == 1
    source, existed, digest = spy.calls[0]
    assert isinstance(source, (str, os.PathLike)), "the extractor was handed bytes, not a path"
    assert existed and digest == hashlib.sha256(bundle.pdf).hexdigest()
    assert Path(source).parent == Path(tempfile.gettempdir())
    assert not Path(source).exists()
    assert _source_files() == before


def test_the_temporary_file_is_removed_when_the_extraction_fails(store, monkeypatch) -> None:
    spy = _Spy(source_preparation.extract_document, fail=True)
    monkeypatch.setattr(source_preparation, "extract_document", spy)
    before = _source_files()

    result = _run(store, bundle_inputs(store, members("ar_baseline.zip")))

    assert result.status is StageStatus.FAILED
    assert result.error.details.get("reason") == "spy_failure"
    source, existed, _digest = spy.calls[0]
    assert existed and not Path(source).exists()
    assert _source_files() == before


def test_the_temporary_file_is_removed_when_the_document_is_refused(store) -> None:
    before = _source_files()
    _assert_text_layer_refusal(_run(store, bundle_inputs(store, members("image_only.zip"))))
    truncated = (CORPUS / "ar_baseline.pdf").read_bytes()[:5000]
    failed = _run(store, stage_inputs(store, truncated))
    assert failed.status is StageStatus.FAILED
    assert failed.error.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert _source_files() == before


class _StoreThatBreaksMidStream:
    """A real store whose source stream fails after its first chunk."""

    def __init__(self, inner: Any, source_blob: Any) -> None:
        self._inner = inner
        self._source = source_blob

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)

    def open_stream(self, blob_id: Any, **kwargs: Any) -> Any:
        chunks = self._inner.open_stream(blob_id, **kwargs)
        if blob_id != self._source:
            return chunks

        def broken() -> Any:
            yield next(iter(chunks))
            raise OSError("the connection dropped")

        return broken()


class _StoreThatRefusesWholeReads:
    """A real store that refuses ``read()`` of the source document."""

    def __init__(self, inner: Any, source_blob: Any) -> None:
        self._inner = inner
        self._source = source_blob

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)

    def read(self, blob_id: Any, **kwargs: Any) -> bytes:
        assert blob_id != self._source, "the source document was read whole into memory"
        return self._inner.read(blob_id, **kwargs)


def test_a_stream_that_breaks_is_source_unreadable_and_leaves_no_file(store) -> None:
    bundle = members("ar_baseline.zip")
    inputs = bundle_inputs(store, bundle)
    before = _source_files()
    broken = _StoreThatBreaksMidStream(store, inputs[ROLE_SOURCE_DOCUMENT])

    result = _run(broken, inputs)

    assert result.status is StageStatus.FAILED and result.artifacts == ()
    assert result.error.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert result.error.details.get("reason") == "source_unreadable"
    assert _source_files() == before


def test_the_source_document_is_never_read_whole(store) -> None:
    bundle = members("ar_baseline.zip")
    inputs = bundle_inputs(store, bundle)
    guarded = _StoreThatRefusesWholeReads(store, inputs[ROLE_SOURCE_DOCUMENT])

    result = _run(guarded, inputs)

    assert result.status is StageStatus.SUCCEEDED, result.error
    assert {ref.role for ref in result.artifacts} >= {ROLE_RECOGNISED_TEXT}


def test_no_pdfium_document_is_opened_so_no_pdfium_lock_is_needed(store, monkeypatch) -> None:
    """``PDFIUM_LOCK`` guards PDFium; this stage must not reach it at all."""
    import pypdfium2

    def refuse(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("source_preparation opened a PDFium document")

    monkeypatch.setattr(pypdfium2, "PdfDocument", refuse)
    result = _run(store, bundle_inputs(store, members("ar_baseline.zip")))
    assert result.status is StageStatus.SUCCEEDED, result.error
