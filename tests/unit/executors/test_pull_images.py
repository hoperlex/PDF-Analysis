"""The pull image reference and the token-scoped read, without a model or S3."""

from __future__ import annotations

import hashlib
from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from auditmanager.analysis.public import ModelRequest
from auditmanager.bootstrap.runner import RunnerAdapter
from auditmanager.executors.pull import _task_payload
from auditmanager.executors.runner import RunnerPrincipal, claimed_image
from auditmanager.executors import public as executor_public
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import derive_blob_id


PNG = b"\x89PNG\r\n\x1a\n" + b"small synthetic payload"
DIGEST = hashlib.sha256(PNG).hexdigest()
IMAGE = {
    "blob_id": str(derive_blob_id(sha256=DIGEST, size=len(PNG))),
    "portal_block_id": "blk_" + "a" * 32,
    "sha256": DIGEST, "size_bytes": len(PNG), "media_type": "image/png",
}


def _request(images: object = ()) -> ModelRequest:
    return ModelRequest(model_id="gpt-6-sol", body={
        "system": "Inspect one drawing crop.",
        "messages": [{"role": "user", "content": "Block blk_" + "a" * 32}],
        "output_config": {"format": {"schema": {"type": "object"}}},
        "images": images,
    })


def test_one_checked_blob_reference_enters_the_task_without_copying_png_bytes() -> None:
    payload = _task_payload(_request([IMAGE]))
    assert payload["images"] == [IMAGE]
    assert PNG not in repr(payload).encode()
    assert "images" not in _task_payload(_request())


@pytest.mark.parametrize("change", [
    {"sha256": "0" * 64}, {"size_bytes": 0}, {"size_bytes": 16 * 1024 * 1024 + 1},
    {"media_type": "application/pdf"}, {"portal_block_id": "../wrong"},
])
def test_invalid_or_oversized_reference_never_creates_a_task(change: dict) -> None:
    with pytest.raises(DomainError):
        _task_payload(_request([{**IMAGE, **change}]))


class FakeRepository:
    def __init__(self) -> None:
        self.task = SimpleNamespace(connection_id="exc_a", state="claimed",
                                    past_deadline=False, claimed_by_token_id="ern_a")
        self.live = True

    def get_task(self, _session, _task_id, *, lock):
        assert lock
        return self.task

    def live_claim_and_attempt(self, _session, _task_id, _token_id):
        return self.live

    def payload_of(self, _session, _task_id):
        return {"images": [IMAGE]}


def test_only_the_current_claimant_can_name_the_image() -> None:
    repository = FakeRepository()
    owner = RunnerPrincipal(token_id="ern_a", connection_id="exc_a")
    assert claimed_image(None, owner, "ext_a", IMAGE["blob_id"], repository) == IMAGE
    with pytest.raises(DomainError):
        claimed_image(None, RunnerPrincipal("ern_b", "exc_b"), "ext_a", IMAGE["blob_id"], repository)
    with pytest.raises(DomainError):
        claimed_image(None, owner, "ext_a", "blob_not_the_image", repository)
    repository.live = False
    with pytest.raises(DomainError):
        claimed_image(None, owner, "ext_a", IMAGE["blob_id"], repository)


class FakeBlobStore:
    def __init__(self, content: bytes = PNG) -> None:
        self.content = content
        self.reads = 0

    def inspect(self, _blob_id):
        return SimpleNamespace(size=len(PNG), sha256=DIGEST, media_type="image/png")

    def open_stream(self, _blob_id, *, expected_sha256, expected_size):
        assert (expected_sha256, expected_size) == (DIGEST, len(PNG))
        self.reads += 1
        yield self.content


def test_server_rechecks_claim_after_blob_read_and_refuses_changed_bytes(monkeypatch) -> None:
    checks = []

    def authorize(_session, _principal, _task_id, _blob_id):
        checks.append(True)
        return IMAGE

    monkeypatch.setattr(executor_public, "claimed_image", authorize)
    store = FakeBlobStore()
    adapter = RunnerAdapter(lambda: nullcontext(None), blob_store=store)
    runner = SimpleNamespace(token_id="ern_a", connection_id="exc_a")
    assert adapter.read_image(runner=runner, task_id="ext_a", blob_id=IMAGE["blob_id"]) == PNG
    assert len(checks) == 2 and store.reads == 1
    store.content = PNG + b"changed"
    with pytest.raises(DomainError):
        adapter.read_image(runner=runner, task_id="ext_a", blob_id=IMAGE["blob_id"])


def test_server_does_not_release_bytes_if_claim_ends_during_blob_read(monkeypatch) -> None:
    checks = 0

    def authorize(_session, _principal, _task_id, _blob_id):
        nonlocal checks
        checks += 1
        if checks == 2:
            raise DomainError(ErrorCode.CONFLICT, conflict_reason="claim_lost")
        return IMAGE

    monkeypatch.setattr(executor_public, "claimed_image", authorize)
    store = FakeBlobStore()
    adapter = RunnerAdapter(lambda: nullcontext(None), blob_store=store)
    runner = SimpleNamespace(token_id="ern_a", connection_id="exc_a")
    with pytest.raises(DomainError):
        adapter.read_image(runner=runner, task_id="ext_a", blob_id=IMAGE["blob_id"])
    assert checks == 2 and store.reads == 1


