# V2-ORIGINAL-REVIEW-01 — plan v2 gains the original's deterministic critic and corrector

Owner rulings of 2026-11-10: R-154e (plan v2 is the original application's legacy flow, with executors split per stage), R-154f (v2 gains
the original's deterministic critic and corrector, without a model, as in the original's production, in this wave) and R-154g (under v2 the
«Критик» and «Уточнение» rows and the critic counters are not hidden: v2 now has a critic and a corrector, so they show real results).

"v3" below is the extended-review plan (`extended-review-v3`), the one that V3-OPTIN-01 made opt-in.

## What changed

A NEW v2 estimate freezes a policy marker, `original_review: "deterministic-v1"`. A v2 run accepted with it runs two more procedures after
the norm verification, `finding_review` («Критик наблюдений · правила оригинала, без модели») and `finding_correction` («Предложения по
уточнению · правила оригинала, без модели»). Both are deterministic: no model is called, no executor is needed, the cost does not move (the
estimate digest does, because the policy carries the marker). Their results appear where v3's do.

- `src/auditmanager/analysis/extended/original_deterministic.py` (new): the port. Checks 1 `evidence_presence`, 2 `block_exists` and
  4 `page_sheet_correct` of the original's critic, the verdict-to-advice table, and the corrector as proposals only. It is outside the files
  `workflow.review_bundle_digest` hashes, so v3's frozen `rules_sha256` is what it was (pinned by a test, see Checks).
- `src/auditmanager/analysis/public.py`: additive facade lines (`ORIGINAL_REVIEW_V2` and five functions). Granted by the integrator; the
  ALR-05 boundary lets `runs` reach the module only through this facade.
- `src/auditmanager/runs/preflight.py`: the v2 branch of `estimate_run` adds the marker. Nothing else of the file.
- `src/auditmanager/runs/extended_review.py`: wiring only. `_original_review_enabled` (exact marker; `strict` refuses an unknown word as
  `original_review_policy_invalid`), `planned_workflow_result` lists the two procedures and an `original_review` block for a marked policy,
  `run_extended_review` hands the v2 policy to `_run_workflow_v2`, which calls `_review_original_v2` after the norms. A defect in that step
  is a failed procedure (`original_review_failed`, the corrector then `dependency_failed`) and a warning; the paid results are kept.
- `src/auditmanager/runs/stage_facts.py`: a chip whose procedures all say `model_called: false` has an empty `plan` (no «модель прогона»
  line for a stage that called none).
- `src/auditmanager/runs/stage_layout.py` is unchanged: `rows_in_use` under v2 stays `text, blocks, cross_check, norms`; the critic and the
  corrector bind no cell.
- Web, `widgets/extended-review`, `entities/audit-run`, `widgets/run-stages-dialog`: see "What a person sees".

An accepted v2 consent WITHOUT the marker behaves as before: the same four procedures, no `original_review`, no `critic`, no
`review_status`, no `correction` on its observations (a test compares the two runs, request by request).

## The original, and what was ported

Pinned: PDF-proverka `3c994817` (`analysis/extended/original_review/SOURCE.json`).

