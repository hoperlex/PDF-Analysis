"""Re-recognising one page, and the seam a recogniser plugs into.

`R-19` is *re-recognise, do not classify*. What that needs from this context is small and
almost entirely not about models: a page to re-read, a port that returns text, a rule for
deciding whether the text is a repair, and a record of what happened. Every one of those is
testable without a network, and none of them names a provider.

**Why the port is here and the provider is not.** `norms` imports nothing from another
bounded context, which is the property `W33-CORPUS` argued the context into existence on.
A `ProxyAdapter` import would end that, and for no gain: this module needs *text back from a
page image*, which is one method. The composition — proxy settings, credential, transport —
belongs to the runner in :mod:`auditmanager.norms.__main__`, which is a composition point
and is allowed to know about both sides.

**The two-attempt rule, and why it stops at two.** A page that comes back degenerate is
re-read once. A page that comes back degenerate **twice** is left alone and recorded, because
at that point the evidence is about the page rather than about the call: the same model, the
same crop and the same prompt produced the same failure, and a third attempt buys a
coin-flip at the owner's expense. `R-19`'s cost ceiling is not the reason — the reason is
that *"this page re-recognises degenerate twice"* is a finding the owner asked for, and an
unbounded retry loop converts that finding into a bill.

**Nothing degenerate is ever applied.** :func:`rerecognise` returns a ``PageRepair`` whose
``replacement`` is ``None`` unless the text passed :func:`~auditmanager.norms.degeneracy.inspect`
clean. The attempt is kept with its signals, so the evidence survives; the corpus text stands.

**The prompt is a constant in the tree, not a parameter.** Two runs of this repair must be
comparable, and a prompt that a caller can vary makes *"the page re-recognised degenerate
twice"* a statement about an argument nobody recorded. It is also the one place where the
original failure can be argued about: the drop's own prompt told the model to *"act as a
strict transcription engine"* and *"return clean safe HTML only"*, and the model emitted
those sentences as the page. The prompt below therefore states the prohibition in terms of
the **output**, names no format the model has to describe, and asks for nothing it could
narrate.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from .degeneracy import inspect
from .repair import PageRepair, RepairAttempt, RepairOutcome

#: The instruction the re-recognition runs under.
#:
#: Deliberately short. The drop's degenerate pages are, in substance, the recognition prompt
#: itself: a long numbered ruleset that the model enumerated back instead of following. Every
#: sentence here is a constraint on what may appear in the answer, and there is no numbered
#: list for a model to continue.
RECOGNITION_SYSTEM_PROMPT: str = (
    "Ты распознаёшь одну страницу российского нормативного документа по её изображению.\n"
    "\n"
    "В ответе — только текст самой страницы, по-русски, обычным markdown. "
    "Таблицу передавай markdown-таблицей. Формулы и обозначения — как на странице.\n"
    "\n"
    "В ответе не должно быть ничего, кроме текста страницы: ни описания страницы, "
    "ни рассуждений, ни плана, ни пояснений, ни упоминания этой инструкции, "
    "ни фраз о том, что ты делаешь. Если на странице нет текста, ответ пустой."
)

#: How many times one page is read before it is left alone. See the header.
MAX_ATTEMPTS: int = 2

#: The smallest answer that can be a transcription of a page that had text on it. A page
#: whose replacement is shorter than this is recorded ``UNUSABLE`` rather than applied: an
#: empty or near-empty answer is a silent deletion of whatever the page held, and `R-20`'s
#: *nothing is cut* forbids reaching that outcome by accident.
MINIMUM_REPLACEMENT_CHARACTERS: int = 16


@dataclass(frozen=True, slots=True)
class PageToRecognise:
    """One block of one document, with the crop the pipeline already fetched for it.

    ``crop`` is the bytes of `corpus/<slug>/crops/<block_id>.pdf` — a single-page PDF, one per
    block, 28 246 of them in the drop. It is passed as bytes rather than as a path because
    this context does not decide where the corpus lives (`corpus_source` does) and because a
    recogniser that took a path could read something else.
    """

    document_slug: str
    block_id: str
    page_label: int
    original_text: str
    crop: bytes

    @property
    def original_sha256(self) -> str:
        return hashlib.sha256(self.original_text.encode("utf-8")).hexdigest()

    @property
    def crop_sha256(self) -> str:
        return hashlib.sha256(self.crop).hexdigest()


@dataclass(frozen=True, slots=True)
class RecognisedPage:
    """What a recogniser hands back. Shaped after ``ModelResponse`` on purpose.

    ``cost_usd`` is ``None`` when the transport priced nothing. It is not defaulted to zero:
    a wave that must answer *"what did you spend"* cannot have "free" and "unknown" collapse
    into one number, which is the distinction ``cost.py`` already draws for the analysis
    stage.
    """

    text: str
    model: str
    stop_reason: str
    input_tokens: int
    output_tokens: int
    cost_usd: float | None = None

    @property
    def truncated(self) -> bool:
        """The provider stopped at the output ceiling, so the transcription is incomplete.

        The vocabulary is the provider's, as `W23-PARTIAL` settled it: ``max_tokens`` and
        nothing else decides. A truncated page is ``UNUSABLE`` — half a norm's clause read as
        the whole of it is worse than the degenerate text it would have replaced, because
        nothing downstream can see that it is half.
        """
        return self.stop_reason == "max_tokens"


@runtime_checkable
class PageRecogniser(Protocol):
    """The one thing this context needs from the outside world."""

    def recognise(self, page: PageToRecognise) -> RecognisedPage: ...


def rerecognise(
    page: PageToRecognise,
    recogniser: PageRecogniser,
    *,
    now: str,
    max_attempts: int = MAX_ATTEMPTS,
) -> PageRepair:
    """Re-read one page, up to ``max_attempts`` times, and record what happened.

    ``now`` is passed in rather than read from a clock, so that two runs over one fake
    recogniser produce one value and the ledger is comparable between runs. This context has
    no clock anywhere else for the same reason.
    """
    if max_attempts < 1:
        raise ValueError("a page is read at least once or not at all")

    attempts: list[RepairAttempt] = []
    replacement: str | None = None
    outcome = RepairOutcome.NOT_ATTEMPTED

    for ordinal in range(1, max_attempts + 1):
        answer = recogniser.recognise(page)
        text = answer.text.strip()
        verdict = inspect(text)
        attempts.append(
            RepairAttempt(
                ordinal=ordinal,
                recognised_at=now,
                model=answer.model,
                stop_reason=answer.stop_reason,
                input_tokens=answer.input_tokens,
                output_tokens=answer.output_tokens,
                cost_usd=answer.cost_usd,
                characters=len(text),
                text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                signals=verdict.signals,
                evidence=verdict.evidence,
            )
        )

        if answer.truncated or len(text) < MINIMUM_REPLACEMENT_CHARACTERS:
            # Not a repair and not a retryable shape: the ceiling and the empty answer are
            # both properties of this page against this prompt. Retrying spends again for the
            # same outcome.
            outcome = RepairOutcome.UNUSABLE
            break
        if not verdict.is_degenerate:
            replacement = text
            outcome = RepairOutcome.REPAIRED
            break
        outcome = RepairOutcome.STILL_DEGENERATE

    return PageRepair(
        document_slug=page.document_slug,
        block_id=page.block_id,
        page_label=page.page_label,
        original_sha256=page.original_sha256,
        original_characters=len(page.original_text),
        crop_sha256=page.crop_sha256,
        outcome=outcome,
        replacement=replacement,
        attempts=tuple(attempts),
    )
