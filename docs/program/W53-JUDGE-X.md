# W53-JUDGE-X — independent adversarial execution review

Branch `agent/w53-judge-x`; exact assigned base `f0b1a0ede0c6edb90d4d0072429cb95b28e7a945`. This review used only disposable `gate-w53judge-x` PostgreSQL on 56890 and the **old** MinIO image on 60490/60491, plus a local synthetic HTTP fault server on 56990. No production provider, working stand, new MinIO image, published ref or tag was used. The integrator reads back the handback commit SHA after this report is committed.

## 1. Changed files

Only `docs/program/W53-JUDGE-X.md`. Scratch reproducers and logs under `/tmp/w53-judge-x-*` are not tracked source or tests. No application repair was attempted.

## 2. Commands, observations and logs

Frozen OpenAPI and state-machine SHA-256 values matched `008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193` and `cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466`; migration head is `0017_execution_queue`. At 2026-10-09 13:41:58 UTC, `df -B1 . /var/snap/docker/common/var-lib-docker` reported 11,488,362,496 available bytes on the same filesystem; all reserved ports were free. Already-local old images were inspected before launch. This bounded two-container, small-fixture run had less than 1 GB expected new data with more than 3 GB margin. No image build or shared cache prune ran.

| Independent check | Result | Log SHA-256 |
| --- | --- | --- |
| Fresh private PostgreSQL migration to 0017 | PASS | `/tmp/w53-judge-x-migrate.log`: `a0d302093da343bda890db0d31976107ca602b4f21e9fa44264fa61eed79c036` |
| Existing proxy adapter baseline | 81 passed | `/tmp/w53-judge-x-proxy-baseline.log`: `498967a0171614a3a71e23a0f11fac2e872fcd55066bd9fcb982763847126dbb` |
| Served operation role register, four role sets plus profile/default states and archived/unauthenticated checks | 23 passed | `/tmp/w53-judge-x-roles-live.log`: `a6de5fb133585f685fcf1f55ff7014a0ffc627ef7b94af31e55abce460e8a86b` |
| Four direct role denials: cancel/re-audit with no role, priority/pause with expert only | All `permission_denied`; command-record, audit-event, running-Job counts and pause state unchanged after each | `/tmp/w53-judge-x-denials.log`: `619d3224fc561445e35143966324e2bcea94084e12b29969d77ff675adc3ae53` |
| Unreachable S3 and no filesystem fallback | 4 passed | `/tmp/w53-judge-x-s3-unreachable.log`: `fa1cc45cd6cbd1f12f8324990b7c2190ccbcbbe1793dd9692839895bec350a06` |
| Bounded fake S3 `OSError(ENOSPC)` | Typed `StorageUnavailableError`; no synthetic bucket/path in error details; physical host disk was not filled | `/tmp/w53-judge-x-s3-injection.log`: `0b213b09c177017c89832f491a9dc54ef27911425c3b5cfc8d5dde4c3945835e` |
| Durable W53 lease, uncertain effect, refusal, budget and journal tests | 11 passed | `/tmp/w53-judge-x-w53-durable.log`: `d59be28b84a169bc126f3df4ce51f4d3d9e318a6f50f0bd126c616851304f9a3` |
| Five independent synthetic provider faults on loopback | `not_sent`, 429/Retry-After 2, post-body reset, foreign 503, 400 classified as pinned; same request scope reused its idempotency key, changed scope changed key; each request ID differed. No external provider. | `/tmp/w53-judge-x-proxy-live.log`: `a972a5116c1296e46d364323234f2c6fafdf42936fc52566fc6ccc574958255b` |
| SIGKILL after committed `provider.prepared`, before provider dispatch | First process exit `-9`; one prepared effect was reclaimed to `outcome_unknown`, Run and Job failed, zero provider calls, second `execute_run` typed refused | `/tmp/w53-judge-x-kill-final.log`: `e801497be0c755447118cc82ead4210697259b4b2093f379dca3f14e2f23b2b1` |
| Durable journal/stage-result and own PostgreSQL/MinIO service log sentinel scan | 73 rows scanned; zero secret-token, synthetic provider-body, authorization, proxy-URL or scratch-path occurrences in durable records; zero secret/token/provider-body markers in service logs | `/tmp/w53-judge-x-journal-scan.log`: `d729f1b191def7771bb8194aae0de79089a9fa6fb5dfb3454207eec5bd48b0e2`; PG service `0ec5dff317e0e20411d128a13c9eac0fa86691158291ccaa9293e891ebc3d31a`; S3 service `3fdb759df3a1a54495f4140d9cc63b4b107df2f4215305ca276576a66859a850` |

