"""Step 7 reads the final V3 cards of the plan the run froze at its start (D-530).

Rules from `stage_review/service.py` and docs/program/SPRINT3-STAGE-1030.md: a V3 run keeps its plan in the start command's
outcome (`stage_v3_policy`); the review step takes its cards from the completed `v3:final:cards` unit saved under THAT plan's
bundle -- the bundle the run stored, not the one the current code or switch would pick -- so a run started under one plan is
never reviewed through another plan's cards; a plan-less V3 run reads the legacy bundle; a classic run reads the classic
classifications and knows no plan. Windowed plans carry display excerpts. Stub sessions only.
"""
from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.comparison.stage_review import service as service_module
from auditmanager.comparison.stage_review.service import StageReviewService
from auditmanager.comparison.stage_v3 import consolidation as c, procedures as legacy, windowed as w
from auditmanager.comparison.stage_v3.mode import ENGINE
from auditmanager.comparison.stage_v3.policy import GLOBAL_LIMITS, GLOBAL_VERSION, LIMITS, VERSION

SWITCH = "AUDITMANAGER_STAGE_V3_PLAN"
RUN, PAIR, PROJECT = "crn_00000000000000000000000001", "spr_00000000000000000000000001", "prj_00000000000000000000000001"
WINDOWED = {"plan_version": VERSION, "bundle": w.BUNDLE, "limits": LIMITS}
GLOBAL = {"plan_version": GLOBAL_VERSION, "bundle": c.BUNDLE, "limits": GLOBAL_LIMITS}
HISTORICAL = {"plan_version": VERSION, "bundle": "a" * 64, "limits": LIMITS}      # stored by an older code bundle
FINALS = {bundle: {"classification_id": f"sac_{name}", "cards": [{"title": name}]}
          for name, bundle in (("legacy", legacy.BUNDLE), ("windowed", w.BUNDLE), ("global", c.BUNDLE), ("historical", "a" * 64))}
CLASSIC_ROWS = [{"classification_id": "sac_classic_1", "cards": []}, {"classification_id": "sac_classic_2", "cards": []}]


class _Result:
    def __init__(self, value: Any = None, rows: list[dict[str, Any]] | None = None) -> None:
        self._value, self._rows = value, rows or []

    def scalar_one_or_none(self) -> Any:
        return self._value

    def mappings(self) -> list[dict[str, Any]]:
        return self._rows

    def all(self) -> list[Any]:
        return []


class _Session:
    """Answers the statements step 7 makes. The final-cards query is emulated from its own WHERE clause: it filters by the
    bound bundle only if the SQL text still says so, so dropping the filter from the query changes what is picked."""

    def __init__(self, *, engine: str | None, policy: Any) -> None:
        self.engine, self.policy = engine, policy
        self.statements: list[tuple[str, dict[str, Any]]] = []

    def execute(self, statement: Any, params: dict[str, Any] | None = None) -> _Result:
        sql = " ".join(str(statement).split())
        params = dict(params or {})
        self.statements.append((sql, params))
        if "c.outcome->>'engine' FROM stage_chain_run r" in sql:
            return _Result(self.engine)
        if "c.outcome->'stage_v3_policy' FROM stage_chain_run r" in sql:
            return _Result(self.policy)
        if "u.group_id='v3:final:cards'" in sql:
            wanted = [bundle for bundle in FINALS if "u.progress->>'prompt_bundle_version'=:bundle" not in sql or bundle == params["bundle"]]
            return _Result(rows=[dict(FINALS[bundle]) for bundle in wanted][:1])
        if "FROM stage_ai_classification a JOIN stage_ai_unit u" in sql:
            return _Result(rows=[dict(row) for row in CLASSIC_ROWS])
        return _Result()


