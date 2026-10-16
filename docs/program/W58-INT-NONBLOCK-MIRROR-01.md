# W58-INT-NONBLOCK-MIRROR-01 — bounded refusal for FIFO object paths

**Base:** published `origin/dev=a09721a5895a0aff93d08f203fe1bedbbffffb8a`
(dev64). **Status:** unactivated W58 recovery-code correction; no live drill or
W58/B6 acceptance.

## Result

The offline object sealer and source-mirror retry now open candidate object
files with `O_NONBLOCK` before their existing regular-file, ownership, size
and digest checks. A FIFO at a listed object key or an existing retry key
therefore reaches a typed refusal immediately instead of waiting for another
process to open the pipe. The no-follow checks and regular-file byte/manifest
semantics are unchanged.

## Evidence

- On the frozen dev64 base, the two new subprocess regressions each failed by
  their three-second timeout. Earlier one-second child probes independently
  found both paths still blocked on private FIFOs.
- After the two flag changes, the whole recovery suite passed:
  **167 passed** in 0.85 s. This includes regular-file seal, source stream and
  safe retry tests, plus both FIFO refusal regressions.
- Programme governance: **16 passed**. Python compile and `git diff --check`
  passed. Pytest emitted unrelated cleanup warnings for older restricted
  `/tmp/pytest-of-root/garbage-*` directories; neither suite had a test failure.
- No Docker, PostgreSQL, S3, corpus file, paid provider, full beta gate or
  remote Git ref was used. R-135 reserves the complete gate for the final beta
  code candidate.

## Changed paths and limits

Exactly the six paths owned by the formal task changed:

- `scripts/recovery/object_copy.py`
- `scripts/recovery/source_object_mirror.py`
- `tests/integration/recovery/test_object_copy.py`
- `tests/integration/recovery/test_source_object_mirror.py`
- `docs/program/tasks/W58-INT-NONBLOCK-MIRROR-01.md`
- `docs/program/W58-INT-NONBLOCK-MIRROR-01.md`

No API/domain/stage/storage contract, migration head, root dependency or lock
file, composition root, global style, deployment script or served route
changed. The W58 seal still omits source S3 role, media type and custom
metadata. Byte readback of the synthetic local payload does not establish
faithful source-bucket recovery or restored write behavior. Those require a
separate metadata/seal decision and real isolated source-to-target evidence.

The integrator can cherry-pick this task commit into an assigned `origin/dev`
integration slot and rerun the focused recovery/governance suites. Reverting
these six paths removes the correction; there is no feature flag.
