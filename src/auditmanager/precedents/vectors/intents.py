"""What the encoder is given for a case, and the check of what it returns (`ADR-0029` decision 8, `DECISION-MEMORY-01` section 3.6).

Pure: text and bytes in, text and bytes out. The encoder itself is the offline container of the norms-worker image; the worker (a process with
the database) writes a request file, the container writes a response file, and the worker checks it here before one vector reaches a table.

**The view** ``finding_v1`` is the category, the finding text and the head of the recommendation, in one budget of :data:`INPUT_BUDGET_CHARS`
characters so that it stays below the 512 tokens at which the encoder refuses (about 400 tokens at 2.5 characters a token, plan-v5 section 2.2).
A cut is marked with :data:`CUT_MARK`, never silent. The view is versioned by its name: a change of the budget or of the layout is a new view
kind, because ``input_sha256`` is the identity of the input and a new text under an old kind would answer for the wrong thing.

**The request** is ``auditmanager-embed-texts-request/1`` of the norms embedder, with the digest of the text as the entry's ``id``: two intents with
the same text are one entry (deduplication by ``input_sha256``), and the digest the container reports back for an entry must be the entry's own id.

**The answer** is ``auditmanager-embed-texts/1`` and nothing is trusted in it: the profile, the model revision, the dimensions and the byte order
are the frozen ones; every vector is 1024 finite float32 values of unit norm (the CHECK of ``decision_memory_embedding``, restated) with the digest
its entry claims. A text the container refused for its length (over :data:`MAX_TOKENS` tokens) comes back in the sidecar ``over_limit`` and is
``poisoned``: a text is never truncated to fit.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import math
import struct
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

__all__ = [
    "CUT_MARK", "DIMENSIONS", "EMBEDDING_PROFILE", "INPUT_BUDGET_CHARS", "MAX_ATTEMPTS", "MAX_TOKENS", "MODEL_REVISION", "OVER_LIMIT_FORMAT",
    "POISON_ATTEMPTS", "POISON_DIGEST_MISMATCH", "POISON_TOKEN_LIMIT", "REQUEST_FORMAT", "RESPONSE_FORMAT", "UNIT_NORM_TOLERANCE",
    "VIEW_FINDING", "EncodedVector", "ExportEntry", "ImportRefused", "ParsedAnswer", "build_finding_view", "build_request", "input_sha256",
    "parse_answer", "pgvector_literal",
]

#: The frozen profile (`norms/embedding/profile.py`); a test holds these equal to the norms package's own, which the image runs.
EMBEDDING_PROFILE: Final[str] = "bge-m3-dense-v1"
MODEL_REVISION: Final[str] = "5617a9f61b028005a4858fdac845db406aefb181"
DIMENSIONS: Final[int] = 1024
MAX_TOKENS: Final[int] = 512
#: Accepted distance between a vector's L2 norm and 1: the bound of ``ck_decision_memory_embedding_unit_norm``.
UNIT_NORM_TOLERANCE: Final[float] = 0.0001

REQUEST_FORMAT: Final[str] = "auditmanager-embed-texts-request/1"
RESPONSE_FORMAT: Final[str] = "auditmanager-embed-texts/1"
#: The sidecar the in-image entry writes for the texts it did not encode (plan-v5 section 5: «текст длиннее 512 токенов уходит в poisoned»).
OVER_LIMIT_FORMAT: Final[str] = "auditmanager-embed-over-limit/1"

VIEW_FINDING: Final[str] = "finding_v1"
INPUT_BUDGET_CHARS: Final[int] = 1000
CUT_MARK: Final[str] = " [обрезано]"
_CATEGORY_LINE: Final[str] = "Категория: "
_FINDING_LINE: Final[str] = "Находка: "
_RECOMMENDATION_LINE: Final[str] = "Рекомендация: "
#: A recommendation head shorter than this is not worth a line of its own: it would be a cut with nothing to read.
_MIN_RECOMMENDATION_CHARS: Final[int] = 40

#: ``decision_memory_embedding_intent.attempts`` is at most 5 (its CHECK); the fifth failed attempt poisons the intent.
MAX_ATTEMPTS: Final[int] = 5
POISON_TOKEN_LIMIT: Final[str] = "token_limit_exceeded"
POISON_DIGEST_MISMATCH: Final[str] = "input_digest_mismatch"
POISON_ATTEMPTS: Final[str] = "attempts_exhausted"

_VECTOR_FORMAT: Final[str] = f"!{DIMENSIONS}f"
_VECTOR_BYTES: Final[int] = struct.calcsize(_VECTOR_FORMAT)
_HEX64: Final[frozenset[str]] = frozenset("0123456789abcdef")


def input_sha256(text: str) -> str:
    """SHA-256 of the exact inference input: what the container reports back as ``input_sha256`` (`norms/embedding/windowing.py`)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _squeeze(text: str) -> str:
    """One line, single spaces: two spellings of the same sentence are one input."""
    return " ".join(text.split())


