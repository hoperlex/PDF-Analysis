"""``analysis.text.textlayer``: the eight invariants `load_text_layer` checks.

`W10-ANL` mutation sweep, rows TL-01 and TL-03 to TL-09. Of the nine refusals in
`load_text_layer`, exactly one — `artifact_version_unsupported` — could be reddened by any
existing test. Disabling the other eight was green across
`tests/integration/analysis_engine`, `tests/integration/analysis_text` and `tests/replay`.

The module's own docstring is explicit about why this matters: "an offset computed against a
text layer that violates one of them is wrong in a way no later test detects: it still
resolves, just to the wrong span". The arithmetic that computes the offsets *is* guarded —
five separate offset mutations redden `test_recorded_run_surfaces_every_seeded_issue`. What
was unguarded is the validation of the layer that arithmetic is computed against.

Every document here is built in the test. No byte is added to `fixtures/synthetic/ar/**` or
`fixtures/validation/PC-02/**`.

Each refusal is asserted by its own `reason`, never by "a `DomainError` was raised" — several
of these nine share a catalog code and two share a `reason`, so asserting the code alone
would let a deleted check pass.
"""

from __future__ import annotations

from typing import Any

import pytest

from auditmanager.analysis.text.textlayer import load_text_layer
from auditmanager.shared.errors import DomainError, ErrorCode

#: Pinned as literals. The authority is `docs/program/P02_SEAMS.md` §4.1 and §4.3.
ARTIFACT_ROLE = "prepared.text_layer"
SUPPORTED_ARTIFACT_VERSION = "1.0.0"
NORMALIZATION_ID = "nfc_v1"

#: Two short Russian pages. The corpus is Russian and every quotation is non-ASCII, so a
#: byte-offset implementation misplaces every anchor while looking plausible in English.
PAGE_ONE = "Отчёт за год.\n"
PAGE_TWO = "Выручка выросла.\n"


def _layer(**overrides: Any) -> dict[str, Any]:
    """A well-formed text layer, with exactly the fields a test wants changed."""
    document: dict[str, Any] = {
        "artifact_role": ARTIFACT_ROLE,
        "artifact_version": SUPPORTED_ARTIFACT_VERSION,
        "version_uid": "ver_01M2545JSD15ETSNNV904X991J",
        "normalization": {"id": NORMALIZATION_ID, "description": "NFC"},
        "total_char_count": len(PAGE_ONE) + len(PAGE_TWO),
        "pages": [
            {
                "page_number": 1,
                "char_start": 0,
                "char_end": len(PAGE_ONE),
                "text": PAGE_ONE,
            },
            {
                "page_number": 2,
                "char_start": len(PAGE_ONE),
                "char_end": len(PAGE_ONE) + len(PAGE_TWO),
                "text": PAGE_TWO,
            },
        ],
    }
    document.update(overrides)
    return document


def _refusal_reason(document: dict[str, Any]) -> str:
    with pytest.raises(DomainError) as raised:
        load_text_layer(document)
    error = raised.value
    assert error.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert error.detail_fields["stage_id"] == "text_analysis"
    return str(error.detail_fields["reason"])


# --- the well-formed layer is accepted ----------------------------------------------


def test_a_well_formed_layer_loads_and_concatenates_with_no_separator() -> None:
    """The negative half. Page 2 starts exactly where page 1 ended.

    The expected document text is written out as the concatenation of the two page
    literals, not rebuilt from the module's own output.
    """
    layer = load_text_layer(_layer())
    assert layer.document_text == PAGE_ONE + PAGE_TWO
    assert layer.total_char_count == 31
    assert layer.page_numbers == (1, 2)
    assert layer.normalization_id == NORMALIZATION_ID


def test_the_offsets_are_code_points_and_not_bytes() -> None:
    """31 code points; the same text is 55 bytes in UTF-8. Both figures are literals."""
    layer = load_text_layer(_layer())
    assert layer.total_char_count == 31
    assert len((PAGE_ONE + PAGE_TWO).encode("utf-8")) == 55
    assert layer.slice(0, 13) == "Отчёт за год."


# --- the eight refusals -------------------------------------------------------------


@pytest.mark.parametrize(
    "role", ["prepared.page_inventory", "geometry.block_index", "", "text_layer"]
)
def test_a_document_that_is_not_a_text_layer_is_refused(role: str) -> None:
    """TL-01."""
    assert _refusal_reason(_layer(artifact_role=role)) == "artifact_role_unexpected"


def test_a_document_with_no_artifact_role_at_all_is_refused() -> None:
    document = _layer()
    del document["artifact_role"]
    assert _refusal_reason(document) == "artifact_role_unexpected"


@pytest.mark.parametrize("version", ["1.1.0", "2.0.0", "0.9.0", ""])
def test_an_unsupported_artifact_version_is_refused(version: str) -> None:
    """TL-02 — the one refusal that was already guarded. Kept so the set is complete."""
    assert _refusal_reason(_layer(artifact_version=version)) == "artifact_version_unsupported"