# -- several images and opaque crop references, `CMP-EXEC-IMAGES-01` ------------------------------

from auditmanager.executors.image_input import attach_images  # noqa: E402
from tests.unit.executors.crop_support import crop, descriptor, fake_descriptor, png  # noqa: E402


def test_up_to_eight_crop_references_enter_the_task_in_order_without_their_bytes() -> None:
    crops = [crop(str(index)) for index in range(8)]
    built = attach_images(_request(), crops)
    payload = _task_payload(built)
    assert [item["crop_id"] for item in payload["images"]] == [item.crop_id for item in crops]
    assert [item["blob_id"] for item in payload["images"]] == [
        descriptor(item.data, crop_id=item.crop_id)["blob_id"] for item in crops]
    assert all(item.data not in repr(payload).encode() for item in crops)
    assert all("portal_block_id" not in item for item in payload["images"])


def test_a_portal_block_crop_and_opaque_crops_may_not_be_mixed_with_a_second_identity() -> None:
    mixed = [{**descriptor(png("m"), crop_id="crop-m"), "portal_block_id": "blk_" + "a" * 32}]
    with pytest.raises(DomainError):
        _task_payload(_request(mixed))
    assert _task_payload(_request([IMAGE, descriptor(png("m"), crop_id="crop-m")]))["images"][0] == IMAGE


@pytest.mark.parametrize("images", [
    [fake_descriptor(index, 1) for index in range(9)],                       # a ninth image
    [fake_descriptor(index, 12 << 20) for index in range(3)],                # 36 MiB in all
    [fake_descriptor(0, 16 * 1024 * 1024 + 1)],                              # one above 16 MiB
    [descriptor(png("d"), crop_id="crop-d"), descriptor(png("e"), crop_id="crop-d")],  # a crop twice
    [{**descriptor(png("f"), crop_id="crop-f"), "blob_id": "blob_" + "0" * 26}],        # blob id not derived
    "not-a-list",
])
def test_a_list_outside_the_limits_never_creates_a_task(images: object) -> None:
    with pytest.raises(DomainError) as refused:
        _task_payload(_request(images))
    assert refused.value.code is ErrorCode.ANALYSIS_INPUT_INVALID


class CropRepository(FakeRepository):
    """The held task carries three crops, two with the same bytes."""

    def __init__(self) -> None:
        super().__init__()
        same = png("blank")
        self.images = [descriptor(same, crop_id="crop-a-1"), descriptor(png("x"), crop_id="crop-a-2"),
                       descriptor(same, crop_id="crop-b-1")]

    def payload_of(self, _session, _task_id):
        return {"images": self.images}


def test_a_crop_is_named_by_its_blob_id_exactly_as_a_portal_block_crop_is() -> None:
    repository = CropRepository()
    owner = RunnerPrincipal(token_id="ern_a", connection_id="exc_a")
    found = claimed_image(None, owner, "ext_a", repository.images[1]["blob_id"], repository)
    assert found["crop_id"] == "crop-a-2"
    assert claimed_image(None, owner, "ext_a", repository.images[2]["blob_id"], repository)["sha256"] \
        == repository.images[0]["sha256"], "the same bytes are one Blob under two references"
    with pytest.raises(DomainError):
        claimed_image(None, owner, "ext_a", IMAGE["blob_id"], repository)
    with pytest.raises(DomainError):
        claimed_image(None, RunnerPrincipal("ern_b", "exc_b"), "ext_a", repository.images[1]["blob_id"], repository)


def test_the_served_bytes_of_a_crop_are_checked_against_its_descriptor(monkeypatch) -> None:
    crop_bytes = png("served")
    image = descriptor(crop_bytes, crop_id="crop-served")
    monkeypatch.setattr(executor_public, "claimed_image", lambda *args: image)

    class Store:
        reads = 0

        def inspect(self, _blob_id):
            return SimpleNamespace(size=len(crop_bytes), sha256=image["sha256"], media_type="image/png")

        def open_stream(self, _blob_id, *, expected_sha256, expected_size):
            Store.reads += 1
            yield crop_bytes if Store.reads == 1 else crop_bytes + b"x"

    adapter = RunnerAdapter(lambda: nullcontext(None), blob_store=Store())
    runner = SimpleNamespace(token_id="ern_a", connection_id="exc_a")
    assert adapter.read_image(runner=runner, task_id="ext_a", blob_id=image["blob_id"]) == crop_bytes
    with pytest.raises(DomainError):
        adapter.read_image(runner=runner, task_id="ext_a", blob_id=image["blob_id"])
