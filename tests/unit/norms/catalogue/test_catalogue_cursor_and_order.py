"""`W57B-NORMS-CATALOGUE-XLSX-01`: the catalogue token, the word-start filter and the order.

Pure functions only; the database-backed listing is in
``tests/integration/norms/catalogue/test_catalogue_window.py``.
"""

from __future__ import annotations

import base64
import json

import pytest

from auditmanager.norms.catalogue import (
    CatalogueEntry,
    catalogue_binding,
    decode_catalogue_cursor,
    encode_catalogue_cursor,
)
from auditmanager.norms.catalogue.service import _searchable, matches, sort_key
from auditmanager.shared.errors import DomainError, ErrorCode

NDOC = "ndoc_01M59N9H4XWGGX6AS4RY6QF3F3"
SNAPSHOT = "ns_01M59N8QNBVN91ACA2HCE6VE74"


def _entry(designation: str, title: str | None = None, identity: str = NDOC) -> CatalogueEntry:
    return CatalogueEntry(
        norm_document_id=identity, designation=designation, title=title, kind="СП",
        page_count=1, paragraph_count=1, content_available=True,
        source_attribution="consultant_plus",
    )


def _refused(call) -> None:
    with pytest.raises(DomainError) as caught:
        call()
    assert caught.value.code is ErrorCode.VALIDATION_FAILED
    assert dict(caught.value.detail_fields) == {"field": "cursor", "constraint": "format"}


# --- the token -----------------------------------------------------------------------------


def test_a_token_round_trips_for_its_own_binding_only() -> None:
    binding = catalogue_binding("СП 54", None, SNAPSHOT)
    token = encode_catalogue_cursor(binding, NDOC)
    assert decode_catalogue_cursor(token, binding=binding) == NDOC
    for other in (
        catalogue_binding("СП 55", None, SNAPSHOT),
        catalogue_binding("СП 54", "СП", SNAPSHOT),
        catalogue_binding("СП 54", None, "ns_01M59N8QNBVN91ACA2HCE6VE75"),
        catalogue_binding(None, None, SNAPSHOT),
    ):
        assert other != binding
        _refused(lambda other=other: decode_catalogue_cursor(token, binding=other))


def test_the_token_carries_a_position_and_no_count() -> None:
    binding = catalogue_binding(None, None, SNAPSHOT)
    token = encode_catalogue_cursor(binding, NDOC)
    parts = json.loads(base64.urlsafe_b64decode(token + "=" * (-len(token) % 4)))
    assert parts == ["c1", binding, NDOC]


@pytest.mark.parametrize(
    "parts",
    [
        ["c2", "0" * 32, NDOC],
        ["c1", "0" * 31, NDOC],
        ["c1", "0" * 32, "npar_01M59N9H4XWGGX6AS4RY6QF3F3"],
        ["c1", "0" * 32, NDOC, 1],
        ["c1", "0" * 32, 7],
        {"c1": NDOC},
    ],
)
def test_foreign_shapes_are_refused(parts: object) -> None:
    raw = json.dumps(parts, separators=(",", ":")).encode()
    token = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    _refused(lambda: decode_catalogue_cursor(token, binding="0" * 32))


@pytest.mark.parametrize("token", ["", "!!!", "x" * 513, "e30"])
def test_undecodable_tokens_are_refused(token: str) -> None:
    _refused(lambda: decode_catalogue_cursor(token, binding="0" * 32))


def test_a_re_padded_token_is_refused() -> None:
    binding = "0" * 32
    token = encode_catalogue_cursor(binding, NDOC)
    _refused(lambda: decode_catalogue_cursor(token + "=" * (-len(token) % 4 or 4), binding=binding))


# --- the filter ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("q", "designation", "title", "kept"),
    [
        ("24.04.2013", "Приказ МЧС России от 24.04.2013 N 288 (ред. от 27.06.2023)", None, True),
        ("24 04 2013", "Приказ МЧС России от 24.04.2013 N 288 (ред. от 27.06.2023)", None, True),
        ("СП 54.13330", "СП 54.13330.2022", "Свод правил. Здания жилые", True),
        ("сп 54", "СП 54.13330.2022", None, True),
        ("54", "СП 154.13330.2013", None, False),
        ("сп 54", "СП 542.1325800.2024", None, False),
        ("сп 54.1333", "СП 54.13330.2022", None, False),
        ("огнест", "СП 2.13130.2020", "Обеспечение огнестойкости", True),
        ("здания жилые", "СП 54.13330.2022", "Свод правил. Здания жилые", True),
        ("дания", "СП 54.13330.2022", "Свод правил. Здания жилые", False),
        # Latin homoglyphs and case fold like the search's designations.
        ("CП 54", "СП 54.13330.2022", None, True),
        ("№ 288", "Приказ МЧС России от 24.04.2013 N 288", None, True),
        ("ёлка", "Елка", None, True),
    ],
)
def test_the_filter_matches_from_a_word_start(
    q: str, designation: str, title: str | None, kept: bool
) -> None:
    assert matches(_entry(designation, title), _searchable(q)) is kept


# --- the order -----------------------------------------------------------------------------


def test_the_order_is_natural_folded_and_total() -> None:
    entries = [
        _entry("СП 10.13130.2009", identity="ndoc_01M59N9H4XWGGX6AS4RY6QF3F5"),
        _entry("СП 2.13130.2020", identity="ndoc_01M59N9H4XWGGX6AS4RY6QF3F4"),
        _entry("гост 1.1-2002", identity="ndoc_01M59N9H4XWGGX6AS4RY6QF3F6"),
        _entry("СП 2.13130.2020", identity="ndoc_01M59N9H4XWGGX6AS4RY6QF3F3"),
    ]
    ordered = sorted(entries, key=sort_key)
    assert [entry.norm_document_id[-2:] for entry in ordered] == ["F6", "F3", "F4", "F5"]
