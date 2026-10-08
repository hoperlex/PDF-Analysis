# Task W52-RULE-01 — record the W52 owner rulings

task_id: W52-RULE-01

## Outcome

Four permanent rulings replace the W52 design placeholders, including the
owner's explicit answers to the three deviations in §4. W52 remains
undispatchable until `W52-FREEZE-01` checks the current tree and grants.

## Depends on

- `W52-INT-FREEZE-PREFLIGHT-01`, completed on `origin/dev` at `defade8177ed808049425e15f741a8424997d0c3`.
- `W52-INT-FRONTEND-BASELINE-01`, completed on `origin/dev` at `a94026f6742fa4d61c8a4ef020d6fad9fa4eb5db`.

## Frozen inputs

- Clean development base `a94026f6742fa4d61c8a4ef020d6fad9fa4eb5db`.
- Domain candidate revision 9 / 29 identities; API 27 paths / 34 operations /
  77 schemas; error catalog 23; migration head
  `0015_accounts_roles_registration`.
- `W52-PLAN.md` §3–§4, `ROADMAP-TO-BETA.md` §10, existing R-70 and the
  owner's direct 2026-10-08 answer: «подтверждаю все три» to the three
  W52-RULE-01 confirmations. No `origin/main` instruction was given.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the adopted W52 plan still carries four provisional numbers and
  explicitly requires the owner confirmations before the freeze.

### P-01 — exact base and pending ruling text

- captured_at: 2026-10-08
- command: `git rev-parse a94026f6742fa4d61c8a4ef020d6fad9fa4eb5db && git grep -n -E 'R-V1.*versioning|Owner confirmations.*asked in one message' a94026f6742fa4d61c8a4ef020d6fad9fa4eb5db -- docs/program/dispatch/W52-PLAN.md`
- captured_output:
  ```text
  a94026f6742fa4d61c8a4ef020d6fad9fa4eb5db
  a94026f6742fa4d61c8a4ef020d6fad9fa4eb5db:docs/program/dispatch/W52-PLAN.md:290:- `R-V1` versioning (§3.1; V-1…V-3, V-9, V-10), including: `contract_version` unchanged in W52 and
  a94026f6742fa4d61c8a4ef020d6fad9fa4eb5db:docs/program/dispatch/W52-PLAN.md:299:- **Owner confirmations** asked in one message: the hand-written facts file, and live prose not
  ```
- interpretation: the four plan placeholders need permanent numbers; the
  owner answer supplies the missing decisions, but no task grant or freeze.

## Historical evidence

- correction_mode: addendum
- source_record: `docs/program/dispatch/ROADMAP-TO-BETA.md` §10 owner answers
- addendum_path: `docs/program/W52-RULE-01.md`

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W52-RULE-01.md`
- `docs/program/W52-RULE-01.md`
- `docs/program/OWNER_RULINGS_2026-09-17.md` — R-71 through R-74 only
- `docs/program/dispatch/W52-PLAN.md` — placeholder replacement and ruling status
- `docs/program/dispatch/ROADMAP-TO-BETA.md` — W52 ruling status and A5/A6 confirmation
- `docs/program/CURRENT_STATE.md` — W52 ruling status only
- `docs/program/DEBT_REGISTER.md` — D-120 decision status only
- local integrator card/handoff under `.local/`
- local integration commit and exact fast-forward to `origin/dev`

## Forbidden hotspots

Everything else, especially contracts, migrations, root dependencies/locks,
composition root, global styles, code/tests, `origin/main`, tags and deployment.

## Non-goals

No W52 freeze, lane grant, QA, stand, full gate, release, tag or main push.
D-120's process-risk closure remains assigned to `W52-INT-CLOSE`.

## Deliverables

- R-71 through R-74 in the owner ruling record, with the direct owner answer.
- Reconciled W52 plan, roadmap, current state and D-120 status.
- Report with exact changed paths, checks, contract state and freeze handoff.

## Required checks

- Each of R-71 through R-74 has one heading in the ruling file; no `R-V1`…
  `R-V4` remains in the W52 plan.
- Focused programme governance/prose/surface tests and `git diff --check`.
- Exact remote-ref and fast-forward verification before `origin/dev` push.

## Integration contract

`W52-FREEZE-01` depends on these recorded rulings and remeasures the exact
then-current tree. The ruling commit alone never dispatches a W52 lane.

## Failure/idempotency/security cases

If a permanent number is occupied or a remote ref moves, stop and reconcile.
R-70's diff-derived light acceptance remains in force; serial full-gate
acceleration does not revoke it. No credential or deployment data is recorded.

## Rollback / feature flag

Revert this docs-only commit if the ruling record misstates the owner answer.
No runtime behavior or feature flag changes.

## Handoff

The report names changed files, commands/results, contracts, risks,
integration step and forbidden-hotspot proof.
