"""The non-identity value types are the whole string, never a prefix ending in a newline.

`AR-V3-BETA-REVIEW-FIXES-03` (finding F4, sibling of the opaque-id fix of `-02`). The
patterns are anchored with `^...$` and were applied with `re.match`; `$` also matches just
before one trailing newline, so `"<valid>\\n"` was accepted as a correlation id, an
idempotency key, a sha256 and a payload fingerprint.
"""

from __future__ import annotations

import pytest

from auditmanager.shared.identity import non_identity as ni
from auditmanager.shared.identity.errors import IdentifierFormatError

DIGEST = "0123456789abcdef" * 4

CASES = [
    (ni.CorrelationId, "cid-2704d8936c44105071aed44b73698d99"),
    (ni.IdempotencyKey, "start-run:ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8B"),
    (ni.Sha256, DIGEST),
    (ni.PayloadFingerprint, DIGEST),
]


@pytest.mark.parametrize(("kind", "valid"), CASES, ids=[c[0].__name__ for c in CASES])
def test_the_value_is_accepted_whole_and_refused_with_a_trailing_newline(kind, valid) -> None:
    assert str(kind.parse(valid)) == valid
    for suffix in ("\n", "\n\n", "\r\n"):
        with pytest.raises(IdentifierFormatError):
            kind.parse(valid + suffix)
