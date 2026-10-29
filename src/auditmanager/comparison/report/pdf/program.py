"""The report PDF's child: a program of its own, under limits the kernel enforces (`CMP-VC-REPORT-01`, ADR-0025 decision 8).

The worker starts this file as ``python -I -B program.py '<settings json>'`` with
:class:`~auditmanager.comparison.profile.runner.SubprocessChildRunner` (the technique of the page-profile and engine children, which this file
follows line for line), one report per child, and reads one answer from its standard output. The address space (768 MiB), the CPU time (300 s)
and the size of any file written (the settings' ``file_bytes``) are ceilings the kernel holds; the parent's wall clock (600 s) is the fourth. A
report that needs more ends without a result, and the parent stores the failure of that report -- never a half-written PDF.

**Nothing from the product is imported.** Started with ``-I``, no environment variable, user site or working directory reaches the import
path; after the ceilings are set, ``render.py`` that lies beside this file is loaded by path under a private name (``_cmp_report_render``), and
it imports the standard library and reportlab only. The input is a JSON file the parent wrote (``input_path``), the output a PDF at
``output_path``; the settings hold paths and numbers, not the report.

The protocol is that of the other children: JSON lines on standard output, ``{"stage": "limits_set"}`` once the ceilings are in force, then one
line with ``"status"``: ``ok`` with the number of pages and the size of the file and ``VmPeak`` / ``VmHWM`` / ``VmRSS`` in KiB, ``overrun`` (a
``MemoryError``), or ``error:T``.
"""

from __future__ import annotations

import importlib.util
import json
import os
import resource
import sys
from typing import Any

EXIT_OVERRUN = 3
EXIT_ERROR = 4


def _limit(settings: dict[str, Any]) -> None:
    """The kernel's ceilings on this process, set before anything else is loaded."""
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    address_space = int(settings["address_space"])
    resource.setrlimit(resource.RLIMIT_AS, (address_space, address_space))
    cpu_seconds = int(settings["cpu_seconds"])
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1))
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


def _load(name: str, path: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main(argv: list[str]) -> int:
    settings = json.loads(argv[1])
    _limit(settings)
    _say({"stage": "limits_set"})
    here = os.path.dirname(os.path.abspath(__file__))
    try:
        render = _load("_cmp_report_render", os.path.join(here, "render.py"))
        with open(settings["input_path"], encoding="utf-8") as handle:
            document = json.load(handle)
        pages = render.render(document, settings["output_path"], font_dir=settings["font_dir"])
        size = os.path.getsize(settings["output_path"])
    except MemoryError:
        _say({"status": "overrun", "reason": "MemoryError", **_proc_status()})
        return EXIT_OVERRUN
    except Exception as failure:  # noqa: BLE001 - reported to the parent as data
        if _wraps_memory_error(failure):
            _say({"status": "overrun", "reason": "MemoryError", **_proc_status()})
            return EXIT_OVERRUN
        _say({"status": f"error:{type(failure).__name__}", **_proc_status()})
        return EXIT_ERROR
    _say({"status": "ok", "pages": pages, "bytes": size, **_proc_status()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
