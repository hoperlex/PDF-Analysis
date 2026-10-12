"""The norms continuation tokens and the hit fragments -- without a database.

`W55A-SEARCH-01` (`W55-PLAN.md` section A3.4): a search token is bound to its query and its
snapshot and is refused for any other; it carries the rank as exact ``float4`` bits; no token
outgrows the contract's ``Cursor`` (512 characters); a fragment is plain text whose matched
spans are code-point offsets (`NORM-Q01`).
"""

from __future__ import annotations

import base64
import json
import struct
from datetime import datetime, timezone

import pytest

from auditmanager.norms.search.cursor import (
    MAX_CURSOR_CHARACTERS,
    DesignationPosition,
    EventPosition,
    ParagraphPosition,
    RankPosition,
    SnapshotPosition,
    decode_event_cursor,
    decode_paragraph_cursor,
    decode_search_cursor,
    decode_snapshot_cursor,
    encode_event_cursor,
    encode_paragraph_cursor,
    encode_search_cursor,
    encode_snapshot_cursor,
    query_binding,
    rank_bits,
)
from auditmanager.norms.search.fragment import (
    FRAGMENT_MAX_CHARACTERS,
    START,
    STOP,
    UNRANKED_FRAGMENT_CHARACTERS,
    fragment_from_headline,
    plain_fragment,
)
from auditmanager.shared.errors import DomainError, ErrorCode

SNAPSHOT = "ns_01M2545JSD15ETSNNV904X991N"
OTHER_SNAPSHOT = "ns_01M2545JSD15ETSNNV904X992N"
NPAR = "npar_01M2545JSD15ETSNNV904X991P"
NDOC = "ndoc_01M2545JSD15ETSNNV904X991V"
EVT = "evt_01M2545JSD15ETSNNV904X991E"


def _float4(value: float) -> float:
    return struct.unpack(">f", struct.pack(">f", value))[0]


def _refused_as_format(call) -> None:
    with pytest.raises(DomainError) as caught:
        call()
    assert caught.value.code is ErrorCode.VALIDATION_FAILED
    assert dict(caught.value.detail_fields) == {"field": "cursor", "constraint": "format"}


def test_a_ranked_token_round_trips_its_exact_float4_rank() -> None:
    rank = _float4(0.1)
    binding = query_binding("здания", SNAPSHOT)
    token = encode_search_cursor(binding, RankPosition(rank, NPAR))
    position = decode_search_cursor(token, binding=binding, ranked=True)
    assert position == RankPosition(rank, NPAR)
    assert struct.pack(">f", position.rank) == struct.pack(">f", rank)
    assert rank_bits(rank) == struct.pack(">f", rank).hex()


def test_an_ordered_token_round_trips() -> None:
    binding = query_binding("СП 54", SNAPSHOT)
    token = encode_search_cursor(binding, DesignationPosition(NDOC, 17, NPAR))
    assert decode_search_cursor(token, binding=binding, ranked=False) == DesignationPosition(
        NDOC, 17, NPAR
    )


def test_a_token_is_refused_for_another_query_or_another_snapshot() -> None:
    token = encode_search_cursor(query_binding("здания", SNAPSHOT), RankPosition(0.5, NPAR))
    for q, snapshot in (("зданий", SNAPSHOT), ("здания", OTHER_SNAPSHOT), ("Здания", SNAPSHOT)):
        _refused_as_format(
            lambda: decode_search_cursor(
                token, binding=query_binding(q, snapshot), ranked=True
            )
        )


def test_a_ranked_token_is_refused_by_an_ordered_query_and_back() -> None:
    binding = query_binding("СП 54", SNAPSHOT)
    ranked = encode_search_cursor(binding, RankPosition(0.5, NPAR))
    ordered = encode_search_cursor(binding, DesignationPosition(NDOC, 1, NPAR))
    _refused_as_format(lambda: decode_search_cursor(ranked, binding=binding, ranked=False))
    _refused_as_format(lambda: decode_search_cursor(ordered, binding=binding, ranked=True))


@pytest.mark.parametrize(
    "token",
    [
        "",
        "not-base64!",
        base64.urlsafe_b64encode(b"[1,2,3]").decode().rstrip("="),
        base64.urlsafe_b64encode(b'["s1r","00","3f000000","x"]').decode().rstrip("="),
        "A" * (MAX_CURSOR_CHARACTERS + 1),
    ],
)
def test_a_forged_token_is_refused(token: str) -> None:
    binding = query_binding("здания", SNAPSHOT)
    _refused_as_format(lambda: decode_search_cursor(token, binding=binding, ranked=True))


