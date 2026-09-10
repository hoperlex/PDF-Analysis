"""Read-only views over the three stage artifacts the grounding gate resolves against.

The gate takes ``prepared.text_layer`` (§4.3), ``geometry.block_index`` (§4.4) and
``analysis.text_observations`` (§4.7) and nothing else. It reads no PDF, calls no model
and opens no blob: ``B2`` owns extraction and ``B3`` owns analysis, and a gate that
re-extracted would be judging its own work.

Two rules are load-bearing here and are worth stating where the code lives.

**Offsets are Unicode code points into one document-global sequence** (§4.1). The pages
are concatenated in ascending page order with no separator between them, and
``sequence[char_start:char_end]`` on that string is the definition of an anchor. The
corpus is Russian, where one code point is commonly two UTF-8 bytes, so a byte offset
misplaces every anchor while still looking plausible in an English test. There is no
``.encode()`` anywhere in this package.

**Normalization happens once, upstream.** ``source_preparation`` applied the single
declared normalization and recorded its identifier in ``text_layer.normalization.id``.
This package records that identifier and applies nothing: the gate compares exactly, so
a second normalization here would let a quotation that is *not* in the document pass by
being rewritten until it was.

A malformed artifact is refused with ``analysis_input_invalid`` rather than repaired. A
gate that repairs its input has no idea what it is measuring.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final, Iterator, Mapping, Sequence

from auditmanager.shared.errors import DomainError, ErrorCode

TEXT_LAYER_ROLE: Final[str] = "prepared.text_layer"
BLOCK_INDEX_ROLE: Final[str] = "geometry.block_index"
OBSERVATIONS_ROLE: Final[str] = "analysis.text_observations"


def _invalid(detail: str) -> DomainError:
    return DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, message=detail)


def _require(
    payload: Mapping[str, Any], key: str, kind: type | tuple[type, ...], where: str
) -> Any:
    if key not in payload:
        raise _invalid(f"{where} is missing the required key {key!r}")
    value = payload[key]
    if kind is int and isinstance(value, bool):
        # bool is a subclass of int; a boolean offset is a type error, not an offset.
        raise _invalid(f"{where}.{key} is a boolean where an integer was declared")
    if not isinstance(value, kind):
        raise _invalid(f"{where}.{key} has the wrong type")
    return value


def _require_role(payload: Mapping[str, Any], expected: str) -> None:
    role = payload.get("artifact_role")
    if role != expected:
        raise _invalid(f"expected artifact_role {expected!r}, got {role!r}")


@dataclass(frozen=True, slots=True)
class Page:
    """One page's half-open interval in the document-global sequence."""

    page_number: int
    char_start: int
    char_end: int

    def contains(self, char_start: int, char_end: int) -> bool:
        """Is the half-open interval ``[char_start, char_end)`` inside this page?

        A span that begins on this page and runs past its end is **not** contained.
        That is the page-boundary case: an anchor crossing from one page into the next
        names a stretch of text no single page owns.
        """
        return self.char_start <= char_start and char_end <= self.char_end


@dataclass(frozen=True, slots=True)
class Block:
    """One block's half-open interval, from ``geometry.block_index``."""

    block_id: str
    page_number: int
    char_start: int
    char_end: int

    def contains(self, char_start: int, char_end: int) -> bool:
        return self.char_start <= char_start and char_end <= self.char_end


