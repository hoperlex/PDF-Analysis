"""Validate the selected PNGs before a model transport builds its request (ADR-0025 decision 18).

A request carries an **ordered list of up to eight images**. Each one is addressed by a
descriptor, the task-scoped reference the pull channel also uses::

    {"blob_id", "sha256", "size_bytes", "media_type", <identity>}

where ``<identity>`` is exactly one of ``portal_block_id`` (a crop of a portal block, the only
shape before `CMP-EXEC-IMAGES-01`) or ``crop_id`` (an **opaque** crop reference of the
comparison modules: echoed, never parsed, never a path or a display number). The limits are
**8** images, **16 MiB** each and **32 MiB** in all.

This module checks that the supplied bytes really match their descriptors, and that the list
is within the limits and has no repeated identity. It neither opens a Blob nor stores bytes.
A caller builds a request with :func:`attach_images`; the order given is the order the model
sees. The request's checksum covers the descriptors (and so every crop's digest) and never the
bytes, which travel beside the body in ``ModelRequest.images_bytes``.
"""

from __future__ import annotations

import base64
import hashlib
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Final

from auditmanager.analysis.public import ModelRequest, ProxyDispatchError
from auditmanager.shared.errors import ErrorCode
from auditmanager.storage.public import derive_blob_id

__all__ = [
    "MAX_IMAGES",
    "MAX_IMAGE_BYTES",
    "MAX_TOTAL_IMAGE_BYTES",
    "CropImage",
    "ImageLoad",
    "ImageReferenceError",
    "add_anthropic_images",
    "add_openai_images",
    "attach_images",
    "checked_descriptors",
    "checked_png",
    "checked_pngs",
    "crop_descriptor",
    "image_load",
]

#: At most this many images in one request (the contract's ``ClaimedExecutorTask.images`` bound).
MAX_IMAGES: Final[int] = 8
MAX_IMAGE_BYTES: Final[int] = 16 << 20
#: All the images of one request together.
MAX_TOTAL_IMAGE_BYTES: Final[int] = 32 << 20
_PNG_SIGNATURE: Final[bytes] = b"\x89PNG\r\n\x1a\n"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_BLOCK = re.compile(r"blk_[0-9a-f]{32}\Z")
#: The contract's pattern of ``RunnerImage.crop_id``.
_CROP = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
_COMMON: Final[frozenset[str]] = frozenset({"blob_id", "sha256", "size_bytes", "media_type"})
_BY_BLOCK: Final[frozenset[str]] = _COMMON | {"portal_block_id"}
_BY_CROP: Final[frozenset[str]] = _COMMON | {"crop_id"}


