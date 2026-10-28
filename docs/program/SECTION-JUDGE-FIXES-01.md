# SECTION-JUDGE-FIXES-01 — the fixes for the independent judge J2's findings on the section-analysis path

Task: `docs/program/tasks/SECTION-JUDGE-FIXES-01.md`. Branch `agent/section-judge-fixes-01`, base `93bc5037` (`integration/ar-close-1026`). Source of the findings: the read-only judge J2's review of the section-analysis path at `93bc5037` (omission check, spelling, prompts, scans, budget). Accepted risks `A-5`, `A-7` stand.

**Nothing below was run against a model, and `reviewed` still carries no human review (`R-146ag`, `A-7`).** Every prompt sentence and every test text is the lane's own wording; what a model reports with the corrected check, and how often the stricter check refuses a true omission, is unmeasured (`A-5`).

## Result

| # | Finding (judge) | Severity | State | What exists |
| --- | --- | --- | --- | --- |
| 1 | The omission check proved an absence only for the range the model chose | MED | **fixed** | the term must be absent from every page the model was shown except the pages of the naming quote (`term_on_other_visible_page`); a claim ending on the last page of a window that is not the last is refused (`range_reaches_window_end`); the appended sentence names the pages searched |
| 2 | The presence test missed spellings | MED | **fixed** | `fold` reads Latin look-alikes of Cyrillic letters, the decimal comma, the separators of a mark, the diameter sign, combining and zero-width characters, the multiplication sign and the Roman numeral one; a table-driven test over the judge's list and negative controls |
| 3 | Three prompt sentences contradicted the schema | MED | **fixed** | `AI TX EOM SS ITP` say two categories for the checks above and `documentation` only for the omission paragraph; `profile_version` `1.3.1`; five recordings rebuilt; three present and three absent fragments added to the sentence-guard table through its builder |
| 4 | `decide` knew neither the version's text-less pages nor the recognised text | MED | **fixed** | both are passed in (`stage`, `windowed`, the executor's two call sites); `range_page_textless` and `term_in_recognised_text` |
| 5 | The budget reserved the АР bundle's 3,639 characters for every run | LOW | **fixed for the window policy**; the start-time check is **not** changed (outside the lane's paths) | `input_budget_characters(..., bundle=)`, `text_window_policy(..., bundle=)`, the executor passes the profile's bundle |
| 6 | (optional) a finding text may claim absence from the project | LOW | **done** (a few lines) | `finding_text_overclaims` |

## Finding 1 — the range the model chose is not the whole schedule

**What was wrong.** `decide` searched the text of the claimed range only. The judge's reproduction (Appendix A): a term named on page 1, the schedule's heading on page 3, the schedule continuing on page 4 with the term. The claim «pages 3 to 3» with `visible=(1, 3)` was published as «не найдена в текстовом слое на странице 3». The sentence was true of page 3 and misleading about the schedule.

**The fix** (`omission.py`, `decide`):

- the term must not occur, in any of the ways `occurs` reads, on any page of the call or window **other than the pages of the naming quote(s)** — pages before the range, between the naming page and the range, and after it; the searched pages are tried in order, so a term broken between the range and the next page is found too. New closed reason `term_on_other_visible_page`, checked after `term_present_in_range`;
- a claim whose `last_page` equals the window's last page, when that window is not the last one (`visible[1] <` the document's last page), is refused: `range_reaches_window_end`. The page after the range is the sentinel: a claim that ends before the window end is published only if the visible page after it is clean;
- the sentence names exactly what was searched (`note_for`): «…не найдена в текстовом слое на странице 3 и на остальных страницах 2, 4–5, которые видела модель (кроме страницы 1, где запись названа); сравнение без учёта регистра, тире, пробелов и сходных по начертанию букв; другие написания не проверялись.» With nothing else searched, the clause about other pages is left out.

**Failing first.** `tests/unit/analysis/test_omission_judge_fixes.py` against the unmodified source: **21 failed, 3 passed** — among them `test_the_judges_reproduction_is_not_published_in_one_call` (published; expected `term_on_other_visible_page`) and `…_from_the_first_of_two_windows` (published; expected `range_reaches_window_end`). The stage-level cases (`tests/integration/sections/test_section_omission_judge_fixes.py`) drive the judge's reproduction through `run_text_analysis` and through `run_text_analysis_windows` with two real windows.

**Mutations** — J1a to J1g in the table below, all red.

**Limits.** (a) The symmetric case is not handled: a claim that *starts* on the first page of a window that is not the first (a continuation heading) says nothing about the pages before the window; the sentence says exactly which pages were searched, and the claim stays true of them. (b) The pages of the naming quote are exempt, so a second mention of the term elsewhere on the naming page is not a presence. (c) A visible page outside the range that has no text and no recognised text cannot be searched, and is not made a refusal (it would refuse every omission in a document that has any scan).

