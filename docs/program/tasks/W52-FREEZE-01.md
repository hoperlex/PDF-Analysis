# Task W52-FREEZE-01 — freeze W52 Stage A on the ruled development base

task_id: W52-FREEZE-01

## Outcome

The exact post-ruling development tree is measured and W52 Stage A has one
executable, disjoint remaining code task, `W52-GATE-01`. Later stage grants
remain conditional on the Stage-A merge and their own pin-sweep checks.

## Depends on

- `W52-RULE-01`, completed and read back on `origin/dev` at
  `3ab4097c8014ff70f5187882a188d0ef3f955f33`.

## Frozen inputs

- Clean `integration/w51` and remote `origin/dev` at
  `3ab4097c8014ff70f5187882a188d0ef3f955f33`.
- Owner rulings R-71…R-74 and R-70; W52 plan §3–§5; code-only full-gate
  deferral to D-140 and QA/live deferral to D-137/D-139.
- Domain `1.0.0-draft.1` candidate revision 9 / 29 identities; API 27 paths /
  34 operations / 77 schemas, OpenAPI SHA-256
  `633a58a53baf6652625b59d3db9438ae01e8c4ac8da788160882f031123f2e37`;
  error catalog 23; migration head `0015_accounts_roles_registration`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the clean post-ruling base exists and records both boundary
  rulings needed by Stage A.

### P-01 — exact base and ruling headings

- captured_at: 2026-10-08
- command: `git rev-parse HEAD && git status --porcelain --untracked-files=no && rg -n '^### .R-71.|^### .R-74.' docs/program/OWNER_RULINGS_2026-09-17.md`
- captured_output:
  ```text
  3ab4097c8014ff70f5187882a188d0ef3f955f33
  1302:### `R-71` — one product version and a separate contract version
  1336:### `R-74` — bounded judging, independent facts and serial gate preparation
  ```
- interpretation: the ruling prerequisite is committed; the empty status
  line means tracked files were clean at measurement. This is not a gate or
  Stage-B grant.

## Historical evidence

- correction_mode: addendum
- source_record: `docs/program/W52-INT-FREEZE-PREFLIGHT-01.md` at `defade8`
- addendum_path: `docs/program/W52-FREEZE-01.md`

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W52-FREEZE-01.md`
- `docs/program/tasks/W52-GATE-01.md` — Stage-A grant only
- `docs/program/W52-FREEZE-01.md`
- `docs/program/dispatch/W52-PLAN.md` — freeze status and staged-grant boundary
- `docs/program/dispatch/PORT_REGISTRY.md` — one Stage-A lane reservation
- `docs/program/CURRENT_STATE.md` — Stage-A freeze status
- local integrator card/handoff under `.local/`
- local integration commit and exact fast-forward to `origin/dev`

## Forbidden hotspots

Everything else, especially contracts, migration head, root dependencies
and locks, composition root, global styles, product code/tests, owner
rulings, other task grants, `origin/main`, tags and deployment.

## Non-goals

No W52 code merge, retrospective freeze of already merged preparations,
Stage-B/C dispatch, QA, live/manual acceptance, full `make gate`, release,
tag or main push. The plan's deferred full gate remains D-140.

## Deliverables

- Exact current contract and pin-sweep measurements, with advisory hits
  classified for later Stage-B/C grant work.
- One complete remaining Stage-A task, reconciled with the already merged
  Makefile and PC-01 provider-fixture slices.
- A reserved lane and a report spelling out the next integration step.

## Required checks

- Command-derived OpenAPI, identifier, error and migration-head measurements;
  match `tests/support/expected_facts.json`.
- `python3 tools/plan/pin_sweep.py` for the six event families; record the
  advisory counts, not treat the list as permission to edit.
- Focused governance/prose/surface checks and `git diff --check` on the
  docs-only candidate. No full gate or JUnit timing claim under D-140.
- Exact remote-ref, clean-tree and fast-forward proof before dev publication.

## Integration contract

Only `W52-GATE-01` may start from the read-back SHA of this docs-only freeze.
The integrator rechecks its lane ports before use. Stage B receives concrete
task files and clean `pin_sweep --check` only after Stage A is accepted and
merged; Stage C/C2 grants follow the Stage-B merge.

## Failure/idempotency/security cases

If a contract differs, a port is bound, a pin demands a path outside a
grant, or remote dev moves, stop and reconcile before publication or lane
start. A test fixture must not write to another lane's bucket/database.
No credential is recorded in this task or its report.

## Rollback / feature flag

Revert the docs-only freeze commit if its base or grant is wrong. No behavior
or feature flag changes here.

## Handoff

The report names changed files, checks/results, contracts, risks,
integration instruction and forbidden-hotspot proof.
