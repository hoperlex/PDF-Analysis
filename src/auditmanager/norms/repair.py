"""The re-recognition result, as data the segmenter can consume — and what it does to `R-17`.

`R-19` repairs `D-59` at the source. It does **not** follow that the source files are
rewritten: `.local/` is a read-only drop, it is invisible to git, and a corpus that is
mutated in place cannot be compared with the one every earlier figure was taken against. So
the repair is a **ledger**, keyed by `(document_slug, block_id)`, that a segmentation run
consults before it reads a block's body.

Three things follow from that shape, and the third is the one that matters.

**1. A repair is addressed to a block, not to a page and not to a file.** `AGENTS.md` §4
forbids a path or a filename as identity, and a page label is not unique either — `results.md`
prints no heading for a page with no block, and two blocks can share a page. `block_id` is the
`blk_<32 hex>` the pipeline minted, it is what the crop is named after, and it is what
`Paragraph.block_id` already carries.

**2. A replacement that is still degenerate is never applied.** It is recorded, with its
signals, and the original stands. `AGENTS.md` §4 forbids a silent fallback, and quietly
swapping one unusable page for another unusable page is exactly that — it would look like a
repair in every count while changing nothing a reader can use. `R-20`'s *nothing is cut* is
the same instinct one step earlier.

**3. A repair moves the corpus-snapshot identifier, and `R-17`'s identifier as built does not
notice.** :func:`repaired_snapshot` is the answer and the argument for it is this:

    `CorpusSnapshot.content_digest` is SHA-256 over `(slug, source document id,
    sha256(results.md))` for every document. A repair does not touch `results.md`, so the
    base digest is **unchanged by construction** — and the text that gets segmented,
    chunked, embedded and cited is no longer the text that digest names.

    That is precisely the failure `R-17`'s recorded consequence exists to prevent, read the
    other way round. The ruling's case was *"a refresh silently reissues a ГОСТ and verdicts
    taken against the old text claim to have been taken against the new"*. A repair is the
    same divergence with our own hand on it: two chunk sets, one identifier, and nothing on a
    verdict row able to say which text an expert actually read.

    So the identifier must move — and it must move **visibly**, not merely differ. The window
    is unchanged, because a repair changes nothing about *when* the corpus was drawn; the
    undated count is unchanged for the same reason; the digest folds in every applied
    replacement, and a new `+<n>r` term says how many pages were repaired. A reader who sees
    `+79r` asks which 79, exactly as `R-17`'s `+17d` was meant to make them ask which
    seventeen.

    `2026-07-23..2026-08-20+17d.4b74348debf7` → `2026-07-23..2026-08-20+17d+79r.<digest12>`

    **A ledger that applied nothing returns the base snapshot unchanged**, object for object.
    An empty repair pass is not a new corpus and must not be presented as one.

Structure, then compute, then write the value: the applied repairs are sorted into a
canonical order before a byte is hashed, for the same reason `snapshot.derive` sorts — the
corpus has no commit name to identify a draw by, and a ledger written by a partially-completed
run has no guaranteed order either.
"""

from __future__ import annotations

import enum
import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from .degeneracy import DegeneracySignal
from .snapshot import DIGEST_CHARACTERS, CorpusSnapshot

#: The ledger's own format version. A consumer that reads a ledger it does not understand
#: must refuse rather than guess: the values in it decide which text an expert is shown.
LEDGER_VERSION: str = "1"


class RepairOutcome(enum.Enum):
    """What happened to one page. Four values, and none of them is a bare boolean.

    ``STILL_DEGENERATE`` is a **result**, not an error. `R-19`'s scope was set by a
    measurement of the defect; a page that comes back degenerate twice says the corpus holds
    a page no pipeline can read, and that is a count the owner asked for rather than a
    failure to report.
    """

    REPAIRED = "repaired"
    STILL_DEGENERATE = "still_degenerate"
    UNUSABLE = "unusable"
    NOT_ATTEMPTED = "not_attempted"