class TextLayer:
    """The document-global character sequence and its page intervals.

    Construction validates exactly the invariants §4.3 says a consumer may rely on, so
    an upstream mistake surfaces here rather than as a silently misplaced anchor: pages
    ascending, contiguous and gapless, starting at zero, each interval the length of its
    own text, and the last interval ending at ``total_char_count``.
    """

    __slots__ = ("_pages", "_by_number", "_sequence", "_normalization_id", "_version_uid")

    def __init__(
        self,
        *,
        pages: Sequence[Page],
        sequence: str,
        normalization_id: str,
        version_uid: str | None = None,
    ) -> None:
        self._pages: tuple[Page, ...] = tuple(pages)
        self._by_number: Mapping[int, Page] = {page.page_number: page for page in self._pages}
        self._sequence = sequence
        self._normalization_id = normalization_id
        self._version_uid = version_uid

    @classmethod
    def from_artifact(cls, payload: Mapping[str, Any]) -> "TextLayer":
        _require_role(payload, TEXT_LAYER_ROLE)
        normalization = _require(payload, "normalization", Mapping, TEXT_LAYER_ROLE)
        normalization_id = normalization.get("id")
        if not isinstance(normalization_id, str) or not normalization_id:
            raise _invalid(
                "prepared.text_layer declares no normalization.id. The gate compares "
                "against the one declared normalization and nothing else, so an "
                "artifact that does not name it cannot be judged."
            )
        total = _require(payload, "total_char_count", int, TEXT_LAYER_ROLE)
        raw_pages = _require(payload, "pages", Sequence, TEXT_LAYER_ROLE)
        if not raw_pages:
            raise _invalid("prepared.text_layer carries no pages")

        pages: list[Page] = []
        chunks: list[str] = []
        expected_start = 0
        previous_number: int | None = None
        for position, entry in enumerate(raw_pages):
            if not isinstance(entry, Mapping):
                raise _invalid(f"prepared.text_layer.pages[{position}] is not an object")
            where = f"prepared.text_layer.pages[{position}]"
            number = _require(entry, "page_number", int, where)
            start = _require(entry, "char_start", int, where)
            end = _require(entry, "char_end", int, where)
            text = _require(entry, "text", str, where)
            if previous_number is not None and number <= previous_number:
                raise _invalid(
                    f"{where} is not ascending by page_number "
                    f"({number} follows {previous_number})"
                )
            if start != expected_start:
                raise _invalid(
                    f"{where} starts at {start}, breaking the contiguous, gapless "
                    f"sequence that should start at {expected_start}"
                )
            if end - start != len(text):
                raise _invalid(
                    f"{where} declares {end - start} characters and carries {len(text)}. "
                    "Offsets are code points, not bytes."
                )
            pages.append(Page(page_number=number, char_start=start, char_end=end))
            chunks.append(text)
            previous_number = number
            expected_start = end

        if expected_start != total:
            raise _invalid(
                f"prepared.text_layer.total_char_count is {total} but the pages end at "
                f"{expected_start}"
            )
        # No separator between pages: §4.1 defines the document-global sequence as the
        # bare concatenation, and a joiner inserted here would shift every later anchor.
        return cls(
            pages=pages,
            sequence="".join(chunks),
            normalization_id=normalization_id,
            version_uid=payload.get("version_uid"),
        )

    @property
    def sequence(self) -> str:
        """The one document-global character sequence. Indexed in code points."""
        return self._sequence

    @property
    def normalization_id(self) -> str:
        return self._normalization_id

    @property
    def version_uid(self) -> str | None:
        return self._version_uid

    @property
    def total_char_count(self) -> int:
        return len(self._sequence)

    @property
    def pages(self) -> tuple[Page, ...]:
        return self._pages

    def page(self, page_number: int) -> Page | None:
        return self._by_number.get(page_number)

    def slice(self, char_start: int, char_end: int) -> str:
        """The declared interval, sliced from the document-global sequence."""
        return self._sequence[char_start:char_end]

    def pages_containing(self, quote: str) -> tuple[int, ...]:
        """Every page whose own interval wholly contains an occurrence of ``quote``.

        Used only to tell ``quotation_absent`` from ``quotation_on_different_page``.
        An occurrence straddling two pages belongs to neither and is not reported.
        """
        if not quote:
            return ()
        found: list[int] = []
        for page in self._pages:
            window = self._sequence[page.char_start : page.char_end]
            if quote in window:
                found.append(page.page_number)
        return tuple(found)


class BlockIndex:
    """The block spans a secondary anchor is checked against.

    ``block_id`` is an anchor inside one artifact and never a contract identifier
    (§4.4), so nothing here treats it as a foreign key.
    """

    __slots__ = ("_blocks", "_by_id")

    def __init__(self, blocks: Sequence[Block]) -> None:
        self._blocks: tuple[Block, ...] = tuple(blocks)
        self._by_id: Mapping[str, Block] = {block.block_id: block for block in self._blocks}

    @classmethod
    def from_artifact(cls, payload: Mapping[str, Any]) -> "BlockIndex":
        _require_role(payload, BLOCK_INDEX_ROLE)
        raw_blocks = _require(payload, "blocks", Sequence, BLOCK_INDEX_ROLE)
        blocks: list[Block] = []
        for position, entry in enumerate(raw_blocks):
            if not isinstance(entry, Mapping):
                raise _invalid(f"geometry.block_index.blocks[{position}] is not an object")
            where = f"geometry.block_index.blocks[{position}]"
            blocks.append(
                Block(
                    block_id=_require(entry, "block_id", str, where),
                    page_number=_require(entry, "page_number", int, where),
                    char_start=_require(entry, "char_start", int, where),
                    char_end=_require(entry, "char_end", int, where),
                )
            )
        return cls(blocks)

    @classmethod
    def empty(cls) -> "BlockIndex":
        return cls(())

    def block(self, block_id: str) -> Block | None:
        return self._by_id.get(block_id)

    def __len__(self) -> int:
        return len(self._blocks)

    def __iter__(self) -> Iterator[Block]:
        return iter(self._blocks)


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    """One declared anchor, exactly as ``B3`` wrote it. Never rewritten here."""

    evidence_ordinal: int
    page_number: int
    quote: str
    char_start: int
    char_end: int
    block_id: str | None = None


