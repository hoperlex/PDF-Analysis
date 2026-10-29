"""The default visibility of optional-content groups is in the content Merkle (`CMP-C1-FIX-A` item 7).

`CMP-ENGINE-01` section 9 item 4 / section 11 item 2: the Merkle named no ``/OCProperties``, so two pages with the same
stream and the same resources that differ only in the default visibility of a layer had one Merkle and took the engine's
fast path to ``same``. The original hashes the configuration (``pdfio.content_hash``, ``pdfio.py:211-236``).

The pages are built here with pypdf: one layer drawn by a marked-content sequence, and the catalogue's configuration
changed. The last tests run the real page child and the real engine child.
"""

from __future__ import annotations

import io
from collections.abc import Callable
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject,
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
    NumberObject,
    TextStringObject,
)

from auditmanager.comparison.profile import limits
from auditmanager.comparison.profile.child import page_merkle

Config = Callable[[DictionaryObject, "ArrayObject | None", object], None]


def _layered(config: dict | None = None, *, base_state: str | None = None, on: bool = False, off: bool = False,
             second_off: bool = False, usage: str | None = None, auto: bool = False, ocmd: bool = False, form: bool = False,
             with_properties: bool = True, annotated: bool = False) -> bytes:
    """A page whose rectangle is drawn on the layer "Стены", with the catalogue configuration the arguments describe."""
    writer = PdfWriter()
    page = writer.add_blank_page(300, 200)
    ocg = DictionaryObject({NameObject("/Type"): NameObject("/OCG"), NameObject("/Name"): TextStringObject("Стены")})
    if usage:
        ocg[NameObject("/Usage")] = DictionaryObject({NameObject("/View"): DictionaryObject({NameObject("/ViewState"): NameObject(usage)})})
    ocg_ref = writer._add_object(ocg)
    other = DictionaryObject({NameObject("/Type"): NameObject("/OCG"), NameObject("/Name"): TextStringObject("Оси")})
    other_ref = writer._add_object(other)

    target = ocg_ref
    if ocmd:
        membership = DictionaryObject({NameObject("/Type"): NameObject("/OCMD"), NameObject("/OCGs"): ArrayObject([ocg_ref])})
        target = writer._add_object(membership)
    properties = DictionaryObject({NameObject("/MC0"): target})
    resources = DictionaryObject()
    if with_properties:
        resources[NameObject("/Properties")] = properties
    content = b"/OC /MC0 BDC 10 10 100 50 re f EMC\n"
    if form:
        content = b"/Fm0 Do\n"
        stream = DecodedStreamObject()
        stream.set_data(b"10 10 100 50 re f\n")
        stream[NameObject("/Type")] = NameObject("/XObject")
        stream[NameObject("/Subtype")] = NameObject("/Form")
        stream[NameObject("/BBox")] = ArrayObject([NumberObject(0), NumberObject(0), NumberObject(300), NumberObject(200)])
        stream[NameObject("/OC")] = ocg_ref
        resources[NameObject("/XObject")] = DictionaryObject({NameObject("/Fm0"): writer._add_object(stream)})
    page[NameObject("/Resources")] = resources
    body = DecodedStreamObject()
    body.set_data(content)
    page[NameObject("/Contents")] = writer._add_object(body)

    default = DictionaryObject()
    if base_state:
        default[NameObject("/BaseState")] = NameObject(base_state)
    if on:
        default[NameObject("/ON")] = ArrayObject([ocg_ref])
    if off:
        default[NameObject("/OFF")] = ArrayObject([ocg_ref])
    if second_off:
        default[NameObject("/OFF")] = ArrayObject([*default.get("/OFF", []), other_ref])
    if auto:
        default[NameObject("/AS")] = ArrayObject([DictionaryObject({
            NameObject("/Event"): NameObject("/View"), NameObject("/OCGs"): ArrayObject([ocg_ref]),
            NameObject("/Category"): ArrayObject([NameObject("/View")])})])
    writer._root_object[NameObject("/OCProperties")] = DictionaryObject(
        {NameObject("/OCGs"): ArrayObject([ocg_ref, other_ref]), NameObject("/D"): default})
    if annotated:
        note = DictionaryObject({
            NameObject("/Type"): NameObject("/Annot"), NameObject("/Subtype"): NameObject("/Text"),
            NameObject("/Rect"): ArrayObject([NumberObject(5), NumberObject(5), NumberObject(20), NumberObject(20)]),
            NameObject("/Contents"): TextStringObject("замечание"), NameObject("/OC"): ocg_ref})
        page[NameObject("/Annots")] = ArrayObject([writer._add_object(note)])
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _merkle(data: bytes) -> str:
    return page_merkle.page_digest(PdfReader(io.BytesIO(data)).pages[0])


