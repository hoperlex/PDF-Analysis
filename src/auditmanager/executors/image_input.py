"""Validate one selected PNG before a direct model transport builds its request.

The image descriptor is the same task-scoped reference used by the pull channel.
Only a future image stage may select a crop; this module checks that its supplied
bytes really match the descriptor. It neither opens a Blob nor stores image bytes.
"""

from __future__ import annotations

import base64
import hashlib
import re
from collections.abc import Mapping

from auditmanager.analysis.public import ModelRequest, ProxyDispatchError
from auditmanager.shared.errors import ErrorCode
from auditmanager.storage.public import derive_blob_id

MAX_IMAGE_BYTES = 16 << 20
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_BLOCK = re.compile(r"blk_[0-9a-f]{32}\Z")


def _invalid() -> ProxyDispatchError:
    return ProxyDispatchError(
        ErrorCode.ANALYSIS_INPUT_INVALID, dispatch_class="not_sent", retry_safe=False,
        message="the selected image bytes do not match the saved crop reference",
    )


def checked_png(request: ModelRequest) -> bytes | None:
    """Return verified bytes, or refuse before a key, prompt or image is sent."""
    images = request.body.get("images", ())
    if not isinstance(images, (list, tuple)):
        raise _invalid()
    if len(images) == 0 and request.image_bytes is None:
        return None
    if len(images) != 1:
        raise _invalid()
    descriptor = images[0]
    raw = request.image_bytes
    if not isinstance(descriptor, Mapping) or not isinstance(raw, bytes):
        raise _invalid()
    digest = descriptor.get("sha256")
    size = descriptor.get("size_bytes")
    if (set(descriptor) != {"blob_id", "portal_block_id", "sha256", "size_bytes", "media_type"}
            or not isinstance(digest, str) or _SHA256.fullmatch(digest) is None
            or not isinstance(size, int) or isinstance(size, bool)
            or not 1 <= size <= MAX_IMAGE_BYTES
            or descriptor.get("media_type") != "image/png"
            or not isinstance(descriptor.get("portal_block_id"), str)
            or _BLOCK.fullmatch(descriptor["portal_block_id"]) is None
            or descriptor.get("blob_id") != str(derive_blob_id(sha256=digest, size=size))
            or len(raw) != size or not raw.startswith(_PNG_SIGNATURE)
            or hashlib.sha256(raw).hexdigest() != digest):
        raise _invalid()
    return raw


def png_data_url(raw: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")


def add_anthropic_image(body: dict, raw: bytes) -> dict:
    """Append an Anthropic image block to the last user message."""
    messages = [dict(item) for item in body.get("messages", ())]
    for message in reversed(messages):
        if message.get("role") == "user":
            content = message.get("content")
            if isinstance(content, str):
                blocks = [{"type": "text", "text": content}]
            elif isinstance(content, list):
                blocks = list(content)
            else:
                raise _invalid()
            blocks.append({
                "type": "image", "source": {"type": "base64", "media_type": "image/png",
                                           "data": base64.b64encode(raw).decode("ascii")},
            })
            message["content"] = blocks
            body["messages"] = messages
            return body
    raise _invalid()


def add_openai_image(body: dict, raw: bytes) -> dict:
    """Append an OpenAI Chat image_url block to the last user message."""
    messages = [dict(item) for item in body.get("messages", ())]
    for message in reversed(messages):
        if message.get("role") == "user":
            content = message.get("content")
            if isinstance(content, str):
                blocks = [{"type": "text", "text": content}]
            elif isinstance(content, list):
                blocks = list(content)
            else:
                raise _invalid()
            blocks.append({"type": "image_url", "image_url": {"url": png_data_url(raw)}})
            message["content"] = blocks
            body["messages"] = messages
            return body
    raise _invalid()
