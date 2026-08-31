# Task W0-BHV-01 — evidence-backed legacy capability inventory

## Outcome

Produce `docs/behavior/legacy_capability_inventory.md`: a user-verifiable inventory
that maps 100% of discovered public legacy router modules and declared pipeline
stages either to an observed capability or to an explicit exclusion with rationale.
Every capability claim must have a status and immutable source evidence so later W0
tasks can distinguish fact, inference and unknown behavior.

## Ownership

- implementation owner: planned agent `/root/w0_behavior_inventory`
- program integrator / architecture owner: primary agent `/root`
- independent reviewer: planned agent `/root/w0_independent_review`; must not author
  or repair the inventory it reviews
- product/domain approval authority: repository owner/user; approves meaning or
  synopsis changes and is not an implementation agent

## Depends on

- None. This first-wave task has no task-ID dependency.

## Frozen inputs

- domain contract: `contracts/domain/v1/**` exactly at
  `cf11eddbadd134bc09e1c65e01662939134eb01b`; draft, read-only, not ratified
- API contract: `contracts/api/v1/**` at the same base; draft/read-only
- analysis/comparison/event contract: `contracts/analysis/v1/**`,
  `contracts/comparison/v1/**` and `contracts/events/v1/**` at the same base;
  advisory draft inputs only
- migration head: none; no migration may be created
- base commit: `cf11eddbadd134bc09e1c65e01662939134eb01b`
- behavioral source policy: `docs/SOURCE_TRACEABILITY.md` at the base commit
- product taxonomy to test against evidence: `docs/PRODUCT_SYNOPSIS.md` at the base
  commit; it is not evidence of legacy behavior
- immutable legacy oracle: repository discovery path
  `/root/projects/PDF-proverka/PDF-proverka`, commit
  `32b9d903792b30506048a1d42b0e6b2d07aee403`

The discovery path is local workspace context, not a product/runtime contract. Read
the commit object with `git show`, `git grep`, `git ls-tree` or an equivalent
read-only Git-object command. Do not use the current checkout as evidence.

## Allowed paths

- `docs/behavior/legacy_capability_inventory.md`
- `docs/PRODUCT_SYNOPSIS.md` only when direct legacy evidence proves that an existing
  factual legacy statement is wrong or incomplete; every such edit must cite the
  inventory finding and be flagged for product/domain approval

Creating `docs/behavior/` for the inventory is allowed. No other path is writable.

## Forbidden hotspots

- every path not listed under Allowed paths
- `contracts/**` and all contract examples
- migration head, root dependency/lock files, composition root and global styles
- `docs/SOURCE_TRACEABILITY.md`, Architecture Bible, ADRs, stage plans and templates
- `fixtures/**` and `tests/**`; golden journeys belong to `W0-BHV-02`
- every file, ref, checkout and worktree entry in the legacy repository

## Non-goals

- Do not design the greenfield architecture or ratify contract semantics.
- Do not create golden fixtures, characterization tests or copied legacy payloads.
- Do not port algorithms, routes, models or pipeline code.
- Do not run legacy services, jobs, providers, migrations or external side effects.
- Do not claim live-LLM text parity or turn inferred behavior into fact.
- Do not resolve a product/domain contradiction without repository-owner approval.

## Deliverables

The primary inventory document must contain:

1. Scope, method, inspection date, repository discovery path, exact legacy SHA and
   greenfield base SHA.
2. A discovery coverage ledger listing every public router module and every pipeline
   stage/order declaration found in the immutable tree. Each item is `mapped` or
   `excluded`, with reason; coverage must total 100% of discovered items.
3. A stable capability matrix. Each row has a capability ID, actor/user intent,
   trigger/input, observable output/artifact, failure/retry/recovery behavior,
   status (`observed`, `inferred`, or `not observed`), confidence, and evidence.
4. Evidence references in `legacy_commit:path:symbol-or-line` form. Direct evidence
   and inference must be visibly distinct; one source reference must never be used
   to imply behavior it does not show.
5. Coverage of ingest/version inputs, audit execution/progress, pipeline stages,
   findings/evidence, expert decision and rerun behavior, comparison, export, and
   distributed execution/recovery when present. Missing areas are recorded as
   `not observed`, never silently omitted.
6. An input/output and side-effect inventory identifying files/artifacts, stores,
   provider calls and user-visible failure surfaces without exposing values.
