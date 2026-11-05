"""`UI-PARITY-P0B`: the audit state of a document and its counters, with no database.

Every case is stated from the owner's rulings (`R-150n` ... `R-150u`) and not read back from the module:

* `R-150n` a result run with no finding is `clean`, a state of its own;
* `R-150o` the red badge is `awaiting_decision`; the original's column «Нет решений эксперта» is
  `not_run + awaiting_decision` and never contains `clean`;
* `R-150p` the counted object is the current version (the SQL's join, asserted in the integration suite);
* `R-150r` a failed or cancelled run is not a result: the document is `not_run`;
* `R-150s` `published` and `partial` are both results and `partial` is a flag, not a fifth state;
* `R-150t` AR v3 groups use the per-run rule (a comment in the module, asserted below);
* `R-150u` optimisation is not part of the state: the function takes no such input.

The statement itself is judged on a real database in `tests/integration/dashboard/test_audit_state.py`.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from auditmanager.dashboard import audit_state as module
from auditmanager.dashboard.audit_state import (
    AUDIT_STATES,
    RESULT_RUN_STATES,
    UNDECIDED_VERDICTS,
    AuditCountsRecord,
    AuditGroupRecord,
    DocumentAuditState,
    audit_state,
    awaiting_decision_findings,
    counts_by_project,
    counts_by_section,
    tally,
)

# --- the state of one document -------------------------------------------------------------------


def test_a_current_version_with_no_result_run_is_not_run() -> None:
    """Never run, or run only to `failed` / `cancelled`, or only in flight: the read model reports no result."""
    assert audit_state(None, False, False) == DocumentAuditState("not_run", False)


def test_a_published_run_with_no_finding_is_clean_and_not_checked() -> None:
    """`R-150n`: its own state. It is neither `checked` nor `awaiting_decision`."""
    state = audit_state("published", False, False)
    assert state == DocumentAuditState("clean", False)
    assert state.state not in {"checked", "awaiting_decision", "not_run"}


def test_a_published_run_with_an_undecided_finding_is_awaiting_decision() -> None:
    assert audit_state("published", True, True) == DocumentAuditState("awaiting_decision", False)


def test_a_published_run_whose_every_finding_is_decided_is_checked() -> None:
    assert audit_state("published", True, False) == DocumentAuditState("checked", False)


@pytest.mark.parametrize(
    ("has_findings", "has_undecided", "expected"),
    [(False, False, "clean"), (True, True, "awaiting_decision"), (True, False, "checked")],
)
def test_a_partial_result_is_a_result_with_the_flag(
    has_findings: bool, has_undecided: bool, expected: str
) -> None:
    """`R-150s`: `partial` does not change the state, it marks it."""
    assert audit_state("partial", has_findings, has_undecided) == DocumentAuditState(expected, True)


@pytest.mark.parametrize("not_a_result", ["created", "queued", "running", "validating", "failed", "cancelled", "bogus"])
def test_a_run_that_is_not_a_result_is_refused_not_classified(not_a_result: str) -> None:
    """The read model never hands such a state to the function; one that arrived anyway is an error, not a
    quiet `not_run` (`AGENTS.md` section 4: no silent fallback)."""
    with pytest.raises(ValueError):
        audit_state(not_a_result, False, False)


def test_an_impossible_combination_is_refused() -> None:
    with pytest.raises(ValueError):
        audit_state("published", False, True)  # undecided findings without findings
    with pytest.raises(ValueError):
        audit_state(None, True, False)  # findings without a result run


def test_the_vocabularies_are_the_rulings() -> None:
    assert AUDIT_STATES == ("not_run", "clean", "awaiting_decision", "checked")
    assert RESULT_RUN_STATES == ("published", "partial")
    assert set(UNDECIDED_VERDICTS) == {"pending", "needs_manual_review"}


def test_the_statement_names_exactly_the_result_states_and_the_undecided_verdicts() -> None:
    """The SQL restates the two vocabularies; this is what keeps the two copies equal."""
    sql = str(module._AUDIT_GROUPS)
    assert "r.state IN ('published', 'partial')" in sql
    assert "cv.current_verdict IN ('pending', 'needs_manual_review')" in sql
    for excluded in ("'failed'", "'cancelled'", "'running'", "'queued'", "'created'", "'validating'"):
        assert excluded not in sql, f"{excluded} would make a run that is not a result one"


def test_the_result_run_is_the_latest_in_listruns_order() -> None:
    """`(created_at, run_id)` descending, the order `listRuns` returns (`runs.repository._LIST_RUNS_FOR_VERSION`)."""
    sql = " ".join(str(module._AUDIT_GROUPS).split())
    assert "ORDER BY r.version_uid, r.created_at DESC, r.run_id DESC" in sql
    assert "DISTINCT ON (r.version_uid)" in sql


def test_the_counted_object_is_the_current_version_only() -> None:
    """`R-150p`: the join through `document.current_version_uid`, the one `listProjects` counts through."""
    sql = " ".join(str(module._AUDIT_GROUPS).split())
    assert "JOIN document_version v ON v.version_uid = d.current_version_uid" in sql
    assert "r.version_uid IN (SELECT version_uid FROM current_docs)" in sql


def test_the_state_takes_no_optimisation_input_and_the_ar_v3_rule_is_cited() -> None:
    """`R-150u` and `R-150t`: the signature is findings only, and the module says why AR v3 groups are per run."""
    assert list(inspect.signature(audit_state).parameters) == ["result_state", "has_findings", "has_undecided"]
    source = Path(module.__file__).read_text(encoding="utf-8")
    assert "R-150t" in source and "R-150u" in source


# --- the counters -----------------------------------------------------------------------------------


def _group(
    state: str | None,
    *,
    documents: int = 1,
    findings: int = 0,
    undecided: int = 0,
    project: str = "prj_a",
    section: str | None = "AR",
) -> AuditGroupRecord:
    return AuditGroupRecord(
        project_uid=project,
        section=section,
        result_state=state,
        has_findings=findings > 0,
        has_undecided=undecided > 0,
        documents=documents,
        findings=findings,
        undecided_findings=undecided,
    )


def test_an_empty_tally_is_zero_everywhere() -> None:
    zero = tally([])
    assert zero == AuditCountsRecord()
    assert (zero.document_count, zero.no_expert_decision) == (0, 0)


def test_the_document_count_is_the_sum_of_the_four_states_and_partial_is_not_a_fifth() -> None:
    counts = tally(
        [
            _group(None, documents=4),
            _group("published", documents=2),  # clean
            _group("published", documents=3, findings=5, undecided=2),  # awaiting
            _group("published", documents=1, findings=2),  # checked
            _group("partial", documents=2, findings=1, undecided=1),  # awaiting + partial
            _group("partial", documents=1),  # clean + partial
        ]
    )
    assert (counts.not_run, counts.clean, counts.awaiting_decision, counts.checked) == (4, 3, 5, 1)
    assert counts.partial == 3
    assert counts.document_count == 13 == counts.not_run + counts.clean + counts.awaiting_decision + counts.checked


def test_no_expert_decision_is_not_run_plus_awaiting_and_never_clean() -> None:
    """`R-150o` / `R-150n`: the original's column counts everything not closed, never-run documents included,
    and does not count a run with no finding."""
    counts = tally([_group(None, documents=4), _group("published", documents=7), _group("published", findings=1, undecided=1, documents=3)])
    assert counts.clean == 7
    assert counts.no_expert_decision == counts.not_run + counts.awaiting_decision == 4 + 3 == 7
    assert counts.no_expert_decision != counts.document_count - counts.checked, "clean must not be inside it"


def test_a_failed_only_document_is_not_run_in_the_tally() -> None:
    """`R-150r`: the read model gives such a document no result state at all, so it is `not_run`."""
    assert tally([_group(None, documents=2)]).not_run == 2


def test_counts_are_grouped_by_project_and_a_project_without_documents_is_absent() -> None:
    by_project = counts_by_project(
        [
            _group(None, project="prj_a"),
            _group("published", project="prj_a", findings=1, undecided=1),
            _group("published", project="prj_b"),
        ]
    )
    assert set(by_project) == {"prj_a", "prj_b"}
    assert (by_project["prj_a"].document_count, by_project["prj_a"].awaiting_decision) == (2, 1)
    assert (by_project["prj_b"].clean, by_project["prj_b"].document_count) == (1, 1)


def test_sections_carry_their_documents_and_the_findings_of_their_result_runs() -> None:
    by_section = counts_by_section(
        [
            _group("published", section="AR", documents=2, findings=7, undecided=3),
            _group(None, section="AR", documents=1),
            _group("published", section=None, documents=1, findings=2),
        ]
    )
    assert by_section["AR"].counts.document_count == 3 and by_section["AR"].finding_count == 7
    assert by_section[None].counts.checked == 1 and by_section[None].finding_count == 2
    assert "KJ" not in by_section


def test_the_findings_tile_sums_only_undecided_findings_of_the_groups() -> None:
    groups = [
        _group("published", documents=2, findings=7, undecided=3),
        _group("partial", findings=2, undecided=2),
        _group("published", findings=4),  # checked: contributes nothing
        _group(None),
    ]
    assert awaiting_decision_findings(groups) == 5
    assert awaiting_decision_findings([]) == 0


def test_the_three_outputs_tally_the_same_groups_the_same_way() -> None:
    """One function, three views: whatever the grouping, the totals are the totals."""
    groups = [
        _group(None, project="prj_a", section="AR", documents=2),
        _group("published", project="prj_a", section="KJ", documents=1, findings=3, undecided=1),
        _group("partial", project="prj_b", section=None, documents=2, findings=1),
        _group("published", project="prj_b", section="AR"),
    ]
    whole = tally(groups)
    assert sum(c.document_count for c in counts_by_project(groups).values()) == whole.document_count
    assert sum(c.counts.document_count for c in counts_by_section(groups).values()) == whole.document_count
    assert sum(c.awaiting_decision for c in counts_by_project(groups).values()) == whole.awaiting_decision
    assert sum(c.counts.partial for c in counts_by_section(groups).values()) == whole.partial == 2
    assert awaiting_decision_findings(groups) == 1
