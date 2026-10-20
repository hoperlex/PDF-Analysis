"""`CLASSIFICATION-CORRECTION-01` phase A: the correction rules, with no database.

Every rule of ``auditmanager.sections.correction`` is stated here from the task's outcome and
`W59-SECTION-IDENTITY-DECISION-01` (an append-only correction with actor, reason and revision;
a revision never rewrites the one before it), not read back from the module. A test per guard,
so each can be shown failing under a mutation (the report quotes them): who may correct, what
a correction may change, revision numbering, the exact repeat, the conflicting concurrent
correction, the reason, the stored history that is checked rather than trusted, and the
module's purity.
"""

from __future__ import annotations

import ast
import random
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from typing import Any

import pytest

from auditmanager.sections import correction
from auditmanager.sections import public as sections_public
from auditmanager.sections.correction import (
    ClassificationRevision,
    CorrectionPlan,
    CorrectionRequest,
    changed_fields,
    current_revision,
    normalize_reason,
    plan_classification_correction,
)
from auditmanager.shared.errors import DomainError, ErrorCode

SOURCE = Path(correction.__file__)

VERSION = "ver_01M25P3TH08VVTTGJRXYBZZ7RP"
OTHER_VERSION = "ver_01M25P3TH08VVTTGJRXYBZZ7RQ"
FIRST = "usr_01M25P3TH08VVTTGJRXYBZZ7RP"  # confirmed the original
SECOND = "usr_01M25P3TH08VVTTGJRXYBZZ7RQ"
THIRD = "usr_01M25P3TH08VVTTGJRXYBZZ7RR"
EXPERT = frozenset({"expert"})

#: The fifteen section codes, written out here, not read from the catalogue under test.
FIFTEEN = ("AR", "AI", "KM", "KJ", "OV", "EOM", "VK", "PT", "PB", "SS", "ITP", "GP", "TX", "POS", "PS")
REASON = "Раздел определён по штампу листа неверно"


def original(stage: str = "P", section: str = "AR", actor: str = FIRST) -> ClassificationRevision:
    return ClassificationRevision(VERSION, 1, stage, section, actor, None)


def revision(
    number: int, stage: str, section: str, actor: str = SECOND, reason: str = REASON,
    version: str = VERSION,
) -> ClassificationRevision:
    return ClassificationRevision(version, number, stage, section, actor, reason)


def ask(**changes: Any) -> CorrectionRequest:
    values: dict[str, Any] = dict(
        project_stage="P", section_code="KJ", reason=REASON, expected_revision=1
    )
    values.update(changes)
    return CorrectionRequest(**values)


def plan(
    history: Any = None, *, request: CorrectionRequest | None = None, actor: Any = SECOND,
    roles: Any = EXPERT, version: str = VERSION,
) -> CorrectionPlan:
    return plan_classification_correction(
        version_uid=version,
        history=[original()] if history is None else history,
        request=request or ask(),
        actor_uid=actor,
        actor_roles=roles,
    )


def refusal(call: Any) -> DomainError:
    with pytest.raises(DomainError) as caught:
        call()
    return caught.value


def assert_refused(error: DomainError, code: ErrorCode, **details: Any) -> None:
    assert error.code is code, (error.code, dict(error.detail_fields))
    for key, value in details.items():
        assert error.detail_fields.get(key) == value, (key, dict(error.detail_fields))


# -- who may correct -------------------------------------------------------------------------


def test_an_expert_may_correct_and_need_not_be_the_first_confirmer() -> None:
    appended = plan(actor=SECOND)
    assert appended.action == "append"
    assert appended.revision.actor_user_uid == SECOND != FIRST
    assert plan(actor=FIRST).action == "append"  # the first confirmer may correct their own


def test_admin_alone_is_refused_and_so_is_every_set_that_lacks_expert() -> None:
    for roles in (frozenset({"admin"}), frozenset(), frozenset({"viewer"}), frozenset({"admin", "viewer"})):
        error = refusal(lambda roles=roles: plan(roles=roles))
        assert_refused(error, ErrorCode.PERMISSION_DENIED, required_capability="role:expert")
    assert plan(roles=frozenset({"admin", "expert"})).action == "append"


