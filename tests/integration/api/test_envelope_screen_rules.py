"""Every forbidden shape the envelope screens, reddened one rule at a time.

`W10-API` swept `shared/errors/envelope.py` by mutation and found that the screen reads
as far more coverage than it carries. The suite that existed asserted
``pytest.raises(UnsafeMessage)`` over three sentences and nothing else, so it could not
distinguish *which* of the six patterns refused -- and two of the three sentences match
two patterns each, which means deleting either of the overlapping rules left the suite
green. The detail-**value** screen, added after `B6` leaked a caller-supplied property
name into ``details.field``, had no test at all: neutering it left all 816 tests green.

Two things therefore matter in every case below and neither is optional:

* **One shape per value.** The screen iterates ``_FORBIDDEN`` in order and raises on the
  first match, so a value matching two patterns only ever reports the earlier one and
  the later one can be deleted unnoticed. Each value here was checked to match exactly
  one pattern.
* **The reason is asserted, not the exception class.** ``UnsafeMessage`` is raised by
  all six rules and by the length rule. Asserting only the class is the mistake that let
  a deleted check survive a sweep: the test asserts the phrase naming the rule.

Nothing here imports ``_FORBIDDEN``, ``_MAX_MESSAGE`` or ``_MAX_DETAIL_VALUE``. Every
expected value is written as a literal, because a test that builds its expectation from
the module's own constant moves with the constant and cannot fail when it drifts.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from auditmanager.shared.errors import (
    ErrorCode,
    UnsafeDetailKey,
    UnsafeDetailValue,
    UnsafeMessage,
)
from auditmanager.shared.errors.envelope import build

#: One value per forbidden shape, each matching exactly that shape's pattern and no
#: other, paired with the phrase the screen must use to name it. The phrases are the
#: literals: they are the caller-visible reason, and they are what distinguishes a rule
#: that fired from a rule that was deleted.
#:
#: The overlaps that forced these particular values are worth recording, because the
#: obvious choices do not work:
#:   * ``s3://bucket/key`` matches "a URL" first, so it cannot reach the S3 rule.
#:   * ``/var/lib/audit/objects/ab/cd.pdf`` -- the value the previous suite used --
#:     matches "a filesystem path" first and "an S3-style object key" second.
#: A three-segment relative key with an extension reaches the S3 rule and nothing else;
#: a Windows path and a POSIX path each reach only the path rule.
ONE_SHAPE_EACH: tuple[tuple[str, str, str], ...] = (
    ("url", "https://minio.internal/audit-b6", "a URL"),
    ("posix_path", "the object at /var/lib/audit/ was refused", "a filesystem path"),
    ("windows_path", "C:\\Windows\\System32", "a filesystem path"),
    ("s3_key", "bucket/prefix/object.pdf", "an S3-style object key"),
    ("credential", "api_key=sk-ant-abc123", "a credential"),
    ("sql", "SELECT id FROM blob", "SQL"),
    ("stack_frame", 'File "s3.py", line 3', "a stack frame"),
)


class TestTheMessageScreenNamesTheRuleThatRefused:
    @pytest.mark.parametrize(
        ("label", "value", "reason"),
        ONE_SHAPE_EACH,
        ids=[case[0] for case in ONE_SHAPE_EACH],
    )
    def test_each_forbidden_shape_is_refused_and_named(
        self, label: str, value: str, reason: str
    ) -> None:
        with pytest.raises(UnsafeMessage) as caught:
            build(ErrorCode.INTERNAL_ERROR, "cid-fixed-0001", message=value)
        assert reason in str(caught.value), (
            f"the {label} case was refused, but the screen named "
            f"{str(caught.value)!r} rather than {reason!r}; a refusal that does not "
            "name its own rule cannot tell a working rule from a deleted one"
        )

    def test_a_sentence_carrying_no_forbidden_shape_passes(self) -> None:
        """The screen is a floor, not a wall: an ordinary refusal must survive it."""
        text = "No document version has that identity."
        assert build(ErrorCode.NOT_FOUND, "cid-fixed-0001", message=text).message == text


class TestTheDetailValueScreenNamesTheRuleThatRefused:
    """The rule `B6` paid for. Before this suite, neutering it left the battery green.

    ``validation_failed`` declares ``field`` as a safe detail key. A key being declared
    safe says nothing about what a call site puts under it -- `B6`'s
    ``additionalProperties`` refusal echoed the caller's own property name, so a
    property named ``/etc/passwd`` came back inside the envelope. The key was
    legitimate; the value was raw input.
    """

    @pytest.mark.parametrize(
        ("label", "value", "reason"),
        ONE_SHAPE_EACH,
        ids=[case[0] for case in ONE_SHAPE_EACH],
    )
    def test_each_forbidden_shape_is_refused_under_a_declared_key(
        self, label: str, value: str, reason: str
    ) -> None:
        with pytest.raises(UnsafeDetailValue) as caught:
            build(ErrorCode.VALIDATION_FAILED, "cid-fixed-0001", details={"field": value})
        assert reason in str(caught.value), (
            f"the {label} case was refused, but the screen named "
            f"{str(caught.value)!r} rather than {reason!r}"
        )

    def test_the_key_was_declared_safe_so_this_is_the_value_rule_not_the_key_rule(
        self,
    ) -> None:
        """Without this, the suite above would pass if ``field`` were simply undeclared.

        ``UnsafeDetailValue`` and ``UnsafeDetailKey`` are distinct classes precisely
        because the remedies differ, and the tests above would be vacuous if the key
        they use were rejected before its value was ever read.
        """
        envelope = build(
            ErrorCode.VALIDATION_FAILED, "cid-fixed-0001", details={"field": "page_count"}
        )
        assert envelope.details == {"field": "page_count"}

    def test_a_non_scalar_detail_value_is_refused(self) -> None:
        """Neutering this left the battery green. A mapping under a declared key would
        otherwise reach ``as_dict`` unscreened -- the value screen only reads strings."""
        with pytest.raises(UnsafeDetailKey) as caught:
            build(
                ErrorCode.VALIDATION_FAILED,
                "cid-fixed-0001",
                details={"field": {"nested": "https://minio.internal/x"}},
            )
        assert "must be a scalar" in str(caught.value)


class TestTheLengthCeilings:
    """Pinned as literals. No independent authority declares either number -- neither
    the frozen OpenAPI document nor the error catalog carries a length for a message or
    a detail value -- so these assert the numbers themselves, at the boundary. If a
    constant moves, this reddens, which is the whole point of not importing it."""

    def test_a_message_of_512_characters_is_accepted_and_513_is_not(self) -> None:
        at_limit = "a" * 512
        assert build(ErrorCode.INTERNAL_ERROR, "cid-fixed-0001", message=at_limit).message == at_limit
        with pytest.raises(UnsafeMessage, match="1..512 characters"):
            build(ErrorCode.INTERNAL_ERROR, "cid-fixed-0001", message="a" * 513)

    def test_an_empty_message_is_refused_rather_than_replaced_by_the_summary(self) -> None:
        """``message=""`` is not ``message=None``. The first is a call site with nothing
        to say, the second asks for the catalog summary; conflating them would ship an
        envelope whose message field is empty."""
        with pytest.raises(UnsafeMessage):
            build(ErrorCode.INTERNAL_ERROR, "cid-fixed-0001", message="")
        assert (
            build(ErrorCode.INTERNAL_ERROR, "cid-fixed-0001").message
            == ErrorCode.INTERNAL_ERROR.summary
        )

    def test_a_detail_value_of_256_characters_is_accepted_and_257_is_not(self) -> None:
        at_limit = "b" * 256
        envelope = build(
            ErrorCode.VALIDATION_FAILED, "cid-fixed-0001", details={"field": at_limit}
        )
        assert envelope.details == {"field": at_limit}
        with pytest.raises(UnsafeDetailKey, match="exceeds 256 characters"):
            build(
                ErrorCode.VALIDATION_FAILED, "cid-fixed-0001", details={"field": "b" * 257}
            )


class TestTheDefaultMessageIsTheSummaryTheFrozenContractDeclares:
    """Replacing ``code.summary`` with a constant left the battery green.

    ``build(code)`` with no message uses the catalog summary. The obvious assertion --
    ``build(code).message == code.summary`` -- reads both sides out of the same module,
    so a catalog that drifted would move both together and the test could not fail. This
    reads the declared summary out of ``contracts/domain/v1/error-codes.json``, resolved
    from *this file's* location rather than from the module's, which is the independent
    authority ``shared/errors/catalog.py`` itself names: "the contract is the authority.
    This module ... never restates a value the contract owns."
    """

    CONTRACT = Path(__file__).resolve().parents[3] / "contracts/domain/v1/error-codes.json"

    def _declared(self) -> dict[str, dict[str, object]]:
        raw = json.loads(self.CONTRACT.read_text(encoding="utf-8"))
        assert len(raw["codes"]) == 20, (
            f"the frozen catalog declares {len(raw['codes'])} codes, not 20; this suite "
            "pins the count so a code added or removed is a red test rather than a "
            "silently narrower sweep"
        )
        return raw["codes"]

    def test_every_code_defaults_to_its_declared_summary(self) -> None:
        declared = self._declared()
        for code in ErrorCode:
            assert build(code, "cid-fixed-0001").message == declared[code.value]["summary"], (
                f"{code.value}: the envelope's default message is not the summary the "
                "frozen contract declares"
            )

    def test_the_enum_and_the_contract_declare_the_same_codes(self) -> None:
        """Otherwise the loop above could be vacuous over a shrunken enum."""
        assert {c.value for c in ErrorCode} == set(self._declared())

    def test_a_supplied_message_still_replaces_the_summary(self) -> None:
        text = "No document version has that identity."
        assert build(ErrorCode.NOT_FOUND, "cid-fixed-0001", message=text).message == text