@pytest.mark.parametrize(
    "normalization", [{}, {"id": ""}, {"description": "NFC"}, {"id": 1}, {"id": None}]
)
def test_a_layer_declaring_no_normalization_is_refused(normalization: Any) -> None:
    """TL-03. The normalization is applied once and named; a consumer must not guess it."""
    assert _refusal_reason(_layer(normalization=normalization)) == "normalization_undeclared"


@pytest.mark.parametrize("pages", [[], None])
def test_a_layer_carrying_no_pages_is_refused(pages: Any) -> None:
    """TL-04."""
    assert _refusal_reason(_layer(pages=pages)) == "text_layer_empty"


def test_pages_that_skip_a_number_are_refused() -> None:
    """TL-05. Page 3 after page 1 is a gap, and a gap silently shifts every later offset."""
    document = _layer()
    document["pages"][1]["page_number"] = 3
    assert _refusal_reason(document) == "page_sequence_broken"


def test_pages_out_of_ascending_order_are_refused() -> None:
    document = _layer()
    document["pages"][0]["page_number"] = 2
    document["pages"][1]["page_number"] = 1
    assert _refusal_reason(document) == "page_sequence_broken"


def test_a_page_that_does_not_begin_where_the_previous_ended_is_refused() -> None:
    """TL-06. A one-code-point gap between pages — the separator that must not exist."""
    document = _layer()
    document["pages"][1]["char_start"] = len(PAGE_ONE) + 1
    document["pages"][1]["char_end"] = len(PAGE_ONE) + 1 + len(PAGE_TWO)
    document["total_char_count"] = len(PAGE_ONE) + 1 + len(PAGE_TWO)
    assert _refusal_reason(document) == "page_offsets_discontiguous"


def test_a_first_page_that_does_not_start_at_zero_is_refused() -> None:
    """The rule holds — but the line that states it is dead code. See TL-08.

    `load_text_layer` ends with

        if pages[0].char_start != 0:
            raise _invalid("page_offsets_discontiguous", "the first text layer page ...")

    and that branch is **unreachable by construction**. `expected_start` is initialised to
    `0` before the loop, so on the first iteration `if page.char_start != expected_start`
    is exactly `if pages[0].char_start != 0` and has already refused. `raw_pages` is
    checked non-empty above, so the loop always runs at least once.

    This test therefore asserts the *rule* — a first page that does not start at zero is
    refused, by `page_offsets_discontiguous` — and cannot distinguish which of the two
    lines enforced it. Deleting the dead post-loop branch leaves this green, correctly:
    nothing is lost. It is reported as dead code rather than guarded by a test that would
    have to lie about what it checks.
    """
    document = _layer()
    document["pages"][0]["char_start"] = 1
    document["pages"][0]["char_end"] = 1 + len(PAGE_ONE)
    document["pages"][1]["char_start"] = 1 + len(PAGE_ONE)
    document["pages"][1]["char_end"] = 1 + len(PAGE_ONE) + len(PAGE_TWO)
    document["total_char_count"] = 1 + len(PAGE_ONE) + len(PAGE_TWO)
    assert _refusal_reason(document) == "page_offsets_discontiguous"


def test_a_span_measured_in_bytes_rather_than_code_points_is_refused() -> None:
    """TL-07. The concrete failure: a producer that used `len(text.encode())`.

    Page one is 14 code points and 25 UTF-8 bytes. A byte-measured span is caught here.
    """
    assert len(PAGE_ONE) == 14
    assert len(PAGE_ONE.encode("utf-8")) == 24
    document = _layer()
    document["pages"][0]["char_end"] = 24
    document["pages"][1]["char_start"] = 24
    document["pages"][1]["char_end"] = 24 + len(PAGE_TWO)
    document["total_char_count"] = 24 + len(PAGE_TWO)
    assert _refusal_reason(document) == "page_span_length_mismatch"


@pytest.mark.parametrize("declared", [30, 32, 0, 55])
def test_a_declared_total_that_disagrees_with_the_spans_is_refused(declared: int) -> None:
    """TL-09. 55 is the UTF-8 byte length - the figure a byte-counting producer would write."""
    assert _refusal_reason(_layer(total_char_count=declared)) == "total_char_count_mismatch"


def test_an_absent_total_char_count_is_permitted() -> None:
    """The negative half: the field is optional, and only a *disagreeing* one is refused."""
    document = _layer()
    del document["total_char_count"]
    assert load_text_layer(document).total_char_count == 31


def test_every_refusal_reason_is_distinct_from_the_others_it_could_be_confused_with() -> None:
    """Field is not reason.

    All nine refusals share `ErrorCode.ANALYSIS_INPUT_INVALID`, so a test asserting only the
    code would pass whichever check fired. These are the reasons this file distinguishes.
    """
    observed = {
        _refusal_reason(_layer(artifact_role="geometry.block_index")),
        _refusal_reason(_layer(artifact_version="2.0.0")),
        _refusal_reason(_layer(normalization={})),
        _refusal_reason(_layer(pages=[])),
        _refusal_reason(_layer(total_char_count=99)),
    }
    assert observed == {
        "artifact_role_unexpected",
        "artifact_version_unsupported",
        "normalization_undeclared",
        "text_layer_empty",
        "total_char_count_mismatch",
    }
