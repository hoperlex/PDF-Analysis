"""`AR-V3-OPT-IN` (design 4.2): the deployment's allowance to start AR v3, container-free.

The value rules are strict -- a value that silently read as «on» would be a permission nobody gave -- and the refusal
is the start's own: ``409 conflict`` with a typed ``conflict_reason``, only while a pack is installed (a deployment
without a pack keeps the answer it always had).
"""

from __future__ import annotations

import pytest

from auditmanager.runs.v3_start_switch import (
    CONFLICT_MEMBER_NOT_REPEATABLE,
    CONFLICT_START_NOT_ENABLED,
    START_ALLOWED_ENV,
    parse_start_allowed,
    refuse_member_repeat,
    require_start_allowed,
)
from auditmanager.shared.errors import DomainError, ErrorCode


def test_the_variable_and_the_reasons_are_the_ones_the_contract_names() -> None:
    assert START_ALLOWED_ENV == "AR_V3_BETA_START_ALLOWED"
    assert CONFLICT_START_NOT_ENABLED == "ar_v3_start_not_enabled"
    assert CONFLICT_MEMBER_NOT_REPEATABLE == "ar_v3_member_not_repeatable"


@pytest.mark.parametrize("raw", [None, "", "   ", "0", " 0 ", "\t0\n"])
def test_absent_blank_or_zero_is_off(raw: str | None) -> None:
    assert parse_start_allowed(raw) is False


@pytest.mark.parametrize("raw", ["1", " 1 ", "\n1\t"])
def test_only_one_is_on(raw: str) -> None:
    assert parse_start_allowed(raw) is True


@pytest.mark.parametrize(
    "raw", ["true", "TRUE", "True", "yes", "on", "enabled", "2", "-1", "01", "00", "1x", " 1x", "1 1", "0.0", "1.0", "١"],
)
def test_anything_else_refuses_the_start_and_never_reads_as_on(raw: str) -> None:
    with pytest.raises(ValueError) as refused:
        parse_start_allowed(raw)
    assert START_ALLOWED_ENV in str(refused.value)


def test_a_pack_with_the_allowance_off_is_the_typed_conflict() -> None:
    with pytest.raises(DomainError) as refused:
        require_start_allowed(pack_installed=True, start_allowed=False)
    assert refused.value.code is ErrorCode.CONFLICT
    assert refused.value.detail_fields["conflict_reason"] == "ar_v3_start_not_enabled"


@pytest.mark.parametrize(("pack_installed", "start_allowed"), [(True, True), (False, True), (False, False)])
def test_it_refuses_nothing_else(pack_installed: bool, start_allowed: bool) -> None:
    """With no pack the caller's own «no pack» answer stands; with the allowance on nothing is refused here."""
    require_start_allowed(pack_installed=pack_installed, start_allowed=start_allowed)


def test_the_refusal_of_a_repeat_of_a_member_is_the_typed_conflict() -> None:
    refused = refuse_member_repeat()
    assert refused.code is ErrorCode.CONFLICT
    assert refused.detail_fields["conflict_reason"] == "ar_v3_member_not_repeatable"
