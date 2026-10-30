# HOTFIX-AR-COMPREHENSIVE-1030 — core handoff

2026-10-30. Adds four genuine procedures inside the existing extended artifact: `block_analysis`, `comprehensive_analysis`, deterministic `finding_merge`, and `norm_verification`. These accompany the four canonical ordinary stages, producing eight visible work steps when the accepted v2 policy enables them. They are not fabricated canonical StageResults and do not establish parity with original critic/correction, authoritative norms status or unrestricted full-document analysis.

## Core/public seams

- `core.PLAN_VERSION_V2` and `workflow.WORKFLOW_V2`: `extended-review-v2`. `enabled` accepts exact v1/v2 policies with `enabled=true,max_blocks=16`; other block counts remain refused. V1 planning/result/hash shape is preserved.
- `workflow_procedures()` returns fresh `{id,title,status:'queued'}` objects for the four IDs above. Runtime owns transitions/reasons and durable receipts. V2 `plan_inputs` includes `workflow_version='extended-review-v2'` and these planned procedures.
- `plan_inputs(...,native_sources=None,plan_version='extended-review-v1')` accepts runtime's actual native-page helper dictionary only under v2. It preserves `native_*` identities, source type, published crop/digest facts, coverage/skipped/warnings and binds their actual metadata/hash into source identity. It does not manufacture a portal cohort. Page/neighbor native text and marked recognised context are attached as for existing image input. Plain-PDF raster publication/custody is runtime owner's responsibility.
- `build_comprehensive_request(*,model_id,run_id,section,payload)` performs a separate model request using actual `visual_observations`, `text_observations`, `sources` and `native_context:[{source_id,page_number,text,recognised_context?}]`. Native/recognised context shares a48,000-character bound; cuts are explicit in `context_coverage` and individual entries. Source-context duplicates cannot bypass that bound. Oversized total payload is refused, not silently dropped. Results use existing source-bound `parse_reply`/observation schema; no expert verdict is introduced.
- `deterministic_lossless_merge(items)` accepts up to160 incoming text/block/comprehensive observations. Only exact content matches with compatible noncollection fields collapse; source IDs, norm queries, candidates and input IDs are unioned. Complete original duplicate metadata remains in `merged_observations`. Different descriptions/unknown conflicting fields remain separate. No model call or semantic grouping is hidden in this procedure.
- `build_norm_review_request(*,model_id,run_id,section,payload)` makes a separate quote-review request with12,000 output tokens. `parse_norm_review(text,*,observations:{input_id:item},allowed_sources=None)` demands exactly one unchanged observation per input, exact source union and only its real corpus IDs/full supplied quotes. New queries, rewritten observations, missing/duplicate/foreign inputs and fabricated quotes are refused. Window max40 is explicit; runtime additionally bounds input size and retains overflow observations as unreviewed/partial.

Root exports the helpers through `analysis.public` as `extended_workflow_procedures`, `build_comprehensive_request`, `deterministic_extended_merge`, `build_norm_review_request`, `parse_norm_review`. Runtime owner is `roadmap_inventory`; UI owner is `c4_seal_plan`. This core lane does not edit those shared exports, runtime, UI, API, contracts or migrations.

## Original procedure provenance and limits

The comprehensive prompt adapts arithmetic, cross-sheet, specification/text and text-versus-visual tasks from `SU10KAZ/PDF-proverka` commit `3c99481719218b9cfa7560886529916646c61939`, `prompts/pipeline/ru/text_analysis_task.md` (SHA256 `1d410a212f7fbe22910cabe5e300f4e1f31f2b77a660a98aeb83c7553735755e`). This provenance is embedded in request metadata. Original filesystem/Read-tool/catalogue instructions, absence claims and legal-currency assertions are excluded. Only supplied source/context participates; output remains preliminary and needs expert review.

V2 budget is at most four additional model calls: two batches of at most8 images, one independent comprehensive crosscheck and one corpus-quote review. Deterministic merge costs no model call. Ordinary text calls are additional to those four. V1 accepted policy retains its old three-call extension. Context/page/block/normative windows and missing corpus remain explicit limitations; no hidden completion or full-original-parity claim follows from eight UI steps.

## Changed core paths and verification

- `src/auditmanager/analysis/extended/core.py`.
- New `src/auditmanager/analysis/extended/workflow.py`.
- New `tests/unit/analysis_extended/test_workflow_core.py`.
- This report.

Focused command: `.venv/bin/python -m pytest tests/unit/analysis_extended/test_core.py tests/unit/analysis_extended/test_workflow_core.py -q --tb=short`: **18 passed**. Helper compile PASS. Cases verify unchanged v1/strict v2 activation, genuine native sources without fake portal input, source identity changes, four independent planned procedures, actual visual/native comprehensive inputs and explicit48k cuts, foreign-source refusal,160-item lossless retention, exact normative partition/source/quote checks, mutation rejection and12k norm output bound.

No real model/provider call, DB/browser test, production mutation, full gate/build, contract/DDL change or Git operation was performed by this lane. Root alone integrates and publishes. Runtime/UI tests and integrated behavior are separate owner evidence.