## Finding 2 — the spellings

**What was wrong.** At the base every one of the judge's pairs was *not* a presence: `ВК-1`/`BK-1`, `ВРУ-1`/`BPY-1`, `3х2,5`/`3x2,5`, `3х2,5`/`3х2.5`, `Г-3`/`Г.3`, `Ø20`/`Ф20`, `ЩО-1` with a combining accent, `ЩО-1`/`ЩО-I` (Appendix A prints six of them). Each is a false «не найдена».

**The fix** (`omission.py`, `fold` and the loose view of `occurs`; the rule stays «presence wins», a fold can only add presences):

| Spelling | Reading |
| --- | --- |
| Latin `a b c e h k m o p t x y` (after case folding) | the Cyrillic `а в с е н к м о р т х у` |
| `×`, `*` | `х` (the cable mark `3х2,5`) |
| `ø ⌀ ∅ φ ϕ ɸ` | `ф` (the diameter sign: `Ø20`, `Ф20`) |
| Latin `i`, `l`, Cyrillic `і`, `ӏ`, dotless `ı`, and the Roman numeral sign `Ⅰ` (by compatibility decomposition) | `1` — **decided: fold I and l to 1.** A mark's «1» is written `I` or `l` in the wild, a presence is the safe error, and the price is that every Latin `i` and `l` reads as `1` on both sides of the comparison |
| a decimal comma between two digits | a point |
| the separators of a mark: hyphen, point, comma, slash, underscore, bar, middle dot, every kind of whitespace | removed in the loose view, so `Г-3`, `Г.3`, `Г 3`, `Г/3` and a mark broken over two table cells with only whitespace or a bar between the halves are one string |
| combining marks, zero-width and soft-hyphen characters | dropped (so `ё` reads as `е` and `й` as `и`) |
| compatibility forms: full-width, ligatures, superscripts, non-breaking spaces | decomposed (NFKD) |

The separate hyphenation view was removed: the loose view already joins a word hyphenated at a line end and no test could make the other fail (a mutation of it survived: an equivalent mutant); one test for the hyphenated word stands in its place.

**Failing first.** `tests/unit/analysis/test_omission_spelling.py` against the unmodified source: **54 failed, 24 passed** (the 24 are the negative controls and the spellings the old fold already read). The table has 37 pairs, each tried in both directions, the 24 look-alike letters one by one, and 15 pairs of *different* designations that must stay different (`ВК-1`/`ВК-2`, `Ø20`/`Ф25`, `ЩО-1`/`ЩО-2`, …).

**Mutations** — S1 to S13, all red (S9 and S10 are over-fold mutations: digits as separators, every Latin letter as `ф`; the negative controls turn red).

