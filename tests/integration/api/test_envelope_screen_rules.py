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


class TestTheScreenHasSixShapesAndTheDocstringSaysSo:
    """`W11-FIX`. The module docstring named **five** forbidden shapes; there are six.

    It omitted the S3-style object key -- the one shape whose pattern is the hardest to
    reconstruct from a name, and the one a reader is therefore most likely to re-add by
    hand. A count in prose is exactly the kind of claim that survives being false,
    because nothing executes it. This executes it.

    The wave-10 brief that commissioned the suite above said "seven" twice and was also
    wrong, which is the second reason the number is pinned here rather than counted by
    whoever next reads the tuple.

    **On importing ``_FORBIDDEN``.** The suite above deliberately does not, because a
    test that *builds its expectation* from a constant moves with the constant. These
    tests do the opposite: the expectation is the literal tuple below, written out by
    hand, and ``_FORBIDDEN`` is the thing under test. A drift in either the tuple or the
    docstring reddens against a fixed authority.
    """

    #: The six shapes, in the tuple's own order, as literals. Not derived from anything.
    SIX_SHAPES: tuple[str, ...] = (
        "a URL",
        "a filesystem path",
        "an S3-style object key",
        "a credential",
        "SQL",
        "a stack frame",
    )

    def test_the_screen_carries_exactly_six_shapes_in_this_order(self) -> None:
        from auditmanager.shared.errors import envelope as module

        labels = tuple(label for label, _ in module._FORBIDDEN)
        assert labels == self.SIX_SHAPES, (
            f"the screen carries {len(labels)} shapes {labels!r}, not the six this suite "
            f"pins {self.SIX_SHAPES!r}. A shape added without a case below is a rule no "
            "test can tell from a deleted one; a shape removed is a hole."
        )

    def test_the_module_docstring_names_every_shape_the_screen_carries(self) -> None:
        """The defect itself: a docstring that enumerated five of six.

        Reverting the docstring to its five-shape sentence reddens this and nothing
        else, which is what makes the prose claim a guarded one.
        """
        from auditmanager.shared.errors import envelope as module

        # Whitespace-collapsed: the docstring is wrapped at 90 columns and "an S3-style
        # object key" straddles a line break. A naive substring check reports that shape
        # missing from a docstring that names it -- a false red, which is as bad as a
        # false green because the next reader "fixes" it by unwrapping prose.
        docstring = " ".join((module.__doc__ or "").split())
        missing = [shape for shape in self.SIX_SHAPES if shape not in docstring]
        assert not missing, (
            f"the envelope docstring does not name {missing!r}. It tells a reader what "
            "the screen forbids, and a reader who trusts an undercount will add a check "
            "that already exists or route around one they did not know was there."
        )

    def test_the_docstring_does_not_claim_a_count_other_than_six(self) -> None:
        """A docstring may enumerate correctly and still state the wrong total."""
        from auditmanager.shared.errors import envelope as module

        docstring = " ".join((module.__doc__ or "").split()).lower()
        for wrong in ("five", "seven", "four", "eight"):
            assert f"{wrong}**" not in docstring and f"**{wrong}" not in docstring, (
                f"the envelope docstring emphasises the count {wrong!r}; the screen "
                "carries six shapes"
            )
        assert "six" in docstring, (
            "the envelope docstring no longer states how many shapes the screen carries"
        )

    def test_every_one_of_the_six_is_reachable_by_a_real_refusal(self) -> None:
        """A count is worth nothing if a pattern can never fire.

        ``ONE_SHAPE_EACH`` above drives seven values through both screens and asserts
        each names its own rule. This asserts that the reasons those cases exercise are
        *exactly* the six -- so a seventh shape added to the tuple without a case here
        reddens rather than passing untested, and a shape that no value can reach
        reddens too.
        """
        exercised = {reason for _, _, reason in ONE_SHAPE_EACH}
        assert exercised == set(self.SIX_SHAPES), (
            f"the cases above reach {sorted(exercised)!r}, not the six shapes "
            f"{sorted(self.SIX_SHAPES)!r}"
        )


class TestNoCallSiteClaimsDetailsAreUnscreened:
    """`W11-FIX`. Two comments said the screen this suite exercises does not exist.

    `api/routers/multipart.py` and `api/schemas/projects.py` each stated that ``details``
    values "are not screened the way ``message`` is". They are, and have been since
    `B6`. Both comments sat beside a *correct* refusal and gave a *false* reason for it,
    which is the dangerous direction: a later reader who believes the screen is absent
    either adds a second one or, worse, concludes the value must be sanitised at the
    call site and echoes it "safely".

    Wave 10's finding was that a stale comment on a security surface outlives a stale
    test because nothing executes it. So this executes it, in two halves: the screen is
    demonstrably live at the exact text those two sites refuse, and no source file in
    the boundary asserts the negative.
    """

    API_TREE = Path(__file__).resolve().parents[3] / "src/auditmanager/api"

    #: The caller-controlled text each of the two sites is refusing when its comment
    #: speaks. `/etc/passwd` is `B6`'s own property name; `file` is the repeated part.
    CALLER_TEXT = "/etc/passwd"

    def test_the_screen_refuses_the_very_text_those_sites_decline_to_echo(self) -> None:
        """If either site did echo, the envelope would refuse rather than ship it."""
        with pytest.raises(UnsafeDetailValue) as caught:
            build(
                ErrorCode.VALIDATION_FAILED,
                "cid-fixed-0001",
                details={"field": self.CALLER_TEXT},
            )
        assert "a filesystem path" in str(caught.value)

    def test_no_api_source_file_claims_details_are_unscreened(self) -> None:
        """The defect, made executable. Restoring either comment reddens this.

        A phrase check is a blunt instrument and is used here only because the claim
        itself is a phrase. It is paired with the test above, which proves the thing the
        phrase denied.
        """
        offenders: list[str] = []
        for path in sorted(self.API_TREE.rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            if "not screened" in text or "are not screened the way" in text:
                offenders.append(str(path.relative_to(self.API_TREE.parents[1])))
        assert not offenders, (
            f"{offenders!r} state that details values are not screened. "
            "`shared/errors/envelope.py` runs every string detail value through the "
            "same six `_FORBIDDEN` patterns as a message and raises UnsafeDetailValue; "
            "the test above proves it on the exact text these sites refuse."
        )
