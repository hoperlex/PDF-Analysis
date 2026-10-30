# SPRINT3-STAGE-1030 — bounded native windowed V3

UNVERIFIED source implementation. Fresh experimental Stage V3 runs use a genuine `windowed-v1` planner for up to 64 native-text pages, 240,000 characters and 1,600 fragments across both sides. This is a new accepted planning policy, not a larger legacy constant. No checks or model execution were performed in this package.

## Changed files and ownership

- New `src/auditmanager/comparison/stage_v3/policy.py`: fresh/stored policy handling and command-outcome readers.
- New `src/auditmanager/comparison/stage_v3/windowed.py`: full native source catalogue, bounded request planning and source-bound parsing.
- `stage_v3/{bridge,mode,procedures,report}.py`: policy dispatch, selected-bundle results/progress, final card/report projection and display metadata.
- `stage_ai/{runtime,repository}.py`: select the accepted policy for estimate/prepare/resume/worker and the existing one-call consent fence.
- `stage_run/service.py`: keep the idempotency fingerprint limited to actual client fields, then freeze the new policy in command outcome/input hash; compare it before reusing an active run.
- `stage_run/batch.py`: freeze parent policy and pass that exact policy to child starts. This actual file was explicitly granted; no nonexistent `stage_batch` or `stage_run/repository.py` was created.
- `stage_review/{cards,service}.py`: explicitly granted fresh-windowed display excerpts, source pins and selection of the matching final experimental classification.
- This report. No UI files were changed by this lane in SPRINT3; the UI owner received the exact metadata fields.

## Accepted authority and historical behavior

Fresh starts freeze `stage_v3_policy = {plan_version: 'windowed-v1', bundle, limits}` in the accepted command outcome and run input hash; fresh initial estimates use its bundle/limits. The idempotency fingerprint includes only actual client fields, including the consent digest which binds the estimate. Internal policy selection happens after `CommandReplay`, so an identical accepted start/batch retry keeps its original replay across deployment/default changes. Batch children inherit the parent command's policy, including an absent legacy policy, rather than selecting the current default later.

Absent policy selects the existing legacy `procedures.BUNDLE` path with sixteen pages /80,000 characters /400 fragments and its existing requests. Resume/worker select the run's stored policy. An active run is reused only when engine, AI choice, staleness and the frozen policy agree. A changed fresh windowed code bundle refuses before new paid dispatch; saved historical policy/result metadata can still be read. Historical client retries are not silently upgraded or assigned a new internal-policy fingerprint.

`AUDITMANAGER_STAGE_V3_PLAN=windowed-v1` is the fresh-start default; `legacy` rolls new estimates/starts back to the historical native plan. Unsupported values explicitly refuse new planning. Accepted command replay occurs before consulting the switch, and accepted windowed/legacy runs and parent batches continue to select their own stored authority rather than the current environment.

The windowed bundle binds its version, limits, legacy prompt/schema bundle, its own actual implementation bytes, shared V3 parsing/report/policy helpers and copied original pure-module bytes. Result lookup, durable progress and card materialization select the run's own accepted bundle. The original copied prompt/algorithm provenance remains `stage_v3/original/SOURCE.json`, PDF-proverka commit `3c99481719218b9cfa7560886529916646c61939`.

## Actual scalable procedure flow

1. Every admitted page and full saved native block is retained. The global Mapper sees all admitted page identities, physical ordinals/source versions and at most two 256-character representative block excerpts per page. `catalogue_only`, excerpt cuts and omitted block counts are explicit; this is not represented as a full text read. The Mapper must account for every page as mapped or unmatched, and its cited block IDs must exist in the supplied catalogue. Overlapping region assignments are refused under this bounded policy.
2. Each mapped region's OLD and NEW blocks are packed by actual encoded size, at most 60,000 characters and 64 blocks per side pack. The planner compares their bounded Cartesian pack pairs, preserving every block within that region. Each plan has stable IDs derived from its region and actual block IDs. Miner evidence can cite only blocks actually included in that request, with exact source version, box and quote binding.
3. Each unmatched primary page is processed in complete source packs. The original deterministic lexical selector provides at most two opposite page candidates. Without a counterpart, a genuine one-sided request can produce only unresolved observations; no counterpart or bilateral change is invented. The accepted response must explicitly address the actual primary page. Candidate-search limitations remain visible.
4. Dedupe operates on stable batches of up to eight events /120,000 compact characters. It must return an exact input partition. Original lossless application preserves event contents/lineage; no global semantic uniqueness is claimed across batches.
5. Every retained parameter gets an independent source-verification unit. One parameter is sent per request. Actual source blocks are selected per side by the saved value/source binding, with a conservative contextual fallback and explicit omitted-source IDs. Confirmed/corrected values must occur in the exact cited text that was actually sent. Unreadable/conflicting results remain distinct; the model does not record an expert decision.
6. Existing deterministic final card/source-report projection retains original Miner values, independent verifier results, all pinned native sources and page coverage. The existing raw comparison evidence is unchanged.

