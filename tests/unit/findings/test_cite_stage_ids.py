"""The citation reader certifies a partition only through a stage it knows."""

from __future__ import annotations

import pytest

from auditmanager.findings.citation_reader import CITE_STAGE_IDS, CitationReadRefused, read_verified_citations


def test_the_two_certifying_stages_are_exactly_the_v1_v2_stage_and_the_ar_v3_beta_stage() -> None:
    assert CITE_STAGE_IDS == {"norm_verification", "ar_v3_citation_review"}


@pytest.mark.parametrize("stage", ["text_analysis", "finding_merge", "", "ar_v3_citation_review ", "AR_V3_CITATION_REVIEW"])
def test_any_other_stage_name_is_refused_before_the_database_is_asked(stage: str) -> None:
    class Untouched:
        def execute(self, *args: object, **kwargs: object) -> None:
            raise AssertionError("the database must not be asked for an unknown stage")

    with pytest.raises(CitationReadRefused, match="cite_stage_unknown"):
        read_verified_citations(
            Untouched(), run_id="run_x", version_uid="ver_x", profile_id="ap_x", cite_stage_id=stage,  # type: ignore[arg-type]
        )
