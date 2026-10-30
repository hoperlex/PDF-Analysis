# Task CMP-BATCH-AUDIT-01 — atomic audit trail for comparison batch acts

## Outcome
Exclude/retry/pause/resume/cancel writes exactly one identity-only audit_event with the actor and command in the same transaction as the keyed batch act; replay/refusal never duplicates or invents an act.

## Depends on
- CMP-INGEST-02
- CMP-SEAL-C2

## Frozen inputs
- domain: ADR-0025 batch expert acts; debt D-263
- API: 1.13.0, unchanged operations/DTOs
- events: v1 free-string event_type envelope; C2 seal D-263 proposal names
- migration head: 0042_comparison_stage_review
- base commit: `c626706164675b8daf6e71cf8f78c351a602bebf`
- root/owner 2026-10-30: exact batch service grant; functional code today and heavy gates tomorrow

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: src/auditmanager/ingest/comparison_batch/service.py
- enumerator_owner: CMP-BATCH-AUDIT-01
- totality_query: `rg -n 'comparison\.upload_' src/auditmanager/ingest/comparison_batch/service.py`

## Captured premise evidence
- premise: D-263 batch acts currently end with command success and no audit append.

### P-01 — base
- captured_at: 2026-10-30
- command: `git rev-parse HEAD`
- captured_output:
  ```text
  c626706164675b8daf6e71cf8f78c351a602bebf
  ```
- interpretation: root owns integration and register closure; this lane owns the exact batch writer only.

## Historical evidence
- correction_mode: addendum
- source_record: CMP-SEAL-C2 D-263 registry analysis
- addendum_path: docs/program/CMP-BATCH-AUDIT-01.md

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/ingest/comparison_batch/service.py`
- `tests/unit/ingest/comparison_batch/**`
- `tests/integration/ingest/comparison_batch/**`
- `docs/program/tasks/CMP-BATCH-AUDIT-01.md`
- `docs/program/CMP-BATCH-AUDIT-01.md`

## Lane resources
- foundation_instance: `auditmanager-cmp-seal-c4`
- postgres_port: `58040`
- s3_api_port: `62040`
- s3_console_port: `62041`
- postgres_db: `auditmanager_cmp_seal_c4`
- s3_bucket: `auditmanager-cmp-seal-c4`

Assigned stack remains sequentially owned; the existing ingest fixture creates/drops its own random throwaway database and per-test bucket within this local foundation.

## Forbidden hotspots
- contracts, migrations, composition/shared public/audit registry, root locks, graphic/AI/UI source, remote refs

## Non-goals
- no generic journal writer, no new event envelope/schema, no external publication or debt-register edit

## Deliverables
- closed batch event mapping, identity-only caller-transaction append, focused keyed replay/rollback tests, report/local commit

## Required tests
- focused actual-service batch audit checks, git diff --check
- expected: each of five acts has one event with correct aggregate/command/actor; failed audit rolls back state and command; replay adds none

## Integration contract
Use existing comparison.upload_set_excluded/upload_set_retried/upload_paused/upload_resumed/upload_cancelled names proposed by C2 seal. Root can close D-263 implementation after merge. Comparison audit.py is the legacy Comparison aggregate writer, not a generic cross-context registry; no deep import is added.

## Failure/idempotency/security cases
- role/refusal/replay never appends an act
- audit failure propagates and rolls back act/command in the same transaction
- payload admits only validated upload/set/project/user/command IDs, no label/file/text/model/raw key

## Rollback / feature flag
Existing batch behavior/module policy remains; append-only audit rows are historical. Reverting this writer does not delete prior events.

## Handoff
- status: completed
- changed files/checks/limits: `docs/program/CMP-BATCH-AUDIT-01.md`; six actual-service/DB cases passed; no broader upload/gate claim
- contracts: none
- integration: root sole integrator/ref writer