def _advance(monkeypatch: pytest.MonkeyPatch, *, engine: str | None, policy: Any, with_ai: bool = True,
             switch: str | None = None) -> tuple[dict[str, Any], _Session]:
    session = _Session(engine=engine, policy=policy)
    seen: dict[str, Any] = {}

    @contextmanager
    def scope(_factory: Any) -> Any:
        yield session

    def prepare_cards(sources: Any, answers: Any, **kwargs: Any) -> tuple[()]:
        seen.update(answers=list(answers), **kwargs)
        return ()

    monkeypatch.setattr(service_module, "session_scope", scope)
    monkeypatch.setattr(service_module, "prepare_cards", prepare_cards)
    if switch is None:
        monkeypatch.delenv(SWITCH, raising=False)
    else:
        monkeypatch.setenv(SWITCH, switch)
    service = StageReviewService(object())  # type: ignore[arg-type]
    run = {"stage_pair_id": PAIR, "project_uid": PROJECT, "state": "running", "kind": "full", "stale": False,
           "with_ai": with_ai, "revision_id": "slr_00000000000000000000000001"}
    service._run = lambda _s, run_id: dict(run)  # type: ignore[method-assign]
    service._sources = lambda _s, revision_id, run_id: {}  # type: ignore[method-assign]
    service._previous = lambda _s, _run: []  # type: ignore[method-assign]
    service._audit = lambda *_a, **_k: None  # type: ignore[method-assign]
    service._counts = lambda _s, _run: {"cards": 0}  # type: ignore[method-assign]
    item = SimpleNamespace(project_uid=PROJECT, module="stages", kind="stage_chain", payload={"run_id": RUN},
                           require_current=lambda _session: None)
    service.advance(item, RUN)  # type: ignore[arg-type]
    return seen, session


# --- a V3 run reads the final cards saved under its own plan ----------------------------------------------------------------

@pytest.mark.parametrize("stored,final,switch_now", [
    (WINDOWED, "windowed", None), (WINDOWED, "windowed", "windowed-global-v1"),
    (GLOBAL, "global", None), (GLOBAL, "global", "windowed-v1"), (GLOBAL, "global", "legacy"),
])
def test_a_v3_run_takes_the_final_cards_saved_under_the_bundle_of_its_stored_stage_v3_policy(monkeypatch, stored, final, switch_now):
    seen, session = _advance(monkeypatch, engine=ENGINE, policy=stored, switch=switch_now)
    assert seen["answers"] == [FINALS[stored["bundle"]]] and seen["answers"][0]["cards"] == [{"title": final}]
    (query,) = [params for sql, params in session.statements if "u.group_id='v3:final:cards'" in sql]
    assert query == {"run": RUN, "bundle": stored["bundle"]}
    assert seen["include_uncovered"] is False and seen["display_excerpts"] is True       # windowed plans show source excerpts


def test_a_run_stored_under_an_older_bundle_is_read_through_that_bundle_not_the_current_code(monkeypatch):
    seen, _session = _advance(monkeypatch, engine=ENGINE, policy=HISTORICAL)
    assert seen["answers"] == [FINALS["a" * 64]]
    assert seen["answers"] != [FINALS[w.BUNDLE]]


def test_a_v3_run_without_a_stored_plan_reads_the_legacy_bundle_and_shows_no_excerpts(monkeypatch):
    seen, session = _advance(monkeypatch, engine=ENGINE, policy=None, switch="windowed-global-v1")
    assert seen["answers"] == [FINALS[legacy.BUNDLE]]
    (query,) = [params for sql, params in session.statements if "u.group_id='v3:final:cards'" in sql]
    assert query["bundle"] == legacy.BUNDLE
    assert seen["include_uncovered"] is False and seen["display_excerpts"] is False


def test_a_v3_run_that_did_not_ask_for_ai_reads_no_final_cards(monkeypatch):
    seen, session = _advance(monkeypatch, engine=ENGINE, policy=WINDOWED, with_ai=False)
    assert seen["answers"] == [] and seen["display_excerpts"] is True
    assert not any("u.group_id='v3:final:cards'" in sql for sql, _p in session.statements)


# --- a classic run knows no plan -----------------------------------------------------------------------------------------------

def test_a_classic_run_reads_the_classic_classifications_and_never_looks_up_a_plan(monkeypatch):
    seen, session = _advance(monkeypatch, engine=None, policy=GLOBAL)          # a plan row would be ignored for a classic run
    assert seen["answers"] == CLASSIC_ROWS
    assert seen["include_uncovered"] is True and seen["display_excerpts"] is False
    assert not any("stage_v3_policy" in sql or "v3:final:cards" in sql for sql, _p in session.statements)
