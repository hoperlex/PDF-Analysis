# W59-INT-SUMMARY-INPUT-PREP-01 — bounded version-summary input

Base: `origin/dev` at `445efc5db8556ef5a5e13fa680f9f49eb9783954`.
The new pure module rechecks an ordered version pair, all approved raw page
differences and their whole-comparison seal before projecting changed lines.
Every linked sheet remains in the output with its raw evidence SHA-256, even
if its two pages have no changes. The projection has its own deterministic
digest and refuses a 100,000-character, 1,000-line or 256-hunk changed-input
overrun in full; it does not truncate or omit sheets to fit.

## Checks

- Focused comparison suite: **28 passed** (`test_summary_input.py`,
  `test_raw_evidence_seal.py`, `test_raw_text.py`).
- Program task governance: **16 passed**.
- Python compilation: passed for both new Python files.
- Frozen domain/API/error/stage/scope/roadmap SHA-256 values: exact match to
  task file; migration head remains `0022_findings_v2`.
- `git diff --check`: passed. Exact changed paths are this report, its task,
  `src/auditmanager/comparison/summary_input.py` and
  `tests/integration/comparison/test_summary_input.py`.
- No Docker, database, provider call or complete `make gate` was run under
  R-135 while the shared W55 gate runs.

## Contracts and integration

No frozen contract, migration, registry or existing module changed. The W59
comparison owner can call `prepare_version_summary_input` only after reading
authoritative approved links and immutable version facts under a consistent
transaction and storing the raw evidence separately. A future AI summary
needs a separately identified and versioned derived artifact referencing
`raw_seal_sha256`; this input grants no approval and has no persistence or
runtime wiring. Any provider profile, output schema, authorization and
publication remain future owned work after SECTION-SEAL.

Rollback: remove the additive module and test before runtime integration;
there is no data migration or feature flag. Known limit: the input contains
changed lines without surrounding equal-line context, and its raw seal proves
the supplied canonical evidence rather than authoritative approval or PDF
custody.
