"""Candidate rewrites of the counters' statement (``D-572``, ``_AUDIT_GROUPS``) and of the pass's ``decision_counts`` (``D-574``), on the 700-document
seed (``perf_seed.py``). Every candidate is built from the module's own constants; rows are compared with the shipped statement's rows; each is
benchmarked cold/warm and EXPLAINed. Nothing here changes the repository.

The candidates are built by REPLACING a text block of the shipped statement (``assert old_rf in rules``): when the statement is rewritten, the
assertion stops this driver on purpose, and the candidates have to be re-derived from the new text. The results it produced are in the
README of this directory."""
from __future__ import annotations

import importlib
import json
import sys
import time

from sqlalchemy import text

import perf_lib as lib
import perf_seed
from perf_lib import admin, bench, explain, explain_of, factory, log, norm, results, save

A = importlib.import_module("auditmanager.dashboard.audit_state")
oprepo = importlib.import_module("auditmanager.optimisation.proposals.repository")


def d572(ids) -> None:
    section: dict = {}
    results["d572"] = section
    base_text = A._AUDIT_GROUPS.text
    head = A._CURRENT_DOCS_OF_A_PROJECT_OR_ALL
    rules = A._RESULT_RUN_RULES
    assert base_text == head + rules + base_text[len(head) + len(rules):]
    tail = base_text[len(head) + len(rules):]

    old_rf = """    run_finding AS (
        SELECT rr.version_uid, o.finding_uid
        FROM result_run rr
        JOIN finding_observation o ON o.run_id = rr.run_id
        JOIN finding f ON f.finding_uid = o.finding_uid
        GROUP BY rr.version_uid, o.finding_uid
    ),"""
    assert old_rf in rules
    new_rf = """    run_finding AS (
        SELECT rr.version_uid, o.finding_uid
        FROM result_run rr
        JOIN finding_observation o ON o.run_id = rr.run_id
        WHERE o.finding_uid IS NOT NULL
        GROUP BY rr.version_uid, o.finding_uid
    ),"""
    C1 = rules.replace(old_rf, new_rf)

    old_vf = """        FROM run_finding rf
        JOIN finding_current_verdict cv ON cv.finding_uid = rf.finding_uid
        GROUP BY rf.version_uid"""
    assert old_vf in rules
    # R1 (information only: it writes the verdict rule a second time)
    r1_new = """        FROM run_finding rf
        LEFT JOIN LATERAL (
            SELECT e.verdict FROM expert_decision_event e
            WHERE e.finding_uid = rf.finding_uid AND e.verdict IS NOT NULL
            ORDER BY e.sequence_no DESC LIMIT 1
        ) lv ON TRUE
        GROUP BY rf.version_uid"""
    cvcond = "cv.current_verdict IN ('pending', 'needs_manual_review')"
    assert cvcond in rules
    R1 = rules.replace(old_vf, r1_new).replace(cvcond, "coalesce(lv.verdict, 'pending') IN ('pending', 'needs_manual_review')")
    C1_R1 = C1.replace(old_vf, r1_new).replace(cvcond, "coalesce(lv.verdict, 'pending') IN ('pending', 'needs_manual_review')")

    # C2: view read through a lateral that names only the verdict column
    c2_new = """        FROM run_finding rf
        CROSS JOIN LATERAL (SELECT cv0.current_verdict FROM finding_current_verdict cv0 WHERE cv0.finding_uid = rf.finding_uid) cv
        GROUP BY rf.version_uid"""
    C2 = C1.replace(old_vf, c2_new)

    # C3: one pass over the observations, no per-version grouping step before the verdict join (dedupe by DISTINCT inside the join input)
    c3_rf = """    run_finding AS MATERIALIZED (
        SELECT rr.version_uid, o.finding_uid
        FROM result_run rr
        JOIN finding_observation o ON o.run_id = rr.run_id
        WHERE o.finding_uid IS NOT NULL
        GROUP BY rr.version_uid, o.finding_uid
    ),"""
    C3 = rules.replace(old_rf, c3_rf)

    def stmt(rules_text: str) -> str:
        return head + rules_text + tail

    variants = {"base": stmt(rules), "C1_no_finding_join": stmt(C1), "C2_C1_lateral_verdict": stmt(C2), "C3_materialized_rf": stmt(C3),
                "R1_info_rule_twice": stmt(R1), "C1_R1_info": stmt(C1_R1)}

    def run(sql: str, project):
        def call():
            with factory() as session:
                return norm(session.execute(text(sql), {"project_uid": project}).all())
        return call

    reference = {"all": run(variants["base"], None)(), "p1": run(variants["base"], ids["prj:1"])()}
    section["rows"] = {k: len(v) for k, v in reference.items()}
    section["reference_findings_sum"] = {k: sum(int(r[6]) for r in v) for k, v in reference.items()}
    section["equal"] = {}
    for name, sql in variants.items():
        section["equal"][name] = {"all": run(sql, None)() == reference["all"], "p1": run(sql, ids["prj:1"])() == reference["p1"]}
    save()
    log(f"d572 equal: {section['equal']}")

    # does Postgres drop the unused lateral probes of the view?
    one = admin("SELECT finding_uid FROM finding LIMIT 1")[0][0]
    plan = admin("EXPLAIN SELECT cv.current_verdict FROM finding_current_verdict cv WHERE cv.finding_uid = '%s'" % one)
    section["view_plan_for_one_finding_verdict_only"] = [r[0] for r in plan]

    for name, sql in variants.items():
        for label, project in (("whole", None), ("project", ids["prj:1"])):
            figure = bench(f"d572_{name}_{label}", run(sql, project))
            figure["explain_warm"] = explain_of(f"d572_{name}_{label}", run(sql, project))
            section[f"{name}__{label}"] = figure
        save()
    # JIT share of the shipped statement
    admin("ALTER DATABASE %s SET jit = off" % admin("SELECT current_database()")[0][0])
    lib.engine.dispose()
    for name in ("base", "C1_no_finding_join"):
        figure = bench(f"d572_{name}_whole_jit_off", run(variants[name], None))
        section[f"{name}__whole_jit_off"] = figure
    admin("ALTER DATABASE %s RESET jit" % admin("SELECT current_database()")[0][0])
    lib.engine.dispose()
    save()


