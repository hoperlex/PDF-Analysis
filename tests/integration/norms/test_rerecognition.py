"""`R-19`'s repair, as data: what is applied, what is recorded, and what it does to `R-17`.

No network and no provider. The recogniser is a fake because every rule worth guarding here
is about what the context does with an answer, not about how the answer arrives — and a guard
that needed a credential would be a guard nobody runs.
"""

from __future__ import annotations

import json

import pytest

from auditmanager.norms import (
    DegeneracySignal,
    PageRepair,
    PageToRecognise,
    RecognisedPage,
    RepairLedger,
    RepairOutcome,
    derive,
    fingerprint,
    ledger_of,
    repaired_snapshot,
    rerecognise,
)
from auditmanager.norms.__main__ import RunRefused, resolve_transport

CLEAN_PAGE = (
    "##### 7.2 РАСЧЁТ ПО ПРЕДЕЛЬНЫМ СОСТОЯНИЯМ\n\n"
    "7.2.4 Расчёт элементов железобетонных конструкций по прочности производят "
    "для сечений, нормальных к их продольной оси."
)
DEGENERATE_PAGE = (
    "The user wants me to act as a strict transcription engine for Russian construction "
    "documents. I must adhere to the following rules: 1. Extract only visible text."
)

NOW = "2026-09-23T00:00:00+00:00"


class FakeRecogniser:
    """Answers from a script, and counts how many times it was asked."""

    def __init__(self, *answers: RecognisedPage) -> None:
        self._answers = list(answers)
        self.calls = 0

    def recognise(self, page: PageToRecognise) -> RecognisedPage:
        self.calls += 1
        return self._answers[min(self.calls, len(self._answers)) - 1]


def answer(text: str, *, stop_reason: str = "end_turn", cost_usd: float | None = 0.03) -> RecognisedPage:
    return RecognisedPage(
        text=text,
        model="a-model",
        stop_reason=stop_reason,
        input_tokens=1800,
        output_tokens=900,
        cost_usd=cost_usd,
    )


@pytest.fixture
def page() -> PageToRecognise:
    return PageToRecognise(
        document_slug="СП_63_13330_2018",
        block_id="blk_" + "a" * 32,
        page_label=70,
        original_text=DEGENERATE_PAGE,
        crop=b"%PDF-1.4 not a real pdf, and nothing here opens it",
    )


# --- what is applied, and what is not ------------------------------------------------


def test_a_clean_answer_is_applied_and_the_page_is_read_once(page: PageToRecognise) -> None:
    recogniser = FakeRecogniser(answer(CLEAN_PAGE))
    repair = rerecognise(page, recogniser, now=NOW)
    assert repair.outcome is RepairOutcome.REPAIRED
    assert repair.replacement == CLEAN_PAGE
    assert recogniser.calls == 1


def test_a_degenerate_answer_is_read_again_and_a_clean_second_answer_is_applied(
    page: PageToRecognise,
) -> None:
    recogniser = FakeRecogniser(answer(DEGENERATE_PAGE), answer(CLEAN_PAGE))
    repair = rerecognise(page, recogniser, now=NOW)
    assert recogniser.calls == 2
    assert repair.outcome is RepairOutcome.REPAIRED
    assert repair.replacement == CLEAN_PAGE
    assert repair.attempts[0].signals  # the first answer's evidence survives
    assert repair.attempts[1].was_clean


def test_a_page_degenerate_twice_is_recorded_and_the_corpus_text_stands(
    page: PageToRecognise,
) -> None:
    """`R-19`'s finding, not `R-19`'s failure.

    Swapping one unusable page for another unusable page would count as a repair in every
    summary while changing nothing a reader can use — `AGENTS.md` §4's silent fallback, with
    a bill. The replacement is unreachable and the signals are kept so the count can be read.
    """
    recogniser = FakeRecogniser(answer(DEGENERATE_PAGE))
    repair = rerecognise(page, recogniser, now=NOW)
    assert recogniser.calls == 2
    assert repair.outcome is RepairOutcome.STILL_DEGENERATE
    assert repair.replacement is None
    assert DegeneracySignal.FIRST_PERSON_PLAN in repair.attempts[-1].signals


