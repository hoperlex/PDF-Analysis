"""`R-48`'s policy, pure: length and the blocklist's first two entries, no database.

The third blocklist entry -- the current password -- is enforced by
:func:`auditmanager.access.repository.UserRepository.change_password`, not by
:func:`~auditmanager.access.policy.enforce_password_policy`, and is exercised together
with the rest of that method's five steps in
``tests/integration/db/test_app_user_repository.py``'s
``TestChangingAPasswordUnderTheR48Policy``, which also carries the `D-101` test -- the one
that stated the gap and now proves it shut.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from auditmanager.access.policy import (
    MIN_PASSWORD_LENGTH,
    PRODUCT_NAME,
    SHIPPED_DEFAULT_PASSWORD,
    enforce_password_policy,
)
from auditmanager.shared.errors import DomainError, ErrorCode

#: The migration that writes the seeded account. Read, never imported: importing a
#: migration module to reach a constant would be a deep import into another context's
#: internals, and ``db/migrations`` is not this module's to depend on.
SEED_MIGRATION = (
    Path(__file__).resolve().parents[3]
    / "db/migrations/versions/20260922_0006_app_user.py"
)


def test_the_floor_is_eight() -> None:
    """Pinned as a value and not just as behaviour: `R-48` names the number itself."""
    assert MIN_PASSWORD_LENGTH == 8


def test_the_product_name_is_auditmanager() -> None:
    assert PRODUCT_NAME == "AuditManager"


def test_the_shipped_default_is_the_one_the_migration_seeds() -> None:
    """`D-101`. The only blocklist entry with a second copy in this tree, pinned to it.

    :data:`PRODUCT_NAME` is spelled once and has nothing to disagree with. This value
    exists twice -- here, and as ``SEED_PASSWORD`` in the migration that writes the account
    -- and the failure mode of a drift is the quietest kind there is: a blocklist entry
    that refuses nothing, on a deployment that thinks `D-101` is closed.

    The literal is read out of the migration's source rather than imported, so this pins
    the two together without depending on ``db/migrations`` at runtime.
    """
    source = SEED_MIGRATION.read_text(encoding="utf-8")
    seeded = re.search(r'^SEED_PASSWORD = "([^"]*)"', source, re.M)
    assert seeded is not None, (
        f"{SEED_MIGRATION.name} no longer declares SEED_PASSWORD at module level; the "
        "blocklist entry below can no longer be pinned to what is actually seeded"
    )
    assert SHIPPED_DEFAULT_PASSWORD == seeded.group(1), (
        "policy.py's blocklist entry and the password the migration seeds have drifted, "
        "so D-101 is open again and nothing says so"
    )


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


class TestTheShippedDefaultEntry:
    """`D-101`, closed by the owner on 2026-09-29.

    Before it, the shipped default was refused at exactly one moment -- the forced first
    change, where it is the account's own *current* password -- and was legal everywhere
    after that, including being set straight back. `W47-JUDGE-X` §1.3 drove the shape that
    matters against the built API: from the default, ``"Password"`` answered **200
    changed**.
    """

    def test_the_shipped_default_is_refused(self) -> None:
        with pytest.raises(DomainError) as caught:
            enforce_password_policy(SHIPPED_DEFAULT_PASSWORD, login="someone")
        assert caught.value.code is ErrorCode.VALIDATION_FAILED
        assert "ships with" in str(caught.value), str(caught.value)

    def test_it_is_refused_in_any_case(self) -> None:
        """One shift key is the whole distance between the value and the measured bypass."""
        for candidate in ("Password", "PASSWORD", "pAssWord"):
            with pytest.raises(DomainError):
                enforce_password_policy(candidate, login="someone")

    def test_a_password_that_merely_contains_it_is_not_refused(self) -> None:
        """Contextual means "is", not "contains" -- the same rule the login entry follows.
        `R-48` names one exact fact per entry and no substring rule was ever ruled on."""
        enforce_password_policy("password-and-then-some", login="someone")

    def test_the_refusal_is_the_length_one_when_both_would_apply(self) -> None:
        """Order, pinned: length is checked first, so a short candidate gets the message
        about its length rather than one about the shipped default. Two messages that
        could both be true must not be able to disagree about which fired."""
        with pytest.raises(DomainError) as caught:
            enforce_password_policy("passwor", login="someone")
        assert "at least" in str(caught.value), str(caught.value)


def test_an_unrelated_password_of_legal_length_is_accepted() -> None:
    enforce_password_policy("correct-horse-battery", login="someone")
