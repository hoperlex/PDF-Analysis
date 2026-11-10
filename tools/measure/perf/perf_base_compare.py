"""The working tree's statements against the same statements of a base commit, on the 700-document seed (``perf_seed.py``): ``D-574`` (the pass
list and the pass's ``decision_counts``) and ``D-572`` (the counters' and the per-document audit statements).

    PERF_BASE=<commit> perf_base_compare.py        (default ``73206c679``: the tree ``D-574`` was measured against)

* D-574: the base repository module is loaded from ``git show <PERF_BASE>:...`` under another name and run beside the shipped one over the same
  database; every row of every statement is compared (the pass's counts included) before anything is timed.
* D-572: the counters' statement and the per-document audit statement are asserted equal to the base's text; their figures are taken here, with
  the page and whole-listing reads, and again with JIT off (the share of JIT).
Cold = shared buffers evicted and a fresh connection; warm = the median of ``PERF_RUNS`` runs. Nothing here changes the repository.

Importing this module touches neither git nor the database; ``main()`` loads the base modules (the commit must be in the local clone)."""
from __future__ import annotations

import importlib
import importlib.util
import os
import subprocess
import sys
import time
from pathlib import Path

from sqlalchemy import text

import perf_lib as lib
import perf_seed
from perf_lib import admin, bench, explain_of, factory, log, norm, results, save

BASE = os.environ.get("PERF_BASE", "73206c679")
REPOSITORY = Path(__file__).resolve().parents[3]
A = importlib.import_module("auditmanager.dashboard.audit_state")
new_repo = importlib.import_module("auditmanager.optimisation.proposals.repository")
old_repo = None  # the base commit's modules, loaded by main()
old_audit = None


def load_base(relative: str, name: str):
    """The file ``relative`` as of commit ``BASE``, imported as module ``name`` (relative imports resolve against the real package of ``name``)."""
    try:
        source = subprocess.run(["git", "show", f"{BASE}:{relative}"], cwd=REPOSITORY, check=True, capture_output=True, text=True).stdout
    except subprocess.CalledProcessError as error:
        raise SystemExit(f"cannot read {relative} at {BASE} (is the commit in this clone?): {error.stderr.strip()}") from error
    path = Path(os.environ["PERF_OUT"]) / (name.rsplit(".", 1)[1] + "_base.py")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def rows(statement, params):
    def call():
        with factory() as session:
            return [tuple(r) for r in session.execute(statement, params).all()]
    return call


def passes() -> None:
    ids = ID
    section: dict = {}
    results["d574"] = section
    p1, p2 = ids["prj:1"], ids["prj:2"]
    section["old_statement_has_lateral"] = "LATERAL" in old_repo._LIST_PASSES.text
    section["new_statement_has_lateral"] = "LATERAL" in new_repo._LIST_PASSES.text
    section["equal"] = {}
    equal = section["equal"]
    for label, project, limit in (("p1_20", p1, 20), ("p1_50", p1, 50), ("p1_200", p1, 200), ("p1_all", p1, 100000), ("p2_all", p2, 100000)):
        params = {"project": project, "document": None, "limit": limit}
        old, new = rows(old_repo._LIST_PASSES, params)(), rows(new_repo._LIST_PASSES, params)()
        equal[f"list_{label}"] = {"rows": len(old), "equal": old == new}
    every = [r[0] for r in admin("SELECT optimisation_pass_id FROM optimisation_pass ORDER BY 1")]
    unequal = []
    with factory() as session:
        for pass_id in every:
            a = [tuple(r) for r in session.execute(old_repo._SELECT_PASS, {"id": pass_id}).all()]
            b = [tuple(r) for r in session.execute(new_repo._SELECT_PASS, {"id": pass_id}).all()]
            if a != b or len(a) != 1:
                unequal.append(pass_id)
        documents = [r[0] for r in admin("SELECT DISTINCT document_uid FROM optimisation_pass ORDER BY 1")]
        for document in documents[:150]:
            for project in (p1, p2):
                params = {"project": project, "document": document, "limit": 10}
                a = [tuple(r) for r in session.execute(old_repo._LIST_PASSES, params).all()]
                b = [tuple(r) for r in session.execute(new_repo._LIST_PASSES, params).all()]
                if a != b:
                    unequal.append(f"{project}/{document}")
        # the record the readers build (the four states filled with zero)
        old_records = [old_repo._pass(r) for r in session.execute(old_repo._LIST_PASSES, {"project": p1, "document": None, "limit": 100000})]
        new_records = [new_repo._pass(r) for r in session.execute(new_repo._LIST_PASSES, {"project": p1, "document": None, "limit": 100000})]
    equal["every_pass_get"] = {"passes": len(every), "unequal": unequal}
    equal["records_p1"] = {"n": len(old_records), "equal_by_repr": [repr(r) for r in old_records] == [repr(r) for r in new_records]}
    save()
    log(f"d574 equal: {equal}")
    assert not unequal, unequal[:5]

    big = admin("SELECT optimisation_pass_id FROM optimisation_pass WHERE proposal_count = (SELECT max(proposal_count) FROM optimisation_pass) LIMIT 1")[0][0]
    one_doc = admin("SELECT document_uid FROM optimisation_pass WHERE project_uid = '%s' GROUP BY document_uid HAVING count(*) >= 2 ORDER BY 1 LIMIT 1" % p1)[0][0]
    find_key = admin("SELECT version_uid, run_id, price_list_id, vendor_list_id, extraction_algorithm, match_algorithm, generator_version FROM optimisation_pass WHERE optimisation_pass_id = '%s'" % big)[0]
    find_params = dict(zip(("version", "run", "price_list", "vendor_list", "extraction", "match", "generator"), find_key))
    cases = {
        "list20": ("_LIST_PASSES", {"project": p1, "document": None, "limit": 20}),
        "list50": ("_LIST_PASSES", {"project": p1, "document": None, "limit": 50}),
        "list200": ("_LIST_PASSES", {"project": p1, "document": None, "limit": 200}),
        "list_of_one_document": ("_LIST_PASSES", {"project": p1, "document": one_doc, "limit": 50}),
        "one_pass_800": ("_SELECT_PASS", {"id": big}),
        "find_pass": ("_FIND_PASS", find_params),
    }
    for label, (name, params) in cases.items():
        for tree, module in (("base", old_repo), ("shipped", new_repo)):
            statement = getattr(module, name)
            figure = bench(f"d574_{tree}_{label}", rows(statement, params))
            figure["explain_warm"] = explain_of(f"d574_{tree}_{label}", rows(statement, params))
            section[f"{tree}__{label}"] = figure
        save()
    admin("ALTER DATABASE %s SET jit = off" % admin("SELECT current_database()")[0][0])
    lib.engine.dispose()
    for label in ("list50", "list200"):
        name, params = cases[label]
        for tree, module in (("base", old_repo), ("shipped", new_repo)):
            section[f"{tree}__{label}__jit_off"] = bench(f"d574_{tree}_{label}_jit_off", rows(getattr(module, name), params))
    admin("ALTER DATABASE %s RESET jit" % admin("SELECT current_database()")[0][0])
    lib.engine.dispose()
    save()


