"""Seed a throwaway PostgreSQL and measure the read model's heavy statements: the optimisation counts of ``listDocuments`` (``D-463``) and the
decision memory's read model (``D-494``). Candidate indexes are tried on the stand only. Nothing here changes the repository.

    perf_main.py [--dry-run]

Run by ``perf_stand.sh`` inside ONE locked command (the README of this directory has the exact command, the volumes and the figures).
``--dry-run`` prints the configured scale and exits: no database, no seed.

Results go to ``$PERF_OUT/result.json`` after every phase, EXPLAIN texts to ``$PERF_OUT/explain/``. The method of a figure (cold = shared buffers
evicted and a fresh connection; warm = the median of ``PERF_RUNS`` runs; the plan of the exact statement the code sent) is ``perf_lib.py``'s.
The statement is run through the shipped code path (``DocumentAuditReadModel.audits``, ``MemoryReader``, the adapter and router helpers of
``listDocuments``).

Environment: ``DATABASE_URL``, ``PERF_OUT``, ``PERF_RUNS`` (``perf_lib.py``); the scale of the seed (``perf_seed.py``: ``PERF_P1_DOCS``,
``PERF_P2_DOCS``, ``PERF_PASS_SIZES``, ``PERF_OLD_PASS_SIZE``, ``PERF_P2_PASS_SIZE``); ``PERF_MEMORY_STEPS`` (default ``5000,20000,100000``
cases); ``PERF_SKIP_D463=1`` to measure the memory only; ``PERF_TREE`` (the tree's name, copied into the result).
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

from sqlalchemy import bindparam, text

sys.path.insert(0, str(Path(__file__).parent))
import perf_seed  # noqa: E402
from perf_lib import RUNS, admin, bench, engine, explain_of, factory, log, ms, results, save  # noqa: E402,F401

MEMORY_STEPS = tuple(int(x) for x in os.environ.get("PERF_MEMORY_STEPS", "5000,20000,100000").split(","))


def table_sizes(tables: list[str]) -> dict[str, Any]:
    out = {}
    for table in tables:
        row = admin(f"SELECT (SELECT count(*) FROM {table}), pg_size_pretty(pg_total_relation_size('{table}'))")[0]
        out[table] = {"rows": int(row[0]), "total_size": row[1]}
    return out


# ---------------------------------------------------------------------------------------------------------------------
# D-463


def d463(ids: dict[str, str]) -> None:
    from auditmanager.api.routers.documents import _version_sort_key
    from auditmanager.api.routers.wire import encode_json
    from auditmanager.api.schemas.common import page_body, paginate
    from auditmanager.api.schemas.documents import document_version_body
    from auditmanager.bootstrap.adapters import DocumentAdapter
    from auditmanager.dashboard import DocumentAuditReadModel
    from auditmanager.ingest.service import IngestService
    from auditmanager.optimisation.proposals import repository as oprepo

    A = importlib.import_module("auditmanager.dashboard.audit_state")
    model = DocumentAuditReadModel()
    section: dict[str, Any] = {}
    results["d463"] = section
    section["tables"] = table_sizes([
        "document", "document_version", "audit_run", "finding", "finding_observation", "expert_decision_event",
        "optimisation_pass", "optimisation_proposal", "optimisation_proposal_decision", "command_record",
    ])
    section["passes_of_the_page_project"] = [
        {"proposals": int(r[0]), "passes": int(r[1])} for r in admin(
            "SELECT proposal_count, count(*) FROM optimisation_pass WHERE project_uid = '%s' GROUP BY 1 ORDER BY 1" % ids["prj:1"])
    ]
    p1 = ids["prj:1"]
    with factory() as session:
        versions = [row[0] for row in session.execute(text(
            "SELECT v.version_uid FROM document d JOIN document_version v ON v.version_uid = d.current_version_uid "
            "WHERE d.project_uid = :p ORDER BY v.version_uid"), {"p": p1})]
    page200, page50, everything = versions[:200], versions[:50], versions
    section["versions_in_page_project"] = len(versions)
    save()

    def audits(names):
        def call() -> None:
            with factory() as session:
                model.audits(session, version_uids=names)
        return call

    variants = {"audits_page200": page200, "audits_page50": page50, "audits_all": everything, "audits_one": versions[:1]}
    for label, names in variants.items():
        figure = bench(label, audits(names))
        figure["explain_warm"] = explain_of(label, audits(names))
        if label == "audits_page200":
            figure["explain_cold"] = explain_of(label, audits(names), cold=True)
        section[label] = figure
        save()

    # Attribution: the same statement without the optimisation part (the statement of 1.42.0), the optimisation part alone, and the
    # findings part alone. Built from the module's own constants, so they cannot drift from what ships.
    docs, results_rules, active, optimisation = A._CURRENT_DOCS_OF_VERSIONS, A._RESULT_RUN_RULES, A._ACTIVE_RUN_RULE, A._OPTIMISATION_RULE
    parts = {
        "noopt": docs + results_rules + active + """
            SELECT cd.version_uid, rr.state, rr.run_id, coalesce(vf.findings, 0), coalesce(vf.undecided, 0), ar.run_id, ar.state
            FROM current_docs cd LEFT JOIN result_run rr ON rr.version_uid = cd.version_uid
            LEFT JOIN version_findings vf ON vf.version_uid = cd.version_uid LEFT JOIN active_run ar ON ar.version_uid = cd.version_uid""",
        "optonly": docs + optimisation + """
            SELECT cd.version_uid, lp.proposal_count, CASE WHEN lp.version_uid IS NULL THEN NULL ELSE coalesce(pu.undecided, 0) END
            FROM current_docs cd LEFT JOIN latest_pass lp ON lp.version_uid = cd.version_uid
            LEFT JOIN pass_undecided pu ON pu.version_uid = cd.version_uid""",
        "findingsonly": docs + results_rules + """
            SELECT cd.version_uid, rr.run_id, coalesce(vf.findings, 0), coalesce(vf.undecided, 0)
            FROM current_docs cd LEFT JOIN result_run rr ON rr.version_uid = cd.version_uid
            LEFT JOIN version_findings vf ON vf.version_uid = cd.version_uid""",
    }

    def raw_statement(sql: str, names):
        statement = text(sql).bindparams(bindparam("version_uids", expanding=True))

        def call() -> None:
            with factory() as session:
                session.execute(statement, {"version_uids": list(names)}).all()
        return call

    for label, sql in parts.items():
        figure = bench(f"page200_{label}", raw_statement(sql, page200))
        figure["explain_warm"] = explain_of(f"page200_{label}", raw_statement(sql, page200))
        section[f"page200_{label}"] = figure
        save()

    # The listing end to end: the adapter and the router's own helpers, no HTTP (the router closure is not importable on its own).
    ingest = IngestService(None, session_factory=factory)  # type: ignore[arg-type]
    adapter = DocumentAdapter(ingest, factory)

    def list_documents_page(limit: int, order: str | None = None):
        def call() -> int:
            rows = adapter.list_documents(project_uid=p1, order=order)
            page = paginate(rows, limit=limit, cursor=None, sort_key=_version_sort_key)
            unread = [view.version_uid for view in page.items if view.audit is None]
            got = adapter.document_audits(version_uids=unread)
            body = page_body(
                [document_version_body(view if view.audit is not None else replace(view, audit=got[view.version_uid]))
                 for view in page.items], page.next_cursor)
            return len(encode_json(body))
        return call

    for label, (limit, order) in {"listDocuments_limit200": (200, None), "listDocuments_limit50": (50, None),
                                   "listDocuments_order_audit_limit200": (200, "audit")}.items():
        try:
            figure = bench(label, list_documents_page(limit, order))
            figure["response_bytes"] = list_documents_page(limit, order)()
            section[label] = figure
        except Exception as error:  # record, go on
            section[label] = {"error": repr(error)}
            log(f"{label} failed: {error!r}")
        save()

    # Phases of the default listing, to say where the time goes outside the audit statement.
    phases: dict[str, float] = {}
    t = time.perf_counter(); rows = adapter.list_documents(project_uid=p1); phases["adapter.list_documents (all documents of the project)"] = ms(time.perf_counter() - t)
    t = time.perf_counter(); page = paginate(rows, limit=200, cursor=None, sort_key=_version_sort_key); phases["paginate"] = ms(time.perf_counter() - t)
    t = time.perf_counter(); got = adapter.document_audits(version_uids=[v.version_uid for v in page.items]); phases["document_audits (page)"] = ms(time.perf_counter() - t)
    t = time.perf_counter()
    body = page_body([document_version_body(replace(v, audit=got[v.version_uid])) for v in page.items], page.next_cursor)
    phases["document_version_body x page"] = ms(time.perf_counter() - t)
    t = time.perf_counter(); encoded = encode_json(body); phases["encode_json"] = ms(time.perf_counter() - t)
    section["listDocuments_limit200_phases_warm_ms"] = phases
    section["listDocuments_limit200_response_bytes"] = len(encoded)
    save()

    # The pass's own decision_counts (`_COUNTS` of the repository) -- listOptimisationPasses and getOptimisationPass read it per pass.
    def list_passes(limit: int):
        def call() -> None:
            with factory() as session:
                session.execute(oprepo._LIST_PASSES, {"project": p1, "document": None, "limit": limit}).all()
        return call

    for limit in (20, 50, 200):
        figure = bench(f"list_passes_limit{limit}", list_passes(limit))
        figure["explain_warm"] = explain_of(f"list_passes_limit{limit}", list_passes(limit))
        section[f"list_passes_limit{limit}"] = figure
        save()
    big = admin("SELECT optimisation_pass_id FROM optimisation_pass WHERE proposal_count = (SELECT max(proposal_count) FROM optimisation_pass) LIMIT 1")[0][0]

    def one_pass() -> None:
        with factory() as session:
            session.execute(oprepo._SELECT_PASS, {"id": big}).all()

    figure = bench("one_pass_800", one_pass)
    figure["explain_warm"] = explain_of("one_pass_800", one_pass)
    section["one_pass_800"] = figure
    save()

    # ---- candidates, on the stand only -------------------------------------------------------------------------------
    trials: dict[str, Any] = {}
    section["trials"] = trials

    def run_trial(name: str, ddl: list[str], undo: list[str]) -> None:
        for statement in ddl:
            admin(statement)
        admin("VACUUM (ANALYZE) optimisation_proposal_decision")
        admin("VACUUM (ANALYZE) expert_decision_event")
        figure = bench(f"trial_{name}_audits_page200", audits(page200))
        figure["explain_warm"] = explain_of(f"trial_{name}_audits_page200", audits(page200))
        trials[name] = figure
        for statement in undo:
            admin(statement)
        save()

    run_trial(
        "I1_cover_decision_verdict",
        ["CREATE INDEX ix_trial_opd_cover ON optimisation_proposal_decision (optimisation_proposal_id, seq DESC) INCLUDE (verdict)"],
        ["DROP INDEX ix_trial_opd_cover"],
    )
    run_trial(
        "I2_cover_expert_event_verdict",
        ["CREATE INDEX ix_trial_ede_cover ON expert_decision_event (finding_uid, sequence_no DESC) INCLUDE (verdict) WHERE verdict IS NOT NULL"],
        ["DROP INDEX ix_trial_ede_cover"],
    )
    run_trial(
        "I1_plus_I2",
        ["CREATE INDEX ix_trial_opd_cover ON optimisation_proposal_decision (optimisation_proposal_id, seq DESC) INCLUDE (verdict)",
         "CREATE INDEX ix_trial_ede_cover ON expert_decision_event (finding_uid, sequence_no DESC) INCLUDE (verdict) WHERE verdict IS NOT NULL"],
        ["DROP INDEX ix_trial_opd_cover", "DROP INDEX ix_trial_ede_cover"],
    )
    admin("VACUUM (ANALYZE)")


# ---------------------------------------------------------------------------------------------------------------------
# D-494

_LATERAL_LIST = """
SELECT c.case_id, c.category, c.section_code, c.data_class, c.crop_state, c.origin_project_uid, c.captured_at,
       CASE s.kind WHEN 'withdraw' THEN 'withdrawn' WHEN 'forget' THEN 'forgotten' ELSE 'active' END AS status,
       s.status_event_id AS status_event_id, s.reason_code AS status_reason_code, s.created_at AS status_changed_at,
       v.memory_decision_id AS current_decision_id, v.verdict AS current_verdict, v.severity AS current_severity,
       v.origin_kind AS current_origin_kind, v.decided_at AS current_decided_at,
       (SELECT count(*) FROM decision_memory_decision d WHERE d.case_id = c.case_id) AS decision_count
  FROM decision_memory_case c
  LEFT JOIN LATERAL (SELECT e.kind, e.status_event_id, e.reason_code, e.created_at FROM decision_memory_status_event e
                      WHERE e.case_id = c.case_id ORDER BY e.created_at DESC, e.status_event_id DESC LIMIT 1) s ON TRUE
  LEFT JOIN LATERAL (SELECT d.memory_decision_id, d.verdict, d.severity, d.origin_kind, d.decided_at FROM decision_memory_decision d
                      WHERE d.case_id = c.case_id ORDER BY d.decided_at DESC, d.memory_decision_id DESC LIMIT 1) v ON TRUE
 WHERE (CAST(:section AS text) IS NULL OR c.section_code = :section)
   AND (CAST(:category AS text) IS NULL OR c.category = :category)
   AND (CAST(:verdict AS text) IS NULL OR v.verdict = :verdict)
   AND (CAST(:status AS text) IS NULL OR CASE s.kind WHEN 'withdraw' THEN 'withdrawn' WHEN 'forget' THEN 'forgotten' ELSE 'active' END = :status)
   AND (CAST(:data_class AS text) IS NULL OR c.data_class = :data_class)
   AND (CAST(:project AS text) IS NULL OR c.origin_project_uid = :project)
   AND (CAST(:after_at AS timestamptz) IS NULL OR (c.captured_at, c.case_id) < (:after_at, :after_id))
 ORDER BY c.captured_at DESC, c.case_id DESC LIMIT :limit
