"""``analysis.text.artifact``: every refusal that stands between the model and ``B4``.

`W10-ANL` mutation sweep, rows AR-01 to AR-08, AR-10, AR-11 and TL-13/TL-14. **Every one of
the seven refusals in `build_text_observations` and `_validate_anchor` was green** across
`tests/integration/analysis_engine`, `tests/integration/analysis_text` and `tests/replay` —
and so was deleting the `_validate_anchor(text_layer, anchor)` call outright (AR-08), which
removes four of them at once.

This module's docstring says it plainly: this artifact is `B4`'s **only** input, the gate
takes no model input of any other kind, and so "every invariant the gate relies on is checked
here before the document is written, not asserted in a comment". The invariants were checked
in the code and by nothing else.

The existing suites pass a *well-formed* run through and assert the artifact that comes out.
That exercises the happy path of these checks and cannot distinguish a check that fires from
a check that has been deleted. The anchors `resolve_anchor` produces are correct by
construction, so no real run ever presents `_validate_anchor` with a bad one; the guards are
reached here by constructing a `ResolvedAnchor` directly, which is the public dataclass.

Also covers `textlayer.Page.contains` (TL-13, TL-14): loosening either bound by one code
point was green everywhere, and `_validate_anchor`'s `evidence_span_outside_page` is the rule
that depends on it.
"""

from __future__ import annotations

from typing import Any

import pytest

from auditmanager.analysis.text.anchors import ResolvedAnchor
from auditmanager.analysis.text.artifact import Observation, build_text_observations
from auditmanager.analysis.text.config import ProviderMode
from auditmanager.analysis.text.profile import AR_TEXT_PROFILE
from auditmanager.analysis.text.textlayer import load_text_layer
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ModelCallId, RunId

#: Pinned literals, matching guard 4's document so the offsets below are hand-checkable.
PAGE_ONE = "Отчёт за год.\n"   # 14 code points, offsets 0..14
PAGE_TWO = "Выручка выросла.\n"  # 17 code points, offsets 14..31
CATEGORY = "internal_contradiction"
ARTIFACT_ROLE = "analysis.text_observations"
ARTIFACT_VERSION = "1.0.0"


def _text_layer() -> Any:
    return load_text_layer(
        {
            "artifact_role": "prepared.text_layer",
            "artifact_version": "1.0.0",
            "version_uid": "ver_01M2545JSD15ETSNNV904X991J",
            "normalization": {"id": "nfc_v1", "description": "NFC"},
            "total_char_count": 31,
            "pages": [
                {"page_number": 1, "char_start": 0, "char_end": 14, "text": PAGE_ONE},
                {"page_number": 2, "char_start": 14, "char_end": 31, "text": PAGE_TWO},
            ],
        }
    )


#: "Отчёт" lies at document-global 0..5 on page 1. Every figure written out.
GOOD_ANCHOR = ResolvedAnchor(page_number=1, quote="Отчёт", char_start=0, char_end=5)
#: "Выручка" lies at 14..21 on page 2 — page two starts at 14, not at 0.
PAGE_TWO_ANCHOR = ResolvedAnchor(page_number=2, quote="Выручка", char_start=14, char_end=21)


def _observation(**overrides: Any) -> Observation:
    fields: dict[str, Any] = {
        "category": CATEGORY,
        "finding_text": "Две суммы не сходятся.",
        "recommendation_text": "Сверить показатели.",
        "model_call_id": ModelCallId.new(),
        "evidence": (GOOD_ANCHOR,),
    }
    fields.update(overrides)
    return Observation(**fields)


def _build(**overrides: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "run_id": RunId.new(),
        "profile": AR_TEXT_PROFILE,
        "provider_mode": ProviderMode.RECORDED,
        "text_layer": _text_layer(),
        "pages_analysed": [1, 2],
        "observations": [_observation()],
    }
    kwargs.update(overrides)
    return build_text_observations(**kwargs)


def _refusal_reason(**overrides: Any) -> str:
    with pytest.raises(DomainError) as raised:
        _build(**overrides)
    error = raised.value
    assert error.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert error.detail_fields["stage_id"] == "text_analysis"
    return str(error.detail_fields["reason"])


# --- the well-formed artifact -------------------------------------------------------


def test_a_well_formed_artifact_is_written() -> None:
    """The negative half: every refusal below admits the correct document."""
    document = _build()
    assert document["artifact_role"] == ARTIFACT_ROLE
    assert document["artifact_version"] == ARTIFACT_VERSION
    assert document["provider_mode"] == "recorded"
    assert document["pages_analysed"] == [1, 2]
    assert document["observations"][0]["evidence"][0] == {
        "evidence_ordinal": 0,
        "page_number": 1,
        "quote": "Отчёт",
        "char_start": 0,
        "char_end": 5,
    }


def test_block_id_is_absent_rather_than_null_when_no_block_index_bound() -> None:
    """AR-10. Section 4.7 allows the field to be absent; a null is a different claim."""
    item = _build()["observations"][0]["evidence"][0]
    assert "block_id" not in item


def test_block_id_is_written_when_the_anchor_carries_one() -> None:
    anchored = ResolvedAnchor(
        page_number=1, quote="Отчёт", char_start=0, char_end=5, block_id="b_000001"
    )
    item = _build(observations=[_observation(evidence=(anchored,))])["observations"][0][
        "evidence"
    ][0]
    assert item["block_id"] == "b_000001"


