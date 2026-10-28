"""The content Merkle and the annotation hashes (`CMP-PROFILE-01`, ADR-0025 decision 15).

The synthetic corpus gives the oracle: its answer key records, for every page, the SHA-256 of the page's
content stream (``content_sha256``) and of its one image (``image_sha256``), authored by the generator.
Two pages the key puts in one class (the same stream, the same image: byte-identical sheets, and the A1 plan
before and after an annotation was added) must have one Merkle, and two pages in different classes must not.
Then each kind of change the cache key exists to see is made to a real page with pypdf, and the Merkle has to
move: a stream byte, a resource, an image, the page box -- and has to stay put for an annotation, which is
hashed beside it.
"""

from __future__ import annotations

import io

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, DictionaryObject, FloatObject, NameObject, NumberObject, TextStringObject

from auditmanager.comparison.profile.child import page_merkle


def _digest(path, index: int) -> str:
    with open(path, "rb") as handle:
        return page_merkle.page_digest(PdfReader(handle).pages[index])


def _rewritten(path, index: int, change) -> object:
    """Page ``index`` of ``path`` after ``change(page, writer)``, read back from memory."""
    writer = PdfWriter(clone_from=str(path))
    change(writer.pages[index], writer)
    buffer = io.BytesIO()
    writer.write(buffer)
    buffer.seek(0)
    return PdfReader(buffer).pages[index]


def test_the_merkle_classes_are_the_answer_keys_content_classes(vs1_key: dict, vs1_profiles: dict) -> None:
    by_merkle: dict[str, set[str]] = {}
    by_key: dict[str, set[str]] = {}
    for version in vs1_key["versions"]:
        for index, page in enumerate(version["pages"]):
            where = f"{version['id']}.{index + 1}"
            merkle = vs1_profiles[version["id"]][index].summary["content_merkle"]
            by_merkle.setdefault(merkle, set()).add(where)
            by_key.setdefault(f"{page['content_sha256']}|{page['image_sha256']}", set()).add(where)
    assert sorted(map(sorted, by_merkle.values())) == sorted(map(sorted, by_key.values()))
    # The key does say there are repeats worth telling apart from a mere equality of everything.
    assert any(len(group) > 1 for group in by_key.values()) and len(by_key) > 6


def test_an_annotation_only_change_moves_the_annotation_hash_and_not_the_merkle(vs1_key: dict, vs1_profiles: dict) -> None:
    before, after = vs1_profiles["V1"][4].summary, vs1_profiles["V2"][4].summary
    assert before["content_merkle"] == after["content_merkle"]
    assert before["annotation_hashes"] == [] and len(after["annotation_hashes"]) == 1
    assert before["counts"]["annotations"] == 0 and after["counts"]["annotations"] == 1
    # ... and it moves the content key, which is what the cache and the unique key see.
    assert vs1_profiles["V1"][4].content_key != vs1_profiles["V2"][4].content_key


def test_a_duplicated_sheet_has_one_merkle_and_two_content_keys(vs1_profiles: dict) -> None:
    third, eighth = vs1_profiles["V5"][2], vs1_profiles["V5"][7]
    assert third.summary["content_merkle"] == eighth.summary["content_merkle"]
    assert third.content_key != eighth.content_key, "UNIQUE (version, content_key) would refuse the second row"


@pytest.mark.parametrize("version", ["V1", "V2", "V3", "V4", "V5"])
def test_the_content_keys_of_a_version_are_unique(vs1_profiles: dict, version: str) -> None:
    keys = [outcome.content_key for outcome in vs1_profiles[version]]
    assert len(set(keys)) == len(keys)


def test_a_changed_stream_byte_changes_the_digest(fixtures_dir) -> None:
    path = fixtures_dir / "vs1" / "v1.pdf"

    def change(page, writer):
        stream = page["/Contents"].get_object()
        data = stream.get_data()
        stream.set_data(data.replace(b"(", b"( ", 1) if b"(" in data else data + b"\n% x\n")

    assert page_merkle.page_digest(_rewritten(path, 1, change)) != _digest(path, 1)


