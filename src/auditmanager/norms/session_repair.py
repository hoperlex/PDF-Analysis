"""Re-recognition from a session transcription: `R-137`'s route for the degenerate blocks.

`R-137` (owner, 2026-10-19) has the blocks whose corpus text is the recognition model's own
reasoning re-read by Sonnet subagents of an interactive Claude Code session instead of the
paid proxy run. What that changes is **where the text comes from**, and nothing else:

- the pages are :func:`~auditmanager.norms.corpus_source.degenerate_pages`, the same set;
- every crop is checked against the operator's ``SHA256SUMS`` before it is rendered;
- the image is the crop rendered by the runner's own renderer at the recorded resolution, and
  the ledger step renders every crop again and requires the same bytes;
- the instruction handed to the readers is ``prompt.txt``, which must hold
  :data:`~auditmanager.norms.rerecognition.RECOGNITION_SYSTEM_PROMPT` byte for byte. A reader's
  context also holds its own system prompt and the operator's brief; this code cannot see
  either, so the result report records the brief and the readers' declared model;
- every answer is judged by :func:`~auditmanager.norms.rerecognition.rerecognise`, so the
  two-read rule, the degeneracy check, the minimum length and *nothing degenerate is
  applied* are the rules the paid run would have applied;
- the result is a version-2 :class:`~auditmanager.norms.repair.RepairLedger`, the file the
  loader and the bundle export already read.

**Why not the durable journal.** The journal exists so that a paid proxy call is never paid
twice and never lost (`R-106`). A session transcription is not a proxy call: nothing is
charged to this project per page, there is no response body to checkpoint and nothing to
re-pay. Putting it through the journal would mean inventing a transport, a charge and a
settlement, which are exactly the records the journal must never hold falsely.

**What the ledger says about it.** Each attempt names the model the session declared,
``stop_reason`` :data:`SESSION_STOP_REASON`, zero tokens (the session meters none for this
project) and ``cost_usd`` ``None`` -- *unpriced*, not *free*, which
:attr:`~auditmanager.norms.repair.RepairLedger.unpriced_attempts` already counts.

The work is three steps, and the middle one happens outside this code:

1. :func:`prepare_session` writes ``pages/<block_id>.png``, ``prompt.txt`` and
   ``session.json``;
2. a reader writes ``answers/<block_id>.<n>.md``, read *n* only where read *n - 1* came back
   degenerate;
3. :func:`session_ledger` replays those answers through the rule and returns the ledger, or
   refuses and names what is wrong or still owed.

**What a stopped run leaves behind.** The two-read rule bounds reads only if an answer, once
judged, cannot be swapped for a better one before the next run. Every ledger run, stopped or
not, appends the name and SHA-256 of each answer it consumed to ``answers.log``, and every
later run refuses when a logged answer has changed or gone (``answer_changed``). A degenerate
first read therefore stays the first read, and the second read is the only way forward.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any, Final

from .repair import RepairLedger, ledger_of
from .rerecognition import (
    MAX_ATTEMPTS,
    RECOGNITION_SYSTEM_PROMPT,
    PageToRecognise,
    RecognisedPage,
    rerecognise,
)

SESSION_FORMAT: Final[str] = "norm-session-repair/1"
SESSION_FILENAME: Final[str] = "session.json"
PROMPT_FILENAME: Final[str] = "prompt.txt"
PAGES_DIRECTORY: Final[str] = "pages"
ANSWERS_DIRECTORY: Final[str] = "answers"
ANSWERS_LOG: Final[str] = "answers.log"

#: The ``stop_reason`` of a session answer. Never ``max_tokens``: a session reader has no
#: output ceiling this code can observe, so a transcription is not marked truncated by it.
SESSION_STOP_REASON: Final[str] = "session_transcript"

_ANSWER_NAME = re.compile(r"(blk_[0-9a-f]{32})\.([1-9])\.md")
_MODEL = re.compile(r"claude-[a-z]+(?:-[0-9]+)+")


class SessionRefused(RuntimeError):
    """The session directory, the drop or an answer is not what the ledger may be built from."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(f"{reason}: {message}")
        self.reason = reason
        self.message = message


