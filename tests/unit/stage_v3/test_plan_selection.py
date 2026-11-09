"""Selecting a V3 plan by its name: the fresh-start switch, the stored authority, the saved-bundle readers, progress.

Rules from policy.py and docs/program/SPRINT3-STAGE-1030.md / BLOCK4-STAGE-1030.md: a fresh start reads
AUDITMANAGER_STAGE_V3_PLAN (default windowed-global-v1; `legacy` rolls back; anything else refuses); a run
keeps the authority frozen at its start whatever the switch says later; changed code under a saved bundle
refuses new paid work but history stays readable; replies are read only under the run's own bundle.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from auditmanager.comparison.stage_ai.validation import StageAiValidationError
from auditmanager.comparison.stage_v3 import bridge, consolidation as c, mode, policy
from auditmanager.comparison.stage_v3 import procedures as legacy
from auditmanager.comparison.stage_v3 import windowed as w
from auditmanager.comparison.stage_v3.policy import GLOBAL_LIMITS, GLOBAL_VERSION, LIMITS, VERSION

SWITCH = "AUDITMANAGER_STAGE_V3_PLAN"
WINDOWED = {"plan_version": VERSION, "bundle": w.BUNDLE, "limits": LIMITS}
GLOBAL = {"plan_version": GLOBAL_VERSION, "bundle": c.BUNDLE, "limits": GLOBAL_LIMITS}


# --- the three bundles -----------------------------------------------------------------------------------------

def test_each_plan_has_its_own_64_hex_bundle():
    bundles = [legacy.BUNDLE, w.BUNDLE, c.BUNDLE]
    assert len(set(bundles)) == 3
    assert all(len(bundle) == 64 and set(bundle) <= set("0123456789abcdef") for bundle in bundles)


def test_bundle_for_names_the_bundle_of_the_plan_and_none_means_legacy():
    assert policy.bundle_for(None) == legacy.BUNDLE
    assert policy.bundle_for(WINDOWED) == w.BUNDLE
    assert policy.bundle_for(GLOBAL) == c.BUNDLE
    with pytest.raises(StageAiValidationError, match="v3_windowed_policy_changed_requires_fresh_run"):
        policy.bundle_for(dict(WINDOWED, bundle="0" * 64))


# --- a fresh start: the switch ---------------------------------------------------------------------------------------

def test_a_fresh_start_defaults_to_the_global_plan_with_its_bundle_and_limits(monkeypatch):
    monkeypatch.delenv(SWITCH, raising=False)
    assert policy.fresh_policy() == GLOBAL


@pytest.mark.parametrize("value,expected", [("windowed-v1", WINDOWED), ("windowed-global-v1", GLOBAL), ("legacy", None),
                                            ("  windowed-v1\n", WINDOWED), (" legacy ", None)])
def test_the_switch_selects_a_plan_by_its_name(monkeypatch, value, expected):
    monkeypatch.setenv(SWITCH, value)
    assert policy.fresh_policy() == expected


@pytest.mark.parametrize("value", ["", "   ", "windowed", "windowed-v2", "WINDOWED-V1", "native-text-v3/1", "global"])
def test_an_unsupported_switch_value_refuses_new_planning_instead_of_falling_back(monkeypatch, value):
    monkeypatch.setenv(SWITCH, value)
    with pytest.raises(StageAiValidationError, match="^v3_plan_configuration_unsupported$"):
        policy.fresh_policy()


def test_a_fresh_policy_is_a_copy_that_cannot_alter_the_limits_in_force(monkeypatch):
    monkeypatch.setenv(SWITCH, VERSION)
    fresh = policy.fresh_policy()
    fresh["limits"]["pages"] = 1
    assert LIMITS["pages"] == 64 and policy.fresh_policy()["limits"]["pages"] == 64


# --- a started run: the frozen authority -----------------------------------------------------------------------------------

def test_a_stored_authority_stays_valid_when_the_switch_later_says_legacy(monkeypatch):
    monkeypatch.setenv(SWITCH, "legacy")
    for stored in (WINDOWED, GLOBAL):
        accepted = policy.validate_policy(stored)
        assert accepted == stored and accepted is not stored
        accepted["limits"]["pages"] = 1
        assert stored["limits"]["pages"] == 64
    assert policy.validate_policy(None) is None


@pytest.mark.parametrize("stored", [
    dict(WINDOWED, bundle="0" * 64),                       # the code under the bundle changed
    dict(WINDOWED, limits=dict(LIMITS, pages=65)),         # the limits changed
    dict(WINDOWED, extra=1),
    {key: value for key, value in WINDOWED.items() if key != "limits"},
    dict(GLOBAL, bundle=w.BUNDLE),                         # one plan's bundle under the other's name
    dict(GLOBAL, limits=LIMITS),
    "windowed-v1", ["windowed-v1"], 1,
])
def test_changed_authority_requires_a_fresh_run(stored):
    with pytest.raises(StageAiValidationError, match="^v3_windowed_policy_changed_requires_fresh_run$"):
        policy.validate_policy(stored)


def test_an_unknown_plan_in_a_stored_authority_is_unsupported():
    with pytest.raises(StageAiValidationError, match="^v3_plan_configuration_unsupported$"):
        policy.validate_policy(dict(WINDOWED, plan_version="windowed-v9"))


HISTORICAL = {"plan_version": VERSION, "bundle": "a" * 64, "limits": {"pages": 64, "characters": 1}}


def test_history_is_read_as_stored_without_substituting_the_current_bundle():
    stored = policy.stored_policy(HISTORICAL)
    assert stored == HISTORICAL and stored is not HISTORICAL and stored["bundle"] != w.BUNDLE
    assert policy.stored_policy(None) is None
    with pytest.raises(StageAiValidationError, match="v3_windowed_policy_changed_requires_fresh_run"):
        policy.validate_policy(HISTORICAL)               # readable, but no new paid work under it


@pytest.mark.parametrize("stored", [
    dict(HISTORICAL, plan_version="native-text-v3/1"), dict(HISTORICAL, plan_version="legacy"),
    dict(HISTORICAL, bundle="a" * 63), dict(HISTORICAL, bundle="a" * 65), dict(HISTORICAL, bundle=1),
    dict(HISTORICAL, limits=[]), dict(HISTORICAL, extra=1),
    {key: value for key, value in HISTORICAL.items() if key != "bundle"},
    "windowed-v1", [], 0,
])
def test_a_malformed_saved_authority_is_refused_when_read(stored):
    with pytest.raises(StageAiValidationError, match="^v3_windowed_saved_policy_invalid$"):
        policy.stored_policy(stored)


class OneValue:
    """A session whose one query returns `value`; remembers the SQL and parameters it was asked."""
    def __init__(self, value):
        self.value, self.asked = value, []

    def execute(self, statement, parameters=None):
        self.asked.append((str(statement), parameters))
        return SimpleNamespace(scalar_one_or_none=lambda: self.value)


@pytest.mark.parametrize("reader,table,key", [(policy.policy_for_run, "stage_chain_run", "run"),
                                               (policy.policy_for_batch, "stage_chain_batch", "batch")])
def test_the_run_and_batch_readers_return_the_frozen_authority_or_none(reader, table, key):
    session = OneValue(GLOBAL)
    assert reader(session, "id-1") == GLOBAL
    sql, parameters = session.asked[0]
    assert table in sql and "stage_v3_policy" in sql and parameters == {key: "id-1"}
    assert reader(OneValue(None), "id-2") is None                 # no stored authority: the historical legacy path
    with pytest.raises(StageAiValidationError, match="v3_windowed_saved_policy_invalid"):
        reader(OneValue({"plan_version": "x"}), "id-3")


# --- the implementation behind a name ---------------------------------------------------------------------------------------

def test_the_bridge_picks_the_implementation_from_the_stored_plan_name():
    assert bridge._implementation(None) is legacy
    assert bridge._implementation(WINDOWED) is w
    assert bridge._implementation(GLOBAL) is c
    assert bridge._implementation(dict(WINDOWED, bundle="0" * 64)) is w     # picking is by name; validation is a separate gate


def test_the_method_reports_the_bundle_of_its_plan_and_validates_the_plan_on_creation():
    assert bridge.V3Method(None).bundle_version == legacy.BUNDLE
    assert bridge.V3Method(None, v3_policy=WINDOWED).bundle_version == w.BUNDLE
    assert bridge.V3Method(None, v3_policy=GLOBAL).bundle_version == c.BUNDLE
    assert bridge.V3Method(None, v3_policy=GLOBAL).v3_policy == GLOBAL
    with pytest.raises(StageAiValidationError, match="v3_windowed_policy_changed_requires_fresh_run"):
        bridge.V3Method(None, v3_policy=dict(GLOBAL, bundle="0" * 64))


class Mappings(list):
    def all(self):
        return list(self)


class Rows:
    """A session whose one query returns `rows` as mappings; remembers the SQL and parameters it was asked."""
    def __init__(self, rows):
        self.rows, self.asked = rows, []

    def execute(self, statement, parameters=None):
        self.asked.append((str(statement), parameters))
        return SimpleNamespace(mappings=lambda: Mappings(self.rows), scalar_one_or_none=lambda: None)


def test_saved_replies_are_read_only_under_the_requested_bundle_and_the_last_one_wins():
    rows = [
        {"group_id": "v3:mapper:catalogue", "progress": {"prompt_bundle_version": w.BUNDLE, "v3_result": {"n": 1}}},
        {"group_id": "v3:mapper:catalogue", "progress": {"prompt_bundle_version": w.BUNDLE, "v3_result": {"n": 2}}},
        {"group_id": "v3:miner:a", "progress": {"prompt_bundle_version": legacy.BUNDLE, "v3_result": {"n": 3}}},
        {"group_id": "v3:miner:b", "progress": {"prompt_bundle_version": w.BUNDLE}},                        # no reply yet
        {"group_id": "v3:miner:c", "progress": {"v3_result": {"n": 4}}},                                     # no bundle
        {"group_id": "v3:consolidate:z", "progress": {"prompt_bundle_version": c.BUNDLE, "v3_result": {"n": 5}}},
    ]
    session = Rows(rows)
    assert bridge.results(session, "run-1", bundle=w.BUNDLE) == {"v3:mapper:catalogue": {"n": 2}}
    assert bridge.results(session, "run-1", bundle=c.BUNDLE) == {"v3:consolidate:z": {"n": 5}}
    assert bridge.results(session, "run-1") == {"v3:miner:a": {"n": 3}}                  # default: the legacy bundle
    sql, parameters = session.asked[0]
    assert "state='completed'" in sql and "group_id LIKE 'v3:%'" in sql and parameters == {"run": "run-1"}


# --- progress shows the plan that is running ------------------------------------------------------------------------------------

def progress_rows(*rows):
    return [{"group_id": group, "state": state, "progress": progress or {}} for group, state, progress in rows]


NO_UNMATCHED = {"v3_result": {"unmatched_old": [], "unmatched_new": []}}


def progress_for(monkeypatch, stored, rows):
    monkeypatch.setattr(mode, "engine_for_run", lambda _session, _run: mode.ENGINE)
    monkeypatch.setattr(policy, "policy_for_run", lambda _session, _run: stored)
    return mode.experimental_progress(Rows(rows), "run-1")


def test_progress_of_a_running_windowed_plan_counts_known_units_and_shows_no_consolidator(monkeypatch):
    rows = progress_rows(("v3:mapper:catalogue", "completed", NO_UNMATCHED), ("v3:miner:a", "completed", None),
                         ("v3:miner:b", "running", None))
    shown = progress_for(monkeypatch, WINDOWED, rows)
    assert shown["plan_version"] == VERSION and shown["limits"] == LIMITS and shown["engine"] == mode.ENGINE
    by_name = {row["name"]: row for row in shown["procedures"]}
    assert list(by_name) == ["Mapper", "Miner", "Разбор непарных страниц", "Dedupe", "Проверка параметров", "Карточки V3"]
    assert (by_name["Miner"]["state"], by_name["Miner"]["planned"], by_name["Miner"]["completed"], by_name["Miner"]["pending"]) == (
        "running", 2, 1, 1)
    assert by_name["Mapper"]["state"] == "completed" and by_name["Разбор непарных страниц"]["state"] == "completed"
    assert by_name["Dedupe"]["state"] == "queued" and by_name["Dedupe"]["planned"] == 0      # not yet constructed: not counted
    assert (shown["planned_units"], shown["completed_units"], shown["pending_units"]) == (3, 2, 1)
    assert shown["procedure"] == "Miner" and shown["status"] == "running" and shown["coverage"] is None
    assert any("Удаление повторов выполняется внутри пакетов" in line for line in shown["limitations"])
    assert not any("Глобальный свод" in line for line in shown["limitations"])
    assert any("каталог всех страниц" in line for line in shown["limitations"])


def test_progress_of_the_global_plan_adds_the_consolidator_and_its_limitation(monkeypatch):
    rows = progress_rows(("v3:mapper:catalogue", "completed", NO_UNMATCHED), ("v3:consolidate:a", "completed", None),
                         ("v3:consolidate:b", "queued", None))
    shown = progress_for(monkeypatch, GLOBAL, rows)
    names = [row["name"] for row in shown["procedures"]]
    assert names == ["Mapper", "Miner", "Разбор непарных страниц", "Dedupe", "Проверка параметров", "Consolidator", "Карточки V3"]
    consolidator = shown["procedures"][names.index("Consolidator")]
    assert (consolidator["planned"], consolidator["completed"], consolidator["pending"]) == (2, 1, 1)
    assert shown["plan_version"] == GLOBAL_VERSION and shown["limits"] == GLOBAL_LIMITS
    assert any("Глобальный свод сравнивает ограниченные межпакетные кандидаты" in line for line in shown["limitations"])
    assert not any("Удаление повторов выполняется внутри пакетов" in line for line in shown["limitations"])


def test_progress_of_a_run_without_stored_authority_is_the_historical_native_plan(monkeypatch):
    shown = progress_for(monkeypatch, None, progress_rows(("v3:mapper:all", "completed", NO_UNMATCHED)))
    assert shown["plan_version"] == "native-text-v3/1" and shown["limits"] == {"pages": 16, "characters": 80000, "fragments": 400}
    assert [row["name"] for row in shown["procedures"]][-1] == "Карточки V3" and "Consolidator" not in str(shown["procedures"])
    assert len(shown["limitations"]) == 2


def test_a_finished_run_is_partial_when_coverage_is_incomplete_or_pairs_were_left_out_of_the_global_window(monkeypatch):
    def finished(stored, coverage):
        rows = progress_rows(("v3:mapper:catalogue", "completed", NO_UNMATCHED),
                             ("v3:final:cards", "completed", {"coverage": coverage, "source_report": {"x": 1}}))
        return progress_for(monkeypatch, stored, rows)
    assert finished(WINDOWED, {"complete": True})["status"] == "completed"
    assert finished(WINDOWED, {"complete": False})["status"] == "partial"
    assert finished(GLOBAL, {"complete": True, "global_consolidation": {"not_compared_pairs": 0}})["status"] == "completed"
    left_out = finished(GLOBAL, {"complete": True, "global_consolidation": {"not_compared_pairs": 64}})
    assert left_out["status"] == "partial" and left_out["source_report"] == {"x": 1}
    assert {row["state"] for row in left_out["procedures"]} == {"completed"}


def test_progress_exists_only_for_the_experimental_engine(monkeypatch):
    monkeypatch.setattr(mode, "engine_for_run", lambda _session, _run: mode.CLASSIC)
    assert mode.experimental_progress(Rows([]), "run-1") is None