def test_roles_must_be_a_frozenset_of_known_roles() -> None:
    for roles in ({"expert"}, ["expert"], ("expert",), "expert", None):
        assert_refused(
            refusal(lambda roles=roles: plan(roles=roles)),
            ErrorCode.PERMISSION_DENIED, required_capability="role:expert",
        )


def test_a_role_set_holding_an_unknown_role_is_refused_even_with_expert_in_it() -> None:
    """Authenticated state naming a role the product does not have is corrupt: fail closed."""
    for roles in (frozenset({"expert", "superuser"}), frozenset({"expert", ""})):
        assert_refused(
            refusal(lambda roles=roles: plan(roles=roles)),
            ErrorCode.PERMISSION_DENIED, required_capability="role:expert",
        )


def test_an_invalid_actor_identity_is_refused_as_permission_denied() -> None:
    for actor in ("", "usr_x", "ver_01M25P3TH08VVTTGJRXYBZZ7RP", None, 7):
        assert_refused(
            refusal(lambda actor=actor: plan(actor=actor)),
            ErrorCode.PERMISSION_DENIED, required_capability="role:expert",
        )


def test_authorization_is_decided_before_the_request_and_before_the_version_state() -> None:
    admin = frozenset({"admin"})
    bad_body = ask(project_stage="X", section_code="ZZ", reason="", expected_revision=0)
    assert refusal(lambda: plan(roles=admin, request=bad_body)).code is ErrorCode.PERMISSION_DENIED
    assert refusal(lambda: plan(history=[], roles=admin)).code is ErrorCode.PERMISSION_DENIED
    assert refusal(lambda: plan(roles=admin, request=ask(expected_revision=9))).code is (
        ErrorCode.PERMISSION_DENIED
    )


# -- what a correction may change ------------------------------------------------------------


@pytest.mark.parametrize(
    ("stage", "section", "changed"),
    [
        ("R", "AR", {"project_stage"}),
        ("P", "KJ", {"section_code"}),
        ("R", "KJ", {"project_stage", "section_code"}),
    ],
)
def test_a_correction_may_change_the_stage_the_section_or_both(
    stage: str, section: str, changed: set[str]
) -> None:
    appended = plan(request=ask(project_stage=stage, section_code=section))
    assert appended.action == "append"
    assert appended.changed == frozenset(changed)
    assert (appended.revision.project_stage, appended.revision.section_code) == (stage, section)


@pytest.mark.parametrize("code", FIFTEEN)
def test_every_one_of_the_fifteen_sections_is_a_valid_target(code: str) -> None:
    current = "KJ" if code == "AR" else "AR"
    appended = plan(history=[original(section=current)], request=ask(section_code=code))
    assert appended.revision.section_code == code


@pytest.mark.parametrize("section", ["", "XX", "ar", "Ar", " AR", "AR ", None, 5, ["AR"], "PSS"])
def test_an_unknown_section_is_validation_failed(section: Any) -> None:
    error = refusal(lambda: plan(request=ask(section_code=section)))
    assert_refused(error, ErrorCode.VALIDATION_FAILED, field="section_code", constraint="enum")


@pytest.mark.parametrize("stage", ["", "p", "r", "PR", "X", " P", None, 1, ["P"], True])
def test_an_unknown_stage_is_validation_failed(stage: Any) -> None:
    error = refusal(lambda: plan(request=ask(project_stage=stage)))
    assert_refused(error, ErrorCode.VALIDATION_FAILED, field="project_stage", constraint="enum")


def test_a_request_that_is_not_a_correction_request_is_refused() -> None:
    error = refusal(lambda: plan(request={"project_stage": "P"}))  # type: ignore[arg-type]
    assert_refused(error, ErrorCode.VALIDATION_FAILED, field="body", constraint="type")


def test_a_no_op_correction_is_refused_and_writes_nothing() -> None:
    error = refusal(lambda: plan(history=[original("P", "AR")], request=ask(section_code="AR")))
    assert_refused(
        error, ErrorCode.VALIDATION_FAILED, field="section_code", constraint="differs_from_current"
    )


