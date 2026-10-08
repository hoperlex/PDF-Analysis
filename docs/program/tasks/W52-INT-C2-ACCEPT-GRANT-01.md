# Task W52-INT-C2-ACCEPT-GRANT-01 — refresh ACCEPT base after RELNOTES

task_id: W52-INT-C2-ACCEPT-GRANT-01

## Outcome

`W52-ACCEPT-01` has a current-tree execution base and completed RELNOTES
dependency before its implementation starts.

## Depends on

- `W52-INT-C2-RELNOTES-01`, published on `origin/dev` at
  `a6ff1ff6ea8bf5c21ed125f3a07c9cb613a85a89`.

## Frozen inputs

- Exact `origin/dev` readback
  `a6ff1ff6ea8bf5c21ed125f3a07c9cb613a85a89`;
  `origin/main=9d5b0105334f2f54d80d1f3ee0109b59fb6d8b7c`.
- `VERSION=0.3.0`, API 30/37/83, 23 errors, domain revision 9 / 29
  identities, migration `0016_release_notes`, contract version
  `1.0.0-draft.1`; W52 plan §3.1/§3.4 and Stage C2.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: acceptance journey route/refusal sets remain unchanged

## Captured premise evidence

- premise: the ACCEPT task still names the Stage-C2 grant readback before
  RELNOTES and omits its newly completed dependency.

### P-01 — task base drift

- captured_at: 2026-10-08
- command: `git ls-remote origin refs/heads/dev refs/heads/main;
  git show a6ff1ff:docs/program/tasks/W52-ACCEPT-01.md | rg -n
  'W52-INT-C2-GRANT-01|Start from'`
- captured_output:
  ```text
  a6ff1ff6ea8bf5c21ed125f3a07c9cb613a85a89 refs/heads/dev
  9d5b0105334f2f54d80d1f3ee0109b59fb6d8b7c refs/heads/main
  15:- `W52-INT-C2-GRANT-01`, published on `origin/dev`.
  19:- Start from the exact `origin/dev` SHA read back by
  20:  `W52-INT-C2-GRANT-01`; record it in the lane report.
  ```
- interpretation: update those two task lines and keep the owned paths,
  behavior and test obligations intact.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W52-ACCEPT-01.md`: dependency and frozen-base
  lines only.
- `docs/program/tasks/W52-INT-C2-ACCEPT-GRANT-01.md` and
  `docs/program/W52-INT-C2-ACCEPT-GRANT-01.md`: grant record.
- `docs/program/CURRENT_STATE.md` and `docs/program/dispatch/W52-PLAN.md`:
  opening Stage-C2 status only if needed.
- Local integration branch and fast-forward `origin/dev` only.

## Forbidden hotspots

Every other path, including acceptance implementation, release notes,
contracts, migrations, root dependencies/locks, generated client,
composition root, global styles, `origin/main`, tags and deployment.

## Non-goals

No acceptance implementation, judgment, full gate, live acceptance,
release row, tag or deployment.

## Deliverables

Current-tree ACCEPT task, exact three-path or narrower grant diff,
governance/prose checks and clean development SHA readback.

## Required checks

- Exact base/remote readback, allowed-path audit, `git diff --check`.
- Wave-governance and prose/count tests on the docs candidate.

## Integration contract

Publish only this docs grant to `origin/dev` as a fast-forward. The ACCEPT
lane must start from its readback, not the earlier Stage-C2 grant SHA.

## Failure / idempotency / security

A stale remote or unexpected path stops publication. No credentials enter
this grant.

## Rollback / feature flag

Correct dev-only task prose by a new reviewed commit. No runtime flag.

## Handoff

Return paths, checks, contracts, risks, next step and forbidden-hotspot
proof. No checkpoint or tag.
