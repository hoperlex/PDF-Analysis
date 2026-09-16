"""The identifier shape rules, pinned against the frozen domain catalog.

The brief asked whether the Crockford alphabet is enforced anywhere a test can see.
**It is**, and the sweep says where: swapping `J` for `I` in `ulid._ALPHABET`, and
widening `pattern_for`'s character class to `[0-9A-Z]`, both redden --- the first through
`tests/integration/api/test_database_refusals.py` and the second through
`tests/integration/db/test_schema_shape.py::test_every_identity_column_carries_a_format_check`,
because `pattern_for` is also the source of the migration's CHECK constraints. The
database is what guards the alphabet.

Three rules around it were not reachable from the gate:

* `is_valid_ulid`'s **length** check. Removing it left all 816 tests green.
* the declared `IDENTIFIER_PATTERN` constant. Widening it left all 816 tests green.
* which exception a wrong-prefix identifier raises.

All three are covered by `tests/contract/domain_p02/test_identifier_catalog.py`, and that
suite is quarantined out of `make gate` by `PROTOTYPE_PROFILE.md` 6.3 --- it is red before
any wave starts. Coverage there guards nothing the gate would catch, which is the whole
reason this file exists rather than a note saying "already covered".

Everything is pinned against `contracts/domain/v1/identifiers.json`, read from this
file's own location, so the module restating a contract value incorrectly is a red test.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from auditmanager.shared.identity import (
    IDENTIFIER_PATTERN,
    PREFIX_PATTERN,
    IdentifierFormatError,
    IdentifierPrefixError,
    ProjectUid,
    VersionUid,
    is_valid_ulid,
    new_ulid,
)
from auditmanager.shared.identity.ulid import ULID_LENGTH, alphabet

CONTRACT = Path(__file__).resolve().parents[3] / "contracts/domain/v1/identifiers.json"


def _contract() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


class TestTheDeclaredShapeMatchesTheFrozenCatalog:
    """`ids.py` says these constants are the contract's, "restated so the code can be
    read without the catalog open". A restatement is a second place to be wrong."""

    def test_the_identifier_pattern_is_the_contract_s_id_pattern(self) -> None:
        assert IDENTIFIER_PATTERN == _contract()["id_pattern"]

    def test_the_prefix_pattern_is_the_contract_s_prefix_pattern(self) -> None:
        assert PREFIX_PATTERN == _contract()["prefix_pattern"]

    def test_the_ulid_length_is_the_contract_s_length(self) -> None:
        assert ULID_LENGTH == _contract()["ulid"]["length"] == 26

    def test_the_alphabet_is_the_contract_s_crockford_alphabet(self) -> None:
        declared = _contract()["ulid"]["alphabet"]
        assert alphabet() == declared == "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

    def test_the_alphabet_excludes_i_l_o_and_u(self) -> None:
        """The four letters Crockford drops, named rather than implied: they are what
        makes the alphabet 32 characters rather than 36, and an alphabet that quietly
        re-admitted one would still be "uppercase alphanumeric"."""
        assert len(alphabet()) == 32
        for excluded in ("I", "L", "O", "U"):
            assert excluded not in alphabet(), excluded


class TestIsValidUlidChecksTheLengthAndNotOnlyTheAlphabet:
    def test_a_generated_ulid_is_valid(self) -> None:
        assert is_valid_ulid(new_ulid())

    def test_a_body_of_26_alphabet_characters_is_valid(self) -> None:
        assert is_valid_ulid("0" * 26)

    @pytest.mark.parametrize("length", [0, 1, 25, 27, 52], ids=str)
    def test_a_body_of_any_other_length_is_not_valid(self, length: int) -> None:
        """Every one of these is drawn entirely from the alphabet, so the alphabet
        check passes them. Only the length rule can refuse them."""
        candidate = "0" * length
        assert all(character in alphabet() for character in candidate)
        assert not is_valid_ulid(candidate)

    def test_a_body_of_the_right_length_outside_the_alphabet_is_not_valid(self) -> None:
        assert not is_valid_ulid("I" * 26)

    def test_a_non_string_is_not_valid(self) -> None:
        assert not is_valid_ulid(None)
        assert not is_valid_ulid(26)


class TestAWrongPrefixIsADifferentFaultFromAWrongShape:
    """`IdentifierPrefixError` **subclasses** `IdentifierFormatError`, so
    `pytest.raises(IdentifierFormatError)` passes for both and cannot tell them apart.
    These assert the exact type.

    The distinction is the one `is_valid_ulid` is called for at `ids.py:105`: a
    well-formed identity of the wrong entity gets the prefix error, and anything else
    gets the format error. Without the length check, a short body with a known prefix is
    misreported as a prefix problem, and the caller is told to look at the wrong thing.
    """

    def test_a_well_formed_identity_of_another_entity_raises_the_prefix_error(self) -> None:
        other = str(VersionUid.new())
        with pytest.raises(IdentifierFormatError) as caught:
            ProjectUid(other)
        assert type(caught.value) is IdentifierPrefixError, (
            f"expected IdentifierPrefixError, got {type(caught.value).__name__}"
        )
        assert "prj" in str(caught.value)

    def test_a_right_prefix_with_a_short_body_raises_the_format_error(self) -> None:
        with pytest.raises(IdentifierFormatError) as caught:
            ProjectUid("prj_" + "0" * 25)
        assert type(caught.value) is IdentifierFormatError, (
            f"a malformed body was reported as {type(caught.value).__name__}"
        )

    def test_an_unknown_prefix_with_a_valid_body_raises_the_prefix_error(self) -> None:
        with pytest.raises(IdentifierFormatError) as caught:
            ProjectUid("zzz_" + new_ulid())
        assert type(caught.value) is IdentifierPrefixError

    def test_a_valid_identity_of_its_own_type_is_accepted(self) -> None:
        value = str(ProjectUid.new())
        assert str(ProjectUid(value)) == value
