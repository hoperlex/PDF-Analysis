# W56A-INT-MERGE-PUBLICATION-PLAN-PREP-01 — result

The additive `plan_v2_merge_publication` builds a typed, pure plan from
`ProposalGroundingResult` and `MergePreparation`. It validates the dense source
map, total and disjoint merge membership, canonical member and category, and
checks the artifact against the deterministic merge rule. Every accepted
member retains its original proposal ordinal, proposal fields and resolved
PDF evidence. Rejected proposals retain all failure diagnostics and receive
no finding group. The plan allocates no IDs or verdicts and performs no I/O.

## Checks

- Planner, merge core and merge-input tests: **30 passed**.
- Python compilation: passed.
- Direct task governance: `[]`.
- Whitespace check and exact owned-path proof: passed. The four
  task-owned paths are the only changes made by this lane; selected forbidden
  hotspots have no diff.
- Full local gate and acceptance: deferred under `R-135`.

## Contracts and limits

No contract, migration, provider lock, existing publication function, runtime
stage or v1 behavior changed. A legacy `GateResult` is refused as planner
input; existing v1 publication remains on its original path. This does not
publish findings, store diagnostics or exercise a database savepoint. The
future publisher must allocate one UID per group, insert all members and set
the canonical observation ID in one savepoint. No active v2 provider call is
claimed; the gateway model identity remains unresolved.

Only the planner, its focused test, this report and its task file belong to
this lane. Forbidden hotspots, `CURRENT_STATE.md`, Git refs and tags were not
changed by this lane. Integration can revert these four additive paths before
runtime wiring without data migration.
