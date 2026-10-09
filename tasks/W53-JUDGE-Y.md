# Task W53-JUDGE-Y — independent invariant and recoverability review

## Outcome

Independently challenge W53's durable execution invariants and the exact limits of MinIO recovery evidence. Return findings with executable counterexamples where possible; do not repair implementation.

## Depends on

- W53-FREEZE-01
- W53-SEAL-01
- W53-EXEC-WEB
- W53-EXEC-REPAIR-02
- W53-REHEARSAL-01 (measured partial evidence integrated)

## Frozen inputs

- domain revision 9 / 29 identities; state-machine SHA-256 `cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466`.
- API `1.0.0-draft.1`, 36 paths / 43 operations / 91 schemas; OpenAPI SHA-256 `008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`.
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
- command: `git rev-parse HEAD; ss -ltn '( sport = :56900 or sport = :60500 or sport = :60501 or sport = :57000 or sport = :31510 )'; sha256sum contracts/api/v1/openapi.json contracts/domain/v1/state-machines.json`
- captured_output:
  ```text
  b6d15733f0e9bf2bffc262f6217ffa9ba8f26e8e
  State Recv-Q Send-Q Local Address:Port Peer Address:PortProcess
  008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193  contracts/api/v1/openapi.json
  cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466  contracts/domain/v1/state-machines.json
  ```
- interpretation: ports were free at capture, require fresh check; no runtime result inferred.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/W53-JUDGE-Y.md`

## Forbidden hotspots

- All other tracked files, especially source, contracts, migrations, tests, root lock/dependency, composition root, global styles, `VERSION`, notes and deployment.
- Unowned Docker resources, cache, working stand, refs and tags.

## Non-goals

- Converting Stage-C old-image baseline into new-image compatibility/rollback proof; the new image is unavailable. No DB backup, working-stand S3 change, release notes or full gate.
- Patching implementation. Report exact defect evidence for integrator repair grant.

## Deliverables

- Y report with line/path evidence and direct test results, severity/affected behavior, clean branch/HEAD, six AGENTS.md §5 handback items, and changed-path proof.

## Required tests

- Review every W53 path that mutates `audit_run`, Job, Attempt or Lease for the lock order `audit_run → job → attempt → lease`; reason about `FOR UPDATE` scope, transaction boundaries and crash windows. Probe at least one two-connection race on private `gate-w53judge-y` PG 56900 if capacity permits; S3 60500/60501, API 57000, Next 31510 reserved only for this lane. Recheck ports and disk before launch; no heavy run in parallel with another lane.
- Check journal event-to-transition completeness and one-to-one semantics, payload allowlist against `non_identity` identifiers, ALR-05 for `execution`, bounded pagination and cursor stability, `CostMeter` across Attempts, orphan-running refusal and startup reconciliation. Directly inspect the W53-REHEARSAL scripts and logs for evidence gaps; distinguish a test's own assertions from verified recoverability.
- On old MinIO baseline, compare source manifest and versioned objects if useful. New-image read/rollback and S3-level restore remain blocked until built and run. If a defect in the proposed full script is found, give exact repro/repair scope.
- Run focused existing tests for claims that can be independently executed; keep lane-specific logs under `/tmp/w53-judge-y/` with hashes. Check frozen hashes, `git diff --check`, exact changed-path audit. Do not add product tests without integrator repair grant.

## Integration contract

The integrator receives an independent invariant review. Findings need exact evidence and a repair grant; only observed disposable results may support acceptance. Owner and disk stops remain open until resolved with new evidence.

## Failure/idempotency/security cases

- Concurrent claim/cancel and lost-lease paths must not duplicate provider effects or invert locks; journal must reveal transitions without leaking provider or identity secrets.

## Rollback / feature flag

No behavior change. Remove only lane-owned disposable resources after evidence capture; the report is revertible.

## Handoff

- changed files; commands/results; contracts; risks; integration instructions; forbidden-hotspot proof — all six AGENTS.md §5 items.
