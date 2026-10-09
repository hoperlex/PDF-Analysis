# Task W53-QA-RECHECK-01 — independent repaired-candidate acceptance

## Outcome

Independently repeat all six original `qa_w53` red regressions and the real two-connection reclaim overlap on the integrated repair candidate. Record precise pass/fail, new defects and a bounded 780 px live-browser result if an isolated stand can be built within the measured disk budget. This is evidence for the integrator's personal QA verdict, not a release verdict.

## Depends on

- W53-QA-01
- W53-JUDGE-X
- W53-JUDGE-Y
- W53-PROXY-REPAIR-01
- W53-ALR05-REPAIR-01
- W53-QUEUE-REPAIR-01
- W53-JOBS-REPAIR-03

## Frozen inputs

- Exact pre-grant integrated code SHA `a70e677271045463fb8e03c3426b5430f5f425d8`; integrator assigns the post-grant dispatch SHA.
- API `1.0.0-draft.1`, OpenAPI SHA-256 `008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`; domain rev 9/29 and state-machine SHA-256 `cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466`; migration head `0017_execution_queue`.
- `W53-EXEC-STOP-01/02`, MinIO new-image build/upgrade stop, global pause public-journal scope, and release-notes stop remain outside a green verdict.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- QA report `docs/program/W53-QA-01.md` names six red tests; independent X/Y reports reproduce the key races and omissions. Integrator merged the four exact repairs, repeated ALR-05 and proxy guards **4/4** at `a70e677`.
- On 2026-10-09 14:01:55 UTC, private ports 56960/60560/60561/57060/31560 were unbound; worktree and Docker filesystem each had 10,783,543,296 bytes available. Recheck before any service or expensive run.
- A Chrome for Testing executable exists at `/root/.cache/chrome-for-testing/chrome/linux-154.0.8037.92/chrome-linux64/chrome`; it passed a headless smoke test. Set `E2E_PC01_CHROME` explicitly because the repository CDP harness's default candidates omit that path.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/W53-QA-RECHECK-01.md` only.

## Forbidden hotspots

All product code, tests, contracts, migration, dependencies/locks, composition root, global styles, release/backup/deployment paths, other reports, refs/tags and the working stand. Temporary private logs and config remain outside Git.

## Non-goals

Fixes, contract reseals, publishing a ref/tag, claiming new MinIO/working-stand acceptance, a full `make gate`, or converting owner decisions into inferred policy.

## Deliverables

- Exact SHA/path audit, fresh migrated 0017 private DB and old MinIO, six unchanged independent QA tests; report each outcome. Repeat the two-connection periodic/forced reclaim regression and ALR-05. Review repaired code against X/Y concerns and record any new counterexample precisely.
- If the private stand can be launched with existing images and a defensible disk peak plus margin, use the cached Chrome override to verify the W53 queue and journal at 780 px, including horizontal overflow and one admin/one expert action if fixtures permit. If not, record the exact prerequisite and measured stop; do not silently call static tests a live viewport pass.
- Six AGENTS.md §5 handback items and hashes of private logs.

## Required checks

Use private lane `gate-w53qare`: PostgreSQL 56960, old S3 API 60560, console 60561, API 57060, Next 31560. Measure ports and free bytes immediately before use; use unique database, bucket, volumes and credentials; clean only own resources. Run all `tests/integration/qa_w53` on a fresh database plus `tests/integration/runs/test_w53_jobs_repair.py`, the W53 execution focused suite and ALR-05. Verify frozen hashes and `git diff --check`. Keep exact commands, status and SHA-256 logs under `/tmp/w53-qa-recheck-01/`. No new MinIO image build or shared cache prune.

## Integration contract

Report only. The integrator audits the clean branch, cherry-picks its report, personally repeats the QA checks and decides acceptance. Any confirmed defect returns a precise repair grant before source edits.

## Failure/idempotency/security cases

No duplicate/unseen queue loss, no pause claim after committed pause, every changed provider effect journaled once, no proxy-body leak or false 503 assurance, no `40P01` on periodic/forced overlap, no sensitive payload in audit_event.

## Rollback / feature flag

No behavior change; no flag or rollback.

## Handoff

Changed files; checks/results; contracts; risks; integrator instructions; forbidden-hotspot proof — six AGENTS.md §5 items.
