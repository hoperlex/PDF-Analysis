# Task CFB-INT-DEV-PUBLISH-39 — integrate W58 drill fix and unserved W56/W57 reads

task_id: CFB-INT-DEV-PUBLISH-39

## Outcome

A clean fast-forward `origin/dev` candidate contains the W58 driver-safe
pre-restore query and successful isolated synthetic DB/Blob drill record,
plus two checked unserved W56b/W57a read primitives. Exact remote SHA is
read back; no `origin/main` deployment or beta claim follows.

## Depends on

- `CFB-INT-DEV-PUBLISH-38` — published
  `26a9af241bf81f222304a43b9d14c4d50baffe54`;
- `W58-INT-RELATIONS-PLACEHOLDER-FIX-01` — completed at `b8a548ce`;
- `W56B-INT-WINDOW-ANCHOR-PREP-01` — completed at `414c384f`;
- `W57A-INT-REPORT-READ-PREP-01` — completed at `d77e4a50`.

## Frozen inputs

- base commit: `26a9af241bf81f222304a43b9d14c4d50baffe54`
- direct remote read, 2026-10-16: `origin/dev=26a9af241bf81f222304a43b9d14c4d50baffe54`;
- direct remote read, 2026-10-16: `origin/main=23fd729dbb06c642be0588017f6b195305e2e53e`;
- W56b source `414c384f2ae9bd26df561e7e715f459b0ff09b1d`, binary patch SHA-256
  `2e52e44c94a0c26b1b9c82a468bcf76ab9920b33a6d8060cce9848800130ce7a`;
- W57a source `d77e4a50c85870e2e25963ff4b03d4f0ffcde65e`, binary patch SHA-256
  `2643f4b2d8431c1591d9e589bc1c39ef871bb3c98e07dd0f744ee451364e28ab`;
- W58 corrected script SHA-256
  `12068923d6e0b88a1a07ad2b9a5587a342238d6bc762716519ca4ba5948c58af`;
- code-first plan and W58–W63 scope SHA-256
  `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`,
  `81cc57b54e519caa9b284e48565dda5642ecaf228f3b7237ab7e9f7e22c62dee`;
- API 48 paths / 55 operations / 131 schemas, 25 errors, migration head
  `0023_norm_citations` at the base.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: remote dev lacks the three completed source slices; W58
  synthetic target-02 passed after the driver-safe query correction.

### P-01 — remote refs

- captured_at: 2026-10-16
- command: `git ls-remote origin refs/heads/dev refs/heads/main`
- captured_output:
  ```text
  26a9af241bf81f222304a43b9d14c4d50baffe54 refs/heads/dev
  23fd729dbb06c642be0588017f6b195305e2e53e refs/heads/main
  ```
- interpretation: reread before publication; a moved ref stops this task.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `scripts/recovery/isolated_postgres_restore.py`
- `docs/program/tasks/W58-INT-RELATIONS-PLACEHOLDER-FIX-01.md`
- `docs/program/W58-INT-RELATIONS-PLACEHOLDER-FIX-01.md`
- `src/auditmanager/analysis/text/window_anchor.py`
- `tests/integration/analysis_text/test_window_anchor.py`
- `docs/program/tasks/W56B-INT-WINDOW-ANCHOR-PREP-01.md`
- `docs/program/W56B-INT-WINDOW-ANCHOR-PREP-01.md`
- `src/auditmanager/findings/citation_report.py`
- `tests/integration/findings/test_w57a_citation_report_offline.py`
- `docs/program/tasks/W57A-INT-REPORT-READ-PREP-01.md`
- `docs/program/W57A-INT-REPORT-READ-PREP-01.md`
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-39.md`
- `docs/program/CFB-INT-DEV-PUBLISH-39.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependency/lock, composition root,
global styles, other application/runtime source or tests, source corpus,
production DB/S3, `origin/main`, tags and deployment workflow.

## Non-goals

No activation of W56b or W57a routes, provider calls, real client corpus,
stand copy, `origin/main` publication, complete beta gate or beta verdict.

## Deliverables

Exact source slices and W58 drill evidence, this task/report, a short live
state update and direct `origin/dev` SHA read-back.

## Required tests

- direct source patch/path equality and frozen-input readback;
- combined W56b/W57a/W58 offline focused and programme-governance tests;
- W58 real synthetic target-02 result and same-copy/restore digests;
- exact changed-path scope, whitespace, clean tree, fresh remote ref,
  fast-forward proof and push read-back. Full beta gate deferred by R-135.

## Integration contract

Only this integration task updates `origin/dev`; W58 recovery remains
opt-in. W56b and W57a modules remain unserved. W56b still needs policy
freeze and effects; W57a still needs real DB readback, registered v3
profile and authorized route owner. No source SHA's gate evidence applies
to the combined beta tree.

## Failure/idempotency/security cases

A moved ref, dirty tree, drifted source patch or missing synthetic readback
stops publication. No force-push; a retry finding the exact published SHA
does nothing. Ignored `.env`, dumps, logs and Docker volumes remain outside
Git. Do not report the synthetic fixture as a stand backup.

## Rollback / feature flag

Unserved additive code and opt-in recovery tooling can be corrected by
forward commits. No active runtime flag or deployment rollback is involved.

## Handoff

- changed files: exactly the 14 allowed paths;
- contracts: none;
- next: W56b freeze, W57a real PG/citation path, W54 corpus credential;
- forbidden hotspots remain untouched.
