"""The login, name, label and role rules of ``auditmanager.access.models`` (`W49-PLAN.md` §3.1).

`W49-ACCESS-01b`. Pure: no database. The database restates the shapes as CHECKs and
``tests/integration/db/test_accounts_migration.py`` proves the two engines agree.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from auditmanager.access.models import (
    MAX_EMAIL_LENGTH,
    MAX_NAME_LABEL_LENGTH,
    MAX_PERSON_NAME_LENGTH,
    RegistrationId,
    UserRecord,
    UserUid,
    name_label,
    normalize_email,
    normalize_login,
    normalize_person_name,
    parse_role,
)
from auditmanager.shared.errors import DomainError, ErrorCode

NOW = datetime(2026, 10, 5, tzinfo=UTC)


def _record(**fields) -> UserRecord:
    base = dict(
        user_uid=UserUid.new(),
        login="anna@example.com",
        is_default_credential=False,
        created_at=NOW,
        password_updated_at=NOW,
        token_epoch=1,
        token_epoch_updated_at=NOW,
        failed_sign_ins=0,
        last_failed_sign_in_at=None,
        sign_in_blocked_until=None,
        display_name=None,
    )
    base.update(fields)
    return UserRecord(**base)


class TestTheEmailLogin:
    @pytest.mark.parametrize(
        ("raw", "stored"),
        [
            ("anna@example.com", "anna@example.com"),
            ("  Anna.Petrova@Example.COM  ", "anna.petrova@example.com"),
            ("​anna@example.com﻿", "anna@example.com"),
            ("o'brien+tag@sub.example.ie", "o'brien+tag@sub.example.ie"),
            ("x@xn--80ak6aa92e.com", "x@xn--80ak6aa92e.com"),
            ("a" * 64 + "@x.ru", "a" * 64 + "@x.ru"),
        ],
    )
    def test_accepted_addresses_fold_to_their_stored_form(self, raw: str, stored: str) -> None:
        assert normalize_email(raw) == stored

    @pytest.mark.parametrize(
        "raw",
        ["", "admin", "anna@", "@example.com", "anna@example", "anna@@example.com",
         "an na@example.com", "anna@-example.com", "анна@пример.рф", "a" * 65 + "@x.ru",
         "anna@" + "d" * (MAX_EMAIL_LENGTH - 7) + ".ru", "anna@exa_mple.com", 42],
    )
    def test_refused_addresses_raise_rather_than_being_repaired(self, raw) -> None:
        with pytest.raises(DomainError) as caught:
            normalize_email(raw)
        assert caught.value.code is ErrorCode.VALIDATION_FAILED

    def test_the_length_bound_is_254(self) -> None:
        local = "a" * 60
        domain_len = MAX_EMAIL_LENGTH - len(local) - 1 - 3
        address = f"{local}@{'b' * domain_len}.ru"
        assert len(address) == MAX_EMAIL_LENGTH
        # A single label longer than 63 is allowed by this shape on purpose (it bounds the
        # whole address, not DNS); the bound under test is the total.
        assert normalize_email(address) == address
        with pytest.raises(DomainError):
            normalize_email(f"{local}@{'b' * (domain_len + 1)}.ru")

    def test_a_lookup_accepts_both_shapes_and_a_new_login_only_the_email(self) -> None:
        assert normalize_login(" Admin ") == "admin"
        assert normalize_login("Anna@Example.com") == "anna@example.com"
        with pytest.raises(DomainError):
            normalize_email("admin")


class TestThePersonName:
    @pytest.mark.parametrize(
        "raw",
        ["Петрова", "Петрова-Водкина", "О'Нил", "д’Артаньян", "де ла Фуэнте",
         "Müller", "Smith-Jones", "Ёлкина", "Я", "A" * MAX_PERSON_NAME_LENGTH],
    )
    def test_accepted_names_are_stored_as_typed(self, raw: str) -> None:
        assert normalize_person_name(raw, field="last_name", required=True) == raw

    def test_surroundings_and_invisible_characters_go_and_composition_is_canonical(self) -> None:
        """"Й" typed as "И" plus a combining breve is the same letter as the precomposed
        one, and is stored precomposed; a combining mark with no precomposed form is not a
        letter of the rule and is refused rather than silently dropped."""
        assert (
            normalize_person_name(" И\u0306ван\u200b ", field="first_name", required=True)
            == "\u0419ван"
        )
        with pytest.raises(DomainError):
            normalize_person_name("Ио\u0301ан", field="first_name", required=True)

    @pytest.mark.parametrize(
        ("raw", "fragment"),
        [
            ("", "must not be empty"),
            ("   ", "must not be empty"),
            ("A" * (MAX_PERSON_NAME_LENGTH + 1), "at most 60"),
            ("Петр0ва", "letters separated"),
            ("Пет  рова", "letters separated"),
            ("-Петрова", "letters separated"),
            ("Петрова-", "letters separated"),
            ("О''Нил", "letters separated"),
            ("Петров\nа", "letters separated"),
            ("日本", "letters separated"),
            ("Иванoв", "mixes Cyrillic and Latin"),
            ("Ivanоv-Петров", "mixes Cyrillic and Latin"),
        ],
    )
    def test_refused_names_say_why(self, raw: str, fragment: str) -> None:
        with pytest.raises(DomainError) as caught:
            normalize_person_name(raw, field="last_name", required=True)
        assert caught.value.code is ErrorCode.VALIDATION_FAILED
        assert fragment in str(caught.value)
        assert caught.value.detail_fields == {"field": "last_name"}

    def test_scripts_may_differ_between_words(self) -> None:
        """The `technic` rule is per word: a double-barrelled name may join two scripts."""
        assert normalize_person_name("Petrova Петрова", field="last_name", required=True)

    def test_an_absent_middle_name_is_none_and_a_required_one_is_refused(self) -> None:
        assert normalize_person_name(None, field="middle_name", required=False) is None
        assert normalize_person_name("  ", field="middle_name", required=False) is None
        with pytest.raises(DomainError):
            normalize_person_name(None, field="first_name", required=True)


class TestTheLabel:
    def test_the_name_form(self) -> None:
        assert name_label("Петрова", "анна", "сергеевна") == "Петрова А. С."
        assert name_label("Петрова", "Анна", None) == "Петрова А."

    def test_the_longest_label_is_66_and_inside_author_label(self) -> None:
        label = name_label("Ж" * MAX_PERSON_NAME_LENGTH, "Анна", "Сергеевна")
        assert len(label) == MAX_NAME_LABEL_LENGTH == 66
        assert 1 <= len(label) <= 128

    @pytest.mark.parametrize(
        ("fields", "label"),
        [
            ({"last_name": "Петрова", "first_name": "Анна", "display_name": "Аня"}, "Петрова А."),
            ({"display_name": "Аня"}, "Аня"),
            ({}, "anna@example.com"),
            ({"last_name": "Петрова", "display_name": "Аня"}, "Аня"),
            ({"first_name": "Анна"}, "anna@example.com"),
        ],
        ids=["names-win", "display-name", "login", "half-a-name-is-no-name", "first-only"],
    )
    def test_display_label_precedence(self, fields, label) -> None:
        """`R-55`: the name form, else ``display_name``, else the login."""
        assert _record(**fields).display_label == label


class TestTheVocabularies:
    @pytest.mark.parametrize("role", ["expert", "admin"])
    def test_a_known_role_parses(self, role: str) -> None:
        assert parse_role(role) == role

    @pytest.mark.parametrize("role", ["Admin", "root", "", None, "reviewer"])
    def test_an_unknown_role_is_refused_and_never_dropped(self, role) -> None:
        with pytest.raises(DomainError) as caught:
            parse_role(role)
        assert caught.value.code is ErrorCode.VALIDATION_FAILED

    def test_a_registration_identity_is_reg_and_a_ulid(self) -> None:
        value = str(RegistrationId.new())
        assert value.startswith("reg_") and len(value) == 30
        with pytest.raises(DomainError):
            RegistrationId.parse("usr_" + value[4:])
