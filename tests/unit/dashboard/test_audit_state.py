"""`UI-PARITY-P0B`: the audit state of a document and its counters, with no database.

Every case is stated from the owner's rulings (`R-150n` ... `R-150u`) and not read back from the module:

* `R-150n` a result run with no finding is `clean`, a state of its own;
* `R-150o` the red badge is `awaiting_decision`; the original's column «Нет решений эксперта» is
  `not_run + awaiting_decision` and never contains `clean`;
* `R-150p` the counted object is the current version (the SQL's join, asserted in the integration suite);
* `R-150r` a failed or cancelled run is not a result: the document is `not_run`;
* `R-150s` `published` and `partial` are both results and `partial` is a flag, not a fifth state;
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
    DocumentAuditRecord,
    DocumentAuditState,
    audit_order_key,
    audit_order_rank,
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


def test_the_state_takes_no_optimisation_input_and_the_rule_is_cited() -> None:
    """`R-150u`: the signature is findings only, and the module says why."""
    assert list(inspect.signature(audit_state).parameters) == ["result_state", "has_findings", "has_undecided"]
    source = Path(module.__file__).read_text(encoding="utf-8")
    assert "R-150u" in source


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


# --- the audit of one listed version and the order of a listing (`UI-PARITY-DOC-AUDIT`) -----------------


def test_the_two_statements_share_one_copy_of_the_rules() -> None:
    """The per-document read is the counters' rules with another scope, not a second copy of them (`UI-A-46`)."""
    groups = " ".join(str(module._AUDIT_GROUPS).split())
    audits = " ".join(str(module._DOCUMENT_AUDITS).split())
    tail = " ".join(module._RESULT_RUN_RULES.split())
    assert tail in groups and tail in audits, "the result-run rule and the undecided rule are written once"
    assert "r.state IN ('published', 'partial')" in audits
    assert "cv.current_verdict IN ('pending', 'needs_manual_review')" in audits
    assert "ORDER BY r.version_uid, r.created_at DESC, r.run_id DESC" in audits
    # The scope differs exactly where it should: the counters leave an archived document out, a listing that was
    # asked to show one says what state it is in.
    assert "archived_at IS NULL" in groups and "archived_at" not in audits
    # (the compiled statement spells the expanding bind its own way, so the scope is read from its source)
    assert "v.version_uid IN :version_uids" in " ".join(module._CURRENT_DOCS_OF_VERSIONS.split())
    assert "project_uid" not in audits


def test_the_undecided_proposals_are_counted_in_one_pass_over_the_decisions_and_not_by_a_probe_each() -> None:
    """`D-463`: the latest decision of a proposal decides, and it is found for all the proposals of the page's passes at once.

    The first form of the statement looked the latest decision up with a ``LATERAL`` probe per proposal (106,000 probes for a
    page of 200 documents of ~530 proposals: 0.83 s). A guard on the shape, not on the time -- the time is the stand's
    (`DEBT_REGISTER.md` `D-463`); the answers are compared with the old form, proposal by proposal, in
    ``tests/integration/dashboard/test_document_audit_optimisation_counts.py``.
    """
    sql = " ".join(module._OPTIMISATION_RULE.split())
    assert "LATERAL" not in sql, "a per-proposal probe is the form `D-463` replaced"
    assert "SELECT DISTINCT ON (d.optimisation_proposal_id)" in sql
    assert "ORDER BY d.optimisation_proposal_id, d.seq DESC" in sql
    # a withdrawal (`revoke`) is the one verdict that leaves a proposal undecided; the pass's own count is the base
    assert "lp.proposal_count - count(*) FILTER (WHERE cur.verdict <> 'revoke')" in sql
    # the latest pass is still chosen by (started_at DESC, optimisation_pass_id DESC) and the counters' statement still reads none of it
    assert "ORDER BY p.version_uid, p.started_at DESC, p.optimisation_pass_id DESC" in sql
    assert "optimisation" not in " ".join(str(module._AUDIT_GROUPS).split())


