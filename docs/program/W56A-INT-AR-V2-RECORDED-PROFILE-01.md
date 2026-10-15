# W56A-INT-AR-V2-RECORDED-PROFILE-01 — immutable recorded descriptor

**Result:** `resolve_recorded_profile` now binds the literal profile
`ap_01K7F4N2A9R8T6V5W3X2Y1Z0QH` to bundle
`pb_01K7F4N2A9R8T6V5W3X2Y1Z0QJ`. Both parse as the contract's opaque
identity types, differ from v1, and occur nowhere else in the source before
this task. Resolution verifies the six reviewed resource bytes, the response
schema, deterministic prompt material and the descriptor content hash. It
refuses mismatched identities or material. The returned value is frozen and
has recorded provider mode and the W56a five-stage tuple.

`STAGE_PLAN` is descriptor data only. It is not the executor's active stage
plan or a change to the stage registry, run row, composition root or provider
selection. `2.0.0-recorded` is an internal descriptor version, not a release
or contract version. The descriptor carries no live model identity, tariff,
generation parameters or provider call authority. A future runtime caller
must obtain the registration independently of the run row, prove recorded
mode and bind the exact request checksum before any stage can run.

## Pinned digests

| Input | SHA-256 |
| --- | --- |
| Six reviewed source resources | `0b560e485a07f96af511e3879740d1db0a0fc3f15fc013ab63507d609e3870ee` |
| Response schema | `031083983b7497852ebddad44207fa4adf59db8924a3ffc9fe705c85ac27906d` |
| Deterministic prompt material | `01bee01f8c7f1c59227ff6c17398f1034f5094c9c3b8e26fc66ab5130a4ca610` |
| Descriptor content | `73cc187ef0aecd5a84d0ec98588552247382158bfd0cbe0ec3b78de55ac56647` |

## Checks and limits

- Focused pytest: **9 passed**, including wrong IDs, altered resource bytes,
  altered material/schema fingerprints and immutable value checks. Pytest
  emitted only unrelated stale `/tmp` cleanup warnings.
- Both IDs parsed; both differ from v1. Repository search found these literals
  only in the new descriptor.
- Python compilation and direct task governance: passed (`[]`).
- `git diff --check`: passed. The task's four owned paths are the only files
  this lane changed; the integrator verifies the combined candidate.
- Full `make gate`, PostgreSQL acceptance, recorded replay and provider calls
  were deferred under R-135. No baseline or beta verdict follows.

## Integration

Changed paths are the new `registered.py`, its focused test, this report and
its task. No contract, migration head, provider lock, existing runtime module,
dependency, composition root, global style, recording, `VERSION`, Git ref or
tag changed. Integrate only on the exact `697279facee30216871389cc783e68b3bc58243b`
development base after checking the combined diff. Rollback is removal of
the additive descriptor before runtime wiring; a later material change
requires a new profile/bundle identity and recordings.
