"""The vocabulary of the AI check of the doubtful sheet pairs (`CMP-VC-AIPAIR-01`, ADR-0025 decisions 3, 14, 19 and 20).

Plain records and constants; nothing here reads a database or calls a model. The rules they serve are those of the original's
``version_comparison_ai/sheet_match.py`` at commit ``23f379fd`` (every constant names its line below).

A **question** is one doubtful cell of the effective matrix: sheet A of an older version against the cell of the next version.

* ``no_pair`` (the original's ``review``, ``sheet_match.py:151-158``): A has a sheet there and the cell of B is ``unmatched`` with
  candidates («⁇»); the model is asked which candidate, if any, is the same sheet;
* ``medium_pair`` (``medium``, ``sheet_match.py:159-165``): the algorithm paired A with a B page at ``medium`` confidence; the
  model is asked whether that page, or a neighbour of it, is the same sheet.

The answer to the *reverse* question (``reverse_check``, ``sheet_match.py:318-324``) is asked from the sheet B chose back to A's
version. It is a third kind of stored answer.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Final

__all__ = [
    "ANSWER_CONFIDENCES",
    "ANSWER_KINDS",
    "ANSWER_REASON_MAX",
    "CONFLICT_MATRIX_STALE",
    "DECISIONS",
    "DECISION_ANSWER_MISMATCH",
    "DECISION_FAILED",
    "DECISION_HINT_CONFIDENCE",
    "DECISION_HINT_REVERSE",
    "DECISION_HINT_SHARED",
    "DECISION_HINT_TABLE",
    "DECISION_HINT_TAKEN",
    "DECISION_LINK_ACCEPTED",
    "DECISION_MEDIUM_CONFIRM",
    "DECISION_MEDIUM_NONE",
    "DECISION_MEDIUM_OTHER",
    "DECISION_MEDIUM_WEAK",
    "DECISION_NONE",
    "HINT_DECISIONS",
    "KIND_MEDIUM_PAIR",
    "KIND_NO_PAIR",
    "KIND_REVERSE",
    "MAX_CANDIDATES_NO_PAIR",
    "MAX_OUTPUT_TOKENS",
    "MAX_REVERSE_CANDIDATES",
    "PAIR_CHECK_KIND",
    "PROMPT_VERSION",
    "QUESTION_STATES",
    "Answer",
    "PageFacts",
    "Question",
    "QuestionPage",
]

#: The work kind of the method (`ADR-0025` decision 17); one handler serves the question items and the closing item.
PAIR_CHECK_KIND: Final[str] = "comparison_pair_check"

#: The version of the prompt, the schema and the way the images are named. A new prompt is a new estimate (the core puts it in
#: the digest) and a new content key (an answer to the old prompt is not an answer to the new one). The original's own
#: version is ``vcsm-p3`` (``settings.py:259``); this port changes the images (no caption band, see the report) and the
#: schema's strictness, so it has a version of its own.
PROMPT_VERSION: Final[str] = "cmp-pair-p1"

KIND_NO_PAIR: Final[str] = "no_pair"
KIND_MEDIUM_PAIR: Final[str] = "medium_pair"
KIND_REVERSE: Final[str] = "reverse_check"
#: The kinds of a stored answer (the CHECK of ``comparison_ai_pair_answer``).
ANSWER_KINDS: Final[tuple[str, ...]] = (KIND_NO_PAIR, KIND_MEDIUM_PAIR, KIND_REVERSE)

#: A ``no_pair`` question offers at most four candidates (``sheet_match.py:154`` ``[:4]``), a reverse question at most the
#: three candidates of B's own cell plus sheet A (``sheet_match.py:320`` ``[:3]``): with the sheet itself at most five images, far
#: below the executors' eight (ADR-0025 decision 18, ``A-12``).
MAX_CANDIDATES_NO_PAIR: Final[int] = 4
MAX_REVERSE_CANDIDATES: Final[int] = 3

#: ``max_tokens`` of one request. ``[own design]``: the answer is a four-member JSON object whose longest member is 300
#: characters, and adaptive thinking is on, so the ceiling is a few times the answer; the estimate prices every call at it.
MAX_OUTPUT_TOKENS: Final[int] = 1_200
ANSWER_REASON_MAX: Final[int] = 300
ANSWER_CONFIDENCES: Final[tuple[str, ...]] = ("high", "medium", "low")

QUESTION_STATES: Final[tuple[str, ...]] = ("queued", "answered", "failed", "cancelled")

DECISION_LINK_ACCEPTED: Final[str] = "link_accepted"
DECISION_HINT_TABLE: Final[str] = "hint_table"
DECISION_HINT_CONFIDENCE: Final[str] = "hint_confidence"
DECISION_HINT_TAKEN: Final[str] = "hint_taken"
DECISION_HINT_SHARED: Final[str] = "hint_shared"
DECISION_HINT_REVERSE: Final[str] = "hint_reverse"
DECISION_NONE: Final[str] = "none"
DECISION_ANSWER_MISMATCH: Final[str] = "answer_mismatch"
DECISION_FAILED: Final[str] = "failed"
DECISION_MEDIUM_CONFIRM: Final[str] = "medium_confirm"
DECISION_MEDIUM_WEAK: Final[str] = "medium_weak"
DECISION_MEDIUM_OTHER: Final[str] = "medium_other"
DECISION_MEDIUM_NONE: Final[str] = "medium_none"
#: The CHECK of ``comparison_ai_pair_question.decision`` (the original's ``DECISIONS``, ``sheet_match.py:51-65``;
#: ``accepted`` is ``link_accepted`` and ``hint_double`` is ``hint_shared`` here).
DECISIONS: Final[tuple[str, ...]] = (
    DECISION_LINK_ACCEPTED, DECISION_HINT_TABLE, DECISION_HINT_CONFIDENCE, DECISION_HINT_TAKEN, DECISION_HINT_SHARED,
    DECISION_HINT_REVERSE, DECISION_NONE, DECISION_ANSWER_MISMATCH, DECISION_FAILED, DECISION_MEDIUM_CONFIRM,
    DECISION_MEDIUM_WEAK, DECISION_MEDIUM_OTHER, DECISION_MEDIUM_NONE,
)
#: What the screen shows as «ИИ ?» or «🌙 ИИ: вероятно стр. N» -- a model's page that changed nothing.
HINT_DECISIONS: Final[frozenset[str]] = frozenset({
    DECISION_HINT_TABLE, DECISION_HINT_CONFIDENCE, DECISION_HINT_TAKEN, DECISION_HINT_SHARED, DECISION_HINT_REVERSE,
    DECISION_MEDIUM_WEAK, DECISION_MEDIUM_OTHER,
})

#: The registered ``409 conflict`` reason of a matrix that is not ``ready`` (`CMP-SEAL-C1`, also on ``estimate``).
CONFLICT_MATRIX_STALE: Final[str] = "comparison_matrix_stale"


@dataclass(frozen=True, slots=True)
class PageFacts:
    """What the question needs to know of one page, read from its stored profile summary (never from the archive): the stamp's
    sheet number, title and designation, the content key and the stored preview. The words of the page are not read here
    (see the report: the original's header rule for a specification sheet needs them)."""

    page_profile_id: str
    version_uid: str
    page_number: int
    content_key: str
    sheet_number: str = ""
    title: str = ""
    designation: str = ""
    preview_blob_id: str | None = None
    preview_sha256: str | None = None
    preview_size: int = 0


@dataclass(frozen=True, slots=True)
class QuestionPage:
    """A page named by a question: the version, the number inside it and its profile identity."""

    version_uid: str
    page_number: int
    page_profile_id: str

    def wire(self) -> dict[str, Any]:
        return {"version_uid": self.version_uid, "page_number": self.page_number, "page_profile_id": self.page_profile_id}


@dataclass(frozen=True, slots=True)
class Question:
    """One doubtful cell. ``candidates`` are pages of the B version in the order they are shown (``no_pair``: up to four,
    sorted by number; ``medium_pair``: the algorithm's page and its neighbours that are not specification sheets);
    ``algo_b`` is the algorithm's page of a ``medium_pair`` question. ``multi`` says sheet A is inside a multi-sheet
    specification; ``taken_b`` are the candidates already paired with an A sheet; ``back`` maps a candidate to the pages of
    version A that B's own cell offers (the reverse question's candidates)."""

    kind: str
    a: QuestionPage
    b_version_uid: str
    candidates: tuple[QuestionPage, ...]
    algo_b: int | None = None
    multi: bool = False
    taken_b: frozenset[int] = frozenset()
    back: Mapping[int, tuple[int, ...]] = field(default_factory=dict)

    @property
    def key(self) -> tuple[str, int, str]:
        """The cell the question is about (the table's unique key without the job): sheet A and the version of B."""
        return (self.a.version_uid, self.a.page_number, self.b_version_uid)

    def payload(self) -> dict[str, Any]:
        """The part of the question a work item carries: what the ask phase needs and nothing a client could rewrite."""
        return {
            "kind": self.kind,
            "a": self.a.wire(),
            "b_version_uid": self.b_version_uid,
            "candidates": [page.wire() for page in self.candidates],
            "algo_b": self.algo_b,
            "multi": self.multi,
            "taken_b": sorted(self.taken_b),
            "back": {str(page): list(pages) for page, pages in sorted(self.back.items())},
        }

    @classmethod
    def from_payload(cls, document: Mapping[str, Any]) -> "Question":
        def page(raw: Mapping[str, Any]) -> QuestionPage:
            return QuestionPage(str(raw["version_uid"]), int(raw["page_number"]), str(raw["page_profile_id"]))

        return cls(
            kind=str(document["kind"]), a=page(document["a"]), b_version_uid=str(document["b_version_uid"]),
            candidates=tuple(page(item) for item in document["candidates"]),
            algo_b=None if document.get("algo_b") is None else int(document["algo_b"]),
            multi=bool(document.get("multi", False)), taken_b=frozenset(int(n) for n in document.get("taken_b", ())),
            back={int(k): tuple(int(n) for n in v) for k, v in (document.get("back") or {}).items()},
        )


@dataclass(frozen=True, slots=True)
class Answer:
    """A validated answer of the model and the candidate pages it chose among (``cands`` in the order they were shown).
    ``ok`` is false for an answer that could not be used (the call failed, the reply was not the schema)."""

    ok: bool
    choice: int = 0
    page: int = 0
    confidence: str = "low"
    reason: str = ""
    cands: tuple[int, ...] = ()
