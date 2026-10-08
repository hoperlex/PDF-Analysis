# Task W51-FREEZE-01 — freeze the identity screen wave from W50's accepted development tip

## Outcome

W51 has a checked base, a reconciled plan and an executable Stage-A grant. The exact clean
docs-only freeze candidate passes R-70 light acceptance and becomes the fast-forward
`origin/dev` base for `W51-ROUTES-01`.

## Depends on

- `W50-INT-CLOSE` — complete at `75dd70843b7c3a2a7451368da28376abb899cf26`, published
  and read back on `origin/dev` on 2026-10-07.

## Frozen inputs

- Base: `75dd70843b7c3a2a7451368da28376abb899cf26` on clean `integration/w51` and
  `origin/dev` when this freeze starts.
- Planning-owned read-only presweep: `plan/roadmap-to-beta` commit `2b45a11`, file
  `docs/program/dispatch/W51-PRESWEEP.md` (P-1 through P-18). It is evidence, not a merge
  source; the planning worktree and ref remain untouched.
- Domain `1.0.0-draft.1` revision 9 / 29 opaque identities; API 27 paths / 34 operations /
  77 schemas; error catalog 23; migration head `0015_accounts_roles_registration`.
- `W51-PLAN.md`, `IDENTITY-WAVES.md` §8, `AGENTS.md` §8 and owner ruling `R-70`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: W50's exact accepted SHA is the W51 base, and the planning presweep is complete

### P-01 — accepted W51 base is published

- captured_at: 2026-10-07
- command: `git ls-remote origin refs/heads/dev refs/heads/main`
- captured_output:
  ```text
  75dd70843b7c3a2a7451368da28376abb899cf26 refs/heads/dev
  3a54108ba8dbcd9723cdeb7c6ad1fb0c0209b801 refs/heads/main
  ```
- interpretation: `dev` names the accepted W50 close; `main` has no W51 publication authority.

### P-02 — read-only presweep was finalized after the SHELL-FRAME merge

- captured_at: 2026-10-07
- command: `git -C .local/worktrees/plan-roadmap-to-beta log -1 --format='%h %s'`
- captured_output:
  ```text
  2b45a11 docs(plan): W51 pre-freeze sweep — re-checked on the SHELL-FRAME merge
  ```
- interpretation: its P-5, P-16 and P-17 checks apply to the merged frame; re-check the
  relevant paths on this freeze base before granting edits.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

The W50 reports and planning presweep are not rewritten.

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W51-FREEZE-01.md`
- `docs/program/tasks/W51-ROUTES-01.md` — Stage-A grant from this freeze
- `docs/program/W51-FREEZE-01.md` — freeze evidence and handoff
- `docs/program/dispatch/W51-PLAN.md` — reconcile presweep and R-70 before dispatch
- `docs/program/dispatch/PORT_REGISTRY.md` — reserve Stage-A lane only
- local `integration/w51` and fast-forward publication of its exact accepted freeze SHA to
  `origin/dev`

## Forbidden hotspots

- All product code/tests, `contracts/**`, `db/migrations/**`, `infra/**`, root dependencies
  and locks, composition roots, global styles, other programme records, planning worktrees
  and refs, `origin/main`, tags and deployment.

## Non-goals

- No W51 implementation or parallel Stage-B dispatch before `W51-ROUTES-01` completes.
- No behavior change, contract reseal, release tag or deployment.

## Deliverables

- Re-measure presweep's path/guard premises on the accepted W50 base and amend W51's plan:
  preserve `next`, avoid a protected `loading.tsx`, use existing query-key factories,
  identify all shared guard/manifest/runbook pins, and make Stage B sequential where
  multiple lanes must edit one file.
- A complete `W51-ROUTES-01` task with exact Stage-A allowed paths, tests, stand/port plan,
  mutation/red controls, contract state and handoff.
- A freeze report with exact SHA lineage, baseline, grant rationale, checks, stop conditions,
  risks, rollback and proof of untouched hotspots.

## Required tests

- Static checks of the presweep's exact paths and W51 generated-client operations.
- `git diff --check` and grant-path proof.
- On the clean committed docs-only freeze candidate: `make light-acceptance
  BASE=d8ea61351489fcf08c7ebfe8ff90045b2127b559` with literal
  `LIGHT ACCEPTANCE OK` under `R-70`; a changed R-70 risk path requires a full gate.
- Re-read remote `dev`, prove it is an ancestor of the exact candidate, push without force,
  and read back the remote SHA.

## Integration contract

`W51-ROUTES-01` starts only from the published freeze SHA and may edit only its task's paths.
The integrator owns the W51 freeze and every merge/publication. Stage-B tasks are written or
activated after Stage A; shared guard and journey files receive sequential ownership.

## Failure/idempotency/security cases

- A stale presweep premise is corrected in this freeze's plan/task evidence before dispatch.
- A changed remote `dev`, non-ancestor relationship or failed acceptance stops publication.
- No force push, credential handling or stand mutation in this docs-only task.

## Rollback / feature flag

No runtime behavior or flag changes. Revert the docs freeze commit on `dev` if its grants or
facts are wrong; Stage-A work must then be rebased onto a corrected freeze.

## Handoff

- changed files: only the five granted programme Markdown files
- commands/results: exact accepted SHA, light sentinel and remote read-back
- known limits: later Stage-B grants depend on Stage-A merge and its measured tree
- integration notes: Stage A starts from the verified development ref
