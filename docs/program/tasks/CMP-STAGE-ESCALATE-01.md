# Task CMP-STAGE-ESCALATE-01 — expert REVIEW card over current raw evidence

## Outcome
An expert's keyed command reveals service/masked/raw stage evidence as an immutable REVIEW card with source-side anchors and a reasoned audit trail, without changing the source evidence or model classification.

## Depends on
- CMP-STAGE-ESCALATE-SEAL-01
- CMP-STAGE-REVIEW-01
- CMP-STAGE-GRAPHIC-01

## Frozen inputs
- domain: roadmap R3-02 expert escalation and A-9/A-10 evidence-bound cards
- API: createStageReviewCard and CreateStageReviewCardRequest, root seal 80b6b9e3
- migration: 0042; existing card/evidence/audit/command tables only
- base commit: `924153cbfb686c33d8b1bf73cac23bdcaacee38a`
- root owns router/transport/generated wiring; full gates/heavy windows deferred to tomorrow by owner

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: root sealed the command but StageReviewService has no promote implementation.

### P-01 — base
- captured_at: 2026-10-30
- command: `git rev-parse HEAD`
- captured_output:
  ```text
  924153cbfb686c33d8b1bf73cac23bdcaacee38a
  ```
- interpretation: the completed root seal is inherited; this task authors only review runtime.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/comparison/stage_review/**`
- `tests/unit/comparison/stage_review/**`
- `tests/integration/comparison/stage_review/**`
- `docs/program/tasks/CMP-STAGE-ESCALATE-01.md`
- `docs/program/CMP-STAGE-ESCALATE-01.md`

## Lane resources
- foundation_instance: `auditmanager-cmp-seal-c4`
- postgres_port: `58040`
- s3_api_port: `62040`
- s3_console_port: `62041`
- postgres_db: `auditmanager_cmp_seal_c4`
- s3_bucket: `auditmanager-cmp-seal-c4`

Sequential root-assigned local foundation; tests are DB-only.

## Forbidden hotspots
- API/contracts/generated schemas, migrations, composition/public, root locks, AI/graphic/UI code, remote refs

## Non-goals
- no new model call or raw rewrite, no automatic verdict, no generic service/repository refactor

## Deliverables
- promote(run_id,source_ids,reason,*,user_uid,actor_roles,idempotency_key)->dict; immutable card/evidence/audit with scoped original sources
- focused keyed/current/foreign/masked source tests and local commit/report

## Required tests
- focused review PostgreSQL checks and pure review suite; whitespace clean
- expected: raw masked fragments reveal without losing original proof, service evidence escalates, replay exact, role/scope/stale checks enforced by business service

## Integration contract
Source IDs are std/sge or current pinned stf IDs of the pair's effective map. Source fragments are extended only for this command, never automatically as fallback cards. Card identity remains REVIEW + sorted source IDs; a pre-existing identical REVIEW card is reused under its canonical identity. Reason is an explicit expert comment (trimmed 1..2000) kept in audit payload with typed source/card/actor/command IDs, never copied document excerpts. Root wires frozen operation to this service.

## Failure/idempotency/security cases
- missing/wrong revision/version/project sources refuse atomically
- role/current-completed state enforced before creating a card; successful key replays its historical result
- source/evidence/verdict rows remain untouched; no new acceptance is inferred

## Rollback / feature flag
Root stages gate remains; created cards/audit are immutable historical rows. No DDL is owned.

## Handoff
- status: completed
- changed files/checks/limits: `docs/program/CMP-STAGE-ESCALATE-01.md`; 3 actual-0042 DB checks and 9 unit/export checks passed; source/card budgets retained
- contracts: none
- integration: local commit only
