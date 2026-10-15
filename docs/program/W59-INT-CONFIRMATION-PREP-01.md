# W59-INT-CONFIRMATION-PREP-01 — result

The additive `sections.confirmation` policy prepares an explicit expert choice
of one of the 15 section codes for a single opaque `VersionUid`. It requires an
explicit `P` or `R` version stage and an authenticated expert role. A repeated
same-code request is `unchanged` and preserves the original expert; another
code, stage or version refuses. A document-level legacy section and filename
suggestions cannot become confirmation records through this API.

## Checks

- Focused confirmation, routing and suggestion suite: **40 passed**. It covers
  all 15 codes, PS/PB, a misleading AR filename, both stages, repeat,
  conflict, foreign version, unknown values, non-expert roles and refusal to
  route an unpersisted plan.
- ALR-05 architecture boundary suite: **2 passed** (five unrelated pytest
  temporary-directory cleanup warnings appeared after success).
- Python compilation, direct task governance `[]`, changed-path review and
  whitespace check: passed.
- `ruff` is not installed in this worktree's Python environment; the named
  task tests did not require it. Full local gate and database upgrade deferred
  by R-135 and because this task changes no database object.

## Contracts, limits and integration

No API, domain, error, analysis, migration, active profile, run or database
contract changed. The `P`/`R` spellings are provisional internal values, not a
resealed wire contract. This pure policy does not persist a row or prove that
the caller supplied authenticated roles and the version's actual stored stage.
The W59 contract/migration owner must first close the W58 prerequisite,
reseal the 15-code API/DB vocabulary (including PS), place stage on the version,
and add a unique version-bound confirmation record and expert-authorized API.
That service should call this policy inside its transaction. The future DB
must enforce uniqueness on `version_uid` so concurrent inserts cannot both
commit. A separate adapter must read the persisted row, construct
`routing.ConfirmedSection`, and pass that to `route_confirmed_section`; the
pure plan itself grants no routing authority. A conflicting change requires a
separate auditable correction rule, not an overwrite here.

Changed paths:

- `src/auditmanager/sections/confirmation.py`
- `tests/integration/sections/test_confirmation.py`
- `docs/program/tasks/W59-INT-CONFIRMATION-PREP-01.md`
- `docs/program/W59-INT-CONFIRMATION-PREP-01.md`

The forbidden hotspots, including `contracts/**`, `db/migrations/**`, existing
section files, API/router/UI/run code, provider lock, root dependencies/locks,
composition root, global styles, `CURRENT_STATE.md`, tags and `origin/main`,
were not edited. Revert these additive files to roll back before runtime
wiring; there is no data rollback or feature flag.
