# SECTION-CATEGORY-OCR-01 — the existing category `documentation` for same-document omissions in AI TX EOM SS ITP, and recognised text as marked context for the 14 section prompts

Task: `docs/program/tasks/SECTION-CATEGORY-OCR-01.md`. Branch `agent/section-category-ocr-01`, base `05f4584d` (`integration/ar-close-1026`). Owner rulings `R-146ao` (omissions) and `R-146aq` (scanned pages), wave brief `docs/program/dispatch/PRODUCTION-WAVE-PW5.md` section 5, gap report options P1 and P8 (`ROADMAP-GAP-2026-10-27.md` section 4.3). Accepted risks `A-2` (widened by part b), `A-5`, `A-7`.

**`reviewed` carries no human review (`R-146ag`, `A-7`).** Nothing below was run against a model; every prompt sentence and every specimen is the lane's own wording. Whether a model reports omissions usefully, and how often the mechanical check refuses a true one, is unmeasured (`A-5`).

## Design

Decided before any code. Part (a) first, then part (b), then what stays out.

### Part (a) — the honest problem and the smallest mechanism

**The problem, stated by lane G1 (decision `AI-1`, repeated for `TX-1`, `EOM-4`, `SS-5`, `ITP-5`).** An omission has no quote. The evidence of a finding is the quotes of the places that disagree; an absence is not in the text, so a quote can only show *where to look*, and the grounding gate, which checks that every quote exists, would publish «X does not exist» as grounded without being able to check it. Four reasons were given: (a) that, (b) v1 condition 5 says an absent statement is no finding, (c) windows never see each other, (d) the identity an omission check needs (a room number, a position number, a panel designation) was removed from the prompts because it repeats.

**What the owner changed (`R-146ao`).** The existing contract value `documentation` may carry a same-document omission («named on a scheme, plan or explication, absent from the specification or schedule») for `AI TX EOM SS ITP`, with an honest anchor. The contract and both CHECKs already hold the value (`contracts/api/v1/openapi.json:7990`, migrations `0022` and `0023`); nothing there changes.

**The mechanism: a pair of places and a check that code can make.** The claim the product publishes is not «the item does not exist» (code cannot know that) but «this term is named here and does not occur, letter for letter, in the saved text of these pages». The second half is a fact about the saved text layer, and code can verify it exactly. So an omission observation is checkable in two independent parts:

