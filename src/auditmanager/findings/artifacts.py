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

The views of the second half of this module (``PortalBlockGeometry``, ``CropManifest``,
``RecognisedText``, bundled as ``BlockGateInputs``) are read only for a run whose
``publication_mode`` is ``one_list`` (`F8-GATE`, ADR-0029 decision 7). They are the three
artifacts of **that run** a block as evidence is judged against; a run in ``text_only`` mode
never builds them.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Final, Iterator, Mapping, Sequence

from auditmanager.shared.errors import DomainError, ErrorCode

TEXT_LAYER_ROLE: Final[str] = "prepared.text_layer"
BLOCK_INDEX_ROLE: Final[str] = "geometry.block_index"
OBSERVATIONS_ROLE: Final[str] = "analysis.text_observations"
#: The three artifacts of a run's geometry and recognised text that a block as evidence is judged against.
PORTAL_BLOCKS_ROLE: Final[str] = "geometry.portal_blocks"
PAGE_CROPS_ROLE: Final[str] = "geometry.page_crops"
RECOGNISED_TEXT_ROLE: Final[str] = "prepared.recognised_text"
#: The ``kind`` of a ``prepared.recognised_text`` entry that is the portal's recognised TEXT of a block. The other kind,
#: ``portal_description``, is a machine description of an IMAGE block, "never an input of any analysis stage" (`R-117`,
#: ``P02_SEAMS`` section 4.8): a quote found only there is not recognised text.
RECOGNISED_TEXT_KIND: Final[str] = "recognised_text"

#: How an observation is grounded: the vocabulary of ``finding_observation.grounding_kind`` (``ck_finding_observation_grounding_kind``).
GROUNDING_TEXT_SPAN: Final[str] = "text_span"
GROUNDING_PORTAL_BLOCK: Final[str] = "portal_block"
#: ``ck_finding_block_evidence_recognised_quote``: a quote the store cannot keep is not admitted as evidence.
MAX_BLOCK_QUOTE_CHARS: Final[int] = 2000
#: ``ck_finding_observation_extended_observation_ref``.
MAX_EXTENDED_OBSERVATION_REF_CHARS: Final[int] = 128

_SHA256: Final[re.Pattern[str]] = re.compile(r"[0-9a-f]{64}")


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
    if kind is Sequence and isinstance(value, (str, bytes)):
        # str satisfies Sequence, so a string where a list of pages was declared would
        # otherwise be iterated one character at a time and fail somewhere less useful.
        raise _invalid(f"{where}.{key} is a string where a list was declared")
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

    @property
    def grounding_kind(self) -> str:
        """A text observation is grounded by a span of the text layer (a property, not a field: nothing can set it)."""
        return GROUNDING_TEXT_SPAN


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



# ---------------------------------------------------------------------------------------------
# Block evidence (`F8-GATE`): the run's geometry, crops and recognised text, and what is judged
# ---------------------------------------------------------------------------------------------


def _require_version(payload: Mapping[str, Any], version_uid: str, role: str) -> None:
    """The artifact describes the version this run is about, and no other.

    A ``blk_`` identifier is the portal's, "addressed only together with a ``version_uid``"
    (``P02_SEAMS`` section 4.9), so a document of another version could hold the same identifier
    for another block. Refusing it here is what makes "in this run's geometry" mean this run's.
    """
    if payload.get("version_uid") != version_uid:
        raise _invalid(f"{role} describes another version than the run's own")


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _bbox(value: object, where: str) -> tuple[float, float, float, float]:
    """``[x0, y0, x1, y1]`` in the page's normalised space, as ``ck_finding_block_evidence_bbox`` will want it."""
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes))
        or len(value) != 4
        or not all(_is_number(n) and 0 <= n <= 1 for n in value)
    ):
        raise _invalid(f"{where}.bbox_norm is not four numbers in [0, 1]")
    x0, y0, x1, y1 = (float(n) for n in value)
    if x0 >= x1 or y0 >= y1:
        raise _invalid(f"{where}.bbox_norm is empty or inverted")
    return x0, y0, x1, y1


@dataclass(frozen=True, slots=True)
class PortalBlockPlace:
    """Where one block of this run's geometry stands: its page and its normalised box."""

    portal_block_id: str
    page_number: int
    bbox_norm: tuple[float, float, float, float]


