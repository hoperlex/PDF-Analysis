"""The additive price/consent wire stays strict and unmetered is explicit."""

import pytest
from pydantic import ValidationError

from auditmanager.api.schemas import models
from auditmanager.api.security import OPERATION_ROLES


def test_cost_consent_requires_exact_digest_integer_ceiling_and_boolean_confirmation():
    valid = {"estimate_digest": "a" * 64, "ceiling_micros": 2_000_000, "confirmed": True}
    assert models.RunCostConsent.model_validate(valid).ceiling_micros == 2_000_000
    for change in ({"ceiling_micros": -1}, {"ceiling_micros": True}, {"ceiling_micros": 1.2},
                   {"confirmed": "yes"}, {"estimate_digest": "bad"}, {"expert_verdict": "accepted"}):
        with pytest.raises(ValidationError):
            models.RunCostConsent.model_validate(valid | change)


def test_cost_requests_preserve_default_off_raised_limit_and_do_not_require_consent_for_read():
    version = "ver_01M2545JSD15ETSNNV904X991J"
    assert models.RunCostEstimateRequest(version_uid=version).relaxed_limits is None
    assert models.ArV3GroupCostEstimateRequest(version_uid=version).relaxed_limits is None
    assert models.StartRunRequest(version_uid=version).cost_consent is None
    assert models.StartArV3BetaGroupRequest(version_uid=version).cost_consent is None


def test_both_estimates_have_the_same_expert_guard_as_their_starts():
    assert OPERATION_ROLES["estimateRunCost"] == OPERATION_ROLES["startRun"]
    assert OPERATION_ROLES["estimateArV3GroupCost"] == OPERATION_ROLES["startArV3BetaGroup"]
    assert models.ReauditRunRequest().cost_consent is None


def test_new_unit_algorithm_keeps_historical_v1_records_readable():
    from typing import get_args
    assert get_args(models.SpecificationMatching.model_fields["algorithm"].annotation) == ("price-match-v1", "price-match-v2")
    assert get_args(models.SectionSpecification.model_fields["match_algorithm"].annotation) == ("price-match-v1", "price-match-v2")
