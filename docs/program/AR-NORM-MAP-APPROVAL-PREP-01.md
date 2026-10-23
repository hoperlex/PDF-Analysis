# AR C01–C22: decision sheet before map approval and v3 activation

**Task:** [AR-NORM-MAP-APPROVAL-PREP-01](tasks/AR-NORM-MAP-APPROVAL-PREP-01.md). **Frozen development base:** `b5e089b5c6a07a7bb53f6b60007c9f5041ebff8d`, 2026-10-23. **Decision state:** no C item is owner-approved; no reviewed `map_sha256`, qualified production `nrs_`, or served v3 profile exists in this tree. The original checklist supplies *topics*, never thresholds. Its 46 bullet dispositions and source hashes are in `AR-NORM-MAP-DISCOVERY-01` at `281a54181e8ae499bc8152e74d5ff646f01f44dc` on the separate `integration/ar-evidence-01` line. This packet does not import that branch or rewrite its historical reports.

## Evidence levels and source identity

Candidate paragraph IDs belong only to repaired snapshot `ns_01M59N8QNBVN91ACA2HCE6VE74` (`2026-07-23..2026-08-20+17d+121r.0a1bafe103ff`). `AR-NORM-MAP-REVIEW-PREP-01` at `bc8e296272e6b90935d187dc2f63f7ecfae2f016` verified 22 anchor paragraphs against effective recognised text and local PDF pages, and matched six PDF hashes to the offline bundle. Its promotion DB still had **zero** Blob, admission and binding rows. That proves a candidate text location, not served PDF custody or legal applicability. The later edition audit at `9956efecc7a4a7e29c0b45e1cfd70932f58ce965` found **no D1–D6 candidate with complete page-level final-edition confirmation**.

| Alias | Corpus document | Source family and open decision |
| --- | --- | --- |
| D1 | `ndoc_01M59N9JD4VPS1C8ACDFC01BGG` | СП 1.13130.2020; compare selected clauses with actual №2/№3 change pages and project date/class. |
| D2 | `ndoc_01M59N9WF2B93HJQ3GYNR5FCWS` | СП 54.13330.2022; selected residential clauses and №1/№2 change pages need review. |
| D3 | `ndoc_01M59N9WJPYS8FAQED34RPJF14` | СП 59.13330.2020; №3/№4 wording and N/R/P accessibility branches need review. |
| D4 | `ndoc_01M59N9VSS64AB4R6N6XX3Q74G` | СП 50.13330.2024; source page, thermal-zone and element scope need review. |
| D5 | `ndoc_01M59N9W1JY06JA08QK08DE2HT` | СП 51.13330.2011; table/footnote segmentation and amendments need review. |
| D6 | `ndoc_01M59N9Z9MD1RNV7QJDBFNC87X` | 123-ФЗ; local selected text has a later official editorial comparator, but the original amendment chain and project date remain open. |

