# Task W53-JUDGE-X — independent adversarial runtime review

## Outcome

On a disposable W53 stand, independently attack execution fault handling, role-protected queue commands and secret boundaries. Return evidence-backed findings to the integrator; do not repair source.

## Depends on

- W53-FREEZE-01
- W53-SEAL-01
- W53-EXEC-WEB
- W53-EXEC-REPAIR-02
- W53-REHEARSAL-01 (its MinIO capacity stop remains open)

## Frozen inputs

- domain revision 9 / 29 identities; state-machine SHA-256 `cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466`.
- API `1.0.0-draft.1`, 36/43/91; OpenAPI SHA-256 `008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`.
- analysis/comparison/event: frozen W53 SEAL set; migration head `0017_execution_queue`.
- base code before dispatch: `b6d15733f0e9bf2bffc262f6217ffa9ba8f26e8e`; use assigned post-dispatch SHA.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

### P-01 — integrated base, hashes and reserved lane

- captured_at: 2026-10-09 13:31:34 UTC
- command: `git rev-parse HEAD; ss -ltn '( sport = :56890 or sport = :60490 or sport = :60491 or sport = :56990 or sport = :31490 )'; sha256sum contracts/api/v1/openapi.json contracts/domain/v1/state-machines.json`
- captured_output:
  ```text
  b6d15733f0e9bf2bffc262f6217ffa9ba8f26e8e
  State Recv-Q Send-Q Local Address:Port Peer Address:PortProcess
  008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193  contracts/api/v1/openapi.json
  cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466  contracts/domain/v1/state-machines.json
  ```
- interpretation: ports were free then; recheck immediately before use. This does not prove service behavior or disk capacity.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/W53-JUDGE-X.md`

## Forbidden hotspots

- All other tracked files, especially source, contracts, migrations, tests, root lock/dependency, composition root, global styles, `VERSION`, notes and deployment.
- Unowned Docker resources, cache, working stand, refs and tags.

## Non-goals

- Backups, forced-command pull, stand upgrade and release checks; owner moved backup to a separate beta wave. The new MinIO image is not built, so label any old-image runtime result accurately.
- Claiming own-proxy 503 safe retry without real source-backed envelope (`W53-EXEC-STOP-01`) or `validating` cancel as success (`W53-EXEC-STOP-02`).
- Filling the physical host disk or sending real provider calls.

## Deliverables

- Adversarial X report with actual observed results, exact reproducers, finding severity/affected paths, log hashes, clean branch/HEAD, six AGENTS.md §5 handback items and allowed-path proof.

## Required tests

- Use only private `gate-w53judge-x`: PG 56890, S3 60490/60491, API 56990, Next 31490 and unique database/bucket. If a built stand needs the unavailable new MinIO image, use an explicitly labeled old-image disposable stand for execution behavior and record the new-image stop separately. Recheck ports and disk as AGENTS.md §8 before a heavy launch. Coordinate so no heavy builds/gates overlap another lane; no Docker prune.
- Probe the five provider faults from W53 §3.1 independently: no bytes, 429/Retry-After, post-send reset, foreign 503, 400. Test real own-proxy 503 only if owner evidence arrives. Vary retries, idempotency key and process interruption to search for double spend.
- Exercise queue actions for all active role combinations and an unauthenticated user; verify denied actions leave durable state unchanged. Probe S3 unreachable and a bounded injected disk-full error without consuming host capacity. Inspect UI error handling and 780 px overflow with a browser if available; otherwise report the exact limitation.
- Search relevant app, service and journal logs for test secret sentinels, tokens, provider bodies, URLs and path leaks. Inspect that a deploy check sees a clean checkout; do not invoke the working stand or publish anything.
- Read the Stage-C logs but do not treat them as your own evidence. Return independent observations or an exact blocked matrix. `git diff --check` and exact changed-path audit are required.

## Integration contract

The integrator receives a hostile runtime review on the merged SHA. Each upheld defect needs a narrow repair grant before acceptance; a blocked case is named and not converted into a pass. No source or contract edit is authorized.

## Failure/idempotency/security cases

- Ambiguous transport cannot cause automatic replay. All role denials are typed and atomic. Sensitive material must not enter journal, browser text or logs. Stop at any unowned resource boundary.

## Rollback / feature flag

No behavior change. Remove only lane-owned disposable resources; report/reproduce any failed cleanup.

## Handoff

- changed files; commands/results; contracts; risks; integration instructions; forbidden-hotspot proof — all six AGENTS.md §5 items.