def test_a_truncated_transcription_is_never_applied(page: PageToRecognise) -> None:
    """Half a clause read as the whole of it is worse than the text it would replace."""
    recogniser = FakeRecogniser(answer(CLEAN_PAGE, stop_reason="max_tokens"))
    repair = rerecognise(page, recogniser, now=NOW)
    assert repair.outcome is RepairOutcome.UNUSABLE
    assert repair.replacement is None
    assert recogniser.calls == 1  # the ceiling is a property of the page, not of the call


def test_an_all_but_empty_answer_is_never_applied(page: PageToRecognise) -> None:
    """Otherwise a repair deletes whatever the page held, and `R-20` says nothing is cut."""
    recogniser = FakeRecogniser(answer("—"))
    repair = rerecognise(page, recogniser, now=NOW)
    assert repair.outcome is RepairOutcome.UNUSABLE
    assert repair.replacement is None


def test_a_page_that_was_not_repaired_cannot_carry_a_replacement() -> None:
    with pytest.raises(ValueError, match="must not be reachable"):
        PageRepair(
            document_slug="s",
            block_id="b",
            page_label=1,
            original_sha256="0" * 64,
            original_characters=10,
            crop_sha256="1" * 64,
            outcome=RepairOutcome.STILL_DEGENERATE,
            replacement="text that was not good enough to apply",
            attempts=(),
        )


# --- what a spend can be stated from ------------------------------------------------


def test_an_unpriced_call_is_not_read_as_a_free_one(page: PageToRecognise) -> None:
    """`cost.py` draws the same line for the analysis stage: measured is not estimated.

    A transport that prices nothing and a transport that charges nothing produce the same
    `0.00`, and only one of them means the run can state what it spent.
    """
    recogniser = FakeRecogniser(answer(CLEAN_PAGE, cost_usd=None))
    repair = rerecognise(page, recogniser, now=NOW)
    assert repair.cost_usd == 0.0
    assert repair.unpriced_attempts == 1


def test_a_priced_call_is_summed_over_every_attempt(page: PageToRecognise) -> None:
    recogniser = FakeRecogniser(answer(DEGENERATE_PAGE, cost_usd=0.02), answer(CLEAN_PAGE, cost_usd=0.03))
    repair = rerecognise(page, recogniser, now=NOW)
    assert repair.cost_usd == pytest.approx(0.05)
    assert repair.unpriced_attempts == 0


# --- the ledger ----------------------------------------------------------------------


def _repair(slug: str, block: str, *, replacement: str | None = CLEAN_PAGE) -> PageRepair:
    return PageRepair(
        document_slug=slug,
        block_id=block,
        page_label=1,
        original_sha256="0" * 64,
        original_characters=len(DEGENERATE_PAGE),
        crop_sha256="1" * 64,
        outcome=RepairOutcome.REPAIRED if replacement else RepairOutcome.STILL_DEGENERATE,
        replacement=replacement,
        attempts=(),
    )


def test_two_repairs_for_one_block_are_refused() -> None:
    with pytest.raises(ValueError, match="two repairs for one block"):
        ledger_of("snap", NOW, [_repair("a", "blk_1"), _repair("a", "blk_1")])


def test_a_ledger_of_an_unknown_version_is_refused() -> None:
    document = ledger_of("snap", NOW, [_repair("a", "blk_1")]).as_document()
    document["version"] = "99"
    with pytest.raises(ValueError, match="refusing to guess"):
        RepairLedger.from_document(document)


def test_the_ledger_round_trips_through_json() -> None:
    ledger = ledger_of("snap", NOW, [_repair("b", "blk_2"), _repair("a", "blk_1")])
    restored = RepairLedger.from_document(json.loads(ledger.as_json()))
    assert restored == ledger
    assert [r.document_slug for r in restored.repairs] == ["a", "b"]


def test_an_unapplied_repair_reads_as_use_what_the_corpus_says() -> None:
    ledger = ledger_of("snap", NOW, [_repair("a", "blk_1", replacement=None)])
    assert ledger.replacement_for("a", "blk_1") is None
    assert ledger.replacement_for("a", "never-seen") is None


# --- `R-17`: does a re-recognition move the snapshot identifier? ----------------------


@pytest.fixture
def base_snapshot():
    return derive(
        [
            fingerprint("a", "doc_a", b"one", "2026-07-23"),
            fingerprint("b", "doc_b", b"two", "2026-08-20"),
            fingerprint("c", "doc_c", b"three", None),
        ]
    )