class PortalBlockGeometry:
    """The blocks of ``geometry.portal_blocks`` (``P02_SEAMS`` section 4.9) of one run, by ``portal_block_id``."""

    __slots__ = ("_places",)

    def __init__(self, places: Sequence[PortalBlockPlace]) -> None:
        self._places: Mapping[str, PortalBlockPlace] = {place.portal_block_id: place for place in places}

    @classmethod
    def from_artifact(cls, payload: Mapping[str, Any], *, version_uid: str) -> "PortalBlockGeometry":
        _require_role(payload, PORTAL_BLOCKS_ROLE)
        _require_version(payload, version_uid, PORTAL_BLOCKS_ROLE)
        raw_blocks = _require(payload, "blocks", Sequence, PORTAL_BLOCKS_ROLE)
        places: list[PortalBlockPlace] = []
        for position, entry in enumerate(raw_blocks):
            where = f"{PORTAL_BLOCKS_ROLE}.blocks[{position}]"
            if not isinstance(entry, Mapping):
                raise _invalid(f"{where} is not an object")
            places.append(
                PortalBlockPlace(
                    portal_block_id=_require(entry, "portal_block_id", str, where),
                    page_number=_require(entry, "page_number", int, where),
                    bbox_norm=_bbox(entry.get("bbox_norm"), where),
                )
            )
        if len({place.portal_block_id for place in places}) != len(places):
            raise _invalid(f"{PORTAL_BLOCKS_ROLE} repeats a portal_block_id")
        return cls(places)

    @classmethod
    def empty(cls) -> "PortalBlockGeometry":
        return cls(())

    def place(self, portal_block_id: str) -> PortalBlockPlace | None:
        return self._places.get(portal_block_id)

    def __len__(self) -> int:
        return len(self._places)


class CropManifest:
    """The crops of ``geometry.page_crops`` of one run: the SHA-256 of each block's PNG, by ``portal_block_id``."""

    __slots__ = ("_digests",)

    def __init__(self, digests: Mapping[str, str]) -> None:
        self._digests: Mapping[str, str] = dict(digests)

    @classmethod
    def from_artifact(cls, payload: Mapping[str, Any], *, version_uid: str) -> "CropManifest":
        _require_role(payload, PAGE_CROPS_ROLE)
        _require_version(payload, version_uid, PAGE_CROPS_ROLE)
        raw_crops = _require(payload, "crops", Sequence, PAGE_CROPS_ROLE)
        digests: dict[str, str] = {}
        for position, entry in enumerate(raw_crops):
            where = f"{PAGE_CROPS_ROLE}.crops[{position}]"
            if not isinstance(entry, Mapping):
                raise _invalid(f"{where} is not an object")
            block = _require(entry, "portal_block_id", str, where)
            digest = _require(entry, "sha256", str, where)
            if _SHA256.fullmatch(digest) is None:
                raise _invalid(f"{where}.sha256 is not a lowercase SHA-256 digest")
            if block in digests:
                raise _invalid(f"{PAGE_CROPS_ROLE} holds two crops of one block")
            digests[block] = digest
        return cls(digests)

    @classmethod
    def empty(cls) -> "CropManifest":
        return cls({})

    def sha256(self, portal_block_id: str) -> str | None:
        return self._digests.get(portal_block_id)

    def __len__(self) -> int:
        return len(self._digests)


class RecognisedText:
    """The recognised TEXT of ``prepared.recognised_text`` (``P02_SEAMS`` section 4.8), by ``portal_block_id``.

    Only entries of ``kind: recognised_text`` are kept. The text is held exactly as the artifact has it (markdown,
    kept as text); nothing here normalises it.
    """

    __slots__ = ("_texts",)

    def __init__(self, texts: Mapping[str, tuple[str, ...]]) -> None:
        self._texts: Mapping[str, tuple[str, ...]] = dict(texts)

    @classmethod
    def from_artifact(cls, payload: Mapping[str, Any], *, version_uid: str) -> "RecognisedText":
        _require_role(payload, RECOGNISED_TEXT_ROLE)
        _require_version(payload, version_uid, RECOGNISED_TEXT_ROLE)
        raw_entries = _require(payload, "entries", Sequence, RECOGNISED_TEXT_ROLE)
        texts: dict[str, list[str]] = {}
        for position, entry in enumerate(raw_entries):
            where = f"{RECOGNISED_TEXT_ROLE}.entries[{position}]"
            if not isinstance(entry, Mapping):
                raise _invalid(f"{where} is not an object")
            block = _require(entry, "portal_block_id", str, where)
            kind = _require(entry, "kind", str, where)
            body = _require(entry, "text", str, where)
            if kind == RECOGNISED_TEXT_KIND:
                texts.setdefault(block, []).append(body)
        return cls({block: tuple(bodies) for block, bodies in texts.items()})

    @classmethod
    def empty(cls) -> "RecognisedText":
        return cls({})

    def texts(self, portal_block_id: str) -> tuple[str, ...]:
        """The recognised texts of the block; empty when it has none (an IMAGE or STAMP block, or no bundle)."""
        return self._texts.get(portal_block_id, ())

    def __len__(self) -> int:
        return len(self._texts)


