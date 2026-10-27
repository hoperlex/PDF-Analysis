"""What ties the spend journal to the rest of the tree (`CMP-SPEND-01`): the settler the queue's reclaim calls,
the one door to a model, and the facts this context restates from the contexts it may not import. Container-free."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from auditmanager.comparison import public
from auditmanager.comparison.spend import caller, repository, settler

ROOT = Path(__file__).resolve().parents[4]
COMPARISON = ROOT / "src/auditmanager/comparison"


# --- the settler: the one thing between a dead worker and a double spend ----------------------------------------


def test_the_settler_is_registered_for_the_queues_reclaim() -> None:
    assert settler.settle_lost_attempt in public.SPEND_SETTLERS


def test_the_worker_composition_hands_the_registered_settlers_to_the_queue() -> None:
    from auditmanager.bootstrap.composition import build_comparison_work

    runner = build_comparison_work(sessions=object(), engine=object(), blob_store=object(), environ={})  # type: ignore[arg-type]
    assert settler.settle_lost_attempt in runner._settlers  # type: ignore[attr-defined]


def test_the_settler_marks_the_attempts_open_calls_and_says_whether_there_were_any() -> None:
    class Result:
        def __init__(self, rows: list[object]) -> None:
            self.rows = rows

        def all(self) -> list[object]:
            return self.rows

    class Session:
        def __init__(self, rows: list[object]) -> None:
            self.rows, self.executed = rows, []

        def execute(self, statement: object, params: dict[str, object]) -> Result:
            self.executed.append((str(statement), params))
            return Result(self.rows)

    none, some = Session([]), Session([("cmc_1",)])
    assert settler.settle_lost_attempt(none, "cqa_A") is False  # type: ignore[arg-type]
    assert settler.settle_lost_attempt(some, "cqa_A") is True  # type: ignore[arg-type]
    sql, params = some.executed[0]
    assert params["attempt_id"] == "cqa_A" and params["error_code"] == "attempt_lost"
    # Exactly the open states, to unknown, for that attempt only.
    assert "state = 'unknown'" in sql and "state IN ('prepared', 'sent')" in sql
    assert "comparison_work_attempt_id = :attempt_id" in sql


# --- one door to a model --------------------------------------------------------------------------------------


def test_only_the_spend_wrapper_calls_an_adapter_in_the_comparison_context() -> None:
    """No module of ``comparison`` calls ``.complete(...)`` but the wrapper (and the recorded summary seam, which holds
    no client). A model call that skips the wrapper skips the journal, the consent and the ceilings."""
    allowed = {COMPARISON / "spend" / "caller.py", COMPARISON / "summary_model.py", COMPARISON / "summaries.py"}
    offenders: list[str] = []
    for path in sorted(COMPARISON.rglob("*.py")):
        if path in allowed:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "complete":
                offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    assert offenders == []


def test_the_summary_seam_that_is_allowed_to_complete_holds_no_client() -> None:
    """The recorded summary model is the one other ``complete`` of this context: it reads a committed file,
    imports no network code, and a live implementation of it would have to go through the wrapper."""
    tree = ast.parse((COMPARISON / "summary_model.py").read_text(encoding="utf-8"))
    imported = {
        (node.module or "").split(".")[0] if isinstance(node, ast.ImportFrom) else alias.name.split(".")[0]
        for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in (node.names if isinstance(node, ast.Import) else [None])
    }
    assert imported.isdisjoint({"urllib", "http", "socket", "ssl", "requests", "httpx", "anthropic", "openai"})


def test_the_wrapper_is_the_only_caller_of_an_adapter_inside_the_spend_package() -> None:
    callers = []
    for path in sorted((COMPARISON / "spend").glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "complete":
                callers.append((path.name, node.lineno))
    # ``repository.complete`` is the journal's own statement; the adapter's call is on ``route.adapter``.
    adapter_calls = [c for c in callers if c[0] == "caller.py"]
    journal_defs = [c for c in callers if c[0] != "caller.py"]
    assert journal_defs == []
    source = (COMPARISON / "spend" / "caller.py").read_text(encoding="utf-8")
    assert source.count("route.adapter.complete(") == 1
    assert len(adapter_calls) >= 1


# --- facts restated from contexts this one may not import ---------------------------------------------------------


def test_the_gateway_stubs_are_the_ones_the_proxy_adapter_knows() -> None:
    from auditmanager.analysis.text import proxy

    assert caller.MODEL_STUBS == proxy.MODEL_STUBS


def test_the_connection_lock_is_the_one_the_run_claim_takes() -> None:
    from auditmanager.jobs import repository as jobs

    assert str(repository._LOCK_CONNECTION) == str(jobs._LOCK_CONNECTION)  # type: ignore[attr-defined]


def test_the_active_run_states_are_the_ones_the_run_claim_decides_on() -> None:
    from auditmanager.jobs import repository as jobs

    assert jobs._ACTIVE_JOB_STATES == "(" + ", ".join(f"'{s}'" for s in repository.ACTIVE_JOB_STATES) + ")"  # type: ignore[attr-defined]


def test_the_runs_claim_names_an_active_comparison_call_the_way_this_context_does() -> None:
    """The Run claim's mirror of ``connection_has_active_call``: the same two states of the call and three of the attempt."""
    from auditmanager.jobs import repository as jobs

    run_side = str(jobs._CONNECTION_HAS_OTHER_ACTIVE_RUN)  # type: ignore[attr-defined]
    ours = str(repository._CONNECTION_HAS_ACTIVE_CALL)  # type: ignore[attr-defined]
    for fragment in ("c.state IN ('prepared', 'sent')", "a.state IN ('created', 'leased', 'running')"):
        assert fragment in ours
    for fragment in ("active_call.state IN ('prepared', 'sent')", "active_attempt.state IN ('created', 'leased', 'running')"):
        assert fragment in run_side


