"""Start one page-profile child under its ceilings, wait for it with a wall clock, classify its end.

`CMP-PROFILE-01`, ADR-0025 decision 8 and the addendum of 2026-10-27. The technique is the one the
measurement (`tools/measure/comparison_render.py`, `MEASURE-RENDER-01`) used for 642 children and the
one `ingest/envelope.py::_run_reader` uses for the upload reader: the child is a program
(:mod:`.child.program`) started with ``python -I -B``, a bare environment and ``/`` as its working
directory; it sets its own kernel ceilings before it loads anything; the parent reads JSON lines from
its standard output, adds a wall clock, signals **only that child, by its PID**, and reaps it with
``wait4`` (so the child's peak resident set and CPU time are the kernel's, not the child's word).

How an end is classified (:attr:`ChildResult.status`)
-----------------------------------------------------
``ok``, ``refused`` (the page is over the pixel cap) and ``range`` (the tile is not in the pyramid) are
answers. ``overrun`` (a ``MemoryError``), ``cpu`` (the CPU ceiling's signal), ``wall`` (the clock ran out
and the child was killed), ``signal:NAME`` (PDFium aborts with ``SIGABRT`` or ``SIGTRAP`` below its
need) and ``error:TYPE`` are ends **without a result**, and the caller maps every one of them to
``RENDER_FAILED`` for that item. A child that dies before it wrote ``limits_set`` never reached the
page: that is ``no_start``, a fault of the server (:class:`ChildStartError`), not a verdict on the page.
"""

from __future__ import annotations

import json
import os
import selectors
import signal
import subprocess
import sys
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final, Protocol

from auditmanager.comparison.profile.limits import FILE_BYTES, ChildLimits

__all__ = [
    "PROGRAM",
    "ChildResult",
    "ChildRunner",
    "ChildStartError",
    "SubprocessChildRunner",
]

#: The program every child runs.
PROGRAM: Final[Path] = Path(__file__).with_name("child") / "program.py"
#: The child's environment: nothing of the worker's, which holds the deployment's secrets.
_ENVIRONMENT: Final[dict[str, str]] = {"PATH": os.defpath, "LANG": "C.UTF-8", "PYTHONHASHSEED": "0"}
_SIGNAL_NAMES: Final[dict[int, str]] = {int(number): number.name for number in signal.Signals}
_ENDS_WITHOUT_RESULT: Final[tuple[str, ...]] = ("overrun", "cpu", "wall")


class ChildStartError(RuntimeError):
    """The child never reached the page (it died before its limits were set): the server's fault."""


@dataclass(frozen=True, slots=True)
class ChildResult:
    status: str
    facts: Mapping[str, Any] = field(default_factory=dict)
    stage: str | None = None
    wall_s: float = 0.0
    cpu_s: float = 0.0
    max_rss_kib: int = 0

    @property
    def ok(self) -> bool:
        return self.status == "ok"

    @property
    def answered(self) -> bool:
        """The child gave an answer about the page (ok, refused, range); every other end is a failure."""
        return self.status in ("ok", "refused", "range")

    @property
    def end(self) -> str:
        """The class of an end without a result, for the operator (never page content)."""
        if self.status.startswith(("signal:", "error:")) or self.status in _ENDS_WITHOUT_RESULT:
            return self.status
        return "exit"


class ChildRunner(Protocol):
    """What the builder and the tile path need of a runner (a test can supply its own)."""

    def run(self, settings: Mapping[str, Any], limits: ChildLimits) -> ChildResult: ...


class SubprocessChildRunner:
    """Starts :data:`PROGRAM` with ``sys.executable``; one child at a time per call."""

    def __init__(self, program: Path = PROGRAM, python: str | None = None) -> None:
        self._program = program
        self._python = python or sys.executable

    def run(self, settings: Mapping[str, Any], limits: ChildLimits) -> ChildResult:
        full = dict(settings)
        full["address_space"] = limits.address_space
        full["cpu_seconds"] = limits.cpu_seconds
        full.setdefault("file_bytes", FILE_BYTES)
        began = time.monotonic()
        child = subprocess.Popen(  # noqa: S603 - a fixed argument vector, no shell
            [self._python, "-I", "-B", str(self._program), json.dumps(full)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=_ENVIRONMENT,
            cwd="/",
            close_fds=True,
        )
        pid = child.pid
        selector = selectors.DefaultSelector()
        selector.register(child.stdout, selectors.EVENT_READ)  # type: ignore[arg-type]
        chunks: list[bytes] = []
        timed_out = False
        try:
            while True:
                remaining = limits.wall_seconds - (time.monotonic() - began)
                if remaining <= 0:
                    timed_out = True
                    os.kill(pid, signal.SIGKILL)  # this child, by its own PID, and only this one
                    break
                if selector.select(timeout=min(remaining, 5.0)):
                    data = os.read(child.stdout.fileno(), 65536)  # type: ignore[union-attr]
                    if not data:
                        break
                    chunks.append(data)
            if timed_out:
                try:
                    while True:
                        data = os.read(child.stdout.fileno(), 65536)  # type: ignore[union-attr]
                        if not data:
                            break
                        chunks.append(data)
                except OSError:
                    pass
        except BaseException:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            os.wait4(pid, 0)
            child.returncode = 0
            child.stdout.close()  # type: ignore[union-attr]
            selector.close()
            raise
        _, wait_status, usage = os.wait4(pid, 0)
        child.returncode = 0  # reaped here, not by Popen
        wall = time.monotonic() - began
        child.stdout.close()  # type: ignore[union-attr]
        selector.close()
        return _classify(chunks, wait_status, timed_out, wall, usage)


def _classify(chunks: list[bytes], wait_status: int, timed_out: bool, wall: float, usage: Any) -> ChildResult:
    final: dict[str, Any] | None = None
    stage: str | None = None
    started = False
    for line in b"".join(chunks).decode("utf-8", "replace").splitlines():
        if not line.startswith("{"):
            continue
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if "status" in item:
            final = item
        elif "stage" in item:
            stage = str(item["stage"])
            started = started or stage == "limits_set"
    common = {
        "stage": stage,
        "wall_s": round(wall, 3),
        "cpu_s": round(usage.ru_utime + usage.ru_stime, 3),
        "max_rss_kib": int(usage.ru_maxrss),
    }
    if not started:
        raise ChildStartError("the page-profile child did not start")
    if timed_out:
        return ChildResult("wall", **common)
    if final is not None:
        status = str(final.pop("status"))
        return ChildResult(status, facts=final, **common)
    if os.WIFSIGNALED(wait_status):
        number = os.WTERMSIG(wait_status)
        return ChildResult("cpu" if number == signal.SIGXCPU else f"signal:{_SIGNAL_NAMES.get(number, number)}", **common)
    return ChildResult(f"exit:{os.WEXITSTATUS(wait_status)}", **common)
