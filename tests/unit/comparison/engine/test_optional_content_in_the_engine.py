"""A visibility-only change of a layer is not ``same`` (`CMP-C1-FIX-A` item 7), through the real children.

`CMP-ENGINE-01` section 9 item 4: with one content Merkle for two pages that differ only in the default visibility of a
layer, the engine took its fast path to ``same`` without starting a child. The profile's Merkle now covers the state of the
layers a page uses (`tests/unit/comparison/profile/test_optional_content.py` builds the variants); here the consequence.
"""

from __future__ import annotations

import io
from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import ArrayObject, DecodedStreamObject, DictionaryObject, NameObject, TextStringObject


def layered(visible: bool) -> bytes:
    """One page with a rectangle drawn on the layer "Стены"; the layer is on or off in the default configuration."""
    writer = PdfWriter()
    page = writer.add_blank_page(300, 200)
    ocg = writer._add_object(DictionaryObject({NameObject("/Type"): NameObject("/OCG"), NameObject("/Name"): TextStringObject("Стены")}))
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Properties"): DictionaryObject({NameObject("/MC0"): ocg})})
    body = DecodedStreamObject()
    body.set_data(b"/OC /MC0 BDC 10 10 100 50 re f EMC\n")
    page[NameObject("/Contents")] = writer._add_object(body)
    default = DictionaryObject({NameObject("/ON" if visible else "/OFF"): ArrayObject([ocg])})
    writer._root_object[NameObject("/OCProperties")] = DictionaryObject({NameObject("/OCGs"): ArrayObject([ocg]), NameObject("/D"): default})
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_the_engine_does_not_take_the_fast_path_to_same_for_a_visibility_only_change(tmp_path: Path, compare) -> None:
    """With one Merkle the pair was ``same`` without a child; now it is compared, and the rectangle that appeared is a difference."""
    shown, hidden = tmp_path / "shown.pdf", tmp_path / "hidden.pdf"
    shown.write_bytes(layered(True))
    hidden.write_bytes(layered(False))
    computed = compare(str(shown), 1, str(hidden), 1)
    assert computed.end == "ok", computed.end  # a child ran: not the "identical" fast path
    assert computed.outcome["status"] != "same"
    assert computed.outcome["channels"]["geometry"]["diffs"] >= 1


def test_the_same_layer_in_the_same_state_is_still_the_fast_path_to_same(tmp_path: Path, compare) -> None:
    one, two = tmp_path / "one.pdf", tmp_path / "two.pdf"
    one.write_bytes(layered(True))
    two.write_bytes(layered(True))
    computed = compare(str(one), 1, str(two), 1)
    assert computed.end == "identical" and computed.outcome["status"] == "same"
