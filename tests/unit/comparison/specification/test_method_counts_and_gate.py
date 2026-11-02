"""The zero-call consent gate travels with the counts of its command; a job pins the attempts it was consented for (`REVIEW-FIX-CMP-SPEC-1102`).

Code review 2026-11-02, S2-blocks-4-9-05 (and the attempts of -04). ``SpecMethod`` is one object serving every request of the process, so a
fact about one plan must not live on it. The sides, the reader and the store are fakes; the planning is not run (the prepared sides are
handed to the method), because what is proved here is where the answer of one request is kept, not how a text is planned.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.comparison.ai_jobs import service as jobs_service
from auditmanager.comparison.ai_jobs.model import AiEstimateRequest, AiMode, AiScope
from auditmanager.comparison.specification import method as method_module
from auditmanager.comparison.specification.method import SpecCounts, SpecMethod, _attempts
from auditmanager.comparison.specification.repository import TransitionScope
from auditmanager.comparison.specification.transition import PreparedSide, Side

PROJECT = "prj_01M2545JSD15ETSNNV904X991F"
DOCUMENT = "doc_01M2545JSD15ETSNNV904X991D"
OLD, NEW = "ver_01M2545JSD15ETSNNV904X991A", "ver_01M2545JSD15ETSNNV904X991B"


def transition_id(n: int) -> str:
    return f"ctn_unit{n}"


class Repository:
    """The two reads the method makes: the scope of a transition and the row of its whole comparison."""

    def __init__(self, row: Any = None) -> None:
        self.row, self.opened, self.pinned = row, [], []

    def transition(self, session: Any, tid: str) -> TransitionScope:
        return TransitionScope(tid, "cser_X", 1, OLD, NEW, PROJECT, DOCUMENT)

    def whole(self, session: Any, tid: str) -> Any:
        return self.row

    def open_whole(self, session: Any, scope: Any, **kw: Any) -> None:
        self.opened.append(kw)

    def pin_plan(self, session: Any, tid: str, keys: list[str]) -> None:
        self.pinned.append(keys)


def batch(packet: dict[str, Any], *, stored: bool, raw: bool = False, attempt: int = 1, batch_id: str = "sb_1") -> dict[str, Any]:
    return {"batch_id": batch_id, "source": packet, "stored": object() if stored else None, "raw": object() if raw else None,
            "attempt": attempt}


def side(version: str, packet: dict[str, Any], *batches: dict[str, Any]) -> PreparedSide:
    return PreparedSide(Side(version, 1, False), packet, f"key-{version}", None, tuple(batches))


@pytest.fixture
def packet(drawn: Any, whole: Any) -> dict[str, Any]:
    page = drawn.Page(numbered_row=True)
    page.row({"pos": "2", "mark": "М-2", "name": "Щит", "quantity": "1"})
    return whole.source_of(page)


def method_over(monkeypatch: pytest.MonkeyPatch, sides: dict[str, PreparedSide], row: Any = None) -> SpecMethod:
    def prepare(factory: Any, reader: Any, repository: Any, *, project_uid: str, version_uid: str, renew_failed: bool = False, **_: Any):
        assert renew_failed is True, "an estimate and a start read the next attempts"
        return sides[version_uid]

    monkeypatch.setattr(method_module, "prepare_side", prepare)
    return SpecMethod(None, None, reader=object(), repository=Repository(row))  # type: ignore[arg-type]


def request(n: int = 1) -> AiEstimateRequest:
    return AiEstimateRequest(scope=AiScope(method="spec", project_uid=PROJECT, document_uid=DOCUMENT, transition_id=transition_id(n)),
                             mode=AiMode.START)


def estimate_of(counts: Any, n: int = 1) -> Any:
    return SimpleNamespace(scope=request(n).scope, counts=counts)


def test_the_flag_is_on_the_counts_of_each_command_and_never_on_the_method(monkeypatch: pytest.MonkeyPatch, packet: dict[str, Any]) -> None:
    stored_only = {OLD: side(OLD, packet, batch(packet, stored=True)), NEW: side(NEW, packet, batch(packet, stored=True))}
    to_ask = {OLD: side(OLD, packet, batch(packet, stored=False)), NEW: side(NEW, packet, batch(packet, stored=True))}
    zero = method_over(monkeypatch, stored_only)
    ready = zero.counts(None, request())  # type: ignore[arg-type]
    paid = method_over(monkeypatch, to_ask)
    priced = paid.counts(None, request())  # type: ignore[arg-type]
    for method in (zero, paid):
        assert not hasattr(method, "can_run_without_model") and not hasattr(method, "_zero_ready")
    assert isinstance(ready, SpecCounts) and ready.can_run_without_model is True and ready.groups == () and ready.units >= 1
    assert isinstance(priced, SpecCounts) and priced.can_run_without_model is False and len(priced.groups) == 1


def test_two_interleaved_estimates_on_one_method_each_keep_their_own_answer(monkeypatch: pytest.MonkeyPatch, packet: dict[str, Any]) -> None:
    """The mutation: the flag as an attribute of the method is whatever the last ``counts`` set -- A would be refused (or B allowed)."""
    plans: dict[str, dict[str, PreparedSide]] = {
        "A": {OLD: side(OLD, packet, batch(packet, stored=True)), NEW: side(NEW, packet, batch(packet, stored=True))},
        "B": {OLD: side(OLD, packet, batch(packet, stored=False)), NEW: side(NEW, packet, batch(packet, stored=True))},
    }
    current = {"plan": "A"}

    def prepare(factory: Any, reader: Any, repository: Any, *, project_uid: str, version_uid: str, renew_failed: bool = False, **_: Any):
        return plans[current["plan"]][version_uid]

    monkeypatch.setattr(method_module, "prepare_side", prepare)
    method = SpecMethod(None, None, reader=object(), repository=Repository())  # type: ignore[arg-type]
    current["plan"] = "A"
    a = method.counts(None, request(1))  # type: ignore[arg-type]
    current["plan"] = "B"
    b = method.counts(None, request(2))  # type: ignore[arg-type]
    # the consent gate of A is decided after B's estimate has been made on the same method
    assert jobs_service._may_run_without_model(method, estimate_of(a, 1)) is True  # noqa: SLF001
    assert jobs_service._may_run_without_model(method, estimate_of(b, 2)) is False  # noqa: SLF001


def test_the_gate_reads_the_counts_for_spec_and_the_method_for_a_report_and_nothing_for_the_others() -> None:
    carried = SpecCounts(groups=(), units=1, can_run_without_model=True)
    plain = SimpleNamespace(scope=SimpleNamespace(method="spec"), counts=SimpleNamespace())
    method_says = SimpleNamespace(can_run_without_model=True)
    assert jobs_service._may_run_without_model(method_says, SimpleNamespace(scope=SimpleNamespace(method="spec"), counts=carried))  # noqa: SLF001
    assert jobs_service._may_run_without_model(object(), SimpleNamespace(scope=SimpleNamespace(method="spec"), counts=carried))  # noqa: SLF001
    # counts that say nothing: a method that states it (the report, built per command) is asked; a spec method states nothing
    assert jobs_service._may_run_without_model(method_says, SimpleNamespace(scope=SimpleNamespace(method="report"), counts=plain.counts))  # noqa: SLF001
    assert not jobs_service._may_run_without_model(object(), plain)  # noqa: SLF001
    for other in ("pair_check", "sheet_changes", "stage_review"):
        assert not jobs_service._may_run_without_model(method_says, SimpleNamespace(scope=SimpleNamespace(method=other), counts=carried))  # noqa: SLF001
    # counts that say "no" win over a method that says "yes"
    no = SpecCounts(groups=(), units=1, can_run_without_model=False)
    assert not jobs_service._may_run_without_model(method_says, SimpleNamespace(scope=SimpleNamespace(method="spec"), counts=no))  # noqa: SLF001


def _job() -> Any:
    return SimpleNamespace(transition_id=transition_id(1), project_uid=PROJECT, job_id="cai_01M2545JSD15ETSNNV904X991J")


def test_a_job_with_nothing_to_send_and_nothing_to_assemble_has_no_work(monkeypatch: pytest.MonkeyPatch, packet: dict[str, Any]) -> None:
    done = SimpleNamespace(state="completed", coverage_a=None, coverage_b=None)
    empty = {OLD: PreparedSide(Side(OLD, 1, False), packet, "k1", object(), ()),  # type: ignore[arg-type]
             NEW: PreparedSide(Side(NEW, 1, False), packet, "k2", object(), ())}  # type: ignore[arg-type]
    assert method_over(monkeypatch, empty, done).work_items(None, _job(), AiMode.START) == []  # type: ignore[arg-type]


def test_the_zero_call_work_of_a_start_is_decided_from_its_own_plan(monkeypatch: pytest.MonkeyPatch, packet: dict[str, Any]) -> None:
    """``work_items`` used to read the flag some earlier ``counts`` had left on the method; it now recomputes from the sides in hand."""
    stored_only = {OLD: side(OLD, packet, batch(packet, stored=True)), NEW: side(NEW, packet, batch(packet, stored=True))}
    method = method_over(monkeypatch, stored_only)
    items = method.work_items(None, _job(), AiMode.START)  # type: ignore[arg-type]
    assert len(items) == 1 and items[0].payload["source_keys"] == [f"key-{OLD}", f"key-{NEW}"] and "attempts" not in items[0].payload


def test_the_payload_pins_the_attempts_after_the_first(monkeypatch: pytest.MonkeyPatch, packet: dict[str, Any]) -> None:
    sides = {OLD: side(OLD, packet, batch(packet, stored=True), batch(packet, stored=False, attempt=2, batch_id="sb_2"),
                       batch(packet, stored=False, batch_id="sb_3")),
             NEW: side(NEW, packet, batch(packet, stored=True, batch_id="sb_9"))}
    method = method_over(monkeypatch, sides)
    (item,) = method.work_items(None, _job(), AiMode.START)  # type: ignore[arg-type]
    assert item.payload["attempts"] == {"sb_2": 2}


def test_the_attempts_of_an_item_are_validated() -> None:
    assert _attempts({}) == {} and _attempts({"attempts": {"sb_2": 2, "sb_7": 3}}) == {"sb_2": 2, "sb_7": 3}
    for bad in ([("sb_2", 2)], {"sb_2": 1}, {"sb_2": "2"}, {"sb_2": True}, {3: 2}):
        with pytest.raises(ValueError):
            _attempts({"attempts": bad})