def test_a_no_op_is_judged_against_the_current_classification_not_the_original() -> None:
    history = [original("P", "AR"), revision(2, "P", "KJ")]
    # back to the original values is a legitimate revision 3 ...
    back = plan(history=history, request=ask(section_code="AR", expected_revision=2))
    assert back.action == "append" and back.revision.revision == 3
    # ... and asking for what is current now is the no-op, although it is not the original.
    error = refusal(lambda: plan(history=history, request=ask(section_code="KJ", expected_revision=2)))
    assert_refused(error, ErrorCode.VALIDATION_FAILED, constraint="differs_from_current")


def test_changed_fields_names_exactly_the_differing_values() -> None:
    assert changed_fields("P", "AR", "P", "AR") == frozenset()
    assert changed_fields("P", "AR", "R", "AR") == {"project_stage"}
    assert changed_fields("P", "AR", "P", "KJ") == {"section_code"}
    assert changed_fields("P", "AR", "R", "KJ") == {"project_stage", "section_code"}


# -- revision numbering ----------------------------------------------------------------------


def test_the_first_correction_is_revision_two_and_carries_everything_it_records() -> None:
    appended = plan()
    assert appended.revision == ClassificationRevision(VERSION, 2, "P", "KJ", SECOND, REASON)
    assert not appended.revision.is_original and original().is_original


def test_each_correction_is_the_current_revision_plus_one() -> None:
    history: list[ClassificationRevision] = [original()]
    sections = ["KJ", "AR", "PS", "KJ", "OV"]
    for number, section in enumerate(sections, start=2):
        appended = plan(history=history, request=ask(section_code=section, expected_revision=number - 1))
        assert appended.action == "append"
        assert appended.revision.revision == number
        history.append(appended.revision)
    assert [item.revision for item in history] == [1, 2, 3, 4, 5, 6]
    assert current_revision(VERSION, history) == history[-1]


def test_a_version_without_history_has_no_current_revision() -> None:
    assert current_revision(VERSION, []) is None


def test_correcting_an_unclassified_version_is_a_conflict_that_says_classify_first() -> None:
    error = refusal(lambda: plan(history=[]))
    assert_refused(
        error, ErrorCode.CONFLICT,
        conflict_reason="version_not_classified", aggregate_type="DocumentVersionClassification",
    )


# -- the exact repeat ------------------------------------------------------------------------


def _after(first: CorrectionPlan, base: list[ClassificationRevision] | None = None) -> list[ClassificationRevision]:
    return [*(base or [original()]), first.revision]


def test_an_exact_repeat_answers_the_stored_revision_and_appends_nothing() -> None:
    first = plan()
    stored = _after(first)
    again = plan(history=stored)  # the same actor, values, reason, expected_revision=1
    assert again.action == "unchanged"
    assert again.revision is stored[1]
    assert again.changed == {"section_code"}


def test_the_repeat_is_still_answered_when_someone_else_corrected_afterwards() -> None:
    first = plan()
    later = revision(3, "R", "KJ", actor=THIRD, reason="другая причина")
    again = plan(history=[*_after(first), later])
    assert again.action == "unchanged"
    assert again.revision.revision == 2  # the revision this request created, not the current one


def test_a_repeat_by_another_actor_is_not_a_repeat() -> None:
    stored = _after(plan(actor=SECOND))
    error = refusal(lambda: plan(history=stored, actor=THIRD))
    assert_refused(error, ErrorCode.CONFLICT, conflict_reason="classification_revision_stale")


def test_a_repeat_with_other_target_values_is_not_a_repeat() -> None:
    stored = _after(plan(request=ask(section_code="KJ")))
    for changes in ({"section_code": "TX"}, {"project_stage": "R"}):
        error = refusal(lambda changes=changes: plan(history=stored, request=ask(**changes)))
        assert_refused(error, ErrorCode.CONFLICT, conflict_reason="classification_revision_stale")


def test_a_repeat_with_another_reason_is_refused_and_says_the_first_reason_stands() -> None:
    stored = _after(plan())
    error = refusal(lambda: plan(history=stored, request=ask(reason="совсем другая причина")))
    assert_refused(error, ErrorCode.CONFLICT, conflict_reason="classification_revision_stale")
    assert "different reason" in str(error)


def test_a_repeat_ignores_surrounding_whitespace_in_the_reason() -> None:
    stored = _after(plan(request=ask(reason="  " + REASON + "\n")))
    assert stored[1].reason == REASON  # stored trimmed
    again = plan(history=stored, request=ask(reason=REASON))
    assert again.action == "unchanged"


