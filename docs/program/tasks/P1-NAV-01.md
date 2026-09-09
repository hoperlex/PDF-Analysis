# Task P1-NAV-01 — build the decision-to-code navigation layer

> **Status: specified; dispatchable after `FF-01 ACCEPTED` and after the repository owner
> accepts ADR-0019 with this plan.** It may be authored in parallel with the P01 provider
> lanes and does not gate them. It is a **required predecessor of P02 fan-out**.

## Outcome

A rebuildable, machine-validated navigation layer in which an agent resolves a decision
to its implementation seam, contracts and proving tests without repository-wide search,
and in which a planned path can never be presented as implemented.

## Depends on

- `P0-FND-00` — completed with `FF-01 ACCEPTED` on 2026-09-09

Planned graph and dispatch conditions, not dependencies:

- `P0-NAV-00` is a candidate at this plan's base commit, not an accepted task. Its
  deliverables — ADR-0019, Bible P-23 and the roadmap navigation gate — are the frozen
  inputs below. Dispatch requires the owner to accept ADR-0019 together with this plan.
- This task waits for no P01 provider. Foundation implementation seams are authored here
  with lifecycle `planned` and reconciled to `implemented` by `P2-INT-00` against the
  accepted PF-01 tree.

## Frozen inputs

- ADR-0019 and Architecture Bible P-23 as committed at the `P0-PLN-01` base commit
  `1cb86cd2708f11712a0cd2f481862652fac2e377`; their acceptance is an owner decision
  recorded with this plan, never assumed by this task
- `docs/program/PROTOTYPE_FOUNDATION_FREEZE.md` at `0b01a3eefe0e6724f6570ccebb9154daf1fdbaec`
  — source of the frozen command surface and the four reserved provider paths
- domain/analysis/event contracts at `1.0.0-draft.1`: read only
- migration head: `none`; this task creates no schema
- base commit: the accepted `P0-PLN-01` integration commit, pinned by the integrator at
  dispatch

## Allowed paths

- `docs/navigation/navigation-entry.schema.json`
- `docs/navigation/entries/**`
- `docs/navigation/INDEX.md` — first generation only; every later regeneration belongs to
  the integration owner of the active batch, per ADR-0019 item 5
- `docs/navigation/README.md`
- `tools/navigation/**`
- `docs/program/tasks/P1-NAV-01.md` status/handoff

## Forbidden hotspots

- `Makefile` and the frozen nine-target command surface: this task adds no target and no
  private alias; its commands are invoked directly
- `scripts/**`, `contracts/**`, `fixtures/**`, `tests/**`
- root dependency/lock files, `db/migrations/**`, `infra/local/**`,
  `src/auditmanager/**`, `web/**`
- `docs/architecture/**` including ADR-0019 itself, CP-00 evidence and Git tags

## Non-goals

- No new architectural authority: entries point at decisions and never restate or
  override them.
- No embeddings, vector index, external service or semantic search.
- No line-number identity, no per-file architecture comments.
- No runtime, product or infrastructure code.
- No commit SHA that would have to identify the commit containing it.

## Deliverables

- one versioned JSON Schema for a navigation entry, requiring at least: stable
  `entry_id`, `lifecycle` (`planned` | `implemented` | `superseded`), bounded scope,
  owning task and bounded context, decision references, contract references,
  implementation paths with public symbol names, runtime entrypoints, test/evidence
  references, supersession links and known gaps
- independently owned entry fragments under `docs/navigation/entries/`, one file per
  owner scope, covering: the accepted FF-01 decisions, ADR-0019 itself, the CP-00
  contract families actually consumed by the prototype, and the four FF-01-reserved
  provider seams as `planned`
- a deterministic generator producing `docs/navigation/INDEX.md` with both directions —
  decision → implementation and implementation path/context → decisions/contracts/tests
- a validator enforcing unique IDs, schema conformance, referenced-path and
  referenced-document existence, lifecycle and supersession consistency, one owner per
  fragment, and byte-identical regeneration
- `docs/navigation/README.md`: the agent onboarding order — `CURRENT_STATE.md`, then the
  index, then the entries relevant to the task, then the task and its frozen contracts
- a negative-control fixture proving the validator fails: at least one case per rule for
  a duplicate `entry_id`, a dangling reference, a `planned` path claimed as
  `implemented`, and a stale generated index

## Required tests

- Command: `.venv/bootstrap/bin/python tools/navigation/validate_navigation.py`
  Expected: exit `0`; prints the counts of validated entries and rules.
- Command: `.venv/bootstrap/bin/python tools/navigation/generate_index.py --check`
  Expected: exit `0`; the committed `docs/navigation/INDEX.md` is byte-identical to a
  fresh generation.
- Command: `.venv/bootstrap/bin/python tools/navigation/validate_navigation.py
  --self-test`
  Expected: exit `0`; every negative-control case is reported as a failure by the rule
  that owns it, proving each guard can go red.
- Command: `.venv/bootstrap/bin/python scripts/validate_bootstrap.py`
  Expected: exit `0`, standalone `PASS`.
- Command: `git diff --check`
  Expected: exit `0`.

## Integration contract

Every P02+ implementation task owns exactly one navigation fragment for the code it adds
or materially changes, or records a reviewed `navigation_not_applicable` reason. The
generated aggregate index has one writer — the integration owner of the active batch —
and is regenerated, never hand-edited. Consumers may rely on the schema and on the
two-direction index; they may not treat an entry as authority over the decision,
contract or test it points at.

## Failure/idempotency/security cases

- Regeneration is deterministic: identical input fragments produce byte-identical output.
- A dangling decision, contract, path or test reference fails validation.
- A `planned` entry that names an implemented symbol, or an `implemented` entry whose
  path does not exist, fails validation.
- The layer holds no credential, no customer payload and no internal S3 object key.
- A superseded entry keeps its ID and points forward; history is never deleted.

## Rollback / feature flag

Documentation and tooling only. Revert the integration commit; no runtime, schema or
foundation behavior changes. The layer is additive and blocking only from P02 fan-out.

## Estimate

P50 1–2 days, P80 3 days. Parallel with P01; not on the foundation critical path.

## Handoff

- changed files and the validator/generator transcripts
- entry inventory with lifecycle counts and the list of `planned` seams awaiting
  `P2-INT-00` reconciliation
- known gaps recorded as entries rather than omitted
- integration notes: accept before P02 fan-out; `P2-INT-00` flips the foundation seams to
  `implemented` against the accepted PF-01 tree
