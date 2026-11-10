"""The shipped statement AFTER the ``D-463`` rewrite, against the base statement, on the seed of ``perf_main.py``.

* ``pm.d463`` (perf_main): the same figures, through the shipped ``DocumentAuditReadModel.audits``.
* A/B on the SAME database: the statement before ``D-463`` (``_OPTIMISATION_RULE`` of tree ``672609ab1``, kept here verbatim as
  ``BASE_OPTIMISATION_RULE``) against the shipped one, over a
  page of 200 heavy documents, a page of 50, the whole page project, a realistic page (10 heavy AR documents among 160) and everything,
  with the rows compared over all 700 versions.
* The finding-verdict candidate (R1: the verdict lateral instead of the four of ``finding_current_verdict``) on ``audits`` and on the
  counters' ``groups`` statement, rows compared with the shipped ones.
"""
from __future__ import annotations

import importlib
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

#: `_OPTIMISATION_RULE` of the base tree 672609ab1, verbatim.
BASE_OPTIMISATION_RULE = """,
    latest_pass AS (
        SELECT DISTINCT ON (p.version_uid) p.version_uid, p.optimisation_pass_id, p.proposal_count
        FROM optimisation_pass p
        WHERE p.version_uid IN (SELECT version_uid FROM current_docs)
        ORDER BY p.version_uid, p.started_at DESC, p.optimisation_pass_id DESC
    ),
    pass_undecided AS (
        SELECT lp.version_uid, count(*) AS undecided
        FROM latest_pass lp
        JOIN optimisation_proposal q ON q.optimisation_pass_id = lp.optimisation_pass_id
        LEFT JOIN LATERAL (
            SELECT d.verdict FROM optimisation_proposal_decision d
            WHERE d.optimisation_proposal_id = q.optimisation_proposal_id
            ORDER BY d.seq DESC LIMIT 1
        ) cur ON TRUE
        WHERE cur.verdict IS NULL OR cur.verdict = 'revoke'
        GROUP BY lp.version_uid
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

R1_OLD = """        FROM run_finding rf
        JOIN finding_current_verdict cv ON cv.finding_uid = rf.finding_uid
        GROUP BY rf.version_uid"""
R1_NEW = """        FROM run_finding rf
        LEFT JOIN LATERAL (
            SELECT e.verdict FROM expert_decision_event e
            WHERE e.finding_uid = rf.finding_uid AND e.verdict IS NOT NULL
            ORDER BY e.sequence_no DESC LIMIT 1
        ) lv ON TRUE
        GROUP BY rf.version_uid"""


def r1(rules: str) -> str:
    assert R1_OLD in rules
    return rules.replace(R1_OLD, R1_NEW).replace(
        "cv.current_verdict IN ('pending', 'needs_manual_review')", "coalesce(lv.verdict, 'pending') IN ('pending', 'needs_manual_review')")


def audits_statement(rules: str, optimisation: str):
    return text(A._CURRENT_DOCS_OF_VERSIONS + rules + A._ACTIVE_RUN_RULE + optimisation + TAIL).bindparams(
        bindparam("version_uids", expanding=True))


def rows_of(stmt, names) -> list[tuple]:
    with pm.factory() as session:
        return sorted(tuple(r) for r in session.execute(stmt, {"version_uids": list(names)}).all())


def main() -> None:
    ids = perf_seed.prepare(pm.engine)
    perf_seed.seed_d463(pm.engine, ids)
    results["seed_d463_seconds"] = 0
    pm.d463(ids)  # the shipped code, same figures as run-full
    section: dict = {}
    results["final"] = section
    with pm.factory() as session:
        def versions_of(project: str, where: str = "TRUE") -> list[str]:
            return [r[0] for r in session.execute(text(
                "SELECT v.version_uid FROM document d JOIN document_version v ON v.version_uid = d.current_version_uid "
                "LEFT JOIN document_version_classification c ON c.version_uid = v.version_uid "
                f"WHERE d.project_uid = :p AND {where} ORDER BY v.version_uid"), {"p": project})]
        p1 = versions_of(ids["prj:1"])
        p2_with_pass = [r[0] for r in session.execute(text(
            "SELECT v.version_uid FROM optimisation_pass s JOIN document_version v ON v.version_uid = s.version_uid "
            "JOIN document d ON d.current_version_uid = v.version_uid WHERE s.project_uid = :p ORDER BY 1"), {"p": ids["prj:2"]})]
        p2_all = versions_of(ids["prj:2"])
    p2_without = [v for v in p2_all if v not in set(p2_with_pass)]
    sets = {
        "page200_heavy": p1[:200], "page50_heavy": p1[:50], "project_400_heavy": p1,
        "realistic": p1[:10] + p2_without[:150] + p2_with_pass[:10], "everything": p1 + p2_all,
    }
    section["set_sizes"] = {k: len(v) for k, v in sets.items()}
    variants = {
        "base": audits_statement(A._RESULT_RUN_RULES, BASE_OPTIMISATION_RULE),
        "shipped": audits_statement(A._RESULT_RUN_RULES, A._OPTIMISATION_RULE),
        "shipped_plus_R1": audits_statement(r1(A._RESULT_RUN_RULES), A._OPTIMISATION_RULE),
    }
    reference = rows_of(variants["base"], sets["everything"])
    section["rows_compared"] = len(reference)
    section["rows_with_a_pass"] = sum(1 for r in reference if r[7] is not None)
    for name, stmt in variants.items():
        section[f"rows_equal_to_base_{name}"] = rows_of(stmt, sets["everything"]) == reference
    pm.save()
    for set_name, names in sets.items():
        for name, stmt in variants.items():
            runs = 3 if set_name == "everything" else pm.RUNS
            figure = pm.bench(f"final_{name}_{set_name}", lambda stmt=stmt, names=names: rows_of(stmt, names), runs=runs)
            if set_name in ("page200_heavy", "realistic"):
                figure["explain_warm"] = pm.explain_of(f"final_{name}_{set_name}", lambda stmt=stmt, names=names: rows_of(stmt, names))
            section[f"{name}__{set_name}"] = figure
        pm.save()
    # the counters' statement, with and without R1
    from auditmanager.dashboard import DocumentAuditReadModel
    model = DocumentAuditReadModel()
    groups_base = A._AUDIT_GROUPS
    groups_r1 = text(str(groups_base).replace(R1_OLD, R1_NEW).replace(
        "cv.current_verdict IN ('pending', 'needs_manual_review')", "coalesce(lv.verdict, 'pending') IN ('pending', 'needs_manual_review')"))
    assert str(groups_r1) != str(groups_base)

    def groups(stmt, project=None):
        def call():
            with pm.factory() as session:
                return sorted(tuple(r) for r in session.execute(stmt, {"project_uid": project}).all())
        return call

    section["groups_rows_equal_with_R1"] = groups(groups_base)() == groups(groups_r1)()
    for label, project in (("whole_deployment", None), ("page_project", ids["prj:1"])):
        for name, stmt in (("shipped", groups_base), ("R1", groups_r1)):
            figure = pm.bench(f"final_groups_{name}_{label}", groups(stmt, project))
            figure["explain_warm"] = pm.explain_of(f"final_groups_{name}_{label}", groups(stmt, project))
            section[f"groups_{name}__{label}"] = figure
    pm.save()


if __name__ == "__main__":
    t = time.time()
    main()
    results["total_seconds"] = round(time.time() - t, 1)
    pm.save()
