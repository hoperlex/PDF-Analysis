# AR-V3-BETA-SPANS-MEASURE-01 — the paragraph-row exporter and the first measurement of the C01–C22 candidate spans

**Task:** [AR-V3-BETA-SPANS-MEASURE-01](tasks/AR-V3-BETA-SPANS-MEASURE-01.md). **Base:** `30aa736776e7cfacbd7bb5c86d70345731aa557b`. **Snapshot:** `ns_01M59N8QNBVN91ACA2HCE6VE74` (674 documents, 350,194 paragraphs, 0 unreliable). **Measured:** 2026-10-26 on the stopped-then-started local custody stack of `AR-BETA-LOCAL-CUSTODY-01` (container `auditmanager-ar-beta-custody-postgres-1`, health `healthy`), database read in `READ ONLY` transactions only.

## Result

1. **The exporter exists.** `scripts/norms/export_paragraph_rows.py` turns a spans file into the exact `paragraphs` input of `map_pack`, or with `--measure` prints numbers and no corpus text. It reads through the public `norms` reads (`get_norm_document`, `list_norm_paragraphs`), inside one `REPEATABLE READ READ ONLY` transaction whose read-only state is checked before the first query.
2. **All 22 candidate spans of the sheet exist in the snapshot.** Every ordinal is present, there is no gap, and all 88 distinct paragraphs of the 20 distinct spans are reliable. Every figure the sheet quotes (1,417; 1,281; 1,139; 1,523; 1,773; 9,205 characters) is reproduced exactly.
3. **All six scopes fit the 22,000-character cap** in the target-only measure, on the beta-policy modes: F1 5,728, F2 11,958, A1 15,032, A2 14,143, S1 14,078, S2 14,078 (or 5,789 with the alternative C22 span). `map_pack build` exited 0 and `map_pack validate` exited 0 on both builds.
4. **Nothing is decided.** The measurement used a temporary, uncommitted decision file with placeholders; no span is approved, no mode changed, nothing signed. **No map produced this way may be promoted** (see "Placeholders and the limits of the measure").

## The exporter

```text
DATABASE_URL=… python scripts/norms/export_paragraph_rows.py --spans spans.json --snapshot ns_… --out .local/ar-v3-draft/paragraphs.json
DATABASE_URL=… python scripts/norms/export_paragraph_rows.py --spans spans.json --snapshot ns_… --measure
```

The spans file is a JSON list of `{norm_document_id, ordinal_first, ordinal_last}` (inclusive; overlaps are exported once). The output is `{paragraphs_version: ar-beta-map-paragraphs-v1, synthetic: false, norms_snapshot_id, paragraphs[]}` with the nine row keys `map_pack` requires (`norm_document_id`, `norm_paragraph_id`, `designation`, `title`, `ordinal`, `clause_number`, `page_label`, `text`, `reliable`). Before anything is written, the rows go through `map_pack.parse_paragraphs`, so what `map_pack` would refuse is never exported. `designation` is the reader's derived designation (`reader_designation` of the document slug), `title` the stored title, `page_label` the integer page as text.

Refusals (`REFUSED: <code>` on stderr, exit 2, no output file): `document_unknown`, `document_not_in_snapshot`, `ordinal_missing` (first or last ordinal of a span absent), `range_gap` (a hole inside a span), `paragraph_unreliable`, `paragraph_ordinal_duplicate`, `rows_not_accepted_by_map_pack`, `paragraph_text_not_encodable`, `spans_file_invalid` (one code for every shape defect, a 5,000-digit integer included), `spans_file_unreadable`, `snapshot_id_invalid`, `database_url_missing`, `database_url_invalid` (never echoes the value), `database_not_read_only`, `database_unavailable`, `database_refused`, `output_exists` (checked before the database is opened and again by `O_EXCL`, so a dangling symlink counts as taken), `output_unwritable`, `output_inside_repository_tree` (corpus text may only be written outside the tree or under the ignored `.local/`). The output is created with `O_EXCL | O_NOFOLLOW`, mode 0600; a failed write removes the half file. Re-running on the same inputs gives byte-identical rows (SHA-256 `ca560dc93a074dae5328d8b50591743e52c9e893bdf4ad004fe8667bb0fd99dc` for the 88 rows measured here; the file itself stays untracked).

