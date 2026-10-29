"""Write a report's PDF in a child under its ceilings and read the bytes back (`CMP-VC-REPORT-01`, ADR-0025 decision 8).

:class:`~auditmanager.comparison.profile.runner.SubprocessChildRunner` starts a program with a bare environment and ``/`` as its working
directory, waits with a wall clock, signals only its own child by its PID and reads the end from the kernel's wait status; it is given the
PDF program here. The ceilings are those of decision 8 and its addendum -- **768 MiB** of address space, **300 s** of CPU, **600 s** of wall
(under the 900 s attempt watchdog) -- and the size of the file the child may write is **64 MiB**. An end without a result (``overrun``, ``cpu``,
``wall``, a signal, an error) is a :class:`PdfFailed` of that report only; a child that never started is a fault of the server
(:class:`~auditmanager.comparison.profile.runner.ChildStartError`, passed on).

The report's document goes to the child as a JSON file in a private temporary directory, which is removed with the child's result; a test may
supply any object with ``run(settings, limits) -> ChildResult``.
"""

from __future__ import annotations

import json
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from auditmanager.comparison.profile.limits import MIB, ChildLimits
from auditmanager.comparison.profile.runner import ChildResult, ChildRunner, ChildStartError, SubprocessChildRunner

__all__ = [
    "ChildStartError",
    "FONT_DIR",
    "OUTPUT_LIMIT_BYTES",
    "PDF_LIMITS",
    "PROGRAM",
    "PdfFailed",
    "PdfResult",
    "pdf_runner",
    "write_pdf",
]

PROGRAM: Final[Path] = Path(__file__).with_name("program.py")
FONT_DIR: Final[Path] = Path(__file__).resolve().parent.parent / "fonts"
#: ADR-0025 decision 8 and its addenda: 768 MiB, 300 s of CPU, 600 s of wall.
PDF_LIMITS: Final[ChildLimits] = ChildLimits(768 * MIB, 300, 600.0)
#: The largest file the child may write (``RLIMIT_FSIZE``).
OUTPUT_LIMIT_BYTES: Final[int] = 64 * MIB


class PdfFailed(RuntimeError):
    """The child ended without a PDF: ``end`` is the class of the end (``overrun``, ``cpu``, ``wall``, ``signal:…``, ``error:…``, ``exit``)."""

    def __init__(self, end: str) -> None:
        super().__init__(f"the PDF child ended without a result: {end}")
        self.end = end


@dataclass(frozen=True, slots=True)
class PdfResult:
    """The PDF and what the child's check found in it: ``problems`` empty means the file passed (A4, the font embedded, the label and the
    recall line on every page, every transition in the text, nothing of the service in it)."""

    content: bytes
    pages: int
    wall_s: float
    max_rss_kib: int
    problems: tuple[str, ...] = ()


def pdf_runner() -> SubprocessChildRunner:
    return SubprocessChildRunner(program=PROGRAM)


def write_pdf(
    document: Mapping[str, Any], *, runner: ChildRunner | None = None, limits: ChildLimits = PDF_LIMITS,
    font_dir: Path = FONT_DIR, output_limit: int = OUTPUT_LIMIT_BYTES,
) -> PdfResult:
    """The PDF of ``document`` (see ``render.py``), written by the child. Raises :class:`PdfFailed` for an end without a result and
    :class:`~auditmanager.comparison.profile.runner.ChildStartError` when the child never started."""
    with tempfile.TemporaryDirectory(prefix="cmp-report-") as directory:
        base = Path(directory)
        source, target = base / "document.json", base / "report.pdf"
        source.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
        result: ChildResult = (runner or pdf_runner()).run({
            "input_path": str(source), "output_path": str(target), "font_dir": str(font_dir), "file_bytes": output_limit,
        }, limits)
        if not result.ok:
            raise PdfFailed(result.end)
        if not target.is_file():
            raise PdfFailed("error:NoOutput")
        content = target.read_bytes()
    pages = int(result.facts.get("pages") or 0)
    if not content.startswith(b"%PDF-") or pages < 1:
        raise PdfFailed("error:NotAPdf")
    return PdfResult(
        content=content, pages=pages, wall_s=result.wall_s, max_rss_kib=result.max_rss_kib,
        problems=tuple(str(p) for p in result.facts.get("problems") or ()),
    )
