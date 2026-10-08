# Task W52-INT-DEFER-01 — record the continuing validation deferral

task_id: W52-INT-DEFER-01

## Outcome

`D-139` and `D-140` make the owner's code-first QA/gate deferral explicit for W52 and later
implementation candidates, with closure checks tied to exact SHAs.

## Depends on

- `W52-PINSWEEP-01` — integrated at `57237f458ee275aff3b786721a6811aa9775ff50`.

## Frozen inputs

- Base `57237f458ee275aff3b786721a6811aa9775ff50`; W51 domain revision 9 / 29 identities,
  API 27 paths / 34 operations / 77 schemas, error catalog 23, migration head
  `0015_accounts_roles_registration`.
- Owner instruction 2026-10-08: take tasks without approval; defer QA and full gates into future
  debt. `D-137`/`D-138` already cover W51 specifically.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `docs/program/DEBT_REGISTER.md`
- enumerator_owner: `W52-INT-DEFER-01`
- totality_query: `rg -n '^### D-13[789]|^### D-140' docs/program/DEBT_REGISTER.md`

## Captured premise evidence

- premise: the register currently ends at D-138 for validation deferral.

### P-01 — debt baseline

- captured_at: 2026-10-08
- command: `rg -n '^### D-13[78]' docs/program/DEBT_REGISTER.md`
- captured_output:
  ```text
  124:### D-137 — W51 QA and live identity acceptance are deferred
  137:### D-138 — the W51 end-of-wave gate is deferred
  ```
- interpretation: W51 has two explicit rows; this does not cover W52 or later candidates.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/DEBT_REGISTER.md`
- `docs/program/tasks/W52-INT-DEFER-01.md`

## Forbidden hotspots

All other paths, especially contracts, migrations, root dependencies/locks, composition root,
global styles and application code.

## Non-goals

No QA, stand, full gate, W51/W52 close, tag or `origin/main` publication.

## Deliverables

Two separate debt rows, summary entries and objective closure checks.

## Required tests

- `rg -n '^### D-13[789]|^### D-140' docs/program/DEBT_REGISTER.md`
- `git diff --check`

## Integration contract

The integrator alone writes and publishes this docs-only record to `origin/dev`; later code tasks
cite D-139/D-140 and make no validation claim.

## Failure/idempotency/security cases

Duplicate debt IDs are refused by review of the complete heading query. Reapplying the change
does not create a second row.

## Rollback / feature flag

Revert the docs commit if the owner changes the deferral. No runtime behavior or feature flag.

## Handoff

- changed files, commands/results, contracts, risks, integration notes, forbidden-hotspot proof.