# ----------------------------------------------------------------------------------------------------------------------------------
_PASS_COLS = ("optimisation_pass_id, project_uid, document_uid, version_uid, run_id, text_layer_sha256, price_list_id, vendor_list_id, "
              "vendor_list_source, extraction_algorithm, match_algorithm, generator_version, specification_row_count, matched_row_count, "
              "proposed_row_count, proposal_count, started_by_user_uid, started_at")

LATEST_T2 = """
    latest AS (
        SELECT DISTINCT ON (d.optimisation_proposal_id) q.optimisation_pass_id, d.verdict
        FROM optimisation_proposal_decision d
        JOIN optimisation_proposal q ON q.optimisation_proposal_id = d.optimisation_proposal_id
        WHERE q.optimisation_pass_id IN (SELECT optimisation_pass_id FROM chosen)
        ORDER BY d.optimisation_proposal_id, d.seq DESC
    ),
    decided AS (
        SELECT optimisation_pass_id, verdict, count(*) AS n FROM latest WHERE verdict <> 'revoke' GROUP BY 1, 2
    ),
    tally AS (
        SELECT t.optimisation_pass_id, jsonb_object_agg(t.verdict, t.n) AS decision_counts
        FROM (
            SELECT optimisation_pass_id, verdict, n FROM decided
            UNION ALL
            SELECT c.optimisation_pass_id, 'pending', c.proposal_count - coalesce(sum(x.n), 0)
            FROM chosen c LEFT JOIN decided x ON x.optimisation_pass_id = c.optimisation_pass_id
            GROUP BY c.optimisation_pass_id, c.proposal_count
        ) t
        WHERE t.n > 0
        GROUP BY t.optimisation_pass_id
    )"""

# T1: proposals left-joined to their latest decision, grouped (keeps the old grouping literally; reads the proposals of the passes)
LATEST_T1 = """
    latest AS (
        SELECT DISTINCT ON (d.optimisation_proposal_id) d.optimisation_proposal_id, d.verdict
        FROM optimisation_proposal_decision d
        JOIN optimisation_proposal q ON q.optimisation_proposal_id = d.optimisation_proposal_id
        WHERE q.optimisation_pass_id IN (SELECT optimisation_pass_id FROM chosen)
        ORDER BY d.optimisation_proposal_id, d.seq DESC
    ),
    tally AS (
        SELECT k.optimisation_pass_id, jsonb_object_agg(k.verdict, k.n) AS decision_counts
        FROM (
            SELECT q.optimisation_pass_id, COALESCE(NULLIF(l.verdict, 'revoke'), 'pending') AS verdict, count(*) AS n
            FROM optimisation_proposal q
            LEFT JOIN latest l ON l.optimisation_proposal_id = q.optimisation_proposal_id
            WHERE q.optimisation_pass_id IN (SELECT optimisation_pass_id FROM chosen)
            GROUP BY 1, 2
        ) k
        GROUP BY k.optimisation_pass_id
    )"""