def test_pages_analysed_is_sorted_and_deduplicated() -> None:
    """AR-11."""
    assert _build(pages_analysed=[2, 1, 2, 1])["pages_analysed"] == [1, 2]


# --- the refusals -------------------------------------------------------------------


@pytest.mark.parametrize("pages", [[3], [1, 3], [0], [-1], [1, 2, 3]])
def test_pages_analysed_naming_an_unknown_page_is_refused(pages: list[int]) -> None:
    """AR-01."""
    assert _refusal_reason(pages_analysed=pages) == "pages_analysed_unknown"


def test_an_observation_with_no_evidence_is_refused() -> None:
    """AR-02. Section 4.7: evidence-free is *malformed*, not "ungrounded"."""
    assert (
        _refusal_reason(observations=[_observation(evidence=())])
        == "observation_without_evidence"
    )


@pytest.mark.parametrize(
    "category", ["unsupported_claim", "explicit_placeholder_x", "", "INTERNAL_CONTRADICTION"]
)
def test_a_category_the_profile_does_not_declare_is_refused(category: str) -> None:
    """AR-03."""
    assert (
        _refusal_reason(observations=[_observation(category=category)])
        == "category_not_declared"
    )


def test_evidence_citing_a_page_the_text_layer_does_not_carry_is_refused() -> None:
    """AR-04 and AR-08."""
    anchor = ResolvedAnchor(page_number=7, quote="Отчёт", char_start=0, char_end=5)
    assert (
        _refusal_reason(observations=[_observation(evidence=(anchor,))])
        == "evidence_page_unknown"
    )


@pytest.mark.parametrize("char_end", [4, 6, 0, 31])
def test_a_span_whose_length_is_not_the_quotation_length_is_refused(char_end: int) -> None:
    """AR-05 and AR-08. "Отчёт" is 5 code points, so only 0..5 is honest."""
    assert len("Отчёт") == 5
    anchor = ResolvedAnchor(page_number=1, quote="Отчёт", char_start=0, char_end=char_end)
    assert (
        _refusal_reason(observations=[_observation(evidence=(anchor,))])
        == "evidence_span_length_mismatch"
    )


def test_a_span_that_leaves_its_declared_page_by_one_code_point_is_refused() -> None:
    """AR-06, AR-08, TL-13 and TL-14 — the off-by-one on the page boundary.

    Page one is 0..14 and page two is 14..31. The seven code points at document-global
    14..21 are "Выручка", and they are on page **two**. An evidence item that cites them
    as page one is off the end of its declared page by exactly the amount that matters,
    and `Page.contains` is the rule that must catch it.
    """
    layer = _text_layer()
    assert layer.slice(14, 21) == "Выручка"
    off_the_end = ResolvedAnchor(
        page_number=1, quote="Выручка", char_start=14, char_end=21
    )
    assert (
        _refusal_reason(observations=[_observation(evidence=(off_the_end,))])
        == "evidence_span_outside_page"
    )


def test_a_span_that_starts_one_code_point_before_its_page_is_refused() -> None:
    """TL-13: the lower bound of `Page.contains`.

    Page two is 14..31. A span at 13..20 begins one code point inside page one.
    """
    layer = _text_layer()
    quote = layer.slice(13, 20)
    straddling = ResolvedAnchor(
        page_number=2, quote=quote, char_start=13, char_end=20
    )
    assert (
        _refusal_reason(observations=[_observation(evidence=(straddling,))])
        == "evidence_span_outside_page"
    )


def test_a_span_that_does_not_slice_back_to_its_own_quotation_is_refused() -> None:
    """AR-07 and AR-08. Right length, right page, wrong text."""
    layer = _text_layer()
    assert layer.slice(2, 7) != "Отчёт"
    wrong_text = ResolvedAnchor(page_number=1, quote="Отчёт", char_start=2, char_end=7)
    assert (
        _refusal_reason(observations=[_observation(evidence=(wrong_text,))])
        == "evidence_quotation_mismatch"
    )


def test_the_four_anchor_refusals_are_distinguishable_from_one_another() -> None:
    """Field is not reason.

    All four `_validate_anchor` refusals share `ErrorCode.ANALYSIS_INPUT_INVALID` and
    `stage_id`, so a test asserting only those would pass whichever fired — which is how a
    deleted check survives a sweep. These are the four reasons, and they are distinct.
    """
    layer = _text_layer()
    reasons = {
        _refusal_reason(
            observations=[
                _observation(
                    evidence=(ResolvedAnchor(page_number=7, quote="Отчёт", char_start=0, char_end=5),)
                )
            ]
        ),
        _refusal_reason(
            observations=[
                _observation(
                    evidence=(ResolvedAnchor(page_number=1, quote="Отчёт", char_start=0, char_end=6),)
                )
            ]
        ),
        _refusal_reason(
            observations=[
                _observation(
                    evidence=(ResolvedAnchor(page_number=1, quote="Выручка", char_start=14, char_end=21),)
                )
            ]
        ),
        _refusal_reason(
            observations=[
                _observation(
                    evidence=(ResolvedAnchor(page_number=1, quote="Отчёт", char_start=2, char_end=7),)
                )
            ]
        ),
    }
    assert reasons == {
        "evidence_page_unknown",
        "evidence_span_length_mismatch",
        "evidence_span_outside_page",
        "evidence_quotation_mismatch",
    }
    assert layer.total_char_count == 31
