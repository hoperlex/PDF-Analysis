# Task W52-INT-PREP-01 — record code preparation and validation limits

task_id: W52-INT-PREP-01

## Outcome

The first-read state and deferred-validation debts identify W52's code preparations, basic
checks and exact limitations before the next task is dispatched.

## Depends on

- `W52-PINSWEEP-01` — integrated at `57237f458ee275aff3b786721a6811aa9775ff50`.
- `W52-INT-DEFER-01` — committed at `27f27428679ae02745938f49da52dcffc034ade0`.
- `W52-FACTS-01` — integrated at `b5be37e56745f9d9ebecdd5e14fce64e5f58afdd`.

## Frozen inputs

- Base `b5be37e56745f9d9ebecdd5e14fce64e5f58afdd`; domain revision 9 / 29 identities,
  API 27 paths / 34 operations / 77 schemas, error catalog 23 and migration head
  `0015_accounts_roles_registration`.
- Owner direction 2026-10-08: proceed without approval, defer QA, stand and full gate to
  D-139/D-140. No application contract changes here.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: W52 preparations are merged and validation debts are open.

### P-01 — merge and debt baseline

- captured_at: 2026-10-08
- command: `git rev-parse HEAD && rg -n '^### D-13[789]|^### D-140' docs/program/DEBT_REGISTER.md`
- captured_output:
  ```text
  b5be37e56745f9d9ebecdd5e14fce64e5f58afdd
  129:### D-139 — later code-only waves defer QA and live checks
  142:### D-140 — later code-only waves defer full gates
  153:### D-137 — W51 QA and live identity acceptance are deferred
  166:### D-138 — the W51 end-of-wave gate is deferred
  ```
- interpretation: the merge and row headings exist; it does not prove QA or gate passed.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/CURRENT_STATE.md`
- `docs/program/DEBT_REGISTER.md`
- `docs/program/tasks/W52-INT-PREP-01.md`
- `docs/program/W52-INT-PREP-01.md`

## Forbidden hotspots

All other paths, especially contracts, migrations, dependencies/locks, application code,
composition root and global styles.

## Non-goals

No QA, stand, full gate, W52 freeze/close, release tag or `origin/main` publication.

## Deliverables

Current-state update, known-validation limits in D-139/D-140 and a short integration record.

## Required tests

- Basic `tests/contract/program/test_wave_governance.py` and `git diff --check`.
- No full gate under the owner's direction.

## Integration contract

This docs-only integrator commit may fast-forward `origin/dev` after remote-ref verification.
Future task briefs read it as planning state, not release evidence.

## Failure/idempotency/security cases

Do not turn an absent service or existing typecheck error into a green result. Re-running this
update changes no runtime state.

## Rollback / feature flag

Revert the docs commit. No runtime behavior or feature flag.

## Handoff

- changed files, commands/results, contracts, risks, integration notes, forbidden-hotspot proof.
