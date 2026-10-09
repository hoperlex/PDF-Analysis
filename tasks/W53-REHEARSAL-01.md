# Task W53-REHEARSAL-01 — disposable W53 rehearsal

## Outcome

Produce reproducible, measured evidence for the pinned MinIO image upgrade/rollback and W53 execution fault behavior on isolated, disposable services. Report each scenario as passed, failed, or blocked with its exact cause; a script or static assertion alone is not runtime acceptance.

## Depends on

- W53-FREEZE-01 — frozen input and lane/port ownership completed.
- W53-SEAL-01 — contract and migration implementation integrated.
- W53-EXEC-WEB — Stage-B code handback integrated; its UI tests passed.
- W53-EXEC-REPAIR-02 — orphan-running execution authority repair integrated.

The MinIO source/image preparation is present at the assigned base, but its runtime acceptance is still open. This task measures that open acceptance; it does not assume success. W53-EXEC-STOP-01 and W53-EXEC-STOP-02 remain owner decisions, not dependencies whose completion may be claimed.

## Frozen inputs

- domain contract: candidate revision 9, 29 identities; `contracts/domain/v1/state-machines.json` SHA-256 `cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466`.
- API contract: `1.0.0-draft.1`, 36 paths / 43 operations / 91 schemas; `contracts/api/v1/openapi.json` SHA-256 `008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`.
- analysis/comparison/event contract: frozen W53 SEAL set; do not edit or reseal.
- migration head: `0017_execution_queue`.
- base code commit before this dispatch: `afb28913cdf613fc6f8968dabd6d9c641ef224a4`. Integrator assigns the exact post-dispatch SHA for the new worktree.
- pinned MinIO source: `RELEASE.2025-10-15T17-29-55Z`, commit `9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a`, archive SHA-256 `45521908307306e925c98d629e1c17d78c8b72b6ee242b1bfb1409f7d8ee5841`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

### P-01 — integrated code and contract files

- captured_at: 2026-10-09 13:21:48 UTC
- command: `git rev-parse HEAD; sha256sum contracts/api/v1/openapi.json contracts/domain/v1/state-machines.json; git ls-files infra/minio/Dockerfile infra/local/docker-compose.yml infra/deploy/compose.server.yml src/auditmanager/runs/executor.py src/auditmanager/jobs/repository.py tests/integration/runs/test_w53_execution.py`
- captured_output:
  ```text
  afb28913cdf613fc6f8968dabd6d9c641ef224a4
  008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193  contracts/api/v1/openapi.json
  cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466  contracts/domain/v1/state-machines.json
  infra/deploy/compose.server.yml
  infra/local/docker-compose.yml
  infra/minio/Dockerfile
  src/auditmanager/jobs/repository.py
  src/auditmanager/runs/executor.py
  tests/integration/runs/test_w53_execution.py
  ```
- interpretation: the named code paths and hashes exist at the integrated candidate; runtime outcomes are not proven.

### P-02 — reserved ports and current disk

- captured_at: 2026-10-09 13:21:48 UTC
- command: `ss -ltn '( sport = :56880 or sport = :60480 or sport = :60481 or sport = :56980 or sport = :31480 )'; date -u '+%Y-%m-%d %H:%M:%S UTC'; df -B1 . /var/snap/docker/common/var-lib-docker`
- captured_output:
  ```text
  State Recv-Q Send-Q Local Address:Port Peer Address:PortProcess
  2026-10-09 13:21:48 UTC
  Filesystem        1B-blocks         Used   Available Use% Mounted on
  /dev/vda3      126828056576 108314820608 12059766784  90% /
  /dev/vda3      126828056576 108314820608 12059766784  90% /
  ```
