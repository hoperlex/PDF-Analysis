"""A blob identity is the whole string, never one that ends in a newline.

`AR-V3-BETA-REVIEW-FIXES-03` finding F4, the sibling of `AR-V3-BETA-REVIEW-FIXES-02` finding B.
`BLOB_ID_PATTERN` ends in `$`, which also matches just before one trailing newline, and
`parse_blob_id` matched with `re.match`, so `"blob_<ULID>\\n"` came back as a `BlobId`
while the database CHECK and the API schema refuse it.
"""

from __future__ import annotations

import pytest

from auditmanager.storage.errors import InvalidBlobIdError
from auditmanager.storage.models import BLOB_ID_PATTERN, parse_blob_id

ULID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"


def test_a_valid_blob_id_is_accepted_unchanged() -> None:
    assert parse_blob_id(f"blob_{ULID}") == f"blob_{ULID}"


@pytest.mark.parametrize(
    "decorated",
    [f"blob_{ULID}\n", f"blob_{ULID}\n\n", f"blob_{ULID}\r\n", f"\nblob_{ULID}", f"blob_{ULID} ",
     f"blob_{ULID[:5]}\n{ULID[5:]}", f"blob_{ULID}\x00"],
    ids=["trailing_lf", "two_lf", "crlf", "leading_lf", "trailing_space", "inner_lf", "nul"],
)
def test_a_blob_id_with_anything_around_it_is_refused(decorated: str) -> None:
    with pytest.raises(InvalidBlobIdError):
        parse_blob_id(decorated)


def test_the_exported_pattern_text_is_unchanged() -> None:
    # The wire pattern is frozen by the analysis contract; only the way it is applied changed.
    assert BLOB_ID_PATTERN.pattern == r"^blob_[0-9A-HJKMNP-TV-Z]{26}$"


def test_a_value_that_is_not_text_is_refused_not_raised_as_a_type_error() -> None:
    with pytest.raises(InvalidBlobIdError):
        parse_blob_id(b"blob_" + ULID.encode())  # type: ignore[arg-type]