@dataclass(frozen=True, slots=True)
class RepairAttempt:
    """One call to the recogniser, priced and dated.

    ``cost_usd`` is what the **transport reported**, or ``None`` where it reported nothing.
    It is never an estimate dressed as a measurement: `cost.py` already draws that line for
    the analysis stage (``BASIS_MEASURED`` against ``BASIS_ESTIMATED``) and a wave that has
    to answer *"what did you spend"* cannot have the two collapse.
    """

    ordinal: int
    recognised_at: str
    model: str
    stop_reason: str
    input_tokens: int
    output_tokens: int
    cost_usd: float | None
    characters: int
    text_sha256: str
    signals: tuple[DegeneracySignal, ...]
    evidence: tuple[str, ...]

    @property
    def was_clean(self) -> bool:
        return not self.signals

    def as_document(self) -> dict[str, Any]:
        return {
            "ordinal": self.ordinal,
            "recognised_at": self.recognised_at,
            "model": self.model,
            "stop_reason": self.stop_reason,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": self.cost_usd,
            "characters": self.characters,
            "text_sha256": self.text_sha256,
            "signals": [signal.value for signal in self.signals],
            "evidence": list(self.evidence),
        }

    @classmethod
    def from_document(cls, document: Mapping[str, Any]) -> RepairAttempt:
        return cls(
            ordinal=int(document["ordinal"]),
            recognised_at=str(document["recognised_at"]),
            model=str(document["model"]),
            stop_reason=str(document["stop_reason"]),
            input_tokens=int(document["input_tokens"]),
            output_tokens=int(document["output_tokens"]),
            cost_usd=None if document.get("cost_usd") is None else float(document["cost_usd"]),
            characters=int(document["characters"]),
            text_sha256=str(document["text_sha256"]),
            signals=tuple(DegeneracySignal(value) for value in document.get("signals", ())),
            evidence=tuple(str(value) for value in document.get("evidence", ())),
        )


@dataclass(frozen=True, slots=True)
class PageRepair:
    """One block's repair: what was there, what came back, and whether it is applied.

    ``replacement`` is non-``None`` **only** when :attr:`outcome` is ``REPAIRED``. That is
    the invariant the whole ledger rests on, and :meth:`__post_init__` refuses any other
    combination rather than letting a consumer discover it at read time.
    """

    document_slug: str
    block_id: str
    page_label: int
    original_sha256: str
    original_characters: int
    crop_sha256: str
    outcome: RepairOutcome
    replacement: str | None
    attempts: tuple[RepairAttempt, ...]

    def __post_init__(self) -> None:
        applied = self.outcome is RepairOutcome.REPAIRED
        if applied and not self.replacement:
            raise ValueError(
                f"{self.document_slug}/{self.block_id}: a repaired page carries no replacement text"
            )
        if not applied and self.replacement is not None:
            raise ValueError(
                f"{self.document_slug}/{self.block_id}: a page that was not repaired carries a "
                f"replacement; an unapplied replacement must not be reachable as one"
            )

    @property
    def key(self) -> tuple[str, str]:
        return (self.document_slug, self.block_id)

    @property
    def replacement_sha256(self) -> str | None:
        if self.replacement is None:
            return None
        return hashlib.sha256(self.replacement.encode("utf-8")).hexdigest()

    @property
    def replacement_characters(self) -> int:
        return 0 if self.replacement is None else len(self.replacement)

    @property
    def cost_usd(self) -> float:
        """What this page cost, over every attempt. Unpriced attempts contribute nothing."""
        return sum(a.cost_usd for a in self.attempts if a.cost_usd is not None)

    @property
    def unpriced_attempts(self) -> int:
        """Attempts the transport did not price — so a zero cost cannot be read as free."""
        return sum(1 for a in self.attempts if a.cost_usd is None)

    def as_document(self) -> dict[str, Any]:
        return {
            "document_slug": self.document_slug,
            "block_id": self.block_id,
            "page_label": self.page_label,
            "original_sha256": self.original_sha256,
            "original_characters": self.original_characters,
            "crop_sha256": self.crop_sha256,
            "outcome": self.outcome.value,
            "replacement": self.replacement,
            "replacement_sha256": self.replacement_sha256,
            "attempts": [attempt.as_document() for attempt in self.attempts],
        }

    @classmethod
    def from_document(cls, document: Mapping[str, Any]) -> PageRepair:
        return cls(
            document_slug=str(document["document_slug"]),
            block_id=str(document["block_id"]),
            page_label=int(document["page_label"]),
            original_sha256=str(document["original_sha256"]),
            original_characters=int(document["original_characters"]),
            crop_sha256=str(document["crop_sha256"]),
            outcome=RepairOutcome(document["outcome"]),
            replacement=document.get("replacement"),
            attempts=tuple(
                RepairAttempt.from_document(a) for a in document.get("attempts", ())
            ),
        )