def pass_statement(latest_sql: str, where: str, order_limit: str, outer_order: str) -> str:
    return f"""
    WITH chosen AS (
        SELECT s.optimisation_pass_id, s.project_uid, s.document_uid, s.version_uid, s.run_id, s.text_layer_sha256, s.price_list_id,
               s.vendor_list_id, s.vendor_list_source, s.extraction_algorithm, s.match_algorithm, s.generator_version,
               s.specification_row_count, s.matched_row_count, s.proposed_row_count, s.proposal_count, s.started_by_user_uid,
               s.started_at, v.version_ordinal
        FROM optimisation_pass s JOIN document_version v ON v.version_uid = s.version_uid
        WHERE {where} {order_limit}
    ),{latest_sql}
    SELECT c.optimisation_pass_id, c.project_uid, c.document_uid, c.version_uid, c.run_id, c.text_layer_sha256, c.price_list_id,
           c.vendor_list_id, c.vendor_list_source, c.extraction_algorithm, c.match_algorithm, c.generator_version,
           c.specification_row_count, c.matched_row_count, c.proposed_row_count, c.proposal_count, c.started_by_user_uid,
           c.started_at, t.decision_counts, c.version_ordinal
    FROM chosen c LEFT JOIN tally t ON t.optimisation_pass_id = c.optimisation_pass_id {outer_order}"""


def d574(ids) -> None:
    section: dict = {}
    results["d574"] = section
    p1 = ids["prj:1"]
    list_where = "s.project_uid = :project AND (CAST(:document AS text) IS NULL OR s.document_uid = CAST(:document AS text))"
    order = "ORDER BY s.started_at DESC, s.optimisation_pass_id DESC"
    outer = "ORDER BY c.started_at DESC, c.optimisation_pass_id DESC"
    candidates = {
        "T1": lambda: text(pass_statement(LATEST_T1, list_where, order + " LIMIT :limit", outer)),
        "T2": lambda: text(pass_statement(LATEST_T2, list_where, order + " LIMIT :limit", outer)),
    }

    def rows(statement, params):
        def call():
            with factory() as session:
                return [tuple(r) for r in session.execute(statement, params).all()]
        return call

    section["equal"] = {}
    for limit in (20, 50, 200, 5000):
        params = {"project": p1, "document": None, "limit": limit}
        ref = rows(oprepo._LIST_PASSES, params)()
        section["equal"][f"limit{limit}_n"] = len(ref)
        for name, make in candidates.items():
            got = rows(make(), params)()
            section["equal"][f"{name}_limit{limit}"] = got == ref
    # the other project (passes of 100 proposals) and everything
    for project in (ids["prj:2"],):
        params = {"project": project, "document": None, "limit": 5000}
        ref = rows(oprepo._LIST_PASSES, params)()
        section["equal"]["p2_n"] = len(ref)
        for name, make in candidates.items():
            section["equal"][f"{name}_p2"] = rows(make(), params)() == ref
    save()
    log(f"d574 equal: {section['equal']}")

    for limit in (20, 50, 200):
        params = {"project": p1, "document": None, "limit": limit}
        for name, statement in (("base", oprepo._LIST_PASSES), *((n, m()) for n, m in candidates.items())):
            figure = bench(f"d574_{name}_list{limit}", rows(statement, params))
            figure["explain_warm"] = explain_of(f"d574_{name}_list{limit}", rows(statement, params))
            section[f"{name}__list{limit}"] = figure
        save()
    big = admin("SELECT optimisation_pass_id FROM optimisation_pass WHERE proposal_count = (SELECT max(proposal_count) FROM optimisation_pass) LIMIT 1")[0][0]
    one_where, one_params = "s.optimisation_pass_id = :id", {"id": big}
    single = {"T1": text(pass_statement(LATEST_T1, one_where, "", "")), "T2": text(pass_statement(LATEST_T2, one_where, "", ""))}
    section["equal"]["one_pass_800"] = {n: rows(s, one_params)() == rows(oprepo._SELECT_PASS, one_params)() for n, s in single.items()}
    for name, statement in (("base", oprepo._SELECT_PASS), *single.items()):
        figure = bench(f"d574_{name}_one", rows(statement, one_params))
        figure["explain_warm"] = explain_of(f"d574_{name}_one", rows(statement, one_params))
        section[f"{name}__one"] = figure
    save()


def main() -> None:
    started = time.time()
    ids = perf_seed.prepare(lib.engine)
    perf_seed.seed_d463(lib.engine, ids)
    results["seed_seconds"] = round(time.time() - started, 1)
    results["env"] = {"tree": __import__("os").environ.get("PERF_TREE"), "postgres": admin("SHOW server_version")[0][0],
                      "shared_buffers": admin("SHOW shared_buffers")[0][0], "work_mem": admin("SHOW work_mem")[0][0], "jit": admin("SHOW jit")[0][0]}
    save()
    d572(ids)
    d574(ids)
    results["total_seconds"] = round(time.time() - started, 1)
    save()


if __name__ == "__main__":
    main()
