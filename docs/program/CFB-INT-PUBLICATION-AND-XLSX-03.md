# CFB-INT-PUBLICATION-AND-XLSX-03 — integration result

## Result

The dev candidate contains four bounded follow-ups:

- The wave-13 CSV characterization now derives only the two appended empty
  W56a cells in memory from digest-pinned historical record 12; original
  bytes and all other record comparisons remain unchanged.
- The AR v2 publisher inserts one finding per validated merge group, every
  member observation and evidence item, then sets the canonical observation
  within one savepoint. It is not connected to the run executor.
- The analysis public seam exports the AR v2 types and merge constants that
  findings consumes, removing direct imports into analysis internals.
- The W57b XLSX projection validates canonical/member completeness, page
  labels, citations and expert verdict semantics before the existing pure
  writer receives `WorkbookInput`. It does no DB read or API operation.

## Changed files

- Three files for CSV characterization: test, task and report named
  `W56A-INT-CSV-CHARACTERIZATION-COMPAT-01`.
- Four files for AR v2 SQL publication: `findings/v2_publication.py`, its
  focused test, task and report named `W56A-INT-V2-PUBLICATION-PREP-01`.
- Six files for the public boundary: `analysis/public.py`, two findings
  consumers, the boundary test, task and report named
  `W56A-INT-ANALYSIS-PUBLIC-BOUNDARY-01`.
- Four files for XLSX projection: `exports/xlsx/projection.py`, its focused
  test, task and report named `W57B-INT-XLSX-PROJECTION-PREP-01`.
- This task/report and `CURRENT_STATE.md`.

## Checks

- Publisher, merge, analysis boundary, XLSX projection and writer: **61
  passed**.
- Pure historical CSV compatibility probes: **2 passed, 61 deselected**.
- Direct governance on five new task files: `[]`; compilation, frozen hashes,
  whitespace and exact changed-path proof: pass.
- A broader characterization selection reached nine DB fixture errors
  because this worktree has no `.env`. It did not execute those DB cases.
  `DATABASE_URL` and the test services are unavailable here.

## Contracts, limits and next work

No `contracts/**`, migration, provider lock, root dependency/lock file,
composition root, global style, corpus source, historical record 12 or
`origin/main` changed. Migration head remains `0022_findings_v2`.

The SQL publisher's fake-session checks prove statement order and savepoint
rollback shape; they do not prove PostgreSQL constraints, triggers or run
idempotency. A hand-built `MergePublicationPlan` is not by itself proof of
PDF grounding or rule consistency: runtime must call
`plan_v2_merge_publication` after `finish_response`. The full
characterization suite and the derived PC-01 CSV bytes need an isolated DB.
The XLSX query, role/state policy, route, contract seal, spreadsheet opening
and verified normative set remain future tasks. W54's heavy corpus chain
remains behind the host's capacity and window requirements.

## Publication

Target: `origin/dev` only after exact checks and remote fast-forward proof.
No `origin/main` authority, release tag, complete `make gate` or beta
acceptance is claimed under R-135.
