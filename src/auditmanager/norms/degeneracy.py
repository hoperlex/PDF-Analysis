"""Is this page the norm's text, or the recognition model talking about the norm?

`D-59`: 79 of the corpus's 28 249 blocks carry the recognition model's own reasoning where
the document's text should be. The corpus's own vocabulary cannot express that — **every one
of the 79 is marked `recognized`** — so there is nothing structural to filter on and the
question has to be asked of the text itself. `R-19` repairs the source rather than classifying
the symptom; this module is the check that says whether a repair worked.

**What this module is for, stated narrowly.** It is not a quality score and it is not a
language detector. It answers one question — *does this text speak about the page instead of
transcribing it* — and it answers it in four families, each of which is a different way the
same failure shows up in the drop:

`INSTRUCTION_ECHO`
    The recognition prompt's own words, read back as content: *"act as a strict transcription
    engine"*, *"return clean safe HTML only"*, *"inside the exact crop"*. The model was handed
    its instructions and emitted them.

`FIRST_PERSON_PLAN`
    The model speaking as itself about what it is about to do: *"The user wants me to…"*,
    *"I will transcribe the table exactly as it appears"*, *"**Transcription strategy:**"*.
    This is the family `D-59` was found by.

`PAGE_NARRATION`
    English description of the page in place of the page: *"The document is a technical table
    from a Russian engineering standard…"*, *"The first table lists districts in Kemerovo
    Oblast"*. No first-person pronoun appears, so the `D-59` grep never saw these — and the
    longest of them is **50 989 characters**.

`SERIALISED_PAYLOAD`
    Not the model at all: the pipeline's own JSON envelope, `[{"text": "…"`, written into the
    body. A different leak with the same consequence, and it is here because a repaired page
    carrying it is no more usable than one carrying the other three.

**Two families that were measured and deliberately left out**, because a guard that fires on
legitimate text costs more than it saves:

- **token repetition.** The obvious signal for *"the model looped"*, and it does catch
  `СП_131.13330.2025` page 280, where `Vladikavkaz` is 98 % of the tokens. But
  `ГОСТ_9544-2015`'s seal-tightness tables sit at **0.72–0.86** on `PN` and are entirely
  legitimate, and `ГОСТ_33259-2015` page 23 reaches **0.90** on a real flange table. One loop
  above the noise and 27 blocks inside it: the margin is too thin to assert on.
- **ascending enumeration runs.** Of the three blocks in the corpus with 40+ consecutive
  ascending integers, **two are the real symbol table of `ГОСТ_2.304-81`** and one is a
  narration. Two false positives out of three is not a guard.

Both are recorded in `docs/program/W39-CORPUS.md` with the commands, because they are real
defects in the drop even though they are not *this* defect.

Every phrase below is case-folded before comparison and was taken from a block in the drop,
never invented. `OPERATING_CONSTRAINTS.md` §12 asks for more than one spelling of a thing:
these are four independent families and the corpus measurement of each is in the wave record.
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass


class DegeneracySignal(enum.Enum):
    """The four ways a block turns out not to be the document's text."""

    INSTRUCTION_ECHO = "instruction_echo"
    FIRST_PERSON_PLAN = "first_person_plan"
    PAGE_NARRATION = "page_narration"
    SERIALISED_PAYLOAD = "serialised_payload"


#: The recognition prompt read back as content.
INSTRUCTION_ECHO_PHRASES: tuple[str, ...] = (
    "transcription engine",
    "clean safe html",
    "image fragment",
    "inside the exact crop",
    "visibly present",
    "never output any commentary",
    "extract only visible text",
    "extract only text and table content",
)

#: The model speaking as itself about the task.
FIRST_PERSON_PLAN_PHRASES: tuple[str, ...] = (
    "the user wants",
    "i will transcribe",
    "i must adhere",
    "i must ensure",
    "i need to extract",
    "i will extract",
    "i will use html",
    "i will follow these instructions",
    "i will now",
    "i'll transcribe",
    "i am a strict",
    "my task is",
    "transcription strategy",
    "let me ",
    "i should ",
)

#: English description of the page in place of the page.
PAGE_NARRATION_PHRASES: tuple[str, ...] = (
    "the document is a",
    "the table is divided",
    "the page is numbered",
    "the table lists",
    "the image shows",
    "the table contains",
    "the table has",
    "the first table lists",
    "the page contains",
    "this appears to be",
    "it appears to be",
)

#: `[{"text": "…"` and `, "text": "…"` — the pipeline's envelope, not the page.
SERIALISED_PAYLOAD = re.compile(r'[\[,]\s*\{?\s*"text"\s*:')

_FAMILIES: tuple[tuple[DegeneracySignal, tuple[str, ...]], ...] = (
    (DegeneracySignal.INSTRUCTION_ECHO, INSTRUCTION_ECHO_PHRASES),
    (DegeneracySignal.FIRST_PERSON_PLAN, FIRST_PERSON_PLAN_PHRASES),
    (DegeneracySignal.PAGE_NARRATION, PAGE_NARRATION_PHRASES),
)


@dataclass(frozen=True, slots=True)
class DegeneracyVerdict:
    """What the check found, and the phrase it found it by.

    The evidence is carried rather than discarded because a bare boolean cannot be argued
    with. A reviewer disputing a verdict needs the words that produced it, and a repair that
    comes back degenerate a second time is a finding someone has to read (`R-19`).
    """

    signals: tuple[DegeneracySignal, ...]
    evidence: tuple[str, ...]

    @property
    def is_degenerate(self) -> bool:
        return bool(self.signals)

    def describe(self) -> str:
        """One line naming the families and the first phrase of each. For a test's message."""
        if not self.signals:
            return "clean"
        return "; ".join(
            f"{signal.value}: {phrase!r}" for signal, phrase in zip(self.signals, self.evidence)
        )


def inspect(text: str) -> DegeneracyVerdict:
    """Ask one block's body whether it is the document's text.

    Signals come back in the order of :data:`_FAMILIES` rather than in the order they occur in
    the text, so two runs over one string produce one verdict and the value is comparable
    between runs — the same reason every value in this context is frozen.
    """
    folded = text.casefold()
    signals: list[DegeneracySignal] = []
    evidence: list[str] = []
    for signal, phrases in _FAMILIES:
        found = next((phrase for phrase in phrases if phrase in folded), None)
        if found is not None:
            signals.append(signal)
            evidence.append(found)
    payload = SERIALISED_PAYLOAD.search(text)
    if payload is not None:
        signals.append(DegeneracySignal.SERIALISED_PAYLOAD)
        evidence.append(payload.group(0))
    return DegeneracyVerdict(signals=tuple(signals), evidence=tuple(evidence))


def is_degenerate(text: str) -> bool:
    """The whole check as a predicate, for a caller that does not need the evidence."""
    return inspect(text).is_degenerate