## Method (so the figures can be reproduced)

Tree: this lane at the commit that adds the exporter, on base `30aa7367`. Spans: `docs/program/ar-v3-beta/spans.proposal.json` (the sheet's table; C22 lists both alternatives). The exporter's spans file is the distinct `(norm_document_id, ordinal_first, ordinal_last)` triples of that proposal (20 of them, because C13 repeats C12, C20 repeats C19 and C22's first alternative repeats C21). Commands run from the lane directory with the stack's `DATABASE_URL`:

1. `--measure` over the 20 spans (exit 0): the per-item tables below.
2. `--out` over the same 20 spans (exit 0): 88 rows; a second run into a second path produced the same SHA-256; a third run into the first path was refused `output_exists` (exit 2).
3. A temporary decision file per variant, written under the untracked `.local/ar-v3-draft/`: the 22 items with the **beta-policy modes** (14 provisional, 8 context-only), the sheet's spans as the only target of each item, the real snapshot id, content key and embedding build label read from the database (`bge-m3-dense-v1:characters-v2:1200`), and **placeholders** everywhere a decision, edition or vector would be: edition and branch text starts with `PLACEHOLDER-NOT-A-DECISION`, `edition_evidence` is empty, the six query-vector digests are 64 zeros and the model revision is 40 zeros. Variant `main` uses C22 = D5 289–300, variant `c22b` uses C22 = D5 301–308.
4. `python -m auditmanager.analysis.profiles.ar_v3.norm_map.map_pack build --decisions … --paragraphs … --out …` for each variant (exit 0 both), then `map_pack validate` on both packs (exit 0 both). The per-scope numbers equal the `prompt_part_characters` of `pack-summary.json`; a scratch script (not committed) also computed them for all six scopes independently of the cap so that an over-cap scope could not hide the later ones. None was over.

## Per item: the sheet's span against the snapshot

`Sheet-blocked` is the sheet's own stop (C15; C21 and C22): they are measured as they are and are not repaired. "Text chars" is the sum of the paragraph text lengths of the span (the sheet's "source chars").

| Item | Doc | Sheet span | Mode (policy) | Ordinals exist | Paragraphs | Text chars | Longest paragraph | Unreliable | Sheet-blocked |
|---|---|---|---|---|---|---|---|---|---|
| C01 | D1 | 132-137 | provisional | all 6/6 | 6 | 1,417 | 475 | 0 | no |
| C02 | D1 | 168-169 | provisional | all 2/2 | 2 | 526 | 329 | 0 | no |
| C03 | D1 | 213-214 | provisional | all 2/2 | 2 | 271 | 185 | 0 | no |
| C04 | D1 | 240-248 | provisional | all 9/9 | 9 | 1,281 | 332 | 0 | no |
| C05 | D6 | 489-492 | context-only | all 4/4 | 4 | 479 | 147 | 0 | no |
| C06 | D1 | 206-207 | context-only | all 2/2 | 2 | 713 | 656 | 0 | no |
| C07 | D1 | 100-100 | provisional | all 1/1 | 1 | 235 | 235 | 0 | no |
| C08 | D6 | 932-932 | context-only | all 1/1 | 1 | 311 | 311 | 0 | no |
| C09 | D2 | 343-345 | context-only | all 3/3 | 3 | 680 | 323 | 0 | no |
| C10 | D6 | 356-356 | context-only | all 1/1 | 1 | 268 | 268 | 0 | no |
| C11 | D3 | 301-304 | provisional | all 4/4 | 4 | 1,139 | 507 | 0 | no |
| C12 | D3 | 365-373 | provisional | all 9/9 | 9 | 1,523 | 284 | 0 | no |
| C13 | D3 | 365-373 | provisional | all 9/9 | 9 | 1,523 | 284 | 0 | no |
| C14 | D3 | 377-380 | provisional | all 4/4 | 4 | 646 | 336 | 0 | no |
| C15 | D3 | 390-391 | context-only | all 2/2 | 2 | 444 | 260 | 0 | **yes** |
| C16 | D3 | 296-300 | provisional | all 5/5 | 5 | 387 | 112 | 0 | no |
| C17 | D3 | 345-346 | provisional | all 2/2 | 2 | 539 | 301 | 0 | no |
| C18 | D3 | 447-452 | provisional | all 6/6 | 6 | 1,773 | 654 | 0 | no |
| C19 | D4 | 138-142 | provisional | all 5/5 | 5 | 597 | 154 | 0 | no |
| C20 | D4 | 138-142 | provisional | all 5/5 | 5 | 597 | 154 | 0 | no |
| C21 | D5 | 289-300 | context-only | all 12/12 | 12 | 9,205 | 2,367 | 0 | **yes** |
| C22 (alt 1) | D5 | 289-300 | context-only | all 12/12 | 12 | 9,205 | 2,367 | 0 | **yes** |
| C22 (alt 2) | D5 | 301-308 | context-only | all 8/8 | 8 | 2,590 | 788 | 0 | **yes** |

Documents (alias, `ndoc_` id from the sheet, stored paragraph count; all in the snapshot above): D1 `ndoc_01M59N9JD4VPS1C8ACDFC01BGG` 922; D2 `ndoc_01M59N9WF2B93HJQ3GYNR5FCWS` 740; D3 `ndoc_01M59N9WJPYS8FAQED34RPJF14` 879; D4 `ndoc_01M59N9VSS64AB4R6N6XX3Q74G` 901; D5 `ndoc_01M59N9W1JY06JA08QK08DE2HT` 811; D6 `ndoc_01M59N9Z9MD1RNV7QJDBFNC87X` 1,580. Ordinals are dense (0 to count-1) in each.

First and last paragraph ids of every span:

| Item span | First `npar_` | Last `npar_` |
|---|---|---|
| C01 132-137 | `npar_01M59N9JD76Z1P9NMG3GFQJFXA` | `npar_01M59N9JD7XGP58HFVBEKF0X17` |
| C02 168-169 | `npar_01M59N9JD7QMHBPYNPX8Y3DWYS` | `npar_01M59N9JD7WH6809DSCKJ23TKT` |
| C03 213-214 | `npar_01M59N9JD7F83055AH0YY9VYWK` | `npar_01M59N9JD70SV02QPGW5BKK9BC` |
| C04 240-248 | `npar_01M59N9JD7DQ8EGMMP5322EE4T` | `npar_01M59N9JD771XG5ZX3338651P0` |
| C05 489-492 | `npar_01M59N9Z9QN4CKGZF31T5Y59E8` | `npar_01M59N9Z9QNZ79W0F6NF3R5ET5` |
| C06 206-207 | `npar_01M59N9JD7C1PMAASD2DD18J72` | `npar_01M59N9JD7502PB4VEQKNR00WA` |
| C07 100-100 | `npar_01M59N9JD74NS77SSQYMGZFKP3` | `npar_01M59N9JD74NS77SSQYMGZFKP3` |
| C08 932-932 | `npar_01M59N9Z9SE5C0BE6WXWSSQS5B` | `npar_01M59N9Z9SE5C0BE6WXWSSQS5B` |
| C09 343-345 | `npar_01M59N9WF4AG09DXM1XDWMCZG7` | `npar_01M59N9WF4QX2HFCS42YTEYA24` |
| C10 356-356 | `npar_01M59N9Z9QPR4DYWGT0TC2AZ96` | `npar_01M59N9Z9QPR4DYWGT0TC2AZ96` |
| C11 301-304 | `npar_01M59N9WJSC6ZPCTMRAH22FF11` | `npar_01M59N9WJSSJ7TFKY1EJ1H3HGP` |
| C12, C13 365-373 | `npar_01M59N9WJSB370M00DYFYDS5ME` | `npar_01M59N9WJSCHWJCHRXG4RWWAFR` |
| C14 377-380 | `npar_01M59N9WJS1GR0EXPKCK67JGGB` | `npar_01M59N9WJSFD60RD4MA4DHXKNB` |
| C15 390-391 | `npar_01M59N9WJSTE5RG1K5D81NKMHM` | `npar_01M59N9WJSRXDHJRWY41PH6PMS` |
| C16 296-300 | `npar_01M59N9WJSP6F2C1R9VCW0AC6R` | `npar_01M59N9WJS8RHAGSSF2CNPAPB4` |
| C17 345-346 | `npar_01M59N9WJSXSZCFZKXNJX8GED6` | `npar_01M59N9WJSBZTMT6XQAAKSZG0K` |
| C18 447-452 | `npar_01M59N9WJS7M96V5JQHYPTNP71` | `npar_01M59N9WJSG0GM8DXGPEX3B7JR` |
| C19, C20 138-142 | `npar_01M59N9VSV5B5M1PA0W4ZMVA3N` | `npar_01M59N9VSVRWCMWHW8RX6P9BMJ` |
| C21, C22 alt 1 289-300 | `npar_01M59N9W1MRAP221SWF5Z40NGT` | `npar_01M59N9W1MQNXE72MFHNWECQ6E` |
| C22 alt 2 301-308 | `npar_01M59N9W1M20X2YZRQPQ7NAEB7` | `npar_01M59N9W1M33A9954S3R58JG45` |

Text digests (SHA-256 of the paragraph texts joined by one line feed), to detect any later change of these spans:

| Item span | `text_sha256` |
|---|---|
| C01 132-137 | `f4a4ed3322ca7474942febcdd2642c7a3bc7a46a811157638210ac3a046b37bb` |
| C02 168-169 | `920587204b72c37d3e1ac5ca3a7091500dee6ebce1d0083653ca7b3a3cca6455` |
| C03 213-214 | `c070968bb6d308f2bd8e5bfdd072994350b31da856dfea0b5e39efcf45fdab66` |
| C04 240-248 | `37771dae41a9a6d17eb119e7e1fd10b23a29afd25d7f60a999246136aca19dba` |
| C05 489-492 | `da011b33cac5b5f957ff4982e202a9d66b8a3cbae033758325e337bff3dfe7d8` |
| C06 206-207 | `c12d43aea69cdf64cbe950187b4e64e56d71d31685b725fbd0e4457cf40efc34` |
| C07 100-100 | `9da6ded4d796afab8f6fe1a80de6d4af7dca8fdee4a1dbaeb86ef39ba72c59d9` |
| C08 932-932 | `1d53c6939b32b303c44d3336d1b03fdb8b6701b31c1a1cdb101943faf2371187` |
| C09 343-345 | `29dd13249ab63f4d4fff3195cbb48ee86d3d102fa00414835078e271b74db26a` |
| C10 356-356 | `4d280f5f71b79751e581acfa8cf38c62abbe0c9c9be80b9d6b29349b900be2ef` |
| C11 301-304 | `fa6cfc7d8098dda8f182440ad726605a832ae779ce6ecc7c194ca90463d9fb0f` |
| C12, C13 365-373 | `c8a83d851863ad563b49ee2e5c3e7a4e0704ba1e77f27ab644c242a33b99e6d0` |
| C14 377-380 | `bcb4a5c95f384c6b2cbcae2de0425716c864cfa604090c80285487d5c217bf61` |
| C15 390-391 | `f2774c185f41922e143449a880fbca5e8b59bdab955a102fdbf6f52faaf25663` |
| C16 296-300 | `4da748f3e2f2d0a5eba11fda484fe12e36d7e5e1c69a32d7d1552135abbaf83b` |
| C17 345-346 | `8473db8e5a808897b0dd90c656efa6ca14e1108a98407357752abaa26384dc49` |
| C18 447-452 | `232c80055da4c55b51b84d3fbc769fc681f284c0e95e30e304b214aaae762aae` |
| C19, C20 138-142 | `a976918705522983bbb12cda6c79ac1a5e17908e46e357e583684724ba4c26d1` |
| C21, C22 alt 1 289-300 | `7bf125c79f102a9a40e99a61e230dfa8176cfd41f439d3dfa67fe0e868f7e697` |
| C22 alt 2 301-308 | `6aaf5f935498379773129a9ec68104ad8ec09b83cdcb42017a7b37b8b381814e` |

## Per scope: the target-only prompt part against the 22,000 cap

Basis: the target rows of the scope's items, zero retrieved windows (`prompt_part_basis` of the pack summary). The part grows when the real selector adds retrieved windows, so each figure is a lower bound; a pack that fits here can be refused at promotion, never the reverse. Rows are counted per item (a span shared by two items of a scope is rendered twice, as the real renderer does).

| Scope | Items | Provisional / context-only | Rows | Mapped docs | Span text chars (sum over items) | Prompt part chars | Cap | Headroom | Within cap |
|---|---|---|---|---|---|---|---|---|---|
| F1 | C01–C03 | 3 / 0 | 10 | 1 | 2,214 | 5,728 | 22,000 | 16,272 | yes |
| F2 | C04–C10 | 2 / 5 | 21 | 3 | 3,967 | 11,958 | 22,000 | 10,042 | yes |
| A1 | C11–C14 | 4 / 0 | 26 | 1 | 4,831 | 15,032 | 22,000 | 6,968 | yes |
| A2 | C15–C20 | 5 / 1 | 25 | 2 | 4,337 | 14,143 | 22,000 | 7,857 | yes |
| S1 | C21 | 0 / 1 | 12 | 1 | 9,205 | 14,078 | 22,000 | 7,922 | yes |
| S2 (C22 = 289–300) | C22 | 0 / 1 | 12 | 1 | 9,205 | 14,078 | 22,000 | 7,922 | yes |
| S2 (C22 = 301–308) | C22 | 0 / 1 | 8 | 1 | 2,590 | 5,789 | 22,000 | 16,211 | yes |

Every other scope is the same in both variants. Per-item share of the rendered row JSON (characters, separators not counted): F1 C01 3,481, C02 1,217, C03 963; F2 C04 4,380, C05 2,218, C06 1,404, C07 578, C08 745, C09 1,852, C10 703; A1 C11 2,694, C12 5,022, C13 5,027, C14 2,206; A2 C15 1,225, C16 2,332, C17 1,318, C18 4,110, C19 2,538, C20 2,538; S1 C21 14,009; S2 C22 14,009 (alt 1) or 5,724 (alt 2). The part adds about 400 characters of identity and metadata per row (14,009 rendered against 9,205 of text over 12 rows), so row count matters as much as text length.

## Discrepancies and observations (against the sheet)

**Confirmed, no ordinal discrepancy.** All sheet ordinals exist; no gap, none unreliable. The sheet's quoted lengths are exact: C01 1,417; C04 1,281; C11 1,139; C12 1,523; C18 1,773; C21 9,205. The sheet's "per-item guide" they are said to exceed is not defined anywhere in this tree (the budget report it comes from lives on another line), so only the figures are confirmed, not the comparison.

**Clause labels match the sheet's section numbers.** In D1–D5 the first paragraph of each span carries exactly the stored clause number the sheet names (4.2.7, 4.2.19, 4.3.3, 4.4.1, 4.3.1, 6.2.1.9, 6.1.5, 6.2.9, 6.2.11, 6.2.14, 6.1.4, 6.2.4, 6.3.2, 5.1, 9.2, and 9.3 for the second C22 alternative), and the paragraph after the last one starts the next clause or a heading. So each of these spans is a complete clause: it neither stops short nor runs into the next one. Only the first paragraph of a span carries a clause number; the continuation paragraphs have none, as stored.

**D6 spans are parts of an article.** For D6 the stored `clause_number` is the part number inside an article, not the article. The article heading nearest before each span was read locally: C10 (ordinal 356, part 2) sits under the heading at ordinal 354 for article 28; C05 (489–492, from part 3) under the heading at 480 for article 40, and the next paragraph (493) is a chapter heading, so the span runs to the end of the article; C08 (932, part 2) under the heading at 926 for article 90. These match the sheet's "article 28 / 40 / 90". C05 is the last part of article 40 only (parts 1 and 2 at ordinals 481 and 485 are outside the span); C08 is one part of article 90 and the paragraph after it (933) is an unnumbered amendment note.

**C07 is a mid-clause fragment.** Ordinal 100 carries no clause number; the nearest numbered clause before it is 4.2.1 (ordinal 96, under the heading 4.2 at 95), and the neighbours 99 and 101 are unnumbered too. So the span is one continuation paragraph of 4.2.1, neither its opening nor its end. The sheet gives no section for it ("explicit 100–100"), so this contradicts nothing, but the owner should know that the clause's opening paragraphs (96–99) are outside the span.

**Duplicated spans confirmed.** C13 repeats C12 (365–373, 1,523 chars) and C20 repeats C19 (138–142, 597 chars), as the sheet says. In the measure they are rendered twice, which costs A1 5,036 and A2 2,543 characters (their rows plus separators); without the repeat A1 would be 9,996 and A2 11,600. S1 and S2 (alternative 1) are the same 12 paragraphs, so the same 14,078 characters appear in two scopes.

**C21/C22 table rows.** The span 289–300 holds 6 body, 2 heading and 4 table-row paragraphs. The four table rows are 2,083 (ordinal 294), 1,962 (295), 1,898 (297) and 2,367 (298) characters, which is why this span is 9,205 characters from 12 paragraphs; the sheet's remark that paragraph 294 merges several rows is consistent with its size but this lane did not re-read the table. The 301–308 alternative has two table rows (788, 483).

**Blocked items measured as they are.** C15 (2 paragraphs, 444 chars), C21 and both C22 alternatives exist and fit; the sheet's stops (missing correction text, unresolved table row, direction and footnote) are source and decision gaps that a character count cannot close, and they are untouched. The policy keeps C15, C21 and C22 `context_only`.

**Not compared.** The sheet's earlier zero-window figure for one broad C01–C22 set (86,379 N, 87,810 R, 76,118 P office) was a different composition and branch; the six scopes here sum to 75,017 only because each is measured on its own candidate spans (and S1 and S2 repeat one span). The two are not comparable and no conclusion is drawn.

## Placeholders and the limits of the measure

- **No map built here may be promoted.** The decision file that produced the maps was a measurement device: edition and branch text are marked `PLACEHOLDER-NOT-A-DECISION`, `edition_evidence` is empty (so every provisional item is `edition_evidence_missing` in the summary), the six BGE-M3 query-vector digests are 64 zeros and the model revision 40 zeros, `review_state` is `pending_expert`, and there is no attestation. The six map digests that came out are digests of placeholder maps and are deliberately not recorded here.
- The temporary decisions, both packs, the rows file (corpus text, 78,852 bytes, mode 0600) and the measurement JSON stay under the untracked `.local/ar-v3-draft/` of the lane worktree. No corpus text is in git; the only corpus-derived values committed are ids, ordinals, counts, character lengths and digests (the clause labels above are structural labels, not paragraph text).
- The rows carry the **reader's derived designation** (for example the document's `СП nn.13330.yyyy`), not a reviewed designation. The real set takes a reviewed designation from the owner; if it differs in length, every prompt part changes by (difference × rows). D6's derived designation is 61 characters, the others 15–16.
- The measure is target-only and so a lower bound; retrieved windows are only known at promotion. Headroom therefore shows how much room the windows have, not that the final parts fit.
- Modes are the policy's (14 provisional, 8 context-only). Changing a mode or a span changes these numbers.