def test_a_changed_resource_changes_the_digest(fixtures_dir) -> None:
    path = fixtures_dir / "vs1" / "v1.pdf"

    def change(page, writer):
        resources = page["/Resources"]
        fonts = resources["/Font"]
        first = next(iter(fonts))
        fonts[first].get_object()[NameObject("/BaseFont")] = NameObject("/Changed")

    assert page_merkle.page_digest(_rewritten(path, 1, change)) != _digest(path, 1)


def test_a_replaced_image_changes_the_digest_of_a_scan(fixtures_dir) -> None:
    path = fixtures_dir / "vs1" / "v4.pdf"

    def change(page, writer):
        xobjects = page["/Resources"]["/XObject"]
        image = xobjects[next(iter(xobjects))].get_object()
        data = bytearray(image._data)
        data[len(data) // 2] ^= 0x01
        image._data = bytes(data)

    assert page_merkle.page_digest(_rewritten(path, 3, change)) != _digest(path, 3)


def test_a_changed_page_box_changes_the_digest(fixtures_dir) -> None:
    path = fixtures_dir / "vs1" / "v1.pdf"

    def change(page, writer):
        page.mediabox.upper_right = (float(page.mediabox.right) + 1.0, float(page.mediabox.top))

    assert page_merkle.page_digest(_rewritten(path, 1, change)) != _digest(path, 1)


def test_an_added_annotation_leaves_the_digest_and_has_its_own_hash(fixtures_dir) -> None:
    path = fixtures_dir / "vs1" / "v1.pdf"

    def change(page, writer):
        annotation = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Annot"),
                NameObject("/Subtype"): NameObject("/Text"),
                NameObject("/Rect"): ArrayObject([FloatObject(10), FloatObject(10), FloatObject(30), FloatObject(30)]),
                NameObject("/Contents"): TextStringObject("проверить"),
            }
        )
        reference = writer._add_object(annotation)
        page[NameObject("/Annots")] = ArrayObject([reference])

    changed = _rewritten(path, 1, change)
    assert page_merkle.page_digest(changed) == _digest(path, 1)
    records = page_merkle.annotation_records(changed)
    assert len(records) == 1 and records[0]["subtype"] == "/Text" and records[0]["contents"] == "проверить"
    assert records[0]["rect"] == [10.0, 10.0, 30.0, 30.0]
    # A different text is a different hash.
    other = _rewritten(path, 1, lambda page, writer: change(page, writer) or None)
    assert page_merkle.annotation_records(other)[0]["sha256"] == records[0]["sha256"], "deterministic"

    def change_text(page, writer):
        change(page, writer)
        annotation = page["/Annots"][0].get_object()
        annotation[NameObject("/Contents")] = TextStringObject("другое")

    assert page_merkle.annotation_records(_rewritten(path, 1, change_text))[0]["sha256"] != records[0]["sha256"]


def test_a_reference_loop_does_not_loop_and_a_deep_chain_is_refused(fixtures_dir, monkeypatch: pytest.MonkeyPatch) -> None:
    path = fixtures_dir / "vs1" / "v1.pdf"

    def make_loop(page, writer):
        first = DictionaryObject()
        reference = writer._add_object(first)
        first[NameObject("/Self")] = reference
        page["/Resources"][NameObject("/Loop")] = reference

    looped = _rewritten(path, 1, make_loop)
    first = page_merkle.page_digest(looped)
    assert first == page_merkle.page_digest(looped) and len(first) == 64

    monkeypatch.setattr(page_merkle, "MAX_NODES", 50)
    with pytest.raises(page_merkle.MerkleBudgetExceeded):
        page_merkle.page_digest(_rewritten(path, 1, lambda page, writer: None))


def test_the_digest_does_not_depend_on_object_numbers(fixtures_dir) -> None:
    """The same page written with its objects renumbered (a copy through ``PdfWriter``) keeps its digest."""
    path = fixtures_dir / "vs1" / "v1.pdf"
    renumbered = _rewritten(path, 1, lambda page, writer: None)
    original = _digest(path, 1)
    # pypdf rewrites the file with new object numbers and the same objects: the digest is a function of
    # content, so it is the same -- unless the rewrite changed a stream, which it must not.
    assert page_merkle.page_digest(renumbered) == original
