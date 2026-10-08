# Task W52-INT-C2-ACCEPT-01 — integrate measured-build acceptance

task_id: W52-INT-C2-ACCEPT-01

## Outcome

The exact W52 ACCEPT lane is reviewed on the merged development tree and
published to `origin/dev`, completing Stage C2 implementation.

## Depends on

- `W52-INT-C2-ACCEPT-GRANT-01`, published at
  `092466980912e3937ca794edd37cd22917e0b53f`.
- `W52-ACCEPT-01`, complete on clean lane commit
  `8cbff0e91c14516d08622fe2e73ff2b5e9eb33ea`.

## Frozen inputs

- Integration base and `origin/dev`:
  `092466980912e3937ca794edd37cd22917e0b53f`.
- `VERSION=0.3.0`; API 30/37/83, 23 error codes, domain revision
  9 / 29 identities, migration head `0016_release_notes`, contract
  version `1.0.0-draft.1`.
- `docs/program/dispatch/W52-PLAN.md` Stage C2 and §5;
  `W52-ACCEPT-01.md` lane evidence. D-137–D-140 remain open.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: exact six-path lane diff; route and refusal sets unchanged

## Captured premise evidence

- premise: the lane descends from the current ACCEPT grant and changed
  only its six owned paths.

### P-01 — parent and path inventory

- captured_at: 2026-10-08
- command: `git rev-parse 8cbff0e^^; git diff --name-only 0924669..8cbff0e`
- captured_output:
  ```text
  092466980912e3937ca794edd37cd22917e0b53f
  docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md
  docs/program/ALPHA-MANUAL-01.md
  docs/program/W52-ACCEPT-01.md
  scripts/manual-alpha-check.sh
  tests/contract/test_alpha_acceptance_command.py
  tests/e2e/pc01/journey/verify-acceptance.mjs
  ```
- interpretation: the clean lane has been fast-forwarded into the local
  integration tree. The remote target is development only.

## Historical evidence

- correction_mode: addendum
- source_record: `docs/program/ALPHA-MANUAL-01.md`
- addendum_path: `docs/program/W52-ACCEPT-01.md`

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- Exact six paths in P-01 for fast-forward integration only, as granted
  by `tasks/W52-ACCEPT-01.md`.
- `docs/program/tasks/W52-INT-C2-ACCEPT-01.md` and
  `docs/program/W52-INT-C2-ACCEPT-01.md`: integration record.
- `docs/program/CURRENT_STATE.md` opening W52 Stage-C2 status and
  `docs/program/dispatch/W52-PLAN.md` Stage-C2 status only.
- Clean `integration/w51` ref and fast-forward of `origin/dev` only.

## Forbidden hotspots

All other paths: contracts, migrations, API runtime, root dependencies
and locks, generated client, UI, composition root, global styles,
`origin/main`, tags and deployed services.

## Non-goals

No independent QA/judge, full `make gate`, live/manual acceptance,
release ledger row, tag or deployment.

## Deliverables

Exact lane review, merged focused checks, current-tree pin sweep,
six-part report and clean `origin/dev` SHA readback.

## Required checks

- Exact parent/six-path audit; `git diff --check`.
- Shell syntax and ShellCheck; Node syntax; full alpha acceptance
  contract tests with clean-checkout success, build mismatch and absent
  version; wave-governance/prose/count checks.
- `python tools/plan/pin_sweep.py table` for the combined Stage-C2 tree;
  report its findings without inventing a release verdict.
- Re-read `origin/dev` before push and after publication. Full gate and
  live pack remain D-139/D-140.

## Integration contract

Keep the clean lane fast-forward. Commit only the named docs follow-up
after checks, publish the exact checked SHA to `origin/dev` if the remote
still equals the base, and read it back. Stage C2 code is then ready for
separate development close/validation decisions.

## Failure / idempotency / security

Unexpected paths, mismatched build tests, secret leakage, stale remote
or failed applicable checks stop publication. No reviewer credential is
required for local stub tests or written into the report.

## Rollback / feature flag

Dev-only repair is a new reviewed commit. No runtime feature flag.

## Handoff

Return paths, checks/results, contracts, risks, next step and hotspot
proof. No checkpoint or tag.
