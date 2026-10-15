"""Decision policy before W59 persistence and contract reseal."""

from __future__ import annotations

import pytest

from auditmanager.sections.confirmation import (
    ExpertSectionConfirmation,
    SectionConfirmationPlan,
    SectionConfirmationRefused,
    prepare_section_confirmation,
)
from auditmanager.sections.routing import SectionRouteUnavailable, route_confirmed_section
from auditmanager.sections.suggestion import _catalogue, suggest_sections


VERSION = "ver_01M25P3TH08VVTTGJRXYBZZ7RP"
OTHER_VERSION = "ver_01M25P3TH08VVTTGJRXYBZZ7RQ"
EXPERT = "usr_01M25P3TH08VVTTGJRXYBZZ7RP"
OTHER_EXPERT = "usr_01M25P3TH08VVTTGJRXYBZZ7RQ"


def _prepare(**changes: object) -> SectionConfirmationPlan:
    values = dict(
        version_uid=VERSION,
        code="AR",
        stage="P",
        expert_uid=EXPERT,
        actor_roles=frozenset({"expert"}),
    )
    values.update(changes)
    return prepare_section_confirmation(**values)  # type: ignore[arg-type]


def test_all_fifteen_codes_are_eligible_for_explicit_confirmation() -> None:
    codes = {item.code for item in _catalogue()}
    assert len(codes) == 15
    assert {"AR", "PS", "PB"}.issubset(codes)
    for code in codes:
        plan = _prepare(code=code)
        assert plan.action == "insert"
        assert plan.confirmation == ExpertSectionConfirmation(VERSION, code, "P", EXPERT)


def test_explicit_ps_choice_overrides_ar_filename_suggestion() -> None:
    assert suggest_sections("01-АР-Планы.pdf", "")[0].code == "AR"
    plan = _prepare(code="PS", stage="R")
    assert plan.confirmation == ExpertSectionConfirmation(VERSION, "PS", "R", EXPERT)


def test_unpersisted_plan_is_not_a_routing_confirmation() -> None:
    plan = _prepare(code="AR")
    with pytest.raises(SectionRouteUnavailable, match="section_confirmation_invalid"):
        route_confirmed_section(
            VERSION,
            plan.confirmation,  # type: ignore[arg-type]
            {"AR": "ap_01M25P3TH08VVTTGJRXYBZZ7RP"},
        )


def test_repeat_keeps_original_expert_and_does_not_request_second_insert() -> None:
    previous = ExpertSectionConfirmation(VERSION, "PB", "R", EXPERT)
    assert _prepare(
        code="PB", stage="R", expert_uid=OTHER_EXPERT, previous=previous
    ) == SectionConfirmationPlan("unchanged", previous)


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"code": "unknown"}, "section_unknown"),
        ({"code": "ПБ"}, "section_unknown"),
        ({"stage": None}, "version_stage_unclassified"),
        ({"stage": ""}, "version_stage_unclassified"),
        ({"stage": "П"}, "version_stage_unclassified"),
        ({"stage": "P "}, "version_stage_unclassified"),
        ({"version_uid": OTHER_EXPERT}, "version_identity_invalid"),
        ({"expert_uid": VERSION}, "expert_identity_invalid"),
        ({"actor_roles": frozenset()}, "expert_role_required"),
        ({"actor_roles": frozenset({"admin"})}, "expert_role_required"),
        ({"actor_roles": "expert"}, "expert_role_required"),
        ({"actor_roles": frozenset({"expert", "unknown"})}, "expert_role_required"),
        (
            {"previous": ExpertSectionConfirmation(OTHER_VERSION, "AR", "P", EXPERT)},
            "previous_confirmation_version_mismatch",
        ),
        (
            {"previous": ExpertSectionConfirmation(VERSION, "AR", "R", EXPERT)},
            "previous_confirmation_stage_mismatch",
        ),
        (
            {"previous": ExpertSectionConfirmation(VERSION, "PS", "P", EXPERT)},
            "section_already_confirmed",
        ),
    ],
)
def test_invalid_or_conflicting_decisions_refuse(changes: dict[str, object], reason: str) -> None:
    with pytest.raises(SectionConfirmationRefused, match=f"^{reason}$"):
        _prepare(**changes)