def dashboard() -> None:
    ids = ID
    section: dict = {}
    results["d572"] = section
    section["groups_statement_unchanged"] = old_audit._AUDIT_GROUPS.text == A._AUDIT_GROUPS.text
    section["audits_statement_unchanged"] = old_audit._DOCUMENT_AUDITS.text == A._DOCUMENT_AUDITS.text
    log(f"d572 statements unchanged: {section['groups_statement_unchanged']} {section['audits_statement_unchanged']}")
    p1 = ids["prj:1"]
    with factory() as session:
        versions = [r[0] for r in session.execute(text(
            "SELECT v.version_uid FROM document d JOIN document_version v ON v.version_uid = d.current_version_uid "
            "WHERE d.project_uid = :p ORDER BY v.version_uid"), {"p": p1})]
        everything = [r[0] for r in session.execute(text(
            "SELECT v.version_uid FROM document d JOIN document_version v ON v.version_uid = d.current_version_uid ORDER BY v.version_uid"))]
    model = A.DocumentAuditReadModel()

    def audits(names):
        def call():
            with factory() as session:
                return model.audits(session, version_uids=names)
        return call

    def groups(project):
        def call():
            with factory() as session:
                return model.groups(session, project_uid=project)
        return call

    reads = {"groups_whole_deployment": groups(None), "groups_one_project_400": groups(p1), "audits_page50": audits(versions[:50]),
             "audits_page200": audits(versions[:200]), "audits_whole_project_400": audits(versions), "audits_all_700": audits(everything)}
    for jit in ("on", "off"):
        if jit == "off":
            admin("ALTER DATABASE %s SET jit = off" % admin("SELECT current_database()")[0][0])
            lib.engine.dispose()
        for label, fn in reads.items():
            figure = bench(f"d572_{label}_jit_{jit}", fn)
            if jit == "on":
                figure["explain_warm"] = explain_of(f"d572_{label}", fn)
            section[f"{label}__jit_{jit}"] = figure
        save()
    admin("ALTER DATABASE %s RESET jit" % admin("SELECT current_database()")[0][0])
    lib.engine.dispose()
    save()


def main() -> None:
    global ID, old_repo, old_audit
    started = time.time()
    old_repo = load_base("src/auditmanager/optimisation/proposals/repository.py", "auditmanager.optimisation.proposals.repository_base")
    old_audit = load_base("src/auditmanager/dashboard/audit_state.py", "auditmanager.dashboard.audit_state_base")
    ID = perf_seed.prepare(lib.engine)
    perf_seed.seed_d463(lib.engine, ID)
    results["seed_seconds"] = round(time.time() - started, 1)
    results["env"] = {"base": BASE, "tree": os.environ.get("PERF_TREE"), "postgres": admin("SHOW server_version")[0][0],
                      "shared_buffers": admin("SHOW shared_buffers")[0][0], "work_mem": admin("SHOW work_mem")[0][0], "jit": admin("SHOW jit")[0][0],
                      "passes": admin("SELECT count(*) FROM optimisation_pass")[0][0], "proposals": admin("SELECT count(*) FROM optimisation_proposal")[0][0],
                      "decisions": admin("SELECT count(*) FROM optimisation_proposal_decision")[0][0], "findings": admin("SELECT count(*) FROM finding")[0][0],
                      "documents": admin("SELECT count(*) FROM document")[0][0]}
    save()
    passes()
    dashboard()
    results["total_seconds"] = round(time.time() - started, 1)
    save()


if __name__ == "__main__":
    main()
