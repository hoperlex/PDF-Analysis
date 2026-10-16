# Task CFB-INT-STATE-49 — refresh development state after dev48

task_id: CFB-INT-STATE-49

## Outcome

Publish an accurate top summary of the code-first development state through
the exact dev48 candidate, without changing the retained dated history or
claiming beta, corpus publication or a new deployment.

## Depends on

- `CFB-INT-DEV-PUBLISH-48`, completed at `3a7c558a862d975f5305f6c54b15c6dfa5e9dca6`.

## Frozen inputs

- base commit: `3a7c558a862d975f5305f6c54b15c6dfa5e9dca6`
- API SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- `origin/main` and `v0.6.0`: `37393a979a430e490843d7f410e9eca9491a4ea1`;
- `VERSION=0.6.0`, migration head `0023_norm_citations`;
- `R-135` defers full beta gate until the last code candidate.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the top of `CURRENT_STATE.md` still names dev43 although dev48 is
  the checked and remotely read-back development ref.

### P-01 — outdated top heading

- captured_at: 2026-10-16
- command: `sed -n '1,4p' docs/program/CURRENT_STATE.md`
- captured_output:
  ```text
  # Current state

  **Updated 2026-10-16, after code-first development candidate 43.** W55b is
  published on `origin/main` and tagged `v0.6.0`. Its exact-tree gate counts as
  ```
- interpretation: refresh only the live summary; the dated dev39 body remains
  historical evidence.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/CURRENT_STATE.md`
- `docs/program/tasks/CFB-INT-STATE-49.md`
- `docs/program/CFB-INT-STATE-49.md`

## Forbidden hotspots

Product source/tests, `contracts/**`, migrations, root dependency/lock files,
composition root, global styles, deployment workflow, private corpus and
credentials, `origin/main` and tags.

## Non-goals

No implementation, corpus repair/import, gate conclusion, beta acceptance,
deployment, client-data policy or rewrite of historical dated snapshots.

## Deliverables

Updated live summary, task/report, focused document/governance checks,
exact-path handoff and dev fast-forward/readback.

## Required tests

- Programme governance selection, frozen API SHA, exact three-path diff,
  whitespace and clean-tree handoff: pass.
- Fresh remote dev/main/tag read, fast-forward proof, exact-SHA dev push and
  readback. No full gate for this documentation-only intermediate candidate.

## Integration contract

The top summary cites the exact dev48 source reports and preserves the dated
dev39 snapshot. Only this integration task advances `origin/dev`; no product
contract or runtime changes.

## Failure/idempotency/security cases

Stop on moved dev, dirty tree, path expansion, inaccurate state or failed
check. No force push or private payload enters Git. Repeating the exact
published SHA is a no-op.

## Rollback / feature flag

Correct the summary with a reviewed forward documentation commit. No runtime
flag or data rollback is needed.

## Handoff

- changed files: three exact allowed paths;
- contracts: none;
- checks and limitations: paired report;
- forbidden hotspots untouched.