def test_asking_for_the_current_values_again_at_the_current_revision_is_a_no_op_not_a_repeat() -> None:
    stored = _after(plan())
    error = refusal(lambda: plan(history=stored, request=ask(expected_revision=2)))
    assert_refused(error, ErrorCode.VALIDATION_FAILED, constraint="differs_from_current")


# -- conflicting concurrent corrections ------------------------------------------------------


def test_two_experts_correcting_the_same_revision_the_second_one_conflicts() -> None:
    # both looked at revision 1; the first commit wins, the second meets the new history.
    won = plan(actor=SECOND, request=ask(section_code="KJ"))
    after = _after(won)
    error = refusal(lambda: plan(history=after, actor=THIRD, request=ask(section_code="TX")))
    assert_refused(
        error, ErrorCode.CONFLICT,
        conflict_reason="classification_revision_stale", aggregate_type="DocumentVersionClassification",
    )
    assert "revision 2" in str(error)


def test_the_loser_conflicts_even_when_they_asked_for_the_same_values() -> None:
    after = _after(plan(actor=SECOND))
    error = refusal(lambda: plan(history=after, actor=THIRD))  # same values, another expert
    assert_refused(error, ErrorCode.CONFLICT, conflict_reason="classification_revision_stale")


def test_a_stale_expected_revision_conflicts_against_a_longer_history() -> None:
    history = [original(), revision(2, "P", "KJ"), revision(3, "R", "KJ", actor=THIRD)]
    error = refusal(lambda: plan(history=history, request=ask(section_code="TX", expected_revision=2)))
    assert_refused(error, ErrorCode.CONFLICT, conflict_reason="classification_revision_stale")
    assert "revision 3" in str(error)


def test_an_expected_revision_ahead_of_the_history_is_validation_failed() -> None:
    error = refusal(lambda: plan(request=ask(expected_revision=2)))
    assert_refused(
        error, ErrorCode.VALIDATION_FAILED,
        field="expected_revision", constraint="exceeds_current_revision",
    )


@pytest.mark.parametrize("expected", [0, -1, -100])
def test_an_expected_revision_below_one_is_validation_failed(expected: int) -> None:
    error = refusal(lambda: plan(request=ask(expected_revision=expected)))
    assert_refused(error, ErrorCode.VALIDATION_FAILED, field="expected_revision", constraint="minimum")


@pytest.mark.parametrize("expected", [True, False, 1.0, "1", None, [1], 1.5])
def test_an_expected_revision_must_be_a_plain_integer(expected: Any) -> None:
    error = refusal(lambda: plan(request=ask(expected_revision=expected)))
    assert_refused(error, ErrorCode.VALIDATION_FAILED, field="expected_revision", constraint="type")


# -- the reason ------------------------------------------------------------------------------


@pytest.mark.parametrize("reason", ["", " ", "   \t\n ", "  "])
def test_a_blank_reason_is_required(reason: str) -> None:
    error = refusal(lambda: plan(request=ask(reason=reason)))
    assert_refused(error, ErrorCode.VALIDATION_FAILED, field="reason", constraint="required")


@pytest.mark.parametrize("reason", [None, 5, b"x", ["причина"]])
def test_a_reason_must_be_text(reason: Any) -> None:
    error = refusal(lambda: plan(request=ask(reason=reason)))
    assert_refused(error, ErrorCode.VALIDATION_FAILED, field="reason", constraint="type")


@pytest.mark.parametrize("reason", [".", "...", "-", "?!", "​", "​​.", "№ ", "§"])
def test_a_reason_without_a_letter_or_digit_is_not_a_reason(reason: str) -> None:
    error = refusal(lambda: plan(request=ask(reason=reason)))
    assert_refused(error, ErrorCode.VALIDATION_FAILED, field="reason", constraint="required")


def test_the_reason_is_trimmed_before_it_is_stored() -> None:
    appended = plan(request=ask(reason="\n  " + REASON + "  \t"))
    assert appended.revision.reason == REASON
    assert normalize_reason(" а ") == "а"


