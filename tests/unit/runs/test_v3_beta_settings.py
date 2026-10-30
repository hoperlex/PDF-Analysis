"""The AR v3 beta generation settings (`D-284`).

The first live Runs ended at exactly 4,096 output tokens on a real АР package and the citation stage refused the
truncated reply; the cap is the largest value the settings class admits.
"""

from __future__ import annotations

import pytest

from auditmanager.analysis.profiles.ar_v3.request_delivery import V3DeliveryRefused, V3GenerationSettings
from auditmanager.runs.v3_worker import V3_BETA_SETTINGS, V3_RELAXED_SETTINGS

#: What the live Runs showed: ``model_call.output_tokens`` 4096 with status ``truncated``, six times in six.
LIVE_TRUNCATION_CAP = 4096


def test_the_beta_output_cap_is_above_what_truncated_the_first_live_runs() -> None:
    assert V3_BETA_SETTINGS.max_output_tokens > LIVE_TRUNCATION_CAP


def test_the_default_beta_output_cap_stays_at_sixteen_thousand() -> None:
    assert V3_BETA_SETTINGS.max_output_tokens == 16_000


def test_the_temporary_relaxed_cap_is_larger_but_provider_bounded() -> None:
    assert V3_RELAXED_SETTINGS.max_output_tokens == 64_000
    with pytest.raises(V3DeliveryRefused):
        V3GenerationSettings(64_001, V3_BETA_SETTINGS.effort, dict(V3_BETA_SETTINGS.thinking))


def test_the_other_beta_settings_are_unchanged() -> None:
    assert V3_BETA_SETTINGS.effort == "high"
    assert dict(V3_BETA_SETTINGS.thinking) == {"type": "adaptive"}
