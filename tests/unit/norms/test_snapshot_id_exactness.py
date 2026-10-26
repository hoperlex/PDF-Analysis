"""A norms snapshot identity is the whole string, never one that ends in a newline.

`AR-V3-BETA-REVIEW-FIXES-03` finding F4. `SNAPSHOT_ID_PATTERN` ends in `$`, which also matches
just before one trailing newline, and `require_snapshot_id` matched with `re.match`, so
`"ns_<ULID>\\n"` was returned as valid on the promote path (the set tool, the evidence bridge)
while the `0012` CHECK and the API schema refuse it.
"""

from __future__ import annotations

import pytest

from auditmanager.norms.embedding.profile import SNAPSHOT_ID_PATTERN, require_snapshot_id

ULID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"


def test_a_valid_snapshot_id_is_returned_unchanged() -> None:
    assert require_snapshot_id(f"ns_{ULID}") == f"ns_{ULID}"


@pytest.mark.parametrize(
    "decorated",
    [f"ns_{ULID}\n", f"ns_{ULID}\n\n", f"ns_{ULID}\r\n", f"\nns_{ULID}", f"ns_{ULID} ",
     f"ns_{ULID[:5]}\n{ULID[5:]}", f"ns_{ULID}\x00"],
    ids=["trailing_lf", "two_lf", "crlf", "leading_lf", "trailing_space", "inner_lf", "nul"],
)
def test_a_snapshot_id_with_anything_around_it_is_refused(decorated: str) -> None:
    with pytest.raises(ValueError):
        require_snapshot_id(decorated)


def test_the_pattern_text_the_database_check_mirrors_is_unchanged() -> None:
    assert SNAPSHOT_ID_PATTERN.pattern == r"^ns_[0-9A-HJKMNP-TV-Z]{26}$"