## What is still owed (none of it is done or claimed here)

1. **The owner's decisions** for each of C01–C22: include, revise or exclude, the project date, use and work boundary, and one exact span per item (for C22 a choice between 289–300 and 301–308; whether C13 and C20 stay separate from C12 and C19). Until then `spans.proposal.json` is only the sheet's candidate list.
2. **Official edition pages** and their SHA-256 for every provisional item (the policy names the sources), the C15 correction text and the D6 amendment chain for the design date.
3. **BGE-M3 query vectors** for each scope and their provenance (`norms.embedding embed-texts`); the BGE runtime is absent on this host.
4. **A reviewed decision file** (real branch and edition text, evidence, reviewed designations) replacing the placeholders, then `map_pack build` on rows exported with this tool, and a re-measure of the actual prompt part with retrieved windows at promotion.
5. **The expert's signature** on the six exact map digests, recorded outside the tool.
6. A refresh of this measure if the snapshot, the policy, a mode or any span changes (the `text_sha256` table above detects a change of text).

## Verification

From the lane directory. Gate-equivalent invocation: `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages); PYTHONPATH=src:$BS /root/projects/PDF-Analysis/.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider <files>`.

- `tests/unit/scripts/test_export_paragraph_rows.py`: **91 passed, 3 skipped** without a database; **94 passed** with `EXPORT_PARAGRAPH_ROWS_TEST_DATABASE_URL` set to the started custody stack (the three real-database tests: the transaction rejects an `UPDATE` as read-only, a span measures and exports with 1,417 characters, an unknown document is refused). One test runs the exporter's rows through the real `build_scope_maps` and `validate_scope_maps` on all 22 policy items.
- `tests/contract/norm_map`: **117 passed** (unchanged code, run as a regression check).
- Task governance check prints `[]`.
- `git diff --check` clean; the staged non-document files contain no Cyrillic word of 12 or more letters (`rg` count empty).