1. **The naming place is quoted** (`evidence`, one to three quotes): the existing path resolves each quote verbatim on its page (`anchors.resolve_anchor`) and the grounding gate re-verifies it later, exactly as for any finding.
2. **The range is quoted by its heading, and the claim is an object of its own** (`omission`): `term` (the name as printed in a naming quote), `first_page` and `last_page` (the pages of the whole schedule or specification) and `heading` (`page_number`, `quote`: the heading of that schedule, resolved like any quote). The stage then verifies, deterministically and without the model:
   - the range is well formed: pages inside the document, `first_page <= last_page`, the term 3 to 60 characters and at most five words after folding (a long term would make absence trivially true: «светильник встраиваемый 600x600 Г-3» is absent where «Г-3» is present);
   - in a windowed run the range lies inside the window that produced the observation (the model only claims about pages it was shown);
   - the heading lies inside the range;
   - the naming quote and the heading quote both resolved (all-or-nothing: unlike a contradiction, a pair with one place missing is not a pair);
   - the term occurs in at least one naming quote (the naming place really names it);
   - every page of the range has usable text (`>= 50` non-blank characters, the product's own text-less threshold): a scanned page proves nothing about absence;
   - the term does **not** occur in the text of the range. «Occurs» is deliberately wide so that a refusal errs towards dropping: case-folded, `ё`=`е`, Unicode compatibility forms, all dashes one hyphen, whitespace collapsed, soft hyphens removed, and three views are tried (the folded text, the text with line-break hyphenation joined, and both sides with spaces and hyphens removed); a hit in any view means present. Pages are joined with a space and with nothing.
3. **Published form.** An observation that passes is emitted as `documentation` with `evidence` = the naming quote(s) followed by the heading quote (a «pair of places», every item an ordinary resolved anchor, so the unchanged gate accepts and publishes it) and `finding_text` = the model's sentence followed by one sentence the stage writes: «Проверка программой: запись «<term>» не найдена в текстовом слое на страницах <a>–<b> (буквальное совпадение без учёта регистра); другие написания не проверялись.» The expert reads, next to the model's prose, exactly what code verified and what it did not.
4. **Refused with a recorded reason, never silently.** An observation that fails any step is not written to the artifact. It is counted in the stage metrics by a closed set of reasons (`omissions_dropped_<reason>`: `claim_invalid`, `range_outside_window`, `heading_outside_range`, `evidence_unresolved`, `term_not_in_naming_quote`, `range_page_without_text`, `term_present_in_range`) beside `omissions_proposed` and `omissions_published`. A `documentation` reply without a well-formed `omission` object, an `omission` object on another category, or `documentation` from a profile that does not declare it is malformed (`proposals_malformed`), as every other malformed proposal.

What this does **not** do, said once: it does not know whether the item is meant to be in the schedule (that is the expert), whether the schedule lists it under another name (the prompt tells the model to treat another spelling as a record and the code checks only the literal term), or whether a drawing, which no text profile reads, shows it. A published omission is a question for the expert, decided the way every finding is (`appendDecision`).

**How the four reasons of `AI-1` are met.** (a) The finding carries two verified quotes and a code-verified absence, not an unchecked non-existence claim. (b) The v1 text stays; the new paragraph is explicitly the one exception to condition 5 and to «ровно две категории», in each of the five prompts. (c) The check runs on the full saved layer, and in a windowed run the range must lie inside the window, so no claim is made about pages the model did not see; a schedule that spans windows is not reported (a limit, below). (d) The model is asked for the shortest distinguishing designation as printed in the naming quote, and the check is a literal term, not a room or position identity; a repeated designation can only make the term *present* and the observation refused, never the reverse.

**Per-profile categories and schema (internal to the profile package).** The module constants stay for the nine other sections and for every test that imports them. Package format `text-profile/2` adds one key, `categories` (the closed list in the order `internal_contradiction`, `explicit_placeholder`, then only `documentation`). `profile_registry.load_text_profile_registry` reads it, and `prompt.response_schema_for(categories)` returns the v1 `RESPONSE_SCHEMA` object itself for the two-category list and, for the three-category list, the same schema with `documentation` in the category enum and the optional `omission` property (with Russian field descriptions, which keeps the prompt free of new machine names). `AnalysisProfile.categories` carries the list; `response.parse_response(..., categories=...)` and `artifact.build_text_observations` (line 84, which already checks `observation.category in profile.categories`) enforce it. The contract's `Evidence` stays quote-only and the artifact `analysis.text_observations` keeps its shape: the `omission` object is a model-side claim consumed by the stage and not stored; what is stored is its verified outcome (two evidence items and the sentence).

**The five packages.** `AI TX EOM SS ITP` become `text-profile/2`, `profile_version` `1.3.0` (AI from `1.1.0`, the other four from `1.2.0`), `status` stays `reviewed`. Each prompt gains one paragraph of at most 1,000 characters (the brief's limit is 1,200), inserted directly after condition 5 and built from the fragments below; the nine other packages are not touched (their `profile.json`, prompt and recording are byte-identical, proved by `git diff --name-only`). The superseded decisions are `AI-1`, `TX-1` of `SECTION-WIDEN-G1-01` and `EOM-4`, `ITP-5` of `SECTION-WIDEN-G3-01` (the item named on a scheme, plan or explication and absent from the specification), and `SS-5` of the same report **as far as that pair goes** (a device or line named on the scheme and absent from the specification or the cable journal): **X becomes W** by `R-146ao`, for these five sections only. What `SS-5` also covers, a list that is merely shorter in one place than in another (systems in the general data, points on a scheme), stays **X**: the record's own reason, that a shorter list is often by design, is not touched by anything above, and the SS paragraph does not speak of it. The token guard sees one new whole token in each prompt, `documentation` (Latin). It needs no allowlist line: it is a whole token of each of the five pinned `finding_categories.md` files (the legacy category «Соответствие чертежей спецификации» / «несоответствие между схемой, планом и спецификацией» is exactly this use), which the guard's sourced part reads from the legacy repository at the pinned commit; `finding_text` is already a v1 token. No digit, class designation or norm number is added. (While this lane ran, the host's `/root/projects/PDF-proverka` was an empty `git init` skeleton and later absent, so the guard's sourced part skips here; the audit was re-run with the guard's own functions over a copy of the same files found at `/home/ciuser/lane-baseline/src/prompts/disciplines/`, whose 25 sha256 values equal the pins of the five `profile.json` files: no unexplained token in any of the 14 prompts, task file P-06.)

<!-- fragments:begin -->
```json
[
 {
  "id": "O-HEAD",
  "sections": [
   "AI",
   "TX",
   "EOM",
   "SS",
   "ITP"
  ],
  "role": "rule: the one exception to condition 5 and to the two categories",
  "text": "Исключение из условия 5 и из слов «ровно две категории» — пропуск, который затем проверяет программа."
 },
 {
  "id": "O-SCOPE-AI",
  "sections": [
   "AI"
  ],
  "role": "scope: which named item may be reported as an omission",
  "text": "Здесь это марка или наименование, которое текст называет на плане, развёртке или в экспликации, но которого нет в ведомости отделки, ведомости дверных заполнений или спецификации."
 },
 {
  "id": "O-SCOPE-TX",
  "sections": [
   "TX"
  ],
  "role": "scope: which named item may be reported as an omission",
  "text": "Здесь это позиция или наименование оборудования, которое текст называет в экспликации оборудования или на схеме, но которого нет в спецификации оборудования."
 },
 {
  "id": "O-SCOPE-EOM",
  "sections": [
   "EOM"
  ],
  "role": "scope: which named item may be reported as an omission",
  "text": "Здесь это щит, группа или аппарат, который текст называет на схеме, но которого нет в спецификации оборудования."
 },
 {
  "id": "O-SCOPE-SS",
  "sections": [
   "SS"
  ],
  "role": "scope: which named item may be reported as an omission",
  "text": "Здесь это прибор или линия, которые текст называет на схеме, но которых нет в спецификации оборудования или в кабельном журнале."
 },
 {
  "id": "O-SCOPE-ITP",
  "sections": [
   "ITP"
  ],
  "role": "scope: which named item may be reported as an omission",
  "text": "Здесь это аппарат, насос или арматура, которые текст называет на схеме, но которых нет в спецификации оборудования."
 },
 {
  "id": "O-REPORT",
  "sections": [
   "AI",
   "TX",
   "EOM",
   "SS",
   "ITP"
  ],
  "role": "category and object: the existing documentation value, the term, the range, the heading quote",
  "text": "Сообщай его категорией documentation, только если цитата места, называющего запись, дословно содержит её, и заполнен объект пропуска из схемы: запись так, как она напечатана в цитате (короткое обозначение, не более пяти слов), первая и последняя страницы всей ведомости или спецификации и дословная цитата её заголовка на этих страницах."
 },
 {
  "id": "O-CHECK",
  "sections": [
   "AI",
   "TX",
   "EOM",
   "SS",
   "ITP"
  ],
  "role": "the program's check: the term must not occur in the range",
  "text": "Программа проверит, что записи нет в тексте этих страниц, и отбросит находку, если она там есть."
 },
 {
  "id": "O-SPELLING",
  "sections": [
   "AI",
   "TX",
   "EOM",
   "SS",
   "ITP"
  ],
  "role": "conservative: another spelling is a record",
  "text": "Другое написание той же записи считай записью; сомневаешься — не сообщай."
 },
 {
  "id": "O-WORDING",
  "sections": [
   "AI",
   "TX",
   "EOM",
   "SS",
   "ITP"
  ],
  "role": "wording: a pair of places, no claim of non-existence or requirement",
  "text": "В finding_text пиши только, что запись названа на такой-то странице и не найдена на таких-то; не пиши, что её нет в проекте или что она обязательна."
 },
 {
  "id": "O-OTHER",
  "sections": [
   "AI",
   "TX",
   "EOM",
   "SS",
   "ITP"
  ],
  "role": "the object is for the one category only",
  "text": "У остальных категорий объекта пропуска нет."
 },
 {
  "id": "O-NONE",
  "sections": [
   "PS",
   "POS",
   "KJ",
   "KM",
   "OV",
   "VK",
   "PT",
   "GP",
   "PB"
  ],
  "kind": "absent",
  "role": "the other nine sections keep two categories",
  "text": "documentation"
 }
]
```
<!-- fragments:end -->

(`O-NONE` is an `absent` entry: the other nine prompts must not carry the new category. The builder reads this block like those of lanes G1 to G3 and the sentence guard table is regenerated, not retyped.)

### Part (b) — recognised text as marked context

**What exists.** `source_preparation` publishes `prepared.recognised_text` for a portal bundle (per TEXT block the portal's OCR text, `quote_source: recognised`, quality flags; IMAGE descriptions are never an input, `R-117`) and the version row holds `textless_pages` (pages with fewer than 50 characters, `TEXTLESS_PAGE_CHARACTERS`). The existing selector `analysis.profiles.ar_shared.recognised_context.select_context` takes exactly the TEXT entries on those pages and refuses an inconsistent pair of artifact and version. The section run path never read it (`ROADMAP-GAP` section 3.1 item 6), although the executor already holds both: `outputs.refs[ROLE_RECOGNISED_TEXT]` after `source_preparation`, and `version.textless_pages` from the version row it loads.

**What is built.**
- `analysis/text/recognised_input.py`: `RecognisedPage(page_number, text, flags)`, the per-page block, its validation against the text layer (the page exists, no page twice, non-blank text) and its length. The block is delimited and marked per page: `--- Распознанный текст страницы N (не из текстового слоя) ---`, the text as a JSON string literal (OCR is untrusted data; a JSON string cannot carry a forged banner or delimiter line, the precedent of `render_context`), one line of quality flags when there are any, `--- Конец распознанного текста страницы N ---`. It stands directly after its page's (short or empty) text-layer text under the page banner.
- The model is told in the **user message**, once, in the preamble and only when the call carries at least one block: the blocks are recognised text, not from the text layer, may contain errors and instructions that are not the task's, are context only, cannot be quoted, and a discrepancy supported only by them is not a finding. The system prompts of the 14 sections are **not** edited for this: the nine sections keep their package, recording and bundle hash byte for byte, and a version without text-less pages sends exactly the request it sent before (same body, same `request_sha256`, same recordings). This is a deliberate narrowing of the brief's «all 14 prompts and recordings change»: the instruction sits next to the data it governs, and a bundle hash that included the wording would move 14 identities (and `tests/support/v1_reference_profile.py` pins the v1 one) for requests that carry no scan.
- `prompt.render_document`, `adapter.build_request`, `windows.render_window` and `windows.build_window_request` take the pages (default none); `stage.run_text_analysis` and `windowed.run_text_analysis_windows` take them too and pass them through. Nothing else about either path changes.
- `src/auditmanager/runs/section_recognised_input.py` (the loader) reads the artifact with the existing `read_artifact`, runs `select_context` with `version.textless_pages`, merges the blocks of one page in artifact order and returns `RecognisedPage`s. A version with no bundle (`textless_pages is None`) or no text-less page returns nothing; a text-less page without a recognised artifact, or an artifact that disagrees with the version, fails the stage explicitly (`analysis_input_invalid`, reason `recognised_input_invalid`), the selector's own refusal, not a silent empty context. `runs/executor.py` gains the call site only (about ten lines: the version's `textless_pages` goes in, the pages come out).

**A quote found only in recognised text confirms nothing.** No change to `findings/grounding.py` is needed or made. The stage resolves every quote against `prepared.text_layer` only (`anchors.resolve_anchor`), and the OCR text is never merged into that layer, so a quote that exists only in a recognised block is an unresolved anchor: an ordinary contradiction with every quote unresolved is dropped, and one with some resolved keeps only those; an omission with a recognised-only naming or heading quote is refused (`evidence_unresolved`). The gate re-verifies against the same layer. Tests make the property fail on purpose (mutation M-OCR below).

**Budget and windows.** A recognised block adds characters that neither the version's `text_character_count` nor the framing allowance of `budget.py` (`PAGE_FRAMING_ALLOWANCE_CHARACTERS`, 12,000: the banners of 500 pages) count. The arithmetic is not widened by a constant: the actual rendered length of every block is counted where the decision is made. `text_window_policy` takes `recognised_characters` (default 0; the executor passes the blocks' total, notice included) so that a version just under the one-call budget that the scans push over is windowed instead of sent whole; `chunk_preflight.partition_text_layer` takes `page_extra` (the block's length per page) so that a window holds at most the ceiling *with* its blocks, and a page whose text plus block exceeds a window is refused as before (`window_page_exceeds_limit`). The start-time refusal (`runs/commands.py`, `analysis_input_budget_exceeded`) still compares the text-layer count alone; it is outside this lane's paths, and a version that scans push past the windowed limit is refused by the plan with `window_plan_over_limit`, explicitly, before any call. Integration note below.

**More client text goes to the provider (`A-2`).** For a version with text-less pages the provider now receives their recognised text, which it did not before; it already received all the text-layer text. The accepted risk `A-2` is widened by exactly that, as the owner ruled (`R-146aq`); no new recipient, no new field of the contract.

### What stays out

No contract (`Evidence` stays quote-only; the artifact shape is unchanged), no migration, no change to `findings/grounding.py`, `bootstrap/**`, `api/**`, `web/**`, `infra/**`; no edit to the other nine packages, the ledger, the three widen reports or the register. STOP conditions of the brief were checked: part (a) needs no contract or migration change, and the only source outside `analysis/text/**` and `analysis/public.py` is the loader and the executor's call site (`runs/**`, the OCR input loader of part b).

## Result

| Part | State | What exists |
| --- | --- | --- |
| (a) `documentation` for same-document omissions, `AI TX EOM SS ITP` (`R-146ao`) | **built** | the pair-of-places check (`analysis/text/omission.py`), per-profile categories and schema (`text-profile/2`, `prompt.response_schema_for`, `response.parse_response(categories=…)`), five packages at `1.3.0` with one paragraph each (916 to 983 characters), five rebuilt recordings, ten specimens, a fourth source of the sentence-guard table |
| (b) recognised text as marked context for all 14 sections (`R-146aq`) | **built** | `analysis/text/recognised_input.py`, the loader `runs/section_recognised_input.py` and its call site in the executor, window arithmetic that counts the blocks; no contract, no migration, so no STOP condition applied |

Nothing was run against a model. Every prompt sentence, specimen and reply is the lane's own wording; `reviewed` still carries no human review (`R-146ag`, `A-7`), and the quality of what a model reports with the new category, and how often the check refuses a true omission, are unmeasured (`A-5`).

**Two deliberate differences from the wave brief.** (1) `PRODUCTION-WAVE-PW5.md` section 5 says part (b) changes all 14 prompts and recordings. The instruction to the model is in the **user message** of a call that carries a block (the preamble notice), so the nine other packages, their recordings and every bundle hash are byte-identical and a version without a scanned page sends the same request as before; only the five packages of part (a) changed their prompts. (2) The sentence guard needed no allowlist line (`documentation` is sourced), where the lane brief expected five append-only entries.

## Decisions superseded by `R-146ao`

| Decision | Section | Before | After |
| --- | --- | --- | --- |
| `AI-1` (`SECTION-WIDEN-G1-01`) | AI | X: an absence has no quote | **W**: the pair of places and a code-checked absence (Design above) |
| `TX-1` (G1) | TX | X | **W** |
| `EOM-4` (`SECTION-WIDEN-G3-01`) | EOM | X | **W** |
| `ITP-5` (G3) | ITP | X | **W** |
| `SS-5` (G3) | SS | X | **W** for a device or line named on a scheme and absent from the specification or the cable journal; **X** stays for a list that is merely shorter in one place than in another |

The ledger and the two widen reports are not edited (forbidden paths); this table and the fragment table are the record.

## Files

| Group | Files |
| --- | --- |
| New source | `src/auditmanager/analysis/text/omission.py`, `src/auditmanager/analysis/text/recognised_input.py`, `src/auditmanager/runs/section_recognised_input.py` |
| Edited source | `analysis/text/{prompt,response,profile_registry,adapter,stage,windowed,windows,chunk_preflight}.py`; `analysis/public.py` (additive: `RecognisedPage`, `RecognisedContextError`, `select_recognised_context`, `recognised_total_characters`); `runs/executor.py` (the call site only) |
| Packages | `profiles/{ai,tx,eom,ss,itp}/{profile.json,system_prompt.md}` |
| Recordings | `fixtures/recorded/sections/{ai,tx,eom,ss,itp}/<key>.json` renamed to their new keys by `build_fixtures.py` (the nine others unchanged) |
| Fixtures | `fixtures/recorded/sections_widen/omission/build_specimens.py` and ten files `omission/{ai,tx,eom,ss,itp}/{positive,*_negative}.json` |
| New tests | `tests/unit/analysis/test_omission_check.py` (45), `test_recognised_input.py` (13), `tests/integration/analysis_text/test_recognised_context.py` (11), `tests/integration/sections/test_section_recognised_input.py` (12), `test_section_omission_specimens.py` (45), `test_section_omission_over_db.py` (1; skipped without a stack) |
| Edited tests and data | see «Modified tests» |
| Documents | this file and `docs/program/tasks/SECTION-CATEGORY-OCR-01.md` |

## Modified tests (what each asserted before and after; none is weaker)

| File | Before | After |
| --- | --- | --- |
| `tests/unit/analysis/test_text_profile_registry.py` | the defective-package case `format="text-profile/2"` expected `format_invalid` | the same case with `text-profile/3` expects `format_invalid`: `/2` is now a real format (its own cases are in `test_omission_check.py`: it needs a `categories` list that is exactly the v1 pair plus `documentation`; the key set follows the format) |
| `tests/unit/analysis/text_profiles/test_text_profile_packages.py`, `test_every_profile_manifest_has_the_text_profile_1_shape` | every legacy package has the eight keys and `text-profile/1` | the nine others: unchanged; `AI TX EOM SS ITP`: the eight keys plus `categories`, `text-profile/2`, `categories` equal to the three values (a stricter pin; the v1-skeleton test is untouched and still passes for all 14) |
| `tests/unit/analysis/text_profiles/section_profile_expectations.json` | `AI` `1.1.0`; `TX EOM SS ITP` `1.2.0` | all five `1.3.0` (data pinned by four tests and the web) |
| `tests/unit/analysis/text_profiles/build_section_prompt_fragments.py` | sources: ledger, G1 to G3; every widen entry `present` | adds the source `C1` (this report); an entry may carry `kind: absent` |
| `tests/unit/analysis/text_profiles/section_prompt_fragments.json` | 112 entries | 124, regenerated by the builder (`--write`), not retyped |
| `tests/unit/analysis/text_profiles/test_section_prompt_fragments.py` | four sources; counts of G1 to G3 | five sources; the counts of the new one (12 entries, 44 pairs); the paragraph stands in exactly five prompts and `documentation` is kept out of the nine others |
| `tests/integration/sections/test_section_widen_specimens.py` | every sub-directory of `sections_widen` is a section directory | skips the one named `omission` (its own format, held by its own test) |

Recordings: five files renamed to the keys of the new requests and their `origin.prompt_bundle_sha256` updated, by `build_fixtures.py`; `--check` prints `fixtures match`; `test_section_recordings.py` is unedited and passes (it pins one file per section).

## The omission paragraph and the new fragments

Eleven sentences stand in the five prompts (seven shared, five scope sentences, one per section; the block in the Design section is the source, the builder reads it) and `O-NONE` keeps the category name out of the other nine. Growth per prompt: AI +985, TX +963, EOM +918, SS +934, ITP +921 characters (limit 1,200); the response schema grows by 974 characters (627 to 1,601). The paragraph is inserted directly after condition 5 and calls itself the one exception to it and to «ровно две категории».

## The specimens

`build_specimens.py` is the source of the ten files; the test holds the files equal to it.

| Specimen | Text and reply | The stage |
| --- | --- | --- |
| `ai/positive` | a door mark on a floor plan, a door schedule without it | published: two evidence items, the mark's quote and the schedule heading |
| `ai/dash_negative` | the schedule writes the mark with an en dash | dropped `term_present_in_range` |
| `tx/positive` | an item of an equipment explication, a specification without it | published |
| `tx/wrapped_negative` | the specification wraps the mark over two lines | dropped `term_present_in_range` |
| `eom/positive`, `eom/case_negative` | a panel on a single-line scheme; the specification writes it in lower case | published; dropped `term_present_in_range` |
| `ss/positive`, `ss/second_page_negative` | a camera on the scheme, a two-page cable journal; the term is on the second page | published; dropped `term_present_in_range` |
| `itp/positive`, `itp/scan_negative` | a pump on the principal scheme; the range includes a page with no text | published; dropped `range_page_without_text` |

Replayed through `run_text_analysis` with each section's own profile over a text layer built from `pages` and a recording keyed to the request the current prompt sends. Also shown on them: the term added to the range turns every positive into a drop; one altered character in the naming quote or in the heading drops the pair; the same reply to a section that does not declare the category (KJ) is malformed and nothing is published. The database path is shown once on the lane stack (`test_section_omission_over_db.py`): the reply over the AR baseline text is published as one `documentation` finding with two evidence rows whose offsets slice back to the quotes, in the tables whose CHECKs name the categories.

## Mutation table

Each mutation is one exact replacement in a committed source or prompt, applied to the worktree, the named tests run, the file restored with `git checkout -- <file>` (`git status` clean after each; the script is `mutate.py`, kept in the session scratch and summarised here). «Red» counts are of the tests named by the mutation, all of which pass unmutated (507 passed, 1 skipped for the union; the skip is the stack-only test).

| # | Mutation | Result | Red tests (shortened) |
| --- | --- | --- | --- |
| M1 | the absence check never finds the term | 31 failed | the five dropped negatives, the ten «every way a record can hide» cases |
| M2 | the absence check always finds the term | 10 failed | the five positives, the usable-page case |
| M3 | the parser accepts `documentation` from every profile | 6 failed | `a_section_that_does_not_declare_the_category_refuses_the_same_reply` (five positives) and the parser case |
| M4 | recognised text merged into the text-layer pages before grounding | 3 failed | an OCR-only quote is dropped; a text-layer quote is kept and the OCR one lost; an omission whose quote is OCR-only is refused |
| M5 | the loader ignores the text-less list (every page's OCR selected) | 2 failed | only the text-less pages are read; the stage sends a block for the text-less page and none for a page with text |
| M6 | the registry ignores the declared categories | 35 failed | the five profiles' categories and schema, the `/2` package cases |
| M7 | the notice is written into every call | 4 failed | byte-for-byte rendering without scans; no block and no metric without scans |
| M8a | window packing ignores the blocks | 3 failed | the partition weight, the window ceiling, a block larger than a window |
| M8b | the one-call decision ignores the blocks | 1 failed | scans push a version just under the budget into windows |
| M9 | a heading outside the range accepted | 1 failed | `the_heading_must_lie_inside_the_range` |
| M10 | the term need not be in a naming quote | 1 failed | `the_term_must_be_in_a_naming_quote` |
| M11 | a page of the range without text accepted | 2 failed | `itp/scan_negative`, the usable-page case |
| M12 | the range may reach beyond the window | 2 failed | the window case (stage) and the check case |
| M13 | an unresolved quote does not drop the pair | 13 failed | the altered-quote cases, the OCR-only omission case, the unresolved-anchor case |
| M14 | recognised text rendered raw, not as a JSON string | 4 failed | the forged banner and closing marker, the block layout |
| M15 | a long term accepted (length bound removed) | 2 failed | the long and the many-word terms |
| M16 | the dash fold removed | 5 failed | `ai/dash_negative` and four spelling cases |
| M17 | the hyphenation and spacing views removed | 6 failed | `tx/wrapped_negative` and five spelling cases |
| M18 | `documentation` put into the KJ prompt | 3 failed | `C1:O-NONE`, the whole-table check, the re-wrap check |
| M19 | one omission sentence deleted from the AI prompt | 4 failed | `C1:O-SPELLING` (present, deleted, one changed character), the whole-table check |
| M20 | the published text loses the program's sentence | 6 failed | the five positives and the sentence case |

## Commands and counts

All with `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages)`, `PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider` and `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent` (the legacy repository is unusable on this host; the token guard's sourced part and the hash-at-commit check skip with their reasons).

| Command | Result |
| --- | --- |
| `tests/unit/analysis tests/integration/sections tests/integration/analysis_text tests/contract/analysis_packages` (`tests/unit/analysis` holds `text_profiles`) | **1406 passed, 73 skipped** (base 1244 passed, 73 skipped: +162 cases, no new skip) |
| `tests/unit/analysis` / `tests/integration/sections` / `tests/integration/analysis_text` / `tests/contract/analysis_packages` | 649 passed, 73 skipped / 325 passed / 380 passed / 52 passed |
| `tests/unit/analysis/text_profiles` | 433 passed, 72 skipped (the skips are the token guard's sourced part) |
| `tests/integration/sections` without a stack | 324 passed, 1 skipped (the stack-only test, with its reason) |
| `tests/integration/runs` on a private migrated database (`0036_cite_partition_v3`) | **944 passed** (the first run before the last test edit and the last after a fresh database; one intermediate run met a Postgres restart of the lane stack and an unresolved effect it left in the private database: dropped and re-created, not a defect of the lane) |
| `python3 fixtures/recorded/sections/build_fixtures.py --check` | `fixtures match` |
| `python3 -I tests/unit/analysis/text_profiles/build_section_prompt_fragments.py` | `fragments match` |
| `python3 -I fixtures/recorded/sections_widen/omission/build_specimens.py` | `specimens match` |
| web `npx vitest run tests/unit/analysis-settings` (reads the expectations file) | 106 passed |
| the token guard's functions over a hash-identical copy of the legacy files (task file P-09) | no unexplained token in any of the 14 prompts |

`tests/contract/program`, the two prose tests, the governance one-liner and `git diff --check` are listed in the task file's «Required tests» and were run on the committed tree (final section).

## Integration notes

- **Merge.** The diff adds 21 files and edits 27 (5 of them renames of recordings). It touches no contract, migration, `web/`, `infra/`, `bootstrap/`, `api/`, `findings/` file, none of the nine other packages and none of their recordings (`git diff --name-only 05f4584d..HEAD` filtered for those paths prints nothing). The one edit in `runs/executor.py` is the loader's call site; `runs/commands.py` is not edited.
- **The recorded stand.** The five sections' recordings are new files under new keys; an old key finds nothing, as for any prompt edit. The canonical `fixtures/recorded/text_analysis/` is untouched.
- **Metrics.** A five-section run gains `omissions_proposed|published|dropped` and `omissions_dropped_<reason>` (seven reasons); a call that carried a block gains `recognised_pages` and `recognised_characters`. Any other run's metrics do not move (`metrics` keys are `^[a-z][a-z0-9_]{0,63}$` scalars, the longest new one is 42 characters).
- **A follow-up outside this lane's paths.** The start-time refusal `analysis_input_budget_exceeded` (`runs/commands.py`) compares `text_character_count` alone. `recognised_character_count` is on the version row; adding it there would refuse a scan-heavy volume at `startRun` instead of at the window plan (`window_plan_over_limit`, reason with both figures, before any call).
- **A debt candidate.** `budget.input_budget_characters` subtracts the length of v1's prompt and schema (3,639 characters) as the fixed part of every call, while the section prompts are 5,361 to 7,219 characters longer than v1's (SS the longest at 10,231, plus its schema); this lane adds up to 985 + 974 characters to five of them. The shortfall predates this lane; the ceiling still holds the cost (checked after each call).
- **Host and test hygiene.** `/root/projects/PDF-proverka` was an empty `git init` skeleton while the lane ran (later absent). With the skeleton present, `test_source_files_exist_at_the_recorded_legacy_commit` failed on the base tree too; `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent` makes the skip explicit. A test that imports a builder from a fixtures directory must not write bytecode there (`sys.dont_write_bytecode`); one did, and the fixed test is the committed one.
- **Disclosed: one run touched the integrator's lane database.** While checking that `tests/integration/sections` is container-free without a stack, one pytest run used `env -u DATABASE_URL` in a worktree that holds the copied `.env`; the harness then read the shared lane database from that file. The test sessions roll back; what can remain is the test account `section-omission-over-db@suite.invalid` that `provisioned_record` commits (as every suite on that stack does) and the content-addressed baseline PDF blob. A second such run was refused by the permission system and not repeated. Every other database run used a private database that was dropped.

## Limits and assumptions an expert would still check (`A-5`, `A-7`)

1. **The check proves a literal, not an absence.** «The term as printed in the naming quote does not occur, letter for letter, in the text of these pages» is a fact about the saved text layer; whether the item is meant to be in the schedule, whether the schedule lists it under another name, or whether a drawing shows it is the expert's call. The finding says so in its last sentence.
2. **The model chooses the term and the range.** A bad term (too specific: refused only beyond 60 characters or five words; too generic: dropped as present) or a wrong range is possible. The prompt asks for the shortest distinguishing designation and the whole schedule; nobody measured whether a model does.
3. **The presence test errs towards dropping.** Substring, case, dashes, `ё`, wrapped lines, spaces and page breaks all count as presence; `Д-5` is present in `Д-50`. True omissions will be dropped, and each drop is counted by reason; the rate is unknown.
4. **A range page with fewer than 50 non-blank characters** (the product's text-less threshold) makes the pair undecidable, even when its recognised text is available: recognised text is context, not evidence, and is not used to prove an absence.
5. **Windows.** A schedule that spans two windows is not reported (the range must lie inside the window that produced the proposal); a naming place and a schedule heading in different windows are not paired. The stage metrics already say that windows are independent (`windows_note`).
6. **Recognised text.** Only TEXT entries of the pages the version stores as text-less are sent; IMAGE descriptions never. The OCR is rendered as one JSON string per page: it keeps the words and loses the markdown layout of tables. The notice and the quoting are the lane's measures against instructions inside scans; they are untested against a model. More client text goes to the provider (`A-2`, widened by `R-146aq`).
7. **Wording.** The five paragraphs, the notice and the program's sentence were written by the lane; the token guard and the sentence guard see that they are present and sourced, not that they are right. The five recordings and the ten specimens are hand-authored; passing them proves the stage's mechanics, never a profile's quality.
8. **Not added.** The reverse omission (an item in the schedule absent from the plans), a list that is merely shorter in one place, any comparison of the model's `term` with a synonym table, and any use of the OCR to confirm a finding.
