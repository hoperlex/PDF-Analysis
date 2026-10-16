# CFB-INT-DEV-PUBLISH-43 — deploy workflow repair in development

The published development base was
`f812014588010f408e0594d56f1d9f41d1379227`. The scoped source repair
`babab5b5ba30f35dde8be058e143ad5a2f286943` was cherry-picked as
`0fbe358753238bbdbc0134d2a658c516eff7f4f7`. Only the workflow,
its behavioral contract test and its original task/report changed before
this integration record.

The original `origin/main` workflow run `38897018419` stopped after
`deploy.sh` and did not run the verification lines, even though the job
was green. The owner separately executed `verify-deployed.sh` on the host;
`W55B-INT-MAIN-VERIFY-ADDENDUM-01.md` records its exact-tree success.
The source repair feeds `/dev/null` to deploy and verify child scripts.
The regression extracts the actual remote heredoc, uses a child that
drains stdin and proves verification runs and a failing verification
prevents `DEPLOY OK`.

On the integrated dev candidate, the workflow and programme suites passed
**24 tests and 2 subtests**. `git diff --check` passed. No product source,
contract, migration, dependency, composition root, global style, deploy
script, DB/S3 data, main ref or tag changed. A full gate on the isolated
repair commit is running separately; no same-SHA main release result or
new deployment is claimed from this dev integration.

The integrator records the clean-tree handoff and exact dev ref readback
after commit. The deployed `v0.6.0` remains at `37393a97`.
