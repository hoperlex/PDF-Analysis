"""An opaque identity is the whole string, never a prefix of it that ends in a newline.

`AR-V3-BETA-REVIEW-FIXES-02` finding B. The value types anchored their pattern with `^...$`
and matched with `re.match`, and `$` also matches just before one trailing newline, so
`"ndoc_<ULID>\\n"` parsed as a valid identity while the validators of the evidence bridge and
the custody roles (`\\Z`, `fullmatch`) refuse it. Two checkers that disagree about one
identifier are how a tool says "acceptable" and the real path says no.
"""

from __future__ import annotations

import pytest

from auditmanager.shared.identity import (
    IdentifierFormatError,
    IDENTITY_TYPES_BY_PREFIX,
    NormDocumentId,
    NormRetrievalSetId,
)

ULID = "01J9ZQ8K7NHVXW3T2R5M6P4Q8B"


def test_every_identity_type_refuses_a_trailing_newline() -> None:
    assert len(IDENTITY_TYPES_BY_PREFIX) > 20
    for prefix, identity in IDENTITY_TYPES_BY_PREFIX.items():
        plain = f"{prefix}_{ULID}"
        assert str(identity.parse(plain)) == plain
        for suffix in ("\n", "\n\n", "\r\n"):
            with pytest.raises(IdentifierFormatError):
                identity.parse(plain + suffix)


@pytest.mark.parametrize("identity", [NormDocumentId, NormRetrievalSetId])
def test_the_norm_identities_the_tools_check_refuse_it_too(identity: type) -> None:
    plain = f"{identity.prefix}_{ULID}"
    assert identity.parse(plain).value == plain
    for decorated in (plain + "\n", "\n" + plain, plain + " ", " " + plain, plain + "\x00"):
        with pytest.raises(IdentifierFormatError):
            identity.parse(decorated)


def test_a_wrong_prefix_followed_by_a_newline_is_a_format_error_not_a_prefix_error() -> None:
    # The other half of the same defect: the prefix probe on the error path must not accept a
    # prefix that carries a newline either, so the message names the real problem.
    with pytest.raises(IdentifierFormatError) as raised:
        NormDocumentId.parse(f"nrs\n_{ULID}")
    assert type(raised.value) is IdentifierFormatError
