# `origin/main` auto-deploy policy

**Effective 2026-11-02 for future release decisions.** A push or merge to `origin/main`
starts an external deployment. The workflow deploys the triggering SHA and verifies the
host, but it does not run a pre-deployment test suite. A release integrator therefore
records the checks on the exact candidate before publishing it.

## Authority and refs

- `origin/dev` carries development candidates. A candidate may be labelled unverified;
  publication there is not a deployment or acceptance claim.
- `origin/main` carries the release trigger line. Only the named release integrator,
  acting under an owner-assigned release task or standing release role that names this
  ref, may update it. Delegation covers successive candidates; the owner does not need
  to merge in GitHub or approve each SHA separately.
- A coding lane, ordinary integration task or green check does not inherit release
  authority. This policy change does not itself appoint a release integrator or publish
  a candidate.

## Release evidence for one exact candidate

The release integrator writes a short record tied to one full SHA:

1. Diff from the currently deployed/main tree and the affected behavior, contracts,
   migrations, auth, dependencies and deploy inputs. Name tests chosen for each risk.
2. Results of those focused checks on the candidate. For a migration, include upgrade
   and rollback/recovery evidence; for external effects, the relevant integration test;
   for a changed screen, browser proof when its interaction matters. Include build or
   typecheck for affected packages. `git diff --check` always runs.
3. Any failed or missing relevant check and its impact. A failure blocks publication;
   an unverified critical path (auth, data integrity, migration or deployment) also
   blocks it. Do not convert host exhaustion into a pass.
4. Whether a complete `make gate` would cover a risk not already covered by the chosen
   checks. Run it once on a capable runner when it would; its absence is not by itself a
   blocker. A prior gate on another SHA is never substituted for candidate evidence.

The release record may be a concise integration report. It need not restate every task
file, contract count or historical decision when those inputs did not change.

## Publish

1. Fetch `origin` and record remote `main`, `dev` and the candidate SHA. Require a clean
   candidate tree and prove `origin/main` is an ancestor of the candidate. Never force
   push or move `main` backwards.
2. Recheck remote `main` immediately before publication. If it moved, reconcile and
   rerun checks affected by the changed diff. Push the exact checked SHA, with no fix
   appended after the checks. Only one main deployment is in flight.
3. Prefer a direct fast-forward push by the release integrator. A GitHub merge button is
   not a required approval step and must not manufacture a different, unchecked SHA.

## Verify and recover

A successful push is not a successful deployment. Keep the release open until the
workflow succeeds for the triggering SHA, `infra/deploy/verify-deployed.sh` succeeds on
that same tree, and the public origin passes its TLS/application/auth smoke checks.
Record the SHA, workflow run and verification output without secrets. If deployment
fails, report it and use a reviewed forward fix or revert with the same release process;
never force-push `main` or hide failure behind a second unreviewed push.

GitHub and host credentials remain in protected stores. They do not belong in source,
logs, task reports or chat.
