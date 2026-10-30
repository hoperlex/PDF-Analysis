# HOTFIX-AR-WORKFLOW-RUNTIME-1030

Runtime handoff2026-10-30. Fresh policy `extended-review-v2`; existing API1.14.0 and migration0043. Root is the sole Git writer and publisher. No real provider, DB, production, contract, dependency or migration change was performed by this lane.

## Result

A new accepted v2 consent now selects a genuine four-procedure workflow, persisted inside the existing extended-review artifact: `block_analysis`, `comprehensive_analysis`, deterministic `finding_merge`, and `norm_verification`. Procedure statuses are actual queued/running/completed/partial/failed/unavailable/skipped states with reasons. The public reader exposes the accepted v2 plan before the first artifact, derives explicit skipped procedures for a terminal base chain without a receipt, and explains historical/no-v2 policies without inventing stages. Existing v1 execution and its three-call request path remain intact.

Portal sources keep their verified IMAGE crops. A native PDF without portal geometry now uses real whole-page PNGs, rendered by the existing PDFium adapter and shared lock. The helper verifies source Blob metadata, streams the immutable PDF into a temporary file, renders at most16 pages with bounded pixels, publishes PNGs through the caller's durable publication store and returns bound ArtifactRefs. Its identities bind version, source SHA, page and render profile; they are generic native crop IDs, never fabricated portal block IDs. Identical PNGs publish/bind once while page identities remain distinct. Images larger than4MiB and pages outside the approved window are explicitly unreviewed. No OCR is performed or claimed.

At most two eight-image requests perform block analysis, followed by one independent comprehensive request over actual native page context and visual/text observations. Exact deterministic merge preserves original duplicate metadata and never spends another call. Norm lookup uses the pinned local corpus; at most one further model request assesses a bounded window of real paragraph quotes. The norm window is at most40 observations and16,000 characters of titles/descriptions/candidate quotes; overflow remains explicit and unreviewed. Missing corpus or candidates is unavailable, rather than a fictional check. Maximum additional model calls: four; no fourth call when no norm context exists.

Before each dispatch the existing authority, consent, price, journal and saved-reply fences remain active. A failed text parser with source-safe inputs may still receive independent v2 visual work. Prepared/received/unknown text effects, missing binding and credential/model identity failures block further dispatch and produce skipped-procedure receipts. Cancellation checks precede native page rendering and every model effect. A failed/partial/unavailable accepted extended branch degrades a successful text StageResult to PARTIAL with a valid StageError, so terminal selection cannot report full success for an incomplete requested workflow.

## Changed files

- `src/auditmanager/analysis/extended/native_pages.py`
- `src/auditmanager/runs/extended_review.py`
- `src/auditmanager/runs/executor.py`
- `tests/unit/analysis_extended/test_workflow_runtime.py`
- This report.

Root-owned lazy public wrappers expose `prepare_native_page_sources`, procedure/core APIs and existing read transport. The core/workflow and widget changes belong to the separately assigned owners; this lane did not edit them.

## Focused proof

- New runtime/native/read tests: **9 passed**. Includes actual AR fixture PDF rendering, real PNG checksums/page provenance, explicit2-of8 rendering coverage, two image batches plus comprehensive and norm calls, unavailable corpus, bad norm response preserving observations, native runtime variant without false degradation, and queued/terminal/legacy read receipts.
- Existing v1 core/runtime tests: **19 passed**, preserving prior recorded behavior.
- Combined focused runtime/core test files: **28 passed in1.10s**; scoped compile and `git diff --check` PASS.
- No real model calls, DB tests, heavy suite, gate, production mutation or Git action in this task.

## Limits

This remains bounded preliminary analysis, not the original application's complete critic/corrector/export pipeline. It does not create OCR, prove normative edition/applicability, automatically continue beyond16 pages/blocks, or expose generic native crops through the portal crop endpoint. Native sources retain actual page/version/hash anchors for the UI. A failed base preparation cannot create an image workflow; the read receipt explains that the requested procedures did not execute. Fresh v2 consent is required; historical accepted commands are not silently upgraded.

## Integration

Commit with root's v2 preflight authority and public wrappers, the core owner's comprehensive/norm/merge methods, and the UI owner's planned procedures/final refetch/native-source presentation. Root alone performs final build and authorised dev publication. No authority to publish main is granted.

## TEXT-only portal forward fix

A validated portal bundle containing only TEXT blocks, no crops and no page/block geometry mismatch now supplements its PDF with genuine native page visuals. It retains source_type=native_page and the explicit portal_text_only_native_page_visuals reason/warning; no portal IMAGE identity is fabricated. Any IMAGE block/refusal or known geometry mismatch prevents this fallback. Focused runtime tests include TEXT-only portal→native visual workflow and a mismatched portal whose native helper must never execute; the latter retains unavailable block analysis and a partial overall result. Targeted runtime/native/read suite: 11 passed. Scoped compile and whitespace checks PASS. No Git/provider/DB/contract changes.