The [Росстандарт change №3 card for СП 1](https://protect.gost.ru/sp/changesdetails/de574ad5-67fc-4e31-a0a5-a793c94b1cc7), [change №4 card for СП 59](https://protect.gost.ru/sp/changesdetails/070b0f9b-69ba-40a0-837d-eb0d504dbb06), and [change №4 card for СП 51](https://protect.gost.ru/sp/changesdetails/0ff54d77-7ba7-441d-bd68-dbaa9b73f7f2) confirm change identities/dates, not the full amended pages. The [official СП 1 family card](https://protect.gost.ru/sp/details/9fdcb635-708c-4c67-81a7-83e6baad9ab3) explicitly scopes reconstruction to the work performed. Neither a registry “Действует” badge nor a corpus export date decides the rule for a given project's design date.

## Item decision sheet

All rows are **review candidates**. `N` means new residential work, `R` reconstruction within the changed work, and `P` an embedded public-use room; a project can need more than one. Ordinals below are candidate complete spans from `AR-NORM-MAP-REVIEW-PREP-01`; the C21/C22 corrections come from `AR-TABLE-ROWS-01` at `50cd9351af58b041b9f7c78692edbc01103414d7`. Exact first/last `npar_` IDs and PDF pages are in those immutable reports. They must be copied into reviewed map bytes only after owner adjudication and fresh qualification of the same snapshot.

| Item / original line | Candidate source and span | Approval question / present stop |
| --- | --- | --- |
| C01 / 19, exits | D1 §4.2.7, 132–137 | Choose room/floor/F class and full exit-count branch; 1,417 source chars exceeds per-item guide. |
| C02 / 14, 20, exit door | D1 §4.2.19, 168–169 | Prove the measured opening is an evacuation exit and select its exception. |
| C03 / 6, 20, path | D1 §4.3.3, 213–214 | Prove a МОП corridor is an evacuation route and select occupant branch. |
| C04 / 20, stair | D1 §4.4.1, 240–248 | Choose stair function/class; 1,281 source chars exceeds guide. |
| C05 / 21, smoke-free stair | D6 article 40, 489–492 | Classification Н1/Н2/Н3 alone prescribes no type; find applicable prescriptive source or exclude. |
| C06 / 22, apartment-to-exit distance | D1 §4.3.1, 206–207 | Clause delegates to a class-specific table; select complete residential/P branch or exclude. |
| C07 / 25, occupied-roof exit | D1 explicit 100–100 | Prove the roof is occupied and select the referenced floor rule; discard legacy per-length ratio. |
| C08 / 25, fire access to roof | D6 article 90, 932–932 | Verify building height and work scope; keep separate from occupant exit C07. |
| C09 / 23, fire barrier | D2 §6.2.1.9, 343–345 | Only the specified extra-apartment storage block is a candidate. Generic barrier properties depend on absent СП 2/4; P needs another source. |
| C10 / 58–59, fire classification | D6 article 28, 356–356 | Check complete project-document declaration only; no class/degree may be inferred. |
| C11 / 14, accessible door | D3 §6.1.5, 301–304 | Select wheelchair route and N/R exception; 1,139 chars exceeds guide. |
| C12 / 37, ramp slope | D3 §6.2.9, 365–373 | Mixed ramp types/conditions; select complete subrange or exclude. Span is 1,523 chars. |
| C13 / 37, ramp width | D3 §6.2.9, 365–373 | Select one-way/common route; duplicated C12 span needs distinct evidence or merge. |
| C14 / 37, handrails | D3 §6.2.11, 377–380 | Prove selected route actually has a ramp/open stair. |
| C15 / 38, lift | D3 §6.2.14, 390–391 | ГОСТ 33652 cabin source, ИУС 5-2026 correction and N/R/P reach unresolved. **No cabin dimension check.** |
| C16 / 39, entrance landing | D3 §6.1.4, 296–300 | Select with-ramp, no-ramp or R/adaptation branch; legacy square excluded. |
| C17 / 40, threshold | D3 §6.2.4, 345–346 | Identify accessible doorway and stated threshold exception; legacy value excluded. |
| C18 / 42, visitor toilet | D3 §6.3.2, 447–452 | Prove visitor-toilet object; select complete cabin branch. Span is 1,773 chars. |
| C19 / 30, envelope | D4 §5.1, 138–142 | Identify heated envelope, zone and stated project/norm values; no independent calculation. |
| C20 / 30, element | D4 §5.1, 138–142 | Same span as C19; merge or prove a separate element question. §5.2 calculation remains out. |
| C21 / 5, airborne sound | D5 §9.2/table 2, 289–300 | Row 7/8/9 depends on adjoining uses; row-bearing `npar_` 294 merges rows 1–11. Full context is 9,205 chars. |
| C22 / 5, impact sound | D5 §9.2/table 2, 289–300, or §9.3/table 3, 301–308 | Direction, use, row and footnotes differ. Table-1 note 5 is separate paragraph 238; no safe single-row `npar_`. |

The original line 3 insolation/SanPiN, line 4 daylight, line 24 generic fire compartment, line 41 blanket accessible-apartment percentage, and other out-of-category bullets retain the exclusions in discovery §3. **Every original checklist number and clause claim is excluded as a product rule**, including the numbers on rows whose topic is a candidate. The C15 source check at `e711cb0a0c930031e7c9d87960342681a8daf0e7` found the [official ГОСТ 33652 correction card](https://protect.gost.ru/gost/changesdetails/e4ce8ca2-4c41-445f-adb5-6bbfbe400b67) but not the correction's page text; it records `E=false` for N/R/P. C21/C22 must follow the table-row report's direction and footnote decisions, not its obsolete caption-only resolver result.

## Decision needed before a map SHA

1. A qualified owner records **include, revise or exclude for every C01–C22 branch**, the project date/use/work boundary and the exact complete target range. C05/C06 require a prescriptive target; C15 and C21/C22 remain excluded from numerical findings until their source/segmentation stops close. The owner may approve a smaller scope, but cannot label absent items as checked.
2. Acquire and compare the missing official D1–D5 amendment/source pages, the C15 ГОСТ correction and the applicable D6 law text for the design date. Record exact source page hashes and what changed. The edition audit expressly found no fully confirmed D1–D6 final edition.
3. Qualify the **full** repaired bundle through the existing import/custody path: 674 PDF document bindings and 28,920 object bindings, plus complete embedding evidence. A six-PDF backfill does not satisfy the qualification rule (`AR-PDF-CUSTODY-01` at `1a1d13fba8d8b4363422e756ed30fea03d98bad8`). Recheck current DB counts; the zero-binding fact is a dated measurement.
4. Produce canonical `map.json`, reviewed query vectors and exact `map_sha256` per approved scope/variant, then build a verified `nrs_` with the same snapshot and set Blob digest. Review the actual selected prompt part with labels/windows: the unchanged W57 limit is **22,000 characters** with no quote truncation.

The actual renderer's zero-window lower bound for one broad C01–C22 set was **86,379 (N), 87,810 (R), 76,118 (P office)** characters, each refused. The six technical groups F1=C01–C03, F2=C04–C10, A1=C11–C14, A2=C15–C20, S1=C21, S2=C22 each fit in tested *candidate* cases, but need reviewed source/branch completion and actual-window remeasurement (`AR-MAP-BUDGET-01` at `efe765bab44e2f2fdef205f83d69b2fec458dbf6`). A six-map pack design exists at `5e9a7e4b0d47d598ea612e116417d3ea64399acb`; it is a proposal, not a Run-form decision or approved map.

## v3 integration boundary

The existing `runs/v3_citations.py` can read a Run-pinned, Attempt-fenced verified set and make a local citation plan. It does **not** dispatch a provider, create a CITE StageResult or publish a finding. `AR-PROMPT-RUNTIME-01` must own the new registered profile/bundle identity, immutable Run selection, HTTP/pull/SSH request equality and provider provenance. `AR-CITE-PUBLISH-01` must recheck Attempt and set authority after the model effect, ground labels/quotes/values against exact saved bytes and source PDF, then write StageResult and accepted citations in one transaction. Neither task may infer map approval from this report, accept a free caller-supplied map SHA as authority, or fall back to v1 when a v3 set is absent.

The 22,000-character constraint and current one-set-per-Run pin mean any multi-scope product form needs explicit Run/aggregation ownership. The one-Run 128,000-character/$1.50 discussion concerned a different scope and is **not** authorization to raise this set limit or send all 22 items. Until that decision and the four gates above are complete, the active AR section remains on its existing profile. This task makes no contract, migration, runtime, corpus, deployment or legal-status change.

## Checks and rollback

This sheet is derived from immutable local Git reports named above, the original checklist, the frozen dev code and official registry cards checked on 2026-10-23. It does not repeat a DB or PDF read, source-page comparison or provider call. `tests/contract/program`: **28 passed**. The staged path and whitespace proof is part of the task handoff. Revert this task/report pair to remove the packet; there is no feature flag or data rollback.
