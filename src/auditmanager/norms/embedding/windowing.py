"""The 512/64 token windowing, ported byte for byte from the bake-off runner.

:func:`window_spans` is ``tools/norms/embedding_bakeoff.py``'s ``_windows`` with one change of
output: it returns each window's character span and inference token count instead of only the
window text, because ``norm_embedding`` stores both. The control flow, every tokenizer call and
its arguments, and every refusal are the runner's, in the runner's order, so the window texts
are equal on any tokenizer. Three tests hold that: a synthetic fast tokenizer, a replay of
recorded tokenizer answers (which fails on any call the recording does not hold), and, in the
rebuilt image, the real ``BAAI/bge-m3`` tokenizer over the corpus
(``infra/norms-worker/check_windows.py``).

The tokenizer is passed in. Nothing here imports ``tokenizers`` or ``transformers``.

:func:`verify_window_set` is the completeness rule `D-127` names: a chunk's windows are its
*full* window set — they start at its first character, end at its last, overlap pairwise, and
each input digest is the digest of exactly its slice. The repository applies the same rule
before it accepts a build, so one one-character window per chunk no longer passes.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from ..chunking import JOIN
from .profile import MAX_TOKENS, OVERLAP_TOKENS, PASSAGE_PREFIX


class WindowingRefused(ValueError):
    """A text cannot be windowed losslessly, or a window set is not a chunk's full set."""


@dataclass(frozen=True, slots=True)
class WindowSpan:
    """``text[char_start:char_end]`` is the window; ``token_count`` includes special tokens."""

    char_start: int
    char_end: int
    token_count: int


def window_spans(
    tokenizer: Any,
    text: str,
    limit: int = MAX_TOKENS,
    overlap: int = OVERLAP_TOKENS,
    *,
    prefix: str = PASSAGE_PREFIX,
) -> tuple[tuple[WindowSpan, ...], int, int]:
    """``(windows, content token count, inference token count)`` exactly as the runner computes."""
    if not getattr(tokenizer, "is_fast", False):
        raise WindowingRefused("offset-aware lossless windows require a fast tokenizer")
    encoded = tokenizer(
        text,
        add_special_tokens=False,
        return_offsets_mapping=True,
        truncation=False,
    )
    token_ids = encoded["input_ids"]
    offsets = encoded["offset_mapping"]
    if not token_ids:
        raise WindowingRefused("canonical paragraph tokenized to zero tokens")
    if len(token_ids) != len(offsets) or any(end <= start for start, end in offsets):
        raise WindowingRefused("tokenizer returned unusable character offsets")

    special_tokens = tokenizer.num_special_tokens_to_add(pair=False)
    inference_count = (
        len(tokenizer.encode(prefix + text, add_special_tokens=True, truncation=False))
        if prefix
        else len(token_ids) + special_tokens
    )
    if inference_count <= limit:
        return (WindowSpan(0, len(text), inference_count),), len(token_ids), inference_count

    windows: list[WindowSpan] = []
    start = 0
    while start < len(token_ids):
        end = min(len(token_ids), start + limit)
        while end > start:
            char_start = 0 if start == 0 else offsets[start][0]
            char_end = len(text) if end == len(token_ids) else offsets[end - 1][1]
            value = text[char_start:char_end]
            encoded_count = len(
                tokenizer.encode(
                    prefix + value,
                    add_special_tokens=True,
                    truncation=False,
                )
            )
            if encoded_count <= limit:
                break
            end -= max(1, encoded_count - limit)
        if end <= start or not value.strip():
            raise WindowingRefused("cannot produce a non-empty token window within model limit")
        windows.append(WindowSpan(char_start, char_end, encoded_count))
        if end == len(token_ids):
            break
        start = max(start + 1, end - overlap)

    first = text[windows[0].char_start : windows[0].char_end]
    last = text[windows[-1].char_start : windows[-1].char_end]
    if first[0] != text[0] or last[-1] != text[-1]:
        raise WindowingRefused("token windows do not cover the paragraph boundaries")
    return tuple(windows), len(token_ids), inference_count