@dataclass(frozen=True, slots=True)
class Observation:
    """One model observation. Not yet a finding, and possibly never one."""

    observation_ordinal: int
    category: str
    finding_text: str
    recommendation_text: str
    evidence: tuple[EvidenceItem, ...]
    model_call_id: str | None = None


@dataclass(frozen=True, slots=True)
class ObservationSet:
    """``analysis.text_observations`` — the gate's only input from the model side."""

    run_id: str
    stage_id: str
    analysis_profile_id: str
    prompt_bundle_id: str
    provider_mode: str
    pages_analysed: tuple[int, ...]
    observations: tuple[Observation, ...]

    @classmethod
    def from_artifact(cls, payload: Mapping[str, Any]) -> "ObservationSet":
        _require_role(payload, OBSERVATIONS_ROLE)
        raw_observations = _require(payload, "observations", Sequence, OBSERVATIONS_ROLE)
        observations: list[Observation] = []
        for position, entry in enumerate(raw_observations):
            if not isinstance(entry, Mapping):
                raise _invalid(
                    f"analysis.text_observations.observations[{position}] is not an object"
                )
            where = f"observations[{position}]"
            raw_evidence = _require(entry, "evidence", Sequence, where)
            if not raw_evidence:
                # §4.7: an observation with no evidence is not "ungrounded", it is
                # malformed. text_analysis rejects it before writing the artifact, so
                # reaching the gate with one is an input fault, not a gate verdict.
                raise _invalid(
                    f"{where} carries no evidence. An observation with no evidence is "
                    "malformed, not ungrounded, and is refused before the gate runs."
                )
            evidence: list[EvidenceItem] = []
            for index, item in enumerate(raw_evidence):
                if not isinstance(item, Mapping):
                    raise _invalid(f"{where}.evidence[{index}] is not an object")
                block_id = item.get("block_id")
                if block_id is not None and not isinstance(block_id, str):
                    raise _invalid(f"{where}.evidence[{index}].block_id is not a string")
                evidence.append(
                    EvidenceItem(
                        evidence_ordinal=_require(
                            item, "evidence_ordinal", int, f"{where}.evidence[{index}]"
                        ),
                        page_number=_require(
                            item, "page_number", int, f"{where}.evidence[{index}]"
                        ),
                        quote=_require(item, "quote", str, f"{where}.evidence[{index}]"),
                        char_start=_require(
                            item, "char_start", int, f"{where}.evidence[{index}]"
                        ),
                        char_end=_require(item, "char_end", int, f"{where}.evidence[{index}]"),
                        block_id=block_id,
                    )
                )
            observations.append(
                Observation(
                    observation_ordinal=_require(entry, "observation_ordinal", int, where),
                    category=_require(entry, "category", str, where),
                    finding_text=_require(entry, "finding_text", str, where),
                    recommendation_text=_require(entry, "recommendation_text", str, where),
                    evidence=tuple(evidence),
                    model_call_id=entry.get("model_call_id"),
                )
            )
        raw_pages = payload.get("pages_analysed") or ()
        return cls(
            run_id=_require(payload, "run_id", str, OBSERVATIONS_ROLE),
            stage_id=_require(payload, "stage_id", str, OBSERVATIONS_ROLE),
            analysis_profile_id=_require(
                payload, "analysis_profile_id", str, OBSERVATIONS_ROLE
            ),
            prompt_bundle_id=_require(payload, "prompt_bundle_id", str, OBSERVATIONS_ROLE),
            provider_mode=_require(payload, "provider_mode", str, OBSERVATIONS_ROLE),
            pages_analysed=tuple(int(page) for page in raw_pages),
            observations=tuple(observations),
        )
