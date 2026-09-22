"""Hashing, comparison and login folding: everything in this boundary that needs no database.

The database-backed half -- the migration, the seeded account and the repository -- is in
``tests/integration/db/test_app_user_migration.py`` and
``tests/integration/db/test_app_user_repository.py``, where the fixtures that build a
throwaway migrated database live.
"""

from __future__ import annotations

import ast
import hashlib
import inspect

import pytest

from auditmanager.access import models, passwords
from auditmanager.access.models import UserUid, normalize_login
from auditmanager.access.passwords import (
    ALGORITHM,
    DERIVED_KEY_BYTES,
    ITERATIONS,
    MAX_PASSWORD_LENGTH,
    SALT_BYTES,
    StoredPassword,
    hash_password,
    spend_a_verification,
    verify_password,
)
from auditmanager.shared.errors import DomainError, ErrorCode

#: Every test that only needs *a* hash uses this instead of the real cost. 600_000
#: iterations is 0.11 s per derivation on this lane's interpreter, and a suite that paid
#: it forty times would be a suite people start skipping.
CHEAP = 1_000


class TestTheAlgorithmIsTheOneItSaysItIs:
    def test_the_digest_is_pbkdf2_hmac_sha256_over_the_utf8_password(self) -> None:
        """Recomputed independently, straight from :mod:`hashlib`. If this module ever
        started deriving something else -- a different hash, a different key length, the
        salt in the wrong position -- every other test here would still pass."""
        stored = hash_password("correct horse battery", iterations=CHEAP)
        expected = hashlib.pbkdf2_hmac(
            "sha256",
            "correct horse battery".encode("utf-8"),
            bytes.fromhex(stored.salt),
            CHEAP,
            dklen=DERIVED_KEY_BYTES,
        )
        assert stored.digest == expected.hex()
        assert stored.algorithm == ALGORITHM == "pbkdf2_sha256"

    def test_the_declared_cost_is_the_owasp_figure(self) -> None:
        """A number that quietly drops is the failure this catches; it is the one
        parameter whose whole value is being large."""
        assert ITERATIONS == 600_000
        assert SALT_BYTES == 16
        assert DERIVED_KEY_BYTES == 32

    def test_no_third_party_password_library_is_imported(self) -> None:
        """The brief: the standard library has this, and a dependency here does not pay
        for itself.

        Read from the parsed import statements rather than from the source text -- the
        module docstring *names* ``passlib`` to explain why it is absent, and a grep
        cannot tell an explanation from a dependency.
        """
        tree = ast.parse(inspect.getsource(passwords))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        assert imported == {"__future__", "dataclasses", "hashlib", "hmac", "secrets",
                            "typing", "auditmanager"}, imported


class TestSalting:
    def test_the_same_password_hashes_differently_every_time(self) -> None:
        first = hash_password("same", iterations=CHEAP)
        second = hash_password("same", iterations=CHEAP)
        assert first.salt != second.salt
        assert first.digest != second.digest

    def test_the_salt_is_the_declared_width_and_hexadecimal(self) -> None:
        stored = hash_password("anything", iterations=CHEAP)
        assert len(bytes.fromhex(stored.salt)) == SALT_BYTES
        assert len(bytes.fromhex(stored.digest)) == DERIVED_KEY_BYTES


