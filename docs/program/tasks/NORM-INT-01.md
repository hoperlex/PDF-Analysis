# Task NORM-INT-01 — publish the normative-corpus foundation to `origin/main`

## Outcome

The accepted normative-corpus foundation is one gated commit on `origin/main`. An alpha
operator can update an existing VPS without overwriting its secrets, can see that migration
`0012_norms_corpus` runs automatically, and is not told to configure pgvector, embeddings,
custody uploads or search before those runtime slices exist.

## Depends on

- `NORM-LEDGER-01` — completed: repair-ledger text reaches the deterministic projection
- `NORM-PERSIST-01` — completed: migration, repository and idempotent DB loader
- `NORM-ID-01` — completed: opaque document and paragraph identities
- `NORM-CUSTODY-01` — completed: immutable PDF/crop custody handoff
- `NORM-EMBED-EVAL-01` — completed: measured embedding profile recommendation

## Frozen inputs

- base release: `alpha-w47` at `acc6463`
- API: 17 paths / 20 operations / 61 schemas; unchanged
- domain candidate revision: 8 with 27 identities
- incoming migration head: `0011_document_section`
- outgoing migration head: `0012_norms_corpus`
- publish target: fast-forward `origin/main` only; no tag and no `origin/dev` move

## Ownership

This task owns the integration commit, the one requested `origin/main` ref update, the alpha env
example and the VPS update/runbook clarification. It accepts the completed dependency task paths
as delivered and does not reopen their implementation slots.

## Allowed paths

- all delivered paths named in the five dependency-task handoffs
- `docs/program/tasks/NORM-INT-01.md`
- `docs/program/CURRENT_STATE.md`
- `docs/program/DEPLOYMENT_RUNBOOK.md`
- `infra/deploy/README.md`
- `infra/deploy/env/alpha.env.example`
- Git integration commit and `origin/main` fast-forward

## Forbidden hotspots

- API/analysis/comparison/event contracts
- any migration other than delivered `0012_norms_corpus`
- root dependency and lock files
- compose topology, deployment scripts and global styles
- storage/ingest/MinIO implementation and secrets
- source corpus `.local/norms/corpus/**`
- `origin/dev` and every release tag

## Non-goals

- No deployment to a VPS from this task and no mutation of an existing `alpha.env`.
- No corpus import into a persistent alpha database.
- No pgvector image/extension, embedding runtime, search API/UI or custody implementation.
- No claim that the 121-page repair ledger exists before the credentialed run.
- No `alpha-w48` tag: W48 remains the separately planned host/optimisation wave.

## Deliverables

- operator-facing alpha env template aligned with the environment actually consumed by compose
- VPS fast-forward/redeploy instructions that preserve the ignored secret files
- an explicit current-solution boundary for migration, loader, MinIO custody and embeddings
- one gated integration commit pushed as a fast-forward to `origin/main`

## Required tests

- `make gate` — literal `GATE OK`
- targeted norms, identity, migration and deployment-document guards
- `git diff --check`
- `git merge-base --is-ancestor <old-origin-main> HEAD`
- after push: remote `refs/heads/main` equals the local integration commit

## Integration contract

- `deploy.sh` builds the new image and its one-shot `migrate` service upgrades alpha to
  `0012_norms_corpus`; the serving process never races migrations.
- The deployment environment gains no corpus/vector/model variable in this release.
- The corpus loader is a deliberate DB-only operator command with filesystem inputs; it is not
  executed by deploy and the product does not yet query its rows.
- Existing VPS `infra/deploy/env/alpha.env` and optional `provider.env` remain host-owned and must
  not be replaced during `git pull`.

## Failure / idempotency / security cases

- Remote drift is checked before push; a non-fast-forward is refused, never force-pushed.
- Re-running `deploy.sh` is safe and migration `0012` is idempotently already-at-head.
- Copying the example over an existing secret file is explicitly forbidden in the update path.
- No credential, corpus bytes or local environment file enters the commit or command output.

## Rollback / feature flag

There is no behavior flag because no runtime consumer reads the new corpus projection. Before a
snapshot is referenced, a disposable database may downgrade migration `0012`; on an alpha holding
canonical evidence, rollback is database restore or forward repair. Git rollback is a reviewed
revert commit, never a history rewrite or forced remote update.

## Handoff

- changed files: completed dependency-task paths plus this task, alpha env example, deployment
  reference/runbook and current-state publication boundary
- commands/results: canonical `make gate` printed literal `GATE OK`: foundation **35 passed**;
  backend **2625 passed / 5 skipped / 4 warnings / 169 subtests**; frontend lint and typecheck
  passed, Vitest **1162 passed in 82 files**; final whitespace check passed
- contracts: domain candidate revision 8; API unchanged; migration head `0012_norms_corpus`
- known limits: pgvector/runtime embeddings/search, MinIO custody implementation, corpus import
  and the credentialed 121-page repair run remain follow-up work
- integration notes: deploy from repository root, preserve host-owned `.env` files, then run
  `verify-deployed.sh`; no release tag or `origin/dev` move belongs to this task
