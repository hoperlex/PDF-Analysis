# Task W56A-INT-PROBE-TOOL-01 — publish bounded probe tool on dev

## Outcome

`origin/dev` contains the offline-checked W56a one-call probe tool, with no
gateway PASS claim, pin or provider activation.

## Depends on

- `W56A-INT-MATCHER-CORE-01` — complete at `6de331c1`;
- `W56A-PROBE-TOOL-PREP-01` — complete at `f2115754`.

## Frozen inputs

- remote predecessor `6de331c150f6573e320093bb4b2751f3bda016a2`;
- source `f21157544b4b0c24a31366e04980e14c90795dec`;
- API/error/analysis SHA-256 `fad81bc0` / `89e155fc` / `bd1e5b91`;
- model lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`;
- migration head `0022_findings_v2`; R-135 excludes a full local gate.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: source is a direct descendant of the read-back dev predecessor.

### P-01 — ancestry

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev && git merge-base HEAD origin/dev`
- captured_output:
  ```text
  f21157544b4b0c24a31366e04980e14c90795dec
  6de331c150f6573e320093bb4b2751f3bda016a2
  6de331c150f6573e320093bb4b2751f3bda016a2
  ```
- interpretation: a normal fast-forward can publish the source if remote
  dev still equals the predecessor; this says nothing about gateways.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W56A-INT-PROBE-TOOL-01.md`;
- `docs/program/W56A-INT-PROBE-TOOL-01.md`;
- `docs/program/CURRENT_STATE.md` (top development note only);
- normal fast-forward of `origin/dev` from the frozen predecessor.

## Forbidden hotspots

- contracts, migrations, P02/root lockfiles, runtime and web code,
  composition root, global styles, credentials, deployment configuration,
  `VERSION`, `origin/main`, tags and stand state;
- changes to the five source-lane files beyond the accepted `f2115754`.

## Non-goals

- No paid gateway call, lock pin, PROVIDER grant, full local gate,
  acceptance, release or deployment.

## Deliverables

- dev development-state entry and integration report;
- exact source-path and SHA proof, focused checks and fast-forward read-back.

## Required tests

- repeat the 14 focused probe-tool tests and changed-doc prose checks;
- direct governance check of both new task files; `git diff --check`;
- compare remote dev with predecessor immediately before push;
- normal fast-forward push and exact remote read-back. No full local gate.

## Integration contract

`W56A-MODEL-PIN-01` starts from the published dev SHA and may use the tool
only with sanctioned gateway access and fresh spend projection. Its task
file is a later grant, not part of this integration's source diff. No
`P02_LOCK.json` write or live recording follows from this publication.

## Failure/idempotency/security cases

- If remote dev moves, rebase/recheck; never force-push.
- A test failure or changed forbidden path stops publication.
- Development publication conveys no stand state or credential.

## Rollback / feature flag

The tool is offline and unused by runtime; revert its source commit before
dependent use or correct forward afterward. No feature flag or data rollback.

## Handoff

- changed files: three Allowed document paths, plus the accepted five-file
  source ancestor;
- checks/results, ref and limits: `docs/program/W56A-INT-PROBE-TOOL-01.md`;
- next: refresh MODEL-PIN on read-back dev, preserving its gateway block.