def test_a_token_with_a_foreign_identity_is_refused() -> None:
    binding = query_binding("здания", SNAPSHOT)
    raw = json.dumps(["s1r", binding, "3f000000", "ndoc_01M2545JSD15ETSNNV904X991V"],
                     separators=(",", ":")).encode()
    token = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    _refused_as_format(lambda: decode_search_cursor(token, binding=binding, ranked=True))


def test_no_token_outgrows_the_contract_cursor() -> None:
    binding = query_binding("x" * 200, SNAPSHOT)
    tokens = [
        encode_search_cursor(binding, RankPosition(_float4(1e30), NPAR)),
        encode_search_cursor(binding, DesignationPosition(NDOC, 2**31 - 1, NPAR)),
        encode_paragraph_cursor(ParagraphPosition(NDOC, 2**31 - 1)),
        encode_snapshot_cursor(
            SnapshotPosition(datetime(2026, 10, 12, 1, 2, 3, 456789, tzinfo=timezone.utc),
                             SNAPSHOT)
        ),
        encode_event_cursor(
            EventPosition(datetime(2026, 10, 12, 1, 2, 3, 456789, tzinfo=timezone.utc), EVT)
        ),
    ]
    assert max(len(token) for token in tokens) <= MAX_CURSOR_CHARACTERS


def test_a_paragraph_token_is_bound_to_its_document() -> None:
    token = encode_paragraph_cursor(ParagraphPosition(NDOC, 40))
    assert decode_paragraph_cursor(token, norm_document_id=NDOC) == ParagraphPosition(NDOC, 40)
    _refused_as_format(
        lambda: decode_paragraph_cursor(
            token, norm_document_id="ndoc_01M2545JSD15ETSNNV904X992V"
        )
    )


def test_snapshot_and_event_tokens_round_trip_their_instants() -> None:
    at = datetime(2026, 10, 12, 1, 2, 3, 456789, tzinfo=timezone.utc)
    assert decode_snapshot_cursor(
        encode_snapshot_cursor(SnapshotPosition(at, SNAPSHOT))
    ) == SnapshotPosition(at, SNAPSHOT)
    assert decode_event_cursor(encode_event_cursor(EventPosition(at, EVT))) == EventPosition(
        at, EVT
    )
    _refused_as_format(lambda: decode_event_cursor(
        encode_snapshot_cursor(SnapshotPosition(at, SNAPSHOT))
    ))


# --- fragments -----------------------------------------------------------------------------


def test_a_headline_becomes_plain_text_and_offsets() -> None:
    marked = f"Требования к {START}зданиям{STOP} и {START}сооружениям{STOP} ёмкостей"
    fragment = fragment_from_headline(marked, fallback="unused")
    assert fragment.text == "Требования к зданиям и сооружениям ёмкостей"
    assert [fragment.text[a:b] for a, b in fragment.highlights] == ["зданиям", "сооружениям"]
    assert START not in fragment.text and STOP not in fragment.text


def test_an_unbalanced_or_empty_mark_is_not_a_span() -> None:
    fragment = fragment_from_headline(f"{START}{STOP}a {START}b", fallback="unused")
    assert fragment.text == "a b"
    assert fragment.highlights == ((2, 3),)


def test_an_empty_headline_falls_back_to_the_paragraphs_opening() -> None:
    fragment = fragment_from_headline("", fallback="Текст абзаца " * 100)
    assert fragment.highlights == ()
    assert len(fragment.text) == UNRANKED_FRAGMENT_CHARACTERS


def test_a_long_headline_is_cut_to_the_contract_bound() -> None:
    marked = "а" * (FRAGMENT_MAX_CHARACTERS - 1) + f"{START}бб{STOP}"
    fragment = fragment_from_headline(marked, fallback="unused")
    assert len(fragment.text) == FRAGMENT_MAX_CHARACTERS
    assert fragment.highlights == ((FRAGMENT_MAX_CHARACTERS - 1, FRAGMENT_MAX_CHARACTERS),)


def test_an_unranked_fragment_is_unmarked_and_never_empty() -> None:
    assert plain_fragment("7.1.4 Лестницы").text == "7.1.4 Лестницы"
    assert plain_fragment("   ").text == "…"
    assert plain_fragment(f"{START}x{STOP}").text == "x"
