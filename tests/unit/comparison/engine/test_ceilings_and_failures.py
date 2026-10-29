"""A pair that cannot be compared is never «Совпадает» (ADR-0025 decisions 8 and 9, `CMP-ENGINE-01`).

The children here are real: the address space, the CPU time and the wall clock are the kernel's and the runner's. An
end without a result, whatever its cause, is ``needs_review`` with reason ``RENDER_FAILED`` for that pair; a page over the
40 Mpx cap is ``PAGE_TOO_LARGE``; a child that never started is the server's fault and raises.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from auditmanager.comparison.engine.limits import CHILD_LIMITS
from auditmanager.comparison.engine.service import compute_pair
from auditmanager.comparison.engine.validate import validate_outcome
from auditmanager.comparison.profile.limits import MIB, ChildLimits
from auditmanager.comparison.profile.runner import ChildResult, ChildStartError, SubprocessChildRunner

PAIR = ("vs1/v1.pdf", 2, "vs1/v2.pdf", 2)  # a pair of different content: a child must run


def _assert_failed_pair(computed, reason: str = "RENDER_FAILED") -> None:
    outcome = computed.outcome
    assert outcome["status"] == "needs_review" and reason in outcome["reasons"]
    assert all(channel["state"] == "unchecked" for channel in outcome["channels"].values())
    assert outcome["status"] != "same" and computed.mask is None and outcome["result"]["mask"] is None
    validate_outcome(outcome["channels"], outcome["result"])


def test_the_ceiling_is_the_one_of_the_decision() -> None:
    assert CHILD_LIMITS == ChildLimits(768 * MIB, 300, 600.0)


def test_a_child_that_passes_its_address_space_ends_without_a_result_and_the_pair_is_render_failed(compare) -> None:
    computed = compare(*PAIR, child_limits=ChildLimits(120 * MIB, 300, 600.0))
    # Below the cost of the libraries alone the child cannot even import them: an `ImportError` from the loader or a
    # `MemoryError`, both ends without a result.
    assert computed.end in ("overrun", "error:ImportError") and not computed.child.ok
    _assert_failed_pair(computed)


def test_the_same_pair_under_the_real_ceiling_is_compared(compare) -> None:
    computed = compare(*PAIR)
    assert computed.end == "ok" and computed.outcome["status"] == "different"
    assert computed.child.facts["vm_peak_kib"] * 1024 < CHILD_LIMITS.address_space


def test_a_child_that_passes_its_wall_clock_is_killed_and_the_pair_is_render_failed(compare) -> None:
    computed = compare(*PAIR, child_limits=ChildLimits(768 * MIB, 300, 0.4))
    assert computed.end == "wall"
    _assert_failed_pair(computed)


class _Ends:
    """A runner whose child ends in a given way."""

    def __init__(self, result: ChildResult | BaseException) -> None:
        self.result = result

    def run(self, settings: Mapping[str, Any], limits: ChildLimits) -> ChildResult:
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


@pytest.mark.parametrize("status", ["cpu", "signal:SIGSEGV", "signal:SIGABRT", "error:ValueError", "exit:3", "overrun", "wall"])
def test_every_end_without_a_result_is_render_failed_for_that_pair(compare, status: str) -> None:
    computed = compare(*PAIR, runner=_Ends(ChildResult(status)))
    _assert_failed_pair(computed)


def test_a_page_over_the_cap_is_refused_and_is_not_a_same(compare) -> None:
    computed = compare(*PAIR, runner=_Ends(ChildResult("refused", facts={"reason": "PAGE_TOO_LARGE"})))
    _assert_failed_pair(computed, "PAGE_TOO_LARGE")


def test_a_child_that_never_started_is_the_servers_fault_and_raises(compare) -> None:
    with pytest.raises(ChildStartError):
        compare(*PAIR, runner=_Ends(ChildStartError("no")))


def test_an_end_without_a_result_in_one_pair_does_not_touch_the_next(compare) -> None:
    failed = compare(*PAIR, runner=_Ends(ChildResult("overrun")))
    fine = compare("vs1/v1.pdf", 3, "vs1/v2.pdf", 3)
    _assert_failed_pair(failed)
    assert fine.outcome["status"] == "different" and fine.end == "ok"


def test_the_failure_keeps_the_link_reasons_the_caller_gave(compare) -> None:
    computed = compare(*PAIR, runner=_Ends(ChildResult("overrun")), reasons=("DUPLICATE_SHEET",))
    assert "DUPLICATE_SHEET" in computed.outcome["reasons"]


def test_the_real_program_sets_the_kernel_ceilings_before_it_loads_anything() -> None:
    """The program's source: RLIMIT_AS, RLIMIT_CPU and RLIMIT_FSIZE are set by ``_limit`` before ``limits_set`` is said,
    and the thread pools are closed before ``numpy`` is imported."""
    from pathlib import Path

    text = (Path(__file__).resolve().parents[4] / "src/auditmanager/comparison/engine/child/program.py").read_text()
    limit = text.index("def _limit")
    assert "RLIMIT_AS" in text[limit : limit + 600] and "RLIMIT_CPU" in text[limit : limit + 600]
    assert text.index("_limit(settings)") < text.index('_say({"stage": "limits_set"})') < text.index("job.run(settings)")
    assert text.index("OPENBLAS_NUM_THREADS") < text.index("def main")  # the pools are shut at import, before any job module


def test_the_child_imports_nothing_from_the_product() -> None:
    import re
    from pathlib import Path

    child = Path(__file__).resolve().parents[4] / "src/auditmanager/comparison/engine/child"
    for source in child.glob("*.py"):
        for line in source.read_text().splitlines():
            if re.match(r"\s*(from|import)\s+auditmanager", line):
                pytest.fail(f"{source.name} imports the product: {line.strip()}")