@dataclass(frozen=True, slots=True)
class BlockGateInputs:
    """What the gate of block evidence judges against: the three views of one run.

    ``empty()`` is a run with no geometry (a version without a portal bundle): every block is then unverifiable and
    the gate refuses it. The gate fails closed; an absent view is never read as "nothing to check".
    """

    geometry: PortalBlockGeometry
    crops: CropManifest
    recognised: RecognisedText

    @classmethod
    def from_artifacts(
        cls,
        *,
        version_uid: str,
        portal_blocks: Mapping[str, Any] | None = None,
        page_crops: Mapping[str, Any] | None = None,
        recognised_text: Mapping[str, Any] | None = None,
    ) -> "BlockGateInputs":
        """The views of the run's saved documents, each checked to be of ``version_uid``. A document not given is an empty view."""
        return cls(
            geometry=(
                PortalBlockGeometry.empty()
                if portal_blocks is None
                else PortalBlockGeometry.from_artifact(portal_blocks, version_uid=version_uid)
            ),
            crops=(
                CropManifest.empty()
                if page_crops is None
                else CropManifest.from_artifact(page_crops, version_uid=version_uid)
            ),
            recognised=(
                RecognisedText.empty()
                if recognised_text is None
                else RecognisedText.from_artifact(recognised_text, version_uid=version_uid)
            ),
        )

    @classmethod
    def empty(cls) -> "BlockGateInputs":
        return cls(PortalBlockGeometry.empty(), CropManifest.empty(), RecognisedText.empty())


@dataclass(frozen=True, slots=True)
class BlockEvidenceItem:
    """One block as evidence, exactly as a candidate declared it: the row ``finding_block_evidence`` will hold.

    The normalised box is not here on purpose: it is the geometry's (``PortalBlockGeometry.place``), never the
    candidate's. ``recognised_quote`` is optional; when given it is compared as it is.
    """

    evidence_ordinal: int
    page_number: int
    portal_block_id: str
    crop_sha256: str
    recognised_quote: str | None = None

    def __post_init__(self) -> None:
        for name in ("evidence_ordinal", "page_number"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise _invalid(f"block evidence {name} is not an integer")
        for name in ("portal_block_id", "crop_sha256"):
            if not isinstance(getattr(self, name), str):
                raise _invalid(f"block evidence {name} is not a string")
        if self.recognised_quote is not None and not isinstance(self.recognised_quote, str):
            raise _invalid("block evidence recognised_quote is neither a string nor absent")


@dataclass(frozen=True, slots=True)
class BlockObservation:
    """One candidate grounded by blocks. Not yet a finding, and possibly never one.

    ``extended_observation_ref`` is the reference to the extended-review candidate it came from
    (``finding_observation.extended_observation_ref``); the publisher writes it and the gate only carries it.
    """

    observation_ordinal: int
    evidence: tuple[BlockEvidenceItem, ...]
    extended_observation_ref: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.observation_ordinal, int) or isinstance(self.observation_ordinal, bool):
            raise _invalid("block observation_ordinal is not an integer")
        if not self.evidence:
            # The same rule as a text observation: with no evidence it is malformed, not ungrounded.
            raise _invalid("a block observation carries no evidence")
        if len({item.evidence_ordinal for item in self.evidence}) != len(self.evidence):
            raise _invalid("a block observation repeats an evidence_ordinal")
        ref = self.extended_observation_ref
        if ref is not None and (
            not isinstance(ref, str) or not 1 <= len(ref) <= MAX_EXTENDED_OBSERVATION_REF_CHARS
        ):
            raise _invalid("extended_observation_ref is not 1 to 128 characters")

    @property
    def grounding_kind(self) -> str:
        return GROUNDING_PORTAL_BLOCK
