# Task W56A-INT-EVALUATION-LOCAL-BUNDLE-BIND-01 — bind saved PDF source to verified local seeded bundle

task_id: W56A-INT-EVALUATION-LOCAL-BUNDLE-BIND-01

## Outcome

An unserved read-only evaluator verifies the exact committed AR v2 seeded
manifest and every local PDF/portal ZIP byte pair through the existing seeded
validator, calls the saved Run-to-PDF-Blob attestor for one explicit Run and
bundle ID, and returns a typed binding only when the saved PDF matches that
locally verified bundle. A changed ZIP or PDF refuses before a binding exists.

## Depends on

- `W56A-INT-GENERATOR-01` — completed synthetic corpus publication;
- `W56A-INT-EVALUATION-BRIDGE-PREP-01` — completed offline scorer interface;
- `W56A-INT-EVALUATION-RUN-SOURCE-01` — completed saved Run/PDF attestor on dev65.

## Frozen inputs

- base commit: `8c39b9e0dfd63da7d32d1a848e609ae2dd437a01`
- W56 plan SHA-256 `18a5a0c3615c513ac7e682f85ae29b16f70f901bf5a53581e90ba24ecd6e4694`;
- seeded manifest raw SHA-256 `95e07c2919d46a600cb9ffead41c883fd38d141699c6857a4700126d6dae6fb7`;
- API SHA-256 `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- analysis stage registry SHA-256 `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`;
- migration head `0023_norm_citations`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the saved-source attestor checks a caller-supplied seeded manifest
  PDF digest; the local generator validator independently checks full PDF and
  portal ZIP bytes, but no evaluation adapter joins these two proofs.

### P-01 — separate read-only seams and additive paths

- captured_at: 2026-10-16
- command: `rg -n '^def (attest_seeded_run_pdf|validate_bytes|validate_directory|score_seeded_plans)|^class SeededPdfSourceAttestation' tools/evaluation/run_sources.py tools/fixtures/seeded/validate.py tools/evaluation/bridge.py && git ls-tree -r --name-only HEAD tools/evaluation/local_bundle.py tests/integration/evaluation/test_local_bundle.py docs/program/tasks/W56A-INT-EVALUATION-LOCAL-BUNDLE-BIND-01.md docs/program/W56A-INT-EVALUATION-LOCAL-BUNDLE-BIND-01.md`
- captured_output:
  ```text
  tools/evaluation/bridge.py:204:def score_seeded_plans(
  tools/fixtures/seeded/validate.py:37:def validate_bytes(manifest: dict, files: dict[str, bytes], *, require_full: bool) -> None:
  tools/fixtures/seeded/validate.py:138:def validate_directory(root: Path) -> dict:
  tools/evaluation/run_sources.py:60:class SeededPdfSourceAttestation:
  tools/evaluation/run_sources.py:98:def attest_seeded_run_pdf(
  ```
- interpretation: the four owned paths are absent, and the saved-source and
  fixture validators have no shared caller. This task only adds that caller.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `tools/evaluation/local_bundle.py`
- `tests/integration/evaluation/test_local_bundle.py`
- `docs/program/tasks/W56A-INT-EVALUATION-LOCAL-BUNDLE-BIND-01.md`
- `docs/program/W56A-INT-EVALUATION-LOCAL-BUNDLE-BIND-01.md`

## Forbidden hotspots

Existing fixture bytes, source manifest, validator, saved-source attestor,
scorer/matcher, recordings, `baseline.json`, runtime, `contracts/**`, migration
head, provider lock, root dependencies/locks, composition root, global styles,
`CURRENT_STATE.md`, Git refs and tags.

## Non-goals

No actual grounded plan, recorded provider response, measured baseline,
quality claim, original ZIP custody from a saved Version, service activation,
database or Blob write, contract or migration change, full gate or deployment.

## Deliverables

One offline binding adapter, focused success and mutation tests, task and
result report.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/evaluation/test_local_bundle.py tests/integration/evaluation/test_run_sources.py` — pass;
- `../../../.venv/bin/python tools/fixtures/seeded/generate.py --check` — pass;
- Python compilation, direct task governance, frozen hashes,
  `git diff --check` and exact owned-path proof — pass;
- full `make gate` deferred by R-135.

## Integration contract

`bind_seeded_local_bundle` takes one explicit Run ID, bundle ID and fixture
directory plus the same caller-owned transaction/read ports as the existing
attestor. It requires the fixture manifest's raw bytes to match the frozen
SHA-256, reads only the ten declared PDF/ZIP paths with fixed per-file byte
limits, and passes those bytes to `validate_bytes(require_full=True)`. It then
calls `attest_seeded_run_pdf` with that validated manifest and checks the
returned PDF digest and length against the exact local PDF bytes. Its typed
return names the Run, bundle, saved PDF attestation and locally checked ZIP
digest; the ZIP digest is explicitly local fixture evidence, not persisted
Version custody. Paths are used only to open the frozen fixtures, never as
Run or bundle identity.

## Failure/idempotency/security cases

A different or malformed manifest; missing, oversized, symlinked, changed or
swapped PDF/ZIP; validator failure; saved-source mismatch; and unknown bundle
all refuse. Bounded reads prevent a malformed local file from allocating an
unbounded buffer. No fallback or write occurs. Repeated immutable inputs
return an equal binding.

## Rollback / feature flag

Revert the four additive paths. No persistent or served behavior changes, so
no data rollback or feature flag is needed.

## Handoff

- changed files/checks/limits: result report;
- contracts: none;
- next: integrate on the exact dev65 predecessor; the future recorded harness
  must independently provide actual grounded plans and recordings.