Every final payload is measured including `_validation` and the added source hash before any provider intent; the shared 240,000-character request bound is also retained. Validation metadata carries IDs, not a duplicate full-text source tree. A single oversized block, excessive Cartesian units or result-budget overflow is an explicit refusal, never a hidden source prefix. Classification plans are bounded at 128 units, events at 512 and parameters at 1,024; these are limits, not a claim that all admitted inputs will produce a complete result.

## Consent and durable recovery

The existing one-request-per-explicit-consent boundary remains. Initial consent estimates the bounded catalogue call. Each subsequent resume estimates the exact next known plan using its actual prompt/output bounds. A new unit/request cannot use the preceding request's consent revision. Stable saved responses are reused by their pinned bundle/content key. Existing unknown-effect, prior-call, technical-retry, lease and spend fences are preserved; no blind resend, global quota increase or extra provider route was added.

No new API operation, engine enum, database migration, dependency or composition-root seam is needed. Engine remains `v3_native_text_experimental`; planning metadata uses the existing open experimental JSON objects.

## Progress and honest coverage

`experimental_progress` adds:

- `plan_version`: fresh `windowed-v1`, historical `native-text-v3/1`.
- `limits`: the actual stored planning limits.
- `planned_units`, `completed_units`, `pending_units`: actual known durable units.
- Each existing procedure item adds `planned`, `completed`, `pending`; future work not yet constructed is not counted as planned.

The final source report adds `plan_version` and `limits`. Coverage distinguishes page classification/processing from semantic completeness. It records `catalogue_complete: true`, bounded unmatched candidate scope, and `semantic_comparison_complete: false`; completion of the pipeline is not advertised as proof of complete engineering comparison. Graphical content, scanned/OCR-only pages, normative verification and unrestricted cross-region/global semantic dedupe remain outside this native-text experiment.

## Long-card display seam

Only fresh windowed cards may show an explicit display excerpt in their existing <=20,000-character `before`/`after` fields. Source fragments are never rewritten. Full native quotes remain in `experimental.sources` and `experimental_progress.source_report.source_catalogue`, with source/content hashes. Before projection, the stored display metadata is checked against the actual full source join; a mismatch refuses materialization.

The UI/export owner consumes:

```text
card.experimental.display_text = {
  limit_characters: 20000,
  before: {excerpt, full_characters, displayed_characters, display_characters, full_sha256},
  after:  {excerpt, full_characters, displayed_characters, display_characters, full_sha256},
  full_text_location: 'experimental.sources[].quote; experimental_progress.source_report.source_catalogue'
}
```

`displayed_characters` counts actual source-prefix characters; `display_characters` includes the explicit explanatory marker. Classic and historical native cards retain their previous strict text budget. Expert evidence digests continue to pin the full immutable source content keys/anchors, not the display excerpt.

## Verification, limitations and integration

**No tests, checks, lint, typecheck, compile/import execution, build, browser, DB, provider/model calls, Git commands or fixtures were used**, as explicitly required by the owner. Only source reads/edits were performed; no `PASS` is claimed. Runtime/cost-estimate compatibility, larger-set memory/latency, parser/model response compatibility and historical recovery still require the deferred verification window.

The source candidate is bounded at 64 total native pages and the shared repository's existing 64-profile prerequisite. Dense/noisy mappings can hit explicit unit/result budgets. Mapper excerpts can miss a useful correspondence; unmatched lexical candidates and batch-local dedupe are deliberately limited. A complex parameter can need more evidence than the bounded verification source selection supplies and must remain unreadable/conflicting rather than be asserted correct. These limits are recorded instead of being treated as full original V3 parity.

The integrator is the sole Git writer/publisher to `origin/dev`; no main/production action is authorised by this lane. API1.14.0, migration0043, root locks, contracts, global styles, fixtures and other lanes' files remain untouched. Integration needs only the changed owned/granted files and the UI consumer's matching fields. Rollback is a forward revert/disable of fresh windowed selection; never reinterpret saved replies under a different bundle or spend again on an ambiguous outcome.