"""


def d494(ids: dict[str, str], step: int) -> None:
    from auditmanager.decision_memory.reads import MemoryReader

    reader = MemoryReader()
    section: dict[str, Any] = {}
    results.setdefault("d494", {})[str(step)] = section
    section["tables"] = table_sizes([
        "decision_memory_case", "decision_memory_decision", "decision_memory_decision_text", "decision_memory_status_event",
        "decision_memory_content", "decision_memory_evidence",
    ])
    section["case_status_counts"] = {f"{r[0]}/{r[1]}": int(r[2]) for r in admin(
        "SELECT status, data_class, count(*) FROM decision_memory_case_current GROUP BY 1, 2 ORDER BY 1, 2")}
    project = perf_project(0)
    one_case = admin("SELECT case_id FROM decision_memory_case ORDER BY captured_at DESC LIMIT 1 OFFSET 7")[0][0]
    with factory() as session:
        first = reader.list_cases(session, limit=50)
        cursor = first.next_after

    variants: dict[str, dict[str, Any]] = {
        "list_50_nofilter": {"limit": 50},
        "list_200_nofilter": {"limit": 200},
        "list_after_cursor": {"limit": 50, "after": cursor},
        "list_section_AR": {"section": "AR", "limit": 50},
        "list_category": {"category": "dimensions", "limit": 50},
        "list_verdict_accepted": {"verdict": "accepted", "limit": 50},
        "list_status_active": {"status": "active", "limit": 50},
        "list_status_withdrawn": {"status": "withdrawn", "limit": 50},
        "list_data_class_real": {"data_class": "real", "limit": 50},
        "list_project": {"origin_project_uid": project, "limit": 50},
        "list_combination": {"section": "AR", "verdict": "accepted", "status": "active", "data_class": "real", "limit": 50},
    }
    explained = {"list_50_nofilter", "list_status_active", "list_project", "list_combination", "list_verdict_accepted"}

    def listing(kwargs):
        def call() -> None:
            with factory() as session:
                reader.list_cases(session, **kwargs)
        return call

    for label, kwargs in variants.items():
        figure = bench(label, listing(kwargs))
        if label in explained:
            figure["explain_warm"] = explain_of(f"d494_{step}_{label}", listing(kwargs))
        section[label] = figure
    save()

    def counts() -> None:
        with factory() as session:
            reader.counts(session)

    def summary() -> None:
        with factory() as session:
            reader.case_summary(session, one_case)

    def detail() -> None:
        with factory() as session:
            reader.get_case(session, one_case)

    for label, fn in (("counts", counts), ("case_summary_one", summary), ("get_case_one", detail)):
        figure = bench(label, fn)
        if label != "get_case_one":
            figure["explain_warm"] = explain_of(f"d494_{step}_{label}", fn)
        section[label] = figure
    save()

    # Candidates, on the stand only: (a) the page-first LATERAL statement (a query rewrite, no index); (b) an index on captured_at.
    def lateral(kwargs):
        params = {"section": None, "category": None, "verdict": None, "status": None, "data_class": None, "project": None,
                  "after_at": None, "after_id": None, "limit": 51}
        mapped = dict(kwargs)
        params["limit"] = mapped.pop("limit") + 1
        if "origin_project_uid" in mapped:
            params["project"] = mapped.pop("origin_project_uid")
        after = mapped.pop("after", None)
        if after is not None:
            params["after_at"], params["after_id"] = after
        params.update(mapped)

        def call() -> list[Any]:
            with factory() as session:
                return session.execute(text(_LATERAL_LIST), params).mappings().all()
        return call, params

    section["lateral_equals_view"] = {}
    section["lateral"] = {}
    for label, kwargs in variants.items():
        call, params = lateral(kwargs)
        with factory() as session:
            expected = reader.list_cases(session, **kwargs)
        got = call()
        same = [row["case_id"] for row in got[:kwargs["limit"]]] == [item.case_id for item in expected.items] and all(
            tuple(row[k] for k in row.keys()) == tuple(getattr(item, k) for k in row.keys())
            for row, item in zip(got, expected.items))
        section["lateral_equals_view"][label] = same
        figure = bench(f"lateral_{label}", lambda call=call: call())
        if label in explained:
            figure["explain_warm"] = explain_of(f"d494_{step}_lateral_{label}", lambda call=call: call())
        section["lateral"][label] = figure
    save()

    if step == MEMORY_STEPS[-1]:
        section["trial_index_captured_at"] = {}
        admin("CREATE INDEX ix_trial_case_captured ON decision_memory_case (captured_at DESC, case_id DESC)")
        admin("VACUUM (ANALYZE) decision_memory_case")
        for label in ("list_50_nofilter", "list_section_AR", "list_status_active"):
            figure = bench(f"idx_{label}", listing(variants[label]))
            figure["explain_warm"] = explain_of(f"d494_{step}_idx_{label}", listing(variants[label]))
            section["trial_index_captured_at"][label] = figure
            call, _ = lateral(variants[label])
            lat = bench(f"idx_lateral_{label}", lambda call=call: call())
            lat["explain_warm"] = explain_of(f"d494_{step}_idx_lateral_{label}", lambda call=call: call())
            section["trial_index_captured_at"][f"lateral_{label}"] = lat
        admin("DROP INDEX ix_trial_case_captured")
        save()


def perf_project(n: int) -> str:
    return admin("SELECT perf_id('prj', 'mp:%d')" % n)[0][0]


def configured_scale() -> dict[str, Any]:
    """The volume this run would build, from the environment alone (no database)."""
    return {**perf_seed.scale(), "memory_steps": list(MEMORY_STEPS), "runs_per_figure": RUNS, "skip_d463": os.environ.get("PERF_SKIP_D463") == "1"}


def main(argv: list[str] | None = None) -> None:
    arguments = sys.argv[1:] if argv is None else argv
    if arguments == ["--dry-run"]:
        print(json.dumps(configured_scale(), indent=2))
        return
    if arguments:
        raise SystemExit("usage: perf_main.py [--dry-run]")
    started = time.time()
    results["env"] = {
        "tree": os.environ.get("PERF_TREE"), "postgres": admin("SHOW server_version")[0][0],
        "shared_buffers": admin("SHOW shared_buffers")[0][0], "work_mem": admin("SHOW work_mem")[0][0],
        "effective_cache_size": admin("SHOW effective_cache_size")[0][0],
        "scale": {"P1_DOCS": perf_seed.P1_DOCS, "P2_DOCS": perf_seed.P2_DOCS, "PASS_SIZES": perf_seed.PASS_SIZES,
                  "OLD_PASS_SIZE": perf_seed.OLD_PASS_SIZE, "memory_steps": MEMORY_STEPS},
        "runs_per_figure": RUNS,
    }
    ids = perf_seed.prepare(engine)
    if os.environ.get("PERF_SKIP_D463") != "1":
        perf_seed.seed_d463(engine, ids)
        results["seed_d463_seconds"] = round(time.time() - started, 1)
        save()
        d463(ids)
    for step in MEMORY_STEPS:
        perf_seed.seed_memory(engine, ids, step)
        results.setdefault("seed_memory_elapsed_seconds", {})[str(step)] = round(time.time() - started, 1)
        d494(ids, step)
    results["total_seconds"] = round(time.time() - started, 1)
    save()
    log(f"done in {results['total_seconds']}s")


if __name__ == "__main__":
    main()