def paragraph_span(
    paragraph_lengths: Sequence[int], paragraph_ordinal_first: int, char_start: int, char_end: int
) -> tuple[int, int]:
    """The canonical paragraph ordinals a window ``[char_start, char_end)`` of a chunk touches.

    The chunk's text is its paragraphs joined by ``chunking.JOIN``. The first paragraph is the
    first one ending after ``char_start``; the last is the last one starting before
    ``char_end``.
    """
    if not paragraph_lengths or char_end <= char_start:
        raise WindowingRefused("a window touches no paragraph")
    first = last = None
    position = 0
    for index, length in enumerate(paragraph_lengths):
        paragraph_start, paragraph_end = position, position + length
        if first is None and paragraph_end > char_start:
            first = index
        if paragraph_start < char_end:
            last = index
        position = paragraph_end + len(JOIN)
    if first is None or last is None or last < first:
        raise WindowingRefused("a window lies outside its chunk's paragraphs")
    return paragraph_ordinal_first + first, paragraph_ordinal_first + last


def chunk_text_matches_layout(text: str, paragraph_lengths: Sequence[int]) -> bool:
    """True when ``text`` can be the ``JOIN`` of paragraphs of exactly these lengths."""
    expected = sum(paragraph_lengths) + len(JOIN) * (len(paragraph_lengths) - 1)
    if not paragraph_lengths or expected != len(text):
        return False
    position = 0
    for length in paragraph_lengths[:-1]:
        position += length
        if text[position : position + len(JOIN)] != JOIN:
            return False
        position += len(JOIN)
    return True


def input_digest(value: str) -> str:
    """SHA-256 of the exact inference input."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class WindowFacts:
    """What :func:`verify_window_set` reads of one window."""

    window_ordinal: int
    char_offset: int
    char_length: int
    token_count: int
    paragraph_ordinal_first: int
    paragraph_ordinal_last: int
    input_sha256: str


def verify_window_set(
    *,
    label: str,
    text: str,
    paragraph_ordinal_first: int,
    paragraph_ordinal_last: int,
    paragraph_lengths: Sequence[int],
    windows: Sequence[WindowFacts],
    limit: int = MAX_TOKENS,
) -> None:
    """Refuse anything but a chunk's full window set (`D-127`).

    Ordinals ``0..n-1``; every token count within ``1..limit``; the first window starts at the
    chunk's first character and the last ends after its last; each later window starts and ends
    after its predecessor and starts before the predecessor ends (the 64-token overlap is a
    character overlap); every input digest is SHA-256 of exactly its slice; every paragraph
    span is the one the slice touches.
    """
    if len(paragraph_lengths) != paragraph_ordinal_last - paragraph_ordinal_first + 1:
        raise WindowingRefused(f"{label}: paragraph layout does not match its span")
    if not chunk_text_matches_layout(text, paragraph_lengths):
        raise WindowingRefused(f"{label}: text is not the join of its paragraphs")
    if not windows:
        raise WindowingRefused(f"{label}: no window")
    previous: WindowFacts | None = None
    for index, window in enumerate(windows):
        start, end = window.char_offset, window.char_offset + window.char_length
        if window.window_ordinal != index:
            raise WindowingRefused(f"{label}: window ordinal {window.window_ordinal} is not {index}")
        if not 1 <= window.token_count <= limit:
            raise WindowingRefused(f"{label}: window {index} has {window.token_count} tokens")
        if window.char_offset < 0 or window.char_length <= 0 or end > len(text):
            raise WindowingRefused(f"{label}: window {index} span {start}..{end} is outside the text")
        if previous is None:
            if start != 0:
                raise WindowingRefused(f"{label}: the first window starts at {start}, not 0")
        else:
            previous_start = previous.char_offset
            previous_end = previous.char_offset + previous.char_length
            if not (previous_start < start < previous_end < end):
                raise WindowingRefused(
                    f"{label}: window {index} span {start}..{end} does not overlap and advance "
                    f"past window {index - 1} span {previous_start}..{previous_end}"
                )
        if window.input_sha256 != input_digest(text[start:end]):
            raise WindowingRefused(f"{label}: window {index} input digest is not its slice's")
        if (window.paragraph_ordinal_first, window.paragraph_ordinal_last) != paragraph_span(
            paragraph_lengths, paragraph_ordinal_first, start, end
        ):
            raise WindowingRefused(f"{label}: window {index} paragraph span is not its slice's")
        previous = window
    assert previous is not None
    if previous.char_offset + previous.char_length != len(text):
        raise WindowingRefused(
            f"{label}: the last window ends at {previous.char_offset + previous.char_length}, "
            f"not {len(text)}"
        )
