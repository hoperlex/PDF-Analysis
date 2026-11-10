"""The directory the worker and the host's timer meet in (`ADR-0029` decision 8, plan-v5 section 5).

The container that encodes has **no database and no network**; the worker that has the database does not run docker. So the two never speak
directly: they leave files for each other in one directory (a named volume of the stack, ``/embed`` in the worker, in the container and, by its
mountpoint, for ``infra/deploy/embed-window.sh``). The files are the whole protocol:

==================  =============  ===================================================================================================
``request.json``    worker         the batch for the encoder (:func:`~auditmanager.precedents.vectors.intents.build_request`)
``deadline``        worker         the window's close, in epoch seconds; the host stops the container at it (written before the request)
``response.json``   container      the vectors (``auditmanager-embed-texts/1``)
``over_limit.json`` container      the texts it set aside for their length
``result``          host           ``exit_code=<n>`` and ``finished_epoch=<n>``: the container ended; written after the other files
``stderr.log``      host           the tail of what the container said, for the log
``abort``           worker         stop the container now (a pause, or the window ended)
``heartbeat``       host           ``epoch=<n>``: the timer ran; the worker opens no window for a host that is silent
==================  =============  ===================================================================================================

Every file the worker writes is written whole and renamed into place, so the host never reads half of a request. The worker is the only one
that removes the files of a round (:meth:`Exchange.clear`); the host removes nothing but its own stale ``result`` when it starts a new round.
"""

from __future__ import annotations

import contextlib
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Final

__all__ = ["EXCHANGE_DIR_ENV", "HEARTBEAT_FRESH_SECONDS", "Exchange", "HostResult"]

#: The environment name the worker reads the directory from. Unset means the night encoder is not set up on this process and its pass does
#: nothing (a development machine, the API): the stack names it for the worker only.
EXCHANGE_DIR_ENV: Final[str] = "AUDITMANAGER_EMBED_DIR"
#: How old the host's heartbeat may be. The timer fires every minute; ten minutes of silence is a timer that is off, not one that is late.
HEARTBEAT_FRESH_SECONDS: Final[int] = 600
_REQUEST: Final[str] = "request.json"
_DEADLINE: Final[str] = "deadline"
_RESPONSE: Final[str] = "response.json"
_OVER_LIMIT: Final[str] = "over_limit.json"
_RESULT: Final[str] = "result"
_STDERR: Final[str] = "stderr.log"
_ABORT: Final[str] = "abort"
_HEARTBEAT: Final[str] = "heartbeat"
_ROUND_FILES: Final[tuple[str, ...]] = (_REQUEST, _DEADLINE, _RESPONSE, _OVER_LIMIT, _RESULT, _STDERR, _ABORT)


@dataclass(frozen=True, slots=True)
class HostResult:
    """What the host wrote when the container ended: the exit status (0 done; 124 stopped at the deadline; 137 killed, normally at the memory
    limit; 125-127 the container did not start) and when."""

    exit_code: int
    finished_epoch: int


def _atomic_write(path: Path, data: bytes) -> None:
    temporary = path.with_name(path.name + ".part")
    try:
        with temporary.open("wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        with contextlib.suppress(OSError):
            temporary.unlink()
        raise


def _read_assignments(path: Path) -> dict[str, str]:
    found: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        name, separator, value = line.partition("=")
        if separator:
            found[name.strip()] = value.strip()
    return found


class Exchange:
    """The files of one directory. It holds no state of its own: the directory is the state, so a restarted worker finds the round where it was."""

    def __init__(self, directory: Path) -> None:
        self._dir = directory

    @classmethod
    def from_environment(cls, environ: dict[str, str] | None = None) -> Exchange | None:
        """The exchange named by ``AUDITMANAGER_EMBED_DIR``, or ``None`` when the process is not set up for the night encoder."""
        raw = (os.environ if environ is None else environ).get(EXCHANGE_DIR_ENV, "").strip()
        return cls(Path(raw)) if raw else None

    @property
    def directory(self) -> Path:
        return self._dir

    def _path(self, name: str) -> Path:
        return self._dir / name

    # -- the worker's side ---------------------------------------------------------------------------------

    def has_request(self) -> bool:
        return self._path(_REQUEST).is_file()

    def write_request(self, request: dict[str, Any], *, deadline_epoch: int) -> None:
        """Hand a batch to the host: the deadline first, then the request, so a host that sees the request always sees its deadline.

        The files of an earlier round must be gone (:meth:`clear`): a stale ``result`` would be read as this round's."""
        if any(self._path(name).exists() for name in (_RESPONSE, _OVER_LIMIT, _RESULT, _ABORT)):
            raise FileExistsError("the exchange still holds the files of an earlier round; clear it first")
        _atomic_write(self._path(_DEADLINE), f"{int(deadline_epoch)}\n".encode("ascii"))
        _atomic_write(self._path(_REQUEST), (json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"))

    def request_abort(self) -> None:
        """Ask the host to stop the container now. Idempotent."""
        _atomic_write(self._path(_ABORT), b"abort\n")

    def clear(self) -> None:
        """Remove the files of the round. The heartbeat stays: it is the host's, not the round's."""
        for name in _ROUND_FILES:
            with contextlib.suppress(FileNotFoundError):
                self._path(name).unlink()

    def result(self) -> HostResult | None:
        """The host's account of the container, or ``None`` while it has none. A file that cannot be read is an error, not an absence."""
        path = self._path(_RESULT)
        if not path.is_file():
            return None
        values = _read_assignments(path)
        try:
            return HostResult(int(values["exit_code"]), int(values["finished_epoch"]))
        except (KeyError, ValueError) as exc:
            raise ValueError(f"{path} is not exit_code=<n> and finished_epoch=<n>") from exc

    def read_request(self) -> object | None:
        return self._read_json(_REQUEST)

    def read_response(self) -> object | None:
        return self._read_json(_RESPONSE)

    def read_over_limit(self) -> object | None:
        return self._read_json(_OVER_LIMIT)

    def _read_json(self, name: str) -> object | None:
        path = self._path(name)
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise ValueError(f"{path} is not JSON") from exc

    def stderr_tail(self, limit: int = 2000) -> str:
        path = self._path(_STDERR)
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")[-limit:]

    def heartbeat_age_seconds(self, now: datetime) -> float | None:
        """Seconds since the host's timer last ran, or ``None`` when it never has."""
        path = self._path(_HEARTBEAT)
        if not path.is_file():
            return None
        try:
            epoch = int(_read_assignments(path)["epoch"])
        except (KeyError, ValueError):
            return None
        return now.timestamp() - epoch
