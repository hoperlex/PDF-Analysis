"""The `Range` header the content stream accepts, and the one rule no test could redden.

`W10-API` swept `routers/documents.py`. The unsatisfiable-range refusal and the
`application/pdf` media type both redden `test_journey.py`. The **shape** of the header
did not: loosening `^bytes=(\\d*)-(\\d*)$` to `^bytes=(\\d*)-(\\d*).*$` -- which is what a
trailing `.*` does to an anchored pattern -- left all 816 tests green.

That loosening is not cosmetic. The module's own comment says why the pattern is anchored:

    A multi-range request is not served: the frozen 206 declares one `application/pdf`
    body, and a multipart/byteranges response would not be that shape.

With the trailing `.*`, `bytes=0-99,200-299` parses as `0-99` and is **answered 206 with
the first range only**. A caller that asked for two ranges gets one, silently, and the
response claims to satisfy the request.

`_resolve_range` is private, and is called directly here for the same reason
`test_composition_root.py` calls `_provenance_mode` directly: the rule is a pure function
of a header and a size, and driving it through the router would need a published document
to say nothing more.
"""

from __future__ import annotations

import pytest

from auditmanager.api.routers.documents import _resolve_range
from auditmanager.shared.errors import DomainError


class TestTheRangeHeaderShapeIsASingleByteRange:
    def test_a_single_range_resolves(self) -> None:
        assert _resolve_range("bytes=0-99", 1000) == (0, 99)

    def test_an_open_ended_range_runs_to_the_last_byte(self) -> None:
        assert _resolve_range("bytes=5-", 10) == (5, 9)

    def test_a_suffix_range_counts_back_from_the_end(self) -> None:
        assert _resolve_range("bytes=-100", 1000) == (900, 999)

    def test_a_multi_range_request_is_refused_rather_than_partly_answered(self) -> None:
        """The rule the anchor exists for.

        Without it this header resolves to ``(0, 99)`` and the caller is answered 206
        with the first range, having asked for two. The frozen 206 declares one
        ``application/pdf`` body, so there is no shape in which the second range could
        be returned -- which is why refusing is the only honest answer.
        """
        with pytest.raises(DomainError) as caught:
            _resolve_range("bytes=0-99,200-299", 1000)
        assert caught.value.detail_fields["field"] == "Range"
        assert caught.value.detail_fields["constraint"] == "format"

    def test_trailing_text_after_a_range_is_refused(self) -> None:
        with pytest.raises(DomainError) as caught:
            _resolve_range("bytes=0-99junk", 1000)
        assert caught.value.detail_fields["constraint"] == "format"

    def test_a_unit_other_than_bytes_is_refused(self) -> None:
        with pytest.raises(DomainError) as caught:
            _resolve_range("items=0-99", 1000)
        assert caught.value.detail_fields["constraint"] == "format"

    def test_a_range_with_neither_end_is_refused_as_format(self) -> None:
        with pytest.raises(DomainError) as caught:
            _resolve_range("bytes=-", 1000)
        assert caught.value.detail_fields["constraint"] == "format"


class TestAnUnsatisfiableRangeIsADistinctRule:
    """``format`` and ``unsatisfiable`` are different answers and both say
    ``field: "Range"``. Only the constraint separates a header that is the wrong shape
    from one that is the right shape and cannot be served."""

    def test_a_start_past_the_end_of_the_document_is_unsatisfiable(self) -> None:
        with pytest.raises(DomainError) as caught:
            _resolve_range("bytes=2000-3000", 1000)
        assert caught.value.detail_fields["constraint"] == "unsatisfiable"

    def test_a_zero_length_suffix_is_unsatisfiable_not_malformed(self) -> None:
        """``bytes=-0`` asks for the last zero bytes. It is well-formed and cannot be
        served, so it is the other rule."""
        with pytest.raises(DomainError) as caught:
            _resolve_range("bytes=-0", 1000)
        assert caught.value.detail_fields["constraint"] == "unsatisfiable"

    def test_any_range_over_an_empty_document_is_unsatisfiable(self) -> None:
        with pytest.raises(DomainError) as caught:
            _resolve_range("bytes=0-0", 0)
        assert caught.value.detail_fields["constraint"] == "unsatisfiable"
