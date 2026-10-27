"""The stored archive of a page profile (`CMP-PROFILE-01`): deterministic, closed to unknown members."""

from __future__ import annotations

import io
import zipfile

import pytest

from auditmanager.comparison.profile import pack


def _sample(tiles=((2, 0, 0, b"\x89PNG-a"), (2, 1, 0, b"\x89PNG-b"), (3, 0, 0, b"\x89PNG-c"))) -> bytes:
    return pack.build_pack({"schema": "x", "words": [[1, 2, 3, 4, "слово"]]}, mask=b"\x01\x02", tiles=tiles)


def test_the_same_page_is_the_same_bytes_whatever_the_order_the_tiles_arrive_in() -> None:
    first = _sample()
    second = _sample(tuple(reversed(((2, 0, 0, b"\x89PNG-a"), (2, 1, 0, b"\x89PNG-b"), (3, 0, 0, b"\x89PNG-c")))))
    assert first == second


def test_members_round_trip() -> None:
    reader = pack.PackReader(_sample())
    assert reader.document() == {"schema": "x", "words": [[1, 2, 3, 4, "слово"]]}
    assert reader.mask() == b"\x01\x02"
    assert reader.tile(2, 1, 0) == b"\x89PNG-b" and reader.tile(3, 0, 0) == b"\x89PNG-c"
    assert reader.tile(2, 9, 9) is None
    assert reader.tile_names() == ["tiles/2/0_0.png", "tiles/2/1_0.png", "tiles/3/0_0.png"]


def test_a_page_without_a_mask_or_tiles_is_just_its_document() -> None:
    reader = pack.PackReader(pack.build_pack({"schema": "x"}, mask=None, tiles=()))
    assert reader.mask() is None and reader.tile_names() == []


def test_timestamps_are_fixed_so_a_rebuild_is_the_same_blob() -> None:
    with zipfile.ZipFile(io.BytesIO(_sample())) as archive:
        assert {info.date_time for info in archive.infolist()} == {(1980, 1, 1, 0, 0, 0)}


def test_a_file_that_is_not_an_archive_is_unreadable() -> None:
    with pytest.raises(pack.PackUnreadable):
        pack.PackReader(b"not a zip")


@pytest.mark.parametrize("name", ["../evil.png", "/etc/passwd", "tiles/2/a_b.png", "other.txt", "tiles/2/0_0.jpg"])
def test_an_archive_with_a_member_this_lane_never_writes_is_unreadable(name: str) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(pack.PROFILE_MEMBER, b"{}")
        archive.writestr(name, b"x")
    with pytest.raises(pack.PackUnreadable):
        pack.PackReader(buffer.getvalue())


def test_an_archive_without_its_document_is_unreadable() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(pack.MASK_MEMBER, b"x")
    with pytest.raises(pack.PackUnreadable):
        pack.PackReader(buffer.getvalue())


def test_the_canonical_json_is_key_sorted_and_compact() -> None:
    assert pack.canonical_json({"b": 1, "a": [1, 2]}) == b'{"a":[1,2],"b":1}'
    assert pack.canonical_json({"т": "я"}) == '{"т":"я"}'.encode()
