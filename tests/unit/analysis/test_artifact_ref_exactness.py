"""A stage artifact reference carries its identifier and digest exactly, no trailing newline.

`AR-V3-BETA-REVIEW-FIXES-03` finding F4. `_BLOB_ID` and `_SHA256` end in `$`, which also
matches just before one trailing newline, and `ArtifactRef.__post_init__` matched with
`re.match`, so `blob_id="blob_<ULID>\\n"` and `sha256="<hex>\\n"` constructed a reference whose
document the contract schema refuses.
"""

from __future__ import annotations

from typing import Any

import pytest

from auditmanager.analysis.engine.result import ArtifactRef

ULID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
GOOD: dict[str, Any] = {
    "role": "norm_source", "blob_id": f"blob_{ULID}", "sha256": "a" * 64,
    "size_bytes": 1, "media_type": "application/pdf",
}


def test_a_well_formed_reference_is_accepted_and_serialises_as_given() -> None:
    assert ArtifactRef(**GOOD).to_document() == GOOD


@pytest.mark.parametrize("field", ["blob_id", "sha256"])
@pytest.mark.parametrize("suffix", ["\n", "\n\n", "\r\n", " ", "\x00"],
                         ids=["lf", "two_lf", "crlf", "space", "nul"])
def test_an_identifier_or_digest_with_trailing_text_is_refused(field: str, suffix: str) -> None:
    with pytest.raises(ValueError, match=field):
        ArtifactRef(**{**GOOD, field: GOOD[field] + suffix})


@pytest.mark.parametrize("field", ["blob_id", "sha256"])
def test_an_identifier_or_digest_with_a_leading_line_break_is_refused(field: str) -> None:
    with pytest.raises(ValueError, match=field):
        ArtifactRef(**{**GOOD, field: "\n" + GOOD[field]})