- **The original's production runs the deterministic checks only.** `backend/app/pipeline/stages/findings_verify/runner.py:85-88` calls
  `run_deterministic_critic(output_dir, project_id=..., llm_call=None, ...)`, and the routing compiler says so in words
  (`backend/app/services/audit_routing/compiler.py:493` docstring, `:509` the action's note: «0 обращений к модели»). The best-effort model pass
  (checks 3 `evidence_relevance` and 5 `text_consistency`) is therefore **not built**. `docs/critic_corrector.md:63-65` lists a flag
  `FINDINGS_CRITIC_SEMANTIC_LLM` (default `true`); the flag exists nowhere in the code at that commit (`git grep` finds the doc only).
- The original's «Верификатор» also runs an LLM absence guard after the corrector (`findings_verify/runner.py`, `_run_absence_phase`). It is
  a model call and a different procedure; it is not part of this lane.
- **Tests.** At that commit the original has `tests/test_findings_deterministic_critic.py` (11 tests),
  `tests/test_findings_deterministic_corrector.py` (12 tests) and `tests/test_critic_semantic_unverified.py` (4 tests of the model pass). The
  first two are ported as fixtures in `tests/unit/analysis_extended/test_original_deterministic.py`: the same scenarios (no evidence, phantom
  block, tight and broad page evidence, a page list, no finding deleted, the corrector never changes the original, `pass` untouched, other
  fields kept, the critic-then-corrector round trip) over the shape of a v2 record instead of `03_findings.json`. The third has no counterpart,
  and a test pins that nothing here imports a provider, an adapter or a request builder.

### The data model differs: checks 1 and 2 are mostly guaranteed upstream, and check 4 is adapted

An observation of a v2 record is `title`, `description`, `source_ids` (plus the ids and norm fields the workflow adds) over a registry of
sources (`kind` `image` or `text`, `page_number`, for text a `quote`). The original's finding carries `evidence[]`, `related_block_ids`, a
`page` and a `sheet`, checked against `01_blocks_analysis.json` and `document_graph.json`.

- **Check 1** (`no_evidence`): the observation names no source in `source_ids` and no identifier in its title or description
  (`block_…`, `page_N_text`, the portal's `XXXX-XXXX-XXX`, the original's own pattern).
- **Check 2** (`phantom_block`): as the original, only when NONE of the named sources is in the record.
- **Checks 1 and 2 are already enforced upstream in v2.** The reply parser refuses a `source_ids` entry outside the allowed sources
  (`analysis/extended/core.py` `_parse_observations`) and `finalize_items` raises `KeyError` on an unknown id. On a fresh v2 record they can
  flag only a corrupted or legacy one. They are ported, and they run, so that the vocabulary and the record are the original's; they should not
  be expected to fire.
- **Check 4 is ADAPTED, not copied.** An observation here has no `page` or `sheet` of its own, so the original's comparison has nothing to
  compare. The one page claim in a v2 record is the page a *text* source states (the text analysis's own «evidence»: `page_number` and
  `quote`). The check asks whether that quotation is on that page of the text layer. Like the original it flags only a tight case:
  `page_mismatch` when the quotation is NOT on the stated page and IS on one or two other pages. It says nothing when the quotation is found
  nowhere (a paraphrase is the model pass's business, check 3), when it is shorter than 12 characters (too weak to place), when the stated
  page has no text, or for an image source. Whitespace and case are folded. **No sheet is judged:** a v2 record carries no sheet stamp.
  Comparing the page of a text source with the pages of image sources was considered and rejected: it would flag every cross-sheet check,
  which is what a comprehensive observation is for.
- The original's severity protection (critical and economic findings are flagged `requires_human_review` instead of downgraded) is not
  ported: v2 observations have no severity. Every verdict that is not `pass` becomes `needs_human` or `rewrite`, nothing is lowered.

## Verdict mapping

The critic writes the row v3's critic writes (`critic` on the observation, `review_status: "reviewed"` for every observation: there is no
window to leave one out), marked `mode: "deterministic"`, `model_called: false`, `original_verdict`, `failed_checks`, `checks`. It has no
`confidence` (`null`: a rule declares none) and `evidence_checked: false` (no model looked at a source). `expert_decision` is `false`, `status`
is `requires_expert_review`. The corrector writes the row v3's correction writes (`correction`, `original`, `candidate`, `action`). **No verdict
becomes `reject`** (no automatic cancellation, ADR-0027) and no observation, source or expert decision is changed (AGENTS section 4).

| Original verdict | Check | What the original's corrector did to the finding | `llm_decision` | `human_taxonomy_reason` | `source_dependency` | `needs_correction` | Correction row here (proposal beside the untouched original) |
|---|---|---|---|---|---|---|---|
| `pass` | none | nothing | `accept` | none | `enough_source` | false | none |
| `no_evidence` | 1 | critical or economic: `requires_human_review`, severity kept; otherwise severity lowered to «ПРОВЕРИТЬ ПО СМЕЖНЫМ» | `needs_human` | `insufficient_source_context` | `needs_more_context` | false | `needs_context`, no candidate, `required_context`: a source |
| `phantom_block` | 2 | drops the ids that do not exist; if no evidence is left, as `no_evidence` | `needs_human` | `insufficient_source_context` | `needs_more_context` | false | `needs_context`, no candidate (every named source is missing, so nothing is left to keep or propose) |
| `page_mismatch` | 4 | sets `page` and `sheet` from the evidence blocks | `rewrite` | none | `enough_source` | true, with `suggested_fix` | `propose_revision`: the original title and description plus one line «Уточнение страницы: цитата источника найдена на стр. N; в записи указана стр. M.», with the verbatim quotation as `source_evidence`; `needs_context` if the description would then exceed 3000 characters |
| `weak_evidence` | 3 (model) | keeps it, adds a note | `needs_human` | `insufficient_source_context` | `needs_more_context` | false | none. Never produced: the model pass is not built |
| `contradicts_text` | 5 (model) | as `no_evidence` | `needs_human` | none | `enough_source` | false | none. Never produced: the model pass is not built |

Reasons, in short, preferring the original's own meaning:

- `pass` is the original's «nothing to correct», and `accept` is v3's «keep»: the critic queue «Сохранить». It overstates nothing in the row
  itself, whose explanation says that only structure was checked and no model ran.
- A missing or missing-from-the-record source is what the original flags for a person (`requires_human_review`) or demotes, never deletes
  («ни одно замечание не удаляется»). v3's closest word is `needs_human`, «Нужна проверка человека»: not an approval and not a rejection.
- `page_mismatch` is the one verdict whose original action is a fix, so it is the one that becomes a proposed revision: the critic says
  `rewrite` (v3 requires `needs_correction` for `rewrite` and a `suggested_fix` for `needs_correction`), and the corrector offers the text.
- `human_taxonomy_reason` is the original's offline taxonomy; only `insufficient_source_context` means what the structural checks found. For
  `pass` and `page_mismatch` the field is empty, and the web and the exports print no «Основание» line for it.

## What a person sees

- Panel «Расширенный анализ» (the run screen's «Подробнее»): for a v2 record that carries `original_review` the paragraph that said critique
  and correction are not attributed to V2 is replaced by one that says they ran by the original's rules, without a model and without an
  executor, checked source presence, source existence and the page of the quotation, did not check meaning, and gives the counts. The counters
  «Рекомендации машинного критика» and «Предложенные исправленные кандидаты» show the real numbers. An older v2 record keeps today's text and
  its zero counters.
- The critic's queues and the card of an observation: the same tabs and filters; the notes under a tab and the card say «правила оригинала,
  без модели», print no declared confidence and no «источники просмотрены моделью».
- The run rail: the «Критик» and «Уточнение» tiles are drawn for such a record, as stages that call no model (the rail names no model for
  them, as it names none for «Свод»), with their real state.
- Report (MD, HTML), JSON and the technical XLSX: the heading says «по правилам оригинала, без модели»; no empty «Основание» or
  «Предложение» for a pass; `original_review` is in the metadata and the summary sheet.
- «Этапы анализа раздела» before a run: the dialog takes an optional `extendedPlan` (the readiness answer's `extended_plan`, contract 1.50.0,
  BE lane). Under `"v2"` the «Критик» and «Уточнение» stages read `без модели (правила оригинала)` in the list; with the field absent, `null`
  or `"v3"` the dialog is what it was. **The caller `widgets/run-list/ui/start-run-with-readiness.tsx` does not pass the field yet** (it is
  outside this lane's grant): the integrator adds `extendedPlan={readiness.extended_plan}` after the regenerated client lands.

## Checks

Commands run under `flock .local/evidence/exec2-d292/host-run.lock`, one locked command each; logs are in
`.local/evidence/lane-V2-ORIGINAL-REVIEW-01/` (git-ignored). Code tree `f11bfc03d` (tree `e4d3dbc27`); the Python run below was made on
`96b4f7879` (tree `56cd96344`), which differs from it in two web files only (`git diff --stat 96b4f7879 f11bfc03d -- src tests/unit tests/contract` is empty).

- Python, run 1 (`run1.log`): `.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider
  tests/unit/analysis_extended/test_original_deterministic.py tests/unit/analysis_extended/test_original_review_runtime.py
  tests/unit/runs/test_cost_preflight.py tests/contract/architecture/test_alr05_boundaries.py` gave 74 passed and 5 failed. All five were this
  lane's own defects, fixed before run 2: a real one (a `source_ids` that is not a list made `list()` raise; `_listed` now reads it as empty and
  the observation is `no_evidence`), two wrong fixtures (an id too short for the original's `XXXX-XXXX-XXX` pattern; a docstring that contained
  `llm_call`) and two wrong expectations (a call count and a norm status that depend on a primary text observation).
- Python, run 2 (`run2.log`), the same command over `tests/unit/analysis_extended/{test_original_deterministic,test_original_review_runtime,
  test_workflow_runtime,test_workflow_core,test_core,test_runtime}.py`, `tests/unit/runs/{test_cost_preflight,test_stage_plan_consent,
  test_stage_facts,test_stage_facts_ensemble,test_stage_layout,test_cost_policy}.py`, `tests/contract/test_compose_flag_forwarding.py` and
  `tests/contract/architecture/test_alr05_boundaries.py`: **305 passed in 12.02 s.** They include the v2 tests listed in
  `docs/program/V3-OPTIN-01.md` that this change can reach.
- Web, `web/`: `npx tsc --noEmit -p .` exit 0 and `npx eslint` over the ten touched source files and the new test exit 0 (`web1.log`).
  `npx vitest run --maxWorkers=1 tests/unit/analysis-extended tests/unit/run/run-chips.test.ts tests/unit/run/run-stages-dialog.test.ts
  tests/unit/start-run/readiness.test.ts tests/guards/stage-dictionary.guard.test.ts`: 7 files, **119 passed** (`final.log`; the new
  `original-review.test.ts` has 12 tests). `tests/unit/screens/run-screen.test.ts` with `tests/guards/rendered-language.guard.test.ts`: 2 files,
  **76 passed** in 305 s (`web4.log`; run before the last wording edit of the count line, which only changes one sentence of the panel note
  and the new test's expectation of it, both covered by `final.log`). A first attempt to run all of these in one vitest command ended with
  `Channel closed` (a tinypool worker lost while the host had about 180 MB free) and gave no result; it was split and rerun as above.
- Mutation check of the digest pin (`final.log`): at the base the pin holds (`review_bundle_digest("AR")` is `6696fb2e…630`); a probe file
  added under `original_review/` moves it, and removing it restores it. So `test_v3_bundle_digest_is_what_it_was_before_the_original_review_was_added`
  can fail, and the second test (`test_the_new_module_is_outside_the_files_the_bundle_digest_hashes`) names the reason.
- Other guards that can fail: the page and verdict tests (each scenario of the original has its fixture and its opposite); the no-model test
  reads the module's imports (`{__future__, copy, re, core}`) and fails on any provider, adapter or request builder; the provenance test
  compares the pinned hashes and paths with `original_review/SOURCE.json`; the marker test compares the estimate's marker with the facade's
  and the digest with and without it.
- Preview, `v2-review-preview/` in the wave's folder under the git-ignored `.local/evidence/` (dated 2026-11-10): `preview.png` (the sheet), the 24 full-page shots
  `{panel,rail,plan}-{before,after}-{light,dark}-{1280,390}.png`, `facts.json` (DOM facts per shot) and the two records the page was drawn
  from (`reading-before.json`, `reading-after.json`, the lane's own module's output over a five-observation sample; `tools/` rebuilds it with
  `tools/run-preview.sh`). Facts: no horizontal overflow in any of the 24; the «after» panel has the note, six procedures, counters 5 / 5 / 1,
  five cards in `data-machine-mode="deterministic"`, tabs «Сохранить 2 / 2», «Нужен человек 2 / 2», «Уточнить 1 / 1», and no model-confidence
  or «источники просмотрены моделью» line; the rail adds «Критик» and «Уточнение» tiles with no model line, and the plan window reads
  `без модели (правила оригинала)` for those two stages under `extendedPlan: 'v2'`. Images were not opened by the lane; the facts are the DOM's.
- Docs: `git diff --check` is clean; `tests/contract/api_v1/test_surface_counts_in_prose.py`, `test_doc_prose_facts.py` and
  `tests/contract/program/test_wave_governance.py`: 94 passed in 73 s (`docs-guards.log`).
- Not run: DB-backed integration tests (no Postgres in this lane), the browser journey and the full `npm test`. No test carries a v2 consent
  with the marker through start, freeze, worker and publication.

## Risks and limits

- Checks 1 and 2 will rarely fire on fresh v2 data (above). The critic is mostly `accept` plus the occasional `page_mismatch`; it does not
  judge meaning. The queue «Сохранить» therefore means «no structural problem», and the card says so.
- Check 4 is this lane's adaptation (above); it is deterministic and conservative, but a stated page is only the text analysis's claim. A
  quotation that was altered by the model and a quotation that really is on two pages are both silent.
- The page note of a `propose_revision` is the only text the corrector proposes, and it is not checked by the v3 corrector's «no new numbers»
  parser: the page numbers come from the text layer, and the verbatim quotation is attached.
- The two procedures add one artifact save each (`phase`) and one `critic` and at most one `correction` row per observation to the
  `analysis.extended_review` artifact; a large v2 document (thousands of observations) grows the artifact by roughly 1.5 KB per observation.
- The logic is in `analysis/extended/original_deterministic.py` and **must stay outside** `original_review/` and the eight files
  `review_bundle_digest` names; moving it there would change v3's `rules_sha256` and invalidate accepted v3 consents (a test says so).
- «Модели по этапам» still shows all six rows (open owner question since V3-OPTIN-01); only the pre-run window learns the plan, through the
  integrator's caller change.
- Rollback: revert the lane. A consent accepted with the marker is then read by code that ignores the unknown key: its result has the four
  procedures, as a consent without it has.
- Not covered: no DB-backed or executor-level test carries a v2 consent with the marker through start, freeze, worker and publication (the same
  gap `V3-OPTIN-01` reported for v2); the worker path is tested at `run_extended_review`.

## Integrator

- Merge conflicts to expect: `analysis/public.py` (additive lines at the end of the file; the BE lane edits the file elsewhere),
  `run-chips.ts` and `stage-dictionary.ts` neighbours (the web removal lane edits the chip lines around them; this lane touches `runChips`'s `chips.push`
  only).
- Pass `extendedPlan` from the readiness answer to `PlanStagesDialog` in `start-run-with-readiness.tsx`.
- No contract, no migration, no `VERSION` bump here. Release note line for the integrator: «Анализ раздела, план V2: после нормативной проверки
  работают критик и уточнение по правилам оригинала, без модели; результаты видны в «Подробнее» и в выгрузках.»
