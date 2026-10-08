# W52-INT-MAIN-SEAL-01 — pinned Stage-B publication preflight

The owner directly requested an isolated check of development commit
`3fc0dcfa1fbe59c2e00007fdbd7159e43c2d3551` and merge into main. Remote
`origin/dev` had already advanced to `fa3975a32473d69bec1eb9bdba27cef21a6c29e4`;
the named commit is the frozen source. Remote main was
`9d5b0105334f2f54d80d1f3ee0109b59fb6d8b7c`.

The conflict-free merge preserves main's W51 and gate repairs and introduces
the exact Stage-B SEAL and grant changes from `3fc0dcf`, plus this
publication task, report and narrow test-wiring corrections. Stage B adds API 30 paths / 37 operations /
83 schemas and migration head `0016_release_notes`. The domain candidate,
23 error codes and contract version remain fixed. `W52-SEAL-01` owns the
contract, migration, generated client and composition changes; this task
authors none of those hotspots. The first complete gate exposed a missing
premise declaration in this task and two composition guards still enumerating
the pre-SEAL GET surface and router ports. The release port passed through an
opaque test helper is now explicit and checked before the guard sees it. The first gate had no `GATE OK` and
was stopped when disk pressure developed; a fresh full gate is required on
the corrected commit.

The three new release routes are intentionally skeletal: authorized requests
return `dependency_unavailable` until Stage C installs release storage and
VERSION. They are a known limitation of this exact source, not evidence of a
complete product-version feature. A populated `0016` cannot downgrade in
place. D-137–D-139 acceptance remains open.

Publication requires the complete gate and production image builds on the
clean committed successor despite the requested brief isolated check, as
required by `MAIN_AUTODEPLOY_POLICY.md`. Workflow and host results will be
reported after publication without a post-gate commit.
