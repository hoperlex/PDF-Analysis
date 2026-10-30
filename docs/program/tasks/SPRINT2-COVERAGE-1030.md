# SPRINT2-COVERAGE-1030

task_id: SPRINT2-COVERAGE-1030

## Outcome

Improve complete ordinary-section text/norm/critic/correction coverage with durable bounded batches, preserving every saved source and observation.

## Frozen inputs

- Base: `5e4ef75a` (origin/dev refreshed at this window start).
- API: 1.14.0; 233 paths /259 operations /620 schemas; migration0043.
- Original read-only source: `/tmp/pdf-proverka-original`, commit3c99481719218b9cfa7560886529916646c61939.
- Completed dependency: SPRINT-SECTION-INT-1030, published78d5799e.
- Owner explicitly continues another one-hour implementation window: 14:50–15:50 Europe/Moscow, no checks; lane handback15:32, integration/publication before15:50.

## Depends on

- SPRINT-SECTION-INT-1030

## Forbidden hotspots

- Other lane owned files; contracts/**; migrations; root dependencies/locks; global styles; production services; origin/main; tests/** and fixtures/** (synthetic inputs owned by another session).
- No tests, imports/compile, lint/typecheck/build, runtime/browser/DB/model execution or checks. Static source reading and Git metadata for root integration only.

## Non-goals

No production deployment or beta/original quality claim; no automatic expert decision or rewrite of raw comparison evidence; no synthetic inputs; no new OCR service/API/migration.

## Required tests

- command: none, expressly deferred by owner for this hour.
- expected: UNVERIFIED source candidate; no PASS claim.

## Integration contract

Root is sole Git writer and publisher to origin/dev, exact clean FF/read-back. API1.14.0/migration0043 remain frozen. Old accepted v1/v2/v3 authorities keep old request/count behavior; new paid behavior requires separately frozen fresh policy metadata and sufficient explicit cost consent. Unknown paid outcomes never trigger a resend. Coordinate helper signatures before editing another lane seam.

## Rollback / feature flag

Fresh-policy behavior boundary; preserve historical receipts. Disable fresh enhanced policy or forward revert; no retroactive paid expansion. Existing switches retained.

## Handoff

Return changed files, actual work, no-check status, unchanged contracts, limitations and integration notes. Freeze by15:32Europe/Moscow; no Git writes or tags.

## Allowed paths

- `src/auditmanager/runs/extended_review.py`
- `src/auditmanager/analysis/extended/core.py`
- `src/auditmanager/analysis/extended/workflow.py`
- `src/auditmanager/analysis/extended/review.py`
- `src/auditmanager/analysis/extended/coverage.py`
- `web/src/features/export-evidence-package/**`
- `docs/program/SPRINT2-COVERAGE-1030.md`

## Deliverables

Fresh policy revision only. Separate comprehensive text pieces instead of dropped tail; bounded norm/critic/corrector batches instead of first40. Stable per-batch keys, saved replies, actual coverage/counts, global budget/unknown fences. Discuss exact new phase-call limits with root before coding dispatch.

## Frozen batching seam

Fresh ordinary v3 consent defaults to `coverage_version=batched-v1`, `phase_call_limits={block_analysis:2,comprehensive_analysis:4,norm_verification:8,finding_review:8,finding_correction:8}` per window, maximum30 additional calls. Root public helpers: extended_coverage_policy(), validate_extended_coverage_policy(policy), plan_extended_coverage(**kwargs) delegate to analysis.extended.coverage. Fresh budget reserves actual phase caps and output maxima; empty phases spend zero. `AUDITMANAGER_EXTENDED_COVERAGE=legacy` keeps fresh six-call v3 allowance. Old accepted authorities never acquire batch spending. Changed implementation SHA safely refuses old queued v3 before dispatch and requires fresh consent; do not fake legacy hashes.

## Additional exclusive presentation archive slot

The coverage source is frozen. This lane additionally owns `web/src/features/export-evidence-package/**` for a concrete read-only report+original-PDF ZIP feature. Other agents own only consumer buttons. Public API:

```ts
interface EvidencePackageReport { name: string; content: string | ArrayBuffer | Blob; mediaType?: string }
interface EvidencePackageSource { versionUid: VersionUid; side?: 'OLD' | 'NEW' | 'SOURCE' }
interface EvidencePackageProgress { phase: 'preparing' | 'sources' | 'packaging'; completed: number; total: number; currentVersionUid?: string }
buildEvidencePackage({fileName, kind, runId, reports, sources, signal?, onProgress?}): Promise<{blob: Blob; fileName: string}>
```

kind is `section-analysis` or `stage-v3`. Use existing authenticated getDocumentVersion/streamDocumentVersionContent; inspect exact public names/fields. Package all requested reports and unique actual version PDFs; record side roles, actual bytes and SHA in manifest.json, verify against immutable version metadata where exposed. ZIP STORE/CRC32 may be copied from existing repository source with provenance, no new dependency/private cross-layer import. Maximum complete package64MiB, bounded entries. A missing/oversize/refused source aborts the whole package with an explicit error; no silent reports-only fallback. Signal cancellation and progress reflect only completed actual reads. No model calls, API/schema/DB or source mutation. No tests/checks. Handback≤12:30UTC.
