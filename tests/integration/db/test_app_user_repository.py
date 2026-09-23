"""``UserRepository`` against a real database: lookup, authentication, creation.

These live beside the migration suite rather than under ``tests/integration/access``
because the fixtures that build a throwaway migrated database are defined in this
directory's ``conftest.py`` and are not exported anywhere else. Splitting the file away
from its fixtures would mean copying them, and two copies of "make an empty database"
drift.

The pure, database-free half of this boundary -- hashing, comparison, login folding --
is asserted in ``tests/integration/access/test_password_hashing.py``.
"""

from __future__ import annotations

import logging

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from auditmanager.access.models import UserUid
from auditmanager.access.passwords import ITERATIONS
from auditmanager.access.ports import UserRepository as UserRepositoryPort
from auditmanager.access.repository import DEFAULT_CREDENTIAL_WARNING, UserRepository
from auditmanager.shared.errors import DomainError, ErrorCode

SEED_LOGIN = "admin"
SEED_PASSWORD = "password"  # noqa: S105 - the documented default


@pytest.fixture
def repository() -> UserRepository:
    return UserRepository()


@pytest.fixture
def session(migrated_engine: Engine):
    with Session(migrated_engine) as session:
        yield session


def test_the_adapter_satisfies_the_port(repository: UserRepository) -> None:
    """The port is a ``runtime_checkable`` Protocol, so this checks the method names
    exist. It is not a signature check -- that is what the calls below are."""
    assert isinstance(repository, UserRepositoryPort)


class TestFindingAUser:
    def test_the_seeded_account_is_found_and_flagged(
        self, repository: UserRepository, session: Session
    ) -> None:
        found = repository.find_by_login(session, SEED_LOGIN)
        assert found is not None
        assert found.login == SEED_LOGIN
        assert found.is_default_credential is True
        assert str(found.user_uid).startswith("usr_")
        assert found.created_at == found.password_updated_at

    def test_the_login_is_folded_before_the_lookup(
        self, repository: UserRepository, session: Session
    ) -> None:
        for spelling in ("ADMIN", " Admin ", "aDmIn"):
            found = repository.find_by_login(session, spelling)
            assert found is not None, f"{spelling!r} did not reach the seeded account"
            assert found.login == SEED_LOGIN

    def test_an_absent_login_is_none(
        self, repository: UserRepository, session: Session
    ) -> None:
        assert repository.find_by_login(session, "nobody") is None

    def test_an_impossible_login_raises_rather_than_answering_none(
        self, repository: UserRepository, session: Session
    ) -> None:
        """"This cannot be a login" and "no such user" are different facts. Collapsing
        them would make a caller's typo look like a missing account."""
        with pytest.raises(DomainError) as caught:
            repository.find_by_login(session, "-nope!")
        assert caught.value.code is ErrorCode.VALIDATION_FAILED

    def test_the_record_carries_no_credential_material(
        self, repository: UserRepository, session: Session
    ) -> None:
        found = repository.find_by_login(session, SEED_LOGIN)
        assert found is not None
        fields = set(type(found).__dataclass_fields__)
        assert fields == {
            "user_uid",
            "login",
            "is_default_credential",
            "created_at",
            "password_updated_at",
            # `W39-REVOKE`. Two fields, and neither is credential material: `token_epoch` is
            # a counter the seam stamps into every credential it mints and compares on every
            # request, so it is *meant* to travel, and `token_epoch_updated_at` is when it
            # last moved. What this assertion is about is the four columns that must never
            # appear -- the algorithm, the iteration count, the salt and the digest -- and
            # the way it says so is by being a closed set that reports anything new. It did.
            "token_epoch",
            "token_epoch_updated_at",
            # `W40-LIMIT`. Three more, and none of them is credential material either:
            # they say how often somebody has been wrong and until when the door is shut,
            # never what the password is. They are on the record because the operator's two
            # views of a lockout read them -- `access.check` and `access.unlock` -- and a
            # refusal state nobody can see is one nobody can answer for. The assertion is
            # still about the four columns that must never appear, and the way it says so
            # is still by being a closed set that reports anything new. It did, twice.
            "failed_sign_ins",
            "last_failed_sign_in_at",
            "sign_in_blocked_until",
            # `R-37`. The fourth arrival, and this assertion reported it too -- three
            # waves, three reports, which is what a closed set is for. A display name is
            # not credential material by an even wider margin than the six above: it is a
            # string chosen to be *shown to other people*, and it travels on purpose, in
            # the signed credential, so that a decision can be attributed to a name rather
            # than to a login. It is nullable, and the NULL is the state itself -- "this
            # reviewer has chosen no name" -- which is why `display_label` and not this
            # field is what anything reads.
            "display_name",
        }, "a credential column reached the record the boundary hands out"
        for forbidden in (
            "password_algorithm",
            "password_iterations",
            "password_salt",
            "password_hash",
        ):
            assert forbidden not in fields, forbidden


