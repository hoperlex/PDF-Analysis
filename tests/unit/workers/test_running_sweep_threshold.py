"""A running worker does not sweep what a live Attempt may still hold (`AR-V3-LIVENESS-01`).

A live Attempt (its model call shows signs of life) may run until ``ATTEMPT_HARD_CAP_SECONDS``
(two hours); before, the worker's running sweep took a temporary file at the 900 s watchdog plus
a five-minute margin, which would delete the source PDF of an Attempt that is still thinking.
The sweep itself (names, age, owner, links) is proved in ``tests/unit/jobs/test_stale_temporaries.py``
and the worker loop in ``tests/unit/shared/test_tempsweep.py``; this file pins the number.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from auditmanager.jobs import temporaries
from auditmanager.jobs.public import ATTEMPT_HARD_CAP_SECONDS, ATTEMPT_WATCHDOG_SECONDS
from auditmanager.workers import service as service_module
from auditmanager.workers.service import TEMPORARIES_LIVE_MARGIN_SECONDS, sweep_running_temporaries

SOURCE = "am-source-a1b2c3d4.pdf"


def test_the_running_sweep_waits_out_the_live_ceiling_and_the_live_margin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, float] = {}
    monkeypatch.setattr(
        service_module, "sweep_stale_temporaries", lambda **kwargs: seen.update(kwargs) or "swept",
    )
    assert sweep_running_temporaries() == "swept"
    assert seen == {"older_than": float(ATTEMPT_HARD_CAP_SECONDS) + TEMPORARIES_LIVE_MARGIN_SECONDS}
    assert seen["older_than"] == 7500.0
    assert seen["older_than"] > ATTEMPT_WATCHDOG_SECONDS + TEMPORARIES_LIVE_MARGIN_SECONDS


def test_a_file_two_hours_old_is_not_swept_by_a_running_worker_and_one_past_the_margin_is(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    (tmp_path / SOURCE).write_bytes(b"%PDF-1.7\n" + b"x" * 100)
    written = time.time()
    moment = [written]
    monkeypatch.setattr(temporaries, "time", SimpleNamespace(time=lambda: moment[0]))

    # What the old threshold (900 s + 5 min) would have removed, a live Attempt may still hold.
    moment[0] = written + ATTEMPT_WATCHDOG_SECONDS + 600
    assert sweep_running_temporaries().removed == ()
    moment[0] = written + ATTEMPT_HARD_CAP_SECONDS
    assert sweep_running_temporaries().removed == ()
    assert (tmp_path / SOURCE).exists()
    moment[0] = written + ATTEMPT_HARD_CAP_SECONDS + TEMPORARIES_LIVE_MARGIN_SECONDS + 5
    assert sweep_running_temporaries().removed == (SOURCE,)
