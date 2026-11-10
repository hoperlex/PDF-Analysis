"""Candidate rewrites of the optimisation counts of ``DocumentAuditReadModel.audits`` (``D-463``), on the same seed as ``perf_main.py``.

Every candidate is the shipped statement with ONE CTE replaced (built from the module's own constants), so the rest is identical. Each is run for the
page of 200, benchmarked cold/warm, EXPLAINed, and its rows compared with the shipped statement's rows over ALL versions of the page project.
It asserts the shape of the shipped ``_OPTIMISATION_RULE`` (``latest_pass AS`` and ``pass_undecided AS``) and stops when that is rewritten.
"""
from __future__ import annotations

import importlib
import json
import os
import sys
import time
from pathlib import Path

from sqlalchemy import bindparam, text

sys.path.insert(0, str(Path(__file__).parent))
import perf_main as pm  # noqa: E402
import perf_seed  # noqa: E402

A = importlib.import_module("auditmanager.dashboard.audit_state")
results = pm.results

assert "latest_pass AS" in A._OPTIMISATION_RULE and "pass_undecided AS" in A._OPTIMISATION_RULE
HEAD = A._OPTIMISATION_RULE[: A._OPTIMISATION_RULE.index("pass_undecided AS")]   # ", latest_pass AS (...), "

E1 = HEAD + """pass_undecided AS (
        SELECT lp.version_uid,
               lp.proposal_count - count(s.optimisation_proposal_id)
                   FILTER (WHERE s.last_revoke IS NULL OR s.last_revoke < s.last_any) AS undecided
        FROM latest_pass lp
        LEFT JOIN (
            SELECT q.optimisation_pass_id, d.optimisation_proposal_id,
                   max(d.seq) AS last_any,
                   max(d.seq) FILTER (WHERE d.verdict = 'revoke') AS last_revoke
            FROM optimisation_proposal_decision d
            JOIN optimisation_proposal q ON q.optimisation_proposal_id = d.optimisation_proposal_id
            WHERE q.optimisation_pass_id IN (SELECT optimisation_pass_id FROM latest_pass)
            GROUP BY q.optimisation_pass_id, d.optimisation_proposal_id
        ) s ON s.optimisation_pass_id = lp.optimisation_pass_id
        GROUP BY lp.version_uid, lp.proposal_count
    )"""

E2 = HEAD + """pass_undecided AS (
        SELECT lp.version_uid,
               lp.proposal_count - count(*) FILTER (WHERE cur.verdict <> 'revoke') AS undecided
        FROM latest_pass lp
        LEFT JOIN (
            SELECT DISTINCT ON (d.optimisation_proposal_id) d.optimisation_proposal_id, q.optimisation_pass_id, d.verdict
            FROM optimisation_proposal_decision d
            JOIN optimisation_proposal q ON q.optimisation_proposal_id = d.optimisation_proposal_id
            WHERE q.optimisation_pass_id IN (SELECT optimisation_pass_id FROM latest_pass)
            ORDER BY d.optimisation_proposal_id, d.seq DESC
        ) cur ON cur.optimisation_pass_id = lp.optimisation_pass_id
        GROUP BY lp.version_uid, lp.proposal_count
    )"""

# E3: E1 with the proposals of the passes taken first (a hint-free way to ask for the other join order)
E3 = HEAD + """pass_undecided AS (
        SELECT lp.version_uid,
               lp.proposal_count - count(s.optimisation_proposal_id)
                   FILTER (WHERE s.last_revoke IS NULL OR s.last_revoke < s.last_any) AS undecided
        FROM latest_pass lp
        LEFT JOIN (
            SELECT p.optimisation_pass_id, d.optimisation_proposal_id,
                   max(d.seq) AS last_any,
                   max(d.seq) FILTER (WHERE d.verdict = 'revoke') AS last_revoke
            FROM (SELECT q.optimisation_pass_id, q.optimisation_proposal_id FROM optimisation_proposal q
                   WHERE q.optimisation_pass_id IN (SELECT optimisation_pass_id FROM latest_pass) OFFSET 0) p
            JOIN optimisation_proposal_decision d ON d.optimisation_proposal_id = p.optimisation_proposal_id
            GROUP BY p.optimisation_pass_id, d.optimisation_proposal_id
        ) s ON s.optimisation_pass_id = lp.optimisation_pass_id
        GROUP BY lp.version_uid, lp.proposal_count
    )"""

TAIL = """
    SELECT cd.version_uid, rr.state AS result_state, rr.run_id,
           coalesce(vf.findings, 0) AS findings,
           coalesce(vf.undecided, 0) AS undecided,
           ar.run_id AS active_run_id, ar.state AS active_run_state,
           lp.proposal_count AS optimisation_proposals,
           CASE WHEN lp.version_uid IS NULL THEN NULL ELSE coalesce(pu.undecided, 0) END AS optimisation_undecided
    FROM current_docs cd
    LEFT JOIN result_run rr ON rr.version_uid = cd.version_uid
    LEFT JOIN version_findings vf ON vf.version_uid = cd.version_uid
    LEFT JOIN active_run ar ON ar.version_uid = cd.version_uid
    LEFT JOIN latest_pass lp ON lp.version_uid = cd.version_uid
    LEFT JOIN pass_undecided pu ON pu.version_uid = cd.version_uid
"""