def _head(text: str, room: int) -> str:
    """At most ``room`` characters of ``text``, cut at a word and marked when anything was cut."""
    if len(text) <= room:
        return text
    keep = room - len(CUT_MARK)
    if keep <= 0:
        return ""
    cut = text[:keep]
    space = cut.rfind(" ")
    if space >= keep // 2:
        cut = cut[:space]
    return cut.rstrip() + CUT_MARK


def build_finding_view(*, category: str, finding_text: str, recommendation_text: str) -> str:
    """The text of ``finding_v1``: at most :data:`INPUT_BUDGET_CHARS` characters, the finding before the recommendation.

    The category and the finding take what they need (the finding is cut and marked if it alone is over the budget); the recommendation takes
    the room that is left, as a head, and is left out when the room is smaller than :data:`_MIN_RECOMMENDATION_CHARS`."""
    category_line = _CATEGORY_LINE + _squeeze(category)
    finding = _squeeze(finding_text)
    recommendation = _squeeze(recommendation_text)
    if not finding:
        raise ValueError("a finding view needs the finding's text")
    room = INPUT_BUDGET_CHARS - len(category_line) - 1 - len(_FINDING_LINE)
    finding_part = _head(finding, room)
    lines = [category_line, _FINDING_LINE + finding_part]
    used = len(category_line) + 1 + len(_FINDING_LINE) + len(finding_part)
    left = INPUT_BUDGET_CHARS - used - 1 - len(_RECOMMENDATION_LINE)
    if recommendation and left >= _MIN_RECOMMENDATION_CHARS:
        lines.append(_RECOMMENDATION_LINE + _head(recommendation, left))
    text = "\n".join(lines)
    assert len(text) <= INPUT_BUDGET_CHARS
    return text


@dataclass(frozen=True, slots=True)
class ExportEntry:
    """One text for the encoder: the digest is its id."""

    input_sha256: str
    text: str


def build_request(texts: Iterable[str]) -> dict[str, Any]:
    """The request file for ``texts``: one entry per distinct text (deduplicated by the digest of the text), in the order of the digests.

    Refuses an empty batch: the encoder refuses one, and a window with nothing to encode never reaches it."""
    entries: dict[str, str] = {}
    for text in texts:
        entries.setdefault(input_sha256(text), text)
    if not entries:
        raise ValueError("a request holds at least one text")
    return {"format": REQUEST_FORMAT, "texts": [{"id": digest, "text": entries[digest]} for digest in sorted(entries)]}


class ImportRefused(ValueError):
    """The encoder's answer is not one this stand accepts: nothing of it is imported."""


@dataclass(frozen=True, slots=True)
class EncodedVector:
    """A vector the answer carried for one text: its bytes are checked (1024 big-endian float32, unit norm, the digest it claims)."""

    input_sha256: str
    embedding_sha256: str
    values: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class ParsedAnswer:
    """What the answer holds for the requested ids: the vectors, the texts over the token limit, and the ids it did not answer at all."""

    vectors: Mapping[str, EncodedVector]
    over_limit: Mapping[str, int]
    rejected: Mapping[str, str]
    missing: frozenset[str]


