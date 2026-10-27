"""The page-profile child: a program of its own, under limits the kernel enforces.

`CMP-PROFILE-01`, ADR-0025 decision 8 and the addendum of 2026-10-27. The worker starts this file as
``python -I -B program.py '<settings json>'`` (:mod:`auditmanager.comparison.profile.runner`), one
page per child, and reads one answer from its standard output. It is a program and not a function
because what a page does to PDFium and ``pdfplumber`` cannot be bounded from inside the process that
asks for it (`W55B-JUDGE-X` X-1, the precedent of ``ingest/pdf_reader.py``): here the address space,
the CPU time and the size of any file written are ceilings the kernel holds, and the parent adds a
wall clock.

**Nothing from the product is imported**: a crash of PDFium here is the crash of this process only.
Started with ``-I``, no environment variable, user site or working directory reaches its import
path; after the ceilings are set, this file's own directory is appended to ``sys.path`` (last, so
that it can shadow nothing) for the job modules beside it. It writes only into the output directory
named in its settings and receives no secret (the worker starts it with a bare environment).

The protocol
------------
* argument 1: the settings, one JSON object (``mode``, the ceilings, the job's own values);
* standard output, JSON lines: ``{"stage": ...}`` progress marks, the first of which,
  ``limits_set``, is written once the ceilings are in force (a process that dies before it is a
  fault of the server, one that dies after it was stopped by the page), and one last line that
  carries ``"status"``:

  ============  ======================================================================
  ``ok``        the job's facts, and ``VmPeak`` / ``VmHWM`` / ``VmRSS`` in KiB
  ``overrun``   a ``MemoryError`` (also one wrapped by a library's own exception)
  ``refused``   :class:`PageRefused`: the page is over the pixel cap (``reason``)
  ``range``     :class:`TileOutOfRange`: the tile is not in the pyramid
  ``error:T``   any other exception, ``T`` its class name (no message: it can quote the page)
  ============  ======================================================================

A child that ends by a signal (PDFium aborts with ``SIGABRT`` or ``SIGTRAP`` below its need) or by
the CPU ceiling writes no last line; the parent maps every such end to ``RENDER_FAILED``.
"""

from __future__ import annotations

import importlib
import json
import os
import resource
import sys
from typing import Any

EXIT_OVERRUN = 3
EXIT_ERROR = 4
EXIT_REFUSED = 5
EXIT_RANGE = 6

_JOBS = {"extract": "extract_job", "render": "render_job", "tile": "tile_job"}


def _limit(settings: dict[str, Any]) -> None:
    """The kernel's ceilings on this process, set before anything else is loaded."""
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    address_space = int(settings["address_space"])
    resource.setrlimit(resource.RLIMIT_AS, (address_space, address_space))
    cpu_seconds = int(settings["cpu_seconds"])
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1))
    # Whatever a job writes, it writes into its own output directory and no more than this.
    file_bytes = int(settings["file_bytes"])
    resource.setrlimit(resource.RLIMIT_FSIZE, (file_bytes, file_bytes))


def _say(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def _proc_status() -> dict[str, int]:
    wanted = {"VmPeak": "vm_peak_kib", "VmHWM": "vm_hwm_kib", "VmRSS": "vm_rss_kib"}
    found: dict[str, int] = {}
    try:
        with open("/proc/self/status", encoding="ascii") as handle:
            for line in handle:
                key, _, rest = line.partition(":")
                if key in wanted:
                    found[wanted[key]] = int(rest.split()[0])
    except OSError:
        pass
    return found


def _wraps_memory_error(failure: BaseException) -> bool:
    """Whether a ``MemoryError`` is the failure itself, its cause or context, or one of its arguments
    (``pdfplumber`` re-raises whatever ``pdfminer`` raised as ``PdfminerException(original)``)."""
    seen: set[int] = set()
    pending: list[Any] = [failure]
    while pending:
        item = pending.pop()
        if id(item) in seen:
            continue
        seen.add(id(item))
        if isinstance(item, MemoryError):
            return True
        if isinstance(item, BaseException):
            pending.extend([item.__cause__, item.__context__, *item.args])
    return False


def main(argv: list[str]) -> int:
    settings = json.loads(argv[1])
    _limit(settings)
    _say({"stage": "limits_set"})
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import geometry  # noqa: PLC0415 - after the ceilings

    try:
        job = importlib.import_module(_JOBS[str(settings["mode"])])
        facts = job.run(settings)
    except MemoryError:
        _say({"status": "overrun", "reason": "MemoryError", **_proc_status()})
        return EXIT_OVERRUN
    except geometry.PageRefused as refusal:
        _say(
            {
                "status": "refused",
                "reason": refusal.reason,
                "width_pt": round(refusal.width_pt, 2),
                "height_pt": round(refusal.height_pt, 2),
                **_proc_status(),
            }
        )
        return EXIT_REFUSED
    except geometry.TileOutOfRange as miss:
        _say({"status": "range", "reason": str(miss), **_proc_status()})
        return EXIT_RANGE
    except Exception as failure:  # noqa: BLE001 - reported to the parent as data
        if _wraps_memory_error(failure):
            _say({"status": "overrun", "reason": "MemoryError", **_proc_status()})
            return EXIT_OVERRUN
        _say({"status": f"error:{type(failure).__name__}", **_proc_status()})
        return EXIT_ERROR
    _say({"status": "ok", **facts, **_proc_status()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
