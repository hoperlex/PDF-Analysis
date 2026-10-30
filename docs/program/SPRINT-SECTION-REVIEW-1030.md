# SPRINT-SECTION-REVIEW-1030 — critique and correction lane

Source implementation prepared for fresh `extended-review-v3` section runs. Historical v1/v2 request builders and parsers retain their existing behavior. This lane adds genuine machine critique and targeted correction proposals; neither operation records an expert decision or replaces an original observation.

## Changed files

- `src/auditmanager/analysis/extended/workflow.py`: separate v3 comprehensive/norm builders, seven procedure descriptors, combined source bundle digest, bounded global collection helper.
- `src/auditmanager/analysis/extended/review.py`: bounded critic/corrector requests and closed, source-bound response parsers.
- `src/auditmanager/analysis/extended/original_review/__init__.py`.
- `src/auditmanager/analysis/extended/original_review/{models,normalize,rule_filter,scorer}.py`: copied pure original modules.
- `src/auditmanager/analysis/extended/original_review/prompts/{human_taxonomy.ru,quality_criteria}.md`: copied original prompt/criteria.
- `src/auditmanager/analysis/extended/original_review/{deterministic_critic,deterministic_corrector}.source.txt`: reference source, never imported.
- `src/auditmanager/analysis/extended/original_review/SOURCE.json`: exact original paths and copied-file SHA256 provenance.
- This report.

The task, runtime/core/native-page implementation, section resources, public wrappers, cost policy and UI are owned by the integrator or other named lanes. This lane did not edit them.

## Original procedures and adaptation

Original repository: `https://github.com/SU10KAZ/PDF-proverka`, commit `3c99481719218b9cfa7560886529916646c61939`. `SOURCE.json` records each original path and byte digest. Pure `critic_v2` normalization, rule filtering and usefulness scoring run as advisory structural signals in the critic/corrector input. They do not establish semantic truth or discard findings.

The original `critic_v2` human-taxonomy prompt was an offline/experimental component. The original current production structural critic/corrector were deterministic. The new path combines those genuine source materials with bounded model requests adapted to this application's source IDs, durable receipts and separate expert workflow; it does not claim identical production behavior or full original pipeline parity.

The critic returns one recommendation for every selected input: `accept`, `reject`, `borderline`, `needs_human` or `rewrite`, with the original human-rejection taxonomy, confidence, source dependency, evidence and correction intent. Rejection advice requires the supplied evidence, exact source quotes and the original confidence thresholds. A reason/decision contradiction, missing input, added input, changed source binding or fabricated quote is refused.

The corrector receives only inputs explicitly marked for correction. It can retain the original, request context or propose a separate revision. Every selected target must be accounted for exactly once. A proposal uses known source IDs and exact quotes; conservative number and identifier guards reject additions unsupported by those quotes or the preceding bound normative assessment. Original observations remain saved alongside the proposal. `expert_decision` is always false.

## Callable integration seams

The integrator's `analysis.public` wrappers forward to these local functions:

```python
workflow_procedures_v3()
review_bundle_digest(section)
build_comprehensive_request_v3(*, model_id, run_id, section, payload, window_id=None)
build_norm_review_request_v3(*, model_id, run_id, section, payload, window_id=None)
deterministic_lossless_merge_v3(items, *, max_windows=8)

build_critic_request(*, model_id, run_id, section, observations, sources,
                     window_id, context=None)
parse_critic_reply(text, *, observations, sources, allowed_sources=None, context=None)
build_corrector_request(*, model_id, run_id, section, observations, critiques,
                        sources, window_id, context=None)
parse_corrector_reply(text, *, observations, critiques, sources,
                      allowed_sources=None, context=None)
```

`observations` is a mapping from stable window input IDs to saved observations. Builders return the existing `ModelRequest`; empty critic input or absence of correction targets returns `None` and requires no call. `context.native_context` contains actual `{source_id,page_number,text,recognised_context?}` entries bound to the corresponding source. Parsers return annotations; the runtime attaches critique/correction metadata without applying a rewrite.

`review_bundle_digest(section)` combines actual bytes of `core.py`, `workflow.py`, `review.py`, `native_pages.py`, copied original assets and the selected section rules digest. The authoritative public name is `extended_review_bundle_digest(section)`. Fresh consent and the worker must compare this same combined value as `rules_sha256`; the section-only digest is an internal component. No model identity is substituted for the source bundle hash.

## Bounds and visible coverage

The v3 procedure descriptors are `block_analysis`, `comprehensive_analysis`, `finding_merge`, `norm_verification`, `finding_review`, `finding_correction`, `report_generation`. Canonical base stages remain separate. Runtime owns the approved two-pass order and durable per-window receipts.

The runtime policy permits up to eight windows of sixteen actual image sources, with at most six extra calls per window: two visual, comprehensive, normative review, critic and targeted corrector. Unneeded calls are not made. The runtime selects at most forty/16,000 characters of observations for each critic/norm window and retains other observations with explicit unreviewed reasons. The global collection helper accepts at most `8 * 160` observations, merges exact duplicate content only, unions metadata and retains every duplicate original; overflow is an explicit refusal rather than a hidden prefix.

The comprehensive request copy bounds descriptions to 800 characters, titles to 200 and source quotes to 800; each cut has explicit metadata and sets `context_coverage.truncated`. The caller's full observations and sources are unchanged. Native/recognised text has the existing explicit 48,000-character context bound. Critic/corrector text context and deduplicated normative context each have a 48,000-character bound, with omitted paragraphs/cuts recorded in coverage. Complete request bytes are bounded at 900,000; oversized input is refused. Critic/corrector output is bounded to 12,000 tokens each.

Critic/corrector requests use actual supplied text, normative assessment and previous visual results. They do not reattach pixels or claim another image inspection; the payload states `raw_images_reattached=false`. Any missing context remains an explicit machine limitation. Quote/numeric guards enforce binding, not the correctness of an engineering or legal conclusion.

## Static integration review and verification status

Static reads of runtime `_review_window_v3`, v3 window dispatch and `analysis.public` showed matching function names, keyword arguments, source/page context bindings and the no-correction `None` branch. The runtime owner was asked to project critic/corrector context truncation flags to a partial procedure result. This was a source review, not runtime verification.

**No tests, checks, lint, typecheck, build, compile, imports of implementation code, model calls, DB work, Git commands or fixture changes were performed for this sprint**, as explicitly required by the owner. No `PASS` is claimed. Copying source assets and recording their provenance hashes was implementation work, not an execution check. Runtime behavior and model output compatibility still require the deferred verification window.

## Integration and rollback

The integrator is the sole Git writer and publishes only to `origin/dev` under the integration task. No contract, migration, root lockfile, composition root or global style was changed by this lane. Fresh v3 policy is the behavior boundary: existing accepted v1/v2 runs keep their historical path. Disable fresh v3 starts or forward-revert its code to roll back; do not reinterpret historical receipts or rewrite expert decisions.