@dataclass(frozen=True, slots=True)
class RepairLedger:
    """Every repair taken against one corpus snapshot.

    The base snapshot identifier is carried because a ledger is only meaningful against the
    corpus it was taken from. Replaying a ledger against a re-drawn corpus would silently
    apply a page's old transcription to a document that has since changed, and the identifier
    is what lets a consumer refuse instead.
    """

    base_snapshot_id: str
    generated_at: str
    repairs: tuple[PageRepair, ...]
    version: str = LEDGER_VERSION

    def __post_init__(self) -> None:
        seen: set[tuple[str, str]] = set()
        for repair in self.repairs:
            if repair.key in seen:
                raise ValueError(
                    f"{repair.document_slug}/{repair.block_id}: two repairs for one block; "
                    f"a ledger with a duplicate key cannot say which text is current"
                )
            seen.add(repair.key)

    @property
    def applied(self) -> tuple[PageRepair, ...]:
        return tuple(r for r in self.repairs if r.outcome is RepairOutcome.REPAIRED)

    @property
    def still_degenerate(self) -> tuple[PageRepair, ...]:
        return tuple(r for r in self.repairs if r.outcome is RepairOutcome.STILL_DEGENERATE)

    @property
    def unusable(self) -> tuple[PageRepair, ...]:
        return tuple(r for r in self.repairs if r.outcome is RepairOutcome.UNUSABLE)

    @property
    def total_cost_usd(self) -> float:
        return sum(repair.cost_usd for repair in self.repairs)

    @property
    def unpriced_attempts(self) -> int:
        return sum(repair.unpriced_attempts for repair in self.repairs)

    def replacement_for(self, document_slug: str, block_id: str) -> str | None:
        """The applied replacement for one block, or ``None``.

        ``None`` means *"use what the corpus says"* and covers three different cases — no
        repair was attempted, a repair was attempted and came back degenerate, and a repair
        came back unusable. A caller that needs to tell them apart reads :attr:`repairs`; a
        segmenter does not, because in all three the corpus text is what stands.
        """
        for repair in self.repairs:
            if repair.document_slug == document_slug and repair.block_id == block_id:
                return repair.replacement
        return None

    def as_document(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "base_snapshot_id": self.base_snapshot_id,
            "generated_at": self.generated_at,
            "repairs": [
                repair.as_document()
                for repair in sorted(self.repairs, key=lambda r: (r.document_slug, r.block_id))
            ],
        }

    def as_json(self) -> str:
        return json.dumps(self.as_document(), ensure_ascii=False, indent=1, sort_keys=True) + "\n"

    @classmethod
    def from_document(cls, document: Mapping[str, Any]) -> RepairLedger:
        version = str(document.get("version", ""))
        if version != LEDGER_VERSION:
            raise ValueError(
                f"repair ledger version {version!r} is not {LEDGER_VERSION!r}; refusing to "
                f"guess at a format that decides which text an expert is shown"
            )
        return cls(
            base_snapshot_id=str(document["base_snapshot_id"]),
            generated_at=str(document["generated_at"]),
            repairs=tuple(PageRepair.from_document(r) for r in document.get("repairs", ())),
            version=version,
        )


def repaired_snapshot(base: CorpusSnapshot, ledger: RepairLedger) -> CorpusSnapshot:
    """The identifier of the corpus **as it will be read** once the ledger is applied.

    See this module's header for the argument. In one line: the base digest is over
    `results.md` bytes, a repair changes what is segmented without changing those bytes, and
    an identifier that cannot tell the two texts apart is the `R-17` failure with our own
    hand on it.

    The dates do not move. A repair says nothing about when the corpus was drawn, and a
    window that drifted because we re-read a page would be a false statement about the draw.
    """
    if ledger.base_snapshot_id != base.snapshot_id:
        raise ValueError(
            f"ledger was taken against {ledger.base_snapshot_id!r} and this snapshot is "
            f"{base.snapshot_id!r}; applying it would attribute one corpus's repairs to another"
        )
    applied = sorted(ledger.applied, key=lambda r: (r.document_slug, r.block_id))
    if not applied:
        # Nothing was replaced, so nothing downstream reads different bytes. An empty pass is
        # not a new corpus and giving it a new identifier would make the identifier a record
        # of effort rather than of content.
        return base

    digest = hashlib.sha256()
    digest.update(base.content_digest.encode("ascii"))
    digest.update(b"\n")
    for repair in applied:
        digest.update(repair.document_slug.encode("utf-8"))
        digest.update(b"\x00")
        digest.update(repair.block_id.encode("utf-8"))
        digest.update(b"\x00")
        digest.update(str(repair.replacement_sha256).encode("ascii"))
        digest.update(b"\n")
    content_digest = digest.hexdigest()

    window = (
        f"{base.drawn_from}..{base.drawn_to}" if base.drawn_from is not None else "undated"
    )
    snapshot_id = (
        f"{window}+{base.undated_documents}d+{len(applied)}r."
        f"{content_digest[:DIGEST_CHARACTERS]}"
    )
    return CorpusSnapshot(
        snapshot_id=snapshot_id,
        drawn_from=base.drawn_from,
        drawn_to=base.drawn_to,
        undated_documents=base.undated_documents,
        document_count=base.document_count,
        content_digest=content_digest,
    )


def ledger_of(
    base_snapshot_id: str, generated_at: str, repairs: Iterable[PageRepair]
) -> RepairLedger:
    """Build a ledger, sorted. A convenience with the ordering rule already applied."""
    return RepairLedger(
        base_snapshot_id=base_snapshot_id,
        generated_at=generated_at,
        repairs=tuple(sorted(repairs, key=lambda r: (r.document_slug, r.block_id))),
    )
