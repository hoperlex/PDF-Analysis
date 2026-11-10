"""Can the planner be made to drop the unused LATERALs of ``finding_current_verdict`` (join removal) without rewriting the verdict rule? Plan
shapes only (EXPLAIN without ANALYZE) on the 700-document seed (``perf_seed.py``). Nothing here changes the repository."""
from __future__ import annotations

import perf_lib as lib
import perf_seed
from perf_lib import admin, results, save

CASES = {
    "V1_join_view": "SELECT cv.finding_uid, cv.current_verdict FROM finding_current_verdict cv WHERE cv.finding_uid IN (SELECT finding_uid FROM finding_observation WHERE run_id = 'x')",
    "V2_distinct": "SELECT DISTINCT cv.finding_uid, cv.current_verdict FROM finding_current_verdict cv WHERE cv.finding_uid IN (SELECT finding_uid FROM finding_observation WHERE run_id = 'x')",
    "V3_group_by": "SELECT cv.finding_uid, cv.current_verdict FROM finding_current_verdict cv WHERE cv.finding_uid IN (SELECT finding_uid FROM finding_observation WHERE run_id = 'x') GROUP BY 1, 2",
    "V4_exists_filter": "SELECT count(*) FROM finding_observation o WHERE o.run_id = 'x' AND EXISTS (SELECT 1 FROM finding_current_verdict cv WHERE cv.finding_uid = o.finding_uid AND cv.current_verdict IN ('pending','needs_manual_review'))",
    "V5_scalar_subselect": "SELECT o.finding_uid, (SELECT cv.current_verdict FROM finding_current_verdict cv WHERE cv.finding_uid = o.finding_uid) FROM finding_observation o WHERE o.run_id = 'x'",
    "V6_in_list": "SELECT cv.current_verdict, count(*) FROM finding_current_verdict cv WHERE cv.finding_uid = ANY(ARRAY(SELECT finding_uid FROM finding_observation WHERE run_id = 'x')) GROUP BY 1",
    "V7_distinct_on": "SELECT DISTINCT ON (cv.finding_uid) cv.finding_uid, cv.current_verdict FROM finding_current_verdict cv WHERE cv.finding_uid IN (SELECT finding_uid FROM finding_observation WHERE run_id = 'x')",
}


def main() -> None:
    ids = perf_seed.prepare(lib.engine)
    perf_seed.seed_d463(lib.engine, ids)
    for name, sql in CASES.items():
        plan = [r[0] for r in admin("EXPLAIN " + sql)]
        results[name] = {"limit_nodes": sum("Limit" in line for line in plan), "plan": plan}
        lib.log(f"{name}: Limit nodes = {results[name]['limit_nodes']}")
        save()


if __name__ == "__main__":
    main()
