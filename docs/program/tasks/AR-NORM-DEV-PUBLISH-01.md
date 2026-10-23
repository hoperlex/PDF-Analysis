# Task AR-NORM-DEV-PUBLISH-01 — publish prepared set promotion on dev

task_id: AR-NORM-DEV-PUBLISH-01

## Outcome

The completed `AR-NORM-DEV-INT-01` retrieval-set promotion and draft-profile
audit are merged with the already published AR v3 prompt correction and
published as a fast-forward development candidate on `origin/dev`.

## Depends on

- `AR-NORM-DEV-INT-01` — completed at `49866c68`.
- `AR-V3-PROMPT-REDO-01` — completed and published at `0261ca54`.
- `AR-SET-PROMOTION-01` — completed source and synthetic DB/Blob acceptance.

## Frozen inputs

- `origin/dev=0261ca54e2272a93be84b11d456c321fb21ce6d7` at task start;
- contract `1.0.0`, API 87 paths / 99 operations / 284 schemas, 27 errors;
- migration head `0031_executor_pull_channel`; R-135 intermediate code-first
  checks, no final beta gate.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the source candidate adds only promotion/Run-pin seams and documents
  the 14 still-draft profiles. The remote dev head already has prompt correction.

### P-01 — source and remote ancestry

- captured_at: 2026-10-23
- command: `git diff --name-only 0261ca54..c0ab3d12`
- captured_output:
  ```text
  docs/program/AR-NORM-DEV-INT-01.md
  docs/program/AR-ORIGINAL-CITATIONS-PLAN-01.md
  docs/program/AR-SET-PROMOTION-01.md
  docs/program/tasks/AR-NORM-DEV-INT-01.md
  docs/program/tasks/AR-ORIGINAL-CITATIONS-PLAN-01.md
  docs/program/tasks/AR-SET-PROMOTION-01.md
  src/auditmanager/norms/public.py
  src/auditmanager/norms/retrieval/promotion.py
  src/auditmanager/norms/retrieval/promotion_repository.py
  src/auditmanager/runs/commands.py
  src/auditmanager/runs/repository.py
  tests/integration/norms/custody/test_retrieval_set_promotion.py
  tests/integration/norms/retrieval/test_promotion.py
  tests/integration/runs/test_retrieval_set_persistence.py
  ```
- interpretation: the merge adds only paths already owned by the completed
  source tasks; the present task owns only its two documentation paths.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/AR-NORM-DEV-PUBLISH-01.md`
- `docs/program/AR-NORM-DEV-PUBLISH-01.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependencies/locks, composition root,
API/UI/global styles, corpus, served provider/profile, `origin/main`, tags and
deployment host. Source changes stay within `AR-NORM-DEV-INT-01` paths.

## Non-goals

No v3 activation, reviewed legal map, qualified real set, expert sign-off for
profiles, paid call, full beta gate, release or main deployment.

## Deliverables and checks

This task/report, merged exact-tree focused tests, compilation, governance,
clean tree, rechecked remote ref, fast-forward push and readback. The source
task's synthetic real DB/Blob acceptance remains evidence; do not start a new
lane on this host while free disk is below 6144 MiB.

## Integration contract

`origin/dev` advances only if its rechecked SHA equals the frozen head and is
an ancestor of the checked candidate. The promotion API remains unserved; Run
set pin is NULL on v1/v2. A later owner supplies reviewed map, qualified
snapshot, exact expected digests and custody before v3 selection.

## Rollback / feature flag

Forward revert the integration if needed; no migration or served flag changes.
