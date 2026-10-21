"""Temporaries a killed process left behind, reclaimed when the next one starts.

`RUN-ROBUSTNESS-01`, D-170.

Three places write a large temporary file or directory and remove it with a context manager:

* ``source_preparation`` streams the source PDF to ``am-source-<random>.pdf``;
* ``page_geometry_extraction`` streams it again to ``am-geometry-<random>.pdf``;
* the upload's archive reader unpacks a bundle into ``auditmanager-bundle-<random>/``.

A context manager never runs when the process is killed. `W55B-REHEARSAL-01` §4.2.9 found one
45 MB ``am-source-*.pdf`` per memory kill; on the stand a PDF is up to 250 MiB and a kill leaves
one in the container's writable layer for good. :func:`sweep_stale_temporaries` reclaims them
when a worker or an API process starts.

What makes it safe to delete in a directory other things write to:

* **only the three exact names** -- :data:`FILE_NAME` and :data:`DIRECTORY_NAME` match what the
  producers' ``mkstemp``/``TemporaryDirectory`` write, random part included; nothing else in
  the directory is looked at, and a name that merely starts alike is not matched;
* **only what is old** -- older than :data:`STALE_AFTER_SECONDS`, which is the attempt watchdog
  plus a minute. A file is made after its attempt was claimed, and the watchdog
  (``jobs.lease.ATTEMPT_WATCHDOG_SECONDS``) fences the attempt that long after the claim, so an
  older file belongs to an attempt that no longer holds authority: its results cannot be
  published, and a thread of it still reading the file keeps its open descriptor. Age is the
  later of the modification and the change time (a file touched, renamed or chmod-ed is
  young), and a directory is as young as its youngest member;
* **only a regular file or a real directory, owned by this user** -- a symbolic link of that
  name is never followed and never removed, and neither is a file of another user;
* **never an error** -- a name that vanished, a permission that is missing or a directory that
  cannot be read is logged and skipped. Reclaiming disk must not stop a process from starting.

It does not sweep the web server's multipart spool: Starlette names those ``tmp`` plus random
characters, which no exact prefix can tell from anyone's file.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import stat
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from auditmanager.jobs.lease import ATTEMPT_WATCHDOG_SECONDS

__all__ = [
    "DIRECTORY_NAME",
    "FILE_NAME",
    "STALE_AFTER_SECONDS",
    "SweepReport",
    "sweep_stale_temporaries",
]

_log = logging.getLogger(__name__)

#: ``tempfile`` names the random part of ``mkstemp``/``mkdtemp`` with eight characters of
#: ``[a-z0-9_]``; the pattern is written for ``[A-Za-z0-9_]`` so a different alphabet in a
#: later interpreter cannot make it miss a file.
_RANDOM: Final[str] = r"[A-Za-z0-9_]{8}"
#: ``am-source-<random>.pdf`` (``analysis.stages.source_preparation``) and
#: ``am-geometry-<random>.pdf`` (``analysis.geometry.source_file``).
FILE_NAME: Final[re.Pattern[str]] = re.compile(rf"^am-(?:source|geometry)-{_RANDOM}\.pdf$")
#: ``auditmanager-bundle-<random>`` (``ingest.bundle_archive``).
DIRECTORY_NAME: Final[re.Pattern[str]] = re.compile(rf"^auditmanager-bundle-{_RANDOM}$")

#: Older than the attempt watchdog by a minute (the lease length). See the module docstring.
STALE_AFTER_SECONDS: Final[float] = float(ATTEMPT_WATCHDOG_SECONDS + 60)

#: A bundle directory holds at most eight members; this bounds the walk of a directory that
#: holds something else.
_MAX_ENTRIES_WALKED: Final[int] = 10_000


@dataclass(frozen=True, slots=True)
class SweepReport:
    """What one sweep did. ``removed`` and ``failed`` hold names, never paths or contents."""

    removed: tuple[str, ...] = ()
    bytes_freed: int = 0
    failed: tuple[str, ...] = ()


def _newest(path: str, status: os.stat_result) -> float:
    """The latest modification or change time of ``path``, and of everything inside a directory.

    Never follows a link. A directory that cannot be read counts as young: not provably old.
    """
    newest = max(status.st_mtime, status.st_ctime)
    if not stat.S_ISDIR(status.st_mode):
        return newest
    walked = 0
    pending = [path]
    while pending:
        current = pending.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    walked += 1
                    if walked > _MAX_ENTRIES_WALKED:
                        return float("inf")
                    inner = entry.stat(follow_symlinks=False)
                    newest = max(newest, inner.st_mtime, inner.st_ctime)
                    if stat.S_ISDIR(inner.st_mode):
                        pending.append(entry.path)
        except OSError:
            return float("inf")
    return newest


def _size_of(path: str, status: os.stat_result) -> int:
    if not stat.S_ISDIR(status.st_mode):
        return int(status.st_size)
    total = 0
    for root, _directories, files in os.walk(path, followlinks=False):
        for name in files:
            try:
                total += os.lstat(os.path.join(root, name)).st_size
            except OSError:
                continue
    return total


def sweep_stale_temporaries(
    *,
    directory: str | os.PathLike[str] | None = None,
    now: float | None = None,
    older_than: float = STALE_AFTER_SECONDS,
) -> SweepReport:
    """Remove the stale temporaries of killed stages and uploads from ``directory``.

    ``directory`` is the process's temporary directory unless given; ``now`` is the wall clock
    unless given (a test passes its own). Returns what was removed; never raises.
    """
    base = Path(tempfile.gettempdir() if directory is None else directory)
    moment = time.time() if now is None else now
    removed: list[str] = []
    failed: list[str] = []
    freed = 0
    try:
        listing = list(os.scandir(base))
    except OSError:
        _log.warning("the temporary directory could not be read; nothing was reclaimed")
        return SweepReport()
    owner = os.geteuid()
    for entry in listing:
        name = entry.name
        try:
            if FILE_NAME.match(name):
                wanted = FILE_NAME
            elif DIRECTORY_NAME.match(name):
                wanted = DIRECTORY_NAME
            else:
                continue
            status = entry.stat(follow_symlinks=False)
            if status.st_uid != owner:
                continue
            # `follow_symlinks=False` above: a link has the mode of a link, which is neither
            # a regular file nor a directory, so a link of either name is skipped here.
            if wanted is FILE_NAME and not stat.S_ISREG(status.st_mode):
                continue
            if wanted is DIRECTORY_NAME and not stat.S_ISDIR(status.st_mode):
                continue
            if moment - _newest(entry.path, status) <= older_than:
                continue
            size = _size_of(entry.path, status)
            if wanted is DIRECTORY_NAME:
                shutil.rmtree(entry.path)
            else:
                os.unlink(entry.path)
            removed.append(name)
            freed += size
        except FileNotFoundError:
            continue  # another process reclaimed it first
        except OSError as failure:
            failed.append(name)
            _log.warning("stale temporary %s could not be removed (%s)", name, type(failure).__name__)
    if removed:
        _log.info(
            "reclaimed %d stale temporar%s (%d bytes) left by killed processes",
            len(removed), "y" if len(removed) == 1 else "ies", freed,
        )
    return SweepReport(
        removed=tuple(sorted(removed)), bytes_freed=freed, failed=tuple(sorted(failed))
    )
