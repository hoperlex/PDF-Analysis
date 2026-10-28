"""The engine's child: a program of its own, under limits the kernel enforces.

`CMP-ENGINE-01`, ADR-0025 decision 8 and the addendum of 2026-10-27. The worker starts this file as
``python -I -B program.py '<settings json>'`` with :class:`~auditmanager.comparison.profile.runner.SubprocessChildRunner`
(the technique of the page-profile child, which this file follows line for line), one **pair** of pages per child, and
reads one answer from its standard output. The address space, the CPU time and the size of any file written are
ceilings the kernel holds (768 MiB, 300 s, and the parent's wall clock of 600 s): a pair that needs more ends without a
result, and the parent stores it as ``needs_review`` with reason ``RENDER_FAILED``, never as «Совпадает».

**Nothing from the product is imported.** Started with ``-I``, no environment variable, user site or working directory
reaches the import path. After the ceilings are set the directory of this file is loaded as a package under a private
name (``_amc_engine``) and the mask codec that lies beside it is loaded beside that package; both import only the
standard library, ``numpy``, ``cv2`` and ``pypdfium2``.

The thread pools are shut before ``numpy`` is imported: with the defaults an import of ``numpy`` and ``cv2`` reserves
about 1.5 GiB of address space (a thread arena for each core), which is more than the whole ceiling.

The protocol is that of the page-profile child: JSON lines on standard output, ``{"stage": "limits_set"}`` once the
ceilings are in force, then one line with ``"status"``: ``ok`` with the job's facts and ``VmPeak`` / ``VmHWM`` /
``VmRSS`` in KiB, ``overrun`` (a ``MemoryError``), ``refused`` (the canvas passes the 40 Mpx cap), or ``error:T``.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import os
import resource
import sys
from typing import Any

EXIT_OVERRUN = 3
EXIT_ERROR = 4
EXIT_REFUSED = 5

for _name in (
    "OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS",
    "OPENCV_FOR_THREADS_NUM",
):
    os.environ[_name] = "1"
os.environ["OPENCV_OPENCL_RUNTIME"] = "disabled"


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


def _load(name: str, path: str, *, package_dir: str | None = None) -> Any:
    spec = importlib.util.spec_from_file_location(
        name, path, submodule_search_locations=[package_dir] if package_dir else None
    )
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
        _load("_amc_engine", os.path.join(here, "__init__.py"), package_dir=here)
        _load("_amc_engine._mask_codec", os.path.join(os.path.dirname(here), "mask_codec.py"))
        job = importlib.import_module("_amc_engine.job")
        facts = job.run(settings)
    except MemoryError:
        _say({"status": "overrun", "reason": "MemoryError", **_proc_status()})
        return EXIT_OVERRUN
    except Exception as failure:  # noqa: BLE001 - reported to the parent as data
        if _wraps_memory_error(failure):
            _say({"status": "overrun", "reason": "MemoryError", **_proc_status()})
            return EXIT_OVERRUN
        if getattr(failure, "reason", None) == "PAGE_TOO_LARGE":
            _say({"status": "refused", "reason": "PAGE_TOO_LARGE", **_proc_status()})
            return EXIT_REFUSED
        _say({"status": f"error:{type(failure).__name__}", **_proc_status()})
        return EXIT_ERROR
    _say({"status": "ok", **facts, **_proc_status()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
