# Task W56A-INT-EVALUATION-RUN-SOURCE-01 — attest a seeded run's saved PDF source

task_id: W56A-INT-EVALUATION-RUN-SOURCE-01

## Outcome

An unserved, read-only evaluator attests one persisted recorded AR v2 Run to its
immutable Version's single source PDF manifest entry, reads that Blob within a
fixed bound, verifies its exact bytes and digest, and matches one explicit
seeded bundle ID to the committed evaluation manifest. A swapped PDF or
misbound Run refuses before an attestation is returned.

## Depends on

- `W56A-INT-GENERATOR-01` — completed synthetic bundle and manifest publication;
- `W56A-INT-EVALUATION-BRIDGE-PREP-01` — completed seeded scoring interface;
- `W56A-INT-EVALUATION-GLOBAL-IDENTITY-01` — completed cross-run identity check;
- `W56A-INT-RECORDED-BRIDGE-DB-ACCEPT-01` — completed persisted recorded Run acceptance.

## Frozen inputs

- base commit: `a09721a5895a0aff93d08f203fe1bedbbffffb8a`
- W56 plan SHA-256 `18a5a0c3615c513ac7e682f85ae29b16f70f901bf5a53581e90ba24ecd6e4694`;
- seeded manifest SHA-256 `95e07c2919d46a600cb9ffead41c883fd38d141699c6857a4700126d6dae6fb7`;
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

- premise: seeded scoring trusts caller-supplied source digest strings, while
  persisted Run, Version and bounded Blob read ports exist; no evaluator joins them.

### P-01 — read and scoring seams

- captured_at: 2026-10-16
- command: `rg -n '^def score_seeded_plans|^def validate_directory|^class RunRepository|^    def get\(|^    def get_version\(|^    def open_stream\(|^class DocumentVersionRecord|^class ManifestEntry' tools/evaluation/bridge.py tools/fixtures/seeded/validate.py src/auditmanager/runs/repository.py src/auditmanager/documents/repository.py src/auditmanager/storage/port.py src/auditmanager/documents/models.py && git ls-tree -r --name-only HEAD tools/evaluation/run_sources.py tests/integration/evaluation/test_run_sources.py docs/program/tasks/W56A-INT-EVALUATION-RUN-SOURCE-01.md docs/program/W56A-INT-EVALUATION-RUN-SOURCE-01.md`
- captured_output:
  ```text
  src/auditmanager/documents/models.py:170:class ManifestEntry:
  src/auditmanager/documents/models.py:186:class DocumentVersionRecord:
  src/auditmanager/storage/port.py:124:    def open_stream(
  tools/fixtures/seeded/validate.py:138:def validate_directory(root: Path) -> dict:
  src/auditmanager/documents/repository.py:434:    def get_version(
  tools/evaluation/bridge.py:204:def score_seeded_plans(
  src/auditmanager/runs/repository.py:331:class RunRepository:
  src/auditmanager/runs/repository.py:398:    def get(self, session: Session, run_id: str) -> RunRow:
  ```
- interpretation: the four owned paths are new. The existing scoring bridge
  compares supplied digests; this task adds a separate saved-source proof.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `tools/evaluation/run_sources.py`
- `tests/integration/evaluation/test_run_sources.py`
- `docs/program/tasks/W56A-INT-EVALUATION-RUN-SOURCE-01.md`
- `docs/program/W56A-INT-EVALUATION-RUN-SOURCE-01.md`

## Forbidden hotspots

Existing seeded fixtures and manifest, recordings, `baseline.json`, matcher,
scoring bridge, runtime Run/Document/Blob implementations, `contracts/**`,
migrations, provider lock, root dependencies/locks, composition root, global
styles, `CURRENT_STATE.md`, Git refs and tags.

## Non-goals

No provider call, recorded response, measured quality baseline, portal ZIP
custody from a saved Version, finding decision, service activation, DB/S3
write, contract/migration change, full beta gate or deployment.

## Deliverables

Typed PDF source attestation, bounded source reader, focused refusal and
success tests, and this task plus result report.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/evaluation/test_run_sources.py tests/contract/evaluation/test_bridge.py` — pass;
- `../../../.venv/bin/python -m py_compile tools/evaluation/run_sources.py tests/integration/evaluation/test_run_sources.py` — pass;
- direct task governance, frozen hashes, `git diff --check` and exact
  owned-path proof — pass;
- full `make gate` deferred by R-135.

## Integration contract

`attest_seeded_run_pdf` takes a caller-owned read transaction, explicit run
and seeded bundle IDs, the pinned manifest, injected Run and Version read
ports, and the BlobStore port. It calls the Run reader, checks published
recorded AR v2 identity, calls the Version reader by the Run's saved
`version_uid`, checks the project/version binding and exactly one source PDF
manifest entry, then streams and hashes its Blob under a strict byte limit.
Only the resulting digest matching the explicitly named bundle can yield an
attestation DTO. It does not infer identity from a path or filename.

The original portal ZIP is not saved in the Version manifest. The future
recorded harness must separately call the existing seeded fixture validator
for its local ZIP bytes and join an actual grounded plan/publication before
calling `score_seeded_plans`; this DTO alone proves no evaluation result.

## Failure/idempotency/security cases

Missing, duplicate or non-PDF source entry; missing/mismatched Run or Version;
wrong profile, state or bundle; oversized, short, long or corrupt Blob; and
unknown/swapped bundle digest all refuse. A failed read writes nothing.
Repeated reads of the same immutable source return the same attestation.
Underlying storage failures propagate; no local filesystem fallback.

## Rollback / feature flag

Revert the four additive paths before harness wiring. No persistent state or
served behavior changes; no feature flag or data rollback is needed.

## Handoff

- changed files/checks/limits: result report;
- contracts: none;
- next: integrate on the exact checked development predecessor; retain the
  separate local ZIP, recorded response and measured-baseline requirements.
