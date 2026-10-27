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