class TestVerification:
    def test_the_right_password_verifies(self) -> None:
        stored = hash_password("s3cret", iterations=CHEAP)
        assert verify_password(stored, "s3cret") is True

    @pytest.mark.parametrize(
        "candidate", ["S3cret", "s3cre", "s3secret", " s3cret", "s3cret "]
    )
    def test_a_near_miss_does_not_verify(self, candidate: str) -> None:
        stored = hash_password("s3cret", iterations=CHEAP)
        assert verify_password(stored, candidate) is False

    def test_verification_uses_the_stored_cost_and_not_the_module_constant(self) -> None:
        """The property that keeps a future increase from locking everybody out: a row
        written at one cost stays verifiable when the default moves."""
        stored = hash_password("portable", iterations=CHEAP)
        assert stored.iterations == CHEAP != ITERATIONS
        assert verify_password(stored, "portable") is True

    def test_a_digest_written_at_another_cost_does_not_verify_at_this_one(self) -> None:
        """Which is why the parameter is stored rather than assumed."""
        stored = hash_password("portable", iterations=CHEAP)
        shifted = StoredPassword(
            algorithm=stored.algorithm,
            iterations=CHEAP + 1,
            salt=stored.salt,
            digest=stored.digest,
        )
        assert verify_password(shifted, "portable") is False

    def test_an_unknown_algorithm_raises_rather_than_reporting_a_wrong_password(
        self,
    ) -> None:
        """A credential that cannot be verified is a defect. Answering ``False`` would
        file it under "user typed it wrong" and nobody would ever look."""
        stored = hash_password("s3cret", iterations=CHEAP)
        broken = StoredPassword(
            algorithm="md5", iterations=stored.iterations, salt=stored.salt,
            digest=stored.digest,
        )
        with pytest.raises(DomainError) as caught:
            verify_password(broken, "s3cret")
        assert caught.value.code is ErrorCode.INTERNAL_ERROR

    def test_a_corrupt_salt_raises_rather_than_reporting_a_wrong_password(self) -> None:
        stored = hash_password("s3cret", iterations=CHEAP)
        broken = StoredPassword(
            algorithm=stored.algorithm, iterations=stored.iterations,
            salt="not hexadecimal", digest=stored.digest,
        )
        with pytest.raises(DomainError) as caught:
            verify_password(broken, "s3cret")
        assert caught.value.code is ErrorCode.INTERNAL_ERROR

    def test_the_comparison_is_constant_time(self) -> None:
        """Asserted on the source, because the behaviour is a non-difference in timing
        and a timing assertion on a shared runner measures the runner.

        ``==`` on bytes returns at the first differing byte; over enough attempts that is
        a byte-at-a-time oracle on the digest.
        """
        source = inspect.getsource(passwords)
        assert "hmac.compare_digest" in source
        assert "== expected" not in source
        assert "computed == " not in source


class TestTheMechanicalBounds:
    def test_an_empty_password_is_refused(self) -> None:
        with pytest.raises(DomainError) as caught:
            hash_password("", iterations=CHEAP)
        assert caught.value.code is ErrorCode.VALIDATION_FAILED

    def test_an_over_long_password_is_refused(self) -> None:
        with pytest.raises(DomainError) as caught:
            hash_password("x" * (MAX_PASSWORD_LENGTH + 1), iterations=CHEAP)
        assert caught.value.code is ErrorCode.VALIDATION_FAILED

    def test_a_password_at_the_bound_is_accepted(self) -> None:
        stored = hash_password("x" * MAX_PASSWORD_LENGTH, iterations=CHEAP)
        assert verify_password(stored, "x" * MAX_PASSWORD_LENGTH) is True

    def test_a_unicode_password_is_not_normalised_away(self) -> None:
        """Two strings that look alike but are different code points are different
        passwords. Normalising would accept one for the other."""
        composed = "café"  # e + combining acute
        precomposed = "café"
        stored = hash_password(composed, iterations=CHEAP)
        assert verify_password(stored, composed) is True
        assert verify_password(stored, precomposed) is False

    def test_no_policy_is_enforced_beyond_the_bounds(self) -> None:
        """Deliberate: minimum length, complexity and history belong to the registration
        and password-change work, and a rule invented here would be renegotiated there.
        ``password`` itself has to hash, because the seeded account uses it."""
        assert verify_password(hash_password("password", iterations=CHEAP), "password")


class TestTheRecordDoesNotLeak:
    def test_repr_redacts_the_salt_and_the_digest(self) -> None:
        """A dataclass-generated ``repr`` prints every field, and a ``repr`` reaches any
        traceback, f-string or debug log that touches the object."""
        stored = hash_password("s3cret", iterations=CHEAP)
        rendered = repr(stored)
        assert stored.digest not in rendered
        assert stored.salt not in rendered
        assert "<redacted>" in rendered
        assert str(CHEAP) in rendered, "the cost is operational, not secret"

    def test_the_record_holds_no_plaintext_at_all(self) -> None:
        stored = hash_password("s3cret", iterations=CHEAP)
        assert "s3cret" not in repr(stored)
        assert "s3cret" not in stored.digest
        assert "s3cret" not in stored.salt