**Limits, stated once.** A mark split across table cells with the text of **other cells between the halves** (`ВК-` in one cell, `1` in another, a third cell between them in the extractor's reading order) is not found: it needs the table's structure, and a looser test would call every `ВК` followed anywhere by a `1` a presence. The letter `О` and the digit `0`, `З` and `3`, Greek capitals other than `φ`, and Roman numerals above one are not folded (`II` reads as `11`, which contains `1`: a presence). A term is a substring test: `Д-5` is present in `Д-50`. The fold costs a decomposition and a translation of every searched page for every omission proposal (milliseconds a page).

## Finding 3 — the prompts

**What was wrong.** The five prompts still said «Ровно две категории, третьей нет:» (line 12), «…сообщай только то, что подпадает под одну из двух категорий выше:» (line 20) and «category — строго одно из двух значений выше.» (94, 132, 114, 139, 135), while the paragraph the previous lane inserted after condition 5 and the schema both allow `documentation`.

**The fix.** Three sentences in each of `AI TX EOM SS ITP`, now:

- «Для вопроса выше — ровно две категории; третья, documentation, допустима только для пропуска из абзаца об исключении ниже:»
- «…по этим подсказкам сообщай только то, что подпадает под одну из двух категорий выше (documentation — только для пропуска из абзаца об исключении ниже):»
- «- category — одно из двух значений выше; documentation — только для пропуска из абзаца об исключении, и ни для чего другого.»

The three new sentences are `present` fragments and the three old ones `absent` fragments of the five sections in the sentence-guard table, **written to the table by its builder** from the block below (`build_section_prompt_fragments.py --write`; the builder gained the source key `J1`); the table went from 124 to 130 fragments. `profile_version` of the five is `1.3.1` in `profile.json` and in the expectations file; the five recordings were rebuilt by `fixtures/recorded/sections/build_fixtures.py` (the old five files are gone, `--check` prints `fixtures match`); the nine other prompts, packages and recordings are byte-identical. `build_specimens.py --check` prints `specimens match`: its files do not depend on the prompt.

Token guard: the delta of designations (whole tokens that carry a digit, a Latin letter, two capitals or a hyphenated code) of each of the five prompts against the base is **empty** — nothing added, nothing removed (`documentation` was already there and is sourced by the previous lane); the ten new whole tokens are ordinary Cyrillic words. The guard's sourced part needs the legacy repository and skips on this host, with its reason.

<!-- fragments:begin -->
```json
[
 {
  "id": "J-INTRO",
  "sections": [
   "AI",
   "TX",
   "EOM",
   "SS",
   "ITP"
  ],
  "role": "category list: two categories for the question above, documentation only for the omission paragraph",
  "text": "Для вопроса выше — ровно две категории; третья, documentation, допустима только для пропуска из абзаца об исключении ниже:"
 },
 {
  "id": "J-HINT",
  "sections": [
   "AI",
   "TX",
   "EOM",
   "SS",
   "ITP"
  ],
  "role": "checklist hint: the two categories for the hints, documentation only for the omission paragraph",
  "text": "по этим подсказкам сообщай только то, что подпадает под одну из двух категорий выше (documentation — только для пропуска из абзаца об исключении ниже):"
 },
 {
  "id": "J-CATEGORY",
  "sections": [
   "AI",
   "TX",
   "EOM",
   "SS",
   "ITP"
  ],
  "role": "reply rule: the category value, documentation for the omission paragraph and nothing else",
  "text": "- category — одно из двух значений выше; documentation — только для пропуска из абзаца об исключении, и ни для чего другого."
 },
 {
  "id": "J-OLD-INTRO",
  "sections": [
   "AI",
   "TX",
   "EOM",
   "SS",
   "ITP"
  ],
  "kind": "absent",
  "role": "removed: «exactly two categories, there is no third» contradicted the schema that allows documentation",
  "text": "Ровно две категории, третьей нет:"
 },
 {
  "id": "J-OLD-HINT",
  "sections": [
   "AI",
   "TX",
   "EOM",
   "SS",
   "ITP"
  ],
  "kind": "absent",
  "role": "removed: «report only one of the two categories above» left no room for the omission paragraph",
  "text": "сообщай только то, что подпадает под одну из двух категорий выше:"
 },
 {
  "id": "J-OLD-CATEGORY",
  "sections": [
   "AI",
   "TX",
   "EOM",
   "SS",
   "ITP"
  ],
  "kind": "absent",
  "role": "removed: «category is strictly one of the two values above» contradicted the schema that allows documentation",
  "text": "- category — строго одно из двух значений выше."
 }
]
```
<!-- fragments:end -->

**Failing first.** The three old sentences are `absent` entries and the three new ones `present`: against the unmodified prompts the table check reports the new sentences missing and the old ones back; after the edit the table, the v1-skeleton test and the recordings agree.

**Mutations** — P1 to P9 and the stale recording, all red.

**Limits.** The wording is the lane's own (`A-5`, `A-7`). The guards see that a sentence stands, not that it is right.

## Finding 4 — scans

**What was wrong.** `decide` received neither the version's `textless_pages` nor the recognised (OCR) pages, although the executor holds both: a range page the version stores as text-less, or a term that the OCR of a searched page shows, could not stop the pair. The text layer's own count of 50 characters was the only protection.

**The fix.** `decide(..., textless_pages=None, recognised=())`: a range page in the version's list refuses the pair (`range_page_textless`, checked before the character count); the term in the recognised text of a **searched page** refuses it (`term_in_recognised_text`, last). `run_text_analysis` and `run_text_analysis_windows` take `textless_pages` and pass it, with the recognised pages they already had, to `decide` (single call, windows, and the one-window delegation); the executor passes `textless_pages` at its two call sites. The sentence names the pages whose recognised text was searched.

**A deliberate widening of the brief:** the brief names «the OCR text of a range page»; the lane applies it to **every searched page** (the range and the other visible pages except the naming pages), exactly as finding 1 does for the text layer: a scan that continues the schedule outside the claimed range is the same exposure. This changed one existing control (below).

**Failing first.** The new cases pass keywords that did not exist: against the base they fail with `TypeError: decide() got an unexpected keyword argument` (the interface is the change), so the proof that they bite is behavioural, in the mutation rows J4a to J4d and W1 to W7 (each call that hands the two inputs on is removed in turn, including the executor's single-call and windowed sites and the one-window delegation).

**Limits.** A text-less visible page outside the range with no recognised text is not searched (see finding 1). Recognised text is context, not evidence: it can only refuse a pair, never publish one.

## Finding 5 — the budget

**What was wrong.** `budget._fixed_prompt_characters()` read the АР v1 bundle (3,639 characters, system prompt plus schema) for every run. The section system prompts plus their schemas run from 7,163 (ПБ) to 11,832 (СС) characters at the base (task file P-06). The one-call figure was too large by up to 8.2 thousand characters, so a volume the figure admitted in one call could come out over the per-run cost ceiling (the ceiling still halts the run *after* the call that crosses it).

**The fix.** `input_budget_characters(model_id, ceiling_usd, reserved=0, *, lock=None, bundle=None)`: with a bundle it subtracts **that** bundle's system prompt and schema and prices **its** output cap (all 14 are 16,000, the АР bundle's value); with none it is the figure it always was — the start-up check (`bootstrap/settings`), `startRun` through the connection route's freezer and the AR v3 path pass none and are untouched. `text_window_policy(..., bundle=None)` passes it on; the executor passes `profile.prompt_bundle`. A window is never larger than the run's own one-call figure.

**The invariant the tests hold:** for every one of the 14 profiles, `fixed(section) + budget(section) == fixed(АР) + budget(АР)` (the request's total characters stay at the calibrated figure); the figure is also derived a second time from the prompt files and the lock's JSON, so an arithmetic slip is a disagreement. At the primary model and the lock's ceiling of 1.00 USD the figures are: АР 152,361; ПБ 148,837; СС 143,914 (the smallest: after this lane's three rewordings СС reserves 12,086 characters, 8,447 more than the АР bundle).

**The boundary that moves.** A volume whose recorded count is in (section figure, АР figure] used to be sent whole and is now windowed into windows of the section figure. For СС that is (143,914 .. 152,361]: a count exactly at the old limit (152,361) is windowed, a count exactly at СС's own figure is still one call, one more is windowed (`test_a_section_run_is_windowed_from_its_own_figure_and_the_boundary_moves_down_by_the_difference`, and the same through the executor: `test_the_executor_plans_the_run_with_its_own_prompt_bundle`). A call with no bundle is unchanged: the AR path's boundary does not move.

**Not done: the start-time check.** `runs/commands.py` (`startRun`, `reauditRun`) refuses a version above `12 × input_budget_characters`, with the figure the deployment passes in: one number per deployment, computed from the АР bundle, with no section known where it is computed (`bootstrap/settings`, the connection route's freezer in `bootstrap/providers.py`). Making it per section needs a table of fixed lengths per bundle id through the composition root (`bootstrap/**`), which the brief forbids. Consequence, bounded and explicit: a version whose count lies in (12 × section figure, 12 × АР figure] — for СС 12 × 8,447 = 101,364 characters wide, from 1,726,968 to 1,828,332, the top 5.5 % of the range, volumes near the upload envelope's 500 pages — is accepted at start and refused by the window plan with `window_plan_over_limit` (both figures in the message) **before any call**: no spend. Follow-up: a fixed-length table per bundle id through the composition root and `_refuse_over_window_budget(character_count, budget_for_bundle)`.

**Failing first.** The new file (35 cases) fails against the base with `TypeError` for the `bundle` keyword, as finding 4's. **Mutations** — B1 to B6, all red (B1 ignores the bundle, B2 forgets the schema, B3 prices the АР output cap, B4 and B5 drop the keyword at `text_window_policy` and at the executor, B6 counts the schema twice).

## Finding 6 — the model's sentence must not claim more than the check proved

**What was wrong.** The check proves a literal term absent from a text layer, not an item absent from a project. The prompt tells the model not to write «нет в проекте» or «обязательно», but nothing checked it.

**The fix.** `decide` refuses a pair whose `finding_text`, case-folded, matches `нет\s+в\s+проекте|не\s+предусмотрен|обязательн` (`finding_text_overclaims`, after the naming-quote check). Six cases fail the old code (a pair with such a sentence was published) and a neutral two-places sentence still passes. Mutations J6a to J6e (each stem removed in turn, the check removed, the case fold removed): all red. **Limit:** only `finding_text` is read, not `recommendation_text`; the stems are the three the brief names, and a synonym passes.

## Modified tests — what each asserted before and after (none is weaker)

| Test | Before | After |
| --- | --- | --- |
| `tests/unit/analysis/test_omission_check.py::test_the_sentence_says_what_was_verified_and_what_was_not` | the exact sentence for pages 2–2 ended «(буквальное совпадение без учёта регистра); другие написания не проверялись.»; «на страницах 2–4» for 2–4 | the exact new sentence for the same call («…на странице 2; сравнение без учёта регистра, тире, пробелов и сходных по начертанию букв; другие написания не проверялись.»); the 2–4 check unchanged; the variants with other pages, naming pages and recognised pages are in the new file |
| `…::test_yo_reads_as_ye_and_compatibility_forms_fold` | `fold("ﬁlter") == "filter"` | `fold("ﬁlter") == fold("filter") != "ﬁlter"`: the fold now also reads Latin look-alikes, so the string is no longer `filter`; removing the compatibility decomposition still turns it red (mutation S8) |
| `…::test_the_term_outside_the_range_is_no_presence` → `…_is_no_presence_in_the_range_but_is_on_a_page_the_model_saw` | page 3 holds the term, the range is 2–2: **published** («page 3 is not in the range 2-2»); range 2–3: `term_present_in_range` | the first case is the judge's defect and is **flipped by design**: `term_on_other_visible_page`; the second assertion is unchanged |
| `…::test_in_a_windowed_run_the_range_must_lie_inside_the_window` | four assertions: (1,3) published for 2–3; (1,2) `range_outside_window` for 2–3; **(1,2) published for 2–2**; (3,3) `range_outside_window` | three of the four unchanged; the third is flipped by design to `range_reaches_window_end` and moved into the new `test_a_claim_may_end_before_the_window_end_but_not_on_it_unless_it_is_the_last_window`, which also asserts published for (1,3) with 2–2 (the claim ends before the window end) and for the last window ending on its last page |
| `…::test_the_reasons_are_the_closed_vocabulary_the_stage_counts` | the exact tuple of 7 reasons | the exact tuple of 12, in the order the checks run |
| `…::test_the_registry_serves_three_categories_to_exactly_the_five_and_two_to_the_rest` | `profile_version == "1.3.0"` for the five | `"1.3.1"` |
| `tests/integration/analysis_text/test_recognised_context.py::test_the_same_pair_is_published_once_its_range_is_text_layer_text` | the pair (range page 3) was published with a scan on page 2 whose OCR names the term («щит ЩО-3 в спецификации не указан») | **data changed, flagged**: the control keeps its meaning with a scan that does not name the term (published, and the sentence says the OCR of page 2 was searched); the original scan now makes the pair `term_in_recognised_text` — the widening of finding 4 |
| `tests/integration/sections/test_section_omission_over_db.py` | premise: the term is absent from page 8; sentence `note_for(TERM, 8, 8)` | premise: the term is on the naming page **only** (stronger); sentence `note_for(TERM, 8, 8, others=(1, 3, 4, 5, 6, 7), naming_pages=(2,))` |
| `tests/unit/analysis/text_profiles/test_text_profile_packages.py::test_every_system_prompt_keeps_the_v1_question_categories_and_output_contract` | all 14 prompts contain v1's category block and end with v1's output contract, byte for byte | the nine prompts that do not declare `documentation`: unchanged; the five that do contain the same blocks with exactly the two rewritten lines (`OMISSION_INTRO`, `OMISSION_CATEGORY_RULE`), the old lines being absent; the guard-of-the-guard test asserts both replacements change the v1 text |
| `tests/unit/analysis/text_profiles/test_section_prompt_fragments.py` | five sources; counts of the four lanes; five-section coverage of the omission paragraph | six sources; the new counts `(6, 30)`; the three new sentences stand and the three old ones are gone in exactly the same five sections |
| `tests/unit/analysis/text_profiles/section_profile_expectations.json` | `AI TX EOM SS ITP` at `1.3.0` | `1.3.1` (data read by four tests and by `web/tests/unit/analysis-settings`) |
| `tests/unit/analysis/text_profiles/build_section_prompt_fragments.py`, `section_prompt_fragments.json` | four sources; 124 fragments | five sources (`J1`); 130 fragments, rewritten by the builder |

Recordings: the files of `ai`, `tx`, `eom`, `ss`, `itp` are renamed to the keys of the new requests by `build_fixtures.py` (the old five removed); the nine others are unchanged.

## Files

| Group | Files |
| --- | --- |
| Source | `analysis/text/{omission,stage,windowed,budget,windows}.py`; `runs/executor.py` (the two call sites of the stage and the window decision) |
| Packages | `analysis/text/profiles/{ai,tx,eom,ss,itp}/{profile.json,system_prompt.md}` |
| Recordings | `fixtures/recorded/sections/{ai,tx,eom,ss,itp}/<key>.json` |
| New tests | `tests/unit/analysis/test_omission_judge_fixes.py` (24), `test_omission_spelling.py` (79); `tests/integration/sections/test_section_omission_judge_fixes.py` (18); `tests/integration/analysis_text/test_section_input_budget.py` (35) |
| Edited tests and data | see «Modified tests» |
| Documents | this file and `docs/program/tasks/SECTION-JUDGE-FIXES-01.md` |

## Mutation table

Each mutation is one exact replacement in a committed file, applied to the worktree; the named tests are run (the omission files for findings 1, 2, 4 and 6; the profile, recording and package tests for finding 3; the budget and window tests for finding 5); the file is restored with `git checkout -- <file>` and `git status --short` is empty after each (checked by the script, kept in the session scratch). All the tests named pass unmutated.

| # | Mutation | Red |
| --- | --- | --- |
| J1a | the other visible pages are not searched | 9 |
| J1b | a claim ending on a window's last page is not refused | 3 |
| J1c | the naming page is not exempt (searched too) | 33 |
| J1d | pages beyond the window are searched | 5 |
| J1e | the last window is refused too (`<=` for `<`) | 5 |
| J1f | the sentence omits the other pages | 4 |
| J1g | the sentence omits the naming pages | 4 |
| S1 | the Latin look-alike map removed | 30 |
| S2 | the decimal comma not unified | 1 |
| S3 | the loose view narrowed to space and hyphen (the old view) | 5 |
| S4 | combining and zero-width characters kept | 9 |
| S5 | the diameter sign not folded | 5 |
| S6 | the Roman one, `I` and `l` not folded | 4 |
| S7 | `×` and `*` not folded | 2 |
| S8 | compatibility forms not decomposed (NFKD to NFC) | 4 |
| S9 | over-fold: digits are separators (`ВК-1` = `ВК-2`) | 21 |
| S10 | over-fold: every Latin letter folds to `ф` | 30 |
| S11 | dashes not folded | 5 |
| S12 | whitespace not a separator of the loose view (a hyphenated line break) | 12 |
| S13 | no joining of pages (a term broken at a page break) | 2 |
| P1 | the old intro sentence back in the AI prompt | 14 |
| P2 | the old hint sentence back in the TX prompt | 12 |
| P3 | the old category rule back in the EOM prompt | 13 |
| P4 | the new category rule deleted from the SS prompt | 12 |
| P5 | the old hint sentence back in the ITP prompt | 12 |
| P6 | one changed character in the AI intro | 13 |
| P7 | `profile_version` of ITP reverted to `1.3.0` | 4 |
| P8 | the TX line of the expectations file reverted | 3 |
| P9 | the new intro put into a two-category prompt (KJ) | 11 |
| R1 | the AI recording replaced by the base file | 8 (+ `--check` lists two files) |
| J4a | the version's text-less list ignored | 5 |
| J4b | the recognised text ignored | 7 |
| J4c | the recognised text of unsearched pages counted | 1 |
| J4d | the sentence omits the recognised pages | 4 |
| W1 | wiring: `stage` drops `textless_pages` | 4 |
| W2 | wiring: `stage` drops `recognised_pages` | 4 |
| W3 | wiring: `windowed` cohort call drops `textless_pages` | 1 |
| W4 | wiring: `windowed` `decide` drops the recognised pages | 1 |
| W5 | wiring: the one-window delegation drops `textless_pages` | 2 |
| W6 | wiring: the executor's single-call site drops `textless_pages` | 1 |
| W7 | wiring: the executor's windowed site drops `textless_pages` | 1 |
| B1 | the budget ignores the bundle | 32 |
| B2 | only the system prompt is reserved (schema forgotten) | 29 |
| B3 | the АР output cap is priced | 1 |
| B4 | `text_window_policy` does not pass the bundle on | 3 |
| B5 | the executor does not hand the bundle over | 1 |
| B6 | the schema counted twice | 29 |
| J6a | the overclaim check removed | 6 |
| J6b | the stem «обязательн» removed | 1 |
| J6c | the stem «не предусмотрен» removed | 2 |
| J6d | the stem «нет в проекте» removed | 3 |
| J6e | the finding text not case-folded | 2 |

**An equivalent mutant, found and removed.** The first run of the fold mutations included "the separate hyphenation view removed" and it survived (169 passed): the loose view strips whitespace and hyphens on both sides, so everything the hyphenation view matched it matched too. The view was deleted, a test of the hyphenated word was added, and S12 above (whitespace no longer a separator of the loose view) is red.

## Commands and counts

All with `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages)`, `PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider`, `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent` and, for the stack tests, `DATABASE_URL` naming the private database (migrated to `0037_analysis_presets`).

| Command | Result |
| --- | --- |
| `tests/unit/analysis tests/integration/sections tests/integration/analysis_text tests/contract/analysis_packages` | **1578 passed, 73 skipped** (base 1406 passed, 73 skipped: +172) |
| the same by directory | `tests/unit/analysis` 768 passed, 73 skipped (inside it `tests/unit/analysis/text_profiles` 448 passed, 72 skipped: the skips are the token guard's sourced part); `tests/integration/sections` 343 passed; `tests/integration/analysis_text` 415 passed; `tests/contract/analysis_packages` 52 passed |
| `tests/integration/runs` on a freshly created private database | **944 passed** (4 warnings). The run before it, on the reused database, gave 943 passed and 1 failed (`test_provider_effect_settlement_is_bounded_and_resumable` counted one effect row left in the database by the first full run); the database was dropped, recreated, migrated, and the full suite rerun |
| `python3 fixtures/recorded/sections/build_fixtures.py --check` | `fixtures match` |
| `python3 -I tests/unit/analysis/text_profiles/build_section_prompt_fragments.py` | `fragments match` |
| `python3 -I fixtures/recorded/sections_widen/omission/build_specimens.py` | `specimens match` |
| web `npx vitest run tests/unit/analysis-settings` (the shared `node_modules` linked for the run, then unlinked) | 142 passed (9 files) |
| the token guard's designation delta of the five prompts against the base | empty for all five |
| failing first, against the unmodified source | `test_omission_judge_fixes.py` 21 failed, 3 passed; `test_omission_spelling.py` 54 failed, 24 passed; `test_section_input_budget.py` 35 failed (the `bundle` keyword) |

## Integration notes

- **Merge.** No contract, migration, web, infra, `bootstrap/**`, `api/**`, `findings/**` or AR v3 file is touched, and none of the nine other packages or their recordings (`git diff --name-only 93bc5037..HEAD` filtered for them prints nothing; the allowed paths of the task file hold every changed file). The executor change is two keyword arguments at the stage's two call sites and one at the window decision.
- **Recordings and identities.** The five sections' request keys change (new prompt text); `profile_version` is `1.3.1`. A run already pinned to the previous profile identity is not re-resolved by the version string.
- **Metrics.** A five-section run gains `omissions_dropped_<reason>` for five new reasons (`range_reaches_window_end`, `finding_text_overclaims`, `range_page_textless`, `term_on_other_visible_page`, `term_in_recognised_text`); the other metrics do not move; keys stay under 64 characters. `SECTION-CATEGORY-OCR-01.md` is immutable and still says seven reasons: this report is the record of the twelve.
- **Expected effect on the drop rate.** The check is stricter by design: any mention of the term on any other page the model was shown refuses the pair, and a window's last page is never a claim's last page. True omissions will be dropped more often than before (counted per reason; the rate is unmeasured, `A-5`).
- **Follow-ups.** (1) The start-time check per section (finding 5); (2) the symmetric window-start case (finding 1); (3) `recommendation_text` is not read by the overclaim check; (4) the debt register row for the budget's fixed term, if any, is the integrator's to close — this lane does not edit `DEBT_REGISTER.md`.
- **Disclosed: two runs touched the integrator's lane database.** The baseline run (task file P-09) and the first run after the first omission edit were started in the worktree that holds the copied `.env` with `DATABASE_URL` unset, so `tests/integration/sections/test_section_omission_over_db.py` (the only test of that battery that reads it) used the lane's own database, as that test does on any provisioned lane. Its session rolls back; what can remain is the test account `section-omission-over-db@suite.invalid` that `provisioned_record` commits (as every suite on that stack does) and the content-addressed baseline PDF blob. From the third run on every pytest ran with `DATABASE_URL` set to the private database `auditmanager_sjf01` (the lane's runner refused any other name); it was recreated once (above) and is dropped at the end of the lane.

## Limits

1. **The check still proves a literal, not an absence from the project.** What the expert reads next to the model's prose is the sentence that says which pages code searched and that other spellings were not.
2. **Windows.** A claim that starts at the first page of a non-first window is not refused (finding 1, limit a); a schedule that spans windows is still not reported (the range must lie in the window that produced the proposal).
3. **Spellings the fold does not reach**: a mark split across cells with other cells' text between the halves; `О`/`0`, `З`/`3`; Roman numerals above one (they read as `11`…, a presence); Greek capitals other than `φ`; `Д-5` inside `Д-50`.
4. **Scans.** A text-less visible page outside the range with no recognised text is not searched. Recognised text is used only to refuse.
5. **Start-time budget check** (finding 5): per deployment, not per section; the band of versions it admits and the plan then refuses is stated above.
6. **Wording.** The prompt sentences and the sentence of the stage were written by the lane; nothing ran against a model.

## Proof that forbidden paths are untouched, and the last checks

`git diff --name-only 93bc5037..HEAD`, filtered for `contracts/`, `db/`, `web/`, `infra/`, `scripts/`, `bootstrap/`, `api/`, `findings/`, the AR v3 modules, the nine other packages (`ps pos kj km ov vk pt gp pb`) and their recordings, `fixtures/recorded/text_analysis/`, `DEBT_REGISTER.md`, `CURRENT_STATE.md` and the root dependency files, prints nothing (0 lines). Every changed file is in the allowed paths of the task file.

Added 6 files (the four new test files, the report and the task file), modified 24, renamed 5 (the recordings), deleted none.

| Check (on the committed tree) | Result |
| --- | --- |
| `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` | 105 passed |
| the governance one-liner on `docs/program/tasks/SECTION-JUDGE-FIXES-01.md` | `[]` |
| `git diff --check` | clean |
| `git status --short` | empty |

## Appendix A — the reproduction against the base

Run against a copy of `git show 93bc5037:src/auditmanager/analysis/text/omission.py` (the base module loaded under another name; the rest of the tree is the same). The script, `repro.py`:

```python
import importlib.util, json, sys
spec = importlib.util.spec_from_file_location("omission_base", sys.argv[1])
om = importlib.util.module_from_spec(spec); sys.modules["omission_base"] = om; spec.loader.exec_module(om)
from auditmanager.analysis.text.anchors import resolve_anchor
from auditmanager.analysis.text.prompt import CATEGORIES, OMISSION_CATEGORY
from auditmanager.analysis.text.response import parse_response
from auditmanager.analysis.text.textlayer import load_text_layer
pages = [
 "План. Помещение 4 — санузел. Дверь Д-5 в санузел, ширина 800 мм. Отметка чистого пола 0,000.",
 "Общие данные: двери по проекту принимаются по ведомости; марки приведены ниже на листах.",
 "Ведомость дверных заполнений\nМарка Д-1 Дверь входная, 2 шт.\nМарка Д-2 Дверь межкомнатная, 6 шт.",
 "Продолжение ведомости: марка Д-5 Дверь в санузел, 1 шт.; марка Д-6 Дверь в кухню, 1 шт.",
]
out, start = [], 0
for n, t in enumerate(pages, 1):
    out.append({"page_number": n, "char_start": start, "char_end": start + len(t), "text": t}); start += len(t)
layer = load_text_layer({"artifact_role": "prepared.text_layer", "artifact_version": "1.0.0", "version_uid": "ver_x",
    "normalization": {"id": "nfc_v1", "description": "NFC"}, "total_char_count": start, "pages": out})
body = json.dumps({"observations": [{"category": "documentation", "finding_text": "Марка Д-5 названа на плане и не найдена в ведомости.",
  "recommendation_text": "Сверить.", "evidence": [{"page_number": 1, "quote": "Дверь Д-5 в санузел"}],
  "omission": {"term": "Д-5", "first_page": 3, "last_page": 3, "heading": {"page_number": 3, "quote": "Ведомость дверных заполнений"}}}]}, ensure_ascii=False)
(p,) = parse_response(body, truncated=False, categories=(*CATEGORIES, OMISSION_CATEGORY)).observations
anchors = [resolve_anchor(layer, page_number=i.page_number, quote=i.quote) for i in om.quotes_of(p)]
r = om.decide(layer, p, anchors, (1, 3))
print("visible=(1, 3):", "published" if r.published else r.reason)
print(r.finding_text[-150:])
for term, text in (("ВК-1", "Позиция BK-1 Кран"), ("ВРУ-1", "Щит BPY-1"), ("3х2,5", "Кабель 3х2.5"),
                   ("Г-3", "Светильник Г.3"), ("Ø20", "Труба Ф20"), ("ЩО-1", "Щит ЩО-I")):
    print(f"occurs({term!r}, [{text!r}]) =", om.occurs(term, [text]))
```

Output at the base:

```text
visible=(1, 3): published
оверка программой: запись «Д-5» не найдена в текстовом слое на странице 3 (буквальное совпадение без учёта регистра); другие написания не проверялись.
occurs('ВК-1', ['Позиция BK-1 Кран']) = False
occurs('ВРУ-1', ['Щит BPY-1']) = False
occurs('3х2,5', ['Кабель 3х2.5']) = False
occurs('Г-3', ['Светильник Г.3']) = False
occurs('Ø20', ['Труба Ф20']) = False
occurs('ЩО-1', ['Щит ЩО-I']) = False
```

With the fixed source the same call (`om.decide(layer, p, anchors, (1, 3))`) answers `range_reaches_window_end`, the single call (`visible=None`) `term_on_other_visible_page`, and the six `occurs` calls `True`.