# findings candidate: the verdict lateral only, instead of the whole finding_current_verdict view (four laterals per finding)
R1_RULES = A._RESULT_RUN_RULES.replace(
    """        FROM run_finding rf
        JOIN finding_current_verdict cv ON cv.finding_uid = rf.finding_uid
        GROUP BY rf.version_uid""",
    """        FROM run_finding rf
        LEFT JOIN LATERAL (
            SELECT e.verdict FROM expert_decision_event e
            WHERE e.finding_uid = rf.finding_uid AND e.verdict IS NOT NULL
            ORDER BY e.sequence_no DESC LIMIT 1
        ) lv ON TRUE
        GROUP BY rf.version_uid""",
).replace("cv.current_verdict IN ('pending', 'needs_manual_review')", "coalesce(lv.verdict, 'pending') IN ('pending', 'needs_manual_review')")
assert R1_RULES != A._RESULT_RUN_RULES


def statement(rules: str, optimisation: str) -> object:
    sql = A._CURRENT_DOCS_OF_VERSIONS + rules + A._ACTIVE_RUN_RULE + optimisation + TAIL
    return text(sql).bindparams(bindparam("version_uids", expanding=True))


def rows_of(stmt, names) -> list[tuple]:
    with pm.factory() as session:
        return sorted(tuple(r) for r in session.execute(stmt, {"version_uids": list(names)}).all())


def main() -> None:
    ids = perf_seed.prepare(pm.engine)
    perf_seed.seed_d463(pm.engine, ids)
    section: dict = {}
    results["exp"] = section
    with pm.factory() as session:
        versions = [r[0] for r in session.execute(text(
            "SELECT v.version_uid FROM document d JOIN document_version v ON v.version_uid = d.current_version_uid "
            "WHERE d.project_uid = :p ORDER BY v.version_uid"), {"p": ids["prj:1"]})]
        # a mixed bag: also the background project's versions, to cover versions with no pass and no run
        background = [r[0] for r in session.execute(text(
            "SELECT v.version_uid FROM document d JOIN document_version v ON v.version_uid = d.current_version_uid "
            "WHERE d.project_uid = :p ORDER BY v.version_uid"), {"p": ids["prj:2"]})]
    page200, everything = versions[:200], versions + background
    candidates = {
        "E0_shipped": statement(A._RESULT_RUN_RULES, A._OPTIMISATION_RULE),
        "E1_aggregate_over_decisions": statement(A._RESULT_RUN_RULES, E1),
        "E2_distinct_on_over_decisions": statement(A._RESULT_RUN_RULES, E2),
        "E3_proposals_first": statement(A._RESULT_RUN_RULES, E3),
        "E1_plus_R1_findings_lateral": statement(R1_RULES, E1),
        "R1_findings_lateral_only": statement(R1_RULES, A._OPTIMISATION_RULE),
    }
    reference = rows_of(candidates["E0_shipped"], everything)
    section["rows_compared"] = len(reference)
    section["optimisation_rows_with_a_pass"] = sum(1 for r in reference if r[7] is not None)
    section["distinct_undecided_values"] = len({r[8] for r in reference})
    for label, stmt in candidates.items():
        same = rows_of(stmt, everything) == reference
        figure = pm.bench(f"exp_{label}_page200", lambda stmt=stmt: rows_of(stmt, page200))
        figure["same_rows_as_shipped_over_all_versions"] = same
        figure["explain_warm"] = pm.explain_of(f"exp_{label}", lambda stmt=stmt: rows_of(stmt, page200))
        figure_all = pm.bench(f"exp_{label}_all{len(everything)}", lambda stmt=stmt: rows_of(stmt, everything), runs=3)
        figure["all_versions"] = figure_all
        section[label] = figure
        pm.save()
    # JIT share of the shipped statement
    for setting in ("on", "off"):
        pm.admin(f"ALTER DATABASE {os.environ.get('PERF_DB', 'am_perf')} SET jit = {setting}")
        pm.engine.dispose()
        figure = pm.bench(f"exp_E0_shipped_jit_{setting}", lambda: rows_of(candidates["E0_shipped"], page200))
        section[f"E0_shipped_jit_{setting}"] = figure
        figure = pm.bench(f"exp_E1_jit_{setting}", lambda: rows_of(candidates["E1_aggregate_over_decisions"], page200))
        section[f"E1_jit_{setting}"] = figure
    pm.admin(f"ALTER DATABASE {os.environ.get('PERF_DB', 'am_perf')} RESET jit")
    pm.engine.dispose()
    pm.save()
    # The counters' statement (dashboard, project list): whole deployment and the page project
    from auditmanager.dashboard import DocumentAuditReadModel
    model = DocumentAuditReadModel()
    for label, kwargs in (("groups_whole_deployment", {}), ("groups_page_project", {"project_uid": ids["prj:1"]})):
        def call(kwargs=kwargs):
            with pm.factory() as session:
                model.groups(session, **kwargs)
        figure = pm.bench(label, call)
        figure["explain_warm"] = pm.explain_of(label, call)
        section[label] = figure
    pm.save()
    # Decision counts of one pass as the repository states them, and the same by aggregation (for the note on list_passes)
    pm.save()


if __name__ == "__main__":
    t = time.time()
    main()
    results["total_seconds"] = round(time.time() - t, 1)
    pm.save()
