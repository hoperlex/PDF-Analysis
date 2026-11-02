"""Starting a ceilinged child over a PDF's file descriptor, for the comparison readers.

:func:`auditmanager.ingest.envelope._run_reader` is this function with the portal envelope's wall clock fixed in
the module (60 s). The comparison policy has its own clock (:data:`~auditmanager.ingest.comparison_pdf.envelope`),
and that module is not this lane's to change, so the launcher is restated here with the clock as a parameter and
nothing else different: the same bare environment, ``python -I -B``, a descriptor passed by number, a first line
``ready`` that separates a server fault (the process never reached the document) from a stop by the document (it
ran out of time, ran out of memory or was killed by a signal), and one JSON answer.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any, BinaryIO, Final

from auditmanager.ingest import envelope as _portal
from auditmanager.shared.errors import DomainError

__all__ = ["descriptor_of", "run_child"]

_READY: Final[str] = "ready"
_READER_ENVIRONMENT: Final[dict[str, str]] = {"PATH": os.defpath}
_COPY_PIECE: Final[int] = 1024 * 1024


@contextlib.contextmanager
def descriptor_of(handle: BinaryIO) -> Iterator[int]:
    """A descriptor on a regular file holding the handle's bytes, for the child to inherit.

    A handle on a regular file is passed as it is; anything else is copied into an anonymous temporary file a piece
    at a time (the same rule as the portal envelope's ``_descriptor_of``).
    """
    descriptor = _regular_file_descriptor(handle)
    if descriptor is not None:
        yield descriptor
        return
    with tempfile.TemporaryFile() as spool:
        buffer = bytearray(_COPY_PIECE)
        view = memoryview(buffer)
        handle.seek(0)
        while True:
            count = handle.readinto(view)
            if not count:
                break
            spool.write(view[:count])
        spool.flush()
        yield spool.fileno()


def _regular_file_descriptor(handle: BinaryIO) -> int | None:
    fileno = getattr(handle, "fileno", None)
    if not callable(fileno):
        return None
    try:
        descriptor = int(fileno())
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            return None
    except (OSError, ValueError, io.UnsupportedOperation):
        return None
    flush = getattr(handle, "flush", None)
    if callable(flush):
        flush()
    return descriptor


def run_child(
    program: Path, descriptor: int, settings: dict[str, Any], *, wall_seconds: int
) -> dict[str, Any]:
    """Run ``program`` with ``settings`` over ``descriptor`` and return its one answer.

    A child that does not say ``ready`` is a server fault (:class:`RuntimeError`). One that said it and then ran
    out of time, ran out of memory or was killed by a signal was stopped by the document: the portal's own
    ``pdf_reader_limits`` refusal.
    """
    child = subprocess.Popen(
        [sys.executable, "-I", "-B", str(program), json.dumps(settings)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        pass_fds=(descriptor,),
        cwd="/",
        env=_READER_ENVIRONMENT,
    )
    timed_out = False
    try:
        output, _ = child.communicate(timeout=wall_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        child.kill()
        output, _ = child.communicate()
    except BaseException:
        child.kill()
        child.wait()
        raise
    lines = output.decode("ascii", errors="replace").splitlines()
    if not lines or lines[0] != _READY:
        raise RuntimeError(
            "the PDF reader process did not start"
            + (" within its time" if timed_out else f" (exit status {child.returncode})")
        )
    if timed_out or child.returncode != 0 or len(lines) < 2:
        raise _limits_refusal()
    try:
        answer = json.loads(lines[1])
    except ValueError:
        raise RuntimeError("the PDF reader process answered something else") from None
    if not isinstance(answer, dict):
        raise RuntimeError("the PDF reader process answered something else")
    return answer


def _limits_refusal() -> DomainError:
    return _portal._reader_limits_refusal()  # noqa: SLF001
