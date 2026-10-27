"""The analysis input budget (``W55-PLAN.md`` section B3.3, G-11, owner ruling R-118).

Text analysis sends the whole text layer in one prompt, and the per-run cost ceiling of
``OD-03`` (:mod:`.cost`) halts a run *after* the call that took the meter past it, with
nothing published. A document too large for the ceiling therefore used to be discovered
by paying for it. This module turns the question round: given the configured model and
the ceiling, how many characters of a document can a run afford to send *and still finish
under the ceiling*? ``startRun`` and ``reauditRun`` refuse a version above that figure up
front, before any run exists.

The unit is **characters of pypdfium2's count** (``document_version.text_character_count``,
``W55B-INGEST-01``), because that is the only measure a version carries before its text has
been extracted. The prompt is rendered from pdfplumber's text layer
(:func:`~auditmanager.analysis.text.prompt.render_document`), so the calibration below is
the bridge between the two.

The arithmetic
--------------
::

    output_usd      = MAX_OUTPUT_TOKENS * output rate            (the cap is spent in full)
    input_tokens    = (ceiling - output_usd) / input rate
    budget          = floor(input_tokens * CHARACTERS_PER_TOKEN)
                      - len(system prompt) - len(response schema)   (sent with every call)
                      - PAGE_FRAMING_ALLOWANCE_CHARACTERS           (the banners, see below)
                      - reserved_characters                         (W57's norms context)

clamped at zero. Both rates come from ``docs/program/P02_LOCK.json`` through :mod:`.lock`;
no rate and no model identifier is written down here, and a model the lock does not pin
is refused rather than guessed at.

* **The output cap is priced in full.** The stage asks for at most ``MAX_OUTPUT_TOKENS``
  tokens, adaptive thinking included. Real replies in the PC-02 baseline were 10 to 546
  tokens, but a ceiling that holds only when the model is brief would be a ceiling that
  fails exactly when a long document makes it think longest.
* **One model call per run.** PC-01's text analysis is a single call, so one output cap is
  reserved. A stage that adds calls (W56's block analysis and critic) must revisit this.
* **The context window is not modelled.** The binding constraint at the default ceiling is
  the cost: the lock's one-million-token context is more than eight times the input a one
  dollar ceiling buys at the pinned rate. ``ModelPin`` carries no context, so a ceiling
  high enough for the window to bind (about five and a half dollars for the primary model) is not
  caught here; the provider refuses such a request itself, loudly.
* **Only a character count exists at the check**, not a page count. The prompt frames each
  page with a banner and blank lines; the allowance reserves that framing once, for the
  largest document the upload envelope admits.

The measured figures that fix the constants are recorded, with their method, in
``docs/program/W55B-BUDGET-01.md`` section 3, and the committed test
``tests/integration/analysis_text/test_input_budget_calibration.py`` re-derives them from
the same recorded evidence, so a constant that stops covering a measured document turns it
red.
"""

from __future__ import annotations

import math
from fractions import Fraction
from typing import Final

from auditmanager.analysis.text.lock import ProviderLock, provider_lock
from auditmanager.analysis.text.prompt import (
    AR_TEXT_PROMPT_BUNDLE,
    canonical_json,
)

#: Characters per input token the budget assumes for the whole request.
#:
#: **Provenance.** Measured, not assumed. The only real (live, ``cost_basis: measured``)
#: input-token counts the repository holds are the fourteen documents of the PC-02 baseline
#: (``artifacts/validation/PC-02/baseline/ledger.json``, 2026-09-14, ``claude-opus-5``
#: through the proxy) and the synthetic AR baseline of the PC-01 re-certification (three
#: runs, 3 895 input tokens each; ``artifacts/checkpoints/PC-01/recertification-*.json``).
#: The prompt has not changed since 2026-09-10, so those counts are for today's prompt.
#: Each request's tokens over the characters it carried (system prompt + response schema +
#: the rendered document) are 0.459 to 0.472 tokens per character for the fourteen PC-02
#: documents (2.12 to 2.18 characters per token) and 0.511 for the AR baseline (1.958
#: characters per token), the densest. 1.4 assumes **40 % more tokens per character** than
#: that densest figure (1.958 / 1.4) and 53 % more than the PC-02 mean (2.14): real
#: architectural text (dimensions, tables, designations) is denser than a synthetic
#: document, and the AR baseline is the nearest thing to it that was measured. A
#: ``Fraction`` so the arithmetic below is exact and the budget monotone.
CHARACTERS_PER_TOKEN: Final[Fraction] = Fraction(7, 5)

#: What the prompt adds around a document's text, for the largest document the upload
#: envelope admits (500 pages, ``ingest.MAX_PAGES``).
#:
#: ``prompt.render_document`` prefixes a preamble and puts ``=== Страница N ===`` and a
#: blank line around every page: 11 472 characters for 500 empty pages, measured by
#: ``tests/integration/analysis_text/test_input_budget_calibration.py``, which fails if the
#: envelope's page limit or the rendering outgrows this allowance. Rounded up to 12 000.
PAGE_FRAMING_ALLOWANCE_CHARACTERS: Final[int] = 12_000

