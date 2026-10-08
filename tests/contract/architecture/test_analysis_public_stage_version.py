"""Keep the analysis public version name scoped to the stage it describes."""

from auditmanager.analysis import public as analysis_public
from auditmanager.analysis.text.stage import STAGE_VERSION as text_stage_version
from auditmanager.runs import executor


def test_text_stage_version_has_a_precise_public_name() -> None:
    assert analysis_public.TEXT_STAGE_VERSION == text_stage_version
    assert "TEXT_STAGE_VERSION" in analysis_public.__all__
    assert "STAGE_VERSION" not in analysis_public.__all__
    assert not hasattr(analysis_public, "STAGE_VERSION")
    assert executor.TEXT_STAGE_VERSION == text_stage_version
