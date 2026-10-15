# W56A-INT-ANALYSIS-PUBLIC-BOUNDARY-01 — result

The AR v2 publication path now consumes analysis types, merge constants and
the deterministic merge preparation through `auditmanager.analysis.public`.
The existing analysis implementation objects are re-exported; the merge rule,
database SQL and runtime path are unchanged.

## Changed files

- `src/auditmanager/analysis/public.py`
- `src/auditmanager/findings/merge_publication_plan.py`
- `src/auditmanager/findings/v2_publication.py`
- `tests/integration/findings/test_analysis_public_boundary.py`
- `docs/program/tasks/W56A-INT-ANALYSIS-PUBLIC-BOUNDARY-01.md`
- `docs/program/W56A-INT-ANALYSIS-PUBLIC-BOUNDARY-01.md`

## Checks

- Public boundary, merge planner, v2 SQL publisher, merge core and input:
  **42 passed**.
- Python compilation: passed.
- Direct task governance: `[]`.
- `git diff --check`: passed.
- Existing frozen API, error catalogue, analysis registry and provider lock:
  unchanged; migration head remains `0022_findings_v2`.

## Contracts and limits

No `contracts/**`, migration, root dependency/lock file, composition root,
global style, v1 publication or executor changed. The public seam's Python
exports are additive; no HTTP or stage-registry contract moved. The SQL
publisher remains unconnected to runtime and untested against PostgreSQL.

## Integration note

Integrate only the six owned paths after the additive publisher task is
complete. Future findings code should import analysis types through this
public seam. The same focused tests must pass on the integrated candidate;
DB acceptance and runtime activation require separate grants.
