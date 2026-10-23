# Task AR-V3-ORIGINAL-TOPICS-01 — restore original AR topics in v3 prompt

task_id: AR-V3-ORIGINAL-TOPICS-01

## Outcome

The AR v3 draft prompt names the original AR review topics with immutable
provenance while leaving unsupported legacy thresholds and clause claims out.
The existing twelve-category response schema and selected canonical norm
paragraphs remain the only normative proposal inputs.

## Depends on

- `W56A-LEGACY-SOURCE-01` — completed six-file original manifest.
- `AR-ORIGINAL-CITATIONS-PLAN-01` — completed implementation map.
- `AR-V3-PROMPT-REDO-01` — completed at published dev `0261ca54`.

## Frozen inputs

- `origin/dev=9b4d682ac412deda4fd8b7b2b6881e891e1b7942` at start;
- original `/root/projects/PDF-proverka` at `16ba8e5d`, role SHA-256
  `fda944f74c4a0bd7cd77339f2c2f8519f55d59e899be03da212f93d2ad432203`,
  checklist SHA-256
  `eccb7879023a126427fd61a0ed36237eb42bbebd4bec63c4009004247d7f3179`;
- contract `1.0.0`, migration head `0031_executor_pull_channel`;
- W57 §A1/A3.3 excludes unverified legacy numbers and insolation as a
  normative category for this version.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the original role lists residential AR subject areas; the current
  v3 draft carries generic category policy but not that full topic coverage.

### P-01 — original and draft

- captured_at: 2026-10-23
- command: `sha256sum /root/projects/PDF-proverka/prompts/disciplines/AR/role.md /root/projects/PDF-proverka/prompts/disciplines/AR/checklist.md`
- captured_output:
  ```text
  fda944f74c4a0bd7cd77339f2c2f8519f55d59e899be03da212f93d2ad432203  /root/projects/PDF-proverka/prompts/disciplines/AR/role.md
  eccb7879023a126427fd61a0ed36237eb42bbebd4bec63c4009004247d7f3179  /root/projects/PDF-proverka/prompts/disciplines/AR/checklist.md
  ```
- interpretation: the legacy bytes are identified; their legal assertions
  still require independent current-source and applicability review.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/profiles/ar_v3/original_topics.md`
- `src/auditmanager/analysis/profiles/ar_v3/prompt_material.py`
- `tests/integration/analysis/test_ar_v3_prompt_material.py`
- `docs/program/tasks/AR-V3-ORIGINAL-TOPICS-01.md`
- `docs/program/AR-V3-ORIGINAL-TOPICS-01.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependencies/locks, v1/v2 prompt resources,
composition root, provider, served Run/API, norms storage, UI/global styles,
corpus, `origin/main`, release tags and deployment host.

## Non-goals

No verified normative map or edition, new category, copied legacy threshold,
live provider call, v3 activation or expert verdict.

## Deliverables and checks

One source-bound topic guide, fail-closed loading, focused provenance/prompt
tests, this task/report, compile, program governance, path proof and a
rechecked fast-forward development publication.

## Integration contract

The guide is draft model context only. Every normative observation still needs
a Run-pinned canonical set, exact N-label quote and local grounding; the guide
is never a source of normative values. A later PROFILE/CITE task owns runtime
activation and publication. Existing v1/v2 bytes remain unchanged.

## Rollback / feature flag

Forward revert this unserved prompt packet; no data or flag changes.