def _record(result: str | None, findings: int = 0, undecided: int = 0) -> DocumentAuditRecord:
    return DocumentAuditRecord(
        version_uid="ver_x",
        result_state=result,
        result_run_id=None if result is None else "run_x",
        finding_count=findings,
        undecided_finding_count=undecided,
    )


def test_a_document_audit_record_classifies_through_the_one_function() -> None:
    assert (_record(None).state, _record(None).partial) == ("not_run", False)
    assert (_record("published").state, _record("published").partial) == ("clean", False)
    assert (_record("published", 3, 1).state, _record("published", 3, 1).partial) == ("awaiting_decision", False)
    assert (_record("published", 3, 0).state, _record("published", 3, 0).partial) == ("checked", False)
    assert (_record("partial", 2, 0).state, _record("partial", 2, 0).partial) == ("checked", True)
    assert (_record("partial").state, _record("partial").partial) == ("clean", True)
    for result, findings, undecided in (("published", 2, 1), ("partial", 0, 0), (None, 0, 0)):
        record = _record(result, findings, undecided)
        assert record.audit == audit_state(result, findings > 0, undecided > 0)


def test_the_order_ranks_are_the_originals_projectorderrank() -> None:
    """0 checked by the expert, 1 processed without every verdict (clean or awaiting), 2 never audited (`UI-A-49`)."""
    assert [audit_order_rank(state) for state in AUDIT_STATES] == [2, 1, 1, 0]
    with pytest.raises(ValueError):
        audit_order_rank("failed")


def _ordered(rows: list[tuple[str, str | None]]) -> list[str | None]:
    keyed = [(audit_order_key(state, name, f"ver_{index:02d}"), name) for index, (state, name) in enumerate(rows)]
    return [name for _, name in sorted(keyed)]


def test_the_rank_decides_before_the_name() -> None:
    rows = [
        ("not_run", "А"),
        ("clean", "Б"),
        ("checked", "Я"),
        ("awaiting_decision", "В"),
        ("not_run", "Б"),
        ("checked", "Г"),
    ]
    assert _ordered(rows) == ["Г", "Я", "Б", "В", "А", "Б"]
    states = [state for state, _ in sorted(rows, key=lambda row: audit_order_key(row[0], row[1], row[1] or ""))]
    assert states == ["checked", "checked", "clean", "awaiting_decision", "not_run", "not_run"]


def test_names_compare_the_way_the_original_collator_does() -> None:
    """``Intl.Collator('ru', {numeric: true, sensitivity: 'base'})``: digits as numbers, case and accents ignored."""
    assert _ordered([("clean", "АР1-10"), ("clean", "АР1-2"), ("clean", "АР1-1")]) == ["АР1-1", "АР1-2", "АР1-10"]
    assert _ordered([("clean", "Лист 10"), ("clean", "лист 9"), ("clean", "Лист 100")]) == ["лист 9", "Лист 10", "Лист 100"]
    # Case is ignored, so a lower-case name does not sort after every capital.
    assert _ordered([("clean", "бетон"), ("clean", "Арматура"), ("clean", "Вода")]) == ["Арматура", "бетон", "Вода"]
    # «ё» is «е» and «й» is «и»: neither is sorted to the end of the alphabet.
    assert _ordered([("clean", "Жук"), ("clean", "Ёлка"), ("clean", "Елка а"), ("clean", "Ёж")]) == ["Ёж", "Ёлка", "Елка а", "Жук"]
    assert _ordered([("clean", "Йод"), ("clean", "Икс"), ("clean", "Кит")]) == ["Икс", "Йод", "Кит"]
    # A digit run sorts before a letter run; Latin before Cyrillic.
    assert _ordered([("clean", "Альфа"), ("clean", "Alpha"), ("clean", "1 лист")]) == ["1 лист", "Alpha", "Альфа"]


def test_a_name_the_collator_calls_equal_still_has_one_total_order() -> None:
    """The cursor of the listing is built on the identity, so two equal names must not be left to chance."""
    first = audit_order_key("clean", "АР1", "ver_a")
    second = audit_order_key("clean", "ар1", "ver_b")
    assert first < second and first[:2] == second[:2]
    assert audit_order_key("clean", None, "ver_a")[:2] == audit_order_key("clean", "", "ver_b")[:2]