def test_a_repair_moves_the_identifier_and_says_how_many(base_snapshot) -> None:
    """The base digest is over `results.md` bytes a repair does not touch, so without this
    the repaired corpus and the raw one share an identifier and no verdict row can say which
    text the expert read. That is `R-17`'s own recorded consequence, with our hand on it."""
    ledger = ledger_of(base_snapshot.snapshot_id, NOW, [_repair("a", "blk_1")])
    repaired = repaired_snapshot(base_snapshot, ledger)
    assert repaired.snapshot_id != base_snapshot.snapshot_id
    assert repaired.content_digest != base_snapshot.content_digest
    assert "+1r." in repaired.snapshot_id


def test_the_window_does_not_move_when_a_page_is_repaired(base_snapshot) -> None:
    """A repair says nothing about when the corpus was drawn."""
    ledger = ledger_of(base_snapshot.snapshot_id, NOW, [_repair("a", "blk_1")])
    repaired = repaired_snapshot(base_snapshot, ledger)
    assert repaired.drawn_from == base_snapshot.drawn_from
    assert repaired.drawn_to == base_snapshot.drawn_to
    assert repaired.footnote_window == base_snapshot.footnote_window
    assert repaired.undated_documents == base_snapshot.undated_documents


def test_a_ledger_that_applied_nothing_returns_the_base_unchanged(base_snapshot) -> None:
    """An empty repair pass is not a new corpus, and an identifier is not a record of effort."""
    ledger = ledger_of(base_snapshot.snapshot_id, NOW, [_repair("a", "blk_1", replacement=None)])
    assert repaired_snapshot(base_snapshot, ledger) == base_snapshot


def test_the_identifier_does_not_depend_on_the_order_repairs_were_taken_in(base_snapshot) -> None:
    """A partially completed run has no guaranteed order and the corpus has no commit name."""
    repairs = [_repair("b", "blk_2"), _repair("a", "blk_1"), _repair("a", "blk_9")]
    first = repaired_snapshot(base_snapshot, ledger_of(base_snapshot.snapshot_id, NOW, repairs))
    second = repaired_snapshot(
        base_snapshot, ledger_of(base_snapshot.snapshot_id, NOW, list(reversed(repairs)))
    )
    assert first.snapshot_id == second.snapshot_id


def test_one_changed_character_in_one_replacement_changes_the_identifier(base_snapshot) -> None:
    one = ledger_of(base_snapshot.snapshot_id, NOW, [_repair("a", "blk_1", replacement=CLEAN_PAGE)])
    other = ledger_of(
        base_snapshot.snapshot_id, NOW, [_repair("a", "blk_1", replacement=CLEAN_PAGE + ".")]
    )
    assert (
        repaired_snapshot(base_snapshot, one).snapshot_id
        != repaired_snapshot(base_snapshot, other).snapshot_id
    )


def test_a_ledger_from_another_corpus_is_refused(base_snapshot) -> None:
    ledger = ledger_of("some-other-corpus", NOW, [_repair("a", "blk_1")])
    with pytest.raises(ValueError, match="attribute one corpus's repairs to another"):
        repaired_snapshot(base_snapshot, ledger)


# --- the runner's refusals, before a single call -------------------------------------


def test_a_proxy_url_with_no_host_is_refused() -> None:
    """Measured on this host on 2026-09-23: `infra/deploy/env/provider.env` held exactly this.

    `ProxySettings` checks only that the string starts with `http://` or `https://`, so
    `http://:59990` is constructed happily and fails at call time as
    `dependency_unavailable` — a retryable outage, for a lane pointed at nothing.
    """
    with pytest.raises(RunRefused, match="names no host"):
        resolve_transport(
            {
                "PROXY_LLM_BASE_URL": "http://:59990",
                "PROXY_LLM_TOKEN": "t",
                "PROXY_LLM_MODEL": "m",
            }
        )


def test_a_missing_credential_is_refused_by_name_and_never_by_value() -> None:
    with pytest.raises(RunRefused) as refusal:
        resolve_transport({"PROXY_LLM_BASE_URL": "https://example.invalid", "PROXY_LLM_MODEL": "m"})
    assert "PROXY_LLM_TOKEN" in str(refusal.value)
    assert "example.invalid" not in str(refusal.value)


def test_a_complete_transport_resolves() -> None:
    assert resolve_transport(
        {
            "PROXY_LLM_BASE_URL": "https://proxy.example.invalid",
            "PROXY_LLM_TOKEN": "t",
            "PROXY_LLM_MODEL": "m",
        }
    ) == ("https://proxy.example.invalid", "t", "m")
