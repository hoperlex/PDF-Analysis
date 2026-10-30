"""Bounded worker-side full PDF interpretation, with a cancellable receipt stream.

This is source preparation, not upload admission. The child returns the same pinned
extraction used to build the prepared artifacts; the worker never parses it a second
time or substitutes an unchecked result after a refusal.
"""

from __future__ import annotations

import json
import math
import os
import selectors
import subprocess
import sys
import time
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from auditmanager.analysis.stages.extraction import (
    ExtractedDocument, ExtractedLine, ExtractedPage, normalize,
)
from auditmanager.shared.errors import DomainError, ErrorCode


@dataclass(frozen=True, slots=True)
class PdfPrecheckLimits:
    """Finite per-document worker limits; upload's quick envelope is unchanged."""

    address_space_bytes: int = 1536 * 1024 * 1024
    cpu_seconds: int = 1200
    wall_seconds: float = 1800
    startup_seconds: float = 45
    page_seconds: float = 180
    max_pages: int = 500
    max_page_characters: int = 200_000
    max_document_characters: int = 20_000_000
    max_line_bytes: int = 32 * 1024 * 1024
    max_output_bytes: int = 256 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class PdfPrecheckProgress:
    phase: Literal["started", "checking", "completed", "failed"]
    completed_pages: int
    total_pages: int
    error_code: str | None = None
    reason: str | None = None


Progress = Callable[[PdfPrecheckProgress], None]
Checkpoint = Callable[[], None]
_CHILD = Path(__file__).with_name("pdf_precheck_child.py")
_SAFE_CHILD_REASONS = frozenset({
    "source_unreadable", "source_encrypted", "page_count_disagreement",
    "line_traversal_disagreement", "normalization_disagreement",
    "pdf_precheck_limits",
})


def _refusal(reason: str, *, internal: bool = False) -> DomainError:
    return DomainError(
        ErrorCode.INTERNAL_ERROR if internal else ErrorCode.ANALYSIS_INPUT_INVALID,
        message="the complete PDF check did not succeed; analysis was not started",
        stage_id="source_preparation", reason=reason,
    )


def _positive_int(value: Any) -> bool:
    return type(value) is int and value > 0


def _page(payload: Mapping[str, Any], ordinal: int, limits: PdfPrecheckLimits) -> ExtractedPage:
    """Validate the child's receipt before accepting any extracted page."""
    try:
        if type(payload["page_number"]) is not int or payload["page_number"] != ordinal:
            raise ValueError
        text = payload["text"]
        rotation = payload["rotation_deg"]
        width, height = float(payload["width_pt"]), float(payload["height_pt"])
        if (not isinstance(text, str) or text != normalize(text)
                or len(text) > limits.max_page_characters
                or type(rotation) is not int or rotation not in (0, 90, 180, 270)
                or not math.isfinite(width) or not math.isfinite(height)
                or width <= 0 or height <= 0 or not isinstance(payload["lines"], list)):
            raise ValueError
        lines: list[ExtractedLine] = []
        for raw in payload["lines"]:
            line = ExtractedLine(**raw)
            if (not isinstance(line.text, str) or line.text != normalize(line.text)
                    or not all(math.isfinite(v) for v in
                               (line.x0, line.top, line.x1, line.bottom, line.size))):
                raise ValueError
            lines.append(line)
        if "\n".join(line.text for line in lines) != text:
            raise ValueError
        return ExtractedPage(ordinal, width, height, rotation, text, tuple(lines))
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise _refusal("pdf_precheck_receipt_invalid", internal=True) from exc


def extract_document(
    source: str | os.PathLike[str], *, progress: Progress | None = None,
    checkpoint: Checkpoint | None = None, expected_page_count: int | None = None,
    limits: PdfPrecheckLimits = PdfPrecheckLimits(),
) -> ExtractedDocument:
    """Fully interpret each page in a resource-limited child, kill/reap on any refusal.

    Only an inherited read descriptor reaches the isolated child. No credentials,
    source names, parser stderr or exception text enter the durable progress journal.
    ``checkpoint`` must raise when the current durable Attempt loses authority.
    """
    if expected_page_count is not None and (
        not _positive_int(expected_page_count) or expected_page_count > limits.max_pages
    ):
        raise _refusal("page_count_disagreement")
    if checkpoint is not None:
        checkpoint()
    started = time.monotonic()
    try:
        source_handle = open(source, "rb")
    except OSError as exc:
        raise _refusal("source_unreadable") from exc
    with source_handle:
        settings = {**asdict(limits), "descriptor": source_handle.fileno(),
                    "expected_page_count": expected_page_count}
        try:
            child = subprocess.Popen(
                [sys.executable, "-I", "-B", str(_CHILD), json.dumps(settings)],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, pass_fds=(source_handle.fileno(),),
                cwd="/", env={"PATH": os.defpath},
            )
        except OSError as exc:
            raise _refusal("pdf_precheck_unavailable", internal=True) from exc
        try:
            return _read_receipt(child, started, limits, expected_page_count,
                                 progress, checkpoint)
        finally:
            if child.poll() is None:
                child.kill()
            child.wait()
            if child.stdout is not None:
                child.stdout.close()


