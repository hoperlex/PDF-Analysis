# W56A-INT-EVALUATION-LOCAL-BUNDLE-BIND-01 — result

**Base:** published development candidate `8c39b9e0dfd63da7d32d1a848e609ae2dd437a01`.
**Status:** isolated local source branch; no remote ref moved.

## Result

`bind_seeded_local_bundle` reads the exact pinned AR v2 fixture manifest and
its ten declared PDF/portal ZIP pairs within fixed byte limits, then runs the
existing full seeded validator on the bytes held in memory. Only after the
local corpus is valid does it invoke `attest_seeded_run_pdf` in the caller's
read transaction. The returned typed binding joins one explicit Run and
bundle ID to a saved PDF source attestation, the frozen manifest digest, and
the selected ZIP's **local fixture** digest and byte size. Paths open frozen
fixture files; they never identify a Run or bundle.

## Changed files

- `tools/evaluation/local_bundle.py` — offline binding adapter;
- `tests/integration/evaluation/test_local_bundle.py` — real fixture and mutation checks;
- `docs/program/tasks/W56A-INT-EVALUATION-LOCAL-BUNDLE-BIND-01.md` — exact grant;
- this result report.

## Checks

- local binding and saved-source suites: **27 passed**;
- seeded generator `--check`: **10 bundles, 21 issues, 7 controls OK**;
- architecture boundaries and program governance: passed;
- Python compilation, direct task governance, frozen hashes, whitespace and
  exact owned-path proof: passed;
- full `make gate`: deferred by R-135 to the final beta code candidate.

## Contracts and limits

No API/stage contract, migration, fixture, recording, validator, scorer,
runtime implementation, provider lock or composition root changed. The
original portal ZIP is not persisted in a Version: the ZIP digest here proves
only the locally read fixture bytes. The adapter does not inspect an actual
grounded plan or recorded provider response and cannot produce a measured
recall, quality baseline or beta result. Focused tests use real committed
fixture bytes and fake read ports; this slice has no real DB/S3 acceptance.
The manifest is pinned to its exact current raw SHA-256. Fixture changes or
larger PDFs/ZIPs require a new reviewed task.

## Integrator instruction

Cherry-pick the source commit onto the exact checked dev65 predecessor after
the four-path allowlist proof. A later recorded evaluation harness must use
the returned binding with actual saved plans and recordings; it must not
represent the local ZIP digest as a persisted Version custody claim.
