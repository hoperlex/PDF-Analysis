# Task CMP-WAVE-C2-INT — accept and publish the C2 development candidate

## Outcome
The merged C2 comparison modules pass one complete `make gate` on an exact clean commit; the same commit is fast-forward published to `origin/dev`, and the wave report and current-state header identify that commit and its measured limits. No `origin/main` publication occurs.

## Depends on
- CMP-SEAL-C2
- CMP-AI-JOBS-01
- CMP-VC-SPEC-01
- CMP-VC-AIPAIR-01
- CMP-VC-AISHEET-01
- CMP-VC-REPORT-01
- CMP-VC-QUEUE-01
- CMP-VC-UI-02
- CMP-C2-FIX-01
- CMP-C2-GOV-01

## Frozen inputs
- domain contract: ADR-0025 and the C2 seal
- API contract: `1.11.0`, 176 paths / 198 operations / 517 schemas
- analysis/comparison/event contract: unchanged from `CMP-SEAL-C2`
- migration head: `0040_comparison_ai_reports`
- base commit: `efeefe1f7452cad85adca3d2fd4d93e101a8178d`
- development remote at premise: `0277e4ef507950e2e6bafe6aa5c77928acd94013`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: `make gate-static`

## Captured premise evidence
- premise: P-01, P-02

### P-01 — sealed candidate and clean base
- captured_at: 2026-10-29
- command: `git rev-parse HEAD; git status --short; python3 -c 'import json;d=json.load(open("contracts/api/v1/openapi.json"));print(d["info"]["version"],len(d["paths"]),sum(k in {"get","post","put","patch","delete","head","options","trace"} for p in d["paths"].values() for k in p),len(d["components"]["schemas"]))'`
- captured_output:
  ```text
  efeefe1f7452cad85adca3d2fd4d93e101a8178d
  1.11.0 176 198 517
  ```
- interpretation: the C2 fix is recorded; the frozen API has not moved.

### P-02 — remote refs before integration
- captured_at: 2026-10-29
- command: `git ls-remote origin refs/heads/dev refs/heads/main`
- captured_output:
  ```text
  0277e4ef507950e2e6bafe6aa5c77928acd94013 refs/heads/dev
  2651cc7a5c00267faf9de2cf291f2419974f8a24 refs/heads/main
  ```
- interpretation: only `origin/dev` is this task's publication target; both refs must be checked again immediately before any push.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `docs/program/tasks/CMP-WAVE-C2-INT.md`
- `docs/program/CMP-WAVE-C2-REPORT.md`
- `docs/program/CURRENT_STATE.md`
- `web/node_modules/**`
- `.local/norms/**`

## Forbidden hotspots
- `contracts/**`, `db/migrations/**`, root dependency and lock files, composition root, global styles, `infra/**`
- all application source, tests and `Makefile` unless a failing gate establishes a separate, explicit integration repair task
- `origin/main`

## Non-goals
- no C3 or C4 seal, no new API operation, no migration
- no live model spend, production deploy, or browser journey claim
- no force push and no automatic merge into `origin/main`

## Deliverables
- locally installed web dependencies from this tree's lockfile and the local norms-corpus link required by gate preflight; complete `make gate` with literal `GATE OK` on an exact clean SHA
- `docs/program/CMP-WAVE-C2-REPORT.md` and the current-state header with evidence, known limits and forbidden-hotspot proof
- fast-forward push of that exact checked SHA to `origin/dev`, with remote-ref verification; leave integration branch at that SHA

## Required tests
- `npm --prefix web ci` with the checked-in lockfile (toolchain setup only)
- `make gate` with a copied log under `/tmp`; expected literal `GATE OK`
- `git diff --check` and `git status --short` empty on the candidate
- `git merge-base --is-ancestor <remote-dev> <candidate>` and `git ls-remote` before and after the fast-forward push

## Integration contract
The C2 candidate contains all four AI method lanes, the launch queue and UI on the `1.11.0` contract, with worker-only routing of frozen executor revisions and consented estimates. A gate result applies only to its exact clean commit. This task owns `origin/dev` and must recheck it immediately before publishing, proving the pushed ref is a fast-forward to that commit. It owns no `origin/main` action.

## Failure/idempotency/security cases
- a red or interrupted gate blocks the push; repair is a new scoped task and a new complete gate
- a changed remote ref requires a fresh ancestry check and, if the candidate changes, a fresh gate
- no `--force`, no post-gate code change, no concurrent publication
- `AUDITMANAGER_COMPARISON_MODULES=none` is the operational rollback gate for C2 comparison work; it does not erase any data

## Rollback / feature flag
The default `AUDITMANAGER_COMPARISON_MODULES=none` prevents the comparison worker from claiming C2 work. Reversal of a development publication is a new reviewed fast-forward commit, never a force push. No automatic production rollback is claimed.

## Handoff
- changed files: pending
- commands/results: pending
- contracts: unchanged; frozen `1.11.0` and `0040`
- known limits: pending
- integration notes: pending