class ReadsOutstanding(SessionRefused):
    """Every answer present was usable, but the rule still needs these reads.

    ``outstanding`` holds ``(document_slug, block_id, read)``; a read *n > 1* is owed only
    because read *n - 1* came back degenerate.
    """

    def __init__(self, outstanding: Sequence[tuple[str, str, int]]) -> None:
        self.outstanding = tuple(outstanding)
        super().__init__(
            "reads_outstanding",
            f"{len(self.outstanding)} reads are still owed before the ledger can be built",
        )


def prompt_sha256() -> str:
    return hashlib.sha256(RECOGNITION_SYSTEM_PROMPT.encode("utf-8")).hexdigest()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_regular_file(path: Path) -> bool:
    """A regular file and not a link to one: one answer must not stand in for another."""
    try:
        return stat.S_ISREG(os.lstat(path).st_mode)
    except FileNotFoundError:
        return False


def _unique_blocks(pages: Sequence[PageToRecognise]) -> None:
    seen: set[str] = set()
    for page in pages:
        if page.block_id in seen:
            raise SessionRefused(
                "block_id_not_unique",
                f"{page.block_id} names two pages, so an answer file could not say which",
            )
        seen.add(page.block_id)


def _write_atomically(path: Path, data: bytes) -> None:
    temporary = path.with_name(path.name + ".partial")
    with open(temporary, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _page_entry(page: PageToRecognise, png_sha256: str) -> dict[str, Any]:
    return {
        "document_slug": page.document_slug,
        "block_id": page.block_id,
        "page_label": page.page_label,
        "crop_sha256": page.crop_sha256,
        "original_sha256": page.original_sha256,
        "png": f"{PAGES_DIRECTORY}/{page.block_id}.png",
        "png_sha256": png_sha256,
    }


def prepare_session(
    pages: Sequence[PageToRecognise],
    *,
    directory: Path,
    base_snapshot: str,
    drop_sums_sha256: str,
    dpi: int,
    render: Callable[[bytes], bytes],
    now: str,
) -> dict[str, Any]:
    """Render every page and write the session the readers work from. Never overwrites.

    The caller has already checked every crop against the sums: this function is handed the
    pages and the sums' digest, and records both, so the ledger step can require the same.
    """
    if (directory / SESSION_FILENAME).exists():
        raise SessionRefused(
            "session_exists",
            f"{directory} already holds a session; answers may exist against it, so it is "
            "never rewritten -- use a new directory",
        )
    _unique_blocks(pages)

    images = directory / PAGES_DIRECTORY
    images.mkdir(parents=True, exist_ok=True)
    (directory / ANSWERS_DIRECTORY).mkdir(exist_ok=True)
    entries = []
    for page in pages:
        png = render(page.crop)
        _write_atomically(images / f"{page.block_id}.png", png)
        entries.append(_page_entry(page, _sha256(png)))
    _write_atomically(directory / PROMPT_FILENAME, RECOGNITION_SYSTEM_PROMPT.encode("utf-8"))
    document = {
        "format": SESSION_FORMAT,
        "ruling": "R-137",
        "base_snapshot": base_snapshot,
        "drop_sums_sha256": drop_sums_sha256,
        "prompt_sha256": prompt_sha256(),
        "max_reads": MAX_ATTEMPTS,
        "dpi": dpi,
        "prepared_at": now,
        "pages": entries,
    }
    # The session file is written last: a directory without it is an interrupted prepare.
    _write_atomically(
        directory / SESSION_FILENAME,
        (json.dumps(document, ensure_ascii=False, indent=1, sort_keys=True) + "\n").encode("utf-8"),
    )
    return document


class _ReadMissing(Exception):
    def __init__(self, read: int) -> None:
        super().__init__(read)
        self.read = read


class _AnswerFiles:
    """A :class:`~auditmanager.norms.rerecognition.PageRecogniser` over one block's answers."""

    def __init__(self, answers: Path, block_id: str, *, model: str, consumed: set[str]) -> None:
        self._answers = answers
        self._block_id = block_id
        self._model = model
        self._consumed = consumed
        self._read = 0

    def recognise(self, page: PageToRecognise) -> RecognisedPage:
        self._read += 1
        name = f"{self._block_id}.{self._read}.md"
        path = self._answers / name
        if not _is_regular_file(path):
            raise _ReadMissing(self._read)
        try:
            text = path.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            raise SessionRefused("answer_unreadable", f"{name} is not UTF-8") from None
        self._consumed.add(name)
        return RecognisedPage(
            text=text,
            model=self._model,
            stop_reason=SESSION_STOP_REASON,
            input_tokens=0,
            output_tokens=0,
            cost_usd=None,
        )


def _read_session(directory: Path) -> dict[str, Any]:
    path = directory / SESSION_FILENAME
    if not _is_regular_file(path):
        raise SessionRefused("session_absent", f"no {SESSION_FILENAME} in {directory}")
    try:
        document = json.loads(path.read_bytes().decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise SessionRefused("session_format", f"{path} is not JSON in UTF-8") from None
    if not isinstance(document, dict) or document.get("format") != SESSION_FORMAT:
        raise SessionRefused("session_format", f"{path} is not a {SESSION_FORMAT} session")
    return document


def _check_session(
    document: dict[str, Any],
    pages: Sequence[PageToRecognise],
    directory: Path,
    *,
    base_snapshot: str,
    drop_sums_sha256: str,
    dpi: int,
    render: Callable[[bytes], bytes],
) -> None:
    if document.get("base_snapshot") != base_snapshot:
        raise SessionRefused(
            "session_mismatch",
            f"the session was prepared over {document.get('base_snapshot')!r}, the drop is "
            f"{base_snapshot!r}",
        )
    if document.get("drop_sums_sha256") != drop_sums_sha256:
        raise SessionRefused(
            "session_mismatch", "the session's crops were checked against another SHA256SUMS"
        )
    if document.get("prompt_sha256") != prompt_sha256():
        raise SessionRefused(
            "session_mismatch", "the recognition prompt changed since the session was prepared"
        )
    if document.get("dpi") != dpi:
        raise SessionRefused(
            "session_mismatch",
            f"the session was rendered at {document.get('dpi')!r} dpi, this ledger requires {dpi}",
        )
    prompt = directory / PROMPT_FILENAME
    if not _is_regular_file(prompt) or _sha256(prompt.read_bytes()) != prompt_sha256():
        raise SessionRefused(
            "session_mismatch", f"{PROMPT_FILENAME} is not the recognition prompt the readers had"
        )
    recorded = document.get("pages")
    if not isinstance(recorded, list) or len(recorded) != len(pages):
        raise SessionRefused(
            "session_mismatch",
            f"the session holds {len(recorded) if isinstance(recorded, list) else 'no'} pages, "
            f"the drop has {len(pages)} degenerate blocks",
        )
    for entry, page in zip(recorded, pages, strict=True):
        png = directory / PAGES_DIRECTORY / f"{page.block_id}.png"
        expected = _page_entry(page, str(entry.get("png_sha256") if isinstance(entry, dict) else ""))
        if entry != expected:
            raise SessionRefused(
                "session_mismatch",
                f"{page.document_slug}/{page.block_id} is not the page the session recorded",
            )
        if not _is_regular_file(png) or _sha256(png.read_bytes()) != expected["png_sha256"]:
            raise SessionRefused(
                "page_image_changed",
                f"{expected['png']} is not the image the session recorded for its readers",
            )
        if _sha256(render(page.crop)) != expected["png_sha256"]:
            raise SessionRefused(
                "page_image_changed",
                f"{expected['png']} is not the rendering of the crop the sums verified",
            )


def _read_log(directory: Path) -> dict[str, str]:
    """``answer name -> sha256`` from every earlier ledger run. A malformed line refuses."""
    path = directory / ANSWERS_LOG
    if not path.exists():
        return {}
    if not _is_regular_file(path):
        raise SessionRefused("answers_log_invalid", f"{ANSWERS_LOG} is not a regular file")
    logged: dict[str, str] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            entry = json.loads(line)
            name, digest = str(entry["answer"]), str(entry["sha256"])
        except (ValueError, KeyError, TypeError):
            raise SessionRefused("answers_log_invalid", f"{ANSWERS_LOG} line {number} is not an entry") from None
        if logged.setdefault(name, digest) != digest:
            raise SessionRefused("answers_log_invalid", f"{ANSWERS_LOG} names {name} with two digests")
    return logged


def _check_log(answers: Path, logged: dict[str, str]) -> None:
    for name, digest in sorted(logged.items()):
        path = answers / name
        if not _is_regular_file(path) or _sha256(path.read_bytes()) != digest:
            raise SessionRefused(
                "answer_changed",
                f"{ANSWERS_DIRECTORY}/{name} was judged by an earlier run and has since changed "
                "or gone; a judged read is never replaced",
            )


def _append_log(directory: Path, answers: Path, names: set[str], logged: dict[str, str], now: str) -> None:
    fresh = sorted(names - logged.keys())
    if not fresh:
        return
    lines = "".join(
        json.dumps({"answer": name, "sha256": _sha256((answers / name).read_bytes()), "logged_at": now},
                   sort_keys=True) + "\n"
        for name in fresh
    )
    with open(directory / ANSWERS_LOG, "a", encoding="utf-8") as handle:
        handle.write(lines)
        handle.flush()
        os.fsync(handle.fileno())


def session_ledger(
    pages: Sequence[PageToRecognise],
    *,
    directory: Path,
    base_snapshot: str,
    drop_sums_sha256: str,
    model: str,
    transcribed_at: str,
    generated_at: str,
    dpi: int,
    render: Callable[[bytes], bytes],
) -> RepairLedger:
    """The ledger the session's answers imply, judged by the unchanged rule.

    Refuses (:class:`SessionRefused`) when the session, the drop, the prompt, the resolution or
    an image is not what the readers were given, when an answer belongs to no block, was not
    needed by the rule, is not UTF-8 or changed after an earlier run judged it. Raises
    :class:`ReadsOutstanding` when only further reads are missing. Its one write is the
    append to ``answers.log`` of the answers this run consumed.
    """
    if _MODEL.fullmatch(model) is None:
        raise SessionRefused(
            "model_unnamed", "the session model must be its exact lowercase identifier"
        )
    try:
        datetime.fromisoformat(transcribed_at)
    except ValueError:
        raise SessionRefused(
            "transcribed_at_invalid", f"{transcribed_at!r} is not an ISO 8601 timestamp"
        ) from None
    _unique_blocks(pages)
    document = _read_session(directory)
    _check_session(
        document, pages, directory, base_snapshot=base_snapshot,
        drop_sums_sha256=drop_sums_sha256, dpi=dpi, render=render,
    )

    answers = directory / ANSWERS_DIRECTORY
    logged = _read_log(directory)
    _check_log(answers, logged)
    blocks = {page.block_id for page in pages}
    present: set[str] = set()
    if answers.is_dir():
        for path in answers.iterdir():
            match = _ANSWER_NAME.fullmatch(path.name)
            if match is None or match.group(1) not in blocks or not _is_regular_file(path):
                raise SessionRefused(
                    "answer_unexpected",
                    f"{ANSWERS_DIRECTORY}/{path.name} is not an answer to a block of this session",
                )
            present.add(path.name)

    consumed: set[str] = set()
    outstanding: list[tuple[str, str, int]] = []
    repairs = []
    for page in pages:
        reader = _AnswerFiles(answers, page.block_id, model=model, consumed=consumed)
        try:
            repairs.append(rerecognise(page, reader, now=transcribed_at))
        except _ReadMissing as missing:
            outstanding.append((page.document_slug, page.block_id, missing.read))

    first_missing = [item for item in outstanding if item[2] == 1]
    if first_missing:
        raise SessionRefused(
            "first_read_missing",
            f"{len(first_missing)} blocks have no first answer, e.g. "
            f"{first_missing[0][0]}/{first_missing[0][1]}",
        )
    unconsumed = sorted(present - consumed)
    if unconsumed:
        raise SessionRefused(
            "answer_unconsumed",
            f"{len(unconsumed)} answers were not needed by the rule, so the ledger could not "
            f"record them: {', '.join(unconsumed[:5])}",
        )
    _append_log(directory, answers, consumed, logged, generated_at)
    if outstanding:
        raise ReadsOutstanding(outstanding)
    return ledger_of(base_snapshot, generated_at, repairs)


__all__ = [
    "ANSWERS_DIRECTORY",
    "ANSWERS_LOG",
    "PAGES_DIRECTORY",
    "PROMPT_FILENAME",
    "SESSION_FILENAME",
    "SESSION_FORMAT",
    "SESSION_STOP_REASON",
    "ReadsOutstanding",
    "SessionRefused",
    "prepare_session",
    "prompt_sha256",
    "session_ledger",
]