# --- the pull channel's origin (an integrator hunk in a file this lane does not own) ------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason=(
        "executors/pull.py (the image lane's file) still writes origin 'run_call' for every call; the integrator's "
        "hunk makes PullAdapter._write_task pass origin 'comparison_call' and comparison_attempt_id when the call's "
        "context carries one. Remove this marker when it is applied: the test is then the permanent pin."
    ),
)
def test_a_pull_adapter_writes_the_comparison_origin_for_a_comparison_call() -> None:
    from contextlib import contextmanager
    from datetime import datetime, timezone
    from types import SimpleNamespace

    from auditmanager.executors.model import RevisionRecord, RevisionSettings
    from auditmanager.executors.pull import PullAdapter

    seen: dict[str, object] = {}

    class Store:
        def insert_task(self, session: object, **kwargs: object) -> object:
            seen.update(kwargs)
            return SimpleNamespace(task_id="ext_T")

    class Sessions:
        @contextmanager
        def __call__(self):  # type: ignore[no-untyped-def]
            yield SimpleNamespace(commit=lambda: None)

    now = datetime(2026, 10, 28, tzinfo=timezone.utc)
    revision = RevisionRecord(
        revision_id="excr_R", connection_id="exc_C", revision_no=1, created_at=now, created_by="usr_A",
        settings=RevisionSettings(
            pin_id="claude-opus-5", gateway_model="claude-opus-5", billing="not_metered",
            allow_client_documents=False, timeout_seconds=60, pull_client="claude_code_session",
            answer_deadline_seconds=600, max_claimed_tasks=1),
    )
    context = SimpleNamespace(
        run_id=None, attempt_id=None, call_id=None, comparison_attempt_id="cqa_X", remaining_seconds=lambda: 600.0)
    built = PullAdapter(session_factory=Sessions(), revision=revision, context=context, repository=Store())  # type: ignore[arg-type]
    built._write_task({"system": "s", "user_text": "u", "output_schema": {}}, 60.0)  # type: ignore[attr-defined]
    assert seen["origin"] == "comparison_call" and seen["comparison_attempt_id"] == "cqa_X"
    assert seen["run_id"] is None and seen["attempt_id"] is None
