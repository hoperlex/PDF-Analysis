#!/usr/bin/env python3
"""Resident-memory sampling of one process, and the control that proves the sampler sees memory.

    python scripts/rehearsal/w55b/sampler.py control [--mib 300]

``RssSampler`` reads ``VmRSS`` and ``VmHWM`` from ``/proc/<pid>/status`` every ``interval``
seconds on a thread, with a wall-clock timestamp per sample, so a peak can be read for any
interval of wall time (a stage's ``started_at``/``finished_at``) even when several phases run
in one process. The kernel's own high-water mark (``VmHWM``, reset by writing ``5`` to
``/proc/<pid>/clear_refs``) is the second, independent reading of the same peak: a sampler can
miss a spike shorter than its interval, the kernel cannot.

``control`` is the check that the instrument measures what it says: a child allocates and
touches a known number of MiB, holds them, frees them and exits; the sampler must see a rise of
that size (within 5 %) and the kernel's mark must agree. It writes ``figures/sampler-control.json``.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import common  # noqa: E402


@dataclass
class Sample:
    t: float          # time.time(), seconds since the epoch
    rss_kib: int
    hwm_kib: int


@dataclass
class RssSampler:
    pid: int
    interval: float = 0.25
    samples: list[Sample] = field(default_factory=list)
    _stop: threading.Event = field(default_factory=threading.Event)
    _thread: threading.Thread | None = None

    def _read(self) -> Sample | None:
        try:
            text = Path(f"/proc/{self.pid}/status").read_text()
        except OSError:
            return None
        rss = hwm = -1
        for line in text.splitlines():
            if line.startswith("VmRSS:"):
                rss = int(line.split()[1])
            elif line.startswith("VmHWM:"):
                hwm = int(line.split()[1])
        return Sample(time.time(), rss, hwm)

    def _loop(self) -> None:
        next_at = time.monotonic()
        while not self._stop.is_set():
            sample = self._read()
            if sample is None:
                return
            self.samples.append(sample)
            next_at += self.interval
            self._stop.wait(max(0.0, next_at - time.monotonic()))

    def start(self) -> "RssSampler":
        self._thread = threading.Thread(target=self._loop, name="rss-sampler", daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        last = self._read()
        if last is not None:
            self.samples.append(last)

    def window(self, start: float, end: float) -> list[Sample]:
        return [s for s in self.samples if start <= s.t <= end]

    def peak_between(self, start: float, end: float) -> dict[str, int | float | None]:
        inside = self.window(start, end)
        before = [s for s in self.samples if s.t < start]
        if not inside:
            return {"samples": 0, "peak_rss_kib": None, "rss_at_start_kib": None}
        first = before[-1] if before else inside[0]
        peak = max(inside, key=lambda s: s.rss_kib)
        return {
            "samples": len(inside),
            "rss_at_start_kib": first.rss_kib,
            "peak_rss_kib": peak.rss_kib,
            "peak_growth_kib": peak.rss_kib - first.rss_kib,
            "peak_at": peak.t,
            "rss_at_end_kib": inside[-1].rss_kib,
        }

    def series(self) -> list[list[float | int]]:
        return [[round(s.t, 3), s.rss_kib, s.hwm_kib] for s in self.samples]


_CHILD = """
import time
time.sleep(1.5)
block = b"\\x01" * ({mib} * 1024 * 1024)   # filled, so every page is touched
time.sleep(2.0)
del block
time.sleep(1.5)
"""


def control(mib: int) -> int:
    common.ensure_out()
    child = subprocess.Popen([sys.executable, "-c", _CHILD.format(mib=mib)])
    try:
        time.sleep(0.3)
        common.reset_peak(child.pid)
        hwm_before = common.vm_kib(child.pid, "VmHWM")
        sampler = RssSampler(child.pid).start()
        child.wait(timeout=60)
        sampler.stop()
    finally:
        if child.poll() is None:
            child.kill()
    rss = [s.rss_kib for s in sampler.samples if s.rss_kib >= 0]
    hwm = [s.hwm_kib for s in sampler.samples if s.hwm_kib >= 0]
    baseline = rss[0]
    peak = max(rss)
    rise_mib = (peak - baseline) / 1024
    hwm_rise_mib = (max(hwm) - hwm_before) / 1024
    after = rss[-1]
    within = abs(rise_mib - mib) <= 0.05 * mib and abs(hwm_rise_mib - mib) <= 0.05 * mib
    freed = (after - baseline) / 1024 < 0.25 * mib
    common.write_figures("sampler-control", {
        "method": "a child allocates and touches a known size, holds 2 s, frees; RSS sampled every 0.25 s",
        "allocated_mib": mib,
        "samples": len(rss),
        "baseline_rss_kib": baseline,
        "peak_rss_kib": peak,
        "sampled_rise_mib": round(rise_mib, 1),
        "kernel_hwm_rise_mib": round(hwm_rise_mib, 1),
        "rss_after_free_kib": after,
        "rise_within_5_percent": within,
        "memory_returned_after_free": freed,
    })
    print(f"control: allocated {mib} MiB; sampled rise {rise_mib:.1f} MiB; kernel mark rise "
          f"{hwm_rise_mib:.1f} MiB; after free {(after - baseline) / 1024:.1f} MiB over baseline")
    if not (within and freed):
        print("control: FAILED - the sampler does not see the allocation", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    ctl = sub.add_parser("control", help="prove the sampler against a known allocation")
    ctl.add_argument("--mib", type=int, default=300)
    args = parser.parse_args(argv)
    if args.command == "control":
        return control(args.mib)
    return 2


if __name__ == "__main__":
    sys.exit(main())