def test_the_reason_is_bounded_at_exactly_the_documented_length() -> None:
    assert correction.MAX_REASON_LENGTH == 2000
    longest = "а" * 2000
    assert plan(request=ask(reason=longest)).revision.reason == longest
    error = refusal(lambda: plan(request=ask(reason=longest + "а")))
    assert_refused(error, ErrorCode.VALIDATION_FAILED, field="reason", constraint="max_length")


def test_the_bound_applies_after_trimming_not_before() -> None:
    padded = "  " + "а" * 2000 + "  "
    assert len(padded) > 2000
    assert plan(request=ask(reason=padded)).revision.reason == "а" * 2000


@pytest.mark.parametrize("bad", ["\x00", "\x07", "\x1b", "\x7f", "\x85", "\ud800", "\udfff"])
def test_control_and_surrogate_characters_are_refused_inside_a_reason(bad: str) -> None:
    error = refusal(lambda: plan(request=ask(reason=f"до {bad} после")))
    assert_refused(error, ErrorCode.VALIDATION_FAILED, field="reason", constraint="printable")


def test_line_breaks_and_tabs_are_allowed_inside_a_reason() -> None:
    text = "первая строка\r\nвторая\tстрока"
    assert plan(request=ask(reason=text)).revision.reason == text


# -- a stored history is checked, not trusted ------------------------------------------------


def _internal(history: list[Any]) -> DomainError:
    error = refusal(lambda: plan(history=history))
    assert error.code is ErrorCode.INTERNAL_ERROR, (error.code, dict(error.detail_fields))
    return error


def test_a_history_with_a_gap_a_duplicate_or_a_late_start_is_an_integrity_fault() -> None:
    _internal([original(), revision(3, "P", "KJ")])
    _internal([original(), revision(2, "P", "KJ"), revision(2, "R", "KJ")])
    _internal([revision(2, "P", "KJ")])
    _internal([original(), revision(1, "P", "KJ")])


def test_a_history_naming_another_version_is_an_integrity_fault() -> None:
    _internal([original(), revision(2, "P", "KJ", version=OTHER_VERSION)])


def test_a_history_that_repeats_the_values_of_the_revision_before_it_is_an_integrity_fault() -> None:
    _internal([original("P", "AR"), revision(2, "P", "AR")])
    _internal([original(), revision(2, "P", "KJ"), revision(3, "P", "KJ", actor=THIRD)])


def test_reasons_follow_the_original_and_correction_split() -> None:
    _internal([replace(original(), reason="причина")])
    _internal([original(), replace(revision(2, "P", "KJ"), reason=None)])
    _internal([original(), replace(revision(2, "P", "KJ"), reason="")])
    _internal([original(), replace(revision(2, "P", "KJ"), reason=" с пробелом ")])


def test_a_history_with_values_or_actors_outside_the_catalogue_is_an_integrity_fault() -> None:
    _internal([replace(original(), section_code="XX")])
    _internal([replace(original(), project_stage="Q")])
    _internal([replace(original(), actor_user_uid="admin")])
    _internal([original(), "not a revision"])


def test_a_malformed_version_identity_is_an_integrity_fault_not_a_caller_error() -> None:
    error = refusal(lambda: plan(version="ver_nope"))
    assert error.code is ErrorCode.INTERNAL_ERROR


def test_a_corrupt_history_never_yields_a_plan_even_for_a_repeat() -> None:
    stored = _after(plan())
    broken = [stored[0], replace(stored[1], revision=3)]
    assert refusal(lambda: plan(history=broken)).code is ErrorCode.INTERNAL_ERROR


# -- values ----------------------------------------------------------------------------------


def test_plans_and_revisions_are_immutable_values_and_planning_changes_nothing() -> None:
    history = [original(), revision(2, "P", "KJ")]
    snapshot = list(history)
    first = plan(history=history, request=ask(section_code="TX", expected_revision=2))
    second = plan(history=history, request=ask(section_code="TX", expected_revision=2))
    assert history == snapshot
    assert first == second
    with pytest.raises(FrozenInstanceError):
        first.action = "unchanged"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        first.revision.revision = 9  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        ask().reason = "x"  # type: ignore[misc]


def test_the_history_may_be_any_sequence_but_is_read_in_order() -> None:
    history = (original(), revision(2, "P", "KJ"))
    appended = plan(history=history, request=ask(section_code="TX", expected_revision=2))
    assert appended.revision.revision == 3


