# Task W57A-INT-REPORT-READ-PREP-01 — unserved v3 report read

task_id: W57A-INT-REPORT-READ-PREP-01

## Outcome

One read-only call combines certified W57a citation partitions with the same Run's persisted diagnostic reasons, textless-page context and partial-stage error. It refuses missing or inconsistent evidence and remains unserved.

## Depends on

- `W57A-SEAL-01A` — complete at `c71048f788e5d0bee39a312217dfd4c0912e5bc1`.
- `W57A-SEAL-01B` — complete at `c08182cab78bed70afbc777019d43de6c0bd2e18`.
- `W57A-INT-CITE-READ-PREP-01` — complete in `CFB-INT-DEV-PUBLISH-34`.
- `W57A-INT-SET-CUSTODY-READ-PREP-01` — complete in `CFB-INT-DEV-PUBLISH-36`.

## Frozen inputs

- base commit: `f0580e089867ba6a9380a48dfca19a23e47f6788`
- API: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- stage: `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- domain: `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`;
- errors: `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- migration head `0023_norm_citations`: `fd1da93e07d812819e05381b9956e6a288f1cc71f32132f44c78f7b94c5eaa7e`;
- `docs/program/dispatch/W57-PLAN.md` A3.5–A3.6 and `R-135`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the exact dev37 base has a certified citation reader but no
  report reader, and its served verification route still refuses.

### P-01 — reader exists, served route refuses

- captured_at: 2026-10-16
- command: `git rev-parse HEAD; rg -n 'def read_verified_citations|def get_norm_verification|norm_verification_reader' src/auditmanager/findings/citation_reader.py src/auditmanager/bootstrap/adapters.py; git ls-tree -r --name-only HEAD src/auditmanager/findings/citation_report.py`
- captured_output:
  ```text
  f0580e089867ba6a9380a48dfca19a23e47f6788
  src/auditmanager/bootstrap/adapters.py:769:    def get_norm_verification(self, *, run_id: str) -> models.NormVerificationReport:
  src/auditmanager/bootstrap/adapters.py:777:            dependency="norm_verification_reader",
  src/auditmanager/findings/citation_reader.py:196:def read_verified_citations(
  ```
- interpretation: the exact base has a certified citation reader and a refusing route; no report reader exists. Line numbers are the captured premise, not a runtime proof.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/findings/citation_report.py`
- `tests/integration/findings/test_w57a_citation_report_offline.py`
- `docs/program/tasks/W57A-INT-REPORT-READ-PREP-01.md`
- `docs/program/W57A-INT-REPORT-READ-PREP-01.md`

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, root dependency/lock files;
- `src/auditmanager/bootstrap/**`, API routes/schemas, composition root;
- existing citation reader/writer and shared findings readers, `CURRENT_STATE.md`;
- remote refs, tags, PostgreSQL/S3, UI and global styles.

## Non-goals

No served report, role authorization, profile v3 registration, provider call, qualified set, real PostgreSQL acceptance or beta claim. No change to existing v1/v2 behavior.

## Deliverables

Additive SELECT-only report adapter, focused offline tests and result report.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/integration/findings/test_w57a_citation_report_offline.py tests/integration/findings/test_w57a_citation_reader_offline.py`;
- `python3 -m py_compile src/auditmanager/findings/citation_report.py tests/integration/findings/test_w57a_citation_report_offline.py`;
- `git diff --check`, frozen SHA-256 checks and task handoff guard.

## Integration contract

Caller supplies authorized Run, exact Version, registered v3 profile and one repeatable-read transaction. The adapter first invokes `read_verified_citations`; then it reads matching Run/version context, ungrounded observations and stage rows from the same session. It returns immutable report facts for later API projection. Missing portal page metadata, foreign provenance, invalid diagnostics, partial-stage ambiguity or inconsistent terminal status refuse. It never treats an empty citation query as a zero certificate.

## Failure/idempotency/security cases

Every fault raises `CitationReportRefused` or `CitationReadRefused` without writes. Textless pages remain context only. No route may call the adapter until an integration task owns authorization, API projection and real DB readback.

## Rollback / feature flag

Unserved additive code. Revert its bounded commit before activation; no data rollback or feature flag.

## Handoff

- changed files: four exact allowed paths;
- commands/results: accompanying result report;
- known limits: offline test doubles and no real DB acceptance;
- integration notes: cherry-pick after dev37, then run a real isolated read transaction before wiring `get_norm_verification`.
