# Task W52-INT-CLOSE — close W52 development implementation

task_id: W52-INT-CLOSE

## Outcome

W52 Stage A–C2 implementation is closed on the development line at one
exact, read-back `origin/dev` SHA. The close records combined focused
checks and explicitly leaves D-137–D-140 and release validation open.

## Depends on

- `W52-GATE-01`, Stage-A code accepted on `origin/dev`.
- `W52-INT-B2C-01`, Stage-B SEAL accepted on `origin/dev`.
- `W52-INT-C-TRANSLATE-01`, Stage C complete on `origin/dev`.
- `W52-INT-C2-RELNOTES-01`, notes accepted at `a6ff1ff`.
- `W52-INT-C2-ACCEPT-01`, Stage C2 published at
  `a183dbf970aad4715a9cfad7010b024fd9d304ac`.
- `W52-INT-RELNOTES-GATE-ENV-01`, local correction complete at
  `35c8f3c2aa331a7be43a113a82aa5a29e3faecc1` for this close.

## Frozen inputs

- Exact published development base
  `a183dbf970aad4715a9cfad7010b024fd9d304ac`;
  `origin/main=9d5b0105334f2f54d80d1f3ee0109b59fb6d8b7c`.
- `VERSION=0.3.0`; API 30 paths / 37 operations / 83 schemas;
  23 error codes; domain revision 9 / 29 identities; migration head
  `0016_release_notes`; `contract_version=1.0.0-draft.1`.
- `docs/program/dispatch/W52-PLAN.md` development-exit amendment,
  Stage C2 and `W52-INT-CLOSE` clause. Its register work requiring new
  QA/gate measurements stays in release validation.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: Stage A/B/C/C2 accepted integration task IDs and
  `pin_sweep.py table` inventory; no new route, error or identity

## Captured premise evidence

- premise: Stage C2 is published, but the current state has no W52
  development-close record; the four deferral debts remain open.

### P-01 — refs and validation boundary

- captured_at: 2026-10-08
- command: `git ls-remote origin refs/heads/dev refs/heads/main;
  rg -n '^\| \*\*D-13[789]\*\*|^\| \*\*D-140\*\*' docs/program/DEBT_REGISTER.md`
- captured_output:
  ```text
  a183dbf970aad4715a9cfad7010b024fd9d304ac refs/heads/dev
  9d5b0105334f2f54d80d1f3ee0109b59fb6d8b7c refs/heads/main
  47:| **D-137** | W51 QA, independent review and live/manual identity acceptance have not run | a separate validation wave must run the built-stand and human checks against one exact candidate |
  48:| **D-138** | W51 development implementation closed without its full end-of-wave `make gate` | a separate validation wave must run and record `GATE OK` for the exact candidate before any release claim |
  49:| **D-139** | W52 and subsequent code-only candidates defer QA, independent review, built-stand and manual acceptance | the validation wave must inventory every accumulated candidate and run the applicable checks on exact SHAs |
  50:| **D-140** | W52 and subsequent code-only candidates defer the full end-of-wave gate | the validation wave must record literal `GATE OK` on the release candidate after corrections |
  ```
- interpretation: development implementation can close under the
  owner's code-first amendment without a release or deployed-state
  claim.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W52-INT-CLOSE.md`,
  `docs/program/W52-INT-CLOSE.md` — task and six-part close record.
- `docs/program/CURRENT_STATE.md` — opening W52 development status.
- `docs/program/dispatch/W52-PLAN.md` — opening status and
  development-exit status sentence only.
- Local `integration/w51` branch and fast-forward `origin/dev` only.

## Forbidden hotspots

Every other path, especially `contracts/**`, migrations, runtime,
generated client, release notes, acceptance implementation, root
dependencies/locks, composition root, global styles,
`DEBT_REGISTER.md`, `origin/main`, tags and deployment.

## Non-goals

No QA, attack, judge or live/manual acceptance; no full `make gate` or
`GATE OK` claim; no debt closure requiring those measurements; no
release ledger row, tag or deployment. The register's D-66/D-68/D-72/
D-78/D-79/D-120/D-121/D-122/D-123/D-133 decisions remain for the
release-validation/close task named in the W52 plan.

## Deliverables

- Exact development lineage and combined focused-check evidence,
  current-tree pin sweep, six-part report and clean published SHA
  readback with D-137–D-140 still open.

## Required checks

- `python tools/plan/pin_sweep.py table` and frozen-facts tests.
- Combined release-loader/prose and alpha-acceptance contract tests;
  W52 release UI focused Vitest; governance/prose checks; shell and
  Node syntax; exact path audit and `git diff --check`.
- Record service-backed checks actually run and all unrun release
  checks; re-read `origin/dev` before and after publication.

## Integration contract

Make a docs-only close commit on the clean published development base.
Publish it as a fast-forward to `origin/dev` after focused checks. It
closes implementation only; a separate validation task must first
perform the deferred checks and register work before any release verdict.

## Failure / idempotency / security

Unexpected path, stale ref or failed applicable focused check stops
publication. No reviewer credential or deployment secret is recorded.

## Rollback / feature flag

Correct a dev-only close statement with a new reviewed commit; no
runtime flag changes.

## Handoff

Return paths, checks/results, contracts, risks, next step and hotspot
proof. No checkpoint or tag.
