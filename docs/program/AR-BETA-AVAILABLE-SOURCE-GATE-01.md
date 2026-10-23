# AR beta: available-source policy

**Task:** [AR-BETA-AVAILABLE-SOURCE-GATE-01](tasks/AR-BETA-AVAILABLE-SOURCE-GATE-01.md). **Base:** `54585633bbae7ff4b12f296afdb1c96be0e5f485`. **Policy digest:** `9d3b7e53b512fbde1ea478a77a63c3c48042e85ddc50d57c96241c79bcb91d58`.

The owner asked to proceed toward beta with obtainable public material. The new [source policy](../../src/auditmanager/analysis/profiles/ar_v3/norm_map/beta_sources.json) accounts for all C01–C22 once in the frozen F1/F2/A1/A2/S1/S2 composition. It separates **14 provisional citation candidates** from **8 context-only topics**. Provisional means the local corpus text and at least one open text source are named; it is *not* a claim of the effective legal edition, exact page match, project applicability, a reviewed map or a publishable citation. The validator pins exact canonical policy bytes and refuses a missing/changed policy, duplicate or omitted item, unknown source, card-only citation, and attempted promotion of known gaps C05/C06/C08/C09/C10/C15/C21/C22.

The owner subsequently selected the beta scenario **new multi-apartment residential building, Ф1.3** and required topics without a confirmed edition or table row to read **"requires expert review"**, with no numeric conclusion. The exact policy now pins `scenario=new_multi_apartment_residential_F1.3` and `numeric_output_policy=expert_review_required`; neither value grants source applicability by itself. All 14 provisional candidates still need project facts and edition review before a numeric finding.

| Scope | Provisional candidates | Context-only topics and reason |
| --- | --- | --- |
| F1 | C01–C03 | none |
| F2 | C04, C07 | C05/C06 lack a selected prescriptive target; C08/C10 need the current 123-ФЗ amendment chain and project facts; C09 needs D2 change text and object scope. |
| A1 | C11–C14 | none; all still require D3 final-edition/branch comparison. |
| A2 | C16–C20 | C15 depends on the missing ИУС 5-2026 page and revised D3 §6.2.14. |
| S1/S2 | none | C21/C22 need the exact table row, direction and footnotes; the canonical paragraph merges rows. |

## Public evidence used to grade availability

- D1: [МЧС change №1 PDF](https://78.mchs.gov.ru/uploads/resource/2023-12-27/izmeneniya-1-k-svodu-pravil-sp-1-13130-2020-sistemy-protivopozharnoy-zashchity-evakuacionnye-puti-i-vyhody_17036645221069199865.pdf) is official; [№2](https://nav.tn.ru/cloud/iblock/004/0044d6c98caea587053ff76862c640ee/SP-1.13130.2020-_Izmenenie-_2_.pdf) and [№3](https://nav.tn.ru/cloud/iblock/603/6039b86f35b6072b4238a8c93424fb2f/SP-1.13130.2020-_Izmenenie-_-3_.pdf) are open public copies, not publisher authentication. The №2 copy changes §4.2.7 and §4.4.1, so C01/C04 cannot inherit the base text unreviewed. The [official Росстандарт card](https://protect.gost.ru/sp/changesdetails/de574ad5-67fc-4e31-a0a5-a793c94b1cc7) confirms №3 identity/date but is not its body.
- D3: [ФАУ ФЦС base PDF](https://api.faufcc.ru/api/assets/032a3244-a958-4637-b396-dd141886e4ff) and an [open consolidated public copy](https://nav.tn.ru/documents/regulatory/ast_s_sp_59_13330_2020/) provide comparison material, while the four original amendment bodies remain unverified. The reviewed historical report `AR-OFFICIAL-MIRRORS-D1-D3-01` at `2c61f5ac` records that stop.
- D4: the [ФАУ ФЦС requirements PDF, pages 2–3](https://api.faufcc.ru/api/assets/84a94ceb-75b9-4579-8c41-5929600b4e79) reproduces §5.1. The local paragraph has one spelling difference (`позэлементные` versus `поэлементные`), so it is not byte-identical to the official excerpt. This does not authorize a numeric thermal finding without the project values.
- D5: the [Минстрой archive search](https://minstroyrf.gov.ru/docs/?active%5B%5D=65&date_from=&date_to=&q=%D0%A1%D0%9F+51.13330) indexes change №4, and the [Росстандарт card](https://protect.gost.ru/sp/changesdetails/0ff54d77-7ba7-441d-bd68-dbaa9b73f7f2) fixes its identity. Neither supplies a verified row/footnote selection in this task. An open third-party PDF with blank order/date fields is a draft and was not promoted.
- C15: the [Росстандарт correction card](https://protect.gost.ru/gost/changesdetails/e4ce8ca2-4c41-445f-adb5-6bbfbe400b67) confirms one page in ИУС 5-2026 but leaves content blank. No cabin-dimension claim is enabled.

The local bundle PDF SHA-256 values are copied from the checked `AR-NORM-MAP-REVIEW-PREP-01` source record at `bc8e2962`; they identify offline comparison bytes, not served Blob custody. The prior DB measurement was zero bindings. This task did not fetch and hash new amendment binaries, refresh that DB measurement, prove current editions, qualify a `nrs_` set, or change the served AR profile. The source policy is an input to later map review and runtime work, not a beta release claim.

## Checks and handoff

`tests/contract/norm_map` plus `tests/contract/program`: **34 passed** after the scenario decision. The tests include known-gap refusal, card-only refusal, item totality, scenario/numeric-policy refusal and digest tamper. Python imports succeeded. `git diff --check` passed; changed paths were the task/report, the policy JSON/validator and its contract test. Contracts, migrations, composition root, root locks, provider, UI, corpus bytes, `origin/main` and deployment host are untouched. Revert this task's six files to remove the unserved policy.
