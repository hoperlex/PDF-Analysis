"""`R-48`'s policy, pure: length and the blocklist's first two entries, no database.

The third blocklist entry -- the current password -- is enforced by
:func:`auditmanager.access.repository.UserRepository.change_password`, not by
:func:`~auditmanager.access.policy.enforce_password_policy`, and is exercised together
with the rest of that method's five steps in
``tests/integration/db/test_app_user_repository.py``'s
``TestChangingAPasswordUnderTheR48Policy``, which also carries the `D-101` gap test.
"""

from __future__ import annotations

import pytest

from auditmanager.access.policy import (
    MIN_PASSWORD_LENGTH,
    PRODUCT_NAME,
    enforce_password_policy,
)
from auditmanager.shared.errors import DomainError, ErrorCode


def test_the_floor_is_eight() -> None:
    """Pinned as a value and not just as behaviour: `R-48` names the number itself."""
    assert MIN_PASSWORD_LENGTH == 8


def test_the_product_name_is_auditmanager() -> None:
    assert PRODUCT_NAME == "AuditManager"


class TestLength:
    def test_seven_characters_is_refused(self) -> None:
        with pytest.raises(DomainError) as caught:
            enforce_password_policy("abcdefg", login="someone")
        assert caught.value.code is ErrorCode.VALIDATION_FAILED

    def test_eight_characters_clears_the_floor(self) -> None:
        # Long enough, not the login, not the product name: nothing left to refuse it.
        enforce_password_policy("abcdefgh", login="someone")

    def test_an_empty_password_is_refused_by_length_before_anything_else(self) -> None:
        with pytest.raises(DomainError) as caught:
            enforce_password_policy("", login="")
        assert caught.value.code is ErrorCode.VALIDATION_FAILED


class TestTheLoginEntry:
    def test_the_exact_login_is_refused(self) -> None:
        with pytest.raises(DomainError) as caught:
            enforce_password_policy("reviewer1", login="reviewer1")
        assert caught.value.code is ErrorCode.VALIDATION_FAILED

    def test_the_login_in_a_different_case_is_still_refused(self) -> None:
        with pytest.raises(DomainError):
            enforce_password_policy("Reviewer1", login="reviewer1")

    def test_a_password_that_merely_contains_the_login_is_not_refused(self) -> None:
        """Contextual means "is", not "contains" -- `R-48` names one exact fact per entry,
        not a substring rule the owner was never asked about."""
        enforce_password_policy("reviewer1-plus-more", login="reviewer1")


class TestTheProductNameEntry:
    def test_the_exact_product_name_is_refused(self) -> None:
        with pytest.raises(DomainError) as caught:
            enforce_password_policy("AuditManager", login="someone")
        assert caught.value.code is ErrorCode.VALIDATION_FAILED

    def test_the_product_name_in_another_case_is_still_refused(self) -> None:
        with pytest.raises(DomainError):
            enforce_password_policy("auditmanager", login="someone")
        with pytest.raises(DomainError):
            enforce_password_policy("AUDITMANAGER", login="someone")


def test_an_unrelated_password_of_legal_length_is_accepted() -> None:
    enforce_password_policy("correct-horse-battery", login="someone")
