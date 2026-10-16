"""A review projection must keep every explicit choice separate from evidence."""

from __future__ import annotations

from dataclasses import replace

import pytest

from auditmanager.sections import review
from auditmanager.sections.routing import SectionRouteUnavailable, route_confirmed_section
from auditmanager.sections.suggestion import SectionSuggestion


VERSION = "ver_01M25P3TH08VVTTGJRXYBZZ7RP"


def _packet(filename: str = "комплект.pdf", text: str = "") -> review.SectionReviewPacket:
    return review.prepare_section_review(
        version_uid=VERSION, filename=filename, extracted_text=text
    )


def test_neutral_input_still_offers_all_fifteen_unselected_sections() -> None:
    packet = _packet()
    assert packet.version_uid == VERSION
    assert len(packet.options) == len({option.code for option in packet.options}) == 15
    assert [option.code for option in packet.options] == sorted(
        option.code for option in packet.options
    )
    assert all(option.suggestion is None for option in packet.options)
    assert not hasattr(packet, "confirmed")
    assert not hasattr(packet, "selected")
    assert _packet() == packet


def test_ranked_ar_evidence_does_not_hide_or_preselect_ps_and_pb() -> None:
    packet = _packet("01-АР-Планы.pdf", "фасад")
    by_code = {option.code: option for option in packet.options}
    assert by_code["AR"].suggestion is not None
    assert by_code["AR"].suggestion.filename_patterns
    assert by_code["PS"].name == "Пояснительная записка"
    assert by_code["PB"].name == "Пожарная безопасность"
    assert by_code["PS"].suggestion is None
    assert by_code["PB"].suggestion is None
    with pytest.raises(SectionRouteUnavailable, match="section_confirmation_invalid"):
        route_confirmed_section(
            VERSION, by_code["AR"],  # type: ignore[arg-type]
            {"AR": "ap_01M25P3TH08VVTTGJRXYBZZ7RP"},
        )


def test_ambiguous_evidence_remains_on_two_separate_options() -> None:
    by_code = {option.code: option for option in _packet("АР-КЖ.zip").options}
    assert by_code["AR"].suggestion is not None
    assert by_code["KJ"].suggestion is not None
    assert by_code["AR"].suggestion.score == by_code["KJ"].suggestion.score
    assert sum(option.suggestion is not None for option in by_code.values()) == 2


@pytest.mark.parametrize(
    "values,reason",
    [
        ({"version_uid": "doc_01M25P3TH08VVTTGJRXYBZZ7RP"}, "version_identity_invalid"),
        ({"version_uid": ""}, "version_identity_invalid"),
        ({"version_uid": None}, "version_identity_invalid"),
        ({"filename": None}, "review_evidence_invalid"),
        ({"extracted_text": None}, "review_evidence_invalid"),
    ],
)
def test_invalid_review_inputs_refuse(values: dict[str, object], reason: str) -> None:
    inputs: dict[str, object] = {"version_uid": VERSION, "filename": "a.pdf", "extracted_text": ""}
    inputs.update(values)
    with pytest.raises(review.SectionReviewUnavailable, match=reason):
        review.prepare_section_review(**inputs)  # type: ignore[arg-type]


def test_corrupted_catalogue_or_mismatched_evidence_refuses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalogue = review._catalogue()
    monkeypatch.setattr(review, "_catalogue", lambda: catalogue[:-1] + (catalogue[0],))
    with pytest.raises(review.SectionReviewUnavailable, match="section_catalogue_invalid"):
        _packet()
    monkeypatch.setattr(review, "_catalogue", lambda: catalogue)
    rogue = SectionSuggestion("BAD", "Bad", 1, ("bad",), (), False)
    monkeypatch.setattr(review, "suggest_sections", lambda *_: (rogue,))
    with pytest.raises(review.SectionReviewUnavailable, match="section_suggestion_invalid"):
        _packet()
    real = catalogue[0]
    monkeypatch.setattr(
        review,
        "suggest_sections",
        lambda *_: (replace(rogue, code=real.code),),
    )
    with pytest.raises(review.SectionReviewUnavailable, match="section_suggestion_invalid"):
        _packet()
