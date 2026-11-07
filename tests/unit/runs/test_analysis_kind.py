"""`AR-V3-OPT-IN` (design 4.4): which analysis produced a run, and the one predicate for «the result of a version».

The kind is the pinned pair and nothing else. The SQL spelling is run here on an in-memory table so that the condition
itself -- not a copy of its text -- is what is shown to separate the two analyses.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text

from auditmanager.analysis.public import AR_V3_BETA_BUNDLE_ID, AR_V3_BETA_PROFILE_ID
from auditmanager.analysis.text.profile_registry import load_text_profile_registry
from auditmanager.runs.analysis_kind import (
    ANALYSIS_AR_V3_BETA,
    ANALYSIS_STANDARD,
    STANDARD_RUN_SQL,
    analysis_kind,
)

V3 = (str(AR_V3_BETA_PROFILE_ID), str(AR_V3_BETA_BUNDLE_ID))


def test_the_sealed_pair_is_v3_and_nothing_else_is() -> None:
    assert analysis_kind(*V3) == ANALYSIS_AR_V3_BETA == "ar_v3_beta"
    other_profile, other_bundle = "ap_01M5M28ZCDD8VPSP1BTAEW92YF", "pb_01M5M28ZCDVCR37BX1884JGSPN"
    assert analysis_kind(other_profile, other_bundle) == ANALYSIS_STANDARD == "standard"
    # Half a pair is neither analysis' pair; it is not v3.
    assert analysis_kind(V3[0], other_bundle) == ANALYSIS_STANDARD
    assert analysis_kind(other_profile, V3[1]) == ANALYSIS_STANDARD
    assert analysis_kind(None, None) == ANALYSIS_STANDARD


def test_every_pair_of_the_sealed_section_table_is_standard_and_none_is_v3() -> None:
    """The route `startRun` and `reauditRun` take has no v3 entry, so the default path cannot produce a v3 run."""
    table = load_text_profile_registry().section_profiles()
    assert "AR" in table and len(table) >= 15
    assert V3 not in set(table.values())
    assert {analysis_kind(*pair) for pair in table.values()} == {ANALYSIS_STANDARD}


def _count(where: str | None, rows: list[tuple[str, str]]) -> int:
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE audit_run (analysis_profile_id TEXT, prompt_bundle_id TEXT)"))
        for profile, bundle in rows:
            connection.execute(
                text("INSERT INTO audit_run VALUES (:p, :b)"), {"p": profile, "b": bundle},
            )
        statement = "SELECT count(*) FROM audit_run r" + ("" if where is None else f" WHERE {where}")
        return int(connection.execute(text(statement)).scalar_one())


def test_the_sql_condition_keeps_standard_runs_and_drops_exactly_the_sealed_pair() -> None:
    standard = ("ap_01M5M28ZCDD8VPSP1BTAEW92YF", "pb_01M5M28ZCDVCR37BX1884JGSPN")
    rows = [standard, V3, V3, (V3[0], standard[1]), (standard[0], V3[1])]
    assert _count(None, rows) == 5
    assert _count(STANDARD_RUN_SQL, rows) == 3  # the standard run and the two half pairs
    assert _count(f"NOT ({STANDARD_RUN_SQL})", rows) == 2  # and the complement is exactly the two v3 runs


def test_the_sql_condition_is_the_python_test_over_the_same_rows() -> None:
    standard = ("ap_01M5M28ZCDD8VPSP1BTAEW92YF", "pb_01M5M28ZCDVCR37BX1884JGSPN")
    for pair in (standard, V3, (V3[0], standard[1]), (standard[0], V3[1])):
        assert _count(STANDARD_RUN_SQL, [pair]) == int(analysis_kind(*pair) == ANALYSIS_STANDARD), pair


def test_a_planted_wrong_condition_is_told_apart() -> None:
    """The proof the check can fail: a condition on the profile alone keeps a half pair this one drops, and the
    unconditioned statement keeps the v3 run."""
    standard = ("ap_01M5M28ZCDD8VPSP1BTAEW92YF", "pb_01M5M28ZCDVCR37BX1884JGSPN")
    rows = [standard, V3]
    assert _count(STANDARD_RUN_SQL, rows) == 1
    assert _count("1 = 1", rows) == 2
    assert _count(f"r.analysis_profile_id <> '{V3[0]}'", [(V3[0], standard[1])]) == 0
    assert _count(STANDARD_RUN_SQL, [(V3[0], standard[1])]) == 1


@pytest.mark.parametrize("fragment", [str(AR_V3_BETA_PROFILE_ID), str(AR_V3_BETA_BUNDLE_ID)])
def test_the_condition_names_both_halves_of_the_sealed_pair(fragment: str) -> None:
    assert fragment in STANDARD_RUN_SQL and STANDARD_RUN_SQL.startswith("NOT (")