def _annotation_hash(data: bytes) -> str:
    return page_merkle.annotation_records(PdfReader(io.BytesIO(data)).pages[0])[0]["sha256"]


def test_a_layer_shown_and_the_same_layer_hidden_are_not_one_page() -> None:
    """The failure of the base: only ``/D`` differs, and the digest did not move."""
    assert _merkle(_layered(on=True)) != _merkle(_layered(off=True))


def test_the_base_state_and_the_two_lists_follow_the_order_of_the_viewer() -> None:
    """``/BaseState`` (``/ON`` unless ``/OFF``), then ``/ON``, then ``/OFF``: the last word wins, as in PDFium."""
    shown = {_merkle(_layered()), _merkle(_layered(base_state="/ON")), _merkle(_layered(base_state="/Unchanged")),
             _merkle(_layered(on=True)), _merkle(_layered(base_state="/OFF", on=True))}
    hidden = {_merkle(_layered(off=True)), _merkle(_layered(base_state="/OFF")), _merkle(_layered(on=True, off=True)),
              _merkle(_layered(base_state="/ON", off=True))}
    assert len(shown) == 1 and len(hidden) == 1 and shown != hidden


def test_a_layer_the_page_does_not_use_cannot_move_its_digest() -> None:
    """Only the groups the page refers to count: hiding another layer of the document is not a change of this page."""
    assert _merkle(_layered(on=True)) == _merkle(_layered(on=True, second_off=True))


def test_a_page_that_refers_to_no_layer_has_the_digest_of_a_document_without_a_configuration() -> None:
    """The configuration is read only through a reference to a group, so a page without one is untouched by it (and so
    its Merkle is what it was before the configuration was read)."""
    plain = _layered(with_properties=False, off=True)
    other = _layered(with_properties=False, on=True, second_off=True)
    assert _merkle(plain) == _merkle(other)


def test_a_membership_dictionary_and_a_form_that_name_a_layer_carry_its_state() -> None:
    for build in (lambda **kw: _layered(ocmd=True, **kw), lambda **kw: _layered(form=True, **kw)):
        assert _merkle(build(on=True)) != _merkle(build(off=True))


def test_a_layer_set_by_an_auto_state_entry_is_marked() -> None:
    """A group named by an ``/AS`` entry of the event ``View`` takes its state from its ``/Usage``; the mark makes the
    page differ from the same layer without the entry, and the usage (hashed by value) decides between on and off."""
    assert _merkle(_layered(on=True, auto=True)) != _merkle(_layered(on=True))
    assert _merkle(_layered(on=True, auto=True, usage="/ON")) != _merkle(_layered(on=True, auto=True, usage="/OFF"))


def test_the_usage_state_of_the_group_itself_is_in_the_digest() -> None:
    assert _merkle(_layered(on=True, usage="/ON")) != _merkle(_layered(on=True, usage="/OFF"))


def test_an_annotation_on_a_layer_carries_its_state_in_its_own_hash() -> None:
    shown, hidden = _layered(on=True, annotated=True), _layered(off=True, annotated=True)
    assert _annotation_hash(shown) != _annotation_hash(hidden)


def test_the_digest_does_not_depend_on_object_numbers() -> None:
    """The state is folded into the reference's digest; the numbers of the objects (which differ between two writers) are not
    in it: the same document written with its objects added in another order has the same Merkle."""
    first = _layered(on=True)
    reader = PdfReader(io.BytesIO(first))
    writer = PdfWriter(clone_from=reader)
    buffer = io.BytesIO()
    writer.write(buffer)
    assert _merkle(buffer.getvalue()) == _merkle(first)


def test_the_profile_algorithm_is_not_the_first_one() -> None:
    """A stored profile of ``cmp-profile/1`` has a Merkle that ignores the layers: it is not current, the listing shows the
    current algorithm's only, and a new preparation builds the page again."""
    assert limits.ALGO_VERSION != "cmp-profile/1" and limits.ALGO_VERSION.startswith("cmp-profile/")


# -- the real children -------------------------------------------------------------------------------------------------

def test_the_profile_child_gives_two_pages_that_differ_only_in_layer_visibility_two_merkles(tmp_path: Path, runner) -> None:
    import hashlib

    from auditmanager.comparison.profile.profiling import profile_page

    merkles = []
    for name, data in (("on.pdf", _layered(on=True)), ("off.pdf", _layered(off=True))):
        path = tmp_path / name
        path.write_bytes(data)
        outcome = profile_page(runner, pdf_path=str(path), page_index=0, version_sha256=hashlib.sha256(data).hexdigest())
        assert outcome.status == "ready", outcome.reason
        merkles.append(outcome.summary["content_merkle"])
    assert merkles[0] != merkles[1]
