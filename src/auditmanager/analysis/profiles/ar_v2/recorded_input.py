"""Bind stored PDF and marked OCR artifacts to one offline AR v2 request.

This pure boundary accepts artifact documents after a trusted caller has read
their Blobs. It compares the bytes' read digests with persisted references and
retains the PDF page offsets and source references for later provenance. It
does not load a version row, read a Blob, or execute a model call.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from auditmanager.analysis.engine.result import ArtifactRef
from auditmanager.analysis.engine.serialization import (
    ARTIFACT_MEDIA_TYPE,
    canonical_bytes,
    sha256_hex,
)
from auditmanager.analysis.profiles.ar_shared.recognised_context import (
    RecognisedContext,
    select_context,
)
from auditmanager.analysis.profiles.ar_v2.recorded_request import (
    RecordedGenerationSettings,
    build_recorded_request,
)
from auditmanager.analysis.text.adapter import ModelRequest
from auditmanager.analysis.text.textlayer import TextLayer, load_text_layer
from auditmanager.shared.identity import AnalysisProfileId, PromptBundleId


class RecordedInputError(ValueError):
    """The persisted source identities or bytes cannot form this request."""


_TEXT_ROLE = "prepared.text_layer"
_OCR_ROLE = "prepared.recognised_text"


@dataclass(frozen=True, slots=True)
class PdfPageSource:
    """One page's raw PDF text span in the verified text-layer artifact."""

    page_number: int
    char_start: int
    char_end: int


@dataclass(frozen=True, slots=True)
class RecordedV2Input:
    """The request plus exact source references and non-citable OCR context."""

    version_uid: str
    text_layer: TextLayer
    text_layer_ref: ArtifactRef
    recognised_ref: ArtifactRef | None
    page_sources: tuple[PdfPageSource, ...]
    textless_pages: tuple[int, ...] | None
    recognised_context: tuple[RecognisedContext, ...]
    request: ModelRequest
    source_binding_sha256: str

    @property
    def request_sha256(self) -> str:
        return self.request.request_sha256


def _verify_artifact(
    document: Mapping[str, Any], reference: ArtifactRef, read_sha256: str,
    *, role: str, version_uid: str,
) -> None:
    """Prove the supplied decoded document is the referenced read byte string.

    The engine publishes canonical JSON. Requiring its canonical bytes to match
    the actual read digest prevents a caller from joining a different decoded
    document to a valid read digest. The caller must source ``reference`` from
    the persisted stage and ``read_sha256`` from ``read_artifact``.
    """
    if not isinstance(document, dict) or not isinstance(reference, ArtifactRef):
        raise RecordedInputError("invalid_artifact_binding")
    if (
        reference.role != role
        or reference.media_type != ARTIFACT_MEDIA_TYPE
        or document.get("artifact_role") != role
        or document.get("version_uid") != version_uid
    ):
        raise RecordedInputError("artifact_identity_mismatch")
    try:
        payload = canonical_bytes(document)
    except (TypeError, ValueError):
        raise RecordedInputError("invalid_artifact_document") from None
    if (
        read_sha256 != reference.sha256
        or sha256_hex(payload) != reference.sha256
        or len(payload) != reference.size_bytes
    ):
        raise RecordedInputError("artifact_digest_mismatch")


def prepare_recorded_v2_input(
    *,
    version_uid: str,
    textless_pages: tuple[int, ...] | None,
    text_layer_document: Mapping[str, Any],
    text_layer_ref: ArtifactRef,
    text_layer_read_sha256: str,
    recognised_document: Mapping[str, Any] | None,
    recognised_ref: ArtifactRef | None,
    recognised_read_sha256: str | None,
    analysis_profile_id: AnalysisProfileId | str,
    prompt_bundle_id: PromptBundleId | str,
    fixture_model_id: str,
    settings: RecordedGenerationSettings,
) -> RecordedV2Input:
    """Build a request only from the persisted version's verified page sources.

    OCR stays separate from PDF text. Multiple TEXT blocks on one page are
    refused until a reviewed lossless representation for them is defined.
    """
    if not isinstance(version_uid, str) or not version_uid:
        raise RecordedInputError("invalid_version_identity")
    _verify_artifact(
        text_layer_document, text_layer_ref, text_layer_read_sha256,
        role=_TEXT_ROLE, version_uid=version_uid,
    )
    if any(
        item is not None
        for item in (recognised_document, recognised_ref, recognised_read_sha256)
    ):
        if (
            recognised_document is None
            or recognised_ref is None
            or recognised_read_sha256 is None
        ):
            raise RecordedInputError("incomplete_recognised_binding")
        _verify_artifact(
            recognised_document, recognised_ref, recognised_read_sha256,
            role=_OCR_ROLE, version_uid=version_uid,
        )
    try:
        text_layer = load_text_layer(text_layer_document)
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        raise RecordedInputError("invalid_text_layer_artifact") from None
    if text_layer.version_uid != version_uid:
        raise RecordedInputError("text_layer_version_mismatch")
    recognised_context = select_context(
        recognised_document, version_uid=version_uid, textless_pages=textless_pages,
    )
    if textless_pages is not None and not set(textless_pages).issubset(text_layer.page_numbers):
        raise RecordedInputError("textless_page_absent_from_pdf")
    pages_with_ocr = [item.page_number for item in recognised_context]
    if len(pages_with_ocr) != len(set(pages_with_ocr)):
        raise RecordedInputError("multiple_text_blocks_for_page")
    request = build_recorded_request(
        analysis_profile_id=analysis_profile_id,
        prompt_bundle_id=prompt_bundle_id,
        fixture_model_id=fixture_model_id,
        settings=settings,
        text_layer=text_layer,
        recognised_context=recognised_context,
    )
    source_binding_sha256 = sha256_hex(canonical_bytes({
        "version_uid": version_uid,
        "text_layer_ref": text_layer_ref.to_document(),
        "recognised_ref": None if recognised_ref is None else recognised_ref.to_document(),
        "textless_pages": textless_pages,
        "request_sha256": request.request_sha256,
    }))
    return RecordedV2Input(
        version_uid=version_uid,
        text_layer=text_layer,
        text_layer_ref=text_layer_ref,
        recognised_ref=recognised_ref,
        page_sources=tuple(
            PdfPageSource(page.page_number, page.char_start, page.char_end)
            for page in text_layer.pages
        ),
        textless_pages=textless_pages,
        recognised_context=recognised_context,
        request=request,
        source_binding_sha256=source_binding_sha256,
    )


__all__ = [
    "PdfPageSource", "RecordedInputError", "RecordedV2Input", "prepare_recorded_v2_input",
]
