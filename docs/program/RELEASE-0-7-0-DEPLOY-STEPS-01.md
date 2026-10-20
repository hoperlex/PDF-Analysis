# Release 0.7.0 — operator steps around the deployment

**Status:** preparation record of 2026-10-20 (integrator). It changes no product file. The
release candidate is the exact commit named by the owner's `origin/main` instruction; this
document is on `origin/dev` only and is not part of that commit.

## Premises (owner, 2026-10-20, `R-140`)

- The stand holds only generated test data, so `R-110` applies: no one-off copy, no `R-92`
  window for this migrating publication.
- A guarded wipe of the stand before the migration is permitted (optional, precautionary).

## What the deployment does to an existing stand

- `deploy-auto` runs `deploy.sh` on the stand host for the pushed SHA; migrations `0022`–`0027`
  apply forward in one step from head `0021_portal_bundles`.
- `0022` has one data step: it sets `finding.canonical_observation_id` from each existing
  finding's only observation and **aborts the migration, and so the deploy, if any finding
  does not have exactly one observation**. It was not exercised on the stand's data. A wipe
  (below) removes the risk; without a wipe, check first on the host (`SELECT finding_uid FROM
  finding f WHERE (SELECT count(*) FROM finding_observation o WHERE o.finding_uid =
  f.finding_uid) <> 1;` must return no row).
- `0024` creates the classification table empty: every existing version stays unclassified and
  cannot start a run or a re-audit until an expert confirms its stage and section.
- The normative corpus is **not** imported on the stand: «Нормы» (catalogue, search) show that
  no current snapshot is designated until the import window (`W55-PLAN.md` §A7, bundle at
  `.local/norms/bundles/…7792e307…` on the development host) is done by the owner.

## Optional wipe (host, operator) — before the push to `main`

```
infra/deploy/reset.sh --database <db> --bucket <bucket> --dry-run
infra/deploy/reset.sh --database <db> --bucket <bucket> --yes-destroy-everything
```

It dumps and verifies the dump first, then drops and recreates the schema, re-runs the
migrations of the currently deployed tree, purges the bucket and clears the session register.
**Accounts are wiped too**: afterwards only the seeded `admin` exists and must change the
default password at first sign-in; other accounts register again and an administrator approves
them. Run it only after the owner has decided to do so, immediately before the push, so the
stand is not left empty for long.

## Order

1. (optional) wipe as above, on the host.
2. Owner's direct instruction naming the exact SHA; integrator re-reads `origin/main`, proves a
   fast-forward, pushes that SHA (no later fix), follows the workflow run to completion.
3. Operator: `infra/deploy/verify-deployed.sh` on the host for the same tree; public TLS probe.
4. After deploy evidence is complete: tag `v0.7.0`, fill the `pending` cells of the `v0.7.0` row
   in `docs/program/RELEASES.md`, remove the «not deployed» wording in `RELEASES.md` and
   `CURRENT_STATE.md` (a documentation commit through `dev`).
5. First sign-in: change the default password; an expert classifies a version before starting a
   run; the norms import window is scheduled separately.

## Rollback

There is no schema rollback by image replacement: the downgrades of `0022`/`0023` refuse once
findings exist and `0024`–`0027` drop their tables (row counts are logged). The recovery path is
the verified dump of `reset.sh` (`--restore`) or a forward revert through the full gate and the
same deployment verification (`MAIN_AUTODEPLOY_POLICY.md`).
