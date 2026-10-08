# Task W52-INT-MAIN-01 — publish the checked development snapshot to main

task_id: W52-INT-MAIN-01

## Outcome

The development snapshot `fd78ad8c76f21e034d81c0b1af0e8c2d1d75b022` is
merged with the existing main hotfix. Gate repairs found on the exact merge
candidate are applied once, and the clean, fully gated successor is published
to `origin/dev` and then `origin/main`. The serialized workflow and deployment
host must verify that same commit.

## Depends on

- `W51-INT-HOTFIX-01`, completed on `origin/main` at `1e9bb1308b7b97cd75eef28e206b23c569871b68`.
- `W52-INT-A2B-01`, completed on `origin/dev` at `fd78ad8c76f21e034d81c0b1af0e8c2d1d75b022`.

## Frozen inputs

- Remote `origin/main`: `1e9bb1308b7b97cd75eef28e206b23c569871b68`.
- Remote `origin/dev`: `fd78ad8c76f21e034d81c0b1af0e8c2d1d75b022`.
- Domain candidate revision 9 / 29 identities; API 27 paths / 34 operations /
  77 schemas; error catalog 23; migration head `0015_accounts_roles_registration`.
- `docs/program/MAIN_AUTODEPLOY_POLICY.md`; the owner's direct 2026-10-08
  instruction to bring this `origin/dev` version to `origin/main` and explicit
  clarification that this is main-publication authority.
- The W51 production hotfix is already backported on dev by
  `W52-INT-HOTFIX-BACKPORT-01`. Stage B `W52-SEAL-01` remains outside this
  frozen snapshot.
- The first merge candidate `91292fe40cd01bc05f286557a88c09f58b7a5156`
  passed the production Next.js build but exposed three gate failures: the
  new DB fixture was not re-exported to two suites, characterization leaked
  provider mode, and two task records failed the current governance guard.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the original remote refs diverge because main has a separate W51 hotfix.
- captured_at: 2026-10-08
- command: `git ls-remote --heads origin dev main`
- captured_output:
  ```text
  fd78ad8c76f21e034d81c0b1af0e8c2d1d75b022 refs/heads/dev
  1e9bb1308b7b97cd75eef28e206b23c569871b68 refs/heads/main
  ```
- interpretation: the checked successor must contain both parents before
  either remote ref advances.

## Historical evidence

- correction_mode: addendum
- source_record: docs/program/tasks/W51-INT-HOTFIX-01.md
- addendum_path: docs/program/W52-INT-MAIN-01.md

## Publication authority

- development_target: origin/main
- origin_main_authority: separate direct owner instruction 91292fe40cd01bc05f286557a88c09f58b7a5156

The referenced merge commit records the owner's 2026-10-08 request and direct
clarification to update `origin/main` from `origin/dev`. This task also advances
`origin/dev` first, under the user's instruction to retain the hotfix there.

## Allowed paths

- The Git merge of the two exact frozen refs, with all inherited development
  files taking their exact `origin/dev` blobs.
- `web/tests/guards/rendered-language.guard.test.ts`: resolve the sole merge
  conflict to the already accepted dev blob, which retains the W51 correction
  and later D-128 F-1 coverage.
- `docs/program/tasks/W52-INT-MAIN-01.md`: this publication grant and record.
- `docs/program/tasks/W51-INT-HOTFIX-01.md`: only the governance reference
  format for its already recorded direct owner instruction.
- `docs/program/W52-INT-MAIN-01.md`: correction and pre-publication evidence.
- `tests/integration/access/conftest.py` and
  `tests/integration/api/qa_w49/conftest.py`: expose both levels of the new DB
  clone fixture to their child tests.
- `tests/characterization/w13_baseline/journey.py`: remove an unnecessary
  process-wide provider-mode assignment; the composed app already receives
  recorded mode explicitly.
- One merge commit and one gate-repair commit on
  `integration/w52-main-publication`, then fast-forward `origin/dev` and
  `origin/main` to the exact same gated SHA.

## Forbidden hotspots

No newly authored contract, migration, root dependency/lock, composition-root,
global-style or deployment-input change; no change to a development blob outside
the listed corrections. No tag, force-push or post-gate fix. The inherited
changes were authored under their completed development tasks.

## Non-goals

No W52 Stage B/C implementation, release tag, new API or migration, and no
claim that the deferred D-137–D-140 QA or manual acceptance is complete.

## Deliverables

- A clean successor containing both parent histories, the exact dev product
  content and narrowly scoped gate corrections.
- Complete `make gate` with literal `GATE OK` on that successor; production web
  build and deployment-input review.
- Exact-SHA workflow, host verification and public-origin evidence in the
  integration report, without a second post-deployment commit.

## Required checks

- `git diff --check`; `git merge-base --is-ancestor origin/main HEAD` and
  `git merge-base --is-ancestor origin/dev HEAD`.
- Focused governance, PC-01 and DB clone fixture tests on the repaired tree.
- `make gate` on a clean committed tree with literal `GATE OK`.
- `npm --prefix web run build` on the same tree; review the pinned deployment
  Dockerfiles, compose inputs and workflow.
- Re-read both remote refs immediately before push and verify fast-forward of
  the exact gated SHA. Publish dev first, then main. Verify workflow success, selected SHA, host
  `infra/deploy/verify-deployed.sh` result and public TLS/application probes.

## Integration contract

Only this task publishes its gated successor to `origin/main` under the
owner's direct instruction. Preserve both frozen parents and dev's tested
guard; the three gate corrections are the only changes beyond their merged
content. Stop publication if a check or ref readback differs. The GitHub
workflow is serialized with `cancel-in-progress: false`.

## Rollback / feature flag

No feature flag applies to this publication. A rollback is a newly reviewed,
fully gated forward revert and another exact-SHA deployment; history rewrite is
forbidden.
