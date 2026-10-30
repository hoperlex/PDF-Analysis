# Task CMP-C2-GATE-W13-01 — keep the W13 response corpus immutable across additive C0/C2 fields

## Outcome
The historical W13 response records remain byte-for-byte unchanged while the characterization suite checks the current API's `contract_version` and the portal version's `upload_kind` through a narrow, digest-pinned in-memory projection. The twenty currently failing cases pass, and a planted wrong version or upload kind still fails. No product behavior changes.

## Depends on
- CMP-SEAL-C2
- CMP-C2-FIX-01
- CMP-C2-GATE-FE-01

## Frozen inputs
- domain contract: W13 recorded corpus plus the additive `CMP-SEAL-C0` upload-kind field
- API contract: `1.11.0`, 176 paths / 198 operations / 517 schemas
- analysis/comparison/event contract: unchanged from `CMP-SEAL-C2`
- migration head: `0040_comparison_ai_reports`
- base commit: `06c312a3f8d35b569019066fff9e47d38e69501c`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: `tests/characterization/w13_baseline/test_response_baseline.py` with all W13 records and planted-difference controls

## Captured premise evidence
- premise: P-01 and P-02 establish the clean frozen tree and the exact divergence found by the complete gate before the test edit.

### P-01 — clean C2 candidate
- captured_at: 2026-10-29
- command: `git rev-parse HEAD; git status --short; python3 -c 'import json;x=json.load(open("contracts/api/v1/openapi.json"));print(x["info"]["version"],len(x["paths"]),sum(k in {"get","post","put","patch","delete","head","options","trace"} for p in x["paths"].values() for k in p),len(x["components"]["schemas"]))'; ls db/migrations/versions | tail -n 1`
- captured_output:
  ```text
  06c312a3f8d35b569019066fff9e47d38e69501c
  1.11.0 176 198 517
  20261029_0040_comparison_ai_reports.py
  ```
- interpretation: the gate candidate and frozen API/head match the integration task; the W13 source repair starts separately.

### P-02 — exact baseline divergence
- captured_at: 2026-10-29
- command: `rg -c '^FAILED tests/characterization/w13_baseline/test_response_baseline.py' /tmp/cmp-c2-gate-third.log; rg -c '^E           got .*contract_version.*1\.11\.0' /tmp/cmp-c2-gate-third.log; rg -c '^E           got .*upload_kind.*portal_bundle' /tmp/cmp-c2-gate-third.log`
- captured_output:
  ```text
  20
  16
  4
  ```
- interpretation: the first battery is green. The canonical rest is red in historical response bytes; neither W13 record contents nor application responses should be silently rewritten.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `tests/characterization/w13_baseline/test_response_baseline.py`
- `docs/program/tasks/CMP-C2-GATE-W13-01.md`
- `docs/program/CMP-C2-GATE-W13-01.md`

## Forbidden hotspots
- `tests/characterization/w13_baseline/records/**`, `journey.py`, and all other tests
- all product source, `contracts/**`, migrations, root dependencies/lockfiles, composition root, global styles, infrastructure and remote refs

## Non-goals
- no W13 record recapture, broad JSON normalizer, snapshot deletion or gate exclusion
- no API, migration or runtime behavior change; no publication from this repair task

## Deliverables
- one digest-pinned compatibility projection applied only to the twenty identified records, checking the live contract version from the frozen API and exact `portal_bundle` kind in the four version responses
- planted differences that prove wrong version/kind and unrelated response drift still fail
- a repair report with commands, limits and forbidden-hotspot proof

## Required tests
- focused W13 baseline suite before and after the repair; all historical record files must have identical Git object IDs
- the planted-difference controls and governance; `git diff --check`
- the integration task runs a new complete `make gate` on the exact final clean SHA

## Integration contract
The W13 records remain the historical bytes. The test projects only named additive changes in memory with a frozen source digest, so a response divergence outside these fields remains red. `CMP-WAVE-C2-INT` alone owns `origin/dev` publication after a clean full gate; no `origin/main` action is authorized.

## Failure/idempotency/security cases
- if a record changes, the digest-pinned projection refuses before comparing a live response
- a wrong current contract version or upload kind remains a test failure
- no extra body field, status or header is erased by the projection

## Rollback / feature flag
Tests only. Revert the scoped test commit if the projection weakens the characterization guarantee; no data migration or runtime flag changes.

## Handoff
- changed files: `tests/characterization/w13_baseline/test_response_baseline.py`, this task and `docs/program/CMP-C2-GATE-W13-01.md` only; the W13 `records/**` Git objects are unchanged.
- commands/results: the gate's changed-context battery passed 6,592 / 13 skipped before its canonical rest showed 20 W13 response differences; focused baseline with local DB/S3 permissions reproduced 20 failed / 50 passed; repaired focused file 73 passed, including planted wrong-version/kind and changed-record controls; governance 16 passed; `git diff --check` clean.
- contracts: unchanged, frozen API `1.11.0` and migration head `0040_comparison_ai_reports`.
- known limits: the compatibility projection follows the frozen OpenAPI version on a later reseal; a separate contract test must continue to enforce that the served error version equals the document. The interrupted gate is not acceptance evidence.
- integration notes: merge this tests-only repair into the C2 candidate, then run a new complete `make gate` on the exact clean publication SHA. `CMP-WAVE-C2-INT` alone owns `origin/dev`; no `origin/main` action is authorized. Forbidden source, records, contract, migration, root dependencies, composition root, styles and infrastructure were untouched.
