# CFB-INT-DEV-PUBLISH-24 — W55b D-142 test correction on dev

The candidate builds on directly read
`origin/dev=e70c91ef7064c8e36f377bd3995960a0e93acf35`.
Completed W55b repair commit
`37393a979a430e490843d7f410e9eca9491a4ea1` was merged as `83fc45b6`
with `--no-ff`, preserving the exact source commit as a development ancestor.
Its payload is one integration test plus its task and report. The test now
selects the original crashed Attempt and the separately reclaimed Attempt
by their publication identities, so legitimate rows for one Run/Blob cannot
make the assertion ambiguous.

## Checks and scope

- The source repair passed **2/2 D-142 tests** on fresh isolated
  PostgreSQL/S3 at W55b head `0021_portal_bundles` and 16 governance tests;
  its containers were stopped. This integrated tree collected all 20 tests
  in the changed module without a DB lane and passed **28 programme tests**.
  Direct task governance returned `[]`.
- The source diff is exactly the test, task and report named in the
  integration grant; merge ancestry includes `37393a97`. The integration
  commit changes only this report, its task and bounded `CURRENT_STATE.md`.
- Dev still has API 47 paths / 54 operations / 124 schemas, 25 error codes,
  domain candidate revision 14 and head `0023_norm_citations`. No shared
  contract, migration, root dependency or lock, composition root, global
  style, production DB/S3, `origin/main`, tag or deployment input changed.

The separate clean W55b main candidate is exact `37393a97`, with API
47/54/123, 24 error codes and head 0021. Its complete `make gate` is
waiting for the host memory/load window; this dev integration is **not** a
full-gate pass or deployment acceptance. R-135 defers the full W56–W63 beta
gate independently of W55b's release gate.

## Publication and next step

Publish only the clean exact checked SHA to `origin/dev` as a fast-forward
from the recorded predecessor, then directly read back the remote SHA into
ignored local evidence. This task has no `origin/main` authority. Any main
publication requires the literal `GATE OK` on the unchanged W55b SHA,
direct exact-SHA owner instruction and the full auto-deploy verification
chain.
