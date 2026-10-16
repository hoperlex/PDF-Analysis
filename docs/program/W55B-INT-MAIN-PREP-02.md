# W55B-INT-MAIN-PREP-02 — repaired exact release candidate

## Candidate and scope

The isolated W55b candidate is the clean detached commit
`d3acd511c608dbff94d448b95ebb826cf5437c75`. It is a fast-forward
descendant of `origin/main=23fd729dbb06c642be0588017f6b195305e2e53e`,
which was read directly again on 2026-10-16. This candidate has only the
serving-carrier test deadline correction after `6d63802a`: its three changed
paths are the test, task and report of `W55B-INT-GATE-TIMEOUT-01`. Production
code is byte-identical to the W55b close candidate. The W56–W59 development
slices on `origin/dev` are outside this W55b release candidate.

`VERSION` is `0.6.0`; migration head is `0021_portal_bundles`. Direct JSON
read-back found 47 API paths, 54 operations, 123 schemas and 24 error codes.
The frozen W55 plan, main auto-deploy policy and W55b close report retained
the task-pinned SHA-256 digests. The candidate tree was clean at the gate
start and at the preparation read.

## Full gate result

The fourth complete `make gate` ran on this exact candidate after fresh
disposable gate volumes. Static/frontend (2,047 tests), contracts and
foundation (35 tests) passed. In the changed-context battery, the earlier
49% serving-carrier timeout position passed, but
`tests/integration/runs/test_durable_effect_boundaries.py::test_d142_a_crashed_publication_is_settled_and_the_report_is_clean_after_a_rerun`
failed with SQLAlchemy `MultipleResultsFound` in the test helper's
`_publication_state(...).one()` query. The run was interrupted after this
recorded failure to free the host: **4,168 passed, 1 failed, 3 skipped** in
4,215.96 seconds, with five warnings. Pytest exited 2; the shell command
exited 130 after Ctrl-C. The later canonical battery did not run, and the
literal `GATE OK` was absent. The ignored log is
`.local/worktrees/w55b-main-candidate/.local/gates/w55b-main-repaired-d3acd511.log`,
SHA-256 `0d509389c2db1968c3161b04edc533e39c35c8be3b44df5ef4c60d8f77d4b174`.
The three earlier failed attempts on `6d63802a` remain documented in
`W55B-INT-MAIN-PREP-01.md`; none is inherited as a pass. This candidate is
**not cleared for deployment**. A separate D-142 investigation and a new
complete gate on any repaired SHA are required. The R-125 infrastructure-void
exception is not asserted for this failure.

## Remaining deployment conditions

This task does not publish `origin/main` or deploy. The repository owner's
prior instruction was to **prepare** a release candidate, not to publish an
exact SHA. `W55B-INT-MAIN-01` requires a separate direct instruction naming
the gate-checked candidate, a fresh remote-main read and fast-forward proof,
clean same-SHA tree and the full `MAIN_AUTODEPLOY_POLICY.md` chain. A changed
candidate requires a new complete gate.

The owner confirmed on 2026-10-16 that alpha contained only generated test
data. The R-110 stand-copy waiver applies only while that fact remains true;
the integration owner must recheck it just before any main publication. The
deployment host's provider mode and run cost ceiling require an owner ruling
on the findings produced by `infra/deploy/readiness.sh`; under R-46 that script
reports findings and does not itself block a deployment. This local task has
not inspected or changed host settings. After any authorised main push, the
workflow, same-SHA host verification, public TLS/application check and live
W55b acceptance remain required.

## Ownership and handoff

Tracked changes for this task are exactly this report and
`tasks/W55B-INT-MAIN-PREP-02.md`. The isolated gate worktree, logs,
credentials and disposable DB/S3 volumes are ignored and remain outside Git.
No shared contract, migration, dependency lock, composition root, global
style, product source, remote ref, tag or deployment input is changed. A
green full-gate result would make this exact SHA a reviewable release
candidate; it would not by itself authorise `origin/main`.
