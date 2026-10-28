"""The ceilinged child, end to end (`CMP-PROFILE-01`, ADR-0025 decision 8 and the addendum of 2026-10-27).

Real children, real kernel ceilings. Every end without a result -- an overrun, the CPU ceiling, the wall clock, a
signal, an exception -- is **a typed page** (``needs_review`` / ``RENDER_FAILED``), and it is that page's alone:
the pages around it are built. A page over the pixel cap is **refused and never rendered**. The classification of
an end is also tested on its own, with the wait statuses the kernel gives.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import types
from pathlib import Path

import pytest

from auditmanager.comparison.profile import limits, runner as runner_module
from auditmanager.comparison.profile.profiling import profile_page
from auditmanager.comparison.profile.runner import ChildResult, ChildStartError, SubprocessChildRunner

MIB = 1024 * 1024
ROOT = Path(__file__).resolve().parents[4]


def _usage(rss: int = 1000, user: float = 0.5, system: float = 0.1) -> types.SimpleNamespace:
    return types.SimpleNamespace(ru_utime=user, ru_stime=system, ru_maxrss=rss)


def _line(**item: object) -> bytes:
    import json

    return (json.dumps(item) + "\n").encode()


STARTED = _line(stage="limits_set")


class TestTheClassificationOfAnEnd:
    def test_an_answer_is_ok_refused_or_out_of_range(self) -> None:
        ok = runner_module._classify([STARTED, _line(status="ok", dpi=200)], 0, False, 1.0, _usage())
        assert ok.ok and ok.answered and ok.facts == {"dpi": 200}
        refused = runner_module._classify([STARTED, _line(status="refused", reason="PAGE_TOO_LARGE")], 5 << 8, False, 1.0, _usage())
        assert refused.status == "refused" and refused.answered and not refused.ok
        miss = runner_module._classify([STARTED, _line(status="range")], 6 << 8, False, 1.0, _usage())
        assert miss.status == "range" and miss.answered

    @pytest.mark.parametrize(
        ("chunks", "wait_status", "timed_out", "status", "end"),
        [
            ([STARTED, _line(status="overrun", reason="MemoryError")], 3 << 8, False, "overrun", "overrun"),
            ([STARTED, _line(status="error:ValueError")], 4 << 8, False, "error:ValueError", "error:ValueError"),
            ([STARTED], int(signal.SIGABRT), False, "signal:SIGABRT", "signal:SIGABRT"),
            ([STARTED], int(signal.SIGTRAP), False, "signal:SIGTRAP", "signal:SIGTRAP"),
            ([STARTED], int(signal.SIGSEGV), False, "signal:SIGSEGV", "signal:SIGSEGV"),
            ([STARTED], int(signal.SIGXCPU), False, "cpu", "cpu"),
            ([STARTED], int(signal.SIGKILL), True, "wall", "wall"),
            ([STARTED], 9 << 8, False, "exit:9", "exit"),
        ],
    )
    def test_every_end_without_a_result_is_not_an_answer(
        self, chunks, wait_status, timed_out, status, end
    ) -> None:
        result = runner_module._classify(chunks, wait_status, timed_out, 2.0, _usage())
        assert (result.status, result.end) == (status, end)
        assert not result.ok and not result.answered

    def test_a_child_that_never_set_its_limits_is_the_servers_fault_not_the_pages(self) -> None:
        for chunks, wait_status, timed_out in (([], 1 << 8, False), ([], int(signal.SIGKILL), True), ([b"noise\n"], 0, False)):
            with pytest.raises(ChildStartError):
                runner_module._classify(chunks, wait_status, timed_out, 0.1, _usage())

    def test_the_cpu_wall_and_memory_the_kernel_reports_are_carried(self) -> None:
        result = runner_module._classify([STARTED, _line(status="ok")], 0, False, 1.2349, _usage(rss=4096, user=1.0, system=0.5))
        assert (result.wall_s, result.cpu_s, result.max_rss_kib) == (1.235, 1.5, 4096)


def test_a_child_is_started_bare_in_isolated_mode_with_its_own_working_directory(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def fake_popen(argv, **kwargs):
        seen.update(argv=argv, **kwargs)
        raise RuntimeError("stop here")

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    with pytest.raises(RuntimeError):
        SubprocessChildRunner().run({"mode": "render"}, limits.RENDER_LIMITS)
    assert seen["argv"][1:3] == ["-I", "-B"] and seen["argv"][3].endswith("child/program.py")
    assert seen["env"] == {"PATH": os.defpath, "LANG": "C.UTF-8", "PYTHONHASHSEED": "0"}
    assert seen["cwd"] == "/" and seen["stdin"] == subprocess.DEVNULL and seen["stderr"] == subprocess.DEVNULL
    import json

    sent = json.loads(seen["argv"][4])
    assert sent["address_space"] == 768 * MIB and sent["cpu_seconds"] == 300 and sent["file_bytes"] == limits.FILE_BYTES


def test_the_program_that_does_not_exist_is_a_start_failure(tmp_path: Path) -> None:
    with pytest.raises(ChildStartError):
        SubprocessChildRunner(program=tmp_path / "missing.py").run({"mode": "render"}, limits.RENDER_LIMITS)


# -- real children under real ceilings ---------------------------------------------------------------------------


def test_a_render_that_needs_more_than_its_ceiling_ends_without_a_result_and_the_next_page_is_built(
    fixtures_dir, runner
) -> None:
    """VS-1 v1: the A1 plan needs 196 MiB of address space to render (``MEASURE-RENDER-01``: the smallest ceiling
    that passes a realistic A1 is 224 MiB for the larger one); under 144 MiB only that page fails."""
    path = str(fixtures_dir / "vs1" / "v1.pdf")
    ceiling = limits.ChildLimits(144 * MIB, 300, 600.0)
    outcomes = [
        profile_page(runner, pdf_path=path, page_index=index, version_sha256="1" * 64, render_limits=ceiling)
        for index in range(6)
    ]
    assert [o.status for o in outcomes] == ["ready", "ready", "ready", "ready", "needs_review", "ready"]
    failed = outcomes[4]
    assert failed.reason == limits.REASON_RENDER_FAILED and failed.pack is None and failed.preview is None
    assert failed.summary["failure"]["stage"] == "render"
    assert failed.summary["failure"]["end"] in {"memory", "signal:SIGABRT", "signal:SIGTRAP", "signal:SIGSEGV"}
    assert "extract" not in failed.timings, "a page whose render failed is not extracted"
    assert len({o.content_key for o in outcomes}) == 6, "the unique key (version, content_key) holds for the failed page too"


def test_an_extraction_that_needs_more_than_its_ceiling_keeps_the_pictures_and_says_why(fixtures_dir, runner) -> None:
    outcome = profile_page(
        runner,
        pdf_path=str(fixtures_dir / "vs1" / "v1.pdf"),
        page_index=1,
        version_sha256="1" * 64,
        extract_limits=limits.ChildLimits(40 * MIB, 300, 600.0),
    )
    assert (outcome.status, outcome.reason) == ("needs_review", limits.REASON_RENDER_FAILED)
    assert outcome.summary["failure"]["stage"] == "extract"
    assert outcome.preview and outcome.thumbnail and outcome.pack, "the page image survives a failed extraction"
    assert "counts" not in outcome.summary and "content_merkle" not in outcome.summary
    assert outcome.summary["tiles"]["stored_count"] > 0


def test_an_unreadable_file_is_a_typed_page_not_an_exception(tmp_path: Path, runner) -> None:
    garbage = tmp_path / "garbage.pdf"
    garbage.write_bytes(b"%PDF-1.7\nthis is not a pdf at all\n" * 10)
    outcome = profile_page(runner, pdf_path=str(garbage), page_index=0, version_sha256="2" * 64)
    assert (outcome.status, outcome.reason) == ("needs_review", limits.REASON_RENDER_FAILED)
    assert outcome.summary["failure"]["end"].startswith("error:")


def test_a_page_index_beyond_the_document_is_a_typed_page_too(fixtures_dir, runner) -> None:
    outcome = profile_page(runner, pdf_path=str(fixtures_dir / "vs1" / "v1.pdf"), page_index=99, version_sha256="2" * 64)
    assert outcome.status == "needs_review" and outcome.summary["failure"]["stage"] == "render"


@pytest.fixture(scope="module")
def heavy_pdf(tmp_path_factory) -> Path:
    """The realistic A1 sheet of the corpus tools: 186 000 reader elements, a few CPU seconds to extract."""
    target = tmp_path_factory.mktemp("heavy") / "realistic-a1.pdf"
    done = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "fixtures" / "comparison" / "realistic_a1.py"), str(target)],
        capture_output=True, text=True, cwd="/", timeout=120,
    )
    assert done.returncode == 0, done.stderr
    return target


def test_the_cpu_ceiling_ends_a_child_and_is_reported_as_cpu(heavy_pdf: Path, tmp_path: Path) -> None:
    result = SubprocessChildRunner().run(
        {"mode": "extract", "pdf": str(heavy_pdf), "page": 0, "out_dir": str(tmp_path)},
        limits.ChildLimits(1024 * MIB, 2, 600.0),
    )
    assert result.status == "cpu" and not result.answered
    assert 1.5 <= result.cpu_s <= 4.5


def test_the_wall_clock_kills_only_its_child_and_reaps_it(heavy_pdf: Path, tmp_path: Path) -> None:
    before = set(os.listdir("/proc"))
    result = SubprocessChildRunner().run(
        {"mode": "extract", "pdf": str(heavy_pdf), "page": 0, "out_dir": str(tmp_path)},
        limits.ChildLimits(1024 * MIB, 300, 1.5),
    )
    assert result.status == "wall" and not result.answered
    assert 1.4 <= result.wall_s < 4.0
    # Reaped: no zombie of ours is left behind.
    me = os.getpid()
    leftovers = []
    for entry in set(os.listdir("/proc")) - before:
        if entry.isdigit():
            try:
                stat = Path(f"/proc/{entry}/stat").read_text().rsplit(")", 1)[1].split()
            except OSError:
                continue
            if int(stat[1]) == me and stat[0] == "Z":
                leftovers.append(entry)
    assert leftovers == []


def test_the_heavy_page_passes_under_the_ceilings_the_addendum_sets(heavy_pdf: Path) -> None:
    """The realistic A1 (rotated, cropped, 186 000 elements, no text layer) is profiled end to end: ready, no
    words, a rotation of 90, a frame that agrees, the preview and thumbnail the measurement reported."""
    outcome = profile_page(SubprocessChildRunner(), pdf_path=str(heavy_pdf), page_index=0, version_sha256="3" * 64)
    assert outcome.status == "ready"
    summary = outcome.summary
    assert summary["rotation"] == 90 and summary["text_layer"] is False and summary["scan"] is False
    assert summary["counts"]["words"] == 0 and summary["counts"]["lines"] > 50000
    assert (summary["width_pt"], summary["height_pt"]) == (2366.94, 1666.78), "the CropBox inset is applied"
    assert summary["frame"]["agrees"] is True and summary["frame"]["offset"] == [8.5, 8.5]
    assert (len(outcome.preview), len(outcome.thumbnail)) == (396665, 18006), "the MEASURE-RENDER-01 figures"
    assert outcome.timings["render"]["vm_peak_kib"] < 768 * 1024 and outcome.timings["extract"]["vm_peak_kib"] < 1024 * 1024
