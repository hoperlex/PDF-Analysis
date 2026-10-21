"""Check supplied text-layer bytes before making unserved W56b windows.

The reference and bytes must be obtained from a run-scoped saved stage and
BlobStore by a future caller. This pure function verifies their agreement;
it cannot prove where either value came from or authorize a provider effect.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Final, Mapping

from auditmanager.analysis.engine.result import ArtifactRef
from auditmanager.analysis.engine.serialization import (
    ARTIFACT_MEDIA_TYPE,
    canonical_bytes,
    sha256_hex,
)
from auditmanager.analysis.ports.artifacts import ROLE_TEXT_LAYER
from auditmanager.analysis.text.chunk_preflight import TextChunk, partition_text_layer
from auditmanager.analysis.text.textlayer import TextLayer, load_text_layer
from auditmanager.shared.errors import DomainError
from auditmanager.shared.identity import IdentityError, VersionUid


_SHA256: Final[re.Pattern[str]] = re.compile(r"[0-9a-f]{64}\Z")
_ROOT_KEYS: Final[frozenset[str]] = frozenset({
    "artifact_role", "artifact_version", "version_uid", "extractor",
    "normalization", "total_char_count", "pages",
})
_EXTRACTOR_KEYS: Final[frozenset[str]] = frozenset({
    "name", "version", "options_sha256",
})
_NORMALIZATION_KEYS: Final[frozenset[str]] = frozenset({"id", "description"})
_PAGE_KEYS: Final[frozenset[str]] = frozenset({
    "page_number", "char_start", "char_end", "text",
})


class SuppliedTextSourceRefused(ValueError):
    """The supplied reference and bytes cannot establish W56b text windows."""


@dataclass(frozen=True, slots=True)
class CheckedTextWindowSource:
    version_uid: str
    text_layer_ref: ArtifactRef
    text_layer: TextLayer
    windows: tuple[TextChunk, ...]


def _document_shape(document: Mapping[str, Any], *, version_uid: str) -> None:
    extractor = document.get("extractor")
    normalization = document.get("normalization")
    pages = document.get("pages")
    if (
        set(document) != _ROOT_KEYS
        or document.get("artifact_role") != ROLE_TEXT_LAYER
        or document.get("artifact_version") != "1.0.0"
        or document.get("version_uid") != version_uid
        or not isinstance(extractor, dict) or set(extractor) != _EXTRACTOR_KEYS
        or not isinstance(normalization, dict)
        or set(normalization) != _NORMALIZATION_KEYS
        or not isinstance(pages, list) or not pages
        or type(document.get("total_char_count")) is not int
        or document["total_char_count"] < 0
    ):
        raise SuppliedTextSourceRefused("text_layer_shape_or_identity_invalid")
    if (
        any(not isinstance(extractor[key], str) or not extractor[key]
            for key in ("name", "version"))
        or not isinstance(extractor["options_sha256"], str)
        or _SHA256.fullmatch(extractor["options_sha256"]) is None
        or any(not isinstance(normalization[key], str) or not normalization[key]
               for key in _NORMALIZATION_KEYS)
    ):
        raise SuppliedTextSourceRefused("text_layer_metadata_invalid")
    for page in pages:
        if (
            not isinstance(page, dict) or set(page) != _PAGE_KEYS
            or any(type(page[key]) is not int for key in (
                "page_number", "char_start", "char_end"
            ))
            or not isinstance(page["text"], str)
        ):
            raise SuppliedTextSourceRefused("text_layer_page_shape_invalid")


def check_supplied_text_layer_bytes(
    *,
    version_uid: str,
    expected_page_count: int,
    text_layer_ref: ArtifactRef,
    supplied_bytes: bytes,
) -> TextLayer:
    """Verify exact Blob bytes and canonical text-layer content without chunking."""
    try:
        VersionUid.parse(version_uid)
    except IdentityError:
        raise SuppliedTextSourceRefused("version_identity_invalid") from None
    if type(expected_page_count) is not int or expected_page_count < 1:
        raise SuppliedTextSourceRefused("page_count_invalid")
    if (
        not isinstance(text_layer_ref, ArtifactRef)
        or text_layer_ref.role != ROLE_TEXT_LAYER
        or text_layer_ref.media_type != ARTIFACT_MEDIA_TYPE
        or type(text_layer_ref.size_bytes) is not int
        or text_layer_ref.size_bytes < 1
        or type(supplied_bytes) is not bytes
        or len(supplied_bytes) != text_layer_ref.size_bytes
        or sha256_hex(supplied_bytes) != text_layer_ref.sha256
    ):
        raise SuppliedTextSourceRefused("supplied_text_bytes_mismatch")
    try:
        document = json.loads(supplied_bytes.decode("utf-8"))
        if not isinstance(document, dict) or canonical_bytes(document) != supplied_bytes:
            raise SuppliedTextSourceRefused("text_layer_not_canonical_json")
    except (UnicodeError, ValueError, TypeError):
        raise SuppliedTextSourceRefused("text_layer_not_canonical_json") from None
    _document_shape(document, version_uid=version_uid)
    try:
        layer = load_text_layer(document)
    except (DomainError, AttributeError, IndexError, KeyError, TypeError, ValueError):
        raise SuppliedTextSourceRefused("text_layer_invalid") from None
    if (
        layer.version_uid != version_uid
        or len(layer.pages) != expected_page_count
        or layer.page_numbers != tuple(range(1, expected_page_count + 1))
    ):
        raise SuppliedTextSourceRefused("text_layer_page_count_or_version_mismatch")
    if layer.total_char_count != document["total_char_count"]:
        raise SuppliedTextSourceRefused("text_layer_char_count_mismatch")
    return layer


def check_supplied_text_window_bytes(
    *,
    version_uid: str,
    expected_page_count: int,
    text_layer_ref: ArtifactRef,
    supplied_bytes: bytes,
    max_chunk_characters: int,
) -> CheckedTextWindowSource:
    """Verify one supplied canonical Blob payload and partition every page.

    ``max_chunk_characters`` is an externally approved *document-text* ceiling.
    This function does not calculate a model's context, spend or output budget.
    """
    layer = check_supplied_text_layer_bytes(
        version_uid=version_uid,
        expected_page_count=expected_page_count,
        text_layer_ref=text_layer_ref,
        supplied_bytes=supplied_bytes,
    )
    windows = partition_text_layer(layer, max_chunk_characters=max_chunk_characters)
    return CheckedTextWindowSource(version_uid, text_layer_ref, layer, windows)
