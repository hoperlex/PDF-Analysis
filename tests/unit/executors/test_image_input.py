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


# -- several images, `CMP-EXEC-IMAGES-01` (ADR-0025 decision 18) --------------------------------

from auditmanager.executors.image_input import (  # noqa: E402
    MAX_IMAGE_BYTES,
    MAX_IMAGES,
    MAX_TOTAL_IMAGE_BYTES,
    CropImage,
    ImageReferenceError,
    attach_images,
    checked_descriptors,
    checked_pngs,
    image_load,
)
from tests.unit.executors.crop_support import crop, descriptor, fake_descriptor, png  # noqa: E402

BASE = ModelRequest("pin", {"messages": [{"role": "user", "content": "compare"}]})


def test_the_limits_are_those_of_the_decision() -> None:
    assert (MAX_IMAGES, MAX_IMAGE_BYTES, MAX_TOTAL_IMAGE_BYTES) == (8, 16 << 20, 32 << 20)


def test_attach_images_keeps_the_order_and_every_byte() -> None:
    crops = [crop(label) for label in "abc"]
    built = attach_images(BASE, crops)
    assert [item["crop_id"] for item in built.body["images"]] == ["crop-a", "crop-b", "crop-c"]
    assert checked_pngs(built) == tuple(item.data for item in crops)
    assert BASE.body == {"messages": [{"role": "user", "content": "compare"}]}, "the caller's request is not changed"
    assert "PNG" not in repr(built) and "images_bytes" not in repr(built), "bytes stay out of the repr"


def test_eight_images_are_accepted_and_a_ninth_is_refused() -> None:
    assert len(checked_pngs(attach_images(BASE, [crop(str(i)) for i in range(8)]))) == 8
    with pytest.raises(ProxyDispatchError) as refusal:
        attach_images(BASE, [crop(str(i)) for i in range(9)])
    assert refusal.value.dispatch_class == "not_sent" and "too_many_images" in str(refusal.value)


def test_the_order_and_every_crop_are_bound_by_the_request_checksum() -> None:
    first = attach_images(BASE, [crop("a"), crop("b")])
    assert attach_images(BASE, [crop("a"), crop("b")]).request_sha256 == first.request_sha256
    assert attach_images(BASE, [crop("b"), crop("a")]).request_sha256 != first.request_sha256
    assert attach_images(BASE, [crop("a"), crop("c")]).request_sha256 != first.request_sha256
    assert attach_images(BASE, [crop("a"), CropImage("crop-b", png("b", pad=1))]).request_sha256 \
        != first.request_sha256
    assert attach_images(BASE, [crop("a"), CropImage("other-b", png("b"))]).request_sha256 \
        != first.request_sha256


def test_no_crop_leaves_the_request_unchanged_and_a_second_attachment_is_refused() -> None:
    assert attach_images(BASE, []) is BASE
    with pytest.raises(ProxyDispatchError):
        attach_images(attach_images(BASE, [crop("a")]), [crop("b")])
    with pytest.raises(ProxyDispatchError):
        attach_images(request(), [crop("b")])


def test_image_sizes_are_checked_per_image_and_in_all() -> None:
    at_the_limit = fake_descriptor(0, MAX_IMAGE_BYTES)
    assert checked_descriptors([at_the_limit, fake_descriptor(1, MAX_IMAGE_BYTES)])
    with pytest.raises(ImageReferenceError, match="image_too_large"):
        checked_descriptors([fake_descriptor(0, MAX_IMAGE_BYTES + 1)])
    with pytest.raises(ImageReferenceError, match="image_too_large"):
        checked_descriptors([fake_descriptor(0, 0)])
    third = [fake_descriptor(index, 12 << 20) for index in range(3)]
    with pytest.raises(ImageReferenceError, match="total_too_large"):
        checked_descriptors(third)
    assert checked_descriptors(third[:2]), "24 MiB in all is inside the 32 MiB"
    assert checked_descriptors([fake_descriptor(index, 8 << 20) for index in range(4)]), "exactly 32 MiB"
    with pytest.raises(ImageReferenceError, match="total_too_large"):
        checked_descriptors([fake_descriptor(index, 8 << 20) for index in range(4)]
                            + [fake_descriptor(4, 1)])


