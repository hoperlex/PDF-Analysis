"""A running worker does not sweep what a live Attempt may still hold.

A live Attempt has no age ceiling (`R-155c`: ``ATTEMPT_HARD_CAP_SECONDS`` is ``math.inf``), so no age
proves that the attempt which made a temporary file is gone. Two things protect it: the running sweep
**skips while any slot is busy** (the loop is proved below), and when it does run, it takes only what
is older than the stale age of the start sweep (``jobs.temporaries.STALE_AFTER_SECONDS``, 7260 s) plus a
five-minute margin. Before, it took a file at the 900 s watchdog plus that margin, which would delete the
source PDF of an Attempt that is still thinking.
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
from auditmanager.jobs.public import ATTEMPT_WATCHDOG_SECONDS
from auditmanager.jobs.temporaries import STALE_AFTER_SECONDS
from auditmanager.workers import service as service_module
from auditmanager.workers.service import TEMPORARIES_LIVE_MARGIN_SECONDS, sweep_running_temporaries

SOURCE = "am-source-a1b2c3d4.pdf"


def test_the_running_sweep_waits_out_the_stale_age_and_the_live_margin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, float] = {}
    monkeypatch.setattr(
        service_module, "sweep_stale_temporaries", lambda **kwargs: seen.update(kwargs) or "swept",
    )
    assert sweep_running_temporaries() == "swept"
    assert seen == {"older_than": float(STALE_AFTER_SECONDS) + TEMPORARIES_LIVE_MARGIN_SECONDS}
    assert seen["older_than"] == 7560.0
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
    moment[0] = written + STALE_AFTER_SECONDS
    assert sweep_running_temporaries().removed == ()
    assert (tmp_path / SOURCE).exists()
    moment[0] = written + STALE_AFTER_SECONDS + TEMPORARIES_LIVE_MARGIN_SECONDS + 5
    assert sweep_running_temporaries().removed == (SOURCE,)
