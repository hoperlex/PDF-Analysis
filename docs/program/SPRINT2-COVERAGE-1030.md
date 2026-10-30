# SPRINT2-COVERAGE-1030

Source candidate only; all execution and checks are explicitly deferred by the owner for this hour.

Fresh ordinary v3 authorities can bind `coverage_version: batched-v1` and immutable `phase_call_limits`. The selected per-window caps are block analysis2, comprehensive4, normative quote review8, critic8 and corrector8: at most30 additional calls per window. Empty optional work consumes no call. The worker refuses another distinct unit before a paid intent when its accepted phase limit is reached; the shared meter and the run-wide ambiguous-effect fence remain authoritative.

## Changed files

- `src/auditmanager/analysis/extended/coverage.py`: pure authority metadata/validation and deterministic bounded planning.
- `src/auditmanager/analysis/extended/core.py`: fresh-only inclusion of all primary observations in a source window; coverage validation.
- `src/auditmanager/analysis/extended/workflow.py`: complete-input batched comprehensive builder, compact exact-partition normative annotations, and coverage helper source in the combined consent digest.
- `src/auditmanager/runs/extended_review.py`: new-policy orchestration, saved batch plans/results, coverage aggregation and report metadata.

## Functional behavior

Comprehensive native and recognised text is split into genuine pieces of at most40,000 characters, retaining distinct source identity, page, character field and exact ranges. Whole native/recognised contexts are not silently reduced to the old48k prefix. Each accepted comprehensive request retains complete observation descriptions instead of the previous800-character summaries. Pieces or observation batches beyond the accepted four-call limit remain explicitly queued with `approved_phase_call_limit`; their source ranges are saved.

Every eligible normative candidate, original observation and requested correction enters the complete known batch plan, rather than only the first40. Each request contains at most20 observations and a bounded character budget. Candidate quote variants are retained and explicitly cause partial normative coverage. Fresh normative replies return only input-bound annotations, so they do not spend output on copying full finding titles and descriptions. Their paragraph IDs and complete quotes must match the actual immutable candidates exactly. Critic inputs remain exact partitions; targeted corrections retain original observations and expose proposals separately.

Batch keys bind window, procedure and ordinal; request fingerprints also bind batch content and the frozen global source. Existing durable reply custody reuses a completed response before considering a fresh dispatch. A process interruption during a window reconstructs the same source-bound requests; ambiguous outcomes prohibit another paid dispatch. Partial/failed saved terminal window receipts are preserved. There is no automatic spending expansion for their unpaid tails.

`result.batches` and each window's `batches` contain stable keys, procedure/index, actual status, source/input IDs, page numbers, character counts, source ranges, request/plan digests and refusal reasons. `phase_coverage` reports known planned/completed/remaining batches, processed/eligible items and the accepted call cap. `phase_call_counts.completed_calls` counts newly completed responses in this execution; `replayed` counts reused replies. These counters are not a billing ledger; failed or ambiguous spend remains in the existing durable journal.

Global `text_coverage.characters_*` unions exact immutable source ranges across overlapping windows. A page counts as processed only after all of its known actual text pieces complete. `known_page_contexts` makes the progressively discovered character plan explicit. Entirely textless input does not acquire invented native-text coverage. A clean empty observation set completes norm/critic/corrector as explicit no-ops without a call.

## Compatibility and limits

Historical accepted v1/v2/v3 authorities without the new coverage flag keep their existing dispatch branch and call counts. Updating the combined helper source digest can safely refuse an old queued v3 authority before new spending; a new accepted estimate/consent is required. No historical digest allowlist or fabricated reply is introduced.

The selected caps can still leave text pieces, observations or proposals unprocessed. They remain visible as partial coverage; this is not a complete-document quality claim. Builders/parsers still refuse oversized or malformed responses, and the existing resource/Attempt deadline may stop long documents. A larger policy would need a separately frozen cost estimate and explicit consent; this change does not automatically raise caps. Source-range coverage records successfully parsed answers, not merely a provider having received an input.

## Integration

API1.14.0 and migration0043 are unchanged. The existing generic extended-result object carries the new receipts. Root owns public aliases, cost policy/preflight, UI integration, Git and dev publication. Public helper names requested: `extended_coverage_policy`, `validate_extended_coverage_policy`, `plan_extended_coverage`, `build_comprehensive_request_batched_v3`, `build_norm_review_request_batched_v3`, `parse_norm_review_batched_v3`.

No tests, imports, compilation, lint, typecheck, build, provider/model call, browser or database execution were performed. No contracts, migrations, root locks/dependencies, global styles, production services, tests or fixtures were changed by this lane. No Git write was performed. Rollback is by disabling fresh batched consent or forward reverting its source; historical receipts remain readable.

## Additional report + original PDF archive

Exclusive presentation grant added `web/src/features/export-evidence-package/**` after the analysis source freeze. Added `index.ts` and `model/package.ts`; the analysis files remained frozen during this followup. Public `buildEvidencePackage` accepts all requested string/ArrayBuffer/Blob reports and actual version IDs, and returns a ZIP Blob only after the entire package succeeds. Consumer features own their buttons and the final download action.

The feature reads existing authenticated `getDocumentVersion` metadata and full `streamDocumentVersionContent` responses. It requires HTTP200, the exact immutable version, PDF media metadata, actual byte length and SHA-256 equality. It fetches each unique version once, preserves every requested OLD/NEW/SOURCE role, and stores PDFs under neutral archive names with their real identities in `manifest.json`. The manifest includes byte sizes and hashes of every report and PDF. No PDF is silently excluded, and any required source failure aborts the whole package.

ZIP STORE/CRC32 code was copied and adapted from this repository's `entities/audit-run/lib/extended-xlsx.ts`, with provenance in source; no private cross-feature import or dependency was added. The complete ZIP including headers/manifest is capped at64MiB, at most32 report files and128 unique PDFs. Downloading/hashing and ZIP construction use bounded in-memory buffers. WebCrypto SHA-256 requires a secure browser context (HTTPS or a browser-recognised local secure context); absence is an explicit refusal, with no unverified hash fallback. AbortSignal cancellation is normalised to AbortError, including aborted transport reads, and archive byte loops yield to cancellation. Progress counts actual completed report/metadata/PDF reads or archive writes. No model/provider or mutation operation is used.

Both consumer owners statically acknowledged the exact public types and imports. No tests, typecheck, build, lint, browser, imports or archive execution were performed. These files and this report are handed to the root integrator as an unverified source candidate; no Git writes were performed by this lane.