# -- the whole machine, simulated ------------------------------------------------------------


def test_a_long_random_run_of_concurrent_looking_requests_keeps_every_invariant() -> None:
    """Three experts, stale and fresh reads, retries: the history only ever grows by one."""
    rng = random.Random(20261020)
    history: list[ClassificationRevision] = [original()]
    experts = (FIRST, SECOND, THIRD)
    appended_requests: list[tuple[str, str, str, str, int, int]] = []
    outcomes = {"append": 0, "unchanged": 0, "conflict": 0, "validation": 0}
    for step in range(1500):
        actor = rng.choice(experts)
        if appended_requests and rng.random() < 0.25:  # a retry of something that succeeded
            who, stage, section, reason, expected, number = rng.choice(appended_requests)
            before = list(history)
            result = plan(
                history=history, actor=who,
                request=ask(project_stage=stage, section_code=section, reason=reason, expected_revision=expected),
            )
            assert result.action == "unchanged" and result.revision.revision == number
            assert history == before
            outcomes["unchanged"] += 1
            continue
        current = history[-1].revision
        expected = rng.choice([current, current, current, max(1, current - rng.randint(0, 3)), current + 1])
        stage, section = rng.choice("PR"), rng.choice(FIFTEEN)
        reason = f"причина {step}"
        before = list(history)
        try:
            result = plan(
                history=history, actor=actor,
                request=ask(project_stage=stage, section_code=section, reason=reason, expected_revision=expected),
            )
        except DomainError as error:
            assert history == before, "a refusal must write nothing"
            if error.code is ErrorCode.CONFLICT:
                assert expected < current
                outcomes["conflict"] += 1
            else:
                assert error.code is ErrorCode.VALIDATION_FAILED
                assert expected > current or (stage, section) == (
                    history[-1].project_stage, history[-1].section_code
                )
                outcomes["validation"] += 1
            continue
        assert result.action == "append" and expected == current
        assert result.revision.revision == current + 1
        assert (result.revision.project_stage, result.revision.section_code) != (
            history[-1].project_stage, history[-1].section_code
        )
        history.append(result.revision)
        appended_requests.append((actor, stage, section, reason, expected, result.revision.revision))
        outcomes["append"] += 1
        assert current_revision(VERSION, history) == history[-1]
    assert [item.revision for item in history] == list(range(1, len(history) + 1))
    assert history[0] == original(), "the original confirmation is never rewritten"
    assert all(value > 20 for value in outcomes.values()), outcomes


# -- the module is pure ----------------------------------------------------------------------

PURE_IMPORTS = {
    "__future__",
    "unicodedata",
    "collections.abc",
    "dataclasses",
    "typing",
    "auditmanager.access.public",
    "auditmanager.sections.suggestion",
    "auditmanager.shared.errors",
    "auditmanager.shared.identity",
}


def test_the_module_imports_no_database_store_clock_or_network_code() -> None:
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.module is not None and node.level == 0
            imported.add(node.module)
    assert imported <= PURE_IMPORTS, sorted(imported - PURE_IMPORTS)


def test_the_rules_are_reachable_through_the_sections_public_surface() -> None:
    for name in (
        "plan_classification_correction", "CorrectionRequest", "CorrectionPlan",
        "ClassificationRevision", "CONFLICT_REVISION_STALE", "CONFLICT_VERSION_NOT_CLASSIFIED",
        "MAX_REASON_LENGTH", "ORIGINAL_REVISION",
    ):
        assert name in sections_public.__all__
        assert getattr(sections_public, name) is getattr(correction, name)


def test_the_vocabulary_the_contract_and_the_migration_will_restate() -> None:
    assert correction.PROJECT_STAGES == ("P", "R")
    assert correction.ORIGINAL_REVISION == 1
    assert correction.CONFLICT_REVISION_STALE == "classification_revision_stale"
    assert correction.CONFLICT_VERSION_NOT_CLASSIFIED == "version_not_classified"
    assert correction.CAPABILITY_EXPERT == "role:expert"
    from auditmanager.sections.suggestion import _catalogue

    assert tuple(sorted(entry.code for entry in _catalogue())) == tuple(sorted(FIFTEEN))
