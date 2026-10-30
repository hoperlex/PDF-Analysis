# SPRINT-SECTION-RUNTIME-1030 — source handoff

2026-10-30; development-only source work. The owner explicitly prohibited checks, tests, lint, builds, compilation, model calls and fixture work for this sprint. **No verification PASS is claimed.** Root is the sole Git writer and dev publisher. API1.14.0 and migration0043 remain unchanged by this lane.

## Implemented runtime

Fresh `extended-review-v3` authority selects the complete admitted visual set (up to1000 sources) in up to63 sequential windows of16. The immutable authority binds max_blocks, text_page_limit, window_size16, max_windows, review=true, section_code and the combined rules_sha256. The hybrid window count is MAX(ceil(max_blocks/16),ceil(text_page_limit/16)); the visual source limit is1000, text-page limit500 and max_windows at most63. A portal with two IMAGEs and100 native-text pages therefore receives seven text/review windows rather than silently stopping after its first visual window. Legitimate text-only windows spend no image call and record completed block_analysis with reason no_visual_sources_in_window; known geometry/IMAGE refusals remain explicit. The worker uses the accepted section rather than mutable latest classification, and compares the same public bundle digest used by preflight before paid work. v1/v2 retain their old policy selection and request builders.

The actual order uses two passes. The first pass performs at most two eight-image block calls/window and saves source-bound visual receipts. The ordinary primary-text stage then runs. Fresh v3 explicitly forces the existing durable WindowReplyCustody path even for a single primary-text window; an additional owned flag in analysis/text/windowed.py prevents its historical single-window delegation from bypassing reply custody. v1/v2 do not opt into that flag. The second pass reads the same saved block replies without dispatch or charging, incorporates actual primary-text observations from the current window, and runs comprehensive analysis, deterministic merge, normative quote review, real critic and targeted corrector. A corrector without flagged inputs and a critic without observations consume no call. Maximum additional calls/window: six; deterministic merge/report consume none. The consent also covers ordinary primary-text calls separately.

Native PDFs render genuine bounded whole-page PNGs, at most16 at a time. Window offsets avoid rendering the entire document into memory. The postpass reuses custody-bound PNG references from its saved visual receipt rather than rerendering. Source identities bind the actual PDF/version/page/render profile and SHA; no portal block ID or crop URL is fabricated. TEXT-only portal input can use this native path only after cohort validation and with no known geometry/IMAGE refusal. Existing portal IMAGE crops retain their real source identity. Oversized PNGs, geometry failures and source-budget remainder stay explicit.

Every comprehensive window receives its actual pages and adjacent context, not pages1–16 repeatedly. Portal recognized text is passed in distinctly marked recognized sources with its artifact SHA, without native offsets or invented OCR. Native text, recognized text and images keep separate source IDs. Primary-text source IDs in v3 are content-bound across windows; legacy ordinal IDs are unchanged.

Each window records seven actual procedures: block_analysis, comprehensive_analysis, finding_merge, norm_verification, finding_review, finding_correction and report_generation. Global progress retains window state, terminal counts, visual-pass counts, current window, all observations, critiques and proposed corrections. Merge is deterministic within each window; global collection deliberately retains window identity rather than silently deduplicating distinct window evidence. text_coverage separately records text pages selected, processed and remaining; each comprehensive request gets its current16-page text scope plus actual image pages/neighbors. The deterministic Markdown report includes actual source/coverage limits. Original observations remain beside machine recommendations and proposed rewrites; no expert verdict is created. Source/context or norm clipping degrades the corresponding procedure explicitly. Items outside a bounded norm/critic window and primary findings outside processed windows remain saved and labeled unreviewed.

## Image-only admission and canonical behavior

Only fresh v3 passes `allow_visual_only_pages=True` to the public background preparation handler. The existing full, bounded PDF interpretation/page-count checks remain; empty/encrypted/corrupt PDFs do not acquire a bypass. The flag admits valid pages with zero native characters and performs no OCR. Root's matching document-context handler permits a genuinely empty graph only for empty native text while preserving binding checks.

Before primary-text completion, the existing text stage holds an honest PARTIAL pending placeholder: typed primary_text_pending, primary_text_pending=true, no finished_at and no invented text finding. The final real text result replaces it and retains the extended artifact/metrics. primary_text_status then becomes completed, partial, failed or unavailable; pending is cleared. A real primary provider ambiguity prevents the entire postpass, while source-safe known text failures retain their actual result and do not invent publication. For image-only input, root's full empty-native artifact records observations=[], pages_analysed=[], model_calls_performed=0 and input_disposition=image_only_no_native_text. It passes through the normal grounding gate and terminal selector; there is no terminal bypass or fake model response.

## Durability and spending

All calls reuse the existing attempt authority, approved model/rate/connection, CostMeter, provider-effect journal and checksum-bound saved replies. Stable per-window phase keys and a global immutable input SHA distinguish requests. The global SHA excludes generated primary output, so the pre/post visual requests remain identical; post comprehensive requests still bind actual primary output in their own checksum.

Before a **fresh** v3 dispatch, the public bounded ambiguity guard refuses any prepared/received/unknown/abandoned effect anywhere in the Run. A verified saved response may be reused before that guard because it dispatches nothing. The executor also fences between visual pass and primary text and between primary text and postpass. Unknown outcomes stop subsequent paid work. Budget refusals stop remaining windows with explicit receipts. Saved final windows are reused, and unfinished visual windows continue into post-review rather than being treated as fully complete.

PNG and response publications use the existing durable publication store and actual artifact binding. The latest existing StageResult points to the review snapshot. Phase results affect final degradation; a successful text result cannot conceal a partial requested workflow. Actual receipt/call progress updates attempt liveness, while empty polling is not progress.

## Changed by this lane

- `src/auditmanager/runs/extended_review.py`
- `src/auditmanager/runs/executor.py`
- `src/auditmanager/analysis/extended/core.py`
- `src/auditmanager/analysis/extended/native_pages.py`
- `src/auditmanager/analysis/stages/source_preparation.py`
- `src/auditmanager/analysis/text/windowed.py` — explicit additional root ownership grant, only the fresh-v3 single-window custody flag
- This report.

PDF precheck parent/child required no edits: they already interpret valid textless PDF pages; the admission decision belonged to source_preparation. Root owns cost/public/bootstrap/document-context/empty-native seams. The other lanes own workflow/review/original-source assets and section rubrics/UI. This lane did not edit tests, fixtures, contracts, migrations, dependencies, global styles or Git refs.

## Integration and limits

Integrate with the root v3 authority/read/public helper changes and the two peer source lanes, preserving incoming owner UI changes. No execution was performed to establish runtime correctness; syntax, browser behavior, worker/DB/recovery behavior and live-provider quality remain unverified by explicit owner instruction. Do not claim a gate or beta acceptance. Publish only to the authorized dev ref; no main/deployment authority is granted.

This is bounded preliminary analysis, not a guarantee of complete project coverage, validated numeric/normative legality or expert approval. Source, norm and review bounds remain visible; OCR and automatic extra-window spending are absent. Original method provenance is PDF-proverka3c994817 and the peer lanes' copied source manifests; the original application's filesystem runner is not imported.

Integration addendum: preserve incoming v2 full_document/max_blocks="all" and historical16 behavior. Fresh v3 also plans every admitted image/page with actual source counts and MAXceil windows; all previous per-window context/critic limits remain explicit. Source receipt/report size grows with document scope; existing resource and Attempt ceilings remain. No checks on this combined merge.
