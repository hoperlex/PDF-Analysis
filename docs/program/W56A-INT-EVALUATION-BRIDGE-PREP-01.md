# W56A-INT-EVALUATION-BRIDGE-PREP-01 — result

The additive offline bridge accepts one grounded merge-publication plan per
seeded bundle, with run ID and both source digests supplied by the caller.
It projects every member's page and quote to the existing matcher, preserves
rejected proposal failures and parse diagnostics, and optionally verifies the
published finding/member/canonical mapping against the plan. It refuses
unmapped, duplicate, partial or digest-mismatched bundle input. No bundle is
inferred from a path, display label or generated finding ID.

## Checks

- Bridge and matcher tests: **21 passed**. A removed `ic_area` finding lowers
  recall from `21/21` to `20/21`; a two-member group still matches from its
  second member. The matching report retains over-merge, per-category and
  control-pressure fields of the matcher.
- Python compilation, direct task governance, whitespace and exact owned-path
  proof: passed.
- Full gate and recorded/live evaluation: deferred under R-135; no baseline or
  beta quality verdict is claimed.

## Contracts and limits

No contract, migration, source manifest, matcher, runtime, publisher or
provider lock changed. The bridge cannot cryptographically establish the
source bytes merely from caller-supplied digest strings. The recorded harness
must hash actual PDF and portal bundle bytes and bind each run ID to its
source before calling it. A hand-built plan is not proof of PDF grounding or
the merge rule; the caller must use `plan_v2_merge_publication` after the
grounding pipeline. Published rows alone do not carry quotes, so the bridge
requires their original grounded plan.

Only the four additive task paths were edited by this lane. Other agents'
concurrent worktree changes are outside this task; no forbidden hotspot was
modified by this lane. The integrator can consume the bridge through a later
recorded harness or revert these paths before it is used.