- interpretation: named ports had no listener at capture time; recheck immediately before use. Worktree and Docker root share a nearly full filesystem. This is not a build capacity grant.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/W53-REHEARSAL-01.md`
- `scripts/rehearsal/w53/**` (new files only; avoid prose that accidentally changes the scripts surface census)

Disposable generated data and logs may live under a named `/tmp/w53-rehearsal-*` directory, outside the tracked tree. Record their paths and SHA-256s in the report. Do not alter other tracked paths, even to repair a failure; return an exact defect for an integrator repair grant.

## Forbidden hotspots

- `contracts/**`, migrations, root dependency/lock files, composition roots, global styles, `VERSION`, notes, AGENTS.md, deployment scripts and the working stand.
- Other agents' worktrees and all unowned containers, volumes, Docker caches and image tags.

## Non-goals

- Database backup, forced-command pull, restore policy, and working-stand S3 upgrade or backup. Those belong to a separate beta wave or a separate owner decision.
- Claiming the own-proxy 503 safe-retry case without a measured, source-backed 503 envelope. Keep `W53-EXEC-STOP-01` open if no owner evidence arrives. Keep `validating` cancellation refusal as documented until owner resolves `W53-EXEC-STOP-02`.
- Release `v0.3.0`, `VERSION=0.4.0`, release notes, origin refs, tags, full gate or main deployment.

## Deliverables

- Reproducible isolated rehearsal scripts under `scripts/rehearsal/w53/` where useful.
- `docs/program/W53-REHEARSAL-01.md`: six AGENTS.md §5 handback items; exact branch, assigned base and HEAD SHA; per-scenario evidence, logs and hashes; resource cleanup and changed-path audit.

## Required tests

1. Before **every** image build or large test battery, apply AGENTS.md §8: capture UTC time, `df -B1 .`, `df -B1 "$(docker info --format '{{.DockerRootDir}}')"`, expected peak growth and safety margin next to the log. Recheck immediately before launch. If a credible bound is unavailable or margin is insufficient, do not launch; record the stop and continue independent low-cost checks. Never blindly repeat a disk-failed gate. Do not prune shared Docker caches.
2. On private `gate-w53rehearsal` resources only, build the pinned MinIO server image if the disk rule allows. Inspect executable version and image labels. Write named/versioned objects with the old image, stop it, copy its volume, read and hash the objects with the new image, then restore at S3 level to a fresh old-image volume and verify exact keys, versions and bytes. Preserve evidence of old/new/rollback; no working-stand data.
3. Exercise W53 execution with a fault-injecting provider/proxy on isolated PG/S3: no bytes written, 429 with `Retry-After`, reset after send, foreign 503 and 400. If a genuine own-proxy 503 fixture is not available, mark that scenario blocked. Kill process mid-run, start a second serving process and verify durable recovery, at-most-once effects, journal ordering and no unsanitized secret. Record exact setup and observables; do not substitute code inspection for a runtime result.
4. Run relevant focused tests/static checks, capacity/cost measurements, `git diff --check`, and `git diff --name-only <assigned-base>..HEAD`. Report any scenario that cannot be made independent of disk or owner input as blocked, with evidence.

## Integration contract

The integrator may use only observed disposable results as proof of MinIO compatibility/rollback and execution fault behavior. A passing script alone is insufficient; include actual output and hashes. Failed/blocked scenarios produce exact repair or stop records, without widening this lane's paths. No new app/API contract is authorized.

## Failure/idempotency/security cases

- Retry only the proven pre-send/typed-safe classes. Reset-after-send and foreign 503 retain `outcome_unknown` and the same command key for any explicit repeat. Never infer own-proxy origin from a bare status 503.
- Preserve object identity and bytes over upgrade/rollback; compare manifests, not merely count.
- Keep credentials out of logs and checked-in files. Services must bind the reserved lane ports; clean up only owned disposable resources after evidence capture.

## Rollback / feature flag

No runtime code change is authorized. Disposable MinIO rollback is part of the measurement. Stop and remove only lane-owned resources on failure; retain log evidence.

## Handoff

- changed files: exact base-to-HEAD list
- commands/results: exact commands, status, logs/SHA-256, time and disk preflight
- contracts: unchanged or name an unauthorized issue
- known limits: each blocked or failed scenario separately
- integration notes: what can and cannot be accepted
- forbidden-hotspot proof: diff-path audit and lane resource ownership
