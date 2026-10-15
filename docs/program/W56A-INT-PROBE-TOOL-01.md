# W56A-INT-PROBE-TOOL-01 — development integration

**Source accepted:** `f21157544b4b0c24a31366e04980e14c90795dec`
on predecessor `6de331c150f6573e320093bb4b2751f3bda016a2`.
This integration publishes a verifier, not a model identity result.

## Checks and scope

- The source commit changes exactly five paths: the preparation task/report,
  `tools/provider/{__init__,identity_probe}.py` and
  `tests/contract/provider/test_identity_probe.py`.
- Focused provider and contract-prose tests on the integration tree:
  **91 passed**. Python compilation and CLI help passed in the source lane.
- The new preparation and integration task files each satisfy the direct
  executable governance check. The broader governance assertion remains
  red on six earlier W56a task files, independent of this source.
- `git diff --check` passed. Only this integration task/report and the top
  `CURRENT_STATE.md` entry are added after the source commit.
- No full local gate, manual acceptance, paid gateway call or deployment was
  run under R-135.

## Contracts and publication boundary

API, error catalog, analysis registry, migration head `0022_findings_v2`,
`P02_LOCK.json`, root dependencies, composition root, global styles,
`VERSION`, credentials and stand state are unchanged. The probe tool makes
no call unless an operator invokes it with a host-owned environment file.
The old stand result remains FAIL; no recording gateway result exists.

Normal fast-forward publication is only to `origin/dev`. Before push the
remote predecessor must still equal `6de331c1`; after push the integrator
reads the remote ref back and checks it equals this integration tree.
`origin/main` and tags are outside this grant.

## Next integrator action

Refresh `W56A-MODEL-PIN-01` on the read-back dev SHA. A sanctioned
authenticated route to each distinct gateway and a fresh spend projection
are required before the four bounded calls. The attempted reuse of a
password from a prior session log was rejected by automatic approval
review as credential probing from an unintended source; it is not an
available access method. No lock pin, PROVIDER grant or recording follows
until both gateway pairs pass.