class TestTheEnumerationDefence:
    def test_spending_a_verification_returns_nothing_and_raises_nothing(self) -> None:
        assert spend_a_verification("anything", iterations=CHEAP) is None
        assert spend_a_verification("", iterations=CHEAP) is None
        assert spend_a_verification("x" * 5000, iterations=CHEAP) is None

    def test_it_actually_derives_a_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A defence that returned immediately would be a comment, not a defence."""
        calls: list[int] = []
        real = hashlib.pbkdf2_hmac

        def counting(*args: object, **kwargs: object) -> bytes:
            calls.append(1)
            return real(*args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(passwords.hashlib, "pbkdf2_hmac", counting)
        spend_a_verification("anything", iterations=CHEAP)
        assert calls == [1], "the unknown-login path did no work"


class TestTheLoginRule:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("admin", "admin"),
            ("ADMIN", "admin"),
            ("  Admin  ", "admin"),
            ("a.b_c-d", "a.b_c-d"),
            ("9lives", "9lives"),
            ("x" * 100, "x" * 100),
        ],
    )
    def test_accepted_logins_fold_to_their_stored_form(
        self, raw: str, expected: str
    ) -> None:
        assert normalize_login(raw) == expected

    @pytest.mark.parametrize(
        "raw",
        ["", "   ", "-leading", ".leading", "with space", "tab\tchar", "админ", "a" * 101,
         "semi;colon", "quote'", "back\\slash", "null\x00byte"],
    )
    def test_refused_logins_raise_rather_than_being_repaired(self, raw: str) -> None:
        """A login the caller did not type is a login they cannot type again."""
        with pytest.raises(DomainError) as caught:
            normalize_login(raw)
        assert caught.value.code is ErrorCode.VALIDATION_FAILED

    def test_the_pattern_the_database_enforces_is_the_pattern_the_boundary_enforces(
        self,
    ) -> None:
        assert models.LOGIN_PATTERN == r"^[a-z0-9][a-z0-9._-]{0,99}$"


class TestTheUserIdentity:
    def test_a_fresh_identity_has_the_declared_shape(self) -> None:
        value = str(UserUid.new())
        assert value.startswith("usr_")
        assert len(value) == 4 + 26
        assert models.is_user_uid(value)

    def test_two_identities_differ(self) -> None:
        assert UserUid.new() != UserUid.new()

    def test_a_foreign_identity_is_refused(self) -> None:
        """A well-formed identity of another entity is not a user identity."""
        from auditmanager.shared.identity import ProjectUid

        with pytest.raises(DomainError) as caught:
            UserUid.parse(str(ProjectUid.new()))
        assert caught.value.code is ErrorCode.VALIDATION_FAILED

    def test_it_does_not_register_a_prefix_in_the_frozen_contract_catalog(self) -> None:
        """``usr`` is not in ``contracts/domain/v1/identifiers.json``. Subclassing the
        contract's ``OpaqueId`` would have registered it globally and added a
        twenty-sixth identity to a catalog a contract test pins at twenty-five."""
        from auditmanager.shared.identity import (
            IDENTITY_TYPES_BY_PREFIX,
            IdentifierFormatError,
            OpaqueId,
            identity_type_for_prefix,
        )

        assert "usr" not in IDENTITY_TYPES_BY_PREFIX
        assert not issubclass(UserUid, OpaqueId)
        # The live registry, not only the snapshot taken at import time: a subclass
        # defined anywhere would have written itself into this one.
        with pytest.raises(IdentifierFormatError):
            identity_type_for_prefix("usr")

    def test_the_identity_is_not_derived_from_the_login(self) -> None:
        assert "admin" not in str(UserUid.new()).lower()
