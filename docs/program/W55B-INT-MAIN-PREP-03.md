# W55B-INT-MAIN-PREP-03 — D-142-repaired release candidate

## Candidate and scope

The isolated W55b candidate is the clean detached commit
`37393a979a430e490843d7f410e9eca9491a4ea1`. It is a fast-forward
descendant of directly read `origin/main=23fd729dbb06c642be0588017f6b195305e2e53e`.
After W55b close `6d63802a`, two test-only corrections alter the serving
carrier deadline and D-142 Attempt-specific assertion. Production code is
byte-identical to W55b close; current W56–W59 development slices on
`origin/dev` are outside this release candidate.

`VERSION=0.6.0`; migration head `0021_portal_bundles`; expected API 47 paths,
54 operations, 123 schemas and 24 error codes. W55 plan, main auto-deploy
policy and W55b close report retain their task-pinned SHA-256 digests. The
candidate tree is clean. `make gate-preflight` passed with 8,686 MiB free on
both the worktree and Docker data filesystems. The earlier disposable W55b
gate PostgreSQL/S3 volumes were removed after confirming no W55b or W57A
containers were running. The D-142 repair source passed 2/2 focused tests
on a separate fresh PostgreSQL/S3 lane and 16 governance tests.

## Full gate result

The complete `make gate` attempt on this exact clean SHA passed frontend
lint/typecheck and Vitest (137 files / 2,047 tests), contract tests (806 tests
/ 19,278 subtests) and foundation (35 tests). The changed-context battery
reached 4,173 passes, 3 skips, 10 failures and 47 errors; all failures and
errors were in `tests/integration/runs` with `StorageUnavailableError` from
the disposable S3 service after the host fell to about 2,180 MiB available
RAM and load1 rose to 15.87. It exited 2 after interruption and did not print
`GATE OK`. The exact voided log is
`.local/gates/w55b-main-d142-37393a97.log`, SHA-256
`747859a28246dbc40ebf687184df91fcd24e5c1d282aa983af446c0b30c05d71`;
the failure summary is at lines 4437–4493.

Under owner ruling `R-125`, the complete failed `tests/integration/runs`
directory and the unrun `tests/integration/shared_kernel` directory passed
on the same clean SHA and stand: 210 passed, 244 subtests passed. The exact
unrun canonical remainder then had 938 passes, 5 skips, 4 subtests passed
and one artificial two-second lease timing failure in `tests/integration/jobs`.
The whole `jobs` directory then passed 8/8 on the same SHA and stand. This is
the same lease-timing test and whole-directory remedy recorded in
`W55B-INT-CLOSE.md`. All gate components are green; the candidate **counts as
`GATE OK` under R-125**, not as a literal sentinel from one command.

The three completion logs and SHA-256 values are:

| Log under ignored `.local/gates/` | Result | SHA-256 |
| --- | --- | --- |
| `r125-runs-shared-37393a97.log` | 210 passed, 244 subtests | `048c917e6ac92c7e7bcb296936a37fd95d48aab4c61d3235ebcb61c8d8c59b1f` |
| `r125-remainder-37393a97.log` | 938 passed, 5 skipped, 4 subtests, one lease timing failure | `943cddb9b11317fa0aa709a92500298a7bbae1762cdf69747b03a54c38c0d462` |
| `r125-jobs-37393a97.log` | 8 passed | `dd45c22a56ee67ec27a890c99b403bdb4241a84e6a512ea2c44f90d215e96d39` |

The ignored `.local/gates/r125-evidence.md` records the commands, paths,
resource samples and same-stand checks. The predecessor `d3acd511` result
is not inherited. This gate completion alone grants no deployment authority.

## Remaining deployment conditions

This task does not publish `origin/main` or deploy. The repository owner's
prior instruction was to **prepare** a release candidate, not to publish an
exact SHA. A later `W55B-INT-MAIN-01` requires separate direct instruction
naming the gate-checked SHA, a fresh remote-main read and fast-forward proof,
clean same-SHA tree and the full `MAIN_AUTODEPLOY_POLICY.md` chain.

The owner confirmed on 2026-10-16 that alpha contained only generated test
data. The R-110 stand-copy waiver applies only while that remains true and
must be rechecked immediately before any main publication. R-46 requires an
owner ruling on readiness findings for deployment-host provider mode and run
cost ceiling. After an authorised push, the workflow, same-SHA host
verification, public TLS/application check and live W55b acceptance remain
required.

## Ownership

Tracked changes for this preparation task are exactly this report and
`tasks/W55B-INT-MAIN-PREP-03.md` in the separate programme worktree. The
candidate, ignored gate logs, credentials and disposable DB/S3 volumes are
outside Git. No shared contract, migration, dependency lock, composition
root, global style, product source, remote ref, tag or deployment input is
changed by this preparation task.