7. A synopsis reconciliation table with `supported`, `partial`, `not observed` or
   `contradicted` for each capability group in `docs/PRODUCT_SYNOPSIS.md`.
8. Explicit evidence gaps, contradictions, risk notes and candidates for
   `W0-BHV-02`; no proposed fixture may contain sensitive or production data.
9. The exact read-only discovery commands used and limitations of the inspection.

`docs/PRODUCT_SYNOPSIS.md` is normally unchanged. If it must change, the handoff must
identify every edited statement, its direct evidence and pending/received product
approval separately from the inventory.

## Required tests

- command:
  `git -C /root/projects/PDF-proverka/PDF-proverka cat-file -e '32b9d903792b30506048a1d42b0e6b2d07aee403^{commit}'`
  expected: exit `0`; the immutable oracle object exists.
- command:
  `git -C /root/projects/PDF-proverka/PDF-proverka show -s --format='%H' 32b9d903792b30506048a1d42b0e6b2d07aee403`
  expected: exactly `32b9d903792b30506048a1d42b0e6b2d07aee403`.
- discovery commands, read-only:
  `git -C /root/projects/PDF-proverka/PDF-proverka ls-tree -r --name-only 32b9d903792b30506048a1d42b0e6b2d07aee403 -- backend frontend`
  and targeted `git grep`/`git show` commands recorded in the inventory.
  expected: every discovered public router module and pipeline declaration appears
  in the coverage ledger as mapped or excluded.
- command:
  `rg -n '32b9d903792b30506048a1d42b0e6b2d07aee403|cf11eddbadd134bc09e1c65e01662939134eb01b' docs/behavior/legacy_capability_inventory.md`
  expected: both frozen SHAs are present.
- command:
  `git diff --check -- docs/behavior/legacy_capability_inventory.md docs/PRODUCT_SYNOPSIS.md`
  expected: exit `0`.
- manual evidence check: independent reviewer samples at least one row from each
  present capability group and verifies the reference against the immutable tree;
  expected: no unsupported `observed` claim and no checkout-only evidence.

## Integration contract

After reviewer acceptance, the integrator and downstream `W0-BHV-02`, `W0-ARC-01`,
`W0-DOM-01` and `W0-ANA-01` owners may rely on the inventory as a traceability index
to the pinned legacy snapshot. They may rely on its coverage ledger, status labels,
observable I/O/failure descriptions and explicit gaps. They may not treat an
`inferred`/`not observed` row, a synopsis statement, or a legacy implementation
detail as a frozen greenfield contract.

Acceptance of this task authorizes opening those downstream tasks; it does not
freeze contracts and does not authorize production implementation.

## Failure/idempotency/security cases

- Missing/corrupt legacy Git object: stop and report blocked; do not fall back to
  moving `main`, current checkout, archive copies or internet sources.
- Current legacy branch/worktree differs from the pinned tree: ignore that state and
  continue only through immutable-object reads.
- Conflicting evidence: record both references and mark `contradicted`; escalate the
  semantic choice to the product/domain authority.
- Ambiguous or absent evidence: mark `inferred` or `not observed`; no silent default.
- Secret-shaped or production data encountered: stop inspecting that object, do not
  quote/copy/log the value, record only that the source was excluded, and notify the
  integrator. Never open `.env`, credentials, local databases, uploads, generated
  results or untracked files.
- Binary/oversized artifacts: inventory metadata and observable role only; do not
  copy content into the greenfield repository.
- Re-running discovery against the same SHA must be idempotent: stable evidence IDs
  and coverage rows are updated in place, not duplicated.

## Rollback / feature flag

Documentation-only task; no feature flag applies. Roll back by reverting only this
task's inventory/synopsis commit. There is no schema, migration, runtime or external
state to reverse. A synopsis change may not be integrated without its evidence and
product/domain approval record.

## Handoff

- changed files: list both allowed paths and explicitly say when the conditional
  synopsis path was not touched
- commands/results: include oracle object verification, discovery commands,
  coverage totals, `git diff --check` and reviewer sample results
- new/changed contracts: `none`
- known limits: list all `inferred`, `not observed`, excluded and contradictory areas
- integration notes: state whether the task is accepted to unlock the four dependent
  tasks and identify any product decision still pending
- forbidden-hotspot proof: provide `git diff --name-only <task-base>..<task-head>` (or
  equivalent working-tree diff) showing only Allowed paths; confirm legacy status
  and refs were not changed

