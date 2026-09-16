"""``analysis.text.anchors``: the ``ungrounded_reason`` vocabulary and the unresolved reasons.

`W10-ANL` mutation sweep, rows AN-05, AN-06, AN-07, AN-09, AN-10, AN-11, AN-12 and AN-13 —
all green across `tests/integration/analysis_engine`, `tests/integration/analysis_text` and
`tests/replay`.

The offset *arithmetic* in this module is well guarded: perturbing `char_start`, perturbing
`char_end` in either direction, dropping the page base, and searching the whole document
instead of the declared page all redden `test_corpus_acceptance.py`. What is not guarded is
the **vocabulary**: `REASON_ABSENT` and `REASON_DIFFERENT_PAGE` can be changed to any string
at all and nothing notices, even though the module's docstring says these values are "the
`ungrounded_reason` vocabulary of `P02_SEAMS.md` section 5.1, reused so a diagnostic written
here reads the same as one written by the grounding gate".

There is a real independent authority: migration `0003_open_items` adds
`ck_finding_observation_ungrounded_reason`, a CHECK over exactly five values, and the comment
beside it records that the field "declared a five-value vocabulary and enforced none of it"
until then. A reason string this module invents that is outside that set cannot be persisted.
`db/` is not this module's tree.

`AN-09` is the module's stated boundary: whitespace stripping is "the one liberty taken", and
nothing normalizes. Adding a case-folded candidate to the retry list was green.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from auditmanager.analysis.text import anchors as anchors_module
from auditmanager.analysis.text.anchors import (
    BlockIndex,
    ResolvedAnchor,
    UnresolvedAnchor,
    resolve_anchor,
)
from auditmanager.analysis.text.textlayer import load_text_layer

REPO_ROOT = Path(__file__).resolve().parents[3]
MIGRATION = REPO_ROOT / "db" / "migrations" / "versions" / "20260911_0003_open_items.py"
SEAMS = REPO_ROOT / "docs" / "program" / "P02_SEAMS.md"

#: The five-value vocabulary, pinned as literals.
UNGROUNDED_REASONS = frozenset(
    {
        "quotation_absent",
        "quotation_on_different_page",
        "span_outside_page",
        "span_outside_block",
        "span_length_mismatch",
    }
)

PAGE_ONE = "Отчёт за год. Выручка выросла.\n"
PAGE_TWO = "Выручка упала за тот же год.\n"


def _text_layer():
    return load_text_layer(
        {
            "artifact_role": "prepared.text_layer",
            "artifact_version": "1.0.0",
            "version_uid": "ver_01M2545JSD15ETSNNV904X991J",
            "normalization": {"id": "nfc_v1", "description": "NFC"},
            "total_char_count": len(PAGE_ONE) + len(PAGE_TWO),
            "pages": [
                {"page_number": 1, "char_start": 0, "char_end": len(PAGE_ONE), "text": PAGE_ONE},
                {
                    "page_number": 2,
                    "char_start": len(PAGE_ONE),
                    "char_end": len(PAGE_ONE) + len(PAGE_TWO),
                    "text": PAGE_TWO,
                },
            ],
        }
    )


# --- the authority ------------------------------------------------------------------


def test_the_vocabulary_matches_the_migrations_check_constraint() -> None:
    """`ck_finding_observation_ungrounded_reason`, parsed out of migration `0003`."""
    sql = MIGRATION.read_text(encoding="utf-8")
    match = re.search(
        r"ck_finding_observation_ungrounded_reason.*?ungrounded_reason IN \((.*?)\)",
        sql,
        re.S,
    )
    assert match is not None, "the migration no longer declares the vocabulary CHECK"
    from_db = frozenset(
        part.strip().strip("'").strip()
        for part in match.group(1).split(",")
        if part.strip().strip("'").strip()
    )
    assert from_db == UNGROUNDED_REASONS


def test_the_seams_document_states_the_same_five_values() -> None:
    prose = SEAMS.read_text(encoding="utf-8")
    for reason in sorted(UNGROUNDED_REASONS):
        assert f"`{reason}`" in prose, reason


def test_every_reason_this_module_can_emit_is_in_the_persisted_vocabulary() -> None:
    """AN-12 and AN-13. A reason outside the CHECK cannot be written to the database."""
    emitted = {
        anchors_module.REASON_ABSENT,
        anchors_module.REASON_DIFFERENT_PAGE,
        anchors_module.REASON_SPAN_OUTSIDE_PAGE,
        anchors_module.REASON_LENGTH_MISMATCH,
    }
    assert emitted <= UNGROUNDED_REASONS
    # And each is the specific value, not merely *some* member of the set.
    assert anchors_module.REASON_ABSENT == "quotation_absent"
    assert anchors_module.REASON_DIFFERENT_PAGE == "quotation_on_different_page"
    assert anchors_module.REASON_SPAN_OUTSIDE_PAGE == "span_outside_page"
    assert anchors_module.REASON_LENGTH_MISMATCH == "span_length_mismatch"


# --- the resolution rules -----------------------------------------------------------


def test_a_present_quotation_resolves_to_its_own_interval() -> None:
    resolved = resolve_anchor(_text_layer(), page_number=1, quote="Выручка выросла")
    assert isinstance(resolved, ResolvedAnchor)
    assert resolved.char_start == 14
    assert resolved.char_end == 29
    assert _text_layer().slice(14, 29) == "Выручка выросла"


def test_a_quotation_absent_from_the_document_is_quotation_absent() -> None:
    outcome = resolve_anchor(_text_layer(), page_number=1, quote="Такого текста нет")
    assert isinstance(outcome, UnresolvedAnchor)
    assert outcome.reason == "quotation_absent"


def test_a_quotation_on_another_page_is_quotation_on_different_page() -> None:
    """The declared page is part of the claim; resolving it elsewhere would repair it."""
    outcome = resolve_anchor(_text_layer(), page_number=1, quote="Выручка упала")
    assert isinstance(outcome, UnresolvedAnchor)
    assert outcome.reason == "quotation_on_different_page"


@pytest.mark.parametrize("page_number", [3, 0, -1, 99])
def test_a_quotation_on_a_page_the_layer_does_not_carry_is_quotation_absent(
    page_number: int,
) -> None:
    """AN-07. An unknown page is `absent`, not `on_different_page`.

    The distinction is real: `on_different_page` asserts the quotation *is* in the
    document, somewhere else. For a page that does not exist, nothing was looked at.
    """
    outcome = resolve_anchor(_text_layer(), page_number=page_number, quote="Выручка выросла")
    assert isinstance(outcome, UnresolvedAnchor)
    assert outcome.reason == "quotation_absent"


def test_surrounding_whitespace_is_stripped_and_the_stripped_literal_is_emitted() -> None:
    resolved = resolve_anchor(_text_layer(), page_number=1, quote="  Выручка выросла  ")
    assert isinstance(resolved, ResolvedAnchor)
    assert resolved.quote == "Выручка выросла"
    assert resolved.char_end - resolved.char_start == len(resolved.quote)


@pytest.mark.parametrize(
    "quote",
    [
        "выручка выросла",   # case-folded
        "ВЫРУЧКА ВЫРОСЛА",   # upper-cased
        "Выручка  выросла",  # collapsed whitespace changed
        "Выручка выросла",  # non-breaking space
    ],
)
def test_nothing_but_surrounding_whitespace_is_forgiven(quote: str) -> None:
    """AN-09. Stripping is "the one liberty taken"; no case-fold, no normalization.

    `P02_SEAMS.md` §4.3 says the normalization is applied once by `source_preparation` and
    that `B3` must not normalize model output, because `B4` compares after that one
    declared normalization and nothing else. A quotation in a different form must fail to
    resolve — the correct fail-closed outcome — rather than be quietly repaired.
    """
    outcome = resolve_anchor(_text_layer(), page_number=1, quote=quote)
    assert isinstance(outcome, UnresolvedAnchor), f"{quote!r} must not resolve"
    # Assert *which* rule refused. A case-insensitive `find` would still fail to produce
    # an anchor -- the slice-back check catches it -- but it would fail as
    # `span_length_mismatch` rather than `quotation_absent`, and that difference is the
    # only thing that distinguishes "never found it" from "found it and then noticed".
    assert outcome.reason == "quotation_absent", (
        f"{quote!r} was located by something before being rejected"
    )


# --- AN-10 and AN-11: the block index is a secondary anchor and never a guess ---------


def _block_index(*spans: tuple[str, int, int, int]) -> BlockIndex:
    return BlockIndex.from_document(
        {
            "blocks": [
                {
                    "block_id": block_id,
                    "page_number": page,
                    "char_start": start,
                    "char_end": end,
                }
                for block_id, page, start, end in spans
            ]
        }
    )


def test_a_block_that_wholly_contains_the_span_is_bound() -> None:
    resolved = resolve_anchor(
        _text_layer(),
        page_number=1,
        quote="Выручка выросла",
        block_index=_block_index(("b_000001", 1, 0, 30)),
    )
    assert isinstance(resolved, ResolvedAnchor)
    assert resolved.block_id == "b_000001"


def test_a_block_that_does_not_wholly_contain_the_span_is_not_bound() -> None:
    """AN-11. Containment is both-ended; a block ending mid-span must not claim it."""
    resolved = resolve_anchor(
        _text_layer(),
        page_number=1,
        quote="Выручка выросла",
        block_index=_block_index(("b_000001", 1, 0, 20)),
    )
    assert isinstance(resolved, ResolvedAnchor)
    assert resolved.block_id is None


def test_two_blocks_containing_the_same_span_bind_nothing() -> None:
    """AN-10. Ambiguous, and a secondary anchor is not worth guessing."""
    resolved = resolve_anchor(
        _text_layer(),
        page_number=1,
        quote="Выручка выросла",
        block_index=_block_index(("b_000001", 1, 0, 30), ("b_000002", 1, 0, 30)),
    )
    assert isinstance(resolved, ResolvedAnchor)
    assert resolved.block_id is None


def test_a_block_on_another_page_does_not_bind() -> None:
    resolved = resolve_anchor(
        _text_layer(),
        page_number=1,
        quote="Выручка выросла",
        block_index=_block_index(("b_000001", 2, 0, 30)),
    )
    assert isinstance(resolved, ResolvedAnchor)
    assert resolved.block_id is None
