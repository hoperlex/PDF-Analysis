"""Selected PNG binding before any direct provider call."""

import hashlib

import pytest

from auditmanager.analysis.public import ModelRequest, ProxyDispatchError
from auditmanager.executors.image_input import checked_png
from auditmanager.storage.public import derive_blob_id

PNG = b"\x89PNG\r\n\x1a\n" + b"saved-crop"
DIGEST = hashlib.sha256(PNG).hexdigest()
DESCRIPTOR = {
    "blob_id": str(derive_blob_id(sha256=DIGEST, size=len(PNG))),
    "portal_block_id": "blk_" + "a" * 32,
    "sha256": DIGEST, "size_bytes": len(PNG), "media_type": "image/png",
}


def request(descriptor=DESCRIPTOR, raw=PNG):
    return ModelRequest("pin", {"messages": [{"role": "user", "content": "read"}],
                                "images": [descriptor]}, image_bytes=raw)


def test_selected_bytes_match_descriptor_and_stay_out_of_repr():
    selected = request()
    assert checked_png(selected) == PNG
    assert "saved-crop" not in repr(selected)
    assert checked_png(ModelRequest("pin", {"messages": []})) is None


@pytest.mark.parametrize("descriptor,raw", [
    (DESCRIPTOR, None), (DESCRIPTOR, PNG + b"x"),
    ({**DESCRIPTOR, "sha256": "0" * 64}, PNG),
    ({**DESCRIPTOR, "media_type": "image/jpeg"}, PNG),
    ({**DESCRIPTOR, "size_bytes": True}, PNG),
    (DESCRIPTOR, b"not-png"),
])
def test_bad_selected_bytes_are_refused_before_dispatch(descriptor, raw):
    with pytest.raises(ProxyDispatchError) as refusal:
        checked_png(request(descriptor, raw))
    assert refusal.value.dispatch_class == "not_sent"