### Mutation probes (single edit to the script, run the test file, then revert)

26 probes; every one went red after the first probe set was repaired (see M26). Failing test in brackets.

- Read-only and output: proof of `transaction_read_only` removed (M01, 6 failed) [`test_a_read_write_transaction_is_refused`]; `O_EXCL` replaced by `O_TRUNC` (M02) [`test_existing_file_is_never_overwritten`, `test_a_dangling_symlink_counts_as_taken`]; mode `0o600` to `0o644` (M03) [`test_created_exclusively_with_mode_0600_whatever_the_umask`]; early `output_exists` check removed (M18) [`test_existing_output_is_refused_before_the_database_is_opened`]; half file kept after a failed write (M22) [`test_a_failed_write_leaves_no_half_file`]; repository-tree guard removed (M09) [`test_inside_the_repository_tree_is_refused`].
- Refusals: unreliable guard (M04), endpoint check (M05), gap check (M06), snapshot check (M07), unknown-document check (M08), duplicate-ordinal check (M20), `map_pack` parse before writing (M10), unknown reliability value read as unreliable (M17) — each red in the test named after it.
- Spans file: `bool` accepted as an ordinal (M11), span-length bound removed (M12), spans not deduplicated (M13), identity parse skipped (M26): red in `test_every_defect_is_refused_with_one_code` or `test_valid_file_is_sorted_and_deduplicated`.
- Format: `synthetic` written as `true` (M14), `page_label` not stringified (M24): red in `test_rows_are_the_exact_map_pack_input` and `test_the_rows_go_through_the_real_map_builder_and_validator`.
- Adapter and CLI: paging does not stop at the highest ordinal (M15), non-advancing cursor guard removed (M16), `not_found` not mapped to `None` (M19); exit code 1 instead of 2 (M21, 8 failed); measure output carries paragraph text (M23) [`test_the_report_carries_no_paragraph_text`]; the database URL echoed in a refusal (M25) [`test_invalid_database_url_never_echoes_the_value`].
- **M26 first survived.** A guard rejecting a trailing line break in an identity was dead code: the shared identity parser already refuses it (`0da149bb`). The guard was removed rather than kept untested, and the probe was re-aimed at the parse call itself (8 failed).

## Known limitations and integrator notes

- **Needs a started stack.** Only the optional test class and the real measurement need the custody container; every other test is container-free. The container was started with `docker start auditmanager-ar-beta-custody-postgres-1` and stopped again with `docker stop auditmanager-ar-beta-custody-postgres-1` at the end of the lane; no other docker command and no other container was touched.
- **The exporter reads all paragraphs of a document up to the highest requested ordinal** (pages of 500) because the public read pages from the start; for the largest document here (D6, 1,580 paragraphs, highest ordinal 932) that is two pages. A span past a few thousand ordinals would read proportionally more.
- `--measure` prints the stored clause labels of the first and last paragraph; they are structural labels. It prints no paragraph text.
- The script imports `map_pack` and the public `norms` reads only; it adds no dependency, contract or migration. `spans.proposal.json` is read by no code.
- Merge order: independent of the other lanes (five new paths). Rollback: forward-revert the five files.
