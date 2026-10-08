# Task W52-INT-FREEZE-PREFLIGHT-01 — measure the unfrozen W52 base

task_id: W52-INT-FREEZE-PREFLIGHT-01

## Outcome

The integrator records current, command-derived contract and pin-sweep facts
for the later `W52-FREEZE-01`. The report identifies what remains blocked by
the missing `W52-RULE-01` owner confirmations without declaring W52 frozen or
granting a lane.

## Depends on

- `W52-INT-ENTRY-01` — adopted and reconciled the W52 plan on `origin/dev`
  through `f2ea05b0053ae0cbb14b8f767c3e576d250931d2`.

## Frozen inputs

- Clean local `origin/dev` / `integration/w51` base
  `f2ea05b0053ae0cbb14b8f767c3e576d250931d2`.
- W52 plan §2–§5 and `IDENTITY-WAVES.md` §10, with the explicit W52 code-only
  gate exception; D-137–D-140 remain open.
- Frozen W51 contract set: domain `1.0.0-draft.1` candidate revision 9 /
  29 identities, API 27 paths / 34 operations / 77 schemas, 23 API error
  codes and migration head `0015_accounts_roles_registration`.
- No owner answer to the three `W52-RULE-01` confirmations is recorded in
  `OWNER_RULINGS_2026-09-17.md`; no inference from a generic continue request.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the adopted plan remains unfrozen and the current tree contains
  the preparatory pin-sweep and expected-facts files.

### P-01 — clean base and missing freeze

- captured_at: 2026-10-08
- command: `git rev-parse HEAD && git status --porcelain --untracked-files=no && test -f tools/plan/pin_sweep.py && test -f tests/support/expected_facts.json && test ! -f docs/program/tasks/W52-FREEZE-01.md && rg -n 'not frozen or' docs/program/dispatch/W52-PLAN.md`
- captured_output:
  ```text
  f2ea05b0053ae0cbb14b8f767c3e576d250931d2
  5:supersedes the older gate-dependent dispatch sentence. W52 is **not frozen or
  ```
- interpretation: tools and facts exist on a clean development base, while
  the rule/freeze boundary has not been crossed.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W52-INT-FREEZE-PREFLIGHT-01.md`
- `docs/program/W52-INT-FREEZE-PREFLIGHT-01.md`
- local integrator card/handoff under `.local/`
- local `integration/w51` commit and non-force fast-forward to `origin/dev`
  only after exact remote-ref verification

## Forbidden hotspots

Everything else, especially `W52-PLAN.md`, owner rulings, `CURRENT_STATE.md`,
contracts, migration head, root dependency/lock files, composition root,
global styles, product code/tests, planning worktrees, `origin/main`, tags
and deployment.

## Non-goals

No owner ruling, W52 freeze, task grant, lane dispatch, QA, temporary stand,
full gate, release, tag or main push. Pin-sweep output is advisory and must be
re-run against the actual later freeze SHA.

## Deliverables

- Report with measured contract set, exact input hashes, current pin-sweep
  event counts and concrete grant families to inspect at freeze.
- Explicit list of remaining ruling/freeze/validation dependencies.
- Clean docs-only commit and, if refs permit, development-line publication.

## Required tests

- `python3 tools/plan/pin_sweep.py` for the W52 reseal, migration, table and
  route events; verify exact output counts and record that this is advisory.
- Focused governance/prose guards and `git diff --check` on the clean commit.
- No `make gate` under the owner's code-only deferral.

## Integration contract

The later `W52-FREEZE-01` re-runs all measurements on its own exact base,
records owner rulings first, and writes task grants after classifying sweep
hits. This preflight alone cannot make the plan dispatchable. The integrator
alone may publish the docs-only report to `origin/dev` after ancestor and
remote-ref checks.

## Failure/idempotency/security cases

If a contract or migration differs from the frozen set, or a new remote ref
invalidates the base, stop and revise the report rather than asserting a
freeze. Re-running the task overwrites no external evidence or service.

## Rollback / feature flag

Revert the docs-only commit if its measurements are wrong. No product
behavior or feature flag changes.

## Handoff

The report names changed files, checks, contracts, risks, integration step
and forbidden-hotspot proof.