def _is_digest(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= _HEX64


def _decode(raw: object) -> tuple[bytes, tuple[float, ...]]:
    """The bytes and the values of one encoded vector; a refusal names why."""
    if not isinstance(raw, str):
        raise ValueError("the vector is not text")
    try:
        packed = base64.b64decode(raw.encode("ascii"), validate=True)
    except (binascii.Error, UnicodeEncodeError) as exc:
        raise ValueError("the vector is not base64") from exc
    if len(packed) != _VECTOR_BYTES:
        raise ValueError(f"the vector has {len(packed)} bytes, not {_VECTOR_BYTES}")
    values = struct.unpack(_VECTOR_FORMAT, packed)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("the vector holds NaN or infinity")
    norm = math.sqrt(math.fsum(value * value for value in values))
    if abs(norm - 1.0) > UNIT_NORM_TOLERANCE:
        raise ValueError(f"the vector's norm is {norm:.8f}, not 1 within {UNIT_NORM_TOLERANCE}")
    return packed, values


def parse_answer(
    response: object, over_limit: object | None, *, requested: Iterable[str],
) -> ParsedAnswer:
    """Check the answer to a request of ``requested`` ids (digests) and sort what it holds.

    **The envelope refuses the whole answer** (:class:`ImportRefused`): another format, another profile, another model revision, other
    dimensions or byte order, an id that was not asked for or that repeats, an entry whose reported digest is not its id. A frozen identity that
    moved is not a vector to be kept under the old name.

    **A single vector refuses only itself**: one that is not 1024 finite float32 values of unit norm, or whose digest is not the one it claims,
    lands in ``rejected`` with the reason, and its intent is retried (and poisoned on the fifth failure). A text the in-image entry set aside
    for its length is in ``over_limit``. An id that is in none of the three is ``missing``."""
    asked = frozenset(requested)
    if not isinstance(response, dict) or response.get("format") != RESPONSE_FORMAT:
        raise ImportRefused(f"the answer is not {RESPONSE_FORMAT}")
    expected = {
        "embedding_profile": EMBEDDING_PROFILE, "model_revision": MODEL_REVISION, "dimensions": DIMENSIONS,
        "dtype": "float32", "byte_order": "big",
    }
    for name, value in expected.items():
        if response.get(name) != value:
            raise ImportRefused(f"the answer's {name} is {response.get(name)!r}, the frozen profile's is {value!r}")
    entries = response.get("vectors")
    if not isinstance(entries, list):
        raise ImportRefused("the answer holds no list of vectors")
    vectors: dict[str, EncodedVector] = {}
    rejected: dict[str, str] = {}
    for position, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ImportRefused(f"vector {position} of the answer is not an object")
        identifier = entry.get("id")
        if not _is_digest(identifier) or identifier not in asked:
            raise ImportRefused(f"vector {position} of the answer names an id that was not asked for")
        assert isinstance(identifier, str)
        if identifier in vectors or identifier in rejected:
            raise ImportRefused(f"the answer holds the id {identifier} twice")
        if entry.get("input_sha256") != identifier:
            raise ImportRefused(f"the answer reports another input digest for {identifier}")
        try:
            packed, values = _decode(entry.get("vector"))
            if hashlib.sha256(packed).hexdigest() != entry.get("vector_sha256"):
                raise ValueError("the vector's digest is not the one it claims")
        except ValueError as exc:
            rejected[identifier] = str(exc)
            continue
        vectors[identifier] = EncodedVector(identifier, hashlib.sha256(packed).hexdigest(), values)
    skipped: dict[str, int] = {}
    if over_limit is not None:
        if not isinstance(over_limit, dict) or over_limit.get("format") != OVER_LIMIT_FORMAT or not isinstance(over_limit.get("entries"), list):
            raise ImportRefused(f"the over-limit list is not {OVER_LIMIT_FORMAT}")
        for position, item in enumerate(over_limit["entries"]):
            identifier = item.get("id") if isinstance(item, dict) else None
            count = item.get("token_count") if isinstance(item, dict) else None
            if not _is_digest(identifier) or identifier not in asked or not isinstance(count, int) or count <= MAX_TOKENS:
                raise ImportRefused(f"entry {position} of the over-limit list is not a text over {MAX_TOKENS} tokens that was asked for")
            assert isinstance(identifier, str)
            if identifier in vectors or identifier in rejected or identifier in skipped:
                raise ImportRefused(f"the id {identifier} is both encoded and over the limit, or listed twice")
            skipped[identifier] = count
    missing = asked - vectors.keys() - rejected.keys() - skipped.keys()
    return ParsedAnswer(vectors, skipped, rejected, frozenset(missing))


def pgvector_literal(values: Sequence[float]) -> str:
    """The pgvector text of a vector, nine significant digits: it round-trips a float32 exactly, so the norm the database checks is the one checked here."""
    return "[" + ",".join(format(value, ".9g") for value in values) + "]"
