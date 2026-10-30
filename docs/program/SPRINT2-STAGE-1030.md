# SPRINT2-STAGE-1030 — V3 parameters and source reports

UNVERIFIED source candidate for the second implementation hour. The experimental native-text stage-comparison path now prepares a structured parameter/source report and an interactive parameter table. This adds no model requests and changes no API or database schema.

## Changed files

- `src/auditmanager/comparison/stage_v3/report.py` — new deterministic projection over pinned native fragments, event/parameter provenance, complete source catalogue and page coverage.
- `src/auditmanager/comparison/stage_v3/procedures.py` — attach additive source/parameter annotations to experimental card metadata; preserve them when the existing card partition joins related events. Also retain attached numeric signs in the native-value lexical guard.
- `src/auditmanager/comparison/stage_v3/bridge.py` — save the complete deterministic source report with the final existing durable unit and include its digest in that unit's identity.
- `src/auditmanager/comparison/stage_v3/mode.py` — expose saved source-report data inside the existing `experimental_progress` object.
- `web/src/widgets/stage-v3-experimental/model/report.ts` — JSON, formula-protected CSV and escaped printable HTML formatting over all supplied saved V3 cards, sources and coverage.
- `web/src/widgets/stage-v3-experimental/model/xlsx.ts` — local technical OOXML workbook using the repository's pure ZIP/CRC32 writer.
- `web/src/widgets/stage-v3-experimental/ui/report.tsx` — report downloads, parameter search/table, saved verification counts, page coverage and source navigation.
- `web/src/widgets/stage-v3-experimental/ui/experimental.tsx` — per-parameter source details and readable existing coverage labels.
- `web/src/widgets/stage-v3-experimental/index.ts` — public report-component export.
- `web/src/widgets/stage-changes/ui/stage-changes.tsx` — mount the report using the existing complete authenticated card reader and existing PDF callback.
- This report. Additional widget paths were granted by the integrator in the sprint task.

## Visible result

Tab «Изменения проекта» contains «V3 · параметры и источники». It includes every saved V3 card returned by the existing authenticated `readCards` reader, which exhausts pagination. The table's search only affects the screen; downloads include all saved cards, including rejected/unverified cards and observations without structured parameters. Unsaved expert drafts are explicitly excluded. Existing expert editing/saving behavior is retained.

Each parameter keeps its original Miner values and the independent verifier values in separate fields/columns. `CONFIRMED` and `CORRECTED` remain machine-verification labels; neither becomes an expert act. The parameter's source section distinguishes event evidence from the sources actually cited by the verifier. PDF buttons call the existing authenticated navigation callback using a real `StageCardEvidence` anchor; no PDF URL is constructed. Missing anchors and stale cards disable navigation.

Freshly projected final results save every admitted pinned fragment in `experimental_progress.source_report.source_catalogue`, even when no event was found. Full saved native-fragment quotes, actual version/profile IDs, actual physical page numbers, fragment/page content keys and saved boxes are retained. Coverage rows distinguish page matching from actual procedure processing; they do not claim full engineering review. Source report and final-unit identity include deterministic source digests.

New parameter annotations are derived from actual saved event identity, ordinal, original parameter and event sources. They are report annotations inside `experimental`; no canonical API identity is invented. For historical cards without those annotations, IDs and full quotes are explicitly reported as unavailable rather than fabricated. Already terminal historical runs are not backfilled or sent to a model.

## Downloads

- XLSX is a genuine local ZIP/OOXML workbook with `Summary`, `Cards`, `Parameters`, `Sources`, `Coverage`, `RawJSONchunks`. Original and verified values are separate. All cells are literal inline strings, so model text cannot become a spreadsheet formula. Saved expert decisions have separate labelled columns. Long source quotes and card text are split into ordered 32,000-character parts; raw JSON is losslessly chunked. Overlarge cells/packages/row counts cause an explicit error rather than truncation. Package limit: 64 MiB.
- JSON includes the complete saved-card snapshot, source catalogue, source report/progress and coverage. Original values are unchanged.
- CSV contains every parameter or observation-without-parameters record and its source references. Formula-leading cells are protected as text; exact raw values remain in JSON. Complete source catalogue/coverage are in XLSX, JSON and HTML.
- HTML escapes model/source strings, contains no scripts or external PDF links, and can be printed by the browser to PDF. It includes parameter/source tables, page coverage, full catalogue and full saved JSON.

The OOXML/ZIP implementation is copied and adapted from this repository's `web/src/entities/audit-run/lib/extended-xlsx.ts`, as explicitly authorised by the integrator. Only the stage-specific tables and function arguments differ; the source attribution is in the copied module. There is no cross-entity private import or new dependency. Original V3 prompt/algorithm provenance remains in `stage_v3/original/SOURCE.json` at PDF-proverka commit `3c99481719218b9cfa7560886529916646c61939`.

## Source-value guard

The signed-number branch now preserves signs attached to a preceding label, such as `отметка-12,4`. It does not turn that source into a positive `12,4`. Existing standalone-operator rejection remains; a signed candidate after a numeric-ending token is rejected conservatively, so `-20` is not confirmed from range/subtraction `10-20`. Digits and decimal separators are retained. This is a lexical source-binding guard, not arithmetic or engineering confirmation; hyphenated identifiers and equivalent display notations can remain ambiguous and require expert review.

## Preserved limits and contracts

The experiment still admits at most sixteen native-text pages across both sides, 80,000 characters, 400 fragments, eight Mapper regions and the existing event/parameter budgets. No new paid procedure, prompt, model, request count or consent behavior was introduced; the paid prompt `BUNDLE` remains unchanged. The deterministic report has its own version and identity. Classic comparison, raw evidence and expert decisions remain intact.

The suggested expansion to sixty-four pages/240,000 characters/1,600 fragments was deliberately left unimplemented after static source review: shared `stage_ai.requests.make_plan` refuses encoded requests above 240,000 characters, so the native text alone would exceed it after block/ID/box metadata. Four unmatched batches of eight primary pages also cannot cover sixty-four all-unmatched pages. Honest expansion needs bounded/chunked Mapper semantics and fresh authority, not only larger constants.

API remains 1.14.0 and migration head 0043. Existing open experimental-object envelopes carry the additive metadata. No shared schema, migration, lockfile, composition root, global style, fixture or test file was changed.

## Verification and integration

Per the owner's instruction, **no tests, checks, lint, typecheck, build, compile/import execution, model calls, browser, DB, Git commands or fixture work were performed**. Only source reads and edits were used. No `PASS` is claimed. Runtime, Excel interoperability, browser downloads and numeric edge behavior remain unverified pending the deferred check window.

The integrator is the sole Git writer and publishes this source candidate only to `origin/dev`. No new mounting or bootstrap seam is required: the existing StageChanges screen mounts the new widget; existing final-unit persistence and run-reader metadata carry the source report. Rollback is a forward revert of these projection/UI changes. No extra model work is required to roll back or display an older saved card; historical missing metadata remains explicit.
