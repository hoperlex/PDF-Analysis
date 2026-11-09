"""`D-574`: the decision counts of a pass are taken in one pass over the decisions, by every statement that returns a pass.

Container-free: a guard on the shape of the SQL, not on its time (the time is the stand's, `DEBT_REGISTER.md` `D-574`) and not on
its answers (those are compared with the old per-proposal statement and with a replay of the histories in
``tests/integration/optimisation/proposals/test_decision_counts_one_pass.py``).
"""

from __future__ import annotations

import re

import pytest

from auditmanager.optimisation.proposals import policy, repository

STATEMENTS = {
    "_SELECT_PASS": repository._SELECT_PASS,
    "_FIND_PASS": repository._FIND_PASS,
    "_LIST_PASSES": repository._LIST_PASSES,
}


def _flat(sql: str) -> str:
    return " ".join(sql.split())


@pytest.mark.parametrize("name", sorted(STATEMENTS))
def test_no_statement_looks_the_latest_decision_up_once_per_proposal(name: str) -> None:
    """The first form probed the decision index once per proposal of every returned pass (200 passes x ~530 proposals: 0.7 s)."""
    sql = _flat(STATEMENTS[name].text)
    assert "LATERAL" not in sql, "a per-proposal probe is the form `D-574` replaced"
    assert "SELECT DISTINCT ON (d.optimisation_proposal_id) q.optimisation_pass_id, d.verdict" in sql
    assert "ORDER BY d.optimisation_proposal_id, d.seq DESC" in sql


@pytest.mark.parametrize("name", sorted(STATEMENTS))
def test_every_statement_carries_the_one_tally(name: str) -> None:
    assert _flat(repository._TALLY) in _flat(STATEMENTS[name].text), "the counting rule is written once"


def test_a_withdrawal_is_the_one_verdict_that_is_not_decided_and_the_pass_count_is_the_base() -> None:
    sql = _flat(repository._TALLY)
    assert f"WHERE verdict <> '{policy.VERDICT_REVOKE}'" in sql
    assert f"'{policy.DECISION_PENDING}'" in sql
    assert "c.proposal_count - coalesce(sum(x.n), 0)" in sql
    assert "WHERE k.n > 0" in sql, "a state nobody holds is no key, as the per-proposal form answered"
    assert (policy.VERDICT_REVOKE, policy.DECISION_PENDING) == ("revoke", "pending")
    assert policy.VERDICT_REVOKE not in policy.VERDICTS


def test_the_page_is_cut_before_the_decisions_are_read() -> None:
    """``chosen`` holds the passes the caller gets; the decisions are read for those only."""
    sql = _flat(repository._LIST_PASSES.text)
    assert sql.index("LIMIT :limit") < sql.index("latest AS (")
    assert "WHERE q.optimisation_pass_id IN (SELECT optimisation_pass_id FROM chosen)" in sql
    # the cut order is repeated on the joined result: a join promises no order
    assert sql.endswith("ORDER BY c.started_at DESC, c.optimisation_pass_id DESC")


def test_the_columns_are_the_ones_the_reader_takes_by_position() -> None:
    """``_pass`` reads the row by index: eighteen stored columns, the counts, then the version's ordinal."""
    out = [part.strip() for part in repository._PASS_COLUMNS.split(",")]
    chosen = [part.strip() for part in repository._CHOSEN_COLUMNS.split(",")]
    assert len(out) == 20 and len(chosen) == 19
    assert [name.split(".", 1)[1] for name in out[:18]] == [name.split(".", 1)[1] for name in chosen[:18]]
    assert out[18] == "t.decision_counts" and out[19] == "c.version_ordinal" and chosen[18] == "v.version_ordinal"
    assert re.fullmatch(r"s\.[a-z_0-9]+", chosen[0]) and chosen[15] == "s.proposal_count"
