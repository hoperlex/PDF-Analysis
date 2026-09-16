"""Two storage rules that a mutation sweep could not redden.

Found by mutating every constant and refusing branch in ``storage/`` in turn against
``tests/integration/storage`` and ``tests/integration/ingest``. Six mutations; four reddened
properly, two did not:

* ``TEMPORARY_PREFIX`` collapsed onto ``CANONICAL_PREFIX`` — green;
* ``_ROLE_PATTERN`` widened to ``^.*$`` — green.

The asymmetry in the first is the telling part. Moving the *canonical* prefix reddens two
tests, so the suite pins where a published object lands and says nothing about where an
unverified one is held. Publication is two-phase — bytes are staged under ``temporary/`` and
promoted to ``blobs/`` only after digest and size are verified — so the two namespaces being
disjoint is what stops a staged, unverified object from occupying, or being read as, a
canonical one.

Expected values are literals here, not imports. Wave 9 lost five tests to building the
expected value from the module's own constants: both sides of every comparison then move
together under mutation and the test passes against anything.
"""

from __future__ import annotations

import pytest

from auditmanager.storage import BlobMetadataInvalidError, parse_blob_role
from auditmanager.storage.models import BlobId

# Reached through the private module deliberately. `_object_layout` is not exported from the
# package, so the disjointness of the two namespaces is an internal invariant with no public
# surface -- which is part of why nothing was guarding it. A test that refuses to look at it
# would leave it unguarded for the same reason it already was.
from auditmanager.storage._object_layout import (  # noqa: PLC2701
    canonical_key,
    is_canonical_key,
    is_temporary_key,
    temporary_key,
)

#: Pinned literally. The prefixes are an on-disk layout: changing either renames every
#: object already published, so a change here should be a deliberate migration and a red
#: test, not a constant edit that nothing notices.
TEMPORARY = "temporary/"
CANONICAL = "blobs/"

A_BLOB_ID = BlobId("blob_" + "0" * 26)


class TestTheTwoNamespacesAreDisjoint:
    def test_the_prefixes_are_what_they_have_always_been(self) -> None:
        assert temporary_key("tok").startswith(TEMPORARY)
        assert canonical_key(A_BLOB_ID).startswith(CANONICAL)

    def test_a_staged_key_is_never_read_as_canonical(self) -> None:
        """The claim. Collapsing the prefixes makes this true and nothing else notices.

        A staged object is unverified: its digest and size have not been compared yet. If
        it classifies as canonical, a corrupt upload is one classification away from being
        served as published bytes.
        """
        staged = temporary_key("upload-token-0000")
        assert is_temporary_key(staged)
        assert not is_canonical_key(staged), (
            f"a staged, unverified object classifies as canonical: {staged!r}"
        )

    def test_a_canonical_key_is_never_read_as_staged(self) -> None:
        """The other direction, so the property is disjointness and not an ordering."""
        published = canonical_key(A_BLOB_ID)
        assert is_canonical_key(published)
        assert not is_temporary_key(published), (
            f"a published object classifies as staged: {published!r}"
        )

    def test_neither_prefix_is_a_prefix_of_the_other(self) -> None:
        """The general form. ``startswith`` is what both classifiers use, so one prefix
        being a prefix of the other is enough to break them even without equality."""
        assert not TEMPORARY.startswith(CANONICAL)
        assert not CANONICAL.startswith(TEMPORARY)


class TestTheRoleVocabulary:
    """``parse_blob_role`` accepts lowercase snake_case, 3–64 characters.

    Nothing exercised a value outside it, so widening the pattern to ``^.*$`` reddened
    nothing. The role is written into object metadata and read back by the reconciliation
    that decides whether an object is accounted for, so an unconstrained role is a value
    that can be written and never matched.
    """

    def test_the_two_roles_the_system_uses_are_accepted(self) -> None:
        """The precondition. Without it every refusal below could be a broken import."""
        assert parse_blob_role("source_document") == "source_document"
        assert parse_blob_role("foundation_check") == "foundation_check"

    @pytest.mark.parametrize(
        ("value", "why"),
        [
            ("", "empty"),
            ("ab", "two characters, one short of the minimum"),
            ("a" * 65, "one character past the maximum"),
            ("Source_Document", "uppercase"),
            ("1source", "leading digit"),
            ("_source", "leading underscore"),
            ("source-document", "hyphen rather than underscore"),
            ("source document", "space"),
            ("source/document", "separator"),
            ("source\ndocument", "control character"),
        ],
    )
    def test_a_value_outside_the_vocabulary_is_refused_by_the_role_rule(
        self, value: str, why: str
    ) -> None:
        with pytest.raises(BlobMetadataInvalidError) as raised:
            parse_blob_role(value)
        assert raised.value.details["field"] == "role", why

    def test_the_boundaries_are_limits_and_not_prohibitions(self) -> None:
        """Three characters and sixty-four are inside the rule.

        Without this the rule could be implemented as a much narrower one and every
        negative case above would still pass.
        """
        assert parse_blob_role("abc") == "abc"
        assert parse_blob_role("a" + "b" * 63) == "a" + "b" * 63
