# AR-V3-ACTIVATION-PREP-01 — decision file, query texts and seal skeleton for the AR v3 beta

**Task:** [AR-V3-ACTIVATION-PREP-01](tasks/AR-V3-ACTIVATION-PREP-01.md). **Lane:** AR-B, part 1 (authoring), of wave PW5. **Base:** `b32c64f3` (`integration/ar-close-1026`). **Authored:** 2026-10-27. **Authority read:** `R-146ba` (the activation decisions are the integrator's, no subject-matter expert takes part; accepted risks `A-10` and `A-11`) and `R-146bb` (the beta runs on synthetic documents). **Spec:** section 3 (decision schema, what can be proposed), section 6 (attestation wording) and section 8, steps 3 and 7, of [AR-V3-ACTIVATION-FEASIBILITY-01](AR-V3-ACTIVATION-FEASIBILITY-01.md).

No database, container, network, download or vector was used. No corpus text was read or written: the files hold ids, ordinals, digests and authored text. The files are in [`ar-v3-beta/`](ar-v3-beta/README.md); their state is in the first table.

## 1. What exists

| File | State | What remains |
| --- | --- | --- |
| `ar-v3-beta/decisions.json` | complete except one field | `query_vectors.sha256_by_scope`: six placeholders (64 zeros), until the vectors exist (step 6 of the plan) |
| `ar-v3-beta/query-texts.json` | complete | nothing; the integrator embeds it |
| `ar-v3-beta/scopes.json` | skeleton | six `map_sha256` placeholders (not hex, so `seal` refuses them), until `map_pack build` has run |
| `ar-v3-beta/scope-definitions.json` | complete | nothing |
| `ar-v3-beta/README.md` | complete | the mapping note, the placeholders, the attestation wording, the order of the steps |
| `tests/unit/analysis/ar_v3_norm_map/test_decisions_file_shape.py` | complete | 53 pass, 1 is skipped unless `AR_V3_DECISIONS_REQUIRE_FINAL=1` |

## 2. Verification, with the output

The real `map_pack` CLI needs a paragraph file for `build` and a written pack for `validate`; neither can exist without the database export (step 4). So the CLI was driven as far as it goes, and the decision file was also given to the library function the CLI calls first. Commands from the lane directory, `PYTHONPATH=src:$BS`, `.venv/bin/python`.

```text
$ python -m auditmanager.analysis.profiles.ar_v3.norm_map.map_pack build --decisions docs/program/ar-v3-beta/decisions.json --paragraphs <scratch>/no-such-paragraphs.json --out <scratch>/pack-a
REFUSED: file_unreadable:no-such-paragraphs.json
exit=2          # no pack written (the output directory does not exist afterwards)
$ python -m ...map_pack validate --maps <scratch>/pack-a --paragraphs <scratch>/no-such-paragraphs.json
REFUSED: file_unreadable:pack-summary.json
exit=2
$ python -m ...map_pack build --decisions <scratch>/decisions-upgraded.json ...     # control: C05 changed to provisional_citation
REFUSED: context_only_upgrade_refused:C05
exit=2          # a decision defect is refused BEFORE the paragraph file is read
$ python -m auditmanager.runs.v3_pack_cli seal --scopes docs/program/ar-v3-beta/scopes.json --reviewer x --capacity x --reviewed-at 2026-10-27 --decision-ref x --scope-statement x --out <scratch>/pack.json
v3-pack REFUSED spec_value: every map_sha256 must be a lowercase SHA-256
exit=2          # refused before any database is reached
```

`build_scope_maps(parse_decisions(<decisions.json bytes>))`, the first thing `build` does, accepts the file: six maps of 4,958 / 6,350 / 6,487 / 8,399 / 1,204 / 1,204 bytes, six distinct digests (not recorded: they are digests of maps that still carry the placeholder), `review` is `None`, so the summary will say `pending_expert`. The only refusal of the CLI is therefore the missing paragraph rows; **everything in the file that does not need a paragraph row is accepted by the tool.**

**Finding: the tool does not refuse the vector placeholder.** `map_pack` checks only that a query-vector digest is 64 lowercase hex characters; 64 zeros pass, and `AR-V3-BETA-SPANS-MEASURE-01` built maps on such zeros for the same reason. Left in, the placeholder would build, validate and promote. So the guard is outside the tool: the shape test requires the word `PLACEHOLDER` in the `comment` exactly while the zeros are there, refuses a half-replaced set, and fails under `AR_V3_DECISIONS_REQUIRE_FINAL=1` until the digests are real:

```text
$ AR_V3_DECISIONS_REQUIRE_FINAL=1 pytest -k final_state tests/unit/analysis/ar_v3_norm_map/test_decisions_file_shape.py
FAILED ...::test_final_state_has_no_placeholder_left     (- final / + placeholder)      1 failed, 52 deselected
$ pytest tests/unit/analysis/ar_v3_norm_map/test_decisions_file_shape.py
53 passed, 1 skipped
```

**What the paragraph-dependent checks will test and this lane could not:** that the first and last `npar_` of each target are the paragraphs at the declared ordinals, that the rows are reliable, that each target's designation equals the exported rows' designation, and the 22,000-character cap. A dry run on rows built from the same file would prove nothing about them and was not made.

**Mutation probes** (one edit to the test module's guard, run, restore with a copy or `git checkout`; the failing tests are named in brackets). Besides the 43 mutation cases the module carries (every one makes its guard report its code), five edits to the guard code itself: currency guard disabled (2 red, `currency_claimed`, `official_check_claimed`); mixed-vector guard disabled (1 red, `vector_digests_mixed`); span-against-proposal guard disabled (2 red, `span_moved`, `c22_takes_the_other_candidate`); digit and designator guard of the query texts disabled (2 red); review-block guard disabled (1 red). **One probe survived and was repaired:** the clause `modes != policy_modes` in the mode check could be removed with no test going red (the two clauses beside it imply it), so it was deleted and the policy split got its own test; changing the hard-coded split then turns 3 tests red.

## 3. The choices and their evidence

| Choice | Evidence |
| --- | --- |
| 14 `provisional_citation` and 8 `context_only` (C05 C06 C08 C09 C10 C15 C21 C22), exactly the policy | `beta_sources.json`; the tool refuses any upgrade, and the shape test pins the split both ways |
| identity: snapshot `ns_01M59N8QNBVN91ACA2HCE6VE74`, content key `2026-07-23..2026-08-20+17d+121r.0a1bafe103ff`, build `bge-m3-dense-v1:characters-v2:1200`, scenario `new_multi_apartment_residential_F1.3` | the report section 3.2; the tool checks the snapshot and the scenario against the policy |
| targets: one per item; documents, ordinals from `spans.proposal.json`; first and last `npar_` copied by script from the table of `AR-V3-BETA-SPANS-MEASURE-01` (not typed) | the script parsed the table and the shape test compares every ordinal with the proposal; 22 of 22 |
| `kind`: `clause` for D1 to D4 and D6 spans (D2 included: C09 is one clause); `range` for C07 (a one-paragraph continuation of a clause, per the measure); `table` for C21 and C22 | report section 3.2; C09's `clause` is my application of the same rule, the report does not name D2 |
| `designation`: `СП 1.13130.2020`, `СП 54.13330.2022`, `СП 59.13330.2020`, `СП 50.13330.2024`, `СП 51.13330.2011`; D6: `Федеральный закон от 22.07.2008 N 123-ФЗ (ред. от 25.12.2023)` | the five names are the sheet's and have the 15 to 16 characters the measure gives for the exporter's labels. **D6 differs from the report's «123-ФЗ»**: `map_pack validate` requires equality with the exported rows' designation, which is the reader's label; the measure says it is 61 characters for D6, and the unit test of `reader_designation` has exactly this slug and label, 61 characters. The string is inferred, not read from the database: check b of the README catches a wrong one at the export |
| `edition`: «редакция локального корпуса (ConsultantPlus), изменения не сверены с официальной редакцией» | the integrator's wording; the repository's corpus documents (`W33-CORPUS.md`, `W39-CORPUS.md`) record ConsultantPlus-derived text. It says nothing about currency |
| `branch`: id `N`; applicability = scenario + project date «не задана: бета на синтетических документах (R-146bb)» + the sheet's approval question + «применимость не проверена человеком...» | the sheet's table; R and P are outside the scenario and not mapped. Each text is 458 to 629 characters |
| `edition_evidence`: empty on all 14 | nothing was fetched or compared; the summary will list the 14 under `edition_evidence_missing` |
| C13 and C20 kept as separate items on the spans of C12 and C19 | the tool needs all 22 ids; the measure's cost: 5,036 and 2,543 characters, all six scopes stay under 22,000. The applicability sentences of C13 and C20 say that the span repeats another and why it stays |
| **C22 on D5 ordinals 289 to 300** (not 301 to 308) | A judgement. (1) The discovery table (`AR-NORM-MAP-DISCOVERY-01` section 2) anchors C22 on the same table-2 row paragraph as C21 and says to pair it with the clause that opens 289 to 300; the sheet places that row-bearing paragraph at ordinal 294, inside 289 to 300. The smaller span could omit the anchor. (2) The sheet lists 289 to 300 first. (3) Cost: 14,078 characters against 5,789, headroom 7,922 under the cap; the same 12 paragraphs then appear in S1 and in S2. (4) Both are `context_only`, so a wrong choice cannot become a citation. I did not read the database or the section 9.3 table; what §9.3/table 3 holds is not in any repository document I read beyond the sheet's remark that direction, use, row and footnotes differ |
| no `review` block | report section 6: the honest state is `pending_expert` |
| `query_vectors`: profile `bge-m3-dense-v1`, revision `5617a9f61b028005a4858fdac845db406aefb181`, digests = placeholder | the frozen profile; the digest rule is proposed in the README because the tool states none |
| 22 query texts, 230 to 314 characters, no digit, no designator, no clause number | authored from the topic label of each item (`git show 281a5418:docs/program/AR-NORM-MAP-DISCOVERY-01.md`, section 2; the commit is in the shared repository and is not an ancestor of this tree) and the sheet's approval question. The discovery table also quotes 22 short corpus excerpts; none was copied: a scratch comparison found at most a 5-word stock phrase in common. The profile has no instruction prefix (`profile.py`), so the text is embedded as written. Token bound: tokens <= characters + 2 = 316 for the longest, against the limit of 512; the tokenizer is not on this host, so the count is a bound and not a measurement |
| `scopes.json`: profile `ap_01M5M28ZCDD8VPSP1BTAEW92YE`, bundle `pb_01M5M28ZCDVCR37BX1884JGSPM`, builder `norm-retrieval-set-prep-v1`, chunking `characters-v2:1200` | the constants of `v3_profile.py` and `norms.public`, compared by the shape test |
| scope membership F1 C01-C03, F2 C04-C10, A1 C11-C14, A2 C15-C20, S1 C21, S2 C22 | `scope_partition.py`; `scope-definitions.json` is a separate file because `seal` accepts exactly three root keys in `scopes.json` |

## 4. Things the integrator should know

1. **A context-only item is still sent.** The tool has no exclude state; `context_only` forbids a citation of the span and nothing more. The eight policy items put about 21,300 characters of source text into the prompt parts of F2, A2, S1 and S2. The README says this plainly; so does the `comment` of the decision file.
2. **Export 20 spans, not 19.** The decisions use 19 distinct triples (C22's second candidate is not used). The earlier measure exported 20 (88 rows, digest `ca560dc9...`); use the 20 of `spans.proposal.json` so the export is comparable with it. The extra eight paragraphs do not disturb `build`.
3. **The measured scope sizes stay valid only if the inferred D6 label is right** (the measure used the reader's labels; the lengths of D1 to D5 labels are equal to the names here).
4. **`/root/projects/PDF-Analysis/.local/ar-v3-draft/` now exists in the main checkout** (it did not when the feasibility report was written; two files by name). It is another session's and was not read.
5. The attestation of the manifest is Russian text the screen shows verbatim; the values are in the README, copied from the feasibility report.

## 5. Open questions

1. **C22:** keep 289 to 300, or take 301 to 308 (saves 8,289 characters of context, risks omitting the row)? Either is `context_only`.
2. **D6 label:** the reader's 61-character label (used), or the short «123-ФЗ» (the report's choice; then the exported rows' designation for the D6 document must be relabeled, because `validate` demands equality)?
3. **Evidence:** fill `edition_evidence` for the six items with a fetchable comparator (C01 C02 C03 C11 C19 C20) or leave all fourteen empty? Empty is the honest state today and does not block the build.
4. **Per-scope vector digest rule** (README): accept or replace; it is recorded and never read by the tool.
5. **Reviewer string** of the seal: the report proposes «ИИ-интегратор (Claude Code), сессия integration/ar-close-1026»; the integrator may name itself otherwise.

## 6. Assumptions an expert would still check

- That each span is the right clause for its check. The measure confirmed the spans exist, are dense and reliable and open at a clause label; nobody compared them with the project question.
- That branch `N` is enough: R (reconstruction) and P (public-use room) are not mapped; some topics (C11, C16) have a reconstruction exception inside the span.
- That the local corpus text equals the official edition of each norm, and what the amendments change (D1 changes 2 and 3, D2 changes 1 and 2, D3 changes 1 to 4, the base of D4 and D5, the 123-ФЗ chain). The `edition` label says only that nothing was compared.
- C07 is a continuation paragraph without the opening of its clause; C12 and C13, C19 and C20 and, in S1 and S2, C21 and C22 repeat spans.
- The wording of the 22 query texts: they were written from topic labels, and **no retrieval was tried** (no vectors, no windows), so whether each finds its span is unmeasured.
- The Russian applicability sentences repeat the sheet's questions; they decide nothing.

## 7. Commands

| Purpose | Command (from the worktree; `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages)`) |
| --- | --- |
| shape test | `PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/ar_v3_norm_map/test_decisions_file_shape.py` |
| same, final state required (before sealing) | `AR_V3_DECISIONS_REQUIRE_FINAL=1` plus the line above |
| tool accepts the decisions | `PYTHONPATH=src:$BS .venv/bin/python -c "from pathlib import Path; from auditmanager.analysis.profiles.ar_v3.norm_map import map_pack as m; print([x.scope_id for x in m.build_scope_maps(m.parse_decisions(Path('docs/program/ar-v3-beta/decisions.json').read_bytes())).maps])"` |
| spans file for the export (expect 20) | `python3 -c "import json;d=json.load(open('docs/program/ar-v3-beta/spans.proposal.json'));t=sorted({(c['norm_document_id'],c['ordinal_first'],c['ordinal_last']) for i in d['items'] for c in i['candidates']});print(len(t));json.dump([dict(norm_document_id=a,ordinal_first=b,ordinal_last=c) for a,b,c in t],open('.local/ar-v3-draft/spans.json','x'))"` |
| export, measure (no text) | `DATABASE_URL=... python scripts/norms/export_paragraph_rows.py --spans .local/ar-v3-draft/spans.json --snapshot ns_01M59N8QNBVN91ACA2HCE6VE74 --measure` |
| export, rows | the same with `--out .local/ar-v3-draft/paragraphs.json` instead of `--measure` |
| build the six maps | `PYTHONPATH=src python -m auditmanager.analysis.profiles.ar_v3.norm_map.map_pack build --decisions docs/program/ar-v3-beta/decisions.json --paragraphs .local/ar-v3-draft/paragraphs.json --out .local/ar-v3-draft/pack` |
| validate | `... map_pack validate --maps .local/ar-v3-draft/pack --paragraphs .local/ar-v3-draft/paragraphs.json` |
| query-vector requests | the snippet in the README, then `python -m auditmanager.norms.embedding embed-texts --in ... --out ...` |
| seal, verify | the commands in the README |
| governance of the task file | `BS=...; PYTHONPATH=src:$BS /root/projects/PDF-Analysis/.venv/bin/python -c "import sys;sys.path.insert(0,'tests/contract/program');import test_wave_governance as t;print(sorted(t.governance_findings(open('docs/program/tasks/AR-V3-ACTIVATION-PREP-01.md',encoding='utf-8').read())))"` (prints `[]`) |
