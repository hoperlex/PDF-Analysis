# W55B-INT-MAIN-PREP-01 — exact W55b release candidate

## Candidate

The isolated clean worktree `.local/worktrees/w55b-main-candidate` is detached
at `6d63802ab465a0317839c9b57abd5e90f3d91769`, the W55b development
close. It is a fast-forward descendant of `origin/main`
`23fd729dbb06c642be0588017f6b195305e2e53e` by 185 commits and changes
377 paths. The old main release is `VERSION=0.5.0`, migration head
`0020_norms_search`; this candidate is `VERSION=0.6.0`, head
`0021_portal_bundles`, with the W55b revision-2 release notes. The newer
W56–W59 preparations published to `origin/dev` at `8f113f6b` are a separate
development candidate and are not included in this main candidate.

## Checks and evidence

- Remote refs were read directly: `origin/main=23fd729d` and the initial
  `origin/dev=80692209`; later separate dev publications reached
  `origin/dev=445efc5d` while main remained `23fd729d`.
- The release worktree is clean and passes `git merge-base --is-ancestor`
  for the current main predecessor. Locked `npm ci` installed 184 packages;
  `make bootstrap` reproduced Python 3.12.3 and both locked environments.
- `make gate-preflight` passed on the exact clean SHA with 14,954 MiB free
  on both worktree and Docker-data filesystems, above its 6,144 MiB floor.
- Direct JSON read-back on the candidate found 47 API paths, 54 operations,
  123 schemas and 24 error codes. `VERSION` is `0.6.0`, the migration file is
  `20261013_0021_portal_bundles.py`, and release notes revision is 2.
- The complete `make gate` started on that SHA at 2026-10-16 06:12:49 UTC.
  Static frontend (2,047 tests), contract and foundation checks passed. In
  the changed-context battery, three tests in
  `tests/integration/composition/test_the_run_leaves_the_request_thread.py`
  failed because their worker-adapter entry events did not arrive within
  30/60 seconds. The run was interrupted after those failures at 92% to free
  the heavily loaded host: **4,040 passed, 3 failed, 3 skipped** in 1:04:38.
  The command exited 2; the Makefile reported exit 1 and did not run the
  remaining battery. It printed no `GATE OK`. The ignored log is
  `.local/worktrees/w55b-main-candidate/.local/gates/w55b-main-6d63802a.log`,
  SHA-256 `c858186904ba0101abcab105a9ad9b6793690dae9f97494708b1298a18a05fce`.
  The three gate containers were stopped without deleting their volumes.
  This candidate is **not cleared for deployment**. The timeout cause needs
  a targeted quiet-host rerun, followed by a new complete gate on this exact
  clean SHA. These failures are not asserted to meet the narrow R-125
  infrastructure-void exception.

## Remaining deployment conditions

`W55B-INT-MAIN-01` still needs a direct owner instruction naming the exact
candidate SHA. It must reread `origin/main`, prove a clean fast-forward and
repeat the complete gate if the candidate changes. The deployment host's
provider mode and run cost ceiling must pass `infra/deploy/readiness.sh` before
the publication; this local preparation cannot assert that host setting.
On 2026-10-16 the owner
confirmed that alpha contains only generated test data. The existing `R-110`
waiver therefore permits this candidate's migration without a stand copy,
provided that remains true immediately before publication. If real/client
data arrives first, W55's copy and restore-test sequence becomes required.
After an authorised push, the workflow, same-SHA deployment verification,
public TLS/application checks and live W55b acceptance remain. This
preparation performs none of those external actions, creates no release tag
and does not claim a beta.

## Contracts, ownership and integration

No shared contract, migration, root lock, composition, global style,
application/test source or deployment input is edited by this task. The
tracked changes are this report and
`tasks/W55B-INT-MAIN-PREP-01.md`; isolated ignored environments and gate
evidence stay outside Git. A separate development integration may publish
this **interim failed-gate record** for visibility, provided it preserves the
incomplete status. This is not completion of the preparation task and grants
no `origin/main` authority.
