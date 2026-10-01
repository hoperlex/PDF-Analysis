# `origin/main` auto-deploy policy

**Effective for publication decisions from 2026-10-01.** The owner is connecting GitHub
auto-deploy to `origin/main`. Until the workflow exists and its first run is verified, this
document records the required boundary; it does not claim the automation is already operational.

## The boundary

A push or merge to `origin/main` is an externally consequential deployment request. It is not a
repository-only cleanup operation. This includes a pull-request merge, an integration
fast-forward and any command that updates `refs/heads/main`.

Only an explicitly assigned integration task whose integration contract names `origin/main` may
perform that update. Implementation, documentation, review and repair lanes do not inherit push
authority from having a green local branch.

The operator-provided temporary alpha address is
`https://audit.135.106.164.147.sslip.io/`. On 2026-10-01 at 14:46 MSK it was observed with a
valid TLS chain, `/` answered `307` to `/projects`, and unauthenticated
`/api/v1/openapi.json` answered `401`. This is point-in-time reachability evidence only. It does
not identify the deployed Git revision and must not replace `infra/deploy/verify-deployed.sh`.

## Before updating `origin/main`

The integration owner must keep one evidence chain for one exact candidate SHA:

1. Fetch `origin` and record the current remote `main`; stop if it moved during integration.
2. Require a clean candidate tree and prove the update is a fast-forward with
   `git merge-base --is-ancestor origin/main <candidate>`.
3. Run the complete canonical `make gate` on that exact candidate and require the literal
   `GATE OK` sentinel. A partial rerun, an inherited earlier log or a gate from another SHA is
   not evidence.
4. Re-read the frozen contract counts, error catalog, migration head and deployment inputs. Any
   owned change must be recorded by the integration task; an unowned change stops publication.
5. Re-read `origin/main` immediately before the push. Push the intended SHA as a fast-forward;
   never force, never move `main` backwards and never add a post-gate fix to the pushed tip.

Only one deployment publication may be in flight. The workflow must serialize main deployments;
a later push must not race or silently cancel the proof for an earlier SHA.

## After the push

A successful Git push proves only that Git accepted the ref. The integration task remains open
until all of the following hold for the same SHA:

1. The GitHub workflow completed successfully rather than being skipped, cancelled or green on
   an unrelated job.
2. The deployment job selected the triggering commit SHA, not whatever `main` happened to name
   later.
3. On the deployment host, `infra/deploy/verify-deployed.sh` exits `0` against the checkout used
   for deployment.
4. The public origin answers over verified TLS, `/` reaches the application, and an
   unauthenticated protected API operation is refused by the application boundary.
5. The integration report records the candidate SHA, workflow run identity and the literal
   verification results without copying secrets or `docker compose config` output.

If any item fails, report a failed or incomplete deployment. Do not repair it with an unreviewed
follow-up push merely because the change is small.

## Rollback and secrets

Rollback is another deployment: create an explicit reviewed revert, run the complete gate and
fast-forward that new commit through the same procedure. Rewriting or force-pushing `main` is
forbidden.

GitHub and host credentials belong in protected environment/host storage. They do not belong in
repository files, workflow logs, task reports or chat. The ignored deployment env files remain
host-owned and mode `0600`.

## What this document does not claim

- It does not implement or enable the workflow.
- It does not claim what SHA is currently deployed.
- It does not turn `origin/dev`, tags or agent branches into deployment triggers.
- It does not replace `infra/deploy/deploy.sh`, `infra/deploy/readiness.sh` or
  `infra/deploy/verify-deployed.sh`.
