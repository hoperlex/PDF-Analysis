# W56A-INT-EVALUATION-RUN-SOURCE-01 — result

**Base:** published development candidate `a09721a5895a0aff93d08f203fe1bedbbffffb8a`.
**Status:** source task complete on an isolated local branch; no remote ref moved.

## Result

`attest_seeded_run_pdf` is a read-only offline evaluator boundary. It resolves
one persisted, published recorded AR v2 Run through caller-supplied Run and
Version readers in the caller's transaction; requires that the Run and Version
identities, project, registered profile and bundle agree; requires exactly one
immutable source PDF manifest entry; and compares that entry with the explicit
bundle ID in the seeded manifest. It streams at most 2 MiB from the saved Blob,
checks derived Blob identity, exact byte count and independently calculated
SHA-256, then returns a typed PDF source attestation. A mismatch refuses before
an attestation exists. No stage, provider or DB/S3 write is performed.

## Changed files

- `tools/evaluation/run_sources.py` — bounded read-only source attestation;
- `tests/integration/evaluation/test_run_sources.py` — success and failure checks;
- `docs/program/tasks/W56A-INT-EVALUATION-RUN-SOURCE-01.md` — exact task grant;
- this report.

## Checks

- focused source and existing bridge suites: **27 passed**;
- `tools/fixtures/seeded/generate.py --check`: **10 bundles, 21 issues, 7 controls OK**;
- Python compilation, direct task governance, frozen input hashes,
  `git diff --check` and exact owned-path proof: passed;
- full `make gate`: deferred under R-135 for the final beta code candidate.

## Contracts and limits

No API, stage contract, migration, provider lock, fixture, recording, scorer,
runtime implementation or composition root changed. The original portal ZIP
is not persisted in the Version manifest. Its committed fixture bytes are
checked separately by the existing corpus validator; this attestation proves
only the saved PDF source. The adapter accepts a caller-injected Run reader
because `runs.public` does not currently export a read repository. It has no
real DB/S3 acceptance in this task; the focused tests use fake read ports with
real committed PDF bytes. Neither a recorded response nor a measured quality
baseline exists, so this task makes no recall or beta claim.

## Integrator instruction

Cherry-pick the source commit onto the exact development predecessor after
checking its four-path allowlist. A future recorded evaluation harness must
use the saved Run/Version attestation, separately validate local PDF/ZIP fixture
bytes, build plans from the actual grounding and merge pipeline, and then call
the existing scorer. The fixed 2 MiB source ceiling requires a new reviewed
task if the seeded PDF fixtures grow beyond it.
