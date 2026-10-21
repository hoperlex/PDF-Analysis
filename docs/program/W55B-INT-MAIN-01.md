# W55B-INT-MAIN-01 — exact W55b main publication

## Authority and candidate

On 2026-10-16 the owner directly corrected the publication target to
`origin/main` after the integrator named exact candidate
`37393a979a430e490843d7f410e9eca9491a4ea1` and current main
`23fd729dbb06c642be0588017f6b195305e2e53e`. This task owns only that
candidate's fast-forward publication. The owner immediately reconfirmed that
the alpha stand contains no real client data and that the deployment-host
`AUDITMANAGER_RUN_COST_CEILING_USD` is above USD 0.80. Thus the R-110
test-data-only copy waiver and the W55b budget stop condition are satisfied
for this publication; this statement does not cover later client uploads.

## Preflight

- The candidate is a clean detached tree at the exact SHA, `VERSION=0.6.0`.
- Fetched `origin/main` and direct `ls-remote` both named `23fd729d`; the
  candidate is its fast-forward descendant.
- `contracts/api/v1/openapi.json` re-counted to 47 paths, 54 operations and
  123 schemas. W55b close records 24 errors and migration head
  `0021_portal_bundles`; the candidate contains that migration.
- W55 plan, auto-deploy policy and close report SHA-256 values match the
  frozen task values. The workflow is serialized with
  `cancel-in-progress: false` and checks out the exact triggering SHA on the
  host before `deploy.sh` and `verify-deployed.sh`.
- GitHub API showed no in-flight main deployment: the latest run
  `38356461757` for old main `23fd729d` was completed successfully.
- `W55B-INT-MAIN-PREP-03.md` and `.local/gates/r125-evidence.md` carry the
  full `make gate` attempt and same-SHA/same-stand completion under R-125.
  Rehashed four ignored logs; their SHA-256 values match the ledger. The
  whole failed `runs` directory and exact unrun remainder were rerun; the
  lone lease timing failure's whole `jobs` directory passed 8/8. The gate
  counts as `GATE OK` under R-125, without a literal single-run sentinel.
- `git diff --check 23fd729d..37393a97` reports one inherited trailing
  blank line in `docs/program/W55B-WEB-BLOCKS.md:363`; no post-gate edit is
  allowed and the product/test gate result is unaffected.

## Publication and deployment

The remote `main` was re-read immediately before push as `23fd729d`.
`git push origin 37393a979a430e490843d7f410e9eca9491a4ea1:refs/heads/main`
succeeded as a fast-forward (`23fd729d..37393a97`). Direct remote readback
named the exact candidate. GitHub workflow run
[`38897018419`](https://github.com/hoperlex/PDF-Analysis/actions/runs/38897018419)
selected the same `head_sha` and completed with GitHub conclusion `success`
at 11:58:09Z. Its job and `Deploy and verify exact commit` step are also
marked `success`.

The authenticated workflow log archive has SHA-256
`db1be92b1259c7ced95cb06b5f48a08e6488b19b1fc354ed53b4cd4e98b1c39c`
for `Deploy and verify exact commit.txt`. It prints the requested SHA,
`check-db: current 0021_portal_bundles`, `FOUNDATION-CHECK OK check-db`,
the loopback protected API's 401, and `frozen ops : 54`, `served ops : 54`,
`differences: 0`. The last actual line is `deploy.sh` advising the operator
to run `infra/deploy/verify-deployed.sh`. The log has **no actual**
`=== verify deployed tree ===`, no output from that script and no `DEPLOY OK`.
The earlier occurrences of those strings are only echoed shell source in
the GitHub step preamble. Thus the green job does **not** prove item 3 of
`MAIN_AUTODEPLOY_POLICY.md`. The remote `bash -s` heredoc can be drained by a
child command; this is the leading explanation, pending a focused
reproduction. A separate workflow repair is being prepared. This task's
deployment status is **incomplete**, with no release tag or same-SHA host
verification claim.

The exact candidate's `scripts/manual-alpha-check.sh --preflight-only` on
the public TLS origin passed: `/` -> 307 to login, `/login` -> 200,
unauthenticated `/api/v1/openapi.json` -> 401, and synthetic upload fixture
checks green. Its ignored report is
`.local/manual-alpha/20261016T115919Z-2392561/report.md` in the isolated
candidate worktree. This proves public reachability and boundary behavior,
not image/tree identity. No credentialed in-product acceptance was run.

## Scope

The W55b candidate tree remains untouched. This task changes only its own
task/report records in the separate development worktree and the explicitly
authorized remote `origin/main` ref. It changes no contract, migration,
dependency, composition root, global style or deployment input.