class TestAuthentication:
    def test_the_seeded_password_authenticates(
        self, repository: UserRepository, session: Session
    ) -> None:
        user = repository.authenticate(session, SEED_LOGIN, SEED_PASSWORD)
        assert user is not None
        assert user.login == SEED_LOGIN

    @pytest.mark.parametrize(
        "password",
        ["Password", "password ", "passwor", "", "x" * 2000],
        ids=["case", "trailing-space", "prefix", "empty", "over-long"],
    )
    def test_a_wrong_password_is_refused(
        self, repository: UserRepository, session: Session, password: str
    ) -> None:
        """Including the two that are not wrong so much as impossible: an empty and an
        over-long candidate are failed attempts, not server faults."""
        assert repository.authenticate(session, SEED_LOGIN, password) is None

    def test_an_unknown_login_and_a_wrong_password_are_the_same_answer(
        self, repository: UserRepository, session: Session
    ) -> None:
        assert repository.authenticate(session, "ghost", SEED_PASSWORD) is None
        assert repository.authenticate(session, SEED_LOGIN, "wrong") is None

    def test_a_malformed_login_does_not_raise_out_of_authenticate(
        self, repository: UserRepository, session: Session
    ) -> None:
        """``find_by_login`` raises on a login that cannot exist; ``authenticate`` must
        not, or the sign-in form answers "that is not even a login" and enumeration is
        back by another route."""
        assert repository.authenticate(session, "-nope!", SEED_PASSWORD) is None

    def test_signing_in_on_the_default_credential_logs_a_warning(
        self, repository: UserRepository, session: Session, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING, logger="auditmanager.access.repository"):
            assert repository.authenticate(session, SEED_LOGIN, SEED_PASSWORD) is not None
        warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert warnings, "a default credential was used and nothing said so"
        message = warnings[0].getMessage()
        assert DEFAULT_CREDENTIAL_WARNING in message
        assert SEED_LOGIN in message

    def test_the_warning_does_not_print_the_password_it_warns_about(
        self, repository: UserRepository, session: Session, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Asserted on an account whose password is a distinctive string.

        It cannot be asserted on the seeded account: its password is the English word
        ``password``, which the warning also uses as prose, so a substring check there
        would fail on a message that leaked nothing. A test that cannot tell the two
        apart is a test that has to be written against different data.
        """
        secret = "zaphod-beeblebrox-42"  # noqa: S105 - a test fixture, not a credential
        repository.create_user(session, "seeded", secret, is_default_credential=True)
        with caplog.at_level(logging.WARNING, logger="auditmanager.access.repository"):
            assert repository.authenticate(session, "seeded", secret) is not None
        messages = [r.getMessage() for r in caplog.records]
        assert any(DEFAULT_CREDENTIAL_WARNING in m for m in messages), messages
        assert not any(secret in m for m in messages), "the warning printed the password"

    def test_an_account_that_is_not_on_a_default_credential_is_quiet(
        self, repository: UserRepository, session: Session, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Otherwise the warning is noise, and noise gets filtered."""
        repository.create_user(session, "auditor", "a-password-of-their-own")
        with caplog.at_level(logging.WARNING, logger="auditmanager.access.repository"):
            assert (
                repository.authenticate(session, "auditor", "a-password-of-their-own")
                is not None
            )
        assert [r for r in caplog.records if DEFAULT_CREDENTIAL_WARNING in r.getMessage()] == []


class TestCreatingAUser:
    def test_a_created_user_can_sign_in_and_nobody_else_can(
        self, repository: UserRepository, session: Session
    ) -> None:
        created = repository.create_user(session, "Auditor", "correct horse battery")
        assert created.login == "auditor", "the login was not folded on the way in"
        assert created.is_default_credential is False
        assert repository.authenticate(session, "auditor", "correct horse battery") is not None
        assert repository.authenticate(session, "auditor", "correct horse batter") is None

    def test_two_users_with_the_same_password_do_not_share_a_digest(
        self, repository: UserRepository, session: Session
    ) -> None:
        """The salt's whole job. Without it, equal digests would publish which accounts
        share a password, and one precomputed table would cover the whole column."""
        repository.create_user(session, "first", "same-password")
        repository.create_user(session, "second", "same-password")
        rows = session.execute(
            text(
                "SELECT password_salt, password_hash FROM app_user "
                "WHERE login IN ('first', 'second')"
            )
        ).all()
        assert len({row[0] for row in rows}) == 2, "two users share a salt"
        assert len({row[1] for row in rows}) == 2, "two users share a digest"

    def test_the_stored_cost_is_the_declared_one(
        self, repository: UserRepository, session: Session
    ) -> None:
        repository.create_user(session, "costed", "a-password")
        stored = session.execute(
            text("SELECT password_iterations FROM app_user WHERE login = 'costed'")
        ).scalar_one()
        assert int(stored) == ITERATIONS

    def test_a_duplicate_login_is_a_conflict(
        self, repository: UserRepository, session: Session
    ) -> None:
        repository.create_user(session, "twice", "a-password")
        with pytest.raises(DomainError) as caught:
            repository.create_user(session, "TWICE", "another-password")
        assert caught.value.code is ErrorCode.CONFLICT
        session.rollback()

    def test_a_malformed_login_is_refused_before_any_hashing(
        self, repository: UserRepository, session: Session
    ) -> None:
        with pytest.raises(DomainError) as caught:
            repository.create_user(session, "not a login", "a-password")
        assert caught.value.code is ErrorCode.VALIDATION_FAILED

    def test_an_empty_password_is_refused(
        self, repository: UserRepository, session: Session
    ) -> None:
        with pytest.raises(DomainError) as caught:
            repository.create_user(session, "empty", "")
        assert caught.value.code is ErrorCode.VALIDATION_FAILED
        assert repository.find_by_login(session, "empty") is None

    def test_the_identity_is_allocated_here_and_is_not_the_login(
        self, repository: UserRepository, session: Session
    ) -> None:
        one = repository.create_user(session, "alpha", "a-password")
        two = repository.create_user(session, "beta", "a-password")
        assert one.user_uid != two.user_uid
        assert isinstance(one.user_uid, UserUid)
        assert one.login not in str(one.user_uid)


class TestTheDefaultCredentialReport:
    def test_it_names_the_seeded_account_only(
        self, repository: UserRepository, session: Session
    ) -> None:
        repository.create_user(session, "auditor", "a-password-of-their-own")
        reported = repository.users_on_default_credentials(session)
        assert [user.login for user in reported] == [SEED_LOGIN]

    def test_clearing_the_flag_empties_the_report(
        self, repository: UserRepository, session: Session
    ) -> None:
        """The column means "still the seeded password", so it must be clearable -- and
        the report must be driven by it rather than by the login being called admin."""
        session.execute(
            text(
                "UPDATE app_user SET is_default_credential = false, "
                "password_updated_at = now() WHERE login = :login"
            ),
            {"login": SEED_LOGIN},
        )
        assert repository.users_on_default_credentials(session) == ()
