# CFB-INT-DEV-PUBLISH-17 — recorded gate and state compaction

The integration starts from exact `origin/dev=da6dff620140d1c74b5cead1f4c4c7e222d822d7`.
It applies completed source payloads without content edits:

- `4abc555e` → `ca9bec73`, `30000ad6` → `4d8788e9`, `ca372748` →
  `71373417`: W56a's unactivated recorded-publication transaction gate. It
  checks saved text/merge, completed call, stage and source facts; then writes
  findings and terminal Run/Job/Attempt in one caller-owned transaction. Its
  isolated PostgreSQL/MinIO suite passed 15 tests at head `0022_findings_v2`.
- `d3acd511` → `28bec0c1`: the W55b serving-carrier test now allows 120
  seconds to reach its gated provider and reports public Run status on timeout.
  The failed gate database showed 18.761 seconds of source preparation and
  19.160 seconds of geometry before provider entry; the worker claimed its Job
  in about one second and the Run later published. No production code changed.
- The earlier `9bb03d4c` records three unsuccessful complete-gate attempts on
  W55b SHA `6d63802a`. Its separate repaired candidate `d3acd511` owns a new
  full gate; no W55b result is borrowed from the development checks.

## Checks and live-state repair

The integrated focused saved-plan, gate-fake and program governance suite
passed **44 tests**. The changed W55b test collected as one test. W56a's source
lane already passed 15 real-service tests and 36 focused container-free checks;
the W55b repair lane passed 60 documentation/governance checks. Contract
SHA-256 values remain `fad81bc0` (API), `c017864a` (domain) and `bd1e5b91`
(stage registry), identical to dev 16; migration head stays `0022_findings_v2`.

The former 320-line live `CURRENT_STATE.md` is archived byte-for-byte at
`history/CURRENT_STATE_2026-10-16_71373417.md` from tree `71373417`; the
new live entry is 78 lines. `CurrentStateTest` and the program governance suite
now pass. The original 2026-10-15 release-state archive remains unchanged.

## Publication boundary

The integration commit changes only this report, its task, the live state and
the new historical copy. The W56a and W55b source commits keep their own exact
path grants. No contract, migration, root dependency/lock, composition root,
global style, active executor or provider secret is changed by this
integration commit. The complete beta gate remains deferred under R-135.

Before updating `origin/dev`, reread the remote, require a clean tree and
fast-forward from `da6dff62`; after push, read back the exact remote SHA into
ignored local evidence and the final integration result. This task has no
`origin/main` authority. W54 still lacks a proxy credential for the
`claude-opus-5` repair, so no qualified corpus or DB/S3 publication is claimed.