def test_a_descriptor_has_exactly_one_identity_of_the_right_shape() -> None:
    raw = png("x")
    both = descriptor(raw, crop_id="crop-x", portal_block_id="blk_" + "a" * 32)
    neither = descriptor(raw)
    extra = {**descriptor(raw, crop_id="crop-x"), "page": 1}
    for bad in (both, neither, extra, descriptor(raw, crop_id=""), descriptor(raw, crop_id="-lead"),
                descriptor(raw, crop_id="has space"), descriptor(raw, crop_id="a" * 129),
                descriptor(raw, portal_block_id="blk_nope"), descriptor(raw, crop_id=7)):
        with pytest.raises(ImageReferenceError, match="bad_descriptor"):
            checked_descriptors([bad])
    assert checked_descriptors([descriptor(raw, crop_id="a" * 128)])
    assert checked_descriptors([descriptor(raw, crop_id="A1._:-b")])
    assert checked_descriptors([descriptor(raw, portal_block_id="blk_" + "a" * 32)])


def test_an_identity_is_not_repeated_but_the_same_bytes_may_be_two_crops() -> None:
    raw = png("blank")
    with pytest.raises(ImageReferenceError, match="duplicate_identity"):
        checked_descriptors([descriptor(raw, crop_id="crop-1"), descriptor(png("other"), crop_id="crop-1")])
    twice = [descriptor(raw, crop_id="crop-a-1"), descriptor(raw, crop_id="crop-b-1")]
    assert twice[0]["blob_id"] == twice[1]["blob_id"]
    assert checked_descriptors(twice), "two blank regions are the same Blob under two references"
    built = attach_images(BASE, [CropImage("crop-a-1", raw), CropImage("crop-b-1", raw)])
    assert checked_pngs(built) == (raw, raw)


def test_the_bytes_must_match_the_descriptors_one_for_one_and_in_order() -> None:
    built = attach_images(BASE, [crop("a"), crop("b")])
    swapped = ModelRequest("pin", built.body, images_bytes=tuple(reversed(built.images_bytes)))
    short = ModelRequest("pin", built.body, images_bytes=built.images_bytes[:1])
    extra = ModelRequest("pin", built.body, images_bytes=(*built.images_bytes, png("c")))
    both = ModelRequest("pin", built.body, images_bytes=built.images_bytes, image_bytes=png("a"))
    bare = ModelRequest("pin", built.body)
    not_png = ModelRequest("pin", built.body, images_bytes=(png("a"), b"x" * len(png("b"))))
    for bad in (swapped, short, extra, both, bare, not_png):
        with pytest.raises(ProxyDispatchError) as refusal:
            checked_pngs(bad)
        assert refusal.value.dispatch_class == "not_sent" and refusal.value.retry_safe is False
    assert checked_pngs(ModelRequest("pin", {"images": []})) == ()
    with pytest.raises(ProxyDispatchError):
        checked_pngs(ModelRequest("pin", {}, images_bytes=(png("a"),)))


def test_the_one_image_form_still_refuses_a_list_and_serves_a_single_portal_block_crop() -> None:
    assert checked_png(request()) == PNG
    with pytest.raises(ProxyDispatchError):
        checked_png(attach_images(BASE, [crop("a"), crop("b")]))
    assert checked_png(attach_images(BASE, [crop("a")])) == png("a")


def test_the_estimate_counts_images_and_image_bytes() -> None:
    built = attach_images(BASE, [crop("a"), crop("b", pad=10)])
    load = image_load(built)
    assert (load.count, load.total_bytes) == (2, len(png("a")) + len(png("b", pad=10)))
    assert (image_load(BASE).count, image_load(BASE).total_bytes) == (0, 0)
    assert (image_load(request()).count, image_load(request()).total_bytes) == (1, len(PNG))
    with pytest.raises(ImageReferenceError):
        image_load(ModelRequest("pin", {"images": [fake_descriptor(0, MAX_IMAGE_BYTES + 1)]}))