The first role-register attempt without `S3_ENDPOINT_URL` gave two passes and 21 fixture setup errors (`/tmp/w53-judge-x-role-register.log`, `b0fff719b3499a8444510a7e7bdba83e6de533b018e8747da26e23920e13bf99`); the same suite passed 23/23 after the own S3 lane was ready. The first two SIGKILL harness assertions failed because a prior own test's expired lease made the global reclaim count two, and because SQLAlchemy `RowMapping` iteration yields keys. The final assertion scoped to the killed Run and passed; these were measurement errors, not application failures.

Stage-C logs were read and their reported hashes verified, including proxy and process recovery, but are not counted as Judge X evidence. `infra/deploy/verify-deployed.sh` was inspected: it reads `git status --porcelain` and identifies a dirty checkout; it was not invoked against the working stand. No browser executable or installed browser bundle was available, so the 780 px overflow remains static CSS/test evidence, not a live viewport result.

### Findings needing exact repair grants

**X-01 — high, provider error body leaks through service log.** `src/auditmanager/analysis/text/proxy.py` `_map_http_failure` logs `_redacted_error_body(body)` for every HTTP refusal. The regex masks selected token/URL shapes, but arbitrary provider text survives. A pure local call with `{"error":{"code":"foreign","message":"PRIVATE DOCUMENT CHAIRMAN NOTES"}}` printed that full synthetic private phrase in the warning log; the live loopback fault server did the same. See `/tmp/w53-judge-x-pure-proxy-repro.log` SHA `5716e20e5a9c20ad05db8cef1b6ffd5417ae52ed50a6bf3509dfa5ecd4258ae7` and the loopback log above. This is a confidentiality failure in application logs; the durable execution journal and UI projection did not show the marker in this run. Remove the untrusted body text from log output and guard with a short ordinary-language sentinel, not only URL and `sk-` patterns.

**X-02 — medium, foreign 503 writes a false no-spend explanation.** The same `_map_http_failure` returns the message “the model proxy is saturated; the call was not made” for *every* 503. `_classified_http_failure` correctly reports foreign 503 as `outcome_unknown`, `retry_safe=False`, so the executor does not re-spend it; however `StageError.from_domain_error` copies `str(error)` into persisted `stage_result.error.message`. The pure reproducer above prints both contradictory facts. Fix wording without widening the safe-retry classifier; the real proxy-owned envelope is still absent under `W53-EXEC-STOP-01`.

**X-03 — high, pause can commit before a new claim while an Attempt still starts.** `DurableCarrier._poll` reads `next_queued_run` in a session that closes before `super().submit`. `_NEXT_JOB` checks `execution_control.paused`, but `JobRepository.start_execution` does not recheck pause while claiming. On this private 0017 database: choose queued Run, commit administrator pause, confirm `next_queued_run` now returns none, then call `start_execution` in a new session; it minted an Attempt and moved Job/Run to `running` while `paused=true`. No provider call was made. Exact result `/tmp/w53-judge-x-pause.log` SHA `8b5daccacab7603c2437879432511f625a621cf4aca67234e972727ba126fd90`. The W53 plan says the claim checks pause and runnable Run state in the same transaction. The integrator and QA received this evidence before handback.

## 3. Contracts

No API, domain, migration, image, frontend, error catalog or other contract changed. The new MinIO image was not available locally and this review's S3 observations use the old image only.

## 4. Risks and limits

`W53-EXEC-STOP-01` still lacks a genuine own-proxy 503 envelope; it was not invented or called safe. `W53-EXEC-STOP-02` still requires the owner decision on cancellation during `validating`; the existing typed refusal was among the 11 passing W53 tests. New MinIO build/copy/rollback remains blocked by its capacity stop, and backup remains a separate beta wave. The loopback proxy probes verify transport classification and headers, while the own database tests verify durable lease refusal; no paid provider or browser viewport was exercised. A full `make gate`, release verdict, and deployed-stand validation were outside this Judge X grant.

## 5. Integrator instructions

Issue narrow grants for X-01/X-02 in `analysis/text/proxy.py` and X-03 in the Job claim hotspot, then repeat the adverse cases on the merged exact SHA. The body leak and false 503 text must not be dismissed as passing merely because the safe-retry classifier was correct. Continue to mark own-proxy 503, validating cancellation and new-image MinIO upgrade as separate open conditions. No source change from this branch should be merged except this report.

## 6. Allowed paths and forbidden hotspots

The base-to-HEAD changed-path audit must contain exactly `docs/program/W53-JUDGE-X.md`; `git diff --check` must pass. No `contracts/**`, migration, runtime source, test, root dependency/lock, composition root, global style, `VERSION`, notes or deployment file was changed. No ref/tag was published. `docker rm -fv` removed only `gate-w53judge-x-pg` and `gate-w53judge-x-s3` plus their anonymous volumes; there are no matching containers or lane-named volumes, and ports 56890/60490/60491/56990/31490 were free at cleanup readback. The temporary private env file was removed.