#: The real 30-page АР set, in pypdfium2 characters: 93 690 (``W55B-INGEST-01`` section
#: 2.1, counts only; the file itself is never read by the repository's tests). A
#: configuration whose budget does not reach it cannot analyse the one document the
#: product exists for, and is refused when the application starts (``bootstrap/settings``).
REFERENCE_DOCUMENT_CHARACTERS: Final[int] = 93_690


def _exact(value: float) -> Fraction:
    """A float as the decimal it prints as, so ``0.4`` is two fifths and not a neighbour of it."""
    return Fraction(repr(float(value)))


def _fixed_prompt_characters() -> int:
    """What every request carries whatever the document: the system prompt and the schema."""
    bundle = AR_TEXT_PROMPT_BUNDLE
    return len(bundle.system_prompt) + len(canonical_json(bundle.response_schema))


def input_budget_characters(
    model_id: str,
    ceiling_usd: float,
    reserved_characters: int = 0,
    *,
    lock: ProviderLock | None = None,
) -> int:
    """The most pypdfium2 characters a document may have for a run to finish under the ceiling.

    ``reserved_characters`` is room set aside for text the document does not carry -- W57's
    norms context, which ``CAP-01`` fixes. It defaults to zero and is subtracted.

    Never negative: a ceiling the output cap alone exhausts, or a reservation larger than
    the room, is a budget of zero. Monotone: a higher ceiling never lowers the figure, and a
    larger reservation never raises it. An unpinned ``model_id`` raises
    :class:`~auditmanager.shared.errors.DomainError` (``model_not_pinned``) -- the budget of
    a model whose rates are unknown is not a number anyone should act on. ``lock`` exists so
    a test can point at a variant lock.
    """
    if reserved_characters < 0:
        raise ValueError("reserved_characters must not be negative")
    if not math.isfinite(ceiling_usd) or ceiling_usd < 0:
        raise ValueError("ceiling_usd must be a finite, non-negative number of US dollars")

    pin = (lock or provider_lock()).model(model_id)
    input_rate = _exact(pin.input_per_mtok_usd)
    if input_rate <= 0:
        raise ValueError("a pinned input rate must be positive")

    output_usd = (
        Fraction(AR_TEXT_PROMPT_BUNDLE.max_output_tokens)
        * _exact(pin.output_per_mtok_usd)
        / 1_000_000
    )
    input_tokens = (_exact(ceiling_usd) - output_usd) * 1_000_000 / input_rate
    if input_tokens <= 0:
        return 0
    characters = (
        math.floor(input_tokens * CHARACTERS_PER_TOKEN)
        - _fixed_prompt_characters()
        - PAGE_FRAMING_ALLOWANCE_CHARACTERS
        - reserved_characters
    )
    return max(0, characters)


#: `SECTION-CHUNKED-ANALYSIS-01`. The most whole-page windows one run may take.
#:
#: A volume whose recorded character count is **not above** the one-call figure
#: (:func:`input_budget_characters`) is analysed exactly as before, in one call. A larger one is analysed
#: in whole-page windows, each window one call of at most that figure, all of them under the run's one
#: cost ceiling; ``startRun`` and ``reauditRun`` refuse a volume above ``N`` windows' worth, and the stage
#: refuses a plan that comes out above ``N`` windows (page packing can need more than the character
#: count suggests).
#:
#: Why twelve. The upload envelope admits 500 pages and the one real set is 3 123 characters a page
#: (:data:`REFERENCE_DOCUMENT_CHARACTERS` / 30), about 1.56 million characters: 10.2 windows of the primary
#: model's 152 361, so twelve covers the envelope with slack. Twelve windows are also three Attempts of four
#: windows at the proxy's 200 second per-call ceiling inside the 900 second watchdog
#: (``jobs.lease.ATTEMPT_WATCHDOG_SECONDS``, ``R-146y``). The ceiling, not this number, bounds the spend.
#:
#: ``1`` restores the one-call behaviour exactly (the start-time limit equals the per-call figure and no
#: version above it is admitted), which is the rollback of the whole feature.
MAX_ANALYSIS_WINDOWS: Final[int] = 12


def windowed_budget_characters(
    call_budget_characters: int, max_windows: int = MAX_ANALYSIS_WINDOWS
) -> int:
    """The most pypdfium2 characters a version may have for a run to be accepted: ``max_windows`` calls' worth.

    ``call_budget_characters`` is the per-call figure (what ``settings`` and the connection route hand to
    ``startRun``, :func:`input_budget_characters`); a window is never larger than it. Exact integer
    arithmetic, monotone in both arguments, and equal to the per-call figure for one window.
    """
    if type(call_budget_characters) is not int or call_budget_characters < 0:
        raise ValueError("call_budget_characters must be a non-negative whole number")
    if type(max_windows) is not int or max_windows < 1:
        raise ValueError("max_windows must be a positive whole number")
    return call_budget_characters * max_windows


__all__ = [
    "CHARACTERS_PER_TOKEN",
    "MAX_ANALYSIS_WINDOWS",
    "PAGE_FRAMING_ALLOWANCE_CHARACTERS",
    "REFERENCE_DOCUMENT_CHARACTERS",
    "input_budget_characters",
    "windowed_budget_characters",
]