class ImageReferenceError(ValueError):
    """A descriptor list outside the rules. ``reason`` is a fixed word, never a value."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True, slots=True)
class CropImage:
    """One crop a caller attaches: its opaque reference and its PNG bytes."""

    crop_id: str
    data: bytes = field(repr=False)


@dataclass(frozen=True, slots=True)
class ImageLoad:
    """What an estimate counts for the images of one request: how many, and how many bytes."""

    count: int
    total_bytes: int


def _invalid(reason: str = "mismatch") -> ProxyDispatchError:
    return ProxyDispatchError(
        ErrorCode.ANALYSIS_INPUT_INVALID, dispatch_class="not_sent", retry_safe=False,
        message=f"the selected images do not match their saved crop references ({reason})",
    )


def checked_descriptors(images: object) -> tuple[Mapping[str, Any], ...]:
    """The descriptors of a request or a task, or :class:`ImageReferenceError`.

    No bytes are involved: this is what the pull channel writes into a task and what an estimate
    counts. The rules: a list of at most :data:`MAX_IMAGES`; each descriptor has exactly the four
    common members and exactly one identity (``portal_block_id`` or ``crop_id``); a PNG media
    type; a size of 1 to :data:`MAX_IMAGE_BYTES`; the blob id derived from the digest and size;
    the sizes together at most :data:`MAX_TOTAL_IMAGE_BYTES`; no identity twice.
    """
    if not isinstance(images, (list, tuple)):
        raise ImageReferenceError("not_a_list")
    if len(images) > MAX_IMAGES:
        raise ImageReferenceError("too_many_images")
    total = 0
    identities: set[tuple[str, str]] = set()
    for descriptor in images:
        if not isinstance(descriptor, Mapping):
            raise ImageReferenceError("bad_descriptor")
        keys = set(descriptor)
        if keys == _BY_BLOCK:
            kind, pattern = "portal_block_id", _BLOCK
        elif keys == _BY_CROP:
            kind, pattern = "crop_id", _CROP
        else:
            raise ImageReferenceError("bad_descriptor")
        identity, digest, size = descriptor[kind], descriptor["sha256"], descriptor["size_bytes"]
        if (not isinstance(identity, str) or pattern.fullmatch(identity) is None
                or not isinstance(digest, str) or _SHA256.fullmatch(digest) is None
                or not isinstance(size, int) or isinstance(size, bool)
                or descriptor["media_type"] != "image/png"):
            raise ImageReferenceError("bad_descriptor")
        if not 1 <= size <= MAX_IMAGE_BYTES:
            raise ImageReferenceError("image_too_large")
        if descriptor["blob_id"] != str(derive_blob_id(sha256=digest, size=size)):
            raise ImageReferenceError("bad_descriptor")
        if (kind, identity) in identities:
            raise ImageReferenceError("duplicate_identity")
        identities.add((kind, identity))
        total += size
    if total > MAX_TOTAL_IMAGE_BYTES:
        raise ImageReferenceError("total_too_large")
    return tuple(images)


def image_load(request: ModelRequest) -> ImageLoad:
    """The number of images and the image bytes of a request, from its descriptors.

    The estimate of a model call counts both (decision 18); a request with no image is
    ``ImageLoad(0, 0)``. Refuses, as :func:`checked_descriptors` does, a list outside the rules.
    """
    descriptors = checked_descriptors(request.body.get("images", ()))
    return ImageLoad(len(descriptors), sum(item["size_bytes"] for item in descriptors))


def checked_pngs(request: ModelRequest) -> tuple[bytes, ...]:
    """Return the verified bytes in order, or refuse before a key, prompt or image is sent.

    ``()`` for a request with no image. The descriptors must pass :func:`checked_descriptors`;
    there must be exactly one byte string per descriptor, each of the described size and digest
    and starting with the PNG signature. ``image_bytes`` (one) and ``images_bytes`` (a list) are
    exclusive.
    """
    try:
        descriptors = checked_descriptors(request.body.get("images", ()))
    except ImageReferenceError as refusal:
        raise _invalid(refusal.reason) from None
    raws: Sequence[object] = request.images_bytes
    if request.image_bytes is not None:
        if raws:
            raise _invalid("both_forms")
        raws = (request.image_bytes,)
    if len(descriptors) != len(raws):
        raise _invalid("count_mismatch")
    for descriptor, raw in zip(descriptors, raws):
        if (not isinstance(raw, bytes) or len(raw) != descriptor["size_bytes"]
                or not raw.startswith(_PNG_SIGNATURE)
                or hashlib.sha256(raw).hexdigest() != descriptor["sha256"]):
            raise _invalid("bytes_mismatch")
    return tuple(raws)  # type: ignore[arg-type]


def checked_png(request: ModelRequest) -> bytes | None:
    """The one-image form: ``None`` without an image, the bytes of exactly one, a refusal of more."""
    raws = checked_pngs(request)
    if len(raws) > 1:
        raise _invalid("more_than_one")
    return raws[0] if raws else None


def crop_descriptor(crop: CropImage) -> dict[str, Any]:
    """The descriptor of one crop: its digest, size and derived blob id with its opaque reference."""
    digest = hashlib.sha256(crop.data).hexdigest()
    return {
        "blob_id": str(derive_blob_id(sha256=digest, size=len(crop.data))),
        "crop_id": crop.crop_id, "sha256": digest, "size_bytes": len(crop.data),
        "media_type": "image/png",
    }


def attach_images(request: ModelRequest, crops: Sequence[CropImage]) -> ModelRequest:
    """A copy of ``request`` that carries ``crops`` in order, checked against every limit.

    This is how a caller builds a multi-image request. The body gains ``images`` (one
    descriptor per crop) and the bytes go to ``images_bytes``; the checksum therefore binds every
    crop's digest and its place in the list. A request that already carries an image is refused
    rather than overwritten. No crops returns the request unchanged. Raises
    :class:`~auditmanager.analysis.public.ProxyDispatchError` (``not_sent``) for a list outside
    the rules.
    """
    if not crops:
        return request
    if request.body.get("images") or request.image_bytes is not None or request.images_bytes:
        raise _invalid("already_has_images")
    built = ModelRequest(
        model_id=request.model_id,
        body={**request.body, "images": [crop_descriptor(crop) for crop in crops]},
        idempotency_scope=request.idempotency_scope,
        images_bytes=tuple(crop.data for crop in crops),
    )
    checked_pngs(built)
    return built


def png_data_url(raw: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")


def _with_blocks(body: dict, blocks: list[dict]) -> dict:
    """Append ``blocks`` to the content of the last user message, in order."""
    messages = [dict(item) for item in body.get("messages", ())]
    for message in reversed(messages):
        if message.get("role") == "user":
            content = message.get("content")
            if isinstance(content, str):
                existing = [{"type": "text", "text": content}]
            elif isinstance(content, list):
                existing = list(content)
            else:
                raise _invalid("no_user_content")
            message["content"] = existing + blocks
            body["messages"] = messages
            return body
    raise _invalid("no_user_message")


def add_anthropic_images(body: dict, raws: Sequence[bytes]) -> dict:
    """Append one Anthropic image block per PNG to the last user message, in order."""
    return _with_blocks(body, [{
        "type": "image", "source": {"type": "base64", "media_type": "image/png",
                                   "data": base64.b64encode(raw).decode("ascii")},
    } for raw in raws])


def add_openai_images(body: dict, raws: Sequence[bytes]) -> dict:
    """Append one OpenAI Chat image_url block per PNG to the last user message, in order."""
    return _with_blocks(body, [
        {"type": "image_url", "image_url": {"url": png_data_url(raw)}} for raw in raws])