def _read_receipt(
    child: subprocess.Popen[bytes], started: float, limits: PdfPrecheckLimits,
    expected_page_count: int | None, progress: Progress | None, checkpoint: Checkpoint | None,
) -> ExtractedDocument:
    assert child.stdout is not None
    ready = False
    complete = False
    total: int | None = None
    page_started: float | None = None
    pages: list[ExtractedPage] = []
    characters = 0
    output_bytes = 0
    pending = bytearray()
    with selectors.DefaultSelector() as selector:
        selector.register(child.stdout, selectors.EVENT_READ)
        while True:
            if checkpoint is not None:
                checkpoint()
            now = time.monotonic()
            if now - started > limits.wall_seconds:
                raise _refusal("pdf_precheck_timeout")
            if not ready and now - started > limits.startup_seconds:
                raise _refusal("pdf_precheck_unavailable", internal=True)
            if page_started is not None and now - page_started > limits.page_seconds:
                raise _refusal("pdf_precheck_page_timeout")
            if not selector.select(timeout=0.2):
                continue
            chunk = os.read(child.stdout.fileno(), 64 * 1024)
            if not chunk:
                break
            output_bytes += len(chunk)
            if output_bytes > limits.max_output_bytes:
                raise _refusal("pdf_precheck_limits")
            pending.extend(chunk)
            while b"\n" in pending:
                raw, _, rest = pending.partition(b"\n")
                pending = bytearray(rest)
                if len(raw) > limits.max_line_bytes:
                    raise _refusal("pdf_precheck_limits")
                try:
                    record = json.loads(raw)
                    if not isinstance(record, dict) or complete:
                        raise ValueError
                    kind = record.get("kind")
                    if kind == "ready" and not ready:
                        ready = True
                    elif kind == "document" and ready and total is None:
                        count = record["page_count"]
                        if (not _positive_int(count) or count > limits.max_pages
                                or expected_page_count is not None and count != expected_page_count):
                            raise _refusal("page_count_disagreement")
                        total = count
                        # Bound page-tree/interpreter setup as well as the first page.
                        page_started = time.monotonic()
                        if progress is not None:
                            progress(PdfPrecheckProgress("checking", 0, total))
                    elif kind == "page_started" and total is not None:
                        if record["page_number"] != len(pages) + 1 or len(pages) >= total:
                            raise ValueError
                        page_started = time.monotonic()
                    elif kind == "page" and total is not None and len(pages) < total:
                        page = _page(record["page"], len(pages) + 1, limits)
                        pages.append(page)
                        characters += page.char_count
                        if characters > limits.max_document_characters:
                            raise _refusal("pdf_precheck_limits")
                        page_started = time.monotonic()
                        if progress is not None:
                            progress(PdfPrecheckProgress("checking", len(pages), total))
                    elif kind == "complete" and total is not None and len(pages) == total:
                        if record["page_count"] != total:
                            raise ValueError
                        complete = True
                        page_started = None
                    elif kind == "failed":
                        reason = record.get("reason")
                        raise _refusal(reason if reason in _SAFE_CHILD_REASONS else "source_unreadable")
                    else:
                        raise ValueError
                except (json.JSONDecodeError, UnicodeDecodeError, KeyError, TypeError, ValueError) as exc:
                    raise _refusal("pdf_precheck_receipt_invalid", internal=True) from exc
            if len(pending) > limits.max_line_bytes:
                raise _refusal("pdf_precheck_limits")
    # Closing stdout does not prove exit. Keep shutdown cancellable too.
    while child.poll() is None:
        if checkpoint is not None:
            checkpoint()
        if time.monotonic() - started > limits.wall_seconds:
            raise _refusal("pdf_precheck_timeout")
        try:
            child.wait(timeout=0.2)
        except subprocess.TimeoutExpired:
            continue
    return_code = child.returncode
    if pending or not ready:
        raise _refusal("pdf_precheck_unavailable", internal=True)
    if return_code != 0 or not complete:
        raise _refusal("pdf_precheck_limits" if return_code < 0 else "pdf_precheck_incomplete")
    if checkpoint is not None:
        checkpoint()
    return ExtractedDocument(tuple(pages))
