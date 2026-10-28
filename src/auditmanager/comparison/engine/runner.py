"""Start the engine's child under its ceilings (the runner of the page-profile child, another program).

`CMP-ENGINE-01`. :class:`~auditmanager.comparison.profile.runner.SubprocessChildRunner` starts a program with a bare
environment and ``/`` as its working directory, waits with a wall clock, signals only its own child by its PID and reads
the end from the kernel's wait status; it is given the engine's program here. A test may supply any object with
``run(settings, limits) -> ChildResult``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from auditmanager.comparison.profile.runner import ChildResult, ChildRunner, ChildStartError, SubprocessChildRunner

__all__ = ["PROGRAM", "ChildResult", "ChildRunner", "ChildStartError", "engine_runner"]

PROGRAM: Final[Path] = Path(__file__).with_name("child") / "program.py"


def engine_runner() -> SubprocessChildRunner:
    return SubprocessChildRunner(program=PROGRAM)
